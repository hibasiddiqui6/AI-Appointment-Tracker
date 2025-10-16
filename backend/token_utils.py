from datetime import timedelta, datetime
from livekit import api
from config import Config

config = Config()

def build_livekit_token(room_name: str, identity: str, name: str = None,
                        can_publish: bool = False, can_subscribe: bool = True,
                        can_publish_data: bool = False, ttl_hours: int = 24):
    """Build a LiveKit JWT token and return (token_jwt, expires_at_iso).

    This centralizes token creation so callers (FastAPI or background listener)
    can request consistent grants and TTL.
    """
    if not (config.LIVEKIT_API_KEY and config.LIVEKIT_API_SECRET):
        raise RuntimeError("LiveKit API key/secret not configured")

    token = api.AccessToken(api_key=config.LIVEKIT_API_KEY, api_secret=config.LIVEKIT_API_SECRET)
    token.with_identity(identity)
    if name:
        token.with_name(name)
        token.with_metadata(name)

    grant = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=can_publish,
        can_subscribe=can_subscribe,
        can_publish_data=can_publish_data,
        can_update_own_metadata=True,
    )
    token.with_grants(grant)
    token.with_ttl(timedelta(hours=ttl_hours))

    jwt = token.to_jwt()
    expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
    return jwt, expires_at
