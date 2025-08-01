import React from 'react';
import { useLocation } from "react-router-dom";

function Result() {
    const location = useLocation();
    const { interview, analysisResult, questions, chatAnswers } = location.state || {};

    const emotions = interview.interview.map(item => item.emotion);
    const lufs = interview.interview.map(item => item.lufs);
    const wps = interview.interview.map(item => item.wps);

    console.log("인터뷰 결과:", interview);
    console.log("영상 분석 결과:", analysisResult);
    console.log("질문:", questions);
    console.log("답변:", chatAnswers);

    return (
        <>
            <h2>면접 평가</h2>

            <div>
                <h3>영상 분석</h3>
                <p>중심 시선 비율: {analysisResult.gaze_center_ratio}</p>
                <p>시선 이동 횟수: {analysisResult.gaze_shift_count}</p>
                <p>자세 변화 횟수: {analysisResult.posture_change_count}</p>
            </div>

            <div>
                <h3>음성 분석</h3>
                <p>
                    감정 분석: [
                    {emotions.map((emotion, index) => (
                        <span key={index}>{emotion}{index < emotions.length - 1 ? ', ' : ''}</span>
                    ))}
                    ]
                </p>
                <p>
                    음량 분석: [
                    {lufs.map((l, index) => (
                        <span key={index}>{l}{index < lufs.length - 1 ? ', ' : ''}</span>
                    ))}
                    ]
                </p>
                <p>
                    말 속도 분석: [
                    {wps.map((w, index) => (
                        <span key={index}>{w}{index < wps.length - 1 ? ', ' : ''}</span>
                    ))}
                    ]
                </p>
            </div>

            <div>
                <h2>텍스트 분석</h2>
                <p>말버릇 분석</p>
                <p>답변 분석</p>
            </div>
        </>
    );
}

export default Result;