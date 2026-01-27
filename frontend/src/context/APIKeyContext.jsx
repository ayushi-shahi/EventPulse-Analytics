import React, { createContext, useState, useCallback, useEffect } from 'react';

export const APIKeyContext = createContext(null);

export const APIKeyProvider = ({ children }) => {
  const [selectedAPIKey, setSelectedAPIKey] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);

  /**
   * Load selected API key from localStorage on mount
   */
  useEffect(() => {
    const savedKey = localStorage.getItem('selected_api_key');
    const savedKeyId = localStorage.getItem('selected_api_key_id');
    
    if (savedKey && savedKeyId) {
      setSelectedAPIKey({
        id: savedKeyId,
        key: savedKey,
      });
    }
  }, []);

  /**
   * Select an API key
   */
  const selectAPIKey = useCallback((keyData) => {
    if (!keyData) {
      localStorage.removeItem('selected_api_key');
      localStorage.removeItem('selected_api_key_id');
      setSelectedAPIKey(null);
      return;
    }

    const apiKeyData = {
      id: keyData.id,
      key: keyData.api_key || keyData.key,
      client_name: keyData.client_name,
    };

    localStorage.setItem('selected_api_key', apiKeyData.key);
    localStorage.setItem('selected_api_key_id', apiKeyData.id);
    setSelectedAPIKey(apiKeyData);
  }, []);

  /**
   * Update API keys list
   */
  const updateAPIKeys = useCallback((keys) => {
    setApiKeys(keys);
  }, []);

  /**
   * Check if an API key is selected
   */
  const hasSelectedKey = selectedAPIKey !== null;

  const value = {
    selectedAPIKey,
    apiKeys,
    selectAPIKey,
    updateAPIKeys,
    hasSelectedKey,
  };

  return (
    <APIKeyContext.Provider value={value}>
      {children}
    </APIKeyContext.Provider>
  );
};

export default APIKeyContext;