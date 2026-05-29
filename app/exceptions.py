class CandidateNotFoundError(Exception):
    """Raised when a candidate_id does not exist in the database."""
    def __init__(self, candidate_id: str):
        self.candidate_id = candidate_id
        super().__init__(f"Candidate with ID {candidate_id} not found")