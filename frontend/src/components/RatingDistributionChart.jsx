import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function RatingDistributionChart({ feedback, title = "Rating Distribution" }) {
  const getRatingDistribution = (feedbackList) => {
    const distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    feedbackList.forEach(f => {
      distribution[f.rating]++;
    });
    return distribution;
  };

  const distribution = getRatingDistribution(feedback);

  const data = {
    labels: ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars'],
    datasets: [
      {
        label: 'Number of Ratings',
        data: [distribution[1], distribution[2], distribution[3], distribution[4], distribution[5]],
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',   // Red for 1 star
          'rgba(249, 115, 22, 0.8)',  // Orange for 2 stars
          'rgba(234, 179, 8, 0.8)',   // Yellow for 3 stars
          'rgba(34, 197, 94, 0.8)',   // Green for 4 stars
          'rgba(16, 185, 129, 0.8)',  // Emerald for 5 stars
        ],
        borderColor: [
          'rgba(239, 68, 68, 1)',
          'rgba(249, 115, 22, 1)',
          'rgba(234, 179, 8, 1)',
          'rgba(34, 197, 94, 1)',
          'rgba(16, 185, 129, 1)',
        ],
        borderWidth: 1,
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
        callbacks: {
          label: function(context) {
            const total = feedback.length;
            const value = context.parsed.y;
            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
            return `${context.dataset.label}: ${value} (${percentage}%)`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
        },
        title: {
          display: true,
          text: 'Number of Ratings'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Rating'
        }
      }
    },
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <Bar data={data} options={options} />
    </div>
  );
}
