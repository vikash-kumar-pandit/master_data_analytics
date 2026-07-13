import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import DashboardLayout from './DashboardLayout';
import ReportBuilder from './pages/ReportBuilder';
import DataQuality from './pages/DataQuality';
import DataProfiling from './pages/DataProfiling';
import DataPreparationStudio from './pages/DataPreparationStudio';
import PredictiveAnalytics from './pages/PredictiveAnalytics';
import RealTimeInsights from './pages/RealTimeInsights';
import ScheduleExports from './pages/ScheduleExports';
import AuditLogPage from './pages/AuditLogPage';
import WorkflowPage from './pages/WorkflowPage';
import SearchPage from './pages/SearchPage';
import VisualizationIntelligence from './pages/VisualizationIntelligence';
import Login from './Login';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/NotificationContext';

function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <div className="access-denied">Access denied: insufficient permissions.</div>;
  }

  return children;
}

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Router>
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
        </Router>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;