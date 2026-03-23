import { useState, useRef, useEffect } from "react";

export default function SubjectDropdown({ subjects, value, onChange }) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = subjects.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.code.toLowerCase().includes(search.toLowerCase())
  );

  const selected = subjects.find((s) => s.id === value);

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-surface-300 mb-2">
        📚 Select Subject
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full text-left input-dark flex justify-between items-center"
      >
        {selected ? (
          <span>
            <span className="text-surface-100 font-medium">{selected.name}</span>
            <span className="text-surface-500 ml-2">({selected.code})</span>
            {selected.branch_name && (
              <span className="text-xs text-primary-400 ml-2">
                {selected.branch_name} · Sem {selected.semester_number}
              </span>
            )}
          </span>
        ) : (
          <span className="text-surface-500">Choose a subject…</span>
        )}
        <svg
          className={`w-4 h-4 text-surface-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-xl bg-surface-800 border border-surface-700/50 shadow-2xl overflow-hidden animate-fade-in">
          <div className="p-2">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search subjects…"
              className="w-full px-3 py-2 rounded-lg bg-surface-900/80 border border-surface-700/50 text-sm text-surface-200 placeholder:text-surface-500 focus:outline-none focus:ring-1 focus:ring-primary-500/50"
              autoFocus
            />
          </div>
          <ul className="max-h-56 overflow-y-auto divide-y divide-surface-700/30">
            {filtered.length === 0 ? (
              <li className="px-4 py-3 text-sm text-surface-500 text-center">No subjects found</li>
            ) : (
              filtered.map((s) => (
                <li
                  key={s.id}
                  onClick={() => {
                    onChange(s.id);
                    setOpen(false);
                    setSearch("");
                  }}
                  className={`px-4 py-3 cursor-pointer text-sm transition-colors hover:bg-surface-700/40 ${
                    s.id === value ? "bg-primary-500/10 text-primary-400" : "text-surface-200"
                  }`}
                >
                  <span className="font-medium">{s.name}</span>
                  <span className="text-surface-500 ml-2">({s.code})</span>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-xs text-surface-500">👨‍🏫 {s.teacher_name}</span>
                    {s.branch_name && (
                      <span className="text-xs text-primary-400/70">
                        {s.branch_name} · Sem {s.semester_number}
                      </span>
                    )}
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
