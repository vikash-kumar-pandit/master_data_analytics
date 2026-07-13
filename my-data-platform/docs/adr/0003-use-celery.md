# Architectural Decision Record 0003: Use Celery for Background Tasks

## Status
Approved

## Context
Automated Machine Learning (AutoML) training, statistical profiling, and large dataset exports are CPU and RAM intensive. Running these tasks directly inside FastAPI's request-response lifecycle would block the API thread pool and lead to client timeouts.

## Decision
We chose **Celery** as the distributed task queue with **Redis** as the message broker.

## Rationale
1. **Asynchronous execution**: Decouples API execution from heavy machine learning computations, returning task UUIDs instantly to the client.
2. **Task Telemetry**: Celery supports progress callbacks and status checks, which are pushed to the frontend via WebSockets in real time.
3. **Queue Monitoring**: Out-of-the-box integration with Flower allows operational monitoring of task durations, retries, and worker concurrency.
4. **Concurrency Controls**: Concurrency can be set dynamically (`--concurrency=2` in compose) to protect container resource bounds.

## Consequences
* Background ML training, file cleans, and report exports are registered as Celery tasks in `worker.py`.
* Requires a running Redis container to act as the broker and results database backend.
