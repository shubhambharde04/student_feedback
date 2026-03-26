import React, { useState, useEffect } from 'react';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import API from '../api';
import Sidebar from '../components/Sidebar';
import ReportToggle from '../components/ReportToggle';
import EmailComposer from '../components/EmailComposer';
import ExpandableChartModal from '../components/ExpandableChartModal';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend
} from 'recharts';

const COLORS = {
  primary: '#6366f1',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444'
};
const PIE_COLORS = ['#10b981', '#94a3b8', '#ef4444'];

export default function ReportsPage() {
  const [reportType, setReportType] = useState('teacher'); // 'teacher' or 'department'
  const [selectedTeacher, setSelectedTeacher] = useState('');
  
  const [teachers, setTeachers] = useState([]);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState('');

  const [showEmailComposer, setShowEmailComposer] = useState(false);
  const [emailStatus, setEmailStatus] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const [activeChart, setActiveChart] = useState(null);

  useEffect(() => {
    // Initial fetch for teachers dropdown
    const fetchTeachers = async () => {
      try {
        const response = await API.get('hod/teachers/');
        setTeachers(response.data);
      } catch (err) {
        console.error('Failed to load teachers', err);
      } finally {
        setPageLoading(false);
      }
    };
    fetchTeachers();
  }, []);

  useEffect(() => {
    // Dynamically fetch department report on toggle if department selected
    if (reportType === 'department') {
      generateReport();
    } else {
      setReportData(null); // Clear data when switching back to teacher without selection
    }
  }, [reportType]);

  const generateReport = async () => {
    if (reportType === 'teacher' && !selectedTeacher) {
      setError('Please select a teacher to generate their report.');
      return;
    }

    setLoading(true);
    setError('');
    setReportData(null);
    setActiveChart(null);
    
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

  const chartTooltipStyle = {
    backgroundColor: 'rgba(30, 41, 59, 0.95)',
    borderColor: 'rgba(148, 163, 184, 0.15)',
    borderRadius: '0.5rem',
    color: '#f8fafc',
  };

  if (pageLoading) {
    return (
      <div className="flex dashboard-layout h-screen bg-surface-900">
        <Sidebar role="hod" />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-12 h-12 border-4 border-surface-700 border-t-primary-500 rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex dashboard-layout min-h-screen bg-surface-900">
      <Sidebar role="hod" />
      
      <div className="flex-1 overflow-auto">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-surface-900/80 backdrop-blur-md border-b border-surface-700/50 px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-surface-100 font-display">System Reports</h1>
            <p className="text-surface-400 text-sm">Generate and analyze highly detailed performance reports.</p>
          </div>
        </header>

        <main className="p-8 max-w-7xl mx-auto">
          {error && (
            <div className="mb-6 p-4 bg-accent-rose/10 border border-accent-rose/20 text-accent-rose rounded-xl flex items-center gap-3">
              <span className="text-xl">⚠️</span> {error}
            </div>
          )}

          {emailStatus && (
            <div className="mb-6 p-4 bg-accent-emerald/10 border border-accent-emerald/20 text-accent-emerald rounded-xl flex items-center gap-3">
              <span className="text-xl">✅</span> {emailStatus}
            </div>
          )}

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
            <div className="flex-1">
              <ReportToggle reportType={reportType} setReportType={setReportType} />
              
              {reportType === 'teacher' && (
                <div className="flex items-end gap-4 animate-fade-in">
                  <div className="w-72">
                    <label className="block text-sm font-medium text-surface-300 mb-2">Select Teacher</label>
                    <select 
                      value={selectedTeacher} 
                      onChange={e => setSelectedTeacher(e.target.value)}
                      className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-surface-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">Choose a teacher...</option>
                      {teachers?.map(t => (
                        <option key={t.id} value={t.id}>{t.name} ({t.email})</option>
                      ))}
                    </select>
                  </div>
                  <button 
                    onClick={generateReport}
                    disabled={loading}
                    className="btn-primary"
                  >
                    {loading ? 'Generating...' : 'Generate Teacher Report'}
                  </button>
                </div>
              )}
            </div>

            {reportData && (
              <div className="flex gap-3">
                <button onClick={() => setShowEmailComposer(true)} className="btn-success shadow-lg shadow-accent-emerald/20">
                  Email Report
                </button>
                <button onClick={exportPDF} disabled={isExporting} className="btn-secondary">
                  {isExporting ? 'Exporting...' : 'Download PDF'}
                </button>
              </div>
            )}
          </div>

          {/* Loading Indicator */}
          {loading && (
            <div className="flex items-center justify-center p-12">
              <div className="w-10 h-10 border-4 border-surface-700 border-t-primary-500 rounded-full animate-spin"></div>
            </div>
          )}

          {/* Report Content */}
          {reportData && !loading && (
            <div className="space-y-8 animate-fade-in">
              {reportType === 'teacher' ? (
                // TEACHER REPORT BODY
                <>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="glass-card p-6">
                      <p className="text-sm font-medium text-surface-400">Total Feedback</p>
                      <p className="text-3xl font-bold text-surface-100 mt-2">{reportData.total_feedback_count}</p>
                    </div>
                    <div className="glass-card p-6 border-l-4 border-primary-500">
                      <p className="text-sm font-medium text-surface-400">Average Rating</p>
                      <p className="text-3xl font-bold text-primary-400 mt-2">{reportData.average_rating}</p>
                    </div>
                    <div className="glass-card p-6 border-l-4 border-accent-cyan">
                      <p className="text-sm font-medium text-surface-400">Performance</p>
                      <p className="text-2xl font-bold text-accent-cyan mt-2 truncate">{reportData.performance_label}</p>
                    </div>
                    <div className="glass-card p-6">
                      <p className="text-sm font-medium text-surface-400">Subjects Handled</p>
                      <p className="text-3xl font-bold text-surface-100 mt-2">{reportData.subjects.length}</p>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="glass-card p-6 bg-surface-800/80">
                      <h4 className="text-lg font-semibold text-surface-100 mb-4 flex items-center gap-2">
                        <span className="text-accent-emerald">🚀</span> Key Strengths
                      </h4>
                      {reportData.strengths.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {reportData.strengths.map((s, i) => (
                            <span key={i} className="px-3 py-1.5 bg-accent-emerald/10 text-accent-emerald rounded-lg text-sm font-medium border border-accent-emerald/20">
                              {s}
                            </span>
                          ))}
                        </div>
                      ) : <span className="text-surface-500 text-sm">Not enough data to determine strengths.</span>}
                    </div>
                    <div className="glass-card p-6 bg-surface-800/80">
                      <h4 className="text-lg font-semibold text-surface-100 mb-4 flex items-center gap-2">
                        <span className="text-accent-rose">🎯</span> Areas to Improve
                      </h4>
                      {reportData.weaknesses.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {reportData.weaknesses.map((w, i) => (
                            <span key={i} className="px-3 py-1.5 bg-accent-rose/10 text-accent-rose rounded-lg text-sm font-medium border border-accent-rose/20">
                              {w}
                            </span>
                          ))}
                        </div>
                      ) : <span className="text-surface-500 text-sm">Not enough data to determine areas to improve.</span>}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-20">
                    <div className="h-[350px]">
                      <ExpandableChartModal title="Rating Distribution">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={Object.entries(reportData.rating_distribution).map(([k,v]) => ({name: `${k} Star`, value: v}))} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)"/>
                            <XAxis dataKey="name" stroke="#94a3b8" />
                            <Tooltip contentStyle={chartTooltipStyle}/>
                            <Bar dataKey="value" fill={COLORS.primary} radius={[4,4,0,0]} barSize={50} />
                          </BarChart>
                        </ResponsiveContainer>
                      </ExpandableChartModal>
                    </div>

                    <div className="h-[350px]">
                      <ExpandableChartModal title="Performance Trend (Monthly)">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={reportData.performance_trend.labels.map((l, i) => ({name: l, value: reportData.performance_trend.values[i]}))} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)"/>
                            <XAxis dataKey="name" stroke="#94a3b8" />
                            <YAxis domain={[0, 5]} stroke="#94a3b8" />
                            <Tooltip contentStyle={chartTooltipStyle}/>
                            <Line type="monotone" dataKey="value" stroke={COLORS.success} strokeWidth={4} dot={{ r: 6, strokeWidth: 2 }} activeDot={{ r: 8 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </ExpandableChartModal>
                    </div>
                  </div>
                </>
              ) : (
                // DEPARTMENT REPORT BODY
                <>
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                    <div className="glass-card p-6 border-l-4 border-primary-500">
                      <p className="text-sm font-medium text-surface-400">Department Average</p>
                      <p className="text-4xl font-bold text-primary-400 mt-2">{reportData.department_average}</p>
                    </div>
                    <div className="glass-card p-6">
                      <p className="text-sm font-medium text-surface-400">Total Feedback</p>
                      <p className="text-4xl font-bold text-surface-100 mt-2">{reportData.total_feedback}</p>
                    </div>
                    <div className={`glass-card p-6 border-l-4 ${
                      reportData.growth_indicator === 'Improving' ? 'border-accent-emerald' : 
                      reportData.growth_indicator === 'Declining' ? 'border-accent-rose' : 'border-surface-400'
                    }`}>
                      <p className="text-sm font-medium text-surface-400">Growth Status (Recent vs Old)</p>
                      <div className="flex items-center gap-3 mt-2">
                        <p className={`text-3xl font-bold ${
                          reportData.growth_indicator === 'Improving' ? 'text-accent-emerald' : 
                          reportData.growth_indicator === 'Declining' ? 'text-accent-rose' : 'text-surface-100'
                        }`}>
                          {reportData.growth_indicator}
                        </p>
                        <span className="text-sm text-surface-500 px-2 py-1 bg-surface-800 rounded">
                          {reportData.older_avg} → {reportData.recent_avg}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-20">
                     <div className="h-[350px]">
                       <ExpandableChartModal title="Teacher Performance Overview">
                         <ResponsiveContainer width="100%" height="100%">
                           <BarChart data={reportData.teachers} margin={{ top: 20, right: 30, left: 0, bottom: 25 }}>
                             <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)"/>
                             <XAxis dataKey="name" stroke="#94a3b8" />
                             <YAxis domain={[0, 5]} stroke="#94a3b8" />
                             <Tooltip contentStyle={chartTooltipStyle} />
                             <Bar dataKey="avg_rating" fill={COLORS.primary} radius={[4,4,0,0]} barSize={40} />
                           </BarChart>
                         </ResponsiveContainer>
                       </ExpandableChartModal>
                     </div>

                      <div className="h-[350px]">
                        <ExpandableChartModal title="Department Sentiment Analysis">
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={[
                                  {name: 'Positive', value: reportData.sentiment_analysis.positive},
                                  {name: 'Neutral', value: reportData.sentiment_analysis.neutral},
                                  {name: 'Negative', value: reportData.sentiment_analysis.negative}
                                ]}
                                cx="50%" cy="50%" outerRadius={110} innerRadius={60} dataKey="value"
                                labelLine={{ stroke: '#94a3b8' }}
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                              >
                                {PIE_COLORS.map((color, index) => <Cell key={index} fill={color} />)}
                              </Pie>
                              <Tooltip contentStyle={chartTooltipStyle}/>
                              <Legend wrapperStyle={{ color: '#94a3b8' }}/>
                            </PieChart>
                          </ResponsiveContainer>
                        </ExpandableChartModal>
                      </div>
                  </div>

                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-20">
                      <div className="h-[350px]">
                        <ExpandableChartModal title="Year-wise Performance" subtitle="Average rating across academic years">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={reportData.year_performance} margin={{ top: 20, right: 30, left: 0, bottom: 25 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)"/>
                              <XAxis dataKey="year" stroke="#94a3b8" />
                              <YAxis domain={[0, 5]} stroke="#94a3b8" />
                              <Tooltip contentStyle={chartTooltipStyle} />
                              <Bar dataKey="avg_rating" fill={COLORS.success} radius={[4,4,0,0]} barSize={40} />
                            </BarChart>
                          </ResponsiveContainer>
                        </ExpandableChartModal>
                      </div>

                      <div className="h-[350px]">
                        <ExpandableChartModal title="Branch Performance" subtitle="Average rating across branches">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={reportData.branch_performance} margin={{ top: 20, right: 30, left: 0, bottom: 25 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)"/>
                              <XAxis dataKey="name" stroke="#94a3b8" />
                              <YAxis domain={[0, 5]} stroke="#94a3b8" />
                              <Tooltip contentStyle={chartTooltipStyle} />
                              <Bar dataKey="avg_rating" fill={COLORS.warning} radius={[4,4,0,0]} barSize={40} />
                            </BarChart>
                          </ResponsiveContainer>
                        </ExpandableChartModal>
                      </div>
                  </div>
                </>
              )}
            </div>
          )}
        </main>
      </div>

      {showEmailComposer && (
        <EmailComposer
          teachers={teachers}
          subjects={[]} // subjects not strictly needed if we are sending via emails array
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
