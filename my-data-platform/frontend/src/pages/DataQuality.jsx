import React, { useEffect, useState } from 'react';
import DashboardLayout from '../DashboardLayout';
import apiService from '../api/client';
import { useToast } from '../context/NotificationContext';

export default function DataQuality() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const { error } = useToast();

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const payload = { /* optional filters */ };
        const res = await apiService.quality.getReport(payload);
        setReport(res);
      } catch (err) {
        console.error(err);
        error('Failed to load data quality report');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [error]);

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Data Quality Monitoring</h1>
        {loading && <div>Loading…</div>}
        {!loading && !report && <div>No quality report available.</div>}
        {report && (
          <div>
            <div className="grid grid-cols-3 gap-4 mb-6">
              {(report.metrics || []).map((m, i) => (
                <div key={i} className="p-4 border rounded bg-white dark:bg-slate-800">
                  <div className="text-sm text-slate-500">{m.name}</div>
                  <div className="text-xl font-bold">{m.value}</div>
                </div>
              ))}
            </div>

            <div className="space-y-4">
              {(report.details || []).map((d, i) => (
                <div key={i} className="p-3 border rounded bg-white dark:bg-slate-800">
                  <div className="font-medium">{d.section}</div>
                  <pre className="text-sm mt-2">{JSON.stringify(d.summary || d, null, 2)}</pre>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
