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
from src.models.models import AccessCategory, AttendanceStatus, Attendance, Event
from src.command_handlers.conversations.conversation_flow import ConversationFlow
from src.providers.attendance_provider import AttendanceProvider
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
    
    def __init__(self, provider: AttendanceProvider):
        self.provider = provider
    
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
                    CallbackQueryHandler(self.attendance_selected),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.reason_provided),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def attendance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /attendance command"""
        user = update.effective_user
        db_user = await self.provider.get_user(user.id)
        
        if not db_user or db_user.access_category == AccessCategory.PUBLIC:
            await update.message.reply_text(
                "You need to be registered to use this command. Please contact an admin."
            )
            return ConversationHandler.END
        
        events = await self.provider.get_events(
            from_date=date.today(),
            access_category=db_user.access_category
        )
        
        if not events:
            await update.message.reply_text("No upcoming events found.")
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton(event.title, callback_data=str(event.id))]
            for event in events
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
        event = await self.provider.get_event(event_id)
        attendance = Attendance()
        
        if not event:
            await query.edit_message_text("Event not found.")
            return ConversationHandler.END

        context.user_data["selected_event"] = event
        context.user_data["attendance"] = attendance
        
        keyboard = [
            [
                InlineKeyboardButton("Yes I'll be there!", callback_data=f"1"),
                InlineKeyboardButton("No (lame)", callback_data=f"0"),
            ],
            [InlineKeyboardButton("Yes, but... (will prompt for comment)", callback_data=f"2")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Please indicate your attendance for {event.title}:",
            reply_markup=reply_markup
        )
        
        return INDICATING_ATTENDANCE

    async def give_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Prompt user to give reason/comment"""

        query = update.callback_query
        await query.answer()
        context.user_data["is_query_handled"] = True # needed for next handler to check if query has already been handled

        attendance_indicated = int(query.data)

        attendance: Attendance = context.user_data["attendance"]
        attendance.status = attendance_indicated

        context.user_data["attendance"] = attendance

        await query.edit_message_text(
            text="Please write a comment/reason 😏"
        )

        return INDICATING_ATTENDANCE

    
    async def attendance_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle attendance selection"""

        attendance: Attendance = context.user_data["attendance"]
        is_query_handled: bool = context.user_data["is_query_handled"]
        event: Event = context.user_data["selected_event"]

        text = "updating your attendance"
        if is_query_handled:
            # handle update message text

            reason = update.message.text
            attendance.clean_and_set_reason(reason)
            bot_message: Message = await update.message.reply_text(text)
        else:
            # from indicating yes
            query = update.callback_query
            await query.answer()

            attendance.status = int(query.data)
            bot_message: Message = await query.edit_message_text(text)

        # TODO add a job queue to update attendance
        self.provider.update_attendance(attendance)

        # TODO add a job queue to update kaypoh messages

        # TODO proper message to show updated attendance
        await bot_message.edit_text(
            text="you have updated your attendance"
        )

        # TODO resend announcement to user if previously indicated as absent

        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /cancel command"""
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END 