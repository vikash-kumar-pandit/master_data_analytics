# Sequence Diagram — Data Preparation Request Flow

This document details the sequence of execution when a client triggers a data preparation transformation step.

---

```mermaid
sequence_diagram
sequenceLine: 1
sequenceLine: 2
sequenceLine: 3
sequenceLine: 4
sequenceLine: 5
sequenceLine: 6
sequenceLine: 7
sequenceLine: 8
sequenceLine: 9
sequenceLine: 10
sequenceLine: 11
sequenceLine: 12
sequenceLine: 13
sequenceLine: 14
sequenceLine: 15
sequenceLine: 16
sequenceLine: 17
sequenceLine: 18
sequenceLine: 19
sequenceLine: 20
sequenceLine: 21
sequenceLine: 22
sequenceLine: 23
sequenceLine: 24
sequenceLine: 25
```

```mermaid
sequenceDiagram
    autonumber
    actor User as Client (Frontend)
    participant API as FastAPI Router
    participant DB as SQLite Database
    participant Service as Preparer Service
    participant Disk as Parquet Storage

    User->>API: POST /api/preparation/run (project_id, op_type, params)
    API->>DB: Query current Active Version (UndoRedoStack & DatasetVersion)
    DB-->>API: Return active version file path
    API->>Service: Initialize Service (input_file_path, output_file_path)
    API->>Service: execute_transform(op_type, params)
    Service->>Disk: Scan input version (Polars LazyFrame)
    Service->>Service: Compile transformation expression graph
    Service->>Disk: Sink results streamingly (write version_{n}.parquet)
    Service-->>API: Return comparison stats & AI explanation
    API->>DB: Insert new DatasetVersion record
    API->>DB: Insert Transformation details
    API->>DB: Insert TransformationHistory step mapping
    API->>DB: Update UndoRedoStack pointer to (current_pointer + 1)
    DB-->>API: Transaction committed
    API->>Disk: Load preview rows of new version
    Disk-->>API: Return top 10 preview dicts
    API-->>User: Return success response, schema comparisons & table preview
```
