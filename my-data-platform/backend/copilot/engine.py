import os
import re
import math
import logging
from typing import Any, Dict, List, Tuple
import polars as pl
import numpy as np

logger = logging.getLogger(__name__)

class IntentEngine:
    """Parses user natural language queries to classify intent and extract target features."""

    @staticmethod
    def classify_intent(query: str) -> str:
        q = query.lower()
        if any(kw in q for kw in ["anomaly", "outlier", "weird", "unusual"]):
            return "ANOMALY"
        if any(kw in q for kw in ["model", "ml", "predict", "forecast", "regression", "classify"]):
            return "ML_RECOMMENDATION"
        if any(kw in q for kw in ["graph", "chart", "visualize", "heatmap", "plot", "pie"]):
            return "VISUAL"
        if any(kw in q for kw in ["clean", "remove", "impute", "fill", "drop", "null"]):
            return "CLEANING_RECOM"
        if any(kw in q for kw in ["top", "highest", "lowest", "compare", "growth", "vs", "versus"]):
            return "FACT_QUERY"
        return "CHAT"


class RuleEngine:
    """Validates requested columns and parameters against the active dataset schema."""

    @staticmethod
    def validate_action(df: pl.DataFrame, intent: str, query: str) -> Tuple[bool, str, List[str]]:
        cols = df.columns
        q = query.lower()
        extracted_cols = [c for c in cols if c.lower() in q]
        
        if intent == "FACT_QUERY" and not extracted_cols:
            # Try to guess numerical columns for facts
            num_cols = [c for c, dtype in zip(df.columns, df.dtypes) if dtype.is_numeric()]
            if num_cols:
                return True, "No specific column mentioned, using numeric defaults.", [num_cols[0]]
            return False, "Could not identify any numerical columns to query facts.", []

        return True, "Valid action rules passed.", extracted_cols


class AnalyticsEngine:
    """Runs high-performance mathematical and statistical queries directly on Polars dataframes."""

    @staticmethod
    def compute_facts(df: pl.DataFrame, intent: str, extracted_cols: List[str], query: str) -> Dict[str, Any]:
        facts = {}
        q = query.lower()

        if intent == "ANOMALY":
            # Scan numeric columns for outliers
            num_cols = [c for c, dtype in zip(df.columns, df.dtypes) if dtype.is_numeric()]
            outlier_counts = {}
            for c in num_cols[:3]: # Limit to top 3 columns
                valid = df[c].drop_nulls()
                if len(valid) > 0:
                    q1 = float(np.percentile(valid.to_numpy(), 25))
                    q3 = float(np.percentile(valid.to_numpy(), 75))
                    iqr = q3 - q1
                    cnt = int(np.sum((valid.to_numpy() < q1 - 1.5 * iqr) | (valid.to_numpy() > q3 + 1.5 * iqr)))
                    outlier_counts[c] = cnt
            facts["outlier_counts"] = outlier_counts
            facts["evidence"] = f"Scanned {len(num_cols)} numeric columns and identified outliers count: {outlier_counts}."

        elif intent == "FACT_QUERY":
            # Handle comparisons, top 10, or growth
            num_cols = [c for c, dtype in zip(df.columns, df.dtypes) if dtype.is_numeric()]
            cat_cols = [c for c in df.columns if c not in num_cols]

            if "top" in q or "highest" in q:
                target_cat = cat_cols[0] if cat_cols else None
                target_num = num_cols[0] if num_cols else None
                
                # Check if specific extracted columns are present
                for c in extracted_cols:
                    if c in num_cols:
                        target_num = c
                    elif c in cat_cols:
                        target_cat = c

                if target_cat and target_num:
                    agg = df.group_by(target_cat).agg(pl.col(target_num).sum().alias("total"))
                    sorted_agg = agg.sort("total", descending=True).head(5)
                    data_points = sorted_agg.collect() if isinstance(sorted_agg, pl.LazyFrame) else sorted_agg
                    facts["top_values"] = data_points.to_dicts()
                    facts["evidence"] = f"Calculated top 5 groupings of '{target_cat}' by sum of '{target_num}'."
            
            elif "vs" in q or "compare" in q:
                # Group-by category comparison
                target_cat = cat_cols[0] if cat_cols else None
                target_num = num_cols[0] if num_cols else None
                for c in extracted_cols:
                    if c in num_cols:
                        target_num = c
                    elif c in cat_cols:
                        target_cat = c
                if target_cat and target_num:
                    agg = df.group_by(target_cat).agg(pl.col(target_num).mean().alias("average"))
                    facts["comparison"] = agg.head(10).to_dicts()
                    facts["evidence"] = f"Compared averages of '{target_num}' grouped by category '{target_cat}'."

            else:
                facts["summary"] = {c: {"mean": float(df[c].mean() or 0.0)} for c in num_cols[:2]}
                facts["evidence"] = "Computed basic column means on available numeric metrics."

        elif intent == "CLEANING_RECOM":
            null_metrics = {c: int(df[c].null_count()) for c in df.columns}
            high_nulls = {c: cnt for c, cnt in null_metrics.items() if cnt / len(df) > 0.3}
            facts["high_null_columns"] = high_nulls
            facts["evidence"] = f"Identified {len(high_nulls)} columns containing more than 30% missing cells."

        else:
            facts["metrics"] = {"rows": len(df), "columns": len(df.columns)}
            facts["evidence"] = f"Dataset contains {len(df)} rows and {len(df.columns)} columns."

        return facts


