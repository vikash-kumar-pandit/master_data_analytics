from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import polars as pl
import logging
from hypothesis_tester import run_automated_ab_test

logger = logging.getLogger("analytics_engine")

QUESTION_INTENT_KEYWORDS = {
    "predictive": ["predict", "forecast", "future", "next", "will happen", "hoga", "hogi", "when", "kab"],
    "compare": ["compare", "before", "after", "difference", "change", "vs", "versus", "pahle", "ab"],
    "diagnostic": ["why", "kyo", "kyon", "reason", "cause", "drop", "fall", "decrease", "down"],
    "prescriptive": ["what should", "suggest", "recommend", "action", "kaise", "kya kare", "do next"],
}

METRIC_KEYWORDS = {
    "profit": ["profit", "net profit", "margin", "gross profit"],
    "revenue": ["revenue", "sales", "turnover", "income"],
    "customer": ["customer", "customers", "buyer", "buyers", "users", "user"],
    "spend": ["spend", "ad spend", "marketing", "cost", "cpc", "cpm", "budget"],
    "returns": ["return", "returns", "refund", "refunds"],
    "conversion": ["conversion", "conversions", "click", "clicks", "ctr", "engagement"],
}

DATE_KEYWORDS = ["date", "time", "day", "month", "week", "timestamp"]
CATEGORY_KEYWORDS = ["category", "channel", "platform", "company", "brand", "region", "country", "segment", "product"]


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _to_dataframe(rows: list[dict[str, Any]] | None) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    return pl.from_dicts(rows)


def _validate_rows_input(rows: Any, label: str = "rows") -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise TypeError(f"{label} must be a list of dictionaries")
    if any(not isinstance(row, dict) for row in rows):
        raise TypeError(f"{label} must contain dictionaries only")
    return rows


def _find_columns(columns: list[str], keywords: list[str]) -> list[str]:
    matches: list[str] = []
    lowered = {column: column.lower() for column in columns}
    for column, lower_name in lowered.items():
        if any(keyword in lower_name for keyword in keywords):
            matches.append(column)
    return matches


def _likely_date_column(columns: list[str]) -> str | None:
    matches = _find_columns(columns, DATE_KEYWORDS)
    return matches[0] if matches else None


def _likely_category_column(columns: list[str]) -> str | None:
    matches = _find_columns(columns, CATEGORY_KEYWORDS)
    return matches[0] if matches else None


def _detect_intent(question: str, previous_rows: list[dict[str, Any]] | None = None) -> str:
    text = _lower(question)
    if previous_rows:
        return "compare"
    for intent, keywords in QUESTION_INTENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return intent
    return "descriptive"


def _numeric_columns(dataframe: pl.DataFrame) -> list[str]:
    numeric_dtypes = {pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64}
    return [name for name, dtype in zip(dataframe.columns, dataframe.dtypes) if dtype in numeric_dtypes]


def _cast_numeric(dataframe: pl.DataFrame, column_name: str) -> pl.Series:
    return dataframe.select(pl.col(column_name).cast(pl.Float64, strict=False).fill_null(0.0)).to_series()


def _best_metric_column(dataframe: pl.DataFrame, question: str) -> str | None:
    columns = dataframe.columns
    if not columns:
        return None

    text = _lower(question)
    metric_aliases = {
        "profit": ["profit", "margin"],
        "revenue": ["revenue", "sales", "turnover", "income"],
        "customer": ["customer", "users", "buyer"],
        "spend": ["spend", "cost", "budget", "ad spend", "cpc", "cpm"],
        "returns": ["return", "refund"],
    }

    for _, aliases in metric_aliases.items():
        for alias in aliases:
            if alias in text:
                matches = _find_columns(columns, [alias])
                if matches:
                    return matches[0]

    numeric = _numeric_columns(dataframe)
    date_like = set(_find_columns(columns, DATE_KEYWORDS))
    for column_name in numeric:
        if column_name not in date_like:
            return column_name
    if numeric:
        return numeric[0]
    return None


