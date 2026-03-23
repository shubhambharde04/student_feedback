import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import API from "../api";
import SubjectRadarChart from "../components/SubjectRadarChart";

export default function TeacherProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [teacher, setTeacher] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailStatus, setEmailStatus] = useState("");

  useEffect(() => {
    const fetchTeacherProfile = async () => {
      try {
        console.log('Fetching teacher profile for ID:', id);
        console.log('Current user from localStorage:', JSON.parse(localStorage.getItem('user') || '{}'));
        
        const response = await API.get(`hod/teacher/${id}/`);
        console.log('Teacher profile response:', response.data);
        setTeacher(response.data);
      } catch (err) {
        console.error('Failed to load teacher profile:', err);
        console.error('Error response:', err.response);
        console.error('Error status:', err.response?.status);
        console.error('Error data:', err.response?.data);
        setError(`Failed to load teacher profile: ${err.response?.data?.error || err.message}`);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchTeacherProfile();
    }
  }, [id]);

  const handleSendReport = async () => {
    if (!window.confirm("Send performance report to this teacher's email?")) return;
    setSendingEmail(true);
    setEmailStatus("");
    try {
      await API.post("hod/send-report/", { teacher_id: id });
      setEmailStatus({ type: "success", msg: "Email report sent successfully!" });
    } catch (err) {
      setEmailStatus({ type: "error", msg: "Failed to send email report." });
    } finally {
      setSendingEmail(false);
      setTimeout(() => setEmailStatus(""), 5000);
    }
  };

  const generatePDFReport = async () => {
    // This connects to the backend PDF generator View
    try {
      const response = await API.get(`hod/export-report/?type=teacher&id=${id}&format=pdf`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Teacher_Report_${teacher.teacher.name.replace(/\s+/g, '_')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert("Failed to generate PDF report.");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !teacher) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="glass-card p-8 text-center max-w-sm">
          <div className="text-4xl mb-4">⚠️</div>
          <p className="text-surface-100 font-bold mb-4">{error || "Teacher not found"}</p>
          <button onClick={() => navigate("/hod-dashboard")} className="btn-secondary">
            Back to Dashboard
          </button>
          {error && (
            <div className="mt-4 p-3 bg-accent-rose/10 border border-accent-rose/20 rounded-lg">
              <p className="text-xs text-accent-rose">Error details: {error}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  const performanceClass = 
    teacher.overall_performance === "Excellent" ? "badge-excellent" :
    teacher.overall_performance === "Good" ? "badge-good" :
    teacher.overall_performance === "Average" ? "badge-average" :
    teacher.overall_performance === "Poor" ? "badge-poor" : "badge-neutral";

  return (
    <div className="min-h-screen bg-mesh pb-12">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-surface-900/80 backdrop-blur-xl border-b border-surface-700/50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate("/hod-dashboard")}
            className="text-surface-400 hover:text-surface-200 flex items-center gap-2 text-sm transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to HOD Dashboard
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 mt-8 animate-fade-in">
        {emailStatus && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${emailStatus.type === "success" ? "bg-accent-emerald/10 border border-accent-emerald/20 text-accent-emerald" : "bg-accent-rose/10 border border-accent-rose/20 text-accent-rose"}`}>
            <span>{emailStatus.type === "success" ? "✅" : "❌"}</span>
            <span className="font-medium">{emailStatus.msg}</span>
          </div>
        )}

        {/* Profile Card */}
        <div className="glass-card p-8 mb-8 flex flex-col md:flex-row gap-8 items-start md:items-center">
          <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-violet flex items-center justify-center text-4xl text-white font-bold flex-shrink-0 shadow-lg shadow-primary-500/20">
            {teacher.teacher.name.charAt(0)}
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-surface-100 font-display">{teacher.teacher.name}</h1>
            <p className="text-surface-400 mt-1 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              {teacher.teacher.email}
            </p>
            <div className="flex flex-wrap gap-4 mt-4">
              <div className="bg-surface-800/50 px-4 py-2 rounded-lg border border-surface-700/50">
                <p className="text-xs text-surface-500 mb-0.5">Overall Avg</p>
                <p className="text-lg font-bold text-primary-400">{teacher.overall_avg} ⭐</p>
              </div>
              <div className="bg-surface-800/50 px-4 py-2 rounded-lg border border-surface-700/50">
                <p className="text-xs text-surface-500 mb-0.5">Total Feedback</p>
                <p className="text-lg font-bold text-surface-100">{teacher.total_feedback}</p>
              </div>
              <div className="bg-surface-800/50 px-4 py-2 rounded-lg border border-surface-700/50 flex items-center">
                <span className={`badge ${performanceClass} text-sm py-1`}>{teacher.overall_performance}</span>
              </div>
            </div>
          </div>
          
          <div className="w-full md:w-auto flex flex-col sm:flex-row md:flex-col gap-3">
            <button 
              onClick={handleSendReport} 
              disabled={sendingEmail}
              className="btn-success flex items-center justify-center gap-2 whitespace-nowrap"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              {sendingEmail ? "Sending..." : "Email Report"}
            </button>
            <button 
              onClick={generatePDFReport}
              className="btn-primary flex items-center justify-center gap-2 whitespace-nowrap"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              PDF Report
            </button>
          </div>
        </div>

        <h2 className="text-xl font-bold text-surface-100 font-display mb-6">Subject Breakdown</h2>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 stagger">
          {teacher.subjects.map((sub) => {
             const radarData = [
              { category: 'Punctuality', rating: sub.avg_punctuality },
              { category: 'Teaching', rating: sub.avg_teaching },
              { category: 'Clarity', rating: sub.avg_clarity },
              { category: 'Interaction', rating: sub.avg_interaction },
              { category: 'Behavior', rating: sub.avg_behavior },
            ];

            return (
              <div key={sub.subject_id} className="glass-card p-6 flex flex-col">
                <div className="flex justify-between items-start mb-4 pb-4 border-b border-surface-700/50">
                  <div className="min-w-0 pr-4">
                    <h3 className="text-lg font-bold text-surface-100 font-display truncate">
                      {sub.subject_name}
                    </h3>
                    <p className="text-sm text-surface-400">{sub.subject_code}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xl font-bold text-primary-400">
                      {sub.avg_overall} <span className="text-sm text-surface-500 font-normal">/ 5.0</span>
                    </div>
                    <p className="text-xs text-surface-500 mt-0.5">{sub.feedback_count} reviews</p>
                  </div>
                </div>

                <div className="flex-1 min-h-[250px] mb-4">
                  {sub.feedback_count > 0 ? (
                    <SubjectRadarChart data={radarData} />
                  ) : (
                    <div className="h-full flex items-center justify-center text-surface-500">
                      No feedback data yet
                    </div>
                  )}
                </div>

                {/* Sentiment Summary */}
                <div className="mt-auto grid grid-cols-3 gap-2 pt-4 border-t border-surface-700/50">
                  <div className="bg-surface-800/50 rounded-lg p-2 text-center">
                    <div className="text-sm text-surface-500 mb-1">Passionate (Pos)</div>
                    <div className="text-lg font-bold text-accent-emerald flex items-center justify-center gap-1">
                      <span>😊</span> {sub.sentiment_summary?.positive || 0}
                    </div>
                  </div>
                  <div className="bg-surface-800/50 rounded-lg p-2 text-center">
                    <div className="text-sm text-surface-500 mb-1">Neutral</div>
                    <div className="text-lg font-bold text-surface-400 flex items-center justify-center gap-1">
                      <span>😐</span> {sub.sentiment_summary?.neutral || 0}
                    </div>
                  </div>
                  <div className="bg-surface-800/50 rounded-lg p-2 text-center">
                    <div className="text-sm text-surface-500 mb-1">Critical (Neg)</div>
                    <div className="text-lg font-bold text-accent-rose flex items-center justify-center gap-1">
                      <span>😞</span> {sub.sentiment_summary?.negative || 0}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {teacher.subjects.length === 0 && (
          <div className="glass-card p-12 text-center text-surface-500">
            This teacher is not assigned to any subjects yet.
          </div>
        )}
      </main>
    </div>
  );
}
