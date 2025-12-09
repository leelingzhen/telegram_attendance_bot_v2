from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message, Update
from telegram.ext import CallbackContext, ConversationHandler

from command_handlers.conversations.manage_event_conversation import (
    CHOOSING_EVENT,
    SETTING_DATE,
    SETTING_TIME,
    SHOWING_EVENT_MENU,
    ManageEventConversation,
)
from controllers.manage_event_controller import ManageEventControlling
from custom_components.CalendarKeyboardMarkup import CalendarKeyboardMarkup
from models.enums import AccessCategory
from models.models import Event


@pytest.fixture
def controller() -> MagicMock:
    controller = MagicMock(spec=ManageEventControlling)
    controller.retrieve_events.return_value = []
    controller.create_new_event.side_effect = lambda start_datetime: Event(
        id=-1,
        title="New Event",
        description="",
        start=start_datetime,
        end=start_datetime + timedelta(hours=1),
        attendance_deadline=None,
        is_accountable=False,
        access_category=AccessCategory.PUBLIC,
    )
    return controller


@pytest.fixture
def conversation(controller: MagicMock) -> ManageEventConversation:
    return ManageEventConversation(controller=controller)


@pytest.fixture
def sample_event() -> Event:
    now = datetime(2024, 5, 1, 10, 0)
    return Event(
        id=1,
        title="Field Training",
        description=None,
        start=now,
        end=now + timedelta(hours=2),
        attendance_deadline=None,
        is_accountable=True,
        access_category=AccessCategory.MEMBER,
    )


@pytest.mark.asyncio
async def test_select_date_shows_calendar(conversation, sample_event):
    query = MagicMock(spec=CallbackQuery)
    query.data = "set_datetime_start"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"selected_event": sample_event}

    state = await conversation.select_date(update, context)

    query.edit_message_text.assert_awaited_once()
    assert context.user_data["initial_calendar_query"] == "start"
    assert state == SETTING_DATE


def test_callback_patterns_accept_event_and_calendar(conversation):
    handler = conversation.conversation_handler

    choose_handlers = handler.states[CHOOSING_EVENT][0]
    assert choose_handlers.pattern.match("event:123")
    assert choose_handlers.pattern.match("event:uuid-123")

    date_handlers = handler.states[SETTING_DATE]
    date_pattern = CalendarKeyboardMarkup.encode_date(date(2024, 5, 1))
    step_pattern = CalendarKeyboardMarkup.encode_step(2024, 6)
    assert any(getattr(h, "pattern", None) and h.pattern.match(date_pattern) for h in date_handlers)
    assert any(getattr(h, "pattern", None) and h.pattern.match(step_pattern) for h in date_handlers)


@pytest.mark.asyncio
async def test_calendar_step_navigation_updates_markup(conversation):
    query = MagicMock(spec=CallbackQuery)
    query.data = CalendarKeyboardMarkup.encode_step(2024, 6)
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    state = await conversation.select_date(update, context)

    query.edit_message_reply_markup.assert_awaited_once()
    assert state == SETTING_DATE


@pytest.mark.asyncio
async def test_set_time_stores_selected_date(conversation):
    chosen_date = date(2024, 5, 6)
    query = MagicMock(spec=CallbackQuery)
    query.data = CalendarKeyboardMarkup.encode_date(chosen_date)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"initial_calendar_query": "start"}

    state = await conversation.set_time(update, context)

    assert context.user_data["selected_date"] == chosen_date
    assert state == SETTING_TIME


@pytest.mark.asyncio
async def test_update_event_datetime_sets_start_and_returns_to_menu(conversation, sample_event):
    query = MagicMock(spec=CallbackQuery)
    query.data = "0800"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message, edit_text=AsyncMock()))

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {
        "selected_event": sample_event,
        "selected_date": date(2024, 5, 6),
        "initial_calendar_query": "start",
    }

    state = await conversation.update_event_datetime(update, context)

    assert sample_event.start == datetime(2024, 5, 6, 8, 0)
    assert state == SHOWING_EVENT_MENU


@pytest.mark.asyncio
async def test_update_event_datetime_reprompts_on_invalid_text(conversation, sample_event):
    message = MagicMock(spec=Message)
    message.text = "notatime"
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.message = message

    context = MagicMock(spec=CallbackContext)
    context.user_data = {
        "selected_event": sample_event,
        "selected_date": date(2024, 5, 6),
        "initial_calendar_query": "start",
        "time_message": MagicMock(spec=Message),
    }

    state = await conversation.update_event_datetime(update, context)

    message.reply_text.assert_awaited_once()
    assert sample_event.start == datetime(2024, 5, 1, 10, 0)  # unchanged
    assert state == SETTING_TIME


@pytest.mark.asyncio
async def test_end_date_flow_includes_use_start_button(conversation, sample_event):
    query = MagicMock(spec=CallbackQuery)
    query.data = "set_datetime_end"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"selected_event": sample_event}

    await conversation.select_date(update, context)

    args, kwargs = query.edit_message_text.await_args
    markup = kwargs["reply_markup"]
    flat = [btn for row in markup.inline_keyboard for btn in row]
    assert any(btn.text == "Use start date" for btn in flat)


@pytest.mark.asyncio
async def test_deadline_presets_and_clear(conversation, sample_event):
    sample_event.start = datetime(2024, 5, 10, 12, 0)
    sample_event.attendance_deadline = datetime(2024, 5, 9, 23, 59)
    query = MagicMock(spec=CallbackQuery)
    query.data = "set_datetime_deadline"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"selected_event": sample_event}

    await conversation.select_date(update, context)
    args, kwargs = query.edit_message_text.await_args
    markup = kwargs["reply_markup"]
    flat = [btn for row in markup.inline_keyboard for btn in row]
    assert any(btn.text == "1 day before (23:59)" for btn in flat)
    assert any(btn.text == "Remove deadline" for btn in flat)

    preset_query = MagicMock(spec=CallbackQuery)
    preset_query.data = "deadline_preset:none"
    preset_query.answer = AsyncMock()
    preset_query.edit_message_text = AsyncMock()
    preset_update = MagicMock(spec=Update)
    preset_update.callback_query = preset_query
    context.user_data["initial_calendar_query"] = "deadline"

    state = await conversation.apply_deadline_preset(preset_update, context)
    assert sample_event.attendance_deadline is None
    assert state == SHOWING_EVENT_MENU


@pytest.mark.asyncio
async def test_commit_event_updates_controller(conversation, sample_event, controller):
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"selected_event": sample_event}

    state = await conversation.commit_event(update, context)

    controller.update_event.assert_called_once_with(sample_event)
    assert state == ConversationHandler.END
