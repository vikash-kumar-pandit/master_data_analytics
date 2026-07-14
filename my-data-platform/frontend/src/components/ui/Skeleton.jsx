import React from 'react';

export default function Skeleton({
  variant = 'line', // line | circle | card | table
  className = '',
  count = 1,
  ...props
}) {
  const baseStyle = 'animate-pulse bg-slate-200 dark:bg-neutral-800';

  if (variant === 'circle') {
    return <div className={`${baseStyle} rounded-full ${className}`} {...props} />;
  }

  if (variant === 'card') {
    return (
      <div className={`p-6 border border-slate-200 dark:border-neutral-700 rounded-2xl flex flex-col gap-4 bg-white dark:bg-neutral-850 ${className}`} {...props}>
        <div className={`${baseStyle} h-6 w-1/3 rounded-lg`} />
        <div className="space-y-2">
          <div className={`${baseStyle} h-4 w-full rounded-lg`} />
          <div className={`${baseStyle} h-4 w-5/6 rounded-lg`} />
        </div>
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={`border border-slate-200 dark:border-neutral-700 rounded-xl overflow-hidden ${className}`} {...props}>
        {/* Table header */}
        <div className="bg-slate-50 dark:bg-neutral-800 p-4 border-b border-slate-200 dark:border-neutral-700 flex gap-4">
          <div className={`${baseStyle} h-4 w-1/4 rounded`} />
          <div className={`${baseStyle} h-4 w-1/4 rounded`} />
          <div className={`${baseStyle} h-4 w-1/4 rounded`} />
          <div className={`${baseStyle} h-4 w-1/4 rounded`} />
        </div>
        {/* Table rows */}
        <div className="divide-y divide-slate-100 dark:divide-neutral-800 p-4 space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex gap-4">
              <div className={`${baseStyle} h-4 w-1/4 rounded`} />
              <div className={`${baseStyle} h-4 w-1/4 rounded`} />
              <div className={`${baseStyle} h-4 w-1/4 rounded`} />
              <div className={`${baseStyle} h-4 w-1/4 rounded`} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Default 'line' variant
  return (
    <div className="flex flex-col gap-2 w-full">
      {Array.from({ length: count }).map((_, idx) => (
        <div 
          key={idx} 
          className={`${baseStyle} h-4 rounded-lg ${className}`} 
          {...props} 
        />
      ))}
    </div>
  );
}
