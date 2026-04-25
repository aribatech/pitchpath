from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Experience(BaseModel):
    title: str
    company: str
    duration: str
    description: str = ""


class Education(BaseModel):
    degree: str
    institution: str
    years: str


class Profile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = []
    experience: list[Experience] = []
    education: Optional[Education] = None
    summary: str = ""
    keywords: list[str] = []
    raw_text: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
