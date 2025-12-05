from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, InlineKeyboardMarkup, Message, Update, User as TgUser
from telegram.ext import CallbackContext, ConversationHandler

from command_handlers.conversations.registration_conversation import (
    CONFIRMING_NAME,
    FILLING_NAME,
    FILLING_TELEGRAM_USER,
    RegistrationConversation,
)
from controllers.registration_controller import RegistrationControlling
from localization import Key
from models.enums import Gender, UserRecordStatus
from models.models import User


@pytest.fixture
def controller() -> AsyncMock:
    return AsyncMock(spec=RegistrationControlling)


class TestRegistrationConversation:
    @pytest.fixture(autouse=True)
    def _setup(self, controller):
        self.controller = controller
        self.conversation = RegistrationConversation(controller=controller)

    @pytest.mark.asyncio
    async def test_select_gender_ends_when_user_exists(self):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser, id=1, username="existing", first_name=None, last_name=None)
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.controller.check_user_record.return_value = UserRecordStatus.EXISTS

        result = await self.conversation.select_gender(update, context)

        self.controller.check_user_record.assert_awaited_once_with(update.effective_user)
        update.message.reply_text.assert_awaited_once_with(Key.registration_already_registered)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_select_gender_prompts_and_stores_user_model(self):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser, id=9, username="new_user", first_name=None, last_name=None, full_name="")
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.controller.check_user_record.return_value = UserRecordStatus.NEW

        next_state = await self.conversation.select_gender(update, context)

        assert next_state == CONFIRMING_NAME
        assert isinstance(context.user_data["new_user"], User)
        assert context.user_data["new_user"].telegram_user == "new_user"

        reply_args = update.message.reply_text.await_args
        args, kwargs = reply_args
        assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)
        assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "Male"

    @pytest.mark.asyncio
    async def test_confirm_name_conflict_requests_new_name(self):
        update = MagicMock(spec=Update)
        update.message = AsyncMock(spec=Message)
        update.message.text = "Taken Name"
        context = MagicMock(spec=CallbackContext)
        context.user_data = {"new_user": User(id=99, telegram_user=None, name="", gender=None)}

        self.controller.check_name_conflict.return_value = True

        result = await self.conversation.confirm_name_registration(update, context)

        self.controller.check_name_conflict.assert_awaited_once_with("Taken Name")
        update.message.reply_text.assert_awaited_once_with(Key.registration_name_conflict)
        assert result == FILLING_NAME

    @pytest.mark.asyncio
    async def test_confirm_name_success_moves_to_confirmation(self):
        update = MagicMock(spec=Update)
        update.message = AsyncMock(spec=Message)
        update.message.text = "New Person"
        context = MagicMock(spec=CallbackContext)
        context.user_data = {"new_user": User(id=88, telegram_user=None, name="", gender=None)}

        self.controller.check_name_conflict.return_value = False

        result = await self.conversation.confirm_name_registration(update, context)

        assert context.user_data["new_user"].name == "New Person"
        update.message.reply_text.assert_awaited_once()
        reply_kwargs = update.message.reply_text.await_args.kwargs
        assert isinstance(reply_kwargs["reply_markup"], InlineKeyboardMarkup)
        assert result == CONFIRMING_NAME

    @pytest.mark.asyncio
    async def test_select_gender_with_prefilled_name_goes_to_confirm(self):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser, id=10, username="new_user", first_name="Jane", last_name="Doe", full_name="Jane Doe")
        update.message = AsyncMock(spec=Message)
        context = MagicMock(spec=CallbackContext)
        context.user_data = {}

        self.controller.check_user_record.return_value = UserRecordStatus.NEW
        self.controller.check_name_conflict.return_value = False

        state = await self.conversation.select_gender(update, context)
        assert state == CONFIRMING_NAME

        query = MagicMock(spec=CallbackQuery)
        query.data = "Female"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update_callback = MagicMock(spec=Update)
        update_callback.callback_query = query

        next_state = await self.conversation.handle_gender_selection(update_callback, context)

        self.controller.check_name_conflict.assert_awaited_once_with("Jane Doe")
        assert context.user_data["new_user"].gender == Gender.FEMALE
        query.edit_message_text.assert_awaited_once()
        assert next_state == CONFIRMING_NAME

    @pytest.mark.asyncio
    async def test_fill_telegram_user_autofills_and_commits(self):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser, id=5, username="prefilled")
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.data = "forward"
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        update.callback_query = callback_query
        update.message = None

        context = MagicMock(spec=CallbackContext)
        context.user_data = {
            "new_user": User(id=5, telegram_user="prefilled", name="Tester", gender=Gender.MALE)
        }

        result = await self.conversation.fill_telegram_user(update, context)

        self.controller.submit_user_registration.assert_awaited_once_with(context.user_data["new_user"])
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_commit_registration_accepts_manual_handle(self):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser, id=7, username=None)
        update.message = AsyncMock(spec=Message)
        update.message.text = "@manual_handle"
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=CallbackContext)
        context.user_data = {"new_user": User(id=7, telegram_user=None, name="Manual User", gender=Gender.FEMALE)}

        result = await self.conversation.commit_registration(update, context)

        self.controller.submit_user_registration.assert_awaited_once()
        assert context.user_data["new_user"].telegram_user == "manual_handle"
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_commit_registration_reprompts_on_invalid_handle(self):
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TgUser, id=8, username=None)
        update.message = AsyncMock(spec=Message)
        update.message.text = "   "
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=CallbackContext)
        context.user_data = {"new_user": User(id=8, telegram_user=None, name="No Handle", gender=Gender.MALE)}

        result = await self.conversation.commit_registration(update, context)

        assert result == FILLING_TELEGRAM_USER
