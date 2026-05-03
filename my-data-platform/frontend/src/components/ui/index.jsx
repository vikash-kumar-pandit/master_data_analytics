import React from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';

/**
 * Alert Component
 * Displays alert messages with different severity levels
 */
export function Alert({ type = 'info', title, children, icon: Icon, onClose }) {
  const styles = {
    info: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      text: 'text-blue-800 dark:text-blue-100',
      icon: 'text-blue-600 dark:text-blue-400',
      icon_default: Info,
    },
    success: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      text: 'text-green-800 dark:text-green-100',
      icon: 'text-green-600 dark:text-green-400',
      icon_default: CheckCircle2,
    },
    warning: {
      bg: 'bg-yellow-50 dark:bg-yellow-900/20',
      border: 'border-yellow-200 dark:border-yellow-800',
      text: 'text-yellow-800 dark:text-yellow-100',
      icon: 'text-yellow-600 dark:text-yellow-400',
      icon_default: AlertTriangle,
    },
    error: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-800 dark:text-red-100',
      icon: 'text-red-600 dark:text-red-400',
      icon_default: AlertCircle,
    },
  };

  const style = styles[type] || styles.info;
  const IconComponent = Icon || style.icon_default;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`${style.bg} ${style.border} border rounded-md p-4 flex gap-3`}
    >
      <IconComponent className={`${style.icon} flex-shrink-0 w-5 h-5 mt-0.5`} />
      <div className="flex-1">
        {title && <h3 className={`font-semibold ${style.text} mb-1`}>{title}</h3>}
        <div className={style.text}>{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className={`${style.icon} hover:opacity-70 transition-opacity flex-shrink-0`}
          aria-label="Close"
        >
          ✕
        </button>
      )}
    </motion.div>
  );
}

/**
 * Badge Component
 * Compact label for categorization
 */
export function Badge({ children, variant = 'default', className = '' }) {
  const variants = {
    default: 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300',
    secondary: 'bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-300',
    accent: 'bg-accent-100 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300',
    neutral: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300',
    outline: 'border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

/**
 * Button Component
 * Flexible button with multiple variants
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon: Icon,
  className = '',
  ...props
}) {
  const variants = {
    primary: 'bg-primary-600 dark:bg-primary-500 text-white hover:bg-primary-700 dark:hover:bg-primary-600',
    secondary: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 hover:bg-neutral-200 dark:hover:bg-neutral-700',
    accent: 'bg-accent-600 dark:bg-accent-500 text-white hover:bg-accent-700 dark:hover:bg-accent-600',
    outline: 'border-2 border-primary-600 dark:border-primary-400 text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20',
    ghost: 'text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm rounded-md',
    md: 'px-4 py-2 text-base rounded-md',
    lg: 'px-6 py-3 text-lg rounded-lg',
    xl: 'px-8 py-4 text-xl rounded-lg',
  };

  return (
    <button
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 font-medium
        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}
      `}
      {...props}
    >
      {loading && <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />}
      {Icon && <Icon className="w-5 h-5" />}
      {children}
    </button>
  );
}

/**
 * Card Component
 * Container for grouped content
 */
export function Card({ children, className = '', hover = false }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`
        bg-white dark:bg-neutral-800 rounded-lg shadow-card
        ${hover ? 'hover:shadow-hover transition-shadow cursor-pointer' : ''}
        ${className}
      `}
    >
      {children}
    </motion.div>
  );
}

/**
 * Input Component
 * Text input field
 */
export function Input({
  label,
  error,
  icon: Icon,
  className = '',
  ...props
}) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && <Icon className="absolute left-3 top-3 w-5 h-5 text-neutral-400" />}
        <input
          className={`
            w-full px-4 py-2 rounded-lg border-2 border-neutral-200 dark:border-neutral-700
            bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white
            placeholder-neutral-400 dark:placeholder-neutral-500
            focus:outline-none focus:border-primary-500 dark:focus:border-primary-400
            transition-colors duration-200
            ${Icon ? 'pl-10' : ''} ${error ? 'border-red-500' : ''} ${className}
          `}
          {...props}
        />
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>}
    </div>
  );
}

/**
 * Spinner Component
 * Loading indicator
 */
export function Spinner({ size = 'md' }) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`${sizes[size]} border-3 border-primary-200 dark:border-primary-800 border-t-primary-600 dark:border-t-primary-400 rounded-full animate-spin`} />
  );
}

/**
 * Progress Component
 * Progress bar indicator
 */
export function Progress({ value, max = 100, showLabel = true }) {
  const percentage = (value / max) * 100;

  return (
    <div className="w-full">
      <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
          className="h-full bg-gradient-to-r from-primary-500 to-primary-600"
        />
      </div>
      {showLabel && (
        <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">{Math.round(percentage)}%</p>
      )}
    </div>
  );
}

/**
 * Tooltip Component
 * Information on hover
 */
export function Tooltip({ children, content, side = 'top' }) {
  const [showTooltip, setShowTooltip] = React.useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {children}
      </div>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className={`
            absolute z-10 px-3 py-2 text-sm font-medium
            bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900
            rounded-md whitespace-nowrap shadow-lg
            ${side === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}
          `}
        >
          {content}
          <div
            className={`
              absolute w-2 h-2 bg-neutral-900 dark:bg-neutral-100 rotate-45
              ${side === 'top' ? 'top-full -mt-1' : 'bottom-full mb-1'}
              left-1/2 -translate-x-1/2
            `}
          />
        </motion.div>
      )}
    </div>
  );
}

/**
 * Modal Component
 * Dialog overlay
 */
export function Modal({ isOpen, onClose, title, children, footer }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="relative bg-white dark:bg-neutral-800 rounded-lg shadow-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
      >
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">{title}</h2>
            <button
              onClick={onClose}
              className="text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            >
              ✕
            </button>
          </div>
        )}
        <div className="px-6 py-4">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700">{footer}</div>}
      </motion.div>
    </div>
  );
}

/**
 * Tabs Component
 * Tab navigation
 */
export function Tabs({ tabs, defaultTab = 0, onChange }) {
  const [activeTab, setActiveTab] = React.useState(defaultTab);

  const handleTabClick = (index) => {
    setActiveTab(index);
    onChange?.(index);
  };

  return (
    <div>
      <div className="flex gap-1 border-b border-neutral-200 dark:border-neutral-700">
        {tabs.map((tab, index) => (
          <button
            key={index}
            onClick={() => handleTabClick(index)}
            className={`
              px-4 py-3 font-medium text-sm transition-colors relative
              ${
                activeTab === index
                  ? 'text-primary-600 dark:text-primary-400'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
              }
            `}
          >
            {tab.label}
            {activeTab === index && (
              <motion.div
                layoutId="tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-1 bg-primary-600 dark:bg-primary-400"
              />
            )}
          </button>
        ))}
      </div>
      <div className="mt-4">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
        >
          {tabs[activeTab]?.content}
        </motion.div>
      </div>
    </div>
  );
}
