import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth';

/**
 * A component that protects routes, redirecting unauthenticated users to the login page.
 * It uses the AuthContext to determine authentication status.
 */
const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  // While authentication status is loading, render nothing or a loading indicator
  if (loading) {
    return null; // Or a small inline spinner if desired
  }

  // If authenticated, render the child routes
  // Otherwise, redirect to the login page
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
};

export default ProtectedRoute;