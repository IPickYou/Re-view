import React, { useState } from 'react';
import { useNavigate } from "react-router-dom";

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
            .spinner {
                width: 22px;
                height: 22px;
                border: 3px solid #f3f3f3; /* 연한 회색 */
                border-top: 3px solid #00aaff; /* 버튼 배경과 대비 좋은 밝은 파랑 */
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            `}
            </style>

            <div style={styles.container}>
                <div style={styles.inputContainer}>
                    <input 
                        type="url" 
                        value={url} 
                        onChange={handleUrlChange} 
                        placeholder="URL을 입력하세요" 
                        style={styles.input}
                        disabled={loading}
                    />
                    <button
                        onClick={handleUrlSubmit}
                        style={{ ...styles.button, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
                        disabled={loading}
                    >
                        {loading ? <div className="spinner"></div> : '등록'}
                    </button>
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
    }
};

export default Job;