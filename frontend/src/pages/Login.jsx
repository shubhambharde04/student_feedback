import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API, { checkBackendHealth } from "../api";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState("checking");

  useEffect(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");

    const verifyBackend = async () => {
      try {
        const alive = await checkBackendHealth();
        setBackendStatus(alive ? "online" : "offline");
        if (!alive) {
          setTimeout(async () => {
            try {
              const retry = await checkBackendHealth();
              setBackendStatus(retry ? "online" : "offline");
            } catch {
              setBackendStatus("offline");
            }
          }, 3000);
        }
      } catch {
        setBackendStatus("offline");
      }
    };
    verifyBackend();

    const handleBackendStatusChange = (event) => {
      const { isOffline } = event.detail;
      setBackendStatus(isOffline ? "offline" : "online");
    };

    window.addEventListener('backendStatusChange', handleBackendStatusChange);
    return () => window.removeEventListener('backendStatusChange', handleBackendStatusChange);
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please enter both username and password");
      return;
    }

    if (backendStatus === "offline") {
      try {
        const alive = await checkBackendHealth();
        if (!alive) {
          setError("⚠️ Server is currently unavailable. Please try again in a few moments.");
          return;
        }
        setBackendStatus("online");
      } catch {
        setError("⚠️ Server is currently unavailable. Please try again in a few moments.");
        return;
      }
    }

    setLoading(true);
    setError("");
    try {
      const response = await API.post("/auth/login/", { 
        username: username.trim(), 
        password: password.trim() 
      });
      const { access, refresh, user } = response.data;
      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);
      localStorage.setItem("user", JSON.stringify(user));
      if (user.role === 'student' && user.is_first_login) {
        navigate("/change-password");
      } else {
        navigate(`/${user.role}-dashboard`);
      }
    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        "Invalid username or password"
      );
    } finally {
      setLoading(false);
    }
  };

  const statusDot =
    backendStatus === "online"
      ? "bg-accent-emerald"
      : backendStatus === "offline"
      ? "bg-accent-rose"
      : "bg-accent-amber animate-pulse";

  const statusText =
    backendStatus === "online"
      ? "Server Connected"
      : backendStatus === "offline"
      ? "Server Offline"
      : "Checking server…";

  return (
    <div className="min-h-screen flex flex-col bg-surface-950">
      {/* ─── GPN-Style Top Header ─── */}
      <header className="gpn-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-5">
          {/* Logo */}
          <div className="gpn-logo-circle flex-shrink-0">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white font-display leading-tight tracking-wide">
              Government Polytechnic, Nagpur
              <span className="text-sm font-normal text-blue-200 ml-2 hidden sm:inline">
                (An Autonomous Institute of Government of Maharashtra)
              </span>
            </h1>
            <p className="text-sm text-blue-200 font-medium hidden sm:block">
              शासकीय तंत्रनिकेतन, नागपूर
              <span className="text-blue-300/70 ml-2 text-xs">(महाराष्ट्र शासनाची स्वायत्त संस्था)</span>
            </p>
            <p className="text-sm font-semibold text-amber-300 mt-0.5 tracking-wide">
              Online Academic Feedback System
            </p>
          </div>
        </div>
      </header>

      {/* ─── Navigation Bar ─── */}
      <nav className="gpn-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center gap-1">
          <span className="gpn-nav-item active">Welcome</span>
        </div>
      </nav>

      {/* ─── Main Content ─── */}
      <div className="flex-1 bg-mesh flex items-center justify-center p-4 relative overflow-hidden">
        {/* Decorative orbs */}
        <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-primary-600/20 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-violet/15 rounded-full blur-[120px] animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 right-1/3 w-48 h-48 bg-accent-cyan/10 rounded-full blur-[80px] animate-float" style={{ animationDelay: '4s' }} />

        <div className="relative z-10 w-full max-w-md animate-fade-in">
          {/* Welcome text */}
          <div className="text-center mb-6">
            <p className="text-surface-300 text-sm">Welcome to Government Polytechnic Nagpur Feedback Portal</p>
          </div>

          {/* Login Card */}
          <div className="glass-card p-8">
            {/* Backend status indicator */}
            <div className="flex items-center justify-center gap-2 mb-5">
              <span className={`w-2.5 h-2.5 rounded-full ${statusDot}`} />
              <span className="text-xs text-surface-400">{statusText}</span>
            </div>

            <h2 className="text-xl font-semibold text-surface-100 mb-6 text-center font-display">Sign in to your account</h2>

            {error && (
              <div className="mb-5 p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 animate-fade-in">
                <p className="text-accent-rose text-sm text-center font-medium">{error}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">Enrollment No / Username</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </span>
                  <input
                    type="text"
                    placeholder="Enter your enrollment no. or username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="input-dark pl-10"
                    disabled={loading}
                    autoComplete="username"
                    id="login-username"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">Password</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </span>
                  <input
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-dark pl-10"
                    disabled={loading}
                    autoComplete="current-password"
                    id="login-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full btn-primary py-3 text-base relative overflow-hidden group"
                disabled={loading}
                id="login-submit"
              >
                <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-700" />
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Signing in...
                  </span>
                ) : (
                  "Sign In"
                )}
              </button>
            </form>

            {/* Role indicators */}
            <div className="mt-6 pt-5 border-t border-surface-700/50">
              <p className="text-xs text-surface-500 text-center mb-3">Available roles</p>
              <div className="flex justify-center gap-3">
                <span className="badge badge-positive">👨‍🎓 Student</span>
                <span className="badge badge-good">👨‍🏫 Teacher</span>
                <span className="badge badge-average">🧑‍💼 HOD</span>
              </div>
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-surface-600">
            Need help? Contact the administrator for credentials.
          </p>
        </div>
      </div>

      {/* ─── Footer ─── */}
      <footer className="gpn-footer">
        <p>Copyright © 2024-25. Government Polytechnic, Nagpur. All rights reserved.</p>
      </footer>
    </div>
  );
}
