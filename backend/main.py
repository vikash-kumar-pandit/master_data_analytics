from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from auth import create_access_token, get_current_user, TokenData, init_db
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="DataStudio 2026 API", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error", "path": str(request.url)},
    )

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/token")
async def login(payload: LoginRequest):
    if payload.username == "admin" and payload.password == "admin":
        access_token_expires = timedelta(minutes=60)
        access_token = create_access_token(
            data={"sub": payload.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )

@app.get("/stats")
async def get_stats(current_user: TokenData = Depends(get_current_user)):
    logger.info(f"User {current_user.username} requested /stats")
    return {
        "metric1": "54,230",
        "metric2": "1,205",
        "metric3": "99.9%",
        "metric4": "12.5k"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}