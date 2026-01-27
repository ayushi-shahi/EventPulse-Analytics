import { useContext } from 'react';
import { APIKeyContext } from '../context/APIKeyContext';

/**
 * Custom hook to use API Key context
 */
export const useAPIKey = () => {
  const context = useContext(APIKeyContext);
  
  if (!context) {
    throw new Error('useAPIKey must be used within an APIKeyProvider');
  }
  
  return context;
};

export default useAPIKey;