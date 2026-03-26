import axios from "axios";

// 1. Standardize to 127.0.0.1 (Safest for Windows/Chrome dev)
const BASE_URL = "http://127.0.0.1:8000/api";

const API = axios.create({
  baseURL: BASE_URL,
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (cb) => {
  refreshSubscribers.push(cb);
};

const onRefreshed = (token) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

// Backend downtime detection and retry logic
let retryCount = new Map(); // Track retry attempts per URL
const MAX_RETRIES = 1;
const RETRY_DELAY = 3000; // 3 seconds

// Check if error is due to backend being offline
const isBackendOfflineError = (error) => {
  return (
    error.code === 'ERR_NETWORK' ||
    error.code === 'ECONNREFUSED' ||
    error.code === 'ECONNABORTED' ||
    error.message?.includes('Network Error') ||
    error.message?.includes('ERR_CONNECTION_REFUSED') ||
    !error.response // No response indicates server is down
  );
};

// Global backend offline state
let isBackendOffline = false;
let offlineRetryTimer = null;

// Emit custom event for backend status changes
const emitBackendStatusChange = (isOffline) => {
  const event = new CustomEvent('backendStatusChange', { 
    detail: { isOffline, timestamp: Date.now() } 
  });
  window.dispatchEvent(event);
};

// Check backend health
const checkBackendHealth = async () => {
  try {
    const response = await axios.get(`${BASE_URL}/health/`, { 
      timeout: 5000,
      validateStatus: (status) => status < 500
    });
    return response.data?.status === 'ok';
  } catch (error) {
    return false;
  }
};

// Export the function for external use
export { checkBackendHealth };

// Attempt to reconnect to backend
const attemptReconnect = async () => {
  console.log('🔄 Attempting to reconnect to backend...');
  const isHealthy = await checkBackendHealth();
  
  if (isHealthy) {
    console.log('✅ Backend is back online!');
    isBackendOffline = false;
    emitBackendStatusChange(false);
    retryCount.clear(); // Clear retry count on successful reconnection
    return true;
  }
  
  return false;
};

// Schedule reconnection attempt
const scheduleReconnect = () => {
  if (offlineRetryTimer) {
    clearTimeout(offlineRetryTimer);
  }
  
  offlineRetryTimer = setTimeout(async () => {
    await attemptReconnect();
  }, RETRY_DELAY);
};

// --- REQUEST INTERCEPTOR ---
API.interceptors.request.use(
  (config) => {
    // 2. ENFORCE TRAILING SLASH: Django requires '/'. 
    // This prevents 301 redirects which often cause "Network Error" in Axios.
    if (config.url) {
      const [path, query] = config.url.split('?');
      if (path && !path.endsWith('/')) {
        config.url = query ? `${path}/?${query}` : `${path}/`;
      }
    }

    const token = localStorage.getItem("access_token");

    // Don't add Bearer token to login or refresh calls
    const isAuthPath = config.url.includes('auth/login') || config.url.includes('auth/token');

    if (token && !isAuthPath) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Skip request if backend is known to be offline (unless it's a health check)
    if (isBackendOffline && !config.url.includes('health/')) {
      console.log('🚫 Request blocked - backend is offline:', config.method?.toUpperCase(), config.url);
      return Promise.reject({ 
        isBackendOffline: true, 
        message: 'Backend is currently offline',
        config 
      });
    }

    console.log(`🚀 Request: ${config.method.toUpperCase()} ${config.baseURL}${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// --- RESPONSE INTERCEPTOR ---
API.interceptors.response.use(
  (response) => {
    console.log(`✅ Response: ${response.status} from ${response.config.url}`);
    
    // If we were offline but got a successful response, mark backend as online
    if (isBackendOffline) {
      console.log('🎉 Backend connection restored!');
      isBackendOffline = false;
      emitBackendStatusChange(false);
      retryCount.clear();
    }
    
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // --- DETAILED ERROR LOGGING ---
    if (error.response) {
      console.error(
        `❌ API Error [${error.response.status}] ${originalRequest?.method?.toUpperCase()} ${originalRequest?.url}:`,
        error.response.data?.error || error.response.data?.detail || error.message
      );
    } else if (error.code) {
      console.error(
        `❌ Network Error [${error.code}] ${originalRequest?.method?.toUpperCase()} ${originalRequest?.url}:`,
        error.message
      );
    }

    // --- BACKEND OFFLINE HANDLING ---
    if (isBackendOfflineError(error)) {
      console.log('🔌 Backend appears to be offline');
      
      // Mark backend as offline if not already marked
      if (!isBackendOffline) {
        isBackendOffline = true;
        emitBackendStatusChange(true);
        console.log('📡 Broadcasting backend offline status');
      }

      // Check if we should retry this request
      const requestKey = `${originalRequest?.method || 'GET'}-${originalRequest?.url || 'unknown'}`;
      const currentRetries = retryCount.get(requestKey) || 0;

      if (currentRetries < MAX_RETRIES) {
        retryCount.set(requestKey, currentRetries + 1);
        console.log(`🔄 Retrying request (${currentRetries + 1}/${MAX_RETRIES}):`, originalRequest?.url);
        
        // Schedule retry
        return new Promise((resolve) => {
          setTimeout(async () => {
            try {
              // Check backend health before retrying
              const isHealthy = await checkBackendHealth();
              if (isHealthy) {
                console.log('✅ Backend healthy, retrying request...');
                const retryResponse = await API(originalRequest);
                resolve(retryResponse);
              } else {
                console.log('❌ Backend still unhealthy, failing request');
                reject({ ...error, isBackendOffline: true, retryExhausted: true });
              }
            } catch (retryError) {
              console.log('❌ Retry failed:', retryError.message);
              reject({ ...error, isBackendOffline: true, retryExhausted: true });
            }
          }, RETRY_DELAY);
        });
      } else {
        console.log('❌ Max retries exhausted for:', originalRequest?.url);
        return Promise.reject({ ...error, isBackendOffline: true, retryExhausted: true });
      }
    }

    // --- TOKEN EXPIRATION HANDLING (401) ---
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url.includes("auth/login")) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");

      if (refreshToken) {
        if (!isRefreshing) {
          isRefreshing = true;
          console.log("🔄 Access token expired. Refreshing...");

          try {
            // Use BASE_URL directly to ensure consistency
            const response = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
              refresh: refreshToken
            });

            const { access } = response.data;
            localStorage.setItem("access_token", access);
            isRefreshing = false;
            onRefreshed(access);

            // Retry original request with new token
            originalRequest.headers.Authorization = `Bearer ${access}`;
            return API(originalRequest);
          } catch (refreshError) {
            console.error("❌ Session expired. Logging out.");
            isRefreshing = false;
            localStorage.clear();
            window.location.href = "/";
            return Promise.reject(refreshError);
          }
        } else {
          // Wait for the ongoing refresh
          return new Promise((resolve) => {
            subscribeTokenRefresh((newToken) => {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              resolve(API(originalRequest));
            });
          });
        }
      }
    }

    // --- NETWORK ERRORS — max 1 retry only for connection failures ---
    const isNetworkError = error.code === "ERR_NETWORK" || error.code === "ECONNABORTED";

    if (isNetworkError && (!originalRequest._networkRetryCount || originalRequest._networkRetryCount < 1)) {
      originalRequest._networkRetryCount = (originalRequest._networkRetryCount || 0) + 1;
      console.warn("⚠️ Backend unreachable. Retrying once in 2s...");

      return new Promise((resolve) => {
        setTimeout(() => resolve(API(originalRequest)), 2000);
      });
    }

    // User-friendly message for connection failures
    if (error.code === "ERR_NETWORK") {
      error.message = "Could not connect to the server. Please ensure Django is running on port 8000.";
    }

    // --- FIRST LOGIN / PASSWORD CHANGE HANDLING (403) ---
    if (error.response?.status === 403 && error.response.data?.force_password_change) {
      console.warn("🔐 Password change required. Redirecting...");
      window.location.href = "/change-password";
      return Promise.reject(error);
    }

    return Promise.reject(error);
  }
);

/**
 * Manual retry function for user-initiated retries
 */
export const retryRequest = async (originalRequest) => {
  console.log('🔄 Manual retry requested for:', originalRequest?.url);
  
  // Clear retry count for this request
  const requestKey = `${originalRequest?.method || 'GET'}-${originalRequest?.url || 'unknown'}`;
  retryCount.delete(requestKey);
  
  // Check backend health first
  const isHealthy = await checkBackendHealth();
  if (isHealthy) {
    isBackendOffline = false;
    emitBackendStatusChange(false);
    return API(originalRequest);
  } else {
    throw new Error('Backend is still offline');
  }
};

/**
 * Get current backend status
 */
export const getBackendStatus = () => ({
  isOffline: isBackendOffline,
  retryCount: Object.fromEntries(retryCount)
});

export default API;