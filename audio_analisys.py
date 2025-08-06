from audio_utils import extract_audio_features
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import speech
from sklearn.metrics.pairwise import cosine_similarity
from transformers import T5ForConditionalGeneration, PreTrainedTokenizerFast
from utils import OpenAIClient, OpenAIEmbedding, dump_json, read_json
from queue import Queue

import os
import pyaudio
import pyloudnorm as pyln
import soundfile as sf
import threading
import time
import torch
import queue
import wave
import whisper

"""
### 음성 분석의 정상범위 평가 기준
- 소리 크기 : –23 LUFS ± 1.0
- 말 빠르기 : 129.7 ± 25.9 WPM (≈ 1.73 ~ 2.59 WPS)

### 평가 기준 근거
- 소리 크기
    - EBU(European Broadcasting Union)의 라이브 방송 표준 범위
    - 참고 근거 : https://tech.ebu.ch/files/live/sites/tech/files/shared/r/r128.pdf
- 말 빠르기
    - (자연스러운 자발적 발화에서의 평균 WPM 추정 범위) / 60 => WPS(Words Per Second)
    - 참고 근거 : https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002099342
"""

# 마이크 설정
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

class RealtimeAudioAnalyzer:
    def __init__(self, language_code="ko-KR"):
        load_dotenv()
        self.openai_client = OpenAIClient() # OpenAI API 클라이언트 초기화

        # Google Speech-to-Text 설정
        self.language_code = language_code
        self._buff = queue.Queue()
        self.closed = True
        self.client = speech.SpeechClient()
        self.streaming_config = self._get_streaming_config()
        self.recent_audio_chunk = []
        self.sentences = []

        # 후교정 처리를 위한 큐와 스레드
        self.postprocess_queue = Queue()
        self.postprocess_thread = threading.Thread(target=self._postprocess_worker)
        self.postprocess_thread.start()

        # 음성 스트림 설정
        # self.audio_interface = pyaudio.PyAudio()
        # self.audio_stream = self.audio_interface.open(
        #     format=pyaudio.paInt16,
        #     channels=1, rate=RATE,
        #     input=True, frames_per_buffer=CHUNK,
        #     stream_callback=self._fill_buffer,
        # )

        # 음성 인식 결과 저장용 변수
        self.current_transcript = ""
        self.result_text = ""

    # Google Speech-to-Text 설정
    def _get_streaming_config(self):
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
        )
        return speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True
        )
    
    def push_audio(self, audio_chunk):
        if not self.closed:
            self._buff.put(audio_chunk)
            self.recent_audio_chunk.append(audio_chunk)


    # 오디오 스트림 콜백 함수
    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        self.recent_audio_chunk.append(in_data)
        return None, pyaudio.paContinue

    # 오디오 스트림 생성기
    def _audio_generator(self):
        silence_chunk = b'\x00' * CHUNK * 2
        while not self.closed:
            try:
                chunk = self._buff.get(timeout=1)
            except queue.Empty:
                chunk = silence_chunk
            if chunk is None:
                return
            yield speech.StreamingRecognizeRequest(audio_content=chunk)



    # LUFS 계산을 위한 함수
    def _calculate_lufs(self, wav_file_path):
        data, rate = sf.read(wav_file_path)
        meter = pyln.Meter(rate)
        print(f"🧪 LUFS 계산 오디오 길이: {len(data)/rate:.2f}초")
        if len(data.shape) > 1:  # 스테레오인 경우
            data = data.mean(axis=1)  # 모노로 변환

        loudness = meter.integrated_loudness(data) # 통합 LUFS 계산
        return loudness

    # 최근 오디오 세그먼트 저장 함수
    def _save_recent_audio(self, filename, duration_sec):
        required_chunks = int(duration_sec * RATE / CHUNK)
        actual_chunks = len(self.recent_audio_chunk)
        print(f"🧪 저장 요청: duration={duration_sec:.2f}s, 필요 청크={required_chunks}, 현재 청크={actual_chunks}")

        if actual_chunks < required_chunks:
            print("⚠️ 오디오 버퍼 부족, segment 저장 건너뜀")
            return

        byte_data = b''.join(self.recent_audio_chunk[-required_chunks:])

        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16bit PCM
            wf.setframerate(RATE)
            wf.writeframes(byte_data)


    # 오디오 분석 결과 저장 함수
    def save_results(self):
        return {"interview": self.sentences}

    # 오디오 분석 메인 함수
    def _analyze_audio(self, responses):
        start_time = time.time() # 첫 문장 시작 시간 초기화

        for response in responses:
            print("📥 응답 수신됨")

            if not response.results:
                print("⚠️ 빈 응답")
                continue

            # 첫 번째 결과만 처리
            result = response.results[0]
            transcript = result.alternatives[0].transcript.strip()

            if result.is_final:
                end_time = time.time() # 문장 끝 시간 기록
                self.postprocess_queue.put((transcript, start_time, end_time)) # 후처리 큐에 추가
                
                print(f"💬 [최종] {transcript}", flush=True)
                start_time = time.time()  # 다음 문장을 위한 시작시간 초기화
                self.result_text += transcript + " "
                self.result_text = self.result_text[-500:]  # 최대 길이 유지
                self.current_transcript = ""  # 🔴 최종이면 중간 내용 초기화    
            else:
                self.current_transcript = transcript  # 🟢 중간 텍스트 저장
                print(f"💬 [중간] {transcript}", flush=True)

    # 후처리 작업을 위한 워커 스레드
    # 교정, 감정 분석 등을 처리      
    def _postprocess_worker(self):
        while True:
            item = self.postprocess_queue.get() # 큐에서 아이템 가져오기
            if item is None:
                break
            transcript, start_time, end_time = item
            
            # 교정, 감정분석 등 느린 API 호출 처리
            duration = max(0.5, end_time - start_time)  # 🔧 최소 길이 보장
            wps = len(transcript.split()) / duration if duration > 0 else 0

            # 1. 문장 교정
            corrected = self.openai_client.create_response(
                system_content=(
                    "당신은 면접자의 음성 인식 결과를 맞춤법과 흐름 위주로 교정하는 교정 도우미입니다. "
                    "사용자의 문장 구조, 어투 및 어미를 보존하고, 문법 오류와 앞 뒤 단어와 이어지지 않는 어색한 표현만 자연스럽게 수정하세요."
                    "그리고 답변은 수정사항을 적용한 내용만 응답하세요."
                    "만약 수정사항이 없는 경우, 원본을 그대로 응답하세요."
                ),
                user_content=transcript
            )

            # 2. 유사도 계산
            original_embedding = OpenAIEmbedding(transcript).response
            corrected_embedding = OpenAIEmbedding(corrected).response
            similarity = cosine_similarity([original_embedding], [corrected_embedding])[0][0]


            # 3. 실시간 감정 분석용 오디오 segment 추출
            tmp_filename = f"tmp_segment_{int(start_time)}.wav"
            self._save_recent_audio(tmp_filename, duration)

            lufs = self._calculate_lufs(tmp_filename) # 🔊 LUFS 계산

            audio_features = extract_audio_features(tmp_filename, 0, duration) # 음향적 특징 추출

            emotion_prompt = f"""
            문장: "{transcript}"
            평균 pitch: {audio_features["pitch_mean"]:.1f}Hz, pitch 변화량: {audio_features["pitch_std"]:.2f}
            평균 에너지: {audio_features["energy_mean"]:.5f}, 에너지 변화량: {audio_features["energy_std"]:.5f}
            말 빠르기(WPS): {wps:.2f}
            """

            try:
                emotion = self.openai_client.create_response(
                    system_content=(
                        "당신은 문장의 감정을 분석하는 전문가입니다. "
                        "텍스트와 음향적 특성을 고려하여 이 문장의 감정을 추론하여 감정 하나의 단어만 출력하세요. 예: 기쁨, 슬픔, 분노, 불안, 놀람, 중립 중 하나"
                    ),
                    user_content=emotion_prompt
                )

                if not emotion.strip(): emotion = "중립"
            except Exception as e:
                print(f"[감정 분석 실패] {e}")
                emotion = "중립"

            print(f"🗣️ [최종] [{emotion}] {corrected}")

            # 분석 결과 저장
            self.sentences.append({
                "original_sentence": transcript,
                "corrected_sentence": corrected,
                "cosine_similarity": similarity,
                "emotion": emotion,
                "start": start_time,
                "end": end_time,
                "wps": wps,
                "lufs": lufs
            })

            try: # 임시 파일 삭제
                os.remove(tmp_filename)
            except FileNotFoundError:
                pass 

    # 결과를 반환하는 함수
    # result_text가 비어있으면 최대 timeout초까지 기다렸다가 반환
    # 반환 후에는 result_text를 초기화하여 중복 반환 방지
    def get_result(self, timeout=10):
        """
        result_text가 비어있으면 최대 timeout초까지 기다렸다가 반환.
        반환 후에는 result_text를 초기화하여 중복 반환 방지.
        """
        waited = 0
        while not self.result_text and waited < timeout:
            time.sleep(0.1)
            waited += 0.1
        
        final_text = self.result_text
        self.result_text = ""  # 반환 후 초기화
        return final_text

    # 오디오 스트림 시작 함수
    # 이 함수는 별도의 스레드에서 실행되어야 함
    def start(self):
        print("🔧 start() 실행됨")
        self.closed = False
        print("🔁 오디오 스트림 시작됨")

        requests = self._audio_generator()  # _buff 큐에서 데이터 받아 Google STT에 전달

        responses = self.client.streaming_recognize(self.streaming_config, requests)

        def recognize_loop():
            self._analyze_audio(responses)

        audio_thread = threading.Thread(target=recognize_loop)
        audio_thread.start()

        while not self.closed:
            time.sleep(0.1)

        audio_thread.join()
        self.cleanup()

    
    def stop(self):
        print("🛑 중지 함수 호출됨.")
        self.closed = True
        self._buff.put(None)
        self.postprocess_queue.put(None)
        self.postprocess_thread.join()

    # 리소스 정리 함수
    # 오디오 스트림과 후처리 스레드를 정리
    def cleanup(self):
        print("🧹 리소스 정리 중")
        # if self.audio_stream is not None:
        #     self.audio_stream.stop_stream()
        #     self.audio_stream.close()
        # if self.audio_interface is not None:
        #     self.audio_interface.terminate()

