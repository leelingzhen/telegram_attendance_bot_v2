from abc import ABC, abstractmethod
from typing import List

from models.enums import AccessCategory
from models.models import User


class ManageAccessControlling(ABC):
    """Interface for managing user access levels."""

    @abstractmethod
    def retrieve_access_categories(self) -> List[AccessCategory]:
        """Return available access categories that can be managed."""
        raise NotImplementedError

    @abstractmethod
    def retrieve_users(self, category: AccessCategory) -> List[User]:
        """Return users within the selected access category."""
        raise NotImplementedError

    @abstractmethod
    def set_access(self, user: User, access: AccessCategory) -> None:
        """Persist the updated access for the provided user."""
        raise NotImplementedError


class ManageAccessController(ManageAccessControlling):
    def retrieve_access_categories(self) -> List[AccessCategory]:
        raise NotImplementedError

    def retrieve_users(self, category: AccessCategory) -> List[User]:
        raise NotImplementedError

    def set_access(self, user: User, access: AccessCategory) -> None:
        raise NotImplementedError


class FakeManageAccessController(ManageAccessControlling):
    def __init__(self):
        self.available_categories = [
            AccessCategory.PUBLIC,
            AccessCategory.GUEST,
            AccessCategory.MEMBER,
            AccessCategory.ADMIN,
        ]
        self.sample_users = [
            User(id=1, name="Alice Admin", access_category=AccessCategory.ADMIN),
            User(id=2, name="Bob Member", access_category=AccessCategory.MEMBER),
            User(id=3, name="Charlie Guest", access_category=AccessCategory.GUEST),
            User(id=4, name="Paula Public", access_category=AccessCategory.PUBLIC),
        ]
        self.last_set_access: tuple[int, AccessCategory] | None = None

    def retrieve_access_categories(self) -> List[AccessCategory]:
        return self.available_categories

    def retrieve_users(self, category: AccessCategory) -> List[User]:
        return [user for user in self.sample_users if user.access_category == category]

    def set_access(self, user: User, access: AccessCategory) -> None:
        for existing in self.sample_users:
            if existing.id == user.id:
                existing.access_category = access
                break
        self.last_set_access = (user.id, access)
