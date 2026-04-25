from datetime import datetime
from pydantic import BaseModel, Field


class Job(BaseModel):
    job_id: str = ""     # from JSearch external API
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    apply_url: str = ""


class Match(BaseModel):
    profile_id: str      # references profiles._id
    job_id: str
    job_title: str
    company: str
    location: str = ""
    match_score: int = 0
    score_reasoning: str = ""
    skill_gap: list[str] = []
    job_description: str = ""
    apply_url: str = ""
    matched_at: datetime = Field(default_factory=datetime.utcnow)
