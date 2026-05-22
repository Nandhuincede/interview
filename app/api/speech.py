from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.services import stt, tts

router = APIRouter(tags=["Speech Services"])

class TranscribeRequest(BaseModel):
    audio_base64: str
    text_fallback: Optional[str] = None

class TranscribeResponse(BaseModel):
    transcription: str

class GenerateSpeechRequest(BaseModel):
    text: str

class GenerateSpeechResponse(BaseModel):
    audio_base64: str

@router.post("/stt/transcribe", response_model=TranscribeResponse)
def transcribe_speech(payload: TranscribeRequest):
    """
    Transcribes candidate's microphone audio (base64-encoded) to text.
    """
    if not payload.audio_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audio_base64 is required"
        )
        
    text = stt.transcribe_audio_base64(payload.audio_base64, payload.text_fallback)
    return TranscribeResponse(transcription=text)

@router.post("/tts/generate", response_model=GenerateSpeechResponse)
def generate_speech(payload: GenerateSpeechRequest):
    """
    Synthesizes a generated question text into base64 encoded audio speech.
    """
    if not payload.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text is required"
        )
        
    audio = tts.text_to_speech_base64(payload.text)
    return GenerateSpeechResponse(audio_base64=audio)
