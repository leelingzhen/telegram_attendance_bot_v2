from typing import List, Optional

from pydantic import BaseModel

from models.models import Attendance, AccessCategory

class AttendanceResponse(BaseModel):
    status: Optional[bool]
    reason: Optional[str]

class UserAttendance(BaseModel):
    name: str
    telegram_user: str
    gender: str
    access: AccessCategory
    attendance: AttendanceResponse

class UserAttendanceResponse(BaseModel):
    male: List[UserAttendance]
    female: List[UserAttendance]
    absent: List[UserAttendance]
    unindicated: List[UserAttendance]