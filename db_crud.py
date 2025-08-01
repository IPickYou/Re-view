from db import SessionLocal
from models import (
    Session as SessionModel, InterviewEntry, AnalysisResult, EmotionBox,
    FaceLandmark, PoseLandmark, ModelAnswer, Question, ChatAnswer
)

def init_db():
    from db import engine, Base
    Base.metadata.create_all(engine)

def save_full_session(data: dict):
    db = SessionLocal()
    try:
        sess = SessionModel(session_id=data["session_id"])
        db.add(sess)

        # interview entries
        for entry in data.get("interview", []):
            ie = InterviewEntry(
                session=sess,
                original_sentence=entry.get("original_sentence"),
                corrected_sentence=entry.get("corrected_sentence"),
                cosine_similarity=entry.get("cosine_similarity"),
                emotion=entry.get("emotion"),
                start=entry.get("start"),
                end=entry.get("end"),
                wps=entry.get("wps"),
                lufs=entry.get("lufs"),
            )
            db.add(ie)

        # analysis result
        ar_raw = data.get("analysis_result", {})
        ar = AnalysisResult(
            session=sess,
            gaze=ar_raw.get("gaze"),
            shoulder_angle=ar_raw.get("shoulder_angle"),
            shoulder_eval=ar_raw.get("shoulder_eval"),
            jitter_eval=ar_raw.get("jitter_eval"),
            gaze_center_ratio=ar_raw.get("gaze_center_ratio"),
            gaze_shift_count=ar_raw.get("gaze_shift_count"),
            posture_change_count=ar_raw.get("posture_change_count"),
        )
        db.add(ar)

        for emo in ar_raw.get("emotions", []):
            eb = EmotionBox(
                analysis_result=ar,
                emotion=emo.get("emotion"),
                confidence=emo.get("confidence"),
                box=emo.get("box"),
            )
            db.add(eb)

        for fl in ar_raw.get("face_landmarks", []):
            fm = FaceLandmark(
                analysis_result=ar,
                x=fl.get("x"),
                y=fl.get("y"),
                z=fl.get("z"),
                visibility=fl.get("visibility"),
            )
            db.add(fm)

        for pl in ar_raw.get("pose_landmarks", []):
            pm = PoseLandmark(
                analysis_result=ar,
                x=pl.get("x"),
                y=pl.get("y"),
                z=pl.get("z"),
                visibility=pl.get("visibility"),
            )
            db.add(pm)

        for idx, ma in enumerate(data.get("model_answers", [])):
            db.add(ModelAnswer(session=sess, idx=idx, content=ma))
        for idx, q in enumerate(data.get("questions", [])):
            db.add(Question(session=sess, idx=idx, content=q))
        for idx, ca in enumerate(data.get("chat_answers", [])):
            db.add(ChatAnswer(session=sess, idx=idx, content=ca))

        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

def get_session(session_id: str):
    db = SessionLocal()
    try:
        return db.query(SessionModel).filter_by(session_id=session_id).first()
    finally:
        db.close()