class LLMAdapter:
    """Adapter class handling OpenAI API integrations or returning offline templates as fallback."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

    def generate_response(self, intent: str, query: str, facts: Dict[str, Any], columns: List[str]) -> str:
        # Prompt build
        prompt = (
            f"You are the Brain Copilot of DataSaaS Pro. Respond to user's question: '{query}'.\n"
            f"Intent: {intent}. Columns in dataset: {columns}.\n"
            f"Factual data from calculations: {facts}.\n"
            f"Generate a professional executive explanation under 150 words."
        )

        if not self.api_key:
            # Fallback offline template generation
            if intent == "ANOMALY":
                counts = facts.get("outlier_counts", {})
                col_list = ", ".join([f"'{k}' ({v} outliers)" for k, v in counts.items()])
                return f"Offline Engine: Found unusual values in columns: {col_list}. Recommend applying Winsorization cap or dropping outliers."
            elif intent == "ML_RECOMMENDATION":
                return "Offline Engine: Recommend training an XGBoostRegressor for numerical target estimation, or XGBoostClassifier for categorical classes."
            elif intent == "VISUAL":
                return "Offline Engine: Recommended charts include Heatmap (for correlation), Treemap (for categorical distribution), and Line chart (for numeric trends)."
            elif intent == "CLEANING_RECOM":
                nulls = facts.get("high_null_columns", {})
                if nulls:
                    return f"Offline Engine: Columns {list(nulls.keys())} have excessive missingness. Recommend dropping these fields or applying mean/median fill."
                return "Offline Engine: Dataset looks relatively clean. Recommend trimming spacing or lowercasing string dimensions."
            elif intent == "FACT_QUERY":
                if "top_values" in facts:
                    vals = facts["top_values"]
                    formatted = ", ".join([f"{list(v.values())[0]}: {list(v.values())[1]:.2f}" for v in vals[:3]])
                    return f"Offline Engine: Computed top categories. Highlights: {formatted}."
                return f"Offline Engine: Extracted statistics values. Calculated stats: {facts.get('summary', '')}."
            else:
                return f"Offline Engine: Hello! I am your AI Copilot. Ask me to find anomalies, suggest ML models, plot graphs, or clean columns."

        # Call OpenAI if available
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional Data Science Copilot. Speak in concise, CEO-level language."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content or "No response from AI adapter."
        except Exception as e:
            logger.warning(f"LLM API call failed: {e}. Falling back to templates.")
            return f"LLM Adapter error: {e}. Fallback: Calculated facts successfully: {facts}"


class ResponseGenerator:
    """Generates the final unified response object with story, confidence, evidence, and visual assets."""

    @staticmethod
    def build_copilot_response(query: str, df: pl.DataFrame) -> Dict[str, Any]:
        intent = IntentEngine.classify_intent(query)
        valid, msg, extracted = RuleEngine.validate_action(df, intent, query)
        
        if not valid:
            return {
                "content": f"Rule Violation: {msg}",
                "confidence": 0,
                "evidence": "Action rejected by Rule Engine validations.",
                "assets": None
            }

        facts = AnalyticsEngine.compute_facts(df, intent, extracted, query)
        
        # Call LLM or template adapter
        adapter = LLMAdapter()
        content = adapter.generate_response(intent, query, facts, df.columns)

        # Build dynamic UI assets (charts or tables)
        assets = None
        if intent == "FACT_QUERY" and "top_values" in facts:
            # Build bar chart asset meta
            assets = {
                "type": "bar",
                "label": f"Top Values",
                "data": facts["top_values"]
            }
        elif intent == "ANOMALY":
            # Build outlier statistics table asset meta
            assets = {
                "type": "table",
                "label": "Outliers Summary",
                "data": [{"column": k, "outliers_count": v} for k, v in facts.get("outlier_counts", {}).items()]
            }

        # Heuristic confidence calculation
        confidence = 95 if intent != "CHAT" else 80
        if not extracted and intent in ["ANOMALY", "FACT_QUERY"]:
            confidence = 65

        return {
            "content": content,
            "confidence": confidence,
            "evidence": facts.get("evidence", "Computed metrics on loaded dataset."),
            "assets": assets
        }
