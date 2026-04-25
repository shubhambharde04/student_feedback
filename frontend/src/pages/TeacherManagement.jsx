import { useState, useEffect, useCallback } from "react";
import API from "../api";
import Sidebar from "../components/Sidebar";
import Toast from "../components/Toast";
import {
  Users, Plus, Search, Edit2, Trash2, UserPlus,
  AlertCircle, Loader2, Mail, Briefcase, Building2,
  Eye, EyeOff, CheckCircle2, XCircle
} from "lucide-react";

export default function TeacherManagement() {
  const [user, setUser] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create"); // "create" or "edit"
  const [editingTeacher, setEditingTeacher] = useState(null);
  const [showPassword, setShowPassword] = useState(false);

  const [filters, setFilters] = useState({
    search: "",
    department: "",
  });

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    department: "",
    designation: "",
  });

  const [formErrors, setFormErrors] = useState({});

  const fetchData = useCallback(async () => {
    try {
      const [teacherRes, profileRes, deptRes] = await Promise.all([
        API.get("users/teachers/"),
        API.get("auth/profile/"),
        API.get("departments/"),
      ]);

      setTeachers(teacherRes.data);
      setUser(profileRes.data.user);
      setDepartments(deptRes.data);
    } catch (err) {
      console.error("Error fetching teacher data:", err);
      if (err.response?.status !== 403) {
        setToast({ message: "Failed to load teacher data", type: "error" });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const validateForm = () => {
    const errors = {};
    if (!formData.first_name.trim()) errors.first_name = "First name is required";
    if (!formData.last_name.trim()) errors.last_name = "Last name is required";
    if (!formData.email.trim()) {
      errors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = "Invalid email format";
    }
    if (modalMode === "create") {
      if (!formData.password) {
        errors.password = "Password is required";
      } else if (formData.password.length < 6) {
        errors.password = "Password must be at least 6 characters";
      }
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateTeacher = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setProcessing(true);
    try {
      const payload = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim(),
        password: formData.password,
        designation: formData.designation.trim(),
      };
      if (formData.department) {
        payload.department = parseInt(formData.department);
      }

      const res = await API.post("users/teachers/", payload);
      setToast({
        message: `Teacher ${res.data.teacher?.full_name || "created"} added successfully!`,
        type: "success",
      });
      setIsModalOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      const errData = err.response?.data;
      if (errData?.email) {
        setFormErrors({ email: Array.isArray(errData.email) ? errData.email[0] : errData.email });
      } else {
        const msg = errData?.error || errData?.detail ||
          (typeof errData === "string" ? errData : "Failed to create teacher");
        setToast({ message: msg, type: "error" });
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleEditTeacher = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    if (!editingTeacher) return;

    setProcessing(true);
    try {
      const payload = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim(),
        designation: formData.designation.trim(),
      };
      if (formData.department) {
        payload.department = parseInt(formData.department);
      }

      await API.patch(`users/teachers/${editingTeacher.id}/`, payload);
      setToast({ message: "Teacher updated successfully!", type: "success" });
      setIsModalOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      const errData = err.response?.data;
      if (errData?.email) {
        setFormErrors({ email: Array.isArray(errData.email) ? errData.email[0] : errData.email });
      } else {
        setToast({ message: "Failed to update teacher", type: "error" });
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleDeleteTeacher = async (teacher) => {
    const confirmed = window.confirm(
      `Are you sure you want to deactivate ${teacher.full_name || teacher.username}?\n\nThis will prevent them from logging in but preserves their data.`
    );
    if (!confirmed) return;

    try {
      await API.delete(`users/teachers/${teacher.id}/`);
      setToast({ message: `Teacher ${teacher.full_name || teacher.username} deactivated`, type: "success" });
      fetchData();
    } catch (err) {
      setToast({ message: "Failed to deactivate teacher", type: "error" });
    }
  };

  const openCreateModal = () => {
    setModalMode("create");
    setEditingTeacher(null);
    resetForm();
    setIsModalOpen(true);
  };

  const openEditModal = (teacher) => {
    setModalMode("edit");
    setEditingTeacher(teacher);
    setFormData({
      first_name: teacher.first_name || "",
      last_name: teacher.last_name || "",
      email: teacher.email || "",
      password: "",
      department: teacher.department || "",
      designation: teacher.designation || "",
    });
    setFormErrors({});
    setIsModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      department: "",
      designation: "",
    });
    setFormErrors({});
    setShowPassword(false);
  };

  const filteredTeachers = teachers.filter((t) => {
    const matchesSearch =
      !filters.search ||
      (t.full_name || "").toLowerCase().includes(filters.search.toLowerCase()) ||
      (t.email || "").toLowerCase().includes(filters.search.toLowerCase()) ||
      (t.username || "").toLowerCase().includes(filters.search.toLowerCase()) ||
      (t.designation || "").toLowerCase().includes(filters.search.toLowerCase());

    const matchesDepartment =
      !filters.department || 
      String(t.department) === String(filters.department) ||
      (t.assigned_departments && t.assigned_departments.includes(parseInt(filters.department)));

    return matchesSearch && matchesDepartment;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar role="hod" activeSection="teacher-mgmt" user={user} />

      <main className="ml-64 flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <header className="mb-8 flex justify-between items-end">
            <div>
              <h1 className="text-2xl font-bold font-display text-surface-100 flex items-center gap-2">
                <Users className="text-primary-400" /> Teacher Management
              </h1>
              <p className="text-surface-400 text-sm mt-1">
                Add, edit, and manage teacher accounts. Teachers appear automatically in subject offering dropdowns.
              </p>
            </div>
            <button
              onClick={openCreateModal}
              className="btn-primary py-2.5 px-5 text-sm flex items-center gap-2"
              id="add-teacher-btn"
            >
              <UserPlus size={18} /> Add Teacher
            </button>
          </header>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 stagger">
            <div className="stat-card glass-card animate-fade-in" style={{ "--card-accent": "var(--color-primary-500)" }}>
              <p className="text-sm text-surface-400 mb-1">Total Teachers</p>
              <p className="text-3xl font-bold text-primary-400 font-display">{teachers.length}</p>
            </div>
            <div className="stat-card glass-card animate-fade-in" style={{ "--card-accent": "var(--color-accent-emerald)" }}>
              <p className="text-sm text-surface-400 mb-1">Active</p>
              <p className="text-3xl font-bold text-accent-emerald font-display">
                {teachers.filter((t) => t.is_active).length}
              </p>
            </div>
            <div className="stat-card glass-card animate-fade-in" style={{ "--card-accent": "var(--color-accent-cyan)" }}>
              <p className="text-sm text-surface-400 mb-1">Departments</p>
              <p className="text-3xl font-bold text-accent-cyan font-display">
                {new Set(teachers.map((t) => t.department).filter(Boolean)).size}
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="glass-card p-6 mb-8 flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full">
              <label className="block text-xs font-semibold text-surface-500 uppercase mb-2">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-600" size={16} />
                <input
                  type="text"
                  placeholder="Name, email, or designation..."
                  className="input-dark pl-9 text-sm"
                  value={filters.search}
                  onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
                  id="teacher-search"
                />
              </div>
            </div>
            <div className="w-full md:w-56">
              <label className="block text-xs font-semibold text-surface-500 uppercase mb-2">Department</label>
              <select
                className="input-dark text-sm"
                value={filters.department}
                onChange={(e) => setFilters((prev) => ({ ...prev, department: e.target.value }))}
                id="teacher-dept-filter"
              >
                <option value="">All Departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-surface-700/50 bg-surface-800/30 text-surface-400">
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Teacher</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Email</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Department</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Designation</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Subjects</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 font-medium uppercase tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/30">
                  {filteredTeachers.map((teacher) => (
                    <tr key={teacher.id} className="hover:bg-surface-800/20 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                            {(teacher.first_name || teacher.username || "T").charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-surface-100 font-medium">
                              {teacher.full_name || teacher.username}
                            </p>
                            <p className="text-xs text-surface-500 font-mono">@{teacher.username}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1.5 text-surface-300">
                          <Mail size={14} className="text-surface-500" />
                          <span className="text-sm">{teacher.email}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {teacher.department_name ? (
                          <div className="flex items-center gap-1.5 text-surface-200">
                            <Building2 size={14} className="text-accent-cyan" />
                            <span>{teacher.department_name}</span>
                          </div>
                        ) : (
                          <span className="text-surface-500 italic text-xs">Not assigned</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {teacher.designation ? (
                          <div className="flex items-center gap-1.5 text-surface-200">
                            <Briefcase size={14} className="text-accent-violet" />
                            <span>{teacher.designation}</span>
                          </div>
                        ) : (
                          <span className="text-surface-500 italic text-xs">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-surface-800 text-primary-400 font-bold text-sm">
                          {teacher.subject_count || 0}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {teacher.is_active ? (
                          <span className="badge badge-excellent">
                            <CheckCircle2 size={12} /> Active
                          </span>
                        ) : (
                          <span className="badge badge-poor">
                            <XCircle size={12} /> Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => openEditModal(teacher)}
                            className="p-2 rounded-lg bg-primary-500/10 text-primary-400 hover:bg-primary-500/20 transition-colors"
                            title="Edit Teacher"
                          >
                            <Edit2 size={16} />
                          </button>
                          {teacher.is_active && (
                            <button
                              onClick={() => handleDeleteTeacher(teacher)}
                              className="p-2 rounded-lg bg-surface-700/50 text-surface-400 hover:text-accent-rose hover:bg-accent-rose/10 transition-colors"
                              title="Deactivate Teacher"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredTeachers.length === 0 && (
                <div className="p-12 text-center text-surface-500">
                  <p className="text-4xl mb-3">👩‍🏫</p>
                  <p className="font-medium">No teachers found</p>
                  <p className="text-sm mt-1">
                    {teachers.length === 0
                      ? 'Click "Add Teacher" to create the first teacher account.'
                      : "Try adjusting your search or filter criteria."}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-950/80 backdrop-blur-sm animate-fade-in">
          <div className="glass-card w-full max-w-lg shadow-2xl animate-scale-in">
            <div className="p-6 border-b border-surface-700/50 flex justify-between items-center">
              <h3 className="text-xl font-bold text-surface-100 font-display flex items-center gap-2">
                {modalMode === "create" ? (
                  <>
                    <UserPlus size={22} className="text-primary-400" /> Add New Teacher
                  </>
                ) : (
                  <>
                    <Edit2 size={22} className="text-primary-400" /> Edit Teacher
                  </>
                )}
              </h3>
              <button
                onClick={() => { setIsModalOpen(false); resetForm(); }}
                className="text-surface-500 hover:text-white transition-colors text-xl"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={modalMode === "create" ? handleCreateTeacher : handleEditTeacher}
              className="p-6 space-y-5"
            >
              {/* Name Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-400 mb-2">
                    First Name <span className="text-accent-rose">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className={`input-dark ${formErrors.first_name ? "border-accent-rose" : ""}`}
                    value={formData.first_name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, first_name: e.target.value }))}
                    placeholder="John"
                    id="teacher-first-name"
                  />
                  {formErrors.first_name && (
                    <p className="text-xs text-accent-rose mt-1 flex items-center gap-1">
                      <AlertCircle size={12} /> {formErrors.first_name}
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-400 mb-2">
                    Last Name <span className="text-accent-rose">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className={`input-dark ${formErrors.last_name ? "border-accent-rose" : ""}`}
                    value={formData.last_name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, last_name: e.target.value }))}
                    placeholder="Doe"
                    id="teacher-last-name"
                  />
                  {formErrors.last_name && (
                    <p className="text-xs text-accent-rose mt-1 flex items-center gap-1">
                      <AlertCircle size={12} /> {formErrors.last_name}
                    </p>
                  )}
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">
                  Email <span className="text-accent-rose">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-600" size={16} />
                  <input
                    type="email"
                    required
                    className={`input-dark pl-9 ${formErrors.email ? "border-accent-rose" : ""}`}
                    value={formData.email}
                    onChange={(e) => {
                      setFormData((prev) => ({ ...prev, email: e.target.value }));
                      if (formErrors.email) setFormErrors((prev) => ({ ...prev, email: null }));
                    }}
                    placeholder="teacher@gpn.ac.in"
                    id="teacher-email"
                  />
                </div>
                {formErrors.email && (
                  <p className="text-xs text-accent-rose mt-1 flex items-center gap-1">
                    <AlertCircle size={12} /> {formErrors.email}
                  </p>
                )}
                {modalMode === "create" && (
                  <p className="text-xs text-surface-500 mt-1">
                    Username will be auto-generated from the email prefix
                  </p>
                )}
              </div>

              {/* Password (only for create) */}
              {modalMode === "create" && (
                <div>
                  <label className="block text-sm font-medium text-surface-400 mb-2">
                    Initial Password <span className="text-accent-rose">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      className={`input-dark pr-10 ${formErrors.password ? "border-accent-rose" : ""}`}
                      value={formData.password}
                      onChange={(e) => setFormData((prev) => ({ ...prev, password: e.target.value }))}
                      placeholder="Min 6 characters"
                      id="teacher-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300 transition-colors"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {formErrors.password && (
                    <p className="text-xs text-accent-rose mt-1 flex items-center gap-1">
                      <AlertCircle size={12} /> {formErrors.password}
                    </p>
                  )}
                  <p className="text-xs text-surface-500 mt-1">
                    Teacher will be prompted to change this on first login
                  </p>
                </div>
              )}

              {/* Department + Designation Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-400 mb-2">Department</label>
                  <select
                    className="input-dark"
                    value={formData.department}
                    onChange={(e) => setFormData((prev) => ({ ...prev, department: e.target.value }))}
                    id="teacher-department"
                  >
                    <option value="">Select Department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-400 mb-2">Designation</label>
                  <input
                    type="text"
                    className="input-dark"
                    value={formData.designation}
                    onChange={(e) => setFormData((prev) => ({ ...prev, designation: e.target.value }))}
                    placeholder="e.g., Lecturer"
                    id="teacher-designation"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 flex gap-3">
                <button
                  type="button"
                  onClick={() => { setIsModalOpen(false); resetForm(); }}
                  className="flex-1 py-3 px-4 rounded-xl font-bold bg-surface-800 text-surface-400 hover:bg-surface-700 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={processing}
                  className="flex-[2] py-3 px-4 rounded-xl font-bold bg-primary-600 text-white hover:bg-primary-500 shadow-lg shadow-primary-900/20 transition-all flex items-center justify-center gap-2"
                  id="teacher-submit-btn"
                >
                  {processing ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : modalMode === "create" ? (
                    <>
                      <UserPlus size={18} /> Add Teacher
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={18} /> Save Changes
                    </>
                  )}
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