def _summary_stats(dataframe: pl.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    for column_name in columns[:8]:
        try:
            series = _cast_numeric(dataframe, column_name)
        except Exception:
            continue
        if series.len() == 0:
            continue
        stats.append(
            {
                "column": column_name,
                "sum": float(series.sum()),
                "mean": float(series.mean() or 0),
                "min": float(series.min() or 0),
                "max": float(series.max() or 0),
            }
        )
    return stats


def _parse_date_flexible(value: Any) -> datetime | None:
    """Try to parse a date/time value from many common string formats."""
    if value is None:
        return None
    s = str(value).strip()
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y",
        "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _compute_trend_points(
    dataframe: pl.DataFrame,
    metric_column: str,
    date_column: str | None = None,
) -> list[dict[str, Any]]:
    """Return normalized [{date_label, value}] list sorted by date."""
    if metric_column not in dataframe.columns:
        return []

    has_date = date_column and date_column in dataframe.columns and date_column != metric_column

    if has_date:
        working = dataframe.select([
            pl.col(metric_column).cast(pl.Float64, strict=False).fill_null(0.0).alias(metric_column),
            pl.col(date_column).cast(pl.Utf8).alias(date_column),
        ])
        aggregated = (
            working.group_by(date_column)
            .agg(pl.col(metric_column).sum().alias("value"))
            .rename({date_column: "date_label"})
        )
        # Try to sort by parsed date, fall back to string sort
        rows_list = aggregated.to_dicts()
        def _sort_key(r: dict) -> Any:
            parsed = _parse_date_flexible(r["date_label"])
            return parsed if parsed is not None else r["date_label"]
        rows_list.sort(key=_sort_key)
        return rows_list

    # No date column — use row index as x-axis
    indexed = (
        dataframe
        .select(pl.col(metric_column).cast(pl.Float64, strict=False).fill_null(0.0).alias("value"))
        .with_row_index("date_label")
    )
    return indexed.to_dicts()


