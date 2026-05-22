from typing import Dict, Any, Literal
from app.interview_workflow.state import InterviewState

from app.interview_workflow.agents.reflection import ReflectionAgent
from app.interview_workflow.agents.difficulty_controller import DifficultyControllerAgent
from app.interview_workflow.agents.conversation_manager import ConversationManagerAgent

reflection_agent = ReflectionAgent()
difficulty_controller_agent = DifficultyControllerAgent()
conversation_manager_agent = ConversationManagerAgent()


def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluates the candidate's transcribed answer.
    """
    print("[LangGraph Node] evaluate_answer")
    question = state.get("current_question", "")
    answer = state.get("current_answer", "")
    role = state.get("role", "")
    skillset = state.get("skillset", "")
    
    # Evaluate
    evaluation = reflection_agent.evaluate(question, answer, role, skillset)
    overall_score = evaluation.get("overall_score", 0.0)
    
    # Adjust difficulty for the next question
    next_difficulty = difficulty_controller_agent.adjust_difficulty(
        overall_score, 
        state.get("current_difficulty", "easy")
    )
    
    # Update memory context & conversation history
    updated_history = conversation_manager_agent.update_history(
        state.get("history", []),
        question,
        answer,
        overall_score,
        state.get("current_difficulty", "easy"),
        evaluation
    )
    
    return {
        "history": updated_history,
        "current_difficulty": next_difficulty
    }