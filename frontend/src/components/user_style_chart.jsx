import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function UserStyleChart({ data }) {
    if (!data) {
        return <p>데이터가 없습니다.</p>; // 또는 로딩 메시지 등
    }
    // 배열을 recharts용 객체 배열로 변환 (key: 단어, value: 사용횟수)
    const convertData = (arr) =>
        arr.map(([word, count]) => ({
        word,
        count,
    }));

    const keywordData = convertData(data.keywords || []);
    const endingsData = convertData(data.endings || []);
    const fillersData = convertData(data.fillers || []);

    // 각 그래프 공통 스타일
    const renderBarChart = (chartData, title) => (
        <div style={{ width: "100%", height: 250, marginBottom: 40 }}>
        <h3>{title}</h3>
        <ResponsiveContainer width="100%" height="100%">
            <BarChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="word" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#8884d8" />
            </BarChart>
        </ResponsiveContainer>
        </div>
    );

    return (
        <div style={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "center",
            alignItems: "flex-start",
            gap: 40,
            padding: 20,
        }}>
        {keywordData.length > 0 && renderBarChart(keywordData, "Keywords (자주 사용한 단어)")}
        {endingsData.length > 0 && renderBarChart(endingsData, "Endings (자주 사용한 어미)")}
        {fillersData.length > 0 && renderBarChart(fillersData, "Fillers (자주 사용한 필러)")}
        {!keywordData.length && !endingsData.length && !fillersData.length && (
            <p>표시할 데이터가 없습니다.</p>
        )}
        </div>
    );
}