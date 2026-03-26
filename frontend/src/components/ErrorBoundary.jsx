import React, { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      isNetworkError: false 
    };
  }

  static getDerivedStateFromError(error) {
    const isNetworkError = 
      error?.message?.includes('Network Error') ||
      error?.message?.includes('ERR_NETWORK') ||
      error?.message?.includes('ERR_CONNECTION_REFUSED') ||
      error?.code === 'ERR_NETWORK' ||
      error?.code === 'ECONNREFUSED' ||
      error?.isBackendOffline;

    return { hasError: true, error: error || null, isNetworkError };
  }

  componentDidCatch(error, errorInfo) {
    console.error('🚨 Error Boundary caught an error:', error, errorInfo);
    
    // Only update errorInfo — error is already set by getDerivedStateFromError
    this.setState({
      errorInfo: errorInfo || null,
    });

    if (process.env.NODE_ENV === 'production') {
      console.error('Production error logged:', {
        message: error?.message,
        stack: error?.stack,
        componentStack: errorInfo?.componentStack ?? 'N/A',
      });
    }
  }

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      isNetworkError: false 
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.state.isNetworkError) {
        return (
          <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
            <div className="glass-card p-8 max-w-md text-center">
              <div className="w-16 h-16 rounded-full bg-accent-rose/20 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-accent-rose" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              
              <h2 className="text-xl font-bold text-surface-100 mb-2">
                Connection Lost
              </h2>
              
              <p className="text-surface-400 mb-6">
                ⚠️ Server is currently unavailable. Please try again in a few moments.
              </p>
              
              <div className="space-y-3">
                <button
                  onClick={this.handleReset}
                  className="btn-primary w-full"
                >
                  Try Again
                </button>
                
                <button
                  onClick={() => window.location.reload()}
                  className="btn-secondary w-full"
                >
                  Refresh Page
                </button>
              </div>
              
              <div className="mt-6 pt-6 border-t border-surface-700/50">
                <p className="text-xs text-surface-500">
                  If this problem persists, please check your internet connection or contact support.
                </p>
              </div>
            </div>
          </div>
        );
      }

      // Safely extract error details — errorInfo may be null if componentDidCatch hasn't fired yet
      const errorMessage = this.state.error?.toString?.() || 'Unknown error';
      const componentStack = this.state.errorInfo?.componentStack || 'No component stack available';

      return (
        <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
          <div className="glass-card p-8 max-w-md text-center">
            <div className="w-16 h-16 rounded-full bg-accent-amber/20 flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-accent-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            
            <h2 className="text-xl font-bold text-surface-100 mb-2">
              Something went wrong
            </h2>
            
            <p className="text-surface-400 mb-6">
              An unexpected error occurred. We're working to fix this issue.
            </p>
            
            <div className="space-y-3">
              <button
                onClick={this.handleReset}
                className="btn-primary w-full"
              >
                Try Again
              </button>
                
              <button
                onClick={() => window.location.reload()}
                className="btn-secondary w-full"
              >
                Refresh Page
              </button>
            </div>
            
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-6 pt-6 border-t border-surface-700/50 text-left">
                <summary className="text-xs text-surface-500 cursor-pointer hover:text-surface-400">
                  Error Details (Development Only)
                </summary>
                <pre className="mt-2 text-xs text-surface-600 overflow-auto max-h-32 whitespace-pre-wrap">
                  {errorMessage}
                  {'\n'}
                  {componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export const withErrorBoundary = (WrappedComponent) => {
  return function WithErrorBoundary(props) {
    return (
      <ErrorBoundary>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
};

export default ErrorBoundary;
