from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Union

class ReportResponse(BaseModel):
    report_id: str
    session_id: str
    interview_id: str
    overall_score: float
    technical_score: float
    communication_score: float
    recommendation: str
    strengths: Union[List[str], Any]
    improvements: Union[List[str], Any]
    question_wise_evaluation: Union[List[Dict[str, Any]], Any]
    ai_feedback: str
    created_at: datetime

    class Config:
        from_attributes = True
