import os
import json
import random
import re
from typing import Optional, List, Any
from app.config import settings

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.language_models.chat_models import BaseChatModel
except ImportError:
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
    """
    Mock LLM for running without an API key.

    Key fixes vs original:
    - Singleton instance (via _mock_llm_instance) so _asked persists across calls.
    - Reads already-asked questions from the conversation history in the prompt,
      so deduplication works even if the instance is recreated.
    - Returns bloom_level in the question-generator JSON response.
    - Reflection agent response includes bloom_level field.
    """

    BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

    def __init__(self):
        self._asked: set = set()

        self.questions_pool = {
            "React Developer": {
                "easy": [
                    "What is the difference between state and props in React?",
                    "What are React Hooks and why do we use them?",
                    "Can you explain the purpose of the key prop in React lists?",
                    "What is JSX and how does Babel transform it?",
                ],
                "medium": [
                    "How does the virtual DOM work in React, and how does it optimize performance?",
                    "Explain the difference between useEffect and useLayoutEffect, and how to prevent memory leaks.",
                    "What is Redux, and how does it compare to Context API for global state management?",
                    "How does React's reconciliation algorithm decide what to re-render?",
                ],
                "hard": [
                    "Explain React Concurrent Mode, Server Components, and how Suspense works under the hood.",
                    "How do you optimize a large React application experiencing slow renders?",
                    "Explain the Fiber reconciliation algorithm in React in detail.",
                    "How would you implement a custom render pipeline or micro-frontend architecture in React?",
                ],
            },
            "Python Engineer": {
                "easy": [
                    "What is the difference between a list and a tuple in Python?",
                    "What are decorators in Python and how do you write a simple one?",
                    "What is a dictionary comprehension and can you give an example?",
                    "How does Python handle variable scoping (LEGB rule)?",
                ],
                "medium": [
                    "What is the difference between multiprocessing and multithreading in Python, and how does the GIL affect them?",
                    "Explain the difference between __new__ and __init__ in Python classes.",
                    "How does Python's garbage collection and memory management work under the hood?",
                    "What are generators and how do they differ from regular functions?",
                ],
                "hard": [
                    "Explain metaclasses in Python and when you would use them.",
                    "How do you implement a custom context manager using both classes and generators?",
                    "Explain how asyncio works under the hood, including event loops, coroutines, and futures.",
                    "How would you design a plugin system in Python using abstract base classes and entry points?",
                ],
            },
            "Generic Developer": {
                "easy": [
                    "What is Git and how do you resolve a merge conflict?",
                    "What is the difference between HTTP GET and POST requests?",
                    "What is clean code and why is it important?",
                    "What is the difference between SQL and NoSQL databases?",
                ],
                "medium": [
                    "What are RESTful API design principles and how do you design a scalable API endpoint?",
                    "What is a database index and how does it speed up queries? Are there any downsides?",
                    "What is CI/CD and what are the main benefits of using it in a team environment?",
                    "Explain the difference between horizontal and vertical scaling.",
                ],
                "hard": [
                    "Explain the CAP theorem and how you would choose a database based on its requirements.",
                    "How do you design a highly available, distributed rate limiter?",
                    "Explain the SOLID design principles in detail and give a real-world refactoring example.",
                    "How would you design a system to handle 1 million concurrent WebSocket connections?",
                ],
            },
        }

    def _extract_bloom_level(self, prompt_text: str) -> str:
        """Read the bloom level the QuestionGeneratorAgent injected into the prompt."""
        match = re.search(
            r"Target Bloom Level:\s*(REMEMBER|UNDERSTAND|APPLY|ANALYZE|EVALUATE|CREATE)",
            prompt_text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).lower()
        return "remember"

    def _extract_already_asked(self, prompt_text: str) -> set:
        """
        Parse questions already listed in the conversation history section of the
        prompt so we never repeat them even across fresh MockChatModel instances.
        """
        asked = set()
        for match in re.finditer(r"Q\d+:\s*(.+)", prompt_text):
            asked.add(match.group(1).strip())
        return asked

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> MockLLMResponse:
        # Normalize input — LangChain may pass a list of messages or a dict
        if isinstance(input, dict):
            messages = input.get("messages", [])
        elif isinstance(input, list):
            messages = input
        else:
            messages = [input]

        prompt_text = ""
        for m in messages:
            if hasattr(m, "content"):
                prompt_text += m.content + "\n"
            elif isinstance(m, dict) and "content" in m:
                prompt_text += m["content"] + "\n"
            else:
                prompt_text += str(m) + "\n"

        # 1. QUESTION GENERATOR 
        if "generate" in prompt_text.lower() and "question" in prompt_text.lower():
            role = "Generic Developer"
            if "react developer" in prompt_text.lower():
                role = "React Developer"
            elif "python engineer" in prompt_text.lower() or "python developer" in prompt_text.lower():
                role = "Python Engineer"

            difficulty = "easy"
            if "desired difficulty: medium" in prompt_text.lower():
                difficulty = "medium"
            elif "desired difficulty: hard" in prompt_text.lower():
                difficulty = "hard"

            bloom_level = self._extract_bloom_level(prompt_text)

            # Merge instance memory with history parsed from the prompt
            already_asked = self._asked | self._extract_already_asked(prompt_text)

            questions = self.questions_pool.get(role, self.questions_pool["Generic Developer"])[difficulty]
            remaining = [q for q in questions if q not in already_asked]

            if not remaining:
                # Pool exhausted for this difficulty — try other difficulties
                for d in ("easy", "medium", "hard"):
                    remaining = [
                        q for q in self.questions_pool.get(role, self.questions_pool["Generic Developer"])[d]
                        if q not in already_asked
                    ]
                    if remaining:
                        difficulty = d
                        break

            if not remaining:
                # All questions exhausted — reset and start over
                self._asked.clear()
                remaining = questions

            selected = random.choice(remaining)
            self._asked.add(selected)

            return MockLLMResponse(json.dumps({
                "question": selected,
                "bloom_level": bloom_level,
                "difficulty": difficulty,
                "rationale": (
                    f"Mock: {difficulty} question for {role} "
                    f"at Bloom level '{bloom_level}'."
                ),
            }))

        # 2. REFLECTION / EVALUATION 
        elif (
            "evaluate" in prompt_text.lower()
            or "reflection" in prompt_text.lower()
            or "score" in prompt_text.lower()
        ):
            bloom_level = self._extract_bloom_level(prompt_text)

            score = 7.5
            if "i don't know" in prompt_text.lower() or "no idea" in prompt_text.lower():
                score = 3.0
            elif len(prompt_text) > 300:
                score = 8.5

            return MockLLMResponse(json.dumps({
                "technical_accuracy":    min(9.5, score + 0.5),
                "communication_quality": max(4.0, score - 0.5),
                "confidence":            score,
                "completeness":          max(4.5, score - 0.2),
                "relevance":             min(9.8, score + 0.2),
                "bloom_alignment":       score,
                "overall_score":         score,
                "feedback": (
                    "The candidate demonstrated understanding of the core concepts. "
                    "More depth and specific examples would strengthen the answer."
                ),
                "bloom_level": bloom_level,
            }))

        # 3. REPORT GENERATOR 
        elif "report" in prompt_text.lower() or "evaluation report" in prompt_text.lower():
            return MockLLMResponse(json.dumps({
                "overall_score":       8.0,
                "technical_score":     8.2,
                "communication_score": 7.8,
                "recommendation":      "Selected",
                "strengths": [
                    "Solid understanding of core technical concepts",
                    "Clear and structured communication",
                ],
                "improvements": [
                    "Deepen knowledge at higher Bloom levels (Evaluate / Create)",
                    "Provide more concrete real-world examples",
                ],
                "bloom_taxonomy_analysis": {
                    "remember": 8.5,
                    "understand": 8.0,
                    "apply": 7.5,
                },
                "cognitive_strengths": ["Strong recall and conceptual understanding"],
                "ai_feedback": (
                    "The candidate completed the interview with consistent performance. "
                    "Recommended for the next round."
                ),
            }))

        # Default 
        return MockLLMResponse("Interesting response. Could you elaborate on that?")
    def __or__(self, other: Any) -> Any:
        """Support llm | other syntax."""
        from langchain_core.runnables import RunnableLambda
        return RunnableLambda(self.invoke) | other

    def __ror__(self, other: Any) -> Any:
        """Support prompt | llm syntax."""
        from langchain_core.runnables import RunnableLambda
        return other | RunnableLambda(self.invoke)

# Module-level singleton so _asked state is never lost between get_llm() calls
_mock_llm_instance: Optional[MockChatModel] = None


def get_llm(temperature: float = 0.7) -> Any:
    """
    Returns the configured LLM. Falls back to a singleton MockChatModel
    so question history is preserved across the entire server lifetime.
    """
    # 1. Groq (primary)
    if settings.GROQ_API_KEY:
        try:
            return ChatOpenAI(
                model="llama-3.3-70b-versatile",
                openai_api_key=settings.GROQ_API_KEY,
                openai_api_base="https://api.groq.com/openai/v1",
                temperature=temperature,
            )
        except Exception:
            pass

    # 2. Google Gemini (secondary)
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature,
            )
        except ImportError:
            pass

    # 3. Singleton mock
    global _mock_llm_instance
    if _mock_llm_instance is None:
        _mock_llm_instance = MockChatModel()
        print("[LLM Service] No API key found — using MockChatModel (demo mode).")
    return _mock_llm_instance