import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, Moon, Sun } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

/**
 * DashboardLayout Component
 * Main layout with sidebar and header
 */
export function DashboardLayout({ children, sidebar, logo, title }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { isDark, toggle } = useTheme();

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-900">
      {/* Desktop Sidebar */}
      <motion.div
        initial={false}
        animate={{ width: sidebarOpen ? 280 : 80 }}
        transition={{ duration: 0.3 }}
        className="hidden md:flex flex-col bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 shadow-sm"
      >
        <div className="flex items-center justify-between p-4">
          {sidebarOpen && logo && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
            >
              {logo}
            </motion.div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>
        </div>

        {sidebar && (
          <div className="flex-1 overflow-y-auto px-2">
            {typeof sidebar === 'function' ? sidebar(sidebarOpen) : sidebar}
          </div>
        )}
      </motion.div>

      {/* Mobile Sidebar */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ duration: 0.3 }}
            className="md:hidden fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 shadow-lg"
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
              {logo && <div>{logo}</div>}
              <button
                onClick={() => setMobileSidebarOpen(false)}
                className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 py-4">
              {typeof sidebar === 'function' ? sidebar(true) : sidebar}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 shadow-sm">
          <div className="flex items-center justify-between px-4 md:px-8 h-16">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
                className="md:hidden p-1 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg"
              >
                <Menu className="w-5 h-5" />
              </button>
              {title && (
                <h1 className="text-lg md:text-xl font-semibold text-neutral-900 dark:text-white">
                  {title}
                </h1>
              )}
            </div>

            {/* Header Actions */}
            <div className="flex items-center gap-4">
              <button
                onClick={toggle}
                className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
                aria-label="Toggle theme"
              >
                {isDark ? (
                  <Sun className="w-5 h-5" />
                ) : (
                  <Moon className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="p-4 md:p-8 max-w-7xl mx-auto w-full"
          >
            {children}
          </motion.div>
        </main>
      </div>

      {/* Mobile Sidebar Backdrop */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileSidebarOpen(false)}
            className="md:hidden fixed inset-0 bg-black/50 z-30"
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * SidebarNav Component
 * Navigation menu items
 */
export function SidebarNav({ items, expanded = true }) {
  const [activeItem, setActiveItem] = React.useState(items?.[0]?.id);

  return (
    <nav className="space-y-1">
      {items?.map((item) => (
        <motion.button
          key={item.id}
          onClick={() => setActiveItem(item.id)}
          className={`
            w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium
            transition-all duration-200 relative overflow-hidden
            ${
              activeItem === item.id
                ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                : 'text-neutral-700 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700'
            }
          `}
          whileHover={{ x: 4 }}
        >
          {item.icon && <span className="w-5 h-5 flex-shrink-0">{item.icon}</span>}
          {expanded && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex-1 text-left"
            >
              {item.label}
            </motion.span>
          )}
          {activeItem === item.id && (
            <motion.div
              layoutId="nav-indicator"
              className="absolute left-0 top-0 bottom-0 w-1 bg-primary-600"
            />
          )}
        </motion.button>
      ))}
    </nav>
  );
}

/**
 * PageContainer Component
 * Container for page content
 */
export function PageContainer({ children, title, description, actions }) {
  return (
    <div className="space-y-6">
      {(title || description || actions) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start justify-between"
        >
          <div>
            {title && <h1 className="text-3xl font-bold text-neutral-900 dark:text-white">{title}</h1>}
            {description && (
              <p className="mt-2 text-neutral-600 dark:text-neutral-400">{description}</p>
            )}
          </div>
          {actions && <div className="flex gap-3">{actions}</div>}
        </motion.div>
      )}
      {children}
    </div>
  );
}

/**
 * ContentGrid Component
 * Responsive grid layout
 */
export function ContentGrid({ children, columns = { sm: 1, md: 2, lg: 3 } }) {
  return (
    <div
      className={`
        grid gap-6
        grid-cols-1
        ${columns.sm ? 'sm:grid-cols-' + columns.sm : ''}
        ${columns.md ? 'md:grid-cols-' + columns.md : ''}
        ${columns.lg ? 'lg:grid-cols-' + columns.lg : ''}
      `}
    >
      {children}
    </div>
  );
}
