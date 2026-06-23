import React, { useMemo, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

export default function DataGrid({ rowData, columnDefs, onGridReady, theme }) {
  const gridRef = useRef(null);

  const defaultColumnDef = useMemo(
    () => ({
      flex: 1,
      minWidth: 140,
      filter: true,
      sortable: true,
      resizable: true,
    }),
    []
  );

  const jumpToFirstCell = () => {
    const api = gridRef.current?.api;
    if (!api || !columnDefs.length) {
      return;
    }

    api.ensureIndexVisible(0, 'top');
    api.setFocusedCell(0, columnDefs[0].field);
  };

  return (
    <div className="grid-wrap">
      <div className="grid-toolbar">
        <button type="button" onClick={jumpToFirstCell} disabled={!rowData.length}>
          Jump to First Cell
        </button>
      </div>

      {!rowData.length ? (
        <div className="grid-empty-state" role="status" aria-live="polite">
          <div className="grid-empty-icon">CLD</div>
          <h4>No Rows To Show</h4>
          <p>Please upload a dataset to begin exploration.</p>
          <span className="grid-empty-cta">Get Started</span>
        </div>
      ) : null}

      <div className={`${theme === 'dark' ? 'ag-theme-alpine-dark' : 'ag-theme-alpine'} grid-surface`}>
        <AgGridReact
          ref={gridRef}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColumnDef}
          onGridReady={onGridReady}
          pagination
          paginationPageSize={100}
          domLayout="autoHeight"
        />
      </div>
    </div>
  );
}