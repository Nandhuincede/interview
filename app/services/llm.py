import os
import json
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel
from app.config import settings

# Attempt imports, catch errors if packages aren't fully installed yet
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
    from langchain_core.language_models.chat_models import BaseChatModel
except ImportError:
    # Minimal mock interfaces if imports are still completing
    class BaseChatModel:
        pass
    class ChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass

class MockLLMResponse:
    """Mock response that mimics LangChain's LLM message response."""
    def __init__(self, content: str):
        self.content = content
        self.additional_kwargs = {}

class MockChatModel:
    """Mock chat LLM that generates excellent dynamic questions and reflections."""
    def __init__(self):
        self.questions_pool = {
            "React Developer": {
                "easy": [
                    "What is the difference between state and props in React?",
                    "What are React Hooks and why do we use them?",
                    "Can you explain the purpose of key prop in React lists?",
                ],
                "medium": [
                    "How does the virtual DOM work in React, and how does it optimize performance?",
                    "Explain the difference between useEffect, useLayoutEffect, and how to prevent memory leaks in useEffect.",
                    "What is Redux, and how does it compare to Context API for global state management?",
                ],
                "hard": [
                    "Explain React Concurrent Mode, Server Components, and how Suspense works under the hood.",
                    "How do you optimize a large React application experiencing slow renders, and what tools would you use?",
                    "Explain the reconciliation algorithm (Fiber) in React in detail.",
                ]
            },
            "Python Engineer": {
                "easy": [
                    "What is the difference between a list and a tuple in Python?",
                    "What are decorators in Python and how do you write a simple one?",
                    "What is a dictionary comprehension and can you give an example?",
                ],
                "medium": [
                    "What is the difference between multiprocessing and multithreading in Python, and how does the GIL affect them?",
                    "Explain the difference between __new__ and __init__ in Python classes.",
                    "How does Python's garbage collection and memory management work under the hood?",
                ],
                "hard": [
                    "Explain metaclasses in Python and when you would use them.",
                    "How do you implement a custom context manager using both classes and generators?",
                    "Explain how asyncio works under the hood, including event loops, coroutines, and futures.",
                ]
            },
            "Generic Developer": {
                "easy": [
                    "What is Git and how do you resolve a merge conflict?",
                    "What is the difference between HTTP GET and POST requests?",
                    "What is clean code and why is it important?",
                ],
                "medium": [
                    "What are RESTful API design principles and how do you design a scalable API endpoint?",
                    "What is a database index and how does it speed up queries, and are there any downsides?",
                    "What is CI/CD and what are the main benefits of using it in a team environment?",
                ],
                "hard": [
                    "Explain the CAP theorem and how you would choose a database based on its requirements.",
                    "How do you design a highly available, distributed rate limiter?",
                    "Explain the SOLID design principles in detail and give a real-world refactoring example.",
                ]
            }
        }

    def invoke(self, messages: List[Any], response_format: Optional[Any] = None) -> MockLLMResponse:
        # Parse prompt to determine which agent is calling and what data is provided
        prompt_text = ""
        for m in messages:
            if hasattr(m, 'content'):
                prompt_text += m.content + "\n"
            elif isinstance(m, dict) and 'content' in m:
                prompt_text += m['content'] + "\n"
            else:
                prompt_text += str(m) + "\n"

        # 1. QUESTION GENERATOR AGENT
        if "generate" in prompt_text.lower() and "question" in prompt_text.lower():
            # Extract role and difficulty
            role = "Generic Developer"

            if "react developer" in prompt_text.lower():
             role = "React Developer"

            elif (
                "python engineer" in prompt_text.lower()
                or "python developer" in prompt_text.lower()
            ):
                role = "Python Engineer"

            elif "generic developer" in prompt_text.lower():
              role = "Generic Developer"
            
            difficulty = "easy"
            if "medium" in prompt_text.lower():
                difficulty = "medium"
            elif "hard" in prompt_text.lower():
                difficulty = "hard"
            
            # Select question
            questions = self.questions_pool.get(role, self.questions_pool["Generic Developer"])[difficulty]
            # Select based on simple hash or length
            import random
            selected_question = random.choice(questions)
            
            # If structured format is requested (like JSON or Pydantic output)
            if response_format:
                return MockLLMResponse(json.dumps({
                    "question": selected_question,
                    "difficulty": difficulty,
                    "rationale": f"Generating a {difficulty} question for a {role} candidate to evaluate core concepts."
                }))
            return MockLLMResponse(selected_question)

        # 2. REFLECTION AGENT (Answer Evaluator)
        elif "evaluate" in prompt_text.lower() or "reflection" in prompt_text.lower() or "score" in prompt_text.lower():
            # Simulating scoring based on response quality
            # Let's check answer content length/keywords
            score = 7.5
            if "i don't know" in prompt_text.lower() or "no idea" in prompt_text.lower():
                score = 3.0
            elif len(prompt_text) > 150:
                score = 8.5
            
            eval_data = {
                "technical_accuracy": score + 0.5 if score < 9 else 9.5,
                "communication_quality": score - 0.5 if score > 5 else 4.0,
                "confidence": score,
                "completeness": score - 0.2 if score > 5 else 4.5,
                "relevance": score + 0.2 if score < 9.5 else 9.8,
                "overall_score": score,
                "feedback": "The candidate explained the core concepts well, showing good practical understanding. Some edge cases could be explored in more detail."
            }
            if response_format:
                return MockLLMResponse(json.dumps(eval_data))
            return MockLLMResponse(json.dumps(eval_data))

        # 3. REPORT GENERATOR AGENT
        elif "report" in prompt_text.lower() or "evaluation report" in prompt_text.lower():
            report_data = {
                "overall_score": 8.0,
                "technical_score": 8.2,
                "communication_score": 7.8,
                "recommendation": "Selected",
                "strengths": ["Strong understanding of JavaScript closures and lifecycle hooks", "Excellent communication skills and structured reasoning", "Comfortable discussing optimization and web performance patterns"],
                "improvements": ["Deepen understanding of React Fiber reconciliation details", "Improve explanation of React Concurrent Mode features"],
                "ai_feedback": "The candidate has demonstrated strong technical competency and matches the senior frontend role requirements. Communication is highly clear and concise. Ready for onsite team round.",
                "question_wise_evaluation": [
                    {"question": "What is state in React?", "answer": "State is a built-in object that stores property values that belong to the component.", "score": 8.0, "feedback": "Accurate basic explanation."},
                    {"question": "How does virtual DOM work?", "answer": "It is a lightweight copy of the real DOM. React updates the virtual DOM first and then syncs with the real DOM.", "score": 8.5, "feedback": "Strong explanation of reconciliation."}
                ]
            }
            if response_format:
                return MockLLMResponse(json.dumps(report_data))
            return MockLLMResponse(json.dumps(report_data))

        # Generic default
        return MockLLMResponse("Interesting response. Could you elaborate on that?")

def get_llm(temperature: float = 0.7) -> Any:
    """
    Returns an appropriate LLM instance based on available API keys.
    If no keys are found, returns a highly robust MockChatModel so the program runs out-of-the-box.
    """
    # 1. Groq Key (Primary)
    if settings.GROQ_API_KEY:
        try:
            return ChatOpenAI(
                model="llama-3.3-70b-versatile",
                openai_api_key=settings.GROQ_API_KEY,
                openai_api_base="https://api.groq.com/openai/v1",
                temperature=temperature
            )
        except Exception:
            pass

    # 2. Google Gemini Key (Secondary)
    if settings.GEMINI_API_KEY:
        try:
            # We can use ChatGoogleGenerativeAI if imported
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature
            )
        except ImportError:
            pass
            
    # Fallback to extremely powerful MockChatModel
    print("[LLM Service] API key not found or libraries not installed. Operating in Premium Demo Mock LLM Mode.")
    return MockChatModel()
