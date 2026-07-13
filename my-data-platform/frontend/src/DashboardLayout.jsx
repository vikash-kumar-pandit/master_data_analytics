import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Database, LogOut, RefreshCw, BarChart2, Table, 
  ShieldCheck, Bot, Calendar, ClipboardList, AlertCircle, FileBarChart2,
  Search, GitBranch, PieChart, Activity, Sliders, Sparkles
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from './context/AuthContext';
import useDataStore from './store';
import UploadDashboard from './components/UploadDashboard';
import DataViewer from './components/DataViewer';
import AnalyticsChat from './components/AnalyticsChat';
import CopilotPanel from './components/CopilotPanel';

export default function DashboardLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;

  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [activeProjectId, setActiveProjectId] = useState('');

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
        <header className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center shadow-sm shrink-0">
          <div>
            <h2 className="text-xl font-extrabold text-slate-900 capitalize tracking-tight">
              {currentPath === '/' ? 'Data Workspace' : currentPath.slice(1).replace(/([A-Z])/g, ' $1')}
            </h2>
          </div>
          
          <div className="flex items-center gap-4">
            {isDataLoaded && (
              <button
                onClick={resetStore}
                className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl font-semibold text-sm transition shadow-sm"
              >
                <RefreshCw className="w-4 h-4" /> Upload New Dataset
              </button>
            )}
            <span className="px-3 py-1 bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-bold uppercase tracking-wider">
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
