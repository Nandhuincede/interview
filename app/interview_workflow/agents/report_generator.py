# app/interview_workflow/agents/report_generator.py
import json
import re
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm


class ReportGeneratorAgent:
    def __init__(self):
        self.llm = get_llm()

    def generate_report(self, state: dict) -> dict:
        """
        Generates a comprehensive hiring evaluation report using Bloom's Taxonomy.

        Uses state['history'] (in-memory, includes scores/bloom_level per turn)
        and optionally state['_db_conversation'] (flat DB records) for richer context.
        """
        candidate  = state.get("candidate", {})
        role       = candidate.get("role", "Software Engineer")
        experience = candidate.get("experience", "entry level")
        skillset   = candidate.get("skillset", "")
        history    = state.get("history", [])

        if not history:
            return self._empty_report()

        #  Aggregate metrics 
        history_summary = []
        total_score = total_tech = total_comm = 0.0
        bloom_scores: dict[str, list[float]] = {}

        for turn in history:
            eval_dict   = turn.get("evaluation", {})
            score       = float(turn.get("score", 0.0))
            bloom_level = turn.get("bloom_level", "apply")  # now reliably set

            total_score += score
            total_tech  += eval_dict.get("technical_accuracy",   score)
            total_comm  += eval_dict.get("communication_quality", score)

            bloom_scores.setdefault(bloom_level, []).append(score)

            history_summary.append({
                "question":            turn.get("question"),
                "answer":              turn.get("answer"),
                "score":               score,
                "bloom_level":         bloom_level,
                "technical_accuracy":  eval_dict.get("technical_accuracy", score),
                "communication_quality": eval_dict.get("communication_quality", score),
                "bloom_alignment":     eval_dict.get("bloom_alignment", score),
                "feedback":            eval_dict.get("feedback", "No specific feedback."),
            })

        n          = len(history)
        avg_score  = round(total_score / n, 2)
        avg_tech   = round(total_tech  / n, 2)
        avg_comm   = round(total_comm  / n, 2)
        bloom_analysis = {
            level: round(sum(scores) / len(scores), 2)
            for level, scores in bloom_scores.items()
        }

        # LLM report generation 
        system_prompt = (
            "You are an expert HR and senior technical evaluator using Bloom's Taxonomy.\n"
            "Generate a professional, detailed hiring evaluation report.\n"
            "Consider both technical performance and cognitive development across Bloom's levels.\n\n"
            "Respond with a strict JSON object:\n"
            "{\n"
            '  "overall_score": 8.2,\n'
            '  "technical_score": 8.5,\n'
            '  "communication_score": 7.9,\n'
            '  "recommendation": "Selected | Rejected | Needs Further Evaluation",\n'
            '  "strengths": ["item 1", "item 2"],\n'
            '  "improvements": ["item 1", "item 2"],\n'
            '  "bloom_taxonomy_analysis": {"remember": 8.0, "apply": 7.5},\n'
            '  "cognitive_strengths": ["Strong in analysis and evaluation"],\n'
            '  "ai_feedback": "Comprehensive summary with cognitive performance and hiring rationale."\n'
            "}"
        )

        user_prompt = (
            f"Candidate Profile:\n"
            f"- Role: {role}\n"
            f"- Experience: {experience}\n"
            f"- Skillset: {skillset}\n\n"
            f"Interview Summary:\n"
            f"{json.dumps(history_summary, indent=2)}\n\n"
            f"Quantitative Metrics:\n"
            f"- Questions answered: {n}\n"
            f"- Average score:      {avg_score}/10\n"
            f"- Technical score:    {avg_tech}/10\n"
            f"- Communication:      {avg_comm}/10\n\n"
            f"Bloom's Performance:\n"
            f"{json.dumps(bloom_analysis, indent=2)}\n\n"
            f"Generate the report:"
        )

        try:
            prompt   = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human",  user_prompt),
            ])
            chain    = prompt | self.llm
            response = chain.invoke({})
            content  = response.content.strip()

            if content.startswith("```"):
                content = re.sub(r"^```[a-zA-Z]*\n?", "", content).rstrip("```").strip()

            report_data = json.loads(content)

            # Attach computed data
            report_data["question_wise_evaluation"] = history_summary
            report_data["bloom_taxonomy_analysis"]  = bloom_analysis
            report_data["overall_score"]       = float(report_data.get("overall_score",      avg_score))
            report_data["technical_score"]     = float(report_data.get("technical_score",    avg_tech))
            report_data["communication_score"] = float(report_data.get("communication_score", avg_comm))

            if not report_data.get("cognitive_strengths"):
                report_data["cognitive_strengths"] = self._cognitive_strengths(bloom_analysis)

            return report_data

        except Exception as e:
            print(f"[ReportGeneratorAgent Error] {e}")
            return self._fallback_report(avg_score, avg_tech, avg_comm, role,
                                         bloom_analysis, history_summary)

    # Helpers 

    def _empty_report(self) -> dict:
        return {
            "overall_score": 0.0, "technical_score": 0.0, "communication_score": 0.0,
            "recommendation": "Needs Further Evaluation",
            "strengths": ["No interview responses recorded"],
            "improvements": ["No technical Q&A completed"],
            "question_wise_evaluation": [],
            "bloom_taxonomy_analysis": {},
            "cognitive_strengths": [],
            "ai_feedback": "The interview session ended before any questions were answered.",
        }

    def _fallback_report(self, avg_score, avg_tech, avg_comm, role,
                          bloom_analysis, history_summary) -> dict:
        rec = (
            "Selected" if avg_score >= 7.5
            else "Rejected" if avg_score < 5.0
            else "Needs Further Evaluation"
        )
        return {
            "overall_score":      avg_score,
            "technical_score":    avg_tech,
            "communication_score": avg_comm,
            "recommendation":     rec,
            "strengths":  [f"Demonstrated solid knowledge of core {role} concepts."],
            "improvements": ["Provide deeper architectural reasoning at higher Bloom levels."],
            "bloom_taxonomy_analysis":  bloom_analysis,
            "cognitive_strengths":      self._cognitive_strengths(bloom_analysis),
            "question_wise_evaluation": history_summary,
            "ai_feedback": (
                f"The candidate completed the {role} interview with an average score of "
                f"{avg_score}/10. Recommendation: {rec}."
            ),
        }

    def _cognitive_strengths(self, bloom_analysis: dict) -> List[str]:
        strengths = [
            f"Strong performance at {level.capitalize()} level (score: {score})"
            for level, score in sorted(bloom_analysis.items(), key=lambda x: x[1], reverse=True)[:3]
            if score >= 7.5
        ]
        return strengths or ["Consistent performance across cognitive levels."]
