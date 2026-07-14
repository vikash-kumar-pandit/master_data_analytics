import os
# Add GTK+ DLL directory for WeasyPrint on Windows
if os.name == 'nt':
    for sd in [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files\GTK3-Runtime\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime\bin",
    ]:
        if os.path.exists(sd):
            try:
                os.add_dll_directory(sd)
                break
            except Exception:
                pass

import logging
import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from auth import auth_router
import auth as auth_module
from observability import setup_observability

# Existing Sub-routers
from pipeline_routes import router as pipeline_router
from profiling.routes import router as profiling_router
from preparation.routes import router as preparation_router
from copilot.routes import router as copilot_router
from visualization.routes import router as visualization_router

# Refactored Routers
from api.v1.router import router as v1_router
from api.ws.monitor import router as ws_router

# Initialize Sentry if configured
try:
    import sentry_sdk
    SENTRY_DSN = os.getenv('SENTRY_DSN') or os.getenv('SENTRY_DSN_URL')
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=float(os.getenv('SENTRY_TRACES', 0.1)))
except Exception:
    # If sentry not installed or init fails, continue without crashing
    pass

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app_context: FastAPI):
    """Spawn a daemon thread that runs audit log cleanup once per day.

    Controlled via `AUDIT_LOG_RETENTION_DAYS` (days to keep, default 90) and
    `AUDIT_LOG_CLEANUP_INTERVAL_SECONDS` (interval between runs, default 86400).
    """
    import threading
    import time
    import logging

    retention = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
    interval = int(os.getenv("AUDIT_LOG_CLEANUP_INTERVAL_SECONDS", str(24 * 60 * 60)))

    def _cleanup_loop():
        logger = logging.getLogger("audit")
        logger.info("Starting audit cleanup thread: retention=%s days interval=%s seconds", retention, interval)
        try:
            while True:
                try:
                    deleted = auth_module.db.cleanup_old_audit_logs(auth_module.DB_PATH, retention)
                    logger.info("Scheduled audit cleanup removed %d rows older than %d days", deleted, retention)
                except Exception as exc:
                    logger.exception("Scheduled audit cleanup failed: %s", exc)
                time.sleep(interval)
        except Exception as exc:
            logger.exception("Audit cleanup thread terminated unexpectedly: %s", exc)

    thread = threading.Thread(target=_cleanup_loop, name="audit-cleanup", daemon=True)
    thread.start()
    yield


app = FastAPI(title="Stateless No-Code Big Data Platform", lifespan=lifespan)

# Setup CORS Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ],
    allow_origin_regex=os.getenv(
        "CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1):\d+$",
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP exception: {exc.detail} (status code: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"status": "error", "detail": "Invalid request fields", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": "An unexpected error occurred. Please contact the administrator."}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Include Routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(pipeline_router)
app.include_router(profiling_router)
app.include_router(preparation_router)
app.include_router(copilot_router)
app.include_router(visualization_router)
app.include_router(ws_router)
app.include_router(v1_router)

setup_observability(app)

if __name__ == "__main__":
    import uvicorn
    import os

    debug_flag = os.getenv('DEBUG', os.getenv('DEBUG_MODE', 'false')).lower() in ('1', 'true', 'yes')
    reload_flag = os.getenv('RELOAD', 'false').lower() in ('1', 'true', 'yes') or debug_flag
    log_level = os.getenv('LOG_LEVEL', os.getenv('LOGLEVEL', 'info')).lower()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('PORT', 8000)),
        reload=reload_flag,
        log_level=log_level,
    )