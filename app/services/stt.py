import os
import base64
import tempfile
import requests
from app.config import settings
from typing import Optional
def transcribe_audio_base64(audio_base64: str, text_fallback: Optional[str] = None) -> str:
    """
    Decodes a base64 audio string, saves it to a temporary file, and sends it to
    an STT service (like Sarvam AI) to transcribe it into text.
    If no keys are present, it falls back to the text_fallback or a mock answer.
    """
    if not audio_base64:
        return text_fallback or "No speech captured."
        
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(audio_base64)
        
        # Save to temp file (browser sends WAV or WEBM usually)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            temp_path = fp.name
            fp.write(audio_data)
            
        transcription = ""
        
        # 1. Try Sarvam AI if API key is present
        if settings.SARVAM_API_KEY:
            try:
                url = "https://api.sarvam.ai/speech-to-text"
                headers = {"api-subscription-key": settings.SARVAM_API_KEY}
                with open(temp_path, "rb") as audio_file:
                    files = {"file": ("audio.wav", audio_file, "audio/wav")}
                    data = {"model": "saarika:v2.5", "language_code":"en-IN"}
                    response = requests.post(url, headers=headers, files=files, data=data)
                    
                if response.status_code == 200:
                    transcription = response.json().get("transcript", "")
                    print(f"[STT Service] Sarvam AI Transcribed: {transcription}")
            except Exception as e:
                print(f"[STT Service] Sarvam AI failed: {e}")
                
        # Clean up temp file
        os.remove(temp_path)
        
        # 3. Fallback logic
        if not transcription:
            # If transcription still empty, return empty string to indicate missing user input
            return ""
                
        return transcription
        
    except Exception as e:
        print(f"[STT Error] Error transcribing audio: {e}")
        return text_fallback or "Error processing voice recording."
