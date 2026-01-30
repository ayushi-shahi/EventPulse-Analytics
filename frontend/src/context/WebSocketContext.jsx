import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import { API_CONFIG } from '../config';

export const WebSocketContext = createContext(null);

const MAX_EVENTS_STORED = 10000;

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [totalEventsCount, setTotalEventsCount] = useState(0);
  const [metrics, setMetrics] = useState([]);
  const [currentAlert, setCurrentAlert] = useState(null); // Single current alert
  const [connectionError, setConnectionError] = useState(null);
  const [rateLimitExceeded, setRateLimitExceeded] = useState(false);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const alertTimeoutRef = useRef(null);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  const connect = useCallback((clientId, apiKey) => {
    if (!clientId || !apiKey) {
      console.warn('Cannot connect WebSocket: missing clientId or apiKey');
      return;
    }

    disconnect();

    try {
      const wsUrl = `${API_CONFIG.WS_URL}/ws/live/${clientId}?token=${apiKey}`;
      console.log('Connecting to WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        setRateLimitExceeded(false);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Don't reconnect if rate limited
        if (rateLimitExceeded) {
          return;
        }

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          console.log(`Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect(clientId, apiKey);
          }, reconnectDelay);
        } else {
          setConnectionError('Failed to connect after multiple attempts');
        }
      };

    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setConnectionError(err.message);
    }
  }, [rateLimitExceeded]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    reconnectAttemptsRef.current = 0;
  }, []);

  const handleMessage = useCallback((data) => {
    const { type } = data;

    switch (type) {
      case 'connected':
        console.log('WebSocket handshake complete:', data);
        break;

      case 'event':
        // Don't add events if rate limited
        if (!rateLimitExceeded) {
          setTotalEventsCount((c) => c + 1);
          setEvents((prev) => [data, ...prev].slice(0, MAX_EVENTS_STORED));
        }
        break;

      case 'metric':
        setMetrics((prev) => [data, ...prev].slice(0, 100));
        break;

      case 'alert':
        // Show only the latest alert immediately
        // Clear any previous alert timeout
        if (alertTimeoutRef.current) {
          clearTimeout(alertTimeoutRef.current);
        }
        
        // Set current alert
        setCurrentAlert({
          ...data,
          id: Date.now(),
          timestamp: new Date().toISOString(),
        });
        
        // Auto-dismiss after 10 seconds
        alertTimeoutRef.current = setTimeout(() => {
          setCurrentAlert(null);
        }, 10000);
        break;

      case 'rate_limit_exceeded':
      case 'error':
        if (data.message?.toLowerCase().includes('rate limit') || 
            data.message?.toLowerCase().includes('too many requests') ||
            type === 'rate_limit_exceeded') {
          console.log('🚫 Rate limit exceeded - stopping event stream');
          setRateLimitExceeded(true);
          
          // Immediately disconnect
          if (wsRef.current) {
            try {
              wsRef.current.close();
            } catch (e) {
              console.error('Error closing WebSocket:', e);
            }
            wsRef.current = null;
          }
          setIsConnected(false);
        }
        break;

      case 'pong':
        break;

      default:
        console.log('Unknown WebSocket message type:', type, data);
    }
  }, [rateLimitExceeded]);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
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

  useEffect(() => {
    return () => {
      disconnect();
      if (alertTimeoutRef.current) {
        clearTimeout(alertTimeoutRef.current);
      }
    };
  }, [disconnect]);

  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(() => {
      sendPing();
    }, 30000);

    return () => clearInterval(interval);
  }, [isConnected, sendPing]);

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