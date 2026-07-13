# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for postgres client, scipy/numpy compilation,
# and WeasyPrint PDF compilation (pango, cairo, ffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root system user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy application source code
COPY . .

# Set permissions for the non-root user
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose FastAPI default port
EXPOSE 8000

# Configure FastAPI health check inside the container
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "healthcheck.py"]

# Default command (overridden for Celery worker/Flower in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
