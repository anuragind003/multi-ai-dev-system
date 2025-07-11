import React, { lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';
import { useAuth } from '@hooks/useAuth';

// Lazy load page components for performance
const LoginPage = lazy(() => import('@pages/Auth/LoginPage'));
const DashboardPage = lazy(() => import('@pages/DashboardPage'));

const AppRouter: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    // Render a global loading indicator while authentication status is being determined
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-primary"></div>
        <p className="ml-4 text-lg text-text-light">Authenticating...</p>
      </div>
    );
  }

  return (
    <Routes>
      {/* Public route for login */}
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        {/* Add more protected routes here */}
        {/* <Route path="/profile" element={<ProfilePage />} /> */}
        {/* <Route path="/settings" element={<SettingsPage />} /> */}
      </Route>

      {/* Redirect root to dashboard if authenticated, otherwise to login */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />} />

      {/* Catch-all for 404 Not Found */}
      <Route path="*" element={
        <div className="flex flex-col items-center justify-center h-full text-center py-20">
          <h1 className="text-6xl font-bold text-primary mb-4">404</h1>
          <p className="text-2xl text-text-light mb-8">Page Not Found</p>
          <p className="text-lg text-text">The page you are looking for does not exist.</p>
          <a href="/" className="mt-6 px-6 py-3 bg-primary text-white rounded-md hover:bg-primary-dark transition-colors">
            Go to Home
          </a>
        </div>
      } />
    </Routes>
  );
};

export default AppRouter;