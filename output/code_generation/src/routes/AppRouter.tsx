import React from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuthContext } from '@context/AppContext';

// Pages
import HomePage from '@pages/HomePage';
import DashboardPage from '@pages/DashboardPage';
import LoginPage from '@pages/LoginPage';

// Placeholder Pages (for demonstration)
const ProfilePage: React.FC = () => (
  <div className="p-4">
    <h1 className="text-3xl font-bold text-gray-900 mb-4">Profile Page</h1>
    <p className="text-gray-700">This is your user profile. You can view and edit your personal information here.</p>
  </div>
);

const SettingsPage: React.FC = () => (
  <div className="p-4">
    <h1 className="text-3xl font-bold text-gray-900 mb-4">Settings Page</h1>
    <p className="text-gray-700">Manage application settings and preferences.</p>
  </div>
);

const NotFoundPage: React.FC = () => (
  <div className="flex flex-col items-center justify-center min-h-[calc(100vh-16rem)] text-center p-4">
    <h1 className="text-6xl font-bold text-gray-800 mb-4">404</h1>
    <p className="text-2xl text-gray-600 mb-8">Page Not Found</p>
    <p className="text-lg text-gray-500">The page you are looking for does not exist.</p>
    <button
      onClick={() => window.history.back()}
      className="mt-8 px-6 py-3 bg-primary text-white rounded-md hover:bg-indigo-700 transition-colors"
    >
      Go Back
    </button>
  </div>
);

/**
 * ProtectedRoute component ensures that only authenticated users can access its children.
 * If not authenticated, it redirects to the login page.
 */
const ProtectedRoute: React.FC = () => {
  const { isAuthenticated } = useAuthContext();

  if (!isAuthenticated) {
    // Redirect to the login page if not authenticated
    return <Navigate to="/login" replace />;
  }

  // Render the child routes if authenticated
  return <Outlet />;
};

/**
 * AppRouter defines all the application routes, including public and protected ones.
 */
const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      {/* Catch-all route for 404 Not Found */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default AppRouter;