# app/interview_workflow/workflow.py
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from app.interview_workflow.state import InterviewState
from app.interview_workflow.agents.nodes import (
    load_candidate,
    generate_question_node,
    evaluate_answer_node,
    check_completion_node,
    generate_report_node,
)


#  Entry-point router 

def route_phase(state: InterviewState) -> str:
    """
    Conditional entry point — routes to the correct node based on
    the 'phase' field injected by the API layer before each invocation.

      "start"  → load_candidate → generate_question → END
                 (API returns the question to the client)

      "answer" → evaluate_answer → check_completion
                 → generate_question (loop) or generate_report → END

      "report" → generate_report → END
                 (force-finish; useful for manual termination)
    """
    phase = state.get("phase", "start")

    if phase == "start":
        return "load_candidate"
    elif phase == "answer":
        return "evaluate_answer"
    elif phase == "report":
        return "generate_report"

    raise ValueError(f"[route_phase] Unknown phase: '{phase}'")


# Post-evaluation router 

def route_after_completion(state: InterviewState) -> str:
    """
    Runs after check_completion.
    Propagates errors to END so the API can surface them cleanly.
    Otherwise routes to the next question or the final report.
    """
    if state.get("error"):
        return END

    return "generate_report" if state.get("is_completed", False) else "generate_question"


# Graph builder 

def graph_flow() -> CompiledStateGraph:
    g = StateGraph(InterviewState)

    # Register nodes
    g.add_node("load_candidate",    load_candidate)
    g.add_node("generate_question", generate_question_node)
    g.add_node("evaluate_answer",   evaluate_answer_node)
    g.add_node("check_completion",  check_completion_node)
    g.add_node("generate_report",   generate_report_node)

    # Phase-based conditional entry (replaces the fixed START → load_candidate edge)
    g.set_conditional_entry_point(
        route_phase,
        {
            "load_candidate":  "load_candidate",
            "evaluate_answer": "evaluate_answer",
            "generate_report": "generate_report",
        },
    )

    # start phase: load → question → END (returns question to API caller)
    g.add_edge("load_candidate",    "generate_question")
    g.add_edge("generate_question", END)

    # answer phase: evaluate → check → loop or finish
    g.add_edge("evaluate_answer", "check_completion")
    g.add_conditional_edges(
        "check_completion",
        route_after_completion,
        {
            "generate_question": "generate_question",
            "generate_report":   "generate_report",
            END:                 END,
        },
    )

    # report phase
    g.add_edge("generate_report", END)

    return g.compile()


# Singleton compiled graph — import and call directly from API layer
interview_workflow_app = graph_flow()
