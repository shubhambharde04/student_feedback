import { useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";

export default function ChangePassword() {
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const userStr = localStorage.getItem("user");
  const user = userStr ? JSON.parse(userStr) : null;
  const isFirstLogin = user?.is_first_login;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!oldPassword || !newPassword || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    if (oldPassword === newPassword) {
      setError("New password must be different from the current password.");
      return;
    }

    setLoading(true);

    try {
      await API.post("/auth/change-password/", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      
      setSuccess("Password changed successfully! Redirecting to dashboard...");
      
      // Update local user object
      if (user) {
        user.is_first_login = false;
        localStorage.setItem("user", JSON.stringify(user));
      }

      setTimeout(() => {
        if (user?.role) {
          navigate(`/${user.role}-dashboard`);
        } else {
          navigate("/");
        }
      }, 2000);

    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        "Failed to change password. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleGoBack = () => {
    if (user?.role) {
      navigate(`/${user.role}-dashboard`);
    } else {
      navigate("/");
    }
  };

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
        </div>
      </header>

      {/* ─── Nav ─── */}
      <nav className="gpn-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center">
          <span className="gpn-nav-item active">Change Password</span>
          {!isFirstLogin && (
            <button onClick={handleGoBack} className="gpn-nav-item">
              ← Back to Dashboard
            </button>
          )}
        </div>
      </nav>

      {/* ─── Main Content ─── */}
      <div className="flex-1 bg-mesh flex items-center justify-center p-4 relative overflow-hidden">
        <div className="absolute top-1/3 left-1/4 w-64 h-64 bg-primary-600/15 rounded-full blur-[100px] animate-float" />
        <div className="absolute bottom-1/3 right-1/4 w-72 h-72 bg-accent-violet/10 rounded-full blur-[100px] animate-float" style={{ animationDelay: '3s' }} />

        <div className="relative z-10 w-full max-w-md animate-fade-in glass-card p-8">
          {/* Icon */}
          <div className="flex justify-center mb-5">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
          </div>
          
          <h2 className="text-2xl font-bold font-display text-surface-50 mb-2 text-center">
            {isFirstLogin ? "Setup New Password" : "Change Password"}
          </h2>
          <p className="text-surface-400 text-sm mb-6 text-center">
            {isFirstLogin 
              ? "Since this is your first login, you are required to set a new password for security."
              : "Enter your current password and choose a new one."
            }
          </p>

          {/* User info badge */}
          {user && (
            <div className="flex items-center justify-center gap-2 mb-5">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-white text-xs font-bold">
                {(user.first_name || user.username || "U").charAt(0).toUpperCase()}
              </div>
              <span className="text-sm text-surface-300">{user.first_name || user.username}</span>
              <span className="badge badge-good text-[10px] capitalize">{user.role}</span>
            </div>
          )}

          {error && (
            <div className="mb-5 p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 text-accent-rose text-sm font-medium animate-fade-in">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-5 p-3 rounded-lg bg-accent-emerald/10 border border-accent-emerald/20 text-accent-emerald text-sm font-medium animate-fade-in">
              ✅ {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1">
                {isFirstLogin ? "Current Password (Enrollment No.)" : "Current Password"}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </span>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="input-dark w-full pl-10"
                  disabled={loading}
                  placeholder="Enter current password"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1">New Password</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input-dark w-full pl-10"
                  disabled={loading}
                  placeholder="Minimum 6 characters"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1">Confirm New Password</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input-dark w-full pl-10"
                  disabled={loading}
                  placeholder="Confirm new password"
                />
              </div>
            </div>

            {/* Password strength indicator */}
            {newPassword && (
              <div className="animate-fade-in">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-surface-500">Strength:</span>
                  <div className="flex-1 h-1.5 bg-surface-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-300 ${
                        newPassword.length >= 10 ? 'bg-accent-emerald w-full' :
                        newPassword.length >= 8 ? 'bg-accent-amber w-3/4' :
                        newPassword.length >= 6 ? 'bg-orange-500 w-1/2' :
                        'bg-accent-rose w-1/4'
                      }`}
                    />
                  </div>
                  <span className={`text-xs font-medium ${
                    newPassword.length >= 10 ? 'text-accent-emerald' :
                    newPassword.length >= 8 ? 'text-accent-amber' :
                    newPassword.length >= 6 ? 'text-orange-400' :
                    'text-accent-rose'
                  }`}>
                    {newPassword.length >= 10 ? 'Strong' : newPassword.length >= 8 ? 'Good' : newPassword.length >= 6 ? 'Fair' : 'Weak'}
                  </span>
                </div>
              </div>
            )}

            <button
              type="submit"
              className="w-full btn-primary py-3 mt-4"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Updating...
                </span>
              ) : (
                "Update Password"
              )}
            </button>

            {!isFirstLogin && (
              <button
                type="button"
                onClick={handleGoBack}
                className="w-full btn-secondary py-2.5 mt-1"
              >
                Cancel
              </button>
            )}
          </form>
        </div>
      </div>

      {/* ─── Footer ─── */}
      <footer className="gpn-footer">
        <p>Copyright © 2024-25. Government Polytechnic, Nagpur. All rights reserved.</p>
      </footer>
    </div>
  );
}
