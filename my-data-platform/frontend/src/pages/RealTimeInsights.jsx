import React, { useEffect, useState, useMemo, useCallback } from 'react';
import DashboardLayout from '../DashboardLayout';
import useDataStore from '../store';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import {
  Activity, Database, BarChart2, AlertTriangle, CheckCircle, Info,
  Search, TrendingUp, Layers, Hash, Type, Eye, RefreshCw,
  ChevronDown, ChevronUp, ArrowRight, Zap, Target, Shield,
  GitBranch, PieChart as PieChartIcon, Table2, AlertCircle
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ROOT_URL = API_BASE_URL.replace(/\/api\/?$/, '');

function getAuthHeaders() {
  try {
    const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
    if (raw) {
      const token = JSON.parse(raw)?.token;
      if (token) return { Authorization: `Bearer ${token}` };
    }
  } catch {}
  return {};
}

// ─── Color Palette ──────────────────────────────────────────────────────────
const CHART_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#f43f5e', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6'];
const FINDING_STYLES = {
  success: { bg: 'linear-gradient(135deg, #065f46, #064e3b)', border: '#10b981', icon: CheckCircle, color: '#34d399' },
  warning: { bg: 'linear-gradient(135deg, #78350f, #713f12)', border: '#f59e0b', icon: AlertTriangle, color: '#fbbf24' },
  info:    { bg: 'linear-gradient(135deg, #1e3a5f, #1e40af)', border: '#3b82f6', icon: Info, color: '#60a5fa' },
  error:   { bg: 'linear-gradient(135deg, #7f1d1d, #991b1b)', border: '#ef4444', icon: AlertCircle, color: '#f87171' },
};

// ─── Stat Card ──────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, color = '#6366f1', gradient }) {
  return (
    <div style={{
      background: gradient || 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '16px', padding: '20px', flex: '1', minWidth: '160px',
      backdropFilter: 'blur(12px)',
      transition: 'transform 0.2s, box-shadow 0.2s',
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = `0 8px 24px ${color}22`; }}
    onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <div style={{ background: `${color}22`, borderRadius: '10px', padding: '8px', display: 'flex' }}>
          <Icon size={16} color={color} />
        </div>
        <span style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</span>
      </div>
      <p style={{ color: '#f1f5f9', fontSize: '26px', fontWeight: 800, margin: 0, lineHeight: 1.1 }}>{value}</p>
      {sub && <p style={{ color: '#64748b', fontSize: '11px', margin: '6px 0 0', lineHeight: 1.3 }}>{sub}</p>}
    </div>
  );
}

// ─── Finding Card ──────────────────────────────────────────────────────────
function FindingCard({ finding }) {
  const style = FINDING_STYLES[finding.type] || FINDING_STYLES.info;
  const Icon = style.icon;
  return (
    <div style={{
      background: style.bg, border: `1px solid ${style.border}44`,
      borderLeft: `4px solid ${style.border}`, borderRadius: '12px',
      padding: '14px 18px', display: 'flex', alignItems: 'flex-start', gap: '12px',
      animation: 'fadeSlideIn 0.4s ease',
    }}>
      <div style={{ background: `${style.border}22`, borderRadius: '8px', padding: '6px', flexShrink: 0 }}>
        <Icon size={16} color={style.color} />
      </div>
      <div>
        <p style={{ color: style.color, fontWeight: 700, fontSize: '13px', margin: 0 }}>{finding.title}</p>
        <p style={{ color: '#cbd5e1', fontSize: '12px', margin: '4px 0 0', lineHeight: 1.5 }}>{finding.detail}</p>
      </div>
    </div>
  );
}

