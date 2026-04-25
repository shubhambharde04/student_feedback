import { useState, useEffect, useCallback } from "react";
import API from "../api";
import Sidebar from "../components/Sidebar";
import Toast from "../components/Toast";
import { 
  Building2, Plus, Edit2, Trash2, GitBranch, 
  Search, AlertCircle, Loader2, CheckCircle2, 
  ChevronRight, ChevronDown, Layers
} from "lucide-react";

export default function DepartmentManagement() {
  const [user, setUser] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);
  
  const [isDeptModalOpen, setIsDeptModalOpen] = useState(false);
  const [isBranchModalOpen, setIsBranchModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  
  const [editingItem, setEditingItem] = useState(null);
  const [expandedDepts, setExpandedDepts] = useState(new Set());

  const [deptFormData, setDeptFormData] = useState({ name: "" });
  const [branchFormData, setBranchFormData] = useState({ 
    name: "", 
    code: "", 
    department: "" 
  });

  const fetchData = useCallback(async () => {
    try {
      const [deptRes, profileRes] = await Promise.all([
        API.get("departments/"),
        API.get("auth/profile/")
      ]);
      
      // For each department, fetch its branches
      const deptsWithBranches = await Promise.all(
        deptRes.data.map(async (dept) => {
          try {
            const branchRes = await API.get(`branches/?department=${dept.id}`);
            return { ...dept, branches: branchRes.data };
          } catch (e) {
            return { ...dept, branches: [] };
          }
        })
      );

      setDepartments(deptsWithBranches);
      setUser(profileRes.data.user);
      
      // Auto-expand HOD's department
      if (profileRes.data.user.role === 'hod' && profileRes.data.user.department) {
        setExpandedDepts(new Set([profileRes.data.user.department]));
      }
    } catch (err) {
      console.error("Error fetching academic data:", err);
      setToast({ message: "Failed to load academic structure", type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleDept = (id) => {
    const newExpanded = new Set(expandedDepts);
    if (newExpanded.has(id)) newExpanded.delete(id);
    else newExpanded.add(id);
    setExpandedDepts(newExpanded);
  };

  const handleDeptSubmit = async (e) => {
    e.preventDefault();
    setProcessing(true);
    try {
      if (modalMode === "create") {
        await API.post("departments/", deptFormData);
        setToast({ message: "Department created successfully", type: "success" });
      } else {
        await API.patch(`departments/${editingItem.id}/`, deptFormData);
        setToast({ message: "Department updated successfully", type: "success" });
      }
      setIsDeptModalOpen(false);
      fetchData();
    } catch (err) {
      setToast({ message: "Failed to save department", type: "error" });
    } finally {
      setProcessing(false);
    }
  };

  const handleBranchSubmit = async (e) => {
    e.preventDefault();
    setProcessing(true);
    try {
      if (modalMode === "create") {
        await API.post("branches/", branchFormData);
        setToast({ message: "Branch created successfully", type: "success" });
      } else {
        await API.patch(`branches/${editingItem.id}/`, branchFormData);
        setToast({ message: "Branch updated successfully", type: "success" });
      }
      setIsBranchModalOpen(false);
      fetchData();
    } catch (err) {
      setToast({ message: "Failed to save branch", type: "error" });
    } finally {
      setProcessing(false);
    }
  };

  const handleDeleteDept = async (dept) => {
    if (!window.confirm(`Are you sure you want to delete the department "${dept.name}"? This action cannot be undone.`)) return;
    try {
      await API.delete(`departments/${dept.id}/`);
      setToast({ message: "Department deleted successfully", type: "success" });
      fetchData();
    } catch (err) {
      setToast({ message: "Failed to delete department. It may be linked to existing data.", type: "error" });
    }
  };

  const handleDeleteBranch = async (branch) => {
    if (!window.confirm(`Are you sure you want to delete the branch "${branch.name}"? This action cannot be undone.`)) return;
    try {
      await API.delete(`branches/${branch.id}/`);
      setToast({ message: "Branch deleted successfully", type: "success" });
      fetchData();
    } catch (err) {
      setToast({ message: "Failed to delete branch. It may be linked to existing data.", type: "error" });
    }
  };

  const openCreateDept = () => {
    setModalMode("create");
    setDeptFormData({ name: "" });
    setIsDeptModalOpen(true);
  };

  const openEditDept = (dept) => {
    setModalMode("edit");
    setEditingItem(dept);
    setDeptFormData({ name: dept.name });
    setIsDeptModalOpen(true);
  };

  const openCreateBranch = (deptId) => {
    setModalMode("create");
    setBranchFormData({ name: "", code: "", department: deptId || "" });
    setIsBranchModalOpen(true);
  };

  const openEditBranch = (branch) => {
    setModalMode("edit");
    setEditingItem(branch);
    setBranchFormData({ 
      name: branch.name, 
      code: branch.code, 
      department: branch.department 
    });
    setIsBranchModalOpen(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar role="hod" activeSection="departments" user={user} />

      <main className="ml-64 flex-1 p-8">
        <div className="max-w-5xl mx-auto">
          <header className="mb-8 flex justify-between items-end">
            <div>
              <h1 className="text-2xl font-bold font-display text-surface-100 flex items-center gap-2">
                <Layers className="text-primary-400" /> Academic Structure
              </h1>
              <p className="text-surface-400 text-sm mt-1">
                Manage Departments and their respective Branches.
              </p>
            </div>
            {(user?.role === 'admin' || user?.role === 'hod') && (
              <button onClick={openCreateDept} className="btn-primary py-2.5 px-5 text-sm flex items-center gap-2">
                <Plus size={18} /> New Department
              </button>
            )}
          </header>

          <div className="space-y-4">
            {departments.map((dept) => (
              <div key={dept.id} className="glass-card overflow-hidden">
                <div 
                  className={`p-5 flex items-center justify-between cursor-pointer transition-colors ${expandedDepts.has(dept.id) ? 'bg-surface-800/40' : 'hover:bg-surface-800/20'}`}
                  onClick={() => toggleDept(dept.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-lg bg-primary-500/10 text-primary-400">
                      <Building2 size={24} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-surface-100">{dept.name}</h3>
                      <p className="text-xs text-surface-500">{dept.branches?.length || 0} Branches</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {(user?.role === 'admin' || user?.role === 'hod') && (
                      <>
                        <button 
                          onClick={(e) => { e.stopPropagation(); openEditDept(dept); }}
                          className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-primary-400 transition-colors"
                          title="Edit Department"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleDeleteDept(dept); }}
                          className="p-2 rounded-lg hover:bg-accent-rose/20 text-surface-400 hover:text-accent-rose transition-colors"
                          title="Delete Department"
                        >
                          <Trash2 size={16} />
                        </button>
                      </>
                    )}
                    {expandedDepts.has(dept.id) ? <ChevronDown size={20} className="text-surface-500" /> : <ChevronRight size={20} className="text-surface-500" />}
                  </div>
                </div>

                {expandedDepts.has(dept.id) && (
                  <div className="p-5 bg-surface-900/20 border-t border-surface-700/50 animate-fade-in">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="text-xs font-bold text-surface-500 uppercase tracking-widest flex items-center gap-2">
                        <GitBranch size={14} /> Branches in {dept.name}
                      </h4>
                      <button 
                        onClick={() => openCreateBranch(dept.id)}
                        className="text-xs font-bold text-primary-400 hover:text-primary-300 flex items-center gap-1 transition-colors"
                      >
                        <Plus size={14} /> Add Branch
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {dept.branches?.map((branch) => (
                        <div key={branch.id} className="p-4 rounded-xl bg-surface-800/40 border border-surface-700/30 flex items-center justify-between group">
                          <div>
                            <p className="text-sm font-bold text-surface-200">{branch.name}</p>
                            <p className="text-xs text-surface-500 font-mono">{branch.code}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <button 
                              onClick={() => openEditBranch(branch)}
                              className="p-2 rounded-lg opacity-0 group-hover:opacity-100 bg-surface-700 text-surface-400 hover:text-primary-400 transition-all"
                              title="Edit Branch"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button 
                              onClick={() => handleDeleteBranch(branch)}
                              className="p-2 rounded-lg opacity-0 group-hover:opacity-100 bg-surface-700 text-surface-400 hover:text-accent-rose transition-all"
                              title="Delete Branch"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                      {(!dept.branches || dept.branches.length === 0) && (
                        <div className="col-span-2 py-8 text-center text-surface-600 italic text-sm">
                          No branches defined for this department.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Dept Modal */}
      {isDeptModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-950/80 backdrop-blur-sm">
          <div className="glass-card w-full max-w-md shadow-2xl animate-scale-in">
            <div className="p-6 border-b border-surface-700/50 flex justify-between items-center">
              <h3 className="text-xl font-bold text-surface-100 flex items-center gap-2">
                {modalMode === "create" ? "Create Department" : "Edit Department"}
              </h3>
              <button onClick={() => setIsDeptModalOpen(false)} className="text-surface-500 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleDeptSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">Department Name</label>
                <input 
                  type="text" required className="input-dark" 
                  value={deptFormData.name}
                  onChange={(e) => setDeptFormData({ name: e.target.value })}
                  placeholder="e.g. Computer Engineering"
                />
              </div>
              <button type="submit" disabled={processing} className="w-full btn-primary py-3 font-bold flex items-center justify-center gap-2">
                {processing ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 size={18} />}
                {modalMode === "create" ? "Create Department" : "Save Changes"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Branch Modal */}
      {isBranchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-950/80 backdrop-blur-sm">
          <div className="glass-card w-full max-w-md shadow-2xl animate-scale-in">
            <div className="p-6 border-b border-surface-700/50 flex justify-between items-center">
              <h3 className="text-xl font-bold text-surface-100 flex items-center gap-2">
                {modalMode === "create" ? "Create Branch" : "Edit Branch"}
              </h3>
              <button onClick={() => setIsBranchModalOpen(false)} className="text-surface-500 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleBranchSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">Branch Name</label>
                <input 
                  type="text" required className="input-dark" 
                  value={branchFormData.name}
                  onChange={(e) => setBranchFormData({...branchFormData, name: e.target.value})}
                  placeholder="e.g. Information Technology"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">Branch Code</label>
                <input 
                  type="text" required className="input-dark font-mono uppercase" 
                  value={branchFormData.code}
                  onChange={(e) => setBranchFormData({...branchFormData, code: e.target.value.toUpperCase()})}
                  placeholder="e.g. IT"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">Department</label>
                <select 
                  className="input-dark" required
                  value={branchFormData.department}
                  onChange={(e) => setBranchFormData({...branchFormData, department: e.target.value})}
                >
                  <option value="">Select Department</option>
                  {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <button type="submit" disabled={processing} className="w-full btn-primary py-3 font-bold flex items-center justify-center gap-2">
                {processing ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 size={18} />}
                {modalMode === "create" ? "Create Branch" : "Save Changes"}
              </button>
            </form>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
