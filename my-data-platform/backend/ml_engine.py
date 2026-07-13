from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ml_engine")


def _try_pycaret(df_polars, target_column: str) -> dict[str, Any] | None:
    try:
        from pycaret.classification import compare_models, pull, setup
        df_pandas = df_polars.to_pandas()
        if target_column not in df_pandas.columns:
            raise ValueError(f"Target column '{target_column}' not found in dataset")
        setup(data=df_pandas, target=target_column, verbose=False, html=False, fold=5)
        best_model = compare_models(n_select=1)
        metrics_df = pull()
        if metrics_df is None or metrics_df.empty:
            return {
                "best_algorithm": str(best_model),
                "accuracy": None,
                "message": f"AutoML completed, selected {best_model}.",
                "metrics": [],
                "engine": "pycaret",
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
            "engine": "pycaret",
        }
    except Exception as exc:
        logger.warning("PyCaret AutoML failed: %s", exc)
        return None


def _try_sklearn_fallback(df_polars, target_column: str) -> dict[str, Any]:
    try:
        import numpy as np
        from sklearn.ensemble import (
            AdaBoostClassifier,
            GradientBoostingClassifier,
            RandomForestClassifier,
        )
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score, train_test_split
        from sklearn.preprocessing import OneHotEncoder
        from sklearn.impute import SimpleImputer
        from sklearn.compose import ColumnTransformer
        from sklearn.pipeline import Pipeline

        import polars as pl
        if target_column not in df_polars.columns:
            raise ValueError(f"Target column '{target_column}' not found")

        y_series = df_polars[target_column]
        x_df = df_polars.drop(target_column)

        # Vectorized identification of classification vs regression tasks natively in Polars
        n_unique_y = y_series.n_unique()
        y_dtype = y_series.dtype
        is_classification = n_unique_y <= 20 or not (y_dtype.is_numeric() or y_dtype.is_integer())

        # Vectorized split of numeric vs categorical features natively in Polars schema
        numeric_cols = [col for col, dtype in x_df.schema.items() if dtype.is_numeric() or dtype.is_integer() or dtype == pl.Boolean]
        categorical_cols = [col for col in x_df.columns if col not in numeric_cols]

        # Convert only at the end for scikit-learn ColumnTransformer indexing support
        df_pandas = df_polars.to_pandas()
        y = df_pandas[target_column]
        x = df_pandas.drop(columns=[target_column])

        numeric_pipeline = Pipeline([("imputer", SimpleImputer(strategy="median"))])
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])

        preprocessor = ColumnTransformer([
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ])

        candidates = []
        if is_classification:
            candidates = [
                ("RandomForest", RandomForestClassifier(n_estimators=100, random_state=42)),
                ("GradientBoosting", GradientBoostingClassifier(n_estimators=100, random_state=42)),
                ("AdaBoost", AdaBoostClassifier(n_estimators=100, random_state=42)),
                ("LogisticRegression", LogisticRegression(max_iter=500, random_state=42)),
            ]
        else:
            from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
            from sklearn.linear_model import Ridge
            candidates = [
                ("RandomForest", RandomForestRegressor(n_estimators=100, random_state=42)),
                ("GradientBoosting", GradientBoostingRegressor(n_estimators=100, random_state=42)),
                ("Ridge", Ridge(random_state=42)),
            ]

        best_name = candidates[0][0]
        best_score = -float("inf")
        best_pipeline = None

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y if is_classification else None)

        for name, estimator in candidates:
            pipeline = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
            try:
                pipeline.fit(x_train, y_train)
                cv_scores = cross_val_score(pipeline, x_train, y_train, cv=5, scoring="accuracy" if is_classification else "r2")
                mean_cv = float(np.mean(cv_scores))
                std_cv = float(np.std(cv_scores))
                score_for_selection = mean_cv - 0.5 * std_cv
                if score_for_selection > best_score:
                    best_score = score_for_selection
                    best_name = name
                    best_pipeline = pipeline
            except Exception as exc:
                logger.warning("Fallback model %s failed: %s", name, exc)
                continue

        if best_pipeline is None:
            raise RuntimeError("All fallback models failed")

        final_score = float(best_pipeline.score(x_test, y_test))
        metric_label = "accuracy" if is_classification else "r2"

        return {
            "best_algorithm": best_name,
            "accuracy": final_score if is_classification else None,
            "r2": final_score if not is_classification else None,
            "message": f"Selected {best_name} with {metric_label}={final_score:.4f} (CV mean={best_score:.4f}).",
            "metrics": [{"algorithm": best_name, metric_label: final_score, "cv_mean": best_score}],
            "engine": "sklearn_fallback",
            "problem_type": "classification" if is_classification else "regression",
        }
    except Exception as exc:
        logger.exception("Sklearn fallback AutoML failed: %s", exc)
        raise RuntimeError(f"Sklearn fallback failed: {exc}") from exc


def run_automl_stateless(df_polars, target_column: str) -> dict[str, Any]:
    result = _try_pycaret(df_polars, target_column)
    if result is not None:
        return result
    return _try_sklearn_fallback(df_polars, target_column)
