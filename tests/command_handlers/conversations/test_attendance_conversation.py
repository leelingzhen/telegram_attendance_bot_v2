from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message, Update, User
from telegram.ext import CallbackContext, ConversationHandler

from command_handlers.conversations.attendance_conversation import (
    CHOOSING_EVENT,
    INDICATING_ATTENDANCE,
    MarkAttendanceConversation,
)
from controllers.attendance_controller import AttendanceControlling
from models.enums import AccessCategory
from models.models import Attendance, Event
from models.responses import EventAttendance


def make_event_attendance(user_id: int, event_id: int = 1, is_accountable: bool = True) -> EventAttendance:
    """Build a minimal EventAttendance for tests."""
    now = datetime.now()
    event = Event(
        id=event_id,
        title="Test Event",
        description="",
        start=now,
        end=now + timedelta(hours=2),
        is_event_locked=False,
        is_accountable=is_accountable,
        access_category=AccessCategory.PUBLIC,
    )

    return EventAttendance(event=event, attendance=Attendance(event_id=event_id, user_id=user_id))


@pytest.fixture
def controller() -> AsyncMock:
    return AsyncMock(spec=AttendanceControlling)


class TestMarkAttendanceConversation:
    @pytest.fixture(autouse=True)
    def _setup(self, controller):
        self.controller = controller
        self.conversation = MarkAttendanceConversation(controller=controller)

    @pytest.mark.asyncio
    async def test_no_upcoming_events(self):
        user_id = 42
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User, id=user_id)
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.controller.retrieve_upcoming_events.return_value = []

        result = await self.conversation.attendance_command(update, context)

        self.controller.retrieve_upcoming_events.assert_awaited_once_with(
            user_id=user_id, from_date=date.today()
        )
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_yes_flow_updates_attendance(self):
        user_id = 7
        event = make_event_attendance(user_id=user_id)
        self.controller.retrieve_upcoming_events.return_value = [event]

        update_start = MagicMock(spec=Update)
        update_start.effective_user = MagicMock(spec=User, id=user_id)
        update_start.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        start_state = await self.conversation.attendance_command(update_start, context)
        assert start_state == CHOOSING_EVENT

        callback_event = MagicMock(spec=CallbackQuery)
        callback_event.data = str(event.event.id)
        callback_event.answer = AsyncMock()
        callback_event.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_event = MagicMock(spec=Update)
        update_event.callback_query = callback_event
        state_after_selection = await self.conversation.event_selected(update_event, context)
        assert state_after_selection == INDICATING_ATTENDANCE

        callback_yes = MagicMock(spec=CallbackQuery)
        callback_yes.data = "1"
        callback_yes.answer = AsyncMock()
        callback_yes.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_yes = MagicMock(spec=Update)
        update_yes.callback_query = callback_yes

        end_state = await self.conversation.give_reason(update_yes, context)

        assert end_state == ConversationHandler.END
        self.controller.update_attendance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_attendance_selected_calls_update_with_selected_event(self):
        user_id = 99
        selected_event = make_event_attendance(user_id=user_id, event_id=321)

        context = MagicMock(spec=CallbackContext)
        context.user_data = {
            "selected_event": selected_event,
            "is_event_selected_query_handled": False,
        }

        callback_yes = MagicMock(spec=CallbackQuery)
        callback_yes.data = 1
        callback_yes.answer = AsyncMock()
        callback_yes.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update = MagicMock(spec=Update)
        update.callback_query = callback_yes

        end_state = await self.conversation.attendance_selected(update, context)

        assert end_state == ConversationHandler.END
        self.controller.update_attendance.assert_awaited_once_with(events=[selected_event])

    @pytest.mark.asyncio
    async def test_no_for_accountable_event_prompts_then_updates(self):
        user_id = 10
        event = make_event_attendance(user_id=user_id, is_accountable=True)
        self.controller.retrieve_upcoming_events.return_value = [event]

        update_start = MagicMock(spec=Update)
        update_start.effective_user = MagicMock(spec=User, id=user_id)
        update_start.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}
        await self.conversation.attendance_command(update_start, context)

        callback_event = MagicMock(spec=CallbackQuery)
        callback_event.data = str(event.event.id)
        callback_event.answer = AsyncMock()
        callback_event.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_event = MagicMock(spec=Update)
        update_event.callback_query = callback_event
        await self.conversation.event_selected(update_event, context)

        callback_no = MagicMock(spec=CallbackQuery)
        callback_no.data = "0"
        callback_no.answer = AsyncMock()
        callback_no.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_no = MagicMock(spec=Update)
        update_no.callback_query = callback_no

        next_state = await self.conversation.give_reason(update_no, context)
        assert next_state == INDICATING_ATTENDANCE

        user_message = AsyncMock(spec=Message)
        user_message.text = "sorry"
        response_message = AsyncMock(spec=Message)
        response_message.edit_text = AsyncMock()
        user_message.reply_text = AsyncMock(return_value=response_message)
        update_comment = MagicMock(spec=Update)
        update_comment.message = user_message

        end_state = await self.conversation.attendance_selected(update_comment, context)

        assert end_state == ConversationHandler.END
        self.controller.update_attendance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_for_non_accountable_event_updates_immediately(self):
        user_id = 11
        event = make_event_attendance(user_id=user_id, is_accountable=False)
        self.controller.retrieve_upcoming_events.return_value = [event]

        update_start = MagicMock(spec=Update)
        update_start.effective_user = MagicMock(spec=User, id=user_id)
        update_start.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}
        await self.conversation.attendance_command(update_start, context)

        callback_event = MagicMock(spec=CallbackQuery)
        callback_event.data = str(event.event.id)
        callback_event.answer = AsyncMock()
        callback_event.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_event = MagicMock(spec=Update)
        update_event.callback_query = callback_event
        await self.conversation.event_selected(update_event, context)

        callback_no = MagicMock(spec=CallbackQuery)
        callback_no.data = "0"
        callback_no.answer = AsyncMock()
        callback_no.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_no = MagicMock(spec=Update)
        update_no.callback_query = callback_no

        end_state = await self.conversation.give_reason(update_no, context)

        assert end_state == ConversationHandler.END
        self.controller.update_attendance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_yes_with_comment_for_non_accountable_event_updates_immediately(self):
        user_id = 12
        event = make_event_attendance(user_id=user_id, is_accountable=False)
        self.controller.retrieve_upcoming_events.return_value = [event]

        update_start = MagicMock(spec=Update)
        update_start.effective_user = MagicMock(spec=User, id=user_id)
        update_start.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}
        await self.conversation.attendance_command(update_start, context)

        callback_event = MagicMock(spec=CallbackQuery)
        callback_event.data = str(event.event.id)
        callback_event.answer = AsyncMock()
        callback_event.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_event = MagicMock(spec=Update)
        update_event.callback_query = callback_event
        await self.conversation.event_selected(update_event, context)

        callback_yes_but = MagicMock(spec=CallbackQuery)
        callback_yes_but.data = "2"
        callback_yes_but.answer = AsyncMock()
        callback_yes_but.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_yes_but = MagicMock(spec=Update)
        update_yes_but.callback_query = callback_yes_but

        next_state = await self.conversation.give_reason(update_yes_but, context)

        assert next_state == INDICATING_ATTENDANCE

    @pytest.mark.asyncio
    async def test_yes_with_comment_for_accountable_event_prompts_reason(self):
        user_id = 13
        event = make_event_attendance(user_id=user_id, is_accountable=True)
        self.controller.retrieve_upcoming_events.return_value = [event]

        update_start = MagicMock(spec=Update)
        update_start.effective_user = MagicMock(spec=User, id=user_id)
        update_start.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}
        await self.conversation.attendance_command(update_start, context)

        callback_event = MagicMock(spec=CallbackQuery)
        callback_event.data = str(event.event.id)
        callback_event.answer = AsyncMock()
        callback_event.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_event = MagicMock(spec=Update)
        update_event.callback_query = callback_event
        await self.conversation.event_selected(update_event, context)

        callback_yes_but = MagicMock(spec=CallbackQuery)
        callback_yes_but.data = "2"
        callback_yes_but.answer = AsyncMock()
        callback_yes_but.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))
        update_yes_but = MagicMock(spec=Update)
        update_yes_but.callback_query = callback_yes_but

        next_state = await self.conversation.give_reason(update_yes_but, context)

        assert next_state == INDICATING_ATTENDANCE
