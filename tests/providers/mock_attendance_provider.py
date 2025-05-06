from datetime import date, datetime
from typing import List, Optional, Dict
from models.models import User, Event, Attendance, AttendanceStatus, AccessCategory
from providers.attendance_provider import AttendanceProvider

class MockAttendanceProvider(AttendanceProvider):
    """
    Mock implementation of AttendanceProvider for testing.
    
    This provider maintains in-memory state for testing purposes.
    It allows setting up test data and verifying the behavior of
    the attendance marking conversation.
    """
    
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.events: Dict[int, Event] = {}
        self.attendances: Dict[tuple[int, int], Attendance] = {}  # (event_id, user_id) -> Attendance
    
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
        return [
            event for event in self.events.values()
            if event.date >= from_date and event.access_category == access_category
        ]
    
    async def get_event(self, event_id: int) -> Optional[Event]:
        return self.events.get(event_id)
    
    async def get_attendance(self, event_id: int, user_id: int) -> Optional[Attendance]:
        return self.attendances.get((event_id, user_id))
    
    async def update_attendance(self, attendance: Attendance) -> Attendance:
        self.attendances[(attendance.event_id, attendance.user_id)] = attendance
        return attendance 