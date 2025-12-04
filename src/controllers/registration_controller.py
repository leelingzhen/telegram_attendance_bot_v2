from abc import ABC, abstractmethod
from typing import Dict, Optional

from telegram import User as TelegramUser

from models.enums import UserRecordStatus
from models.models import Gender, User


class RegistrationControlling(ABC):

    @abstractmethod
    async def check_user_record(self, telegram_user: TelegramUser) -> UserRecordStatus:
        """
        Determine the status of a user's record and return the appropriate `UserRecordStatus`.

        This function inspects the stored user record associated with `telegram_id` and compares it
        against the current Telegram username.

        Return values:
            - UserRecordStatus.NEW:
                Returned when **no existing record** is found *or* when a record exists but is marked
                as public/unclaimed (i.e., it is treated as effectively new).

            - UserRecordStatus.UPDATED:
                Returned when the record exists but the stored username differs from the provided
                `telegram_user`, indicating that the user has updated their Telegram username.

            - UserRecordStatus.EXISTS:
                Returned when a matching record is found and **no changes** are detected (ID and
                username match the stored values).

        Args:
            telegram_user (TelegramUser): The Telegram user object containing id and username.

        Returns:
            UserRecordStatus: Enum describing whether the user is new, updated, or unchanged.
    """
        pass

    @abstractmethod
    async def check_name_conflict(self, name: str) -> bool:
        """Return True if the provided name is already in use."""
        pass

    @abstractmethod
    async def submit_user_registration(self, user: User):
        """Submit the newly created user for registration."""
        pass

    @abstractmethod
    async def create_new_user(self, telegram_id: int, telegram_user: Optional[str], name: str, gender: Gender) -> User:
        """Create a new user object from the provided details."""
        pass


class RegistrationController(RegistrationControlling):

    async def check_user_record(self, telegram_user: TelegramUser) -> UserRecordStatus:
        raise NotImplementedError

    async def check_name_conflict(self, name: str) -> bool:
        raise NotImplementedError

    async def submit_user_registration(self, user: User):
        raise NotImplementedError

    async def create_new_user(self, telegram_id: int, telegram_user: Optional[str], name: str, gender: Gender) -> User:
        raise NotImplementedError


class FakeRegistrationController(RegistrationControlling):
    """Lightweight fake controller with in-memory sample data."""

    def __init__(self):
        self._existing_users: Dict[int, User] = {
            999: User(id=999, telegram_user="registered_user", name="Registered User", gender=Gender.MALE),
        }
        self._conflicting_names = {"Registered User", "Taken Name"}
        self.created_users: Dict[int, User] = {}

    async def check_name_conflict(self, name: str) -> bool:
        return name in self._conflicting_names

    async def submit_user_registration(self, user: User):
        # Mimic persisting the user by storing it locally
        self._existing_users[user.id] = user
        self.created_users[user.id] = user

    async def create_new_user(self, telegram_id: int, telegram_user: Optional[str], name: str, gender: Gender) -> User:
        return User(
            id=telegram_id,
            telegram_user=telegram_user,
            name=name,
            gender=gender,
        )

    async def check_user_record(self, telegram_user: TelegramUser) -> UserRecordStatus:
        telegram_id = telegram_user.id
        existing = self._existing_users.get(telegram_id)
        if not existing:
            return UserRecordStatus.NEW

        if telegram_user.username and existing.telegram_user != telegram_user.username:
            existing.telegram_user = telegram_user.username
            self._existing_users[telegram_id] = existing
            return UserRecordStatus.UPDATED

        return UserRecordStatus.EXISTS
