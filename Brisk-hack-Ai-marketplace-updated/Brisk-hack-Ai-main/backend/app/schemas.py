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


class MarketplaceListingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    category: str
    description: str = ""
    location: str = ""
    price: float = Field(default=0, ge=0)
    price_unit: str = ""
    contact_email: Optional[EmailStr] = None


class MarketplaceBookingCreate(BaseModel):
    event_id: Optional[int] = None
    quantity: int = Field(default=1, ge=1, le=100000)
    booking_date: str = ""
    note: str = Field(default="", max_length=1000)


class MarketplaceBookingStatusUpdate(BaseModel):
    status: str
