# app/interview_workflow/agents/nodes/check_completion_node.py
from app.interview_workflow.state import InterviewState


async def check_completion_node(state: InterviewState) -> dict:
    """
    Checks whether the interview has reached max_questions.
    The conditional edge in workflow.py reads state['is_completed'].
    """
    print("[LangGraph Node] check_completion")

    is_completed = state.get("question_count", 0) >= state.get("max_questions", 5)

    return {"is_completed": is_completed}
