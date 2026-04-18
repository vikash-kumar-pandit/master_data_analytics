from __future__ import annotations

from typing import Any


def run_automl_stateless(df_polars, target_column: str) -> dict[str, Any]:
    try:
        from pycaret.classification import compare_models, pull, setup
    except ImportError as exc:
        raise ImportError(
            "PyCaret is not installed. Install it with `pip install pycaret` to enable AutoML."
        ) from exc

    df_pandas = df_polars.to_pandas()

    if target_column not in df_pandas.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset")

    setup(data=df_pandas, target=target_column, verbose=False, html=False)
    best_model = compare_models(n_select=1)
    metrics_df = pull()

    if metrics_df is None or metrics_df.empty:
        return {
            "best_algorithm": str(best_model),
            "accuracy": None,
            "message": f"AutoML completed, selected {best_model}.",
            "metrics": [],
        }

    best_algorithm = str(metrics_df.index[0])
    accuracy = None
    if "Accuracy" in metrics_df.columns:
        accuracy = float(metrics_df.iloc[0]["Accuracy"])

    return {
        "best_algorithm": best_algorithm,
        "accuracy": accuracy,
        "message": (
            f"Our AI selected {best_algorithm} with {accuracy * 100:.2f}% accuracy."
            if accuracy is not None
            else f"Our AI selected {best_algorithm}."
        ),
        "metrics": metrics_df.reset_index().to_dict(orient="records"),
    }
