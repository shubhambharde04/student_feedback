import { useState, useEffect, useCallback } from "react";
import API from "../api";
import Sidebar from "../components/Sidebar";
import Toast from "../components/Toast";
import { Users, Upload, Trash2, UserPlus, Search, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

export default function StudentManagement() {
  const [user, setUser] = useState(null);
  const [students, setStudents] = useState([]);
  const [branches, setBranches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStudents, setSelectedStudents] = useState([]);
  
  const [bulkEnrollData, setBulkEnrollData] = useState({
    branch_id: "",
    semester_id: ""
  });

  const fetchInitialData = useCallback(async () => {
    try {
      const [profileRes, branchRes, semRes, sessionRes] = await Promise.all([
        API.get("auth/profile/"),
        API.get("branches/"),
        API.get("semesters/"),
        API.get("sessions/")
      ]);
      
      setUser(profileRes.data.user);
      setBranches(branchRes.data);
      setSemesters(semRes.data);
      
      const activeSessions = sessionRes.data.filter(s => s.is_active);
      setSessions(activeSessions);
      if (activeSessions.length > 0 && !selectedSessionId) {
        setSelectedSessionId(activeSessions[0].id.toString());
      }
    } catch (err) {
      console.error("Error fetching initial data:", err);
      setToast({ message: "Failed to load management data", type: "error" });
    } finally {
      setLoading(false);
    }
  }, [selectedSessionId]);

  const fetchStudents = useCallback(async () => {
    if (!selectedSessionId) return;
    try {
      const studentRes = await API.get(`enrollments/form-data/?session_id=${selectedSessionId}`);
      if (studentRes.data.students) {
        setStudents(studentRes.data.students);
      }
    } catch (err) {
      console.error("Error fetching students:", err);
    }
  }, [selectedSessionId]);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedSessionId) {
      setToast({ message: "Please manually select an Academic Session first", type: "warning" });
      e.target.value = null;
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", selectedSessionId);

    try {
      const res = await API.post("students/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000 // 2 min timeout for large Excel files
      });

      if (res.data.success && res.data.stats) {
        const { created, updated, skipped_existing, errors, warnings } = res.data.stats;
        let msg = `✅ ${created} created, ${updated} updated, ${skipped_existing} skipped.`;
        if (errors.length > 0) msg += ` ⚠️ ${errors.length} error(s).`;
        if (warnings && warnings.length > 0) msg += ` 📋 ${warnings.length} warning(s).`;
        setToast({ message: msg, type: errors.length > 0 ? "warning" : "success" });
      } else if (res.data.success && res.data.preview) {
        setToast({ message: `Preview: ${res.data.total_valid_rows} valid rows found.`, type: "success" });
      } else {
        setToast({ message: res.data.error || "Upload returned unexpected response", type: "error" });
      }

      fetchStudents(); // Refresh list
    } catch (err) {
      const detail = err.response?.data?.error
        || err.response?.data?.detail
        || (err.code === 'ECONNABORTED' ? 'Upload timed out — the file may be too large' : null)
        || err.message
        || "Upload failed";
      setToast({ message: `❌ ${detail}`, type: "error" });
    } finally {
      setUploading(false);
      e.target.value = null; // Reset input
    }
  };

  const handleBulkDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete ${selectedStudents.length} students?`)) return;

    setProcessing(true);
    try {
      await API.post("students/bulk-delete/", { student_ids: selectedStudents });
      setToast({ message: `Successfully deleted selected students`, type: "success" });
      setSelectedStudents([]);
      fetchStudents();
    } catch (err) {
      setToast({ message: "Bulk delete failed", type: "error" });
    } finally {
      setProcessing(false);
    }
  };

  const handleBulkEnroll = async () => {
    if (!bulkEnrollData.branch_id || !bulkEnrollData.semester_id || selectedStudents.length === 0) {
      setToast({ message: "Please select branch, semester and students", type: "warning" });
      return;
    }

    setProcessing(true);
    try {
      await API.post("students/bulk-enroll-semester/", {
        student_ids: selectedStudents,
        branch_id: bulkEnrollData.branch_id,
        semester_id: bulkEnrollData.semester_id,
        session_id: selectedSessionId
      });
      setToast({ message: "Students enrolled successfully", type: "success" });
      setSelectedStudents([]);
      fetchStudents();
    } catch (err) {
      setToast({ message: "Bulk enrollment failed", type: "error" });
    } finally {
      setProcessing(false);
    }
  };

  const toggleStudentSelection = (id) => {
    setSelectedStudents(prev => 
      prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id]
    );
  };

  const filteredStudents = students.filter(s => 
    s.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.full_name && s.full_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar role="hod" activeSection="students" user={user} />
      
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <header className="mb-8 flex justify-between items-end">
            <div>
              <h1 className="text-2xl font-bold font-display text-surface-100 flex items-center gap-2">
                <Users className="text-primary-400" /> Student Management
              </h1>
              <p className="text-surface-400 text-sm mt-1">Manage student database, bulk uploads, and semester enrollment.</p>
            </div>
            
            <div className="flex flex-col items-end gap-2">
              <div className="flex gap-3 items-center">
                <select
                  className="input-dark py-2 text-sm max-w-xs"
                  value={selectedSessionId}
                  onChange={(e) => setSelectedSessionId(e.target.value)}
                >
                  <option value="">Select Session...</option>
                  {sessions.map(s => <option key={s.id} value={s.id}>{s.name} ({s.year})</option>)}
                </select>
                <label className="btn-primary py-2.5 px-4 text-sm cursor-pointer flex items-center gap-2">
                  <Upload size={18} />
                  {uploading ? "Uploading..." : "Bulk Student Upload"}
                  <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFileUpload} disabled={uploading || !selectedSessionId} />
                </label>
              </div>
              <a 
                href={`${API.defaults.baseURL}students/upload-template/`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-primary-400 hover:text-primary-300 underline flex items-center gap-1"
              >
                📥 Download Excel/CSV Template
              </a>
            </div>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Search & Stats */}
            <div className="lg:col-span-2 glass-card p-6">
              <div className="relative mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" size={18} />
                <input 
                  type="text" 
                  placeholder="Search students by enrollment no or name..." 
                  className="input-dark pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              
              <div className="flex items-center justify-between text-sm">
                <div className="flex gap-4">
                  <div className="text-surface-400">Total Students: <span className="text-primary-400 font-bold">{students.length}</span></div>
                  <div className="text-surface-400">Selected: <span className="text-accent-cyan font-bold">{selectedStudents.length}</span></div>
                </div>
                {selectedStudents.length > 0 && (
                  <button 
                    onClick={handleBulkDelete}
                    disabled={processing}
                    className="text-accent-rose hover:text-accent-rose/80 flex items-center gap-1.5 font-medium transition-colors"
                  >
                    <Trash2 size={16} /> Delete Selected
                  </button>
                )}
              </div>
            </div>

            {/* Bulk Enroll Card */}
            <div className="glass-card p-6 border-l-4 border-l-accent-cyan">
              <h3 className="text-sm font-bold text-surface-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                <UserPlus size={16} /> Bulk Semester Enroll
              </h3>
              <div className="space-y-4">
                <select 
                  className="input-dark text-sm"
                  value={bulkEnrollData.branch_id}
                  onChange={(e) => setBulkEnrollData(prev => ({ ...prev, branch_id: e.target.value }))}
                >
                  <option value="">Select Branch</option>
                  {branches.map(b => <option key={b.id} value={b.id}>{b.code} - {b.name}</option>)}
                </select>
                
                <select 
                  className="input-dark text-sm"
                  value={bulkEnrollData.semester_id}
                  onChange={(e) => setBulkEnrollData(prev => ({ ...prev, semester_id: e.target.value }))}
                >
                  <option value="">Select Semester</option>
                  {semesters.map(s => <option key={s.id} value={s.id}>Semester {s.number}</option>)}
                </select>
                
                <button 
                  onClick={handleBulkEnroll}
                  disabled={processing || selectedStudents.length === 0}
                  className="w-full btn-success py-2.5 text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle size={18} />}
                  Enroll Selected
                </button>
              </div>
            </div>
          </div>

          {/* Student Table */}
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-surface-700/50 bg-surface-800/30 text-surface-400">
                    <th className="px-6 py-4 w-10">
                      <input 
                        type="checkbox" 
                        className="rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
                        checked={selectedStudents.length === filteredStudents.length && filteredStudents.length > 0}
                        onChange={() => {
                          if (selectedStudents.length === filteredStudents.length) setSelectedStudents([]);
                          else setSelectedStudents(filteredStudents.map(s => s.id));
                        }}
                      />
                    </th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Student</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Enrollment No</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Current Semester</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">First Login</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/30">
                  {filteredStudents.map(student => (
                    <tr key={student.id} className="hover:bg-surface-800/20 transition-colors">
                      <td className="px-6 py-4">
                        <input 
                          type="checkbox" 
                          className="rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
                          checked={selectedStudents.includes(student.id)}
                          onChange={() => toggleStudentSelection(student.id)}
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-surface-800 flex items-center justify-center text-xs font-bold text-primary-400">
                            {student.username.charAt(0)}
                          </div>
                          <div>
                            <p className="text-surface-100 font-medium">{student.full_name || student.username}</p>
                            <p className="text-xs text-surface-500">{student.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-surface-300 font-mono">
                        {student.username}
                      </td>
                      <td className="px-6 py-4">
                        {student.student_profile ? (
                          <span className="badge badge-excellent">
                            {student.student_profile.branch_code} Sem {student.student_profile.semester_number}
                          </span>
                        ) : (
                          <span className="text-surface-500">Not Enrolled</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {student.is_first_login ? (
                          <span className="text-accent-amber flex items-center gap-1.5 text-xs">
                             <AlertCircle size={14} /> Yes
                          </span>
                        ) : (
                          <span className="text-accent-emerald flex items-center gap-1.5 text-xs">
                             <CheckCircle size={14} /> No
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredStudents.length === 0 && (
                <div className="p-12 text-center text-surface-500">
                  <p className="text-4xl mb-3">🔍</p>
                  <p>No students found matching your search</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
