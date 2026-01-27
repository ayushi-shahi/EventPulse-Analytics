import { useState, useCallback } from 'react';
import { useNotification } from './useNotification';

/**
 * Custom hook for API calls with loading and error states
 */
export const useAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { error: showError } = useNotification();

  /**
   * Execute an async API call
   */
  const execute = useCallback(async (apiCall, options = {}) => {
    const {
      onSuccess = null,
      onError = null,
      showErrorNotification = true,
      showSuccessNotification = false,
      successMessage = 'Success!',
    } = options;

    setLoading(true);
    setError(null);

    try {
      const result = await apiCall();
      
      if (showSuccessNotification) {
        showError(successMessage, 'success');
      }
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err) {
      const errorMessage = err.message || 'An error occurred';
      setError(errorMessage);
      
      if (showErrorNotification) {
        showError(errorMessage);
      }
      
      if (onError) {
        onError(err);
      }
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [showError]);

  /**
   * Reset error state
   */
  const resetError = useCallback(() => {
    setError(null);
  }, []);

  return {
    loading,
    error,
    execute,
    resetError,
  };
};

export default useAPI;