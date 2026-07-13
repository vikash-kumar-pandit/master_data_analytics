import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Activity, ArrowDownToLine, AlertTriangle, CheckCircle, Database, 
  HelpCircle, BarChart3, ShieldAlert, Cpu, Sparkles, RefreshCw, 
  FileText, Columns, ShieldCheck, Info
} from 'lucide-react';
import DashboardLayout from '../DashboardLayout';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Configure auth token interceptor
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token') || localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default function DataProfiling() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  // Load projects list on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/api/analytics/projects');
      setProjects(res.data);
      if (res.data.length > 0) {
        // Auto select first project
        setSelectedProjectId(res.data[0].id);
        fetchProfile(res.data[0].dataset_id);
      }
    } catch (err) {
      console.error("Failed to fetch projects list", err);
      setError("Failed to fetch projects list. Please make sure you are logged in.");
    }
  };

  const fetchProfile = async (datasetId) => {
    if (!datasetId) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/api/profile/${datasetId}`);
      setProfile(res.data);
    } catch (err) {
      // If profile doesn't exist, reset it so user can run it
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (e) => {
    const projId = e.target.value;
    setSelectedProjectId(projId);
    const proj = projects.find(p => p.id === projId);
    if (proj) {
      fetchProfile(proj.dataset_id);
    }
  };

  const handleRunProfiling = async () => {
    if (!selectedProjectId) return;
    setLoading(true);
    setError('');
    const formData = new FormData();
    formData.append('project_id', selectedProjectId);
    
    try {
      const res = await api.post('/api/profile/run', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setProfile(res.data.data);
      fetchProfile(res.data.dataset_id);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Profiling run failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (format) => {
    if (!profile || !profile.dataset_id) return;
    const url = `http://localhost:8000/api/profile/export/${format}?dataset_id=${profile.dataset_id}`;
    
    // Trigger download in new window or iframe
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `profile_${profile.dataset_id}.${format}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Helper to color correlation cells
  const getCorrBgColor = (val) => {
    const absVal = Math.abs(val);
    if (absVal < 0.2) return 'bg-slate-50 dark:bg-neutral-800 text-slate-500';
    if (val > 0) {
      if (absVal < 0.5) return 'bg-blue-50 dark:bg-blue-900/10 text-blue-600';
      if (absVal < 0.8) return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 font-semibold';
      return 'bg-blue-600 text-white font-bold';
    } else {
      if (absVal < 0.5) return 'bg-red-50 dark:bg-red-900/10 text-red-600';
      if (absVal < 0.8) return 'bg-red-100 dark:bg-red-900/30 text-red-700 font-semibold';
      return 'bg-red-600 text-white font-bold';
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 max-w-7xl mx-auto">
        
        {/* Top Header Card */}
        <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex justify-between items-center flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-2xl shadow-sm">
              <Activity className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">Universal Data Profiling</h1>
              <p className="text-slate-500 text-sm">Instant, Enterprise-grade Metadata, Quality & Analytics Diagnostic Suite</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <select 
              value={selectedProjectId}
              onChange={handleProjectChange}
              className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold text-sm focus:outline-none dark:bg-neutral-800 dark:border-neutral-700 text-slate-800 dark:text-slate-200"
            >
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>

            {profile && (
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => handleExport('pdf')}
                  className="flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl font-bold text-xs transition text-slate-700 shadow-sm"
                >
                  <ArrowDownToLine className="w-3.5 h-3.5" /> PDF
                </button>
                <button 
                  onClick={() => handleExport('html')}
                  className="flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl font-bold text-xs transition text-slate-700 shadow-sm"
                >
                  <ArrowDownToLine className="w-3.5 h-3.5" /> HTML
                </button>
                <button 
                  onClick={() => handleExport('json')}
                  className="flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl font-bold text-xs transition text-slate-700 shadow-sm"
                >
                  <ArrowDownToLine className="w-3.5 h-3.5" /> JSON
                </button>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div role="alert" className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-semibold">{error}</span>
          </div>
        )}

        {/* Profiler trigger if no run is loaded */}
        {!profile && !loading && (
          <div className="bg-white dark:bg-neutral-850 p-12 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm text-center flex flex-col items-center justify-center gap-4">
            <div className="p-4 bg-indigo-50 dark:bg-indigo-900/10 text-indigo-600 rounded-full">
              <Database className="w-12 h-12" />
            </div>
            <h2 className="text-xl font-black text-slate-900 dark:text-white">Dataset Not Profiled</h2>
            <p className="text-slate-500 max-w-lg">Click the button below to initialize the universal data profiler. We will calculate statistics, missing densities, correlation heatmaps, PII exposures, and generate an AI data story.</p>
            <button 
              onClick={handleRunProfiling}
              disabled={!selectedProjectId}
              className="mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-xl font-bold transition shadow-lg shadow-blue-200 flex items-center gap-2"
            >
              <RefreshCw className="w-5 h-5" /> Run Advanced Profiler
            </button>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-10 h-10 text-blue-600 animate-spin" />
            <p className="text-sm font-bold text-slate-600">Running Enterprise Diagnostics Engine...</p>
          </div>
        )}

        {/* Profiler dashboard tab layout */}
        {profile && !loading && (
          <div className="flex flex-col gap-6">
            
            {/* Tabs Selector */}
            <div className="flex gap-1 bg-slate-100 dark:bg-neutral-800 p-1.5 rounded-2xl overflow-x-auto">
              {['overview', 'statistics', 'columns', 'quality', 'correlation', 'warnings', 'recommendations', 'ai_summary'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition shrink-0
                    ${activeTab === tab 
                      ? 'bg-white dark:bg-neutral-700 text-indigo-600 dark:text-white shadow-sm' 
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
                >
                  {tab.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* TAB CONTENTS */}
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Stats Cards */}
                <div className="md:col-span-2 bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-6">
                  <h3 className="text-lg font-black text-slate-900 dark:text-white">Dataset Metrics</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 dark:bg-neutral-800 border rounded-xl">
                      <span className="text-[10px] text-slate-400 font-extrabold uppercase">Total Observations</span>
                      <p className="text-2xl font-black text-slate-900 dark:text-white mt-1">{profile.rows?.toLocaleString()}</p>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-neutral-800 border rounded-xl">
                      <span className="text-[10px] text-slate-400 font-extrabold uppercase">Dimensions</span>
                      <p className="text-2xl font-black text-slate-900 dark:text-white mt-1">{profile.columns} Columns</p>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-neutral-800 border rounded-xl">
                      <span className="text-[10px] text-slate-400 font-extrabold uppercase">Memory Footprint</span>
                      <p className="text-2xl font-black text-slate-900 dark:text-white mt-1">{(profile.memory / 1024).toFixed(1)} KB</p>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-neutral-800 border rounded-xl">
                      <span className="text-[10px] text-slate-400 font-extrabold uppercase">Disk Size</span>
                      <p className="text-2xl font-black text-slate-900 dark:text-white mt-1">{(profile.disk / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                </div>

                {/* Column Types Breakdown */}
                <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-4">
                  <h3 className="text-lg font-black text-slate-900 dark:text-white">Types Breakdown</h3>
                  <div className="space-y-3">
                    {[
                      { label: 'Numerical', count: profile.column_types?.numerical?.length || 0, color: 'bg-blue-500' },
                      { label: 'Categorical', count: profile.column_types?.categorical?.length || 0, color: 'bg-green-500' },
                      { label: 'Text', count: profile.column_types?.text?.length || 0, color: 'bg-yellow-500' },
                      { label: 'Datetime', count: profile.column_types?.datetime?.length || 0, color: 'bg-purple-500' },
                      { label: 'Boolean', count: profile.column_types?.boolean?.length || 0, color: 'bg-red-500' }
                    ].map(type => (
                      <div key={type.label} className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${type.color}`} />
                          <span className="text-sm font-semibold text-slate-600 dark:text-slate-400">{type.label}</span>
                        </div>
                        <span className="text-sm font-bold text-slate-900 dark:text-white">{type.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'statistics' && (
              <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm overflow-x-auto">
                <h3 className="text-lg font-black text-slate-900 dark:text-white mb-4">Detailed Statistics</h3>
                <table className="w-full text-left border-collapse min-w-[800px]">
                  <thead>
                    <tr className="bg-slate-50 border-b text-xs font-bold text-slate-500 uppercase dark:bg-neutral-800 dark:border-neutral-700">
                      <th className="p-4">Column Name</th>
                      <th className="p-4">Type</th>
                      <th className="p-4">Mean</th>
                      <th className="p-4">Median</th>
                      <th className="p-4">Std Dev</th>
                      <th className="p-4">Variance</th>
                      <th className="p-4">Skewness</th>
                      <th className="p-4">Kurtosis</th>
                      <th className="p-4">Outliers</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(profile.statistics || {}).map(([col, stats]) => (
                      <tr key={col} className="border-b hover:bg-slate-50/50 dark:hover:bg-neutral-800/30 text-sm">
                        <td className="p-4 font-mono font-bold text-slate-900 dark:text-white">{col}</td>
                        <td className="p-4 text-xs font-semibold text-indigo-600">{stats.category}</td>
                        <td className="p-4 font-mono">{stats.mean !== undefined ? stats.mean : 'N/A'}</td>
                        <td className="p-4 font-mono">{stats.median !== undefined ? stats.median : 'N/A'}</td>
                        <td className="p-4 font-mono">{stats.std_dev !== undefined ? stats.std_dev : 'N/A'}</td>
                        <td className="p-4 font-mono">{stats.variance !== undefined ? stats.variance : 'N/A'}</td>
                        <td className="p-4 font-mono">{stats.skewness !== undefined ? stats.skewness : 'N/A'}</td>
                        <td className="p-4 font-mono">{stats.kurtosis !== undefined ? stats.kurtosis : 'N/A'}</td>
                        <td className="p-4 font-mono text-red-500">{stats.outliers !== undefined ? stats.outliers : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'columns' && (
              <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-4">
                <h3 className="text-lg font-black text-slate-900 dark:text-white">Column Schema & Health</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(profile.statistics || {}).map(([col, stats]) => (
                    <div key={col} className="p-4 border rounded-xl flex justify-between items-start gap-4">
                      <div>
                        <p className="font-mono font-bold text-slate-900 dark:text-white">{col}</p>
                        <span className="text-xs text-slate-400 capitalize">{stats.type} ({stats.category})</span>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-slate-500">Missing: <span className="font-bold text-slate-700">{stats.missing_pct}%</span></p>
                        <p className="text-xs text-slate-500 mt-1">Unique: <span className="font-bold text-slate-700">{stats.unique_count} ({stats.unique_pct}%)</span></p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'quality' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Health Overview */}
                <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col items-center justify-center text-center gap-3">
                  <ShieldCheck className="w-16 h-16 text-emerald-500" />
                  <h3 className="text-lg font-black text-slate-900 dark:text-white">Quality Diagnostics</h3>
                  <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl font-bold text-xl">
                    Health Index: {Math.max(10, 100 - (profile.warnings?.length || 0) * 10)}%
                  </div>
                  <p className="text-xs text-slate-400">Heuristics mapping null rates, duplicate ratios, class imbalance, and data leakage metrics.</p>
                </div>

                {/* Quality Details */}
                <div className="md:col-span-2 bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-4">
                  <h3 className="text-lg font-black text-slate-900 dark:text-white">Security & PII Scans</h3>
                  <div className="space-y-3">
                    {Object.entries(profile.statistics || {}).map(([col, stats]) => (
                      stats.pii_detected ? (
                        <div key={col} className="p-4 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-xl flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <ShieldAlert className="w-5 h-5 text-yellow-600" />
                            <div>
                              <p className="font-mono font-bold">{col}</p>
                              <p className="text-xs text-yellow-600">{stats.pii_detected}</p>
                            </div>
                          </div>
                          <span className="text-xs font-bold bg-yellow-100 text-yellow-800 px-2.5 py-1 rounded-full">HIGH EXPOSURE</span>
                        </div>
                      ) : null
                    ))}
                    
                    {!Object.values(profile.statistics || {}).some(s => s.pii_detected) && (
                      <div className="p-8 text-center text-slate-500 flex flex-col items-center gap-2">
                        <CheckCircle className="w-12 h-12 text-emerald-500" />
                        <h4 className="font-bold text-slate-700">No PII Violations Found</h4>
                        <p className="text-xs max-w-sm">Completed scanning for emails, credit cards, phones, and location descriptors.</p>
                      </div>
                    )}
                  </div>
                </div>

              </div>
            )}

            {activeTab === 'correlation' && (
              <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm">
                <h3 className="text-lg font-black text-slate-900 dark:text-white mb-4">Correlation Matrix Heatmap</h3>
                {Object.keys(profile.correlation_matrix || {}).length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="border-collapse text-xs text-center min-w-[500px]">
                      <thead>
                        <tr>
                          <th></th>
                          {Object.keys(profile.correlation_matrix).map(col => (
                            <th key={col} className="p-3 font-mono font-bold text-slate-600 rotate-45 select-none">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(profile.correlation_matrix).map(([rowName, cols]) => (
                          <tr key={rowName}>
                            <td className="p-3 font-mono font-bold text-slate-600 text-right whitespace-nowrap">{rowName}</td>
                            {Object.entries(cols).map(([colName, val]) => (
                              <td 
                                key={colName} 
                                className={`w-12 h-12 p-1 border border-slate-200 dark:border-neutral-700 ${getCorrBgColor(val)}`}
                                title={`${rowName} vs ${colName}: ${val}`}
                              >
                                {val.toFixed(2)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500">
                    <Info className="w-12 h-12 text-slate-350 mx-auto mb-2" />
                    <p className="text-sm font-semibold">Not enough numerical columns to compute correlation matrix.</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'warnings' && (
              <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-4">
                <h3 className="text-lg font-black text-slate-900 dark:text-white">Active Pipeline Warnings</h3>
                <div className="space-y-3">
                  {profile.warnings?.map((warn, i) => (
                    <div key={i} className="p-4 bg-orange-50 border border-orange-200 text-orange-800 rounded-xl flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-sm uppercase tracking-wider text-orange-700">{warn.type}</p>
                        <p className="text-sm mt-0.5">{warn.message}</p>
                      </div>
                    </div>
                  ))}
                  
                  {(!profile.warnings || profile.warnings.length === 0) && (
                    <div className="p-8 text-center text-slate-500 flex flex-col items-center gap-2">
                      <CheckCircle className="w-12 h-12 text-emerald-500" />
                      <h4 className="font-bold text-slate-700">All Checks Passed</h4>
                      <p className="text-xs">No columns with missing percentages, target leakage, or collinearity violations found.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'recommendations' && (
              <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-4">
                <h3 className="text-lg font-black text-slate-900 dark:text-white">Recommended Actions</h3>
                <div className="space-y-3">
                  {profile.recommendations?.map((rec, i) => (
                    <div key={i} className="p-4 border border-indigo-100 bg-indigo-50/50 text-indigo-900 rounded-xl flex items-start gap-3">
                      <Cpu className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-sm text-indigo-900">{rec.type}</p>
                        <p className="text-sm mt-0.5 text-indigo-700">{rec.message}</p>
                      </div>
                    </div>
                  ))}
                  
                  {(!profile.recommendations || profile.recommendations.length === 0) && (
                    <div className="p-8 text-center text-slate-500">
                      <p className="text-sm font-semibold">No cleaning recommendations required.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'ai_summary' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Data Story */}
                <div className="md:col-span-2 bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-4">
                  <div className="flex items-center gap-2 text-indigo-600">
                    <Sparkles className="w-5 h-5 text-indigo-600 animate-pulse" />
                    <h3 className="text-lg font-black text-slate-900 dark:text-white">AI Data Story</h3>
                  </div>
                  <div className="p-5 bg-indigo-50/50 rounded-xl border border-indigo-100 text-slate-800 leading-relaxed italic text-sm">
                    {profile.story}
                  </div>
                </div>

                {/* Executive Summary */}
                <div className="bg-white dark:bg-neutral-850 p-6 rounded-2xl border border-slate-200 dark:border-neutral-700 shadow-sm flex flex-col gap-3">
                  <div className="flex items-center gap-2 text-slate-700">
                    <FileText className="w-5 h-5 text-slate-600" />
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">Executive Summary</h3>
                  </div>
                  <pre className="p-4 bg-slate-50 rounded-xl font-mono text-xs text-slate-700 border whitespace-pre-wrap">{profile.summary}</pre>
                </div>

              </div>
            )}

          </div>
        )}

      </div>
    </DashboardLayout>
  );
}
