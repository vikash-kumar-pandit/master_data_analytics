# API Endpoint Reference — AI Visualization Engine

This document details the HTTP route specifications for the **AI Visualization Intelligence Engine**.

---

## 1. Recommendation Recommendations
* **Route**: `POST /api/visualization/recommend`
* **Form Parameters**:
  * `project_id` (string, required)
* **Response Model**:
  ```json
  [
    {
      "chart_type": "sales_trend",
      "category": "Time Series",
      "columns": ["sales", "date"],
      "rank": 3,
      "business_value": 5,
      "confidence": 97.0,
      "explanation": "Line plot displaying trends...",
      "story": "Observations follow a progressive trend...",
      "stats_interpretation": "Temporal trend line with average smoothing."
    }
  ]
  ```

---

## 2. Generate Single Chart
* **Route**: `POST /api/visualization/generate`
* **Form Parameters**:
  * `project_id` (string, required)
  * `chart_type` (string, required)
  * `columns_json` (string, JSON list, required)

---

## 3. Generate All Charts
* **Route**: `POST /api/visualization/generate-all`
* **Form Parameters**:
  * `project_id` (string, required)

---

## 4. Export Presentations & ZIPs
* **Route**: `GET /api/visualization/export`
* **Parameters**:
  * `project_id` (string, query, required)
  * `format` (string, options: `zip` or `pptx`, default: `zip`)
* **Response**: Binary stream payload (`application/x-zip-compressed` or `application/vnd.openxmlformats-officedocument.presentationml.presentation`).
