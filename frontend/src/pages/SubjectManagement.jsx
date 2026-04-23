import { useState, useEffect, useCallback } from "react";
import API from "../api";
import Sidebar from "../components/Sidebar";
import Toast from "../components/Toast";
import {
  BookOpen, Plus, Search, Filter, Edit2, Trash2,
  UserCheck, AlertCircle, Loader2, Book, Bookmark
} from "lucide-react";

export default function SubjectManagement() {
  const [user, setUser] = useState(null);
  const [offerings, setOfferings] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState("assign"); // "offering" or "assign"

  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  
  const [filters, setFilters] = useState({
    semester: "",
    branch: "",
    search: ""
  });

  const [formData, setFormData] = useState({
    offering_id: "",
    subject_id: "",
    branch_id: "",
    semester_id: "",
    teacher_id: ""
  });

  const fetchData = useCallback(async () => {
    try {
      const queryParams = new URLSearchParams();
      if (filters.semester) queryParams.append("semester", filters.semester);
      if (filters.branch) queryParams.append("branch", filters.branch);

      const [offeringsRes, teacherRes, subjectRes, branchRes, semRes, profileRes, sessionRes] = await Promise.all([
        API.get(selectedSessionId ? `session-offerings/?session=${selectedSessionId}&${queryParams.toString()}` : `session-offerings/?${queryParams.toString()}`),
        API.get("hod/teachers/"),
        API.get("subjects/"),
        API.get("branches/"),
        API.get("semesters/"),
        API.get("auth/profile/"),
        API.get("sessions/") // Fetch valid sessions
      ]);

      setOfferings(offeringsRes.data);
      setTeachers(teacherRes.data);
      setSubjects(subjectRes.data);
      setBranches(branchRes.data);
      setSemesters(semRes.data);
      setUser(profileRes.data.user);
      
      const activeSessions = sessionRes.data.filter(s => s.is_active);
      setSessions(activeSessions);
      if (!selectedSessionId && activeSessions.length > 0) {
        setSelectedSessionId(activeSessions[0].id.toString());
      }
    } catch (err) {
      console.error("Error fetching subject management data:", err);
      // setToast({ message: "Failed to load management data", type: "error" });
    } finally {
      setLoading(false);
    }
  }, [filters.semester, filters.branch, selectedSessionId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateOffering = async (e) => {
    e.preventDefault();
    if (!selectedSessionId) {
      setToast({ message: "Please select an Academic Session first", type: "warning" });
      return;
    }
    setProcessing(true);
    try {
      // Step 1: Ensure base offering exists
      let baseOfferingId = null;
      try {
        const baseRes = await API.post("subject-offerings/", {
          subject: formData.subject_id,
          branch: formData.branch_id,
          semester: formData.semester_id
        });
        baseOfferingId = baseRes.data.id;
      } catch (err) {
        // Might already exist
        if (err.response?.data?.non_field_errors?.[0]?.includes("unique")) {
          // Fetch existing base offering
          const existingRes = await API.get(`subject-offerings/?branch=${formData.branch_id}&semester=${formData.semester_id}`);
          const existing = existingRes.data.find(o => o.subject === parseInt(formData.subject_id) || o.subject_id === parseInt(formData.subject_id));
          if (existing) {
             baseOfferingId = existing.id;
          }
        } else {
           throw err; // Real error
        }
      }

      if (!baseOfferingId) throw new Error("Could not create or find base Subject Offering");

      // Step 2: Create Session Offering
      await API.post("session-offerings/", {
        session: selectedSessionId,
        base_offering: baseOfferingId,
        teacher: formData.teacher_id
      });
      
      setToast({ message: "Session offering created successfully", type: "success" });
      setIsModalOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.non_field_errors?.[0] || err.message || "Failed to create offering";
      setToast({ message: msg, type: "error" });
    } finally {
      setProcessing(false);
    }
  };

  const handleAssignTeacher = async (e) => {
    e.preventDefault();
    setProcessing(true);
    try {
      // In Session architecture, editing assignment means patching the session-offering
      await API.patch(`session-offerings/${formData.offering_id}/`, {
        teacher: formData.teacher_id
      });
      setToast({ message: "Teacher updated successfully", type: "success" });

      setIsModalOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      const msg = Object.values(err.response?.data || {}).flat()[0] || "Failed to assign teacher";
      setToast({ message: msg, type: "error" });
    } finally {
      setProcessing(false);
    }
  };

  const handleDeleteOffering = async (offeringId) => {
    if (!window.confirm("Delete this session offering? This will remove the teacher assignment and may break feedback bound to this session!")) return;
    try {
      await API.delete(`session-offerings/${offeringId}/`);
      setToast({ message: "Session offering deleted", type: "success" });
      fetchData();
    } catch (err) {
      setToast({ message: "Failed to delete offering", type: "error" });
    }
  };

  const resetForm = () => {
    setFormData({
      offering_id: "",
      subject_id: "",
      branch_id: "",
      semester_id: "",
      teacher_id: ""
    });
  };

  const openAssignModal = (offering) => {
    setModalType(offering.teacher_id ? "assignment-edit" : "assign");
    setFormData({
      ...formData,
      offering_id: offering.id,
      teacher_id: offering.teacher_id || ""
    });
    setIsModalOpen(true);
  };

  const filteredOfferings = offerings.filter(o =>
    o.subject_name.toLowerCase().includes(filters.search.toLowerCase()) ||
    o.subject_code.toLowerCase().includes(filters.search.toLowerCase()) ||
    (o.teacher_name && o.teacher_name.toLowerCase().includes(filters.search.toLowerCase()))
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
      <Sidebar role="hod" activeSection="subjects" user={user} />

      <main className="ml-64 flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <header className="mb-8 flex justify-between items-end">
            <div>
              <h1 className="text-2xl font-bold font-display text-surface-100 flex items-center gap-2">
                <BookOpen className="text-primary-400" /> Subject Management
              </h1>
              <p className="text-surface-400 text-sm mt-1">Configure subjects, offerings per semester, and teacher assignments.</p>
            </div>

            <div className="flex gap-4">
              <select
                className="input-dark py-2 text-sm max-w-xs"
                value={selectedSessionId}
                onChange={(e) => setSelectedSessionId(e.target.value)}
              >
                <option value="">Filter by Session (All)</option>
                {sessions.map(s => <option key={s.id} value={s.id}>{s.name} ({s.year})</option>)}
              </select>
              <button
                onClick={() => { setModalType("offering"); setIsModalOpen(true); }}
                className="btn-primary py-2.5 px-4 text-sm flex items-center gap-2"
              >
                <Plus size={18} /> Add Subject Offering
              </button>
            </div>
          </header>

          {/* Filters */}
          <div className="glass-card p-6 mb-8 flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full">
              <label className="block text-xs font-semibold text-surface-500 uppercase mb-2">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-600" size={16} />
                <input
                  type="text"
                  placeholder="Subject or teacher..."
                  className="input-dark pl-9 text-sm"
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                />
              </div>
            </div>

            <div className="w-full md:w-48">
              <label className="block text-xs font-semibold text-surface-500 uppercase mb-2">Branch</label>
              <select
                className="input-dark text-sm"
                value={filters.branch}
                onChange={(e) => setFilters(prev => ({ ...prev, branch: e.target.value }))}
              >
                <option value="">All Branches</option>
                {branches.map(b => <option key={b.id} value={b.id}>{b.code}</option>)}
              </select>
            </div>

            <div className="w-full md:w-48">
              <label className="block text-xs font-semibold text-surface-500 uppercase mb-2">Semester</label>
              <select
                className="input-dark text-sm"
                value={filters.semester}
                onChange={(e) => setFilters(prev => ({ ...prev, semester: e.target.value }))}
              >
                <option value="">All Semesters</option>
                {semesters.map(s => <option key={s.id} value={s.id}>Sem {s.number}</option>)}
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-surface-700/50 bg-surface-800/30 text-surface-400">
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Subject Offering</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Academic Year</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Assigned Teacher</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/30">
                  {filteredOfferings.map(offering => (
                    <tr key={offering.id} className="hover:bg-surface-800/20 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-surface-800 flex items-center justify-center text-primary-400">
                            <Book size={18} />
                          </div>
                          <div>
                            <p className="text-surface-100 font-medium">{offering.subject_name}</p>
                            <p className="text-xs text-surface-500 font-mono">{offering.subject_code}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="text-surface-200">{offering.branch_code}</span>
                          <span className="text-xs text-accent-cyan font-medium">Semester {offering.semester_number}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {offering.teacher_name ? (
                          <div className="flex items-center gap-2 text-accent-emerald">
                            <UserCheck size={16} />
                            <span className="font-medium">{offering.teacher_name}</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-surface-500 italic">
                            <AlertCircle size={16} />
                            <span>Unassigned</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                            <button
                              onClick={() => openAssignModal(offering)}
                              className="p-2 rounded-lg bg-primary-500/10 text-primary-400 hover:bg-primary-500/20 transition-colors"
                              title="Change Teacher"
                            >
                              <Edit2 size={16} />
                            </button>
                          <button
                            onClick={() => handleDeleteOffering(offering.id)}
                            className="p-2 rounded-lg bg-surface-700/50 text-surface-400 hover:text-white transition-colors"
                            title="Delete Offering"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredOfferings.length === 0 && (
                <div className="p-12 text-center text-surface-500">
                  <p className="text-4xl mb-3">📚</p>
                  <p>No subject offerings found</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-950/80 backdrop-blur-sm animate-fade-in">
          <div className="glass-card w-full max-w-md shadow-2xl animate-scale-in">
            <div className="p-6 border-b border-surface-700/50 flex justify-between items-center">
              <h3 className="text-xl font-bold text-surface-100 font-display">
                {modalType === "offering" ? "Add Subject Offering" :
                  modalType === "assignment-edit" ? "Update Teacher" : "Assign Teacher"}
              </h3>
              <button
                onClick={() => { setIsModalOpen(false); resetForm(); }}
                className="text-surface-500 hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={modalType === "offering" ? handleCreateOffering : handleAssignTeacher} className="p-6 space-y-5">
              {modalType === "offering" ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-surface-400 mb-2">Subject</label>
                    <select
                      required
                      className="input-dark"
                      value={formData.subject_id}
                      onChange={(e) => setFormData(prev => ({ ...prev, subject_id: e.target.value }))}
                    >
                      <option value="">Select Subject</option>
                      {subjects.map(s => <option key={s.id} value={s.id}>{s.code} - {s.name}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-surface-400 mb-2">Branch</label>
                      <select
                        required
                        className="input-dark"
                        value={formData.branch_id}
                        onChange={(e) => setFormData(prev => ({ ...prev, branch_id: e.target.value }))}
                      >
                        <option value="">Select Branch</option>
                        {branches.map(b => <option key={b.id} value={b.id}>{b.code}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-400 mb-2">Semester</label>
                      <select
                        required
                        className="input-dark"
                        value={formData.semester_id}
                        onChange={(e) => setFormData(prev => ({ ...prev, semester_id: e.target.value }))}
                      >
                        <option value="">Select Semester</option>
                        {semesters.map(s => <option key={s.id} value={s.id}>Sem {s.number}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-surface-400 mb-2">Teacher</label>
                      <select
                        required
                        className="input-dark"
                        value={formData.teacher_id}
                        onChange={(e) => setFormData(prev => ({ ...prev, teacher_id: e.target.value }))}
                      >
                        <option value="">Select Teacher</option>
                        {teachers.map(t => <option key={t.id} value={t.id}>{t.name} ({t.department})</option>)}
                      </select>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-surface-800/50 p-4 rounded-xl border border-surface-700/50">
                    <p className="text-xs text-surface-500 uppercase font-bold tracking-wider mb-1">Target Subject Offering</p>
                    {offerings.filter(o => o.id === parseInt(formData.offering_id)).map(o => (
                      <p key={o.id} className="text-surface-100 font-medium">{o.subject_name} ({o.branch_code} Sem {o.semester_number})</p>
                    ))}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-400 mb-2">Assign Teacher</label>
                    <select
                      required
                      className="input-dark"
                      value={formData.teacher_id}
                      onChange={(e) => setFormData(prev => ({ ...prev, teacher_id: e.target.value }))}
                    >
                      <option value="">Select Teacher</option>
                      {teachers.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>
                </>
              )}

              <div className="pt-4 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-3 px-4 rounded-xl font-bold bg-surface-800 text-surface-400 hover:bg-surface-700 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={processing}
                  className="flex-[2] py-3 px-4 rounded-xl font-bold bg-primary-600 text-white hover:bg-primary-500 shadow-lg shadow-primary-900/20 transition-all flex items-center justify-center gap-2"
                >
                  {processing ? <Loader2 className="w-5 h-5 animate-spin" /> : "Confirm Action"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
