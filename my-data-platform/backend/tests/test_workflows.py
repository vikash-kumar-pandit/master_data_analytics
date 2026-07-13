import pytest
import polars as pl
from unittest.mock import patch, MagicMock, ANY
from database import SessionLocal
from models import WorkflowDefinition
from workflows import (
    list_workflows, get_workflow, save_workflow,
    create_workflow_definition, execute_workflow
)

@pytest.fixture
def clean_db():
    with SessionLocal() as db:
        db.query(WorkflowDefinition).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(WorkflowDefinition).delete()
        db.commit()

def test_save_get_list_workflows(clean_db):
    # Retrieve when empty
    assert list_workflows() == []
    assert get_workflow("missing-id") is None
    
    # Save new workflow
    wf_data = {
        "id": "wf-1",
        "name": "My Workflow",
        "description": "Workflow Description",
        "steps": ["profile", "clean"],
        "created_by": "user_a"
    }
    save_workflow(wf_data)
    
    # Get saved workflow
    retrieved = get_workflow("wf-1")
    assert retrieved is not None
    assert retrieved["name"] == "My Workflow"
    assert retrieved["steps"] == ["profile", "clean"]
    assert retrieved["created_by"] == "user_a"
    assert retrieved["created_at"] is not None
    
    # List workflows
    workflow_list = list_workflows()
    assert len(workflow_list) == 1
    assert workflow_list[0]["id"] == "wf-1"
    
    # Update existing workflow
    wf_data_updated = {
        "id": "wf-1",
        "name": "My Workflow Updated",
        "description": "Updated Description",
        "steps": ["profile", "clean", "arrange"]
    }
    save_workflow(wf_data_updated)
    
    retrieved_updated = get_workflow("wf-1")
    assert retrieved_updated["name"] == "My Workflow Updated"
    assert retrieved_updated["steps"] == ["profile", "clean", "arrange"]


def test_create_workflow_definition():
    # Valid definition with some invalid/duplicate steps
    payload = {
        "name": "  Test WF  ",
        "description": "  Desc  ",
        "steps": ["profile", "clean", "invalid_step", "profile"],
        "target_column": "target",
        "text_column": "text",
        "categories": ["  cat1  ", "", "  cat2  "],
        "num_clusters": 5,
        "sample_index": 1,
        "top_k": 20
    }
    
    res = create_workflow_definition(payload)
    assert res["name"] == "Test WF"
    assert res["description"] == "Desc"
    # Duplicate 'profile' and invalid 'invalid_step' should be removed/normalized
    assert res["steps"] == ["profile", "clean"]
    assert res["target_column"] == "target"
    assert res["text_column"] == "text"
    assert res["categories"] == ["cat1", "cat2"]
    assert res["num_clusters"] == 5
    assert res["sample_index"] == 1
    assert res["top_k"] == 20
    assert res["created_at"] is not None
    
    # No valid steps should raise ValueError
    with pytest.raises(ValueError, match="At least one valid workflow step is required"):
        create_workflow_definition({"steps": ["invalid_step"]})


