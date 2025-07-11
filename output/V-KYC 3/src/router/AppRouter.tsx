import React, { lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@context/AuthContext';
import Spinner from '@ui/Spinner';

// Lazy load pages for performance
const LoginPage = lazy(() => import('@pages/LoginPage'));
const DashboardPage = lazy(() => import('@pages/DashboardPage'));

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    // Show a global spinner while checking auth status
    return (
      <div className="flex justify-center items-center min-h-[calc(100vh-120px)]">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page if not authenticated
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const AppRouter: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      {/* Redirect root to dashboard if authenticated, otherwise to login */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      {/* Catch-all for undefined routes */}
      <Route path="*" element={<div className="text-center text-xl font-semibold py-20">404 - Page Not Found</div>} />
    </Routes>
  );
};

export default AppRouter;