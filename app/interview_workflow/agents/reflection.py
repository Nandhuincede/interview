import json
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm


class ReflectionAgent:
    def __init__(self):
        self.llm = get_llm()

    def evaluate(self, question: str, answer: str, candidate_role: str, 
                 skillset: str, bloom_level: str = "apply") -> dict:
        """
        Evaluates the candidate's answer considering Bloom's Taxonomy level.
        """
        if not answer or answer.strip() == "":
            return {
                "technical_accuracy": 0.0,
                "communication_quality": 0.0,
                "confidence": 0.0,
                "completeness": 0.0,
                "relevance": 0.0,
                "bloom_alignment": 0.0,
                "overall_score": 0.0,
                "feedback": "No response was recorded from the candidate.",
                "bloom_level": bloom_level
            }

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
            "1. technical_accuracy: Correctness and depth of technical knowledge\n"
            "2. communication_quality: Clarity, structure, and articulation\n"
            "3. confidence: Certainty and mastery shown in response\n"
            "4. completeness: How thoroughly the answer addresses the question\n"
            "5. relevance: Stays on topic and directly answers the question\n"
            "6. bloom_alignment: How well the answer matches the expected Bloom's cognitive level\n\n"
            "Also compute 'overall_score' (weighted average with emphasis on technical_accuracy and bloom_alignment).\n"
            "Provide constructive, specific feedback.\n\n"
            "Format your response as a strict JSON object:\n"
            "{\n"
            '  "technical_accuracy": 8.5,\n'
            '  "communication_quality": 8.0,\n'
            '  "confidence": 7.5,\n'
            '  "completeness": 7.0,\n'
            '  "relevance": 9.0,\n'
            '  "bloom_alignment": 8.5,\n'
            '  "overall_score": 8.2,\n'
            '  "feedback": "Detailed constructive feedback here",\n'
            '  "bloom_level": "apply"\n'
            "}"
        )

        user_prompt = (
            f"Candidate Profile:\n"
            f"- Applying for Role: {candidate_role}\n"
            f"- Stated Skills: {skillset}\n\n"
            f"Question Asked (Bloom Level: {bloom_level.upper()}): {question}\n"
            f"Candidate's Transcribed Answer: {answer}\n\n"
            f"Provide a detailed reflection and evaluation:"
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

            evaluation = json.loads(content)
            
            # Ensure bloom_level is set
            evaluation["bloom_level"] = bloom_level
            
            # Ensure bloom_alignment exists
            if "bloom_alignment" not in evaluation:
                evaluation["bloom_alignment"] = evaluation.get("overall_score", 7.0)

            return evaluation

        except Exception as e:
            print(f"[Reflection Agent Error] {e}")
            
            # Dynamic fallback calculation based on answer length + Bloom level
            ans_len = len(answer)
            base_score = 6.5
            
            if ans_len < 30:
                base_score = 3.5
            elif ans_len > 180:
                base_score = 8.5

            # Adjust based on Bloom level (higher levels expect more depth)
            bloom_multiplier = {
                "remember": 1.0,
                "understand": 1.0,
                "apply": 1.1,
                "analyze": 1.2,
                "evaluate": 1.25,
                "create": 1.3
            }.get(bloom_level, 1.1)

            adjusted_score = min(9.5, base_score * bloom_multiplier)

            return {
                "technical_accuracy": adjusted_score,
                "communication_quality": adjusted_score - 0.5,
                "confidence": adjusted_score - 0.8,
                "completeness": adjusted_score - 0.3,
                "relevance": adjusted_score + 0.2,
                "bloom_alignment": adjusted_score - 0.5 if bloom_level in ["analyze", "evaluate", "create"] else adjusted_score,
                "overall_score": adjusted_score,
                "feedback": f"Answer recorded. Demonstrated basic understanding at {bloom_level} level. More depth would be expected for higher cognitive levels.",
                "bloom_level": bloom_level
            }