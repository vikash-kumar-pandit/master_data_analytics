import React, { useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

export default function ExecutiveSummary({ analysis, result }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerateSummary = async () => {
    if (!analysis || !result) {
      setError('Run an analysis first.');
      return;
    }

    // Validate data
    if (typeof analysis !== 'object' || typeof result !== 'object') {
      setError('Invalid analysis or result data.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/summary/executive`, {
        analysis,
        result,
      }, {
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000,
      });
      
      if (response.data) {
        setSummary(response.data);
      } else {
        setError('No summary data received.');
      }
    } catch (err) {
      console.error('Summary generation failed:', err);
      const detail = err?.response?.data?.detail;
      if (err.code === 'ECONNABORTED') {
        setError('Request timeout. Please try again.');
      } else if (err.response?.status === 400) {
        setError(`Validation error: ${detail || 'Invalid input data'}`);
      } else if (err.response?.status === 500) {
        setError(`Server error: ${detail || 'Failed to generate summary'}`);
      } else {
        setError(detail || 'Failed to generate summary. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!summary) {
    return (
      <div className="executive-summary-prompt">
        <p>Generate a business-friendly executive summary from this analysis.</p>
        <button
          type="button"
          onClick={handleGenerateSummary}
          disabled={loading || !analysis || !result}
          className="btn-primary"
          title={!analysis || !result ? 'Run an analysis first' : 'Generate executive summary'}
        >
          {loading ? 'Generating...' : 'Generate Executive Summary'}
        </button>
        {error && <p className="error">⚠️ {error}</p>}
      </div>
    );
  }

  return (
    <div className="executive-summary-container">
      <div className="summary-section">
        <h3>Executive Summary</h3>
        <div className="summary-text">
          {summary.executive_summary ? (
            summary.executive_summary.split('\n').map((line, i) => (
              <p key={i}>{line || <br />}</p>
            ))
          ) : (
            <p>No summary available.</p>
          )}
        </div>
      </div>

      {summary.key_findings && summary.key_findings.length > 0 && (
        <div className="summary-section">
          <h3>Key Findings</h3>
          <ul>
            {summary.key_findings.map((finding, i) => (
              <li key={i}>{finding}</li>
            ))}
          </ul>
        </div>
      )}

      {summary.business_impact && (
        <div className="summary-section">
          <h3>Business Impact</h3>
          <p>{summary.business_impact}</p>
        </div>
      )}

      {summary.next_actions && summary.next_actions.length > 0 && (
        <div className="summary-section">
          <h3>Next Actions</h3>
          <ol>
            {summary.next_actions.map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ol>
        </div>
      )}

      {summary.metadata && (
        <div className="summary-metadata">
          <small>
            Analysis: {summary.metadata?.analysis_type || 'N/A'} | 
            Rows: {summary.metadata?.rows_analyzed || 0} | 
            Columns: {summary.metadata?.columns_used || 0}
          </small>
        </div>
      )}

      <button
        type="button"
        onClick={() => setSummary(null)}
        className="btn-secondary-small"
      >
        Generate New Summary
      </button>
    </div>
  );
}
