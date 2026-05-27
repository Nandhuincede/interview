# app/interview_workflow/agents/nodes/generate_question_node.py
import uuid
from datetime import datetime

from app.interview_workflow.state import InterviewState
from app.interview_workflow.agents.question_generator import QuestionGeneratorAgent
from app.db.models import Conversation

question_generator_agent = QuestionGeneratorAgent()


async def generate_question_node(state: InterviewState) -> dict:
    """
    Generates the next interview question using Bloom's Taxonomy,
    persists it to the database, then returns — causing the graph
    to hit END and hand the question back to the API caller.

    The API delivers the question to the client and waits for an answer.
    On the next HTTP request the API re-invokes the graph with phase='answer'.
    """
    print("[LangGraph Node] generate_question")

    result = question_generator_agent.generate(state)

    q_id = f"Q_{uuid.uuid4().hex[:6].upper()}"

    #  Persist question to DB 
    db = state["db"]
    db.add(
        Conversation(
            conversation_id=f"CONV_{uuid.uuid4().hex[:8].upper()}",
            session_id=state["session_id"],
            interview_id=state["interview_id"],
            speaker="agent",
            message=result["current_question"],
            bloom_level=state.get("current_bloom_level", "remember"),
        )
    )
    await db.commit()

    # ── Update state (graph will hit END after this node) 
    return {
        "current_question":    result["current_question"],
        "current_question_id": q_id,
        "current_difficulty":  result["current_difficulty"],
        "current_bloom_level": result["current_bloom_level"],
        "question_count":      state.get("question_count", 0) + 1,
    }
