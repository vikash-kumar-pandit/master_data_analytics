import React, { useState } from 'react';
import DashboardLayout from '../DashboardLayout';
import apiService from '../api/client';
import { useToast } from '../context/NotificationContext';

export default function ScheduleExports() {
  const [loading, setLoading] = useState(false);
  const [cron, setCron] = useState('0 8 * * *');
  const [email, setEmail] = useState('');
  const { success, error } = useToast();

  const createSchedule = async () => {
    setLoading(true);
    try {
      const payload = {
        report_title: 'Scheduled Analytics Report',
        report_data: { /* can include last used template or empty */ },
        cron_expression: cron,
        notify_emails: [email].filter(Boolean),
      };

      await apiService.schedule.create(payload);
      success('Schedule created');
      setEmail('');
    } catch (err) {
      console.error(err);
      error('Failed to create schedule');
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Schedule Exports</h1>

        <div className="mb-4">
          <label className="block mb-1">Cron expression</label>
          <input value={cron} onChange={(e) => setCron(e.target.value)} className="p-2 border rounded w-64" />
          <div className="text-sm text-slate-500 mt-2">Example: <code>0 8 * * *</code> (every day at 08:00)</div>
        </div>

        <div className="mb-4">
          <label className="block mb-1">Notify email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} className="p-2 border rounded w-64" />
        </div>

        <div>
          <button onClick={createSchedule} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded">{loading ? 'Creating…' : 'Create Schedule'}</button>
        </div>
      </div>
    </DashboardLayout>
  );
}
