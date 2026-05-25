import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm


class ReportGeneratorAgent:
    def __init__(self):
        self.llm = get_llm()

    def generate_report(self, state: dict) -> dict:
        """
        Generates a comprehensive interview report including Bloom's Taxonomy analysis.
        """
        role = state.get("role", "Software Engineer")
        experience = state.get("experience", "entry level")
        skillset = state.get("skillset", "")
        history = state.get("history", [])

        # If history is empty
        if not history:
            return {
                "overall_score": 0.0,
                "technical_score": 0.0,
                "communication_score": 0.0,
                "recommendation": "Needs Further Evaluation",
                "strengths": ["No interview responses recorded"],
                "improvements": ["No technical Q&A completed"],
                "question_wise_evaluation": [],
                "bloom_taxonomy_analysis": {},
                "cognitive_strengths": [],
                "ai_feedback": "The interview session was ended before any questions were answered."
            }

        # Compile history summary
        history_summary = []
        total_score = 0.0
        total_tech = 0.0
        total_comm = 0.0

        # Bloom's Taxonomy tracking
        bloom_scores = {}
        bloom_counts = {}

        for turn in history:
            q = turn.get("question")
            a = turn.get("answer")
            eval_dict = turn.get("evaluation", {})
            score = turn.get("score", 0.0)
            bloom_level = turn.get("bloom_level", "apply")

            total_score += score
            total_tech += eval_dict.get("technical_accuracy", score)
            total_comm += eval_dict.get("communication_quality", score)

            # Track Bloom performance
            if bloom_level not in bloom_scores:
                bloom_scores[bloom_level] = []
                bloom_counts[bloom_level] = 0

            bloom_scores[bloom_level].append(score)
            bloom_counts[bloom_level] += 1

            history_summary.append({
                "question": q,
                "answer": a,
                "score": score,
                "bloom_level": bloom_level,
                "technical_accuracy": eval_dict.get("technical_accuracy", score),
                "communication_quality": eval_dict.get("communication_quality", score),
                "bloom_alignment": eval_dict.get("bloom_alignment", score),
                "feedback": eval_dict.get("feedback", "No specific feedback.")
            })

        avg_score = round(total_score / len(history), 2)
        avg_tech = round(total_tech / len(history), 2)
        avg_comm = round(total_comm / len(history), 2)

        # Calculate Bloom level averages
        bloom_analysis = {}
        for level, scores in bloom_scores.items():
            bloom_analysis[level] = round(sum(scores) / len(scores), 2)

        system_prompt = (
            "You are an expert HR and senior technical evaluator using Bloom's Taxonomy.\n"
            "Generate a professional, detailed, and insightful interview evaluation report.\n"
            "Consider both technical performance and cognitive development across Bloom's levels.\n\n"
            "Bloom's Taxonomy Levels: Remember, Understand, Apply, Analyze, Evaluate, Create.\n\n"
            "Format your output as a strict JSON object with these keys:\n"
            "{\n"
            '  "overall_score": 8.2,\n'
            '  "technical_score": 8.5,\n'
            '  "communication_score": 7.9,\n'
            '  "recommendation": "Selected | Rejected | Needs Further Evaluation",\n'
            '  "strengths": ["list item 1", "list item 2"],\n'
            '  "improvements": ["list item 1", "list item 2"],\n'
            '  "bloom_taxonomy_analysis": {"remember": 8.0, "apply": 7.5, ...},\n'
            '  "cognitive_strengths": ["Strong in analysis and evaluation", "Good at practical application"],\n'
            '  "ai_feedback": "Comprehensive summary including cognitive performance and hiring rationale."\n'
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
            f"- Total Questions: {len(history)}\n"
            f"- Average Score: {avg_score}/10\n"
            f"- Average Technical Score: {avg_tech}/10\n"
            f"- Average Communication Score: {avg_comm}/10\n\n"
            f"Bloom's Taxonomy Performance:\n"
            f"{json.dumps(bloom_analysis, indent=2)}\n\n"
            f"Generate a comprehensive professional interview report in JSON format:"
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt)
            ])

            chain = prompt | self.llm
            response = chain.invoke({})

            content = response.content.strip()

            # Clean JSON response
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            report_data = json.loads(content)

            # Attach additional data
            report_data["question_wise_evaluation"] = history_summary
            report_data["bloom_taxonomy_analysis"] = bloom_analysis

            # Ensure numeric values
            report_data["overall_score"] = float(report_data.get("overall_score", avg_score))
            report_data["technical_score"] = float(report_data.get("technical_score", avg_tech))
            report_data["communication_score"] = float(report_data.get("communication_score", avg_comm))

            # Add cognitive strengths if not provided by LLM
            if "cognitive_strengths" not in report_data or not report_data["cognitive_strengths"]:
                report_data["cognitive_strengths"] = self._generate_cognitive_strengths(bloom_analysis)

            return report_data

        except Exception as e:
            print(f"[Report Generator Agent Error] {e}")
            # Enhanced Fallback Report
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
                "strengths": [
                    f"Demonstrated good knowledge of core {role} concepts.",
                    "Handled multiple technical questions effectively."
                ],
                "improvements": [
                    "Provide deeper analysis and architectural reasoning.",
                    "Improve response structure for higher Bloom levels (Analyze/Evaluate/Create)."
                ],
                "bloom_taxonomy_analysis": bloom_analysis,
                "cognitive_strengths": self._generate_cognitive_strengths(bloom_analysis),
                "question_wise_evaluation": history_summary,
                "ai_feedback": f"The candidate completed the {role} interview with an overall score of {avg_score}/10. "
                              f"They showed progressive cognitive development across Bloom's Taxonomy levels. "
                              f"Recommendation: {recommendation}."
            }

    def _generate_cognitive_strengths(self, bloom_analysis: dict) -> List[str]:
        """Generate cognitive insights based on Bloom performance"""
        if not bloom_analysis:
            return ["Basic technical understanding demonstrated."]

        strengths = []
        sorted_bloom = sorted(bloom_analysis.items(), key=lambda x: x[1], reverse=True)

        for level, score in sorted_bloom[:3]:
            if score >= 7.5:
                strengths.append(f"Strong performance at {level.capitalize()} level (Score: {score})")

        if not strengths:
            strengths.append("Consistent performance across cognitive levels.")

        return strengths