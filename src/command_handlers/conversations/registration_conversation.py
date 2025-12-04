from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters, \
    CallbackContext

from command_handlers.conversations.conversation_flow import ConversationFlow
from controllers.registration_controller import RegistrationControlling
from localization import Key
from models.enums import UserRecordStatus
from models.models import Gender, User

SELECTING_GENDER = 1
CONFIRMING_NAME = 2
FILLING_NAME = 3
FILLING_TELEGRAM_USER = 4

class RegistrationConversation(ConversationFlow):

    def __init__(self, controller: RegistrationControlling):
        self.controller = controller

    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler("register", self.select_gender)],
            states={
                FILLING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_name_registration),
                    ],
                CONFIRMING_NAME: [
                    CallbackQueryHandler(self.handle_gender_selection, pattern="^(Male|Female)$"),
                    CallbackQueryHandler(self.fill_name, pattern='^back$'),
                    CallbackQueryHandler(self.fill_telegram_user, pattern='^forward$'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_name_registration),
                    ],
                FILLING_TELEGRAM_USER: [
                    CallbackQueryHandler(self.commit_registration, pattern="^skip_username$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.commit_registration),
                    ],
                },
            fallbacks=[],
            )

    async def select_gender(self, update: Update, context: CallbackContext):

        telegram_user = update.effective_user

        record_status = await self.controller.check_user_record(telegram_user)
        if record_status == UserRecordStatus.EXISTS:
            await update.message.reply_text(Key.registration_already_registered)
            return ConversationHandler.END
        if record_status == UserRecordStatus.UPDATED:
            await update.message.reply_text(Key.registration_handle_updated)
            return ConversationHandler.END

        new_user = User(
            id=telegram_user.id,
            telegram_user=telegram_user.username,
            name=telegram_user.full_name,
            gender=None,
        )
        context.user_data["new_user"] = new_user

        buttons = [
            [InlineKeyboardButton(text=Key.registration_gender_male, callback_data='Male')],
            [InlineKeyboardButton(text=Key.registration_gender_female, callback_data='Female')]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(Key.registration_select_gender, reply_markup=keyboard)
        return CONFIRMING_NAME

    async def handle_gender_selection(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        new_user: User = context.user_data.get("new_user")
        selected_gender = query.data
        if new_user and selected_gender in ("Male", "Female"):
            new_user = new_user.model_copy(update={"gender": Gender(selected_gender)})
            context.user_data["new_user"] = new_user

        prefilled_name = new_user.name if new_user else ""
        if prefilled_name:
            has_conflict = await self.controller.check_name_conflict(prefilled_name)
            if has_conflict:
                new_user = new_user.model_copy(update={"name": ""})
                context.user_data["new_user"] = new_user
                await query.edit_message_text(f"{Key.registration_name_conflict}\n{Key.registration_prompt_name}")
                return FILLING_NAME

            await self._prompt_confirm_name(query, prefilled_name)
            return CONFIRMING_NAME

        await query.edit_message_text(Key.registration_prompt_name)
        return FILLING_NAME

    async def fill_name(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(Key.registration_prompt_name)
        return FILLING_NAME

    async def confirm_name_registration(self, update: Update, context: CallbackContext):
        new_user = context.user_data.get("new_user")
        name = update.message.text.strip()
        if new_user:
            new_user = new_user.model_copy(update={"name": name})
            context.user_data["new_user"] = new_user

        if await self.controller.check_name_conflict(name):
            await update.message.reply_text(Key.registration_name_conflict)
            return FILLING_NAME

        buttons = [
            [
                InlineKeyboardButton(text=Key.registration_back_button, callback_data='back'),
                InlineKeyboardButton(text=Key.registration_forward_button, callback_data='forward')
            ]
        ]
        await self._prompt_confirm_name(update.message, name, buttons)

        return CONFIRMING_NAME

    async def fill_telegram_user(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        new_user: User = context.user_data.get("new_user")

        if new_user and new_user.telegram_user:
            return await self.commit_registration(update, context)

        buttons = [[InlineKeyboardButton(Key.registration_skip_username_button, callback_data="skip_username")]]
        await query.edit_message_text(
            Key.registration_prompt_telegram_user,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return FILLING_TELEGRAM_USER

    async def commit_registration(self, update: Update, context: CallbackContext):
        new_user: User = context.user_data.get("new_user")
        message: Message | None = getattr(update, "message", None)
        bot_message: Message | None = None

        if message and message.text:
            bot_message = await message.reply_text(Key.registration_submitting_user)
            telegram_user = message.text.strip().lstrip("@")
            if not telegram_user:
                await message.reply_text(Key.registration_invalid_telegram_username)
                return FILLING_TELEGRAM_USER
            if new_user:
                new_user = new_user.model_copy(update={"telegram_user": telegram_user})
                context.user_data["new_user"] = new_user
        elif update.callback_query:
            query = update.callback_query
            await query.answer()
            bot_message = await query.edit_message_text(Key.registration_submitting_user)

        await self.controller.submit_user_registration(new_user)

        response_text = Key.registration_submitted.format(
            name=new_user.name,
            username=new_user.telegram_handle,
            gender=new_user.gender.value if new_user.gender else "(not set)",
        )

        await bot_message.edit_text(response_text)

        return ConversationHandler.END

    async def _prompt_confirm_name(self, target, name: str, buttons=None):
        if buttons is None:
            buttons = [
                [
                    InlineKeyboardButton(text=Key.registration_back_button, callback_data='back'),
                    InlineKeyboardButton(text=Key.registration_forward_button, callback_data='forward')
                ]
            ]
        keyboard = InlineKeyboardMarkup(buttons)
        confirm_text = Key.registration_confirm_name.format(name=name)

        if hasattr(target, "edit_message_text"):
            await target.edit_message_text(confirm_text, reply_markup=keyboard)
        else:
            await target.reply_text(confirm_text, reply_markup=keyboard)
