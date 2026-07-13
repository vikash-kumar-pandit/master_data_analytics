from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections import defaultdict, deque
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from auth import decode_access_token
from activity_tracker import record_activity
from metrics import record_request


def _configure_structlog() -> None:
    if not STRUCTLOG_AVAILABLE:
        return
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging() -> logging.Logger:
    if STRUCTLOG_AVAILABLE:
        _configure_structlog()

    logger = logging.getLogger("data_platform")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if STRUCTLOG_AVAILABLE:
            formatter = logging.Formatter("%(message)s")
        else:
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
            )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    return logger


logger = configure_logging()

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
    "/generate-insights": int(os.getenv("RATE_LIMIT_INSIGHTS_PER_MINUTE", "30")),
    "/api/explain-automl": int(os.getenv("RATE_LIMIT_EXPLAIN_PER_MINUTE", "15")),
}

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
    "/api/export-results",
    "/api/explain-automl",
)

FALLBACK_RATE_LIMIT_STATE: dict[str, deque[float]] = defaultdict(deque)
RATE_LIMIT_STATE = FALLBACK_RATE_LIMIT_STATE


class RedisRateLimiter:
    def __init__(self, redis_url: str | None = None) -> None:
        self._client: redis.Redis | None = None
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def _is_test_mode(self) -> bool:
        return bool(os.getenv("PYTEST_CURRENT_TEST"))

    def _get_client(self) -> redis.Redis | None:
        if self._client is not None:
            return self._client
        if not REDIS_AVAILABLE or self._is_test_mode():
            return None
        try:
            self._client = redis.Redis.from_url(self._redis_url, socket_timeout=1, socket_connect_timeout=1)
            self._client.ping()
            return self._client
        except Exception:
            logger.warning("Redis rate limiter unavailable, falling back to in-memory limiter")
            return None

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        if self._is_test_mode():
            return self._fallback_is_allowed(key, limit, window_seconds)
        client = self._get_client()
        if client is None:
            return self._fallback_is_allowed(key, limit, window_seconds)

        redis_key = f"rate_limit:{key}"
        now = time.time()
        try:
            pipeline = client.pipeline()
            pipeline.zadd(redis_key, {now: now})
            pipeline.zremrangebyscore(redis_key, 0, now - window_seconds)
            pipeline.zcard(redis_key)
            pipeline.expire(redis_key, window_seconds + 1)
            results = pipeline.execute()
            current_count = results[2]
            remaining = max(0, limit - current_count)
            allowed = current_count < limit
            return allowed, remaining
        except Exception:
            return self._fallback_is_allowed(key, limit, window_seconds)

    def _fallback_is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        bucket = FALLBACK_RATE_LIMIT_STATE[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        allowed = len(bucket) < limit
        if allowed:
            bucket.append(now)
        remaining = max(0, limit - len(bucket))
        return allowed, remaining


_redis_rate_limiter = RedisRateLimiter()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.scope.get("type") == "websocket":
            return await call_next(request)

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
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=rate_error.status_code,
                content={"detail": rate_error.detail, "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._log_event(
                request=request,
                status_code=500,
                duration_ms=duration_ms,
                request_id=request_id,
                error=str(exc),
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration_ms / 1000.0,
        )

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
        test_id = os.getenv("PYTEST_CURRENT_TEST")
        if test_id:
            return f"{test_id}:{client_host}"
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

    def _check_rate_limit(self, request: Request):
        if request.method == "OPTIONS":
            return None
        limit = self._get_limit(request.url.path)
        if limit <= 0:
            return None
        from fastapi import HTTPException
        from starlette import status

        key = f"{self._client_key(request)}:{request.url.path}"
        allowed, _remaining = _redis_rate_limiter.is_allowed(key, limit, RATE_WINDOW_SECONDS)
        if not allowed:
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry later.",
            )
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

        if STRUCTLOG_AVAILABLE:
            log = structlog.get_logger("data_platform")
            log.info(**payload)
        else:
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
            if STRUCTLOG_AVAILABLE:
                log = structlog.get_logger("data_platform")
                log.exception("activity_record_failed", request_id=request_id, path=request.url.path)
            else:
                logger.exception("activity_record_failed: request_id=%s path=%s", request_id, request.url.path)


def setup_observability(app) -> None:
    app.add_middleware(RequestLoggingMiddleware)
