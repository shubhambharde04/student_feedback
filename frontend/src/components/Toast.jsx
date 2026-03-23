import { useState, useEffect } from "react";

export default function Toast({ message, type = "success", onClose, duration = 4000 }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const colors = {
    success: "from-accent-emerald/20 to-accent-emerald/5 border-accent-emerald/30 text-accent-emerald",
    error: "from-accent-rose/20 to-accent-rose/5 border-accent-rose/30 text-accent-rose",
    warning: "from-accent-amber/20 to-accent-amber/5 border-accent-amber/30 text-accent-amber",
    info: "from-primary-500/20 to-primary-500/5 border-primary-500/30 text-primary-400",
  };

  const icons = {
    success: "✅",
    error: "❌",
    warning: "⚠️",
    info: "ℹ️",
  };

  return (
    <div
      className={`fixed top-6 right-6 z-50 transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"
      }`}
    >
      <div
        className={`flex items-center gap-3 px-5 py-3.5 rounded-xl border bg-gradient-to-r backdrop-blur-xl shadow-2xl ${colors[type]}`}
      >
        <span className="text-lg">{icons[type]}</span>
        <p className="text-sm font-medium">{message}</p>
        <button
          onClick={() => {
            setVisible(false);
            setTimeout(onClose, 300);
          }}
          className="ml-2 opacity-60 hover:opacity-100 transition-opacity text-current"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
