import React, { useMemo, useState, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { Download, Search, Sparkles, BarChart2 } from 'lucide-react';
import useDataStore from '../store'; // आपका Zustand स्टोर
import { useTheme } from '../context/ThemeContext';

const DataViewer = ({ onShowChat }) => {
  const { rawData, cleanedData, columns, aiInsights } = useDataStore();
  const [quickFilterText, setQuickFilterText] = useState('');
  const { theme } = useTheme();
  const gridRef = useRef();

  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;
  const isCleaned = cleanedData.length > 0;

  const gridThemeClass = theme === 'dark' || theme === 'high-contrast' ? 'ag-theme-alpine-dark' : 'ag-theme-alpine';

  // Call columns formatted for AG-Gridcommunity
  const columnDefs = useMemo(() => {
    if (!currentDataset || currentDataset.length === 0) return [];
    
    const dataColumns = columns?.length > 0 ? columns : Object.keys(currentDataset[0]);
    
    return dataColumns.map((col) => ({
      field: col,
      headerName: col.replace(/_/g, ' ').toUpperCase(),
      sortable: true,
      filter: true,
      resizable: true,
      valueFormatter: (params) => {
        if (params.value === null || params.value === undefined || (typeof params.value === 'number' && isNaN(params.value))) {
          return '';
        }
        return params.value;
      },
      // numericColumn only for actual numbers; text cols get no type (avoids 'textColumn does not exist' warning)
      ...(typeof currentDataset[0][col] === 'number' ? { type: 'numericColumn' } : {})
    }));
  }, [currentDataset, columns]);

  // Default settings
  const defaultColDef = useMemo(() => ({
    flex: 1,
    minWidth: 150,
    filterParams: { buttons: ['reset', 'apply'] },
  }), []);

  // CSV Export
  const onExportClick = () => {
    gridRef.current.api.exportDataAsCsv({ fileName: isCleaned ? 'Cleaned_Data_DataSaaS.csv' : 'Raw_Data_DataSaaS.csv' });
  };

  if (!currentDataset || currentDataset.length === 0) return null;

  return (
    <div className="w-full max-w-7xl mx-auto mt-8 bg-white dark:bg-neutral-850 rounded-2xl shadow-lg border border-slate-200 dark:border-neutral-700 overflow-hidden font-sans transition-colors">
      
      {/* Toolbar Section */}
      <div className="p-6 border-b border-slate-100 dark:border-neutral-700 flex flex-col md:flex-row justify-between items-center gap-4 bg-slate-50 dark:bg-neutral-800/40">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-indigo-500" />
            {isCleaned ? 'Cleaned & Engineered Data' : 'Raw Uploaded Data'}
          </h2>
          <p className="text-sm text-slate-550 dark:text-slate-400 mt-1">
            Showing {currentDataset.length.toLocaleString()} rows. Ready for analysis.
          </p>
        </div>

        <div className="flex items-center gap-4 w-full md:w-auto">
          {/* Global Search Bar */}
          <div className="relative w-full md:w-64">
            <Search className="w-5 h-5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search in all columns..."
              className="w-full pl-10 pr-4 py-2 border border-slate-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-slate-700 dark:text-white"
              onChange={(e) => setQuickFilterText(e.target.value)}
            />
          </div>

          {/* Export Button */}
          <button 
            onClick={onExportClick}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition font-medium whitespace-nowrap"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
      </div>

      {/* 🚀 AI Insight Note (Hypothesis testing / Engineering logs) */}
      {aiInsights && (
        <div className="bg-indigo-50 dark:bg-indigo-950/20 px-6 py-3 border-b border-indigo-100 dark:border-indigo-900/50 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400 mt-0.5" />
          <p className="text-sm text-indigo-900 dark:text-indigo-200 font-medium">{aiInsights}</p>
        </div>
      )}

      {/* 📊 The AG-Grid Component */}
      <div className={`${gridThemeClass} w-full`} style={{ height: '500px' }}>
        <AgGridReact
          ref={gridRef}
          rowData={currentDataset}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          quickFilterText={quickFilterText}
          pagination={true}
          paginationPageSize={100}
          rowSelection={{ mode: 'multiRow' }}
          animateRows={true}
          enableCellTextSelection={true}
        />
      </div>

      {/* Action Footer */}
      <div className="p-4 bg-slate-50 dark:bg-neutral-800/40 border-t border-slate-100 dark:border-neutral-700 flex justify-end">
        <button 
          onClick={onShowChat}
          className="flex items-center gap-2 px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl transition font-bold shadow-md dark:bg-neutral-800 dark:hover:bg-neutral-750"
        >
          <BarChart2 className="w-5 h-5" /> Ask AI & Visualize Data
        </button>
      </div>
    </div>
  );
};

export default DataViewer;
