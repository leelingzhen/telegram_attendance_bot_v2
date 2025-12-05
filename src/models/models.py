from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from models.enums import AccessCategory, Gender

class User(BaseModel):
    id: int
    telegram_user: Optional[str] = None
    name: str
    access_category: AccessCategory = AccessCategory.PUBLIC
    username: Optional[str] = None
    gender: Optional[Gender] = None

    @property
    def telegram_handle(self) -> str:
        """
        Display-ready Telegram handle with leading @.

        Returns a placeholder string when no handle is available.
        """
        if self.telegram_user:
            clean = self.telegram_user.lstrip("@")
            return f"@{clean}"
        return "(not yet set on telegram)"

class Event(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    access_category: AccessCategory

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
