from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime, date

from controllers.attendance_controller import AttendanceControlling, AttendanceController
from models.models import Attendance, Event, EventAttendance
from command_handlers.conversations.conversation_flow import ConversationFlow
import logging

logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_EVENT = 1
INDICATING_ATTENDANCE = 2

class MarkAttendanceConversation(ConversationFlow):
    """
    Handles the conversation flow for a user to mark their own attendance at events.
    
    This conversation flow allows individual users to:
    1. Select an event from upcoming events
    2. Indicate their personal attendance status (Attending/Not Attending/Maybe)
    3. Provide a reason for their attendance status
    
    This is specifically for users to mark their own attendance, as opposed to
    viewing or managing other users' attendance.
    """
    
    def __init__(self, controller: AttendanceControlling):
        self.controller = controller
    
    @property
    def conversation_handler(self) -> ConversationHandler:
        """The conversation handler for marking attendance flow"""

        return ConversationHandler(
            entry_points=[
                CommandHandler("attendance", self.attendance_command),
            ],
            states={
                CHOOSING_EVENT: [
                    CallbackQueryHandler(self.event_selected),
                ],
                INDICATING_ATTENDANCE: [
                    CallbackQueryHandler(self.give_reason),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.attendance_selected),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def attendance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /attendance command"""
        user = update.effective_user

        upcoming_events = await self.controller.retrieve_upcoming_events(
            user_id=user.id,
            from_date=date.today(),
        )

        context.user_data["upcoming_events"] = upcoming_events

        if not upcoming_events:
            await update.message.reply_text("No upcoming events found.")
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton(event.start.strftime('%-d-%b-%-y, %a @ %-I:%M%p'), callback_data=str(event.id))]
            for event in upcoming_events

        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Please select an event:",
            reply_markup=reply_markup
        )
        
        return CHOOSING_EVENT
    
    async def event_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle event selection"""
        query = update.callback_query
        await query.answer()
        event_id = int(query.data)
        upcoming_events: List[EventAttendance] = context.user_data["upcoming_events"]

        selected_event = next(event for event in upcoming_events if event.id == event_id)

        context.user_data["selected_event"] = selected_event

        keyboard = [
            [
                InlineKeyboardButton("Yes I'll be there!", callback_data=f"1"),
                InlineKeyboardButton("No (lame)", callback_data=f"0"),
            ],
            [InlineKeyboardButton("Yes, but... (will prompt for comment)", callback_data=f"2")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Please indicate your attendance for {selected_event.title}:",
            reply_markup=reply_markup
        )
        
        return INDICATING_ATTENDANCE

    async def give_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Prompt user to give reason/comment"""

        query = update.callback_query
        await query.answer()
        context.user_data["is_event_selected_query_handled"] = False

        selected_event: EventAttendance = context.user_data["selected_event"]
        attendance_indicated = int(query.data)

        selected_event.attendance.status = bool(attendance_indicated)
        context.user_data["selected_event"] = selected_event

        if attendance_indicated == 1:
            return await self.attendance_selected(update, context)
        elif attendance_indicated != 2 and not selected_event.isAccountable:
            return await self.attendance_selected(update, context)

        context.user_data["is_event_selected_query_handled"] = True
        await query.edit_message_text(
            text="Please write a comment/reason 😏"
        )

        return INDICATING_ATTENDANCE

    
    async def attendance_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle attendance selection"""

        selected_event: EventAttendance = context.user_data["selected_event"]
        is_event_selected_query_handled: bool = context.user_data["is_event_selected_query_handled"]

        text = "updating your attendance"
        if is_event_selected_query_handled:
            reason = update.message.text
            selected_event.attendance.clean_and_set_reason(reason)

            bot_message: Message = await update.message.reply_text(text)
        else:
            query = update.callback_query
            await query.answer()

            selected_event.attendance.status = bool(int(query.data))
            bot_message: Message = await query.edit_message_text(text)

        await self.controller.update_attendance(events=[selected_event])

        await bot_message.edit_text(
            text="you have updated your attendance"
        )
        # TODO resend announcement to user if previously indicated as absent

        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /cancel command"""
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END