import React from 'react';
import { AlertCircle, HelpCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function EmptyState({
  title = 'No Data Available',
  description = 'There is currently no data loaded in this workspace. Please upload a dataset to begin.',
  icon: Icon = AlertCircle,
  actionText = 'Go to Ingestion Workspace',
  actionRoute = '/',
  onActionClick
}) {
  const navigate = useNavigate();

  const handleAction = () => {
    if (onActionClick) {
      onActionClick();
    } else {
      navigate(actionRoute);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center text-center p-12 bg-white dark:bg-neutral-850 border border-slate-200 dark:border-neutral-700 rounded-3xl shadow-sm max-w-lg mx-auto my-12 transition-colors font-sans">
      <div className="p-4 bg-indigo-50 dark:bg-indigo-950/20 text-indigo-650 dark:text-indigo-400 rounded-full mb-5">
        <Icon className="w-10 h-10" />
      </div>
      <h3 className="text-xl font-black text-slate-800 dark:text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-6 leading-relaxed">{description}</p>
      {actionText && (
        <button
          onClick={handleAction}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-750 text-white rounded-xl font-bold text-xs shadow-md shadow-indigo-150 transition"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}
