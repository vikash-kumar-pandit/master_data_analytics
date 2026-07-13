from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram
    from prometheus_fastapi_instrumentator import Instrumentator
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    ACTIVE_USERS = Gauge(
        "active_users_total",
        "Number of active users",
    )
    DATASET_SIZE = Histogram(
        "dataset_row_count",
        "Dataset row count distribution",
        buckets=[10, 100, 1000, 10000, 100000, 1000000],
    )
    MODEL_ACCURACY = Gauge(
        "model_accuracy",
        "Latest model accuracy score",
    )
    TASK_QUEUE_DEPTH = Gauge(
        "celery_task_queue_depth",
        "Number of pending Celery tasks",
    )
else:
    REQUEST_COUNT = None
    REQUEST_LATENCY = None
    ACTIVE_USERS = None
    DATASET_SIZE = None
    MODEL_ACCURACY = None
    TASK_QUEUE_DEPTH = None


def record_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_dataset_size(rows: int) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    DATASET_SIZE.observe(rows)


def record_model_accuracy(accuracy: float | None) -> None:
    if not PROMETHEUS_AVAILABLE or accuracy is None:
        return
    MODEL_ACCURACY.set(accuracy)


def setup_prometheus(app) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    Instrumentator().instrument(app).expose(app, include_in_schema=False)
