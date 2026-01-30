import React, { createContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';

export const APIKeyContext = createContext(null);

export const APIKeyProvider = ({ children }) => {
  const { user } = useAuth();
  const [selectedAPIKey, setSelectedAPIKey] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);

  /**
   * Load selected API key from localStorage on mount
   */
  useEffect(() => {
    loadSelectedAPIKey();
  }, []);

  /**
   * Clear API key when user changes
   */
  useEffect(() => {
    if (user === null) {
      // User logged out - clear everything
      console.log('🔄 User logged out - clearing API key');
      setSelectedAPIKey(null);
      setApiKeys([]);
    }
  }, [user]);

  /**
   * Load API key from localStorage
   */
  const loadSelectedAPIKey = () => {
    try {
      const storedKey = localStorage.getItem('selected_api_key');
      const metadataStr = localStorage.getItem('selected_api_key_metadata');
      
      if (storedKey && metadataStr) {
        const metadata = JSON.parse(metadataStr);
        setSelectedAPIKey({
          id: metadata.id,
          api_key: storedKey,
          key: storedKey,
          client_name: metadata.client_name,
        });
        console.log('✅ Loaded API key from localStorage:', {
          id: metadata.id,
          client_name: metadata.client_name,
        });
      } else if (storedKey) {
        // Backwards compatibility
        const keyId = localStorage.getItem('selected_api_key_id');
        setSelectedAPIKey({
          id: keyId || storedKey,
          api_key: storedKey,
          key: storedKey,
          client_name: 'Unknown',
        });
        console.log('⚠️ Loaded API key in legacy format');
      }
    } catch (error) {
      console.error('Failed to load API key from localStorage:', error);
      clearAPIKey();
    }
  };

  /**
   * Select an API key
   */
  const selectAPIKey = useCallback((keyData) => {
    if (!keyData) {
      clearAPIKey();
      return;
    }

    const apiKey = keyData.api_key || keyData.key;
    if (!apiKey) {
      console.error('❌ Invalid API key data - missing api_key:', keyData);
      return;
    }

    try {
      // Store the API key string
      localStorage.setItem('selected_api_key', apiKey);
      
      // Store metadata separately
      const metadata = {
        id: keyData.id,
        client_name: keyData.client_name || 'Unknown',
      };
      localStorage.setItem('selected_api_key_metadata', JSON.stringify(metadata));
      
      // Clean up legacy storage
      localStorage.removeItem('selected_api_key_id');
      
      // Update state
      const apiKeyData = {
        id: keyData.id,
        api_key: apiKey,
        key: apiKey,
        client_name: keyData.client_name || 'Unknown',
      };
      
      setSelectedAPIKey(apiKeyData);
      
      console.log('✅ API key selected:', {
        id: apiKeyData.id,
        client_name: apiKeyData.client_name,
      });
    } catch (error) {
      console.error('❌ Failed to save API key to localStorage:', error);
    }
  }, []);

  /**
   * Clear selected API key
   */
  const clearAPIKey = useCallback(() => {
    localStorage.removeItem('selected_api_key');
    localStorage.removeItem('selected_api_key_metadata');
    localStorage.removeItem('selected_api_key_id');
    setSelectedAPIKey(null);
    console.log('🗑️ API key cleared');
  }, []);

  /**
   * Update API keys list
   */
  const updateAPIKeys = useCallback((keys) => {
    setApiKeys(keys);
    
    // If we have a selected API key, verify it still exists in the list
    if (selectedAPIKey && keys.length > 0) {
      const keyStillExists = keys.some(k => k.id === selectedAPIKey.id);
      if (!keyStillExists) {
        console.log('⚠️ Selected API key no longer exists - clearing');
        clearAPIKey();
      }
    }
    
    console.log(`📋 Updated API keys list: ${keys.length} keys`);
  }, [selectedAPIKey, clearAPIKey]);

  /**
   * Check if an API key is selected
   */
  const hasSelectedKey = selectedAPIKey !== null && !!selectedAPIKey.api_key;

  /**
   * Get the current API key string
   */
  const getAPIKeyString = useCallback(() => {
    return selectedAPIKey?.api_key || selectedAPIKey?.key || null;
  }, [selectedAPIKey]);

  const value = {
    selectedAPIKey,
    apiKeys,
    selectAPIKey,
    clearAPIKey,
    updateAPIKeys,
    hasSelectedKey,
    getAPIKeyString,
  };

  return (
    <APIKeyContext.Provider value={value}>
      {children}
    </APIKeyContext.Provider>
  );
};

export default APIKeyContext;