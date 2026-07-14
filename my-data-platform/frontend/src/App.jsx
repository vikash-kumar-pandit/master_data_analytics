import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import DashboardLayout from './DashboardLayout';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/NotificationContext';
import { ThemeProvider } from './context/ThemeContext';
import { CommandPalette, Skeleton } from './components/ui';

// Lazy load pages for dynamic code-splitting and optimization (Phase 5 Performance)
const ReportBuilder = lazy(() => import('./pages/ReportBuilder'));
const DataQuality = lazy(() => import('./pages/DataQuality'));
const DataProfiling = lazy(() => import('./pages/DataProfiling'));
const DataPreparationStudio = lazy(() => import('./pages/DataPreparationStudio'));
const PredictiveAnalytics = lazy(() => import('./pages/PredictiveAnalytics'));
const RealTimeInsights = lazy(() => import('./pages/RealTimeInsights'));
const ScheduleExports = lazy(() => import('./pages/ScheduleExports'));
const AuditLogPage = lazy(() => import('./pages/AuditLogPage'));
const WorkflowPage = lazy(() => import('./pages/WorkflowPage'));
const SearchPage = lazy(() => import('./pages/SearchPage'));
const VisualizationIntelligence = lazy(() => import('./pages/VisualizationIntelligence'));
const Login = lazy(() => import('./Login'));

function ProtectedRoute({ children, allowedRoles }) {
  // Authentication and role checks bypassed for easy testing and debugging
  return children;
}

function App() {
  return (
    <ToastProvider>
      <ThemeProvider>
        <AuthProvider>
          <Router>
            <CommandPalette />
            <Suspense fallback={<div className="p-8"><Skeleton variant="card" /></div>}>
              <Routes>
                <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <ReportBuilder />
                </ProtectedRoute>
              }
            />
            <Route
              path="/quality"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <DataQuality />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profiling"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <DataProfiling />
                </ProtectedRoute>
              }
            />
            <Route
              path="/preparation"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <DataPreparationStudio />
                </ProtectedRoute>
              }
            />
            <Route
              path="/predictive"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <PredictiveAnalytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/insights"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <RealTimeInsights />
                </ProtectedRoute>
              }
            />
            <Route
              path="/schedule"
              element={
                <ProtectedRoute allowedRoles={['analyst', 'admin']}>
                  <ScheduleExports />
                </ProtectedRoute>
              }
            />
            <Route
              path="/audit"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AuditLogPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/workflows"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <WorkflowPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/search"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <SearchPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/graphs"
              element={
                <ProtectedRoute allowedRoles={['viewer', 'analyst', 'admin']}>
                  <DashboardLayout>
                    <VisualizationIntelligence />
                  </DashboardLayout>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </Router>
      </AuthProvider>
      </ThemeProvider>
    </ToastProvider>
  );
}

export default App;