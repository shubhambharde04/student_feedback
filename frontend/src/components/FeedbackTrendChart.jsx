import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function FeedbackTrendChart({ feedback, title = "Feedback Trend Over Time" }) {
  const getTrendData = () => {
    const sortedFeedback = [...feedback].sort((a, b) => 
      new Date(a.created_at) - new Date(b.created_at)
    );

    const trendData = {};
    const last30Days = [];
    
    for (let i = 29; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      last30Days.push(dateStr);
      trendData[dateStr] = 0;
    }

    sortedFeedback.forEach(item => {
      const dateStr = new Date(item.created_at).toISOString().split('T')[0];
      if (trendData.hasOwnProperty(dateStr)) {
        trendData[dateStr]++;
      }
    });

    const labels = last30Days.map(date => {
      const d = new Date(date);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    const data = last30Days.map(date => trendData[date]);

    return { labels, data };
  };

  const { labels, data } = getTrendData();

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Number of Feedback Submissions',
        data,
        borderColor: 'rgba(59, 130, 246, 1)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
        },
        title: {
          display: true,
          text: 'Number of Feedback'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date (Last 30 Days)'
        }
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <Line data={chartData} options={options} />
    </div>
  );
}
