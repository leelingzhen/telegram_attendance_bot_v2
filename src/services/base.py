from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional
from src.models.models import User, Event, Attendance, AttendanceStatus, AccessCategory

class BaseService(ABC):
    """
    Abstract base service that defines the interface for all data operations.
    
    This service is responsible for:
    1. User management
    2. Event management
    3. Attendance management
    """
    
    # User Operations
    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by their Telegram ID"""
        pass
    
    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create a new user"""
        pass
    
    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update an existing user"""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: int) -> bool:
        """Delete a user"""
        pass
    
    # Event Operations
    @abstractmethod
    async def get_event(self, event_id: int) -> Optional[Event]:
        """Get event by ID"""
        pass
    
    @abstractmethod
    async def get_events(
        self,
        from_date: date,
        to_date: Optional[date] = None,
        access_category: Optional[AccessCategory] = None
    ) -> List[Event]:
        """Get events within a date range and optional access category"""
        pass
    
    @abstractmethod
    async def create_event(self, event: Event) -> Event:
        """Create a new event"""
        pass
    
    @abstractmethod
    async def update_event(self, event: Event) -> Event:
        """Update an existing event"""
        pass
    
    @abstractmethod
    async def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        pass
    
    # Attendance Operations
    @abstractmethod
    async def get_attendance(self, event_id: int, user_id: int) -> Optional[Attendance]:
        """Get attendance record for a user at an event"""
        pass
    
    @abstractmethod
    async def get_event_attendance(
        self,
        event_id: int,
        status: Optional[AttendanceStatus] = None
    ) -> List[Attendance]:
        """Get all attendance records for an event, optionally filtered by status"""
        pass
    
    @abstractmethod
    async def get_user_attendance(
        self,
        user_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[AttendanceStatus] = None
    ) -> List[Attendance]:
        """Get all attendance records for a user, optionally filtered by date range and status"""
        pass
    
    @abstractmethod
    async def update_attendance(self, attendance: Attendance) -> Attendance:
        """Create or update an attendance record"""
        pass
    
    @abstractmethod
    async def delete_attendance(self, event_id: int, user_id: int) -> bool:
        """Delete an attendance record"""
        pass 