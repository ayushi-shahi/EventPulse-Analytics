import React, { createContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../services/api';

export const AuthContext = createContext(null);

// ⏱️ Wrap any promise with a timeout
const withTimeout = (promise, ms = 8000) => {
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject({ code: 'TIMEOUT', message: 'Request timed out' }), ms)
  );
  return Promise.race([promise, timeout]);
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const clearAllUserData = () => {
    localStorage.removeItem('selected_api_key');
    localStorage.removeItem('selected_api_key_metadata');
    localStorage.removeItem('selected_api_key_id');
    localStorage.removeItem('api_key_secret_by_id');
  };

  const fetchUser = useCallback(async () => {
    try {
      // ✅ 8s timeout — fail fast instead of hanging for 2+ minutes
      const userData = await withTimeout(apiClient.getCurrentUser(), 8000);
      setUser(userData);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch user:', err);

      const isTimeout = err.code === 'TIMEOUT';
      const isNetworkError =
        err.code === 'NETWORK_ERROR' ||
        (err.message && err.message.toLowerCase().includes('network'));
      const isAuthError =
        err.status === 401 ||
        (err.message &&
          (err.message.toLowerCase().includes('could not validate credentials') ||
            err.message.toLowerCase().includes('invalid token') ||
            err.message.toLowerCase().includes('unauthorized') ||
            err.message.toLowerCase().includes('session expired')));

      if (isTimeout || isNetworkError) {
        // ✅ On timeout/network error: clear token and force login
        // Don't silently stay "authenticated" with a dead token
        apiClient.removeToken();
        clearAllUserData();
        setUser(null);
        setError('Connection timed out. Please log in again.');
      } else if (isAuthError) {
        apiClient.removeToken();
        clearAllUserData();
        setUser(null);
        setError(null);
      } else {
        // Unknown error — clear token to be safe
        apiClient.removeToken();
        clearAllUserData();
        setUser(null);
        setError(err.message || 'Failed to fetch user.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = apiClient.getToken();
    if (token) {
      fetchUser().catch((err) => {
        console.error('Initial user fetch failed:', err);
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  const login = async (email, password) => {
    setError(null);
    clearAllUserData();
    try {
      const data = await apiClient.login(email, password);
      await fetchUser();
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const register = async (email, password) => {
    setError(null);
    clearAllUserData();
    try {
      await apiClient.register(email, password);
      return await login(email, password);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const logout = useCallback(() => {
    apiClient.logout();
    clearAllUserData();
    setUser(null);
    setError(null);
  }, []);

  const updateUser = useCallback((userData) => {
    setUser(userData);
  }, []);

  // ✅ Only authenticated if we actually have a user object from the server
  // Removed the (!!token && !loading) fallback — that was the root bug
  const isAuthenticated = !!user;

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