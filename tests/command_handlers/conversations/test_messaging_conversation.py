from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message, Update, User as TgUser
from telegram.ext import CallbackContext, ConversationHandler

from command_handlers.conversations.messaging_conversation import (
    COLLECT_MESSAGE,
    CONFIRM_MESSAGE,
    SELECT_EVENT,
    MessagingConversation,
)
from models.enums import AccessCategory
from models.models import Event, User
from providers.messaging_provider import MessagingProviding


@pytest.fixture
def provider() -> AsyncMock:
    mock = AsyncMock(spec=MessagingProviding)
    mock.retrieve_events.return_value = []
    return mock


class TestMessagingConversation:
    @pytest.fixture(autouse=True)
    def _setup(self, provider):
        self.provider = provider
        self.conversation = MessagingConversation(messaging_provider=provider)

    @pytest.mark.asyncio
    async def test_send_reminders_no_events(self):
        update = MagicMock(spec=Update)
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.provider.retrieve_events.return_value = []

        result = await self.conversation.start_send_reminders(update, context)

        update.message.reply_text.assert_awaited_once()
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_send_reminders_flow(self):
        events = [
            Event(
                id=1,
                title="Event 1",
                description=None,
                start=datetime.now(),
                end=datetime.now(),
                attendance_deadline=None,
                is_accountable=True,
                access_category=AccessCategory.PUBLIC,
            )
        ]
        self.provider.retrieve_events.return_value = events

        update = MagicMock(spec=Update)
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        state = await self.conversation.start_send_reminders(update, context)
        assert state == SELECT_EVENT

        query = MagicMock(spec=CallbackQuery)
        query.data = "1"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update_cb = MagicMock(spec=Update)
        update_cb.callback_query = query

        # simulate failures
        failed_user = User(id=10, name="U", telegram_user="failed_user", access_category=AccessCategory.PUBLIC)
        self.provider.send_reminders.return_value = [failed_user]

        end_state = await self.conversation.event_selected(update_cb, context)

        self.provider.send_reminders.assert_awaited_once_with(events[0])
        query.edit_message_text.assert_awaited_once()
        args, kwargs = query.edit_message_text.await_args
        assert "failed_user" in args[0]
        assert end_state == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_announce_flow(self):
        update = MagicMock(spec=Update)
        update.message = AsyncMock(spec=Message)
        update.message.text = "Hello everyone"
        update.message.entities = []
        update.effective_user = MagicMock(spec=TgUser, id=5, username="john", full_name="John Doe")
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        start_state = await self.conversation.start_announce(update, context)
        assert start_state == COLLECT_MESSAGE

        next_state = await self.conversation.message_collected(update, context)
        assert next_state == CONFIRM_MESSAGE

        query = MagicMock(spec=CallbackQuery)
        query.data = "confirm"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update_cb = MagicMock(spec=Update)
        update_cb.callback_query = query
        update_cb.effective_user = update.effective_user

        end_state = await self.conversation.message_confirmed(update_cb, context)

        self.provider.send_announcement.assert_awaited_once()
        call = self.provider.send_announcement.await_args
        assert call.args[0] == "john"
        assert call.args[1] == "Hello everyone"
        assert call.kwargs.get("for_event") is None
        assert end_state == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_announce_event_flow(self):
        events = [
            Event(
                id=2,
                title="Event 2",
                description=None,
                start=datetime.now(),
                end=datetime.now(),
                attendance_deadline=None,
                is_accountable=True,
                access_category=AccessCategory.PUBLIC,
            )
        ]
        self.provider.retrieve_events.return_value = events

        update = MagicMock(spec=Update)
        update.message = AsyncMock(spec=Message)
        update.effective_user = MagicMock(spec=TgUser, id=8, username="mary", full_name="Mary Poppins")
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        state = await self.conversation.start_announce_event(update, context)
        assert state == SELECT_EVENT

        query = MagicMock(spec=CallbackQuery)
        query.data = "2"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update_cb = MagicMock(spec=Update)
        update_cb.callback_query = query

        msg_state = await self.conversation.event_selected(update_cb, context)
        assert msg_state == COLLECT_MESSAGE

        message_update = MagicMock(spec=Update)
        message_update.message = AsyncMock(spec=Message)
        message_update.message.text = "Event announcement"
        message_update.message.entities = []
        next_state = await self.conversation.message_collected(message_update, context)
        assert next_state == CONFIRM_MESSAGE

        confirm_query = MagicMock(spec=CallbackQuery)
        confirm_query.data = "confirm"
        confirm_query.answer = AsyncMock()
        confirm_query.edit_message_text = AsyncMock()
        confirm_update = MagicMock(spec=Update)
        confirm_update.callback_query = confirm_query
        confirm_update.effective_user = update.effective_user

        self.provider.send_announcement.return_value = [User(id=99, name="X", telegram_user="failuser", access_category=AccessCategory.PUBLIC)]
        end_state = await self.conversation.message_confirmed(confirm_update, context)

        self.provider.send_announcement.assert_awaited_once()
        call = self.provider.send_announcement.await_args
        assert call.args[0] == "mary"
        assert call.args[1] == "Event announcement"
        assert call.args[2] == events[0]
        # ensure failures are mentioned
        assert "failuser" in confirm_query.edit_message_text.await_args.args[0]
        assert end_state == ConversationHandler.END
