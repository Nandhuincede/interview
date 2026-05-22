import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import models
from app.schemas.interview import (
    InterviewSessionCreate, 
    InterviewSessionResponse, 
    StartInterviewRequest, 
    StartInterviewResponse,
    AnswerSubmit,
    AnswerResponse,
    NextQuestionResponse
)
from app.schemas.report import ReportResponse
from app.schemas.conversation import ConversationResponse

from app.services import tts, stt
from app.interview_workflow.agents.question_generator import QuestionGeneratorAgent
from app.interview_workflow.agents.reflection import ReflectionAgent
from app.interview_workflow.agents.difficulty_controller import DifficultyControllerAgent
from app.interview_workflow.agents.conversation_manager import ConversationManagerAgent
from app.interview_workflow.agents.report_generator import ReportGeneratorAgent
from app.interview_workflow.state import InterviewState

router = APIRouter(prefix="/interview", tags=["Interview Flow"])

# Instantiate Agents
question_generator = QuestionGeneratorAgent()
reflection_agent = ReflectionAgent()
difficulty_controller = DifficultyControllerAgent()
conversation_manager = ConversationManagerAgent()
report_generator = ReportGeneratorAgent()

# Helper to build current state dictionary from DB
def build_state_from_db(session_id: str, db: Session) -> dict:
    session = db.query(models.InterviewSession).filter(models.InterviewSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    candidate = db.query(models.Candidate).filter(models.Candidate.candidate_id == session.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    # Rebuild history from conversations
    db_conversations = db.query(models.Conversation).filter(
        models.Conversation.session_id == session_id
    ).order_by(models.Conversation.created_at.asc()).all()
    
    history = []
    current_difficulty = "easy"
    
    # Pair questions with answers
    temp_question = None
    temp_difficulty = "easy"
    
    for msg in db_conversations:
        if msg.speaker_type == "interviewer":
            temp_question = msg.message_text
            # Look up difficulty in metadata or start with current
        elif msg.speaker_type == "candidate" and temp_question is not None:
            # We found a candidate reply to a question
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
                "evaluation": eval_dict
            })
            # The next question's difficulty was determined by the difficulty controller
            if msg.score is not None:
                temp_difficulty = difficulty_controller.adjust_difficulty(msg.score, temp_difficulty)
            temp_question = None
            
    # Count how many interviewer questions have been asked
    q_count = sum(1 for m in db_conversations if m.speaker_type == "interviewer")
    
    state = {
        "candidate_id": candidate.candidate_id,
        "name": candidate.name,
        "role": candidate.role,
        "experience": candidate.experience,
        "qualification": candidate.qualification,
        "skillset": candidate.skillset,
        "session_id": session.session_id,
        "interview_id": session.interview_id,
        "current_difficulty": temp_difficulty,
        "question_count": q_count,
        "max_questions": 5,  # Standard limit
        "history": history,
        "is_completed": session.status == "completed"
    }
    return state


# Endpoints


