import json
import re
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm


class ReflectionAgent:
    def __init__(self) -> None:
        self.llm = get_llm()

    def evaluate(
        self,
        question:       str,
        answer:         str,
        candidate_role: str,
        skillset:       str,
        bloom_level:    str = "remember",
    ) -> dict:
        """
        Evaluates the candidate's answer against the active Bloom level.
        bloom_level is now always supplied by evaluate_answer_node (no default drift).
        """
        if not answer or answer.strip() == "":
            return self._empty_response(bloom_level)

        system_prompt = (
            "You are an expert technical interviewer and reflection agent using Bloom's Taxonomy.\n"
            "Evaluate the candidate's answer considering both technical quality and the expected cognitive level.\n\n"
            f"Current Bloom's Taxonomy Level: {bloom_level.upper()}\n\n"
            "Bloom's Level Expectations:\n"
            "- Remember: Recall facts, definitions, basic concepts\n"
            "- Understand: Explain ideas, concepts, relationships\n"
            "- Apply: Use knowledge in new situations, solve problems\n"
            "- Analyze: Break down information, compare, contrast\n"
            "- Evaluate: Justify decisions, critique, recommend\n"
            "- Create: Design, construct, develop new solutions\n\n"
            "Score each metric from 0.0 to 10.0:\n"
            "1. technical_accuracy   — correctness and depth of technical knowledge\n"
            "2. communication_quality — clarity, structure, and articulation\n"
            "3. confidence           — certainty and mastery shown in response\n"
            "4. completeness         — how thoroughly the answer addresses the question\n"
            "5. relevance            — stays on topic and directly answers the question\n"
            "6. bloom_alignment      — how well the answer matches the expected Bloom level\n\n"
            "Compute 'overall_score' as a weighted average emphasising technical_accuracy and bloom_alignment.\n"
            "Provide constructive, specific feedback.\n\n"
            "Respond with a strict JSON object:\n"
            "{{\n"
            '  "technical_accuracy": 8.5,\n'
            '  "communication_quality": 8.0,\n'
            '  "confidence": 7.5,\n'
            '  "completeness": 7.0,\n'
            '  "relevance": 9.0,\n'
            '  "bloom_alignment": 8.5,\n'
            '  "overall_score": 8.2,\n'
            '  "feedback": "Detailed constructive feedback here",\n'
            '  "bloom_level": "remember"\n'
            "}}"
        )

        user_prompt = (
            f"Candidate Profile:\n"
            f"- Applying for Role: {candidate_role}\n"
            f"- Stated Skills: {skillset}\n\n"
            f"Question Asked (Bloom Level: {bloom_level.upper()}): {question}\n"
            f"Candidate's Answer: {answer}\n\n"
            f"Provide a detailed reflection and evaluation:"
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt),
            ])
            chain  = prompt | self.llm
            response = chain.invoke({})
            content  = response.content.strip()

            if content.startswith("```"):
                content = re.sub(r"^```[a-zA-Z]*\n?", "", content).rstrip("```").strip()

            evaluation = json.loads(content)
            evaluation["bloom_level"] = bloom_level

            if "bloom_alignment" not in evaluation:
                evaluation["bloom_alignment"] = evaluation.get("overall_score", 7.0)

            return evaluation

        except Exception as e:
            print(f"[ReflectionAgent Error] {e}")
            return self._fallback_scores(answer, bloom_level)

    # Helpers 

    def _empty_response(self, bloom_level: str) -> dict:
        return {
            "technical_accuracy":   0.0,
            "communication_quality": 0.0,
            "confidence":           0.0,
            "completeness":         0.0,
            "relevance":            0.0,
            "bloom_alignment":      0.0,
            "overall_score":        0.0,
            "feedback":             "No response was recorded from the candidate.",
            "bloom_level":          bloom_level,
        }

    def _fallback_scores(self, answer: str, bloom_level: str) -> dict:
        ans_len    = len(answer)
        base_score = 3.5 if ans_len < 30 else (8.5 if ans_len > 180 else 6.5)

        bloom_multiplier = {
            "remember":  1.0,
            "understand": 1.0,
            "apply":     1.1,
            "analyze":   1.2,
            "evaluate":  1.25,
            "create":    1.3,
        }.get(bloom_level, 1.1)

        s = min(9.5, base_score * bloom_multiplier)
        return {
            "technical_accuracy":   s,
            "communication_quality": s - 0.5,
            "confidence":           s - 0.8,
            "completeness":         s - 0.3,
            "relevance":            min(9.5, s + 0.2),
            "bloom_alignment":      s - 0.5 if bloom_level in ("analyze", "evaluate", "create") else s,
            "overall_score":        s,
            "feedback":             (
                f"Answer recorded. Demonstrated basic understanding at {bloom_level} level. "
                "More depth would be expected for higher cognitive levels."
            ),
            "bloom_level": bloom_level,
        }