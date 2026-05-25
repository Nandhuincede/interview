import json
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm


class QuestionGeneratorAgent:
    def __init__(self):
        self.llm = get_llm()

    def generate(self, state: dict) -> dict:
        """
        Generates the next technical question using Bloom's Taxonomy.
        """
        role = state.get("role", "Software Engineer")
        experience = state.get("experience", "entry level")
        skillset = state.get("skillset", "")
        difficulty = state.get("current_difficulty", "medium")
        history = state.get("history", [])

        # Get previously used Bloom levels
        used_bloom_levels = [turn.get("bloom_level") for turn in history if turn.get("bloom_level")]
        next_bloom_level = self._get_next_bloom_level(used_bloom_levels)

        # Format history for prompt
        history_str = ""
        for i, turn in enumerate(history):
            bloom = turn.get("bloom_level", "N/A")
            history_str += f"Q{i+1}: {turn.get('question')}\n"
            history_str += f"A{i+1}: {turn.get('answer')}\n"
            history_str += f"Score: {turn.get('score')}/10 | Bloom Level: {bloom}\n\n"

        system_prompt = (
            "You are an expert technical interviewer using Bloom's Taxonomy.\n"
            "Your goal is to conduct a structured, progressive technical interview.\n"
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
            "3. Make questions practical and role-specific.\n"
            "4. Increase cognitive complexity gradually.\n\n"
            "Format your output as a strict JSON object:\n"
            "{\n"
            '  "question": "Your generated question here",\n'
            '  "bloom_level": "remember|understand|apply|analyze|evaluate|create",\n'
            '  "difficulty": "easy|medium|hard",\n'
            '  "rationale": "Brief explanation of why this question fits the Bloom level"\n'
            "}"
        )

        user_prompt = (
            f"Candidate Profile:\n"
            f"- Role: {role}\n"
            f"- Experience: {experience}\n"
            f"- Skills: {skillset}\n\n"
            f"Desired Difficulty: {difficulty}\n"
            f"Target Bloom Level: {next_bloom_level.upper()}\n\n"
            f"Previously Used Bloom Levels: {used_bloom_levels or 'None'}\n\n"
            f"Conversation History:\n{history_str or 'None - This is the start of the interview.'}\n\n"
            f"Generate the next question:"
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt)
            ])

            chain = prompt | self.llm
            response = chain.invoke({})

            content = response.content.strip()

            # Clean markdown JSON fences if present
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            data = json.loads(content)

            return {
                "current_question": data.get("question", "Tell me about your experience in this field."),
                "current_difficulty": data.get("difficulty", difficulty),
                "current_bloom_level": data.get("bloom_level", next_bloom_level),
                "rationale": data.get("rationale", "")
            }

        except Exception as e:
            print(f"[Question Generator Agent Error] {e}")
            
            # Fallback with Bloom's Taxonomy
            fallback = self._get_fallback_question(next_bloom_level, role)
            return {
                "current_question": fallback["question"],
                "current_difficulty": difficulty,
                "current_bloom_level": next_bloom_level,
                "rationale": f"Fallback {next_bloom_level} level question"
            }

    def _get_next_bloom_level(self, used_levels: list) -> str:
        """Determine the next Bloom's level progressively"""
        bloom_order = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        
        if not used_levels:
            return "remember"

        last_level = used_levels[-1]
        
        try:
            current_index = bloom_order.index(last_level)
            
            # Move to next level after 1-2 questions in current level
            if used_levels.count(last_level) >= 2 and current_index < len(bloom_order) - 1:
                return bloom_order[current_index + 1]
            return last_level
        except ValueError:
            return "apply"  # Default to Apply level

    def _get_fallback_question(self, bloom_level: str, role: str) -> dict:
        """Fallback questions mapped to Bloom's levels"""
        fallbacks = {
            "remember": f"What are the fundamental concepts and key technologies used in {role}?",
            "understand": f"Can you explain how {role} concepts work in real-world applications?",
            "apply": f"How would you implement a solution for a common challenge in {role}?",
            "analyze": f"Compare and contrast different approaches to solving scalability issues in {role} projects.",
            "evaluate": f"Which architecture or technology would you recommend for a high-traffic {role} system, and why?",
            "create": f"Design a new feature or system component for a {role} application from scratch."
        }
        
        return {
            "question": fallbacks.get(bloom_level, fallbacks["apply"])
        }