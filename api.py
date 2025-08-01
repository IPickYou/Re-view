from db_crud import init_db, save_full_session, get_session
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

@app.post("/crawling")
def crawl(request: UrlRequest):
    url = request.url
    questions = job_crawling(url)
    return questions

@app.post("/start")
def api_start():
    response = start_recognition()
    return response

@app.post("/analyze-frame")
def analyze_frame(data: ImageData):
    video_analyzer = get_video_analyzer()
    if video_analyzer is None:
        raise HTTPException(status_code=503, detail="Video analyzer not initialized")

    img = decode_base64_image(data.image)
    video_analyzer.update_frame(img)
    return video_analyzer.analyze_latest_frame()

@app.post("/analyze-audio")
def analyze_audio():
    audio_analyzer = get_audio_analyzer()
    if audio_analyzer is not None:
        final_text = audio_analyzer.get_result()
        return {"final_text": final_text}
    else:
        return {"error": "Audio analyzer is not running."}

@app.post("/stop")
def api_stop():
    result = stop_recognition()
    return result

@app.post("/analyze-user")
def analyze_user(data: AnswerData):
    return user_style(data.chatAnswers)

@app.post("/evaluate-answer")
def eval(data: EvalData):
    return eval_answer(data.question, data.answer)

@app.post("/save-result")
async def save(request: Request):
    body = await request.json()

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

    # 조회 예시
    # sess = get_session("2025-08-01-1754037350812")
    # print("Loaded session:", sess.session_id)
    # print("Interview entries:", len(sess.interview_entries))
    # print("Model answers count:", len(sess.model_answers))

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)