import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";

export default function StudentDashboard() {
  const [subjects, setSubjects] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedbackSubject, setFeedbackSubject] = useState(null);
  const navigate = useNavigate();
  const hasFetched = useRef(false);

  const fetchData = useCallback(async () => {
    try {
      const [subjectsRes, profileRes] = await Promise.allSettled([
        API.get("student-subjects/"),
        API.get("auth/profile/"),
      ]);

      if (subjectsRes.status === 'fulfilled') {
        setSubjects(Array.isArray(subjectsRes.value?.data) ? subjectsRes.value.data : []);
      } else {
        console.error("Failed to load subjects:", subjectsRes.reason);
        setSubjects([]);
      }

      if (profileRes.status === 'fulfilled') {
        setUser(profileRes.value?.data?.user ?? null);
      } else {
        console.error("Failed to load profile:", profileRes.reason);
        if (profileRes.reason?.response?.status === 401) {
          navigate("/");
          return;
        }
      }
    } catch (err) {
      console.error("Error fetching data:", err);
      setError("Failed to load dashboard data.");
      if (err.response?.status === 401) navigate("/");
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    // Prevent duplicate fetches from StrictMode double-mount
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
    API.get("student-subjects/").then(r => setSubjects(Array.isArray(r?.data) ? r.data : [])).catch(() => {});
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-surface-400 text-sm">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="glass-card p-8 max-w-md text-center">
          <p className="text-accent-rose text-lg font-medium mb-2">⚠️ Error</p>
          <p className="text-surface-400 mb-4">{error}</p>
          <button onClick={() => { setError(null); setLoading(true); hasFetched.current = false; fetchData(); }} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const totalSubjects = subjects?.length ?? 0;
  const submitted = subjects?.filter((s) => s?.feedback_submitted)?.length ?? 0;
  const pending = totalSubjects - submitted;

  return (
    <div className="min-h-screen flex flex-col bg-surface-950">
      {/* ─── GPN-Style Top Header ─── */}
      <header className="gpn-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-4">
          <div className="gpn-logo-circle flex-shrink-0" style={{ width: '44px', height: '44px' }}>
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
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
              onClick={() => navigate("/change-password")}
              className="btn-secondary text-xs flex items-center gap-1.5"
              title="Change Password"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              <span className="hidden sm:inline">Change Password</span>
            </button>
            <button onClick={handleLogout} className="btn-danger text-xs flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* ─── Dashboard Nav (no Home/Contact/Login) ─── */}
      <nav className="gpn-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-1">
            <span className="gpn-nav-item active">Dashboard</span>
            <span 
              className="gpn-nav-item cursor-pointer hover:text-surface-200 transition-colors"
              onClick={() => {
                const subjectsSection = document.getElementById('subjects-section');
                if (subjectsSection) {
                  subjectsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }}
            >
              My Subjects
            </span>
          </div>
          <p className="text-xs text-blue-200">
            Welcome, {user?.first_name || user?.username || 'Student'} 👋
          </p>
        </div>
      </nav>

      {/* ─── Main Content ─── */}
      <main className="flex-1 bg-mesh">
        <div className="max-w-6xl mx-auto px-6 py-8">
          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8 stagger">
            <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-primary-500)' }}>
              <p className="text-sm text-surface-400 mb-1">Total Subjects</p>
              <p className="text-3xl font-bold text-primary-400 font-display">{totalSubjects}</p>
            </div>
            <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-emerald)' }}>
              <p className="text-sm text-surface-400 mb-1">Feedback Given</p>
              <p className="text-3xl font-bold text-accent-emerald font-display">{submitted}</p>
            </div>
            <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-amber)' }}>
              <p className="text-sm text-surface-400 mb-1">Pending</p>
              <p className="text-3xl font-bold text-accent-amber font-display">{pending}</p>
            </div>
          </div>

          {/* Subjects List */}
          <div id="subjects-section" className="glass-card overflow-hidden mb-8">
            <div className="px-6 py-4 border-b border-surface-700/50">
              <h2 className="text-lg font-semibold font-display text-surface-100">Your Subjects</h2>
            </div>
            <div className="p-6">
              {(!subjects || subjects.length === 0) ? (
                <p className="text-surface-500 text-center py-8">No subjects assigned.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger">
                  {subjects.map((sub) => (
                    <div
                      key={sub?.offering_id || sub?.subject_id || Math.random()}
                      className="glass-card-light p-5 flex justify-between items-center animate-fade-in hover:bg-surface-800/40 transition-colors"
                    >
                      <div className="min-w-0">
                        <h4 className="font-semibold text-surface-100">{sub?.subject_name || 'Unknown Subject'}</h4>
                        <p className="text-sm text-surface-400 mt-0.5">
                          <span className="text-surface-500">{sub?.subject_code || ''}</span> · {sub?.teacher || 'No teacher assigned'}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        {sub?.feedback_submitted ? (
                          <span className="badge badge-submitted">✅ Submitted</span>
                        ) : (
                          <button
                            onClick={() => setFeedbackSubject(sub)}
                            className="btn-primary text-sm"
                          >
                            Give Feedback
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* ─── Footer ─── */}
      <footer className="gpn-footer">
        <p>Copyright © 2024-25. Government Polytechnic, Nagpur. All rights reserved.</p>
      </footer>

      {/* Feedback Modal */}
      {feedbackSubject && (
        <FeedbackModal
          subject={feedbackSubject}
          onClose={() => setFeedbackSubject(null)}
          onSuccess={handleFeedbackSuccess}
        />
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────── */
/*  Inline Feedback Modal with 5 Star Ratings            */
/* ────────────────────────────────────────────────────── */

function FeedbackModal({ subject, onClose, onSuccess }) {
  const [ratings, setRatings] = useState({
    punctuality_rating: 0,
    teaching_rating: 0,
    clarity_rating: 0,
    interaction_rating: 0,
    behavior_rating: 0,
  });
  const [hoverRatings, setHoverRatings] = useState({});
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [feedbackWindow, setFeedbackWindow] = useState(null);
  const [windowLoading, setWindowLoading] = useState(true);

  useEffect(() => {
    API.get("feedback-window/current/")
      .then((r) => setFeedbackWindow(r?.data ?? null))
      .catch(() => setFeedbackWindow(null))
      .finally(() => setWindowLoading(false));
  }, []);

  const ratingFields = [
    { key: "punctuality_rating", label: "Punctuality", emoji: "⏰" },
    { key: "teaching_rating", label: "Teaching Quality", emoji: "📚" },
    { key: "clarity_rating", label: "Clarity", emoji: "💡" },
    { key: "interaction_rating", label: "Interaction", emoji: "🤝" },
    { key: "behavior_rating", label: "Behavior", emoji: "🎯" },
  ];

  const overall =
    Object.values(ratings).reduce((a, b) => a + b, 0) /
    Math.max(Object.values(ratings).filter((v) => v > 0).length, 1);

  const allRated = Object.values(ratings).every((v) => v > 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!allRated) { setError("Please rate all categories"); return; }
    if (comment.trim().length < 10) { setError("Comment must be at least 10 characters"); return; }
    setLoading(true);
    setError("");
    try {
      await API.post("feedback/", {
        offering: subject?.offering_id || subject?.id,
        ...ratings,
        comment: comment.trim(),
      });
      setSubmitted(true);
      setTimeout(() => onSuccess(), 1500);
    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        (typeof err.response?.data === 'object' ? JSON.stringify(err.response.data) : null) ||
        "Failed to submit feedback"
      );
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="glass-card p-10 text-center max-w-sm animate-fade-in">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-accent-emerald font-display mb-2">
            Feedback Submitted!
          </h2>
          <p className="text-surface-400 text-sm">
            Thank you for your feedback on {subject?.subject_name || 'this subject'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-card w-full max-w-lg max-h-[90vh] overflow-y-auto animate-fade-in">
        {/* Header */}
        <div className="sticky top-0 bg-surface-900/90 backdrop-blur-xl px-6 py-4 border-b border-surface-700/50 flex justify-between items-center z-10">
          <div>
            <h2 className="text-lg font-bold text-surface-100 font-display">Give Feedback</h2>
            <p className="text-xs text-surface-500">{subject?.subject_name || ''} · {subject?.teacher || ''}</p>
          </div>
          <button onClick={onClose} className="text-surface-500 hover:text-surface-200 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          {/* Feedback Window */}
          {windowLoading ? (
            <div className="p-3 rounded-lg bg-surface-800/50 mb-5">
              <p className="text-sm text-surface-500">Checking feedback window...</p>
            </div>
          ) : feedbackWindow ? (
            <div className="p-3 rounded-lg bg-accent-emerald/10 border border-accent-emerald/20 mb-5">
              <p className="text-sm text-accent-emerald font-medium">✅ Feedback Window Open</p>
              <p className="text-xs text-accent-emerald/70 mt-0.5">
                Until: {new Date(feedbackWindow.end_date).toLocaleString()}
              </p>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 mb-5">
              <p className="text-sm text-accent-rose font-medium">❌ Feedback Window Closed</p>
              <p className="text-xs text-accent-rose/70 mt-0.5">Contact your HOD to open a window.</p>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 mb-5 animate-fade-in">
              <p className="text-sm text-accent-rose">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Star Ratings */}
            {ratingFields.map(({ key, label, emoji }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  {emoji} {label}
                </label>
                <div className="star-rating">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span
                      key={star}
                      className={`star ${ratings[key] >= star ? "active" : ""} ${(hoverRatings[key] || 0) >= star ? "hover-preview" : ""}`}
                      onClick={() => setRatings((prev) => ({ ...prev, [key]: star }))}
                      onMouseEnter={() => setHoverRatings((prev) => ({ ...prev, [key]: star }))}
                      onMouseLeave={() => setHoverRatings((prev) => ({ ...prev, [key]: 0 }))}
                    >
                      ★
                    </span>
                  ))}
                  <span className="ml-2 text-sm text-surface-500">
                    {ratings[key] > 0 ? `${ratings[key]}/5` : "—"}
                  </span>
                </div>
              </div>
            ))}

            {/* Overall */}
            {allRated && (
              <div className="glass-card-light p-4 animate-fade-in">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-surface-300">Overall Rating</span>
                  <span className="text-lg font-bold text-primary-400">{overall.toFixed(1)}/5</span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-700">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-cyan transition-all duration-500"
                    style={{ width: `${(overall / 5) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Comment */}
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                💬 Your Comment <span className="text-accent-rose">*</span>
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Share your detailed thoughts about this subject... (min 10 characters)"
                className="input-dark"
                rows={4}
                disabled={loading}
              />
              <p className={`text-xs mt-1 ${comment.trim().length < 10 ? "text-accent-amber" : "text-accent-emerald"}`}>
                {comment.trim().length}/10 characters minimum
              </p>
            </div>

            <button
              type="submit"
              className="w-full btn-success py-3 text-base"
              disabled={loading || !feedbackWindow || !allRated}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Submitting...
                </span>
              ) : (
                "Submit Feedback"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
