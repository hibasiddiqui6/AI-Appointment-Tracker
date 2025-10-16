import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LiveKit Configuration
    LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.com")
    LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
    
    # AI Configuration (Google Gemini - FREE)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Speech-to-Text Configuration
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    
    # n8n Webhook
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")