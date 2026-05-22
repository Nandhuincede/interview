from typing import Dict, Any, Literal
from app.interview_workflow.state import InterviewState

from app.interview_workflow.agents.report_generator import ReportGeneratorAgent


report_generator_agent = ReportGeneratorAgent()

def generate_report_node(state: InterviewState) -> Dict[str, Any]:
    """
    Assembles final hiring evaluation report.
    """
    print("[LangGraph Node] generate_report")
    report = report_generator_agent.generate_report(state)
    
    return {
        "overall_score": report.get("overall_score", 0.0),
        "technical_score": report.get("technical_score", 0.0),
        "communication_score": report.get("communication_score", 0.0),
        "recommendation": report.get("recommendation", "Needs Further Evaluation"),
        "strengths": report.get("strengths", []),
        "improvements": report.get("improvements", []),
        "question_wise_evaluation": report.get("question_wise_evaluation", []),
        "ai_feedback": report.get("ai_feedback", "")
    }