# app/interview_workflow/agents/nodes/generate_report_node.py
import uuid
from sqlalchemy import select

from app.interview_workflow.state import InterviewState
from app.interview_workflow.agents.report_generator import ReportGeneratorAgent
from app.db.models import Conversation, Report

report_generator_agent = ReportGeneratorAgent()


async def generate_report_node(state: InterviewState) -> dict:
    """
    Final node — generates and persists the hiring evaluation report.

    Re-fetches the full conversation from DB (source of truth) rather than
    relying on in-memory history, so the report survives server restarts
    and partial graph re-invocations.

    Includes a duplicate-report guard: if a report already exists for this
    session (e.g. phase='report' was called twice), it skips DB insertion
    and returns the existing data.
    """
    print("[LangGraph Node] generate_report")

    db = state["db"]

    # ── Re-fetch conversation from DB ─────────────────────────────────────
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == state["session_id"])
        .order_by(Conversation.timestamp)
    )
    all_messages = result.scalars().all()

    # Build a flat conversation list for the LLM prompt
    conv_list = [
        {"speaker": m.speaker, "message": m.message}
        for m in all_messages
    ]

    # ── Generate report via LLM ───────────────────────────────────────────
    # Pass in-memory history too so the agent has score/bloom context
    report_data = report_generator_agent.generate_report({
        **state,
        "_db_conversation": conv_list,   # extra context for the agent
    })

    # ── Duplicate report guard ────────────────────────────────────────────
    existing = await db.execute(
        select(Report).where(Report.session_id == state["session_id"])
    )
    existing_report = existing.scalars().first()

    if not existing_report:
        report = Report(
            report_id=f"REP_{uuid.uuid4().hex[:6].upper()}",
            session_id=state["session_id"],
            interview_id=state["interview_id"],
            overall_score=report_data.get("overall_score"),
            technical_score=report_data.get("technical_score"),
            communication_score=report_data.get("communication_score"),
            strengths=report_data.get("strengths", []),
            improvements=report_data.get("improvements", []),
            recommendation=report_data.get("recommendation", "Needs Further Evaluation"),
        )
        db.add(report)

    await db.commit()

    return {
        "overall_score":          float(report_data.get("overall_score", 0.0)),
        "technical_score":        float(report_data.get("technical_score", 0.0)),
        "communication_score":    float(report_data.get("communication_score", 0.0)),
        "recommendation":         report_data.get("recommendation", "Needs Further Evaluation"),
        "strengths":              report_data.get("strengths", []),
        "improvements":           report_data.get("improvements", []),
        "question_wise_evaluation": report_data.get("question_wise_evaluation", []),
        "ai_feedback":            report_data.get("ai_feedback", ""),
        "is_completed":           True,
    }
