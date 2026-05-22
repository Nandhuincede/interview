from app.interview_workflow.state import InterviewState
from typing import Dict, Any, Literal
def check_completion_node(state: InterviewState) -> Dict[str, Any]:
    """
    Checks if the maximum question limit has been reached.
    """
    print("[LangGraph Node] check_completion")
    count = state.get("question_count", 0)
    max_q = state.get("max_questions", 5)
    
    is_completed = count >= max_q
    
    return {
        "is_completed": is_completed
    }