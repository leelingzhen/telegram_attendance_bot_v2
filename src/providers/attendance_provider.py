from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional
from models.models import User, Event, Attendance, AttendanceStatus, AccessCategory

class AttendanceProvider(ABC):
    """
    Abstract provider for attendance marking functionality.
    
    This provider encapsulates all the data access requirements for marking attendance,
    making the conversation handler more focused and easier to test.
    """
    
    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by their Telegram ID"""
        pass
    
    @abstractmethod
    async def get_events(self, from_date: date, access_category: AccessCategory) -> List[Event]:
        """Get upcoming events for a specific access category"""
        pass
    
    @abstractmethod
    async def get_event(self, event_id: int) -> Optional[Event]:
        """Get event by ID"""
        pass
    
    @abstractmethod
    async def get_attendance(self, event_id: int, user_id: int) -> Optional[Attendance]:
        """Get existing attendance record for a user at an event"""
        pass
    
    @abstractmethod
    async def update_attendance(self, attendance: Attendance) -> Attendance:
        """Create or update an attendance record"""
        pass 