import { useState, useEffect } from "react";

export default function ThemeToggle({ className = "", variant = "default" }) {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) {
      return savedTheme === "dark";
    }
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
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    
    if (newDarkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  };

  const sunIcon = (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="4" strokeWidth="1.5"></circle>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
    </svg>
  );

  const moonIcon = (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>
    </svg>
  );

  if (variant === "navbar") {
    return (
      <button 
        onClick={toggleTheme}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors text-white ${className}`}
        aria-label="Toggle Dark Mode"
      >
        <span className={isDarkMode ? 'text-amber-400' : 'text-blue-200'}>
          {isDarkMode ? sunIcon : moonIcon}
        </span>
        <span className="text-xs font-bold whitespace-nowrap">
          {isDarkMode ? "Light" : "Dark"}
        </span>
      </button>
    );
  }

  return (
    <button 
      onClick={toggleTheme} 
      className={`flex items-center justify-between p-2.5 rounded-xl bg-surface-800/50 border border-surface-700/50 hover:bg-surface-800 transition-all group ${className}`}
      aria-label="Toggle Dark Mode"
    >
      <div className="flex items-center gap-3">
        <div className={`p-1.5 rounded-lg ${isDarkMode ? 'bg-amber-500/10 text-amber-500' : 'bg-blue-500/10 text-blue-500'}`}>
          {isDarkMode ? sunIcon : moonIcon}
        </div>
        <span className="text-xs font-bold text-surface-400 group-hover:text-surface-200">
          {isDarkMode ? "Light Mode" : "Dark Mode"}
        </span>
      </div>
      <div className={`w-8 h-4 rounded-full relative transition-colors ${isDarkMode ? 'bg-primary-500/50' : 'bg-surface-700'}`}>
        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all shadow-sm ${isDarkMode ? 'left-4.5' : 'left-0.5'}`} />
      </div>
    </button>
  );
}
