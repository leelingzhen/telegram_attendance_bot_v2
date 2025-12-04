from datetime import date, datetime
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, ContextTypes

from command_handlers.conversations.conversation_flow import ConversationFlow
from controllers.team_attendance_controller import TeamAttendanceControlling
from models.models import Event, AccessCategory
from models.responses.responses import UserAttendance, UserAttendanceResponse
from localization import Key

CHOOSING_EVENT = 1

class GetTeamAttendanceConversation(ConversationFlow):
    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler("kaypoh", self.upcoming_events)],
            states={CHOOSING_EVENT: [
                CallbackQueryHandler(self.return_team_attendance),
            ]},
            fallbacks=[],
        )

    def __init__(self, controller: TeamAttendanceControlling):
        self.controller = controller

    async def upcoming_events(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.effective_user

        upcoming_events = await self.controller.retrieve_upcoming_events(
            user_id=user.id,
            from_date=date.today(),
        )

        context.user_data["upcoming_events"] = upcoming_events

        if not upcoming_events:
            await update.message.reply_text(Key.no_upcoming_events_found)
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(self._format_event_datetime(event.start), callback_data=str(event.id))]
            for event in upcoming_events
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            Key.choose_event_message,
            reply_markup=reply_markup
        )

        return CHOOSING_EVENT

    async def return_team_attendance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        event_id = int(query.data)
        upcoming_events: List[Event] = context.user_data.get("upcoming_events", [])
        selected_event = next((event for event in upcoming_events if event.id == event_id), None)

        if not selected_event:
            await query.edit_message_text(Key.event_not_found_retry)
            return ConversationHandler.END

        attendance_response = await self.controller.retrieve_team_attendance(event_id=event_id)

        message = self._build_attendance_message(selected_event, attendance_response)

        await query.edit_message_text(text=message)

        return ConversationHandler.END

    def _build_attendance_message(self, event: Event, attendance: UserAttendanceResponse) -> str:
        total_attending = len(attendance.male) + len(attendance.female)
        lines = [
            Key.team_attendance_header.format(
                title=event.title,
                start=self._format_event_datetime(event.start),
                total=total_attending,
            ),
            "",
            Key.team_attendance_attending_male.format(count=len(attendance.male)),
            *self._format_user_block(attendance.male, section="attending"),
            "",
            Key.team_attendance_attending_female.format(count=len(attendance.female)),
            *self._format_user_block(attendance.female, section="attending"),
            "",
            Key.team_attendance_absent.format(count=len(attendance.absent)),
            *self._format_user_block(attendance.absent, section="absent"),
            "",
            Key.team_attendance_unindicated.format(count=len(attendance.unindicated)),
            *self._format_unindicated_block(attendance.unindicated),
            "",
            Key.team_attendance_last_updated.format(timestamp=self._format_last_updated()),
        ]

        return "\n".join(lines)

    def _format_user_block(self, users: List[UserAttendance], section: str) -> List[str]:
        if not users:
            return [Key.team_attendance_empty_section]
        return [self._format_user_line(user, include_reason=section != "unindicated") for user in users]

    def _format_unindicated_block(self, users: List[UserAttendance]) -> List[str]:
        if not users:
            return [Key.team_attendance_empty_section]
        return [self._format_user_line(user, include_reason=False, unindicated=True) for user in users]

    def _format_user_line(self, user: UserAttendance, include_reason: bool = True, unindicated: bool = False) -> str:
        reason_text = ""
        if include_reason and user.attendance.reason:
            reason_text = f" ({user.attendance.reason})"

        if user.access == AccessCategory.GUEST:
            return Key.team_attendance_user_guest.format(
                name=user.name,
                handle=user.telegram_user,
                reason=reason_text,
            )

        if unindicated:
            return Key.team_attendance_user_unindicated.format(
                name=user.name,
                handle=user.telegram_user,
            )

        return Key.team_attendance_user.format(name=user.name, reason=reason_text)

    def _format_event_datetime(self, start_time: datetime) -> str:
        return start_time.strftime("%-d-%b-%y, %a @ %-I:%M%p")

    def _format_last_updated(self) -> str:
        return datetime.now().strftime("%-d-%b %-I:%M%p")
