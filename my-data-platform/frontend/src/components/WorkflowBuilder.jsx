import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const STEP_OPTIONS = [
  { key: 'profile', label: 'Profile data' },
  { key: 'arrange', label: 'Arrange data' },
  { key: 'clean', label: 'Clean data' },
  { key: 'automl', label: 'Run AutoML' },
  { key: 'cluster', label: 'Cluster rows' },
  { key: 'nlp', label: 'Apply NLP' },
  { key: 'explain', label: 'Explain model' },
];

export default function WorkflowBuilder({ rows, targetOptions = [], onWorkflowRun }) {
  const [workflows, setWorkflows] = useState([]);
  const [workflowName, setWorkflowName] = useState('My First Workflow');
  const [description, setDescription] = useState('');
  const [selectedSteps, setSelectedSteps] = useState(['profile', 'clean']);
  const [targetColumn, setTargetColumn] = useState('');
  const [textColumn, setTextColumn] = useState('');
  const [categories, setCategories] = useState('positive,neutral,negative');
  const [numClusters, setNumClusters] = useState(3);
  const [sampleIndex, setSampleIndex] = useState(0);
  const [topK, setTopK] = useState(10);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const availableStepLabels = useMemo(() => {
    return STEP_OPTIONS.filter((step) => selectedSteps.includes(step.key))
      .map((step) => step.label)
      .join(' -> ');
  }, [selectedSteps]);

  const loadWorkflows = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/workflows`);
      setWorkflows(response.data.items || []);
    } catch (fetchError) {
      setWorkflows([]);
    }
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  const toggleStep = (stepKey) => {
    setSelectedSteps((current) => {
      if (current.includes(stepKey)) {
        return current.filter((value) => value !== stepKey);
      }
      return [...current, stepKey];
    });
  };

  const buildPayload = () => ({
    name: workflowName,
    description,
    steps: selectedSteps,
    target_column: targetColumn || null,
    text_column: textColumn || null,
    categories: categories
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean),
    num_clusters: Number(numClusters) || 3,
    sample_index: Number(sampleIndex) || 0,
    top_k: Number(topK) || 10,
  });

  const handleSaveWorkflow = async () => {
    if (!selectedSteps.length) {
      setError('Select at least one workflow step.');
      return;
    }

    setLoading(true);
    setError('');
    setStatus('Saving workflow...');

    try {
      await axios.post(`${API_BASE_URL}/api/workflows`, buildPayload());
      setStatus('Workflow saved.');
      await loadWorkflows();
    } catch (saveError) {
      setError(saveError?.response?.data?.detail || 'Workflow save failed.');
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  const handleRunWorkflow = async (workflow) => {
    if (!rows.length) {
      setError('Upload a dataset before running a workflow.');
      return;
    }

    setLoading(true);
    setError('');
    setStatus(`Running ${workflow.name}...`);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/workflows/${workflow.id}/run`, {
        rows,
      });
      setResult(response.data);
      setStatus(`Completed ${workflow.name}.`);
      onWorkflowRun?.(response.data);
    } catch (runError) {
      setError(runError?.response?.data?.detail || 'Workflow execution failed.');
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  const handleRunDraft = async () => {
    if (!rows.length) {
      setError('Upload a dataset before running a workflow.');
      return;
    }

    setLoading(true);
    setError('');
    setStatus('Saving draft workflow...');

    try {
      const saveResponse = await axios.post(`${API_BASE_URL}/api/workflows`, buildPayload());
      const savedWorkflow = saveResponse.data.workflow;
      setStatus(`Running ${savedWorkflow.name}...`);

      const runResponse = await axios.post(`${API_BASE_URL}/api/workflows/${savedWorkflow.id}/run`, {
        rows,
      });

      setResult(runResponse.data);
      setStatus(`Completed ${savedWorkflow.name}.`);
      onWorkflowRun?.(runResponse.data);
      await loadWorkflows();
    } catch (draftError) {
      setError(draftError?.response?.data?.detail || 'Workflow execution failed.');
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="workflow-builder">
      <div className="workflow-builder-form">
        <div className="workflow-header">
          <div>
            <h2>No-Code Workflow Builder</h2>
            <p>Compose a reusable pipeline for profiling, cleaning, modeling, and explainability.</p>
          </div>
          <span>{availableStepLabels || 'No steps selected'}</span>
        </div>

        <div className="workflow-grid">
          <label>
            Workflow name
            <input value={workflowName} onChange={(event) => setWorkflowName(event.target.value)} />
          </label>
          <label>
            Description
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label>
            Target column
            <select value={targetColumn} onChange={(event) => setTargetColumn(event.target.value)}>
              <option value="">Select target</option>
              {targetOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Text column
            <select value={textColumn} onChange={(event) => setTextColumn(event.target.value)}>
              <option value="">Select text column</option>
              {targetOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Categories
            <input value={categories} onChange={(event) => setCategories(event.target.value)} />
          </label>
          <label>
            Clusters
            <input type="number" min="2" value={numClusters} onChange={(event) => setNumClusters(event.target.value)} />
          </label>
          <label>
            Sample index
            <input type="number" min="0" value={sampleIndex} onChange={(event) => setSampleIndex(event.target.value)} />
          </label>
          <label>
            Top features
            <input type="number" min="1" value={topK} onChange={(event) => setTopK(event.target.value)} />
          </label>
        </div>

        <div className="workflow-steps">
          {STEP_OPTIONS.map((step) => (
            <button
              key={step.key}
              type="button"
              className={selectedSteps.includes(step.key) ? 'workflow-step active' : 'workflow-step'}
              onClick={() => toggleStep(step.key)}
            >
              {step.label}
            </button>
          ))}
        </div>

        <div className="workflow-actions">
          <button type="button" onClick={handleSaveWorkflow} disabled={loading}>
            {loading ? 'Working...' : 'Save Workflow'}
          </button>
          <button type="button" onClick={handleRunDraft} disabled={loading || !rows.length}>
            Run Draft on Current Data
          </button>
        </div>

        {error ? <p className="error">{error}</p> : null}
        {status ? <p className="workflow-status">{status}</p> : null}
      </div>

      <div className="workflow-history">
        <div className="audit-header">
          <h3>Saved Workflows</h3>
          <p>{workflows.length} saved</p>
        </div>

        <div className="workflow-list">
          {workflows.length ? (
            workflows.map((workflow) => (
              <div key={workflow.id} className="workflow-card">
                <strong>{workflow.name}</strong>
                <small>{workflow.steps.join(' -> ')}</small>
                <small>{workflow.created_at}</small>
                <button type="button" onClick={() => handleRunWorkflow(workflow)} disabled={loading || !rows.length}>
                  Run Saved Workflow
                </button>
              </div>
            ))
          ) : (
            <p>No workflows saved yet.</p>
          )}
        </div>

        {result ? (
          <div className="workflow-result">
            <h3>Latest Run</h3>
            <p>Steps executed: {result.step_outputs?.length || 0}</p>
            <p>Final columns: {(result.final_columns || []).join(', ')}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
