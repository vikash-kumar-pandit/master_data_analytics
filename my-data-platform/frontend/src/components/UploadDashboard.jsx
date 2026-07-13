import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, Activity, CheckCircle, AlertTriangle, ArrowRight } from 'lucide-react';
import useDataStore from '../store'; // आपका Zustand स्टोर

const UploadDashboard = () => {
  // Zustand Store से स्टेट्स और एक्शन्स निकालें
  const { uploadData, isLoading, healthScore, cleanAndEngineerData, rawData } = useDataStore();

  // ड्रैग-एंड-ड्रॉप हैंडलर
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      uploadData(acceptedFiles[0]); // बैकएंड को फ़ाइल भेजें
    }
  }, [uploadData]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: false
  });

  return (
    <div className="w-full flex flex-col items-center font-sans">
      
      {/* 🚀 Header Section */}
      <div className="text-center mb-10 mt-10">
        <h1 className="text-4xl font-extrabold text-slate-900 mb-4">
          DataSaaS <span className="text-blue-600">Pro</span>
        </h1>
        <p className="text-lg text-slate-600 max-w-xl mx-auto">
          Upload your raw business data. Our AI will automatically secure, clean, and mine it for deep insights without a single line of code.
        </p>
      </div>

      {/* 📥 Upload Area (अगर डेटा अभी तक अपलोड नहीं हुआ है) */}
      {!rawData.length > 0 && (
        <div 
          {...getRootProps()} 
          className={`w-full max-w-3xl p-16 border-4 border-dashed rounded-2xl cursor-pointer transition-all duration-300 flex flex-col items-center justify-center
            ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-550'}`}
        >
          <input {...getInputProps()} />
          
          {isLoading ? (
            <div className="flex flex-col items-center animate-pulse">
              <Activity className="w-16 h-16 text-blue-500 mb-4 animate-spin" />
              <p className="text-xl font-semibold text-slate-700">Analyzing & Securing Data...</p>
              <p className="text-sm text-slate-500 mt-2">Masking PII and generating health score</p>
            </div>
          ) : (
            <>
              <UploadCloud className={`w-20 h-20 mb-6 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <p className="text-2xl font-semibold text-slate-700 mb-2">
                {isDragActive ? "Drop the file here!" : "Drag & drop your dataset here"}
              </p>
              <p className="text-slate-500">Supports CSV, Excel, and JSON</p>
              <button className="mt-8 px-6 py-3 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition font-medium">
                Browse Files
              </button>
            </>
          )}
        </div>
      )}

      {/* 🏥 Data Health Score Card (अपलोड होने के तुरंत बाद दिखेगा) */}
      {healthScore && !isLoading && (
        <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl p-8 border border-slate-100 animate-fade-in-up">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="text-2xl font-bold text-slate-800">Dataset Health Profile</h2>
              <p className="text-slate-500">Initial scan complete. PII has been masked securely.</p>
            </div>
            {/* Score Badge */}
            <div className={`px-6 py-4 rounded-xl flex items-center gap-3 ${healthScore.score > 80 ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
              <span className="text-4xl font-extrabold">{healthScore.score}</span>
              <span className="text-sm font-semibold uppercase tracking-wider">
                {healthScore.score > 80 ? 'Excellent' : 'Needs Fix'}
              </span>
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-amber-500 mt-1" />
              <div>
                <p className="text-slate-500 text-sm font-medium">Missing Cells</p>
                <p className="text-xl font-bold text-slate-800">{healthScore.null_cells || 0}</p>
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-orange-500 mt-1" />
              <div>
                <p className="text-slate-500 text-sm font-medium">Duplicate Rows</p>
                <p className="text-xl font-bold text-slate-800">{healthScore.duplicate_rows || 0}</p>
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 flex items-start gap-4">
              <CheckCircle className="w-6 h-6 text-green-500 mt-1" />
              <div>
                <p className="text-slate-500 text-sm font-medium">Total Rows Loaded</p>
                <p className="text-xl font-bold text-slate-800">{rawData.length.toLocaleString()}</p>
              </div>
            </div>
          </div>

          {/* Action Button to trigger Celery Worker */}
          <button 
            onClick={cleanAndEngineerData}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold text-lg transition shadow-lg shadow-blue-200"
          >
            1-Click Auto Clean & Engineer Features <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadDashboard;
