import React, { useCallback, useRef, useState } from 'react';
import { Upload, FileUp, CheckCircle2, X } from 'lucide-react';

const ACCEPTED = ['.csv', '.tsv', '.json', '.ndjson', '.parquet', '.xlsx', '.xls'];
const ACCEPT_STR = ACCEPTED.join(', ');

export default function DropZone({ onFile, file, disabled }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragging(false);
      if (disabled) return;
      const dropped = e.dataTransfer?.files?.[0];
      if (dropped) onFile(dropped);
    },
    [disabled, onFile]
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleInputChange = (e) => {
    const picked = e.target.files?.[0];
    if (picked) onFile(picked);
  };

  const clearFile = (e) => {
    e.stopPropagation();
    onFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div
      className={`dropzone${dragging ? ' dropzone--active' : ''}${disabled ? ' dropzone--disabled' : ''}${file ? ' dropzone--has-file' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label={file ? `Selected file: ${file.name}. Click to change.` : 'Upload dataset file. Click or drag and drop.'}
      onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_STR}
        onChange={handleInputChange}
        disabled={disabled}
        style={{ display: 'none' }}
        aria-hidden="true"
      />

      {file ? (
        <div className="dropzone__file-info">
          <CheckCircle2 className="dropzone__check-icon" />
          <div className="dropzone__file-details">
            <span className="dropzone__file-name" title={file.name}>{file.name}</span>
            <span className="dropzone__file-size">{(file.size / 1024).toFixed(1)} KB</span>
          </div>
          <button
            type="button"
            className="dropzone__clear"
            onClick={clearFile}
            aria-label="Remove selected file"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="dropzone__empty">
          {dragging ? (
            <FileUp className="dropzone__icon dropzone__icon--active" />
          ) : (
            <Upload className="dropzone__icon" />
          )}
          <span className="dropzone__title">
            {dragging ? 'Drop file here' : 'Drop file or click'}
          </span>
          <span className="dropzone__subtitle">CSV, Excel, JSON, Parquet</span>
        </div>
      )}
    </div>
  );
}
