import React, { useState, useEffect } from 'react';
import API from '../api';

export default function FeedbackWindowManager() {
  const [windows, setWindows] = useState([]);
  const [currentWindow, setCurrentWindow] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    start_date: '',
    end_date: '',
    is_active: true
  });

  useEffect(() => {
    fetchWindows();
    fetchCurrentWindow();
  }, []);

  const fetchWindows = async () => {
    try {
      const response = await API.get('hod/feedback-windows/');
      setWindows(response.data);
    } catch (error) {
      console.error('Failed to fetch feedback windows:', error);
    }
  };

  const fetchCurrentWindow = async () => {
    try {
      const response = await API.get('feedback-window/current/');
      setCurrentWindow(response.data);
    } catch (error) {
      // No current window is okay
      setCurrentWindow(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await API.post('hod/feedback-windows/', formData);
      setWindows([response.data, ...windows]);
      setCurrentWindow(response.data);
      setShowForm(false);
      setFormData({ start_date: '', end_date: '', is_active: true });
    } catch (error) {
      console.error('Failed to create feedback window:', error);
      alert('Failed to create feedback window');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (windowId) => {
    try {
      const window = windows.find(w => w.id === windowId);
      const response = await API.put(`hod/feedback-windows/${windowId}/`, {
        is_active: !window.is_active
      });
      
      setWindows(windows.map(w => w.id === windowId ? response.data : w));
      if (response.data.is_active) {
        setCurrentWindow(response.data);
      } else {
        setCurrentWindow(null);
      }
    } catch (error) {
      console.error('Failed to toggle feedback window:', error);
      alert('Failed to update feedback window');
    }
  };

  const handleDelete = async (windowId) => {
    if (!confirm('Are you sure you want to delete this feedback window?')) {
      return;
    }

    try {
      await API.delete(`hod/feedback-windows/${windowId}/`);
      setWindows(windows.filter(w => w.id !== windowId));
      if (currentWindow?.id === windowId) {
        setCurrentWindow(null);
      }
    } catch (error) {
      console.error('Failed to delete feedback window:', error);
      alert('Failed to delete feedback window');
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (window) => {
    const now = new Date();
    const start = new Date(window.start_date);
    const end = new Date(window.end_date);

    if (!window.is_active) return 'bg-gray-100 text-gray-800';
    if (now < start) return 'bg-blue-100 text-blue-800';
    if (now > end) return 'bg-gray-100 text-gray-800';
    return 'bg-green-100 text-green-800';
  };

  const getStatusText = (window) => {
    const now = new Date();
    const start = new Date(window.start_date);
    const end = new Date(window.end_date);

    if (!window.is_active) return 'Inactive';
    if (now < start) return 'Upcoming';
    if (now > end) return 'Expired';
    return 'Active';
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold">Feedback Window Management</h3>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition"
        >
          Create New Window
        </button>
      </div>

      {/* Current Status */}
      {currentWindow && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <h4 className="font-medium text-green-800 mb-2">Current Active Window</h4>
          <div className="text-sm text-green-700">
            <p><strong>Start:</strong> {formatDate(currentWindow.start_date)}</p>
            <p><strong>End:</strong> {formatDate(currentWindow.end_date)}</p>
            <p><strong>Status:</strong> Students can submit feedback</p>
          </div>
        </div>
      )}

      {!currentWindow && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h4 className="font-medium text-yellow-800 mb-2">No Active Feedback Window</h4>
          <p className="text-sm text-yellow-700">Students cannot submit feedback until an active window is created.</p>
        </div>
      )}

      {/* Create Form */}
      {showForm && (
        <div className="mb-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
          <h4 className="font-medium mb-4">Create New Feedback Window</h4>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date and Time
              </label>
              <input
                type="datetime-local"
                value={formData.start_date}
                onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                className="w-full border rounded px-3 py-2"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date and Time
              </label>
              <input
                type="datetime-local"
                value={formData.end_date}
                onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                className="w-full border rounded px-3 py-2"
                required
              />
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                className="mr-2"
              />
              <label htmlFor="is_active" className="text-sm text-gray-700">
                Activate immediately (will deactivate other windows)
              </label>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition disabled:bg-blue-400"
              >
                {loading ? 'Creating...' : 'Create Window'}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Windows List */}
      <div className="space-y-3">
        {windows.map((window) => (
          <div key={window.id} className="border border-gray-200 rounded-lg p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(window)}`}>
                    {getStatusText(window)}
                  </span>
                  {window.is_active && (
                    <span className="text-xs text-green-600 font-medium">Currently Active</span>
                  )}
                </div>
                <div className="text-sm text-gray-600">
                  <p><strong>Start:</strong> {formatDate(window.start_date)}</p>
                  <p><strong>End:</strong> {formatDate(window.end_date)}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleToggleActive(window.id)}
                  className={`px-3 py-1 rounded text-sm transition ${
                    window.is_active 
                      ? 'bg-gray-500 text-white hover:bg-gray-600' 
                      : 'bg-green-600 text-white hover:bg-green-700'
                  }`}
                >
                  {window.is_active ? 'Deactivate' : 'Activate'}
                </button>
                <button
                  onClick={() => handleDelete(window.id)}
                  className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
        
        {windows.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <p>No feedback windows created yet.</p>
            <p className="text-sm">Create a window to allow students to submit feedback.</p>
          </div>
        )}
      </div>
    </div>
  );
}
