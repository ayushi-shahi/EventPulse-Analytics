import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import { API_CONFIG } from '../config';
import { useAPIKey } from '../hooks/useAPIKey';

export const WebSocketContext = createContext(null);

const MAX_EVENTS_STORED = 10000;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 30000;
const ALERT_AUTO_DISMISS_MS = 10000;

export const WebSocketProvider = ({ children }) => {
  const { selectedAPIKey } = useAPIKey();
  const [isConnected, setIsConnected]             = useState(false);
  const [events, setEvents]                       = useState([]);
  const [totalEventsCount, setTotalEventsCount]   = useState(0);
  const [metrics, setMetrics]                     = useState([]);
  const [currentAlert, setCurrentAlert]           = useState(null);
  const [connectionError, setConnectionError]     = useState(null);
  const [rateLimitExceeded, setRateLimitExceeded] = useState(false);

  const wsRef                  = useRef(null);
  const reconnectTimeoutRef    = useRef(null);
  const reconnectAttemptsRef   = useRef(0);
  const alertTimeoutRef        = useRef(null);

  // ─── Generation counter ───────────────────────────────────────────────────
  // Every connect() increments this. Each socket captures its own generation
  // at open-time. Any callback (onmessage / onclose / reconnect timer) that
  // finds its generation stale is silently dropped.
  // This is the core fix: ws.close() is async, so messages keep arriving for
  // a short window after disconnect(). The generation gate drops them all.
  const generationRef = useRef(0);

  // ─── Internal: hard-close the current socket ─────────────────────────────
  const _hardClose = useCallback(() => {
    // Cancel any pending reconnect timer first
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      const ws = wsRef.current;
      // Strip all handlers BEFORE calling close() so the onclose callback
      // cannot trigger a reconnect loop for the old key
      ws.onopen    = null;
      ws.onmessage = null;
      ws.onerror   = null;
      ws.onclose   = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      wsRef.current = null;
    }

    reconnectAttemptsRef.current = 0;
  }, []);

  // ─── connect ─────────────────────────────────────────────────────────────
  const connect = useCallback((clientId, apiKey) => {
    if (!clientId || !apiKey) {
      console.warn('Cannot connect WebSocket: missing clientId or apiKey');
      return;
    }

    // 1. Kill the previous socket and cancel any reconnect timer
    _hardClose();

    // 2. Bump generation — all callbacks from the old socket are now stale
    generationRef.current += 1;
    const myGeneration = generationRef.current;

    // 3. Reset all state so the UI starts clean for the new key
    setEvents([]);
    setTotalEventsCount(0);
    setMetrics([]);
    setCurrentAlert(null);
    setConnectionError(null);
    setRateLimitExceeded(false);
    setIsConnected(false);

    // 4. Open the new socket
    let ws;
    try {
      const wsUrl = `${API_CONFIG.WS_URL}/ws/live/${clientId}?token=${apiKey}`;
      console.log(`🔌 Connecting WebSocket (gen ${myGeneration}):`, wsUrl);
      ws = new WebSocket(wsUrl);
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setConnectionError(err.message);
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      if (generationRef.current !== myGeneration) { ws.close(); return; }
      console.log(`✅ WebSocket connected (gen ${myGeneration})`);
      setIsConnected(true);
      setConnectionError(null);
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      // Drop messages from any previous socket
      if (generationRef.current !== myGeneration) return;

      try {
        const data = JSON.parse(event.data);
        handleMessage(data, myGeneration, clientId, apiKey);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      if (generationRef.current !== myGeneration) return;
      console.error('WebSocket error:', error);
      setConnectionError('WebSocket connection error');
    };

    ws.onclose = (event) => {
      if (generationRef.current !== myGeneration) return;
      console.log(`🔌 WebSocket closed (gen ${myGeneration}):`, event.code, event.reason);
      setIsConnected(false);
      wsRef.current = null;

      // Don't reconnect if rate limited or too many attempts
      if (rateLimitExceeded) return;
      if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        setConnectionError('Failed to connect after multiple attempts');
        return;
      }

      reconnectAttemptsRef.current += 1;
      console.log(`🔄 Reconnecting... (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);

      reconnectTimeoutRef.current = setTimeout(() => {
        // Final stale check before reconnecting — the user may have switched
        // keys during the delay window
        if (generationRef.current !== myGeneration) return;
        connect(clientId, apiKey);
      }, RECONNECT_DELAY);
    };
  }, [_hardClose, rateLimitExceeded]); // rateLimitExceeded read in onclose

  // ─── disconnect (public) ─────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    // Bump generation first so all in-flight callbacks are invalidated
    generationRef.current += 1;
    _hardClose();
    setIsConnected(false);
  }, [_hardClose]);

  // ─── handleMessage ───────────────────────────────────────────────────────
  // myGeneration + credentials are passed in so this stays a stable callback
  // without needing rateLimitExceeded in its closure.
  const handleMessage = useCallback((data, myGeneration, clientId, apiKey) => {
    const { type } = data;

    switch (type) {
      case 'connected':
        console.log('WebSocket handshake complete:', data);
        break;

      case 'event':
        setRateLimitExceeded((isLimited) => {
          if (!isLimited) {
            setTotalEventsCount((c) => c + 1);
            setEvents((prev) => [data, ...prev].slice(0, MAX_EVENTS_STORED));
          }
          return isLimited;
        });
        break;

      case 'metric':
        setMetrics((prev) => [data, ...prev].slice(0, 100));
        break;

      case 'alert':
        if (alertTimeoutRef.current) clearTimeout(alertTimeoutRef.current);
        setCurrentAlert({
          ...data,
          id: Date.now(),
          timestamp: new Date().toISOString(),
        });
        alertTimeoutRef.current = setTimeout(() => {
          setCurrentAlert(null);
        }, ALERT_AUTO_DISMISS_MS);
        break;

      case 'rate_limit_exceeded':
      case 'error': {
        const isRateLimit =
          type === 'rate_limit_exceeded' ||
          data.message?.toLowerCase().includes('rate limit') ||
          data.message?.toLowerCase().includes('too many requests');

        if (isRateLimit) {
          console.log('🚫 Rate limit exceeded — stopping event stream');
          setRateLimitExceeded(true);
          // Bump generation so no further messages are processed
          generationRef.current += 1;
          _hardClose();
          setIsConnected(false);
        }
        break;
      }

      case 'pong':
        break;

      default:
        console.log('Unknown WebSocket message type:', type, data);
    }
  }, [_hardClose]);

  // ─── helpers ─────────────────────────────────────────────────────────────
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  const sendPing = useCallback(() => {
    sendMessage({ type: 'ping', timestamp: new Date().toISOString() });
  }, [sendMessage]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setTotalEventsCount(0);
  }, []);

  const clearMetrics = useCallback(() => {
    setMetrics([]);
  }, []);

  const dismissAlert = useCallback(() => {
    if (alertTimeoutRef.current) {
      clearTimeout(alertTimeoutRef.current);
      alertTimeoutRef.current = null;
    }
    setCurrentAlert(null);
  }, []);

  const resetRateLimit = useCallback(() => {
    setRateLimitExceeded(false);
  }, []);

  // ─── Cleanup on unmount ───────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      generationRef.current += 1;
      _hardClose();
      if (alertTimeoutRef.current) clearTimeout(alertTimeoutRef.current);
    };
  }, [_hardClose]);

  // ─── Ping loop ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isConnected) return;
    const interval = setInterval(sendPing, PING_INTERVAL);
    return () => clearInterval(interval);
  }, [isConnected, sendPing]);

  // ─── Auto-connect while a data source is selected ────────────────────────
  // The socket used to be opened only by the Live Feed page, so the header's
  // connection badge read "Offline" everywhere else even though the app was
  // perfectly healthy. Owning the connection here keeps that indicator honest
  // and means alerts arrive on whichever page the user is looking at.
  //
  // The token may be the key secret or the user's session JWT: keys are stored
  // hashed, so a browser that never created the key has only the session.
  const selectedKeyId = selectedAPIKey?.id ?? null;
  useEffect(() => {
    if (!selectedKeyId) {
      disconnect();
      return;
    }
    const token =
      selectedAPIKey?.api_key || selectedAPIKey?.key || localStorage.getItem('token');
    if (token) connect(selectedKeyId, token);
    // connect/disconnect are stable useCallback refs; re-running on every
    // render would tear the socket down continuously.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKeyId]);

  const value = {
    isConnected,
    connectionError,
    events,
    totalEventsCount,
    metrics,
    currentAlert,
    rateLimitExceeded,
    setRateLimitExceeded,
    connect,
    disconnect,
    sendMessage,
    clearEvents,
    clearMetrics,
    dismissAlert,
    resetRateLimit,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketContext;