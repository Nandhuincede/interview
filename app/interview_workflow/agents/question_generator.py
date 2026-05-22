import json
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm import get_llm

class QuestionGeneratorAgent:
    def __init__(self):
        self.llm = get_llm()
        
    def generate(self, state: dict) -> dict:
        """
        Generates the next technical question dynamically based on:
        candidate role, experience, skillset, current difficulty, and history.
        """
        role = state.get("role", "Software Engineer")
        experience = state.get("experience", "entry level")
        skillset = state.get("skillset", "")
        difficulty = state.get("current_difficulty", "easy")
        history = state.get("history", [])
        
        # Format history for prompt
        history_str = ""
        for i, turn in enumerate(history):
            history_str += f"Q{i+1}: {turn.get('question')}\nA{i+1}: {turn.get('answer')}\nScore: {turn.get('score')}/10\n\n"
            
        system_prompt = (
            "You are an expert, professional technical interviewer. Your goal is to conduct a structured, interactive, dynamic technical interview.\n"
            "Generate ONE technical question for the candidate based on their profile and the desired difficulty.\n"
            "Avoid repeating questions that have already been asked or are highly similar to them.\n"
            "The question must be highly focused on practical technical scenarios matching the role and skills.\n\n"
            "Format your output as a strict JSON object with the following keys:\n"
            "{{\n"
            '  "question": "Your generated question here",\n'
            '  "difficulty": "easy, medium, or hard",\n'
            '  "rationale": "Brief reason why this question is appropriate"\n'
            "}}"
                    )
        
        user_prompt = (
            f"Candidate Profile:\n"
            f"- Role: {role}\n"
            f"- Experience: {experience}\n"
            f"- Skills: {skillset}\n\n"
            f"Desired Difficulty: {difficulty}\n\n"
            f"Conversation History:\n{history_str or 'None - This is the start of the interview.'}\n\n"
            f"Generate the next question:"
        )
        
        try:
            # Setup standard ChatPrompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt)
            ])
            
            # Invoke LLM
            chain = prompt | self.llm
            response = chain.invoke({})
            
            content = response.content.strip()
            
            # Remove markdown JSON fences if present
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
                
            data = json.loads(content)
            question = data.get("question", "Could you tell me about your experience working with technical challenges?")
            difficulty_output = data.get("difficulty", difficulty)
            
            return {
                "current_question": question,
                "current_difficulty": difficulty_output
            }
        except Exception as e:
            print(f"[Question Generator Agent Error] {e}")
            # Fallback direct mock generation if parsing fails
            fallback_questions = {
                "easy": f"What are the core concepts and lifecycle methods you use when building applications in {role}?",
                "medium": f"How do you handle state management, async data fetching, and race conditions in a {role} project?",
                "hard": f"Can you walk me through the system architecture, performance optimization, and scale challenges you faced in your previous {role} role?"
            }
            return {
                "current_question": fallback_questions.get(difficulty, fallback_questions["easy"]),
                "current_difficulty": difficulty
            }
