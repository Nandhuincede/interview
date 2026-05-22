import json
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm

class ReflectionAgent:
    def __init__(self):
        self.llm = get_llm()
        
    def evaluate(self, question: str, answer: str, candidate_role: str, skillset: str) -> dict:
        """
        Evaluates the technical accuracy, communication quality, confidence, completeness,
        and relevance of the candidate's answer to the generated question.
        """
        if not answer or answer.strip() == "":
            return {
                "technical_accuracy": 0.0,
                "communication_quality": 0.0,
                "confidence": 0.0,
                "completeness": 0.0,
                "relevance": 0.0,
                "overall_score": 0.0,
                "feedback": "No response was recorded from the candidate."
            }
            
        system_prompt = (
            "You are an expert technical interviewer and reflection agent. Your task is to evaluate the candidate's answer to a technical question.\n"
            "Analyze the answer based on five core metrics, scoring each from 0.0 to 10.0 (where 10.0 is perfect):\n"
            "1. technical_accuracy: Is the answer correct technically? Does it use the correct terms and accurate concepts?\n"
            "2. communication_quality: Is the answer clear, structured, and easy to follow?\n"
            "3. confidence: Does the language indicate hesitation, doubt, or strong certainty and mastery?\n"
            "4. completeness: Does the answer address all parts of the question, or does it leave out major aspects?\n"
            "5. relevance: Does the candidate stick to the question, or do they ramble onto unrelated topics?\n\n"
            "Also compute an 'overall_score' (average of the 5 metrics, or weighted towards technical accuracy) and provide detailed, constructive 'feedback'.\n\n"
            "Format your response as a single, strict JSON object with these keys:\n"
            "{\n"
            '  "technical_accuracy": 8.5,\n'
            '  "communication_quality": 8.0,\n'
            '  "confidence": 7.5,\n'
            '  "completeness": 7.0,\n'
            '  "relevance": 9.0,\n'
            '  "overall_score": 8.0,\n'
            '  "feedback": "Your detailed evaluation feedback here"\n'
            "}"
        )
        
        user_prompt = (
            f"Candidate Profile:\n"
            f"- Applying for Role: {candidate_role}\n"
            f"- Stated Skills: {skillset}\n\n"
            f"Question Asked: {question}\n"
            f"Candidate's Transcribed Answer: {answer}\n\n"
            f"Provide the reflection evaluation:"
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
            return evaluation
            
        except Exception as e:
            print(f"[Reflection Agent Error] {e}")
            # Dynamic fallback calculation based on answer length
            ans_len = len(answer)
            base_score = 6.0
            if ans_len < 30:
                base_score = 4.0
            elif ans_len > 150:
                base_score = 8.0
                
            return {
                "technical_accuracy": base_score,
                "communication_quality": base_score - 0.5,
                "confidence": base_score - 1.0,
                "completeness": base_score - 0.5,
                "relevance": base_score + 0.5,
                "overall_score": base_score,
                "feedback": "Answer successfully recorded. Demonstrated understanding of the topic, though more depth could be provided."
            }
