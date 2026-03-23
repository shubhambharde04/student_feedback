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

export default function TeacherPerformanceChart({ subjects, feedback, title = "Teacher Performance" }) {
  const getTeacherStats = () => {
    const teachers = {};
    
    subjects.forEach(subject => {
      if (subject.teacher_name) {
        if (!teachers[subject.teacher_name]) {
          teachers[subject.teacher_name] = {
            name: subject.teacher_name,
            subjects: [],
            feedback: []
          };
        }
        teachers[subject.teacher_name].subjects.push(subject);
      }
    });

    Object.keys(teachers).forEach(teacherName => {
      const teacherSubjects = teachers[teacherName].subjects;
      const teacherFeedback = feedback.filter(f => 
        teacherSubjects.some(s => s.id === f.subject)
      );
      teachers[teacherName].feedback = teacherFeedback;
    });

    return Object.values(teachers).map(teacher => {
      const avgRating = teacher.feedback.length > 0 
        ? (teacher.feedback.reduce((acc, f) => acc + f.rating, 0) / teacher.feedback.length).toFixed(1)
        : 0;
      return {
        name: teacher.name,
        avgRating: parseFloat(avgRating),
        feedbackCount: teacher.feedback.length,
        subjectCount: teacher.subjects.length
      };
    });
  };

  const teacherStats = getTeacherStats();

  const data = {
    labels: teacherStats.map(t => t.name),
    datasets: [
      {
        label: 'Average Rating',
        data: teacherStats.map(t => t.avgRating),
        backgroundColor: 'rgba(168, 85, 247, 0.8)',
        borderColor: 'rgba(168, 85, 247, 1)',
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
            const teacher = teacherStats[index];
            return [
              `Subjects: ${teacher.subjectCount}`,
              `Feedback Count: ${teacher.feedbackCount}`
            ];
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
          text: 'Teachers'
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