class StaticAudioAnalyzer:
    def __init__(self):
        self.whisper_model = self.load_whisper_model()
        self.openai_client = OpenAIClient()

    def load_whisper_model(self, model_size = "large"):
        '''
        Whisper 모델을 return 하는 함수(model_size 다운그레이드 시 발음이 부정확할 경우 이상하게 인식되는 경우가 있어 large 고정)

        파라미터
        - model_size: Whisper 모델 크기(tiny, base, small, medium, large 중 선택)

        호출 예시: model = load_whisper_model()
        '''
        
        model = whisper.load_model(model_size) # Whisper 모델 로드
        print(f"호출된 모델 크기: {model_size}")

        # GPU 사용 가능하면 모델을 GPU로
        if torch.cuda.is_available():
            print("✅ CUDA 사용 가능 — GPU로 모델 로드 중")
            model = model.to("cuda")
        else:
            print("⚠️ CUDA 사용 불가 — CPU로 실행됩니다")
        
        return model

    def analize_audio(self, audio_dir):
        """
        주어진 음성 파일을 Whisper로 분석하여 언어를 감지하고, 문장별 시작/끝 시간과 텍스트를 출력하는 함수

        실행 전 세팅은 아래 링크 참조
        - https://velog.io/@strurao/Python-OpenAI-Whisper-%EC%9D%8C%EC%84%B1%EC%9D%B8%EC%8B%9D#-%EC%84%A4%EC%B9%98-%EA%B3%BC%EC%A0%95

        위 링크 세팅 중 필수 여부 정리
        - torch         | ✅ 필수           | Whisper는 PyTorch 기반, 반드시 설치
        - torchaudio    | ❌ 선택           | Whisper 기본 작동에는 필요 없지만, 오디오 전처리 등을 위해 유용
        - torchvision   | ❌ 불필요         | 이미지 처리를 위한 것으로, Whisper에서는 사용되지 않습니다.
        - ffmpeg        | ✅ 사실상 필수    | Whisper는 ffmpeg를 백엔드로 사용하여 다양한 오디오 포맷을 처리하므로 시스템에 설치되어 있어야 함

        파라미터
        - client: OpenAI API 클라이언트
        - audio_dir (str): 분석 할 음성 파일 경로

        호출 예시: analize_audio(client, './audio/voice-sample.mp3')
        """

        # 입력한 파일 경로 검증
        if not audio_dir:
            print('음성 파일 경로 지정이 잘못되었습니다.')
            return
        if not os.path.exists(audio_dir):
            print('존재하지 않는 음성파일입니다.\n파일 위치를 다시 확인하세요.')
            return

        # 평균 소리 크기 계산
        data, rate = sf.read(audio_dir)
        meter = pyln.Meter(rate) 
        loudness = meter.integrated_loudness(data)
        print(f"Integrated Loudness: {loudness:.2f} LUFS")

        # transcribe()는 오디오를 30초 단위로 분할하여 자동으로 텍스트로 변환
        result = self.whisper_model.transcribe(
            audio_dir,
            fp16=torch.cuda.is_available(),
            temperature=0.2, 
            initial_prompt="이 오디오는 면접자의 답변이며 이유, 동기, 배경, 성격, 경험 등의 단어가 포함될 수 있습니다.",
            beam_size = 5 # beam search 사용 (더 많은 후보 탐색 → 정확도 향상)
        ) 
        print(f"모델 transcribe 완료. 감지된 언어: {result['language']}") # 감지된 언어 출력

        # 문장별 시간 출력
        sentences = []
        for segment in result["segments"]:
            start = segment["start"]
            end = segment["end"]
            text = segment["text"].strip()

            # 말 빠르기 계산(초 당 몇 개의 단어를 말 했는지)
            duration = end - start
            word_cnt = len(text.split()) # Whisper로 읽어온 원본 텍스트 기준
            wps = word_cnt / duration if duration > 0 else 0 # words per second

            # 1. 부정확한 발음이나 문맥 상 자연스럽지 않은 표현을 GPT를 통해 후처리 교정
            corrected = self.openai_client.create_response(
                system_content = (
                    "당신은 면접자의 음성 인식 결과를 맞춤법과 흐름 위주로 교정하는 교정 도우미입니다. \
                    사용자의 어투 및 어미를 보존하고, 문법 오류와 앞 뒤 단어와 이어지지 않는 어색한 표현만 자연스럽게 수정하세요. 예: '교본 근무' → '교번근무' 혹은 '교대근무' \
                    오타나 잘못 인식된 단어는 문맥상 자연스럽게 복원하세요. 예: '이후' → '이유'. \
                    답변은 문장 하나로 출력하되, 면접 말투(자연스럽고 공손한 구어체)를 유지하며 문장 구조를 바꾸지 말고 \
                    표현만 위에 제시한대로 다듬으세요."
                ),
                user_content = text
            )

            # 교정 후 코사인 유사도 저장
            original_embedding = OpenAIEmbedding(text)
            corrected_embedding = OpenAIEmbedding(corrected)

            similarity = cosine_similarity([original_embedding], [corrected_embedding])[0][0]

            # 2. 감정 분석
            audio_features = extract_audio_features(audio_dir, start, end) # 음향적 특징 추출

            emotion_prompt = f"""
            문장: "{text}"
            평균 pitch: {audio_features["pitch_mean"]:.1f}Hz, pitch 변화량: {audio_features["pitch_std"]:.2f}
            평균 에너지: {audio_features["energy_mean"]:.5f}, 에너지 변화량: {audio_features["energy_std"]:.5f}
            말 빠르기(WPS): {wps:.2f}
            """

            emotion = self.openai_client.create_response(
                system_content = (
                    "당신은 문장의 감정을 분석하는 전문가입니다. "
                    "텍스트와 음향적 특성을 고려하여 이 문장의 감정을 추론하세요: "
                    "감정 하나의 단어만 출력하세요."
                ),
                user_content = emotion_prompt
            )

            print(f"[{start:.1f}s --> {end:.1f}s] [{emotion}] {corrected}")

            # 분석 된 문장 파일 저장을 위해 append
            sentences.append({
                "original_sentence": text,
                "corrected_sentence": corrected,
                "cosine_similarity": similarity,
                "emotion": emotion,
                "start": start,
                "end": end,
                "wps": wps
            })

        # JSON 데이터 구성
        output_data = {"interview": sentences, "LUFS": loudness}
        base_filename = os.path.splitext(os.path.basename(audio_dir))[0]

        dump_json(filename = base_filename, json_data = output_data)

