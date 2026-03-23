import React, { useState, useEffect } from 'react';
import API, { checkBackendHealth, getBackendStatus } from '../api';
import { useBackendStatus } from '../hooks/useBackendStatus';

export default function BackendStatusDemo() {
  const [testResult, setTestResult] = useState('');
  const [testing, setTesting] = useState(false);
  const { isOffline, lastChecked, retryCount, refreshStatus } = useBackendStatus();

  const testBackendConnection = async () => {
    setTesting(true);
    setTestResult('');
    
    try {
      const isHealthy = await checkBackendHealth();
      setTestResult(isHealthy ? '✅ Backend is online and responding!' : '❌ Backend is offline');
    } catch (error) {
      setTestResult('❌ Backend connection failed: ' + error.message);
    } finally {
      setTesting(false);
    }
  };

  const testAPIRequest = async () => {
    setTesting(true);
    setTestResult('');
    
    try {
      const response = await API.get('auth/profile/');
      setTestResult('✅ API request successful!');
    } catch (error) {
      if (error.isBackendOffline) {
        setTestResult('⚠️ Backend is offline - this is expected behavior');
      } else {
        setTestResult('❌ API request failed: ' + (error.response?.data?.error || error.message));
      }
    } finally {
      setTesting(false);
    }
  };

  const getDetailedStatus = () => {
    const status = getBackendStatus();
    return JSON.stringify(status, null, 2);
  };

  return (
    <div className="min-h-screen bg-mesh p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-surface-100 mb-8">Backend Status Demo</h1>
        
        {/* Status Overview */}
        <div className="glass-card p-6 mb-6">
          <h2 className="text-xl font-semibold text-surface-100 mb-4">Current Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`p-4 rounded-lg border ${
              isOffline 
                ? 'bg-accent-rose/10 border-accent-rose/20' 
                : 'bg-accent-emerald/10 border-accent-emerald/20'
            }`}>
              <div className="text-sm text-surface-400 mb-1">Backend Status</div>
              <div className={`text-lg font-bold ${
                isOffline ? 'text-accent-rose' : 'text-accent-emerald'
              }`}>
                {isOffline ? 'OFFLINE' : 'ONLINE'}
              </div>
            </div>
            
            <div className="p-4 rounded-lg border border-surface-700/50 bg-surface-800/50">
              <div className="text-sm text-surface-400 mb-1">Retry Count</div>
              <div className="text-lg font-bold text-surface-100">{retryCount}</div>
            </div>
            
            <div className="p-4 rounded-lg border border-surface-700/50 bg-surface-800/50">
              <div className="text-sm text-surface-400 mb-1">Last Checked</div>
              <div className="text-lg font-bold text-surface-100">
                {lastChecked ? new Date(lastChecked).toLocaleTimeString() : 'Never'}
              </div>
            </div>
          </div>
        </div>

        {/* Test Controls */}
        <div className="glass-card p-6 mb-6">
          <h2 className="text-xl font-semibold text-surface-100 mb-4">Test Controls</h2>
          <div className="flex gap-4 mb-4">
            <button
              onClick={testBackendConnection}
              disabled={testing}
              className="btn-primary"
            >
              {testing ? 'Testing...' : 'Test Backend Health'}
            </button>
            
            <button
              onClick={testAPIRequest}
              disabled={testing}
              className="btn-secondary"
            >
              {testing ? 'Testing...' : 'Test API Request'}
            </button>
            
            <button
              onClick={refreshStatus}
              className="btn-secondary"
            >
              Refresh Status
            </button>
          </div>
          
          {testResult && (
            <div className={`p-4 rounded-lg border ${
              testResult.includes('✅') 
                ? 'bg-accent-emerald/10 border-accent-emerald/20 text-accent-emerald'
                : 'bg-accent-rose/10 border-accent-rose/20 text-accent-rose'
            }`}>
              {testResult}
            </div>
          )}
        </div>

        {/* Detailed Status */}
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-surface-100 mb-4">Detailed Status</h2>
          <pre className="text-xs text-surface-400 bg-surface-900/50 p-4 rounded-lg overflow-auto">
            {getDetailedStatus()}
          </pre>
        </div>

        {/* Instructions */}
        <div className="glass-card p-6 mt-6">
          <h2 className="text-xl font-semibold text-surface-100 mb-4">How to Test</h2>
          <ol className="list-decimal list-inside space-y-2 text-surface-300">
            <li>Start the Django backend: <code className="bg-surface-800 px-2 py-1 rounded">python manage.py runserver</code></li>
            <li>Click "Test Backend Health" - should show ✅ when backend is online</li>
            <li>Stop the Django backend (Ctrl+C in terminal)</li>
            <li>Click "Test Backend Health" again - should show ❌ when backend is offline</li>
            <li>Notice the notification appears in the top-right corner</li>
            <li>Restart the backend and watch the notification disappear automatically</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
