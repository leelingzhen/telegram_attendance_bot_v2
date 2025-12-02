from abc import ABC, abstractmethod
from datetime import date
from typing import List

from models.models import Event
from models.responses.responses import UserAttendanceResponse


class TeamAttendanceControlling(ABC):
    @abstractmethod
    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[Event]:
        pass

    @abstractmethod
    async def retrieve_team_attendance(self, event_id: int) -> UserAttendanceResponse:
        pass

class TeamAttendanceController(TeamAttendanceControlling):
    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[Event]:
        raise NotImplementedError

    async def retrieve_team_attendance(self, event_id: int) -> UserAttendanceResponse:
        raise NotImplementedError

class FakeTeamAttendanceController(TeamAttendanceControlling):
    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[Event]:
        # return a sample event here
        return []

    async def retrieve_team_attendance(self, event_id: int) -> UserAttendanceResponse:
        # return a sample response here
        return UserAttendanceResponse()