# app/interview_workflow/agents/difficulty_controller.py


class DifficultyControllerAgent:
    def adjust_difficulty(self, last_overall_score: float, current_difficulty: str) -> str:
        """
        Decides whether the next question should be easy, medium, or hard
        based on the candidate's last answer evaluation score (0–10 scale).

        >= 7.5 → ramp up
        <  5.0 → ramp down
        5.0–7.4 → maintain
        """
        current = current_difficulty.lower()

        if last_overall_score >= 7.5:
            return {"easy": "medium", "medium": "hard"}.get(current, "hard")

        if last_overall_score < 5.0:
            return {"hard": "medium", "medium": "easy"}.get(current, "easy")

        return current
