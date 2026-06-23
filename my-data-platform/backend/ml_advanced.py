from __future__ import annotations

import logging
from typing import Any

import polars as pl

logger = logging.getLogger("ml_advanced")


_nlp_classifier = None


def _get_zero_shot_classifier():
    global _nlp_classifier

    if _nlp_classifier is not None:
        return _nlp_classifier

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ImportError(
            "Transformers is not installed. Install it with `pip install transformers torch`."
        ) from exc

    _nlp_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    return _nlp_classifier


def run_nocode_clustering(dataframe: pl.DataFrame, num_clusters: int = 3) -> pl.DataFrame:
    if dataframe.is_empty():
        raise ValueError("Input data is empty")

    try:
        from pycaret.clustering import assign_model, create_model, setup as cluster_setup
    except ImportError as exc:
        raise ImportError("PyCaret is not installed. Install it with `pip install pycaret`.") from exc

    pandas_df = dataframe.to_pandas()
    cluster_setup(data=pandas_df, normalize=True, session_id=123, verbose=False, html=False)

    model = create_model("kmeans", num_clusters=num_clusters)
    clustered_df = assign_model(model)

    return pl.from_pandas(clustered_df)


def run_nocode_nlp(dataframe: pl.DataFrame, text_column: str, categories: list[str]) -> pl.DataFrame:
    if text_column not in dataframe.columns:
        raise ValueError(f"Text column '{text_column}' not found")
    if not categories:
        raise ValueError("At least one category is required")

    texts = dataframe.get_column(text_column).cast(pl.Utf8, strict=False).fill_null("").to_list()

    try:
        classifier = _get_zero_shot_classifier()
        predicted_labels: list[str] = []
        scores: list[float] = []

        for text in texts:
            normalized_text = (text or "").strip()
            if not normalized_text:
                predicted_labels.append("Unknown")
                scores.append(0.0)
                continue

            prediction: dict[str, Any] = classifier(normalized_text, candidate_labels=categories)
            labels = prediction.get("labels", [])
            label_scores = prediction.get("scores", [])

            if labels:
                predicted_labels.append(str(labels[0]))
                scores.append(float(label_scores[0]) if label_scores else 0.0)
            else:
                predicted_labels.append("Unknown")
                scores.append(0.0)

        return dataframe.with_columns(
            [
                pl.Series(name="AI_Text_Category", values=predicted_labels),
                pl.Series(name="AI_Text_Category_Confidence", values=scores),
            ]
        )
    except (ImportError, Exception) as exc:
        logger = logging.getLogger("ml_advanced")
        logger.warning(f"Transformers NLP unavailable, using keyword fallback: {exc}")
        keyword_map = {cat.lower(): cat for cat in categories}
        predicted_labels: list[str] = []
        scores: list[float] = []

        for text in texts:
            normalized_text = (text or "").lower()
            if not normalized_text:
                predicted_labels.append("Unknown")
                scores.append(0.0)
                continue
            matched = None
            for keyword, category in keyword_map.items():
                if keyword in normalized_text:
                    matched = category
                    break
            if matched:
                predicted_labels.append(matched)
                scores.append(0.7)
            else:
                predicted_labels.append(categories[0] if categories else "Unknown")
                scores.append(0.3)

        return dataframe.with_columns(
            [
                pl.Series(name="AI_Text_Category", values=predicted_labels),
                pl.Series(name="AI_Text_Category_Confidence", values=scores),
            ]
        )
