# Changelog — DataSaaS Pro

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-rc1] — 2026-07-13
### Added
* **Phase 12 — Version 1.0 Stabilization**:
  * Exhaustive backend test suite containing 157 passed unit/integration tests.
  * Added regression test suites for AutoML predictive training, scheduled exports, advanced data cleaner, and PDF/PPTX report generators.
  * Integration tests for all core main route endpoints.
  * Expanded backend coverage from 42% to 80% total test coverage.

## [0.8.0] — 2026-07-13
### Added
* **AI Visualization Intelligence Engine (Phase 12)**:
  * Automatic dataset scanning using Polars.
  * Autodetects category dimensions (Business, Statistical, ML, Correlation, Time Series).
  * Matplotlib Agg backend in-memory chart generation.
  * PowerPoint slide creator (`pptx`) inserting visualizations with AI Story commentaries.
  * ZIP packager for HTML dashboards and PNG/SVG assets.
* **AI Analytics Copilot (Phase 11)**:
  * Conversational intent parsing engine.
  * Rules validations before calculating metrics.
  * DB tables (`CopilotSession`, `CopilotMessage`, `CopilotMemory`) storing histories.
  * Sliding ChatGPT-style React panel UI.
* **Intelligent Data Preparation Studio (Phase 10)**:
  * Power Query transformations stack (imputers, Winzorization, regex).
  * Versions history database stack and Undo/Redo rollback operations.
* **Universal Data Profiling Engine (Phase 9)**:
  * High-performance statistical profiling (skewness, kurtosis, standard deviations).

### Changed
* Mounted profiling, preparation, copilot, and visualization routers into backend APIs.
* Added interactive UI layouts inside DashboardLayout sidebars.

---

## [0.5.0] — 2026-07-08
### Added
* Pipeline Node Engine tracking visual task components.
* AutoML XGBoost training models.
* PDF WeasyPrint stream exporter.
