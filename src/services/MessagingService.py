import asyncio
import logging
from abc import ABC
from typing import List, Optional, Sequence

from telegram import Bot, InlineKeyboardMarkup, MessageEntity
from telegram.constants import ParseMode
from telegram.error import (
    BadRequest,
    ChatMigrated,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)

from models.models import User
from utils.markup_converter import MessageMarkupConverter


class MessageSendError(Exception):
    """Raised when one or more messages fail to send."""

    def __init__(self, failed_users: List[User]):
        super().__init__(f"Failed to send messages to {len(failed_users)} user(s)")
        self.failed_users = failed_users


class MessagingServicing(ABC):
    async def send_messages(
        self,
        to_users: List[User],
        message: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        *,
        parse_mode: Optional[str] = None,
        entities: Optional[Sequence[MessageEntity]] = None,
    ) -> None:
        """
        Send a message to each user with optional formatting (parse_mode or entities).

        Raises MessageSendError when one or more sends fail.
        """
        pass


class MessagingService(MessagingServicing):

    def __init__(
        self,
        token: str,
        *,
        logger: Optional[logging.Logger] = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.5,
        max_concurrent_sends: Optional[int] = None,
    ):
        self.bot = Bot(token=token)
        self.logger = logger or logging.getLogger(__name__)
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.max_concurrent_sends = max_concurrent_sends

    async def send_messages(
        self,
        to_users: List[User],
        message: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        *,
        parse_mode: Optional[str] = None,
        entities: Optional[Sequence[MessageEntity]] = None,
    ) -> None:
        """
        Attempt to send a message to each user, retrying transient failures.

        Sends are issued concurrently (optionally bounded by max_concurrent_sends).
        Raises MessageSendError if any send ultimately fails.
        """
        semaphore = (
            asyncio.Semaphore(self.max_concurrent_sends)
            if self.max_concurrent_sends and self.max_concurrent_sends > 0
            else None
        )

        tasks = [
            asyncio.create_task(
                self._send_with_retry(
                    user=user,
                    message=message,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    entities=entities,
                    semaphore=semaphore,
                )
            )
            for user in to_users
        ]

        results = await asyncio.gather(*tasks)
        failed = [user for user in results if user]

        if failed:
            raise MessageSendError(failed)

    async def _send_with_retry(
        self,
        user: User,
        message: str,
        reply_markup: Optional[InlineKeyboardMarkup],
        parse_mode: Optional[str],
        entities: Optional[Sequence[MessageEntity]],
        semaphore: Optional[asyncio.Semaphore],
    ) -> Optional[User]:
        """
        Send a single user's message with retry/backoff. Returns the user on failure, None on success.
        """
        chat_id = user.id
        attempts = 0

        while True:
            try:
                if semaphore:
                    async with semaphore:
                        await self.bot.send_message(
                            chat_id,
                            message,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode,
                            entities=entities,
                        )
                else:
                    await self.bot.send_message(
                        chat_id,
                        message,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                        entities=entities,
                    )
                return None
            except ChatMigrated as exc:
                chat_id = exc.new_chat_id or chat_id
                attempts += 1
            except RetryAfter as exc:
                attempts += 1
                delay = getattr(exc, "retry_after", self.retry_backoff_seconds)
                if hasattr(delay, "total_seconds"):
                    delay = delay.total_seconds()
                await asyncio.sleep(delay)
            except (TimedOut, NetworkError):
                attempts += 1
                backoff = self.retry_backoff_seconds * attempts
                await asyncio.sleep(backoff)
            except (Forbidden, BadRequest, TelegramError) as exc:
                self.logger.warning(
                    "Permanent failure sending message to user %s: %s",
                    chat_id,
                    exc,
                )
                return user

            if attempts > self.max_retries:
                self.logger.error("Exceeded retries sending message to user %s", chat_id)
                return user


    @staticmethod
    def html_payload(html_text: str) -> tuple[str, Optional[str], Optional[Sequence[MessageEntity]]]:
        """
        Convenience helper to prepare payload for send_message.
        Returns (text, parse_mode, entities)
        """
        text, entities = MessageMarkupConverter.html_to_entities(html_text)
        return text, None, entities

    @staticmethod
    def html_payload_with_parse_mode(html_text: str) -> tuple[str, str, None]:
        """
        Prepare payload using Telegram's HTML parse mode instead of entities.
        Returns (text, parse_mode, entities)
        """
        return html_text, ParseMode.HTML, None