// ─── Column Stats Row ──────────────────────────────────────────────────────────
function ColumnRow({ stat, index }) {
  const [expanded, setExpanded] = useState(false);
  const isNumeric = stat.type === 'numeric';
  const completeness = stat.completeness || 0;

  return (
    <div style={{
      background: index % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)',
      borderRadius: '10px', overflow: 'hidden', marginBottom: '4px',
      border: '1px solid rgba(255,255,255,0.05)',
      transition: 'background 0.2s',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 40px',
          alignItems: 'center', padding: '12px 16px', cursor: 'pointer',
          gap: '8px',
        }}
      >
        {/* Name */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            background: isNumeric ? '#6366f122' : '#f59e0b22',
            borderRadius: '6px', padding: '4px', display: 'flex'
          }}>
            {isNumeric ? <Hash size={12} color="#6366f1" /> : <Type size={12} color="#f59e0b" />}
          </div>
          <span style={{ color: '#e2e8f0', fontSize: '13px', fontWeight: 600 }}>{stat.name}</span>
        </div>
        {/* Type */}
        <span style={{
          background: isNumeric ? '#6366f122' : '#f59e0b22',
          color: isNumeric ? '#a5b4fc' : '#fcd34d',
          borderRadius: '6px', padding: '3px 10px', fontSize: '10px',
          fontWeight: 700, textTransform: 'uppercase', textAlign: 'center',
          width: 'fit-content',
        }}>
          {stat.type}
        </span>
        {/* Unique */}
        <span style={{ color: '#94a3b8', fontSize: '12px', textAlign: 'center' }}>{stat.unique_count?.toLocaleString()}</span>
        {/* Null% */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ flex: 1, height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{
              width: `${completeness}%`, height: '100%',
              background: completeness > 90 ? '#10b981' : completeness > 70 ? '#f59e0b' : '#ef4444',
              borderRadius: '3px', transition: 'width 0.6s ease',
            }} />
          </div>
          <span style={{ color: '#94a3b8', fontSize: '10px', minWidth: '36px', textAlign: 'right' }}>
            {completeness}%
          </span>
        </div>
        {/* Outliers */}
        <span style={{ color: (stat.outlier_count || 0) > 0 ? '#fbbf24' : '#475569', fontSize: '12px', textAlign: 'center' }}>
          {isNumeric ? (stat.outlier_count || 0) : '—'}
        </span>
        {/* Expand */}
        {expanded ? <ChevronUp size={14} color="#94a3b8" /> : <ChevronDown size={14} color="#94a3b8" />}
      </div>

      {expanded && (
        <div style={{ padding: '4px 16px 16px', animation: 'fadeSlideIn 0.3s ease' }}>
          {isNumeric && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
              {[
                { label: 'Mean', val: stat.mean },
                { label: 'Median', val: stat.median },
                { label: 'Std Dev', val: stat.std },
                { label: 'Min', val: stat.min },
                { label: 'Max', val: stat.max },
                { label: 'Q1', val: stat.q1 },
                { label: 'Q3', val: stat.q3 },
                { label: 'IQR', val: stat.iqr },
              ].filter(x => x.val !== undefined).map(({ label, val }) => (
                <div key={label} style={{
                  background: '#0f172a', borderRadius: '8px', padding: '8px 14px',
                  border: '1px solid rgba(99,102,241,0.15)',
                }}>
                  <span style={{ color: '#64748b', fontSize: '9px', fontWeight: 700, textTransform: 'uppercase' }}>{label}</span>
                  <p style={{ color: '#a5b4fc', fontSize: '14px', fontWeight: 700, margin: '2px 0 0' }}>
                    {typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : val}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Distribution chart for numeric */}
          {isNumeric && stat.distribution && stat.distribution.length > 0 && (
            <div style={{ height: '140px', marginTop: '4px' }}>
              <p style={{ color: '#64748b', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>Distribution</p>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stat.distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 9 }} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '11px' }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Top values for categorical */}
          {!isNumeric && stat.top_values && stat.top_values.length > 0 && (
            <div>
              <p style={{ color: '#64748b', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>Top Values</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {stat.top_values.map((v, i) => (
                  <span key={i} style={{
                    background: '#0f172a', border: '1px solid rgba(245,158,11,0.2)',
                    borderRadius: '6px', padding: '4px 12px', fontSize: '11px', color: '#fcd34d',
                    display: 'flex', alignItems: 'center', gap: '6px',
                  }}>
                    {v.value} <span style={{ color: '#64748b', fontSize: '10px' }}>({v.count})</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Correlation Card ──────────────────────────────────────────────────────────
function CorrelationCard({ corr }) {
  const absVal = Math.abs(corr.correlation);
  const isPositive = corr.correlation > 0;
  const color = absVal > 0.7 ? '#ef4444' : absVal > 0.5 ? '#f59e0b' : '#10b981';

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: `1px solid ${color}33`,
      borderRadius: '10px', padding: '12px 16px', display: 'flex',
      alignItems: 'center', justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <GitBranch size={14} color={color} />
        <span style={{ color: '#e2e8f0', fontSize: '12px', fontWeight: 600 }}>{corr.col1}</span>
        <ArrowRight size={12} color="#475569" />
        <span style={{ color: '#e2e8f0', fontSize: '12px', fontWeight: 600 }}>{corr.col2}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{
          background: `${color}22`, color, borderRadius: '6px',
          padding: '3px 10px', fontSize: '11px', fontWeight: 700,
        }}>
          {isPositive ? '+' : ''}{corr.correlation.toFixed(3)}
        </span>
        <span style={{
          background: absVal > 0.7 ? '#dc262622' : '#15803d22',
          color: absVal > 0.7 ? '#f87171' : '#4ade80',
          borderRadius: '4px', padding: '2px 8px', fontSize: '9px',
          fontWeight: 700, textTransform: 'uppercase',
        }}>
          {corr.strength}
        </span>
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function RealTimeInsights() {
  const { rawData, cleanedData, analysis } = useDataStore();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [searchCol, setSearchCol] = useState('');

  const currentData = useMemo(() => {
    return cleanedData?.length > 0 ? cleanedData : rawData;
  }, [cleanedData, rawData]);

  const hasData = currentData && currentData.length > 0;

  const fetchInsights = useCallback(async () => {
    if (!hasData) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${ROOT_URL}/api/data-insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ rows: currentData }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setInsights(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [currentData, hasData]);

  useEffect(() => {
    if (hasData) fetchInsights();
  }, [hasData]); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredColumns = useMemo(() => {
    if (!insights?.column_stats) return [];
    if (!searchCol.trim()) return insights.column_stats;
    return insights.column_stats.filter(s =>
      s.name.toLowerCase().includes(searchCol.toLowerCase())
    );
  }, [insights, searchCol]);

  const typeChartData = useMemo(() => {
    if (!insights?.type_distribution) return [];
    return Object.entries(insights.type_distribution).map(([name, value]) => ({ name, value }));
  }, [insights]);

  const TABS = [
    { key: 'overview', label: 'Overview', icon: Eye },
    { key: 'columns', label: 'Column Stats', icon: Table2 },
    { key: 'correlations', label: 'Correlations', icon: GitBranch },
    { key: 'quality', label: 'Data Quality', icon: Shield },
  ];

  return (
    <DashboardLayout>
      <div style={{ maxWidth: '1100px', margin: '0 auto', fontFamily: "'Inter', sans-serif" }}>

        {/* ── Header ── */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div style={{
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                borderRadius: '14px', padding: '12px',
                boxShadow: '0 4px 20px rgba(99,102,241,0.4)'
              }}>
                <Zap size={22} color="#fff" />
              </div>
              <div>
                <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#0f172a', margin: 0 }}>
                  Real-time Data Insights
                </h1>
                <p style={{ color: '#64748b', fontSize: '13px', margin: '4px 0 0' }}>
                  {hasData
                    ? `Analyzing ${currentData.length.toLocaleString()} rows • ${Object.keys(currentData[0] || {}).length} columns`
                    : 'Upload a dataset to see comprehensive insights'}
                </p>
              </div>
            </div>

            {hasData && (
              <button
                onClick={fetchInsights}
                disabled={loading}
                style={{
                  padding: '8px 18px', borderRadius: '10px',
                  background: loading ? '#334155' : 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                  color: 'white', border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: 700, fontSize: '12px',
                  display: 'flex', alignItems: 'center', gap: '6px',
                  boxShadow: '0 2px 10px rgba(99,102,241,0.3)',
                }}
              >
                <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
                {loading ? 'Analyzing...' : 'Refresh Insights'}
              </button>
            )}
          </div>
        </div>

        {/* ── No Data State ── */}
        {!hasData && (
          <div style={{
            background: 'linear-gradient(135deg,#0f172a,#1e1b4b)',
            borderRadius: '24px', padding: '60px 40px',
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', minHeight: '400px',
            border: '1px solid rgba(99,102,241,0.15)',
            boxShadow: '0 8px 32px rgba(15,23,42,0.4)',
          }}>
            <div style={{
              background: 'linear-gradient(135deg,#6366f122,#8b5cf622)',
              borderRadius: '50%', padding: '24px', marginBottom: '20px',
            }}>
              <Database size={48} color="#6366f1" />
            </div>
            <h2 style={{ color: '#e2e8f0', fontSize: '20px', fontWeight: 800, margin: '0 0 8px' }}>
              No Data Loaded
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0, textAlign: 'center', maxWidth: '420px', lineHeight: 1.6 }}>
              Upload a CSV or Excel file from the <strong style={{ color: '#a5b4fc' }}>Upload</strong> page first.
              Once data is loaded, this dashboard will automatically analyze it and show:
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '20px', justifyContent: 'center' }}>
              {['📊 Column Statistics', '📈 Distributions', '🔗 Correlations', '⚠️ Outlier Detection', '🧹 Missing Data Analysis', '💡 Key Findings'].map(item => (
                <span key={item} style={{
                  background: 'rgba(99,102,241,0.12)', color: '#c4b5fd',
                  borderRadius: '8px', padding: '6px 14px', fontSize: '12px', fontWeight: 600,
                }}>
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {error && (
          <div style={{
            background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '12px',
            padding: '14px 18px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px',
          }}>
            <AlertCircle size={16} color="#dc2626" />
            <span style={{ color: '#991b1b', fontSize: '13px' }}>{error}</span>
            <button onClick={fetchInsights} style={{
              marginLeft: 'auto', padding: '4px 12px', borderRadius: '6px',
              background: '#dc2626', color: 'white', border: 'none', cursor: 'pointer',
              fontSize: '11px', fontWeight: 700,
            }}>Retry</button>
          </div>
        )}

        {/* ── Loading ── */}
        {loading && !insights && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', padding: '80px 0', gap: '16px',
          }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '50%',
              border: '3px solid rgba(99,102,241,0.2)', borderTopColor: '#6366f1',
              animation: 'spin 1s linear infinite',
            }} />
            <p style={{ color: '#64748b', fontWeight: 600, fontSize: '14px' }}>Analyzing your data...</p>
          </div>
        )}

        {/* ── Insights Dashboard ── */}
        {insights && (
          <>
            {/* Tab Bar */}
            <div style={{ display: 'flex', gap: '6px', marginBottom: '20px', flexWrap: 'wrap' }}>
              {TABS.map(tab => {
                const TabIcon = tab.icon;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    style={{
                      padding: '8px 18px', borderRadius: '10px', fontSize: '12px', fontWeight: 600,
                      border: activeTab === tab.key ? 'none' : '1.5px solid #e2e8f0',
                      background: activeTab === tab.key ? 'linear-gradient(135deg,#6366f1,#8b5cf6)' : 'white',
                      color: activeTab === tab.key ? 'white' : '#475569',
                      cursor: 'pointer',
                      boxShadow: activeTab === tab.key ? '0 2px 10px rgba(99,102,241,0.3)' : 'none',
                      display: 'flex', alignItems: 'center', gap: '6px',
                      transition: 'all 0.2s',
                    }}
                  >
                    <TabIcon size={13} />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* ─── OVERVIEW TAB ─── */}
            {activeTab === 'overview' && (
              <div style={{ animation: 'fadeSlideIn 0.4s ease' }}>
                {/* Stats Cards */}
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '20px' }}>
                  <StatCard icon={Database} label="Total Rows" value={insights.overview.total_rows?.toLocaleString()} color="#6366f1" />
                  <StatCard icon={Layers} label="Columns" value={insights.overview.total_cols} sub={`${insights.overview.numeric_cols} numeric, ${insights.overview.categorical_cols} categorical`} color="#8b5cf6" />
                  <StatCard icon={AlertTriangle} label="Missing" value={`${insights.overview.null_pct}%`} sub={`${insights.overview.total_null_cells?.toLocaleString()} cells`} color={insights.overview.null_pct > 5 ? '#ef4444' : '#10b981'} />
                  <StatCard icon={Target} label="Duplicates" value={insights.overview.duplicate_rows?.toLocaleString()} color={insights.overview.duplicate_rows > 0 ? '#f59e0b' : '#10b981'} />
                </div>

                {/* Key Findings */}
                {insights.findings && insights.findings.length > 0 && (
                  <div style={{
                    background: 'linear-gradient(135deg,#0f172a,#1e1b4b)',
                    borderRadius: '20px', padding: '20px',
                    border: '1px solid rgba(99,102,241,0.15)',
                    boxShadow: '0 8px 32px rgba(15,23,42,0.3)',
                    marginBottom: '20px',
                  }}>
                    <h3 style={{ color: '#e2e8f0', fontSize: '15px', fontWeight: 700, margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Zap size={16} color="#fbbf24" /> Key Findings
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {insights.findings.map((f, i) => <FindingCard key={i} finding={f} />)}
                    </div>
                  </div>
                )}

                {/* Type Distribution Pie */}
                {typeChartData.length > 0 && (
                  <div style={{
                    background: 'rgba(255,255,255,0.02)', borderRadius: '16px',
                    border: '1px solid rgba(255,255,255,0.06)', padding: '20px',
                  }}>
                    <h3 style={{ color: '#334155', fontSize: '14px', fontWeight: 700, margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <PieChartIcon size={16} color="#8b5cf6" /> Column Type Distribution
                    </h3>
                    <div style={{ height: '240px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={typeChartData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                            innerRadius={60} outerRadius={90} paddingAngle={4} label={({ name, value }) => `${name} (${value})`}
                          >
                            {typeChartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                          </Pie>
                          <Tooltip />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ─── COLUMNS TAB ─── */}
            {activeTab === 'columns' && (
              <div style={{ animation: 'fadeSlideIn 0.4s ease' }}>
                {/* Search */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  background: 'rgba(255,255,255,0.04)', borderRadius: '10px',
                  padding: '8px 14px', marginBottom: '14px',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}>
                  <Search size={14} color="#64748b" />
                  <input
                    placeholder="Search columns..."
                    value={searchCol}
                    onChange={e => setSearchCol(e.target.value)}
                    style={{
                      background: 'transparent', border: 'none', outline: 'none',
                      color: '#334155', fontSize: '13px', flex: 1,
                    }}
                  />
                  <span style={{ color: '#64748b', fontSize: '11px' }}>
                    {filteredColumns.length} / {insights.column_stats?.length || 0}
                  </span>
                </div>

                {/* Header */}
                <div style={{
                  display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 40px',
                  padding: '8px 16px', gap: '8px',
                }}>
                  {['Column', 'Type', 'Unique', 'Completeness', 'Outliers', ''].map(h => (
                    <span key={h} style={{ color: '#64748b', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</span>
                  ))}
                </div>

                {/* Column detail container */}
                <div style={{
                  background: 'linear-gradient(135deg,#0f172a,#1e1b4b)',
                  borderRadius: '16px', padding: '8px',
                  border: '1px solid rgba(99,102,241,0.15)',
                  maxHeight: '600px', overflowY: 'auto',
                }}>
                  {filteredColumns.map((stat, i) => (
                    <ColumnRow key={stat.name} stat={stat} index={i} />
                  ))}
                  {filteredColumns.length === 0 && (
                    <p style={{ color: '#475569', fontSize: '13px', textAlign: 'center', padding: '40px 0' }}>
                      No columns match your search.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* ─── CORRELATIONS TAB ─── */}
            {activeTab === 'correlations' && (
              <div style={{ animation: 'fadeSlideIn 0.4s ease' }}>
                {insights.correlations && insights.correlations.length > 0 ? (
                  <div style={{
                    background: 'linear-gradient(135deg,#0f172a,#1e1b4b)',
                    borderRadius: '20px', padding: '20px',
                    border: '1px solid rgba(99,102,241,0.15)',
                  }}>
                    <h3 style={{ color: '#e2e8f0', fontSize: '15px', fontWeight: 700, margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <GitBranch size={16} color="#8b5cf6" />
                      Column Correlations
                      <span style={{ background: '#6366f122', color: '#a5b4fc', borderRadius: '6px', padding: '2px 10px', fontSize: '11px', fontWeight: 600, marginLeft: '8px' }}>
                        {insights.correlations.length} pairs
                      </span>
                    </h3>
                    <p style={{ color: '#64748b', fontSize: '12px', margin: '0 0 16px', lineHeight: 1.5 }}>
                      Showing correlations with |r| &gt; 0.3. Strong correlations (|r| &gt; 0.7) may indicate redundancy or dependence.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {insights.correlations.map((corr, i) => (
                        <CorrelationCard key={i} corr={corr} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{
                    background: 'rgba(255,255,255,0.03)', borderRadius: '16px',
                    padding: '60px 20px', textAlign: 'center',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}>
                    <GitBranch size={40} color="#475569" />
                    <p style={{ color: '#64748b', fontWeight: 600, fontSize: '14px', marginTop: '12px' }}>
                      No significant correlations found
                    </p>
                    <p style={{ color: '#475569', fontSize: '12px' }}>
                      Columns don't show strong linear relationships (|r| &gt; 0.3)
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* ─── QUALITY TAB ─── */}
            {activeTab === 'quality' && (
              <div style={{ animation: 'fadeSlideIn 0.4s ease' }}>
                {/* Quality Score */}
                <div style={{
                  background: 'linear-gradient(135deg,#0f172a,#1e1b4b)',
                  borderRadius: '20px', padding: '24px',
                  border: '1px solid rgba(99,102,241,0.15)',
                  marginBottom: '16px', textAlign: 'center',
                }}>
                  {(() => {
                    const completeness = 100 - (insights.overview.null_pct || 0);
                    const dupPct = insights.overview.total_rows > 0 ? (insights.overview.duplicate_rows / insights.overview.total_rows * 100) : 0;
                    const score = Math.max(0, Math.round(completeness - dupPct * 0.5));
                    const scoreColor = score > 80 ? '#10b981' : score > 60 ? '#f59e0b' : '#ef4444';
                    return (
                      <>
                        <p style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 8px' }}>
                          Overall Data Quality Score
                        </p>
                        <p style={{ color: scoreColor, fontSize: '56px', fontWeight: 900, margin: 0, lineHeight: 1 }}>
                          {score}
                        </p>
                        <p style={{ color: '#64748b', fontSize: '12px', margin: '8px 0 0' }}>
                          out of 100 — {score > 80 ? 'Excellent quality' : score > 60 ? 'Needs some cleaning' : 'Significant issues detected'}
                        </p>
                      </>
                    );
                  })()}
                </div>

                {/* Missing Data Breakdown */}
                {insights.missing_summary && insights.missing_summary.length > 0 ? (
                  <div style={{
                    background: 'rgba(255,255,255,0.03)', borderRadius: '16px',
                    padding: '20px', border: '1px solid rgba(255,255,255,0.06)',
                  }}>
                    <h3 style={{ color: '#334155', fontSize: '14px', fontWeight: 700, margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertTriangle size={16} color="#f59e0b" /> Missing Data by Column
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {insights.missing_summary.map((col, i) => (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 12px',
                          background: 'rgba(255,255,255,0.02)', borderRadius: '8px',
                        }}>
                          <span style={{ color: '#e2e8f0', fontSize: '13px', fontWeight: 600, minWidth: '140px' }}>{col.name}</span>
                          <div style={{ flex: 1, height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${col.null_pct}%`, height: '100%',
                              background: col.null_pct > 20 ? '#ef4444' : col.null_pct > 5 ? '#f59e0b' : '#6366f1',
                              borderRadius: '4px', transition: 'width 0.6s ease',
                            }} />
                          </div>
                          <span style={{ color: '#94a3b8', fontSize: '12px', minWidth: '60px', textAlign: 'right' }}>
                            {col.null_pct}% ({col.null_count})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{
                    background: 'linear-gradient(135deg,#065f46,#064e3b)', borderRadius: '16px',
                    padding: '30px 20px', textAlign: 'center',
                    border: '1px solid #10b98144',
                  }}>
                    <CheckCircle size={40} color="#34d399" />
                    <p style={{ color: '#34d399', fontWeight: 700, fontSize: '15px', marginTop: '12px' }}>
                      No missing values!
                    </p>
                    <p style={{ color: '#6ee7b7', fontSize: '12px' }}>
                      Your dataset is 100% complete — great data quality.
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </DashboardLayout>
  );
}
