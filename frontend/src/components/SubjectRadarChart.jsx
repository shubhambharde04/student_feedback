import React from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip
} from 'recharts';

export default function SubjectRadarChart({ data }) {
  // data should be an array of objects matching the radar shape
  // e.g., [{ category: 'Punctuality', rating: 4.5 }, ...]

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="rgba(148, 163, 184, 0.2)" />
          <PolarAngleAxis
            dataKey="category"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 5]}
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickCount={6}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(30, 41, 59, 0.9)',
              borderColor: 'rgba(148, 163, 184, 0.1)',
              borderRadius: '0.5rem',
              color: '#f8fafc'
            }}
          />
          <Radar
            name="Rating"
            dataKey="rating"
            stroke="#6366f1"
            fill="#6366f1"
            fillOpacity={0.4}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
