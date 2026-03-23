import React, { useState, useEffect, useCallback } from 'react';
import { getBackendStatus, retryRequest } from '../api';

export default function BackendStatusNotification() {
  const [isOffline, setIsOffline] = useState(false);
  const [showNotification, setShowNotification] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [lastFailedRequest, setLastFailedRequest] = useState(null);

  // Listen for backend status changes
  useEffect(() => {
    const handleBackendStatusChange = (event) => {
      const { isOffline } = event.detail;
      console.log('🔔 Backend status changed:', isOffline ? 'OFFLINE' : 'ONLINE');
      
      setIsOffline(isOffline);
      
      if (isOffline) {
        // Show notification when backend goes offline
        setShowNotification(true);
      } else {
        // Hide notification when backend comes back online
        setShowNotification(false);
        setLastFailedRequest(null);
      }
    };

    // Add event listener
    window.addEventListener('backendStatusChange', handleBackendStatusChange);

    // Check initial status
    const initialStatus = getBackendStatus();
    setIsOffline(initialStatus.isOffline);
    setShowNotification(initialStatus.isOffline);

    // Cleanup
    return () => {
      window.removeEventListener('backendStatusChange', handleBackendStatusChange);
    };
  }, []);

  // Handle manual retry
  const handleManualRetry = useCallback(async () => {
    if (!lastFailedRequest) {
      // If no specific request to retry, just check health
      setRetrying(true);
      try {
        const { checkBackendHealth } = await import('../api');
        const isHealthy = await checkBackendHealth();
        if (isHealthy) {
          setShowNotification(false);
          setIsOffline(false);
        }
      } catch (error) {
        console.error('Health check failed:', error);
      } finally {
        setRetrying(false);
      }
      return;
    }

    setRetrying(true);
    try {
      console.log('🔄 Manually retrying request...');
      const response = await retryRequest(lastFailedRequest);
      console.log('✅ Manual retry successful!');
      
      // If retry succeeds, hide notification
      setShowNotification(false);
      setIsOffline(false);
      setLastFailedRequest(null);
      
      // Optionally trigger a page refresh or data refetch
      window.dispatchEvent(new CustomEvent('backendReconnected'));
    } catch (error) {
      console.error('❌ Manual retry failed:', error);
      // Keep notification visible on failed retry
    } finally {
      setRetrying(false);
    }
  }, [lastFailedRequest]);

  // Store failed request for potential retry
  const storeFailedRequest = useCallback((request) => {
    setLastFailedRequest(request);
  }, []);

  // Don't render anything if backend is online
  if (!isOffline || !showNotification) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 max-w-md animate-fade-in">
      <div className="glass-card border-l-4 border-l-accent-rose p-4 shadow-lg">
        <div className="flex items-start gap-3">
          {/* Warning Icon */}
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-accent-rose/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-accent-rose" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
          </div>

          {/* Message Content */}
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-surface-100 mb-1">
              Server Unavailable
            </h4>
            <p className="text-sm text-surface-400 mb-3">
              ⚠️ Server is currently unavailable. Please try again in a few moments.
            </p>
            
            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleManualRetry}
                disabled={retrying}
                className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-50"
              >
                {retrying ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Retrying...
                  </>
                ) : (
                  <>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry
                  </>
                )}
              </button>
              
              <button
                onClick={() => setShowNotification(false)}
                className="btn-secondary text-xs px-3 py-1.5"
              >
                Dismiss
              </button>
            </div>

            {/* Additional Info */}
            <div className="mt-3 pt-3 border-t border-surface-700/50">
              <p className="text-xs text-surface-500">
                This usually happens when the server is restarting or experiencing high load. 
                Your data will be safe when the connection is restored.
              </p>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={() => setShowNotification(false)}
            className="flex-shrink-0 text-surface-400 hover:text-surface-200 transition-colors p-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// Hook to store failed requests for retry functionality
export const useFailedRequestStore = () => {
  const storeFailedRequest = useCallback((request) => {
    // This will be called by error boundaries or catch blocks
    window.lastFailedRequest = request;
  }, []);

  const getFailedRequest = useCallback(() => {
    return window.lastFailedRequest;
  }, []);

  const clearFailedRequest = useCallback(() => {
    delete window.lastFailedRequest;
  }, []);

  return { storeFailedRequest, getFailedRequest, clearFailedRequest };
};
