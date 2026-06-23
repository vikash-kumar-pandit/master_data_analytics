import React, { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import DataInsightsChart from './DataInsightsChart';
import DataCompareChart from './DataCompareChart';

const GRAPH_OPTIONS = [
  { key: 'quality', label: 'Quality Stack' },
  { key: 'compare', label: 'Before vs After' },
  { key: 'missingTop', label: 'Top Missing Columns' },
  { key: 'severity', label: 'Audit Severity Mix' },
];

const PIE_COLORS = ['#0ea5e9', '#f97316', '#ef4444', '#22c55e', '#a855f7'];

function ChartEmpty({ title, message }) {
  return (
    <div className="chart-shell chart-empty-shell">
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}

export default function MultiGraphPanel({
  qualityData = [],
  compareData = [],
  auditErrors = [],
  selectedGraphKeys = [],
  onChange,
}) {
  const missingTopData = useMemo(
    () => [...qualityData].sort((a, b) => Number(b.missing || 0) - Number(a.missing || 0)).slice(0, 10),
    [qualityData]
  );

  const severityData = useMemo(() => {
    const counters = {};
    auditErrors.forEach((issue) => {
      const severity = String(issue?.severity || 'Unknown');
      counters[severity] = (counters[severity] || 0) + 1;
    });

    return Object.entries(counters).map(([severity, count]) => ({ severity, count }));
  }, [auditErrors]);

  const toggleGraph = (key) => {
    const exists = selectedGraphKeys.includes(key);
    if (exists) {
      const next = selectedGraphKeys.filter((value) => value !== key);
      if (next.length) {
        onChange(next);
      }
      return;
    }
    onChange([...selectedGraphKeys, key]);
  };

  const activateAll = () => onChange(GRAPH_OPTIONS.map((item) => item.key));
  const clearToDefault = () => onChange(['quality']);

  return (
    <div className="multi-graph-shell">
      <div className="multi-graph-header">
        <h3>Multi Graph Explorer</h3>
        <div className="multi-graph-actions">
          <button type="button" onClick={activateAll}>Show All</button>
          <button type="button" onClick={clearToDefault}>Focus Main</button>
        </div>
      </div>

      <p className="multi-graph-copy">Choose one or more visualizations and inspect data from different angles.</p>

      <div className="multi-graph-selector" role="group" aria-label="Select chart views">
        {GRAPH_OPTIONS.map((option) => {
          const active = selectedGraphKeys.includes(option.key);
          return (
            <button
              key={option.key}
              type="button"
              className={active ? 'graph-toggle active' : 'graph-toggle'}
              onClick={() => toggleGraph(option.key)}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <div className="multi-graph-grid">
        {selectedGraphKeys.includes('quality') ? (
          qualityData.length ? (
            <DataInsightsChart data={qualityData} />
          ) : (
            <ChartEmpty title="Data Quality Overview" message="Upload and analyze data to render this graph." />
          )
        ) : null}

        {selectedGraphKeys.includes('compare') ? (
          compareData.length ? (
            <DataCompareChart data={compareData} />
          ) : (
            <ChartEmpty title="Before vs After Data Cleaning" message="Run clean data flow to compare before and after issues." />
          )
        ) : null}

        {selectedGraphKeys.includes('missingTop') ? (
          missingTopData.length ? (
            <div className="chart-shell">
              <h3>Top Missing Columns</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={missingTopData} margin={{ top: 20, right: 20, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                  <XAxis dataKey="columnName" stroke="#334155" angle={-22} textAnchor="end" interval={0} height={86} />
                  <YAxis stroke="#334155" allowDecimals={false} />
                  <Tooltip
                    cursor={{ fill: 'rgba(15, 23, 42, 0.06)' }}
                    contentStyle={{ backgroundColor: '#0f172a', color: '#f8fafc', borderRadius: '10px', border: 'none' }}
                    labelStyle={{ color: '#f8fafc' }}
                  />
                  <Legend />
                  <Bar dataKey="missing" fill="#f97316" name="Missing Count" animationDuration={1200} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <ChartEmpty title="Top Missing Columns" message="No missing-value data available right now." />
          )
        ) : null}

        {selectedGraphKeys.includes('severity') ? (
          severityData.length ? (
            <div className="chart-shell">
              <h3>Audit Severity Mix</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={severityData} dataKey="count" nameKey="severity" outerRadius={98} label>
                    {severityData.map((item, index) => (
                      <Cell key={item.severity} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <ChartEmpty title="Audit Severity Mix" message="No audit issues found to build severity distribution." />
          )
        ) : null}
      </div>
    </div>
  );
}
