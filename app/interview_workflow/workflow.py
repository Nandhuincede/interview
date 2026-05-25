# backend/app/interview_workflow/workflow.py
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from app.interview_workflow.state import InterviewState
from app.interview_workflow.agents.nodes import (
    load_candidate,
    generate_question_node,
    evaluate_answer_node,
    check_completion_node,
    generate_report_node
)


def completion_router(state: InterviewState) -> Literal["generate_question", "generate_report"]:
    """
    Routes control based on whether the interview is completed.
    """
    if state.get("is_completed", False):
        return "generate_report"
    else:
        return "generate_question"


def graph_flow():
    workflow = StateGraph(InterviewState)

    workflow.add_node("load_candidate", load_candidate)
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("check_completion", check_completion_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.add_edge(START, "load_candidate")
    workflow.add_edge("load_candidate", "generate_question")
    workflow.add_edge("generate_question", "evaluate_answer")
    workflow.add_edge("evaluate_answer", "check_completion")

    # Conditional routing
    workflow.add_conditional_edges(
        "check_completion",
        completion_router,
        {
            "generate_question": "generate_question",
            "generate_report": "generate_report"
        }
    )

    workflow.add_edge("generate_report", END)

    return workflow.compile()


# Compile the graph
interview_workflow_app = graph_flow()