import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

/**
 * Data Table Component
 * Displays data in a sortable, filterable table
 */
export function DataTable({
  columns,
  data,
  onRowClick,
  selectable = false,
  sortable = true,
  paginated = true,
  itemsPerPage = 10,
}) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [currentPage, setCurrentPage] = useState(1);

  // Sort data
  const sortedData = useMemo(() => {
    let sorted = [...data];
    if (sortConfig.key && sortable) {
      sorted.sort((a, b) => {
        const aValue = a[sortConfig.key];
        const bValue = b[sortConfig.key];

        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return sorted;
  }, [data, sortConfig, sortable]);

  // Paginate data
  const paginatedData = useMemo(() => {
    if (!paginated) return sortedData;
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    return sortedData.slice(start, end);
  }, [sortedData, currentPage, itemsPerPage, paginated]);

  const totalPages = Math.ceil(sortedData.length / itemsPerPage);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const allRows = new Set(paginatedData.map((_, index) => index));
      setSelectedRows(allRows);
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleSelectRow = (index) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedRows(newSelected);
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown className="w-4 h-4 opacity-50" />;
    }
    return sortConfig.direction === 'asc' ? (
      <ChevronUp className="w-4 h-4" />
    ) : (
      <ChevronDown className="w-4 h-4" />
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card overflow-hidden"
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-700/50">
              {selectable && (
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    onChange={handleSelectAll}
                    checked={selectedRows.size === paginatedData.length && paginatedData.length > 0}
                    className="rounded"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.key}
                  onClick={() => column.sortable !== false && handleSort(column.key)}
                  className={`
                    px-6 py-3 text-left text-sm font-semibold text-neutral-700 dark:text-neutral-300
                    ${column.sortable !== false ? 'cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-600' : ''}
                  `}
                >
                  <div className="flex items-center gap-2">
                    {column.label}
                    {column.sortable !== false && <SortIcon columnKey={column.key} />}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, rowIndex) => (
              <motion.tr
                key={rowIndex}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`
                  border-b border-neutral-100 dark:border-neutral-700
                  hover:bg-neutral-50 dark:hover:bg-neutral-700/50
                  transition-colors
                  ${onRowClick ? 'cursor-pointer' : ''}
                  ${selectedRows.has(rowIndex) ? 'bg-primary-50 dark:bg-primary-900/20' : ''}
                `}
                onClick={() => onRowClick?.(row)}
              >
                {selectable && (
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedRows.has(rowIndex)}
                      onChange={() => handleSelectRow(rowIndex)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded"
                    />
                  </td>
                )}
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300"
                  >
                    {column.render ? column.render(row[column.key], row) : row[column.key]}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {paginated && totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200 dark:border-neutral-700">
          <span className="text-sm text-neutral-600 dark:text-neutral-400">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border rounded-md disabled:opacity-50 hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border rounded-md disabled:opacity-50 hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}

/**
 * Form Builder Component
 * Dynamic form generation
 */
export function FormBuilder({
  fields,
  onSubmit,
  submitLabel = 'Submit',
  isLoading = false,
}) {
  const [values, setValues] = React.useState(() => {
    const initial = {};
    fields.forEach((field) => {
      initial[field.name] = field.defaultValue || '';
    });
    return initial;
  });

  const [errors, setErrors] = React.useState({});

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setValues((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};

    fields.forEach((field) => {
      if (field.required && !values[field.name]) {
        newErrors[field.name] = `${field.label} is required`;
      }
      if (field.validate) {
        const error = field.validate(values[field.name]);
        if (error) newErrors[field.name] = error;
      }
    });

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      await onSubmit(values);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {fields.map((field) => (
        <div key={field.name}>
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
            {field.label}
            {field.required && <span className="text-red-600">*</span>}
          </label>

          {field.type === 'textarea' ? (
            <textarea
              name={field.name}
              value={values[field.name]}
              onChange={handleChange}
              placeholder={field.placeholder}
              rows={field.rows || 4}
              className="w-full px-4 py-2 border-2 border-neutral-200 dark:border-neutral-700 rounded-lg
                bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white
                focus:border-primary-500 dark:focus:border-primary-400
                transition-colors outline-none"
            />
          ) : field.type === 'select' ? (
            <select
              name={field.name}
              value={values[field.name]}
              onChange={handleChange}
              className="w-full px-4 py-2 border-2 border-neutral-200 dark:border-neutral-700 rounded-lg
                bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white
                focus:border-primary-500 dark:focus:border-primary-400
                transition-colors outline-none"
            >
              <option value="">Select {field.label}</option>
              {field.options?.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : field.type === 'checkbox' ? (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                name={field.name}
                checked={values[field.name]}
                onChange={handleChange}
                className="rounded"
              />
              <span className="text-sm text-neutral-700 dark:text-neutral-300">
                {field.description}
              </span>
            </label>
          ) : (
            <input
              type={field.type || 'text'}
              name={field.name}
              value={values[field.name]}
              onChange={handleChange}
              placeholder={field.placeholder}
              className="w-full px-4 py-2 border-2 border-neutral-200 dark:border-neutral-700 rounded-lg
                bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white
                placeholder-neutral-400 dark:placeholder-neutral-500
                focus:border-primary-500 dark:focus:border-primary-400
                transition-colors outline-none"
            />
          )}

          {errors[field.name] && (
            <p className="text-sm text-red-600 dark:text-red-400 mt-1">
              {errors[field.name]}
            </p>
          )}
        </div>
      ))}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full px-4 py-2 bg-primary-600 text-white font-medium rounded-lg
          hover:bg-primary-700 disabled:opacity-50 transition-colors
          flex items-center justify-center gap-2"
      >
        {isLoading && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
        {submitLabel}
      </button>
    </form>
  );
}

/**
 * Statistics Card Component
 * Display metric with trend
 */
export function StatCard({ label, value, change, icon: Icon, color = 'primary' }) {
  const isPositive = change >= 0;
  const colorClasses = {
    primary: 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300',
    success: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300',
    warning: 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300',
    error: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-neutral-800 rounded-lg p-6 shadow-card"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-neutral-600 dark:text-neutral-400 text-sm font-medium">{label}</p>
          <p className="text-3xl font-bold text-neutral-900 dark:text-white mt-2">{value}</p>
          {change !== undefined && (
            <p
              className={`text-sm font-medium mt-2 ${
                isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}
            >
              {isPositive ? '↑' : '↓'} {Math.abs(change)}%
            </p>
          )}
        </div>
        {Icon && (
          <div className={`${colorClasses[color]} p-3 rounded-lg`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </motion.div>
  );
}
