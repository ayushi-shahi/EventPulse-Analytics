import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import apiClient from '../../services/api';
import Spinner from '../common/Spinner';

/**
 * Protected Route Component
 * Redirects to login if user is not authenticated
 */
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const token = apiClient.getToken();

  if (loading) {
    return <Spinner fullScreen message="Loading..." />;
  }

  // If we have a token but no user, it might be a network error
  // Allow access temporarily - the user fetch will retry on next render
  // Only redirect if we truly have no token (not authenticated)
  if (!user && !token) {
    return <Navigate to="/login" replace />;
  }

  // If we have a token but user fetch failed (network error), allow access
  // The AuthContext will retry fetching user when components mount
  return children;
};

export default ProtectedRoute;
