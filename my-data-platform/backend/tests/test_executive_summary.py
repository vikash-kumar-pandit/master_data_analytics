import pytest
from executive_summary import generate_executive_summary

def test_generate_executive_summary_validation():
    # analysis must be a dict
    with pytest.raises(ValueError, match="analysis must be a dictionary"):
        generate_executive_summary(analysis="not a dict", result={})
        
    # result must be a dict
    with pytest.raises(ValueError, match="result must be a dictionary"):
        generate_executive_summary(analysis={}, result="not a dict")
        
    # analysis cannot be empty
    with pytest.raises(ValueError, match="analysis cannot be empty"):
        generate_executive_summary(analysis={}, result={"a": 1})
        
    # result cannot be empty
    with pytest.raises(ValueError, match="result cannot be empty"):
        generate_executive_summary(analysis={"a": 1}, result={})

def test_generate_executive_summary_narratives():
    analysis = {"rows": 1000, "cols": 10}
    
    # Test intent: descriptive
    res_desc = generate_executive_summary(
        analysis=analysis,
        result={"intent": "descriptive", "answer": "Answer here", "metrics": [{"label": "L1", "value": "V1"}]}
    )
    assert "Data Overview" in res_desc["executive_summary"]
    assert "1,000 rows" in res_desc["executive_summary"]
    assert res_desc["key_findings"] == ["L1: V1"]
    assert "strategic planning" in res_desc["business_impact"]
    assert len(res_desc["next_actions"]) == 3
    assert res_desc["next_actions"][0].startswith("Share findings")

    # Test empty answer defaults
    res_empty_ans = generate_executive_summary(
        analysis=analysis,
        result={"intent": "descriptive", "answer": "", "recommendations": ["Rec1"]}
    )
    assert "Analysis completed successfully." in res_empty_ans["executive_summary"]
    assert res_empty_ans["key_findings"] == ["Rec1"]
    assert res_empty_ans["next_actions"] == ["Rec1"]

    # Test intent: predictive
    res_pred = generate_executive_summary(
        analysis=analysis,
        result={"intent": "predictive", "recommendations": ["Rec1", "Rec2", "Rec3"]}
    )
    assert "Forecast & Prediction" in res_pred["executive_summary"]
    assert "Forecasted trends" in res_pred["business_impact"]
    assert any("Monitor forecast accuracy" in action for action in res_pred["next_actions"])

    # Test intent: diagnostic
    res_diag = generate_executive_summary(
        analysis=analysis,
        result={"intent": "diagnostic", "metrics": []}
    )
    assert "Root Cause Analysis" in res_diag["executive_summary"]
    assert "Root cause identification" in res_diag["business_impact"]
    assert any("Implement corrective measures" in action for action in res_diag["next_actions"])

    # Test intent: comparative
    res_comp = generate_executive_summary(
        analysis=analysis,
        result={"intent": "comparative"}
    )
    assert "Before vs After Comparison" in res_comp["executive_summary"]
    assert "Before/after comparison validates" in res_comp["business_impact"]
    assert any("Document changes made" in action for action in res_comp["next_actions"])

    # Test intent: prescriptive
    res_pres = generate_executive_summary(
        analysis=analysis,
        result={"intent": "prescriptive"}
    )
    assert "Recommended Actions" in res_pres["executive_summary"]
    assert "Recommended actions prioritized" in res_pres["business_impact"]

    # Test other/unknown intent
    res_other = generate_executive_summary(
        analysis=analysis,
        result={"intent": "other"}
    )
    assert "Analysis" in res_other["executive_summary"]
