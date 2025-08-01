import React, { useState, useEffect } from 'react';
import { useLocation } from "react-router-dom";

import GazeChart from './components/gaze_chart';
import EmotionChart from './components/emotion_chart';
import LufsChart from './components/lufs_chart';
import WpsChart from './components/wps_chart';
import UserStyleChart from './components/user_style_chart';

import QnaItem from './components/qna_item';

function Result() {
    const [userStyle, setUserStyle] = useState(null);

    const location = useLocation();
    const { interview, analysisResult, questions, chatAnswers } = location.state || {};

    const interviewItems = interview?.interview || [];
    const emotions = interviewItems.map((item) => item.emotion);
    const lufs = interviewItems.map((item) => Number(item.lufs.toFixed(2)));
    const wps = interviewItems.map((item) => Number(item.wps.toFixed(2)));

    const sectionStyle = {
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '24px',
        backgroundColor: '#fafafa',
        boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
        width: '90%',
        maxWidth: '1500px',
        marginLeft: 'auto',
        marginRight: 'auto',
        textAlign: 'center',
    };

    const get_user_style = async () => {
        try {
            const res = await fetch('http://localhost:8000/analyze-user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chatAnswers })
            });
        
            if (!res.ok) {
                console.error('서버 시작 요청 실패:', res.status);
                return;
            }

            const data = await res.json();  // 응답을 JSON으로 파싱
            setUserStyle(data);
        } 
        catch (error) { console.error('Error:', error); }
    }

    useEffect(() => {
        if (chatAnswers) { get_user_style(); }
        else { setUserStyle(null); }   
    }, [chatAnswers]);

    return (
        <>
            <h1 style={{ textAlign: 'center', marginBottom: '24px' }}>면접 평가</h1>

            <section style={sectionStyle}>
                <h2>영상 분석</h2>
                {analysisResult ? (
                    <div style={{
                        display: 'flex',
                        flexDirection: 'column',  // 세로 정렬
                        alignItems: 'center',     // 가로 가운데 정렬
                        gap: '12px',              // 차트와 텍스트 사이 간격
                    }}>
                        <GazeChart title="시선 비율" label="중심" ratio={analysisResult?.gaze_center_ratio} />
                        <div>
                            <span style={{ marginRight: '15px' }}> 시선 이동 횟수: {analysisResult?.gaze_shift_count ?? 'N/A'} </span>
                            <span> 자세 변화 횟수: {analysisResult?.posture_change_count ?? 'N/A'} </span>
                        </div>
                    </div>
                ) : (
                    <p>영상 분석 데이터가 없습니다.</p>
                )}
            </section>

            <section style={sectionStyle}>
                <div style={{ textAlign: 'center', marginBottom: 16 }}>
                    <h2>음성분석</h2>
                </div>
                <div style={{
                    display: 'flex',
                    flexDirection: 'row',
                    justifyContent: 'center',
                    alignItems: 'center',
                    gap: '12px',
                }}>
                    <EmotionChart emotions={emotions} />
                    <LufsChart lufs={lufs} />
                    <WpsChart wps={wps} />
                </div>
            </section>

            <section style={sectionStyle}>
                <div>
                    <h2>텍스트 분석</h2>
                    <UserStyleChart data={userStyle} />

                    <div style={{marginTop: '20px'}}>
                        {questions && chatAnswers ? (
                            questions.map((question, i) => (<QnaItem key={i} index={i} question={question} answer={chatAnswers[i]} />))
                        ) : (
                            <p>질문과 답변 데이터가 없습니다.</p>
                        )}
                    </div>
                </div>
            </section>
        </>
    );
}

export default Result;