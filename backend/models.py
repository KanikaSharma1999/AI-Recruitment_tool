from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Optional[str] = "hr"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    company_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    name: str
    role: str


class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    required_skills: Optional[List[str]] = []
    required_experience_years: Optional[float] = 0.0
    location: Optional[str] = ""


class StatusUpdate(BaseModel):
    status: str  # applied | screening | shortlisted | interview_scheduled | interview_completed | offered | hired | rejected


class InterviewSchedule(BaseModel):
    date: str          # ISO date string
    time: str          # e.g. "10:30"
    mode: str          # "online" | "offline"
    location: Optional[str] = ""
    notes: Optional[str] = ""


class NoteCreate(BaseModel):
    text: str


class EmailSettings(BaseModel):
    provider: str  # gmail, brevo, sendgrid, outlook, custom
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_email: str
    app_name: Optional[str] = "AI Hiring Platform"


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    company_name: Optional[str] = ""

