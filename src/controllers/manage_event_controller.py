from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

from models.enums import AccessCategory
from models.models import Event

class ManageEventControlling(ABC):

    @abstractmethod
    def retrieve_events(self, from_date: datetime) -> List[Event]:
        pass

    @abstractmethod
    def create_new_event(self, start_datetime: datetime) -> Event:
        pass

    @abstractmethod
    def update_event(self, event: Event) -> None:
        """upsert an event"""
        pass

class ManageEventController(ManageEventControlling):

    def retrieve_events(self, from_date: datetime) -> List[Event]:
        raise NotImplementedError()

    def create_new_event(self, start_datetime: datetime) -> Event:
        raise NotImplementedError()

    def update_event(self, event: Event) -> None:
        raise NotImplementedError()

class FakeManageEventController(ManageEventControlling):

    def __init__(self):
        self.sample_events = [
            Event(
            id=1,
            title="Field Training",
            description="Saturday training session",
            start=datetime(2025, 10, 11, 13, 30),
            end=datetime(2025, 10, 11, 15, 0),
            attendance_deadline=None,
            is_accountable=True,
            access_category=AccessCategory.GUEST,
        ),
            Event(
                id=2,
                title="Birthday party",
                description="Saturday training session",
                start=datetime(2025, 10, 12, 13, 30),
                end=datetime(2025, 10, 12, 16, 0),
                attendance_deadline=None,
                is_accountable=True,
                access_category=AccessCategory.GUEST,
            ),
        ]

    def retrieve_events(self, from_date: datetime) -> List[Event]:
        return self.sample_events

    def create_new_event(self, start_datetime: datetime) -> Event:
        default_end_datetime = start_datetime + timedelta(hours=3)

        return Event(
            id=-1,  # idea here is that I want the backend to be responsible for this event creation
            title="Field Training",  # replace with localisation key
            start=start_datetime,
            end=default_end_datetime,
            is_accountable=False,
            access_category=AccessCategory.GUEST,
        )

    def update_event(self, event: Event) -> None:
        pass

