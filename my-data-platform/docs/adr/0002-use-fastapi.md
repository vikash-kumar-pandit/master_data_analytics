# Architectural Decision Record 0002: Use FastAPI for Platform APIs

## Status
Approved

## Context
The application requires a modern, lightweight, high-performance web framework to serve REST APIs and manage persistent real-time connections (WebSockets) for background process telemetry.

## Decision
We chose **FastAPI** as the backend framework instead of Django or Flask.

## Rationale
1. **Asynchronous execution**: Native support for Python's `async/await` syntax allows concurrent I/O task scheduling without thread blocks.
2. **Speed**: Benchmarked close to NodeJS and Go under ASGI servers (uvicorn/gunicorn).
3. **Pydantic Validation**: Automatic schema declaration, typing safety, and JSON serialization out of the box.
4. **Auto-Documentation**: Generates Swagger UI (`/docs`) and ReDoc (`/redoc`) instantly, speeding up frontend API integration.

## Consequences
* Backend routes are structured as ASGI APIRouters and mounted in a single `main.py` entrypoint.
* Direct integration with `starlette` enables simple middleware hooks for CORS, security headers, and rate limiting.
