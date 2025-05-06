from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime, date
from models.models import AccessCategory, AttendanceStatus, Attendance
from command_handlers.conversations.conversation_flow import ConversationFlow
from providers.attendance_provider import AttendanceProvider
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
        
        if not event:
            await query.edit_message_text("Event not found.")
            return ConversationHandler.END
        
        keyboard = [
            [
                InlineKeyboardButton("Attending", callback_data=f"attending_{event_id}"),
                InlineKeyboardButton("Not Attending", callback_data=f"not_attending_{event_id}"),
            ],
            [InlineKeyboardButton("Maybe", callback_data=f"maybe_{event_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Please indicate your attendance for {event.title}:",
            reply_markup=reply_markup
        )
        
        return INDICATING_ATTENDANCE
    
    async def attendance_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle attendance selection"""
        query = update.callback_query
        await query.answer()
        
        status, event_id = query.data.split("_")
        event_id = int(event_id)
        
        user = update.effective_user
        db_user = await self.provider.get_user(user.id)
        
        attendance = await self.provider.get_attendance(event_id, db_user.id)
        if not attendance:
            # Create new attendance
            attendance = await self.provider.update_attendance(
                Attendance(
                    id=0,  # Will be set by the service
                    user_id=db_user.id,
                    event_id=event_id,
                    status=AttendanceStatus(status),
                    reason="",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            )
        
        await query.edit_message_text(
            f"Please provide a reason for your attendance status:"
        )
        
        context.user_data["attendance"] = attendance
        return INDICATING_ATTENDANCE
    
    async def reason_provided(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle reason provided for attendance"""
        attendance = context.user_data["attendance"]
        attendance.reason = update.message.text
        attendance.updated_at = datetime.now()
        
        await self.provider.update_attendance(attendance)
        
        await update.message.reply_text(
            "Thank you for updating your attendance!"
        )
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /cancel command"""
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END 