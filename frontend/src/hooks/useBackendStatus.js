import { useState, useEffect, useCallback } from 'react';
import { getBackendStatus } from '../api';

export const useBackendStatus = () => {
  const [isOffline, setIsOffline] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    // Listen for backend status changes
    const handleBackendStatusChange = (event) => {
      const { isOffline, timestamp } = event.detail;
      setIsOffline(isOffline);
      setLastChecked(timestamp);
    };

    window.addEventListener('backendStatusChange', handleBackendStatusChange);

    // Check initial status
    const initialStatus = getBackendStatus();
    setIsOffline(initialStatus.isOffline);
    setRetryCount(Object.keys(initialStatus.retryCount).length);

    return () => {
      window.removeEventListener('backendStatusChange', handleBackendStatusChange);
    };
  }, []);

  const refreshStatus = useCallback(() => {
    const status = getBackendStatus();
    setIsOffline(status.isOffline);
    setRetryCount(Object.keys(status.retryCount).length);
    setLastChecked(Date.now());
  }, []);

  return {
    isOffline,
    lastChecked,
    retryCount,
    refreshStatus
  };
};

export default useBackendStatus;
