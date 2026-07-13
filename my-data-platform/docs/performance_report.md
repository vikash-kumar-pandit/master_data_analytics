# Performance & Scalability Report — Data Preparation Studio

This document reviews how the **Data Preparation Studio** achieves O(1) memory scalability and handles datasets larger than RAM (e.g. 100M+ rows).

---

## 1. Out-of-Core Processing & Memory Footprint

Traditional preparation packages (like Pandas-based Wranglers) load entire CSV files into memory as dense matrices. If a dataset is 10 GB, Pandas requires up to 30 GB of RAM to perform operations like type-casting or string parsing, resulting in frequent Out-of-Memory (OOM) failures.

DataSaaS Pro circumvents this by utilizing **Polars out-of-core LazyFrames**:
* **Lazy Computation Graph**: When transformations are triggered (e.g., `lowercase()`, `standardization()`), Polars does not immediately load or process rows. Instead, it compiles an abstract syntax tree of expressions.
* **Streaming Engine (`sink_parquet()`)**: When saving, Polars streams data chunks sequentially through CPU cores, writing out-of-core directly to disk into the new Parquet version.
* **Peak Memory Constraint**: Memory consumption remains constant, bound by chunk size, rather than growing linearly with dataset size.

---

## 2. In-Memory Operations Optimization

For operations requiring full statistics computation (such as calculating `mean` for missing value imputation, or `quantile` for outlier capping):
* Polars scans and aggregates numerical values in parallel using SIMD instruction sets.
* Intermediate aggregates are extremely lightweight (e.g., single scalar values), which are then injected back into the lazy expression graph for the streaming write.

---

## 3. Storage Efficiency

While saving sequential versions might appear to consume significant storage:
* Intermediate versions are saved in **Parquet format** rather than raw CSV.
* Parquet uses columnar run-length encoding (RLE) and dictionary compression.
* File footprints on disk are typically **5x to 10x smaller** than the original CSVs, making version history extremely space-efficient.
