import os
import base64
import tempfile
from gtts import gTTS
from app.config import settings

def text_to_speech_base64(text: str) -> str:
    """
    Converts text to speech audio and returns it as a base64 encoded string.
    Uses gTTS (Google Text-to-Speech) which is free and doesn't require keys,
    making it perfect for offline/free standard execution.
    """
    if not text:
        return ""
        
    try:

        # Standard gTTS implementation (100% free and reliable)
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
            
        tts.save(temp_path)
        
        # Read the file and convert to base64
        with open(temp_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")
            
        # Clean up temp file
        os.remove(temp_path)
        return audio_base64
        
    except Exception as e:
        print(f"[TTS Error] Error generating speech: {e}")
        return ""
