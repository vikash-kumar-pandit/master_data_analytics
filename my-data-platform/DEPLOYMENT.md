# DataSaaS Pro Platform Deployment & Operations Guide

This guide details how to deploy and operate the DataSaaS Pro platform (React Frontend, FastAPI Backend, Celery Workers, Redis Cache, PostgreSQL Database, and Nginx reverse proxy) in Dockerized environments.

---

## 🏗️ Deployment Architecture

The production Docker Compose setup configures a **Single Nginx Gateway** serving static files directly and routing API and websocket calls, securing container boundaries and reducing resource footprints:

```text
                             Internet
                                │
                        NGINX (Gateway)
                         (Serves React)
                                │ (Port 80)
                         ┌──────┴──────┐
                         │             │
                      FastAPI      Postgres DB
                         │
         ┌───────────────┴───────────────┐
         │                               │
       Redis                       Celery Worker
                                         │
                                      Flower (Dev)
```

* **Frontend Network (`datasaas_frontend_net`)**: Hosts Nginx (Gateway) and FastAPI.
* **Backend Network (`datasaas_backend_net`)**: Hosts FastAPI, PostgreSQL, Redis, Celery, and Flower. Database ports are shielded from host access in production.

---

## ⚙️ Environment Configuration

1. Copy the `.env.example` template to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```
2. Populate the parameters in `.env`:
   * **`JWT_SECRET_KEY`**: Set a strong cryptographically secure 32+ character key.
   * **`ADMIN_USERNAME`** & **`ADMIN_PASSWORD`**: Seed credentials for the default administrator.
   * **`POSTGRES_USER`**, **`POSTGRES_PASSWORD`**, & **`POSTGRES_DB`**: Settings for the PostgreSQL database container.

---

## 🚀 One-Command Deployment

The platform is designed to be fully bootable in development, staging, or production profiles with a single command.

### 1. Development Mode (With Hot Reloading & UI Dev Server)
In development, the local files are mounted into the containers to enable automatic reloading of both backend Python files (via uvicorn reload) and frontend React files (via Vite Dev Server). Ports 5173, 8000, 5432, and 5555 are mapped directly to the host for debugger connections.

Run the following command:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile development up --build
```
* **Frontend Web Application**: [http://localhost:5173](http://localhost:5173)
* **Backend REST API**: [http://localhost:8000](http://localhost:8000)
* **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)

---

### 2. Staging Mode (Gateway Compilation Verification)
Runs the platform exactly as configured in the base staging compose file. This utilizes a multi-stage Nginx Dockerfile to compile Vite static assets and serve them directly, eliminating the need for a separate frontend container.

Run the following command:
```bash
docker compose --profile staging up --build
```
* **Frontend & Gateway (Nginx)**: [http://localhost](http://localhost)

---

### 3. Production Mode (Hardened Stack)
Production mode locks down all ports on the host machine except for Port 80 (Nginx). Security headers (CSP, XSS, X-Frame) are enforced, debug logs are disabled, CPU/Memory resource constraints are applied, and containers are set to restart automatically if they crash.

Run the following command:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d --build
```
* **Production URL**: [http://localhost](http://localhost) (or configured domain)

To stop the production stack:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile production down
```

---

## 🔍 Verification & Health Checks

Verify container execution status and non-root execution:

1. **Verify Container Health**:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```
   All containers (`datasaas_api`, `datasaas_db`, `datasaas_redis`, etc.) should display `(healthy)`.

2. **Verify Non-Root execution**:
   Ensure FastAPI and Celery are running under the unprivileged `appuser` (UID 1000):
   ```bash
   docker exec -it datasaas_api whoami
   # Output should be: appuser
   ```

3. **Verify Resource Constraints**:
   Check if CPU/Memory limits are enforced:
   ```bash
   docker inspect datasaas_api --format "CPUs: {{.HostConfig.NanoCpus}}, Memory: {{.HostConfig.Memory}} bytes"
   ```
