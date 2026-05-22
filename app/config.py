import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Base Configuration
    PROJECT_NAME: str = "AI-Powered Voice Interview System"
    API_V1_STR: str = "/api"
    
    # Server configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Database
    # Default to a local SQLite database for ease of use
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./interview.db")
    
    # LLM Providers
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # STT & TTS Integrations
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    
    # Interview Configuration
    MAX_QUESTIONS: int = int(os.getenv("MAX_QUESTIONS", 5))

settings = Settings()
