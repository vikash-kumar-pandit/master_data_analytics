import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ExplainableAIChart from './ExplainableAIChart';

const API_BASE_URL = 'http://localhost:8000';

export default function AutoMLWidget({ file, targetColumn, rows, onResult }) {
  const [taskId, setTaskId] = useState('');
  const [status, setStatus] = useState('IDLE');
  const [message, setMessage] = useState('Ready to train models.');
  const [result, setResult] = useState(null);
  const [xaiData, setXaiData] = useState([]);
  const [xaiStatus, setXaiStatus] = useState('');

  const fetchExplainability = async () => {
    if (!Array.isArray(rows) || !rows.length || !targetColumn) {
      setXaiStatus('Explainability skipped: missing data or target column.');
      return;
    }

    try {
      setXaiStatus('Generating explainability insights...');
      const response = await axios.post(`${API_BASE_URL}/api/explain-automl`, {
        rows,
        target_column: targetColumn,
        sample_index: 0,
        top_k: 7,
      });

      const chartData = (response.data?.global_importance || []).map((item) => ({
        feature: String(item.feature || ''),
        impact: Number(item.importance || 0),
      }));
      setXaiData(chartData);
      setXaiStatus(chartData.length ? 'Explainability ready.' : 'No explainability data returned.');
    } catch (error) {
      setXaiData([]);
      setXaiStatus(error?.response?.data?.detail || 'Explainability unavailable for this model/data.');
    }
  };

  const startTraining = async () => {
    if (!file) {
      setStatus('FAILURE');
      setMessage('Please upload a CSV file first.');
      return;
    }

    if (!targetColumn) {
      setStatus('FAILURE');
      setMessage('Please select a target column.');
      return;
    }

    setStatus('STARTING');
    setMessage('Uploading data...');
    setResult(null);
    setXaiData([]);
    setXaiStatus('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_column', targetColumn);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/predict-background`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setTaskId(response.data.task_id);
      setStatus('PENDING');
      setMessage('Task queued for model training.');
    } catch (error) {
      setStatus('FAILURE');
      setMessage(error?.response?.data?.detail || 'Failed to start training.');
    }
  };

  useEffect(() => {
    if (!taskId || !['PENDING', 'PROGRESS', 'STARTED'].includes(status)) {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/task-status/${taskId}`);
        const taskState = res.data.state;

        setStatus(taskState);

        if (taskState === 'SUCCESS') {
          const taskResult = res.data.result?.automl || null;
          setResult(taskResult);
          setMessage('Training complete.');
          if (taskResult && onResult) {
            onResult(taskResult);
          }
          fetchExplainability();
          window.clearInterval(intervalId);
          return;
        }

        if (taskState === 'REVOKED' || taskState === 'FAILURE') {
          setMessage(res.data.status || 'Task failed or cancelled.');
          window.clearInterval(intervalId);
          return;
        }

        setMessage(res.data.status || 'Processing...');
      } catch (error) {
        setStatus('FAILURE');
        setMessage(error?.response?.data?.detail || 'Error fetching task status.');
        window.clearInterval(intervalId);
      }
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [taskId, status, onResult, rows, targetColumn]);

  const cancelTraining = async () => {
    if (!taskId) {
      return;
    }

    try {
      await axios.post(`${API_BASE_URL}/api/revoke-task/${taskId}`);
      setStatus('REVOKED');
      setMessage('Task cancelled by user.');
    } catch (error) {
      setStatus('FAILURE');
      setMessage(error?.response?.data?.detail || 'Unable to cancel task.');
    }
  };

  const canStart = ['IDLE', 'REVOKED', 'FAILURE', 'SUCCESS'].includes(status);
  const isRunning = ['PENDING', 'PROGRESS', 'STARTED'].includes(status);

  return (
    <div className="automl-widget">
      <h3>AutoML Predictor</h3>

      <div className="automl-widget-status">
        <p>
          <strong>Status:</strong> {status}
        </p>
        <p>{message}</p>
      </div>

      {result ? (
        <div className="automl-widget-result">
          <p>
            <strong>Best Model:</strong> {result.best_algorithm}
          </p>
          <p>
            <strong>Accuracy:</strong>{' '}
            {typeof result.accuracy === 'number' ? `${(result.accuracy * 100).toFixed(2)}%` : 'Not available'}
          </p>
        </div>
      ) : null}

      {xaiStatus ? <p className="xai-status">{xaiStatus}</p> : null}
      <ExplainableAIChart featureData={xaiData} />

      <div className="automl-widget-actions">
        {canStart ? (
          <button type="button" onClick={startTraining}>
            {status === 'REVOKED' || status === 'FAILURE' ? 'Retry Training' : 'Start Training'}
          </button>
        ) : null}

        {isRunning ? (
          <button type="button" className="danger" onClick={cancelTraining}>
            Cancel Task
          </button>
        ) : null}
      </div>
    </div>
  );
}