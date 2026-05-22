from langgraph.graph import StateGraph
from app.interview_workflow.state import InterviewState
from typing import Dict, Any, Literal
from app.interview_workflow.agents.question_generator import QuestionGeneratorAgent

question_generator_agent = QuestionGeneratorAgent()

def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generates the next technical question.
    """
    print("[LangGraph Node] generate_question")
    # Call question generator
    result = question_generator_agent.generate(state)
    
    # Increment count only when a question is generated
    count = state.get("question_count", 0) + 1
    
    return {
        "current_question": result["current_question"],
        "current_difficulty": result["current_difficulty"],
        "question_count": count
    }