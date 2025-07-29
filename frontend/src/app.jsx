import React, { useEffect, useState, useRef } from 'react';

function App() {
  const [intervalId, setIntervalId] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [analysisResult, setAnalysisResult] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const faceLandmarks = analysisResult.face_landmarks;
  const poseLandmarks = analysisResult.pose_landmarks;

  const FACE_CONNECTIONS = [
    [33, 133],  // 왼쪽 눈 바깥 - 안쪽
    [133, 1],   // 왼쪽 눈 안쪽 - 코
    [1, 362],   // 코 - 오른쪽 눈 안쪽
    [362, 263], // 오른쪽 눈 안쪽 - 바깥쪽
    [61, 291]   // 입 (왼쪽 - 오른쪽)
  ];
  
  const POSE_CONNECTIONS = [
    [11, 12] // 양 어깨
  ];

  const setupCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      console.log("getUserMedia 성공", stream);
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
      const leftEyePoints = [474, 475, 476, 477].map(i => ({
        index: i,
        y: faceLandmarks[i].y,
      }));
      const rightEyePoints = [469, 470, 471, 472].map(i => ({
        index: i,
        y: faceLandmarks[i].y,
      }));
  
      const leftEyeBottom = leftEyePoints.reduce((max, p) => (p.y > max.y ? p : max), leftEyePoints[0]);
      const rightEyeBottom = rightEyePoints.reduce((max, p) => (p.y > max.y ? p : max), rightEyePoints[0]);
  
      const filteredFacePoints = faceIndices
        .filter(i => i !== leftEyeBottom.index && i !== rightEyeBottom.index)
        .map(i => ({
          index: i,
          x: faceLandmarks[i].x,
          y: faceLandmarks[i].y,
        }))
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
      const res = await fetch('http://localhost:8000/flush', {
        method: 'POST',
      });
      if (!res.ok) {
        console.error("flush 요청 실패:", res.status);
        return;
      }
  
      const data = await res.json();
      if (data.final_text) {
        alert("🗣️ 인식된 음성: " + data.final_text);
      } else {
        alert("⛔ 인식된 음성이 없습니다.");
      }
    } catch (err) {
      console.error("flush 요청 에러:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <button onClick={startRecognition} disabled={isCameraOn}>
        {isCameraOn ? '분석 중...' : '음성/영상 인식 시작'}
      </button>
      <button onClick={stopRecognition} disabled={!isCameraOn}>
        분석 중지
      </button>
      <button onClick={getResponse} disabled={!isCameraOn || isLoading}>
        {isLoading ? "기다리는 중..." : isCameraOn ? '인식된 음성 출력하기' : '인식 중이 아닙니다'}
      </button>

      <h2>📷 웹캠 + 얼굴 분석</h2>
      {isCameraOn && (
        <div
          style={{
            position: 'relative',
            width: videoRef.current?.videoWidth || 400,
            height: videoRef.current?.videoHeight || 300,
          }}
        >
          <video
            ref={videoRef}
            style={{ width: '100%', height: '100%', transform: 'scaleX(-1)' }}
            muted
            autoPlay
            playsInline
          ></video>
  
          {/* ✅ width/height 속성만 사용, style에선 제거 */}
          <canvas
            ref={canvasRef}
            width={videoRef.current?.videoWidth || 400}
            height={videoRef.current?.videoHeight || 300}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              pointerEvents: 'none',
              zIndex: 10,
            }}
          />
  
          <div style={{ marginTop: 10, whiteSpace: 'pre-line', fontFamily: 'monospace' }}>
            <h3>분석 결과</h3>
            <p>👀 Gaze: {analysisResult.gaze || '-'}</p>
            <p>🧍 자세 평가: {analysisResult.shoulder_eval || '-'}</p>
            <p>
              📐 어깨 각도:{' '}
              {analysisResult.shoulder_angle !== undefined
                ? analysisResult.shoulder_angle.toFixed(1)
                : '-'}
            </p>
            <p>📊 안정성: {analysisResult.jitter_eval || '-'}</p>
            <p>
              🎯 중심 시선 비율:{' '}
              {analysisResult.gaze_center_ratio !== undefined
                ? analysisResult.gaze_center_ratio.toFixed(1) + '%'
                : '-'}
            </p>
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
        </div>
      )}
    </div>
  );
}

export default App;