import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  GitBranch, ArrowLeftRight, Settings, Undo2, Redo2, ArrowDownToLine, 
  Trash2, Play, CheckCircle, RefreshCw, Sliders, Search, 
  FileSpreadsheet, Layers, Type, Trash, Edit, Check, AlertTriangle, ShieldCheck
} from 'lucide-react';
import DashboardLayout from '../DashboardLayout';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  let token = null;
  try {
    const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
    if (raw) {
      token = JSON.parse(raw)?.token;
    }
  } catch (e) {
    console.error("Error reading token in DataPreparationStudio interceptor", e);
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default function DataPreparationStudio() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [history, setHistory] = useState({ current_pointer: 0, max_pointer: 0, steps: [] });
  const [previewRows, setPreviewRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Selected Operation & Options
  const [selectedOp, setSelectedOp] = useState('trim_spaces');
  const [targetColumns, setTargetColumns] = useState([]);
  const [renameMap, setRenameMap] = useState({});
  const [operationParams, setOperationParams] = useState({
    separator: ' ',
    output_column: 'merged_col',
    target_type: 'float',
    date_format: '%Y-%m-%d',
    pattern: '',
    replacement: '',
    find_value: '',
    lower_quantile: 0.05,
    upper_quantile: 0.95
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/api/analytics/projects');
      setProjects(res.data);
      if (res.data.length > 0) {
        setSelectedProjectId(res.data[0].id);
        fetchHistory(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch project list. Ensure uvicorn backend is running.");
    }
  };

  const fetchHistory = async (projId) => {
    if (!projId) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/api/preparation/history?project_id=${projId}`);
      setHistory(res.data);
      
      // Get preview of the current active version dataset
      const activeStep = res.data.steps.find(s => s.step_num === res.data.current_pointer);
      if (activeStep) {
        // Fetch active version data preview using project run endpoint
        const proj = projects.find(p => p.id === projId) || { dataset_id: projId };
        const datasetRes = await api.get(`/api/analytics/datasets/${proj.dataset_id || projId}/preview`);
        if (datasetRes.data && datasetRes.data.length > 0) {
          setPreviewRows(datasetRes.data);
          setColumns(Object.keys(datasetRes.data[0]));
        } else {
          setPreviewRows([]);
          setColumns([]);
        }
      }
    } catch (err) {
      console.error(err);
      // Fallback: if preview fails, clean preview rows
      setPreviewRows([]);
      setColumns([]);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (e) => {
    const pId = e.target.value;
    setSelectedProjectId(pId);
    fetchHistory(pId);
  };

  const executeTransformation = async () => {
    if (!selectedProjectId) return;
    setActionLoading(true);
    setError('');
    setSuccessMsg('');

    const formData = new FormData();
    formData.append('project_id', selectedProjectId);
    formData.append('operation_type', selectedOp);

    // Merge target column and rename map overrides
    const parsedParams = {
      ...operationParams,
      columns: targetColumns,
      rename_map: renameMap
    };
    formData.append('parameters_json', JSON.stringify(parsedParams));

    try {
      const res = await api.post('/api/preparation/run', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSuccessMsg(res.data.description);
      fetchHistory(selectedProjectId);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Transformation failed. Please check inputs.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUndo = async () => {
    setActionLoading(true);
    try {
      await api.post('/api/preparation/undo', new URLSearchParams({ project_id: selectedProjectId }));
      fetchHistory(selectedProjectId);
      setSuccessMsg("Undo successful.");
    } catch (err) {
      setError("Undo failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRedo = async () => {
    setActionLoading(true);
    try {
      await api.post('/api/preparation/redo', new URLSearchParams({ project_id: selectedProjectId }));
      fetchHistory(selectedProjectId);
      setSuccessMsg("Redo successful.");
    } catch (err) {
      setError("Redo failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRollback = async (versionNum) => {
    setActionLoading(true);
    try {
      await api.post(`/api/preparation/rollback/${versionNum}`, new URLSearchParams({ 
        project_id: selectedProjectId,
        version: versionNum
      }));
      fetchHistory(selectedProjectId);
      setSuccessMsg(`Rollback to version ${versionNum} complete.`);
    } catch (err) {
      setError("Rollback failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const triggerExport = (format) => {
    if (!selectedProjectId) return;
    const url = `http://localhost:8000/api/preparation/export?project_id=${selectedProjectId}&format=${format}`;
    window.open(url, '_blank');
  };

  const toggleColumnSelection = (col) => {
    if (targetColumns.includes(col)) {
      setTargetColumns(targetColumns.filter(c => c !== col));
    } else {
      setTargetColumns([...targetColumns, col]);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 max-w-7xl mx-auto h-[calc(100vh-120px)]">
        
        {/* Header Block */}
        <div className="bg-white dark:bg-neutral-850 p-4 rounded-xl border border-slate-200 dark:border-neutral-700 shadow-sm flex justify-between items-center flex-wrap gap-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-xl">
              <Sliders className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">AI Data Preparation Studio</h1>
              <p className="text-xs text-slate-500">Power Query-style granular datasets cleaner, transformer and version stack engine</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2.5">
            <select 
              value={selectedProjectId}
              onChange={handleProjectChange}
              className="px-3 py-1.5 bg-slate-50 border rounded-lg font-semibold text-xs text-slate-700 dark:bg-neutral-850 dark:border-neutral-700 dark:text-slate-200"
            >
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            
            <button 
              onClick={handleUndo} 
              disabled={history.current_pointer <= 1 || actionLoading}
              className="p-1.5 bg-white border hover:bg-slate-50 disabled:opacity-40 rounded-lg text-slate-700 transition"
              title="Undo step"
            >
              <Undo2 className="w-4 h-4" />
            </button>
            
            <button 
              onClick={handleRedo} 
              disabled={history.current_pointer >= history.max_pointer || actionLoading}
              className="p-1.5 bg-white border hover:bg-slate-50 disabled:opacity-40 rounded-lg text-slate-700 transition"
              title="Redo step"
            >
              <Redo2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3.5 bg-red-50 text-red-700 border border-red-200 rounded-xl flex items-center gap-2 text-xs shrink-0">
            <AlertTriangle className="w-4 h-4" />
            <span className="font-semibold">{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl flex items-center gap-2 text-xs shrink-0">
            <ShieldCheck className="w-4 h-4" />
            <span className="font-semibold">{successMsg}</span>
          </div>
        )}

        {/* Studio Workspace panels */}
        <div className="flex flex-1 gap-6 min-h-0">
          
          {/* Left panel: Versions list */}
          <div className="w-56 bg-white dark:bg-neutral-850 border rounded-xl p-4 flex flex-col gap-4 overflow-y-auto shadow-sm">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider">Dataset Versions</h3>
            <div className="flex flex-col gap-2">
              {history.steps.map(s => (
                <button
                  key={s.step_num}
                  onClick={() => handleRollback(s.step_num)}
                  className={`w-full p-3 rounded-lg border text-left transition flex flex-col gap-1
                    ${history.current_pointer === s.step_num
                      ? 'bg-blue-50 border-blue-200 text-blue-800' 
                      : 'hover:bg-slate-50 text-slate-600'}`}
                >
                  <div className="flex justify-between items-center w-full">
                    <span className="font-black text-xs">Version {s.step_num}</span>
                    {history.current_pointer === s.step_num && (
                      <span className="text-[9px] bg-blue-600 text-white font-extrabold px-1.5 py-0.5 rounded-full uppercase">ACTIVE</span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-450 leading-tight block">{s.description}</span>
                  <span className="text-[9px] text-slate-400 font-mono mt-1">{s.rows}x{s.columns} cells</span>
                </button>
              ))}
            </div>
          </div>

          {/* Center panel: Canvas and preview table */}
          <div className="flex-1 bg-white dark:bg-neutral-850 border rounded-xl p-4 flex flex-col gap-4 min-w-0 shadow-sm overflow-hidden">
            <div className="flex justify-between items-center border-b pb-3 shrink-0">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Table Live Preview (Top 10 rows)</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-semibold mr-2">Download active version:</span>
                {['csv', 'parquet', 'json', 'sql'].map(f => (
                  <button
                    key={f}
                    onClick={() => triggerExport(f)}
                    className="px-2.5 py-1 text-[10px] bg-slate-50 hover:bg-slate-100 border font-extrabold rounded-md text-slate-600 transition uppercase"
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-2">
                <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
                <p className="text-xs font-bold text-slate-500">Querying active preview data...</p>
              </div>
            ) : previewRows.length > 0 ? (
              <div className="flex-1 overflow-auto border rounded-lg">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-neutral-800 border-b sticky top-0">
                    <tr>
                      {columns.map(col => (
                        <th key={col} className="p-3 font-mono font-bold text-slate-600 select-none border-r">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, rIdx) => (
                      <tr key={rIdx} className="border-b hover:bg-slate-50/55">
                        {columns.map(col => (
                          <td key={col} className="p-3 font-mono border-r max-w-xs truncate text-slate-700">
                            {row[col] !== null ? String(row[col]) : <span className="text-red-400 italic font-normal">null</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center gap-2 text-slate-400">
                <FileSpreadsheet className="w-12 h-12" />
                <p className="text-xs font-semibold">No dataset preview records available. Please ensure data is loaded.</p>
              </div>
            )}
          </div>

          {/* Right panel: Operations and parameters */}
          <div className="w-72 bg-white dark:bg-neutral-850 border rounded-xl p-4 flex flex-col gap-4 overflow-y-auto shadow-sm">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider">Transform Properties</h3>
            
            {/* Op Type Dropdown */}
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-400 font-extrabold uppercase">Operation Type</label>
              <select
                value={selectedOp}
                onChange={(e) => setSelectedOp(e.target.value)}
                className="w-full p-2 border rounded-lg text-xs font-semibold text-slate-700 bg-slate-50"
              >
                <optgroup label="Missing Value Handling">
                  <option value="remove_missing">Remove Missing Rows</option>
                  <option value="fill_mean">Fill Mean Imputation</option>
                  <option value="fill_median">Fill Median Imputation</option>
                  <option value="fill_mode">Fill Mode Imputation</option>
                  <option value="forward_fill">Forward Fill</option>
                  <option value="backward_fill">Backward Fill</option>
                  <option value="interpolate">Series Interpolation</option>
                </optgroup>
                <optgroup label="Column Adjustments">
                  <option value="duplicate_removal">Duplicate Rows Removal</option>
                  <option value="column_rename">Rename Column</option>
                  <option value="column_merge">Merge Columns</option>
                  <option value="column_split">Split Column</option>
                  <option value="drop_column">Drop Selected Columns</option>
                  <option value="keep_column">Keep Selected Columns</option>
                </optgroup>
                <optgroup label="Type Conversions">
                  <option value="cast_type">Cast Datatypes</option>
                  <option value="currency_parsing">Parse Currencies</option>
                  <option value="date_parsing">Parse Dates</option>
                </optgroup>
                <optgroup label="Text Normalizations">
                  <option value="trim_spaces">Trim Spaces</option>
                  <option value="lowercase">To Lowercase</option>
                  <option value="uppercase">To Uppercase</option>
                  <option value="regex_replace">Regex Replace Text</option>
                  <option value="regex_extract">Regex Extract Match</option>
                  <option value="find_replace">Find & Replace Text</option>
                </optgroup>
                <optgroup label="Outliers & Scaling">
                  <option value="outlier_removal">Remove Outliers</option>
                  <option value="winsorization">Winsorize Outliers</option>
                  <option value="minmax_scaling">MinMax Scaler</option>
                  <option value="standardization">Standard Scaler</option>
                </optgroup>
                <optgroup label="Encoders">
                  <option value="one_hot_encoding">One-Hot Encoding</option>
                  <option value="label_encoding">Label Encoding</option>
                </optgroup>
                <optgroup label="NLP & Cleans">
                  <option value="emoji_removal">Remove Emoji Unicode</option>
                  <option value="html_removal">Strip HTML Tags</option>
                  <option value="whitespace_cleaning">Clean Extra Spaces</option>
                </optgroup>
              </select>
            </div>

            {/* Target columns checkbox list */}
            {selectedOp !== 'duplicate_removal' && (
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-extrabold uppercase">Target Columns</label>
                <div className="max-h-36 overflow-y-auto border rounded-lg p-2 space-y-1.5 bg-slate-50">
                  {columns.map(c => (
                    <label key={c} className="flex items-center gap-2 text-xs font-mono text-slate-700 cursor-pointer">
                      <input 
                        type="checkbox"
                        checked={targetColumns.includes(c)}
                        onChange={() => toggleColumnSelection(c)}
                        className="rounded text-blue-600 focus:ring-0"
                      />
                      {c}
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Conditional Parameters */}
            {selectedOp === 'column_merge' && (
              <div className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Separator</label>
                  <input
                    type="text"
                    value={operationParams.separator}
                    onChange={(e) => setOperationParams({ ...operationParams, separator: e.target.value })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Output Column Name</label>
                  <input
                    type="text"
                    value={operationParams.output_column}
                    onChange={(e) => setOperationParams({ ...operationParams, output_column: e.target.value })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
              </div>
            )}

            {selectedOp === 'column_split' && (
              <div className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Target Column</label>
                  <select
                    value={operationParams.column || ''}
                    onChange={(e) => setOperationParams({ ...operationParams, column: e.target.value })}
                    className="p-2 border rounded-lg text-xs text-slate-700 bg-slate-50"
                  >
                    <option value="">Select column</option>
                    {columns.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Split Delimiter</label>
                  <input
                    type="text"
                    value={operationParams.separator}
                    onChange={(e) => setOperationParams({ ...operationParams, separator: e.target.value })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
              </div>
            )}

            {selectedOp === 'cast_type' && (
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-extrabold uppercase">Target Type</label>
                <select
                  value={operationParams.target_type}
                  onChange={(e) => setOperationParams({ ...operationParams, target_type: e.target.value })}
                  className="p-2 border rounded-lg text-xs text-slate-700 bg-slate-50"
                >
                  <option value="int">Integer (Int64)</option>
                  <option value="float">Float (Float64)</option>
                  <option value="str">String (Utf8)</option>
                  <option value="bool">Boolean</option>
                </select>
              </div>
            )}

            {selectedOp === 'date_parsing' && (
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-extrabold uppercase">Date Format Pattern</label>
                <input
                  type="text"
                  value={operationParams.date_format}
                  onChange={(e) => setOperationParams({ ...operationParams, date_format: e.target.value })}
                  className="p-2 border rounded-lg text-xs"
                  placeholder="%Y-%m-%d"
                />
              </div>
            )}

            {(selectedOp === 'regex_replace' || selectedOp === 'regex_extract') && (
              <div className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Regex Pattern</label>
                  <input
                    type="text"
                    value={operationParams.pattern}
                    onChange={(e) => setOperationParams({ ...operationParams, pattern: e.target.value })}
                    className="p-2 border rounded-lg text-xs"
                    placeholder="e.g. \d+"
                  />
                </div>
                {selectedOp === 'regex_replace' ? (
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-slate-400 font-extrabold uppercase">Replacement Value</label>
                    <input
                      type="text"
                      value={operationParams.replacement}
                      onChange={(e) => setOperationParams({ ...operationParams, replacement: e.target.value })}
                      className="p-2 border rounded-lg text-xs"
                    />
                  </div>
                ) : (
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-slate-400 font-extrabold uppercase">Group Index</label>
                    <input
                      type="number"
                      value={operationParams.group_index || 0}
                      onChange={(e) => setOperationParams({ ...operationParams, group_index: parseInt(e.target.value) })}
                      className="p-2 border rounded-lg text-xs"
                    />
                  </div>
                )}
              </div>
            )}

            {selectedOp === 'find_replace' && (
              <div className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Find Value</label>
                  <input
                    type="text"
                    value={operationParams.find_value}
                    onChange={(e) => setOperationParams({ ...operationParams, find_value: e.target.value })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Replacement</label>
                  <input
                    type="text"
                    value={operationParams.replacement}
                    onChange={(e) => setOperationParams({ ...operationParams, replacement: e.target.value })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
              </div>
            )}

            {selectedOp === 'winsorization' && (
              <div className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Lower Quantile</label>
                  <input
                    type="number"
                    step="0.01"
                    value={operationParams.lower_quantile}
                    onChange={(e) => setOperationParams({ ...operationParams, lower_quantile: parseFloat(e.target.value) })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] text-slate-400 font-extrabold uppercase">Upper Quantile</label>
                  <input
                    type="number"
                    step="0.01"
                    value={operationParams.upper_quantile}
                    onChange={(e) => setOperationParams({ ...operationParams, upper_quantile: parseFloat(e.target.value) })}
                    className="p-2 border rounded-lg text-xs"
                  />
                </div>
              </div>
            )}

            {selectedOp === 'column_rename' && (
              <div className="space-y-3">
                <label className="text-[10px] text-slate-400 font-extrabold uppercase">Rename Mappings</label>
                {targetColumns.map(c => (
                  <div key={c} className="flex items-center gap-2">
                    <span className="font-mono text-xs w-24 truncate">{c} :</span>
                    <input
                      type="text"
                      placeholder="new name"
                      value={renameMap[c] || ''}
                      onChange={(e) => setRenameMap({ ...renameMap, [c]: e.target.value })}
                      className="p-1.5 border rounded-lg text-xs flex-1"
                    />
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={executeTransformation}
              disabled={actionLoading || (selectedOp !== 'duplicate_removal' && targetColumns.length === 0 && selectedOp !== 'column_split')}
              className="mt-4 w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-100 flex items-center justify-center gap-2 transition disabled:bg-slate-300"
            >
              {actionLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Apply Transformation
            </button>

          </div>
        </div>

        {/* Bottom panel: Execution steps history list */}
        <div className="bg-slate-50 dark:bg-neutral-800 p-4 rounded-xl border border-slate-200 dark:border-neutral-700 shadow-inner flex flex-col gap-2 shrink-0">
          <h4 className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider">Applied Steps History</h4>
          <div className="flex items-center gap-4 overflow-x-auto py-1">
            {history.steps.map((s, idx) => (
              <div key={s.step_num} className="flex items-center shrink-0">
                <div 
                  className={`p-3 border rounded-xl flex flex-col gap-0.5 cursor-pointer transition select-none
                    ${history.current_pointer === s.step_num 
                      ? 'bg-indigo-600 border-indigo-700 text-white shadow-md' 
                      : (s.step_num <= history.current_pointer ? 'bg-white text-slate-700 border-slate-300' : 'bg-white opacity-40 text-slate-400')}`}
                  onClick={() => handleRollback(s.step_num)}
                >
                  <span className="text-[9px] uppercase tracking-wider font-extrabold opacity-80">Step {s.step_num}</span>
                  <span className="text-xs font-black truncate max-w-[120px]">{s.operation_type.replace('_', ' ')}</span>
                </div>
                {idx < history.steps.length - 1 && (
                  <ArrowLeftRight className="w-4 h-4 text-slate-400 mx-2" />
                )}
              </div>
            ))}
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
}
