import asyncio
from typing import Any, Dict, List

import pytest
from telegram import MessageEntity
from telegram.error import (
    ChatMigrated,
    Forbidden,
    NetworkError,
    RetryAfter,
)

from models.models import User
from providers.messaging_provider import FakeMessagingProvider
from services.MessagingService import MessageSendError, MessagingService
from utils.markup_converter import MessageMarkupConverter


class FakeBot:
    def __init__(self, script: Dict[int, List[Any]]):
        # script maps chat_id -> list of outcomes (Exception to raise, anything else to mean success)
        self.script = {chat_id: list(actions) for chat_id, actions in script.items()}
        self.sent = []

    async def send_message(
        self,
        chat_id: int,
        message: str,
        reply_markup=None,
        parse_mode=None,
        entities=None,
    ):
        actions = self.script.get(chat_id, [])
        if not actions:
            self.sent.append((chat_id, message, parse_mode, entities))
            return "ok"

        action = actions.pop(0) if len(actions) > 1 else actions[0]
        if isinstance(action, Exception):
            raise action

        self.sent.append((chat_id, message, parse_mode, entities))
        return "ok"


@pytest.fixture
def fast_sleep(monkeypatch):
    async def _sleep(duration: float):
        return None

    monkeypatch.setattr(asyncio, "sleep", _sleep)


@pytest.fixture(autouse=True)
def force_ptb_timedelta(monkeypatch):
    monkeypatch.setenv("PTB_TIMEDELTA", "1")


@pytest.mark.asyncio
async def test_send_messages_all_success(monkeypatch):
    users = [User(id=1, name="A"), User(id=2, name="B")]
    service = MessagingService("token")
    service.bot = FakeBot({})

    result = await service.send_messages(users, "hello")

    assert result is None
    assert set(service.bot.sent) == {
        (1, "hello", None, None),
        (2, "hello", None, None),
    }


@pytest.mark.asyncio
async def test_send_messages_collects_failures(monkeypatch, fast_sleep):
    users = [User(id=1, name="A"), User(id=2, name="B")]
    service = MessagingService("token", max_retries=1)
    service.bot = FakeBot({2: [Forbidden("blocked user")]})

    with pytest.raises(MessageSendError) as exc:
        await service.send_messages(users, "hello")
    assert exc.value.failed_users == [users[1]]
    assert service.bot.sent == [(1, "hello", None, None)]


@pytest.mark.asyncio
async def test_send_messages_retries_after_and_succeeds(monkeypatch, fast_sleep):
    users = [User(id=1, name="A")]
    service = MessagingService("token", max_retries=2)
    service.bot = FakeBot({1: [RetryAfter(0), "ok"]})

    await service.send_messages(users, "hi")

    assert service.bot.sent[-1][:2] == (1, "hi")


@pytest.mark.asyncio
async def test_send_messages_network_error_exhausts_retries(monkeypatch, fast_sleep):
    users = [User(id=1, name="A")]
    service = MessagingService("token", max_retries=1, retry_backoff_seconds=0)
    service.bot = FakeBot({1: [NetworkError("flaky")]})

    with pytest.raises(MessageSendError) as exc:
        await service.send_messages(users, "hi")
    assert exc.value.failed_users == users
    assert service.bot.sent == []


@pytest.mark.asyncio
async def test_send_messages_handles_chat_migrated(monkeypatch, fast_sleep):
    users = [User(id=1, name="A")]
    service = MessagingService("token", max_retries=2)
    service.bot = FakeBot({1: [ChatMigrated(new_chat_id=99), "ok"]})

    await service.send_messages(users, "hi")

    assert service.bot.sent == [(99, "hi", None, None)]


@pytest.mark.asyncio
async def test_send_messages_runs_concurrently():
    users = [User(id=1, name="A"), User(id=2, name="B"), User(id=3, name="C")]
    service = MessagingService("token", max_concurrent_sends=10)

    lock = asyncio.Lock()
    active = 0
    max_active = 0

    async def send_message(self, chat_id: int, message: str, reply_markup=None, parse_mode=None, entities=None):
        nonlocal active, max_active
        async with lock:
            active += 1
            max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        async with lock:
            active -= 1
        return "ok"

    service.bot = type("Bot", (), {"send_message": send_message})()

    await service.send_messages(users, "hello")

    assert max_active > 1


@pytest.mark.asyncio
async def test_send_messages_reports_progress(monkeypatch):
    users = [User(id=1, name="A"), User(id=2, name="B"), User(id=3, name="C")]
    service = MessagingService("token", max_concurrent_sends=3)

    # Stagger completions to ensure progress follows completion order.
    async def send_message(self, chat_id: int, message: str, reply_markup=None, parse_mode=None, entities=None):
        await asyncio.sleep(0.01 * chat_id)
        return "ok"

    service.bot = type("Bot", (), {"send_message": send_message})()

    progress_updates: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int):
        progress_updates.append((done, total))

    await service.send_messages(users, "hello", on_progress=on_progress)

    assert progress_updates[-1] == (3, 3)
    # Ensure progress increments, even if order of completions varies.
    assert all(update[0] == idx + 1 for idx, update in enumerate(progress_updates))


@pytest.mark.asyncio
async def test_fake_provider_passes_progress_callback(monkeypatch):
    service = MessagingService("token", max_concurrent_sends=5)

    async def send_message(self, chat_id: int, message: str, reply_markup=None, parse_mode=None, entities=None):
        await asyncio.sleep(0.001)
        return "ok"

    service.bot = type("Bot", (), {"send_message": send_message})()

    provider = FakeMessagingProvider(service)
    provider._test_users = [User(id=1, name="A"), User(id=2, name="B"), User(id=3, name="C")]

    updates: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int):
        updates.append((done, total))

    failed = await provider.send_announcement("alice", "hi", on_progress=on_progress)

    assert failed == []
    assert updates[-1] == (3, 3)


def test_html_to_entities_and_back():
    html = 'Hello <b>World</b> <i>Italic</i> <a href="https://example.com">link</a>'
    text, entities = MessageMarkupConverter.html_to_entities(html)

    assert text == "Hello World Italic link"
    assert {e.type for e in entities} == {
        MessageEntity.BOLD,
        MessageEntity.ITALIC,
        MessageEntity.TEXT_LINK,
    }

    round_trip = MessageMarkupConverter.entities_to_html(text, entities)
    # Order of tags may vary slightly but text and tags should appear
    assert "<b>World</b>" in round_trip
    assert "<i>Italic</i>" in round_trip
    assert '<a href="https://example.com">link</a>' in round_trip
