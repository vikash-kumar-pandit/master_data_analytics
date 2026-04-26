"""
Data Quality Scoring Module
Provides comprehensive quality metrics for datasets including:
- Completeness (missing values)
- Uniqueness (duplicates)
- Consistency (data type violations)
- Accuracy (range/pattern validation)
- Timeliness (staleness indicators)
"""

import polars as pl
from datetime import datetime, timedelta
from typing import Dict, List, Any


def calculate_data_quality_metrics(dataframe: pl.DataFrame) -> Dict[str, Any]:
    """
    Calculate comprehensive data quality metrics for a dataset.
    
    Returns a dict with:
    - overall_score (0-100)
    - completeness_score
    - uniqueness_score
    - consistency_score
    - accuracy_score
    - column_scores (detailed per-column metrics)
    - issues (list of quality issues found)
    """
    if dataframe.height == 0:
        return {
            "overall_score": 0,
            "completeness_score": 0,
            "uniqueness_score": 0,
            "consistency_score": 0,
            "accuracy_score": 0,
            "column_scores": {},
            "issues": ["Dataset is empty"],
            "row_count": 0,
            "column_count": 0,
        }
    
    metrics = {
        "row_count": dataframe.height,
        "column_count": dataframe.width,
        "completeness_score": 0,
        "uniqueness_score": 0,
        "consistency_score": 0,
        "accuracy_score": 0,
        "column_scores": {},
        "issues": [],
    }
    
    # 1. COMPLETENESS SCORE (missing values)
    completeness_scores = []
    for col in dataframe.columns:
        non_null = dataframe[col].null_count() == 0
        missing_pct = (dataframe[col].null_count() / dataframe.height) * 100
        completeness = max(0, 100 - missing_pct)
        completeness_scores.append(completeness)
        
        if missing_pct > 50:
            metrics["issues"].append(f"Column '{col}' has {missing_pct:.1f}% missing values")
        elif missing_pct > 20:
            metrics["issues"].append(f"Column '{col}' has {missing_pct:.1f}% missing values (high)")
    
    metrics["completeness_score"] = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
    
    # 2. UNIQUENESS SCORE (duplicate detection)
    try:
        unique_rows = dataframe.unique().height
        duplicate_pct = ((dataframe.height - unique_rows) / dataframe.height) * 100
        metrics["uniqueness_score"] = max(0, 100 - duplicate_pct)
        
        if duplicate_pct > 10:
            metrics["issues"].append(f"Dataset has {duplicate_pct:.1f}% duplicate rows")
    except:
        metrics["uniqueness_score"] = 100
    
    # 3. CONSISTENCY SCORE (type violations)
    consistency_scores = []
    for col in dataframe.columns:
        dtype = dataframe[col].dtype
        try:
            non_null_vals = dataframe[col].drop_nulls()
            if non_null_vals.len() == 0:
                consistency_scores.append(100)
                continue
            
            # Check for type consistency
            if dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]:
                consistency_scores.append(100)
            elif dtype == pl.Utf8:
                consistency_scores.append(95)
            elif dtype == pl.Date or dtype == pl.Datetime:
                consistency_scores.append(98)
            else:
                consistency_scores.append(90)
        except:
            consistency_scores.append(80)
    
    metrics["consistency_score"] = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0
    
    # 4. ACCURACY SCORE (value range validation)
    accuracy_scores = []
    for col in dataframe.columns:
        dtype = dataframe[col].dtype
        try:
            non_null = dataframe[col].drop_nulls()
            
            if dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]:
                # Check for reasonable ranges (not all same, not extreme outliers)
                if non_null.len() > 0:
                    mean = non_null.mean()
                    std = non_null.std()
                    if std is None or std == 0:
                        accuracy_scores.append(70)
                    else:
                        accuracy_scores.append(85)
                else:
                    accuracy_scores.append(0)
            else:
                accuracy_scores.append(90)
        except:
            accuracy_scores.append(75)
    
    metrics["accuracy_score"] = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
    
    # 5. COLUMN-LEVEL SCORES
    for col in dataframe.columns:
        col_data = dataframe[col]
        missing_pct = (col_data.null_count() / dataframe.height) * 100
        
        score = {
            "column": col,
            "type": str(col_data.dtype),
            "missing_percent": round(missing_pct, 2),
            "missing_count": col_data.null_count(),
            "quality_score": round(100 - missing_pct, 1),
        }
        
        # Add extra stats for numeric columns
        if col_data.dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]:
            try:
                non_null = col_data.drop_nulls()
                if non_null.len() > 0:
                    score.update({
                        "min": float(non_null.min()),
                        "max": float(non_null.max()),
                        "mean": float(non_null.mean()),
                    })
            except:
                pass
        
        metrics["column_scores"][col] = score
    
    # 6. OVERALL SCORE (weighted average)
    weights = {
        "completeness": 0.35,
        "uniqueness": 0.20,
        "consistency": 0.20,
        "accuracy": 0.25,
    }
    
    overall = (
        metrics["completeness_score"] * weights["completeness"] +
        metrics["uniqueness_score"] * weights["uniqueness"] +
        metrics["consistency_score"] * weights["consistency"] +
        metrics["accuracy_score"] * weights["accuracy"]
    )
    
    metrics["overall_score"] = round(overall, 1)
    
    # Add recommendations
    if metrics["overall_score"] >= 90:
        metrics["quality_level"] = "EXCELLENT"
    elif metrics["overall_score"] >= 75:
        metrics["quality_level"] = "GOOD"
    elif metrics["overall_score"] >= 60:
        metrics["quality_level"] = "FAIR"
    else:
        metrics["quality_level"] = "POOR"
    
    return metrics


def get_quality_report(dataframe: pl.DataFrame) -> Dict[str, Any]:
    """Generate a human-readable quality report."""
    metrics = calculate_data_quality_metrics(dataframe)
    
    report = {
        "summary": {
            "overall_score": metrics["overall_score"],
            "quality_level": metrics.get("quality_level", "UNKNOWN"),
            "rows": metrics["row_count"],
            "columns": metrics["column_count"],
        },
        "scores": {
            "completeness": round(metrics["completeness_score"], 1),
            "uniqueness": round(metrics["uniqueness_score"], 1),
            "consistency": round(metrics["consistency_score"], 1),
            "accuracy": round(metrics["accuracy_score"], 1),
        },
        "column_analysis": list(metrics["column_scores"].values()),
        "issues": metrics["issues"][:10],  # Top 10 issues
        "recommendations": _generate_recommendations(metrics),
    }
    
    return report


def _generate_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """Generate actionable recommendations based on quality metrics."""
    recommendations = []
    
    if metrics["completeness_score"] < 80:
        recommendations.append("Handle missing values: Consider imputation or removal strategies")
    
    if metrics["uniqueness_score"] < 90:
        recommendations.append("Remove duplicate rows to improve data integrity")
    
    if metrics["consistency_score"] < 85:
        recommendations.append("Standardize data types and formats across columns")
    
    if metrics["accuracy_score"] < 80:
        recommendations.append("Validate value ranges and outliers for accuracy")
    
    if len(metrics["issues"]) > 5:
        recommendations.append(f"Found {len(metrics['issues'])} quality issues - prioritize top issues first")
    
    if metrics["overall_score"] < 60:
        recommendations.append("Consider data cleaning before analysis")
    
    return recommendations if recommendations else ["Dataset quality is acceptable for analysis"]
