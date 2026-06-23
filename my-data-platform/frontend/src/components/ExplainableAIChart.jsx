import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function ExplainableAIChart({ featureData }) {
  if (!Array.isArray(featureData) || featureData.length === 0) {
    return null;
  }

  return (
    <div className="xai-chart-shell">
      <h3>Explainable AI: Top Prediction Drivers</h3>
      <p>These features had the highest impact on model behavior.</p>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart layout="vertical" data={featureData} margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
          <XAxis type="number" hide />
          <YAxis dataKey="feature" type="category" width={140} tick={{ fill: '#334155', fontSize: 12 }} />
          <Tooltip
            cursor={{ fill: 'rgba(56, 189, 248, 0.1)' }}
            formatter={(value) => [Number(value).toFixed(4), 'Impact']}
          />
          <Bar dataKey="impact" fill="#0ea5e9" radius={[0, 8, 8, 0]} animationDuration={900} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
