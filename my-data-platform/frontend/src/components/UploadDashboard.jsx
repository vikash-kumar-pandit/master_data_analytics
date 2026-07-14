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
    <div className="w-full flex flex-col items-center font-sans max-w-5xl mx-auto py-6">
      
      {/* 🚀 Header Section */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white mb-3 tracking-tight">
          Decision Intelligence <span className="text-indigo-600">DIOS v2.0</span>
        </h1>
        <p className="text-base text-slate-600 dark:text-slate-400 max-w-xl mx-auto leading-relaxed">
          Ingest raw tables. Our operating system handles masking, profiling, cleaning, auto-visualizations, and executive reporting in seconds.
        </p>
      </div>

      {/* 📥 Upload Area & Onboarding (अगर डेटा अभी तक अपलोड नहीं हुआ है) */}
      {rawData.length === 0 && (
        <div className="w-full flex flex-col gap-10">
          <div 
            {...getRootProps()} 
            className={`p-14 border-4 border-dashed rounded-3xl cursor-pointer transition-all duration-300 flex flex-col items-center justify-center shadow-sm
              ${isDragActive ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20' : 'border-slate-200 bg-white dark:bg-neutral-850 hover:border-indigo-400 dark:border-neutral-700'}`}
          >
            <input {...getInputProps()} />
            
            {isLoading ? (
              <div className="flex flex-col items-center animate-pulse">
                <Activity className="w-16 h-16 text-indigo-600 mb-4 animate-spin" />
                <p className="text-xl font-semibold text-slate-700 dark:text-slate-350">Analyzing & Securing Data...</p>
                <p className="text-sm text-slate-500 mt-2">Masking PII and generating health score</p>
              </div>
            ) : (
              <>
                <UploadCloud className={`w-16 h-16 mb-4 ${isDragActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                <p className="text-xl font-black text-slate-700 dark:text-slate-300 mb-1">
                  {isDragActive ? "Drop the file here!" : "Drag & drop your dataset here"}
                </p>
                <p className="text-xs text-slate-400">Supports CSV, Excel, and JSON files</p>
                <button className="mt-6 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl transition font-bold text-xs">
                  Browse Files
                </button>
              </>
            )}
          </div>

          {/* Quick Sample Datasets & Tips Card Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 shrink-0">
            {/* Sample datasets */}
            <div className="bg-white dark:bg-neutral-850 p-6 border dark:border-neutral-700 rounded-2xl shadow-sm flex flex-col gap-4">
              <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-wider">Try Sample Datasets</h3>
              <div className="flex flex-col gap-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    const RETAIL_CSV = `Transaction_ID,Product_Name,Quantity,Price,Customer_Email,Date\nTXN001,Wireless Mouse,2,25.99,john.doe@example.com,2026-01-10\nTXN002,Keyboard,1,45.50,alice.smith@example.com,2026-01-11\nTXN003,USB-C Hub,5,19.99,,2026-01-12\nTXN004,Bluetooth Speaker,1,59.99,bob.jones@example.com,2026-01-12\nTXN005,Wireless Mouse,3,25.99,john.doe@example.com,2026-01-13\nTXN006,Monitor Stand,1,34.99,eve.davis@example.com,2026-01-14`;
                    const file = new File([RETAIL_CSV], "retail_sales_sample.csv", { type: 'text/csv' });
                    uploadData(file);
                  }}
                  className="p-3 bg-slate-50 hover:bg-slate-100 dark:bg-neutral-800/40 dark:hover:bg-neutral-800 border dark:border-neutral-700 rounded-xl text-left transition flex justify-between items-center"
                >
                  <div>
                    <p className="font-extrabold text-xs text-slate-800 dark:text-slate-200">Retail Sales Tracker</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Contains raw sales, quantities, and customer PII details.</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    const HR_CSV = `Employee_ID,Name,Department,Salary,Hire_Date,Phone\nEMP101,Jane Doe,Marketing,75000,2024-03-15,555-0192\nEMP102,John Smith,Engineering,95000,,555-0283\nEMP103,Alice Johnson,HR,68000,2023-01-10,555-0374\nEMP104,Bob Carter,Sales,72000,2025-06-01,555-0465\nEMP105,Charlie Brown,Engineering,98000,2022-11-20,555-0556`;
                    const file = new File([HR_CSV], "employee_directory.csv", { type: 'text/csv' });
                    uploadData(file);
                  }}
                  className="p-3 bg-slate-50 hover:bg-slate-100 dark:bg-neutral-800/40 dark:hover:bg-neutral-800 border dark:border-neutral-700 rounded-xl text-left transition flex justify-between items-center"
                >
                  <div>
                    <p className="font-extrabold text-xs text-slate-800 dark:text-slate-200">HR Directory</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Contains department metrics, salary ranges, and hire dates.</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>

            {/* Quick tips & onboarding */}
            <div className="bg-white dark:bg-neutral-850 p-6 border dark:border-neutral-700 rounded-2xl shadow-sm flex flex-col gap-4">
              <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-wider">DIOS System Quick Guide</h3>
              <ul className="space-y-2 text-xs text-slate-500 leading-relaxed dark:text-slate-400">
                <li className="flex gap-2"><span className="text-indigo-600 font-black">1.</span> Upload a dataset to begin the automated ingestion pipeline.</li>
                <li className="flex gap-2"><span className="text-indigo-600 font-black">2.</span> AI will mask phone numbers, locations, and personal email addresses automatically.</li>
                <li className="flex gap-2"><span className="text-indigo-600 font-black">3.</span> Check Data Profiling or Data Quality sections to run statistical metrics and scans.</li>
              </ul>
            </div>
          </div>
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
