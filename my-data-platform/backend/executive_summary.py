from __future__ import annotations

from typing import Any


def generate_executive_summary(*, analysis: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Generate a business-friendly executive summary from analysis results."""
    # Validate inputs
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a dictionary")
    if not isinstance(result, dict):
        raise ValueError("result must be a dictionary")
    if not analysis:
        raise ValueError("analysis cannot be empty")
    if not result:
        raise ValueError("result cannot be empty")
    
    rows = max(0, analysis.get("rows", 0))
    cols = max(0, analysis.get("cols", 0))
    intent = (result.get("intent") or "descriptive").lower()
    answer = (result.get("answer") or "").strip()
    metrics = result.get("metrics", []) or []
    recommendations = result.get("recommendations", []) or []
    
    if not answer:
        answer = "Analysis completed successfully."
    
    # Build narrative sections
    summary_text = _build_narrative(intent, answer, rows, cols)
    key_findings = _extract_key_findings(metrics, recommendations)
    business_impact = _assess_business_impact(intent, metrics)
    next_actions = _suggest_next_actions(intent, recommendations)
    
    return {
        "executive_summary": summary_text,
        "key_findings": key_findings,
        "business_impact": business_impact,
        "next_actions": next_actions,
        "metadata": {
            "rows_analyzed": rows,
            "columns_used": cols,
            "analysis_type": intent,
        },
    }


def _build_narrative(intent: str, answer: str, rows: int, cols: int) -> str:
    """Build human-readable narrative."""
    intent_map = {
        "descriptive": "Data Overview",
        "diagnostic": "Root Cause Analysis",
        "predictive": "Forecast & Prediction",
        "comparative": "Before vs After Comparison",
        "prescriptive": "Recommended Actions",
    }
    
    analysis_type = intent_map.get(intent, "Analysis")
    
    return (
        f"{analysis_type}\n\n"
        f"Dataset: {rows:,} rows × {cols} columns analyzed.\n\n"
        f"Key Finding:\n{answer}\n\n"
        "This analysis provides actionable insights to support data-driven decision making."
    )


def _extract_key_findings(metrics: list[dict[str, Any]], recommendations: list[str]) -> list[str]:
    """Extract top 3 findings from metrics."""
    findings = []
    
    for metric in metrics[:3]:
        label = metric.get("label", "")
        value = metric.get("value", "")
        if label and value:
            findings.append(f"{label}: {value}")
    
    if not findings and recommendations:
        findings = recommendations[:3]
    
    return findings or ["Dataset loaded and analyzed successfully."]


def _assess_business_impact(intent: str, metrics: list[dict[str, Any]]) -> str:
    """Assess business impact based on intent."""
    if intent == "predictive":
        return "Forecasted trends enable proactive resource allocation and risk mitigation."
    elif intent == "diagnostic":
        return "Root cause identification allows targeted corrective actions."
    elif intent == "comparative":
        return "Before/after comparison validates effectiveness of implemented changes."
    elif intent == "prescriptive":
        return "Recommended actions prioritized by business value and feasibility."
    else:
        return "Data insights inform strategic planning and operational improvements."


def _suggest_next_actions(intent: str, recommendations: list[str]) -> list[str]:
    """Suggest actionable next steps."""
    actions = []
    
    if recommendations:
        actions.extend(recommendations[:2])
    
    if intent == "predictive":
        actions.append("Monitor forecast accuracy weekly and adjust models as needed.")
    elif intent == "diagnostic":
        actions.append("Implement corrective measures and track KPI improvements.")
    elif intent == "comparative":
        actions.append("Document changes made and share results with stakeholders.")
    
    if not actions:
        actions = [
            "Share findings with relevant stakeholders.",
            "Schedule follow-up analysis for deeper insights.",
            "Document decisions made based on this analysis.",
        ]
    
    return actions[:3]
