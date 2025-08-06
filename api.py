from db_crud import (
    init_db,
    save_full_session,
    get_session,
    get_all_session_ids,
    load_full_session,
)
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
    try:
        url = request.url
        questions = job_crawling(url)  # 채용 공고에서 예상 면접 질문과 답변 생성
        return questions
    except Exception as e:
        print("Error in /crawling:", e)
        raise HTTPException(status_code=500, detail=str(e))


# 실시간 음성/영상 인식 시작 API
@app.post("/start")
def api_start():
    response = start_recognition()  # 음성/영상 인식 시작
    return response


# 현재 영상 프레임 분석 API
@app.post("/analyze-frame")
def analyze_frame(data: ImageData):
    video_analyzer = get_video_analyzer()  # 영상 분석기 가져오기
    if video_analyzer is None:
        raise HTTPException(status_code=503, detail="Video analyzer not initialized")

    img = decode_base64_image(data.image)  # base64 이미지 디코딩
    video_analyzer.update_frame(img)  # 최신 프레임 업데이트
    return video_analyzer.analyze_latest_frame()  # 현재 프레임 분석 결과 반환


# 실시간 음성 데이터 수신 API
@app.post("/audio-chunk")
async def audio_chunk(request: Request):
    audio_analyzer = get_audio_analyzer()
    data = await request.body()
    if audio_analyzer:
        audio_analyzer.push_audio(data)
        return {"status": "chunk received"}
    else:
        return {"error": "Audio analyzer not running"}


# 답변 완료 버튼 클릭 시 호출되는 API
@app.post("/analyze-audio")
def analyze_audio():
    audio_analyzer = get_audio_analyzer()
    if audio_analyzer is not None:
        print(f"[analyze_audio] 현재 result_text 길이: {len(audio_analyzer.result_text)}")
        final_text = audio_analyzer.get_result()
        print(f"[analyze_audio] 반환할 텍스트: {final_text}")
        return {"final_text": final_text}
    else:
        return {"error": "Audio analyzer is not running."}


# 실시간 음성/영상 인식 중지 API
@app.post("/stop")
def api_stop():
    result = stop_recognition()  # 음성/영상 인식 중지
    return result


# 사용자 스타일 분석 API
@app.post("/analyze-user")
def analyze_user(data: AnswerData):
    return user_style(data.chatAnswers)  # 사용자 스타일 분석 결과 반환


# 답변 평가 API
@app.post("/evaluate-answer")
def eval(data: EvalData):
    return eval_answer(data.question, data.answer)  # 답변 평가 결과 반환


# 저장한 세션목록 조회 API
@app.post("/get-history")
def get_history():
    return get_all_session_ids()  # 저장된 세션 ID 목록 반환


# 저장한 세션 로드 API
@app.post("/load-session")
async def load_session(request: Request):
    body = await request.json()
    session_id = body.get("sessionId")  # 세션 ID 추출
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
        "chat_answers": chat_answers,
    }

    save_full_session(data)  # 세션 데이터 저장

    sess = get_session(session_id)  # 세션 데이터 조회
    print("저장된 세션 ID: ", sess.session_id)
    print("저장된 세션: ", sess)

    return {"status": "ok", "sessionId": sess.session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
