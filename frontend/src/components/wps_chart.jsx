import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from "recharts";

function WpsChart({ wps }) {
  // wps = [0.5, 0.7, 0.6, 0.8, ...]
  // recharts는 객체 배열이 필요해서 변환
  const data = wps.map((speed, index) => ({
    index: index + 1, // 1번, 2번, 3번 답변 순서 표시용
    speed,
  }));

  const REFERENCE_LINES = [2.59, 1.73];
  const minRef = Math.min(...REFERENCE_LINES);
  const maxRef = Math.max(...REFERENCE_LINES);

  return (
    <div>
        <h3 style={{ textAlign: "center", marginBottom: 10 }}>답변별 빠르기 변화 추이</h3>
        <LineChart width={400} height={300} data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="index" label={{ value: "답변 번호", position: "insideBottomRight", offset: -5 }} />
        <YAxis label={{ value: "말 속도(WPS)", angle: -90, position: "insideLeft" }} domain={[
          // dataMin과 기준선의 최소값 중 더 작은 값에서 여유를 줌
          (dataMin) => Math.min(dataMin, minRef) - 2,
          // dataMax과 기준선의 최대값 중 더 큰 값에서 여유를 줌
          (dataMax) => Math.max(dataMax, maxRef) + 2,
        ]} />
        <ReferenceLine y={2.59} stroke="red" strokeDasharray="3 3" label={{ value: "정상범위 최대 값", position: 'insideRight', fill: 'red' }} />
        <ReferenceLine y={1.73} stroke="red" strokeDasharray="3 3" label={{ value: "정상범위 최소 값", position: 'insideRight', fill: 'red' }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="speed" stroke="#8884d8" strokeWidth={2} dot />
        </LineChart>
    </div>
  );
}

export default WpsChart;