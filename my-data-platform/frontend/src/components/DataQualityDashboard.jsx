import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

export default function DataQualityDashboard({ rows }) {
  const [metrics, setMetrics] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeView, setActiveView] = useState('summary');

  useEffect(() => {
    if (rows && rows.length > 0) {
      calculateQuality();
    }
  }, [rows]);

  const calculateQuality = async () => {
    if (!rows || rows.length === 0) {
      setError('No data available');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const [metricsRes, reportRes] = await Promise.all([
        axios.post(`${API_BASE_URL}/api/quality/score`, { rows }),
        axios.post(`${API_BASE_URL}/api/quality/report`, { rows }),
      ]);

      setMetrics(metricsRes.data.metrics);
      setReport(reportRes.data.report);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Quality scoring failed');
    } finally {
      setLoading(false);
    }
  };

  if (!rows || rows.length === 0) {
    return (
      <div className="quality-empty">
        <p>Upload data to analyze quality metrics</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="quality-loading">
        <p>⏳ Analyzing data quality...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="quality-error">
        <p>❌ {error}</p>
        <button onClick={calculateQuality} className="quality-retry-btn">
          Retry
        </button>
      </div>
    );
  }

  if (!metrics || !report) {
    return <div className="quality-empty">No metrics available</div>;
  }

  const qualityColor = (score) => {
    if (score >= 90) return '#16a34a';
    if (score >= 75) return '#0ea5e9';
    if (score >= 60) return '#f59e0b';
    return '#dc2626';
  };

  return (
    <div className="quality-dashboard">
      {/* Tab Navigation */}
      <div className="quality-tabs">
        <button
          className={`quality-tab ${activeView === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveView('summary')}
        >
          📊 Summary
        </button>
        <button
          className={`quality-tab ${activeView === 'columns' ? 'active' : ''}`}
          onClick={() => setActiveView('columns')}
        >
          📋 Columns
        </button>
        <button
          className={`quality-tab ${activeView === 'issues' ? 'active' : ''}`}
          onClick={() => setActiveView('issues')}
        >
          ⚠️ Issues ({report.issues?.length || 0})
        </button>
        <button
          className={`quality-tab ${activeView === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveView('recommendations')}
        >
          💡 Recommendations
        </button>
      </div>

      {/* Summary View */}
      {activeView === 'summary' && (
        <div className="quality-summary">
          <div className="quality-score-card main">
            <div className="quality-score-circle">
              <div
                className="quality-score-value"
                style={{ color: qualityColor(metrics.overall_score) }}
              >
                {metrics.overall_score}
              </div>
              <div className="quality-score-label">Overall Quality</div>
            </div>
            <div className="quality-level-badge" style={{ backgroundColor: qualityColor(metrics.overall_score) }}>
              {metrics.quality_level}
            </div>
          </div>

          <div className="quality-grid">
            <div className="quality-metric-card">
              <div className="quality-metric-value" style={{ color: qualityColor(metrics.completeness_score) }}>
                {metrics.completeness_score.toFixed(1)}%
              </div>
              <div className="quality-metric-label">Completeness</div>
              <div className="quality-metric-desc">Missing values</div>
            </div>

            <div className="quality-metric-card">
              <div className="quality-metric-value" style={{ color: qualityColor(metrics.uniqueness_score) }}>
                {metrics.uniqueness_score.toFixed(1)}%
              </div>
              <div className="quality-metric-label">Uniqueness</div>
              <div className="quality-metric-desc">No duplicates</div>
            </div>

            <div className="quality-metric-card">
              <div className="quality-metric-value" style={{ color: qualityColor(metrics.consistency_score) }}>
                {metrics.consistency_score.toFixed(1)}%
              </div>
              <div className="quality-metric-label">Consistency</div>
              <div className="quality-metric-desc">Data types</div>
            </div>

            <div className="quality-metric-card">
              <div className="quality-metric-value" style={{ color: qualityColor(metrics.accuracy_score) }}>
                {metrics.accuracy_score.toFixed(1)}%
              </div>
              <div className="quality-metric-label">Accuracy</div>
              <div className="quality-metric-desc">Value ranges</div>
            </div>
          </div>

          <div className="quality-info">
            <div className="quality-stat">
              <span className="stat-label">Rows:</span>
              <span className="stat-value">{metrics.row_count.toLocaleString()}</span>
            </div>
            <div className="quality-stat">
              <span className="stat-label">Columns:</span>
              <span className="stat-value">{metrics.column_count}</span>
            </div>
          </div>
        </div>
      )}

      {/* Columns View */}
      {activeView === 'columns' && (
        <div className="quality-columns">
          <table className="quality-table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Type</th>
                <th>Quality</th>
                <th>Missing</th>
                <th>Stats</th>
              </tr>
            </thead>
            <tbody>
              {report.column_analysis?.map((col, idx) => (
                <tr key={idx}>
                  <td className="col-name">{col.column}</td>
                  <td className="col-type">{col.type}</td>
                  <td>
                    <div className="quality-bar">
                      <div
                        className="quality-fill"
                        style={{
                          width: `${col.quality_score}%`,
                          backgroundColor: qualityColor(col.quality_score),
                        }}
                      />
                    </div>
                    <span className="quality-pct">{col.quality_score}%</span>
                  </td>
                  <td>{col.missing_count > 0 ? `${col.missing_percent}%` : '✓'}</td>
                  <td className="col-stats">
                    {col.mean !== undefined ? `μ=${col.mean?.toFixed(2)}` : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Issues View */}
      {activeView === 'issues' && (
        <div className="quality-issues">
          {report.issues && report.issues.length > 0 ? (
            <ul className="quality-issue-list">
              {report.issues.map((issue, idx) => (
                <li key={idx} className="quality-issue-item">
                  <span className="issue-icon">⚠️</span>
                  <span className="issue-text">{issue}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="quality-empty">
              <p>✓ No quality issues detected</p>
            </div>
          )}
        </div>
      )}

      {/* Recommendations View */}
      {activeView === 'recommendations' && (
        <div className="quality-recommendations">
          {report.recommendations && report.recommendations.length > 0 ? (
            <ul className="quality-rec-list">
              {report.recommendations.map((rec, idx) => (
                <li key={idx} className="quality-rec-item">
                  <span className="rec-icon">💡</span>
                  <span className="rec-text">{rec}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="quality-empty">
              <p>No recommendations at this time</p>
            </div>
          )}
        </div>
      )}

      <button onClick={calculateQuality} className="quality-refresh-btn">
        🔄 Refresh Analysis
      </button>
    </div>
  );
}
