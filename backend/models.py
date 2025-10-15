from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AppointmentData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    appointment_reason: Optional[str] = None
    call_duration: Optional[float] = None
    transcript: Optional[str] = None
    
    def to_json(self) -> dict:
        """Convert to JSON-serializable dict for webhook"""
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "appointment_date": self.appointment_date,
            "appointment_time": self.appointment_time,
            "appointment_reason": self.appointment_reason,
            "call_duration": self.call_duration,
            "transcript": self.transcript,
            "extracted_at": datetime.now().isoformat()
        }

# FastAPI API Models
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    participant_identity: Optional[str] = None
    can_publish: bool = True
    can_subscribe: bool = True
    can_publish_data: bool = True

class TokenResponse(BaseModel):
    token: str
    room_name: str
    participant_identity: str
    livekit_url: str
    expires_at: str

