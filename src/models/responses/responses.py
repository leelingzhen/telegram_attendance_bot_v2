from typing import List, Optional

from pydantic import BaseModel

from models.enums import AccessCategory
from models.models import Attendance, Event

class AttendanceResponse(BaseModel):
    status: Optional[bool]
    reason: Optional[str]

class UserAttendance(BaseModel):
    name: str
    telegram_user: Optional[str]
    gender: str
    access: AccessCategory
    attendance: AttendanceResponse

    @property
    def telegram_handle(self) -> str:
        if self.telegram_user:
            clean = self.telegram_user.lstrip("@")
            return f"@{clean}"
        return "(not yet set on telegram)"

class UserAttendanceResponse(BaseModel):
    male: List[UserAttendance]
    female: List[UserAttendance]
    absent: List[UserAttendance]
    unindicated: List[UserAttendance]


class EventAttendance(BaseModel):
    event: Event
    attendance: Attendance
