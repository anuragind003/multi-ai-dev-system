import React from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuth as useAuthContext } from '../context/AuthContext'; // Rename to avoid conflict
import AppLayout from '../components/layout/AppLayout';
import HomePage from '../pages/HomePage';
import DashboardPage from '../pages/DashboardPage';
import AuthPage from '../pages/AuthPage';

// Example protected pages
const ProfilePage: React.FC = () => (
  <div className="p-4">
    <h1 className="text-3xl font-bold mb-4">Profile Page</h1>
    <p>This is a protected profile page. Only authenticated users can see this.</p>
  </div>
);

const SettingsPage: React.FC = () => (
  <div className="p-4">
    <h1 className="text-3xl font-bold mb-4">Settings Page</h1>
    <p>This is a protected settings page. Only authenticated users can see this.</p>
  </div>
);

/**
 * Custom hook to access authentication status.
 * Provides a cleaner interface than directly importing useContext everywhere.
 */
export const useAuth = () => {
  return useAuthContext();
};

/**
 * ProtectedRoute component.
 * Renders child routes only if the user is authenticated.
 * Otherwise, redirects to the login page.
 */
const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    // Optionally render a full-page loading spinner here
    return <div className="flex justify-center items-center min-h-screen">Loading authentication...</div>;
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/auth" replace />;
};

/**
 * AppRouter component.
 * Defines all application routes, including public and protected routes.
 */
export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<HomePage />} />
      <Route path="/auth" element={<AuthPage />} />

      {/* Protected Routes - require authentication */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}> {/* Layout for authenticated users */}
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      {/* Catch-all for undefined routes */}
      <Route path="*" element={
        <div className="flex flex-col items-center justify-center min-h-screen text-center p-4">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">404 - Page Not Found</h1>
          <p className="text-lg text-gray-600 mb-8">The page you are looking for does not exist.</p>
          <Link to="/" className="text-blue-600 hover:underline text-lg">Go to Home</Link>
        </div>
      } />
    </Routes>
  );
};