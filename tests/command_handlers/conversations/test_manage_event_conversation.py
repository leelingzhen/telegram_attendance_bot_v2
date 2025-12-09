import pytest
from datetime import datetime, timedelta
from unittest.mock import ANY, AsyncMock, MagicMock

from telegram import CallbackQuery, Message, Update

from command_handlers.conversations.manage_event_conversation import (
    EVENT_MENU,
    WAITING_ACCOUNTABILITY,
    WAITING_ACCESS,
    WAITING_FIELD_INPUT,
    ManageEventConversation,
)
from controllers.manage_event_controller import ManageEventControlling
from localization import Key
from models.enums import AccessCategory
from models.models import Event


@pytest.fixture
def controller():
    return MagicMock(spec=ManageEventControlling)


def make_event(event_id: int = 1) -> Event:
    start = datetime.now()
    return Event(
        id=event_id,
        title="Sample",
        description="Old",
        start=start,
        end=start + timedelta(hours=2),
        attendance_deadline=None,
        is_accountable=False,
        access_category=AccessCategory.PUBLIC,
    )


class TestManageEventConversation:
    @pytest.fixture(autouse=True)
    def _setup(self, controller):
        self.controller = controller
        self.conversation = ManageEventConversation(controller=controller)

    @pytest.mark.asyncio
    async def test_description_update_flows_back_to_menu(self):
        event = make_event()
        context = MagicMock()
        context.user_data = {"selected_event": event}

        user_message = AsyncMock(spec=Message)
        bot_message = AsyncMock(spec=Message)
        user_message.reply_text = AsyncMock(return_value=bot_message)

        update_start = MagicMock(spec=Update)
        update_start.message = user_message
        update_start.callback_query = None

        start_state = await self.conversation.manage_event_main_menu(update_start, context)
        assert start_state == EVENT_MENU
        assert context.user_data["manage_event_bot_message"] == bot_message

        description_query = MagicMock(spec=CallbackQuery)
        description_query.data = "set_description"
        description_query.answer = AsyncMock()
        description_query.edit_message_text = AsyncMock()

        update_query = MagicMock(spec=Update)
        update_query.callback_query = description_query
        update_query.message = None

        prompt_state = await self.conversation.prompt_description_update(update_query, context)
        assert prompt_state == WAITING_FIELD_INPUT
        description_query.answer.assert_awaited()
        bot_message.edit_text.assert_awaited_with(
            Key.manage_event_prompt_description, reply_markup=ANY
        )
        assert context.user_data["pending_field"] == "description"

        response_message = AsyncMock(spec=Message)
        response_message.text = "New description"
        response_message.reply_text = AsyncMock()

        update_response = MagicMock(spec=Update)
        update_response.message = response_message
        update_response.callback_query = None

        final_state = await self.conversation.handle_field_input(update_response, context)
        assert final_state == EVENT_MENU
        assert context.user_data["selected_event"].description == "New description"
        updated_bot_message = context.user_data["manage_event_bot_message"]
        assert updated_bot_message.edit_text.await_count >= 1

    @pytest.mark.asyncio
    async def test_accountability_update_sets_flag(self):
        event = make_event()
        context = MagicMock()
        context.user_data = {"selected_event": event, "manage_event_bot_message": AsyncMock(spec=Message)}

        query = MagicMock(spec=CallbackQuery)
        query.data = "set_accountability"
        query.answer = AsyncMock()

        update_query = MagicMock(spec=Update)
        update_query.callback_query = query
        update_query.message = None

        state = await self.conversation.prompt_accountability_update(update_query, context)
        assert state == WAITING_ACCOUNTABILITY
        assert context.user_data["pending_field"] == "is_accountable"

        choice_query = MagicMock(spec=CallbackQuery)
        choice_query.data = "accountability:true"
        choice_query.answer = AsyncMock()
        choice_query.edit_message_text = AsyncMock()

        update_choice = MagicMock(spec=Update)
        update_choice.callback_query = choice_query
        update_choice.message = None

        next_state = await self.conversation.handle_accountability_choice(update_choice, context)
        assert next_state == EVENT_MENU
        assert context.user_data["selected_event"].is_accountable is True

    @pytest.mark.asyncio
    async def test_access_update_uses_enum_and_returns_to_menu(self):
        event = make_event()
        context = MagicMock()
        bot_message = AsyncMock(spec=Message)
        context.user_data = {"selected_event": event, "manage_event_bot_message": bot_message}

        query = MagicMock(spec=CallbackQuery)
        query.data = "set_access_level"
        query.answer = AsyncMock()

        update_query = MagicMock(spec=Update)
        update_query.callback_query = query
        update_query.message = None

        state = await self.conversation.prompt_access_update(update_query, context)
        assert state == WAITING_ACCESS
        bot_message.edit_text.assert_awaited_with(
            text=Key.manage_event_access_prompt, reply_markup=ANY
        )

        choice_query = MagicMock(spec=CallbackQuery)
        choice_query.data = f"access:{AccessCategory.MEMBER.value}"
        choice_query.answer = AsyncMock()
        choice_query.edit_message_text = AsyncMock()

        update_choice = MagicMock(spec=Update)
        update_choice.callback_query = choice_query
        update_choice.message = None

        next_state = await self.conversation.handle_access_choice(update_choice, context)
        assert next_state == EVENT_MENU
        assert context.user_data["selected_event"].access_category == AccessCategory.MEMBER

    @pytest.mark.asyncio
    async def test_commit_event_calls_controller(self):
        event = make_event()
        bot_message = AsyncMock(spec=Message)
        context = MagicMock()
        context.user_data = {
            "selected_event": event,
            "manage_event_bot_message": bot_message,
        }

        query = MagicMock(spec=CallbackQuery)
        query.data = "commit_event"
        query.answer = AsyncMock()

        update_query = MagicMock(spec=Update)
        update_query.callback_query = query
        update_query.message = None

        state = await self.conversation.commit_event_changes(update_query, context)
        assert state == EVENT_MENU
        self.controller.update_event.assert_called_once_with(event)
        bot_message.edit_text.assert_awaited()
