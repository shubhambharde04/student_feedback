import { useState, useEffect, useCallback } from "react";
import API from "../api";
import SubjectDropdown from "../components/SubjectDropdown";
import StudentMultiSelect from "../components/StudentMultiSelect";
import Toast from "../components/Toast";
import Sidebar from "../components/Sidebar";

export default function EnrollmentPage() {
  const [user, setUser] = useState(null);
  const [formData, setFormData] = useState({ subjects: [], students: [] });
  const [enrollments, setEnrollments] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);
  const [toast, setToast] = useState(null);
  const [activeSection, setActiveSection] = useState("enrollments");
  const [filterSubject, setFilterSubject] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [profileRes, formRes, enrollRes] = await Promise.all([
        API.get("auth/profile/"),
        API.get("enrollments/form-data/"),
        API.get("enrollments/"),
      ]);
      setUser(profileRes.data.user);
      setFormData(formRes.data);
      setEnrollments(enrollRes.data);
    } catch (err) {
      console.error("Error fetching enrollment data:", err);
      setToast({ message: "Failed to load enrollment data", type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const currentSubject = formData.subjects.find((s) => s.id === selectedSubject);

  const handleEnroll = async () => {
    if (!selectedSubject || selectedStudents.length === 0) {
      setToast({ message: "Please select a subject and at least one student", type: "warning" });
      return;
    }

    setEnrolling(true);
    try {
      const res = await API.post("enrollments/bulk-enroll/", {
        subject: selectedSubject,
        students: selectedStudents,
      });

      const { created_count, error_count, errors } = res.data;

      if (created_count > 0) {
        setToast({
          message: `Successfully enrolled ${created_count} student${created_count > 1 ? "s" : ""}${
            error_count > 0 ? ` (${error_count} skipped)` : ""
          }`,
          type: error_count > 0 ? "warning" : "success",
        });
      } else if (error_count > 0) {
        const firstError = errors[0]?.error || "Unknown error";
        setToast({ message: `Enrollment failed: ${firstError}`, type: "error" });
      }

      setSelectedStudents([]);
      // Refresh enrollments
      const enrollRes = await API.get("enrollments/");
      setEnrollments(enrollRes.data);
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.errors?.[0]?.error || "Enrollment failed";
      setToast({ message: msg, type: "error" });
    } finally {
      setEnrolling(false);
    }
  };

  const handleRemove = async (id) => {
    try {
      await API.delete(`enrollments/${id}/`);
      setEnrollments((prev) => prev.filter((e) => e.id !== id));
      setToast({ message: "Enrollment removed", type: "success" });
    } catch (err) {
      setToast({ message: "Failed to remove enrollment", type: "error" });
    }
  };

  const filteredEnrollments = filterSubject
    ? enrollments.filter((e) => e.subject === parseInt(filterSubject))
    : enrollments;

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar
        role="hod"
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        user={user}
      />

      <main className="ml-64 flex-1 p-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold font-display text-surface-100">
            📋 Enrollment Management
          </h1>
          <p className="text-surface-500 text-sm mt-1">
            Assign students to subjects. Only enrolled students can view and give feedback.
          </p>
        </div>

        {/* Enrollment Form */}
        <div className="glass-card p-6 mb-8 animate-fade-in">
          <h2 className="text-lg font-semibold font-display text-surface-100 mb-5">
            Assign Students
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Subject */}
            <SubjectDropdown
              subjects={formData.subjects}
              value={selectedSubject}
              onChange={(id) => {
                setSelectedSubject(id);
                setSelectedStudents([]);
              }}
            />

            {/* Right: Students */}
            <StudentMultiSelect
              students={formData.students}
              selectedIds={selectedStudents}
              onChange={setSelectedStudents}
              selectedSubject={currentSubject}
            />
          </div>

          {/* Assign Button */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleEnroll}
              disabled={enrolling || !selectedSubject || selectedStudents.length === 0}
              className="btn-success px-8 py-3 text-sm font-medium flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {enrolling ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Enrolling…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                    />
                  </svg>
                  Assign {selectedStudents.length > 0 ? `(${selectedStudents.length})` : ""}
                </>
              )}
            </button>
          </div>
        </div>

        {/* Enrollment Table */}
        <div className="glass-card overflow-hidden animate-fade-in">
          <div className="px-6 py-4 border-b border-surface-700/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold font-display text-surface-100">
                Current Enrollments
              </h2>
              <p className="text-xs text-surface-500">
                {filteredEnrollments.length} enrollment{filteredEnrollments.length !== 1 ? "s" : ""}
              </p>
            </div>
            <select
              value={filterSubject}
              onChange={(e) => setFilterSubject(e.target.value)}
              className="input-dark text-sm w-auto min-w-[200px]"
            >
              <option value="">All Subjects</option>
              {formData.subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>

          {filteredEnrollments.length === 0 ? (
            <div className="p-12 text-center text-surface-500">
              <p className="text-4xl mb-3">📭</p>
              <p>No enrollments found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-surface-700/50 bg-surface-800/30">
                    <th className="px-6 py-3 text-xs font-medium text-surface-400 uppercase tracking-wider">
                      Student
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-surface-400 uppercase tracking-wider">
                      Subject
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-surface-400 uppercase tracking-wider">
                      Assigned By
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-surface-400 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-xs font-medium text-surface-400 uppercase tracking-wider text-right">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/30">
                  {filteredEnrollments.map((e) => (
                    <tr
                      key={e.id}
                      className="hover:bg-surface-800/30 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <p className="text-surface-200 font-medium">{e.student_name}</p>
                        <p className="text-xs text-surface-500">{e.student_enrollment_no}</p>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-surface-200">{e.subject_name}</p>
                        <p className="text-xs text-surface-500">{e.subject_code}</p>
                      </td>
                      <td className="px-6 py-4 text-surface-400">
                        {e.assigned_by_name || "—"}
                      </td>
                      <td className="px-6 py-4 text-surface-500 text-xs">
                        {new Date(e.created_at).toLocaleDateString("en-IN", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleRemove(e.id)}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-accent-rose/10 text-accent-rose border border-accent-rose/20 hover:bg-accent-rose/20 transition-colors"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
