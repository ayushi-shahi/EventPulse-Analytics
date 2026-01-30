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

      // Network issues: keep token, just show error
      if (err.code === 'NETWORK_ERROR' || err.code === 'TIMEOUT' ||
          (err.message && err.message.toLowerCase().includes('network'))) {
        setError('Connection error. Please check your connection.');
      }
      // Auth issues: explicit 401 or backend auth messages
      else if (err.status === 401 ||
        (err.message && (
          err.message.toLowerCase().includes('could not validate credentials') ||
          err.message.toLowerCase().includes('invalid token') ||
          err.message.toLowerCase().includes('unauthorized') ||
          err.message.toLowerCase().includes('session expired')
        ))
      ) {
        apiClient.removeToken();
        clearAllUserData(); // Clear all user-specific data
        setUser(null);
        setError(null);
      } else {
        setError(err.message || 'Failed to fetch user.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Clear all user-specific data from localStorage
   */
  const clearAllUserData = () => {
    // Clear API key selection
    localStorage.removeItem('selected_api_key');
    localStorage.removeItem('selected_api_key_metadata');
    localStorage.removeItem('selected_api_key_id'); // Legacy
    
    // Clear API key secrets (these are user-specific)
    localStorage.removeItem('api_key_secret_by_id');
    
    console.log('🗑️ Cleared all user-specific data');
  };

  /**
   * Initialize auth state on mount
   */
  useEffect(() => {
    const token = apiClient.getToken();
    if (token) {
      fetchUser().catch((err) => {
        console.error('Initial user fetch failed:', err);
      });
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  /**
   * Login user
   */
  const login = async (email, password) => {
    setError(null);
    
    // Clear previous user's data before logging in
    clearAllUserData();
    
    try {
      const data = await apiClient.login(email, password);
      // Token is now set, try to fetch user
      try {
        await fetchUser();
      } catch (fetchErr) {
        console.warn('User fetch after login failed, but login was successful:', fetchErr);
      }
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
    
    // Clear previous user's data before registering
    clearAllUserData();
    
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
    clearAllUserData(); // Clear all user-specific data
    setUser(null);
    setError(null);
    console.log('✅ User logged out and data cleared');
  }, []);

  /**
   * Update user data
   */
  const updateUser = useCallback((userData) => {
    setUser(userData);
  }, []);

  // Check if authenticated
  const token = apiClient.getToken();
  const isAuthenticated = !!user || (!!token && !loading);

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    updateUser,
    isAuthenticated,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;