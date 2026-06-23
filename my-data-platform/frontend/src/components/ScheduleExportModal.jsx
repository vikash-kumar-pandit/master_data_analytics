import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

export default function ScheduleExportModal({ onClose }) {
  const [schedules, setSchedules] = useState([]);
  const [name, setName] = useState('Weekly Export');
  const [description, setDescription] = useState('');
  const [cronExpression, setCronExpression] = useState('0 9 * * MON');
  const [exportFormat, setExportFormat] = useState('pdf');
  const [recipients, setRecipients] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadSchedules();
  }, []);

  const loadSchedules = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/schedule/my-schedules`, {
        headers: { 'Content-Type': 'application/json' },
      });
      setSchedules(response.data.schedules || []);
      setError('');
    } catch (err) {
      console.error('Failed to load schedules:', err);
      setError(err?.response?.data?.detail || 'Failed to load schedules.');
      setSchedules([]);
    }
  };

  const validateInputs = () => {
    if (!name || !name.trim()) {
      setError('Schedule name is required.');
      return false;
    }
    if (!cronExpression || !cronExpression.trim()) {
      setError('Cron expression is required.');
      return false;
    }
    if (name.length > 100) {
      setError('Schedule name cannot exceed 100 characters.');
      return false;
    }
    return true;
  };

  const handleCreateSchedule = async () => {
    if (!validateInputs()) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const recipientList = recipients
        .split(',')
        .map((r) => r.trim())
        .filter(Boolean);

      // Validate emails if provided
      for (const email of recipientList) {
        if (!email.includes('@')) {
          setError(`Invalid email format: ${email}`);
          setLoading(false);
          return;
        }
      }

      const response = await axios.post(`${API_BASE_URL}/api/schedule/create`, {
        name: name.substring(0, 100),
        description: description.substring(0, 500),
        report_config: { auto_refresh: true },
        schedule_cron: cronExpression.substring(0, 50),
        export_format: exportFormat,
        recipients: recipientList,
        enabled: true,
      }, {
        headers: { 'Content-Type': 'application/json' },
        timeout: 15000,
      });

      if (response.data?.id) {
        setSuccess('✓ Schedule created successfully!');
        setName('Weekly Export');
        setDescription('');
        setCronExpression('0 9 * * MON');
        setExportFormat('pdf');
        setRecipients('');
        await loadSchedules();
      } else {
        setError('Schedule created but no ID returned.');
      }
    } catch (err) {
      console.error('Schedule creation failed:', err);
      const detail = err?.response?.data?.detail;
      if (err.code === 'ECONNABORTED') {
        setError('Request timeout. Please try again.');
      } else {
        setError(detail || 'Failed to create schedule. Please check your inputs.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSchedule = async (id) => {
    if (!window.confirm('Delete this schedule?')) return;

    try {
      await axios.delete(`${API_BASE_URL}/api/schedule/${id}`);
      setSuccess('✓ Schedule deleted.');
      setError('');
      await loadSchedules();
    } catch (err) {
      console.error('Delete failed:', err);
      setError(err?.response?.data?.detail || 'Failed to delete schedule.');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Scheduled Exports</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="schedule-form">
            <h3>Create New Schedule</h3>

            <label>
              Schedule Name *
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Weekly Report"
                disabled={loading}
                maxLength="100"
              />
              <small>{name.length}/100</small>
            </label>

            <label>
              Description
              <textarea
                rows="2"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                disabled={loading}
                maxLength="500"
              />
              <small>{description.length}/500</small>
            </label>

            <label>
              Cron Expression *
              <input
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                placeholder="0 9 * * MON"
                disabled={loading}
              />
              <small>minute hour day month weekday (0=Sunday)</small>
            </label>

            <label>
              Export Format
              <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)} disabled={loading}>
                <option value="pdf">PDF</option>
                <option value="pptx">PowerPoint</option>
                <option value="csv">CSV</option>
                <option value="bundle">PDF + PPTX + CSV</option>
              </select>
            </label>

            <label>
              Recipients (emails, comma-separated)
              <textarea
                rows="2"
                value={recipients}
                onChange={(e) => setRecipients(e.target.value)}
                placeholder="user@example.com, another@example.com"
                disabled={loading}
              />
            </label>

            <button
              type="button"
              onClick={handleCreateSchedule}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Creating...' : 'Create Schedule'}
            </button>
          </div>

          {error && <p className="error">⚠️ {error}</p>}
          {success && <p className="success">{success}</p>}

          <div className="schedule-list">
            <h3>My Schedules ({schedules.length})</h3>
            {schedules.length ? (
              schedules.map((schedule) => (
                <div key={schedule.id} className="schedule-item">
                  <div>
                    <strong>{schedule.name}</strong>
                    {schedule.description && <p>{schedule.description}</p>}
                    <small>Cron: {schedule.schedule_cron}</small>
                    <small>Format: {schedule.export_format} | Status: {schedule.last_status || 'pending'}</small>
                    <small>Runs: {schedule.run_count} | Next: {schedule.next_run ? new Date(schedule.next_run).toLocaleDateString() : 'N/A'}</small>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteSchedule(schedule.id)}
                    className="btn-danger-small"
                    disabled={loading}
                  >
                    Delete
                  </button>
                </div>
              ))
            ) : (
              <p>No schedules created yet.</p>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
