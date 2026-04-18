import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import DataGrid from './components/DataGrid';
import DataInsightsChart from './components/DataInsightsChart';
import AutoMLWidget from './components/AutoMLWidget';
import DataCompareChart from './components/DataCompareChart';
import AIEngineWidget from './components/AIEngineWidget';
import { useAuth } from './context/AuthContext';

const API_BASE_URL = 'http://localhost:8000';

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const canAnalyze = user?.role === 'analyst' || user?.role === 'admin';

  const [activeTab, setActiveTab] = useState('overview');
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [domainData, setDomainData] = useState(null);
  const [rows, setRows] = useState([]);
  const [auditErrors, setAuditErrors] = useState([]);
  const [targetColumn, setTargetColumn] = useState('');
  const [automlResult, setAutomlResult] = useState(null);
  const [aiReport, setAiReport] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [backgroundTaskId, setBackgroundTaskId] = useState('');
  const [backgroundStatus, setBackgroundStatus] = useState('');
  const [backgroundProgress, setBackgroundProgress] = useState(null);
  const [isBackgroundRunning, setIsBackgroundRunning] = useState(false);
  const [compareChartData, setCompareChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const gridApiRef = useRef(null);

  useEffect(() => {
    if (!canAnalyze && activeTab !== 'overview') {
      setActiveTab('overview');
    }
  }, [canAnalyze, activeTab]);

  useEffect(() => {
    if (!backgroundTaskId || !isBackgroundRunning) {
      return undefined;
    }

    const poll = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/task-status/${backgroundTaskId}`);
        const payload = response.data;

        setBackgroundStatus(payload.status || payload.state || 'Processing...');
        if (typeof payload.progress === 'number') {
          setBackgroundProgress(payload.progress);
        }

        if (payload.state === 'SUCCESS') {
          setIsBackgroundRunning(false);
          setBackgroundProgress(100);

          const result = payload.result || {};
          setAnalysis((prev) => result.analysis || prev);
          setDomainData((prev) => result.analysis?.domain_info || prev);
          setRows((prev) => result.grid_data || result.sample_data || prev);
          setAuditErrors(result.analysis?.audit_errors || []);
          setCompareChartData(result.cleaning_stats || []);
        }

        if (payload.state === 'FAILURE' || payload.state === 'REVOKED') {
          setIsBackgroundRunning(false);
          setError(payload.status || 'Background task failed.');
        }
      } catch (pollError) {
        setIsBackgroundRunning(false);
        setError(pollError?.response?.data?.detail || 'Task status polling failed.');
      }
    };

    poll();
    const timer = window.setInterval(poll, 3000);

    return () => window.clearInterval(timer);
  }, [backgroundTaskId, isBackgroundRunning]);

  const columnDefs = useMemo(() => {
    if (!rows.length) {
      return [];
    }

    const semanticColumns = domainData?.columns || [];
    const semanticMap = semanticColumns.reduce((acc, column) => {
      if (column?.name) {
        acc[String(column.name).toLowerCase()] = column.semantic_type || '';
      }
      return acc;
    }, {});

    const semanticEmoji = (semanticType) => {
      const label = String(semanticType || '').toLowerCase();
      if (label.includes('price') || label.includes('currency') || label.includes('amount')) return 'money';
      if (label.includes('date') || label.includes('time')) return 'date';
      if (label.includes('email')) return 'email';
      if (label.includes('id')) return 'id';
      if (label.includes('name') || label.includes('product')) return 'name';
      if (label.includes('category') || label.includes('class')) return 'category';
      if (label.includes('quantity') || label.includes('count')) return 'count';
      return 'field';
    };

    return Object.keys(rows[0]).map((field) => ({
      field,
      headerName: semanticMap[field.toLowerCase()]
        ? `${field} (${semanticEmoji(semanticMap[field.toLowerCase()])}: ${semanticMap[field.toLowerCase()]})`
        : field,
      sortable: true,
      filter: true,
      resizable: true,
    }));
  }, [rows, domainData]);

  const targetOptions = useMemo(() => {
    return rows.length ? Object.keys(rows[0]) : [];
  }, [rows]);

  const chartData = useMemo(() => {
    if (!analysis?.null_counts?.length || !analysis?.column_info?.length) {
      return [];
    }

    const nullMap = analysis.null_counts[0] || {};
    const totalRows = Number(analysis.rows || 0);

    return analysis.column_info.map((columnName) => {
      const missing = Number(nullMap[columnName] || 0);
      return {
        columnName,
        missing,
        valid: Math.max(totalRows - missing, 0),
      };
    });
  }, [analysis]);

  const handleGridReady = (params) => {
    gridApiRef.current = params.api;
  };

  const handleJump = (row, col) => {
    const api = gridApiRef.current;
    if (!api || row === undefined || !col) {
      return;
    }

    api.ensureIndexVisible(row, 'middle');
    api.setFocusedCell(row, col);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please choose a CSV file first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysis(response.data.analysis);
      setDomainData(response.data.analysis?.domain_info || null);
      setRows(response.data.grid_data || response.data.sample_data || []);
      setAuditErrors(response.data.analysis?.audit_errors || []);
      setAutomlResult(null);
      setTargetColumn('');
      setAiReport('');
      setCompareChartData([]);
      setActiveTab('overview');
    } catch (uploadError) {
      setError(uploadError?.response?.data?.detail || 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleClean = async () => {
    if (!file) {
      setError('Please choose a CSV file first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/clean`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysis(response.data.analysis);
      setDomainData(response.data.analysis?.domain_info || domainData);
      setRows(response.data.grid_data || response.data.cleaned_data || response.data.sample_data || []);
      setAuditErrors(response.data.analysis?.audit_errors || []);
      setAutomlResult(null);
      setAiReport('');
      setCompareChartData(response.data.cleaning_stats || []);
      setActiveTab('cleaning');
    } catch (cleanError) {
      setError(cleanError?.response?.data?.detail || 'Cleaning failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleBackgroundClean = async () => {
    if (!file) {
      setError('Please choose a CSV file first.');
      return;
    }

    setLoading(true);
    setError('');
    setBackgroundStatus('Queueing task...');
    setBackgroundProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/api/clean-background`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setBackgroundTaskId(response.data.task_id);
      setIsBackgroundRunning(true);
      setActiveTab('cleaning');
    } catch (backgroundError) {
      setError(backgroundError?.response?.data?.detail || 'Failed to start background clean.');
      setBackgroundTaskId('');
      setIsBackgroundRunning(false);
      setBackgroundProgress(null);
    } finally {
      setLoading(false);
    }
  };

  const getAIInsights = async (summaryData) => {
    setAiLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/generate-insights`, {
        data_summary: summaryData,
      });
      setAiReport(response.data.insights || '');
    } catch (insightError) {
      setError(insightError?.response?.data?.detail || 'AI insight generation failed.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!rows.length) {
      setError('No data available to download.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/export-results`,
        {
          cleaned_data: rows,
          cleaning_stats: compareChartData,
          ml_results: automlResult,
        },
        {
          responseType: 'blob',
        }
      );

      const blob = new Blob([response.data], { type: 'application/zip' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'Analysis_Export.zip';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (downloadError) {
      setError(downloadError?.response?.data?.detail || 'Download failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="sidebar-logo">DataSaaS Pro</div>

        <div className="sidebar-user">
          <span>{user?.username || 'user'}</span>
          <small>Role: {user?.role || 'viewer'}</small>
          <button type="button" className="sidebar-logout" onClick={logout}>
            Logout
          </button>
        </div>

        <div className="sidebar-nav">
          <button
            type="button"
            className={activeTab === 'overview' ? 'sidebar-btn active' : 'sidebar-btn'}
            onClick={() => setActiveTab('overview')}
          >
            Data Workspace
          </button>

          {canAnalyze ? (
            <button
              type="button"
              className={activeTab === 'cleaning' ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setActiveTab('cleaning')}
            >
              Auto-Clean
            </button>
          ) : null}

          {canAnalyze ? (
            <button
              type="button"
              className={activeTab === 'predict' ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setActiveTab('predict')}
            >
              AI Predictions
            </button>
          ) : null}
        </div>

        <div className="sidebar-controls">
          <label className="input-label">CSV File</label>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            disabled={!canAnalyze}
          />

          <button type="button" onClick={handleUpload} disabled={loading || !canAnalyze}>
            {loading ? 'Analyzing...' : 'Upload and Analyze'}
          </button>
          <button type="button" onClick={handleClean} disabled={loading || !file || !canAnalyze}>
            Clean Data
          </button>
          <button
            type="button"
            onClick={handleBackgroundClean}
            disabled={loading || isBackgroundRunning || !file || !canAnalyze}
          >
            {isBackgroundRunning ? 'Background Cleaning...' : 'Clean in Background'}
          </button>

          <select
            value={targetColumn}
            onChange={(event) => setTargetColumn(event.target.value)}
            disabled={!targetOptions.length || loading || !canAnalyze}
          >
            <option value="">Select target column</option>
            {targetOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() =>
              getAIInsights({
                analysis,
                automl: automlResult,
                audit_count: auditErrors.length,
                row_count: rows.length,
                columns: analysis?.column_info || [],
              })
            }
            disabled={aiLoading || loading || !analysis}
          >
            {aiLoading ? 'Generating Insights...' : 'Generate Business Insights'}
          </button>
        </div>

        <div className="sidebar-bottom">
          <button type="button" className="export-btn" onClick={handleDownload} disabled={loading || !rows.length}>
            Export ZIP Report
          </button>
        </div>
      </aside>

      <section className="dashboard-main">
        <header className="dashboard-topbar">
          <h2>{activeTab === 'overview' ? 'Data Workspace' : activeTab === 'cleaning' ? 'Auto-Clean' : 'AI Predictions'}</h2>
          {domainData?.domain ? (
            <span className="domain-badge">
              Detected Domain: {domainData.domain} ({domainData.confidence || 0}% confidence)
            </span>
          ) : null}
        </header>

        <div className="dashboard-content">
          {error ? <p className="error">{error}</p> : null}

          {backgroundTaskId ? (
            <div className="task-status">
              <p>Task: {backgroundTaskId}</p>
              <p>Status: {backgroundStatus || 'Waiting...'}</p>
              {typeof backgroundProgress === 'number' ? (
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${backgroundProgress}%` }} />
                </div>
              ) : null}
            </div>
          ) : null}

          {domainData?.columns?.length ? (
            <div className="semantic-panel">
              <h3>Column Understanding</h3>
              <ul>
                {domainData.columns.map((column, index) => (
                  <li key={`${column.name}-${index}`}>
                    <strong>{column.name}</strong>: {column.semantic_type}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {activeTab === 'overview' ? (
            <>
              <div className="card audit-card">
                <div className="audit-header">
                  <h2>Data Audit Report</h2>
                  <p>{auditErrors.length} issue(s)</p>
                </div>
                {auditErrors.length ? (
                  <div className="audit-list">
                    {auditErrors.map((issue, index) => (
                      <button
                        key={`${issue.row}-${issue.col}-${index}`}
                        type="button"
                        className="error-card"
                        onClick={() => handleJump(issue.row, issue.col)}
                      >
                        <strong>Row {issue.row}</strong>
                        <span>{issue.issue}</span>
                        <small>{issue.col}</small>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p>No audit issues yet.</p>
                )}
              </div>

              <div className="card grid-card">
                <h2>Raw Data Workspace</h2>
                <DataGrid rowData={rows} columnDefs={columnDefs} onGridReady={handleGridReady} />
              </div>
            </>
          ) : null}

          {activeTab === 'cleaning' ? (
            <div className="card stats-card">
              <h2>Data Quality and Cleaning</h2>
              {analysis ? (
                <ul>
                  <li>Category: {analysis.category}</li>
                  <li>Rows: {analysis.rows}</li>
                  <li>Columns: {analysis.cols}</li>
                  <li>Column names: {analysis.column_info.join(', ')}</li>
                </ul>
              ) : (
                <p>No analysis yet. Upload a CSV to begin.</p>
              )}

              {chartData.length ? <DataInsightsChart data={chartData} /> : null}
              {compareChartData.length ? <DataCompareChart data={compareChartData} /> : null}
            </div>
          ) : null}

          {activeTab === 'predict' && canAnalyze ? (
            <div className="card stats-card">
              <h2>AI Prediction Workspace</h2>
              {automlResult ? (
                <div className="automl-panel">
                  <h3>AutoML Result</h3>
                  <p>{automlResult.message}</p>
                </div>
              ) : null}
              <AutoMLWidget file={file} targetColumn={targetColumn} rows={rows} onResult={setAutomlResult} />
              <AIEngineWidget rows={rows} availableColumns={targetOptions} onUpdateData={setRows} />
              {aiReport ? (
                <div className="automl-panel ai-insight-panel">
                  <h3>AI Data Conclusion</h3>
                  <p>{aiReport}</p>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
