import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import API from "../api";
import Sidebar from "../components/Sidebar";
import FeedbackWindowManager from "../components/FeedbackWindowManager";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import ChartModal from "../components/ChartModal";
import { Maximize2 } from "lucide-react";
import { motion } from "framer-motion";

const CHART_COLORS = ['#6366f1', '#22d3ee', '#a78bfa', '#f59e0b', '#10b981', '#ef4444', '#ec4899', '#8b5cf6'];
const PIE_COLORS = ['#10b981', '#94a3b8', '#ef4444'];
const RATING_PIE_COLORS = ['#6366f1', '#22d3ee', '#f59e0b', '#ef4444', '#10b981'];

const chartTooltipStyle = {
  backgroundColor: 'rgba(30, 41, 59, 0.95)',
  borderColor: 'rgba(148, 163, 184, 0.15)',
  borderRadius: '0.5rem',
  color: '#f8fafc',
};

export default function HODDashboard() {
  const [overview, setOverview] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Comparison states
  const [comparisonData, setComparisonData] = useState(null);
  const [comparisonType, setComparisonType] = useState('department'); // 'department' or 'branch'
  const [currentSemester, setCurrentSemester] = useState(6);
  const [previousSemester, setPreviousSemester] = useState(5);
  const [departmentId, setDepartmentId] = useState(1);
  const [loadingComparison, setLoadingComparison] = useState(false);
  
  const location = useLocation();
  const [activeSection, setActiveSection] = useState(location.state?.activeSection || "overview");
  
  const [activeChart, setActiveChart] = useState(null);
  const [expandedChart, setExpandedChart] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const results = await Promise.allSettled([
          API.get("hod/dashboard/"),
          API.get("hod/teachers/"),
          API.get("hod/analytics/"),
          API.get("hod/statistics/"),
          API.get("auth/profile/")
        ]);
        if (results[0].status === 'fulfilled') setOverview(results[0].value.data);
        if (results[1].status === 'fulfilled') setTeachers(results[1].value.data);
        if (results[2].status === 'fulfilled') setAnalytics(results[2].value.data);
        if (results[3].status === 'fulfilled') setStatistics(results[3].value.data);
        if (results[4].status === 'fulfilled') setUser(results[4].value.data.user);

        // Log failures for debugging
        const names = ['overview', 'teachers', 'analytics', 'statistics', 'profile'];
        results.forEach((r, i) => {
          if (r.status === 'rejected') {
            console.error(`Failed to load ${names[i]}:`, r.reason);
          }
        });
      } catch (err) {
        console.error("Error fetching HOD data:", err);
        setError("Failed to load dashboard data. Please ensure the backend is running.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Fetch comparison data when comparison section is active
  useEffect(() => {
    if (activeSection === 'comparison') {
      fetchComparisonData();
    }
  }, [activeSection, comparisonType, currentSemester, previousSemester, departmentId]);

  const fetchComparisonData = async () => {
    setLoadingComparison(true);
    try {
      let url;
      if (comparisonType === 'department') {
        url = `/analytics/department/?department_id=${departmentId}&current_semester=${currentSemester}&previous_semester=${previousSemester}`;
      } else {
        url = `/analytics/branch-comparison/?department_id=${departmentId}&current_semester=${currentSemester}&previous_semester=${previousSemester}`;
      }
      
      const response = await API.get(url);
      setComparisonData(response.data);
    } catch (err) {
      console.error('Error fetching comparison data:', err);
      setError('Failed to load comparison data');
    } finally {
      setLoadingComparison(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="glass-card p-8 max-w-md text-center">
          <p className="text-accent-rose text-lg font-medium mb-2">⚠️ Error</p>
          <p className="text-surface-400">{error}</p>
        </div>
      </div>
    );
  }

  // ============================================================
  // OVERVIEW SECTION
  // ============================================================
  const renderOverview = () => (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-surface-100 font-display">Dashboard Overview</h2>
        <p className="text-surface-400 text-sm mt-1">High-level department metrics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8 stagger">
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-primary-500)' }}>
          <p className="text-sm text-surface-400 mb-1">Total Feedback</p>
          <p className="text-3xl font-bold text-primary-400 font-display">{overview?.total_feedback || 0}</p>
        </div>
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-cyan)' }}>
          <p className="text-sm text-surface-400 mb-1">Total Teachers</p>
          <p className="text-3xl font-bold text-accent-cyan font-display">{overview?.total_teachers || 0}</p>
        </div>
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-violet)' }}>
          <p className="text-sm text-surface-400 mb-1">Total Subjects</p>
          <p className="text-3xl font-bold text-accent-violet font-display">{overview?.total_subjects || 0}</p>
        </div>
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-amber)' }}>
          <p className="text-sm text-surface-400 mb-1">Dept Average</p>
          <p className="text-3xl font-bold text-accent-amber font-display">
            {overview?.average_rating || 0} <span className="text-lg">/ 5.0</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 stagger">
        {overview?.top_teacher && (
          <div className="glass-card p-6 border-l-4 border-l-accent-emerald animate-fade-in">
            <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-2">Top Performer</h3>
            <div className="flex justify-between items-end">
              <div>
                <p className="text-xl font-bold text-surface-100 font-display">{overview.top_teacher.name}</p>
                <p className="text-sm text-surface-500">{overview.top_teacher.email}</p>
              </div>
              <div className="text-2xl font-bold text-accent-emerald">{overview.top_teacher.avg_rating} ⭐</div>
            </div>
          </div>
        )}

        {overview?.lowest_teacher && (
          <div className="glass-card p-6 border-l-4 border-l-accent-rose animate-fade-in">
            <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-2">Needs Improvement</h3>
            <div className="flex justify-between items-end">
              <div>
                <p className="text-xl font-bold text-surface-100 font-display">{overview.lowest_teacher.name}</p>
                <p className="text-sm text-surface-500">{overview.lowest_teacher.email}</p>
              </div>
              <div className="text-2xl font-bold text-accent-rose">{overview.lowest_teacher.avg_rating} ⭐</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // ============================================================
  // COMPARISON SECTION
  // ============================================================
  const renderComparison = () => (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-surface-100 font-display">Feedback Comparison</h2>
        <p className="text-surface-400 text-sm mt-1">Compare feedback performance across semesters.</p>
      </div>

      {/* Controls */}
      <div className="glass-card p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Toggle between department and branch comparison */}
          <div>
            <label className="block text-sm font-medium text-surface-400 mb-2">Comparison Type</label>
            <div className="flex bg-surface-800 rounded-lg p-1">
              <button
                className={`flex-1 py-2 px-4 rounded-md transition-all ${
                  comparisonType === 'department'
                    ? 'bg-primary-500 text-white'
                    : 'text-surface-400 hover:text-white'
                }`}
                onClick={() => setComparisonType('department')}
              >
                Department
              </button>
              <button
                className={`flex-1 py-2 px-4 rounded-md transition-all ${
                  comparisonType === 'branch'
                    ? 'bg-primary-500 text-white'
                    : 'text-surface-400 hover:text-white'
                }`}
                onClick={() => setComparisonType('branch')}
              >
                Branch-wise
              </button>
            </div>
          </div>

          {/* Department Selection */}
          <div>
            <label className="block text-sm font-medium text-surface-400 mb-2">Department</label>
            <select
              value={departmentId}
              onChange={(e) => setDepartmentId(Number(e.target.value))}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value={1}>IT-AIML</option>
              <option value={2}>Computer Science</option>
            </select>
          </div>

          {/* Current Semester */}
          <div>
            <label className="block text-sm font-medium text-surface-400 mb-2">Current Semester</label>
            <select
              value={currentSemester}
              onChange={(e) => setCurrentSemester(Number(e.target.value))}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8].map(sem => (
                <option key={sem} value={sem}>Semester {sem}</option>
              ))}
            </select>
          </div>

          {/* Previous Semester */}
          <div>
            <label className="block text-sm font-medium text-surface-400 mb-2">Previous Semester</label>
            <select
              value={previousSemester}
              onChange={(e) => setPreviousSemester(Number(e.target.value))}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8].map(sem => (
                <option key={sem} value={sem}>Semester {sem}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Comparison Results */}
      {loadingComparison ? (
        <div className="glass-card p-12 text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-surface-400">Loading comparison data...</p>
        </div>
      ) : comparisonData ? (
        <div className="grid grid-cols-1 gap-6">
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-surface-100 mb-4">
              {comparisonType === 'department' ? 'Department Performance' : 'Branch-wise Performance'}
            </h3>
            
            {comparisonType === 'department' ? (
              // Department Comparison View
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-surface-800 rounded-lg">
                    <p className="text-sm text-surface-400">Current Avg</p>
                    <p className="text-2xl font-bold text-primary-400">{comparisonData.current_avg}</p>
                  </div>
                  <div className="text-center p-4 bg-surface-800 rounded-lg">
                    <p className="text-sm text-surface-400">Previous Avg</p>
                    <p className="text-2xl font-bold text-accent-cyan">{comparisonData.previous_avg}</p>
                  </div>
                  <div className="text-center p-4 bg-surface-800 rounded-lg">
                    <p className="text-sm text-surface-400">Improvement</p>
                    <p className={`text-2xl font-bold ${
                      comparisonData.improvement > 0 ? 'text-accent-emerald' : 
                      comparisonData.improvement < 0 ? 'text-accent-rose' : 'text-surface-400'
                    }`}>
                      {comparisonData.improvement > 0 ? '+' : ''}{comparisonData.improvement}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-surface-800 rounded-lg">
                    <p className="text-sm text-surface-400">Total Feedback</p>
                    <p className="text-2xl font-bold text-accent-violet">
                      {comparisonData.total_feedback_current}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              // Branch Comparison View
              <div>
                {comparisonData.branches && comparisonData.branches.length > 0 ? (
                  <div className="space-y-4">
                    {comparisonData.branches.map((branch, index) => (
                      <div key={branch.branch_id || index} className="p-4 bg-surface-800 rounded-lg">
                        <div className="flex justify-between items-center mb-2">
                          <h4 className="font-semibold text-surface-100">{branch.branch}</h4>
                          <span className={`px-2 py-1 rounded text-sm font-medium ${
                            branch.improvement > 0 ? 'bg-accent-emerald/20 text-accent-emerald' :
                            branch.improvement < 0 ? 'bg-accent-rose/20 text-accent-rose' :
                            'bg-surface-700 text-surface-400'
                          }`}>
                            {branch.improvement > 0 ? '+' : ''}{branch.improvement}
                          </span>
                        </div>
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-surface-400">Current</p>
                            <p className="font-medium text-primary-400">{branch.current_avg}</p>
                          </div>
                          <div>
                            <p className="text-surface-400">Previous</p>
                            <p className="font-medium text-accent-cyan">{branch.previous_avg}</p>
                          </div>
                          <div>
                            <p className="text-surface-400">Current Total</p>
                            <p className="font-medium text-accent-violet">{branch.current_total}</p>
                          </div>
                          <div>
                            <p className="text-surface-400">Previous Total</p>
                            <p className="font-medium text-accent-amber">{branch.previous_total}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-surface-400 py-8">
                    No branch data available for the selected semesters.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Summary Stats for Branch Comparison */}
          {comparisonType === 'branch' && comparisonData.summary && (
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-surface-100 mb-4">Summary</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-surface-800 rounded-lg">
                  <p className="text-sm text-surface-400">Total Branches</p>
                  <p className="text-2xl font-bold text-primary-400">{comparisonData.summary.total_branches}</p>
                </div>
                <div className="text-center p-4 bg-surface-800 rounded-lg">
                  <p className="text-sm text-surface-400">Improved</p>
                  <p className="text-2xl font-bold text-accent-emerald">{comparisonData.summary.branches_with_improvement}</p>
                </div>
                <div className="text-center p-4 bg-surface-800 rounded-lg">
                  <p className="text-sm text-surface-400">Declined</p>
                  <p className="text-2xl font-bold text-accent-rose">{comparisonData.summary.branches_with_decline}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card p-12 text-center">
          <p className="text-surface-400">No comparison data available.</p>
        </div>
      )}
    </div>
  );

  // ============================================================
  // TEACHERS SECTION
  // ============================================================
  const renderTeachers = () => (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-surface-100 font-display">Teachers Directory</h2>
        <p className="text-surface-400 text-sm mt-1">Select a teacher to view detailed performance and generate reports.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger">
        {teachers.map((teacher) => {
          const performanceClass = 
            teacher.performance === "Excellent" ? "badge-excellent" :
            teacher.performance === "Good" ? "badge-good" :
            teacher.performance === "Average" ? "badge-average" :
            teacher.performance === "Poor" ? "badge-poor" : "badge-neutral";

          return (
            <div 
              key={teacher.id} 
              onClick={() => navigate(`/hod/teacher/${teacher.id}`)}
              className="glass-card p-6 cursor-pointer hover:bg-surface-800/40 transition-colors group animate-fade-in"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="min-w-0 pr-2">
                  <h3 className="text-lg font-bold text-surface-100 font-display truncate group-hover:text-primary-400 transition-colors">
                    {teacher.name}
                  </h3>
                  <p className="text-sm text-surface-500 truncate">{teacher.email}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-surface-800 flex items-center justify-center text-primary-400 font-bold flex-shrink-0">
                  {teacher.name.charAt(0)}
                </div>
              </div>
              
              <div className="flex justify-between items-center mb-4">
                <div>
                  <p className="text-xs text-surface-500 mb-0.5">Subjects</p>
                  <p className="font-semibold text-surface-200">{teacher.subject_count}</p>
                </div>
                <div>
                  <p className="text-xs text-surface-500 mb-0.5">Feedback</p>
                  <p className="font-semibold text-surface-200">{teacher.feedback_count}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-surface-500 mb-0.5">Rating</p>
                  <p className="font-bold text-primary-400">{teacher.avg_rating} ⭐</p>
                </div>
              </div>

              <div className="pt-4 border-t border-surface-700/50 flex justify-between items-center">
                <span className={`badge ${performanceClass}`}>{teacher.performance}</span>
                <span className="text-xs text-primary-400 font-medium group-hover:underline">View Profile →</span>
              </div>
            </div>
          );
        })}
      </div>
      {teachers.length === 0 && (
         <div className="p-8 text-center text-surface-500 glass-card">No teachers found in the system.</div>
      )}
    </div>
  );

  // ============================================================
  // ANALYTICS SECTION
  // ============================================================
  const teacherComparisonData = analytics?.teacher_ranking?.map(t => ({
    name: t.name.length > 12 ? t.name.substring(0, 12) + '…' : t.name,
    fullName: t.name,
    rating: t.avg_rating,
    feedback: t.feedback_count,
  })) || [];

  const sentimentPieData = analytics?.sentiment_distribution
    ? [
        { name: 'Positive', value: analytics.sentiment_distribution.positive },
        { name: 'Neutral', value: analytics.sentiment_distribution.neutral },
        { name: 'Negative', value: analytics.sentiment_distribution.negative },
      ]
    : [];

  const ratingDistData = analytics?.rating_distribution
    ? Object.entries(analytics.rating_distribution).map(([key, val]) => ({
        name: `${key} ★`,
        value: val,
      }))
    : [];

  const subjectPerfData = analytics?.subject_performance?.map(s => ({
    name: s.subject_name.length > 15 ? s.subject_name.substring(0, 15) + '…' : s.subject_name,
    rating: s.avg_rating,
    feedback: s.feedback_count,
  })) || [];

  const renderAnalytics = () => (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-surface-100 font-display">Performance Analytics</h2>
        <p className="text-surface-400 text-sm mt-1">Department-wide performance insights and comparisons.</p>
      </div>

      {/* Department Average Card */}
      <div className="glass-card p-6 mb-8 animate-fade-in border-l-4 border-l-primary-500">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-surface-400 uppercase tracking-wider">Department Average Rating</p>
            <p className="text-4xl font-bold text-primary-400 font-display mt-1">
              {analytics?.department_average || 0} <span className="text-xl text-surface-500">/ 5.0</span>
            </p>
          </div>
          <div className="w-16 h-16 rounded-2xl bg-primary-500/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8 stagger">
        {/* Teacher Comparison Bar Chart */}
        <motion.div 
          layoutId="chart-teacher-comparison"
          className={`glass-card p-6 relative transition-all duration-300 ${activeChart && activeChart !== 'teacherComparison' ? 'opacity-50 grayscale-[50%]' : ''} ${activeChart === 'teacherComparison' ? 'ring-2 ring-primary-500 scale-[1.02]' : ''}`}
          onClick={() => setActiveChart(activeChart === 'teacherComparison' ? null : 'teacherComparison')}
        >
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-surface-100 font-display">Teacher Comparison</h3>
            <button 
              onClick={(e) => { e.stopPropagation(); setExpandedChart('teacherComparison'); }}
              className="text-surface-400 hover:text-primary-400 transition-colors"
            >
              <Maximize2 size={18} />
            </button>
          </div>
          {teacherComparisonData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={teacherComparisonData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  formatter={(value, name) => [value, name === 'rating' ? 'Avg Rating' : name]}
                  labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
                />
                <Bar dataKey="rating" radius={[6, 6, 0, 0]} barSize={35}>
                  {teacherComparisonData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-surface-500">No teacher data</div>
          )}
        </motion.div>

        {/* Sentiment Distribution Pie */}
        <motion.div 
          layoutId="chart-sentiment-distribution"
          className={`glass-card p-6 relative transition-all duration-300 ${activeChart && activeChart !== 'sentimentDistribution' ? 'opacity-50 grayscale-[50%]' : ''} ${activeChart === 'sentimentDistribution' ? 'ring-2 ring-primary-500 scale-[1.02]' : ''}`}
          onClick={() => setActiveChart(activeChart === 'sentimentDistribution' ? null : 'sentimentDistribution')}
        >
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-surface-100 font-display">Sentiment Distribution</h3>
            <button 
              onClick={(e) => { e.stopPropagation(); setExpandedChart('sentimentDistribution'); }}
              className="text-surface-400 hover:text-primary-400 transition-colors"
            >
              <Maximize2 size={18} />
            </button>
          </div>
          {sentimentPieData.some(d => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sentimentPieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  innerRadius={50}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={{ stroke: '#94a3b8' }}
                >
                  {sentimentPieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={chartTooltipStyle} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-surface-500">No sentiment data</div>
          )}
        </motion.div>

        {/* Rating Distribution Bar */}
        <motion.div 
          layoutId="chart-rating-distribution"
          className={`glass-card p-6 relative transition-all duration-300 ${activeChart && activeChart !== 'ratingDistribution' ? 'opacity-50 grayscale-[50%]' : ''} ${activeChart === 'ratingDistribution' ? 'ring-2 ring-primary-500 scale-[1.02]' : ''}`}
          onClick={() => setActiveChart(activeChart === 'ratingDistribution' ? null : 'ratingDistribution')}
        >
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-surface-100 font-display">Rating Distribution</h3>
            <button 
              onClick={(e) => { e.stopPropagation(); setExpandedChart('ratingDistribution'); }}
              className="text-surface-400 hover:text-primary-400 transition-colors"
            >
              <Maximize2 size={18} />
            </button>
          </div>
          {ratingDistData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={ratingDistData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={40}>
                  {ratingDistData.map((_, i) => (
                    <Cell key={i} fill={RATING_PIE_COLORS[i % RATING_PIE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-surface-500">No rating data</div>
          )}
        </motion.div>

        {/* Subject Performance Bar */}
        <motion.div 
          layoutId="chart-subject-performance"
          className={`glass-card p-6 relative transition-all duration-300 ${activeChart && activeChart !== 'subjectPerformance' ? 'opacity-50 grayscale-[50%]' : ''} ${activeChart === 'subjectPerformance' ? 'ring-2 ring-primary-500 scale-[1.02]' : ''}`}
          onClick={() => setActiveChart(activeChart === 'subjectPerformance' ? null : 'subjectPerformance')}
        >
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-surface-100 font-display">Subject Performance</h3>
            <button 
              onClick={(e) => { e.stopPropagation(); setExpandedChart('subjectPerformance'); }}
              className="text-surface-400 hover:text-primary-400 transition-colors"
            >
              <Maximize2 size={18} />
            </button>
          </div>
          {subjectPerfData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={subjectPerfData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="rating" fill="#a78bfa" radius={[6, 6, 0, 0]} barSize={35}>
                  {subjectPerfData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-surface-500">No subject data</div>
          )}
        </motion.div>
      </div>

      {/* Top & Low Performers Table */}
      {analytics?.teacher_ranking?.length > 0 && (
        <div className="glass-card">
          <div className="px-6 py-4 border-b border-surface-700/50">
            <h3 className="text-lg font-semibold text-surface-100 font-display">Teacher Rankings</h3>
          </div>
          <div className="p-0 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-800/50 border-b border-surface-700/50 text-surface-400 text-sm">
                  <th className="p-4 font-medium">Rank</th>
                  <th className="p-4 font-medium">Teacher</th>
                  <th className="p-4 font-medium">Avg Rating</th>
                  <th className="p-4 font-medium">Feedback Count</th>
                  <th className="p-4 font-medium">Performance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700/30">
                {analytics.teacher_ranking.map((t, i) => {
                  const perfClass =
                    t.performance === "Excellent" ? "badge-excellent" :
                    t.performance === "Good" ? "badge-good" :
                    t.performance === "Average" ? "badge-average" :
                    t.performance === "Poor" ? "badge-poor" : "badge-neutral";
                  return (
                    <tr key={t.id} className="hover:bg-surface-800/30 transition-colors">
                      <td className="p-4 text-surface-300 font-bold">#{i + 1}</td>
                      <td className="p-4 text-surface-100 font-medium">{t.name}</td>
                      <td className="p-4 text-primary-400 font-bold">{t.avg_rating} / 5.0</td>
                      <td className="p-4 text-surface-300">{t.feedback_count}</td>
                      <td className="p-4"><span className={`badge ${perfClass}`}>{t.performance}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals for Expanded Charts */}
      <ChartModal 
        isOpen={expandedChart === 'teacherComparison'} 
        onClose={() => setExpandedChart(null)}
        title="Teacher Comparison"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={teacherComparisonData} margin={{ top: 20, right: 30, left: 20, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 14 }} />
            <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 14 }} />
            <Tooltip
              contentStyle={chartTooltipStyle}
              formatter={(value, name) => [value, name === 'rating' ? 'Avg Rating' : name]}
              labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
            />
            <Bar dataKey="rating" radius={[6, 6, 0, 0]} barSize={50}>
              {teacherComparisonData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartModal>

      <ChartModal 
        isOpen={expandedChart === 'sentimentDistribution'} 
        onClose={() => setExpandedChart(null)}
        title="Sentiment Distribution"
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={sentimentPieData}
              cx="50%"
              cy="50%"
              outerRadius={180}
              innerRadius={90}
              dataKey="value"
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={{ stroke: '#94a3b8' }}
            >
              {sentimentPieData.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={chartTooltipStyle} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 14 }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartModal>

      <ChartModal 
        isOpen={expandedChart === 'ratingDistribution'} 
        onClose={() => setExpandedChart(null)}
        title="Rating Distribution"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={ratingDistData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 14 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 14 }} />
            <Tooltip contentStyle={chartTooltipStyle} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={60}>
              {ratingDistData.map((_, i) => (
                <Cell key={i} fill={RATING_PIE_COLORS[i % RATING_PIE_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartModal>

      <ChartModal 
        isOpen={expandedChart === 'subjectPerformance'} 
        onClose={() => setExpandedChart(null)}
        title="Subject Performance"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={subjectPerfData} margin={{ top: 20, right: 30, left: 20, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 14 }} />
            <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 14 }} />
            <Tooltip contentStyle={chartTooltipStyle} />
            <Bar dataKey="rating" fill="#a78bfa" radius={[6, 6, 0, 0]} barSize={50}>
              {subjectPerfData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartModal>

    </div>
  );

  // ============================================================
  // STATISTICS SECTION
  // ============================================================
  const renderStatistics = () => {
    const summary = statistics?.summary || {};
    const details = statistics?.details || [];

    return (
      <div className="animate-fade-in">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-surface-100 font-display">Feedback Statistics</h2>
          <p className="text-surface-400 text-sm mt-1">Comprehensive subject-wise feedback breakdown.</p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8 stagger">
          <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-primary-500)' }}>
            <p className="text-sm text-surface-400 mb-1">Total Students</p>
            <p className="text-3xl font-bold text-primary-400 font-display">{summary.total_students || 0}</p>
          </div>
          <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-cyan)' }}>
            <p className="text-sm text-surface-400 mb-1">Total Teachers</p>
            <p className="text-3xl font-bold text-accent-cyan font-display">{summary.total_teachers || 0}</p>
          </div>
          <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-emerald)' }}>
            <p className="text-sm text-surface-400 mb-1">Total Feedback</p>
            <p className="text-3xl font-bold text-accent-emerald font-display">{summary.total_feedback || 0}</p>
          </div>
          <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-violet)' }}>
            <p className="text-sm text-surface-400 mb-1">Total Subjects</p>
            <p className="text-3xl font-bold text-accent-violet font-display">{summary.total_subjects || 0}</p>
          </div>
          <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-amber)' }}>
            <p className="text-sm text-surface-400 mb-1">Pending Feedback</p>
            <p className="text-3xl font-bold text-accent-amber font-display">{summary.pending_feedback || 0}</p>
          </div>
        </div>

        {/* Subject-wise Detail Table */}
        <div className="glass-card">
          <div className="px-6 py-4 border-b border-surface-700/50">
            <h3 className="text-lg font-semibold text-surface-100 font-display">Subject-wise Breakdown</h3>
          </div>
          <div className="p-0 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-800/50 border-b border-surface-700/50 text-surface-400 text-sm">
                  <th className="p-4 font-medium">Subject</th>
                  <th className="p-4 font-medium">Teacher</th>
                  <th className="p-4 font-medium">Feedback</th>
                  <th className="p-4 font-medium">Overall</th>
                  <th className="p-4 font-medium">Punctuality</th>
                  <th className="p-4 font-medium">Teaching</th>
                  <th className="p-4 font-medium">Clarity</th>
                  <th className="p-4 font-medium">Interaction</th>
                  <th className="p-4 font-medium">Behavior</th>
                  <th className="p-4 font-medium">Sentiment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700/30">
                {details.map((row, i) => (
                  <tr key={i} className="hover:bg-surface-800/30 transition-colors">
                    <td className="p-4">
                      <p className="text-surface-100 font-medium">{row.subject}</p>
                      <p className="text-xs text-surface-500">{row.subject_code}</p>
                    </td>
                    <td className="p-4 text-surface-300">{row.teacher}</td>
                    <td className="p-4 text-surface-300">{row.total_feedback}</td>
                    <td className="p-4 text-primary-400 font-bold">{row.avg_overall}</td>
                    <td className="p-4 text-surface-300">{row.avg_punctuality}</td>
                    <td className="p-4 text-surface-300">{row.avg_teaching}</td>
                    <td className="p-4 text-surface-300">{row.avg_clarity}</td>
                    <td className="p-4 text-surface-300">{row.avg_interaction}</td>
                    <td className="p-4 text-surface-300">{row.avg_behavior}</td>
                    <td className="p-4">
                      <div className="flex gap-1 text-xs whitespace-nowrap">
                        <span className="text-accent-emerald">😊{row.sentiment_summary?.positive || 0}</span>
                        <span className="text-surface-400">😐{row.sentiment_summary?.neutral || 0}</span>
                        <span className="text-accent-rose">😞{row.sentiment_summary?.negative || 0}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {details.length === 0 && (
              <div className="p-8 text-center text-surface-500">No statistics available yet.</div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ============================================================


  // ============================================================

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar 
        role="hod" 
        activeSection={activeSection} 
        onSectionChange={setActiveSection}
        user={user} 
      />
      <main className="flex-1 ml-64 p-8 overflow-y-auto w-full">
        <div className="max-w-6xl mx-auto">
          {activeSection === "overview" && renderOverview()}
          {activeSection === "teachers" && renderTeachers()}
          {activeSection === "analytics" && renderAnalytics()}
          {activeSection === "statistics" && renderStatistics()}
          {activeSection === "comparison" && renderComparison()}
        </div>
      </main>
    </div>
  );
}
