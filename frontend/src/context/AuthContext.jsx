import React, { createContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../services/api';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Check if user is authenticated on mount
   */
  const checkAuth = useCallback(async () => {
    const token = apiClient.getToken();
    
    if (!token) {
      setLoading(false);
      return;
    }

    // Check if token is expired
    if (apiClient.isTokenExpired()) {
      const refreshToken = apiClient.getRefreshToken();
      if (refreshToken) {
        try {
          await apiClient.refreshToken(refreshToken);
        } catch (err) {
          console.error('Token refresh failed:', err);
          apiClient.removeToken();
          setUser(null);
          setLoading(false);
          return;
        }
      } else {
        apiClient.removeToken();
        setUser(null);
        setLoading(false);
        return;
      }
    }

    try {
      const userData = await apiClient.getCurrentUser();
      setUser(userData);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch user:', err);
      setUser(null);
      apiClient.removeToken();
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Initialize auth state on mount
   */
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  /**
   * Login user
   */
  const login = async (email, password) => {
    setError(null);
    try {
      const data = await apiClient.login(email, password);
      
      // Fetch user data after successful login
      const userData = await apiClient.getCurrentUser();
      setUser(userData);
      
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  /**
   * Register new user
   */
  const register = async (email, password) => {
    setError(null);
    try {
      const data = await apiClient.register(email, password);
      
      // If registration returns tokens, fetch user data
      if (data.access_token) {
        const userData = await apiClient.getCurrentUser();
        setUser(userData);
      } else {
        // Otherwise, auto-login after registration
        await login(email, password);
      }
      
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  /**
   * Logout user
   */
  const logout = useCallback(() => {
    apiClient.logout();
    setUser(null);
    setError(null);
  }, []);

  /**
   * Update user data
   */
  const updateUser = useCallback((userData) => {
    setUser(userData);
  }, []);

  /**
   * Clear error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    updateUser,
    clearError,
    checkAuth,
    isAuthenticated: !!user, // This is the key addition
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;