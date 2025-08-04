import React from 'react';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';

/**
 * @param {string} title - 차트 상단에 보여줄 설명 제목 (예: "정면 응시 비율")
 * @param {string} label - 강조할 항목 이름 (예: "정면")
 * @param {number} ratio - 0~100 사이의 비율 값 (예: 72.3)
 */
function PostureChart({ title, label, ratio }) {
  const safeRatio = Math.min(Math.max(ratio, 0), 100); // 0~100 범위로 클램프
  const remaining = 100 - safeRatio;

  const gazeData = [
    { name: label, value: safeRatio },
    { name: '멈춤', value: remaining },
  ];
  const COLORS = ['#00C49F', '#E0E0E0']; // 강조색, 회색

  return (
    <div
      style={{
        width: 250,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        fontFamily: 'system-ui, sans-serif',
      }}
      aria-label={title ? `${title}: ${safeRatio.toFixed(1)}%` : `${label} 비율: ${safeRatio.toFixed(1)}%`}
    >
      {title && (
        <h3 style={{ marginBottom: 6, textAlign: 'center' }}>
          <strong style={{ fontSize: 14 }}>{title}</strong>
        </h3>
      )}
      <PieChart width={250} height={250}>
        <Pie
          data={gazeData}
          cx="50%"
          cy="50%"
          outerRadius={100}
          innerRadius={60}
          dataKey="value"
          labelLine={false}
          isAnimationActive={true}
          cornerRadius={4}
        >
          {gazeData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={COLORS[index]}
              stroke={index === 0 ? '#007f5f' : '#ccc'}
              strokeWidth={index === 0 ? 2 : 1}
            />
          ))}
        </Pie>
        <Tooltip
          formatter={(val) => `${val.toFixed(1)}%`}
          payload={
            null /* 기본 툴팁이 자동으로 붙음; 필요시 커스터마이징 가능 */
          }
        />
        {/* 중앙 강조 텍스트: 비율 숫자 */}
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="middle"
          style={{ fontSize: '24px', fontWeight: 700 }}
        >
          {`${safeRatio.toFixed(1)}%`}
        </text>
        {/* 라벨 아래쪽에 작게 */}
        <text
          x="50%"
          y="62%"
          textAnchor="middle"
          dominantBaseline="middle"
          style={{ fontSize: '12px', fill: '#555' }}
        >
          {label}
        </text>
      </PieChart>
    </div>
  );
}

export default PostureChart;