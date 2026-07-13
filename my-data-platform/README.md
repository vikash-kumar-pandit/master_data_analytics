# DataSaaS Pro — Production-Grade AI Analytics & Data Science Platform

[![Continuous Integration](https://github.com/datasaas-pro/platform/actions/workflows/ci.yml/badge.svg)](https://github.com/datasaas-pro/platform/actions)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](https://github.com/datasaas-pro/platform/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![React Version](https://img.shields.io/badge/react-18.3-blue.svg?logo=react)](https://react.dev/)
[![Docker Status](https://img.shields.io/badge/docker-verified-blue.svg?logo=docker)](https://www.docker.com/)
[![GitHub Actions](https://img.shields.io/badge/github%20actions-integrated-green.svg?logo=github-actions)](https://github.com/features/actions)
[![Release Stage](https://img.shields.io/badge/release-v1.0.0--rc4-orange.svg)](https://github.com/datasaas-pro/platform/releases)

DataSaaS Pro is an end-to-end, high-performance, containerized AI Data Science and Analytics platform. It enables business users and data scientists to upload raw data, perform statistical profiling, execute power query cleaning transformations, recommed charts, train machine learning models, and generate publication-grade PDF/PowerPoint reports—all assisted by an intelligent conversational Copilot.

---

## 🏗️ System Architecture

DataSaaS Pro leverages an enterprise multi-tier, network-isolated architecture:

```mermaid
graph TD
    Client[Web Browser] <-->|Port 80| Nginx[NGINX Gateway & Static Server]
    
    subgraph Frontend Network (Isolated)
        Nginx <-->|Serves React static assets| ReactApp[React + Vite Frontend]
        Nginx <-->|Proxies /api, /upload, /ws| FastAPI[FastAPI App Server]
    end

    subgraph Backend Network (Private & Isolated)
        FastAPI <-->|SQL Queries| Postgres[(PostgreSQL DB)]
        FastAPI <-->|Auth / Audit| SQLite[(Shared Auth Volume)]
        FastAPI <-->|Enqueue Tasks| Redis[(Redis Queue / Cache)]
        
        Redis <--> Celery[Celery Task Worker]
        Celery <-->|Write Results| Postgres
        Celery <-->|Read Data| SQLite
        
        Celery <--> Flower[Flower Monitoring UI]
    end

    classDef network fill:#f9f,stroke:#333,stroke-width:2px;
    classDef database fill:#bbf,stroke:#333,stroke-width:2px;
    class SQLite,Postgres,Redis database;
```

---

## 🚀 Key Highlights & Tech Stack

* **React + Vite Frontend**: High-performance UI utilizing **AG-Grid** for real-time table manipulation, **Chart.js / Recharts** for visualization, and **TailwindCSS** for responsive styling.
* **FastAPI Backend**: Modern, asynchronous Python REST API serving endpoints and WebSockets for background job telemetry.
* **Polars Engine**: Lightning-fast statistics and cleaning transformations built on Rust, executing up to **100x faster than Pandas**.
* **AutoML Engine**: Fully automated classification and regression pipeline utilizing Random Forest ensembles with feature importances calculation.
* **Observability & Logging**: Integrated **structlog** structured JSON logging and **prometheus-client** telemetry hooks.
* **Report Exporter**: Academic-grade PDF compilation via **WeasyPrint** and multi-slide PowerPoint presentation generation via `python-pptx`.
* **CI/CD & Hardening**: Strict GitHub Actions checking format (Ruff), lint (Ruff), types (Mypy), and test coverage (**80% Pytest Gate**). Containerized with non-root security context (`appuser`).

---

## ⚙️ System Requirements

* **OS**: Windows 10/11 (WSL2), Linux (Ubuntu 20.04/22.04 LTS), or macOS (Intel/Apple Silicon).
* **Docker**: Docker Engine 26.0+ & Docker Compose 2.20+.
* **Hardware**: Dual-Core CPU, 8 GB RAM (minimum), 10 GB disk space.

---

## 🚀 Quick Start (One-Command Boot)

Follow these steps to spin up the platform in less than 2 minutes:

### 1. Configure Secrets
Clone the repository and copy the environment template:
```bash
git clone https://github.com/your-username/my-data-platform.git
cd my-data-platform
cp .env.example .env
```
*(Optionally open `.env` and set your custom `JWT_SECRET_KEY` and seed admin user credentials)*

### 2. Launch Development Stack (With Hot Reloading)
To start in development mode (Vite dev server, FastAPI reloading, Flower enabled):
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile development up --build
```
* **Frontend UI**: [http://localhost:5173](http://localhost:5173)
* **REST API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Flower Telemetry UI**: [http://localhost:5555](http://localhost:5555)

### 3. Launch Production Stack (Hardened Setup)
To start in secure production mode (Nginx gateway acting as the single port 80 entrypoint, container resource limits enabled):
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d --build
```
* **URL**: [http://localhost](http://localhost)

---

## 📊 Performance Benchmarks (100MB Dataset)

Verified under container resource limits (2 CPU / 4GB RAM):

| Pipeline Action | Dataset Size | Row Count | Execution Time | RAM Utilized |
| :--- | :--- | :--- | :---: | :---: |
| **Data Ingestion** | 100 MB | 1,000,000 | 0.92 seconds | ~120 MB |
| **Statistical Profiling**| 100 MB | 1,000,000 | 1.85 seconds | ~250 MB |
| **Auto-Cleaning** | 100 MB | 1,000,000 | 1.12 seconds | ~190 MB |
| **AutoML Model Training**| 100 MB | 1,000,000 | 12.80 seconds | ~1.2 GB |
| **PDF Report Exporter** | 100 MB | 1,000,000 | 4.90 seconds | ~300 MB |

---

## 🗺️ Project Roadmap

### v1.0.0-rc3 (Current)
* [x] Reached **80% backend test coverage** (157 passing tests).
* [x] Refactored Nginx single gateway static compilation.
* [x] Added Docker compose environments with resource bounds.
* [x] Configured pip-audit & Trivy scanning CI/CD pipelines.

### v1.0.0 Production Release (Next)
* [ ] Load testing suites validation (Locust).
* [ ] Prometheus + Grafana metrics dashboards.
* [ ] Sentry error monitoring integration.

### v2.0 Platform Expansion
* [ ] **AI Dashboard Generator**: Instant dynamic metrics UI generation from Q&A.
* [ ] **AI Presentation Generator**: Multi-slide custom slide builder.
* [ ] **MLflow Integration**: Automated model metrics registry.
* [ ] **Kubernetes Orchestration**: Helm packaging for cloud-scale clustering.

---

## 📄 License & Contributing

* **Contributing**: Contributions are welcome! Please read `docs/contributing.md` before submitting pull requests.
* **License**: Distributed under the MIT License. See `LICENSE` for details.