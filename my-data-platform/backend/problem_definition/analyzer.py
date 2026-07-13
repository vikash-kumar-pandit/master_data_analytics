import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class ProblemAnalyzer:
    """Analyzes dataset metadata and generates task recommendations and an AI Execution Plan."""

    def __init__(self, metadata: Dict[str, Any]):
        self.metadata = metadata
        self.columns = metadata.get("columns", [])
        self.col_types = metadata.get("column_types", {})
        self.missing_pct = metadata.get("missing_percentages", {})
        self.pk_candidates = metadata.get("primary_key_candidates", [])

    def detect_identifier_columns(self) -> List[str]:
        """Auto-detects columns that likely serve as unique identifiers."""
        identifiers = []
        id_keywords = ["id", "key", "uuid", "pk", "code", "index", "row"]
        
        for col in self.columns:
            col_lower = col.lower()
            # If name matches keywords or is detected in PK candidates
            if col in self.pk_candidates or any(kw in col_lower for kw in id_keywords):
                identifiers.append(col)
        return identifiers

    def detect_date_columns(self) -> List[str]:
        """Auto-detects columns representing date or time."""
        dates = []
        # Explicit datetime types
        dates.extend(self.col_types.get("datetime", []))
        
        # Name-based checks
        date_keywords = ["date", "time", "timestamp", "year", "month", "day", "created", "updated", "period"]
        for col in self.columns:
            if col not in dates:
                col_lower = col.lower()
                if any(kw in col_lower for kw in date_keywords):
                    dates.append(col)
        return dates

    def detect_possible_targets(self) -> List[str]:
        """Auto-detects potential prediction target columns based on cardinality and types."""
        targets = []
        identifiers = self.detect_identifier_columns()
        dates = self.detect_date_columns()
        
        for col in self.columns:
            # Exclude IDs and dates
            if col in identifiers or col in dates:
                continue
                
            # If missing percentage is low (can't predict if target is mostly nulls)
            missing = self.missing_pct.get(col, 0)
            if missing > 50:
                continue
                
            targets.append(col)
        return targets

    def generate_execution_plan(self) -> Dict[str, Any]:
        """Generates a complete recommended AI execution plan based on metadata."""
        identifiers = self.detect_identifier_columns()
        dates = self.detect_date_columns()
        possible_targets = self.detect_possible_targets()
        
        # Categorize tasks
        recommended_tasks = []
        if dates:
            recommended_tasks.append("Forecasting / Time-Series Analysis")
        if len(self.col_types.get("numerical", [])) >= 2:
            recommended_tasks.append("Regression / Numerical Modeling")
            recommended_tasks.append("Segmentation / Clustering")
        if len(self.col_types.get("categorical", [])) >= 1 or len(self.col_types.get("numerical", [])) >= 1:
            recommended_tasks.append("Classification / Binary & Multi-class")
            
        # Target recommendations
        primary_target = possible_targets[0] if possible_targets else None
        
        # Determine modeling tasks and models
        recommended_models = []
        is_classification = False
        
        if primary_target:
            if primary_target in self.col_types.get("numerical", []):
                recommended_models = ["RandomForestRegressor", "XGBoostRegressor", "LightGBMRegressor"]
            else:
                recommended_models = ["RandomForestClassifier", "XGBoostClassifier", "LogisticRegression"]
                is_classification = True

        # Recommendations for cleaning
        cleaning_steps = []
        for col, pct in self.missing_pct.items():
            if pct > 0:
                if pct > 50:
                    cleaning_steps.append(f"Drop column '{col}' due to high missing rate ({pct:.1f}%)")
                else:
                    strategy = "median imputation" if col in self.col_types.get("numerical", []) else "mode imputation"
                    cleaning_steps.append(f"Impute missing values in '{col}' using {strategy}")
                    
        # Feature engineering recommendations
        feature_recommendations = []
        if dates:
            for date_col in dates:
                feature_recommendations.append(f"Extract datetime features (hour, day_of_week, month, year) from '{date_col}'")
        for num_col in self.col_types.get("numerical", [])[:3]:
            for cat_col in self.col_types.get("categorical", [])[:2]:
                feature_recommendations.append(f"Create group aggregation (mean/std of '{num_col}' grouped by '{cat_col}')")

        # Visualization recommendations
        recommended_charts = []
        for num_col in self.col_types.get("numerical", [])[:2]:
            recommended_charts.append({
                "type": "Histogram / Distribution Plot",
                "column": num_col,
                "reason": f"To visualize distribution, skewness, and spread of numerical variable '{num_col}'"
            })
            if primary_target and num_col != primary_target:
                recommended_charts.append({
                    "type": "Scatter Plot",
                    "x": num_col,
                    "y": primary_target,
                    "reason": f"To understand dependency between '{num_col}' and target '{primary_target}'"
                })
        for cat_col in self.col_types.get("categorical", [])[:2]:
            recommended_charts.append({
                "type": "Bar / Frequency Chart",
                "column": cat_col,
                "reason": f"To evaluate counts and proportions of categories in '{cat_col}'"
            })

        return {
            "possible_targets": possible_targets,
            "possible_date_columns": dates,
            "possible_identifier_columns": identifiers,
            "primary_target_recommendation": primary_target,
            "is_classification_task": is_classification,
            "recommended_tasks": recommended_tasks,
            "recommended_models": recommended_models,
            "recommended_cleaning_steps": cleaning_steps,
            "recommended_features": feature_recommendations,
            "recommended_charts": recommended_charts,
            "ai_execution_plan": {
                "step_1_ingestion": "Check dataset integrity, delimiters, and verify schema mapping.",
                "step_2_cleansing": f"Apply auto-cleaning: {', '.join(cleaning_steps[:2]) if cleaning_steps else 'No null values detected'}.",
                "step_3_profiling": "Perform distribution analysis, missing counts correlation, and multi-collinearity checks.",
                "step_4_modeling": f"Build prediction model targeting '{primary_target}' using {', '.join(recommended_models[:2]) if recommended_models else 'clustering models'}."
            }
        }
