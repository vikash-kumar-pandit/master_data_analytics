import React, { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Funnel,
  FunnelChart,
  LabelList,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Sankey,
  Scatter,
  ScatterChart,
  Tooltip,
  Treemap,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

const CHART_DEFINITIONS = [
  {
    key: 'bar',
    title: 'Bar Chart',
    category: 'Comparison',
    description: 'Category-wise count comparison.',
    requirement: (profile) => profile.categoricalColumns.length >= 1,
  },
  {
    key: 'stackedBar',
    title: 'Stacked Bar Chart',
    category: 'Comparison',
    description: 'Compare multiple metrics by category.',
    requirement: (profile) => profile.categoricalColumns.length >= 1 && profile.numericColumns.length >= 2,
  },
  {
    key: 'line',
    title: 'Line Chart',
    category: 'Trend',
    description: 'Time-series or ordered trend analysis.',
    requirement: (profile) => profile.numericColumns.length >= 1,
  },
  {
    key: 'area',
    title: 'Area Chart',
    category: 'Trend',
    description: 'Trend with emphasis on volume.',
    requirement: (profile) => profile.numericColumns.length >= 1,
  },
  {
    key: 'pie',
    title: 'Pie Chart',
    category: 'Composition',
    description: 'Share distribution across categories.',
    requirement: (profile) => profile.categoricalColumns.length >= 1,
  },
  {
    key: 'donut',
    title: 'Donut Chart',
    category: 'Composition',
    description: 'Pie chart with center total view.',
    requirement: (profile) => profile.categoricalColumns.length >= 1,
  },
  {
    key: 'histogram',
    title: 'Histogram',
    category: 'Distribution',
    description: 'Distribution of a numeric variable.',
    requirement: (profile) => profile.numericColumns.length >= 1,
  },
  {
    key: 'scatter',
    title: 'Scatter Plot',
    category: 'Relationship',
    description: 'Relationship between two numeric fields.',
    requirement: (profile) => profile.numericColumns.length >= 2,
  },
  {
    key: 'bubble',
    title: 'Bubble Chart',
    category: 'Relationship',
    description: '3-variable relationship with bubble size.',
    requirement: (profile) => profile.numericColumns.length >= 3,
  },
  {
    key: 'radar',
    title: 'Radar Chart',
    category: 'Multivariate',
    description: 'Compare multiple metrics across categories.',
    requirement: (profile) => profile.categoricalColumns.length >= 1 && profile.numericColumns.length >= 2,
  },
  {
    key: 'treemap',
    title: 'Treemap',
    category: 'Hierarchy',
    description: 'Category blocks sized by measure.',
    requirement: (profile) => profile.categoricalColumns.length >= 1,
  },
  {
    key: 'funnel',
    title: 'Funnel Chart',
    category: 'Process',
    description: 'Stage-wise conversion analysis from top groups.',
    requirement: (profile) => profile.categoricalColumns.length >= 1,
  },
  {
    key: 'waterfall',
    title: 'Waterfall Chart',
    category: 'Contribution',
    description: 'Step-wise contribution and cumulative movement.',
    requirement: (profile) => profile.categoricalColumns.length >= 1 && profile.numericColumns.length >= 1,
  },
  {
    key: 'sankey',
    title: 'Sankey Diagram',
    category: 'Flow',
    description: 'Flow between two categorical dimensions.',
    requirement: (profile) => profile.categoricalColumns.length >= 2,
  },
  {
    key: 'qualityStack',
    title: 'Quality Stack',
    category: 'Data Quality',
    description: 'Valid vs missing values by columns.',
    requirement: () => true,
  },
  {
    key: 'severityMix',
    title: 'Audit Severity Mix',
    category: 'Data Quality',
    description: 'Error severity distribution from audit report.',
    requirement: () => true,
  },
];

const CHART_COLORS = ['#0ea5e9', '#2563eb', '#14b8a6', '#f97316', '#ef4444', '#22c55e', '#a855f7', '#f59e0b'];

function toNumber(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function parseDate(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function detectProfile(rows = [], analysis = {}, domainData = {}) {
  if (!rows.length) {
    return {
      totalRows: 0,
      columns: [],
      numericColumns: [],
      dateColumns: [],
      categoricalColumns: [],
      category: analysis?.category || null,
      domain: domainData?.domain || null,
      auditErrors: analysis?.audit_errors || [],
      nullCounts: analysis?.null_counts || [],
    };
  }

  const sampleRows = rows.slice(0, 1000);
  const columns = Object.keys(sampleRows[0] || {});

  const numericColumns = [];
  const dateColumns = [];
  const categoricalColumns = [];

  columns.forEach((columnName) => {
    const values = sampleRows.map((row) => row?.[columnName]).filter((value) => value !== null && value !== undefined && value !== '');
    if (!values.length) {
      categoricalColumns.push(columnName);
      return;
    }

    const numericHits = values.filter((value) => toNumber(value) !== null).length;
    const dateHits = values.filter((value) => parseDate(value) !== null).length;

    const numericRatio = numericHits / values.length;
    const dateRatio = dateHits / values.length;

    if (numericRatio >= 0.8) {
      numericColumns.push(columnName);
      return;
    }

    if (dateRatio >= 0.8) {
      dateColumns.push(columnName);
      return;
    }

    categoricalColumns.push(columnName);
  });

  return {
    totalRows: rows.length,
    columns,
    numericColumns,
    dateColumns,
    categoricalColumns,
    category: analysis?.category || null,
    domain: domainData?.domain || null,
    auditErrors: analysis?.audit_errors || [],
    nullCounts: analysis?.null_counts || [],
  };
}

function aggregateByCategory(rows, categoryCol, valueCols = []) {
  const buckets = new Map();

  rows.slice(0, 3000).forEach((row) => {
    const key = String(row?.[categoryCol] ?? 'Unknown').trim() || 'Unknown';
    if (!buckets.has(key)) {
      buckets.set(key, { name: key, count: 0, sums: valueCols.map(() => 0), numericCounts: valueCols.map(() => 0) });
    }

    const entry = buckets.get(key);
    entry.count += 1;

    valueCols.forEach((col, index) => {
      const n = toNumber(row?.[col]);
      if (n !== null) {
        entry.sums[index] += n;
        entry.numericCounts[index] += 1;
      }
    });
  });

  return [...buckets.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, 12)
    .map((entry) => {
      const row = { name: entry.name, count: entry.count };
      valueCols.forEach((col, index) => {
        row[col] = entry.numericCounts[index] ? Number((entry.sums[index] / entry.numericCounts[index]).toFixed(2)) : 0;
      });
      return row;
    });
}

function buildHistogram(rows, numericCol, bins = 10) {
  const values = rows
    .slice(0, 5000)
    .map((row) => toNumber(row?.[numericCol]))
    .filter((value) => value !== null);

  if (!values.length) {
    return [];
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return [{ bin: String(min), value: values.length }];
  }

  const step = (max - min) / bins;
  const histogram = Array.from({ length: bins }, (_, index) => ({
    bin: `${(min + index * step).toFixed(1)} - ${(min + (index + 1) * step).toFixed(1)}`,
    value: 0,
  }));

  values.forEach((value) => {
    const idx = Math.min(Math.floor((value - min) / step), bins - 1);
    histogram[idx].value += 1;
  });

  return histogram;
}

function buildTrend(rows, dateCol, numericCol) {
  const series = rows
    .slice(0, 5000)
    .map((row, index) => {
      const rawDate = dateCol ? row?.[dateCol] : index + 1;
      const parsedDate = dateCol ? parseDate(rawDate) : null;
      const value = toNumber(row?.[numericCol]);
      if (value === null) {
        return null;
      }
      return {
        label: dateCol
          ? parsedDate !== null
            ? new Date(parsedDate).toLocaleDateString()
            : String(rawDate)
          : `Row ${index + 1}`,
        rawOrder: dateCol ? parsedDate ?? index : index,
        value,
      };
    })
    .filter(Boolean)
    .sort((a, b) => Number(a.rawOrder) - Number(b.rawOrder))
    .slice(0, 200);

  return series;
}

function buildScatter(rows, xCol, yCol, zCol = null) {
  return rows
    .slice(0, 500)
    .map((row) => {
      const x = toNumber(row?.[xCol]);
      const y = toNumber(row?.[yCol]);
      if (x === null || y === null) {
        return null;
      }
      const point = { x, y };
      if (zCol) {
        const z = toNumber(row?.[zCol]);
        point.z = z === null ? 10 : Math.max(5, Math.min(60, z));
      }
      return point;
    })
    .filter(Boolean);
}

function buildFunnelData(categoryData) {
  return categoryData
    .slice(0, 8)
    .sort((a, b) => Number(b.count) - Number(a.count))
    .map((item) => ({ name: item.name, value: item.count }));
}

function buildWaterfallData(categoryData, numericCol) {
  let cumulative = 0;
  return categoryData.slice(0, 10).map((item) => {
    const delta = Number(item?.[numericCol] || 0);
    cumulative += delta;
    return {
      name: item.name,
      delta,
      cumulative: Number(cumulative.toFixed(2)),
      fill: delta >= 0 ? '#14b8a6' : '#ef4444',
    };
  });
}

function buildSankeyData(rows, sourceCol, targetCol) {
  const nodeIndex = new Map();
  const nodes = [];
  const linkMap = new Map();

  rows.slice(0, 4000).forEach((row) => {
    const source = String(row?.[sourceCol] ?? 'Unknown').trim() || 'Unknown';
    const target = String(row?.[targetCol] ?? 'Unknown').trim() || 'Unknown';

    if (!nodeIndex.has(source)) {
      nodeIndex.set(source, nodes.length);
      nodes.push({ name: source });
    }
    if (!nodeIndex.has(target)) {
      nodeIndex.set(target, nodes.length);
      nodes.push({ name: target });
    }

    const key = `${source}__${target}`;
    linkMap.set(key, (linkMap.get(key) || 0) + 1);
  });

  const links = [...linkMap.entries()]
    .map(([key, value]) => {
      const [source, target] = key.split('__');
      return {
        source: nodeIndex.get(source),
        target: nodeIndex.get(target),
        value,
      };
    })
    .sort((a, b) => b.value - a.value)
    .slice(0, 35);

  return { nodes, links };
}

function buildQualityData(columns, rows, nullCountsFromAnalysis) {
  const totalRows = rows.length;
  const nullMap = (nullCountsFromAnalysis && nullCountsFromAnalysis[0]) || {};

  return columns.slice(0, 20).map((column) => {
    const missing = Number(nullMap[column] || 0);
    return {
      columnName: column,
      valid: Math.max(totalRows - missing, 0),
      missing,
    };
  });
}

function buildSeverityData(auditErrors = []) {
  const buckets = {};
  auditErrors.forEach((issue) => {
    const severity = String(issue?.severity || 'Unknown');
    buckets[severity] = (buckets[severity] || 0) + 1;
  });

  return Object.entries(buckets).map(([severity, count]) => ({ severity, count }));
}

function EmptyChart({ text }) {
  return <p className="graph-gallery-empty">{text}</p>;
}

export default function GraphGallery({ rows = [], analysis = null, domainData = null }) {
  const profile = useMemo(() => detectProfile(rows, analysis, domainData), [rows, analysis, domainData]);

  const chartList = useMemo(() => {
    return CHART_DEFINITIONS.map((chart) => {
      const enabled = chart.requirement(profile);
      return {
        ...chart,
        enabled,
      };
    });
  }, [profile]);

  const enabledChartKeys = useMemo(
    () => chartList.filter((item) => item.enabled).map((item) => item.key),
    [chartList]
  );

  const [selectedChartKeys, setSelectedChartKeys] = useState([]);
  const [viewMode, setViewMode] = useState('multiple');

  useEffect(() => {
    setSelectedChartKeys(enabledChartKeys);
  }, [enabledChartKeys.join('|')]);

  const chartDataPack = useMemo(() => {
    const categoryCol = profile.categoricalColumns[0];
    const categoryCol2 = profile.categoricalColumns[1];
    const numericCol1 = profile.numericColumns[0];
    const numericCol2 = profile.numericColumns[1];
    const numericCol3 = profile.numericColumns[2];
    const dateCol = profile.dateColumns[0];

    const categoryAgg = categoryCol ? aggregateByCategory(rows, categoryCol, [numericCol1, numericCol2].filter(Boolean)) : [];
    const qualityData = buildQualityData(profile.columns, rows, profile.nullCounts);
    const severityData = buildSeverityData(profile.auditErrors);
    const funnelData = buildFunnelData(categoryAgg);
    const waterfallData = categoryCol && numericCol1 ? buildWaterfallData(categoryAgg, numericCol1) : [];
    const sankeyData = categoryCol && categoryCol2 ? buildSankeyData(rows, categoryCol, categoryCol2) : { nodes: [], links: [] };

    return {
      categoryCol,
      categoryCol2,
      numericCol1,
      numericCol2,
      numericCol3,
      dateCol,
      bar: categoryAgg,
      stackedBar: categoryAgg,
      pie: categoryAgg.map((item) => ({ name: item.name, value: item.count })),
      donut: categoryAgg.map((item) => ({ name: item.name, value: item.count })),
      treemap: categoryAgg.map((item) => ({ name: item.name, size: item.count })),
      histogram: numericCol1 ? buildHistogram(rows, numericCol1) : [],
      line: numericCol1 ? buildTrend(rows, dateCol, numericCol1) : [],
      area: numericCol1 ? buildTrend(rows, dateCol, numericCol1) : [],
      scatter: numericCol1 && numericCol2 ? buildScatter(rows, numericCol1, numericCol2) : [],
      bubble: numericCol1 && numericCol2 && numericCol3 ? buildScatter(rows, numericCol1, numericCol2, numericCol3) : [],
      radar:
        categoryCol && numericCol1 && numericCol2
          ? aggregateByCategory(rows, categoryCol, [numericCol1, numericCol2]).map((item) => ({
              subject: item.name,
              [numericCol1]: item[numericCol1],
              [numericCol2]: item[numericCol2],
            }))
          : [],
      funnel: funnelData,
      waterfall: waterfallData,
      sankey: sankeyData,
      qualityStack: qualityData,
      severityMix: severityData,
    };
  }, [rows, profile]);

  const selectedCharts = useMemo(() => {
    const allowed = new Set(enabledChartKeys);
    const fromSelection = selectedChartKeys.filter((key) => allowed.has(key));
    return fromSelection.length ? fromSelection : enabledChartKeys.slice(0, 1);
  }, [selectedChartKeys, enabledChartKeys]);

  const toggleChartSelection = (key) => {
    if (!enabledChartKeys.includes(key)) {
      return;
    }

    if (viewMode === 'single') {
      setSelectedChartKeys([key]);
      return;
    }

    setSelectedChartKeys((current) => {
      if (current.includes(key)) {
        const next = current.filter((item) => item !== key);
        return next.length ? next : [key];
      }
      return [...current, key];
    });
  };

  const selectAllEnabled = () => {
    setViewMode('multiple');
    setSelectedChartKeys(enabledChartKeys);
  };

  const clearSelection = () => {
    setSelectedChartKeys(enabledChartKeys.slice(0, 1));
    setViewMode('single');
  };

  const renderChartByKey = (chartKey) => {
    switch (chartKey) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartDataPack.bar}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="name" angle={-20} textAnchor="end" interval={0} height={78} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#0ea5e9" name={`Count by ${chartDataPack.categoryCol || 'Category'}`} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'stackedBar':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartDataPack.stackedBar}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="name" angle={-20} textAnchor="end" interval={0} height={78} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey={chartDataPack.numericCol1} stackId="a" fill="#0ea5e9" name={chartDataPack.numericCol1 || 'Metric 1'} />
              <Bar dataKey={chartDataPack.numericCol2} stackId="a" fill="#14b8a6" name={chartDataPack.numericCol2 || 'Metric 2'} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartDataPack.line}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="label" minTickGap={20} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={false} name={chartDataPack.numericCol1 || 'Value'} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={chartDataPack.area}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="label" minTickGap={20} />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke="#0ea5e9" fill="#93c5fd" name={chartDataPack.numericCol1 || 'Value'} />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie data={chartDataPack.pie} dataKey="value" nameKey="name" outerRadius={110} label>
                {chartDataPack.pie.map((entry, index) => (
                  <Cell key={`${entry.name}-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'donut':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie data={chartDataPack.donut} dataKey="value" nameKey="name" innerRadius={60} outerRadius={110} label>
                {chartDataPack.donut.map((entry, index) => (
                  <Cell key={`${entry.name}-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'histogram':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartDataPack.histogram}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="bin" angle={-15} textAnchor="end" interval={0} height={80} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#f97316" name={chartDataPack.numericCol1 || 'Distribution'} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis type="number" dataKey="x" name={chartDataPack.numericCol1} />
              <YAxis type="number" dataKey="y" name={chartDataPack.numericCol2} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={chartDataPack.scatter} fill="#2563eb" />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'bubble':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis type="number" dataKey="x" name={chartDataPack.numericCol1} />
              <YAxis type="number" dataKey="y" name={chartDataPack.numericCol2} />
              <ZAxis type="number" dataKey="z" range={[60, 320]} name={chartDataPack.numericCol3} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={chartDataPack.bubble} fill="#14b8a6" />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'radar':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart outerRadius={105} data={chartDataPack.radar}>
              <PolarGrid stroke="#cbd5e1" />
              <PolarAngleAxis dataKey="subject" />
              <PolarRadiusAxis />
              <Tooltip />
              <Legend />
              <Radar name={chartDataPack.numericCol1 || 'Metric 1'} dataKey={chartDataPack.numericCol1} stroke="#2563eb" fill="#2563eb" fillOpacity={0.28} />
              <Radar name={chartDataPack.numericCol2 || 'Metric 2'} dataKey={chartDataPack.numericCol2} stroke="#14b8a6" fill="#14b8a6" fillOpacity={0.2} />
            </RadarChart>
          </ResponsiveContainer>
        );

      case 'treemap':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <Treemap data={chartDataPack.treemap} dataKey="size" stroke="#fff" fill="#0ea5e9" nameKey="name" />
          </ResponsiveContainer>
        );

      case 'funnel':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <FunnelChart>
              <Tooltip />
              <Funnel dataKey="value" data={chartDataPack.funnel} isAnimationActive>
                <LabelList position="right" fill="#0f172a" stroke="none" dataKey="name" />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        );

      case 'waterfall':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={chartDataPack.waterfall}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="name" angle={-20} textAnchor="end" interval={0} height={78} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="delta" name="Step Delta">
                {chartDataPack.waterfall.map((item) => (
                  <Cell key={item.name} fill={item.fill} />
                ))}
              </Bar>
              <Line type="monotone" dataKey="cumulative" stroke="#1d4ed8" strokeWidth={2} name="Cumulative" />
            </ComposedChart>
          </ResponsiveContainer>
        );

      case 'sankey':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <Sankey
              data={chartDataPack.sankey}
              nodePadding={25}
              nodeWidth={16}
              linkCurvature={0.5}
              iterations={32}
            >
              <Tooltip />
            </Sankey>
          </ResponsiveContainer>
        );

      case 'qualityStack':
        return (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartDataPack.qualityStack} margin={{ top: 20, right: 20, left: 0, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
              <XAxis dataKey="columnName" stroke="#334155" angle={-20} textAnchor="end" interval={0} height={72} />
              <YAxis stroke="#334155" allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="valid" stackId="a" fill="#16a34a" name="Valid" animationDuration={1200} />
              <Bar dataKey="missing" stackId="a" fill="#ef4444" name="Missing" animationDuration={1200} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'severityMix':
        if (!chartDataPack.severityMix.length) {
          return <EmptyChart text="No audit severity data available for this dataset." />;
        }
        return (
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie data={chartDataPack.severityMix} dataKey="count" nameKey="severity" outerRadius={98} label>
                {chartDataPack.severityMix.map((item, index) => (
                  <Cell key={item.severity} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      default:
        return <EmptyChart text="Select a chart to render visualization." />;
    }
  };

  const renderPreviewTiles = () => {
    if (!selectedCharts.length) {
      return <EmptyChart text="Upload and analyze dataset to activate relevant chart types." />;
    }

    if (viewMode === 'single') {
      const key = selectedCharts[0];
      const chart = chartList.find((item) => item.key === key);
      return (
        <div className="graph-gallery-preview-tile">
          <div className="graph-gallery-preview-head">
            <h3>{chart?.title || 'Chart Preview'}</h3>
            <p>{chart?.description || ''}</p>
          </div>
          <div className="graph-gallery-canvas">{renderChartByKey(key)}</div>
        </div>
      );
    }

    return (
      <div className="graph-gallery-multi-grid">
        {selectedCharts.map((key) => {
          const chart = chartList.find((item) => item.key === key);
          return (
            <div key={key} className="graph-gallery-preview-tile">
              <div className="graph-gallery-preview-head compact">
                <h3>{chart?.title || key}</h3>
                <p>{chart?.category || ''}</p>
              </div>
              <div className="graph-gallery-canvas">{renderChartByKey(key)}</div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="card stats-card graph-gallery-shell">
      <div className="audit-header">
        <h2>Graph Gallery</h2>
        <p>{profile.totalRows ? `${profile.totalRows.toLocaleString()} rows analyzed` : 'No analyzed dataset yet'}</p>
      </div>

      <p className="card-note graph-gallery-note">
        Dataset analysis ke baad relevant saare graphs auto activate ho jate hain. Aap one by one, multiple, ya all mode me charts visualize kar sakte hain.
      </p>

      <div className="graph-gallery-meta">
        <span>Category: {profile.category || 'Unknown'}</span>
        <span>Domain: {profile.domain || 'Unknown'}</span>
        <span>Numeric: {profile.numericColumns.length}</span>
        <span>Date: {profile.dateColumns.length}</span>
        <span>Categorical: {profile.categoricalColumns.length}</span>
        <span>Active Charts: {enabledChartKeys.length}</span>
      </div>

      <div className="graph-gallery-layout">
        <div className="graph-gallery-list" role="list">
          {chartList.map((chart) => {
            const isSelected = selectedChartKeys.includes(chart.key);
            const classNames = [
              'graph-gallery-item',
              chart.enabled ? 'enabled' : 'disabled',
              isSelected ? 'active' : '',
            ]
              .filter(Boolean)
              .join(' ');

            return (
              <button
                key={chart.key}
                type="button"
                className={classNames}
                onClick={() => toggleChartSelection(chart.key)}
                disabled={!chart.enabled}
                role="listitem"
              >
                <div className="graph-gallery-item-header">
                  <strong>{chart.title}</strong>
                  <span>{chart.category}</span>
                </div>
                <p>{chart.description}</p>
                <small>{chart.enabled ? 'Active for current dataset' : 'Not suitable for current dataset'}</small>
              </button>
            );
          })}
        </div>

        <div className="graph-gallery-preview">
          <div className="graph-gallery-controls">
            <div className="graph-gallery-selection">
              <button
                type="button"
                className={viewMode === 'single' ? 'graph-toggle active' : 'graph-toggle'}
                onClick={() => {
                  setViewMode('single');
                  if (selectedChartKeys.length > 1) {
                    setSelectedChartKeys([selectedChartKeys[0]]);
                  }
                }}
              >
                One by One
              </button>
              <button
                type="button"
                className={viewMode === 'multiple' ? 'graph-toggle active' : 'graph-toggle'}
                onClick={() => setViewMode('multiple')}
              >
                Multiple
              </button>
            </div>

            <div className="graph-gallery-selection">
              <button type="button" className="graph-toggle" onClick={selectAllEnabled}>
                Show All Active
              </button>
              <button type="button" className="graph-toggle" onClick={clearSelection}>
                Clear to One
              </button>
            </div>
          </div>

          {renderPreviewTiles()}
        </div>
      </div>
    </div>
  );
}
