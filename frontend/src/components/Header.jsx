import React from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../api';
import ThemeToggle from './ThemeToggle';

export default function Header({ user }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) await API.post("auth/logout/", { refresh: refreshToken });
    } catch (e) { /* ignore */ }
    localStorage.clear();
    navigate("/");
  };

  return (
    <header className="gpn-header sticky top-0 z-30 shadow-xl w-full">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
        {/* Logo */}
        <div className="gpn-logo-circle animate-float overflow-hidden bg-white p-0.5 w-12 h-12 sm:w-14 sm:h-14 flex-shrink-0">
          <img src="/gpn_logo.png" alt="GPN Logo" className="w-full h-full object-contain" />
        </div>

        {/* Title */}
        <div className="min-w-0 flex-1">
          <h1 className="text-base sm:text-xl font-bold text-white font-display leading-tight">
            Government Polytechnic, Nagpur
          </h1>
          <p className="text-[10px] sm:text-xs text-amber-300 font-semibold uppercase tracking-wider">
            Online Academic Feedback System
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <ThemeToggle variant="navbar" />
          
          <button 
            onClick={() => navigate("/change-password")} 
            className="hidden md:flex btn-secondary text-xs items-center gap-1.5 py-1.5 px-3" 
            title="Change Password"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            <span>Password</span>
          </button>

          <button 
            onClick={handleLogout} 
            className="btn-danger text-xs flex items-center gap-1.5 py-1.5 px-3"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
