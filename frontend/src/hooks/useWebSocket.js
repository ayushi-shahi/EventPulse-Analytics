import { useContext } from 'react';
import { WebSocketContext } from '../context/WebSocketContext';

/**
 * Custom hook to use WebSocket context
 */
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  
  return context;
};

export default useWebSocket;