@router.post("/session", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: InterviewSessionCreate, db: Session = Depends(get_db)):
    """
    Creates a new interview session for a candidate.
    """
    candidate = db.query(models.Candidate).filter(models.Candidate.candidate_id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
        
    session = models.InterviewSession(
        candidate_id=payload.candidate_id,
        status="pending"
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.post("/start", response_model=StartInterviewResponse)
def start_interview(payload: StartInterviewRequest, db: Session = Depends(get_db)):
    """
    Sets session status to active, generates a personalized greeting and the
    first technical question, synthesizes speech, and saves to conversations.
    """
    session = db.query(models.InterviewSession).filter(models.InterviewSession.session_id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    candidate = db.query(models.Candidate).filter(models.Candidate.candidate_id == session.candidate_id).first()
    
    # Set status to active
    session.status = "active"
    db.commit()
    
    # 1. Run "load_candidate" and "generate_question" nodes logic
    state = {
        "candidate_id": candidate.candidate_id,
        "name": candidate.name,
        "role": candidate.role,
        "experience": candidate.experience,
        "qualification": candidate.qualification,
        "skillset": candidate.skillset,
        "current_difficulty": "easy",
        "question_count": 0,
        "history": []
    }
    
    q_result = question_generator.generate(state)
    first_q = q_result["current_question"]
    
    greeting = f"Welcome {candidate.name}! Thank you for attending the interview today for the {candidate.role} position. Are you ready to start the interview? Let's begin with your first question: "
    full_message = greeting + first_q
    
    # Convert greeting + first question to base64 audio speech
    audio_base64 = tts.text_to_speech_base64(full_message)
    
    # Save interviewer conversation to DB
    db_conv = models.Conversation(
        session_id=session.session_id,
        interview_id=session.interview_id,
        speaker_type="interviewer",
        message_text=full_message
    )
    db.add(db_conv)
    db.commit()
    
    return StartInterviewResponse(
        session_id=session.session_id,
        interview_id=session.interview_id,
        greeting=greeting,
        first_question=first_q,
        audio_base64=audio_base64
    )

@router.post("/answer", response_model=AnswerResponse)
def submit_answer(payload: AnswerSubmit, db: Session = Depends(get_db)):
    """
    Accepts candidate's answer (via base64 microphone audio or text fallback),
    transcribes it, runs the reflection evaluator, checks completion, and saves to database.
    """
    session = db.query(models.InterviewSession).filter(models.InterviewSession.session_id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Interview session is not active")
        
    # 1. Speech to Text Transcription
    transcription = stt.transcribe_audio_base64(payload.audio_base64, payload.text_fallback)
    
    # Load state from database to identify the question that was answered
    state = build_state_from_db(payload.session_id, db)
    
    # The last asked question is the most recent interviewer conversation
    last_interviewer_msg = db.query(models.Conversation).filter(
        models.Conversation.session_id == payload.session_id,
        models.Conversation.speaker_type == "interviewer"
    ).order_by(models.Conversation.created_at.desc()).first()
    
    if not last_interviewer_msg:
        raise HTTPException(status_code=400, detail="No question has been asked yet in this session")
        
    # Clean the question text (removing welcome greeting if it was the first question)
    raw_question = last_interviewer_msg.message_text
    question_text = raw_question
    if "Let's begin with your first question:" in raw_question:
        question_text = raw_question.split("Let's begin with your first question:")[-1].strip()
        
    # 2. Run Reflection Agent Evaluation
    eval_result = reflection_agent.evaluate(
        question_text, 
        transcription, 
        state["role"], 
        state["skillset"]
    )
    overall_score = eval_result.get("overall_score", 0.0)
    
    # Save Candidate response to conversations table with evaluation metadata
    db_conv = models.Conversation(
        session_id=session.session_id,
        interview_id=session.interview_id,
        speaker_type="candidate",
        message_text=transcription,
        score=overall_score,
        evaluation_json=json.dumps(eval_result)
    )
    db.add(db_conv)
    db.commit()
    
    # Rebuild state after appending this answer to check completion
    updated_state = build_state_from_db(payload.session_id, db)
    
    # 3. Check completion node logic
    # Reached question limit (configured at 5 for quick demo)
    is_completed = len(updated_state["history"]) >= updated_state["max_questions"]
    
    if is_completed:
        # Finalize interview session
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        db.commit()
        
        # 4. Generate final report automatically
        report_data = report_generator.generate_report(updated_state)
        
        # Save report to DB
        db_report = models.Report(
            session_id=session.session_id,
            interview_id=session.interview_id,
            overall_score=report_data.get("overall_score", 0.0),
            technical_score=report_data.get("technical_score", 0.0),
            communication_score=report_data.get("communication_score", 0.0),
            recommendation=report_data.get("recommendation", "Needs Further Evaluation"),
            strengths=json.dumps(report_data.get("strengths", [])),
            improvements=json.dumps(report_data.get("improvements", [])),
            question_wise_evaluation=json.dumps(report_data.get("question_wise_evaluation", [])),
            ai_feedback=report_data.get("ai_feedback", "")
        )
        db.add(db_report)
        db.commit()
        
    return AnswerResponse(
        transcription=transcription,
        score=overall_score,
        evaluation=eval_result,
        is_completed=is_completed
    )

@router.post("/next-question", response_model=NextQuestionResponse)
def get_next_question(payload: StartInterviewRequest, db: Session = Depends(get_db)):
    """
    Generates the next dynamic question based on history and difficulty,
    synthesizes it to speech, saves to DB, and returns it.
    """
    session = db.query(models.InterviewSession).filter(models.InterviewSession.session_id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    if session.status != "active":
        return NextQuestionResponse(
            question="The interview is completed.",
            difficulty="none",
            is_completed=True
        )
        
    # Rebuild state from DB
    state = build_state_from_db(payload.session_id, db)
    
    # Verify completion again
    if len(state["history"]) >= state["max_questions"]:
        return NextQuestionResponse(
            question="The interview is completed. Thank you!",
            difficulty="none",
            is_completed=True
        )
        
    # Generate the question using state (which holds the current adjusted difficulty)
    q_result = question_generator.generate(state)
    next_q = q_result["current_question"]
    difficulty = q_result["current_difficulty"]
    
    # Synthesize text to speech base64 audio
    audio_base64 = tts.text_to_speech_base64(next_q)
    
    # Store interviewer question in DB
    db_conv = models.Conversation(
        session_id=session.session_id,
        interview_id=session.interview_id,
        speaker_type="interviewer",
        message_text=next_q
    )
    db.add(db_conv)
    db.commit()
    
    return NextQuestionResponse(
        question=next_q,
        difficulty=difficulty,
        audio_base64=audio_base64,
        is_completed=False
    )

@router.post("/end", response_model=InterviewSessionResponse)
def end_interview_manually(payload: StartInterviewRequest, db: Session = Depends(get_db)):
    """
    Ends the interview session manually and generates the final report.
    """
    session = db.query(models.InterviewSession).filter(models.InterviewSession.session_id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    if session.status != "completed":
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        db.commit()
        
        # Build state and generate final report
        state = build_state_from_db(payload.session_id, db)
        
        # Check if report already exists
        existing_report = db.query(models.Report).filter(models.Report.session_id == payload.session_id).first()
        if not existing_report:
            report_data = report_generator.generate_report(state)
            
            db_report = models.Report(
                session_id=session.session_id,
                interview_id=session.interview_id,
                overall_score=report_data.get("overall_score", 0.0),
                technical_score=report_data.get("technical_score", 0.0),
                communication_score=report_data.get("communication_score", 0.0),
                recommendation=report_data.get("recommendation", "Needs Further Evaluation"),
                strengths=json.dumps(report_data.get("strengths", [])),
                improvements=json.dumps(report_data.get("improvements", [])),
                question_wise_evaluation=json.dumps(report_data.get("question_wise_evaluation", [])),
                ai_feedback=report_data.get("ai_feedback", "")
            )
            db.add(db_report)
            db.commit()
            
    return session

@router.post("/report/generate", response_model=ReportResponse)
def trigger_report_generation(payload: StartInterviewRequest, db: Session = Depends(get_db)):
    """
    Compiles/re-generates and saves the final interview report.
    """
    session = db.query(models.InterviewSession).filter(models.InterviewSession.session_id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    state = build_state_from_db(payload.session_id, db)
    report_data = report_generator.generate_report(state)
    
    # Check if report already exists and update it, else create new
    db_report = db.query(models.Report).filter(models.Report.session_id == payload.session_id).first()
    if db_report:
        db_report.overall_score = report_data.get("overall_score", 0.0)
        db_report.technical_score = report_data.get("technical_score", 0.0)
        db_report.communication_score = report_data.get("communication_score", 0.0)
        db_report.recommendation = report_data.get("recommendation", "Needs Further Evaluation")
        db_report.strengths = json.dumps(report_data.get("strengths", []))
        db_report.improvements = json.dumps(report_data.get("improvements", []))
        db_report.question_wise_evaluation = json.dumps(report_data.get("question_wise_evaluation", []))
        db_report.ai_feedback = report_data.get("ai_feedback", "")
    else:
        db_report = models.Report(
            session_id=session.session_id,
            interview_id=session.interview_id,
            overall_score=report_data.get("overall_score", 0.0),
            technical_score=report_data.get("technical_score", 0.0),
            communication_score=report_data.get("communication_score", 0.0),
            recommendation=report_data.get("recommendation", "Needs Further Evaluation"),
            strengths=json.dumps(report_data.get("strengths", [])),
            improvements=json.dumps(report_data.get("improvements", [])),
            question_wise_evaluation=json.dumps(report_data.get("question_wise_evaluation", [])),
            ai_feedback=report_data.get("ai_feedback", "")
        )
        db.add(db_report)
        
    db.commit()
    db.refresh(db_report)
    
    # Parse lists for response model
    return ReportResponse(
        report_id=db_report.report_id,
        session_id=db_report.session_id,
        interview_id=db_report.interview_id,
        overall_score=db_report.overall_score,
        technical_score=db_report.technical_score,
        communication_score=db_report.communication_score,
        recommendation=db_report.recommendation,
        strengths=json.loads(db_report.strengths),
        improvements=json.loads(db_report.improvements),
        question_wise_evaluation=json.loads(db_report.question_wise_evaluation),
        ai_feedback=db_report.ai_feedback,
        created_at=db_report.created_at
    )

@router.get("/report/{session_id}", response_model=ReportResponse)
def get_interview_report(session_id: str, db: Session = Depends(get_db)):
    """
    Fetches the final interview evaluation report for a session from the DB.
    """
    db_report = db.query(models.Report).filter(models.Report.session_id == session_id).first()
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation report not found for this session"
        )
        
    return ReportResponse(
        report_id=db_report.report_id,
        session_id=db_report.session_id,
        interview_id=db_report.interview_id,
        overall_score=db_report.overall_score,
        technical_score=db_report.technical_score,
        communication_score=db_report.communication_score,
        recommendation=db_report.recommendation,
        strengths=json.loads(db_report.strengths),
        improvements=json.loads(db_report.improvements),
        question_wise_evaluation=json.loads(db_report.question_wise_evaluation),
        ai_feedback=db_report.ai_feedback,
        created_at=db_report.created_at
    )

@router.get("/conversation/{session_id}", response_model=List[ConversationResponse])
def get_conversation_history(session_id: str, db: Session = Depends(get_db)):
    """
    Retrieves full chronological dialogue history for the interview session.
    """
    db_conversations = db.query(models.Conversation).filter(
        models.Conversation.session_id == session_id
    ).order_by(models.Conversation.created_at.asc()).all()
    
    return db_conversations

@router.post("/reflection/evaluate")
def evaluate_custom_answer(question: str, answer: str, role: str, skillset: str):
    """
    Direct endpoint to evaluate any raw question-answer pair.
    """
    return reflection_agent.evaluate(question, answer, role, skillset)
