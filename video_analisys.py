# posture
from collections import deque

import cv2
import math
import mediapipe as mp
import numpy as np

class VideoAnalyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils

        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks = True)
        self.pose = self.mp_pose.Pose()

        self.cap = cv2.VideoCapture(0)

        self.eye_history = deque(maxlen = 30)
        self.shoulder_center_history = deque(maxlen = 30)

        self.center_gaze_count = 0
        self.total_frame_count = 0
        self.gaze_away_count = 0
        self.last_gaze = None

        self.posture_change_count = 0
        self.last_jitter_eval = None

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
        while self.cap.isOpened():

            ret, frame = self.cap.read()

            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape

            face_result = self.face_mesh.process(rgb)
            pose_result = self.pose.process(rgb)

            self.total_frame_count += 1

            if face_result.multi_face_landmarks:

                for face_landmarks in face_result.multi_face_landmarks:

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
                        gaze_text = "Gaze : Right"
                        gaze_color = (255, 255, 0)
                        current_gaze = "Right"

                    elif avg_ratio > 0.65:
                        gaze_text = "Gaze : Left"
                        gaze_color = (0, 0, 255)
                        current_gaze = "Left"

                    else:
                        gaze_text = "Gaze : Center"
                        gaze_color = (0, 200, 0)
                        current_gaze = "Center"

                        self.center_gaze_count += 1

                    if self.last_gaze and current_gaze != self.last_gaze and current_gaze != "Center":
                        self.gaze_away_count += 1

                    self.last_gaze = current_gaze

                    cv2.putText(frame, gaze_text, (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, gaze_color, 2)

            if pose_result.pose_landmarks:

                landmarks = pose_result.pose_landmarks.landmark

                self.mp_drawing.draw_landmarks(frame, pose_result.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

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

                cv2.putText(frame, f"Shoulder : {shoulder_eval}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,200), 2)
                cv2.putText(frame, f"Stability : {jitter_eval}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128,128,255), 2)

            if self.total_frame_count > 0:

                ratio = self.center_gaze_count / self.total_frame_count * 100

                cv2.putText(frame, f"Gaze Center Ratio : {ratio:.1f}%", (20, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                cv2.putText(frame, f"Gaze Shift Count : {self.gaze_away_count}", (20, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                cv2.putText(frame, f"Posture Change Count : {self.posture_change_count}", (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,0), 2)

            cv2.imshow('Posture & Gaze Tracker', frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

        self.cap.release()
        cv2.destroyAllWindows()