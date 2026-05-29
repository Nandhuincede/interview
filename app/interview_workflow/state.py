# app/interview_workflow/state.py
from typing import List, Dict, Any, Optional, Literal
from typing_extensions import TypedDict


class InterviewState(TypedDict):
    # ── Identity ──────────────────────────────────────────────────────────
    candidate_id: str
    session_id: str
    interview_id: str

    # ── Phase-based entry routing (v2 pattern) ────────────────────────────
    # "start"  → load_candidate → generate_question → END
    # "answer" → evaluate_answer → check_completion → loop or report
    # "report" → generate_report → END
    phase: Literal["start", "answer", "report"]

    # ── Candidate profile (loaded from DB in load_candidate) ──────────────
    candidate: dict  # {name, role, experience, qualification, skillset}

    # ── Bloom's Taxonomy tracking ─────────────────────────────────────────
    current_bloom_level: str   # active level for this turn
    bloom_scores: Dict[str, float]

    # ── Current turn ──────────────────────────────────────────────────────
    current_question: str
    current_question_id: str
    current_answer: str
    current_difficulty: str    # "easy" | "medium" | "hard"

    # ── Progress ──────────────────────────────────────────────────────────
    question_count: int
    max_questions: int
    is_completed: bool
    scores: List[float]

    # ── Conversation memory (in-memory context for LLM) ───────────────────
    history: List[Dict[str, Any]]
    # Each entry: {question, answer, score, difficulty, bloom_level, evaluation}

    # ── Final report ──────────────────────────────────────────────────────
    overall_score: float
    technical_score: float
    communication_score: float
    recommendation: str        # "Selected" | "Rejected" | "Needs Further Evaluation"
    strengths: List[str]
    improvements: List[str]
    question_wise_evaluation: List[Dict[str, Any]]
    ai_feedback: str

    # ── DB session injected at graph invocation ───────────────────────────
    db: Any

    # ── Runtime error propagation ─────────────────────────────────────────
    error: Optional[str]
