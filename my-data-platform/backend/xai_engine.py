from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _is_classification_target(series: pd.Series) -> bool:
    if str(series.dtype) in {"object", "bool", "category"}:
        return True
    unique_count = series.nunique(dropna=True)
    return unique_count <= 20


def _build_pipeline(is_classification: bool):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    def make_pipeline(feature_frame: pd.DataFrame):
        numeric_columns = feature_frame.select_dtypes(include=["number", "bool"]).columns.tolist()
        categorical_columns = [column for column in feature_frame.columns if column not in numeric_columns]

        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
            ]
        )
        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, numeric_columns),
                ("cat", categorical_transformer, categorical_columns),
            ]
        )

        estimator = (
            RandomForestClassifier(n_estimators=200, random_state=123)
            if is_classification
            else RandomForestRegressor(n_estimators=200, random_state=123)
        )

        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])
        return pipeline

    return make_pipeline


def generate_shap_explanations(
    rows: list[dict],
    target_column: str,
    sample_index: int = 0,
    top_k: int = 12,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("No rows provided")

    dataframe = pd.DataFrame(rows)
    if target_column not in dataframe.columns:
        raise ValueError(f"Target column '{target_column}' not found")

    dataframe = dataframe.dropna(subset=[target_column])
    if dataframe.empty:
        raise ValueError("No valid target values after removing nulls")

    y = dataframe[target_column]
    x = dataframe.drop(columns=[target_column])

    if x.empty:
        raise ValueError("No feature columns available for explanation")

    is_classification = _is_classification_target(y)
    pipeline_factory = _build_pipeline(is_classification)
    pipeline = pipeline_factory(x)
    pipeline.fit(x, y)

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    transformed = preprocessor.transform(x)
    if hasattr(transformed, "toarray"):
        transformed_dense = transformed.toarray()
    else:
        transformed_dense = np.asarray(transformed)

    feature_names = preprocessor.get_feature_names_out().tolist()

    try:
        import shap
    except ImportError as exc:
        raise ImportError("SHAP is not installed. Install it with `pip install shap`." ) from exc

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(transformed_dense)

    if isinstance(shap_values, list):
        values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    else:
        values = shap_values

    mean_abs = np.abs(values).mean(axis=0)
    order = np.argsort(mean_abs)[::-1][:top_k]

    global_importance = [
        {
            "feature": feature_names[index],
            "importance": float(mean_abs[index]),
        }
        for index in order
    ]

    bounded_index = min(max(sample_index, 0), len(values) - 1)
    local_vector = values[bounded_index]
    local_order = np.argsort(np.abs(local_vector))[::-1][:top_k]
    local_explanation = [
        {
            "feature": feature_names[index],
            "shap_value": float(local_vector[index]),
        }
        for index in local_order
    ]

    return {
        "problem_type": "classification" if is_classification else "regression",
        "target_column": target_column,
        "global_importance": global_importance,
        "local_explanation": local_explanation,
        "sample_index": bounded_index,
        "total_rows_used": int(len(dataframe)),
    }
