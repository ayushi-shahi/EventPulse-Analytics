import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import { API_CONFIG } from '../config';

export const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [connectionError, setConnectionError] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  /**
   * Connect to WebSocket
   */
  const connect = useCallback((clientId, apiKey) => {
    if (!clientId || !apiKey) {
      console.warn('Cannot connect WebSocket: missing clientId or apiKey');
      return;
    }

    // Close existing connection
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

        // Attempt to reconnect
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
  }, []);

  /**
   * Disconnect from WebSocket
   */
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

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((data) => {
    const { type } = data;

    switch (type) {
      case 'connected':
        console.log('WebSocket handshake complete:', data);
        break;

      case 'event':
        setEvents((prev) => {
          const newEvents = [data, ...prev].slice(0, 1000); // Keep last 1000
          return newEvents;
        });
        break;

      case 'metric':
        setMetrics((prev) => {
          const newMetrics = [data, ...prev].slice(0, 100); // Keep last 100
          return newMetrics;
        });
        break;

      case 'alert':
        setAlerts((prev) => {
          const newAlerts = [data, ...prev].slice(0, 50); // Keep last 50
          return newAlerts;
        });
        break;

      case 'pong':
        // Heartbeat response
        break;

      default:
        console.log('Unknown WebSocket message type:', type, data);
    }
  }, []);

  /**
   * Send message through WebSocket
   */
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  /**
   * Send ping to keep connection alive
   */
  const sendPing = useCallback(() => {
    sendMessage({ type: 'ping', timestamp: new Date().toISOString() });
  }, [sendMessage]);

  /**
   * Clear events
   */
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  /**
   * Clear metrics
   */
  const clearMetrics = useCallback(() => {
    setMetrics([]);
  }, []);

  /**
   * Clear alerts
   */
  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  /**
   * Heartbeat ping every 30 seconds
   */
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
    metrics,
    alerts,
    connect,
    disconnect,
    sendMessage,
    clearEvents,
    clearMetrics,
    clearAlerts,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketContext;