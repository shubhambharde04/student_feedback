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
    <header className="gpn-header sticky top-0 z-50 shadow-2xl w-full border-b border-white/10">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-8 py-3 flex items-center justify-between gap-6">
        
        {/* Left Side: Logo & Institution Info */}
        <div className="flex items-center gap-5 flex-1 min-w-0">
          <div className="gpn-logo-container relative group">
            <div className="absolute inset-0 bg-white/20 rounded-full blur-md group-hover:bg-white/40 transition-all duration-500"></div>
            <div className="relative overflow-hidden bg-white rounded-full p-1 w-16 h-16 sm:w-20 sm:h-20 shadow-lg border-2 border-white/50">
              <img src="/gpn_logo.png" alt="GPN Logo" className="w-full h-full object-contain" />
            </div>
          </div>

          <div className="flex flex-col min-w-0">
            <div className="flex items-baseline gap-2 flex-wrap">
              <h1 className="text-xl sm:text-3xl font-black text-white font-display tracking-tight leading-none drop-shadow-md">
                Government Polytechnic, Nagpur
              </h1>
              <span className="text-[10px] sm:text-sm text-blue-100/80 font-medium italic hidden lg:inline">
                (An Autonomous Institute of Government of Maharashtra)
              </span>
            </div>
            
            <div className="mt-1 flex flex-col">
              <h2 className="text-sm sm:text-base font-semibold text-blue-50/90 leading-tight Marathi-font">
                शासकीय तंत्रनिकेतन, नागपूर <span className="text-[9px] sm:text-xs font-normal opacity-80">(महाराष्ट्र शासनाची स्वायत्त संस्था)</span>
              </h2>
              <p className="mt-1.5 text-xs sm:text-sm font-bold text-amber-400 uppercase tracking-widest drop-shadow-sm flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                Online Academic Feedback System
              </p>
            </div>
          </div>
        </div>

        {/* Right Side: Actions */}
        <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0">
          <div className="hidden sm:block">
            <ThemeToggle variant="navbar" />
          </div>
          
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <button 
                onClick={() => navigate("/change-password")} 
                className="hidden md:flex items-center gap-1.5 py-1 px-3 rounded-md bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold uppercase tracking-wider transition-all border border-white/5" 
                title="Change Password"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                <span>Account Security</span>
              </button>

              <button 
                onClick={handleLogout} 
                className="group flex items-center gap-2 py-2 px-4 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-black uppercase tracking-tighter transition-all shadow-lg hover:shadow-red-500/40"
              >
                <svg className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span>Logout</span>
              </button>
            </div>
            
            {user && (
              <div className="hidden lg:flex items-center justify-end gap-2 text-[10px] font-bold text-white/60">
                <span className="uppercase">{user.role} Portal</span>
                <span className="w-1 h-1 rounded-full bg-white/20"></span>
                <span>{user.username}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
