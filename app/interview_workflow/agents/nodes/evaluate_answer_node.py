# app/interview_workflow/agents/nodes/evaluate_answer_node.py
import uuid
from datetime import datetime

from app.interview_workflow.state import InterviewState
from app.interview_workflow.agents.reflection import ReflectionAgent
from app.interview_workflow.agents.difficulty_controller import DifficultyControllerAgent
from app.interview_workflow.agents.conversation_manager import ConversationManagerAgent
from app.db.models import Conversation

reflection_agent         = ReflectionAgent()
difficulty_controller    = DifficultyControllerAgent()
conversation_manager     = ConversationManagerAgent()

BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


async def evaluate_answer_node(state: InterviewState) -> dict:
    """
    Evaluates the candidate's answer (phase='answer').

    Responsibilities:
    - Persist candidate answer to DB
    - Evaluate answer via ReflectionAgent (passes current_bloom_level correctly)
    - Adapt difficulty via DifficultyControllerAgent
    - Adapt Bloom level based on score thresholds (mirrors v2 logic)
    - Append turn to history with bloom_level stored
    - Return immutable state patch (no direct state mutation)
    """
    print("[LangGraph Node] evaluate_answer")

    question     = state.get("current_question", "")
    answer       = state.get("current_answer", "")
    role         = state["candidate"]["role"]
    skillset     = state["candidate"]["skillset"]
    bloom_level  = state.get("current_bloom_level", "remember")
    difficulty   = state.get("current_difficulty", "easy")

    # ── Persist candidate answer ──────────────────────────────────────────
    db = state["db"]
    db.add(
        Conversation(
            conversation_id=f"CONV_{uuid.uuid4().hex[:8].upper()}",
            session_id=state["session_id"],
            interview_id=state["interview_id"],
            speaker="candidate",
            message=answer,
            question_id=state.get("current_question_id", ""),
            timestamp=datetime.utcnow(),
        )
    )
    await db.commit()

    # ── Defaults (used if LLM call fails) ─────────────────────────────────
    evaluation    = {}
    overall_score = 0.0
    next_difficulty = difficulty
    next_bloom      = bloom_level
    error           = None

    try:
        # ── Evaluate answer — bloom_level is now correctly threaded in ────
        evaluation    = reflection_agent.evaluate(question, answer, role, skillset, bloom_level)
        overall_score = evaluation.get("overall_score", 0.0)

        # ── Adaptive difficulty ───────────────────────────────────────────
        next_difficulty = difficulty_controller.adjust_difficulty(overall_score, difficulty)

        # ── Adaptive Bloom level (v2 thresholds: score is 0–10) ───────────
        # overall_score >= 8.5 → promote  (equivalent to v2's >=85 on 0–100 scale)
        # overall_score <  5.0 → demote
        idx = BLOOM_ORDER.index(bloom_level)
        if overall_score >= 8.5 and idx < len(BLOOM_ORDER) - 1:
            next_bloom = BLOOM_ORDER[idx + 1]
        elif overall_score < 5.0 and idx > 0:
            next_bloom = BLOOM_ORDER[idx - 1]
        else:
            next_bloom = bloom_level

    except Exception as e:
        print(f"[evaluate_answer_node Error] {e}")
        error = str(e)

    # ── Append turn to history (bloom_level stored per turn) ─────────────
    updated_history = conversation_manager.update_history(
        history    = state.get("history", []),
        question   = question,
        answer     = answer,
        score      = overall_score,
        difficulty = difficulty,
        bloom_level= bloom_level,   # store the level the question was asked at
        evaluation = evaluation,
    )

    updated_scores = state.get("scores", []) + [overall_score]

    # ── Update bloom_scores aggregate ────────────────────────────────────
    bloom_scores = dict(state.get("bloom_scores", {}))
    prev = bloom_scores.get(bloom_level, [])
    if not isinstance(prev, list):
        prev = [prev]
    bloom_scores[bloom_level] = prev + [overall_score]

    return {
        "history":             updated_history,
        "scores":              updated_scores,
        "current_difficulty":  next_difficulty,
        "current_bloom_level": next_bloom,
        "bloom_scores":        bloom_scores,
        "error":               error,
    }
