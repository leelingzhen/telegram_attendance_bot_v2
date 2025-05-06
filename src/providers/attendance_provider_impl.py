from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from models.models import User, Event, Attendance, AttendanceStatus, AccessCategory
from providers.attendance_provider import AttendanceProvider

class AttendanceProviderImpl(AttendanceProvider):
    """
    Implementation of AttendanceProvider that provides mock data.
    
    This implementation maintains in-memory state for attendance-related operations.
    It's designed to be used during development and testing before a real service
    implementation is available.
    """
    
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.events: Dict[int, Event] = {}
        self.attendances: Dict[tuple[int, int], Attendance] = {}  # (event_id, user_id) -> Attendance
        self._setup_mock_data()
    
    def _setup_mock_data(self):
        """Setup initial mock data"""
        # Create mock users
        self.users[1] = User(
            id=1,
            telegram_id=123456789,
            name="Test User",
            username="testuser",
            access_category=AccessCategory.MEMBER,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create mock events
        self.events[1] = Event(
            id=1,
            title="Training Session",
            description="Regular training session",
            date=datetime.now() + timedelta(days=1),
            access_category=AccessCategory.MEMBER,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create mock attendance
        self.attendances[(1, 1)] = Attendance(
            id=1,
            user_id=1,
            event_id=1,
            status=AttendanceStatus.ATTENDING,
            reason="Will be there",
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
    
    async def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)
    
    async def get_events(self, from_date: date, access_category: AccessCategory) -> List[Event]:
        events = [
            event for event in self.events.values()
            if event.date.date() >= from_date
            and event.access_category == access_category
        ]
        return sorted(events, key=lambda e: e.date)
    
    async def get_event(self, event_id: int) -> Optional[Event]:
        return self.events.get(event_id)
    
    async def get_attendance(self, event_id: int, user_id: int) -> Optional[Attendance]:
        return self.attendances.get((event_id, user_id))
    
    async def update_attendance(self, attendance: Attendance) -> Attendance:
        self.attendances[(attendance.event_id, attendance.user_id)] = attendance
        return attendance 