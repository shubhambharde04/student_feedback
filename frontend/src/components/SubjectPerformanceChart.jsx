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

export default function SubjectPerformanceChart({ subjects, feedback, title = "Subject Performance" }) {
  const getSubjectStats = () => {
    return subjects.map(subject => {
      const subjectFeedback = feedback.filter(f => f.subject === subject.id);
      const avgRating = subjectFeedback.length > 0 
        ? (subjectFeedback.reduce((acc, f) => acc + f.rating, 0) / subjectFeedback.length).toFixed(1)
        : 0;
      return {
        name: subject.name,
        avgRating: parseFloat(avgRating),
        feedbackCount: subjectFeedback.length
      };
    });
  };

  const subjectStats = getSubjectStats();

  const data = {
    labels: subjectStats.map(s => s.name),
    datasets: [
      {
        label: 'Average Rating',
        data: subjectStats.map(s => s.avgRating),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderColor: 'rgba(59, 130, 246, 1)',
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
          afterLabel: function(context) {
            const index = context.dataIndex;
            const feedbackCount = subjectStats[index].feedbackCount;
            return `Feedback Count: ${feedbackCount}`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 5,
        ticks: {
          stepSize: 0.5,
        },
        title: {
          display: true,
          text: 'Average Rating'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Subjects'
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