def _moving_average(values: list[float], window: int = 3) -> list[float]:
    """Simple centered moving average for smoothing."""
    result = []
    n = len(values)
    for i in range(n):
        lo = max(0, i - window // 2)
        hi = min(n, i + window // 2 + 1)
        result.append(float(np.mean(values[lo:hi])))
    return result


def _forecast_from_points(
    points: list[dict[str, Any]],
    horizon: int = 7,
    metric_column: str | None = None,
) -> dict[str, Any]:
    """Linear regression forecast from normalized [{date_label, value}] points.

    Returns a dict with 'forecast', 'slope', 'r_squared', 'mae', 'trend_direction',
    'growth_pct', 'smoothed_history' — everything the frontend needs.
    """
    if not points:
        return {"forecast": [], "error": "No data points available"}

    # Extract (label, value) from normalized structure
    numeric_points: list[float] = []
    labels: list[Any] = []
    for i, pt in enumerate(points):
        val = pt.get("value")
        lbl = pt.get("date_label", i)
        try:
            numeric_points.append(float(val))
            labels.append(lbl)
        except (TypeError, ValueError):
            continue

    if len(numeric_points) < 2:
        return {"forecast": [], "error": "Need at least 2 data points to forecast"}

    n = len(numeric_points)
    x = np.arange(n, dtype=float)
    y = np.asarray(numeric_points, dtype=float)

    # Linear regression (OLS)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred_history = slope * x + intercept

    # R-squared
    ss_res = float(np.sum((y - y_pred_history) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0.0

    # MAE on history
    mae = round(float(np.mean(np.abs(y - y_pred_history))), 4)

    # Smoothed history (3-period MA)
    smoothed = _moving_average(numeric_points, window=min(3, n))

    # Growth stats
    first_val = float(y[0]) if y[0] != 0 else 1.0
    last_val = float(y[-1])
    growth_pct = round(((last_val - first_val) / abs(first_val)) * 100, 2)
    trend_direction = "upward" if slope > 0.01 else ("downward" if slope < -0.01 else "stable")

    # Build future labels
    last_label = labels[-1] if labels else n - 1
    last_date = _parse_date_flexible(last_label)

    forecast_pts: list[dict[str, Any]] = []
    for offset in range(1, horizon + 1):
        pred_x = n - 1 + offset
        pred_val = float(max(0.0, slope * pred_x + intercept))
        if last_date is not None:
            lbl = (last_date + timedelta(days=offset)).date().isoformat()
        else:
            lbl = f"t+{offset}"
        forecast_pts.append({"point": lbl, "value": round(pred_val, 4)})

    return {
        "forecast": forecast_pts,
        "slope": round(float(slope), 6),
        "intercept": round(float(intercept), 4),
        "r_squared": r_squared,
        "mae": mae,
        "n_points": n,
        "growth_pct": growth_pct,
        "trend_direction": trend_direction,
        "smoothed_history": [round(v, 4) for v in smoothed],
    }


def _build_recommendations(intent: str, question: str, relevant_stats: list[dict[str, Any]], comparison: dict[str, Any] | None = None) -> list[str]:
    question_text = _lower(question)
    recommendations: list[str] = []

    if comparison:
        if comparison.get("row_delta", 0) < 0:
            recommendations.append("Investigate upstream data loss or filtering changes that reduced row count.")
        if comparison.get("null_delta", 0) > 0:
            recommendations.append("Re-check data entry and validation rules because null values increased.")
        if comparison.get("numeric_delta_summary"):
            top_line = comparison["numeric_delta_summary"][0]
            recommendations.append(f"Review the largest metric change in {top_line['column']} before scaling any action.")

    if "profit" in question_text:
        recommendations.append("Check whether revenue dropped, costs increased, or returns rose in the same period.")
    if "customer" in question_text:
        recommendations.append("Compare acquisition channels, repeat customers, and churn-linked segments.")
    if "sales" in question_text or "revenue" in question_text:
        recommendations.append("Break performance down by channel and category to isolate the main driver.")
    if "forecast" in question_text or intent == "predictive":
        recommendations.append("Use the forecast as a planning signal and validate it against seasonality and campaign calendars.")
    if "weather" in question_text:
        recommendations.append("For weather-style forecasts, use date series data with a time column and enough historical points.")

    if not recommendations:
        recommendations.append("Review the top metrics and compare them against the previous period before acting.")

    if relevant_stats:
        recommendations.append(f"Focus first on {relevant_stats[0]['column']} because it is the strongest available metric in the dataset.")

    return recommendations[:5]


def analyze_question(
    *,
    question: str,
    rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]] | None = None,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = _validate_rows_input(rows)
    if previous_rows is not None:
        previous_rows = _validate_rows_input(previous_rows, label="previous_rows")

    dataframe = _to_dataframe(rows)
    previous_dataframe = _to_dataframe(previous_rows)

    if dataframe.is_empty():
        return {
            "intent": "descriptive",
            "question": question,
            "answer": "No data available. Upload a dataset first.",
            "report_title": "Question Analysis Report",
            "report_sections": [
                {"heading": "Question", "rows": [{"label": "User Question", "value": question}]},
            ],
            "recommendations": ["Upload data before asking a question."],
            "chart_data": [],
        }

    intent = _detect_intent(question, previous_rows=previous_rows)
    columns = dataframe.columns
    numeric_columns = _numeric_columns(dataframe)
    date_column = _likely_date_column(columns)
    category_column = _likely_category_column(columns)
    metric_column = _best_metric_column(dataframe, question)
    relevant_stats = _summary_stats(dataframe, numeric_columns)

    comparison: dict[str, Any] | None = None
    forecast: list[dict[str, Any]] = []
    trend_points: list[dict[str, Any]] = []
    top_breakdown: list[dict[str, Any]] = []

    if metric_column:
        trend_points = _compute_trend_points(dataframe, metric_column, date_column=date_column)
        if intent == "predictive":
            forecast_result = _forecast_from_points(trend_points, horizon=7, metric_column=metric_column)
            forecast = forecast_result.get("forecast", [])

    if category_column and metric_column and category_column in columns and metric_column in columns:
        try:
            grouped = (
                dataframe.with_columns(pl.col(metric_column).cast(pl.Float64, strict=False).fill_null(0.0).alias(metric_column))
                .group_by(category_column)
                .agg(pl.col(metric_column).sum().alias("value"))
                .sort("value", descending=True)
                .head(5)
            )
            top_breakdown = grouped.to_dicts()
        except Exception:
            top_breakdown = []

    if previous_dataframe.is_empty() is False:
        before_cols = set(previous_dataframe.columns)
        after_cols = set(columns)
        before_numeric = set(_numeric_columns(previous_dataframe))
        after_numeric = set(numeric_columns)
        numeric_union = sorted(before_numeric.intersection(after_numeric))

        numeric_delta_summary: list[dict[str, Any]] = []
        for column_name in numeric_union[:8]:
            try:
                before_sum = float(_cast_numeric(previous_dataframe, column_name).sum())
                after_sum = float(_cast_numeric(dataframe, column_name).sum())
            except Exception:
                continue
            numeric_delta_summary.append(
                {
                    "column": column_name,
                    "before": before_sum,
                    "after": after_sum,
                    "delta": after_sum - before_sum,
                    "pct_change": round(((after_sum - before_sum) / before_sum) * 100, 2) if before_sum else None,
                }
            )

        null_delta = int(dataframe.null_count().sum_horizontal()[0] if dataframe.columns else 0) - int(previous_dataframe.null_count().sum_horizontal()[0] if previous_dataframe.columns else 0)

        comparison = {
            "row_delta": dataframe.height - previous_dataframe.height,
            "column_delta": dataframe.width - previous_dataframe.width,
            "added_columns": sorted(after_cols - before_cols),
            "removed_columns": sorted(before_cols - after_cols),
            "null_delta": null_delta,
            "numeric_delta_summary": numeric_delta_summary,
        }

    question_lower = _lower(question)
    answer_lines: list[str] = []

    if comparison:
        answer_lines.append(
            f"Compared with the previous version, rows changed by {comparison['row_delta']} and columns changed by {comparison['column_delta']}."
        )

    if metric_column:
        metric_series = _cast_numeric(dataframe, metric_column)
        latest_value = float(metric_series.tail(1).item()) if metric_series.len() else 0.0
        total_value = float(metric_series.sum())
        mean_value = float(metric_series.mean() or 0)
        answer_lines.append(
            f"The main metric I found is '{metric_column}' with total {total_value:.2f}, average {mean_value:.2f}, and latest value {latest_value:.2f}."
        )

        if metric_column.lower() in question_lower or any(token in question_lower for token in ["profit", "sales", "revenue", "customer", "spend", "return"]):
            if trend_points:
                first_value = float(trend_points[0].get(metric_column, 0) or 0)
                last_value = float(trend_points[-1].get(metric_column, 0) or 0)
                delta = last_value - first_value
                pct_change = round((delta / first_value) * 100, 2) if first_value else None
                if pct_change is not None:
                    answer_lines.append(
                        f"The metric moved from {first_value:.2f} to {last_value:.2f} across the available timeline, a change of {pct_change:.2f}%."
                    )
                else:
                    answer_lines.append(f"The metric moved from {first_value:.2f} to {last_value:.2f} across the available timeline.")

    if "why" in question_lower or "kyo" in question_lower or "reason" in question_lower:
        if any(keyword in question_lower for keyword in ["profit", "margin"]):
            answer_lines.append("Likely drivers are revenue movement, spending changes, and return or cost pressure.")
        elif any(keyword in question_lower for keyword in ["customer", "users"]):
            answer_lines.append("Likely drivers are acquisition decline, retention loss, or a channel-specific drop.")
        else:
            answer_lines.append("The likely cause is visible in the strongest metric trend and category breakdown below.")

    if intent == "predictive":
        if forecast:
            projected_end = forecast[-1]["value"]
            answer_lines.append(f"Based on the current trend, the next periods are projected to move toward {projected_end:.2f}.")
        else:
            answer_lines.append("A forecast was requested, but the dataset does not have enough time-series structure yet.")

    if not answer_lines:
        answer_lines.append(
            f"This dataset has {dataframe.height} rows, {dataframe.width} columns, and {len(numeric_columns)} numeric fields available for analysis."
        )

    if top_breakdown:
        best_segment = top_breakdown[0]
        answer_lines.append(
            f"The strongest segment is {best_segment.get(category_column)} with a combined {metric_column} of {float(best_segment.get('value') or 0):.2f}."
        )

    recommendations = _build_recommendations(intent, question, relevant_stats, comparison=comparison)

    report_sections: list[dict[str, Any]] = [
        {
            "heading": "Question Summary",
            "rows": [
                {"label": "Question", "value": question},
                {"label": "Intent", "value": intent},
                {"label": "Rows", "value": dataframe.height},
                {"label": "Columns", "value": dataframe.width},
            ],
        },
        {
            "heading": "Key Metrics",
            "rows": [
                {"label": item["column"], "value": f"sum={item['sum']:.2f}, mean={item['mean']:.2f}"}
                for item in relevant_stats[:6]
            ],
        },
    ]

    if comparison:
        report_sections.append(
            {
                "heading": "Version Comparison",
                "rows": [
                    {"label": "Row Delta", "value": comparison["row_delta"]},
                    {"label": "Column Delta", "value": comparison["column_delta"]},
                    {"label": "Null Delta", "value": comparison["null_delta"]},
                    {"label": "Added Columns", "value": ", ".join(comparison["added_columns"]) or "None"},
                    {"label": "Removed Columns", "value": ", ".join(comparison["removed_columns"]) or "None"},
                ] + [
                    {"label": item["column"], "value": f"{item['before']:.2f} -> {item['after']:.2f} ({item['delta']:+.2f})"}
                    for item in comparison["numeric_delta_summary"][:5]
                ],
            }
        )

    if forecast:
        report_sections.append(
            {
                "heading": "Forecast",
                "rows": [{"label": item["point"], "value": f"{item['value']:.2f}"} for item in forecast[:7]],
            }
        )

    if top_breakdown and category_column and metric_column:
        report_sections.append(
            {
                "heading": f"Top {category_column} Segments",
                "rows": [
                    {"label": str(item.get(category_column)), "value": f"{float(item.get('value') or 0):.2f}"}
                    for item in top_breakdown
                ],
            }
        )
        
        # Run Automated Hypothesis Testing
        try:
            ab_result = run_automated_ab_test(dataframe, metric_column, category_column)
            if ab_result and ab_result.get("status") == "success":
                report_sections.append({
                    "heading": "Automated Hypothesis Test (A/B Test)",
                    "rows": [
                        {"label": "Metric Tested", "value": ab_result["metric"]},
                        {"label": f"Group A ({ab_result['group_a']['name']}) Average", "value": f"{ab_result['group_a']['average']:.2f} (n={ab_result['group_a']['sample_size']})"},
                        {"label": f"Group B ({ab_result['group_b']['name']}) Average", "value": f"{ab_result['group_b']['average']:.2f} (n={ab_result['group_b']['sample_size']})"},
                        {"label": "P-Value", "value": f"{ab_result['p_value']:.4f}"},
                        {"label": "Statistically Significant", "value": "Yes" if ab_result["is_statistically_significant"] else "No"},
                        {"label": "AI Scientist Insight", "value": ab_result["business_insight"]}
                    ]
                })
                # Add to answer_lines if it's statistically significant or comparative
                answer_lines.append(ab_result["business_insight"])
        except Exception as ab_exc:
            logger.warning(f"Failed to append hypothesis test to report: {ab_exc}")

    report_sections.append(
        {
            "heading": "Recommendations",
            "rows": [{"label": f"Action {index + 1}", "value": recommendation} for index, recommendation in enumerate(recommendations)],
        }
    )

    return {
        "intent": intent,
        "question": question,
        "answer": " ".join(answer_lines),
        "report_title": "Question Analysis Report",
        "report_subtitle": f"Generated from {dataframe.height} rows and {dataframe.width} columns",
        "report_sections": report_sections,
        "recommendations": recommendations,
        "chart_data": trend_points,
        "forecast": forecast,
        "comparison": comparison,
        "metrics": relevant_stats,
        "top_breakdown": top_breakdown,
    }


def forecast_metric(
    *,
    rows: list[dict[str, Any]],
    metric_column: str | None = None,
    date_column: str | None = None,
    horizon: int = 7,
) -> dict[str, Any]:
    rows = _validate_rows_input(rows)
    dataframe = _to_dataframe(rows)
    if dataframe.is_empty():
        return {
            "answer": "No data available for forecasting.",
            "forecast": [],
            "chart_data": [],
            "report_sections": [],
        }

    if not metric_column:
        metric_column = _best_metric_column(dataframe, "forecast")

    if not metric_column:
        raise ValueError("A numeric metric column is required for forecasting")

    if not date_column:
        date_column = _likely_date_column(dataframe.columns)

    chart_data = _compute_trend_points(dataframe, metric_column, date_column=date_column)
    forecast_result = _forecast_from_points(chart_data, horizon=max(1, min(horizon, 30)), metric_column=metric_column)

    forecast_pts = forecast_result.get("forecast", [])
    r_squared = forecast_result.get("r_squared", 0)
    mae = forecast_result.get("mae", 0)
    slope = forecast_result.get("slope", 0)
    growth_pct = forecast_result.get("growth_pct", 0)
    trend_direction = forecast_result.get("trend_direction", "stable")
    smoothed_history = forecast_result.get("smoothed_history", [])
    n_points = forecast_result.get("n_points", 0)
    forecast_error = forecast_result.get("error")

    if forecast_error:
        answer = f"Forecast could not be generated: {forecast_error}"
    elif forecast_pts:
        end_val = forecast_pts[-1]["value"]
        answer = (
            f"Based on {n_points} historical data points for '{metric_column}', the trend is {trend_direction} "
            f"(slope: {slope:+.4f}, R²: {r_squared:.3f}). "
            f"The model projects the metric will reach approximately {end_val:.2f} "
            f"after {len(forecast_pts)} periods. Historical growth: {growth_pct:+.1f}%."
        )
    else:
        answer = f"A forecast could not be built confidently for '{metric_column}'. Ensure the column contains numeric values."

    # Summary stats for the metric
    metric_series = dataframe.select(
        pl.col(metric_column).cast(pl.Float64, strict=False).fill_null(0.0)
    ).to_series()
    metric_stats = {
        "column": metric_column,
        "sum": round(float(metric_series.sum()), 4),
        "mean": round(float(metric_series.mean() or 0), 4),
        "min": round(float(metric_series.min() or 0), 4),
        "max": round(float(metric_series.max() or 0), 4),
        "std": round(float(metric_series.std() or 0), 4),
        "count": int(metric_series.len()),
    }

    report_sections = [
        {
            "heading": "Forecast Inputs",
            "rows": [
                {"label": "Metric Column", "value": metric_column},
                {"label": "Date Column", "value": date_column or "Row order (index)"},
                {"label": "Horizon", "value": f"{len(forecast_pts)} periods"},
                {"label": "Model", "value": "Linear Trend Regression (OLS)"},
                {"label": "Data Points Used", "value": n_points},
            ],
        },
        {
            "heading": "Model Performance",
            "rows": [
                {"label": "R² (Fit Quality)", "value": f"{r_squared:.4f}"},
                {"label": "MAE", "value": f"{mae:.4f}"},
                {"label": "Slope", "value": f"{slope:+.6f} per period"},
                {"label": "Trend Direction", "value": trend_direction.capitalize()},
                {"label": "Historical Growth", "value": f"{growth_pct:+.2f}%"},
            ],
        },
        {
            "heading": "Metric Summary",
            "rows": [
                {"label": "Total", "value": f"{metric_stats['sum']:.2f}"},
                {"label": "Average", "value": f"{metric_stats['mean']:.2f}"},
                {"label": "Min", "value": f"{metric_stats['min']:.2f}"},
                {"label": "Max", "value": f"{metric_stats['max']:.2f}"},
                {"label": "Std Dev", "value": f"{metric_stats['std']:.2f}"},
            ],
        },
        {
            "heading": "Forecast Output",
            "rows": [{"label": str(item["point"]), "value": f"{item['value']:.2f}"} for item in forecast_pts],
        },
    ]

    return {
        "intent": "predictive",
        "question": f"Forecast {metric_column}",
        "answer": answer,
        "report_title": "Forecast Report",
        "report_subtitle": f"Metric: {metric_column} | Direction: {trend_direction}",
        "report_sections": report_sections,
        "recommendations": [
            "Validate the forecast against seasonality and recent business events.",
            "Use the predicted values as a planning range, not as a guarantee.",
            f"The R² score of {r_squared:.3f} indicates {'good' if r_squared > 0.7 else 'moderate' if r_squared > 0.4 else 'weak'} model fit.",
        ],
        "chart_data": chart_data,
        "forecast": forecast_pts,
        "model_stats": {
            "r_squared": r_squared,
            "mae": mae,
            "slope": slope,
            "growth_pct": growth_pct,
            "trend_direction": trend_direction,
            "n_points": n_points,
        },
        "smoothed_history": smoothed_history,
        "metric_stats": metric_stats,
        "metrics": [metric_stats],
    }


def compare_versions(*, before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]]) -> dict[str, Any]:
    before_rows = _validate_rows_input(before_rows, label="before_rows")
    after_rows = _validate_rows_input(after_rows, label="after_rows")
    before = _to_dataframe(before_rows)
    after = _to_dataframe(after_rows)

    if before.is_empty() or after.is_empty():
        return {
            "answer": "Comparison needs both versions of the dataset.",
            "report_sections": [],
            "comparison": None,
            "chart_data": [],
        }

    before_cols = set(before.columns)
    after_cols = set(after.columns)
    numeric_union = sorted(set(_numeric_columns(before)).intersection(_numeric_columns(after)))
    numeric_delta_summary: list[dict[str, Any]] = []
    for column_name in numeric_union[:10]:
        try:
            before_sum = float(_cast_numeric(before, column_name).sum())
            after_sum = float(_cast_numeric(after, column_name).sum())
        except Exception:
            continue
        numeric_delta_summary.append(
            {
                "column": column_name,
                "before": before_sum,
                "after": after_sum,
                "delta": after_sum - before_sum,
                "pct_change": round(((after_sum - before_sum) / before_sum) * 100, 2) if before_sum else None,
            }
        )

    before_null = int(before.null_count().sum_horizontal()[0] if before.columns else 0)
    after_null = int(after.null_count().sum_horizontal()[0] if after.columns else 0)

    comparison = {
        "row_delta": after.height - before.height,
        "column_delta": after.width - before.width,
        "added_columns": sorted(after_cols - before_cols),
        "removed_columns": sorted(before_cols - after_cols),
        "null_delta": after_null - before_null,
        "numeric_delta_summary": numeric_delta_summary,
    }

    answer_parts = [
        f"Rows changed by {comparison['row_delta']} and columns changed by {comparison['column_delta']}.",
    ]
    if numeric_delta_summary:
        top_change = numeric_delta_summary[0]
        answer_parts.append(
            f"The biggest numeric change is in {top_change['column']} with a delta of {top_change['delta']:+.2f}."
        )
    if comparison["null_delta"] > 0:
        answer_parts.append("Null values increased, so the data quality risk is higher.")

    report_sections = [
        {
            "heading": "Comparison Summary",
            "rows": [
                {"label": "Row Delta", "value": comparison["row_delta"]},
                {"label": "Column Delta", "value": comparison["column_delta"]},
                {"label": "Null Delta", "value": comparison["null_delta"]},
                {"label": "Added Columns", "value": ", ".join(comparison["added_columns"]) or "None"},
                {"label": "Removed Columns", "value": ", ".join(comparison["removed_columns"]) or "None"},
            ] + [
                {"label": item["column"], "value": f"{item['before']:.2f} -> {item['after']:.2f} ({item['delta']:+.2f})"}
                for item in numeric_delta_summary[:8]
            ],
        }
    ]

    return {
        "intent": "compare",
        "question": "Compare dataset versions",
        "answer": " ".join(answer_parts),
        "report_title": "Change Comparison Report",
        "report_subtitle": "Before vs After snapshot",
        "report_sections": report_sections,
        "recommendations": [
            "Review the largest metric delta first.",
            "If null values increased, validate the transformation or import step.",
            "Save this comparison report as a baseline for the next change cycle.",
        ],
        "chart_data": numeric_delta_summary,
        "comparison": comparison,
        "row_delta": comparison["row_delta"],
        "column_delta": comparison["column_delta"],
        "null_delta": comparison["null_delta"],
        "added_columns": comparison["added_columns"],
        "removed_columns": comparison["removed_columns"],
        "metrics": numeric_delta_summary,
    }