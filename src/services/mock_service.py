from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from services.base import BaseService
from models.models import User, Event, Attendance, AccessCategory, AttendanceStatus

class MockService(BaseService):
    """
    Mock implementation of BaseService for testing.
    
    This service maintains in-memory state for testing purposes.
    It allows setting up test data and verifying the behavior of
    the application without a real database.
    """
    
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.events: Dict[int, Event] = {}
        self.attendances: Dict[tuple[int, int], Attendance] = {}  # (event_id, user_id) -> Attendance
        self._setup_mock_data()
    
    def _setup_mock_data(self):
        # Create some mock users
        self.users[1] = User(
            id=1,
            telegram_id=123456789,
            name="Test User",
            username="testuser",
            access_category=AccessCategory.MEMBER,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create some mock events
        self.events[1] = Event(
            id=1,
            title="Training Session",
            description="Regular training session",
            date=datetime.now() + timedelta(days=1),
            access_category=AccessCategory.MEMBER,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def add_user(self, user: User) -> None:
        """Add a user to the mock database"""
        self.users[user.id] = user
    
    def add_event(self, event: Event) -> None:
        """Add an event to the mock database"""
        self.events[event.id] = event
    
    def add_attendance(self, attendance: Attendance) -> None:
        """Add an attendance record to the mock database"""
        self.attendances[(attendance.event_id, attendance.user_id)] = attendance
    
    # User Operations
    async def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)
    
    async def create_user(self, user: User) -> User:
        self.users[user.id] = user
        return user
    
    async def update_user(self, user: User) -> User:
        self.users[user.id] = user
        return user
    
    async def delete_user(self, user_id: int) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False
    
    # Event Operations
    async def get_event(self, event_id: int) -> Optional[Event]:
        return self.events.get(event_id)
    
    async def get_events(
        self,
        from_date: date,
        to_date: Optional[date] = None,
        access_category: Optional[AccessCategory] = None
    ) -> List[Event]:
        events = [
            event for event in self.events.values()
            if event.date.date() >= from_date
            and (to_date is None or event.date.date() <= to_date)
            and (access_category is None or event.access_category == access_category)
        ]
        return sorted(events, key=lambda e: e.date)
    
    async def create_event(self, event: Event) -> Event:
        self.events[event.id] = event
        return event
    
    async def update_event(self, event: Event) -> Event:
        self.events[event.id] = event
        return event
    
    async def delete_event(self, event_id: int) -> bool:
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
    
    # Attendance Operations
    async def get_attendance(self, event_id: int, user_id: int) -> Optional[Attendance]:
        return self.attendances.get((event_id, user_id))
    
    async def get_event_attendance(
        self,
        event_id: int,
        status: Optional[AttendanceStatus] = None
    ) -> List[Attendance]:
        attendances = [
            attendance for (e_id, _), attendance in self.attendances.items()
            if e_id == event_id
            and (status is None or attendance.status == status)
        ]
        return sorted(attendances, key=lambda a: a.created_at)
    
    async def get_user_attendance(
        self,
        user_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[AttendanceStatus] = None
    ) -> List[Attendance]:
        attendances = []
        for (_, u_id), attendance in self.attendances.items():
            if u_id == user_id:
                event = self.events.get(attendance.event_id)
                if event and (
                    (from_date is None or event.date.date() >= from_date)
                    and (to_date is None or event.date.date() <= to_date)
                    and (status is None or attendance.status == status)
                ):
                    attendances.append(attendance)
        return sorted(attendances, key=lambda a: a.created_at)
    
    async def update_attendance(self, attendance: Attendance) -> Attendance:
        self.attendances[(attendance.event_id, attendance.user_id)] = attendance
        return attendance
    
    async def delete_attendance(self, event_id: int, user_id: int) -> bool:
        key = (event_id, user_id)
        if key in self.attendances:
            del self.attendances[key]
            return True
        return False 