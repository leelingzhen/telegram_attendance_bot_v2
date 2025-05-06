from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum

class AccessCategory(str, Enum):
    PUBLIC = "public"
    GUEST = "guest"
    MEMBER = "member"
    ADMIN = "admin"

class User(BaseModel):
    id: int
    telegram_id: int
    name: str
    username: Optional[str] = None
    access_category: AccessCategory = AccessCategory.PUBLIC
    created_at: datetime
    updated_at: datetime

class Event(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    date: datetime
    access_category: AccessCategory
    created_at: datetime
    updated_at: datetime

class AttendanceStatus(str, Enum):
    ATTENDING = "attending"
    NOT_ATTENDING = "not_attending"
    MAYBE = "maybe"

class Attendance(BaseModel):
    id: int
    user_id: int
    event_id: int
    status: AttendanceStatus
    reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime 