from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from main import decode_base64_image, get_video_analyzer, start_recognition, stop_recognition
from schema import ImageData 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 개발 서버 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/start")
def api_start():
    response = start_recognition()
    return response

@app.post("/analyze-frame")
def analyze(data: ImageData):
    video_analyzer = get_video_analyzer()
    if video_analyzer is None:
        raise HTTPException(status_code=503, detail="Video analyzer not initialized")

    img = decode_base64_image(data.image)
    video_analyzer.update_frame(img)
    return video_analyzer.analyze_latest_frame()

@app.post("/stop")
def api_stop():
    stop_recognition()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)