import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

export default function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary', // primary | secondary | outline | ghost | danger
  size = 'md', // sm | md | lg
  disabled = false,
  loading = false,
  className = '',
  icon: Icon,
  ...props
}) {
  const baseStyle = 'inline-flex items-center justify-center font-bold transition-colors select-none focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variants = {
    primary: 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md focus:ring-indigo-500 border border-transparent dark:bg-indigo-500 dark:hover:bg-indigo-600',
    secondary: 'bg-slate-100 hover:bg-slate-200 text-slate-800 focus:ring-slate-500 border border-transparent dark:bg-neutral-800 dark:hover:bg-neutral-700 dark:text-slate-200',
    outline: 'bg-transparent border border-slate-200 text-slate-700 hover:bg-slate-50 focus:ring-indigo-500 dark:border-neutral-700 dark:text-slate-350 dark:hover:bg-neutral-800',
    ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-indigo-500 dark:text-slate-400 dark:hover:bg-neutral-800 dark:hover:text-slate-100',
    danger: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500 border border-transparent dark:bg-red-650 dark:hover:bg-red-700'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs rounded-lg gap-1',
    md: 'px-4 py-2 text-sm rounded-xl gap-2',
    lg: 'px-6 py-3 text-base rounded-2xl gap-3'
  };

  const currentVariant = variants[variant] || variants.primary;
  const currentSize = sizes[size] || sizes.md;
  const isDisabled = disabled || loading;

  return (
    <motion.button
      whileHover={!isDisabled ? { scale: 1.015 } : {}}
      whileTap={!isDisabled ? { scale: 0.985 } : {}}
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`${baseStyle} ${currentVariant} ${currentSize} ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''} ${className}`}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
      {!loading && Icon && <Icon className="w-4 h-4 shrink-0" />}
      {children}
    </motion.button>
  );
}
