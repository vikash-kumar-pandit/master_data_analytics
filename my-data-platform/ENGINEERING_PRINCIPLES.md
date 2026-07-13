# DataSaaS Pro Platform Engineering Principles

This document defines the core technical values, architectural constraints, and operational principles governing the development and release of the DataSaaS Pro platform.

---

## 📜 Core Engineering Principles

### 1. Truth over Marketing
Never publish or state an unverified benchmark. Performance metrics, row scaling capacities, and processing limits must be clearly classified under their exact status:
* **Measured**: Proven directly via the automated Pytest/Locust validation suites.
* **Validated**: Executed under constrained production container profiles.
* **Target / Estimated**: System scaling limits based on mathematical time/space complexity modeling.

### 2. AI Must Explain Itself
Artificial Intelligence recommendations must never be a black box. Every prediction, clean operation, visualization recommended, or insight returned must be structured with the following metadata:
* **Reason**: Why this operation is being suggested.
* **Evidence**: The statistical or logical data features supporting the action.
* **Confidence**: Statistical rating or confidence intervals.
* **Next Action**: Recommended next execution steps for the user.

### 3. Everything is Versioned
The platform treats state updates as nodes in an immutable graph. The following assets must be versioned, logged, and rollable:
* System Code configurations.
* Raw and transformed Datasets.
* Processing Pipelines and Nodes.
* Data Cleaning sequences.
* AutoML Models parameters.
* Executive Reports configurations.
* AI Copilot Conversational Memories.

### 4. Every Feature Must Be Observable
No component is ready for production without instrumentation. Every engine must expose telemetry including:
* Structured logs (using `structlog` JSON format).
* Performance metrics (latencies, rows per second, memory consumption).
* HTTP/WebSocket health statuses.

### 5. Every Feature Must Be Testable
No feature code is merged without matching regression and unit tests. The backend codebase enforces an automated **80% minimum test coverage gate** inside the CI/CD pipeline.

### 6. Every Feature Must Be Exportable
No dead ends are allowed. Every processing stage must produce clean, reusable, and standard-compliant outputs (e.g. Polars dataframes, SQLite logs, PDF streams, or PPTX slides) for downstream integrations.

### 7. AI Assists the User
The AI is an assistant, not a replacement for human decisions. The user must always remain in control with the ability to review, edit, reject, or undo any auto-generated actions.

### 8. Performance is a Feature
Scalability, memory efficiency, and execution latency are part of software correctness. Code must leverage efficient data structures (e.g. Polars lazy evaluation, zero-copy formats) to minimize footprint limits.

### 9. Documentation Ships with Code
A feature is incomplete until its operations manual is compiled. Every module release requires:
* Architectural guidelines.
* API endpoints specifications.
* Executed benchmark results.

### 10. Never Sacrifice Architecture for Speed
A feature delayed is acceptable; introducing technical debt is not. Code must remain modular, decoupled, and consistent with the platform's multi-tier design.
