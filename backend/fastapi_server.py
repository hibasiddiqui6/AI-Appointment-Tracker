from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from livekit import api
from config import Config
from models import TokenRequest, TokenResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="LiveKit Token API",
    description="Issue LiveKit access tokens; no UI or streaming endpoints",
    version="1.0.0",
)

# CORS: allow local frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
config = Config()

@app.get("/")
async def root():
    return {
        "message": "LiveKit Token API",
        "endpoints": [
            "POST /generate-token",
            "GET /health",
            "GET /config",
            "GET /docs",
        ],
    }

@app.post("/generate-token", response_model=TokenResponse)
async def generate_token(request: TokenRequest):
    """Generate a LiveKit access token for joining a room."""
    if not config.LIVEKIT_URL or not config.LIVEKIT_API_KEY or not config.LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="Missing LIVEKIT_URL/API_KEY/API_SECRET")

    try:
        participant_identity = request.participant_identity or f"user-{request.participant_name.lower().replace(' ', '-')}"

        # Build token
        token = api.AccessToken(api_key=config.LIVEKIT_API_KEY, api_secret=config.LIVEKIT_API_SECRET)
        token.with_identity(participant_identity)
        token.with_name(request.participant_name)
        token.with_metadata(request.participant_name)

        grant = api.VideoGrants(
            room_join=True,
            room=request.room_name,
            can_publish=request.can_publish,
            can_subscribe=request.can_subscribe,
            can_publish_data=request.can_publish_data,
            can_update_own_metadata=True,
            hidden=False,
            recorder=False,
        )
        token.with_grants(grant)
        token.with_ttl(timedelta(hours=24))

        jwt_token = token.to_jwt()
        expires_at = datetime.now() + timedelta(hours=24)

        return TokenResponse(
            token=jwt_token,
            room_name=request.room_name,
            participant_identity=participant_identity,
            livekit_url=config.LIVEKIT_URL,
            expires_at=expires_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {e}")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "livekit_configured": bool(config.LIVEKIT_URL and config.LIVEKIT_API_KEY and config.LIVEKIT_API_SECRET),
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/config")
async def cfg():
    return {
        "livekit_url": config.LIVEKIT_URL,
        "livekit_configured": bool(config.LIVEKIT_URL and config.LIVEKIT_API_KEY and config.LIVEKIT_API_SECRET),
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
