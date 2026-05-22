import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm

class ReportGeneratorAgent:
    def __init__(self):
        self.llm = get_llm()
        
    def generate_report(self, state: dict) -> dict:
        """
        Aggregates all evaluation scores and conversation history, then
        generates the final structured interview evaluation report.
        """
        role = state.get("role", "Software Engineer")
        experience = state.get("experience", "entry level")
        skillset = state.get("skillset", "")
        history = state.get("history", [])
        
        # If history is empty, create a dummy or warning
        if not history:
            return {
                "overall_score": 0.0,
                "technical_score": 0.0,
                "communication_score": 0.0,
                "recommendation": "Needs Further Evaluation",
                "strengths": ["No interview responses recorded"],
                "improvements": ["No technical Q&A completed"],
                "question_wise_evaluation": [],
                "ai_feedback": "The interview session was ended before any questions were answered."
            }
            
        # Compile history summary for LLM
        history_summary = []
        total_score = 0.0
        total_tech = 0.0
        total_comm = 0.0
        
        for turn in history:
            q = turn.get("question")
            a = turn.get("answer")
            eval_dict = turn.get("evaluation", {})
            score = turn.get("score", 0.0)
            
            total_score += score
            total_tech += eval_dict.get("technical_accuracy", score)
            total_comm += eval_dict.get("communication_quality", score)
            
            history_summary.append({
                "question": q,
                "answer": a,
                "score": score,
                "technical_accuracy": eval_dict.get("technical_accuracy", score),
                "communication_quality": eval_dict.get("communication_quality", score),
                "feedback": eval_dict.get("feedback", "No specific feedback.")
            })
            
        avg_score = round(total_score / len(history), 2)
        avg_tech = round(total_tech / len(history), 2)
        avg_comm = round(total_comm / len(history), 2)
        
        system_prompt = (
            "You are an expert HR and senior technical evaluator. Your job is to aggregate the details of a technical interview and generate a beautiful, production-ready, professional interview report.\n"
            "Analyze the candidate's answers and their technical scores.\n"
            "Decide on a hiring recommendation: 'Selected', 'Rejected', or 'Needs Further Evaluation'.\n"
            "Format your output as a strict JSON object with the following keys:\n"
            "{\n"
            '  "overall_score": 8.2,\n'
            '  "technical_score": 8.5,\n'
            '  "communication_score": 7.9,\n'
            '  "recommendation": "Selected | Rejected | Needs Further Evaluation",\n'
            '  "strengths": ["list item 1", "list item 2", ...],\n'
            '  "improvements": ["list item 1", "list item 2", ...],\n'
            '  "ai_feedback": "A summary synthesis of the candidate\'s overall performance, capability, fit, and rationale for the decision."\n'
            "}"
        )
        
        user_prompt = (
            f"Candidate Profile:\n"
            f"- Applying for Role: {role}\n"
            f"- Stated Experience: {experience}\n"
            f"- Skillset: {skillset}\n\n"
            f"Interview History Details:\n"
            f"{json.dumps(history_summary, indent=2)}\n\n"
            f"Quantitative Summary:\n"
            f"- Count of Questions: {len(history)}\n"
            f"- Average Score: {avg_score}/10\n"
            f"- Average Technical Score: {avg_tech}/10\n"
            f"- Average Communication Score: {avg_comm}/10\n\n"
            f"Generate the comprehensive interview report in JSON format:"
        )
        
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt)
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({})
            
            content = response.content.strip()
            
            # Remove markdown JSON fences if present
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
                
            report_data = json.loads(content)
            
            # Attach question_wise_evaluation
            report_data["question_wise_evaluation"] = history_summary
            
            # Ensure numbers are floats
            report_data["overall_score"] = float(report_data.get("overall_score", avg_score))
            report_data["technical_score"] = float(report_data.get("technical_score", avg_tech))
            report_data["communication_score"] = float(report_data.get("communication_score", avg_comm))
            
            return report_data
            
        except Exception as e:
            print(f"[Report Generator Agent Error] {e}")
            # Fallback report compilation
            recommendation = "Needs Further Evaluation"
            if avg_score >= 7.5:
                recommendation = "Selected"
            elif avg_score < 5.0:
                recommendation = "Rejected"
                
            return {
                "overall_score": avg_score,
                "technical_score": avg_tech,
                "communication_score": avg_comm,
                "recommendation": recommendation,
                "strengths": [f"Demonstrated good knowledge of core {role} concepts.", "Handled multiple technical questions in the session."],
                "improvements": ["Could provide deeper architecture and scale analysis in answers.", "Improve response completeness and confidence under technical drilling."],
                "question_wise_evaluation": history_summary,
                "ai_feedback": f"The candidate completed the interactive {role} technical interview with an overall score of {avg_score}/10. Rationale: {recommendation} based on performance across all questions."
            }
network_request = False
