import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import {
  LayoutDashboard, Wand2, MessageSquare, BarChart3,
  Search, ShieldCheck, Bot, GitBranch, ClipboardList,
  FileBarChart2, User, LogOut, Upload, Sparkles,
  Database, AlertCircle, ChevronRight, Bell, Sun, Moon, HelpCircle, Keyboard
} from 'lucide-react';
import DropZone from './components/DropZone';
import DataGrid from './components/DataGrid';
import AutoMLWidget from './components/AutoMLWidget';
import AIEngineWidget from './components/AIEngineWidget';
import WorkflowBuilder from './components/WorkflowBuilder';
import MultiGraphPanel from './components/MultiGraphPanel';
import AnalyticsWorkbench from './components/AnalyticsWorkbench';
import GraphGallery from './components/GraphGallery';
import SearchAndExport from './components/SearchAndExport';
import DataQualityDashboard from './components/DataQualityDashboard';
import AdminAuditLog from './AdminAuditLog';
import { useAuth } from './context/AuthContext';
import { API_BASE_URL } from './config';

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
  const [arrangingNotes, setArrangingNotes] = useState([]);
  const [baselineRows, setBaselineRows] = useState([]);
  const [catalogItems, setCatalogItems] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [activitySummary, setActivitySummary] = useState(null);
  const [activityLoading, setActivityLoading] = useState(false);
  const [dashboardSummary, setDashboardSummary] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [selectedGraphKeys, setSelectedGraphKeys] = useState(['quality', 'compare']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const gridApiRef = useRef(null);

  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);
  const [showOnboardingTour, setShowOnboardingTour] = useState(() => {
    return !localStorage.getItem('hasSeenTour');
  });
  const [tourStep, setTourStep] = useState(1);

  const [profileData, setProfileData] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [editFullName, setEditFullName] = useState('');
  const [editBio, setEditBio] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [uploadedAvatar, setUploadedAvatar] = useState(null);
  const fileInputRef = useRef(null);

  const loadCatalog = async () => {
    setCatalogLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/catalog?limit=8`);
      setCatalogItems(response.data.items || []);
    } catch (catalogError) {
      setCatalogItems([]);
    } finally {
      setCatalogLoading(false);
    }
  };

  const loadActivitySummary = async () => {
    setActivityLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/activity/summary?days=30&recent_limit=12`);
      setActivitySummary(response.data || null);
    } catch (activityError) {
      setActivitySummary(null);
    } finally {
      setActivityLoading(false);
    }
  };

  const loadDashboardSummary = async () => {
    setDashboardLoading(true);
    setCatalogLoading(true);
    setActivityLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/dashboard/summary?days=30&recent_limit=12&catalog_limit=24`);
      const payload = response.data || null;
      setDashboardSummary(payload);
      setActivitySummary(payload?.activity || null);
      setCatalogItems(payload?.recent_runs || []);
    } catch (summaryError) {
      setDashboardSummary(null);
      await Promise.all([loadCatalog(), loadActivitySummary()]);
    } finally {
      setDashboardLoading(false);
      setCatalogLoading(false);
      setActivityLoading(false);
    }
  };

  const loadProfile = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/auth/profile`);
      const data = response.data;
      setProfileData(data);
      setEditFullName(data.full_name || '');
      setEditBio(data.bio || '');
      setEditPhone(data.phone || '');
      setEditLocation(data.location || '');
      setUploadedAvatar(data.avatar_url || null);
    } catch (profileError) {
      // Not created yet or fallback
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        full_name: editFullName,
        bio: editBio,
        phone: editPhone,
        location: editLocation,
        avatar_url: uploadedAvatar
      };
      const response = await axios.put(`${API_BASE_URL}/api/auth/profile`, payload);
      setProfileData(response.data);
      setShowProfileModal(false);
    } catch (saveError) {
      setError(saveError?.response?.data?.detail || "Failed to save profile.");
    }
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 1024 * 1024) {
      alert("Image size should be less than 1MB");
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setUploadedAvatar(reader.result);
    };
    reader.readAsDataURL(file);
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const dismissTour = () => {
    setShowOnboardingTour(false);
    localStorage.setItem('hasSeenTour', 'true');
  };

  const getBreadcrumbs = () => {
    const base = 'Console';
    let path = [];
    switch (activeTab) {
      case 'overview':
        path = ['Workspace', 'Data Workspace'];
        break;
      case 'cleaning':
        path = ['Analytics', 'Auto-Clean'];
        break;
      case 'insights':
        path = ['Insights', 'Ask & Report'];
        break;
      case 'graphs':
        path = ['Visuals', 'Graph Gallery'];
        break;
      case 'search':
        path = ['Tools', 'Search & Export'];
        break;
      case 'quality':
        path = ['Security', 'Data Quality'];
        break;
      case 'predict':
        path = ['Intelligence', 'AI Predictions'];
        break;
      case 'workflow':
        path = ['Workflows', 'Builder'];
        break;
      case 'audit-log':
        path = ['Admin', 'Audit Log'];
        break;
      default:
        path = ['Workspace'];
    }
    return [base, ...path];
  };

  useEffect(() => {
    let keyBuffer = '';
    let bufferTimeout;

    const handleKeyDown = (event) => {
      const activeEl = document.activeElement;
      if (
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.tagName === 'SELECT' ||
          activeEl.isContentEditable)
      ) {
        return;
      }

      if (event.key === 'Escape') {
        setShowShortcutsModal(false);
        setShowUserDropdown(false);
        return;
      }

      if (event.key === '?' || event.key === '/') {
        if (event.key === '?' || (event.key === '/' && event.shiftKey)) {
          event.preventDefault();
          setShowShortcutsModal((prev) => !prev);
          return;
        }
      }

      keyBuffer += event.key.toLowerCase();
      clearTimeout(bufferTimeout);
      bufferTimeout = setTimeout(() => {
        keyBuffer = '';
      }, 1000);

      if (keyBuffer === 'go') {
        setActiveTab('overview');
        keyBuffer = '';
      } else if (keyBuffer === 'gc') {
        if (canAnalyze) setActiveTab('cleaning');
        keyBuffer = '';
      } else if (keyBuffer === 'gr') {
        setActiveTab('insights');
        keyBuffer = '';
      } else if (keyBuffer === 'gg') {
        setActiveTab('graphs');
        keyBuffer = '';
      } else if (keyBuffer === 'gs') {
        setActiveTab('search');
        keyBuffer = '';
      } else if (keyBuffer === 'gq') {
        setActiveTab('quality');
        keyBuffer = '';
      } else if (keyBuffer === 'gp') {
        if (canAnalyze) setActiveTab('predict');
        keyBuffer = '';
      } else if (keyBuffer === 'gw') {
        if (canAnalyze) setActiveTab('workflow');
        keyBuffer = '';
      } else if (keyBuffer === 'gl') {
        if (user?.role === 'admin') setActiveTab('audit-log');
        keyBuffer = '';
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      clearTimeout(bufferTimeout);
    };
  }, [canAnalyze, user?.role]);

  useEffect(() => {
    if (!canAnalyze && activeTab !== 'overview') {
      setActiveTab('overview');
    }
  }, [canAnalyze, activeTab]);

  useEffect(() => {
    loadDashboardSummary();
    loadProfile();
  }, []);

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
          setArrangingNotes([]);
          loadDashboardSummary();
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

  const workspaceMetrics = useMemo(
    () => [
      {
        label: 'Rows loaded',
        value: Number(rows.length || dashboardSummary?.workspace?.rows_loaded || 0).toLocaleString(),
        hint: 'Current workspace dataset size',
      },
      {
        label: 'Columns',
        value: Number(analysis?.cols || dashboardSummary?.workspace?.columns || 0).toLocaleString(),
        hint: 'Detected schema fields',
      },
      {
        label: 'Audit issues',
        value: Number(auditErrors.length || dashboardSummary?.workspace?.audit_issues || 0).toLocaleString(),
        hint: 'Cells that need attention',
      },
      {
        label: 'Saved runs',
        value: Number(dashboardSummary?.workspace?.saved_runs || catalogItems.length || 0).toLocaleString(),
        hint: 'Recent lineage entries',
      },
    ],
    [rows.length, analysis?.cols, auditErrors.length, catalogItems.length, dashboardSummary]
  );

  const activeTitle =
    activeTab === 'overview'
      ? 'Data Workspace'
      : activeTab === 'cleaning'
        ? 'Auto-Clean'
        : activeTab === 'graphs'
          ? 'Graph Gallery'
        : activeTab === 'insights'
          ? 'Ask & Report'
        : activeTab === 'predict'
          ? 'AI Predictions'
          : activeTab === 'audit-log'
            ? 'Audit Log'
            : 'Workflow Builder';

  const activeSubtitle =
    activeTab === 'overview'
      ? 'Inspect the dataset, jump to issues, and review lineage from a single control surface.'
      : activeTab === 'cleaning'
        ? 'Clean data with background progress, compare quality before and after, and stay audit-ready.'
        : activeTab === 'graphs'
          ? 'Explore all major chart types and auto-activated visualizations based on analyzed dataset structure.'
        : activeTab === 'insights'
          ? 'Ask natural-language questions, forecast outcomes, compare versions, and export reports.'
        : activeTab === 'predict'
          ? 'Run AutoML, generate explainability, and produce a business-friendly data narrative.'
          : activeTab === 'audit-log'
            ? 'Track all authentication and authorization events for compliance and security.'
            : 'Compose reusable no-code pipelines for profile, clean, model, and explain workflows.';

  const activityCards = useMemo(() => {
    const currentUser = activitySummary?.current_user || {};
    return [
      {
        label: 'Total actions',
        value: Number(currentUser.total_requests || 0).toLocaleString(),
        hint: 'API operations completed in last 30 days',
      },
      {
        label: 'Work score',
        value: Number(currentUser.work_units || 0).toLocaleString(),
        hint: 'Weighted output score across tasks',
      },
      {
        label: 'Successful',
        value: Number(currentUser.successful_requests || 0).toLocaleString(),
        hint: 'Requests completed without error',
      },
      {
        label: 'Last activity',
        value: currentUser.last_activity_at ? new Date(currentUser.last_activity_at).toLocaleString() : 'No activity yet',
        hint: 'Most recent task timestamp',
      },
    ];
  }, [activitySummary]);

  const roleBreakdown = useMemo(() => activitySummary?.roles || [], [activitySummary]);
  const topUsers = useMemo(() => (activitySummary?.users || []).slice(0, 6), [activitySummary]);
  const recentActivity = useMemo(() => activitySummary?.recent || [], [activitySummary]);

  const dataHealthScore = useMemo(() => {
    if (typeof dashboardSummary?.data_quality?.score === 'number') {
      return dashboardSummary.data_quality.score;
    }
    if (!rows.length) {
      return 0;
    }
    const penalty = Math.min(70, auditErrors.length * 5);
    const score = Math.max(25, 100 - penalty);
    return score;
  }, [rows.length, auditErrors.length, dashboardSummary]);

  const processingHistory = useMemo(() => {
    const daily = dashboardSummary?.processing_history || activitySummary?.daily || [];
    const windowDays = daily.slice(-7);
    const maxWork = Math.max(1, ...windowDays.map((entry) => Number(entry.work_units || 0)));
    return windowDays.map((entry) => ({
      date: entry.date,
      workUnits: Number(entry.work_units || 0),
      height: Math.max(12, Math.round((Number(entry.work_units || 0) / maxWork) * 100)),
    }));
  }, [activitySummary, dashboardSummary]);

  const visibleAuditErrors = useMemo(() => {
    if (auditErrors.length) {
      return auditErrors;
    }
    return dashboardSummary?.audit_report || [];
  }, [auditErrors, dashboardSummary]);

  const overviewRowCount = Number(rows.length || dashboardSummary?.workspace?.rows_loaded || 0);

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
      setError('Please choose a dataset file first.');
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
      const uploadedRows = response.data.grid_data || response.data.sample_data || [];
      setRows(uploadedRows);
      setBaselineRows(uploadedRows);
      setAuditErrors(response.data.analysis?.audit_errors || []);
      setAutomlResult(null);
      setTargetColumn('');
      setAiReport('');
      setCompareChartData([]);
      setArrangingNotes([]);
      setActiveTab('overview');
      loadDashboardSummary();
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
      setArrangingNotes([]);
      setActiveTab('cleaning');
      loadDashboardSummary();
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

  const handleArrange = async () => {
    if (!file) {
      setError('Please choose a dataset file first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/arrange`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysis(response.data.analysis);
      setDomainData(response.data.analysis?.domain_info || domainData);
      setRows(response.data.grid_data || response.data.arranged_data || response.data.sample_data || []);
      setAuditErrors(response.data.analysis?.audit_errors || []);
      setCompareChartData(response.data.cleaning_stats || []);
      setArrangingNotes(response.data.arranging_notes || []);
      setActiveTab('cleaning');
      loadDashboardSummary();
    } catch (arrangeError) {
      setError(arrangeError?.response?.data?.detail || 'Arrange data failed.');
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

  const safeText = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    };
    return map[char] || char;
  });

  const printReport = ({ title, subtitle, sections }) => {
    const popup = window.open('', '_blank', 'width=1100,height=900');
    if (!popup) {
      setError('Please allow popups to print the report.');
      return;
    }

    const sectionHtml = sections
      .map((section) => {
        const rowsHtml = (section.rows || [])
          .map(
            (row) =>
              `<tr><td>${safeText(row.label)}</td><td>${safeText(row.value)}</td></tr>`
          )
          .join('');
        return `
          <section class="report-card">
            <h2>${safeText(section.heading)}</h2>
            <table>
              <tbody>
                ${rowsHtml}
              </tbody>
            </table>
          </section>
        `;
      })
      .join('');

    popup.document.write(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>${safeText(title)}</title>
          <style>
            body { font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #0f172a; }
            h1 { margin: 0 0 4px; }
            .subtitle { margin: 0 0 18px; color: #475569; }
            .report-card { border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; margin-bottom: 12px; }
            h2 { margin: 0 0 10px; font-size: 18px; }
            table { width: 100%; border-collapse: collapse; }
            td { border-top: 1px solid #e2e8f0; padding: 7px 8px; font-size: 14px; vertical-align: top; }
            td:first-child { width: 34%; font-weight: 700; color: #1e293b; }
          </style>
        </head>
        <body>
          <h1>${safeText(title)}</h1>
          <p class="subtitle">${safeText(subtitle)}</p>
          ${sectionHtml}
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    window.setTimeout(() => {
      popup.print();
      popup.close();
    }, 250);
  };

  const handlePrintOverviewReport = () => {
    const topActions = (activitySummary?.current_user?.top_actions || [])
      .map((actionPair) => `${actionPair[0]} (${actionPair[1]})`)
      .join(', ') || 'No recent actions';

    printReport({
      title: 'Workspace Summary Report',
      subtitle: `Generated on ${new Date().toLocaleString()}`,
      sections: [
        {
          heading: 'Dataset Identification',
          rows: [
            { label: 'Detected Category', value: analysis?.category || 'Unknown' },
            { label: 'Detected Domain', value: domainData?.domain || 'Unknown' },
            { label: 'Rows', value: analysis?.rows || rows.length || 0 },
            { label: 'Columns', value: analysis?.cols || 0 },
            { label: 'Column Names', value: (analysis?.column_info || []).join(', ') || 'N/A' },
          ],
        },
        {
          heading: 'Quality and Audit',
          rows: [
            { label: 'Data Health Score', value: `${dataHealthScore}%` },
            { label: 'Total Audit Issues', value: visibleAuditErrors.length },
            {
              label: 'Issue Locations (Row/Column)',
              value:
                visibleAuditErrors.slice(0, 20).map((issue) => `Row ${issue.row}, ${issue.col}`).join(' | ') || 'No issues',
            },
            { label: 'Saved Runs', value: catalogItems.length },
          ],
        },
        {
          heading: 'Activity and Conclusion',
          rows: [
            { label: 'Total Actions (30 Days)', value: activitySummary?.current_user?.total_requests || 0 },
            { label: 'Successful Requests', value: activitySummary?.current_user?.successful_requests || 0 },
            { label: 'Top Actions', value: topActions },
            {
              label: 'Conclusion',
              value:
                visibleAuditErrors.length > 0
                  ? 'Dataset is usable, but quality issues should be cleaned before advanced modeling.'
                  : 'Dataset quality looks healthy and ready for EDA, predictive analytics, and reporting.',
            },
          ],
        },
      ],
    });
  };

  const handlePrintCleaningReport = () => {
    const cleaningRows = compareChartData.length
      ? compareChartData.slice(0, 24).map((item) => `${item.columnName}: ${item.missingBefore} -> ${item.missingAfter}`)
      : ['No cleaning delta available yet'];

    printReport({
      title: 'Data Cleaning Report',
      subtitle: `Generated on ${new Date().toLocaleString()}`,
      sections: [
        {
          heading: 'Cleaning Summary',
          rows: [
            { label: 'Rows', value: analysis?.rows || rows.length || 0 },
            { label: 'Columns', value: analysis?.cols || 0 },
            { label: 'Audit Issues Remaining', value: visibleAuditErrors.length },
            { label: 'Columns Updated', value: compareChartData.length },
          ],
        },
        {
          heading: 'Missing and Duplicate Resolution',
          rows: [
            { label: 'Before -> After By Column', value: cleaningRows.join(' | ') },
            { label: 'Arrange Notes', value: arrangingNotes.join(' | ') || 'No arrange action executed' },
            {
              label: 'Duplicate/Missing Coordinates',
              value:
                visibleAuditErrors.slice(0, 20).map((issue) => `Row ${issue.row}, ${issue.col}`).join(' | ') || 'No issue coordinates',
            },
          ],
        },
      ],
    });
  };

  const handlePrintEDAReport = () => {
    const nullCounts = analysis?.null_counts?.[0] || {};
    const nullLines = Object.entries(nullCounts)
      .map(([column, value]) => `${column}: ${value}`)
      .join(' | ') || 'No null-count data available';

    printReport({
      title: 'EDA Report',
      subtitle: `Generated on ${new Date().toLocaleString()}`,
      sections: [
        {
          heading: 'Structure and Types',
          rows: [
            { label: 'Category', value: analysis?.category || 'Unknown' },
            { label: 'Rows', value: analysis?.rows || rows.length || 0 },
            { label: 'Columns', value: analysis?.cols || 0 },
            { label: 'Columns List', value: (analysis?.column_info || []).join(', ') || 'N/A' },
          ],
        },
        {
          heading: 'Data Quality Statistics',
          rows: [
            { label: 'Null Counts', value: nullLines },
            { label: 'Total Audit Issues', value: visibleAuditErrors.length },
            {
              label: 'Issue Coordinates',
              value:
                visibleAuditErrors.slice(0, 24).map((issue) => `Row ${issue.row}, ${issue.col}`).join(' | ') || 'No issue coordinates',
            },
          ],
        },
      ],
    });
  };

  const handlePrintPredictionReport = () => {
    printReport({
      title: 'Predictive Analytics Report',
      subtitle: `Generated on ${new Date().toLocaleString()}`,
      sections: [
        {
          heading: 'Modeling Inputs',
          rows: [
            { label: 'Target Column', value: targetColumn || 'Not selected' },
            { label: 'Rows Used', value: rows.length || 0 },
            { label: 'Columns Used', value: targetOptions.length || 0 },
          ],
        },
        {
          heading: 'Prediction Outputs',
          rows: [
            { label: 'AutoML Message', value: automlResult?.message || 'No AutoML output yet' },
            {
              label: 'Model Details',
              value: automlResult ? JSON.stringify(automlResult) : 'N/A',
            },
            {
              label: 'Business Insight',
              value: aiReport || 'No business insight generated yet',
            },
          ],
        },
      ],
    });
  };

  const handlePrintWorkflowReport = () => {
    const latestWorkflowRuns = catalogItems.filter((item) => item.action === 'workflow').slice(0, 6);
    printReport({
      title: 'Workflow Report',
      subtitle: `Generated on ${new Date().toLocaleString()}`,
      sections: [
        {
          heading: 'Workflow Activity',
          rows: [
            { label: 'Total Saved Workflows/Runs', value: latestWorkflowRuns.length },
            {
              label: 'Recent Workflow Runs',
              value:
                latestWorkflowRuns
                  .map((item) => `${item.dataset_name || 'Workflow'} (${item.created_at || 'N/A'})`)
                  .join(' | ') || 'No workflow run found',
            },
          ],
        },
      ],
    });
  };

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="sidebar-logo">
          <Database className="sidebar-logo-icon" />
          <strong>DataSaaS Pro</strong>
        </div>

        <div className="sidebar-user" onClick={() => setShowUserDropdown((prev) => !prev)} style={{ cursor: 'pointer', position: 'relative' }}>
          <div className="sidebar-avatar" style={{ overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {profileData?.avatar_url ? (
              <img src={profileData.avatar_url} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <span>{(profileData?.full_name || user?.username || 'U')[0].toUpperCase()}</span>
            )}
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-username">{profileData?.full_name || user?.username || 'user'}</span>
            <span className={`role-badge role-badge--${user?.role || 'viewer'}`}>{user?.role || 'viewer'}</span>
          </div>
          <button type="button" className="sidebar-logout" onClick={(e) => { e.stopPropagation(); logout(); }} aria-label="Logout" title="Logout">
            <LogOut className="w-4 h-4" />
          </button>

          {showUserDropdown && (
            <div className="user-dropdown-panel glass-effect" onClick={(e) => e.stopPropagation()}>
              <div className="user-dropdown-header">
                <strong>{profileData?.full_name || user?.username}</strong>
                <span className="user-dropdown-email">{user?.email || 'No email registered'}</span>
              </div>
              <div className="user-dropdown-divider" />
              <div className="user-dropdown-item" onClick={() => { setShowProfileModal(true); setShowUserDropdown(false); }}>
                <span>Edit Profile</span>
              </div>
              <div className="user-dropdown-item theme-switch-row" onClick={toggleTheme} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Theme</span>
                <span style={{ fontSize: '0.8rem', opacity: 0.8, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {theme === 'dark' ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
                  {theme === 'dark' ? 'Dark' : 'Light'}
                </span>
              </div>
              <div className="user-dropdown-item" onClick={() => { setShowShortcutsModal(true); setShowUserDropdown(false); }} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Shortcuts</span>
                <kbd style={{ background: 'var(--line-strong)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem' }}>?</kbd>
              </div>
              <div className="user-dropdown-item" onClick={() => { setShowOnboardingTour(true); setTourStep(1); setShowUserDropdown(false); }}>
                <span>Quick Tour</span>
              </div>
              <div className="user-dropdown-divider" />
              <button type="button" className="user-dropdown-logout-btn" onClick={logout} style={{ width: '100%', background: 'transparent', border: 'none', color: '#ef4444', textAlign: 'left', padding: '6px 8px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <LogOut className="w-3.5 h-3.5" />
                Log Out
              </button>
            </div>
          )}
        </div>

        <div className="sidebar-nav">
          <button
            type="button"
            aria-current={activeTab === 'overview' ? 'page' : undefined}
            aria-label="Data Workspace"
            className={activeTab === 'overview' ? 'sidebar-btn active' : 'sidebar-btn'}
            onClick={() => setActiveTab('overview')}
          >
            <span className="nav-item-content">
              <LayoutDashboard className="nav-icon-svg" />
              Data Workspace
            </span>
          </button>

          {canAnalyze ? (
            <button
              type="button"
              aria-current={activeTab === 'cleaning' ? 'page' : undefined}
              aria-label="Auto-Clean"
              className={activeTab === 'cleaning' ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setActiveTab('cleaning')}
            >
              <span className="nav-item-content">
                <Wand2 className="nav-icon-svg" />
                Auto-Clean
              </span>
            </button>
          ) : null}

          <button
            type="button"
            aria-current={activeTab === 'insights' ? 'page' : undefined}
            aria-label="Ask & Report"
            className={activeTab === 'insights' ? 'sidebar-btn active' : 'sidebar-btn'}
            onClick={() => setActiveTab('insights')}
          >
            <span className="nav-item-content">
              <MessageSquare className="nav-icon-svg" />
              Ask & Report
            </span>
          </button>

          <button
            type="button"
            aria-current={activeTab === 'graphs' ? 'page' : undefined}
            aria-label="Graph Gallery"
            className={activeTab === 'graphs' ? 'sidebar-btn active' : 'sidebar-btn'}
            onClick={() => setActiveTab('graphs')}
          >
            <span className="nav-item-content">
              <BarChart3 className="nav-icon-svg" />
              Graph Gallery
            </span>
          </button>

          <button
            type="button"
            aria-current={activeTab === 'search' ? 'page' : undefined}
            aria-label="Search & Export"
            className={activeTab === 'search' ? 'sidebar-btn active' : 'sidebar-btn'}
            onClick={() => setActiveTab('search')}
          >
            <span className="nav-item-content">
              <Search className="nav-icon-svg" />
              Search & Export
            </span>
          </button>

          <button
            type="button"
            aria-current={activeTab === 'quality' ? 'page' : undefined}
            aria-label="Data Quality"
            className={activeTab === 'quality' ? 'sidebar-btn active' : 'sidebar-btn'}
            onClick={() => setActiveTab('quality')}
          >
            <span className="nav-item-content">
              <ShieldCheck className="nav-icon-svg" />
              Data Quality
            </span>
          </button>

          {canAnalyze ? (
            <button
              type="button"
              aria-current={activeTab === 'predict' ? 'page' : undefined}
              aria-label="AI Predictions"
              className={activeTab === 'predict' ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setActiveTab('predict')}
            >
              <span className="nav-item-content">
                <Bot className="nav-icon-svg" />
                AI Predictions
              </span>
            </button>
          ) : null}

          {canAnalyze ? (
            <button
              type="button"
              aria-current={activeTab === 'workflow' ? 'page' : undefined}
              aria-label="Workflow Builder"
              className={activeTab === 'workflow' ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setActiveTab('workflow')}
            >
              <span className="nav-item-content">
                <GitBranch className="nav-icon-svg" />
                Workflow Builder
              </span>
            </button>
          ) : null}

          {user?.role === 'admin' ? (
            <button
              type="button"
              aria-current={activeTab === 'audit-log' ? 'page' : undefined}
              aria-label="Audit Log"
              className={activeTab === 'audit-log' ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setActiveTab('audit-log')}
            >
              <span className="nav-item-content">
                <ClipboardList className="nav-icon-svg" />
                Audit Log
              </span>
            </button>
          ) : null}
        </div>

        <div className="sidebar-controls">
          <label className="input-label">Dataset File</label>
          <DropZone onFile={setFile} file={file} disabled={!canAnalyze || loading} />

          <button type="button" className="btn btn-primary btn-sm sidebar-action-btn" onClick={handleUpload} disabled={!canAnalyze || loading}>
            <Upload className="w-3.5 h-3.5" />
            {loading ? 'Analyzing...' : 'Upload & Analyze'}
          </button>
          <button type="button" className="btn btn-secondary btn-sm sidebar-action-btn" onClick={handleClean} disabled={loading || !file || !canAnalyze}>
            <Wand2 className="w-3.5 h-3.5" />
            Clean Data
          </button>
          <button type="button" className="btn btn-secondary btn-sm sidebar-action-btn" onClick={handleArrange} disabled={loading || !file || !canAnalyze}>
            <GitBranch className="w-3.5 h-3.5" />
            Arrange Data
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm sidebar-action-btn"
            onClick={handleBackgroundClean}
            disabled={loading || isBackgroundRunning || !file || !canAnalyze}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {isBackgroundRunning ? 'Running...' : 'BG Clean'}
          </button>

          <select
            value={targetColumn}
            onChange={(event) => setTargetColumn(event.target.value)}
            disabled={!targetOptions.length || loading || !canAnalyze}
            aria-label="Target column for predictions"
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
            className="btn btn-ghost btn-sm sidebar-action-btn"
            onClick={() =>
              getAIInsights({
                analysis,
                automl: automlResult,
                audit_count: visibleAuditErrors.length,
                row_count: rows.length,
                columns: analysis?.column_info || [],
              })
            }
            disabled={aiLoading || loading || !analysis}
          >
            <Bot className="w-3.5 h-3.5" />
            {aiLoading ? 'Generating...' : 'AI Insights'}
          </button>

          {!canAnalyze ? <p className="sidebar-note">Viewer role has read-only access.</p> : null}
        </div>

        <div className="sidebar-bottom">
          <button type="button" className="export-btn" onClick={handleDownload} disabled={loading || !rows.length}>
            Export ZIP Report
          </button>
        </div>
      </aside>

      <section className="dashboard-main">
        <header className="dashboard-topbar">
          <div className="topbar-copy">
            <div className="topbar-breadcrumbs" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
              {getBreadcrumbs().map((crumb, idx) => (
                <React.Fragment key={crumb}>
                  {idx > 0 && <span style={{ opacity: 0.5 }}>/</span>}
                  <span style={{ color: idx === getBreadcrumbs().length - 1 ? 'var(--topbar-eyebrow, #0369a1)' : 'inherit' }}>
                    {crumb}
                  </span>
                </React.Fragment>
              ))}
            </div>
            <h2>{activeTitle}</h2>
            <p>{activeSubtitle}</p>
          </div>

          <div className="topbar-status">
            <button
              type="button"
              aria-label="Quick Tour"
              title="Quick Tour"
              onClick={() => { setShowOnboardingTour(true); setTourStep(1); }}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px', borderRadius: '8px', display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-main)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
            >
              <HelpCircle className="w-5 h-5" />
            </button>
            <button
              type="button"
              aria-label="Notifications"
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px', borderRadius: '8px', display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-main)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
            >
              <Bell className="w-5 h-5" />
            </button>
            <span className="topbar-role">{user?.role || 'viewer'}</span>
            {domainData?.domain ? (
              <span className="domain-badge">
                {domainData.domain} · {domainData.confidence || 0}% confidence
              </span>
            ) : null}
          </div>
        </header>

        <div className="dashboard-content">
          {showOnboardingTour ? (
            <div className="onboarding-tour-banner glass-effect" style={{ gridColumn: '1 / -1', padding: '20px', borderRadius: '16px', border: '1px solid var(--accent-cyan)', background: 'rgba(14, 165, 233, 0.08)', animation: 'fadeIn 0.3s ease-out', marginBottom: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span className="role-badge role-badge--analyst" style={{ margin: 0 }}>Step {tourStep} of 4</span>
                <button type="button" onClick={dismissTour} style={{ background: 'none', border: 'none', fontSize: '1.25rem', color: 'var(--text-soft)', cursor: 'pointer' }} aria-label="Skip tour">×</button>
              </div>
              <h4 style={{ margin: '0 0 8px 0', fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                {tourStep === 1 && "👋 Welcome to DataSaaS Pro!"}
                {tourStep === 2 && "📁 1. Upload Your Dataset"}
                {tourStep === 3 && "🧹 2. Clean & Profile Data"}
                {tourStep === 4 && "🤖 3. AI Insights & AutoML Predictions"}
              </h4>
              <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', color: 'var(--text-soft)', lineHeight: 1.6 }}>
                {tourStep === 1 && "This is your unified data engineering and AI workspace. Let's do a quick 30-second walkthrough to get you familiarized with all the features."}
                {tourStep === 2 && "Start by dragging & dropping your CSV, Excel, JSON, or Parquet file into the sidebar drop zone, then click 'Upload & Analyze' to run baseline profiling."}
                {tourStep === 3 && "Click 'Clean Data' or 'Arrange Data' to fix outliers and formats. You can inspect specific structural and value errors in the 'Data Quality' tab."}
                {tourStep === 4 && "Choose a target column in the sidebar and run predictive model inference, or click 'AI Insights' to ask natural language questions about your data."}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button type="button" className="btn btn-ghost btn-sm" onClick={dismissTour} style={{ padding: '4px 8px' }}>Skip Tour</button>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {tourStep > 1 && (
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setTourStep((p) => p - 1)} style={{ padding: '6px 12px' }}>Back</button>
                  )}
                  {tourStep < 4 ? (
                    <button type="button" className="btn btn-primary btn-sm" onClick={() => setTourStep((p) => p + 1)} style={{ padding: '6px 12px' }}>Next</button>
                  ) : (
                    <button type="button" className="btn btn-primary btn-sm" onClick={dismissTour} style={{ padding: '6px 12px' }}>Finish</button>
                  )}
                </div>
              </div>
            </div>
          ) : null}
          <section className="workspace-hero">
            <div className="workspace-hero-copy">
              <span className="workspace-kicker">Fast, no-code analytics for admins and analysts</span>
              <h3>Operate data, quality, and ML from one workspace.</h3>
              <p>
                Upload a file, inspect it instantly, clean issues, run predictions, and export results without leaving the console.
              </p>
            </div>

            <div className="workspace-metrics">
              {workspaceMetrics.map((metric) => (
                <article key={metric.label} className="metric-card">
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.hint}</small>
                </article>
              ))}
            </div>
          </section>

          {error ? (
            <div role="alert" className="error-banner" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', marginBottom: '16px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', color: '#fca5a5', fontSize: '0.875rem' }}>
              <AlertCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#ef4444' }} />
              <span>{error}</span>
              <button type="button" onClick={() => setError('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', padding: '0 4px', fontSize: '1.25rem', lineHeight: '1' }} aria-label="Dismiss error">×</button>
            </div>
          ) : null}

          {dashboardLoading && !rows.length ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="skeleton-pulse" style={{ height: '100px' }} />
              ))}
            </div>
          ) : null}

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
              <div className="card workspace-overview-card">
                <div className="audit-header">
                  <h2>Workspace Overview</h2>
                  <p>{overviewRowCount ? `${overviewRowCount.toLocaleString()} rows loaded` : 'No dataset loaded'}</p>
                </div>
                <div className="section-actions">
                  <button type="button" className="section-print-btn" onClick={handlePrintOverviewReport}>
                    Print Workspace Report
                  </button>
                </div>

                <div className="workspace-overview-grid">
                  <div className="overview-panel">
                    <h3>Data Health Score</h3>
                    <div className="health-meter-wrap">
                      <div className="health-meter-track">
                        <div className="health-meter-fill" style={{ width: `${dataHealthScore}%` }} />
                      </div>
                      <div className="health-meter-value">
                        <strong>{dataHealthScore}%</strong>
                        <small>Overall Health</small>
                      </div>
                    </div>
                  </div>

                  <div className="overview-panel">
                    <h3>Processing History</h3>
                    {processingHistory.length ? (
                      <div className="processing-bars">
                        {processingHistory.map((item) => (
                          <div key={item.date} className="processing-bar-item">
                            <div className="processing-bar-value">{item.workUnits}</div>
                            <div className="processing-bar-column">
                              <div className="processing-bar-fill" style={{ height: `${item.height}%` }} />
                            </div>
                            <small>{new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</small>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>No processing history yet.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="card activity-card">
                <div className="audit-header">
                  <h2>Work Activity Dashboard</h2>
                  <p>{activityLoading || dashboardLoading ? 'Refreshing...' : `${activitySummary?.scope === 'all_users' ? 'All users' : 'My activity'} · 30 days`}</p>
                </div>

                <div className="activity-metrics">
                  {activityCards.map((metric) => (
                    <article key={metric.label} className="activity-metric-item">
                      <span>{metric.label}</span>
                      <strong>{metric.value}</strong>
                      <small>{metric.hint}</small>
                    </article>
                  ))}
                </div>

                <div className="activity-grid">
                  <div className="activity-block">
                    <h3>Recent Work</h3>
                    {recentActivity.length ? (
                      <div className="activity-list">
                        {recentActivity.slice(0, 8).map((entry) => (
                          <div key={entry.id} className="activity-item">
                            <strong>{entry.username}</strong>
                            <span>{entry.action} · {entry.method}</span>
                            <small>{new Date(entry.timestamp).toLocaleString()}</small>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>No tracked activity yet.</p>
                    )}
                  </div>

                  <div className="activity-block">
                    <h3>Role Productivity</h3>
                    {roleBreakdown.length ? (
                      <div className="activity-list">
                        {roleBreakdown.map((role) => (
                          <div key={role.role} className="activity-item">
                            <strong>{role.role}</strong>
                            <span>{role.work_units} work score · {role.total_requests} actions</span>
                            <small>{role.last_activity_at ? new Date(role.last_activity_at).toLocaleString() : 'No recent activity'}</small>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>No role activity available.</p>
                    )}
                  </div>

                  {user?.role === 'admin' ? (
                    <div className="activity-block">
                      <h3>Top Contributors</h3>
                      {topUsers.length ? (
                        <div className="activity-list">
                          {topUsers.map((member) => (
                            <div key={member.username} className="activity-item">
                              <strong>{member.username}</strong>
                              <span>{member.role} · {member.work_units} work score</span>
                              <small>{member.total_requests} actions · {member.successful_requests} successful</small>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p>No user activity available.</p>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="card audit-card">
                <div className="audit-header">
                  <h2>Data Audit Report</h2>
                  <p>{visibleAuditErrors.length} issue(s)</p>
                </div>
                {visibleAuditErrors.length ? (
                  <div className="audit-list">
                    {visibleAuditErrors.map((issue, index) => (
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

              <div className="card catalog-card">
                <div className="audit-header">
                  <h2>Recent Analysis Runs</h2>
                  <p>{catalogLoading ? 'Loading...' : `${catalogItems.length} run(s)`}</p>
                </div>
                {catalogItems.length ? (
                  <div className="catalog-list">
                    {catalogItems.map((item) => (
                      <div key={item.id} className="catalog-item">
                        <strong>{item.dataset_name || 'Untitled Dataset'}</strong>
                        <span>{item.action}</span>
                        <small>
                          {item.summary?.rows || 0} rows · {item.summary?.cols || 0} cols · {item.summary?.domain || 'Unknown'}
                        </small>
                        <small>{item.created_at}</small>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>No catalog entries yet. Upload a dataset to create lineage history.</p>
                )}
              </div>

              <div className="card grid-card">
                <h2>Raw Data Workspace</h2>
                {!rows.length ? (
                  <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)' }}>
                    <Database style={{ width: '48px', height: '48px', margin: '0 auto 16px', color: 'var(--brand-500)', opacity: 0.6 }} />
                    <h4 style={{ color: 'var(--text-secondary)', marginBottom: '8px', fontSize: '1.125rem' }}>No Dataset Loaded</h4>
                    <p style={{ marginBottom: '20px', fontSize: '0.9rem', lineHeight: '1.6' }}>Upload a CSV, Excel, or JSON file from the sidebar to start exploring your data.</p>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-faint)' }}>
                      <span style={{ padding: '4px 10px', background: 'var(--bg-soft)', borderRadius: '20px', border: '1px solid var(--border-soft)' }}>📄 CSV</span>
                      <span style={{ padding: '4px 10px', background: 'var(--bg-soft)', borderRadius: '20px', border: '1px solid var(--border-soft)' }}>📊 Excel</span>
                      <span style={{ padding: '4px 10px', background: 'var(--bg-soft)', borderRadius: '20px', border: '1px solid var(--border-soft)' }}>🗄️ JSON</span>
                      <span style={{ padding: '4px 10px', background: 'var(--bg-soft)', borderRadius: '20px', border: '1px solid var(--border-soft)' }}>⚡ Parquet</span>
                    </div>
                  </div>
                ) : null}
                <DataGrid rowData={rows} columnDefs={columnDefs} onGridReady={handleGridReady} theme={theme} />
              </div>
            </>
          ) : null}

          {activeTab === 'cleaning' ? (
            <div className="card stats-card">
              <h2>Data Quality and Cleaning</h2>
              <div className="section-actions">
                <button type="button" className="section-print-btn" onClick={handlePrintCleaningReport}>
                  Print Cleaning Report
                </button>
                <button type="button" className="section-print-btn" onClick={handlePrintEDAReport}>
                  Print EDA Report
                </button>
              </div>
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

              {arrangingNotes.length ? (
                <div className="arrange-notes">
                  <h3>Arrange Data Notes</h3>
                  <ul>
                    {arrangingNotes.map((note, index) => (
                      <li key={`${note}-${index}`}>{note}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <MultiGraphPanel
                qualityData={chartData}
                compareData={compareChartData}
                auditErrors={visibleAuditErrors}
                selectedGraphKeys={selectedGraphKeys}
                onChange={setSelectedGraphKeys}
              />
            </div>
          ) : null}

          {activeTab === 'insights' ? (
            <AnalyticsWorkbench
              rows={rows}
              analysis={analysis}
              baselineRows={baselineRows}
              onSaveBaseline={setBaselineRows}
            />
          ) : null}

          {activeTab === 'graphs' ? <GraphGallery rows={rows} analysis={analysis} domainData={domainData} /> : null}

          {activeTab === 'search' ? <SearchAndExport rows={rows} analysis={analysis} /> : null}

          {activeTab === 'quality' ? <DataQualityDashboard rows={rows} /> : null}

          {activeTab === 'predict' && canAnalyze ? (
            <div className="card stats-card">
              <h2>AI Prediction Workspace</h2>
              <div className="section-actions">
                <button type="button" className="section-print-btn" onClick={handlePrintPredictionReport}>
                  Print Prediction Report
                </button>
              </div>
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

          {activeTab === 'workflow' && canAnalyze ? (
            <div className="card workflow-card-shell">
              <div className="section-actions section-actions-workflow">
                <button type="button" className="section-print-btn" onClick={handlePrintWorkflowReport}>
                  Print Workflow Report
                </button>
              </div>
              <WorkflowBuilder
                rows={rows}
                targetOptions={targetOptions}
                onWorkflowRun={(workflowResult) => {
                  setAnalysis(workflowResult.analysis || analysis);
                  setDomainData(workflowResult.analysis?.domain_info || domainData);
                  setRows(workflowResult.data || rows);
                  setAuditErrors(workflowResult.analysis?.audit_errors || []);
                  setCompareChartData(workflowResult.cleaning_stats || []);
                  setArrangingNotes([]);
                  setActiveTab('workflow');
                  loadDashboardSummary();
                }}
              />
            </div>
          ) : null}

          {activeTab === 'audit-log' && user?.role === 'admin' ? (
            <AdminAuditLog />
          ) : null}
        </div>
      </section>

      {showShortcutsModal && (
        <div className="shortcuts-modal-overlay" onClick={() => setShowShortcutsModal(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)', display: 'grid', placeItems: 'center', zIndex: 1000, animation: 'fadeIn 0.2s' }}>
          <div className="shortcuts-modal-content glass-effect" onClick={(e) => e.stopPropagation()} style={{ width: '450px', background: 'var(--surface-card-strong)', border: '1px solid var(--line-strong)', borderRadius: '18px', padding: '24px', boxShadow: 'var(--shadow-soft)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
                <Keyboard className="w-5 h-5" style={{ color: 'var(--accent-cyan)' }} /> Keyboard Shortcuts
              </h3>
              <button type="button" onClick={() => setShowShortcutsModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-soft)' }}>×</button>
            </div>
            
            <div style={{ display: 'grid', gap: '12px', color: 'var(--text-main)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                <span>Show Keyboard Shortcuts</span>
                <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>?</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                <span>Navigate to Workspace</span>
                <span style={{ display: 'flex', gap: '4px' }}>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                  <span>then</span>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>o</kbd>
                </span>
              </div>
              {canAnalyze && (
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                  <span>Navigate to Auto-Clean</span>
                  <span style={{ display: 'flex', gap: '4px' }}>
                    <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                    <span>then</span>
                    <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>c</kbd>
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                <span>Navigate to Ask & Report</span>
                <span style={{ display: 'flex', gap: '4px' }}>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                  <span>then</span>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>r</kbd>
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                <span>Navigate to Graph Gallery</span>
                <span style={{ display: 'flex', gap: '4px' }}>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                  <span>then</span>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                <span>Navigate to Search & Export</span>
                <span style={{ display: 'flex', gap: '4px' }}>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                  <span>then</span>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>s</kbd>
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                <span>Navigate to Data Quality</span>
                <span style={{ display: 'flex', gap: '4px' }}>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                  <span>then</span>
                  <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>q</kbd>
                </span>
              </div>
              {canAnalyze && (
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                  <span>Navigate to AI Predictions</span>
                  <span style={{ display: 'flex', gap: '4px' }}>
                    <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                    <span>then</span>
                    <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>p</kbd>
                  </span>
                </div>
              )}
              {user?.role === 'admin' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: '8px' }}>
                  <span>Navigate to Audit Log</span>
                  <span style={{ display: 'flex', gap: '4px' }}>
                    <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>g</kbd>
                    <span>then</span>
                    <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>l</kbd>
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px' }}>
                <span>Dismiss Modals / Dropdowns</span>
                <kbd style={{ background: 'var(--line-soft)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--line-strong)' }}>ESC</kbd>
              </div>
            </div>
            
            <button type="button" className="btn btn-primary" onClick={() => setShowShortcutsModal(false)} style={{ width: '100%', marginTop: '16px', padding: '10px' }}>Got It</button>
          </div>
        </div>
      )}

      {showProfileModal && (
        <div className="shortcuts-modal-overlay" onClick={() => setShowProfileModal(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)', display: 'grid', placeItems: 'center', zIndex: 1000, animation: 'fadeIn 0.2s' }}>
          <div className="shortcuts-modal-content glass-effect" onClick={(e) => e.stopPropagation()} style={{ width: '480px', background: 'var(--surface-card-strong)', border: '1px solid var(--line-strong)', borderRadius: '18px', padding: '24px', boxShadow: 'var(--shadow-soft)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
                <User className="w-5 h-5" style={{ color: 'var(--accent-cyan)' }} /> Edit Profile
              </h3>
              <button type="button" onClick={() => setShowProfileModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-soft)' }}>×</button>
            </div>

            <form onSubmit={handleSaveProfile} style={{ display: 'grid', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                <div className="sidebar-avatar" style={{ width: '80px', height: '80px', borderRadius: '20px', fontSize: '2rem', cursor: 'pointer', position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={() => fileInputRef.current?.click()}>
                  {uploadedAvatar ? (
                    <img src={uploadedAvatar} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <span>{(editFullName || user?.username || 'U')[0].toUpperCase()}</span>
                  )}
                  <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(0,0,0,0.6)', color: 'white', fontSize: '0.65rem', textAlign: 'center', padding: '4px 0' }}>Upload</div>
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleAvatarChange}
                  accept="image/*"
                  style={{ display: 'none' }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Click to change photo</span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>Full Name</label>
                <input
                  type="text"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  placeholder="John Doe"
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--line-strong)', background: 'var(--surface-base)', color: 'var(--text-main)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>Bio</label>
                <textarea
                  value={editBio}
                  onChange={(e) => setEditBio(e.target.value)}
                  placeholder="Tell us about yourself..."
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--line-strong)', background: 'var(--surface-base)', color: 'var(--text-main)', minHeight: '80px', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>Phone</label>
                  <input
                    type="text"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    placeholder="+1 555-0199"
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--line-strong)', background: 'var(--surface-base)', color: 'var(--text-main)' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>Location</label>
                  <input
                    type="text"
                    value={editLocation}
                    onChange={(e) => setEditLocation(e.target.value)}
                    placeholder="San Francisco, CA"
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--line-strong)', background: 'var(--surface-base)', color: 'var(--text-main)' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyItems: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowProfileModal(false)} style={{ marginLeft: 'auto', padding: '10px 16px' }}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ padding: '10px 16px' }}>Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
