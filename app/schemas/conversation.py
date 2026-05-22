from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ConversationResponse(BaseModel):
    conversation_id: str
    session_id: str
    interview_id: str
    speaker_type: str # "candidate" or "interviewer"
    message_text: str
    audio_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
