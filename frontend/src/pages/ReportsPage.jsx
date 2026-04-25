import React, { useState, useEffect, useRef } from 'react';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import API from '../api';
import Sidebar from '../components/Sidebar';
import ReportToggle from '../components/ReportToggle';

export default function ReportsPage() {
  const [reportType, setReportType] = useState('teacher');
  const [selectedTeacher, setSelectedTeacher] = useState('');

  const [teachers, setTeachers] = useState([]);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState('');

  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState('');

  // Class report filters
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedYear, setSelectedYear] = useState('');

  // Editable qualitative fields (teacher report)
  const [keyObservations, setKeyObservations] = useState('');
  const [correctiveAction, setCorrectiveAction] = useState('');
  const [observationStatus, setObservationStatus] = useState('Pending');
  const [facultyResponse, setFacultyResponse] = useState('');
  const [hodComments, setHodComments] = useState('');
  const [conclusion, setConclusion] = useState('');
  const [overallRemarks, setOverallRemarks] = useState('');

  const reportRef = useRef(null);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await API.get('sessions/');
        setSessions(res.data);
        const active = res.data.find(s => s.is_active);
        if (active) setSelectedSession(active.id);
        else if (res.data.length > 0) setSelectedSession(res.data[0].id);
      } catch (err) {
        console.error('Failed to load sessions', err);
      } finally {
        setPageLoading(false);
      }
    };
    fetchSessions();
  }, []);

  // Fetch teachers when selectedSession changes
  useEffect(() => {
    if (selectedSession) {
      const fetchTeachers = async () => {
        try {
          const res = await API.get(`hod/teachers/?session_id=${selectedSession}`);
          setTeachers(res.data);
          setSelectedTeacher(''); // Reset teacher when session changes
        } catch (err) {
          console.error('Failed to load teachers', err);
        }
      };
      fetchTeachers();
    }
  }, [selectedSession]);

  // Fetch filter options on class report toggle
  useEffect(() => {
    if (reportType === 'department' && selectedSession) {
      fetchClassReport();
    } else {
      setReportData(null);
    }
  }, [reportType, selectedSession]);

  const fetchClassReport = async () => {
    if (!selectedSession) return;
    setLoading(true);
    setError('');
    setReportData(null);
    try {
      const params = new URLSearchParams();
      if (selectedBranch) params.append('branch', selectedBranch);
      if (selectedYear) params.append('year', selectedYear);
      params.append('session_id', selectedSession);
      const response = await API.get(`hod/department/report/?${params.toString()}`);
      setReportData(response.data);
      setOverallRemarks(response.data.overall_remarks || '');
      if (response.data.available_branches) setBranches(response.data.available_branches);
      if (response.data.available_branches) setBranches(response.data.available_branches);
    } catch (err) {
      setError('Failed to fetch class report.');
    } finally {
      setLoading(false);
    }
  };

  const generateTeacherReport = async () => {
    if (!selectedTeacher || !selectedSession) {
      setError('Please select a teacher to generate their report.');
      return;
    }
    setLoading(true);
    setError('');
    setReportData(null);
    try {
      const response = await API.get(`hod/teacher/${selectedTeacher}/report/?session_id=${selectedSession}`);
      setReportData(response.data);
      // Reset editable fields
      setKeyObservations(response.data.key_observations || '');
      setCorrectiveAction(response.data.corrective_action || '');
      setObservationStatus(response.data.observation_status || 'Pending');
      setFacultyResponse(response.data.faculty_response || '');
      setHodComments(response.data.hod_comments || '');
      setConclusion(response.data.conclusion || '');
    } catch (err) {
      setError('Failed to fetch teacher report.');
    } finally {
      setLoading(false);
    }
  };

  const generateReport = () => {
    if (reportType === 'teacher') {
      generateTeacherReport();
    } else {
      fetchClassReport();
    }
  };

  // ==========================
  // PDF EXPORT — Teacher Report
  // ==========================
  const exportTeacherPDF = () => {
    if (!reportData) return;
    const doc = new jsPDF('landscape', 'mm', 'a4');
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 14;
    let y = 15;

    // Header
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('GOVERNMENT POLYTECHNIC NAGPUR', pageWidth / 2, y, { align: 'center' });
    y += 6;
    doc.setFontSize(10);
    doc.text(reportData.department?.toUpperCase() || 'DEPARTMENT', pageWidth / 2, y, { align: 'center' });
    y += 7;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('FEEDBACK ANALYSIS & ACTION TAKEN REPORT', pageWidth / 2, y, { align: 'center' });
    y += 7;

    // Session and Semester
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(`Session: ${reportData.session || 'N/A'}`, margin, y);
    doc.text(`Semester: ${reportData.semester_label || 'N/A'}`, pageWidth - margin, y, { align: 'right' });
    y += 6;

    // Section 1: Quantitative Analysis
    doc.setFontSize(9);
    doc.setFont('helvetica', 'bold');
    doc.text('1. Feedback Analysis Summary (Quantitative Analysis):', margin, y);
    y += 4;

    const offerings = reportData.offerings || [];
    const tableBody = offerings.map(o => [
      reportData.teacher?.name || '',
      `${o.course_name} (${o.course_code})`,
      o.punctuality?.toFixed(4) || '0',
      o.domain_knowledge?.toFixed(4) || '0',
      o.presentation_skills?.toFixed(4) || '0',
      o.resolve_difficulties?.toFixed(4) || '0',
      o.teaching_aids?.toFixed(4) || '0',
      o.score?.toFixed(4) || '0',
      o.percentage?.toFixed(2) || '0',
    ]);

    doc.autoTable({
      startY: y,
      head: [[
        'Faculty', 'Course Name (Course Code)',
        'Punctuality\n& Discipline', 'Domain\nKnowledge',
        'Presentation\nSkills &\nInteraction\nwith Students',
        'Ability to\nResolve\nDifficulties',
        'Effective\nuse of\nteaching\nAids',
        'Score\n(25)', 'Percent\nage (%)'
      ]],
      body: tableBody,
      theme: 'grid',
      headStyles: {
        fillColor: [255, 200, 200],
        textColor: [0, 0, 0],
        fontStyle: 'bold',
        fontSize: 7,
        halign: 'center',
        valign: 'middle',
      },
      bodyStyles: { fontSize: 8, halign: 'center' },
      columnStyles: {
        0: { cellWidth: 30, halign: 'left' },
        1: { cellWidth: 45, halign: 'left' },
      },
      margin: { left: margin, right: margin },
    });

    y = doc.lastAutoTable.finalY + 6;

    // Section 2: Past Feedback
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('2. Past feedback (Comparative Study):', margin, y);
    const pastNote = reportData.past_comparison?.note || '';
    const pastPerc = reportData.past_comparison?.percentage;
    const pastText = pastPerc != null
      ? `Previous session percentage: ${pastPerc}%`
      : (pastNote || 'No past data available.');
    doc.setFont('helvetica', 'normal');
    doc.text(pastText, margin + 70, y);
    if (pastPerc != null) {
      doc.text(`${pastPerc}%`, pageWidth - margin, y, { align: 'right' });
    }
    y += 8;

    // Section 3: Key Observations
    doc.setFont('helvetica', 'bold');
    doc.text('3. Key Observations:', margin, y);
    doc.setFontSize(8);
    doc.text('(Qualitative Analysis)', margin + 35, y);
    y += 2;

    doc.autoTable({
      startY: y,
      head: [['Key Observations', 'Corrective Action Taken', 'Status (Completed/Ongoing/Pending)']],
      body: [[keyObservations || '-', correctiveAction || '-', observationStatus || 'Pending']],
      theme: 'grid',
      headStyles: { fillColor: [255, 200, 200], textColor: [0, 0, 0], fontStyle: 'bold', fontSize: 8 },
      bodyStyles: { fontSize: 8 },
      margin: { left: margin, right: margin },
    });
    y = doc.lastAutoTable.finalY + 6;

    // Section 4: Faculty Response
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('4. Faculty Response & Recommendations:', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.text(facultyResponse || '-', margin + 75, y);
    y += 8;

    // Section 5: HoD Comments
    doc.setFont('helvetica', 'bold');
    doc.text('5. HoD Comments:', margin, y);
    doc.setFont('helvetica', 'normal');
    const hodLines = doc.splitTextToSize(hodComments || '-', pageWidth - margin * 2 - 40);
    doc.text(hodLines, margin + 40, y);
    y += hodLines.length * 4 + 6;

    // Section 6: Conclusion
    doc.setFont('helvetica', 'bold');
    doc.text('6. Conclusion & Future Improvements:', margin, y);
    doc.setFont('helvetica', 'normal');
    const concLines = doc.splitTextToSize(conclusion || '-', pageWidth - margin * 2 - 65);
    doc.text(concLines, margin + 65, y);
    y += concLines.length * 4 + 10;

    // Signature
    doc.setFontSize(8);
    doc.text(`Date: ${reportData.report_date || ''}`, margin, y);
    doc.text('Sign', margin + 60, y);
    doc.text('HoD', pageWidth - margin - 40, y);
    y += 4;
    doc.setFont('helvetica', 'bold');
    doc.text('Faculty Member', margin + 50, y);
    doc.text(`Dept. of ${reportData.department?.replace(' Department', '') || 'Information Technology'}`, pageWidth - margin - 60, y);

    doc.save(`teacher-report-${reportData.teacher?.name || 'report'}-${new Date().toISOString().split('T')[0]}.pdf`);
  };

  // ==========================
  // PDF EXPORT — Class Report
  // ==========================
  const exportClassPDF = () => {
    if (!reportData) return;
    const doc = new jsPDF('landscape', 'mm', 'a4');
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 14;
    let y = 15;

    // Header
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Government Polytechnic Nagpur', pageWidth / 2, y, { align: 'center' });
    y += 6;
    doc.setFontSize(10);
    doc.text(reportData.department?.toUpperCase() || 'DEPARTMENT', pageWidth / 2, y, { align: 'center' });
    y += 5;
    doc.text('Feedback analysis and Action Taken', pageWidth / 2, y, { align: 'center' });
    y += 7;

    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('Cummulative Report', pageWidth / 2, y, { align: 'center' });
    y += 6;

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(reportData.class_label || '', margin, y);
    doc.text(`Sample: ${reportData.sample_size} (${reportData.participation_rate}% students)`, pageWidth / 2, y, { align: 'center' });
    doc.text(reportData.session_year || '', pageWidth - margin, y, { align: 'right' });
    y += 6;

    // Table
    const teacherRows = (reportData.teachers || []).map(t => [
      t.faculty,
      `${t.course_name}\n(${t.course_code})`,
      t.punctuality?.toFixed(4) || '0',
      t.domain_knowledge?.toFixed(4) || '0',
      t.presentation_skills?.toFixed(4) || '0',
      t.resolve_difficulties?.toFixed(4) || '0',
      t.teaching_aids?.toFixed(4) || '0',
      t.score?.toFixed(4) || '0',
      t.percentage?.toFixed(2) || '0',
    ]);

    doc.autoTable({
      startY: y,
      head: [[
        'Faculty', 'Course Name',
        'Punctuality\n& Discipline', 'Domain\nKnowledge',
        'Presentation\nSkills &\nInteraction\nwith Students',
        'Ability to\nResolve\nDifficulties',
        'Effective\nuse of\nteaching\nAids',
        'Score(2\n5)', 'Percent\nage (%)'
      ]],
      body: teacherRows,
      theme: 'grid',
      headStyles: {
        fillColor: [255, 200, 200],
        textColor: [0, 0, 0],
        fontStyle: 'bold',
        fontSize: 7,
        halign: 'center',
        valign: 'middle',
      },
      bodyStyles: { fontSize: 8, halign: 'center' },
      columnStyles: {
        0: { cellWidth: 30, halign: 'left' },
        1: { cellWidth: 45, halign: 'left' },
      },
      margin: { left: margin, right: margin },
    });

    y = doc.lastAutoTable.finalY + 6;

    // Overall Remarks
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('Overall Remarks:', margin, y);
    doc.setFont('helvetica', 'normal');
    const remarkLines = doc.splitTextToSize(overallRemarks || '', pageWidth - margin * 2 - 35);
    doc.text(remarkLines, margin + 35, y);
    y += remarkLines.length * 4 + 12;

    // Signature
    doc.text(`Date: ${reportData.report_date || ''}`, pageWidth / 2, y, { align: 'center' });
    y += 6;
    doc.setFont('helvetica', 'bold');
    doc.text('HoD', pageWidth - margin - 20, y, { align: 'right' });
    y += 4;
    doc.text(`Dept. of ${reportData.department?.replace(' Department', '') || 'Information Technology'}`, pageWidth - margin - 20, y, { align: 'right' });

    doc.save(`class-report-${reportData.class_label || 'cumulative'}-${new Date().toISOString().split('T')[0]}.pdf`);
  };

  const exportPDF = () => {
    if (reportType === 'teacher') exportTeacherPDF();
    else exportClassPDF();
  };

  // ==========================
  // RENDER
  // ==========================

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
            <p className="text-surface-400 text-sm">Generate GPN-format Feedback Analysis & Action Taken Reports</p>
          </div>
        </header>

        <main className="p-8 max-w-7xl mx-auto">
          {error && (
            <div className="mb-6 p-4 bg-accent-rose/10 border border-accent-rose/20 text-accent-rose rounded-xl flex items-center gap-3">
              <span className="text-xl">⚠️</span> {error}
            </div>
          )}

          {/* Controls */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
            <div className="flex-1">
              <ReportToggle reportType={reportType} setReportType={setReportType} />

              {reportType === 'teacher' ? (
                <div className="flex flex-wrap items-end gap-4 animate-fade-in">
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
                  <div>
                    <label className="block text-sm font-medium text-surface-300 mb-2">Session</label>
                    <select
                      value={selectedSession}
                      onChange={e => setSelectedSession(e.target.value)}
                      className="w-48 bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-surface-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      {sessions.map(s => (
                        <option key={s.id} value={s.id}>{s.name} ({s.year})</option>
                      ))}
                    </select>
                  </div>
                  <button onClick={generateReport} disabled={loading} className="btn-primary">
                    {loading ? 'Generating...' : 'Generate Teacher Report'}
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap items-end gap-4 animate-fade-in">
                  <div>
                    <label className="block text-sm font-medium text-surface-300 mb-2">Branch</label>
                    <select
                      value={selectedBranch}
                      onChange={e => setSelectedBranch(e.target.value)}
                      className="w-48 bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-surface-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">All Branches</option>
                      {branches.map(b => (
                        <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-300 mb-2">Year</label>
                    <select
                      value={selectedYear}
                      onChange={e => setSelectedYear(e.target.value)}
                      className="w-36 bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-surface-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">All Years</option>
                      <option value="1">1st Year</option>
                      <option value="2">2nd Year</option>
                      <option value="3">3rd Year</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-300 mb-2">Session</label>
                    <select
                      value={selectedSession}
                      onChange={e => setSelectedSession(e.target.value)}
                      className="w-48 bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-surface-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      {sessions.map(s => (
                        <option key={s.id} value={s.id}>{s.name} ({s.year})</option>
                      ))}
                    </select>
                  </div>
                  <button onClick={generateReport} disabled={loading} className="btn-primary">
                    {loading ? 'Generating...' : 'Generate Class Report'}
                  </button>
                </div>
              )}
            </div>

            {reportData && reportData.data_available !== false && (
              <button onClick={exportPDF} className="btn-secondary shadow-lg whitespace-nowrap">
                📄 Download PDF
              </button>
            )}
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center p-12">
              <div className="w-10 h-10 border-4 border-surface-700 border-t-primary-500 rounded-full animate-spin"></div>
            </div>
          )}

          {/* No Data Available Banner */}
          {reportData && !loading && reportData.data_available === false && (
            <div className="mb-8 p-8 bg-surface-800/60 border-2 border-dashed border-surface-600 rounded-2xl text-center animate-fade-in">
              <div className="text-5xl mb-4">📊</div>
              <h3 className="text-xl font-bold text-surface-200 mb-2">No Data Available</h3>
              <p className="text-surface-400 text-lg">
                {reportData.no_data_message || `No feedback data was collected for session ${reportData.session}.`}
              </p>
              <p className="text-surface-500 text-sm mt-3">
                Feedback data is not available for this session. Please select a different session that has feedback submissions.
              </p>
            </div>
          )}

          {/* ============================= */}
          {/* TEACHER REPORT — GPN FORMAT */}
          {/* ============================= */}
          {reportData && !loading && reportType === 'teacher' && reportData.data_available !== false && (
            <div ref={reportRef} className="space-y-0 animate-fade-in">
              {/* Institution Header */}
              <div className="bg-white text-black border-2 border-black">
                <div className="text-center py-3 border-b border-black">
                  <h2 className="text-lg font-bold uppercase tracking-wide">Government Polytechnic Nagpur</h2>
                  <p className="text-sm font-semibold uppercase">{reportData.department}</p>
                </div>
                <div className="text-center py-2 border-b border-black">
                  <h3 className="text-sm font-bold uppercase">Feedback Analysis & Action Taken Report</h3>
                </div>
                <div className="flex justify-between px-4 py-2 border-b border-black text-sm">
                  <span><strong>Session:</strong> {reportData.session || 'N/A'}</span>
                  <span><strong>Semester:</strong> {reportData.semester_label || 'N/A'}</span>
                </div>

                {/* Section 1: Quantitative Analysis */}
                <div className="px-4 py-2 border-b border-black">
                  <p className="text-sm font-bold">1. Feedback Analysis Summary (Quantitative Analysis):</p>
                </div>
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="bg-red-200">
                      <th className="border border-black px-2 py-2 text-left font-bold">Faculty</th>
                      <th className="border border-black px-2 py-2 text-left font-bold">Course Name (Course Code)</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Punctuality<br/>& Discipline</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Domain<br/>Knowledge</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Presentation<br/>Skills &<br/>Interaction<br/>with Students</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Ability to<br/>Resolve<br/>Difficulties</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Effective<br/>use of<br/>teaching<br/>Aids</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Score<br/>(25)</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Percent<br/>age (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(reportData.offerings || []).map((o, i) => (
                      <tr key={i}>
                        <td className="border border-black px-2 py-2">{reportData.teacher?.name}</td>
                        <td className="border border-black px-2 py-2">{o.course_name} ({o.course_code})</td>
                        <td className="border border-black px-2 py-2 text-center">{o.punctuality?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{o.domain_knowledge?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{o.presentation_skills?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{o.resolve_difficulties?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{o.teaching_aids?.toFixed(4)}</td>
                        <td className={`border border-black px-2 py-2 text-center ${!o.threshold_met ? 'bg-amber-100 text-amber-900 font-bold' : ''}`}>
                          {o.threshold_met ? o.score?.toFixed(3) : `In Progress (${o.feedback_percentage}%)`}
                        </td>
                        <td className={`border border-black px-2 py-2 text-center ${!o.threshold_met ? 'bg-amber-100 text-amber-900 font-bold' : ''}`}>
                          {o.threshold_met ? o.percentage?.toFixed(2) : `In Progress`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Threshold Warnings */}
                {reportData.offerings?.some(o => !o.threshold_met) && (
                  <div className="bg-amber-50 border-b border-black p-4 text-amber-800 text-sm flex items-center gap-2">
                    <span className="text-lg">⚠️</span>
                    <div>
                      <p className="font-bold">Statistical Validity Note:</p>
                      <p>Some courses have not yet reached the 30% feedback threshold. Quantitative scores for these courses are hidden to ensure report accuracy.</p>
                    </div>
                  </div>
                )}

                {/* Section 2: Past Feedback */}
                <div className="flex border-t border-black text-sm">
                  <div className="font-bold px-4 py-2 border-r border-black w-1/3">
                    2. Past feedback (Comparative Study):
                  </div>
                  <div className="px-4 py-2 flex-1">
                    {reportData.past_comparison?.note || 
                     (reportData.past_comparison?.percentage != null 
                       ? `Previous session: ${reportData.past_comparison.session_name}, Percentage: ${reportData.past_comparison.percentage}%`
                       : 'No past data available.')}
                  </div>
                  <div className="px-4 py-2 border-l border-black font-bold w-20 text-center">
                    {reportData.past_comparison?.percentage != null ? `${reportData.past_comparison.percentage}%` : 'N/A'}
                  </div>
                </div>

                {/* Section 3: Key Observations */}
                <div className="border-t border-black">
                  <div className="px-4 py-2 border-b border-black">
                    <span className="font-bold text-sm">3. Key Observations:</span>
                    <span className="text-sm ml-2">(Qualitative Analysis)</span>
                  </div>
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr>
                        <th className="border border-black px-2 py-2 text-left w-1/3">Key Observations</th>
                        <th className="border border-black px-2 py-2 text-left w-1/3">Corrective Action Taken</th>
                        <th className="border border-black px-2 py-2 text-left w-1/3">Status (Completed/Ongoing/Pending)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-black px-2 py-1">
                          <textarea
                            value={keyObservations}
                            onChange={e => setKeyObservations(e.target.value)}
                            className="w-full bg-transparent resize-none outline-none text-sm min-h-[40px]"
                            placeholder="Enter key observations..."
                          />
                        </td>
                        <td className="border border-black px-2 py-1">
                          <textarea
                            value={correctiveAction}
                            onChange={e => setCorrectiveAction(e.target.value)}
                            className="w-full bg-transparent resize-none outline-none text-sm min-h-[40px]"
                            placeholder="Enter corrective actions..."
                          />
                        </td>
                        <td className="border border-black px-2 py-1">
                          <select
                            value={observationStatus}
                            onChange={e => setObservationStatus(e.target.value)}
                            className="w-full bg-transparent outline-none text-sm"
                          >
                            <option value="Pending">Pending</option>
                            <option value="Ongoing">Ongoing</option>
                            <option value="Completed">Completed</option>
                          </select>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Section 4: Faculty Response */}
                <div className="flex border-t border-black text-sm">
                  <div className="font-bold px-4 py-2 border-r border-black w-1/3">
                    4. Faculty Response & Recommendations
                  </div>
                  <div className="px-2 py-1 flex-1">
                    <textarea
                      value={facultyResponse}
                      onChange={e => setFacultyResponse(e.target.value)}
                      className="w-full bg-transparent resize-none outline-none text-sm min-h-[40px]"
                      placeholder="Faculty member's response..."
                    />
                  </div>
                </div>

                {/* Section 5: HoD Comments */}
                <div className="flex border-t border-black text-sm">
                  <div className="font-bold px-4 py-2 border-r border-black w-1/3">
                    5. HoD Comments:
                  </div>
                  <div className="px-2 py-1 flex-1">
                    <textarea
                      value={hodComments}
                      onChange={e => setHodComments(e.target.value)}
                      className="w-full bg-transparent resize-none outline-none text-sm min-h-[50px]"
                      placeholder="Enter HoD comments..."
                    />
                  </div>
                </div>

                {/* Section 6: Conclusion */}
                <div className="flex border-t border-black text-sm">
                  <div className="font-bold px-4 py-2 border-r border-black w-1/3">
                    6. Conclusion & Future Improvements
                  </div>
                  <div className="px-2 py-1 flex-1">
                    <textarea
                      value={conclusion}
                      onChange={e => setConclusion(e.target.value)}
                      className="w-full bg-transparent resize-none outline-none text-sm min-h-[50px]"
                      placeholder="Student feedback is collected, analyzed and corrective action has been taken..."
                    />
                  </div>
                </div>

                {/* Signature Block */}
                <div className="flex justify-between border-t border-black px-4 py-3 text-sm">
                  <div>
                    <p>Date: {reportData.report_date}</p>
                    <p className="mt-4 font-bold">Sign</p>
                    <p className="font-bold">Faculty Member</p>
                  </div>
                  <div className="text-right">
                    <p className="mt-4 font-bold">HoD</p>
                    <p className="font-bold">Dept. of {reportData.department?.replace(' Department', '') || 'Information Technology'}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================= */}
          {/* CLASS (CUMULATIVE) REPORT */}
          {/* ============================= */}
          {reportData && !loading && reportType === 'department' && reportData.data_available !== false && (
            <div ref={reportRef} className="space-y-0 animate-fade-in">
              <div className="bg-white text-black border-2 border-black">
                {/* Header */}
                <div className="text-center py-3 border-b border-black">
                  <h2 className="text-lg font-bold">Government Polytechnic Nagpur</h2>
                  <p className="text-sm font-semibold uppercase">{reportData.department}</p>
                  <p className="text-sm font-semibold">Feedback analysis and Action Taken</p>
                </div>
                <div className="text-center py-2 border-b border-black">
                  <h3 className="text-sm font-bold">Cummulative Report</h3>
                </div>
                <div className="flex justify-between px-4 py-2 border-b border-black text-sm">
                  <span><strong>{reportData.class_label}</strong></span>
                  <span><strong>{reportData.session_year}</strong></span>
                  <span><strong>Sample: {reportData.sample_size} ({reportData.participation_rate}% students)</strong></span>
                </div>

                {/* Branch Comparisons Summary */}
                {reportData.branch_comparisons?.length > 0 && (
                  <div className="px-4 py-4 border-b border-black bg-gray-50">
                    <h4 className="text-sm font-bold mb-3 uppercase flex items-center gap-2">
                       📊 Branch-wise Performance Benchmarking
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {reportData.branch_comparisons.map((bc, idx) => (
                        <div key={idx} className="border border-black p-2 bg-white flex flex-col items-center">
                          <span className="text-xs font-bold text-gray-600">{bc.branch_code}</span>
                          <span className="text-lg font-black text-red-700">{bc.average?.toFixed(2)}</span>
                          <span className="text-[10px] text-gray-500">{bc.participation} Responses</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Table */}
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="bg-red-200">
                      <th className="border border-black px-2 py-2 text-left font-bold">Faculty</th>
                      <th className="border border-black px-2 py-2 text-left font-bold">Course Name</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Punctuality<br/>& Discipline</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Domain<br/>Knowledge</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Presentation<br/>Skills &<br/>Interaction<br/>with Students</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Ability to<br/>Resolve<br/>Difficulties</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Effective<br/>use of<br/>teaching<br/>Aids</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Score(2<br/>5)</th>
                      <th className="border border-black px-2 py-2 text-center font-bold">Percent<br/>age (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(reportData.teachers || []).map((t, i) => (
                      <tr key={i}>
                        <td className="border border-black px-2 py-2">{t.faculty}</td>
                        <td className="border border-black px-2 py-2">{t.course_name}<br/>({t.course_code})</td>
                        <td className="border border-black px-2 py-2 text-center">{t.punctuality?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{t.domain_knowledge?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{t.presentation_skills?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{t.resolve_difficulties?.toFixed(4)}</td>
                        <td className="border border-black px-2 py-2 text-center">{t.teaching_aids?.toFixed(4)}</td>
                        <td className={`border border-black px-2 py-2 text-center ${!t.threshold_met ? 'bg-amber-100 text-amber-900 font-bold' : ''}`}>
                          {t.threshold_met ? t.score?.toFixed(4) : `In Progress (${t.feedback_percentage}%)`}
                        </td>
                        <td className={`border border-black px-2 py-2 text-center ${!t.threshold_met ? 'bg-amber-100 text-amber-900 font-bold' : ''}`}>
                          {t.threshold_met ? t.percentage?.toFixed(2) : `In Progress`}
                        </td>
                      </tr>
                    ))}
                    {(!reportData.teachers || reportData.teachers.length === 0) && (
                      <tr>
                        <td colSpan="9" className="border border-black px-4 py-6 text-center text-gray-500">
                          No faculty data found for the selected filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {/* Overall Remarks */}
                <div className="border-t border-black px-4 py-2">
                  <p className="text-sm font-bold mb-1">Overall Remarks:</p>
                  <textarea
                    value={overallRemarks}
                    onChange={e => setOverallRemarks(e.target.value)}
                    className="w-full bg-transparent resize-none outline-none text-sm min-h-[50px]"
                    placeholder="Enter overall remarks..."
                  />
                </div>

                {/* Signature */}
                <div className="flex justify-end border-t border-black px-4 py-3 text-sm">
                  <div className="text-center">
                    <p>Date: {reportData.report_date}</p>
                    <p className="mt-4 font-bold">HoD</p>
                    <p className="font-bold">Dept. of {reportData.department?.replace(' Department', '') || 'Information Technology'}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
