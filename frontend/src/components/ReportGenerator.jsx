import React, { useState } from 'react';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import API from '../api';
import EmailComposer from './EmailComposer';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line
} from "recharts";

const COLORS = {
  primary: '#6366f1',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444'
};

export default function ReportGenerator({ teachers, subjects }) {
  const [reportType, setReportType] = useState('teacher'); // 'teacher' or 'department'
  const [selectedTeacher, setSelectedTeacher] = useState('');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [showEmailComposer, setShowEmailComposer] = useState(false);
  const [emailStatus, setEmailStatus] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const generateReport = async () => {
    if (reportType === 'teacher' && !selectedTeacher) {
      setError('Please select a teacher to generate their report.');
      return;
    }

    setLoading(true);
    setError('');
    setReportData(null);
    
    try {
      const endpoint = reportType === 'teacher' 
        ? `hod/teacher/${selectedTeacher}/report/`
        : `hod/department/report/`;
        
      const response = await API.get(endpoint);
      setReportData(response.data);
    } catch (err) {
      setError('Failed to fetch report data.');
    } finally {
      setLoading(false);
    }
  };

  const exportPDF = () => {
    if (!reportData) return;
    setIsExporting(true);
    
    try {
      const doc = new jsPDF();
      doc.setFontSize(20);
      
      if (reportType === 'teacher') {
        doc.text(`Performance Report: ${reportData.teacher.name}`, 14, 20);
        doc.setFontSize(12);
        doc.text(`Email: ${reportData.teacher.email}`, 14, 30);
        doc.text(`Total Feedback: ${reportData.total_feedback_count}`, 14, 38);
        doc.text(`Average Rating: ${reportData.average_rating} / 5.0 (${reportData.performance_label})`, 14, 46);
        
        doc.text('Subjects Handled:', 14, 60);
        let yPos = 68;
        reportData.subjects.forEach(s => {
          doc.text(`- ${s.name} (${s.code})`, 14, yPos);
          yPos += 8;
        });
        
        yPos += 10;
        doc.text(`Strengths: ${reportData.strengths.join(', ') || 'N/A'}`, 14, yPos);
        yPos += 8;
        doc.text(`Weaknesses: ${reportData.weaknesses.join(', ') || 'N/A'}`, 14, yPos);
        
      } else {
        doc.text('Department Performance Report', 14, 20);
        doc.setFontSize(12);
        doc.text(`Department Average: ${reportData.department_average} / 5.0`, 14, 30);
        doc.text(`Total Feedback: ${reportData.total_feedback}`, 14, 38);
        doc.text(`Growth Indicator: ${reportData.growth_indicator}`, 14, 46);
        
        // Teachers list
        if (doc.autoTable) {
          const tableData = reportData.teachers.map(t => [
            t.name,
            t.feedback_count.toString(),
            t.avg_rating.toString()
          ]);
          doc.autoTable({
            head: [['Teacher Name', 'Feedback Count', 'Avg Rating']],
            body: tableData,
            startY: 60,
          });
        }
      }
      
      doc.save(`${reportType}-report-${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (err) {
      alert("Error generating PDF.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="glass-card p-6">
      {/* Controls */}
      <div className="flex flex-wrap gap-4 items-end mb-6">
        <div>
          <label className="block text-sm font-medium text-surface-300 mb-2">Report Type</label>
          <select 
            value={reportType} 
            onChange={e => { setReportType(e.target.value); setReportData(null); }}
            className="w-48 bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-surface-100"
          >
            <option value="teacher">Teacher Report</option>
            <option value="department">Department Report</option>
          </select>
        </div>

        {reportType === 'teacher' && (
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">Select Teacher</label>
            <select 
              value={selectedTeacher} 
              onChange={e => setSelectedTeacher(e.target.value)}
              className="w-64 bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-surface-100"
            >
              <option value="">Choose a teacher...</option>
              {teachers?.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        )}

        <button 
          onClick={generateReport}
          disabled={loading}
          className="btn-primary"
        >
          {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-accent-rose/10 border border-accent-rose/20 text-accent-rose rounded-lg">
          {error}
        </div>
      )}

      {emailStatus && (
        <div className="mb-4 p-3 bg-accent-emerald/10 border border-accent-emerald/20 text-accent-emerald rounded-lg">
          {emailStatus}
        </div>
      )}

      {/* Render Report Data */}
      {reportData && (
        <div className="border-t border-surface-700/50 pt-6 animate-fade-in">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-surface-100 font-display">
              {reportType === 'teacher' ? `Report: ${reportData.teacher.name}` : `Department Report`}
            </h3>
            <div className="flex gap-2">
              <button onClick={() => setShowEmailComposer(true)} className="btn-success">Email Report</button>
              <button onClick={exportPDF} disabled={isExporting} className="btn-secondary">
                {isExporting ? 'Exporting...' : 'Export PDF'}
              </button>
            </div>
          </div>

          {reportType === 'teacher' ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30">
                  <p className="text-xs text-surface-400">Total Feedback</p>
                  <p className="text-2xl font-bold text-surface-100">{reportData.total_feedback_count}</p>
                </div>
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30">
                  <p className="text-xs text-surface-400">Average Rating</p>
                  <p className="text-2xl font-bold text-primary-400">{reportData.average_rating}</p>
                </div>
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30">
                  <p className="text-xs text-surface-400">Performance</p>
                  <p className="text-xl font-bold text-accent-cyan mt-1">{reportData.performance_label}</p>
                </div>
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30">
                  <p className="text-xs text-surface-400">Subjects</p>
                  <p className="text-xl font-bold text-surface-100 mt-1">{reportData.subjects.length}</p>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-surface-300 font-medium mb-3">Key Strengths</h4>
                  {reportData.strengths.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-accent-emerald">
                      {reportData.strengths.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  ) : <span className="text-surface-500 text-sm">Not enough data.</span>}
                </div>
                <div>
                  <h4 className="text-surface-300 font-medium mb-3">Areas to Improve</h4>
                  {reportData.weaknesses.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-accent-rose">
                      {reportData.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  ) : <span className="text-surface-500 text-sm">Not enough data.</span>}
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="h-64">
                  <h4 className="text-sm font-medium text-surface-400 mb-2">Rating Distribution</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={Object.entries(reportData.rating_distribution).map(([k,v]) => ({name: `${k} Star`, value: v}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)"/>
                      <XAxis dataKey="name" stroke="#94a3b8" />
                      <Bar dataKey="value" fill={COLORS.primary} radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="h-64">
                  <h4 className="text-sm font-medium text-surface-400 mb-2">Performance Trend</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={reportData.performance_trend.labels.map((l, i) => ({name: l, value: reportData.performance_trend.values[i]}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)"/>
                      <XAxis dataKey="name" stroke="#94a3b8" />
                      <YAxis domain={[0, 5]} stroke="#94a3b8" />
                      <Line type="monotone" dataKey="value" stroke={COLORS.success} strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30">
                  <p className="text-xs text-surface-400">Department Average</p>
                  <p className="text-2xl font-bold text-primary-400">{reportData.department_average}</p>
                </div>
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30">
                  <p className="text-xs text-surface-400">Total Feedback</p>
                  <p className="text-2xl font-bold text-surface-100">{reportData.total_feedback}</p>
                </div>
                <div className="bg-surface-800/50 p-4 rounded-lg border border-surface-700/30 col-span-2">
                  <p className="text-xs text-surface-400">Growth Indicator (Recent vs Older)</p>
                  <div className="flex items-center gap-3">
                    <p className={`text-xl font-bold mt-1 ${
                      reportData.growth_indicator === 'Improving' ? 'text-accent-emerald' : 
                      reportData.growth_indicator === 'Declining' ? 'text-accent-rose' : 'text-surface-100'
                    }`}>
                      {reportData.growth_indicator}
                    </p>
                    <span className="text-sm text-surface-500">
                      ({reportData.recent_avg} vs {reportData.older_avg})
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-surface-400 mb-4">Sentiment Breakdown</h4>
                <div className="flex gap-4">
                  <span className="text-accent-emerald">Pos: {reportData.sentiment_analysis.positive}</span>
                  <span className="text-surface-400">Neu: {reportData.sentiment_analysis.neutral}</span>
                  <span className="text-accent-rose">Neg: {reportData.sentiment_analysis.negative}</span>
                </div>
              </div>

              <div className="border border-surface-700 rounded-lg overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-surface-800/50">
                    <tr>
                      <th className="p-3 text-sm text-surface-400 font-medium">Teacher</th>
                      <th className="p-3 text-sm text-surface-400 font-medium text-right">Feedback Count</th>
                      <th className="p-3 text-sm text-surface-400 font-medium text-right">Avg Rating</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-700/30">
                    {reportData.teachers.map((t, i) => (
                      <tr key={i} className="hover:bg-surface-800/30 transition-colors">
                        <td className="p-3 text-surface-200">{t.name}</td>
                        <td className="p-3 text-surface-300 text-right">{t.feedback_count}</td>
                        <td className="p-3 text-primary-400 font-bold text-right">{t.avg_rating}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {showEmailComposer && (
        <EmailComposer
          teachers={teachers || []}
          subjects={subjects || []}
          onEmailSent={(res) => {
            setEmailStatus(res.message);
            setTimeout(() => setEmailStatus(''), 5000);
          }}
          onClose={() => setShowEmailComposer(false)}
        />
      )}
    </div>
  );
}
