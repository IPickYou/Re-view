import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

function History() {
    const { sessionId } = useParams(); // /result-:sessionId 라우트에서 sessionId 추출
    const navigate = useNavigate();

    useEffect(() => {
        if (sessionId) {
            const loadHistory = async () => {
                try {
                    const res = await fetch('http://localhost:8000/load-session', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ sessionId })
                    });

                    if (!res.ok) {
                        const errBody = await res.json();
                        console.error('검증 에러 상세:', errBody);
                        return;
                    }

                    const data = await res.json();
                    const session_id = data["session_id"]
                    const interview = data["interview"]
                    const analysis_result = data["analysis_result"]
                    const model_answers = data["model_answers"]
                    const questions = data["questions"]
                    const chat_answers = data["chat_answers"]

                    console.log("session_id:", session_id);
                    console.log("interview:", interview);
                    console.log("analysis_result:", analysis_result);
                    console.log("model_answers:", model_answers);
                    console.log("questions:", questions);
                    console.log("chat_answers:", chat_answers);

                    navigate("/result", {
                        state: {
                            interview: interview,
                            analysisResult: analysis_result,
                            questions: questions,
                            modelAnswers: model_answers,
                            chatAnswers: chat_answers
                        }
                    });
                }
                catch (error) { console.error('Error:', error); }
            }

            loadHistory();
        }
    }, [sessionId]);

    return (
        <></>
    );
}

export default History;