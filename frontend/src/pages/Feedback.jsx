import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import API from "../api";

export default function Feedback() {
  const [ratings, setRatings] = useState({
    punctuality_rating: 0,
    teaching_rating: 0,
    clarity_rating: 0,
    interaction_rating: 0,
    behavior_rating: 0,
  });
  const [hoverRatings, setHoverRatings] = useState({});
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [subject, setSubject] = useState(null);
  const [feedbackWindow, setFeedbackWindow] = useState(null);
  const [windowLoading, setWindowLoading] = useState(true);

  const navigate = useNavigate();
  const location = useLocation();

  const ratingFields = [
    { key: "punctuality_rating", label: "Punctuality", emoji: "⏰" },
    { key: "teaching_rating", label: "Teaching Quality", emoji: "📚" },
    { key: "clarity_rating", label: "Clarity", emoji: "💡" },
    { key: "interaction_rating", label: "Interaction", emoji: "🤝" },
    { key: "behavior_rating", label: "Behavior", emoji: "🎯" },
  ];

  useEffect(() => {
    if (location.state?.subject) {
      setSubject(location.state.subject);
    } else {
      navigate("/student-dashboard");
    }

    API.get("feedback-window/current/")
      .then((r) => setFeedbackWindow(r.data))
      .catch(() => setFeedbackWindow(null))
      .finally(() => setWindowLoading(false));
  }, [location.state, navigate]);

  const allRated = Object.values(ratings).every((v) => v > 0);
  const overall =
    Object.values(ratings).reduce((a, b) => a + b, 0) /
    Math.max(Object.values(ratings).filter((v) => v > 0).length, 1);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!allRated) { setError("Please rate all categories."); return; }
    setLoading(true);
    setError("");

    try {
      await API.post("feedback/", {
        subject: subject.id,
        ...ratings,
        comment: comment.trim() || "",
      });
      setSubmitted(true);
    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        "Failed to submit feedback"
      );
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center p-4">
        <div className="glass-card p-10 text-center max-w-sm animate-fade-in">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-accent-emerald font-display mb-2">
            Feedback Submitted!
          </h2>
          <p className="text-surface-400 text-sm mb-6">
            Thank you for your feedback on {subject?.name}
          </p>
          <button
            onClick={() => navigate("/student-dashboard")}
            className="btn-primary"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!subject) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh">
      <header className="sticky top-0 z-20 bg-surface-900/80 backdrop-blur-xl border-b border-surface-700/50">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate("/student-dashboard")}
            className="text-surface-400 hover:text-surface-200 flex items-center gap-2 text-sm transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <h1 className="text-lg font-bold text-surface-100 font-display">Submit Feedback</h1>
          <div className="w-16" />
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="glass-card p-8 animate-fade-in">
          {/* Subject Info */}
          <div className="glass-card-light p-4 mb-6">
            <p className="text-sm text-surface-300">
              <strong>Subject:</strong> {subject.name}
            </p>
            <p className="text-sm text-surface-400">
              <strong>Teacher:</strong> {subject.teacher_name || "Not specified"}
            </p>
          </div>

          {/* Feedback Window Status */}
          {windowLoading ? (
            <div className="p-3 rounded-lg bg-surface-800/50 mb-6">
              <p className="text-sm text-surface-500">Checking feedback window...</p>
            </div>
          ) : feedbackWindow ? (
            <div className="p-3 rounded-lg bg-accent-emerald/10 border border-accent-emerald/20 mb-6">
              <p className="text-sm text-accent-emerald font-medium">✅ Feedback Window is Open</p>
              <p className="text-xs text-accent-emerald/70">
                Until: {new Date(feedbackWindow.end_date).toLocaleString()}
              </p>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 mb-6">
              <p className="text-sm text-accent-rose font-medium">❌ Feedback Window is Closed</p>
              <p className="text-xs text-accent-rose/70">Contact your HOD to open a feedback window.</p>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 mb-6 animate-fade-in">
              <p className="text-sm text-accent-rose">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
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

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                💬 Your Comment <span className="text-surface-500 text-xs font-normal ml-1">(Optional)</span>
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Share any additional thoughts about this subject... (optional)"
                className="input-dark"
                rows={4}
                disabled={loading}
              />
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