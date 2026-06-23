import React, { useState } from 'react';
import DashboardLayout from '../DashboardLayout';
import apiService from '../api/client';
import { useToast } from '../context/NotificationContext';

export default function PredictiveAnalytics() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [horizon, setHorizon] = useState(30);
  const { error } = useToast();

  const runForecast = async () => {
    setLoading(true);
    try {
      const payload = { horizon };
      const res = await apiService.forecasting.forecast(payload);
      setResults(res);
    } catch (err) {
      console.error(err);
      error('Forecast failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Predictive Analytics</h1>
        <div className="mb-4">
          <label className="block mb-1">Forecast horizon (days)</label>
          <input type="number" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="p-2 border rounded w-32" />
          <button onClick={runForecast} disabled={loading} className="ml-3 px-3 py-2 bg-blue-600 text-white rounded">{loading ? 'Running…' : 'Run Forecast'}</button>
        </div>

        {results && (
          <div className="mt-6">
            <h2 className="text-lg font-medium mb-2">Forecast Results</h2>
            <pre className="bg-white dark:bg-slate-800 p-3 rounded">{JSON.stringify(results, null, 2)}</pre>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
