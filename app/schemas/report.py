from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Dict, Any
import json

class ReportResponse(BaseModel):
    report_id: str
    session_id: str
    interview_id: str
    overall_score: float
    technical_score: float
    communication_score: float
    recommendation: str
    strengths: List[str]                    
    improvements: List[str]                 
    question_wise_evaluation: List[Dict[str, Any]]  
    ai_feedback: str
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("strengths", "improvements", mode="before")
    @classmethod
    def parse_str_to_list(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator("question_wise_evaluation", mode="before")
    @classmethod
    def parse_str_to_dict_list(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v