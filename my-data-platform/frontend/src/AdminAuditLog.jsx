import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from './context/AuthContext';
import { API_BASE_URL } from './config';
import './styles.css';

export default function AdminAuditLog() {
  const { user, getAuthHeaders } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [eventFilter, setEventFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchAuditLogs = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/auth/audit-log?limit=${limit}&offset=${offset}`,
        {
          headers: getAuthHeaders(),
        }
      );
      setLogs(response.data.logs || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchAuditLogs();
    }
  }, [limit, offset, user?.role]);

  // Filter logs based on event type and search term
  const filteredLogs = logs.filter((log) => {
    const matchesEvent = !eventFilter || log.event_type === eventFilter;
    const matchesSearch =
      !searchTerm ||
      log.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.client_ip?.includes(searchTerm);
    return matchesEvent && matchesSearch;
  });

  // Get unique event types for filter dropdown
  const eventTypes = [...new Set(logs.map((log) => log.event_type))];

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  const getStatusBadge = (status) => {
    return (
      <span className={`badge badge-${status}`}>
        {status}
      </span>
    );
  };

  if (user?.role !== 'admin') {
    return (
      <div className="audit-log-container">
        <h2>Access Denied</h2>
        <p>Only administrators can view audit logs.</p>
      </div>
    );
  }

  return (
    <div className="audit-log-container">
      <h2>Audit Log</h2>
      <p style={{ color: '#666', fontSize: '14px', marginBottom: '20px' }}>
        Track all authentication and authorization events
      </p>

      {error && (
        <div style={{
          backgroundColor: '#fee',
          border: '1px solid #f99',
          color: '#c33',
          padding: '12px',
          borderRadius: '4px',
          marginBottom: '16px',
        }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: '20px' }}>
        <div style={{ marginBottom: '12px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <label htmlFor="search-term" style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>
              Search (username, email, IP):
            </label>
            <input
              id="search-term"
              type="text"
              placeholder="e.g., admin@example.com or 192.168.1.1"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            />
          </div>

          <div style={{ flex: 1, minWidth: '200px' }}>
            <label htmlFor="event-filter" style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>
              Event Type:
            </label>
            <select
              id="event-filter"
              value={eventFilter}
              onChange={(e) => {
                setEventFilter(e.target.value);
                setOffset(0);
              }}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            >
              <option value="">All Events</option>
              {eventTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
            <button
              onClick={() => {
                setOffset(0);
                fetchAuditLogs();
              }}
              style={{
                padding: '8px 16px',
                backgroundColor: '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
              }}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', fontSize: '14px' }}>
          <label htmlFor="limit">
            Rows per page:
            <select
              id="limit"
              value={limit}
              onChange={(e) => {
                setLimit(parseInt(e.target.value));
                setOffset(0);
              }}
              style={{ marginLeft: '8px', padding: '4px' }}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={250}>250</option>
            </select>
          </label>
        </div>
      </div>

      {loading ? (
        <p>Loading audit logs...</p>
      ) : filteredLogs.length === 0 ? (
        <p>No audit logs found.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            border: '1px solid #ddd',
          }}>
            <thead>
              <tr style={{ backgroundColor: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '12px', textAlign: 'left', borderRight: '1px solid #ddd' }}>Timestamp</th>
                <th style={{ padding: '12px', textAlign: 'left', borderRight: '1px solid #ddd' }}>Event Type</th>
                <th style={{ padding: '12px', textAlign: 'left', borderRight: '1px solid #ddd' }}>Username</th>
                <th style={{ padding: '12px', textAlign: 'left', borderRight: '1px solid #ddd' }}>Email</th>
                <th style={{ padding: '12px', textAlign: 'left', borderRight: '1px solid #ddd' }}>Client IP</th>
                <th style={{ padding: '12px', textAlign: 'left', borderRight: '1px solid #ddd' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Message</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '12px', borderRight: '1px solid #ddd', fontSize: '13px' }}>
                    {formatDate(log.timestamp)}
                  </td>
                  <td style={{ padding: '12px', borderRight: '1px solid #ddd', fontSize: '13px' }}>
                    <code style={{
                      backgroundColor: '#f0f0f0',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      fontFamily: 'monospace',
                    }}>
                      {log.event_type}
                    </code>
                  </td>
                  <td style={{ padding: '12px', borderRight: '1px solid #ddd', fontSize: '13px' }}>
                    {log.username || '—'}
                  </td>
                  <td style={{ padding: '12px', borderRight: '1px solid #ddd', fontSize: '13px' }}>
                    {log.email || '—'}
                  </td>
                  <td style={{ padding: '12px', borderRight: '1px solid #ddd', fontSize: '13px' }}>
                    <code style={{
                      backgroundColor: '#f0f0f0',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      fontFamily: 'monospace',
                    }}>
                      {log.client_ip || '—'}
                    </code>
                  </td>
                  <td style={{ padding: '12px', borderRight: '1px solid #ddd', fontSize: '13px' }}>
                    {getStatusBadge(log.status)}
                  </td>
                  <td style={{ padding: '12px', fontSize: '13px' }}>
                    {log.message || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '14px' }}>
        <button
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0 || loading}
          style={{
            padding: '8px 16px',
            marginRight: '8px',
            backgroundColor: offset === 0 ? '#ccc' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: offset === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          Previous
        </button>
        <span style={{ margin: '0 12px' }}>
          Showing {filteredLogs.length} of {logs.length} logs (offset: {offset})
        </span>
        <button
          onClick={() => setOffset(offset + limit)}
          disabled={logs.length < limit || loading}
          style={{
            padding: '8px 16px',
            marginLeft: '8px',
            backgroundColor: logs.length < limit ? '#ccc' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: logs.length < limit ? 'not-allowed' : 'pointer',
          }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
