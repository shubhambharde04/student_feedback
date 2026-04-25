import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";

export default function StudentDashboard() {
  const [subjects, setSubjects] = useState([]);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [activeForm, setActiveForm] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedbackSubject, setFeedbackSubject] = useState(null);
  const navigate = useNavigate();
  const hasFetched = useRef(false);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    return document.documentElement.classList.contains("dark");
  });

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark") {
      document.documentElement.classList.add("dark");
      setIsDarkMode(true);
    } else if (savedTheme === "light") {
      document.documentElement.classList.remove("dark");
      setIsDarkMode(false);
    }
  }, []);

  const toggleTheme = () => {
    if (isDarkMode) {
      document.documentElement.classList.remove("dark");
      setIsDarkMode(false);
      localStorage.setItem("theme", "light");
    } else {
      document.documentElement.classList.add("dark");
      setIsDarkMode(true);
      localStorage.setItem("theme", "dark");
    }
  };

  const fetchData = useCallback(async () => {
    try {
      const [formRes, profileRes] = await Promise.allSettled([
        API.get("feedback/active-form/"),
        API.get("auth/profile/"),
      ]);

      if (formRes.status === 'fulfilled') {
        const data = formRes.value.data;
        setSubjects(data.subjects || []);
        setSessionInfo(data.session || null);
        setActiveForm(data.form || null);
      } else {
        console.error("Failed to load active form:", formRes.reason);
        setSubjects([]);
        if (formRes.reason?.response?.status === 404) {
          setError(formRes.reason.response.data.error || "No active feedback session available.");
        } else if (formRes.reason?.response?.status === 403) {
          setError(formRes.reason.response.data.error || "Feedback submission is closed.");
        } else {
          setError("Failed to load feedback form.");
        }
      }

      if (profileRes.status === 'fulfilled') {
        setUser(profileRes.value?.data?.user ?? null);
      } else {
        if (profileRes.reason?.response?.status === 401) {
          navigate("/");
          return;
        }
      }
    } catch (err) {
      console.error("Error fetching data:", err);
      setError("Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;
    fetchData();
  }, [fetchData]);

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) await API.post("auth/logout/", { refresh: refreshToken });
    } catch (e) { /* ignore */ }
    localStorage.clear();
    navigate("/");
  };

  const handleFeedbackSuccess = () => {
    setFeedbackSubject(null);
    setLoading(true);
    hasFetched.current = false;
    fetchData();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-[#105b96] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-surface-500 text-sm font-medium">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  const totalSubjects = subjects?.length ?? 0;
  const submitted = subjects?.filter((s) => s?.feedback_submitted)?.length ?? 0;
  const pending = totalSubjects - submitted;

  return (
    <div className="min-h-screen flex flex-col bg-surface-50">
      <header className="gpn-header sticky top-0 z-30 shadow-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
          <div className="gpn-logo-circle animate-float">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-bold text-white font-display leading-tight">
              Government Polytechnic, Nagpur
            </h1>
            <p className="text-xs text-amber-300 font-semibold">Online Academic Feedback System</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button 
              onClick={toggleTheme} 
              className="p-2.5 rounded-xl bg-white/10 text-white hover:bg-white/20 transition-all border border-white/20 hover:border-white/40 shadow-inner"
              title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {isDarkMode ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" strokeWidth="2"/><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
              )}
            </button>
            <button onClick={() => navigate("/change-password")} className="btn-secondary text-xs flex items-center gap-1.5" title="Change Password">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
              <span className="hidden sm:inline">Change Password</span>
            </button>
            <button onClick={handleLogout} className="btn-danger text-xs flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Logout
            </button>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b border-surface-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-1">
            <span className="px-4 py-3 text-sm font-semibold text-[#105b96] border-b-2 border-[#105b96]">Dashboard</span>
          </div>
          <p className="text-xs text-surface-500 font-medium">Welcome, {user?.first_name || user?.username || 'Student'} 👋</p>
        </div>
      </nav>

      <main className="flex-1">
        <div className="max-w-6xl mx-auto px-6 py-8">
          {error ? (
            <div className="bg-white rounded-xl shadow-sm border border-surface-200 p-8 text-center max-w-md mx-auto">
              <p className="text-accent-rose text-lg font-medium mb-2">⚠️ Cannot Submit Feedback</p>
              <p className="text-surface-600 mb-4">{error}</p>
              <button onClick={() => { setError(null); setLoading(true); hasFetched.current = false; fetchData(); }} className="btn-primary shadow-sm hover:shadow">Refresh Page</button>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8 animate-fade-in stagger">
                <div className="bg-white rounded-xl shadow-sm border border-surface-200 p-6 border-t-4 border-t-primary-500">
                  <p className="text-sm text-surface-500 mb-1 font-semibold uppercase tracking-wide">Total Subjects</p>
                  <p className="text-3xl font-bold text-primary-600 font-display">{totalSubjects}</p>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-surface-200 p-6 border-t-4 border-t-accent-emerald">
                  <p className="text-sm text-surface-500 mb-1 font-semibold uppercase tracking-wide">Feedback Given</p>
                  <p className="text-3xl font-bold text-accent-emerald font-display">{submitted}</p>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-surface-200 p-6 border-t-4 border-t-accent-amber">
                  <p className="text-sm text-surface-500 mb-1 font-semibold uppercase tracking-wide">Pending</p>
                  <p className="text-3xl font-bold text-accent-amber font-display">{pending}</p>
                </div>
              </div>

              <div id="subjects-section" className="bg-white rounded-xl shadow-sm border border-surface-200 overflow-hidden mb-8 animate-fade-in" style={{ animationDelay: '400ms' }}>
                <div className="px-6 py-4 border-b border-surface-200 bg-surface-50 flex justify-between items-center">
                  <h2 className="text-lg font-bold text-[#105b96]">Your Subjects</h2>
                  {sessionInfo && <span className="text-xs font-semibold px-2.5 py-1 bg-primary-100 text-primary-700 rounded-full">{sessionInfo.name}</span>}
                </div>
                <div className="p-6 bg-surface-50/50">
                  {(!subjects || subjects.length === 0) ? (
                    <div className="text-center py-10 bg-white rounded-lg border border-surface-200 border-dashed">
                      <p className="text-surface-500 font-medium">No subjects assigned for this session.</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {subjects.map((sub) => (
                        <div key={sub?.id || Math.random()} className="border border-surface-200 rounded-lg p-5 flex justify-between items-center hover:shadow-md transition-shadow bg-white">
                          <div className="min-w-0">
                            <h4 className="font-bold text-surface-800">{sub?.subject_name || 'Unknown Subject'}</h4>
                            <p className="text-sm text-surface-500 mt-0.5 font-medium">
                              <span className="text-primary-600">{sub?.subject_code || ''}</span> · {sub?.teacher_name || 'No teacher assigned'}
                            </p>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            {sub?.feedback_submitted ? (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-50 text-emerald-700 text-sm font-bold border border-emerald-200">✅ Submitted</span>
                            ) : (
                              <button onClick={() => setFeedbackSubject(sub)} className="btn-primary text-sm shadow-sm hover:shadow">Give Feedback</button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      <footer className="bg-white text-surface-500 py-6 text-center text-sm border-t border-surface-200">
        <p>Copyright © 2024-25. Government Polytechnic, Nagpur. All rights reserved.</p>
      </footer>

      {feedbackSubject && activeForm && (
        <FeedbackModal
          subject={feedbackSubject}
          form={activeForm}
          session={sessionInfo}
          onClose={() => setFeedbackSubject(null)}
          onSuccess={handleFeedbackSuccess}
        />
      )}
    </div>
  );
}

function FeedbackModal({ subject, form, session, onClose, onSuccess }) {
  const [responses, setResponses] = useState({});
  const [hoverRatings, setHoverRatings] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [overallRemark, setOverallRemark] = useState("");

  const questions = form?.questions || [];
  
  // Calculate if all required questions are answered
  const requiredQuestions = questions.filter(q => q.is_required);
  const allRequiredAnswered = requiredQuestions.every(q => {
    const res = responses[q.id];
    if (!res) return false;
    if (q.question_type === 'RATING') return res.rating > 0;
    if (q.question_type === 'TEXT') return res.text_response?.trim().length > 0;
    return true;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!allRequiredAnswered) { setError("Please answer all required questions"); return; }
    
    setLoading(true);
    setError("");
    
    const formattedResponses = Object.entries(responses).map(([question_id, res]) => ({
      question_id: parseInt(question_id),
      ...res
    }));

    try {
      await API.post("feedback/submit/", {
        offering_id: subject?.id,
        responses: formattedResponses,
        overall_remark: overallRemark.trim()
      });
      setSubmitted(true);
      setTimeout(() => onSuccess(), 1500);
    } catch (err) {
      console.error("Feedback submission error:", err.response?.data);
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || "Failed to submit feedback. Please ensure all required fields are filled.";
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const updateResponse = (questionId, key, value) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: {
        ...(prev[questionId] || {}),
        [key]: value
      }
    }));
  };

  if (submitted) {
    return (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl border border-surface-200 p-10 text-center max-w-sm animate-fade-in">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-emerald-600 font-display mb-2">Feedback Submitted!</h2>
          <p className="text-surface-500 text-sm">Thank you for your feedback!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-fade-in border border-surface-200">
        <div className="sticky top-0 bg-white px-6 py-4 border-b border-surface-200 flex justify-between items-center z-10 shadow-sm">
          <div>
            <h2 className="text-xl font-bold text-[#105b96] font-display">Give Feedback</h2>
            <p className="text-sm text-surface-500 font-medium">
              <span className="text-primary-600">{subject?.subject_name}</span> · {subject?.teacher_name || ''}
            </p>
          </div>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-700 bg-surface-100 hover:bg-surface-200 rounded-full p-2 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="p-6 bg-surface-50">
          {!session?.can_submit_feedback ? (
            <div className="p-4 rounded-lg bg-red-50 border border-red-200 mb-5">
              <p className="text-sm text-red-700 font-bold">❌ Feedback Window Closed</p>
              <p className="text-xs text-red-600 mt-1">Contact your HOD to open a window.</p>
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200 mb-6 flex items-start gap-3">
              <span className="text-xl">ℹ️</span>
              <div>
                <p className="text-sm text-blue-900 font-bold">Feedback Form: {form?.name}</p>
                <p className="text-xs text-blue-700 mt-1">{form?.description || 'Please fill out all required questions below.'}</p>
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-lg bg-red-50 border border-red-200 mb-6 animate-fade-in text-center">
              <p className="text-sm text-red-600 font-bold">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {questions.map((q) => (
              <div key={q.id} className="bg-white p-5 rounded-xl border border-surface-200 shadow-sm">
                <label className="block text-sm font-bold text-surface-800 mb-3">
                  {q.text} {q.is_required && <span className="text-red-500">*</span>}
                </label>
                
                {q.question_type === 'RATING' && (
                  <div className="flex items-center gap-2">
                    <div className="flex bg-surface-50 rounded-lg p-2 border border-surface-200">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          type="button"
                          key={star}
                          className="text-2xl px-1 focus:outline-none transition-transform hover:scale-110"
                          onClick={() => updateResponse(q.id, 'rating', star)}
                          onMouseEnter={() => setHoverRatings(prev => ({ ...prev, [q.id]: star }))}
                          onMouseLeave={() => setHoverRatings(prev => ({ ...prev, [q.id]: 0 }))}
                        >
                          <span className={
                            (responses[q.id]?.rating >= star || (hoverRatings[q.id] || 0) >= star) 
                            ? "text-amber-400 drop-shadow-sm" 
                            : "text-surface-300"
                          }>
                            ★
                          </span>
                        </button>
                      ))}
                    </div>
                    <span className="ml-3 font-bold text-surface-500 w-8 text-center">
                      {responses[q.id]?.rating > 0 ? `${responses[q.id].rating}/5` : ""}
                    </span>
                  </div>
                )}

                {q.question_type === 'TEXT' && (
                  <textarea
                    className="w-full bg-surface-50 border border-surface-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-shadow"
                    rows={3}
                    placeholder="Enter your detailed feedback here..."
                    value={responses[q.id]?.text_response || ''}
                    onChange={(e) => updateResponse(q.id, 'text_response', e.target.value)}
                  />
                )}
              </div>
            ))}

            {/* Overall Remark Section */}
            <div className="bg-surface-900/50 dark:bg-surface-800/30 p-5 rounded-2xl border border-surface-200 dark:border-surface-700/50 shadow-sm transition-all hover:shadow-md">
              <label className="block text-sm font-bold text-surface-800 dark:text-surface-100 mb-3 flex items-center gap-2">
                <span className="p-1.5 bg-primary-100 dark:bg-primary-900/30 rounded-lg text-primary-600 dark:text-primary-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
                </span>
                Overall Remark <span className="text-surface-500 text-xs font-normal ml-auto">(Optional)</span>
              </label>
              <textarea
                className="input-dark mt-1 focus:ring-2 focus:ring-primary-500/20"
                rows={3}
                placeholder="Share your thoughts, suggestions, or words of appreciation..."
                value={overallRemark}
                onChange={(e) => setOverallRemark(e.target.value)}
              />
            </div>

            <div className="pt-4 sticky bottom-0 bg-surface-50 pb-2">
              <button
                type="submit"
                className="w-full btn-success py-3.5 text-base shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all"
                disabled={loading || !session?.can_submit_feedback || !allRequiredAnswered}
              >
                {loading ? "Submitting..." : "Submit Feedback"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
