class DifficultyControllerAgent:
    def adjust_difficulty(self, last_overall_score: float, current_difficulty: str) -> str:
        """
        Decides whether the next question should be easy, medium, or hard
        based on the candidate's last answer evaluation score.
        """
        current_difficulty = current_difficulty.lower()
        
        # High performance (>= 7.5): ramp up difficulty
        if last_overall_score >= 7.5:
            if current_difficulty == "easy":
                return "medium"
            elif current_difficulty == "medium":
                return "hard"
            else:
                return "hard"
                
        # Low performance (< 5.0): lower the difficulty to assist the candidate
        elif last_overall_score < 5.0:
            if current_difficulty == "hard":
                return "medium"
            elif current_difficulty == "medium":
                return "easy"
            else:
                return "easy"
                
        # Average performance (5.0 to 7.5): maintain current difficulty
        else:
            return current_difficulty
