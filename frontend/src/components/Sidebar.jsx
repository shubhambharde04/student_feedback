import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import API from "../api";

const TEACHER_MENU = [
  { key: "dashboard", label: "Dashboard", icon: "grid" },
  { key: "performance", label: "My Performance", icon: "chart" },
];

const HOD_MENU = [
  { key: "overview", label: "Dashboard Overview", icon: "grid", path: "/hod-dashboard" },
  { key: "subjects", label: "Subject Offering", icon: "book", path: "/hod/subjects" },
  { key: "teachers", label: "Teachers", icon: "users", path: "/hod-dashboard" },
  { key: "teacher-mgmt", label: "Manage Teachers", icon: "users", path: "/hod/teachers-manage" },
  { key: "analytics", label: "Performance Analytics", icon: "chart", path: "/hod-dashboard" },
  { key: "statistics", label: "Feedback Statistics", icon: "bar", path: "/hod-dashboard" },
  { key: "students", label: "Students", icon: "users", path: "/hod/students" },
  { key: "enrollments", label: "Enrollments", icon: "users", path: "/hod/enrollments" },
  { key: "reports", label: "Reports", icon: "doc", path: "/hod/reports" },
  { key: "sessions", label: "Academic Sessions", icon: "clock", path: "/hod/sessions" },
  { key: "departments", label: "Academic Structure", icon: "grid", path: "/hod/structure" },
  { key: "formbuilder", label: "Form Matrix", icon: "grid", path: "/hod/forms" },
];

const icons = {
  grid: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  book: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
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
  trending: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
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
  sun: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="4" strokeWidth="1.5"></circle>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
    </svg>
  ),
  moon: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>
    </svg>
  ),
};

export default function Sidebar({ role, activeSection, onSectionChange, user }) {
  const navigate = useNavigate();
  const menu = role === "hod" ? HOD_MENU : TEACHER_MENU;
  
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
    <aside className="w-64 min-h-screen bg-white border-r border-surface-700 flex flex-col fixed left-0 top-0 z-30 shadow-sm">
      {/* GPN Brand - Official Header Style */}
      <div className="p-4 gpn-sidebar-brand text-white flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center shadow-md overflow-hidden flex-shrink-0">
          <img src="/gpn_logo.png" alt="GPN Logo" className="w-full h-full object-contain p-0.5" />
        </div>
        <div className="flex flex-col">
          <h2 className="text-xs font-bold leading-tight uppercase">Government Polytechnic</h2>
          <h2 className="text-xs font-bold uppercase">Nagpur</h2>
          <p className="text-[9px] text-amber-200 mt-0.5 uppercase tracking-wider font-semibold">Academic Feedback</p>
        </div>
      </div>

      <div className="gpn-sidebar-menu-header text-white font-bold text-xs px-4 py-2 uppercase tracking-wide">
        Main Menu ({role})
      </div>


      {/* Nav Items */}
      <nav className="flex-1 p-0 overflow-y-auto">
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
          className="sidebar-item w-full text-left text-accent-amber/80 hover:text-accent-amber"
        >
          {icons.key}
          <span>Change Password</span>
        </button>
      </nav>

      {/* User + Controls + Logout */}
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
        
        {/* Theme Toggle */}
        <div className="px-2 mb-2">
          <button 
            onClick={toggleTheme} 
            className="w-full flex items-center justify-between p-2.5 rounded-xl bg-surface-800/50 border border-surface-700/50 hover:bg-surface-800 transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className={`p-1.5 rounded-lg ${isDarkMode ? 'bg-amber-500/10 text-amber-500' : 'bg-blue-500/10 text-blue-500'}`}>
                {isDarkMode ? icons.sun : icons.moon}
              </div>
              <span className="text-xs font-bold text-surface-400 group-hover:text-surface-200">
                {isDarkMode ? "Light Mode" : "Dark Mode"}
              </span>
            </div>
            <div className={`w-8 h-4 rounded-full relative transition-colors ${isDarkMode ? 'bg-primary-500/50' : 'bg-surface-700'}`}>
              <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all shadow-sm ${isDarkMode ? 'left-4.5' : 'left-0.5'}`} />
            </div>
          </button>
        </div>

        <button onClick={handleLogout} className="sidebar-item w-full text-left text-accent-rose/80 hover:text-accent-rose">
          {icons.logout}
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
