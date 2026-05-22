from typing import List, Dict, Any

class ConversationManagerAgent:
    def update_history(
        self, 
        history: List[Dict[str, Any]], 
        question: str, 
        answer: str, 
        score: float, 
        difficulty: str, 
        evaluation: dict
    ) -> List[Dict[str, Any]]:
        """
        Updates the conversation history with the latest question, answer, difficulty, and score breakdown.
        """
        new_turn = {
            "question": question,
            "answer": answer,
            "score": score,
            "difficulty": difficulty,
            "evaluation": evaluation
        }
        
        # Append to history and return
        updated_history = list(history)
        updated_history.append(new_turn)
        return updated_history
