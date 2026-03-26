import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import Sidebar from "../components/Sidebar";
import SubjectRadarChart from "../components/SubjectRadarChart";
import ExpandableChartModal from "../components/ExpandableChartModal";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from "recharts";

const CHART_COLORS = ['#6366f1', '#22d3ee', '#a78bfa', '#f59e0b', '#10b981'];
const PIE_COLORS = ['#10b981', '#6366f1', '#f59e0b', '#ef4444'];

const chartTooltipStyle = {
  backgroundColor: 'rgba(30, 41, 59, 0.95)',
  borderColor: 'rgba(148, 163, 184, 0.15)',
  borderRadius: '0.5rem',
  color: '#f8fafc',
};

export default function TeacherDashboard() {
  const [dashboardData, setDashboardData] = useState([]);
  const [performanceData, setPerformanceData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("dashboard");
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState('classwise');
  const [isRefetching, setIsRefetching] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!user) setLoading(true);
      else setIsRefetching(true);

      try {
        const params = `?view=${viewMode}`;
        const results = await Promise.allSettled([
          API.get(`teacher/dashboard/${params}`),
          API.get("teacher/performance/"),
          API.get(`teacher/performance-charts/${params}`),
          API.get("auth/profile/")
        ]);
        if (results[0].status === 'fulfilled') setDashboardData(results[0].value.data);
        if (results[1].status === 'fulfilled') setPerformanceData(results[1].value.data);
        if (results[2].status === 'fulfilled') setChartData(results[2].value.data);
        if (results[3].status === 'fulfilled') setUser(results[3].value.data.user);
      } catch (err) {
        console.error("Error fetching data:", err);
      } finally {
        setLoading(false);
        setIsRefetching(false);
      }
    };
    fetchData();
  }, [viewMode]);

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  const renderDashboard = () => (
    <div className="animate-fade-in">
      <div className="mb-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-surface-100 font-display">Dashboard Overview</h2>
          <p className="text-surface-400 text-sm mt-1">Summary of your assigned subjects and feedback.</p>
        </div>
        <div className="flex bg-surface-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('classwise')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              viewMode === 'classwise' ? 'bg-primary-500 text-white' : 'text-surface-400 hover:text-surface-100'
            }`}
          >
            Class-wise
          </button>
          <button
            onClick={() => setViewMode('combined')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              viewMode === 'combined' ? 'bg-primary-500 text-white' : 'text-surface-400 hover:text-surface-100'
            }`}
          >
            Combined
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 stagger">
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-primary-500)' }}>
          <p className="text-sm text-surface-400 mb-1">Your Subjects</p>
          <p className="text-3xl font-bold text-primary-400 font-display">{dashboardData.length}</p>
        </div>
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-emerald)' }}>
          <p className="text-sm text-surface-400 mb-1">Total Feedback</p>
          <p className="text-3xl font-bold text-accent-emerald font-display">
            {performanceData?.total_feedback || 0}
          </p>
        </div>
        <div className="stat-card glass-card animate-fade-in" style={{ '--card-accent': 'var(--color-accent-amber)' }}>
          <p className="text-sm text-surface-400 mb-1">Overall Average</p>
          <p className="text-3xl font-bold text-accent-amber font-display">
            {performanceData?.overall_average || 0} <span className="text-lg">/ 5.0</span>
          </p>
        </div>
      </div>

        <div className={`grid grid-cols-1 xl:grid-cols-2 gap-6 stagger ${isRefetching ? 'opacity-50 pointer-events-none' : ''}`}>
        {dashboardData.map((subject, index) => {
          const radarData = [
            { category: 'Punctuality', rating: subject.avg_punctuality },
            { category: 'Teaching', rating: subject.avg_teaching },
            { category: 'Clarity', rating: subject.avg_clarity },
            { category: 'Interaction', rating: subject.avg_interaction },
            { category: 'Behavior', rating: subject.avg_behavior },
          ];

          const performanceClass = 
            subject.performance === "Excellent" ? "badge-excellent" :
            subject.performance === "Good" ? "badge-good" :
            subject.performance === "Average" ? "badge-average" :
            subject.performance === "Poor" ? "badge-poor" : "badge-neutral";

          return (
            <div key={subject.subject_id || index} className="glass-card p-6 flex flex-col">
              <div className="flex justify-between items-start mb-4 pb-4 border-b border-surface-700/50">
                <div className="min-w-0 pr-4">
                  <h3 className="text-lg font-bold text-surface-100 font-display truncate">
                    {subject.subject_name}
                  </h3>
                  <p className="text-sm text-surface-400">{subject.subject_code}</p>
                </div>
                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  <span className={`badge ${performanceClass}`}>{subject.performance}</span>
                  <div className="text-xl font-bold text-primary-400">
                    {subject.avg_overall} <span className="text-sm text-surface-500 font-normal">/ 5.0</span>
                  </div>
                </div>
              </div>

              <div className="flex-1 min-h-[250px] mb-4">
                {subject.feedback_count > 0 ? (
                  <SubjectRadarChart data={radarData} />
                ) : (
                  <div className="h-full flex items-center justify-center text-surface-500">
                    No feedback data yet
                  </div>
                )}
              </div>

              {/* Sentiment Summary */}
              <div className="mt-auto grid grid-cols-3 gap-2 pt-4 border-t border-surface-700/50">
                <div className="bg-surface-800/50 rounded-lg p-2 text-center tooltip" data-tooltip="Positive">
                  <div className="text-xl mb-1">😊</div>
                  <div className="text-sm font-bold text-accent-emerald">
                    {subject.sentiment_summary?.positive || 0}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-2 text-center tooltip" data-tooltip="Neutral">
                  <div className="text-xl mb-1">😐</div>
                  <div className="text-sm font-bold text-surface-400">
                    {subject.sentiment_summary?.neutral || 0}
                  </div>
                </div>
                <div className="bg-surface-800/50 rounded-lg p-2 text-center tooltip" data-tooltip="Negative">
                  <div className="text-xl mb-1">😞</div>
                  <div className="text-sm font-bold text-accent-rose">
                    {subject.sentiment_summary?.negative || 0}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  // --- Build Recharts data from chartData ---
  const subjectBarData = chartData?.subject_ratings
    ? chartData.subject_ratings.labels.map((label, i) => ({
        name: label,
        rating: chartData.subject_ratings.values[i],
      }))
    : [];

  const categoryBarData = chartData?.category_averages
    ? chartData.category_averages.labels.map((label, i) => ({
        name: label,
        value: chartData.category_averages.values[i],
      }))
    : [];

  const pieData = chartData?.rating_distribution
    ? chartData.rating_distribution.labels.map((label, i) => ({
        name: label,
        value: chartData.rating_distribution.values[i],
      }))
    : [];

  const trendLineData = chartData?.monthly_trend
    ? chartData.monthly_trend.labels.map((label, i) => ({
        month: label,
        rating: chartData.monthly_trend.values[i],
      }))
    : [];

  const renderPerformance = () => (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-surface-100 font-display">My Performance Details</h2>
        <p className="text-surface-400 text-sm mt-1">Detailed subject-wise breakdown with charts.</p>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8 stagger">
        {/* Bar Chart — Subject-wise Ratings */}
        <div className="glass-card p-6 animate-fade-in">
          <h3 className="text-lg font-semibold text-surface-100 font-display mb-4">Subject-wise Ratings</h3>
          {subjectBarData.length > 0 ? (
            <div className="h-[280px]">
              <ExpandableChartModal title="Subject-wise Ratings" subtitle="Average rating per subject">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={subjectBarData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip contentStyle={chartTooltipStyle} />
                    <Bar dataKey="rating" fill="#6366f1" radius={[6, 6, 0, 0]} barSize={40}>
                      {subjectBarData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ExpandableChartModal>
            </div>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-surface-500">No data available</div>
          )}
        </div>

        {/* Pie Chart — Rating Distribution */}
        <div className="glass-card p-6 animate-fade-in">
          <h3 className="text-lg font-semibold text-surface-100 font-display mb-4">Rating Distribution</h3>
          {pieData.some(d => d.value > 0) ? (
            <div className="h-[280px]">
              <ExpandableChartModal title="Rating Distribution" subtitle="Breakdown of student feedback categories">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      innerRadius={50}
                      dataKey="value"
                      label={({ name, percent }) => `${name.split(' ')[0]} ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: '#94a3b8' }}
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} />
                    <Legend
                      wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </ExpandableChartModal>
            </div>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-surface-500">No data available</div>
          )}
        </div>

        {/* Bar Chart — Category-wise Averages */}
        <div className="glass-card p-6 animate-fade-in">
          <h3 className="text-lg font-semibold text-surface-100 font-display mb-4">Category-wise Averages</h3>
          {categoryBarData.length > 0 ? (
            <div className="h-[280px]">
              <ExpandableChartModal title="Category-wise Averages" subtitle="Performance across specific evaluation criteria">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categoryBarData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip contentStyle={chartTooltipStyle} />
                    <Bar dataKey="value" fill="#22d3ee" radius={[6, 6, 0, 0]} barSize={40}>
                      {categoryBarData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ExpandableChartModal>
            </div>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-surface-500">No data available</div>
          )}
        </div>

        {/* Line Chart — Monthly Trend */}
        <div className="glass-card p-6 animate-fade-in">
          <h3 className="text-lg font-semibold text-surface-100 font-display mb-4">Performance Trend</h3>
          {trendLineData.length > 0 ? (
            <div className="h-[280px]">
              <ExpandableChartModal title="Performance Trend" subtitle="6-month rolling performance average">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendLineData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                    <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis domain={[0, 5]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip contentStyle={chartTooltipStyle} />
                    <Line
                      type="monotone"
                      dataKey="rating"
                      stroke="#6366f1"
                      strokeWidth={3}
                      dot={{ fill: '#6366f1', r: 5 }}
                      activeDot={{ r: 7, fill: '#a78bfa' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ExpandableChartModal>
            </div>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-surface-500">No trend data yet</div>
          )}
        </div>
      </div>

      {/* Performance Table */}
      <div className="glass-card mb-8">
        <div className="px-6 py-4 border-b border-surface-700/50">
          <h3 className="text-lg font-semibold text-surface-100 font-display">Performance by Subject</h3>
        </div>
        <div className="p-0 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-800/50 border-b border-surface-700/50 text-surface-400 text-sm">
                <th className="p-4 font-medium">Subject Code</th>
                <th className="p-4 font-medium">Subject Name</th>
                <th className="p-4 font-medium">Feedback Count</th>
                <th className="p-4 font-medium">Average Rating</th>
                <th className="p-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700/30">
              {performanceData?.subject_performance?.map((sub, i) => {
                const performanceClass = 
                  sub.performance === "Excellent" ? "badge-excellent" :
                  sub.performance === "Good" ? "badge-good" :
                  sub.performance === "Average" ? "badge-average" :
                  sub.performance === "Poor" ? "badge-poor" : "badge-neutral";
                
                return (
                  <tr key={i} className="hover:bg-surface-800/30 transition-colors">
                    <td className="p-4 text-surface-300 font-medium">{sub.subject_code}</td>
                    <td className="p-4 text-surface-100">{sub.subject_name}</td>
                    <td className="p-4 text-surface-300">{sub.feedback_count}</td>
                    <td className="p-4 text-primary-400 font-bold">{sub.avg_overall} / 5.0</td>
                    <td className="p-4">
                      <span className={`badge ${performanceClass}`}>{sub.performance}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {(!performanceData?.subject_performance || performanceData.subject_performance.length === 0) && (
             <div className="p-8 text-center text-surface-500">No performance data found.</div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar 
        role="teacher" 
        activeSection={activeSection} 
        onSectionChange={setActiveSection} 
        user={user} 
      />
      <main className="flex-1 ml-64 p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto">
          {activeSection === "dashboard" && renderDashboard()}
          {activeSection === "performance" && renderPerformance()}
        </div>
      </main>
    </div>
  );
}
