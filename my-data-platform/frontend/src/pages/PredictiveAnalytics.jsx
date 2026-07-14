import React, { useState, useEffect, useMemo } from 'react';
import DashboardLayout from '../DashboardLayout';
import apiService from '../api/client';
import useDataStore from '../store';
import AutoMLWidget from '../components/AutoMLWidget';
import AIEngineWidget from '../components/AIEngineWidget';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine, Area
} from 'recharts';
import {
  TrendingUp, TrendingDown, Minus, Sparkles, Calendar,
  AlertCircle, Info, BarChart2, Activity, Target,
  ChevronDown, ChevronUp, ArrowUpRight, ArrowDownRight,
  Download, RefreshCw, AlertTriangle
} from 'lucide-react';

// ─── Custom Tooltip ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(99,102,241,0.4)',
      borderRadius: '12px', padding: '12px 16px', backdropFilter: 'blur(8px)',
      boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
    }}>
      <p style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '8px', fontWeight: 700 }}>{label}</p>
      {payload.map((entry, i) => (
        entry.value !== null && entry.value !== undefined && (
          <p key={i} style={{ color: entry.color, fontSize: '13px', fontWeight: 700, margin: '3px 0' }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
          </p>
        )
      ))}
    </div>
  );
};

// ─── Stat Card ─────────────────────────────────────────────────────────────────
const StatCard = ({ label, value, sub, color = '#6366f1', icon: Icon }) => (
  <div style={{
    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '14px', padding: '18px 20px', flex: '1', minWidth: '140px'
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <p style={{ color: '#64748b', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>{label}</p>
        <p style={{ color: color, fontSize: '22px', fontWeight: 800, margin: 0 }}>{value}</p>
        {sub && <p style={{ color: '#475569', fontSize: '11px', marginTop: '4px' }}>{sub}</p>}
      </div>
      {Icon && <div style={{ background: color + '22', borderRadius: '10px', padding: '8px' }}><Icon size={18} color={color} /></div>}
    </div>
  </div>
);

// ─── Trend Badge ───────────────────────────────────────────────────────────────
const TrendBadge = ({ direction }) => {
  const config = {
    upward:   { icon: TrendingUp,   color: '#22c55e', bg: '#15803d22', label: 'Upward Trend' },
    downward: { icon: TrendingDown, color: '#ef4444', bg: '#dc262622', label: 'Downward Trend' },
    stable:   { icon: Minus,        color: '#f59e0b', bg: '#d9770622', label: 'Stable' },
  };
  const c = config[direction] || config.stable;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px',
      background: c.bg, color: c.color, border: `1px solid ${c.color}44`,
      borderRadius: '999px', padding: '4px 12px', fontSize: '12px', fontWeight: 700
    }}>
      <c.icon size={13} /> {c.label}
    </span>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────
export default function PredictiveAnalytics() {
  const { rawData, cleanedData, columns, setForecastResult, fileObject } = useDataStore();
  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;

  const [predictiveTab, setPredictiveTab] = useState('forecast'); // forecast | automl | nlp
  const [automlTarget, setAutomlTarget] = useState('');

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [horizon, setHorizon] = useState(14);
  const [metricCol, setMetricCol] = useState('');
  const [dateCol, setDateCol] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [showTable, setShowTable] = useState(false);
  const [showSmoothed, setShowSmoothed] = useState(false);

  // Numeric and date-like columns separately
  const numericCols = useMemo(() => {
    if (!currentDataset?.length) return [];
    return columns.filter(c => {
      const sample = currentDataset.find(r => r[c] !== null && r[c] !== undefined);
      return sample && !isNaN(Number(sample[c]));
    });
  }, [columns, currentDataset]);

  const dateLikeCols = useMemo(() => {
    return columns.filter(c =>
      /date|time|day|month|week|year|period|quarter/i.test(c)
    );
  }, [columns]);

  // Auto-detect best columns
  useEffect(() => {
    if (numericCols.length > 0) {
      const salesCol = numericCols.find(c => /sales|revenue|profit|amount|value|price|count|qty|quantity/i.test(c));
      setMetricCol(salesCol || numericCols[0]);
    }
    if (dateLikeCols.length > 0) {
      setDateCol(dateLikeCols[0]);
    } else if (columns.length > 0) {
      setDateCol('');
    }
  }, [numericCols, dateLikeCols, columns]);

  // Build unified chart data: history + smoothed + forecast
  const chartData = useMemo(() => {
    if (!results) return [];

    const history = (results.chart_data || []).map((pt, i) => {
      const smoothedVal = results.smoothed_history?.[i];
      return {
        displayDate: String(pt.date_label ?? pt.row_index ?? i),
        actual: typeof pt.value === 'number' ? pt.value : null,
        smoothed: typeof smoothedVal === 'number' ? smoothedVal : null,
        predicted: null,
        isForecast: false,
      };
    });

    const future = (results.forecast || []).map(pt => ({
      displayDate: String(pt.point),
      actual: null,
      smoothed: null,
      predicted: typeof pt.value === 'number' ? pt.value : null,
      isForecast: true,
    }));

    // Bridge: connect last actual point to first predicted point
    if (history.length > 0 && future.length > 0) {
      const last = history[history.length - 1];
      future.unshift({
        displayDate: last.displayDate,
        actual: last.actual,
        smoothed: null,
        predicted: last.actual,
        isForecast: false,
      });
    }

    return [...history, ...future];
  }, [results]);

  // Subsample chart data if too many points (keep max 120 labels for readability)
  const displayChartData = useMemo(() => {
    if (chartData.length <= 120) return chartData;
    const step = Math.ceil(chartData.length / 120);
    return chartData.filter((_, i) => i % step === 0 || i === chartData.length - 1);
  }, [chartData]);

  const runForecast = async () => {
    if (!currentDataset?.length || !metricCol) return;
    setLoading(true);
    setErrorMsg('');
    setResults(null);
    setForecastResult(null);
    try {
      const payload = {
        rows: currentDataset,
        metric_column: metricCol,
        date_column: dateCol || null,
        horizon: Number(horizon),
      };
      const res = await apiService.forecasting.forecast(payload);
      const data = res.data || res;
      if (!data || (!data.forecast && !data.chart_data)) {
        setErrorMsg('Server returned an empty response. Please check your column selections.');
        return;
      }
      setResults(data);
      setForecastResult(data);
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Forecasting failed.';
      setErrorMsg(`Error: ${detail}. Ensure the Metric column is numeric.`);
    } finally {
      setLoading(false);
    }
  };

  const ms = results?.model_stats || {};
  const mst = results?.metric_stats || {};
  const forecastPts = results?.forecast || [];

  // Download CSV
  const downloadCSV = () => {
    if (!forecastPts.length) return;
    const rows = [['Period', 'Predicted Value'], ...forecastPts.map(p => [p.point, p.value])];
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `forecast_${metricCol}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <DashboardLayout>
      <div style={{ maxWidth: '1200px', margin: '0 auto', fontFamily: "'Inter', sans-serif" }}>

        {/* ── Header ── */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', borderRadius: '14px', padding: '10px' }}>
              <TrendingUp size={22} color="#fff" />
            </div>
            <div>
              <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#0f172a', margin: 0 }} className="dark:text-white">
                Predictive AI Analytics Studio
              </h1>
              <p style={{ color: '#64748b', fontSize: '13px', margin: '3px 0 0' }} className="dark:text-slate-400">
                AutoML estimator engine • Explainable AI insights • Time-series trend models
              </p>
            </div>
          </div>

          {/* Tab Selector buttons */}
          <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(125,157,191,0.15)', paddingBottom: '10px' }}>
            {[
              { id: 'forecast', label: 'Time-Series Forecasting' },
              { id: 'automl', label: 'AutoML Predictor (XAI)' },
              { id: 'nlp', label: 'Clustering & NLP Classification' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setPredictiveTab(tab.id)}
                style={{
                  padding: '8px 16px', borderRadius: '10px', fontWeight: 700, fontSize: '12px', border: 'none', cursor: 'pointer',
                  background: predictiveTab === tab.id ? '#4f46e5' : 'transparent',
                  color: predictiveTab === tab.id ? '#fff' : '#64748b',
                  transition: 'all 0.2s'
                }}
                className={predictiveTab !== tab.id ? 'hover:bg-slate-100 dark:hover:bg-neutral-800' : ''}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── No Data State ── */}
        {!currentDataset?.length ? (
          <div style={{
            textAlign: 'center', padding: '80px 20px',
            background: 'white', borderRadius: '20px',
            border: '2px dashed #e2e8f0', boxShadow: '0 1px 4px rgba(0,0,0,0.06)'
          }}>
            <div style={{ background: '#f1f5f9', borderRadius: '50%', width: '80px', height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <BarChart2 size={36} color="#94a3b8" />
            </div>
            <p style={{ fontSize: '18px', fontWeight: 700, color: '#334155', marginBottom: '8px' }}>No Dataset Loaded</p>
            <p style={{ color: '#64748b', fontSize: '14px' }}>Upload a CSV or Excel file in the <strong>Workspace</strong> tab to start forecasting.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

            {/* ── Tab 1: Forecasting ── */}
            {predictiveTab === 'forecast' && (
              <>
                {/* ── Config Panel ── */}
            <div style={{
              background: 'white', borderRadius: '18px',
              border: '1px solid #e2e8f0', padding: '24px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
            }}>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#334155', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Target size={15} color="#6366f1" /> Configuration
              </h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'flex-end' }}>

                {/* Metric Column */}
                <div style={{ flex: '1', minWidth: '180px' }}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                    📈 Metric Column (Y-axis) *
                  </label>
                  <select
                    value={metricCol}
                    onChange={e => setMetricCol(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #cbd5e1', borderRadius: '10px', fontSize: '13px', background: 'white', color: '#0f172a', outline: 'none' }}
                  >
                    <option value="">-- Select numeric column --</option>
                    {numericCols.map(c => <option key={c} value={c}>{c}</option>)}
                    {numericCols.length === 0 && columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                {/* Date Column */}
                <div style={{ flex: '1', minWidth: '180px' }}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                    📅 Date / Time Column (X-axis)
                  </label>
                  <select
                    value={dateCol}
                    onChange={e => setDateCol(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #cbd5e1', borderRadius: '10px', fontSize: '13px', background: 'white', color: '#0f172a', outline: 'none' }}
                  >
                    <option value="">-- None (use row order) --</option>
                    {columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                {/* Horizon */}
                <div style={{ width: '140px' }}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                    🔭 Horizon (periods)
                  </label>
                  <input
                    type="number" min="1" max="90" value={horizon}
                    onChange={e => setHorizon(Number(e.target.value))}
                    style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #cbd5e1', borderRadius: '10px', fontSize: '13px', outline: 'none' }}
                  />
                </div>

                {/* Run button */}
                <button
                  onClick={runForecast}
                  disabled={loading || !metricCol}
                  style={{
                    padding: '11px 28px', borderRadius: '10px', border: 'none', cursor: loading || !metricCol ? 'not-allowed' : 'pointer',
                    background: loading || !metricCol ? '#94a3b8' : 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                    color: 'white', fontWeight: 700, fontSize: '14px',
                    display: 'flex', alignItems: 'center', gap: '8px',
                    boxShadow: loading || !metricCol ? 'none' : '0 4px 14px rgba(99,102,241,0.4)',
                    transition: 'all 0.2s'
                  }}
                >
                  {loading ? (
                    <><RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> Forecasting...</>
                  ) : (
                    <><Sparkles size={15} /> Run Forecast</>
                  )}
                </button>
              </div>

              {/* Info bar */}
              <div style={{ marginTop: '12px', padding: '10px 14px', background: '#f8fafc', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Info size={13} color="#6366f1" />
                <span style={{ fontSize: '12px', color: '#475569' }}>
                  Dataset: <strong>{currentDataset.length.toLocaleString()}</strong> rows × <strong>{columns.length}</strong> columns •
                  Model: <strong>OLS Linear Trend Regression</strong> •
                  Smoothing: <strong>3-period Moving Average</strong>
                </span>
              </div>
            </div>

            {/* ── Error ── */}
            {errorMsg && (
              <div style={{
                padding: '14px 18px', background: '#fef2f2', border: '1px solid #fca5a5',
                borderRadius: '12px', display: 'flex', alignItems: 'flex-start', gap: '12px'
              }}>
                <AlertCircle size={18} color="#ef4444" style={{ flexShrink: 0, marginTop: '1px' }} />
                <div>
                  <p style={{ fontWeight: 700, color: '#b91c1c', fontSize: '13px', margin: '0 0 4px' }}>Forecasting Failed</p>
                  <p style={{ color: '#dc2626', fontSize: '13px', margin: 0 }}>{errorMsg}</p>
                  <p style={{ color: '#64748b', fontSize: '12px', margin: '6px 0 0' }}>
                    💡 Tips: Make sure Metric Column has numeric values and Date Column has parseable dates (YYYY-MM-DD, DD/MM/YYYY, etc.)
                  </p>
                </div>
              </div>
            )}

            {/* ── Loading skeleton ── */}
            {loading && (
              <div style={{
                background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0',
                padding: '40px', textAlign: 'center'
              }}>
                <div style={{ width: '60px', height: '60px', borderRadius: '50%', border: '4px solid #e2e8f0', borderTopColor: '#6366f1', animation: 'spin 1s linear infinite', margin: '0 auto 20px' }} />
                <p style={{ fontWeight: 700, color: '#334155', fontSize: '16px' }}>Running ML Forecast...</p>
                <p style={{ color: '#64748b', fontSize: '13px', marginTop: '6px' }}>Fitting OLS model on {currentDataset.length.toLocaleString()} data points</p>
              </div>
            )}

            {/* ── Results ── */}
            {results && !loading && (
              <>
                {/* KPI Cards */}
                <div style={{
                  background: 'linear-gradient(135deg,#0f172a,#1e1b4b)',
                  borderRadius: '18px', padding: '24px',
                  boxShadow: '0 8px 32px rgba(15,23,42,0.3)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <div>
                      <h3 style={{ color: '#f8fafc', fontSize: '16px', fontWeight: 800, margin: 0 }}>
                        Forecast Results — {metricCol}
                      </h3>
                      <p style={{ color: '#94a3b8', fontSize: '12px', margin: '4px 0 0' }}>{results.answer}</p>
                    </div>
                    <TrendBadge direction={ms.trend_direction || 'stable'} />
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                    <StatCard
                      label="R² Score"
                      value={ms.r_squared !== undefined ? ms.r_squared.toFixed(3) : '—'}
                      sub={ms.r_squared > 0.7 ? 'Good fit' : ms.r_squared > 0.4 ? 'Moderate fit' : 'Weak fit'}
                      color={ms.r_squared > 0.7 ? '#22c55e' : ms.r_squared > 0.4 ? '#f59e0b' : '#ef4444'}
                      icon={Activity}
                    />
                    <StatCard
                      label="MAE"
                      value={ms.mae !== undefined ? ms.mae.toFixed(2) : '—'}
                      sub="Mean Abs. Error"
                      color="#6366f1"
                      icon={Target}
                    />
                    <StatCard
                      label="Slope"
                      value={ms.slope !== undefined ? (ms.slope > 0 ? '+' : '') + ms.slope.toFixed(4) : '—'}
                      sub="per period"
                      color={ms.slope > 0 ? '#22c55e' : '#ef4444'}
                      icon={ms.slope > 0 ? TrendingUp : TrendingDown}
                    />
                    <StatCard
                      label="Historical Growth"
                      value={ms.growth_pct !== undefined ? (ms.growth_pct > 0 ? '+' : '') + ms.growth_pct.toFixed(1) + '%' : '—'}
                      sub="first → last value"
                      color={ms.growth_pct >= 0 ? '#22c55e' : '#ef4444'}
                      icon={ms.growth_pct >= 0 ? ArrowUpRight : ArrowDownRight}
                    />
                    <StatCard
                      label="Forecast End"
                      value={forecastPts.length > 0 ? Number(forecastPts[forecastPts.length - 1].value).toFixed(0) : '—'}
                      sub={`Period: ${forecastPts[forecastPts.length - 1]?.point || '—'}`}
                      color="#a78bfa"
                      icon={Calendar}
                    />
                    <StatCard
                      label="Data Points"
                      value={ms.n_points || currentDataset.length}
                      sub="used in model"
                      color="#38bdf8"
                      icon={BarChart2}
                    />
                  </div>
                </div>

                {/* Chart */}
                <div style={{
                  background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0',
                  padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#0f172a', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Sparkles size={16} color="#6366f1" /> Trend + Forecast Chart
                    </h3>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <button
                        onClick={() => setShowSmoothed(v => !v)}
                        style={{
                          padding: '6px 12px', borderRadius: '8px', border: '1.5px solid #cbd5e1',
                          background: showSmoothed ? '#6366f1' : 'white',
                          color: showSmoothed ? 'white' : '#475569',
                          fontSize: '12px', fontWeight: 600, cursor: 'pointer'
                        }}
                      >
                        {showSmoothed ? '✓ ' : ''}Smoothed Line
                      </button>
                      <button
                        onClick={downloadCSV}
                        style={{
                          padding: '6px 12px', borderRadius: '8px', border: '1.5px solid #cbd5e1',
                          background: 'white', color: '#475569', fontSize: '12px', fontWeight: 600,
                          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
                        }}
                      >
                        <Download size={12} /> Export CSV
                      </button>
                    </div>
                  </div>

                  <div style={{ height: '380px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={displayChartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                        <defs>
                          <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
                          </linearGradient>
                          <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                        <XAxis
                          dataKey="displayDate"
                          tick={{ fontSize: 10, fill: '#94a3b8' }}
                          axisLine={{ stroke: '#e2e8f0' }}
                          tickLine={false}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tick={{ fontSize: 11, fill: '#94a3b8' }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(1)}K` : v}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend
                          wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }}
                          formatter={v => <span style={{ color: '#475569', fontWeight: 600 }}>{v}</span>}
                        />

                        {/* Reference line where forecast begins */}
                        {displayChartData.findIndex(d => d.isForecast) > 0 && (
                          <ReferenceLine
                            x={displayChartData.find(d => d.isForecast)?.displayDate}
                            stroke="#6366f1"
                            strokeDasharray="4 4"
                            label={{ value: 'Forecast →', position: 'insideTopRight', fill: '#6366f1', fontSize: 11, fontWeight: 700 }}
                          />
                        )}

                        <Area
                          type="monotone"
                          dataKey="actual"
                          name="Historical Actuals"
                          stroke="#6366f1"
                          strokeWidth={2}
                          fill="url(#actualGrad)"
                          dot={false}
                          connectNulls={true}
                          activeDot={{ r: 4, fill: '#6366f1' }}
                        />

                        {showSmoothed && (
                          <Line
                            type="monotone"
                            dataKey="smoothed"
                            name="Smoothed (3-MA)"
                            stroke="#38bdf8"
                            strokeWidth={1.5}
                            strokeDasharray="4 2"
                            dot={false}
                            connectNulls={true}
                          />
                        )}

                        <Area
                          type="monotone"
                          dataKey="predicted"
                          name="Forecast Projection"
                          stroke="#f59e0b"
                          strokeWidth={2.5}
                          strokeDasharray="6 3"
                          fill="url(#forecastGrad)"
                          dot={false}
                          connectNulls={true}
                          activeDot={{ r: 4, fill: '#f59e0b' }}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Metric Stats + Model Info */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

                  {/* Metric Summary */}
                  <div style={{ background: 'white', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 800, color: '#334155', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                      <BarChart2 size={14} color="#6366f1" /> Metric Statistics — {metricCol}
                    </h4>
                    {[
                      ['Total Sum', mst.sum?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—'],
                      ['Average', mst.mean?.toFixed(2) ?? '—'],
                      ['Minimum', mst.min?.toFixed(2) ?? '—'],
                      ['Maximum', mst.max?.toFixed(2) ?? '—'],
                      ['Std Deviation', mst.std?.toFixed(2) ?? '—'],
                      ['Row Count', mst.count?.toLocaleString() ?? '—'],
                    ].map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                        <span style={{ color: '#64748b', fontSize: '12px' }}>{k}</span>
                        <span style={{ color: '#0f172a', fontWeight: 700, fontSize: '13px' }}>{v}</span>
                      </div>
                    ))}
                  </div>

                  {/* Model Info */}
                  <div style={{ background: 'white', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 800, color: '#334155', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                      <Activity size={14} color="#8b5cf6" /> Model Performance
                    </h4>
                    {[
                      ['Algorithm', 'OLS Linear Regression'],
                      ['R² (Fit Quality)', ms.r_squared?.toFixed(4) ?? '—'],
                      ['MAE', ms.mae?.toFixed(4) ?? '—'],
                      ['Slope', ms.slope !== undefined ? (ms.slope > 0 ? '+' : '') + ms.slope.toFixed(6) : '—'],
                      ['Trend Direction', ms.trend_direction ? ms.trend_direction.charAt(0).toUpperCase() + ms.trend_direction.slice(1) : '—'],
                      ['Historical Growth', ms.growth_pct !== undefined ? (ms.growth_pct > 0 ? '+' : '') + ms.growth_pct.toFixed(2) + '%' : '—'],
                    ].map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                        <span style={{ color: '#64748b', fontSize: '12px' }}>{k}</span>
                        <span style={{ color: '#0f172a', fontWeight: 700, fontSize: '13px' }}>{v}</span>
                      </div>
                    ))}

                    {ms.r_squared !== undefined && (
                      <div style={{ marginTop: '12px', padding: '10px', background: ms.r_squared > 0.7 ? '#f0fdf4' : ms.r_squared > 0.4 ? '#fffbeb' : '#fef2f2', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {ms.r_squared > 0.7
                          ? <><Activity size={13} color="#22c55e" /><span style={{ fontSize: '12px', color: '#15803d', fontWeight: 600 }}>Good model fit (R² &gt; 0.7) — forecast is reliable.</span></>
                          : ms.r_squared > 0.4
                          ? <><AlertTriangle size={13} color="#d97706" /><span style={{ fontSize: '12px', color: '#b45309', fontWeight: 600 }}>Moderate fit — treat forecast as directional only.</span></>
                          : <><AlertCircle size={13} color="#dc2626" /><span style={{ fontSize: '12px', color: '#b91c1c', fontWeight: 600 }}>Weak fit — data may not follow a linear trend.</span></>
                        }
                      </div>
                    )}
                  </div>
                </div>

                {/* Forecast Table */}
                <div style={{ background: 'white', borderRadius: '16px', border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
                  <button
                    onClick={() => setShowTable(v => !v)}
                    style={{ width: '100%', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    <span style={{ fontSize: '14px', fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Calendar size={15} color="#6366f1" /> Forecast Table ({forecastPts.length} periods)
                    </span>
                    {showTable ? <ChevronUp size={16} color="#94a3b8" /> : <ChevronDown size={16} color="#94a3b8" />}
                  </button>

                  {showTable && (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ background: '#f8fafc' }}>
                            <th style={{ padding: '10px 20px', textAlign: 'left', color: '#475569', fontWeight: 700, fontSize: '11px', textTransform: 'uppercase', borderBottom: '1px solid #e2e8f0' }}>#</th>
                            <th style={{ padding: '10px 20px', textAlign: 'left', color: '#475569', fontWeight: 700, fontSize: '11px', textTransform: 'uppercase', borderBottom: '1px solid #e2e8f0' }}>Period</th>
                            <th style={{ padding: '10px 20px', textAlign: 'right', color: '#475569', fontWeight: 700, fontSize: '11px', textTransform: 'uppercase', borderBottom: '1px solid #e2e8f0' }}>Predicted {metricCol}</th>
                            <th style={{ padding: '10px 20px', textAlign: 'right', color: '#475569', fontWeight: 700, fontSize: '11px', textTransform: 'uppercase', borderBottom: '1px solid #e2e8f0' }}>Trend</th>
                          </tr>
                        </thead>
                        <tbody>
                          {forecastPts.map((pt, i) => {
                            const prev = i > 0 ? forecastPts[i - 1].value : null;
                            const delta = prev !== null ? pt.value - prev : null;
                            return (
                              <tr key={i} style={{ background: i % 2 === 0 ? 'white' : '#fafafa' }}>
                                <td style={{ padding: '10px 20px', color: '#94a3b8', fontWeight: 600 }}>{i + 1}</td>
                                <td style={{ padding: '10px 20px', color: '#334155', fontWeight: 600 }}>{String(pt.point)}</td>
                                <td style={{ padding: '10px 20px', textAlign: 'right', color: '#6366f1', fontWeight: 700 }}>{Number(pt.value).toFixed(2)}</td>
                                <td style={{ padding: '10px 20px', textAlign: 'right' }}>
                                  {delta !== null ? (
                                    <span style={{ color: delta >= 0 ? '#22c55e' : '#ef4444', fontWeight: 600, fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '3px' }}>
                                      {delta >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                      {delta >= 0 ? '+' : ''}{delta.toFixed(2)}
                                    </span>
                                  ) : <span style={{ color: '#94a3b8', fontSize: '12px' }}>—</span>}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Recommendations */}
                {results.recommendations?.length > 0 && (
                  <div style={{ background: 'linear-gradient(135deg,#f0f9ff,#e0f2fe)', borderRadius: '16px', border: '1px solid #bae6fd', padding: '20px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 800, color: '#0369a1', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '7px' }}>
                      <Sparkles size={14} /> AI Recommendations
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {results.recommendations.map((rec, i) => (
                        <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                          <span style={{ background: '#0369a1', color: 'white', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, flexShrink: 0, marginTop: '1px' }}>{i + 1}</span>
                          <p style={{ color: '#0c4a6e', fontSize: '13px', margin: 0, lineHeight: '1.5' }}>{rec}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}

            {/* ── Tab 2: AutoML Predictor (XAI) ── */}
            {predictiveTab === 'automl' && (
              <div style={{ background: 'white', borderRadius: '18px', border: '1px solid rgba(125,157,191,0.15)', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }} className="dark:bg-neutral-900 dark:border-neutral-800">
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }} className="dark:text-slate-400">
                    🎯 Select Target Column for AutoML Estimator
                  </label>
                  <select
                    value={automlTarget}
                    onChange={e => setAutomlTarget(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #cbd5e1', borderRadius: '10px', fontSize: '13px', background: 'white', color: '#0f172a', outline: 'none' }}
                  >
                    <option value="">-- Select target column --</option>
                    {columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <AutoMLWidget 
                  file={fileObject} 
                  targetColumn={automlTarget} 
                  rows={currentDataset} 
                  onResult={(res) => console.log('AutoML completed:', res)} 
                />
              </div>
            )}

            {/* ── Tab 3: Clustering & NLP ── */}
            {predictiveTab === 'nlp' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ background: 'white', borderRadius: '18px', border: '1px solid rgba(125,157,191,0.15)', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }} className="dark:bg-neutral-900 dark:border-neutral-800">
                  <AIEngineWidget 
                    rows={currentDataset} 
                    availableColumns={columns} 
                    onUpdateData={(newData) => {
                      useDataStore.setState({ cleanedData: newData });
                      alert('NLP classification applied successfully! Check Data Workspace for new category values.');
                    }} 
                  />
                </div>
                
                {/* Clustering Action */}
                <div style={{ background: 'white', borderRadius: '18px', border: '1px solid rgba(125,157,191,0.15)', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }} className="dark:bg-neutral-900 dark:border-neutral-800">
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#334155', marginBottom: '8px' }} className="dark:text-white">No-Code K-Means Clustering</h3>
                  <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px' }} className="dark:text-slate-400">Autonomously run K-Means partitions on numeric vector columns of the dataset.</p>
                  <button 
                    onClick={async () => {
                      try {
                        const response = await apiService.post('/api/run-clustering', { rows: currentDataset });
                        if (response.data.data) {
                          useDataStore.setState({ cleanedData: response.data.data });
                          alert('Clustering complete! Added "cluster" label column to dataset.');
                        }
                      } catch (err) {
                        alert('Clustering failed: ' + (err?.response?.data?.detail || err.message));
                      }
                    }}
                    style={{ padding: '10px 16px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '10px', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}
                  >
                    Execute K-Means Clustering
                  </button>
                </div>
              </div>
            )}

          </div>
        )}

        {/* CSS spin animation */}
        <style>{`
          @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        `}</style>
      </div>
    </DashboardLayout>
  );
}