class AudioEvaluator:
    def __init__(self, filename):
        self.filename = filename
        self.data = read_json(filename = filename)
    
    def evaluate(self):
        # 문장별 평가
        similarities = []
        for idx, sentence in enumerate(self.data.get("interview", []), 1):
            similarity = sentence.get("cosine_similarity")
            emotion = sentence.get("emotion")
            wps = sentence.get("wps")
            
            similarities.append(similarity)
            if similarity < 0.8:
                print(f"❌ 문장 {idx}: 의미적 차이 큼 (유사도 {similarity:.4f}) — 교정 필요")
            elif similarity < 0.9:
                print(f"⚠️ 문장 {idx}: 약간의 차이 있음 (유사도 {similarity:.4f}) — 자연스러움 개선")
            else:
                print(f"✅ 문장 {idx}: 거의 동일 (유사도 {similarity:.4f}) — 문법 교정만 필요")

            print(f"문장 {idx}의 감정 : {emotion}")

            if wps is None:
                print(f"문장 {idx}: WPS 데이터가 없습니다.")
            elif 1.73 <= wps <= 2.59:
                print(f"✅ 문장 {idx}의 WPS [{wps}] : 정상")
            else:
                print(f"⚠️ 문장 {idx}의 WPS [{wps}] : 빠르거나 느립니다.")
    
        # 전체 평가
        lufs = self.data.get("LUFS")
        if lufs is None:
            print("LUFS 데이터가 없습니다.")
        elif -24 <= lufs <= -22:
            print(f"✅ 목소리 평균 크기 [{lufs} LUFS] : 정상")
        else:
            print(f"⚠️ 목소리 평균 크기 [{lufs} LUFS] : 너무 크거나 작습니다. ")
        
        if similarities:
            avg_sim = sum(similarities) / len(similarities)
            print(f"\n📊 전체 평균 코사인 유사도: {avg_sim:.4f}")