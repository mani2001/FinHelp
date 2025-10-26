# src/finhelp/models.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6,max_length=72)
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=72)


class User(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime


class ChatMessage(BaseModel):
    role: str
    content: str


class EarningsContext(BaseModel):
    ticker: str
    quarter: str
    year: str
    summary: str
    transcript_content: str = ""  # Can be truncated


class ChatSession(BaseModel):
    id: str
    user_id: str
    messages: List[ChatMessage]
    earnings_contexts: List[EarningsContext] = []
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SaveChatRequest(BaseModel):
    messages: List[ChatMessage]
    earnings_contexts: List[EarningsContext] = []