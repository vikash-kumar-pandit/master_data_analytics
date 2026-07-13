# API Endpoint Reference — AI Analytics Copilot

This document outlines the API contracts for the **AI Analytics Copilot**.

---

## 1. Post Chat Message
* **Route**: `POST /api/copilot/chat`
* **Content-Type**: `multipart/form-data`
* **Request Fields**:
  * `project_id` (string, required)
  * `message` (string, required)
  * `session_id` (string, optional)
* **Response Model**:
  ```json
  {
    "session_id": "session-uuid",
    "title": "Discussion Title",
    "messages": [
      {
        "role": "user",
        "content": "Find outlier anomalies"
      },
      {
        "role": "assistant",
        "content": "Offline Engine: Found unusual values in columns: 'val' (2 outliers).",
        "assets": {
          "type": "table",
          "label": "Outliers Summary",
          "data": [{"column": "val", "outliers_count": 2}]
        }
      }
    ],
    "confidence": 95,
    "evidence": "Scanned numeric columns and identified outliers: {'val': 2}."
  }
  ```

---

## 2. Get AI Execution Plan
* **Route**: `GET /api/copilot/plan`
* **Parameters**:
  * `project_id` (string, query, required)
* **Response Model**:
  ```json
  {
    "project_id": "proj-uuid",
    "domain": "Retail & E-commerce",
    "health": "95%",
    "rows": 9994,
    "columns": 21,
    "recommended_goal": "Sales Forecasting",
    "confidence": "94%",
    "recommended_pipeline": [
      "✓ Data Ingestion Inplace",
      "✓ Universal Profiling Run",
      "✓ Intelligent Cleaning Cap",
      "✓ Auto Feature Engineering"
    ],
    "estimated_time": "1 min 42 sec",
    "expected_accuracy": "90–95%"
  }
  ```

---

## 3. Create Session
* **Route**: `POST /api/copilot/sessions/create`
* **Request Fields**:
  * `project_id` (string, form)
  * `title` (string, form)

---

## 4. Get Sessions List
* **Route**: `GET /api/copilot/sessions`
* **Parameters**:
  * `project_id` (string, query)
