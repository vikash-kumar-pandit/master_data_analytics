import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

export default function ShareModal({ result, onClose, onShareCreated }) {
  const [shares, setShares] = useState([]);
  const [expiryDays, setExpiryDays] = useState(30);
  const [accessLevel, setAccessLevel] = useState('view');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copySuccess, setCopySuccess] = useState('');

  useEffect(() => {
    loadMyShares();
  }, []);

  const loadMyShares = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/share/my-shares`, {
        headers: { 'Content-Type': 'application/json' },
      });
      setShares(response.data.shares || []);
      setError('');
    } catch (err) {
      console.error('Failed to load shares:', err);
      setError(err?.response?.data?.detail || 'Failed to load shares. Please try again.');
      setShares([]);
    }
  };

  const handleCreateShare = async () => {
    if (!result) {
      setError('Run an analysis first to share.');
      return;
    }

    // Validate inputs
    const days = Number(expiryDays);
    if (!days || days < 1 || days > 365) {
      setError('Expiry must be between 1 and 365 days.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/share/create`, {
        report_title: (result.report_title || 'Analytics Report').substring(0, 200),
        report_data: result,
        expires_days: days,
        access_level: accessLevel,
      }, {
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.data?.token) {
        setSuccess(`✓ Share link created! Copy the URL to share.`);
        setCopySuccess('');
        setExpiryDays(30);
        setAccessLevel('view');
        await loadMyShares();
        onShareCreated?.(response.data);
      } else {
        setError('Share created but no token returned.');
      }
    } catch (err) {
      console.error('Share creation failed:', err);
      const detail = err?.response?.data?.detail;
      setError(detail || 'Failed to create share. Please check your inputs and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeShare = async (token) => {
    if (!window.confirm('Are you sure you want to revoke this share?')) return;

    try {
      await axios.delete(`${API_BASE_URL}/api/share/${token}`);
      setSuccess('✓ Share revoked.');
      setCopySuccess('');
      await loadMyShares();
      setError('');
    } catch (err) {
      console.error('Revoke failed:', err);
      setError(err?.response?.data?.detail || 'Failed to revoke share.');
    }
  };

  const handleCopyToken = (token) => {
    const shareUrl = `${window.location.origin}/share/${token}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopySuccess('✓ Share URL copied to clipboard!');
      setTimeout(() => setCopySuccess(''), 3000);
    }).catch(() => {
      setCopySuccess('Failed to copy. Please copy manually.');
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Share Report</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="share-form">
            <label>
              Expires in (days)
              <input
                type="number"
                min="1"
                max="365"
                value={expiryDays}
                onChange={(e) => setExpiryDays(e.target.value)}
                disabled={loading}
              />
            </label>

            <label>
              Access Level
              <select value={accessLevel} onChange={(e) => setAccessLevel(e.target.value)} disabled={loading}>
                <option value="view">View only</option>
                <option value="download">Allow download</option>
              </select>
            </label>

            <button
              type="button"
              onClick={handleCreateShare}
              disabled={loading || !result}
              className="btn-primary"
            >
              {loading ? 'Creating...' : 'Create Share Link'}
            </button>
          </div>

          {error && <p className="error">⚠️ {error}</p>}
          {success && <p className="success">{success}</p>}
          {copySuccess && <p className="info">{copySuccess}</p>}

          <div className="share-history">
            <h3>My Shares ({shares.length})</h3>
            {shares.length ? (
              <div className="share-list">
                {shares.map((share) => (
                  <div key={share.token} className="share-item">
                    <div className="share-info">
                      <strong>{share.report_title}</strong>
                      <small>Created: {new Date(share.created_at).toLocaleDateString()}</small>
                      <small>Views: {share.view_count} | Downloads: {share.downloads_count}</small>
                      <small>Expires: {new Date(share.expires_at).toLocaleDateString()}</small>
                    </div>
                    <div className="share-actions">
                      <button
                        type="button"
                        onClick={() => handleCopyToken(share.token)}
                        className="btn-info-small"
                        title="Copy share URL"
                      >
                        Copy URL
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRevokeShare(share.token)}
                        className="btn-danger-small"
                      >
                        Revoke
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p>No shares created yet.</p>
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
