import React, { useState, useEffect } from 'react';

export default function QnaItem({ question, answer, modelAnswer, index }) {
  const [isOpen, setIsOpen] = useState(false);
  const [analyzed, setAnalyzed] = useState(null);

  const questionStyle = {
    cursor: 'pointer',
    backgroundColor: '#eaeaea',
    padding: '10px',
    borderRadius: '6px',
    marginBottom: '8px',
    userSelect: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between', // 텍스트와 화살표를 좌우 끝으로 분리
  };

  const toggleOpen = () => setIsOpen(!isOpen);

  const analyze = async () => {
    try {
        const res = await fetch('http://localhost:8000/evaluate-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, answer })
        });
    
        if (!res.ok) {
            console.error('서버 시작 요청 실패:', res.status);
            return;
        }

        const data = await res.json();  // 응답을 JSON으로 파싱
        setAnalyzed(data);
    } 
    catch (error) { console.error('Error:', error); }
  }

  useEffect(() => {
    if (question && answer) { analyze(); }
    else { setAnalyzed(null); }   
  }, [question, answer]);

  return (
    <div style={{ marginBottom: '12px', textAlign: 'left' }}>
      <div
        style={questionStyle}
        onClick={toggleOpen}
        aria-expanded={isOpen}
        aria-controls={`answer-${index}`}
      >
        <strong>Q{index + 1}.</strong> {question}
        <span style={{ fontWeight: 'bold' }}>
          {isOpen ? '▲' : '▼'}
        </span>
      </div>
      {isOpen && (
        <div
          id={`answer-${index}`}
          style={{
            background: '#f5f5f5',
            padding: '12px',
            borderRadius: '6px',
            marginTop: '6px',
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
            fontSize: '0.9rem',
          }}
        >
          <div><strong>답변:</strong> {answer || "답변하지 않은 질문입니다."}</div>
          <div style={{ marginTop: '8px' }}>
            <strong>분석 결과:</strong>
            {analyzed ? (<div>{analyzed}</div>) : (<div>답변하지 않은 질문입니다.</div>)}
          </div>
          <div style={{ marginTop: '8px' }}>
            <strong>모범 답안:</strong>
            {modelAnswer ? (<div>{modelAnswer}</div>) : (<div>답변하지 않은 질문입니다.</div>)}
          </div>
        </div>
      )}
    </div>
  );
}