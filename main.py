from audio_analisys import RealtimeAudioAnalyzer
from interview_question_generator import QuestionGenerator
from job_crawling import JobCrawler
from sentence_analisys import SentenceAnalyzer
from video_analisys import VideoAnalyzer

import base64
import cv2
import numpy as np
import re
import threading

job_crawler = None
question_generator = None

is_running = False # 실행 중복 방지용 플래그
video_analyzer = None
audio_analyzer = None
audio_thread = None
video_thread = None

sentence_analyzer = SentenceAnalyzer()

# 채용공고 크롤링 함수
def job_crawling(url):
    global job_crawler
    global question_generator

    # JobCrawler와 QuestionGenerator 인스턴스 생성
    job_crawler = JobCrawler()
    question_generator = QuestionGenerator()

    job_text = job_crawler.extract_wanted_job_text_selenium(url) # 채용 공고 텍스트 추출
    if not job_text:
        print("채용 공고 내용을 찾지 못 했습니다.")
        return

    # 예상 면접 질문과 답변 생성
    questions = []
    crawl_questions = job_crawler.generate_interview_questions(job_text) # OpenAI API를 사용하여 면접 질문 생성
    crawl_questions = job_crawler.extract_text(crawl_questions) # 채용 공고에서 추출한 질문 텍스트를 정제
    gen_questions = question_generator.generate() # LLM을 사용하여 추가 질문 생성
    questions.extend(crawl_questions[:min(2, len(crawl_questions))]) # 채용 공고에서 추출한 질문 중 2개만 사용
    questions.extend(gen_questions[:min(1, len(gen_questions))]) # 각 클러스터에서 2개의 질문만 사용
    print("\n예상 면접 질문 :")
    print(questions)

    answers = job_crawler.generate_interview_answers(questions) # OpenAI API를 사용하여 면접 답변 생성
    answers = job_crawler.extract_text(answers) # 예상 답변에서 추출한 답변 텍스트를 정제
    print("\n예상 면접 답변 :")
    print(answers)

    return {"questions": questions, "answers": answers}

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

    if not is_running: # 실행 중복 방지
        # 멀티 스레딩 시작
        is_running = True
        audio_thread = threading.Thread(target=run_audio, daemon=False)
        video_thread = threading.Thread(target=run_video, daemon=False)
        audio_thread.start()
        video_thread.start()
        return {"status": "Recognition started"}
    else: return {"status": "Already running"}

def stop_recognition():
    global is_running, audio_analyzer, video_analyzer, audio_thread, video_thread

    if is_running: # 실행 중복 방지
        if audio_analyzer: # 음성 인식 중지 및 결과 저장
            audio_analyzer.stop()
            result = audio_analyzer.save_results()
            audio_analyzer = None
        else: result = {"interview": []} 

        if video_analyzer: # 영상 인식 중지
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
        return result
    else: return {"status": "Not running"}

def decode_base64_image(base64_str):
    base64_str = re.sub("^data:image/.+;base64,", "", base64_str) # base64 문자열에서 메타데이터 제거
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8) # OpenCV에서 사용할 수 있는 형식으로 변환
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR) # OpenCV BGR 이미지로 디코딩

def user_style(answer):
    return sentence_analyzer.analyze_user_style(answer) # 사용자 스타일 분석

def eval_answer(question, answer):
    return sentence_analyzer.evaluate_answer(question, answer) # 답변 평가

def get_video_analyzer():
    global video_analyzer
    return video_analyzer

def get_audio_analyzer():
    global audio_analyzer
    return audio_analyzer

if __name__ == "__main__":
    start_recognition()  # ✅ 직접 실행할 때만 동작