from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from auth import decode_access_token
from activity_tracker import record_activity


logger = logging.getLogger("data_platform")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

RATE_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
DEFAULT_RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
RATE_LIMITS = {
    "/api/auth/login": int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10")),
    "/upload": int(os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "20")),
    "/clean": int(os.getenv("RATE_LIMIT_CLEAN_PER_MINUTE", "20")),
    "/arrange": int(os.getenv("RATE_LIMIT_ARRANGE_PER_MINUTE", "20")),
    "/automl": int(os.getenv("RATE_LIMIT_AUTOML_PER_MINUTE", "10")),
    "/api/analytics/query": int(os.getenv("RATE_LIMIT_ANALYTICS_QUERY_PER_MINUTE", "30")),
    "/api/analytics/forecast": int(os.getenv("RATE_LIMIT_ANALYTICS_FORECAST_PER_MINUTE", "20")),
    "/api/analytics/compare": int(os.getenv("RATE_LIMIT_ANALYTICS_COMPARE_PER_MINUTE", "20")),
    "/api/analytics/report": int(os.getenv("RATE_LIMIT_ANALYTICS_REPORT_PER_MINUTE", "20")),
    "/api/clean-background": int(os.getenv("RATE_LIMIT_BACKGROUND_CLEAN_PER_MINUTE", "10")),
    "/api/predict-background": int(os.getenv("RATE_LIMIT_BACKGROUND_PREDICT_PER_MINUTE", "10")),
    "/generate-insights": int(os.getenv("RATE_LIMIT_INSIGHTS_PER_MINUTE", "30")),
    "/api/explain-automl": int(os.getenv("RATE_LIMIT_EXPLAIN_PER_MINUTE", "15")),
}
RATE_LIMIT_STATE: dict[str, deque[float]] = defaultdict(deque)

SENSITIVE_PATH_PREFIXES = (
    "/upload",
    "/clean",
    "/arrange",
    "/automl",
    "/api/analytics/query",
    "/api/analytics/forecast",
    "/api/analytics/compare",
    "/api/analytics/report",
    "/generate-insights",
    "/api/clean-background",
    "/api/predict-background",
    "/api/export-results",
    "/api/explain-automl",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        rate_error = self._check_rate_limit(request)
        if rate_error:
            self._log_event(
                request=request,
                status_code=rate_error.status_code,
                duration_ms=0,
                request_id=request_id,
                error=rate_error.detail,
            )
            return JSONResponse(
                status_code=rate_error.status_code,
                content={"detail": rate_error.detail, "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )

        try:
            response = await call_next(request)
        except HTTPException as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._log_event(
                request=request,
                status_code=exc.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                error=str(exc.detail),
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail, "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        except Exception as exc:  # pragma: no cover - defensive middleware guard
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                json.dumps(
                    {
                        "event": "unhandled_error",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(exc),
                    }
                )
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        self._log_event(
            request=request,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        return response

    def _get_limit(self, path: str) -> int:
        for prefix, limit in RATE_LIMITS.items():
            if path.startswith(prefix):
                return limit
        return DEFAULT_RATE_LIMIT

    def _client_key(self, request: Request) -> str:
        client_host = request.client.host if request.client else "unknown"
        return client_host

    def _get_user_context(self, request: Request) -> dict[str, Any]:
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return {"username": None, "role": None}

        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            return {"username": None, "role": None}

        try:
            return decode_access_token(token)
        except Exception:
            return {"username": None, "role": None}

    def _check_rate_limit(self, request: Request) -> HTTPException | None:
        if request.method == "OPTIONS":
            return None

        limit = self._get_limit(request.url.path)
        if limit <= 0:
            return None

        key = f"{self._client_key(request)}:{request.url.path}"
        now = time.time()
        bucket = RATE_LIMIT_STATE[key]

        while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= limit:
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry later.",
            )

        bucket.append(now)
        return None

    def _log_event(
        self,
        *,
        request: Request,
        status_code: int,
        duration_ms: int,
        request_id: str,
        error: str | None = None,
    ) -> None:
        user_context = self._get_user_context(request)
        payload = {
            "event": "request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_ip": self._client_key(request),
            "username": user_context.get("username"),
            "role": user_context.get("role"),
        }
        if error:
            payload["error"] = error
        logger.info(json.dumps(payload, default=str))

        try:
            record_activity(
                username=user_context.get("username"),
                role=user_context.get("role"),
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=self._client_key(request),
            )
        except Exception:
            # Never block API responses for analytics persistence issues.
            logger.exception(
                json.dumps(
                    {
                        "event": "activity_record_failed",
                        "request_id": request_id,
                        "path": request.url.path,
                    }
                )
            )


def setup_observability(app) -> None:
    app.add_middleware(RequestLoggingMiddleware)
