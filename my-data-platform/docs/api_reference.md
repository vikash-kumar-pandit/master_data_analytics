# API Endpoint Reference — Data Preparation Studio

This document lists all FastAPI endpoints exposed by the **Intelligent Data Preparation Studio**.

---

## 1. Run Transformation Step
* **Route**: `POST /api/preparation/run`
* **Content-Type**: `multipart/form-data`
* **Request Fields**:
  * `project_id` (string, required): The ID of the active pipeline project.
  * `operation_type` (string, required): Name of transformation (e.g. `fill_mean`, `regex_replace`).
  * `parameters_json` (JSON string, required): Dict containing parameters (target columns, separators, etc.).
* **Response Model**:
  ```json
  {
    "success": true,
    "version_num": 3,
    "comparison": {
      "schema_before": {"val": "str"},
      "schema_after": {"val": "float64"},
      "rows_after": 1000,
      "columns_after": 1
    },
    "description": "Parsed string characters and currencies into raw decimal values for columns: val.",
    "preview_data": [{"val": 12.5}]
  }
  ```

---

## 2. Get Transformation History
* **Route**: `GET /api/preparation/history`
* **Parameters**:
  * `project_id` (string, query, required)
* **Response Model**:
  ```json
  {
    "current_pointer": 2,
    "max_pointer": 2,
    "steps": [
      {
        "step_num": 1,
        "operation_type": "raw_ingestion",
        "description": "Ingested original raw dataset.",
        "rows": 1000,
        "columns": 1,
        "version_num": 1
      }
    ]
  }
  ```

---

## 3. Undo Step
* **Route**: `POST /api/preparation/undo`
* **Content-Type**: `application/x-www-form-urlencoded`
* **Request Fields**:
  * `project_id` (string, required)

---

## 4. Redo Step
* **Route**: `POST /api/preparation/redo`
* **Content-Type**: `application/x-www-form-urlencoded`
* **Request Fields**:
  * `project_id` (string, required)

---

## 5. Rollback Version
* **Route**: `POST /api/preparation/rollback/{version}`
* **Content-Type**: `application/x-www-form-urlencoded`
* **Request Fields**:
  * `project_id` (string, required)
  * `version` (integer, required)

---

## 6. Stream Export File
* **Route**: `GET /api/preparation/export`
* **Parameters**:
  * `project_id` (string, query, required)
  * `format` (string, query, default="csv"): Format selection (`csv`, `parquet`, `json`, `sql`).
