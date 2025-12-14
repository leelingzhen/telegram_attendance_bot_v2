from typing import List

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, ContextTypes

from command_handlers.conversations.conversation_flow import ConversationFlow
from controllers.manage_access_controller import ManageAccessControlling
from localization import Key
from models.enums import AccessCategory
from models.models import User

(
    SHOWING_CATEGORIES,
    SHOWING_USERS,
    SHOWING_ACCESS_OPTIONS,
    CONFIRMING_ACCESS,
) = range(4)


class ManageAccessConversation(ConversationFlow):
    def __init__(self, controller: ManageAccessControlling):
        self.controller = controller

    @property
    def conversation_handler(self) -> ConversationHandler:
        category_pattern = r"^category:.+$"
        user_pattern = r"^user:\d+$"
        access_pattern = r"^access:.+$"

        return ConversationHandler(
            entry_points=[CommandHandler("manage_access", self.show_categories)],
            states={
                SHOWING_CATEGORIES: [CallbackQueryHandler(self.show_users, pattern=category_pattern)],
                SHOWING_USERS: [
                    CallbackQueryHandler(self.back_to_categories, pattern="^back:categories$"),
                    CallbackQueryHandler(self.show_access_options, pattern=user_pattern),
                ],
                SHOWING_ACCESS_OPTIONS: [
                    CallbackQueryHandler(self.back_to_users, pattern="^back:users$"),
                    CallbackQueryHandler(self.choose_access, pattern=access_pattern),
                ],
                CONFIRMING_ACCESS: [
                    CallbackQueryHandler(self.back_to_access_options, pattern="^back:access$"),
                    CallbackQueryHandler(self.confirm_access, pattern="^confirm:set_access$"),
                ],
            },
            fallbacks=[],
            allow_reentry=True,
        )

    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        categories = self.controller.retrieve_access_categories()
        context.user_data["categories"] = categories

        keyboard = [
            [InlineKeyboardButton(cat.value.title(), callback_data=f"category:{cat.value}")]
            for cat in categories
        ]
        markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(Key.manage_access_select_category, reply_markup=markup)
        else:
            message: Message = update.message
            await message.reply_text(Key.manage_access_select_category, reply_markup=markup)

        return SHOWING_CATEGORIES

    async def show_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query: CallbackQuery = update.callback_query
        await query.answer()

        _, category_value = query.data.split(":", 1)
        category = AccessCategory(category_value)
        context.user_data["selected_category"] = category

        users = self.controller.retrieve_users(category)
        context.user_data["users"] = users

        keyboard = [
            [InlineKeyboardButton(user.name, callback_data=f"user:{user.id}")]
            for user in users
        ]
        keyboard.append(
            [InlineKeyboardButton(Key.manage_access_back_button, callback_data="back:categories")]
        )

        await query.edit_message_text(
            text=Key.manage_access_users_in_category.format(category=category.value.title()),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SHOWING_USERS

    async def show_access_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query: CallbackQuery = update.callback_query
        await query.answer()

        _, user_id_text = query.data.split(":", 1)
        user_id = int(user_id_text)
        users: List[User] = context.user_data.get("users", [])
        selected_user = next((u for u in users if u.id == user_id), None)
        context.user_data["selected_user"] = selected_user

        options = self._access_options_for_user(selected_user)
        context.user_data["access_options"] = options

        keyboard = [
            [InlineKeyboardButton(opt.value.title(), callback_data=f"access:{opt.value}")]
            for opt in options
        ]
        keyboard.append(
            [InlineKeyboardButton(Key.manage_access_back_button, callback_data="back:users")]
        )

        await query.edit_message_text(
            text=Key.manage_access_access_options.format(name=selected_user.name),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SHOWING_ACCESS_OPTIONS

    async def choose_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query: CallbackQuery = update.callback_query
        await query.answer()

        _, access_value = query.data.split(":", 1)
        selected_access = AccessCategory(access_value)
        context.user_data["selected_access"] = selected_access

        selected_user: User = context.user_data.get("selected_user")
        keyboard = [
            [
                InlineKeyboardButton(
                    Key.manage_access_confirm_button, callback_data="confirm:set_access"
                )
            ],
            [InlineKeyboardButton(Key.manage_access_back_button, callback_data="back:access")],
        ]

        await query.edit_message_text(
            text=Key.manage_access_set_access_confirmation.format(
                name=selected_user.name, access=selected_access.value.title()
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRMING_ACCESS

    async def confirm_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query: CallbackQuery = update.callback_query
        await query.answer()

        user: User = context.user_data.get("selected_user")
        selected_access: AccessCategory = context.user_data.get("selected_access")
        self.controller.set_access(user, selected_access)

        await query.edit_message_text(
            text=Key.manage_access_access_updated.format(
                name=user.name, access=selected_access.value.title()
            ),
        )
        return ConversationHandler.END

    async def back_to_access_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query: CallbackQuery = update.callback_query
        await query.answer()

        selected_user: User = context.user_data.get("selected_user")
        options: List[AccessCategory] = context.user_data.get("access_options", [])
        keyboard = [
            [InlineKeyboardButton(opt.value.title(), callback_data=f"access:{opt.value}")]
            for opt in options
        ]
        keyboard.append(
            [InlineKeyboardButton(Key.manage_access_back_button, callback_data="back:users")]
        )

        await query.edit_message_text(
            text=Key.manage_access_access_options.format(name=selected_user.name),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SHOWING_ACCESS_OPTIONS

    async def back_to_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query: CallbackQuery = update.callback_query
        await query.answer()

        category: AccessCategory = context.user_data.get("selected_category")
        users: List[User] = context.user_data.get("users", [])

        keyboard = [
            [InlineKeyboardButton(user.name, callback_data=f"user:{user.id}")]
            for user in users
        ]
        keyboard.append(
            [InlineKeyboardButton(Key.manage_access_back_button, callback_data="back:categories")]
        )

        await query.edit_message_text(
            text=Key.manage_access_users_in_category.format(category=category.value.title()),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SHOWING_USERS

    async def back_to_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self.show_categories(update, context)

    def _access_options_for_user(self, user: User) -> List[AccessCategory]:
        if user and user.access_category == AccessCategory.ADMIN:
            return [AccessCategory.ADMIN]
        return self.controller.retrieve_access_categories()