@patch("workflows.register_catalog_entry")
@patch("workflows.analyze_dataframe")
@patch("workflows.identify_dataset_semantics")
@patch("workflows.advanced_data_cleaning")
@patch("workflows.advanced_data_arranging")
@patch("workflows.run_automl_stateless")
@patch("workflows.run_nocode_clustering")
@patch("workflows.run_nocode_nlp")
@patch("workflows.generate_shap_explanations")
def test_execute_workflow(
    mock_shap, mock_nlp, mock_cluster, mock_automl,
    mock_arrange, mock_clean, mock_semantics, mock_analyze, mock_catalog
):
    # Setup mock return values
    mock_analyze.return_value = {"metrics": 1}
    mock_semantics.return_value = {"domain": "sales"}
    
    df_clean = pl.DataFrame({"a": [1, 2]})
    mock_clean.return_value = df_clean
    
    mock_arrange.return_value = (pl.DataFrame({"b": [3, 4]}), ["arranging_note"])
    mock_automl.return_value = {"best_algorithm": "LightGBM"}
    mock_cluster.return_value = pl.DataFrame({"c": [5, 6]})
    mock_nlp.return_value = pl.DataFrame({"d": [7, 8]})
    mock_shap.return_value = {"problem_type": "classification", "importances": {}}
    
    # Execution with empty rows
    with pytest.raises(ValueError, match="No rows provided"):
        execute_workflow({"steps": ["profile"]}, [])
        
    rows = [{"col1": "val1"}]
    
    # Test step: profile
    wf_profile = {"id": "w1", "name": "Profile", "steps": ["profile"]}
    res = execute_workflow(wf_profile, rows)
    assert res["workflow_id"] == "w1"
    assert res["step_outputs"][0]["step"] == "profile"
    assert res["analysis"]["domain_info"] == {"domain": "sales"}
    mock_analyze.assert_called()
    mock_semantics.assert_called()
    mock_catalog.assert_called()
    
    # Test step: clean
    wf_clean = {"id": "w2", "name": "Clean", "steps": ["clean"]}
    res = execute_workflow(wf_clean, rows)
    assert res["step_outputs"][0]["step"] == "clean"
    mock_clean.assert_called()
    
    # Test step: arrange
    wf_arrange = {"id": "w3", "name": "Arrange", "steps": ["arrange"]}
    res = execute_workflow(wf_arrange, rows)
    assert res["step_outputs"][0]["step"] == "arrange"
    assert res["step_outputs"][0]["notes"] == ["arranging_note"]
    mock_arrange.assert_called()
    
    # Test step: automl
    wf_automl_err = {"id": "w4", "steps": ["automl"]}
    with pytest.raises(ValueError, match="target_column is required for AutoML"):
        execute_workflow(wf_automl_err, rows)
        
    wf_automl = {"id": "w4", "steps": ["automl"], "target_column": "target"}
    res = execute_workflow(wf_automl, rows)
    assert res["step_outputs"][0]["step"] == "automl"
    assert res["step_outputs"][0]["best_algorithm"] == "LightGBM"
    mock_automl.assert_called()
    
    # Test step: cluster
    wf_cluster = {"id": "w5", "steps": ["cluster"], "num_clusters": 4}
    res = execute_workflow(wf_cluster, rows)
    assert res["step_outputs"][0]["step"] == "cluster"
    assert res["step_outputs"][0]["num_clusters"] == 4
    mock_cluster.assert_called_with(ANY, num_clusters=4) # First arg is Polars Lazy/DataFrame
    
    # Test step: nlp
    wf_nlp_err1 = {"id": "w6", "steps": ["nlp"]}
    with pytest.raises(ValueError, match="text_column is required for NLP"):
        execute_workflow(wf_nlp_err1, rows)
    
    wf_nlp_err2 = {"id": "w6", "steps": ["nlp"], "text_column": "txt"}
    with pytest.raises(ValueError, match="categories are required for NLP"):
        execute_workflow(wf_nlp_err2, rows)
        
    wf_nlp = {"id": "w6", "steps": ["nlp"], "text_column": "txt", "categories": ["A", "B"]}
    res = execute_workflow(wf_nlp, rows)
    assert res["step_outputs"][0]["step"] == "nlp"
    mock_nlp.assert_called()
    
    # Test step: explain
    wf_explain_err = {"id": "w7", "steps": ["explain"]}
    with pytest.raises(ValueError, match="target_column is required for explainability"):
        execute_workflow(wf_explain_err, rows)
        
    wf_explain = {"id": "w7", "steps": ["explain"], "target_column": "target", "sample_index": 0, "top_k": 5}
    res = execute_workflow(wf_explain, rows)
    assert res["step_outputs"][0]["step"] == "explain"
    assert res["step_outputs"][0]["problem_type"] == "classification"
    mock_shap.assert_called()
    
    # Test step: unsupported step name
    wf_unsupported = {"id": "w8", "steps": ["unsupported"]}
    with pytest.raises(ValueError, match="Unsupported workflow step"):
        execute_workflow(wf_unsupported, rows)
