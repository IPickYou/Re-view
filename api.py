from db_crud import init_db, save_full_session, get_session, get_all_session_ids, load_full_session
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from main import (
    decode_base64_image,
    eval_answer,
    get_audio_analyzer,
    get_video_analyzer,
    job_crawling,
    start_recognition,
    stop_recognition,
    user_style,
)
from schema import AnswerData, EvalData, ImageData, UrlRequest

init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 개발 서버 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 웹 크롤링 API
@app.post("/crawling")
def crawl(request: UrlRequest):
    url = request.url
    questions = job_crawling(url)
    return questions

# 실시간 음성/영상 인식 시작 API
@app.post("/start")
def api_start():
    response = start_recognition()
    return response

# 현재 영상 프레임 분석 API
@app.post("/analyze-frame")
def analyze_frame(data: ImageData):
    video_analyzer = get_video_analyzer()
    if video_analyzer is None:
        raise HTTPException(status_code=503, detail="Video analyzer not initialized")

    img = decode_base64_image(data.image)
    video_analyzer.update_frame(img)
    return video_analyzer.analyze_latest_frame()

# 답변 완료 버튼 클릭 시 호출되는 API
@app.post("/analyze-audio")
def analyze_audio():
    audio_analyzer = get_audio_analyzer()
    if audio_analyzer is not None:
        final_text = audio_analyzer.get_result()
        return {"final_text": final_text}
    else:
        return {"error": "Audio analyzer is not running."}

# 실시간 음성/영상 인식 중지 API
@app.post("/stop")
def api_stop():
    result = stop_recognition()
    return result

# 사용자 스타일 분석 API
@app.post("/analyze-user")
def analyze_user(data: AnswerData):
    return user_style(data.chatAnswers)

# 답변 평가 API
@app.post("/evaluate-answer")
def eval(data: EvalData):
    return eval_answer(data.question, data.answer)

# 저장한 세션목록 조회 API
@app.post("/get-history")
def get_history():
    return get_all_session_ids()

# 저장한 세션 로드 API
@app.post("/load-session")
async def load_session(request: Request):
    body = await request.json()
    session_id = body.get("sessionId")
    if not session_id:
        raise HTTPException(status_code=400, detail="sessionId is required")
    result = load_full_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    
    print("Loaded session:", result)

    return result

# 세션 저장 API
@app.post("/save-result")
async def save(request: Request):
    body = await request.json()

    # 저장할 데이터 추출
    session_id = body["sessionId"]
    interview = body["interview"]
    analysis_result = body["analysisResult"]
    model_answers = body["modelAnswers"]
    questions = body["questions"]
    chat_answers = body["chatAnswers"]

    data = {
        "session_id": session_id,
        "interview": interview,
        "analysis_result": analysis_result,
        "model_answers": model_answers,
        "questions": questions,
        "chat_answers": chat_answers
    }

    save_full_session(data)

    sess = get_session(session_id)
    print("저장된 세션 ID: ", sess.session_id)
    print("저장된 세션: ", sess)

    return {"status": "ok", "sessionId": sess.session_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)