import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Spinner from '../common/Spinner';

/**
 * Protected Route Component
 * Redirects to login if user is not authenticated
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  // Show loading spinner while checking authentication
  if (loading) {
    return <Spinner fullScreen message="Loading..." />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Render protected content
  return children;
};

export default ProtectedRoute;