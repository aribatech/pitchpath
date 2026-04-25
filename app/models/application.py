from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

ApplicationStatus = Literal["applied", "no_reply", "interview", "rejected", "offer"]


class Application(BaseModel):
    profile_id: str
    match_id: str        # references matches._id
    company: str
    role: str
    status: ApplicationStatus = "applied"
    linkedin_message: str = ""
    whatsapp_message: str = ""
    notes: str = ""
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ApplicationCreate(BaseModel):
    profile_id: str
    match_id: str
    company: str
    role: str
    notes: str = ""


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: Optional[str] = None
