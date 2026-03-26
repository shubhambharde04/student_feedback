import { useNavigate } from "react-router-dom";
import API from "../api";

const TEACHER_MENU = [
  { key: "dashboard", label: "Dashboard", icon: "grid" },
  { key: "performance", label: "My Performance", icon: "chart" },
];

const HOD_MENU = [
  { key: "overview", label: "Dashboard Overview", icon: "grid", path: "/hod-dashboard" },
  { key: "teachers", label: "Teachers", icon: "users", path: "/hod-dashboard" },
  { key: "analytics", label: "Performance Analytics", icon: "chart", path: "/hod-dashboard" },
  { key: "statistics", label: "Feedback Statistics", icon: "bar", path: "/hod-dashboard" },
  { key: "students", label: "Students", icon: "users", path: "/hod/students" },
  { key: "enrollments", label: "Enrollments", icon: "users", path: "/hod/enrollments" },
  { key: "reports", label: "Reports", icon: "doc", path: "/hod/reports" },
  { key: "windows", label: "Feedback Windows", icon: "clock", path: "/hod-dashboard" },
];

const icons = {
  grid: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  chart: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  bar: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
    </svg>
  ),
  doc: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  key: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
    </svg>
  ),
  logout: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
    </svg>
  ),
};

export default function Sidebar({ role, activeSection, onSectionChange, user }) {
  const navigate = useNavigate();
  const menu = role === "hod" ? HOD_MENU : TEACHER_MENU;

  const handleNavClick = (item) => {
    if (item.path && window.location.pathname !== item.path) {
      navigate(item.path, { state: { activeSection: item.key } });
    } else if (onSectionChange) {
      onSectionChange(item.key);
    }
  };

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        await API.post("auth/logout/", { refresh: refreshToken });
      }
    } catch (e) {
      console.error("Logout error:", e);
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      navigate("/");
    }
  };

  return (
    <aside className="w-64 min-h-screen bg-surface-900/80 backdrop-blur-xl border-r border-surface-700/50 flex flex-col fixed left-0 top-0 z-30">
      {/* GPN Brand */}
      <div className="p-4 border-b border-surface-700/50 bg-gradient-to-b from-[#1a365d] to-surface-900/80">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center flex-shrink-0 shadow-lg">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div className="min-w-0">
            <h2 className="text-xs font-bold text-white font-display leading-tight">Govt. Polytechnic</h2>
            <h2 className="text-xs font-bold text-blue-200 font-display">Nagpur</h2>
          </div>
        </div>
        <div className="ml-0">
          <p className="text-[10px] text-amber-300 font-semibold">Online Academic Feedback System</p>
          <p className="text-[10px] text-blue-300/60 capitalize">{role} Panel</p>
        </div>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {menu.map((item) => (
          <button
            key={item.key}
            onClick={() => handleNavClick(item)}
            className={`sidebar-item w-full text-left ${
              (activeSection === item.key || (window.location.pathname === item.path && !activeSection)) ? "active" : ""
            }`}
          >
            {icons[item.icon]}
            <span>{item.label}</span>
          </button>
        ))}

        {/* Divider */}
        <div className="my-3 border-t border-surface-700/50" />

        {/* Change Password */}
        <button
          onClick={() => navigate("/change-password")}
          className="sidebar-item w-full text-left text-accent-amber/80 hover:text-accent-amber hover:bg-accent-amber/10"
        >
          {icons.key}
          <span>Change Password</span>
        </button>
      </nav>

      {/* User + Logout */}
      <div className="p-4 border-t border-surface-700/50">
        {user && (
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
              {(user.first_name || user.username || "U").charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-surface-200 truncate">
                {user.first_name || user.username}
              </p>
              <p className="text-xs text-surface-500 capitalize">{user.role}</p>
            </div>
          </div>
        )}
        <button onClick={handleLogout} className="sidebar-item w-full text-left text-accent-rose/80 hover:text-accent-rose hover:bg-accent-rose/10">
          {icons.logout}
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
