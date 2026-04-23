import { useEffect, useState } from "react";
import API from "../api";
import Sidebar from "../components/Sidebar";

export default function SessionManagement() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Form visibility and states
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    type: "ODD",
    year: new Date().getFullYear(),
    start_date: "",
    end_date: "",
    description: "",
    is_active: true
  });
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const { data } = await API.get("sessions/");
      setSessions(data);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch sessions.");
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      if (formData.id) {
        await API.put(`sessions/${formData.id}/`, formData);
      } else {
        await API.post("sessions/", formData);
      }
      setShowForm(false);
      setFormData({
        name: "",
        type: "ODD",
        year: new Date().getFullYear(),
        start_date: "",
        end_date: "",
        description: "",
        is_active: true
      });
      fetchSessions();
    } catch (err) {
      alert("Error saving session. Please check your data.");
      console.error(err);
    } finally {
      setFormLoading(false);
    }
  };

  const handleEdit = (session) => {
    setFormData(session);
    setShowForm(true);
  };

  const handleToggleActive = async (session) => {
    try {
      await API.patch(`sessions/${session.id}/`, {
        is_active: !session.is_active
      });
      fetchSessions();
    } catch (err) {
      alert("Error updating session status.");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex">
        <Sidebar role="hod" activeSection="sessions" />
        <main className="flex-1 ml-64 p-8 overflow-y-auto w-full flex items-center justify-center">
          <div className="spinner" />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar role="hod" activeSection="sessions" />
      <main className="flex-1 ml-64 p-8 overflow-y-auto w-full">
        <div className="max-w-6xl mx-auto animate-fade-in">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="text-3xl font-bold text-surface-100 font-display">Academic Sessions</h2>
              <p className="text-surface-400 mt-1">Manage overarching academic sessions for feedback mapping.</p>
            </div>
            <button
              onClick={() => {
                setFormData({
                  name: "",
                  type: "ODD",
                  year: new Date().getFullYear(),
                  start_date: "",
                  end_date: "",
                  description: "",
                  is_active: true
                });
                setShowForm(!showForm);
              }}
              className="btn-primary"
            >
              {showForm ? "Cancel" : "Create Session"}
            </button>
          </div>

          {error && (
            <div className="bg-accent-rose/20 text-accent-rose p-4 rounded-lg mb-6 border border-accent-rose/30">
              {error}
            </div>
          )}

          {showForm && (
            <div className="glass-card p-6 mb-8 border border-primary-500/30">
              <h3 className="text-xl font-semibold mb-4 text-surface-100">
                {formData.id ? "Edit Session" : "Create New Session"}
              </h3>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">Session Name</label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="e.g. ODD 2024"
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">Type</label>
                    <select
                      name="type"
                      value={formData.type}
                      onChange={handleInputChange}
                      className="input-field"
                    >
                      <option value="ODD">ODD</option>
                      <option value="EVEN">EVEN</option>
                      <option value="SUMM">SUMMER</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">Year</label>
                    <input
                      type="number"
                      name="year"
                      required
                      value={formData.year}
                      onChange={handleInputChange}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">Is Active</label>
                    <div className="mt-2 text-surface-200">
                      <input
                        type="checkbox"
                        name="is_active"
                        checked={formData.is_active}
                        onChange={handleInputChange}
                        className="mr-2"
                      />
                      Make this session currently active
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">Start Date</label>
                    <input
                      type="date"
                      name="start_date"
                      required
                      value={formData.start_date}
                      onChange={handleInputChange}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">End Date</label>
                    <input
                      type="date"
                      name="end_date"
                      required
                      value={formData.end_date}
                      onChange={handleInputChange}
                      className="input-field"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Description</label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleInputChange}
                    className="input-field min-h-[100px]"
                    placeholder="Optional details..."
                  />
                </div>
                <div className="pt-4 flex justify-end">
                  <button type="submit" disabled={formLoading} className="btn-primary">
                    {formLoading ? "Saving..." : "Save Session"}
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`glass-card p-6 border-l-4 ${
                  session.is_active ? "border-l-accent-emerald" : "border-l-surface-600"
                } relative`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-xl font-bold text-surface-100 font-display">
                    {session.name}
                  </h3>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      session.is_active
                        ? "bg-accent-emerald/20 text-accent-emerald"
                        : "bg-surface-700 text-surface-400"
                    }`}
                  >
                    {session.is_active ? "ACTIVE" : "INACTIVE"}
                  </span>
                </div>
                
                <p className="text-sm text-surface-400 mb-4">{session.description || "No description provided."}</p>
                
                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  <div>
                    <span className="block text-surface-500">Year</span>
                    <span className="text-surface-200">{session.year}</span>
                  </div>
                  <div>
                    <span className="block text-surface-500">Dates</span>
                    <span className="text-surface-200">{session.start_date.slice(5)} to {session.end_date.slice(5)}</span>
                  </div>
                </div>

                <div className="flex flex-col gap-2 pt-4 border-t border-surface-700/50">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(session)}
                      className="flex-1 py-1.5 px-3 bg-surface-700 hover:bg-surface-600 text-surface-200 rounded transition-colors text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleToggleActive(session)}
                      className={`flex-1 py-1.5 px-3 rounded transition-colors text-sm ${
                        session.is_active 
                          ? 'bg-amber-500/10 text-amber-500 hover:bg-amber-500/20' 
                          : 'bg-accent-emerald/10 text-accent-emerald hover:bg-accent-emerald/20'
                      }`}
                    >
                      {session.is_active ? "Togge Inactive" : "Activate"}
                    </button>
                  </div>
                  
                  {session.is_active && (
                    <button
                      onClick={async () => {
                        if (window.confirm(`Are you sure you want to end and archive the session "${session.name}"? This will close all active feedback windows.`)) {
                          try {
                            await API.post(`sessions/${session.id}/close/`);
                            fetchSessions();
                          } catch (err) {
                            alert("Failed to close session.");
                          }
                        }
                      }}
                      className="w-full py-1.5 px-3 bg-accent-rose/10 text-accent-rose hover:bg-accent-rose/20 rounded transition-colors text-sm font-bold border border-accent-rose/30"
                    >
                      🛑 End Feedback Session
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {sessions.length === 0 && !showForm && (
            <div className="glass-card p-12 text-center">
              <p className="text-surface-400 mb-4">No academic sessions found.</p>
              <button onClick={() => setShowForm(true)} className="btn-primary">
                Create First Session
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
