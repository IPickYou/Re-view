from sqlalchemy import (
    Column, String, Integer, Float, ForeignKey, JSON, Text
)
from sqlalchemy.orm import relationship

from db import Base

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True)
    interview_entries = relationship("InterviewEntry", back_populates="session", cascade="all, delete-orphan")
    analysis_result = relationship("AnalysisResult", uselist=False, back_populates="session", cascade="all, delete-orphan")
    model_answers = relationship("ModelAnswer", back_populates="session", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan")
    chat_answers = relationship("ChatAnswer", back_populates="session", cascade="all, delete-orphan")

class InterviewEntry(Base):
    __tablename__ = "interview_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    original_sentence = Column(Text)
    corrected_sentence = Column(Text)
    cosine_similarity = Column(Float)
    emotion = Column(String)
    start = Column(Float)
    end = Column(Float)
    wps = Column(Float)
    lufs = Column(Float)
    session = relationship("Session", back_populates="interview_entries")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    gaze = Column(String)
    shoulder_angle = Column(Float)
    shoulder_eval = Column(String)
    jitter_eval = Column(String)
    gaze_center_ratio = Column(Float)
    gaze_shift_count = Column(Integer)
    posture_change_count = Column(Integer)
    session = relationship("Session", back_populates="analysis_result")
    emotions = relationship("EmotionBox", back_populates="analysis_result", cascade="all, delete-orphan")
    face_landmarks = relationship("FaceLandmark", back_populates="analysis_result", cascade="all, delete-orphan")
    pose_landmarks = relationship("PoseLandmark", back_populates="analysis_result", cascade="all, delete-orphan")

class EmotionBox(Base):
    __tablename__ = "emotion_boxes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    emotion = Column(String)
    confidence = Column(Float)
    box = Column(JSON)
    analysis_result = relationship("AnalysisResult", back_populates="emotions")

class FaceLandmark(Base):
    __tablename__ = "face_landmarks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    visibility = Column(Float)
    analysis_result = relationship("AnalysisResult", back_populates="face_landmarks")

class PoseLandmark(Base):
    __tablename__ = "pose_landmarks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    visibility = Column(Float)
    analysis_result = relationship("AnalysisResult", back_populates="pose_landmarks")

class ModelAnswer(Base):
    __tablename__ = "model_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    idx = Column(Integer)
    content = Column(Text)
    session = relationship("Session", back_populates="model_answers")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    idx = Column(Integer)
    content = Column(Text)
    session = relationship("Session", back_populates="questions")

class ChatAnswer(Base):
    __tablename__ = "chat_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    idx = Column(Integer)
    content = Column(Text)
    session = relationship("Session", back_populates="chat_answers")