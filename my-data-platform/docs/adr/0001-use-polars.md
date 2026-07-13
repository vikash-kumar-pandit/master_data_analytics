# Architectural Decision Record 0001: Use Polars over Pandas

## Status
Approved

## Context
The platform requires a fast, low-memory data manipulation engine to process CSV, TSV, Parquet, and Excel files up to 1GB size inside constrained container environments (capped at 4GB RAM).

## Decision
We chose **Polars** as the primary data processing engine instead of standard Pandas.

## Rationale
1. **Performance**: Polars is written in Rust and utilizes parallel execution natively, performing up to 100x faster than Pandas on large aggregations.
2. **Lazy Evaluation**: The `LazyFrame` API compiles query graphs and optimizes filters before execution, reducing unnecessary RAM loading.
3. **Out-of-Core Processing**: Polars supports streaming queries (`collect(streaming=True)`), enabling datasets exceeding physical container memory constraints to be processed gracefully without OOM crashes.
4. **Data Type Strictness**: Polars enforces schema consistency, catching null and type mismatches early in the execution pipeline.

## Consequences
* All data preparation transformations, column splits, and profiling actions must leverage Polars APIs.
* PyCaret AutoML is bypassed in Python 3.12/Polars runtimes in favor of our custom scikit-learn training algorithms to maintain library compatibility.
