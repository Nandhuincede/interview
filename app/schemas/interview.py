from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class InterviewSessionCreate(BaseModel):
    candidate_id: str

class InterviewSessionResponse(BaseModel):
    session_id: str
    interview_id: str
    candidate_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AnswerSubmit(BaseModel):
    session_id: str
    audio_base64: Optional[str] = None  # Captured candidate audio as base64 WAV/MP3
    text_fallback: Optional[str] = None # Optional text backup in case of manual input or browser-native STT

class AnswerResponse(BaseModel):
    transcription: str
    score: float # Overall evaluation score for this question (0-10 or 0-100)
    evaluation: dict # Detailed evaluation result (technical, communication, etc.)
    is_completed: bool # True if the interview has finished

class StartInterviewRequest(BaseModel):
    session_id: str

class StartInterviewResponse(BaseModel):
    session_id: str
    interview_id: str
    greeting: str
    first_question: str
    audio_base64: Optional[str] = None # Greeting + first question synthesized speech

class NextQuestionResponse(BaseModel):
    question: str
    difficulty: str # easy, medium, hard
    audio_base64: Optional[str] = None # Audio of the generated question
    is_completed: bool
