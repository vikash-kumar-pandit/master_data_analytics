import React, { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';

const ToastContext = createContext();

/**
 * Toast Provider Component
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = Date.now();
    const toast = { id, message, type, duration };

    setToasts((prev) => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const value = {
    toasts,
    addToast,
    removeToast,
    success: (msg, duration) => addToast(msg, 'success', duration),
    error: (msg, duration) => addToast(msg, 'error', duration),
    warning: (msg, duration) => addToast(msg, 'warning', duration),
    info: (msg, duration) => addToast(msg, 'info', duration),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

/**
 * Toast Hook
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

/**
 * Toast Container Component
 */
function ToastContainer({ toasts, onRemove }) {
  return (
    <div className="fixed bottom-4 right-4 z-[9999] pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast, index) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            index={index}
            onRemove={onRemove}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

/**
 * Toast Item Component
 */
function ToastItem({ toast, index, onRemove }) {
  const toastConfig = {
    success: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      text: 'text-green-800 dark:text-green-100',
      icon: <CheckCircle2 className="w-5 h-5" />,
      iconColor: 'text-green-600 dark:text-green-400',
    },
    error: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-800 dark:text-red-100',
      icon: <AlertCircle className="w-5 h-5" />,
      iconColor: 'text-red-600 dark:text-red-400',
    },
    warning: {
      bg: 'bg-yellow-50 dark:bg-yellow-900/20',
      border: 'border-yellow-200 dark:border-yellow-800',
      text: 'text-yellow-800 dark:text-yellow-100',
      icon: <AlertTriangle className="w-5 h-5" />,
      iconColor: 'text-yellow-600 dark:text-yellow-400',
    },
    info: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      text: 'text-blue-800 dark:text-blue-100',
      icon: <Info className="w-5 h-5" />,
      iconColor: 'text-blue-600 dark:text-blue-400',
    },
  };

  const config = toastConfig[toast.type] || toastConfig.info;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, x: 0 }}
      animate={{ opacity: 1, y: index * 80, x: 0 }}
      exit={{ opacity: 0, y: 20, x: 100 }}
      transition={{ duration: 0.3 }}
      className="pointer-events-auto mb-3"
    >
      <div
        className={`
          flex items-start gap-3 p-4 rounded-lg shadow-lg
          border-2 ${config.bg} ${config.border} ${config.text}
          max-w-md w-full
        `}
      >
        <div className={config.iconColor}>{config.icon}</div>
        <div className="flex-1 break-words">{toast.message}</div>
        <button
          onClick={() => onRemove(toast.id)}
          className="flex-shrink-0 ml-2 hover:opacity-70 transition-opacity"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  );
}

/**
 * Dialog Provider Component
 */
const DialogContext = createContext();

export function DialogProvider({ children }) {
  const [dialogs, setDialogs] = useState([]);

  const openDialog = useCallback((config) => {
    const id = Date.now();
    const dialog = {
      id,
      ...config,
    };

    setDialogs((prev) => [...prev, dialog]);
    return id;
  }, []);

  const closeDialog = useCallback((id) => {
    setDialogs((prev) => prev.filter((dialog) => dialog.id !== id));
  }, []);

  const value = {
    dialogs,
    openDialog,
    closeDialog,
  };

  return (
    <DialogContext.Provider value={value}>
      {children}
      <DialogContainer dialogs={dialogs} onClose={closeDialog} />
    </DialogContext.Provider>
  );
}

/**
 * Dialog Hook
 */
export function useDialog() {
  const context = useContext(DialogContext);
  if (!context) {
    throw new Error('useDialog must be used within DialogProvider');
  }
  return context;
}

/**
 * Dialog Container Component
 */
function DialogContainer({ dialogs, onClose }) {
  return (
    <AnimatePresence>
      {dialogs.map((dialog) => (
        <ConfirmDialog
          key={dialog.id}
          dialog={dialog}
          onClose={onClose}
        />
      ))}
    </AnimatePresence>
  );
}

/**
 * Confirm Dialog Component
 */
function ConfirmDialog({ dialog, onClose }) {
  const {
    id,
    title,
    message,
    type = 'info',
    onConfirm,
    onCancel,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
  } = dialog;

  const typeStyles = {
    info: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    warning: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
    error: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    success: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  };

  const icons = {
    info: <Info className="w-6 h-6" />,
    warning: <AlertTriangle className="w-6 h-6" />,
    error: <AlertCircle className="w-6 h-6" />,
    success: <CheckCircle2 className="w-6 h-6" />,
  };

  const handleConfirm = async () => {
    if (onConfirm) {
      await onConfirm();
    }
    onClose(id);
  };

  const handleCancel = async () => {
    if (onCancel) {
      await onCancel();
    }
    onClose(id);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={handleCancel}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="relative bg-white dark:bg-neutral-800 rounded-lg shadow-lg max-w-sm w-full mx-4 p-6"
      >
        <div className="flex gap-4">
          <div className={`${typeStyles[type]} p-2 rounded-lg flex-shrink-0`}>
            {icons[type]}
          </div>
          <div className="flex-1">
            {title && (
              <h2 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
                {title}
              </h2>
            )}
            <p className="text-neutral-600 dark:text-neutral-400">{message}</p>
          </div>
        </div>

        <div className="flex gap-3 mt-6 justify-end">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 bg-primary-600 text-white hover:bg-primary-700 rounded-lg transition-colors"
          >
            {confirmText}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
