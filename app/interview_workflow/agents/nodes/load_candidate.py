from langgraph.graph import StateGraph
from app.interview_workflow.state import InterviewState
from typing import Dict, Any, Literal

def load_candidate(state: InterviewState) -> Dict[str, Any]:
    """
    Initializes state parameters, ensuring base settings are loaded.
    """
    print("[LangGraph Node] load_candidate")
    return {
        "question_count": state.get("question_count", 0),
        "max_questions": state.get("max_questions", 5),
        "is_completed": False,
        "history": state.get("history", []),
        "current_difficulty": state.get("current_difficulty", "easy")
    }