import pyaudio
import threading
import queue
import requests
import time

CHUNK = 1024
RATE = 16000

send_queue = queue.Queue()

def sender():
    print("[sender] 스레드 시작")
    while True:
        data = send_queue.get()
        if data is None:
            print("[sender] 종료")
            break
        try:
            r = requests.post("http://host.docker.internal:8000/audio-chunk", data=data)
            print(f"[sender] Sent chunk, status: {r.status_code}")
        except Exception as e:
            print(f"[sender] 전송 오류: {e}")

print("[main] PyAudio 초기화")
p = pyaudio.PyAudio()

print("[main] stream.open 시작")
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
print("[main] stream.open 완료")

threading.Thread(target=sender, daemon=True).start()

try:
    while True:
        data = stream.read(CHUNK)
        print(f"[main] 오디오 chunk 캡처됨: {len(data)} bytes")
        send_queue.put(data)
except KeyboardInterrupt:
    print("[main] 종료 요청 수신")

send_queue.put(None)
stream.stop_stream()
stream.close()
p.terminate()