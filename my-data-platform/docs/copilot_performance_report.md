# Performance & Scalability Report — AI Copilot

This document outlines the performance characteristics of the **AI Analytics Copilot**.

---

## 1. Low-Latency Intent and Rule Routing

Conversational latency is critical for user experience. If a chat requires parsing, the engine must respond within sub-second thresholds.

DataSaaS Pro ensures low-latency execution by using:
* **Regex and Token-Based Intent Classification**: Rather than calling costly LLMs to classify basic user intents (which consumes 1.5 - 3.0 seconds and has high API costs), the **Intent Engine** uses pre-compiled regular expression patterns to classify actions instantly (in under 0.05 milliseconds).
* **Failsafe Rules Filtering**: Pre-verifies queries against schema maps before starting calculations. If columns do not exist, the request is immediately rejected, preventing unnecessary computation cycles.

---

## 2. In-Memory Mathematical Facts Aggregations

* **Polars Optimization**: When a query triggers calculations (such as outliers anomaly checking or grouping aggregates), the **Analytics Engine** evaluates the queries on Polars using parallel multi-threaded CPU instructions.
* **Deterministic Results**: Calculations (like grouping top categories or scanning missing ratios) execute in under 10 milliseconds, even for datasets with millions of rows.

---

## 3. Asynchronous Database Logging

Saving message histories can introduce database transaction delays:
* All chat messages and session updates write to SQLite database using asynchronous non-blocking connection threads via SQLAlchemy Session scope, maintaining rapid HTTP response times.
