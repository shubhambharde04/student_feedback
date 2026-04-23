import React from 'react';
import { motion } from 'framer-motion';

export default function ReportToggle({ reportType, setReportType }) {
  return (
    <div className="flex p-1 bg-surface-800 rounded-lg w-fit mb-6 border border-surface-700">
      <button
        onClick={() => setReportType('teacher')}
        className={`relative px-6 py-2 text-sm font-medium transition-colors ${
          reportType === 'teacher' ? 'text-surface-100' : 'text-surface-400 hover:text-surface-200'
        }`}
      >
        {reportType === 'teacher' && (
          <motion.div
            layoutId="active-toggle"
            className="absolute inset-0 bg-primary-600 rounded-md shadow-sm"
            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
          />
        )}
        <span className="relative z-10">Teacher Report</span>
      </button>
      
      <button
        onClick={() => setReportType('department')}
        className={`relative px-6 py-2 text-sm font-medium transition-colors ${
          reportType === 'department' ? 'text-surface-100' : 'text-surface-400 hover:text-surface-200'
        }`}
      >
        {reportType === 'department' && (
          <motion.div
            layoutId="active-toggle"
            className="absolute inset-0 bg-primary-600 rounded-md shadow-sm"
            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
          />
        )}
        <span className="relative z-10">Class Report (Cumulative)</span>
      </button>
    </div>
  );
}
