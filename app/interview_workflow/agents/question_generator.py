# app/interview_workflow/agents/question_generator.py
import json
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm


BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

BLOOM_DESCRIPTIONS = {
    "remember":  "Ask recall-based questions about definitions, concepts, or facts.",
    "understand": "Ask conceptual explanation questions to test understanding.",
    "apply":     "Ask scenario-based questions where concepts must be applied.",
    "analyze":   "Ask comparison, debugging, optimisation, or reasoning questions.",
    "evaluate":  "Ask judgment, tradeoff, architecture, or decision-making questions.",
    "create":    "Ask system design or solution-creation questions.",
}


class QuestionGeneratorAgent:
    def __init__(self):
        self.llm = get_llm()

    def generate(self, state: dict) -> dict:
        """
        Generates the next technical interview question.

        Bloom level is now read directly from state['current_bloom_level'],
        which is set by evaluate_answer_node after each answer.  This removes
        the v1 bug where the generator recomputed the level independently and
        the two could drift apart.
        """
        candidate   = state.get("candidate", {})
        role        = candidate.get("role", "Software Engineer")
        experience  = candidate.get("experience", "entry level")
        skillset    = candidate.get("skillset", "")
        difficulty  = state.get("current_difficulty", "easy")
        history     = state.get("history", [])

        # ── Bloom level: trust state, computed by evaluate_answer_node ────
        bloom_level = state.get("current_bloom_level", "remember")
        bloom_instruction = BLOOM_DESCRIPTIONS.get(bloom_level, BLOOM_DESCRIPTIONS["understand"])

        # ── Format history for the LLM prompt ────────────────────────────
        history_str = ""
        for i, turn in enumerate(history):
            history_str += (
                f"Q{i+1}: {turn.get('question')}\n"
                f"A{i+1}: {turn.get('answer')}\n"
                f"Score: {turn.get('score')}/10 | "
                f"Bloom: {turn.get('bloom_level', 'N/A')} | "
                f"Difficulty: {turn.get('difficulty', 'N/A')}\n\n"
            )

        system_prompt = (
            "You are an expert technical interviewer using Bloom's Taxonomy.\n"
            "Generate ONE technical question at the specified Bloom's cognitive level.\n\n"
            "Bloom's Levels:\n"
            "- Remember: Recall basic facts and concepts\n"
            "- Understand: Explain ideas and concepts\n"
            "- Apply: Use information in new situations\n"
            "- Analyze: Break down information into parts\n"
            "- Evaluate: Justify decisions or compare ideas\n"
            "- Create: Produce new or original work\n\n"
            "Rules:\n"
            "1. Strictly follow the requested Bloom level.\n"
            "2. Avoid repeating previous questions.\n"
            "3. Make questions practical and role-specific.\n\n"
            "Respond with a strict JSON object:\n"
            "{{\n"
            '  "question": "Your generated question here",\n'
            '  "bloom_level": "remember|understand|apply|analyze|evaluate|create",\n'
            '  "difficulty": "easy|medium|hard",\n'
            '  "rationale": "Brief explanation of why this fits the Bloom level"\n'
            "}}"
        )

        user_prompt = (
            f"Candidate Profile:\n"
            f"- Role: {role}\n"
            f"- Experience: {experience}\n"
            f"- Skills: {skillset}\n\n"
            f"Desired Difficulty: {difficulty}\n"
            f"Target Bloom Level: {bloom_level.upper()}\n"
            f"Bloom Instruction: {bloom_instruction}\n\n"
            f"Conversation History:\n"
            f"{history_str or 'None — this is the first question.'}\n\n"
            f"Generate the next question:"
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt),
            ])
            chain = prompt | self.llm
            response = chain.invoke({})
            content = response.content.strip()

            # Strip markdown fences (case-insensitive)
            if content.startswith("```"):
                import re
                content = re.sub(r"^```[a-zA-Z]*\n?", "", content).rstrip("```").strip()

            data = json.loads(content)

            return {
                "current_question":    data.get("question", self._fallback(bloom_level, role)["question"]),
                "current_difficulty":  data.get("difficulty", difficulty),
                "current_bloom_level": data.get("bloom_level", bloom_level),
                "rationale":           data.get("rationale", ""),
            }

        except Exception as e:
            print(f"[QuestionGeneratorAgent Error] {e}")
            fallback = self._fallback(bloom_level, role)
            return {
                "current_question":    fallback["question"],
                "current_difficulty":  difficulty,
                "current_bloom_level": bloom_level,
                "rationale":           f"Fallback question for {bloom_level} level",
            }

    def _fallback(self, bloom_level: str, role: str) -> dict:
        """Role-specific fallback questions per Bloom level."""
        fallbacks = {
            "remember":  f"What are the fundamental concepts and key technologies used in {role}?",
            "understand": f"Can you explain how core {role} concepts work in real-world applications?",
            "apply":     f"How would you implement a solution for a common challenge in {role}?",
            "analyze":   f"Compare and contrast different approaches to solving scalability issues in {role} projects.",
            "evaluate":  f"Which architecture or technology would you recommend for a high-traffic {role} system, and why?",
            "create":    f"Design a new feature or system component for a {role} application from scratch.",
        }
        return {"question": fallbacks.get(bloom_level, fallbacks["apply"])}