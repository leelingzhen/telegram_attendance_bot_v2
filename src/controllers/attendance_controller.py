import logging
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import List

from models.enums import AccessCategory
from models.models import Attendance, Event
from models.responses import EventAttendance


class AttendanceControlling(ABC):
    @abstractmethod
    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[EventAttendance]:
        """Get upcoming events for a specific userID"""
        pass

    @abstractmethod
    async def update_attendance(self, events: List[EventAttendance]):
        """update attendance for a list of events"""
        pass

class AttendanceController(AttendanceControlling):

    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[EventAttendance]:
        raise NotImplementedError

    async def update_attendance(self, events: List[EventAttendance]) -> List[Event]:
        raise NotImplementedError

class FakeAttendanceController(AttendanceControlling):

    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[EventAttendance]:
        return [
            EventAttendance(
                event=Event(
                    id=123,
                    title="test event",
                    description="test description",
                    start=datetime.now(),
                    end=datetime.now() + timedelta(hours=2),
                    attendance_deadline=None,
                    is_accountable=True,
                    access_category=AccessCategory.PUBLIC,
                ),
                attendance=Attendance(
                    event_id=123,
                    user_id=user_id,
                    status=True,
                    reason="test reason",
                )
            )
        ]

    async def update_attendance(self, events: List[EventAttendance]):
        logging.debug("fake update attendance called")
