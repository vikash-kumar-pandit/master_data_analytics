import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
const BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');

function getAuthHeaders() {
  try {
    const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
    if (raw) {
      const token = JSON.parse(raw)?.token;
      if (token) return { Authorization: `Bearer ${token}` };
    }
  } catch {}
  return {};
}

export default function SearchAndExport({ rows, analysis }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [exportFilename, setExportFilename] = useState('data_export');
  const [exportLoading, setExportLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState('csv');
  const [activeTab, setActiveTab] = useState('search');

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    setSearchError('');
    try {
      const response = await axios.post(`${BASE_URL}/api/search/catalog`, {
        query: searchQuery,
        limit: 20,
        offset: 0,
      }, { headers: getAuthHeaders() });
      setSearchResults(response.data.items || []);
    } catch (error) {
      setSearchError(error?.response?.data?.detail || 'Search failed');
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!rows || rows.length === 0) {
      alert('No data to export');
      return;
    }

    setExportLoading(true);
    try {
      const endpoint =
        format === 'excel'
          ? '/api/export/excel'
          : format === 'parquet'
          ? '/api/export/parquet'
          : '/api/export/json';

      const response = await axios.post(
        `${BASE_URL}${endpoint}`,
        {
          rows: rows,
          filename: exportFilename || 'export',
        },
        { 
          responseType: 'blob',
          headers: getAuthHeaders()
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const extension =
        format === 'excel' ? '.xlsx' : format === 'parquet' ? '.parquet' : '.json';
      link.setAttribute('download', `${exportFilename || 'export'}${extension}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(error?.response?.data?.detail || `Export to ${format} failed`);
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <div className="search-export-container">
      {/* Tab Navigation */}
      <div className="search-export-tabs">
        <button
          className={`tab-button ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          🔍 Search Catalog
        </button>
        <button
          className={`tab-button ${activeTab === 'export' ? 'active' : ''}`}
          onClick={() => setActiveTab('export')}
        >
          📥 Export Data
        </button>
      </div>

      {/* Search Tab */}
      {activeTab === 'search' && (
        <div className="search-panel">
          <div className="search-input-group">
            <input
              type="text"
              placeholder="Search by name, type, tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="search-input"
            />
            <button
              onClick={handleSearch}
              disabled={searchLoading}
              className="search-button"
            >
              {searchLoading ? '⏳ Searching...' : '🔍 Search'}
            </button>
          </div>

          {searchError && <div className="error-message">{searchError}</div>}

          <div className="search-results">
            {searchResults.length === 0 && !searchLoading && searchQuery && (
              <div className="no-results">No results found</div>
            )}
            {searchResults.map((item, idx) => (
              <div key={idx} className="search-result-item">
                <div className="result-header">
                  <h4>{item.name || 'Unnamed'}</h4>
                  <span className="result-type">{item.type || 'unknown'}</span>
                </div>
                <p className="result-description">
                  {item.description || 'No description'}
                </p>
                {item.tags && item.tags.length > 0 && (
                  <div className="result-tags">
                    {item.tags.map((tag, t) => (
                      <span key={t} className="tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className="result-meta">
                  <span>Owner: {item.owner || 'Unknown'}</span>
                  <span>Created: {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Tab */}
      {activeTab === 'export' && (
        <div className="export-panel">
          <div className="export-info">
            <p>
              {rows && rows.length > 0
                ? `Ready to export ${rows.length} rows of data`
                : 'No data available to export'}
            </p>
          </div>

          <div className="export-filename-group">
            <label>Filename:</label>
            <input
              type="text"
              value={exportFilename}
              onChange={(e) => setExportFilename(e.target.value)}
              placeholder="Export filename"
              className="filename-input"
            />
          </div>

          <div className="export-formats">
            <h4>Export Format:</h4>
            <div className="format-buttons">
              <button
                onClick={() => handleExport('csv')}
                disabled={exportLoading || !rows || rows.length === 0}
                className="export-format-button"
              >
                📄 CSV
              </button>
              <button
                onClick={() => handleExport('excel')}
                disabled={exportLoading || !rows || rows.length === 0}
                className="export-format-button"
              >
                📊 Excel
              </button>
              <button
                onClick={() => handleExport('parquet')}
                disabled={exportLoading || !rows || rows.length === 0}
                className="export-format-button"
              >
                ⚡ Parquet
              </button>
              <button
                onClick={() => handleExport('json')}
                disabled={exportLoading || !rows || rows.length === 0}
                className="export-format-button"
              >
                {} JSON
              </button>
            </div>
          </div>

          {exportLoading && (
            <div className="export-status">
              ⏳ Preparing download...
            </div>
          )}

          <div className="export-notes">
            <h5>Format Guide:</h5>
            <ul>
              <li><strong>CSV:</strong> Universal spreadsheet format, human-readable</li>
              <li><strong>Excel:</strong> Formatted spreadsheet with native .xlsx support</li>
              <li><strong>Parquet:</strong> Columnar format, highly efficient for analytics</li>
              <li><strong>JSON:</strong> Structured format, easy for APIs and programmatic use</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
