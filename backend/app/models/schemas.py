from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    action_taken: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    follow_up_needed: bool = False
    suggested_questions: List[str] = Field(default_factory=list)


class VoiceRequest(BaseModel):
    audio_data: Optional[str] = None
    text: Optional[str] = None


class CommandResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    credentials: Dict[str, Any]


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    credentials: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
