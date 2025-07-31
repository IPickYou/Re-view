import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useLocation } from "react-router-dom";

function Interview() {
  const [intervalId, setIntervalId] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [analysisResult, setAnalysisResult] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [audioCapture, setAudioCapture] = useState("");
  const [videoSize, setVideoSize] = useState({ width: 640, height: 480 });

  const location = useLocation();
  const { questions, answers } = location.state || {};
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [chatAnswers, setChatAnswers] = useState(Array(questions?.length || 0).fill(""));

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const faceLandmarks = analysisResult.face_landmarks;
  const poseLandmarks = analysisResult.pose_landmarks;
  
  const POSE_CONNECTIONS = [ [11, 12] /* 양 어깨 */  ];

  const navigate = useNavigate();

  const setupCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 960 }, height: { ideal: 540 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play();
        
          const video = videoRef.current;
          const canvas = canvasRef.current;
          if (canvas && video) {
            canvas.style.width = video.videoWidth + 'px';
            canvas.style.height = video.videoHeight + 'px';
          }
        };
      } 
      else { console.error("videoRef.current가 없음"); }
    } 
    catch (e) { console.error('웹캠 연결 실패:', e); }
  };

  const captureWebcamImage = async () => {
    const video = videoRef.current;
    if (!video) {
      console.error('비디오 요소가 없습니다!');
      return null;
    }
  
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  
    const ctx = canvas.getContext('2d');
    ctx.translate(canvas.width, 0);     // 오른쪽으로 이동
    ctx.scale(-1, 1);                    // 좌우 반전
    ctx.drawImage(video, 0, 0);         // 반전된 채로 그리기
  
    return canvas.toDataURL('image/jpeg').split(',')[1];
  };

  useEffect(() => {
    if (isCameraOn) { setupCamera(); } 
    else {
      // 정지 처리
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
        videoRef.current.srcObject = null;
      }
    }
  }, [isCameraOn]);

  const startRecognition = async () => {
    try {
      // 1) 서버에 /start 요청 보내기
      const startRes = await fetch('http://localhost:8000/start', {method: 'POST'});

      if (!startRes.ok) {
        console.error('서버 시작 요청 실패:', startRes.status);
        return;
      }

      const startData = await startRes.json();
  
      // 2) 카메라 켜기
      setIsCameraOn(true);
  
      // 3) 분석 주기적 요청
      const id = setInterval(async () => {
        try {
          const imageBase64 = await captureWebcamImage();
          if (!imageBase64) return;
  
          const res = await fetch('http://localhost:8000/analyze-frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageBase64 }),
          });
  
          if (res.ok) {
            const result = await res.json();
            setAnalysisResult(result);
          } 
          else { console.error('분석 실패:', res.status); }
        } 
        catch (e) { console.error('분석 중 에러:', e); }
      }, 2000);
  
      setIntervalId(id);
    } 
    catch (error) { console.error('Error:', error); }
  };

  const stopRecognition = async () => {
    if (intervalId) {
      clearInterval(intervalId);
      setIntervalId(null);
    }
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsCameraOn(false);
    setAnalysisResult({});
  
    // 서버에 정지 요청 보내기 (필요하면)
    try {
      const stopRes = await fetch('http://localhost:8000/stop', {method: 'POST'});

      if (!stopRes.ok) { console.error('서버 정지 요청 실패:', stopRes.status); } 
      else {
        const data = await stopRes.json();
        navigate("/result", {
          state: {
            interview: data,
            analysisResult,
            questions,
            chatAnswers,
          }
        });
      }
    } 
    catch (e) { console.error('서버 정지 요청 중 에러:', e); }
  };

  useEffect(() => {
    return () => {
      if (intervalId) clearInterval(intervalId);

      if (videoRef.current && videoRef.current.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
      }
    };
  }, [intervalId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
  
    if (!canvas || !video || !faceLandmarks) return;
  
    const ctx = canvas.getContext("2d");
  
    // ✅ 실제 비디오 픽셀 기준으로 캔버스 크기 설정
    const vw = video.videoWidth;
    const vh = video.videoHeight;

    if (!vw || !vh) return; // 비디오 아직 준비 안됐을 수 있음
  
    canvas.width = vw;
    canvas.height = vh;
  
    // ✅ 캔버스 초기화 및 좌우 반전
    ctx.clearRect(0, 0, vw, vh);
    ctx.save();
    ctx.translate(vw, 0); // 반전
    ctx.scale(-1, 1);
  
    // 🔧 유틸 함수
    const drawPoints = (landmarks, indices, color) => {
      ctx.fillStyle = color;
      for (const i of indices) {
        const lm = landmarks[i];

        if (!lm) continue;

        const x = (1 - lm.x) * vw;  // 반전!
        const y = lm.y * vh;

        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
      }
    };
  
    const drawConnections = (landmarks, connections, color) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      for (const [i1, i2] of connections) {
        const p1 = landmarks[i1];
        const p2 = landmarks[i2];

        if (!p1 || !p2) continue;

        const x1 = (1 - p1.x) * vw; // 반전
        const y1 = p1.y * vh;
        const x2 = (1 - p2.x) * vw; // 반전
        const y2 = p2.y * vh;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    };
  
    // ✅ 얼굴 랜드마크
    if (faceLandmarks.length) {
      const faceIndices = [33, 133, 474, 475, 476, 477, 362, 263, 469, 470, 471, 472, 1];
  
      // 눈 아래쪽 점 제거
      const leftEyePoints = [474, 475, 476, 477].map(i => ({index: i, y: faceLandmarks[i].y}));
      const rightEyePoints = [469, 470, 471, 472].map(i => ({index: i, y: faceLandmarks[i].y}));
  
      const leftEyeBottom = leftEyePoints.reduce((max, p) => (p.y > max.y ? p : max), leftEyePoints[0]);
      const rightEyeBottom = rightEyePoints.reduce((max, p) => (p.y > max.y ? p : max), rightEyePoints[0]);
  
      const filteredFacePoints = faceIndices
        .filter(i => i !== leftEyeBottom.index && i !== rightEyeBottom.index)
        .map(i => ({index: i, x: faceLandmarks[i].x, y: faceLandmarks[i].y}))
        .sort((a, b) => a.x - b.x); // x좌표 기준 정렬
  
      drawPoints(faceLandmarks, filteredFacePoints.map(p => p.index), 'red');
  
      const faceConnections = [];
      for (let i = 0; i < filteredFacePoints.length - 1; i++) {
        faceConnections.push([filteredFacePoints[i].index, filteredFacePoints[i + 1].index]);
      }
      drawConnections(faceLandmarks, faceConnections, 'grey');
  
      // ✅ 입 (양 끝점만)
      const mouthIndices = [61, 291];
      drawPoints(faceLandmarks, mouthIndices, 'red');
      drawConnections(faceLandmarks, [[61, 291]], 'grey');
    }
  
    // ✅ 포즈 랜드마크
    if (poseLandmarks?.length) {
      const poseIndices = [11, 12];
      drawPoints(poseLandmarks, poseIndices, 'red');
      drawConnections(poseLandmarks, POSE_CONNECTIONS, 'grey');
    }
  
    ctx.restore();
  }, [faceLandmarks, poseLandmarks]);
  
  const getResponse = async () => {
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/analyze-audio', {method: 'POST'});
      if (!res.ok) {
        console.error("analyze-audio 요청 실패:", res.status);
        return;
      }
  
      const data = await res.json();
      if (data.final_text) { setAudioCapture(data.final_text) } 
      else { alert("⛔ 인식된 음성이 없습니다."); }
    } 
    catch (err) { console.error("analyze-audio 요청 에러:", err); } 
    finally { setIsLoading(false); }
  };

  useEffect(() => {
    if (!audioCapture) return;
    setChatAnswers(prev => {
      const updated = [...prev];
      updated[currentQuestionIndex] = audioCapture;
      return updated;
    });
  }, [audioCapture, currentQuestionIndex]);

  const prevQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
      setAudioCapture("");  // 이동 시 음성 결과 초기화
    }
  };

  const nextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      setAudioCapture("");  // 다음 질문에서 초기화
    }
  };

  return (
    <div>
      <button onClick={startRecognition} disabled={isCameraOn}>
        {isCameraOn ? '분석 중...' : '면접 시작'}
      </button>
      <button onClick={stopRecognition} disabled={!isCameraOn}>
        면접 종료
      </button>
  
      <h2>📷 웹캠 + 얼굴 분석</h2>
  
      {isCameraOn && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '20px' }}>
          {/* 🎥 영상 + 분석 (왼쪽) */}
          <div style={{ position: 'relative', width: `${videoSize.width}px`, height: `${videoSize.height}px`, flexShrink: 0 }}>
            <video
              ref={videoRef}
              style={{ width: '100%', height: '100%', transform: 'scaleX(-1)', display: 'block' }}
              muted
              autoPlay
              playsInline
              onLoadedMetadata={() => {
                const video = videoRef.current;
                if (video) {
                  setVideoSize({
                    width: video.videoWidth,
                    height: video.videoHeight,
                  });
                }
              }}
            ></video>

            <canvas
              ref={canvasRef}
              width={videoSize.width}
              height={videoSize.height}
              style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none', zIndex: 10 }}
            />

            {/* 📊 분석 결과 UI (왼쪽 위) */}
            <div style={{
              position: 'absolute', top: 10, left: 10,
              backgroundColor: 'rgba(0, 0, 0, 0.6)', color: 'white',
              padding: '10px', borderRadius: '8px', fontSize: '14px',
              fontFamily: 'monospace', maxWidth: '300px', zIndex: 20
            }}>
              <h3>영상 분석 결과</h3>
              <p>👀 Gaze: {analysisResult.gaze || '-'}</p>
              <p>🧍 자세 평가: {analysisResult.shoulder_eval || '-'}</p>
              <p>📐 어깨 각도: {analysisResult.shoulder_angle !== undefined ? analysisResult.shoulder_angle.toFixed(1) : '-'}</p>
              <p>📊 안정성: {analysisResult.jitter_eval || '-'}</p>
              <p>🎯 중심 시선 비율: {analysisResult.gaze_center_ratio !== undefined ? analysisResult.gaze_center_ratio.toFixed(1) + '%' : '-'}</p>
              <p>🔄 시선 이동 횟수: {analysisResult.gaze_shift_count || 0}</p>
              <p>🔄 자세 변화 횟수: {analysisResult.posture_change_count || 0}</p>

              {/* 감정 분석 요약 (텍스트만) */}
              {analysisResult.emotions && analysisResult.emotions.length > 0 && (() => {
                const topEmotion = analysisResult.emotions.reduce((prev, current) =>
                  current.confidence > prev.confidence ? current : prev
                );
                return (
                  <div style={{ marginTop: 10 }}>
                    <h3>😊 감정 분석</h3>
                    <p>😃 감정: <strong>{topEmotion.emotion}</strong> (신뢰도: {(topEmotion.confidence * 100).toFixed(1)}%)</p>
                  </div>
                );
              })()}
            </div>
          </div>

          {/* ⚠️ 감정 경고 (오른쪽) */}
          {analysisResult.emotions && analysisResult.emotions.length > 0 && (() => {
            const topEmotion = analysisResult.emotions.reduce((prev, current) =>
              current.confidence > prev.confidence ? current : prev
            );
            const isWarning = topEmotion.emotion === "부정" || topEmotion.emotion === "긴장";
            if (!isWarning) return null;

            return (
              <div style={{
                backgroundColor: 'rgba(255, 0, 0, 0.75)',
                color: 'white',
                padding: '20px',
                borderRadius: '10px',
                fontSize: '16px',
                fontFamily: 'monospace',
                width: '300px',
                height: 'fit-content',
                alignSelf: 'flex-start'
              }}>
                <h3>⚠️ 감정 경고</h3>
                <p>현재 감정이 <strong>{topEmotion.emotion}</strong>입니다.<br />표정에 주의해주세요.</p>
              </div>
            );
          })()}
        </div>
      )}
  
      {/* 🎤 챗봇 인터뷰 UI */}
      {isCameraOn && (
        <div style={{ marginTop: '30px', fontFamily: 'monospace', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '8px' }}>
          <h3>📝 인터뷰 진행</h3>
          
          {/* 질문 이동 버튼 */}
          <button
            onClick={prevQuestion}
            disabled={currentQuestionIndex === 0}
            style={{ marginRight: '10px', marginBottom: '10px', padding: '8px 16px' }}
          >
            이전 질문으로 이동
          </button>
          <button
            onClick={nextQuestion}
            disabled={currentQuestionIndex >= questions.length - 1}
            style={{ marginBottom: '10px', padding: '8px 16px' }}
          >
            다음 질문으로 이동
          </button>

          {/* 현재 질문 */}
          <div style={{ padding: '10px', backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '6px', marginBottom: '10px' }}>
            <strong>Q{currentQuestionIndex + 1}.</strong> {questions[currentQuestionIndex]}
          </div>

          {/* 현재 답변 */}
          <div style={{ 
            padding: '10px', 
            backgroundColor: '#e1ffe1', 
            borderRadius: '6px', 
            minHeight: '40px', 
            marginBottom: '10px' 
          }}>
            🗣️ {chatAnswers[currentQuestionIndex] || "아직 답변이 인식되지 않았습니다."}
          </div>

          {/* ⬇️ 인식된 음성 출력 버튼 - 현재 답변 아래에 위치 */}
          <div style={{ marginBottom: '20px' }}>
            <button 
              onClick={getResponse} 
              disabled={!isCameraOn || isLoading}
              style={{
                padding: '8px 16px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isCameraOn && !isLoading ? 'pointer' : 'not-allowed'
              }}
            >
              {isLoading ? "기다리는 중..." : "🎤 답변 완료"}
            </button>
          </div>

          {/* 이전 질문들 히스토리 */}
          <div style={{ marginTop: '20px' }}>
            {questions.slice(0, currentQuestionIndex).map((q, i) => (
              <div key={i} style={{ marginBottom: '8px' }}>
                <div><strong>Q{i + 1}.</strong> {q}</div>
                <div style={{ marginLeft: 10, color: '#333' }}>{chatAnswers[i] || <i>답변 없음</i>}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Interview;