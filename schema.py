from pydantic import BaseModel
from typing import List, Any, Optional

class AnswerData(BaseModel):
    chatAnswers: List[str]

class EvalData(BaseModel):
    question: str
    answer: str

class ImageData(BaseModel):
    image: str

class UrlRequest(BaseModel):
    url: str

class InterviewItem(BaseModel):
    original_sentence: str
    corrected_sentence: str
    cosine_similarity: float
    emotion: str
    start: float
    end: float
    wps: float
    lufs: float

class AnalysisResult(BaseModel):
    emotions: List[Any]
    face_landmarks: List[Any]
    gaze: str
    pose_landmarks: List[Any]
    shoulder_angle: float
    shoulder_eval: str
    jitter_eval: str
    gaze_center_ratio: float
    gaze_shift_count: int
    posture_change_count: int

class DataPayload(BaseModel):
    interview: List[InterviewItem]
    analysisResult: AnalysisResult
    modelAnswers: List[str]
    questions: List[str]
    chatAnswers: List[str]