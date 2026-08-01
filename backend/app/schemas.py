from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class Signup(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "participant"
    skills: str = ""


class Login(BaseModel):
    email: EmailStr
    password: str


class EventCreate(BaseModel):
    name: str
    description: str = ""
    format: str = "in-person"
    team_size: int = 4
    tracks: str = "Open Innovation"
    start_date: str = ""
    end_date: str = ""


class TeamCreate(BaseModel):
    name: str
    event_id: int
    track: str = "Open Innovation"


class SubmissionCreate(BaseModel):
    team_id: int
    title: str
    description: str = ""
    github_url: str = ""
    demo_url: str = ""


class ScoreUpdate(BaseModel):
    score: float = Field(ge=0, le=100)
