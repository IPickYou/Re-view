from audio_analisys import RealtimeAudioAnalyzer
from video_analisys import VideoAnalyzer

import threading

# 🔊 음성 인식 함수
def run_audio():
    analyzer = RealtimeAudioAnalyzer()
    analyzer.start()

# 🎥 영상 인식 함수 (예: 얼굴 감지)
def run_video():
    analyzer = VideoAnalyzer()
    analyzer.start()

def start_recognition():
    audio_thread = threading.Thread(target=run_audio)
    video_thread = threading.Thread(target=run_video)

    audio_thread.start()
    video_thread.start()

    return {"status": "recognition started"}

start_recognition()