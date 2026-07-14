import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Database, LogOut, RefreshCw, BarChart2, Table, 
  ShieldCheck, Bot, Calendar, ClipboardList, AlertCircle, FileBarChart2,
  Search, GitBranch, PieChart, Activity, Sliders, Sparkles, Bell, Sun, Moon, Palette
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from './context/AuthContext';
import { useTheme } from './context/ThemeContext';
import useDataStore from './store';
import UploadDashboard from './components/UploadDashboard';
import DataViewer from './components/DataViewer';
import AnalyticsChat from './components/AnalyticsChat';
import CopilotPanel from './components/CopilotPanel';

export default function DashboardLayout({ children }) {
  const { user, logout } = useAuth();
  const { theme, setTheme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;

  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [activeProjectId, setActiveProjectId] = useState('');
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [notifications, setNotifications] = useState([
    { id: 1, message: "Welcome to DataSaaS Pro DIOS v2.0 Platform Overhaul!", unread: true },
    { id: 2, message: "AutoML engine configured and ready.", unread: false }
  ]);

  useEffect(() => {
    const token = user?.token;
    if (token) {
      axios.get('http://localhost:8000/api/analytics/projects', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => {
        if (res.data.length > 0) {
          setActiveProjectId(res.data[0].id);
        }
      })
      .catch(err => console.error("Layout projects fetch failed", err));
    }
  }, [user]);

  const { 
    rawData, 
    cleanedData, 
    resetStore
  } = useDataStore();

  const [workspaceTab, setWorkspaceTab] = useState('grid'); // grid or chat

  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;
  const isDataLoaded = currentDataset && currentDataset.length > 0;

  useEffect(() => {
    if (isDataLoaded) {
      const hasUploadedNotif = notifications.some(n => n.message === "Dataset uploaded and parsed successfully.");
      if (!hasUploadedNotif) {
        setNotifications(prev => [
          { id: Date.now(), message: "Dataset uploaded and parsed successfully.", unread: true },
          ...prev
        ]);
      }
    }
  }, [isDataLoaded]);

  // Protect routes that require data
  const dataRequiredPaths = ['/quality', '/predictive', '/reports', '/workflows', '/search', '/graphs'];
  const isBlocked = dataRequiredPaths.includes(currentPath) && !isDataLoaded;

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans text-slate-800">
      
      {/* 📁 Left Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col justify-between shrink-0 shadow-xl">
        <div>
          {/* Logo */}
          <div className="p-6 flex items-center gap-3 border-b border-slate-800 cursor-pointer" onClick={() => navigate('/')}>
            <div className="p-2 bg-blue-600 rounded-lg text-white">
              <Database className="w-6 h-6" />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">DataSaaS Pro</span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <button
              onClick={() => navigate('/')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <Table className="w-5 h-5" /> Data Workspace
            </button>

            <button
              onClick={() => navigate('/profiling')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/profiling' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <Activity className="w-5 h-5" /> Data Profiling
            </button>

            <button
              onClick={() => navigate('/preparation')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/preparation' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <Sliders className="w-5 h-5" /> Data Prep Studio
            </button>

            <button
              onClick={() => navigate('/quality')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/quality' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <ShieldCheck className="w-5 h-5" /> Data Quality
            </button>

            <button
              onClick={() => navigate('/predictive')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/predictive' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <Bot className="w-5 h-5" /> AutoML Predictions
            </button>

            <button
              onClick={() => navigate('/insights')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/insights' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <BarChart2 className="w-5 h-5" /> Real-time Insights
            </button>

            {user?.role !== 'viewer' && (
              <button
                onClick={() => navigate('/schedule')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                  ${currentPath === '/schedule' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
              >
                <Calendar className="w-5 h-5" /> Schedule Exports
              </button>
            )}

            {user?.role !== 'viewer' && (
              <button
                onClick={() => navigate('/reports')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                  ${currentPath === '/reports' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
              >
                <FileBarChart2 className="w-5 h-5" /> Report Builder
              </button>
            )}

            <button
              onClick={() => navigate('/workflows')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/workflows' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <GitBranch className="w-5 h-5" /> Workflow Builder
            </button>

            <button
              onClick={() => navigate('/graphs')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/graphs' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <PieChart className="w-5 h-5" /> Graph Gallery
            </button>

            <button
              onClick={() => navigate('/search')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                ${currentPath === '/search' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
            >
              <Search className="w-5 h-5" /> Search & Export
            </button>

            <button
              onClick={() => setIsCopilotOpen(!isCopilotOpen)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-900/30 mt-4 transition hover:brightness-110"
            >
              <Sparkles className="w-5 h-5 animate-pulse" /> AI Copilot
            </button>

            {user?.role === 'admin' && (
              <button
                onClick={() => navigate('/audit')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition
                  ${currentPath === '/audit' ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 hover:text-white'}`}
              >
                <ClipboardList className="w-5 h-5" /> Admin Audit Logs
              </button>
            )}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shadow-md">
              {user?.username ? user.username[0].toUpperCase() : 'U'}
            </div>
            <div>
              <p className="text-sm font-semibold text-white truncate max-w-[140px]">{user?.username || 'User'}</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-wider font-extrabold mt-0.5">{user?.role || 'Viewer'}</p>
            </div>
          </div>
          <button 
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-red-900/30 hover:text-red-400 border border-slate-700 hover:border-red-900/50 rounded-xl transition font-semibold text-xs"
          >
            <LogOut className="w-4 h-4" /> Log Out
          </button>
        </div>
      </aside>

      {/* 🖥️ Main Screen Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        
        {/* Top Header Bar */}
        <header className="bg-white dark:bg-neutral-850 border-b border-slate-200 dark:border-neutral-700 px-8 py-4 flex justify-between items-center shadow-sm shrink-0 transition-colors">
          <div className="flex items-center gap-6">
            <h2 className="text-xl font-extrabold text-slate-900 dark:text-white capitalize tracking-tight">
              {currentPath === '/' ? 'Data Workspace' : currentPath.slice(1).replace(/([A-Z])/g, ' $1')}
            </h2>

            {/* Active Pipeline Progress Timeline */}
            {isDataLoaded && (
              <div className="hidden lg:flex items-center gap-2 bg-slate-50 dark:bg-neutral-800/40 px-4 py-1.5 rounded-full border border-slate-200 dark:border-neutral-700 text-[10px] font-bold select-none tracking-wider uppercase text-slate-400">
                <span>Timeline:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600 dark:text-emerald-450">✔ Ingested</span>
                  <span>/</span>
                  <span className="text-emerald-600 dark:text-emerald-450">✔ Profiled</span>
                  <span>/</span>
                  <span className={cleanedData.length > 0 ? "text-emerald-600 dark:text-emerald-450" : ""}>
                    {cleanedData.length > 0 ? "✔ Cleaned" : "○ Clean"}
                  </span>
                  <span>/</span>
                  <span className={currentPath === '/predictive' ? "text-indigo-600" : ""}>○ Predictive</span>
                  <span>/</span>
                  <span className={currentPath === '/reports' ? "text-indigo-600" : ""}>○ Reports</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            {isDataLoaded && (
              <button
                onClick={resetStore}
                className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-slate-700 dark:text-slate-250 border border-slate-200 dark:border-neutral-700 rounded-xl font-bold text-xs transition shadow-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Upload New
              </button>
            )}

            {/* 🔔 Notifications Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsNotificationOpen(!isNotificationOpen)}
                className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-neutral-800 rounded-xl transition relative"
                aria-label="Toggle notifications"
              >
                <Bell className="w-5 h-5" />
                {notifications.some(n => n.unread) && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
                )}
              </button>

              {isNotificationOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-neutral-800 border border-slate-200 dark:border-neutral-700 rounded-2xl shadow-xl z-50 p-4 flex flex-col gap-3">
                  <div className="flex justify-between items-center border-b pb-2 dark:border-neutral-700">
                    <h3 className="font-extrabold text-sm text-slate-900 dark:text-white">Activity Feed</h3>
                    <button 
                      onClick={() => setNotifications(prev => prev.map(n => ({ ...n, unread: false })))}
                      className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      Mark all read
                    </button>
                  </div>
                  <div className="max-h-60 overflow-y-auto space-y-2.5">
                    {notifications.map(n => (
                      <div key={n.id} className={`p-2.5 rounded-xl border text-xs leading-relaxed transition ${n.unread ? 'bg-indigo-50/50 border-indigo-100 text-indigo-950 dark:bg-indigo-950/20 dark:border-indigo-900/50 dark:text-indigo-200' : 'border-slate-100 text-slate-600 dark:border-neutral-700 dark:text-slate-400'}`}>
                        {n.message}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* 🎨 Theme Selector Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-neutral-800 p-1 rounded-xl border dark:border-neutral-700">
              {[
                { name: 'light', icon: Sun, label: 'Light' },
                { name: 'dark', icon: Moon, label: 'Dark' },
                { name: 'corporate', icon: Database, label: 'Corp' },
                { name: 'high-contrast', icon: Palette, label: 'Contrast' }
              ].map(t => {
                const IconComponent = t.icon;
                const active = theme === t.name;
                return (
                  <button
                    key={t.name}
                    onClick={() => setTheme(t.name)}
                    title={t.label}
                    className={`p-1.5 rounded-lg transition-all ${active ? 'bg-white dark:bg-neutral-750 text-indigo-600 dark:text-white shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                  >
                    <IconComponent className="w-4 h-4" />
                  </button>
                );
              })}
            </div>

            <span className="px-3 py-1.5 bg-slate-100 dark:bg-neutral-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-neutral-700 rounded-xl text-[10px] font-extrabold uppercase tracking-wider">
              {user?.role || 'viewer'} mode
            </span>
          </div>
        </header>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-8">
          {isBlocked ? (
            <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500">
              <AlertCircle className="w-16 h-16 text-slate-350 mb-4 animate-bounce" />
              <h3 className="text-lg font-bold text-slate-700">No Dataset Uploaded</h3>
              <p className="max-w-md mt-1">Please upload a dataset in the Data Workspace tab before accessing this page.</p>
              <button onClick={() => navigate('/')} className="mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition text-sm">
                Go to Workspace
              </button>
            </div>
          ) : (
            children ? children : (
              // Default Homepage Workspace view when no children exist (SPA behavior)
              !isDataLoaded ? <UploadDashboard /> : (
                <div className="flex flex-col gap-6">
                  {/* Dashboard Subheader with control tabs */}
                  <div className="flex justify-between items-center flex-wrap gap-4 border-b border-slate-200 pb-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setWorkspaceTab('grid')}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition
                          ${workspaceTab === 'grid' 
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' 
                            : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'}`}
                      >
                        <Table className="w-4 h-4" /> Data Grid
                      </button>
                      <button
                        onClick={() => setWorkspaceTab('chat')}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition
                          ${workspaceTab === 'chat' 
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' 
                            : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'}`}
                      >
                        <BarChart2 className="w-4 h-4" /> AI Analyst Chat
                      </button>
                    </div>
                  </div>

                  {/* Render active workspace view */}
                  {workspaceTab === 'grid' ? (
                    <DataViewer onShowChat={() => setWorkspaceTab('chat')} />
                  ) : (
                    <AnalyticsChat />
                  )}
                </div>
              )
            )
          )}
        </div>

        {/* 🤖 Sliding AI Copilot Panel */}
        <CopilotPanel 
          projectId={activeProjectId} 
          isOpen={isCopilotOpen} 
          onClose={() => setIsCopilotOpen(false)} 
        />

      </div>

    </div>
  );
}
