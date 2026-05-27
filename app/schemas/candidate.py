from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class CandidateBase(BaseModel):
    name: str = Field(..., example="Alice Smith")
    email: EmailStr = Field(..., example="alice@example.com")
    phone: str = Field(..., example="+1234567890")
    qualification: str = Field(..., example="B.Tech in Computer Science")
    experience: str = Field(..., example="3 years")
    role: str = Field(..., example="React Developer")
    skillset: str = Field(..., example="React, Redux, JavaScript, TailwindCSS")

class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    candidate_id: str
    created_at: datetime

    class Config:
        from_attributes = True
