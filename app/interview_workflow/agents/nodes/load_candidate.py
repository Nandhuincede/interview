# app/interview_workflow/agents/nodes/load_candidate.py
import json as _json
from sqlalchemy import select
from typing import Any
from app.interview_workflow.state import InterviewState
from app.db.models import Candidate
from app.exceptions import CandidateNotFoundError


def _ensure_list(value: Any) -> list:
    """Coerce SQLite JSON columns (stored as strings) back to Python lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = _json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


async def load_candidate(state: InterviewState) -> dict:
    """
    Node 1 (phase='start') — Fetches the candidate profile from the database
    and writes it into state so every downstream node can read state['candidate'].

    Raises CandidateNotFoundError if the candidate_id is unknown, which the
    API layer should catch and return as a 404.
    """
    print("[LangGraph Node] load_candidate")

    db = state["db"]
    result = await db.execute(
        select(Candidate).where(Candidate.candidate_id == state["candidate_id"])
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise CandidateNotFoundError(state["candidate_id"])

    return {
        "candidate": {
            "name":          candidate.name,
            "role":          candidate.role,
            "experience":    candidate.experience,
            "qualification": getattr(candidate, "qualification", ""),
            "skillset":      _ensure_list(candidate.skillset),
        },
        # Initialise progress fields on first entry so downstream nodes
        # never need to call .get() with a default.
        "question_count":    state.get("question_count", 0),
        "max_questions":     state.get("max_questions", 5),
        "is_completed":      False,
        "scores":            state.get("scores", []),
        "history":           state.get("history", []),
        "current_difficulty":  state.get("current_difficulty", "easy"),
        "current_bloom_level": state.get("current_bloom_level", "remember"),
        "bloom_scores":        state.get("bloom_scores", {}),
        "error":             None,
    }
