import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart3, RefreshCw, Star, Download, Presentation, ShieldCheck, 
  HelpCircle, Eye, FileText, LayoutGrid, CheckCircle2, AlertCircle
} from 'lucide-react';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  let token = null;
  try {
    const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
    if (raw) {
      token = JSON.parse(raw)?.token;
    }
  } catch (e) {
    console.error("Error reading token in VisualizationIntelligence interceptor", e);
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default function VisualizationIntelligence() {
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState('');
  const [recs, setRecs] = useState([]);
  const [savedCharts, setSavedCharts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [activeCategory, setActiveCategory] = useState('All');
  
  // Card-specific active tabs to display narrative insights vs stats
  const [cardTabs, setCardTabs] = useState({}); // { [chart_type]: 'story' | 'stats' | 'tech' }

  const categories = ['All', 'Business', 'Statistical', 'Time Series', 'Correlation', 'Machine Learning'];

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (activeProjectId) {
      fetchRecommendationsAndCharts();
    }
  }, [activeProjectId]);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/api/analytics/projects');
      setProjects(res.data);
      if (res.data.length > 0) {
        setActiveProjectId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchRecommendationsAndCharts = async () => {
    setLoading(true);
    try {
      // 1. Get AI recommendations list
      const recRes = await api.post('/api/visualization/recommend', new URLSearchParams({
        project_id: activeProjectId
      }));
      setRecs(recRes.data);

      // 2. Get pre-generated charts from DB
      const savedRes = await api.get(`/api/visualization/project/${activeProjectId}`);
      setSavedCharts(savedRes.data);

      // Init card tabs
      const tabs = {};
      recRes.data.forEach(r => {
        tabs[r.chart_type] = 'story';
      });
      setCardTabs(tabs);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateChart = async (r) => {
    try {
      const res = await api.post('/api/visualization/generate', new URLSearchParams({
        project_id: activeProjectId,
        chart_type: r.chart_type,
        columns_json: JSON.stringify(r.columns)
      }));
      
      // Update saved charts list
      const updated = savedCharts.filter(c => c.chart_type !== r.chart_type);
      setSavedCharts([...updated, { ...res.data, column_names: r.columns, explanation: r.explanation, stats_interpretation: r.stats_interpretation }]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateAll = async () => {
    setGeneratingAll(true);
    try {
      await api.post('/api/visualization/generate-all', new URLSearchParams({
        project_id: activeProjectId
      }));
      await fetchRecommendationsAndCharts();
    } catch (err) {
      console.error(err);
    } finally {
      setGeneratingAll(false);
    }
  };

  const handleExport = (format) => {
    if (!activeProjectId) return;
    let token = '';
    try {
      const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
      if (raw) {
        token = JSON.parse(raw)?.token;
      }
    } catch (e) {
      console.error("Error reading token in handleExport", e);
    }
    window.open(`http://localhost:8000/api/visualization/export?project_id=${activeProjectId}&format=${format}&token=${token}`);
  };

  // Filter recommendations based on active categories tab
  const filteredRecs = recs.filter(r => activeCategory === 'All' || r.category === activeCategory);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      
      {/* Top Gallery Header */}
      <div className="flex justify-between items-center flex-wrap gap-4 border-b border-slate-200 pb-5">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-blue-600 animate-pulse" />
          <div>
            <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">AI Visualization Intelligence Gallery</h1>
            <p className="text-xs text-slate-500 mt-1">Automatic smart matching, business narratives, statistical contexts, and PPTX storyboards.</p>
          </div>
        </div>

        {/* Project Selector dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-slate-500 uppercase">Active Workspace:</label>
          <select
            value={activeProjectId}
            onChange={(e) => setActiveProjectId(e.target.value)}
            className="bg-white border border-slate-200 text-xs font-extrabold px-3 py-2 rounded-xl text-slate-700 shadow-sm focus:outline-none focus:border-blue-600"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Control Actions Header */}
      <div className="flex justify-between items-center flex-wrap gap-3.5 bg-slate-900 text-white p-4 rounded-2xl shadow-xl">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <span className="text-xs font-bold text-slate-350">
            {recs.length} visual suggestions identified for this dataset.
          </span>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={handleGenerateAll}
            disabled={generatingAll || loading || recs.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:brightness-110 disabled:opacity-40 text-white font-extrabold text-xs rounded-xl shadow-md transition"
          >
            {generatingAll ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <LayoutGrid className="w-3.5 h-3.5" />}
            GENERATE ALL CHARTS
          </button>
          
          <button
            onClick={() => handleExport('pptx')}
            disabled={savedCharts.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-extrabold text-xs rounded-xl border border-slate-700 transition"
          >
            <Presentation className="w-3.5 h-3.5 text-orange-400" />
            EXPORT PPTX SLIDESHOW
          </button>

          <button
            onClick={() => handleExport('zip')}
            disabled={savedCharts.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-extrabold text-xs rounded-xl border border-slate-700 transition"
          >
            <Download className="w-3.5 h-3.5 text-blue-405" />
            DOWNLOAD PACKAGE (.ZIP)
          </button>
        </div>
      </div>

      {/* Categories Filter Tabs */}
      <div className="flex border-b border-slate-200 gap-1.5 overflow-x-auto pb-0.5">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2.5 text-xs font-black uppercase tracking-wider transition border-b-2
              ${activeCategory === cat ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Charts List Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-xs font-bold text-slate-500">AI scanning dataset attributes...</p>
        </div>
      ) : filteredRecs.length === 0 ? (
        <div className="text-center py-20 bg-slate-50 border border-slate-100 rounded-3xl space-y-3">
          <AlertCircle className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="font-extrabold text-slate-700 text-sm">No Visualizations Suggested</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">Upload a dataset or verify that correct numerical dimensions exist in your selected active workspace.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {filteredRecs.map(r => {
            const saved = savedCharts.find(c => c.chart_type === r.chart_type);
            const activeTab = cardTabs[r.chart_type] || 'story';
            
            return (
              <div key={r.chart_type} className="bg-white rounded-3xl border border-slate-150 shadow-sm overflow-hidden flex flex-col hover:shadow-md transition">
                
                {/* Chart Card Header */}
                <div className="p-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
                  <div>
                    <span className="text-[10px] font-black text-blue-650 uppercase tracking-widest block">{r.category} Category</span>
                    <h3 className="font-black text-slate-800 text-sm mt-0.5">{r.chart_type.replace('_', ' ').title() || r.chart_type}</h3>
                  </div>
                  <div className="flex items-center gap-1">
                    {/* Render rating stars */}
                    {Array.from({ length: r.business_value }).map((_, sIdx) => (
                      <Star key={sIdx} className="w-3.5 h-3.5 fill-amber-400 text-amber-450" />
                    ))}
                  </div>
                </div>

                {/* Plot Area */}
                <div className="flex-1 min-h-[250px] bg-slate-50 flex items-center justify-center p-4 border-b border-slate-100">
                  {saved ? (
                    <img 
                      src={`data:image/png;base64,${saved.image_base64}`} 
                      alt={r.chart_type} 
                      className="max-h-[280px] w-auto rounded-lg object-contain"
                    />
                  ) : (
                    <div className="text-center space-y-3.5 py-10">
                      <HelpCircle className="w-8 h-8 text-slate-400 mx-auto" />
                      <div>
                        <p className="text-xs text-slate-500">Not generated yet</p>
                        <span className="text-[10px] text-slate-400 block mt-1 font-mono">Params: {r.columns.join(', ')}</span>
                      </div>
                      <button
                        onClick={() => handleGenerateChart(r)}
                        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-[10px] rounded-lg transition shadow-sm"
                      >
                        GENERATE CHART
                      </button>
                    </div>
                  )}
                </div>

                {/* AI Explanation & Insight Card Footer */}
                <div className="p-4 flex flex-col flex-shrink-0 bg-white">
                  
                  {/* Card Tab triggers */}
                  <div className="flex border-b border-slate-100 gap-3.5 text-[10px] font-bold uppercase tracking-wider mb-3 shrink-0">
                    <button
                      onClick={() => setCardTabs({ ...cardTabs, [r.chart_type]: 'story' })}
                      className={`pb-1.5 border-b-2 ${activeTab === 'story' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}
                    >
                      AI Business Insight
                    </button>
                    <button
                      onClick={() => setCardTabs({ ...cardTabs, [r.chart_type]: 'stats' })}
                      className={`pb-1.5 border-b-2 ${activeTab === 'stats' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}
                    >
                      Interpretation
                    </button>
                    <button
                      onClick={() => setCardTabs({ ...cardTabs, [r.chart_type]: 'tech' })}
                      className={`pb-1.5 border-b-2 ${activeTab === 'tech' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}
                    >
                      Technical Explanation
                    </button>
                  </div>

                  {/* Tab Contents */}
                  <div className="min-h-[60px] text-xs text-slate-600 leading-relaxed">
                    {activeTab === 'story' && (
                      <div className="space-y-1.5">
                        <span className="text-[9px] uppercase font-bold text-red-500 tracking-wider block">Insight Story:</span>
                        <p className="italic">"{saved?.story || r.story}"</p>
                      </div>
                    )}
                    {activeTab === 'stats' && (
                      <div className="space-y-1.5">
                        <span className="text-[9px] uppercase font-bold text-indigo-500 tracking-wider block">Statistical Context:</span>
                        <p>{saved?.stats_interpretation || r.stats_interpretation}</p>
                      </div>
                    )}
                    {activeTab === 'tech' && (
                      <div className="space-y-1.5">
                        <span className="text-[9px] uppercase font-bold text-slate-500 tracking-wider block">Technical Details:</span>
                        <p>{saved?.explanation || r.explanation}</p>
                      </div>
                    )}
                  </div>

                  {/* Confidence rating badges */}
                  <div className="border-t border-slate-100 pt-3 mt-3 flex justify-between items-center text-[10px] text-slate-450 font-bold shrink-0">
                    <span className="flex items-center gap-1 text-emerald-600">
                      <CheckCircle2 className="w-3.5 h-3.5" /> AI Confidence: {saved?.confidence || r.confidence}%
                    </span>
                    <span className="font-mono text-slate-400">
                      Columns: {r.columns.join(', ')}
                    </span>
                  </div>

                </div>

              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}

// Add string prototype title extension for visual types styling
if (!String.prototype.title) {
  String.prototype.title = function () {
    return this.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };
}
