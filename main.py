from audio_analisys import RealtimeAudioAnalyzer
from job_crawling import JobCrawler
from video_analisys import VideoAnalyzer

import base64
import cv2
import numpy as np
import re
import threading

job_crawler = None

is_running = False # 실행 중복 방지용 플래그
video_analyzer = None
audio_analyzer = None
audio_thread = None
video_thread = None

# 채용공고 크롤링 함수
def job_crawling(url):
    global job_crawler

    job_crawler = JobCrawler()

    print("채용 공고 텍스트 추출 중 ...")
    job_text = job_crawler.extract_wanted_job_text_selenium(url)
    if not job_text:
        print("채용 공고 내용을 찾지 못 했습니다.")
        return

    print("\n추출된 채용 공고 텍스트 일부 :\n")
    print(job_text, "\n")

    print("면접 질문 생성 중 ...")
    questions = job_crawler.generate_interview_questions(job_text)
    print("\n예상 면접 질문 :\n")
    print(questions)

    return questions

# 🔊 음성 인식 함수
def run_audio():
    global audio_analyzer

    audio_analyzer = RealtimeAudioAnalyzer()
    audio_analyzer.start()

# 🎥 영상 인식 함수 (예: 얼굴 감지)
def run_video():
    global video_analyzer

    video_analyzer = VideoAnalyzer()
    video_analyzer.start()

def start_recognition():
    global is_running, audio_thread, video_thread

    if not is_running:
        is_running = True
        audio_thread = threading.Thread(target=run_audio, daemon=False)
        video_thread = threading.Thread(target=run_video, daemon=False)
        audio_thread.start()
        video_thread.start()
        return {"status": "Recognition started"}
    else: return {"status": "Already running"}

def stop_recognition():
    global is_running, audio_analyzer, video_analyzer, audio_thread, video_thread

    if is_running:
        if audio_analyzer:
            audio_analyzer.stop()
            audio_analyzer = None

        if video_analyzer:
            video_analyzer.stop()
            video_analyzer = None

        # 쓰레드 종료 대기
        if audio_thread:
            audio_thread.join()
            audio_thread = None
        if video_thread:
            video_thread.join()
            video_thread = None

        is_running = False
        return {"status": "Recognition stopped"}
    else: return {"status": "Not running"}

def decode_base64_image(base64_str):
    base64_str = re.sub("^data:image/.+;base64,", "", base64_str)
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def get_video_analyzer():
    global video_analyzer
    return video_analyzer

def get_audio_analyzer():
    global audio_analyzer
    return audio_analyzer

if __name__ == "__main__":
    start_recognition()  # ✅ 직접 실행할 때만 동작