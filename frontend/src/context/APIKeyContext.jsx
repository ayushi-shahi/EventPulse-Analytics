import React, { createContext, useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';

export const APIKeyContext = createContext(null);

// ---------------------------------------------------------------------------
// Storage helpers (kept outside the component so they never re-create)
// ---------------------------------------------------------------------------
const KEYS = {
  API_KEY:  'selected_api_key',
  META:     'selected_api_key_metadata',
  LEGACY_ID:'selected_api_key_id',
};

function readFromStorage() {
  try {
    const apiKey = localStorage.getItem(KEYS.API_KEY);
    if (!apiKey) return null;

    const metaRaw = localStorage.getItem(KEYS.META);
    const meta    = metaRaw ? JSON.parse(metaRaw) : {};

    return {
      id:          meta.id          ?? localStorage.getItem(KEYS.LEGACY_ID) ?? apiKey,
      api_key:     apiKey,
      client_name: meta.client_name ?? 'Unknown',
    };
  } catch {
    return null;
  }
}

function writeToStorage(keyData) {
  try {
    localStorage.setItem(KEYS.API_KEY, keyData.api_key);
    localStorage.setItem(KEYS.META, JSON.stringify({
      id:          keyData.id,
      client_name: keyData.client_name,
    }));
    localStorage.removeItem(KEYS.LEGACY_ID);
  } catch (err) {
    console.error('❌ Failed to persist API key:', err);
  }
}

function clearStorage() {
  try {
    Object.values(KEYS).forEach(k => localStorage.removeItem(k));
  } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export const APIKeyProvider = ({ children }) => {
  // useAuth may expose `loading` (or `isLoading`) while it rehydrates the
  // session after a refresh.  We support both naming conventions and fall back
  // to a ref-based approach when neither is available.
  const auth = useAuth();
  const user        = auth.user;
  // Accept loading / isLoading / initializing — whichever the hook exposes
  const authLoading = auth.loading ?? auth.isLoading ?? auth.initializing ?? false;

  // ✅ FIX 1: Lazy initializer — reads localStorage synchronously on first
  //    render, so the key is available immediately (survives page refresh).
  const [selectedAPIKey, setSelectedAPIKey] = useState(() => readFromStorage());
  const [apiKeys, setApiKeys]               = useState([]);

  // Keep a ref in sync so callbacks never capture stale state
  const selectedAPIKeyRef = useRef(selectedAPIKey);
  useEffect(() => { selectedAPIKeyRef.current = selectedAPIKey; }, [selectedAPIKey]);

  // Track the previous confirmed user so we can tell the difference between
  // "auth is still loading (user transiently null)" and "user actually logged out".
  const prevUserRef = useRef(user);

  // ✅ FIX: Only clear when auth has finished loading AND user transitioned
  //    from a real logged-in value to null.  This prevents the false-logout
  //    that fires on every refresh while the session is being rehydrated.
  useEffect(() => {
    // Still resolving — don't act yet
    if (authLoading) return;

    const prevUser = prevUserRef.current;
    prevUserRef.current = user;

    // user went from a real value → null after auth finished loading = genuine logout
    if (prevUser !== null && user === null) {
      console.log('🔄 User logged out - clearing API key');
      clearStorage();
      setSelectedAPIKey(null);
      setApiKeys([]);
    }
  }, [user, authLoading]);

  // ---------------------------------------------------------------------------
  const selectAPIKey = useCallback((keyData) => {
    if (!keyData) {
      clearStorage();
      setSelectedAPIKey(null);
      return;
    }

    const apiKey = keyData.api_key ?? keyData.key;
    if (!apiKey) {
      console.error('❌ Invalid API key data — missing api_key:', keyData);
      return;
    }

    const normalized = {
      id:          keyData.id,
      api_key:     apiKey,
      client_name: keyData.client_name ?? 'Unknown',
    };

    writeToStorage(normalized);
    setSelectedAPIKey(normalized);
    console.log('✅ API key selected:', { id: normalized.id, client_name: normalized.client_name });
  }, []);

  const clearAPIKey = useCallback(() => {
    clearStorage();
    setSelectedAPIKey(null);
    console.log('🗑️ API key cleared');
  }, []);

  // ✅ FIX: Use ref to avoid stale closure without recreating the callback on
  //    every key change (which would cause downstream re-renders).
  const updateAPIKeys = useCallback((keys) => {
    setApiKeys(keys);
    const current = selectedAPIKeyRef.current;
    if (current && keys.length > 0 && !keys.some(k => k.id === current.id)) {
      console.warn('⚠️ Selected API key no longer exists — clearing');
      clearStorage();
      setSelectedAPIKey(null);
    }
    console.log(`📋 Updated API keys list: ${keys.length} keys`);
  }, []); // no deps needed — uses ref

  const getAPIKeyString = useCallback(
    () => selectedAPIKey?.api_key ?? null,
    [selectedAPIKey]
  );

  const value = {
    selectedAPIKey,
    apiKeys,
    selectAPIKey,
    clearAPIKey,
    updateAPIKeys,
    hasSelectedKey: !!selectedAPIKey?.api_key,
    getAPIKeyString,
  };

  return (
    <APIKeyContext.Provider value={value}>
      {children}
    </APIKeyContext.Provider>
  );
};

export default APIKeyContext;