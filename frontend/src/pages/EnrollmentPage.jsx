import { useState, useEffect, useCallback } from "react";
import API from "../api";
import Toast from "../components/Toast";
import Sidebar from "../components/Sidebar";

export default function EnrollmentPage() {
  const [user, setUser] = useState(null);
  const [formData, setFormData] = useState({ subjects: [], students: [] });
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);
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
            📋 Subject Enrollments
          </h1>
          <p className="text-surface-500 text-sm mt-1">
            Students are automatically enrolled in these subjects based on their semester assignment from the Excel upload.
          </p>
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
                      Date
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
                      <td className="px-6 py-4 text-surface-500 text-xs">
                        {new Date(e.created_at).toLocaleDateString("en-IN", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
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
