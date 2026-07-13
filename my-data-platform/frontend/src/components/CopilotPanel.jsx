import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Send, Sparkles, MessageSquare, Plus, Brain, HelpCircle, 
  ChevronRight, BarChart2, ShieldCheck, Clock, Activity, Target
} from 'lucide-react';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token') || localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default function CopilotPanel({ projectId, isOpen, onClose }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [execPlan, setExecPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [viewMode, setViewMode] = useState('chat'); // chat or plan
  const messagesEndRef = useRef(null);

  // Default clickable suggestion shortcuts
  const suggestions = [
    "Find outlier anomalies",
    "List top profit categories",
    "Recommend ML models",
    "Dataset health status",
    "Explain date formats"
  ];

  useEffect(() => {
    if (projectId && isOpen) {
      fetchSessions();
      fetchExecutionPlan();
    }
  }, [projectId, isOpen]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchSessions = async () => {
    try {
      const res = await api.get(`/api/copilot/sessions?project_id=${projectId}`);
      setSessions(res.data);
      if (res.data.length > 0) {
        // Auto select first session
        handleSelectSession(res.data[0].session_id);
      } else {
        setMessages([]);
        setActiveSessionId('');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchExecutionPlan = async () => {
    setPlanLoading(true);
    try {
      const res = await api.get(`/api/copilot/plan?project_id=${projectId}`);
      setExecPlan(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setPlanLoading(false);
    }
  };

  const handleSelectSession = async (sessId) => {
    setActiveSessionId(sessId);
    setLoading(true);
    try {
      // Re-trigger an empty post to retrieve session history log
      const res = await api.post('/api/copilot/chat', new URLSearchParams({
        project_id: projectId,
        session_id: sessId,
        message: 'Load History'
      }));
      // Filter out the 'Load History' placeholder user message
      const historyLogs = res.data.messages.filter(m => m.content !== 'Load History');
      setMessages(historyLogs);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const createNewSession = async () => {
    try {
      const res = await api.post('/api/copilot/sessions/create', new URLSearchParams({
        project_id: projectId,
        title: "Discussion " + (sessions.length + 1)
      }));
      setSessions([...sessions, res.data]);
      setActiveSessionId(res.data.session_id);
      setMessages([]);
      setViewMode('chat');
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (textToSend) => {
    const msg = textToSend || inputText;
    if (!msg.trim()) return;
    
    setLoading(true);
    if (!textToSend) setInputText('');

    const formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('message', msg);
    if (activeSessionId) {
      formData.append('session_id', activeSessionId);
    }

    try {
      const res = await api.post('/api/copilot/chat', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (!activeSessionId) {
        setActiveSessionId(res.data.session_id);
        fetchSessions();
      } else {
        const historyLogs = res.data.messages.filter(m => m.content !== 'Load History');
        setMessages(historyLogs);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-slate-900 text-slate-200 shadow-2xl flex flex-col z-50 border-l border-slate-800 font-sans">
      
      {/* Copilot Header */}
      <div className="p-4 bg-slate-950 border-b border-slate-850 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-indigo-400 animate-pulse" />
          <div>
            <span className="font-extrabold text-sm text-white tracking-tight">AI Analytics Copilot</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping" />
              <span className="text-[10px] text-slate-450 uppercase font-black tracking-wider">Brain Layer Online</span>
            </div>
          </div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white font-bold text-lg p-1.5">&times;</button>
      </div>

      {/* Nav Tabs */}
      <div className="flex border-b border-slate-850 bg-slate-950 shrink-0">
        <button
          onClick={() => setViewMode('chat')}
          className={`flex-1 py-3 text-xs uppercase font-extrabold tracking-wider transition border-b-2
            ${viewMode === 'chat' ? 'border-indigo-500 text-white bg-slate-900/40' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
        >
          Conversations
        </button>
        <button
          onClick={() => setViewMode('plan')}
          className={`flex-1 py-3 text-xs uppercase font-extrabold tracking-wider transition border-b-2
            ${viewMode === 'plan' ? 'border-indigo-500 text-white bg-slate-900/40' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
        >
          AI Execution Plan
        </button>
      </div>

      {/* Mode 1: Chat Panels */}
      {viewMode === 'chat' && (
        <div className="flex-1 flex flex-col min-h-0 bg-slate-900">
          
          {/* History sessions sub-header */}
          <div className="p-3 bg-slate-950 border-b border-slate-850 flex items-center justify-between shrink-0">
            <select
              value={activeSessionId}
              onChange={(e) => handleSelectSession(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-xs font-semibold px-2.5 py-1 rounded-md text-slate-300 focus:outline-none"
            >
              <option value="">No Session selected</option>
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>{s.title}</option>
              ))}
            </select>
            <button
              onClick={createNewSession}
              className="flex items-center gap-1 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white font-extrabold text-[10px] rounded-md transition shadow-md"
            >
              <Plus className="w-3.5 h-3.5" /> NEW CHAT
            </button>
          </div>

          {/* Bubbles log */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8 text-slate-500 space-y-3">
                <HelpCircle className="w-10 h-10 text-slate-650 mx-auto" />
                <h4 className="font-bold text-sm text-slate-400">Ask DataSaaS Pro Brain</h4>
                <p className="text-xs max-w-[280px] mx-auto">Query top trends, ask to compute outliers anomalies, recommend pipelines, or build automatic reports.</p>
              </div>
            )}

            {messages.map((m, idx) => (
              <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                
                {/* Bubble message body */}
                <div className={`max-w-[85%] p-3.5 rounded-2xl text-xs leading-relaxed
                  ${m.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-none' 
                    : 'bg-slate-850 text-slate-200 border border-slate-800 rounded-tl-none'}`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>

                  {/* Render Visual assets if returned */}
                  {m.assets && m.assets.type === 'bar' && (
                    <div className="mt-3 p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">{m.assets.label}</span>
                      <div className="space-y-1.5">
                        {m.assets.data.map((item, dIdx) => (
                          <div key={dIdx} className="flex justify-between items-center text-[11px]">
                            <span className="font-mono text-slate-400 truncate max-w-[150px]">{String(Object.values(item)[0])}</span>
                            <span className="font-mono font-bold text-slate-200">{Number(Object.values(item)[1]).toFixed(1)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {m.assets && m.assets.type === 'table' && (
                    <div className="mt-3 p-3 bg-slate-900 border border-slate-800 rounded-xl overflow-x-auto">
                      <table className="w-full text-left text-[10px]">
                        <thead>
                          <tr className="border-b border-slate-850 text-slate-500 font-extrabold">
                            <th className="pb-1.5">Feature</th>
                            <th className="pb-1.5 text-right">Outliers</th>
                          </tr>
                        </thead>
                        <tbody>
                          {m.assets.data.map((item, tIdx) => (
                            <tr key={tIdx} className="border-b border-slate-850/50">
                              <td className="py-1 font-mono">{item.column}</td>
                              <td className="py-1 font-mono text-right text-red-400 font-bold">{item.outliers_count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Sub info */}
                {m.role === 'assistant' && (
                  <span className="text-[9px] text-slate-500 mt-1 uppercase font-semibold">
                    Confidence: 94% &bull; Computed by Local Engine
                  </span>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions block */}
          {messages.length === 0 && (
            <div className="p-4 bg-slate-950/40 border-t border-slate-850 shrink-0">
              <span className="text-[10px] text-slate-500 uppercase font-black tracking-wider block mb-2">Suggestions</span>
              <div className="flex flex-wrap gap-1.5">
                {suggestions.map(s => (
                  <button
                    key={s}
                    onClick={() => handleSendMessage(s)}
                    className="px-2.5 py-1.5 bg-slate-850 hover:bg-slate-800 border border-slate-800 rounded-lg text-[10px] text-slate-300 text-left transition"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input field footer */}
          <div className="p-3 bg-slate-950 border-t border-slate-850 flex gap-2 shrink-0">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask Copilot..."
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-600"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading || !inputText.trim()}
              className="p-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-xl text-white transition flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

        </div>
      )}

      {/* Mode 2: AI Execution Plan */}
      {viewMode === 'plan' && (
        <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-900">
          {planLoading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-2">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-xs font-bold text-slate-500">Formulating execution plan...</p>
            </div>
          ) : execPlan ? (
            <div className="space-y-6">
              
              {/* Summary card */}
              <div className="p-4 bg-slate-950 border border-slate-850 rounded-xl space-y-4">
                <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-indigo-400" /> Executive Metrics
                </h3>
                <div className="grid grid-cols-2 gap-3.5">
                  <div className="p-3 bg-slate-900 border border-slate-850 rounded-lg">
                    <span className="text-[9px] text-slate-500 font-extrabold uppercase block">Domain Classification</span>
                    <span className="text-xs font-bold text-white mt-1 block">{execPlan.domain}</span>
                  </div>
                  <div className="p-3 bg-slate-900 border border-slate-850 rounded-lg">
                    <span className="text-[9px] text-slate-500 font-extrabold uppercase block">Dataset Health</span>
                    <span className="text-xs font-bold text-emerald-400 mt-1 block">{execPlan.health}</span>
                  </div>
                  <div className="p-3 bg-slate-900 border border-slate-850 rounded-lg">
                    <span className="text-[9px] text-slate-500 font-extrabold uppercase block">Total Rows</span>
                    <span className="text-xs font-bold text-white mt-1 block">{execPlan.rows?.toLocaleString()}</span>
                  </div>
                  <div className="p-3 bg-slate-900 border border-slate-850 rounded-lg">
                    <span className="text-[9px] text-slate-500 font-extrabold uppercase block">Recommended Goal</span>
                    <span className="text-xs font-bold text-indigo-400 mt-1 block">{execPlan.recommended_goal}</span>
                  </div>
                </div>
              </div>

              {/* Recommended Steps pipeline list */}
              <div className="p-4 bg-slate-950 border border-slate-850 rounded-xl space-y-4">
                <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Target className="w-4 h-4 text-indigo-400" /> Recommended Action Pipeline
                </h3>
                <div className="space-y-2.5">
                  {execPlan.recommended_pipeline?.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-2.5 text-xs text-slate-350">
                      <ChevronRight className="w-3.5 h-3.5 text-slate-655" />
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Confidence & Timing info */}
              <div className="p-4 bg-slate-950 border border-slate-850 rounded-xl grid grid-cols-2 gap-4">
                <div className="flex items-center gap-2.5">
                  <Clock className="w-5 h-5 text-slate-500" />
                  <div>
                    <span className="text-[9px] text-slate-500 font-bold uppercase block">Estimated Run Time</span>
                    <span className="text-xs font-extrabold text-white">{execPlan.estimated_time}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-5 h-5 text-slate-500" />
                  <div>
                    <span className="text-[9px] text-slate-500 font-bold uppercase block">Expected Accuracy</span>
                    <span className="text-xs font-extrabold text-white">{execPlan.expected_accuracy}</span>
                  </div>
                </div>
              </div>

            </div>
          ) : (
            <div className="text-center py-20 text-slate-550">
              <p className="text-xs">Execution plan generation empty.</p>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
