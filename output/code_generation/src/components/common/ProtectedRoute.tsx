import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import useAuth from '@hooks/useAuth';
import LoadingSpinner from './LoadingSpinner';

/**
 * A component that protects routes, redirecting unauthenticated users to the login page.
 */
const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />; // Show a loading spinner while authentication status is being checked
  }

  if (!isAuthenticated) {
    // Redirect to the login page if not authenticated
    return <Navigate to="/login" replace />;
  }

  // If authenticated, render the child routes
  return <Outlet />;
};

export default ProtectedRoute;