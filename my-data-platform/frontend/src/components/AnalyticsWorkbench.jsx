import React, { useMemo, useState } from 'react';
import axios from 'axios';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { API_BASE_URL } from '../config';
import ShareModal from './ShareModal';
import ExecutiveSummary from './ExecutiveSummary';
import ScheduleExportModal from './ScheduleExportModal';

function safeText(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    };
    return map[char] || char;
  });
}

export default function AnalyticsWorkbench({ rows, analysis, baselineRows = [], onSaveBaseline }) {
  const [question, setQuestion] = useState('Profit kyo gir gaya?');
  const [metricColumn, setMetricColumn] = useState('');
  const [dateColumn, setDateColumn] = useState('');
  const [horizon, setHorizon] = useState(7);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showSummary, setShowSummary] = useState(false);

  const availableColumns = useMemo(() => (rows.length ? Object.keys(rows[0]) : []), [rows]);

  const reportSections = result?.report_sections || [];

  const trendData = useMemo(() => {
    if (Array.isArray(result?.forecast) && result.forecast.length) {
      return result.forecast.map((item) => ({ label: item.point, value: Number(item.value || 0) }));
    }
    if (Array.isArray(result?.chart_data) && result.chart_data.length) {
      return result.chart_data.map((item, index) => ({
        label: item.date || item.point || item.row_index || `P${index + 1}`,
        value: Number(item.value || item[metricColumn] || 0),
      }));
    }
    return [];
  }, [result, metricColumn]);

  const handleAsk = async () => {
    if (!rows.length) {
      setError('Upload a dataset first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/analytics/query`, {
        question,
        rows,
        previous_rows: baselineRows.length ? baselineRows : null,
        analysis,
      });
      setResult(response.data || null);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Question analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleForecast = async () => {
    if (!rows.length) {
      setError('Upload a dataset first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/analytics/forecast`, {
        rows,
        metric_column: metricColumn || null,
        date_column: dateColumn || null,
        horizon: Number(horizon) || 7,
      });
      setResult(response.data || null);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Forecast failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!rows.length || !baselineRows.length) {
      setError('Baseline snapshot and current data are both required for comparison.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/analytics/compare`, {
        before_rows: baselineRows,
        after_rows: rows,
      });
      setResult(response.data || null);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async (outputFormat) => {
    if (!result) {
      setError('Run a question, forecast, or comparison first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/analytics/report`,
        {
          title: result.report_title || 'Analytics Report',
          subtitle: result.report_subtitle || 'Generated from dataset',
          sections: reportSections,
          output_format: outputFormat,
        },
        { responseType: 'blob' }
      );

      const mimeType =
        outputFormat === 'pptx'
          ? 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
          : 'application/pdf';
      const fileName = outputFormat === 'pptx' ? 'analytics_report.pptx' : 'analytics_report.pdf';
      const blob = new Blob([response.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Report download failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBaseline = () => {
    if (!rows.length) {
      setError('Upload a dataset before saving a baseline.');
      return;
    }
    onSaveBaseline?.(rows);
  };

  return (
    <div className="card stats-card analytics-workbench">
      <div className="audit-header">
        <h2>Ask the Data Platform</h2>
        <p>{rows.length ? `${rows.length} current row(s)` : 'No dataset loaded'}</p>
      </div>

      <p className="card-note">
        Ask plain-language questions like "Profit kyo gir gaya?", "Customer kyo kam ho gaya?", or "Agle month kya hoga?".
      </p>

      <div className="analytics-grid">
        <label>
          Your question
          <textarea
            rows="3"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Profit kyo gir gaya?"
          />
        </label>

        <label>
          Metric column for forecast
          <select value={metricColumn} onChange={(event) => setMetricColumn(event.target.value)}>
            <option value="">Auto detect</option>
            {availableColumns.map((column) => (
              <option key={column} value={column}>
                {column}
              </option>
            ))}
          </select>
        </label>

        <label>
          Date column for forecast
          <select value={dateColumn} onChange={(event) => setDateColumn(event.target.value)}>
            <option value="">Auto detect</option>
            {availableColumns.map((column) => (
              <option key={column} value={column}>
                {column}
              </option>
            ))}
          </select>
        </label>

        <label>
          Forecast horizon
          <input type="number" min="1" max="30" value={horizon} onChange={(event) => setHorizon(event.target.value)} />
        </label>
      </div>

      <div className="workflow-actions analytics-actions">
        <button type="button" onClick={handleAsk} disabled={loading || !rows.length}>
          Analyze Question
        </button>
        <button type="button" onClick={handleForecast} disabled={loading || !rows.length}>
          Forecast
        </button>
        <button type="button" onClick={handleCompare} disabled={loading || !rows.length || !baselineRows.length}>
          Compare Versions
        </button>
        <button type="button" onClick={() => handleDownloadReport('pdf')} disabled={loading || !result}>
          Download Report PDF
        </button>
        <button type="button" onClick={() => handleDownloadReport('pptx')} disabled={loading || !result}>
          Download Report PPT
        </button>
        <button type="button" onClick={() => setShowShareModal(true)} disabled={loading || !result}>
          Share Report
        </button>
        <button type="button" onClick={() => setShowSummary(true)} disabled={loading || !result}>
          Executive Summary
        </button>
        <button type="button" onClick={() => setShowScheduleModal(true)} disabled={loading || !result}>
          Schedule Export
        </button>
        <button type="button" className="secondary" onClick={handleSaveBaseline} disabled={loading || !rows.length}>
          Save Baseline Snapshot
        </button>
      </div>

      {baselineRows.length ? (
        <p className="workflow-status">
          Baseline snapshot saved with {baselineRows.length} row(s). Current vs baseline comparison is available.
        </p>
      ) : (
        <p className="workflow-status">Save a baseline snapshot if you want before/after comparison for future edits.</p>
      )}

      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <div className="analytics-result-stack">
          <div className="automl-widget-result">
            <p>
              <strong>Intent:</strong> {result.intent}
            </p>
            <p>
              <strong>Answer:</strong> {result.answer}
            </p>
          </div>

          {Array.isArray(result.recommendations) && result.recommendations.length ? (
            <div className="analysis-bullets">
              <h3>Recommendations</h3>
              <ul>
                {result.recommendations.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {trendData.length ? (
            <div className="chart-shell">
              <h3>Trend / Forecast</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendData} margin={{ top: 16, right: 16, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                  <XAxis dataKey="label" stroke="#334155" />
                  <YAxis stroke="#334155" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', color: '#f8fafc', borderRadius: '10px', border: 'none' }}
                    labelStyle={{ color: '#f8fafc' }}
                  />
                  <Line type="monotone" dataKey="value" stroke="#0ea5e9" strokeWidth={3} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : null}

          {reportSections.length ? (
            <div className="analytics-report-preview">
              <div className="audit-header">
                <h3>Report Preview</h3>
                <p>{safeText(result.report_title || 'Analytics Report')}</p>
              </div>
              <div className="workflow-list">
                {reportSections.slice(0, 4).map((section) => (
                  <div key={section.heading} className="workflow-card">
                    <strong>{section.heading}</strong>
                    <small>
                      {(section.rows || [])
                        .slice(0, 4)
                        .map((row) => `${row.label}: ${row.value}`)
                        .join(' | ')}
                    </small>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {showShareModal && (
        <ShareModal
          result={result}
          onClose={() => setShowShareModal(false)}
          onShareCreated={() => setShowShareModal(false)}
        />
      )}

      {showScheduleModal && <ScheduleExportModal onClose={() => setShowScheduleModal(false)} />}

      {showSummary && (
        <div className="modal-overlay" onClick={() => setShowSummary(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Executive Summary</h2>
              <button className="modal-close" onClick={() => setShowSummary(false)}>
                ×
              </button>
            </div>
            <div className="modal-body">
              <ExecutiveSummary analysis={analysis} result={result} />
            </div>
            <div className="modal-footer">
              <button type="button" onClick={() => setShowSummary(false)} className="btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}