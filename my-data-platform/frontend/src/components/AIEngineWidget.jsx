import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export default function AIEngineWidget({ rows, availableColumns, onUpdateData }) {
  const [columnName, setColumnName] = useState('');
  const [categories, setCategories] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  const runNLP = async () => {
    if (!rows?.length) {
      setStatus('Please upload and clean data first.');
      return;
    }

    if (!columnName.trim()) {
      setStatus('Please select or enter a text column.');
      return;
    }

    const categoryList = categories
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);

    if (!categoryList.length) {
      setStatus('Please provide categories separated by commas.');
      return;
    }

    setLoading(true);
    setStatus('Initializing AI Model...');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/apply-nlp`, {
        rows,
        text_column: columnName.trim(),
        categories: categoryList,
      });

      setStatus('NLP classification successful.');
      onUpdateData?.(response.data.data || []);
    } catch (error) {
      setStatus(error?.response?.data?.detail || 'Error running NLP classification.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-engine-widget">
      <h3>No-Code NLP Text Classification</h3>
      <p>
        Categorize any text column using zero-shot AI. Example labels: Positive, Neutral, Negative.
      </p>

      <div className="ai-engine-inputs">
        <select value={columnName} onChange={(event) => setColumnName(event.target.value)} disabled={loading}>
          <option value="">Select text column</option>
          {availableColumns.map((column) => (
            <option key={column} value={column}>
              {column}
            </option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Categories: Positive, Neutral, Negative"
          value={categories}
          onChange={(event) => setCategories(event.target.value)}
          disabled={loading}
        />
      </div>

      <button type="button" onClick={runNLP} disabled={loading}>
        {loading ? 'Processing NLP...' : 'Run AI Classification'}
      </button>

      {status ? <p className="ai-engine-status">{status}</p> : null}
    </div>
  );
}
