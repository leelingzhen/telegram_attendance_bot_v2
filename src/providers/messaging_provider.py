from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from models.enums import AccessCategory
from models.models import User, Event
from services.MessagingService import MessagingServicing, MessageSendError
from telegram import MessageEntity


class MessagingProviding(ABC):

    @abstractmethod
    async def retrieve_events(self, from_date: datetime) -> List[Event]:
        pass

    @abstractmethod
    async def send_reminders(self, event: Event) -> List[User]:
        """Send reminders to users who have not indicated attendance for the given event. Returns users that failed to receive the message."""
        pass

    @abstractmethod
    async def send_announcement(self, from_user: str, message: str, for_event: Optional[Event] = None, *, parse_mode: Optional[str] = None, entities=None) -> List[User]:
        """Broadcast an announcement from the sender; target a specific event if provided, otherwise all users with at least member access. Returns users that failed to receive the message."""
        pass

    @abstractmethod
    async def notify(self, user: User, new_access: AccessCategory) -> List[User]:
        """Send a status-upgrade notification template to the specified user. Returns users that failed to receive the message."""
        pass

    @abstractmethod
    async def notify_users(self, of_access: AccessCategory) -> List[User]:
        """Notify all users in the access group that someone has registered for the Telegram bot. Returns users that failed to receive the message."""
        pass

class MessagingProvider(MessagingProviding):

    async def retrieve_events(self, from_date: datetime) -> List[Event]:
        raise NotImplementedError

    async def send_reminders(self, event: Event) -> List[User]:
        """
        TODO: first get users who have not indicated for the specified event
        then send a template message to remind the user to indicate attendance
        """
        raise NotImplementedError

    async def send_announcement(self, from_user: str, message: str, for_event: Optional[Event] = None, *, parse_mode: Optional[str] = None, entities=None):
        """
        TODO: send announcement to everyone if for_event is empty
        send announcement to everyone who is attending or has not indicated for the specified event
        """
        raise NotImplementedError

    async def notify(self, user: User, new_access: AccessCategory):
        raise NotImplementedError

    async def notify_users(self, of_access: AccessCategory):
        raise NotImplementedError

class FakeMessagingProvider(MessagingProviding):

    def __init__(self, messaging_service: MessagingServicing):
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
        self.messaging_service = messaging_service
        self._test_users = [
            User(id=89637568, name="", telegram_user="leelingzhen"),
            User(id=89637568, name="", telegram_user="leelingzhen"),
            User(id=89637568, name="", telegram_user="leelingzhen"),
            User(id=89637568, name="", telegram_user="leelingzhen"),
            User(id=89637568, name="", telegram_user="leelingzhen"),
            User(id=89637568, name="", telegram_user="leelingzhen"),
        ]

    async def retrieve_events(self, from_date: datetime) -> List[Event]:
        return self.sample_events

    async def send_reminders(self, event: Event):
        """
        for this fake service, send a reminder message of this template
        Hey you there! YES YOU THERE 🫵🏻 it seems you have not indicated your attendance 🧐 for 05-Oct-25, Sunday (Field Training).
        where you tell the date, day and title of the event. remember to use localisation keys for the message template
        """
        date_str = event.start.strftime("%d-%b-%y, %A")
        message = (
            "Hey you there! YES YOU THERE 🫵🏻 it seems you have not indicated your attendance 🧐 "
            f"for {date_str} ({event.title})."
        )
        try:
            await self.messaging_service.send_messages(to_users=self._test_users, message=message)
            return []
        except MessageSendError as exc:
            return exc.failed_users


    async def send_announcement(self, from_user: str, message: str, for_event: Optional[Event] = None, *, parse_mode: Optional[str] = None, entities=None) -> List[User]:
        """
        for here i want to put the telegram user's at the end of the message as sort of like a sign off, just a simple -@telegram_user will do
        after that, if for_event is not optional, i want add a Message for Field Training on 22-Jun, Sun @ 11:00AM at the end of the message in italics
        """

        signoff = f"-@{from_user.lstrip('@')}"
        body = f"{message}\n\n{signoff}"

        # Start with any incoming entities
        base_entities = list(entities) if entities else []

        if for_event:
            event_date = for_event.start.strftime("%d-%b, %a @ %I:%M%p")
            italic_text = f"Message for {for_event.title} on {event_date}"
            offset = len(body) + 2  # account for the \n\n before the event text
            body = f"{body}\n\n{italic_text}"
            base_entities.append(
                MessageEntity(
                    type=MessageEntity.ITALIC,
                    offset=offset,
                    length=len(italic_text),
                )
            )

        # Telegram forbids parse_mode together with entities; prefer entities
        if base_entities:
            parse_mode = None

        try:
            await self.messaging_service.send_messages(
                to_users=self._test_users,
                message=body,
                parse_mode=parse_mode,
                entities=base_entities or None,
            )
            return []
        except MessageSendError as exc:
            return exc.failed_users

    async def notify(self, user: User, new_access: AccessCategory) -> List[User]:
        """
        here i just want to send a message to the user of "your access status has been changed to {new_access}"
        """
        message = f"your access status has been changed to {new_access.name}"
        try:
            await self.messaging_service.send_messages(to_users=[user], message=message)
            return []
        except MessageSendError as exc:
            return exc.failed_users

    async def notify_users(self, of_access: AccessCategory) -> List[User]:
        """"""
        message = f"A new user has registered for the Telegram bot (access group: {of_access.name})."
        try:
            await self.messaging_service.send_messages(to_users=self._test_users, message=message)
            return []
        except MessageSendError as exc:
            return exc.failed_users
