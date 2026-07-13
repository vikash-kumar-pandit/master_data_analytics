# DataSaaS Pro v2 Distributed Enterprise Architecture (1M+ Concurrent Users Target)

This document establishes the architecture blueprint and scalability parameters for the next-generation (v2.0) distributed microservices platform, designed to support **1,000,000+ concurrent users**.

---

## 🏗️ High-Level Distributed Architecture (HLD)

To scale past the constraints of a single server, all core modules are split into decoupled services operating across isolated container layers, orchestrated via an asynchronous event bus:

```text
                               Users / Clients
                                     │
                             Cloudflare CDN + WAF
                                     │
                             L4/L7 Load Balancers
                                     │ (Gunicorn/Nginx)
                             API Gateway (Kong/APISIX)
                                     │
        ┌───────────────────┬────────┴───────────┬───────────────────┐
        │                   │                    │                   │
  Auth Service       Dataset Service       AI Copilot API      Reporting API
   (FastAPI)           (Go/Rust)             (FastAPI)           (FastAPI)
        │                   │                    │                   │
        └───────────────────┴────────┬───────────┴───────────────────┘
                                     │
                          Event Message Bus (Apache Kafka)
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       │                             │                             │
Data Cleaning Worker       Visual Recommendation Worker     AutoML Train Worker
     (Polars/Rust)                 (Matplotlib/Rust)          (Scikit-Learn/Go)
       │                             │                             │
       └─────────────────────────────┼─────────────────────────────┘
                                     │
                       Distributed Object Storage (MinIO/S3)
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
  PostgreSQL Cluster           Redis Sentinel Cluster       ClickHouse Cluster
(Transactional Data)          (Caching & Session Store)    (High-Volume Logs)
```

---

## 📦 Microservices Boundaries & Core APIs

The monolith is partitioned into nine distinct, containerized services. Each service owns its data repository and scales independently under Kubernetes (HPA):

1. **Auth Service**: Manages JWT lifecycle, OAuth2 providers, and Role-Based Access Controls (RBAC).
2. **Dataset API Service**: High-throughput file parser (written in Go/Rust for fast file streaming), chunking data fragments and writing raw files to MinIO/S3.
3. **Profiling Service**: Aggregates statistical metrics (null rates, skewness, quantiles) using Polars, publishing metadata back to PostgreSQL.
4. **Data Cleaning Worker**: Event-triggered consumer executing Winsorization, formatting, and custom regex transformations.
5. **Visualization Recommendation Service**: Scans dataset shapes and recomend charts, storing renders directly in CDN cache.
6. **AutoML Worker**: Distributed scikit-learn/XGBoost queue processor managing isolated train/test tasks.
7. **Reporting Service**: Compiles executive slides and PDF formats.
8. **AI Copilot Service**: Conversational LLM middleware parsing intents, loading history, and calling local vector databases.
9. **Notification Service**: WebSockets broadcaster pushing process alerts to the UI.

---

## 🗄️ Database Tiers & Storage Splitting

No single datastore can handle transactional records, cache storage, vector metrics, and log aggregation simultaneously. Storage is decoupled:

| Storage Domain | Database Engine | Rationale | Scaling Method |
| :--- | :--- | :--- | :--- |
| **Users & Catalog** | **PostgreSQL** | Strict ACID transactional compliance. | Primary-Replica Replication + Sharding |
| **User Sessions** | **Redis** | Sub-millisecond read/write speeds. | Redis Sentinel + Partitioning |
| **Raw Datasets** | **S3 / MinIO** | Highly durable, cheap blob storage. | Bucket replication + CDN caching |
| **Audit Logs & Metrics** | **ClickHouse** | Columnar storage optimized for high-volume logs. | ClickHouse Cluster |
| **Vector Embeddings** | **Qdrant / pgvector** | Fast cosine similarity search for LLM RAG. | Horizontal Index Sharding |
| **Analytics Cache** | **Redis** | Caches recommended visuals and metrics facts. | Local cluster shards |

---

## ⚡ Event-Driven Asynchronous Workflows

Synchronous HTTP calls block threads under heavy loads. Services communicate via **Apache Kafka** event topics:

```text
User uploads CSV ──> Dataset Service writes to S3 ──> Publishes topic `dataset.uploaded`
                                                             │
  ┌───────────────────────────┬──────────────────────────────┴──────────────────────────────┐
  ▼                           ▼                                                             ▼
Profiling Worker            Cleaning Worker                                               Notification API
Aggregates stats            Applies initial transforms                                    Pushes socket "Ingested"
Publishes `stats.completed`  Publishes `cleanup.completed`                                 to client UI
```

---

## 🎯 Target Scale Matrix

| Scaling Target Metric | Value Parameter | Architecture Enforcement |
| :--- | :--- | :--- |
| **Concurrent Connections** | **1,000,000** | Kubernetes HPA + Go-based API Gateway |
| **API Latency** | **< 300 ms** | Caching layer via Redis + CDN cache edges |
| **Upload Size Ceiling** | **100 GB** | Multipart chunked streaming directly to S3 |
| **Active Workspaces** | **100,000+** | Database sharding on Workspace ID |
| **System Uptime** | **99.99%** | Multi-region deployment + failover Sentinel |
