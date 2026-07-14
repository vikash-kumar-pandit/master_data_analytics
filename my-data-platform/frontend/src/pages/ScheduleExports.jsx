import React, { useState, useEffect } from 'react';
import DashboardLayout from '../DashboardLayout';
import useDataStore from '../store';
import { Calendar, Trash2, CheckCircle, AlertCircle } from 'lucide-react';

export default function ScheduleExports() {
  const { schedulesList, getSchedules, createSchedule, deleteSchedule } = useDataStore();

  const [scheduleName, setScheduleName] = useState('');
  const [scheduleCron, setScheduleCron] = useState('0 8 * * *');
  const [scheduleEmail, setScheduleEmail] = useState('');
  const [scheduleFormat, setScheduleFormat] = useState('pdf');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    getSchedules();
  }, [getSchedules]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!scheduleName.trim() || !scheduleCron.trim()) return;

    setLoading(true);
    setMessage('');
    setErrorMsg('');

    try {
      await createSchedule({
        name: scheduleName,
        description: `Scheduled report delivery cron: ${scheduleCron}`,
        report_config: { title: scheduleName, subtitle: "Automated Data Report", sections: [] },
        schedule_cron: scheduleCron,
        export_format: scheduleFormat,
        recipients: scheduleEmail ? [scheduleEmail] : [],
        enabled: true
      });
      setMessage('Schedule created successfully!');
      setScheduleName('');
      setScheduleEmail('');
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to create scheduling task.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto font-sans">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-slate-900 flex items-center gap-3">
            <Calendar className="w-8 h-8 text-blue-600" />
            Scheduled Exports
          </h1>
          <p className="text-slate-500 mt-2 text-sm">
            Set up and manage automated PDF/PPTX report deliveries directly to team emails.
          </p>
        </div>

        {message && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm flex items-center gap-3 mb-6">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <span>{message}</span>
          </div>
        )}

        {errorMsg && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-3 mb-6">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Creation Form */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm h-fit">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Create Schedule Task</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Schedule Name</label>
                <input
                  type="text"
                  required
                  value={scheduleName}
                  onChange={(e) => setScheduleName(e.target.value)}
                  placeholder="e.g. Weekly Operations Summary"
                  className="w-full p-2.5 border border-slate-350 rounded-lg text-sm bg-slate-50 focus:bg-white transition outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Cron Expression</label>
                <input
                  type="text"
                  required
                  value={scheduleCron}
                  onChange={(e) => setScheduleCron(e.target.value)}
                  placeholder="e.g. 0 8 * * *"
                  className="w-full p-2.5 border border-slate-350 rounded-lg text-sm font-mono bg-slate-50 focus:bg-white transition outline-none"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">Daily at 8:00 AM is `0 8 * * *`</span>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Recipient Email</label>
                <input
                  type="email"
                  value={scheduleEmail}
                  onChange={(e) => setScheduleEmail(e.target.value)}
                  placeholder="e.g. admin@datasaas.local"
                  className="w-full p-2.5 border border-slate-350 rounded-lg text-sm bg-slate-50 focus:bg-white transition outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Export Format</label>
                <select
                  value={scheduleFormat}
                  onChange={(e) => setScheduleFormat(e.target.value)}
                  className="w-full p-2.5 border border-slate-350 rounded-lg text-sm bg-slate-50 focus:bg-white transition outline-none"
                >
                  <option value="pdf">PDF Document</option>
                  <option value="pptx">PowerPoint Presentation</option>
                  <option value="csv">Raw CSV File</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg text-sm transition shadow-md"
              >
                {loading ? 'Creating...' : 'Create Scheduled Task'}
              </button>
            </form>
          </div>

          {/* Active List */}
          <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Active Scheduling Tasks</h3>
            {schedulesList.length === 0 ? (
              <p className="text-slate-400 text-sm italic">No active scheduled exports created yet.</p>
            ) : (
              <div className="space-y-4">
                {schedulesList.map((sched) => (
                  <div key={sched.id} className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex justify-between items-center">
                    <div>
                      <p className="font-bold text-slate-800">{sched.name}</p>
                      <p className="text-xs text-slate-500 font-mono mt-1">Cron: {sched.schedule_cron} · Format: {sched.export_format.toUpperCase()}</p>
                      {sched.next_run && <p className="text-[10px] text-slate-400 mt-1">Next Run: {new Date(sched.next_run).toLocaleString()}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-2.5 py-1 text-[10px] font-bold rounded-full ${sched.enabled ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                        {sched.enabled ? 'Active' : 'Paused'}
                      </span>
                      <button
                        onClick={async () => {
                          if (window.confirm("Are you sure you want to delete this schedule?")) {
                            await deleteSchedule(sched.id);
                            setMessage("Schedule deleted successfully!");
                            setTimeout(() => setMessage(''), 3000);
                          }
                        }}
                        className="text-red-500 hover:text-red-700 p-1.5 rounded-lg hover:bg-red-50 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
    </DashboardLayout>
  );
}
