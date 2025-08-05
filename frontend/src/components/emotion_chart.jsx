import React from "react";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import * as d3 from "d3-scale";
import * as d3Chromatic from "d3-scale-chromatic";

// emotions 배열을 받아서 카운트하는 함수
function countEmotions(emotions) {
  const counts = {};
  emotions.forEach((emotion) => {
    counts[emotion] = (counts[emotion] || 0) + 1;
  });
  // recharts에서 쓸 데이터 포맷으로 변환
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

function EmotionChart({ emotions }) {
  const data = countEmotions(emotions);
  const colorScale = d3.scaleOrdinal()
    .domain(data.map(d => d.name))
    .range(d3Chromatic.schemeCategory10); // 10가지 색상 팔레트, 필요하면 schemeCategory20 등 사용 가능

  return (
    <div>
        <h3 style={{ textAlign: "center", marginBottom: 10 }}>답변 어감 비율</h3>
        <PieChart width={400} height={300}>
        <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={100}
            fill="#8884d8"
            label
        >
            {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={colorScale(entry.name)} />
            ))}
        </Pie>
        <Tooltip />
        <Legend />
        </PieChart>
    </div>
  );
}

export default EmotionChart;