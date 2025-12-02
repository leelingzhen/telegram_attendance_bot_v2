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
    telegram_user: str
    name: str
    username: Optional[str] = None
    access_category: AccessCategory = AccessCategory.PUBLIC
    gender: str

class Event(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    access_category: AccessCategory

class AttendanceStatus(str, Enum):
    ATTENDING = "attending"
    NOT_ATTENDING = "not_attending"
    MAYBE = "maybe"

class Attendance(BaseModel):
    user_id: int = None
    event_id: int = None
    status: Optional[bool] = None
    reason: Optional[str] = ""

class Attendance(Attendance):
    def clean_and_set_reason(self, reason: str):
        clean_reason = self.remove_html_tags(text=reason)
        self.reason = clean_reason
        return

    @staticmethod
    def remove_html_tags(text: str) -> str:
        html_tags = {
            "&": "&amp",
            '"': "&quote",
            "'": "&#39",
            "<": "&lt",
            ">": "&gt",
        }
        for tag in html_tags:
            text = text.replace(tag, html_tags[tag])
        return text

class EventAttendance(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: str
    isAccountable: bool
    attendance: Attendance