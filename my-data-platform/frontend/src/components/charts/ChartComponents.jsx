import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';

/**
 * LineChart Component
 * Display time-series data with trend lines
 */
export function LineChart({ data, xAxis, yAxis, title, showGrid = true, height = 300 }) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    // Set canvas size
    canvas.width = rect.width;
    canvas.height = height;

    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Find min/max values
    const yValues = data.map(d => d[yAxis]);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    const yRange = maxY - minY || 1;

    // Clear canvas
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
      }
    }

    // Draw axes
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    // Draw line
    ctx.strokeStyle = '#0ea5e9';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = padding + (chartWidth / (data.length - 1 || 1)) * i;
      const y = canvas.height - padding - ((data[i][yAxis] - minY) / yRange) * chartHeight;
      
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Draw points
    ctx.fillStyle = '#0ea5e9';
    for (let i = 0; i < data.length; i++) {
      const x = padding + (chartWidth / (data.length - 1 || 1)) * i;
      const y = canvas.height - padding - ((data[i][yAxis] - minY) / yRange) * chartHeight;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [data, xAxis, yAxis, height, showGrid]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <div style={{ height: `${height}px`, width: '100%' }} className="overflow-x-auto">
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%' }}
          className="dark:bg-neutral-900"
        />
      </div>
    </motion.div>
  );
}

/**
 * BarChart Component
 * Display categorical data
 */
export function BarChart({ data, xAxis, yAxis, title, height = 300, horizontal = false }) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    canvas.width = rect.width;
    canvas.height = height;

    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Find min/max
    const yValues = data.map(d => d[yAxis]);
    const minY = Math.min(...yValues, 0);
    const maxY = Math.max(...yValues);
    const yRange = maxY - minY || 1;

    // Clear
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw axes
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    // Draw bars
    const barWidth = chartWidth / data.length * 0.8;
    const barSpacing = chartWidth / data.length;

    ctx.fillStyle = '#0ea5e9';
    for (let i = 0; i < data.length; i++) {
      const value = data[i][yAxis];
      const x = padding + barSpacing * i + (barSpacing - barWidth) / 2;
      const barHeight = ((value - minY) / yRange) * chartHeight;
      const y = canvas.height - padding - barHeight;

      ctx.fillRect(x, y, barWidth, barHeight);
    }
  }, [data, xAxis, yAxis, height, horizontal]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <div style={{ height: `${height}px`, width: '100%' }} className="overflow-x-auto">
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%' }}
          className="dark:bg-neutral-900"
        />
      </div>
    </motion.div>
  );
}

/**
 * PieChart Component
 * Display composition data
 */
export function PieChart({ data, nameAxis, valueAxis, title, height = 300 }) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    canvas.width = rect.width;
    canvas.height = height;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 20;

    // Calculate total
    const total = data.reduce((sum, d) => sum + d[valueAxis], 0);

    // Colors
    const colors = [
      '#0ea5e9', '#06b6d4', '#10b981', '#f59e0b',
      '#ef4444', '#8b5cf6', '#ec4899', '#6366f1'
    ];

    // Clear
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw pie
    let startAngle = 0;
    data.forEach((item, index) => {
      const sliceAngle = (item[valueAxis] / total) * Math.PI * 2;
      
      ctx.fillStyle = colors[index % colors.length];
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
      ctx.closePath();
      ctx.fill();

      // Draw label
      const labelAngle = startAngle + sliceAngle / 2;
      const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
      const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);

      ctx.fillStyle = 'white';
      ctx.font = 'bold 12px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const percentage = Math.round((item[valueAxis] / total) * 100);
      ctx.fillText(`${percentage}%`, labelX, labelY);

      startAngle += sliceAngle;
    });
  }, [data, nameAxis, valueAxis, height]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <div style={{ height: `${height}px`, width: '100%' }}>
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%' }}
          className="dark:bg-neutral-900"
        />
      </div>
    </motion.div>
  );
}

/**
 * HeatmapChart Component
 * Display 2D data matrix
 */
export function HeatmapChart({ data, title, height = 300 }) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    canvas.width = rect.width;
    canvas.height = height;

    const rows = data.length;
    const cols = data[0].length;
    const cellWidth = canvas.width / cols;
    const cellHeight = canvas.height / rows;

    // Find min/max
    let min = Infinity, max = -Infinity;
    data.forEach(row => {
      row.forEach(val => {
        if (val < min) min = val;
        if (val > max) max = val;
      });
    });

    const range = max - min || 1;

    // Draw heatmap
    data.forEach((row, i) => {
      row.forEach((val, j) => {
        const normalized = (val - min) / range;
        const hue = (1 - normalized) * 240; // Blue to red
        
        ctx.fillStyle = `hsl(${hue}, 100%, 50%)`;
        ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth, cellHeight);

        // Draw border
        ctx.strokeStyle = 'white';
        ctx.strokeRect(j * cellWidth, i * cellHeight, cellWidth, cellHeight);
      });
    });
  }, [data, height]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <div style={{ height: `${height}px`, width: '100%' }}>
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%' }}
          className="dark:bg-neutral-900"
        />
      </div>
    </motion.div>
  );
}

/**
 * ScatterChart Component
 * Display correlation data
 */
export function ScatterChart({ data, xAxis, yAxis, title, height = 300 }) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    canvas.width = rect.width;
    canvas.height = height;

    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Find ranges
    const xValues = data.map(d => d[xAxis]);
    const yValues = data.map(d => d[yAxis]);
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    const xRange = maxX - minX || 1;
    const yRange = maxY - minY || 1;

    // Clear
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw axes
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    // Draw points
    ctx.fillStyle = '#0ea5e9';
    data.forEach(d => {
      const x = padding + ((d[xAxis] - minX) / xRange) * chartWidth;
      const y = canvas.height - padding - ((d[yAxis] - minY) / yRange) * chartHeight;
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fill();
    });
  }, [data, xAxis, yAxis, height]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <div style={{ height: `${height}px`, width: '100%' }}>
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%' }}
          className="dark:bg-neutral-900"
        />
      </div>
    </motion.div>
  );
}

/**
 * TrendCard Component
 * Display metric with trend indicator
 */
export function TrendCard({ label, value, change, isPositive = true, icon: Icon }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-neutral-600 dark:text-neutral-400 text-sm font-medium">{label}</p>
          <p className="text-3xl font-bold text-neutral-900 dark:text-white mt-2">{value}</p>
          <div className="flex items-center gap-2 mt-3">
            {isPositive ? (
              <TrendingUp className="w-4 h-4 text-green-600 dark:text-green-400" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-600 dark:text-red-400" />
            )}
            <span
              className={`text-sm font-medium ${
                isPositive
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-red-600 dark:text-red-400'
              }`}
            >
              {Math.abs(change)}% {isPositive ? 'increase' : 'decrease'}
            </span>
          </div>
        </div>
        {Icon && (
          <div className="bg-primary-50 dark:bg-primary-900/20 p-3 rounded-lg">
            <Icon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          </div>
        )}
      </div>
    </motion.div>
  );
}

/**
 * AreaChart Component
 * Display stacked area data
 */
export function AreaChart({ data, xAxis, yAxisList, title, height = 300 }) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    canvas.width = rect.width;
    canvas.height = height;

    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Calculate max for all axes
    let maxY = 0;
    data.forEach(d => {
      yAxisList.forEach(axis => {
        if (d[axis] > maxY) maxY = d[axis];
      });
    });

    // Clear
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw axes
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    // Colors for different areas
    const colors = ['#0ea5e9', '#06b6d4', '#10b981', '#f59e0b'];

    // Draw areas
    yAxisList.forEach((axis, axisIndex) => {
      ctx.fillStyle = colors[axisIndex % colors.length];
      ctx.globalAlpha = 0.5;
      ctx.beginPath();
      ctx.moveTo(padding, canvas.height - padding);

      for (let i = 0; i < data.length; i++) {
        const x = padding + (chartWidth / (data.length - 1 || 1)) * i;
        const y = canvas.height - padding - ((data[i][axis] / maxY) * chartHeight);
        if (i === 0) ctx.lineTo(x, y);
        else ctx.lineTo(x, y);
      }

      ctx.lineTo(canvas.width - padding, canvas.height - padding);
      ctx.closePath();
      ctx.fill();
    });

    ctx.globalAlpha = 1;
  }, [data, xAxis, yAxisList, height]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white dark:bg-neutral-800 rounded-lg shadow-card p-6"
    >
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <div style={{ height: `${height}px`, width: '100%' }}>
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%' }}
          className="dark:bg-neutral-900"
        />
      </div>
    </motion.div>
  );
}
