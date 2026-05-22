from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

class InterviewState(TypedDict):
    # Candidate details
    candidate_id: str
    name: str
    role: str
    experience: str
    qualification: str
    skillset: str
    
    # Session Details
    session_id: str
    interview_id: str
    
    # Current Question Context
    current_question: str
    current_difficulty: str # "easy", "medium", "hard"
    current_answer: str
    
    # Loop control
    question_count: int
    max_questions: int
    is_completed: bool
    
    # History of conversations & scores
    history: List[Dict[str, Any]] # Stores list of {"question": str, "answer": str, "score": float, "difficulty": str, "evaluation": dict}
    
    # Final Report Details
    overall_score: float
    technical_score: float
    communication_score: float
    recommendation: str # "Selected", "Rejected", "Needs Further Evaluation"
    strengths: List[str]
    improvements: List[str]
    question_wise_evaluation: List[Dict[str, Any]]
    ai_feedback: str
