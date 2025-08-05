# posture
from collections import deque
from ultralytics import YOLO

import cv2
import math
import mediapipe as mp
import numpy as np
import threading
import time

class VideoAnalyzer:
    def __init__(self):
        # MediaPipe 초기화
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose

        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.pose = self.mp_pose.Pose()

        self.yolo_model = YOLO('bestbest.pt') # YOLO 모델 로드

        # 이력 저장용
        self.eye_history = deque(maxlen=30)
        self.shoulder_center_history = deque(maxlen=30)

        # 반환할 결과 값 초기화
        self.center_gaze_count = 0
        self.total_frame_count = 0
        self.gaze_away_count = 0
        self.last_gaze = None

        self.posture_change_count = 0
        self.last_jitter_eval = None

        self.lock = threading.Lock()  # 🔒 스레드 간 충돌 방지
        self.latest_frame = None

        self.running = False

    # 두 점 사이의 각도를 계산하는 함수
    # p1, p2: (x, y) 좌표 튜플
    # 반환값: -180 ~ 180 사이의 각도
    def get_angle(self, p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        angle = math.degrees(math.atan2(dy, dx))

        if angle > 90: angle -= 180
        elif angle < -90: angle += 180

        return angle

    # 두 점 사이의 유클리드 거리를 계산하는 함수
    # p1, p2: (x, y) 좌표 튜플
    # 반환값: 두 점 사이의 거리
    def get_distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    # 분석 루프를 시작하는 함수
    # 이 함수는 별도의 스레드에서 실행되어야 함
    def start(self):
        print("[VideoAnalyzer] Starting analysis loop...")
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.start()

    def stop(self):
        print("[VideoAnalyzer] Stopping analysis loop...")
        self.running = False

    # Dummy 분석 루프
    # 현재는 단순히 루프를 돌며 대기
    # 이 부분은 React에서 이미지 POST 방식으로 처리 중
    def _run_loop(self):
        print("[VideoAnalyzer] Dummy _run_loop started.")
        while self.running:
            # 실제로 이 루프에서 할 일 없을 수도 있음 (예: React에서 이미지 POST 방식이라면)
            time.sleep(0.1)
        print("[VideoAnalyzer] Dummy _run_loop ended.")

    # 프레임 업데이트 함수
    # 이 함수는 외부에서 호출되어야 하며, 프레임을 업데이트하고 분석을 수행함
    # frame: OpenCV BGR 이미지 1장
    def update_frame(self, frame):
        with self.lock:
            self.latest_frame = frame

    # 최신 프레임을 분석하는 함수
    # 이 함수는 외부에서 호출되어야 하며, 최신 프레임을 분석하고 결과를 반환함
    # 반환값: 분석 결과 딕셔너리
    def analyze_latest_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return {"error": "No frame received yet"}
            frame = self.latest_frame.copy()

        return self.analyze_frame(frame)

    # 프레임을 분석하는 함수
    # frame: OpenCV BGR 이미지 1장
    # 반환값: 분석 결과 딕셔너리
    def analyze_frame(self, frame):
        # frame: OpenCV BGR 이미지 1장
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape

        # MediaPipe 분석
        face_result = self.face_mesh.process(rgb)
        pose_result = self.pose.process(rgb)

        self.total_frame_count += 1 # 총 프레임 수 증가

        response = {}

        # ✅ YOLO 감정 분석 추가
        try:
            results = self.yolo_model.predict(source=frame, conf=0.3, stream=False, verbose=False)[0]  # 첫 번째 결과
            emotions = []

            # YOLO 결과에서 감정 추출
            for box, cls, conf in zip(results.boxes.xyxy, results.boxes.cls, results.boxes.conf):
                emotion = self.yolo_model.names[int(cls)]
                emotions.append({
                    "emotion": emotion,
                    "confidence": float(conf),
                    "box": [float(coord) for coord in box.tolist()]
                })

            response["emotions"] = emotions
        except Exception as e:
            response["emotion_error"] = str(e)

        # 얼굴 메시 결과가 있으면
        if face_result.multi_face_landmarks:
            face_landmarks = face_result.multi_face_landmarks[0]

            # 얼굴 메시 랜드마크를 리스트로 변환
            landmark_list = []
            for lm in face_landmarks.landmark:
                landmark_list.append({
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "visibility": getattr(lm, "visibility", 1.0)  # pose에서는 visibility가 있음
                })

            response["face_landmarks"] = landmark_list

            # 보고있는 방향 비율 계산
            left_outer = face_landmarks.landmark[33].x * w
            left_inner = face_landmarks.landmark[133].x * w
            left_iris_x = np.mean([face_landmarks.landmark[i].x * w for i in range(474, 478)])
            left_ratio = (left_iris_x - left_outer) / (left_inner - left_outer + 1e-6)

            right_outer = face_landmarks.landmark[362].x * w
            right_inner = face_landmarks.landmark[263].x * w
            right_iris_x = np.mean([face_landmarks.landmark[i].x * w for i in range(469, 473)])
            right_ratio = (right_outer - right_iris_x) / (right_outer - right_inner + 1e-6)

            avg_ratio = (left_ratio + right_ratio) / 2

            if avg_ratio < 0.35:
                current_gaze = "Right"
            elif avg_ratio > 0.65:
                current_gaze = "Left"
            else:
                current_gaze = "Center"
                self.center_gaze_count += 1

            if self.last_gaze and current_gaze != self.last_gaze and current_gaze != "Center":
                self.gaze_away_count += 1

            self.last_gaze = current_gaze

            response["gaze"] = current_gaze

        # 자세 결과가 있으면
        if pose_result.pose_landmarks:
            landmarks = pose_result.pose_landmarks.landmark

            # 자세 랜드마크를 리스트로 변환
            pose_landmark_list = []
            for lm in landmarks:
                pose_landmark_list.append({
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "visibility": lm.visibility
                })

            response["pose_landmarks"] = pose_landmark_list

            l_shoulder = [int(landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x * w),
                          int(landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].y * h)]
            r_shoulder = [int(landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x * w),
                          int(landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].y * h)]

            shoulder_center = [(l_shoulder[0] + r_shoulder[0]) // 2,
                               (l_shoulder[1] + r_shoulder[1]) // 2]

            self.shoulder_center_history.append(shoulder_center)

            shoulder_angle = self.get_angle(l_shoulder, r_shoulder) # 어깨 각도 계산

            # 어깨 각도 평가
            if abs(shoulder_angle) <= 1:
                shoulder_eval = "Good"
            elif abs(shoulder_angle) <= 3:
                shoulder_eval = "Slightly Tilted"
            else:
                shoulder_eval = "Tilted"

            # 어깨 중심 위치 이력에서 진동 평가
            jitter = 0
            if len(self.shoulder_center_history) >= 2:
                jitter = self.get_distance(self.shoulder_center_history[-1], self.shoulder_center_history[-2])

            jitter_eval = "Stable" if jitter < 2 else "Moving"

            if self.last_jitter_eval == "Stable" and jitter_eval == "Moving":
                self.posture_change_count += 1

            self.last_jitter_eval = jitter_eval

            response["shoulder_angle"] = shoulder_angle
            response["shoulder_eval"] = shoulder_eval
            response["jitter_eval"] = jitter_eval

        # 프레임 분석 결과를 종합하여 반환
        if self.total_frame_count > 0:
            ratio = self.center_gaze_count / self.total_frame_count * 100
            posture_change_rate = self.posture_change_count / self.total_frame_count * 100
            response["gaze_center_ratio"] = ratio
            response["gaze_shift_count"] = self.gaze_away_count
            response["posture_change_count"] = self.posture_change_count
            response["posture_change_rate"] = posture_change_rate

        return response