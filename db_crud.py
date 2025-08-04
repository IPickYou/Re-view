from db import SessionLocal
from models import (
    Session as SessionModel, InterviewEntry, AnalysisResult, EmotionBox,
    FaceLandmark, PoseLandmark, ModelAnswer, Question, ChatAnswer
)

def init_db():
    import models # models.py 안의 declarative 클래스들이 등록되도록
    from db import engine, Base
    Base.metadata.create_all(bind=engine)

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
            posture_change_rate=ar_raw.get("posture_change_rate")
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

def get_all_session_ids():
    db = SessionLocal()
    try:
        return [sess.session_id for sess in db.query(SessionModel).all()]
    finally:
        db.close()

def load_full_session(session_id: str):
    db = SessionLocal()
    try:
        sess = db.query(SessionModel).filter_by(session_id=session_id).first()
        if not sess:
            return None

        # interview
        interview_entries = db.query(InterviewEntry).filter_by(session_id=sess.session_id).all()
        interview = [
            {
                "original_sentence": ie.original_sentence,
                "corrected_sentence": ie.corrected_sentence,
                "cosine_similarity": ie.cosine_similarity,
                "emotion": ie.emotion,
                "start": ie.start,
                "end": ie.end,
                "wps": ie.wps,
                "lufs": ie.lufs,
            }
            for ie in interview_entries
        ]

        # analysis_result
        ar = db.query(AnalysisResult).filter_by(session_id=sess.session_id).first()
        if ar:
            emotions = db.query(EmotionBox).filter_by(analysis_result_id=ar.id).all()
            face_landmarks = db.query(FaceLandmark).filter_by(analysis_result_id=ar.id).all()
            pose_landmarks = db.query(PoseLandmark).filter_by(analysis_result_id=ar.id).all()
            analysis_result = {
                "gaze": ar.gaze,
                "shoulder_angle": ar.shoulder_angle,
                "shoulder_eval": ar.shoulder_eval,
                "jitter_eval": ar.jitter_eval,
                "gaze_center_ratio": ar.gaze_center_ratio,
                "gaze_shift_count": ar.gaze_shift_count,
                "posture_change_count": ar.posture_change_count,
                "posture_change_rate": ar.posture_change_rate,
                "emotions": [
                    {
                        "emotion": e.emotion,
                        "confidence": e.confidence,
                        "box": e.box,
                    }
                    for e in emotions
                ],
                "face_landmarks": [
                    {
                        "x": fl.x,
                        "y": fl.y,
                        "z": fl.z,
                        "visibility": fl.visibility,
                    }
                    for fl in face_landmarks
                ],
                "pose_landmarks": [
                    {
                        "x": pl.x,
                        "y": pl.y,
                        "z": pl.z,
                        "visibility": pl.visibility,
                    }
                    for pl in pose_landmarks
                ],
            }
        else:
            analysis_result = {}

        # model_answers, questions, chat_answers
        model_answers = [
            ma.content for ma in db.query(ModelAnswer).filter_by(session_id=sess.session_id).order_by(ModelAnswer.idx).all()
        ]
        questions = [
            q.content for q in db.query(Question).filter_by(session_id=sess.session_id).order_by(Question.idx).all()
        ]
        chat_answers = [
            ca.content for ca in db.query(ChatAnswer).filter_by(session_id=sess.session_id).order_by(ChatAnswer.idx).all()
        ]

        return {
            "session_id": sess.session_id,
            "interview": interview,
            "analysis_result": analysis_result,
            "model_answers": model_answers,
            "questions": questions,
            "chat_answers": chat_answers,
        }
    finally:
        db.close()