from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, InlineKeyboardMarkup, Message, Update, User
from telegram.ext import CallbackContext, ConversationHandler

from command_handlers.conversations.get_team_attendance_conversation import (
    CHOOSING_EVENT,
    GetTeamAttendanceConversation,
)
from controllers.team_attendance_controller import (
    FakeTeamAttendanceController,
    TeamAttendanceControlling,
)
from models.models import AccessCategory, Event
from models.responses.responses import AttendanceResponse, UserAttendance, UserAttendanceResponse


@pytest.fixture
def controller() -> AsyncMock:
    return AsyncMock(spec=TeamAttendanceControlling)


class TestGetTeamAttendanceConversation:
    @pytest.fixture(autouse=True)
    def _setup(self, controller):
        self.controller = controller
        self.conversation = GetTeamAttendanceConversation(controller=controller)

    @pytest.mark.asyncio
    async def test_upcoming_events_handles_empty_results(self):
        user_id = 42
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User, id=user_id)
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.controller.retrieve_upcoming_events.return_value = []

        result = await self.conversation.upcoming_events(update, context)

        self.controller.retrieve_upcoming_events.assert_awaited_once_with(
            user_id=user_id, from_date=date.today()
        )
        update.message.reply_text.assert_awaited_once_with("No upcoming events found.")
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_upcoming_events_prompts_selection(self):
        user_id = 7
        event = Event(
            id=1,
            title="Field Training",
            description=None,
            start=datetime(2025, 10, 11, 13, 30),
            end=datetime(2025, 10, 11, 15, 0),
            attendance_deadline=None,
            is_accountable=True,
            access_category=AccessCategory.MEMBER,
        )

        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User, id=user_id)
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.controller.retrieve_upcoming_events.return_value = [event]

        next_state = await self.conversation.upcoming_events(update, context)

        assert context.user_data["upcoming_events"] == [event]
        assert next_state == CHOOSING_EVENT

        reply_text_args = update.message.reply_text.await_args
        assert reply_text_args is not None
        args, kwargs = reply_text_args
        assert args[0] == "Please select an event:"
        assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)
        assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == str(event.id)

    @pytest.mark.asyncio
    async def test_return_team_attendance_handles_missing_event(self):
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.data = "2"
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = callback_query

        result = await self.conversation.return_team_attendance(update, context)

        callback_query.answer.assert_awaited_once()
        callback_query.edit_message_text.assert_awaited_once_with(
            "Event not found. Please try again."
        )
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_return_team_attendance_formats_full_message(self, monkeypatch):
        controller = FakeTeamAttendanceController()
        conversation = GetTeamAttendanceConversation(controller=controller)

        event = controller.sample_event
        context = MagicMock(spec=CallbackContext)
        context.user_data = {"upcoming_events": [event]}

        attendance_response = await controller.retrieve_team_attendance(event_id=event.id)
        monkeypatch.setattr(conversation, "_format_last_updated", lambda: "11-Oct 2:58PM")

        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.data = str(event.id)
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = callback_query

        expected_message = conversation._build_attendance_message(event, attendance_response)

        result = await conversation.return_team_attendance(update, context)

        callback_query.answer.assert_awaited_once()
        callback_query.edit_message_text.assert_awaited_once_with(text=expected_message)
        assert result == ConversationHandler.END


@pytest.fixture
def attendance_response_fixture() -> UserAttendanceResponse:
    return UserAttendanceResponse(
        male=[
            UserAttendance(
                name="Guest Guy",
                telegram_user="guestguy",
                gender="M",
                access=AccessCategory.GUEST,
                attendance=AttendanceResponse(status=True, reason="Cheering on"),
            ),
        ],
        female=[],
        absent=[],
        unindicated=[
            UserAttendance(
                name="Uncertain User",
                telegram_user="uncertain",
                gender="F",
                access=AccessCategory.GUEST,
                attendance=AttendanceResponse(status=None, reason="maybe"),
            )
        ],
    )


class TestMessageFormatting:
    def test_guest_and_unindicated_formatting(self, attendance_response_fixture, monkeypatch):
        conversation = GetTeamAttendanceConversation(controller=AsyncMock())
        event = Event(
            id=99,
            title="Scrimmage",
            description=None,
            start=datetime(2025, 12, 25, 18, 0),
            end=datetime(2025, 12, 25, 20, 0),
            attendance_deadline=None,
            is_accountable=True,
            access_category=AccessCategory.MEMBER,
        )

        monkeypatch.setattr(conversation, "_format_last_updated", lambda: "01-Jan 1:00PM")

        expected_lines = [
            "Attendance for Scrimmage on 25-Dec-25, Thu @ 6:00PM : 1",
            "",
            "Attending 👦🏻: 1",
            "(guest) Guest Guy - @guestguy (Cheering on)",
            "",
            "Attending 👩🏻: 0",
            "-",
            "",
            "Absent: 0",
            "-",
            "",
            "Unindicated: 1",
            "(guest) Uncertain User - @uncertain",
            "",
            "last updated: 01-Jan 1:00PM",
        ]

        message = conversation._build_attendance_message(event, attendance_response_fixture)

        assert message.split("\n") == expected_lines
