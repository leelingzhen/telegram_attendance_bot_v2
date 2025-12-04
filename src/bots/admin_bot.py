from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from datetime import datetime
from bots.base_bot import BaseBot
from models.models import AccessCategory, Event, User
from localization import Key
import logging

logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_ACTION = 1
CREATING_EVENT = 2
MANAGING_USERS = 3

class AdminBot(BaseBot):
    def __init__(self, token: str, service):
        super().__init__(token, service)
        self._setup_admin_handlers()
    
    def _setup_admin_handlers(self):
        """Setup handlers specific to the admin bot"""
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("admin", self.admin_command),
            ],
            states={
                CHOOSING_ACTION: [
                    CallbackQueryHandler(self.create_event, pattern="^create_event$"),
                    CallbackQueryHandler(self.manage_users, pattern="^manage_users$"),
                ],
                CREATING_EVENT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.event_details),
                ],
                MANAGING_USERS: [
                    CallbackQueryHandler(self.user_action),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        
        self.application.add_handler(conv_handler)
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /admin command"""
        user = update.effective_user
        db_user = await self.service.get_user(user.id)
        
        if not db_user or db_user.access_category != AccessCategory.ADMIN:
            await update.message.reply_text(Key.admin_permission_denied)
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(Key.admin_create_event_button, callback_data="create_event")],
            [InlineKeyboardButton(Key.admin_manage_users_button, callback_data="manage_users")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            Key.admin_choose_action,
            reply_markup=reply_markup
        )
        
        return CHOOSING_ACTION
    
    async def create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle event creation"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(Key.admin_create_event_prompt)
        
        return CREATING_EVENT
    
    async def event_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle event details input"""
        try:
            title, description, date_str, access_str = update.message.text.split("\n")
            event_date = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")
            access_category = AccessCategory(access_str.strip().lower())
            
            # Create event through service
            event = await self.service.create_event(
                title=title.strip(),
                description=description.strip(),
                date=event_date,
                access_category=access_category
            )
            
            await update.message.reply_text(
                Key.admin_event_created.format(
                    title=event.title,
                    date=event.date,
                    access=event.access_category,
                )
            )

            return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(
                Key.admin_event_creation_error.format(error=str(e))
            )
            return CREATING_EVENT
    
    async def manage_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user management"""
        query = update.callback_query
        await query.answer()
        
        # Get all users
        users = await self.service.get_all_users()
        
        keyboard = []
        for user in users:
            keyboard.append([
                InlineKeyboardButton(
                    f"{user.name} ({user.access_category})",
                    callback_data=f"user_{user.id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            Key.admin_select_user,
            reply_markup=reply_markup
        )
        
        return MANAGING_USERS
    
    async def user_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user action selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split("_")[1])
        user = await self.service.get_user_by_id(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton(Key.admin_promote_button, callback_data=f"promote_{user_id}"),
                InlineKeyboardButton(Key.admin_demote_button, callback_data=f"demote_{user_id}"),
            ],
            [InlineKeyboardButton(Key.admin_remove_button, callback_data=f"remove_{user_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            Key.admin_select_action_for_user.format(user_name=user.name),
            reply_markup=reply_markup
        )

        return MANAGING_USERS