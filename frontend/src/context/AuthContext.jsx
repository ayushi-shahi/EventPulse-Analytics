import React, { createContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../services/api';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Fetch current user from API
   */
  const fetchUser = useCallback(async () => {
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
    const token = apiClient.getToken();
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  /**
   * Login user
   */
  const login = async (email, password) => {
    setError(null);
    try {
      const data = await apiClient.login(email, password);
      await fetchUser();
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
      await apiClient.register(email, password);
      // Auto-login after registration
      return await login(email, password);
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

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    updateUser,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;

