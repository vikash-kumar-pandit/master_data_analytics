import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export default function DataCompareChart({ data = [] }) {
  if (!data.length) {
    return null;
  }

  return (
    <div className="compare-chart-shell">
      <h3>Before vs After Data Cleaning</h3>

      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
          <XAxis dataKey="columnName" stroke="#334155" angle={-20} textAnchor="end" interval={0} height={72} />
          <YAxis stroke="#334155" allowDecimals={false} />
          <Tooltip
            cursor={{ fill: 'rgba(15, 23, 42, 0.06)' }}
            contentStyle={{ backgroundColor: '#0f172a', color: '#f8fafc', borderRadius: '10px', border: 'none' }}
            labelStyle={{ color: '#f8fafc' }}
          />
          <Legend />
          <Bar dataKey="missingBefore" fill="#ef4444" name="Missing Issues (Before)" animationDuration={1200} />
          <Bar dataKey="missingAfter" fill="#16a34a" name="Missing Issues (After)" animationDuration={1200} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}