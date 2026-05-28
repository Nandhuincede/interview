import json
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db import models
from app.interview_workflow.agents.difficulty_controller import DifficultyControllerAgent

_difficulty_controller = DifficultyControllerAgent()

class InterviewService:
    def build_state_from_db(self, session_id: str, db: Session) -> dict:
        session = db.query(models.InterviewSession).filter(
            models.InterviewSession.session_id == session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")

        candidate = db.query(models.Candidate).filter(
            models.Candidate.candidate_id == session.candidate_id
        ).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate profile not found")

        db_conversations = db.query(models.Conversation).filter(
            models.Conversation.session_id == session_id
        ).order_by(models.Conversation.created_at.asc()).all()

        history = self._reconstruct_history(db_conversations)
        q_count = sum(1 for m in db_conversations if m.speaker_type == "interviewer")
        temp_difficulty = history[-1]["difficulty"] if history else "easy"

        return {
            "candidate_id": candidate.candidate_id,
            "name": candidate.name,
            "role": candidate.role,
            "experience": candidate.experience,
            "qualification": candidate.qualification,
            "skillset": candidate.skillset,
            "session_id": session.session_id,
            "interview_id": session.interview_id,
            "current_difficulty": temp_difficulty,
            "current_bloom_level": history[-1]["bloom_level"] if history else "remember",
            "question_count": q_count,
            "max_questions": 5,
            "history": history,
            "is_completed": session.status == "completed",
        }

    def _reconstruct_history(self, db_conversations) -> list:
        history = []
        temp_question = None
        temp_difficulty = "easy"

        for msg in db_conversations:
            if msg.speaker_type == "interviewer":
                temp_question = msg.message_text
            elif msg.speaker_type == "candidate" and temp_question is not None:
                eval_dict = {}
                if msg.evaluation_json:
                    try:
                        eval_dict = json.loads(msg.evaluation_json)
                    except Exception:
                        pass
                history.append({
                    "question": temp_question,
                    "answer": msg.message_text,
                    "score": msg.score or 0.0,
                    "difficulty": temp_difficulty,
                    "bloom_level": msg.bloom_level or "remember",
                    "evaluation": eval_dict,
                })
                if msg.score is not None:
                    temp_difficulty = _difficulty_controller.adjust_difficulty(msg.score, temp_difficulty)
                temp_question = None

        return history

interview_service = InterviewService()