# Release Notes — DataSaaS Pro v0.8.0 Stabilization

We are proud to release version **0.8.0 (Stabilization Release)** of DataSaaS Pro, representing a significant milestone in turning this AI Data Science platform into a production-grade enterprise product.

---

## 🌟 Major Highlights

1. **80%+ Test Coverage Gate**: Expanded backend test coverage from 42% to **80%** by writing complete testing suites covering formerly untested critical components.
2. **AI Analytics Copilot**: Centralized coordinator parsing natural language intents, computing direct facts on Polars, and formatting CEO-level explanations.
3. **AI Visualization Engine**: Automatic recommendation matcher categorizing 100+ chart types, rendering vector assets in-memory, and generating downloadable PowerPoint slide decks.

---

## 🚀 Deployment & Installation

### Prerequisite Dependencies
Ensure that the GTK3 runtime is installed on the host machine to support WeasyPrint PDF compilation:
* **Windows**: Install the GTK3-Runtime environment and add it to system environment variables.
* **Linux/Ubuntu**: `sudo apt-get install python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0`

### Setup Instructions
1. Install dependencies using uv:
   ```bash
   uv pip install -r requirements.txt
   ```
2. Initialize database migration:
   ```bash
   python -c "from database import init_db; init_db()"
   ```
3. Boot API servers:
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
