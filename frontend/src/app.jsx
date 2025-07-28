import React, { useEffect, useState, useRef } from 'react';

function App() {
  const [intervalId, setIntervalId] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [analysisResult, setAnalysisResult] = useState({});

  const videoRef = useRef(null);

  const setupCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      console.log("getUserMedia 성공", stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(e => console.error("video.play() 실패:", e));
        console.log("videoRef.current:", videoRef.current);
      } else {
        console.error("videoRef.current가 없음");
      }
    } catch (e) {
      console.error('웹캠 연결 실패:', e);
    }
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
    if (isCameraOn) {
      setupCamera();
    } else {
      // 정지 처리
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
        videoRef.current.srcObject = null;
      }
    }
  }, [isCameraOn]);

  const startRecognition = async () => {
    console.log("startRecognition 실행됨");
    try {
      // 1) 서버에 /start 요청 보내기
      const startRes = await fetch('http://localhost:8000/start', {
        method: 'POST',
      });
      if (!startRes.ok) {
        console.error('서버 시작 요청 실패:', startRes.status);
        return;
      }
      const startData = await startRes.json();
      console.log('서버 시작 응답:', startData);
  
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
            console.log('분석 결과:', result);
          } else {
            console.error('분석 실패:', res.status);
          }
        } catch (e) {
          console.error('분석 중 에러:', e);
        }
      }, 2000);
  
      setIntervalId(id);
    } catch (error) {
      console.error('Error:', error);
    }
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
      const stopRes = await fetch('http://localhost:8000/stop', {
        method: 'POST',
      });
      if (!stopRes.ok) {
        console.error('서버 정지 요청 실패:', stopRes.status);
      } else {
        console.log('서버 정지 완료');
      }
    } catch (e) {
      console.error('서버 정지 요청 중 에러:', e);
    }
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

  return (
    <div>
      <button onClick={startRecognition} disabled={isCameraOn}>
        {isCameraOn ? '분석 중...' : '음성/영상 인식 시작'}
      </button>
      <button onClick={stopRecognition} disabled={!isCameraOn}>
        분석 중지
      </button>

      <h2>📷 웹캠 + 얼굴 분석</h2>
      {isCameraOn && (
        <>
          <video ref={videoRef} style={{ width: 400, height: 300, transform: 'scaleX(-1)' }} muted autoPlay playsInline></video>
          <div style={{ marginTop: 10, whiteSpace: 'pre-line', fontFamily: 'monospace' }}>
            <h3>분석 결과</h3>
            <p>👀 Gaze: {analysisResult.gaze || '-'}</p>
            <p>🧍 자세 평가: {analysisResult.shoulder_eval || '-'}</p>
            <p>📐 어깨 각도: {analysisResult.shoulder_angle !== undefined ? analysisResult.shoulder_angle.toFixed(1) : '-'}</p>
            <p>📊 안정성: {analysisResult.jitter_eval || '-'}</p>
            <p>🎯 중심 시선 비율: {analysisResult.gaze_center_ratio !== undefined ? analysisResult.gaze_center_ratio.toFixed(1) + '%' : '-'}</p>
            <p>🔄 시선 이동 횟수: {analysisResult.gaze_shift_count || 0}</p>
            <p>🔄 자세 변화 횟수: {analysisResult.posture_change_count || 0}</p>

            {analysisResult.emotions && analysisResult.emotions.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <h3>😊 감정 분석</h3>
                {analysisResult.emotions.map((emotionObj, index) => (
                  <p key={index}>
                    😃 감정: <strong>{emotionObj.emotion}</strong> (
                    신뢰도: {(emotionObj.confidence * 100).toFixed(1)}%)
                  </p>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default App;