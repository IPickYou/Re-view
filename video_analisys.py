# posture
from collections import deque
from ultralytics import YOLO

import cv2
import math
import mediapipe as mp
import numpy as np
import threading
import os

class VideoAnalyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.pose = self.mp_pose.Pose()

        self.yolo_model = YOLO('best.pt')

        self.eye_history = deque(maxlen=30)
        self.shoulder_center_history = deque(maxlen=30)

        self.center_gaze_count = 0
        self.total_frame_count = 0
        self.gaze_away_count = 0
        self.last_gaze = None

        self.posture_change_count = 0
        self.last_jitter_eval = None

        self.lock = threading.Lock()  # 🔒 스레드 간 충돌 방지
        self.latest_frame = None

        self.running = False

    def get_angle(self, p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        angle = math.degrees(math.atan2(dy, dx))

        if angle > 90: angle -= 180
        elif angle < -90: angle += 180

        return angle

    def get_distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def start(self):
        print("[VideoAnalyzer] Starting analysis loop...")
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.start()

    def stop(self):
        print("[VideoAnalyzer] Stopping analysis loop...")
        self.running = False

    def update_frame(self, frame):
        with self.lock:
            self.latest_frame = frame

    def analyze_latest_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return {"error": "No frame received yet"}
            frame = self.latest_frame.copy()

        return self.analyze_frame(frame)

    def analyze_frame(self, frame):
        # frame: OpenCV BGR 이미지 1장
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = frame.shape

        face_result = self.face_mesh.process(rgb)
        pose_result = self.pose.process(rgb)

        self.total_frame_count += 1

        response = {}

        # ✅ YOLO 감정 분석 추가
        try:
            results = self.yolo_model.predict(source=frame, conf=0.3, stream=False, verbose=False)[0]  # 첫 번째 결과
            emotions = []

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

            landmark_list = []
            for lm in face_landmarks.landmark:
                landmark_list.append({
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "visibility": getattr(lm, "visibility", 1.0)  # pose에서는 visibility가 있음
                })

            response["face_landmarks"] = landmark_list

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

            l_shoulder = [int(landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x * w),
                          int(landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].y * h)]
            r_shoulder = [int(landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x * w),
                          int(landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].y * h)]

            shoulder_center = [(l_shoulder[0] + r_shoulder[0]) // 2,
                               (l_shoulder[1] + r_shoulder[1]) // 2]

            self.shoulder_center_history.append(shoulder_center)

            shoulder_angle = self.get_angle(l_shoulder, r_shoulder)

            if abs(shoulder_angle) <= 1:
                shoulder_eval = "Good"
            elif abs(shoulder_angle) <= 3:
                shoulder_eval = "Slightly Tilted"
            else:
                shoulder_eval = "Tilted"

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

        if self.total_frame_count > 0:
            ratio = self.center_gaze_count / self.total_frame_count * 100
            response["gaze_center_ratio"] = ratio
            response["gaze_shift_count"] = self.gaze_away_count
            response["posture_change_count"] = self.posture_change_count

        return response