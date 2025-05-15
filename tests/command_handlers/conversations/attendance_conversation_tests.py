import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, date
from telegram import Update, User, Message, CallbackQuery
from telegram.ext import ConversationHandler
from src.command_handlers.conversations.attendance_conversation import MarkAttendanceConversation
from src.models.models import AccessCategory, Event, User as ModelUser
from tests.providers.mock_attendance_provider import MockAttendanceProvider

def make_mock_event(event_id=1, title="Test Event"):
    return Event(
        id=event_id,
        title=title,
        start=datetime.now(),
        end=datetime.now(),
        access_category=AccessCategory.MEMBER,
    )

def make_mock_user(user_id=123, access_category=AccessCategory.MEMBER):
    return ModelUser(
        id=user_id,
        telegram_user="@test_telegram_id",
        name="Test User",
        username="testuser",
        access_category=access_category,
        gender="male"
    )

@pytest.fixture
def mock_provider():
    provider = MockAttendanceProvider()
    return provider

@pytest.fixture
def conversation(mock_provider):
    return MarkAttendanceConversation(provider=mock_provider)

@pytest.mark.asyncio
async def test_attendance_happy_flow(conversation, mock_provider):
    # Step 1: User sends /attendance, is registered, and there are events
    user = make_mock_user()
    mock_provider.add_user(user)
    mock_event = make_mock_event()
    mock_provider.add_event(mock_event)

    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User, id=user.id)
    update.effective_user.access_category = user.access_category
    update.message = AsyncMock(spec=Message)

    result = await conversation.attendance_command(update, MagicMock())
    update.message.reply_text.assert_awaited()
    assert result == 1  # CHOOSING_EVENT

    # Step 2: User selects an event
    update2 = MagicMock(spec=Update)
    update2.callback_query = AsyncMock(spec=CallbackQuery)
    update2.callback_query.data = str(mock_event.id)
    update2.callback_query.edit_message_text = AsyncMock()
    update2.callback_query.answer = AsyncMock()
    context = MagicMock()
    context.user_data = {}

    result2 = await conversation.event_selected(update2, context)
    update2.callback_query.edit_message_text.assert_awaited()
    assert context.user_data["selected_event"] == mock_event
    assert result2 == 2  # INDICATING_ATTENDANCE
