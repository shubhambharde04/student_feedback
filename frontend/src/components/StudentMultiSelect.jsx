import { useState, useMemo } from "react";

export default function StudentMultiSelect({
  students,
  selectedIds,
  onChange,
  selectedSubject,
}) {
  const [search, setSearch] = useState("");

  // Filter students by matching branch+semester of selected subject
  const eligible = useMemo(() => {
    if (!selectedSubject) return students;
    return students.filter((s) => {
      const branchMatch =
        !selectedSubject.branch_id || s.branch_id === selectedSubject.branch_id;
      const semMatch =
        !selectedSubject.semester_id || s.semester_id === selectedSubject.semester_id;
      return branchMatch && semMatch;
    });
  }, [students, selectedSubject]);

  const filtered = useMemo(
    () =>
      eligible.filter(
        (s) =>
          (s.first_name + " " + s.last_name).toLowerCase().includes(search.toLowerCase()) ||
          s.username.toLowerCase().includes(search.toLowerCase()) ||
          (s.enrollment_no || "").toLowerCase().includes(search.toLowerCase())
      ),
    [eligible, search]
  );

  const allSelected = filtered.length > 0 && filtered.every((s) => selectedIds.includes(s.id));

  const toggleAll = () => {
    if (allSelected) {
      onChange(selectedIds.filter((id) => !filtered.some((s) => s.id === id)));
    } else {
      const newIds = [...new Set([...selectedIds, ...filtered.map((s) => s.id)])];
      onChange(newIds);
    }
  };

  const toggle = (id) => {
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter((i) => i !== id)
        : [...selectedIds, id]
    );
  };

  return (
    <div>
      <label className="block text-sm font-medium text-surface-300 mb-2">
        👨‍🎓 Select Students
        {selectedSubject && (
          <span className="text-xs text-primary-400 ml-2">
            (showing {eligible.length} eligible students)
          </span>
        )}
      </label>

      {/* Search + Select All */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or enrollment no…"
          className="flex-1 input-dark text-sm"
        />
        <button
          type="button"
          onClick={toggleAll}
          className="px-4 py-2 rounded-lg text-xs font-medium bg-surface-800 border border-surface-700/50 text-surface-300 hover:bg-surface-700/50 transition-colors whitespace-nowrap"
        >
          {allSelected ? "Deselect All" : "Select All"}
        </button>
      </div>

      {/* Selected count badge */}
      {selectedIds.length > 0 && (
        <div className="mb-3 flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-primary-500/15 text-primary-400 text-xs font-medium">
            {selectedIds.length} selected
          </span>
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs text-surface-500 hover:text-accent-rose transition-colors"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Student List */}
      <div className="max-h-72 overflow-y-auto rounded-xl border border-surface-700/50 bg-surface-800/50 divide-y divide-surface-700/30">
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-surface-500">
            {!selectedSubject
              ? "Select a subject first to see eligible students"
              : "No matching students found"}
          </div>
        ) : (
          filtered.map((s) => (
            <label
              key={s.id}
              className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-surface-700/30 ${
                selectedIds.includes(s.id) ? "bg-primary-500/5" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={selectedIds.includes(s.id)}
                onChange={() => toggle(s.id)}
                className="w-4 h-4 rounded border-surface-600 text-primary-500 focus:ring-primary-500/30 bg-surface-800"
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-surface-200 font-medium truncate">
                  {s.first_name} {s.last_name}
                  <span className="text-surface-500 font-normal ml-1">({s.username})</span>
                </p>
                {s.enrollment_no && (
                  <p className="text-xs text-surface-500">Enroll: {s.enrollment_no}</p>
                )}
              </div>
            </label>
          ))
        )}
      </div>
    </div>
  );
}
