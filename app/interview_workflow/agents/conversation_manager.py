# app/interview_workflow/agents/conversation_manager.py
from typing import List, Dict, Any


class ConversationManagerAgent:
    def update_history(
        self,
        history:    List[Dict[str, Any]],
        question:   str,
        answer:     str,
        score:      float,
        difficulty: str,
        bloom_level: str,      # ← now a required param; was missing in v1
        evaluation: dict,
    ) -> List[Dict[str, Any]]:
        """
        Appends the latest Q&A turn to the conversation history.
        bloom_level is stored per-turn so the report generator and
        question generator can read it without recomputing it.
        """
        new_turn = {
            "question":   question,
            "answer":     answer,
            "score":      score,
            "difficulty": difficulty,
            "bloom_level": bloom_level,
            "evaluation": evaluation,
        }
        return list(history) + [new_turn]
