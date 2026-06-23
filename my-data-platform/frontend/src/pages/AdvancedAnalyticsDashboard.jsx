import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { DashboardLayout, SidebarNav, PageContainer } from '../../components/layout/DashboardLayout';
import { Card, Button, Badge, Input, Tabs } from '../../components/ui';
import { StatCard } from '../../components/ui/DataComponents';
import {
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  AreaChart,
  HeatmapChart,
  TrendCard,
} from '../../components/charts/ChartComponents';
import {
  BarChart3,
  TrendingUp,
  Users,
  Database,
  Settings,
  Home,
  Filter,
  Download,
  RefreshCw,
} from 'lucide-react';
import { useToast } from '../../context/NotificationContext';

/**
 * Advanced Analytics Dashboard
 * Comprehensive data visualization and insights
 */
export function AdvancedAnalyticsDashboard() {
  const { success } = useToast();
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [timeRange, setTimeRange] = useState('month');
  const [isLoading, setIsLoading] = useState(false);
  const [analyticsData, setAnalyticsData] = useState(null);

  // Sample navigation items
  const navItems = [
    { id: 'home', label: 'Home', icon: <Home className="w-5 h-5" /> },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-5 h-5" /> },
    { id: 'data-quality', label: 'Data Quality', icon: <Database className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  // Mock analytics data
  const mockAnalytics = {
    timeSeriesData: [
      { date: '2024-01-01', revenue: 45000, cost: 12000, profit: 33000 },
      { date: '2024-01-02', revenue: 52000, cost: 14000, profit: 38000 },
      { date: '2024-01-03', revenue: 48000, cost: 13000, profit: 35000 },
      { date: '2024-01-04', revenue: 61000, cost: 15000, profit: 46000 },
      { date: '2024-01-05', revenue: 55000, cost: 14000, profit: 41000 },
      { date: '2024-01-06', revenue: 67000, cost: 16000, profit: 51000 },
      { date: '2024-01-07', revenue: 72000, cost: 18000, profit: 54000 },
    ],
    categoryData: [
      { category: 'Electronics', value: 28000 },
      { category: 'Clothing', value: 22000 },
      { category: 'Home', value: 18000 },
      { category: 'Sports', value: 15000 },
      { category: 'Other', value: 12000 },
    ],
    regionData: [
      { region: 'North', sales: 45000, customers: 1200, growth: 12 },
      { region: 'South', sales: 38000, customers: 950, growth: 8 },
      { region: 'East', sales: 52000, customers: 1400, growth: 15 },
      { region: 'West', sales: 41000, customers: 1100, growth: 10 },
    ],
    correlationData: [
      { advertising: 5000, sales: 45000 },
      { advertising: 7000, sales: 52000 },
      { advertising: 6000, sales: 48000 },
      { advertising: 8000, sales: 61000 },
      { advertising: 7500, sales: 55000 },
      { advertising: 9000, sales: 67000 },
      { advertising: 10000, sales: 72000 },
    ],
    heatmapData: [
      [1, 2, 3, 4, 5],
      [2, 3, 4, 5, 6],
      [3, 4, 5, 6, 7],
      [4, 5, 6, 7, 8],
      [5, 6, 7, 8, 9],
    ],
  };

  useEffect(() => {
    setAnalyticsData(mockAnalytics);
  }, []);

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      success('Analytics data refreshed');
    }, 1000);
  };

  const handleExport = () => {
    success('Analytics exported as PDF');
  };

  const tabs = [
    {
      label: 'Overview',
      content: (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <TrendCard
              label="Total Revenue"
              value="$400,000"
              change={15}
              isPositive={true}
              icon={TrendingUp}
            />
            <TrendCard
              label="Average Order Value"
              value="$125.50"
              change={8}
              isPositive={true}
              icon={TrendingUp}
            />
            <TrendCard
              label="Customer Count"
              value="8,543"
              change={12}
              isPositive={true}
              icon={Users}
            />
            <TrendCard
              label="Conversion Rate"
              value="3.45%"
              change={-2}
              isPositive={false}
              icon={TrendingUp}
            />
          </div>

          {/* Revenue Trend & Category Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {analyticsData && (
              <>
                <LineChart
                  data={analyticsData.timeSeriesData}
                  xAxis="date"
                  yAxis="revenue"
                  title="Revenue Trend (7 Days)"
                  height={300}
                />
                <PieChart
                  data={analyticsData.categoryData}
                  nameAxis="category"
                  valueAxis="value"
                  title="Sales by Category"
                  height={300}
                />
              </>
            )}
          </div>

          {/* Profit Margin & Regional Performance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {analyticsData && (
              <>
                <AreaChart
                  data={analyticsData.timeSeriesData}
                  xAxis="date"
                  yAxisList={['revenue', 'cost']}
                  title="Revenue vs Cost"
                  height={300}
                />
                <BarChart
                  data={analyticsData.regionData}
                  xAxis="region"
                  yAxis="sales"
                  title="Regional Sales Performance"
                  height={300}
                />
              </>
            )}
          </div>
        </motion.div>
      ),
    },
    {
      label: 'Advanced Analysis',
      content: (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          {/* Correlation Analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {analyticsData && (
              <>
                <ScatterChart
                  data={analyticsData.correlationData}
                  xAxis="advertising"
                  yAxis="sales"
                  title="Advertising Spend vs Sales (Correlation: 0.92)"
                  height={300}
                />
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Statistical Summary</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center pb-3 border-b">
                      <span className="text-neutral-600 dark:text-neutral-400">Mean Revenue</span>
                      <span className="font-semibold">$55,714</span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b">
                      <span className="text-neutral-600 dark:text-neutral-400">Std Deviation</span>
                      <span className="font-semibold">$8,345</span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b">
                      <span className="text-neutral-600 dark:text-neutral-400">Min Value</span>
                      <span className="font-semibold">$45,000</span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b">
                      <span className="text-neutral-600 dark:text-neutral-400">Max Value</span>
                      <span className="font-semibold">$72,000</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-neutral-600 dark:text-neutral-400">Trend</span>
                      <Badge variant="secondary">Increasing</Badge>
                    </div>
                  </div>
                </Card>
              </>
            )}
          </div>

          {/* Heatmap for correlation matrix */}
          {analyticsData && (
            <HeatmapChart
              data={analyticsData.heatmapData}
              title="Feature Correlation Matrix"
              height={300}
            />
          )}
        </motion.div>
      ),
    },
    {
      label: 'Insights',
      content: (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-4"
        >
          <Card className="p-6 border-l-4 border-green-500">
            <h3 className="font-semibold text-green-900 dark:text-green-100">✓ Positive Trend</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
              Revenue has increased by 60% over the last week. Strong market performance driven by
              successful advertising campaigns.
            </p>
          </Card>

          <Card className="p-6 border-l-4 border-yellow-500">
            <h3 className="font-semibold text-yellow-900 dark:text-yellow-100">⚠ Attention Needed</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
              Conversion rate declined by 2%. Consider reviewing marketing strategy to improve
              customer engagement.
            </p>
          </Card>

          <Card className="p-6 border-l-4 border-blue-500">
            <h3 className="font-semibold text-blue-900 dark:text-blue-100">💡 Recommendation</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
              Strong correlation (0.92) between advertising spend and sales. Recommend increasing
              ad budget by 15% to capitalize on this trend.
            </p>
          </Card>

          <Card className="p-6 border-l-4 border-purple-500">
            <h3 className="font-semibold text-purple-900 dark:text-purple-100">🎯 Opportunity</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
              East region showing highest growth (15%). Consider expanding operations in this
              region to maximize revenue potential.
            </p>
          </Card>
        </motion.div>
      ),
    },
  ];

  return (
    <DashboardLayout
      logo={
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold hidden sm:inline">Analytics</span>
        </div>
      }
      sidebar={<SidebarNav items={navItems} />}
      title="Advanced Analytics"
    >
      <PageContainer
        title="Analytics Dashboard"
        description="Comprehensive data analysis and insights"
        actions={
          <div className="flex gap-3">
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={handleRefresh}
              loading={isLoading}
            >
              Refresh
            </Button>
            <Button variant="primary" icon={Download} onClick={handleExport}>
              Export
            </Button>
          </div>
        }
      >
        {/* Filters */}
        <Card className="p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input
              label="Dataset"
              placeholder="Select dataset..."
              icon={Database}
            />
            <Input
              label="Time Range"
              type="select"
              placeholder={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
            />
            <div className="flex items-end gap-2">
              <Button variant="secondary">Apply Filters</Button>
            </div>
          </div>
        </Card>

        {/* Tabs with different analyses */}
        <Card className="p-6">
          <Tabs tabs={tabs} />
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}

export default AdvancedAnalyticsDashboard;
