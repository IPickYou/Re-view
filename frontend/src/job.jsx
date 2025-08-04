import React, { useState } from 'react';
import { useNavigate } from "react-router-dom";

import LoadingOverlay from './components/loading_overlay.jsx';

function Job() {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);

    const handleUrlChange = (e) => { setUrl(e.target.value); }; // URL 입력처리
    const navigate = useNavigate();

    // 크롤링
    const handleUrlSubmit = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/crawling', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            if (!res.ok) {
                console.error('서버 시작 요청 실패:', res.status);
                setLoading(false);
                return;
            }

            const data = await res.json();  // 응답을 JSON으로 파싱
            navigate("/interview", { state: { questions: data.questions, modelAnswers: data.answers } });
        }
        catch (error) { console.error('Error:', error); }
        finally { setLoading(false); }
    };

    return (
        <>
            <style>
                {`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .spinner-small {
                    width: 22px;
                    height: 22px;
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #00aaff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto;
                }
                .spinner-large {
                    width: 80px;
                    height: 80px;
                    border: 8px solid rgba(255,255,255,0.3);
                    border-top: 8px solid white;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 20px;
                }
                .overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0,0,0,0.4);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 1000;
                }
                .overlay-content {
                    background: #2f2f2f;
                    padding: 30px 40px;
                    border-radius: 12px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    color: white;
                    max-width: 90%;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
                    font-family: system-ui,-apple-system,BlinkMacSystemFont,sans-serif;
                }
                .overlay-text {
                    font-size: 1.25rem;
                    line-height: 1.3;
                    margin-top: 8px;
                }
                .sr-only {
                    position: absolute;
                    width: 1px;
                    height: 1px;
                    padding: 0;
                    margin: -1px;
                    overflow: hidden;
                    clip: rect(0 0 0 0);
                    white-space: nowrap;
                    border: 0;
                }
            `}
            </style>

            {loading && (<LoadingOverlay message="해당 채용공고에 맞는 예시 질문 및 답변을 생성 중 입니다." />)}

            <div style={styles.container}>
                <div style={{ ...styles.inputContainer, flexDirection: 'column', alignItems: 'center' }}>
                    <h2>모의 면접을 희망하는 채용공고 링크를 입력해주세요.</h2>
                    <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginTop: 12 }}>
                        <input
                            type="url"
                            value={url}
                            onChange={handleUrlChange}
                            placeholder="URL을 입력하세요"
                            style={styles.input}
                            disabled={loading}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !loading) {
                                handleUrlSubmit();
                                }
                            }}
                            aria-label="채용공고 링크 입력"
                        />
                        <button
                            onClick={handleUrlSubmit}
                            style={{
                                ...styles.button,
                                cursor: loading ? 'not-allowed' : 'pointer',
                                opacity: loading ? 0.7 : 1,
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                            }}
                            disabled={loading}
                            aria-disabled={loading}
                            aria-label="등록 버튼"
                        >
                            {loading ? (
                                <>
                                    <div className="spinner-small" aria-hidden="true" />
                                    <span className="sr-only">로딩 중</span>
                                </>
                            ) : ('등록')}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

const styles = {
    container: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh', // 화면 높이를 100%로 설정
        backgroundColor: '#f0f0f0', // 배경색
    },
    inputContainer: {
        display: 'flex',
        alignItems: 'center',
        border: '1px solid #ccc', // 입력창과 버튼을 감싸는 테두리
        padding: '10px',
        borderRadius: '5px',
        backgroundColor: 'white',
    },
    input: {
        padding: '8px',
        fontSize: '16px',
        border: '1px solid #ccc',
        borderRadius: '5px',
        marginRight: '10px', // 버튼과의 간격을 추가
        width: '250px', // 입력창의 너비
    },
    button: {
        padding: '10px 15px',
        fontSize: '16px',
        backgroundColor: '#007BFF',
        color: 'white',
        border: 'none',
        borderRadius: '5px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
    },
};

export default Job;