import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Candidate(Base):
    __tablename__ = "candidates"
    
    candidate_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=False)
    qualification = Column(String, nullable=False)
    experience = Column(String, nullable=False) # e.g. "3 years" or "3"
    role = Column(String, nullable=False)        # e.g. "React Developer"
    skillset = Column(Text, nullable=False)      # e.g. "React, JavaScript, Redux"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("InterviewSession", back_populates="candidate", cascade="all, delete-orphan")

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    session_id = Column(String, primary_key=True, default=generate_uuid)
    interview_id = Column(String, default=generate_uuid, unique=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False)
    status = Column(String, default="pending") # pending, active, completed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    report = relationship("Report", uselist=False, back_populates="session", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    
    conversation_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("interview_sessions.session_id"), nullable=False)
    interview_id = Column(String, nullable=False)
    speaker_type = Column(String, nullable=False) # "candidate" or "interviewer"
    message_text = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)
    score = Column(Float, nullable=True)          # Score for candidate answers
    evaluation_json = Column(Text, nullable=True) # Full evaluation breakdown as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("InterviewSession", back_populates="conversations")

class Report(Base):
    __tablename__ = "reports"
    
    report_id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("interview_sessions.session_id"), nullable=False)
    interview_id = Column(String, nullable=False)
    overall_score = Column(Float, nullable=False)
    technical_score = Column(Float, nullable=False)
    communication_score = Column(Float, nullable=False)
    recommendation = Column(String, nullable=False) # e.g. "Selected", "Rejected", "Needs Further Evaluation"
    strengths = Column(Text, nullable=False)        # JSON string of strengths
    improvements = Column(Text, nullable=False)      # JSON string of improvements/weaknesses
    question_wise_evaluation = Column(Text, nullable=False) # JSON string of question evaluations
    ai_feedback = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("InterviewSession", back_populates="report")
