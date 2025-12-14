from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message, Update
from telegram.ext import CallbackContext, ConversationHandler

from command_handlers.conversations.manage_access_conversation import (
    CONFIRMING_ACCESS,
    SHOWING_ACCESS_OPTIONS,
    SHOWING_CATEGORIES,
    SHOWING_USERS,
    ManageAccessConversation,
)
from controllers.manage_access_controller import ManageAccessControlling
from models.enums import AccessCategory
from models.models import User


@pytest.fixture
def controller() -> MagicMock:
    controller = MagicMock(spec=ManageAccessControlling)
    controller.retrieve_access_categories.return_value = list(AccessCategory)
    return controller


@pytest.fixture
def conversation(controller: MagicMock) -> ManageAccessConversation:
    return ManageAccessConversation(controller=controller)


def create_user(id: int, name: str, access: AccessCategory) -> User:
    return User(id=id, name=name, access_category=access)


@pytest.mark.asyncio
async def test_manage_access_entry_shows_categories(conversation, controller):
    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.message = message
    update.callback_query = None

    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    state = await conversation.show_categories(update, context)

    controller.retrieve_access_categories.assert_called_once()
    args, kwargs = message.reply_text.await_args
    markup = kwargs["reply_markup"]
    callback_data = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    expected_data = [f"category:{c.value}" for c in AccessCategory]
    assert callback_data == expected_data
    assert state == SHOWING_CATEGORIES


@pytest.mark.asyncio
async def test_category_selection_retrieves_users(conversation, controller):
    users = [create_user(1, "Alice", AccessCategory.MEMBER), create_user(2, "Bob", AccessCategory.MEMBER)]
    controller.retrieve_users.return_value = users

    query = MagicMock(spec=CallbackQuery)
    query.data = "category:member"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock(return_value=AsyncMock(spec=Message))

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    state = await conversation.show_users(update, context)

    controller.retrieve_users.assert_called_once_with(AccessCategory.MEMBER)
    args, kwargs = query.edit_message_text.await_args
    markup = kwargs["reply_markup"]
    user_callbacks = [btn.callback_data for row in markup.inline_keyboard[:-1] for btn in row]
    assert user_callbacks == ["user:1", "user:2"]
    back_callback = markup.inline_keyboard[-1][0].callback_data
    assert back_callback == "back:categories"
    assert context.user_data["selected_category"] == AccessCategory.MEMBER
    assert state == SHOWING_USERS


@pytest.mark.asyncio
async def test_user_selection_shows_access_options_for_regular_and_super_users(conversation, controller):
    regular_user = create_user(1, "Alice", AccessCategory.MEMBER)
    admin_user = create_user(2, "Admin", AccessCategory.ADMIN)
    controller.retrieve_users.return_value = [regular_user, admin_user]

    # Regular user shows all categories
    query = MagicMock(spec=CallbackQuery)
    query.data = "user:1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"users": [regular_user, admin_user]}

    state = await conversation.show_access_options(update, context)

    args, kwargs = query.edit_message_text.await_args
    markup = kwargs["reply_markup"]
    callbacks = [btn.callback_data for row in markup.inline_keyboard[:-1] for btn in row]
    assert set(callbacks) == {f"access:{c.value}" for c in AccessCategory}
    assert state == SHOWING_ACCESS_OPTIONS

    # Super user should only show admin option
    query_admin = MagicMock(spec=CallbackQuery)
    query_admin.data = "user:2"
    query_admin.answer = AsyncMock()
    query_admin.edit_message_text = AsyncMock()

    update_admin = MagicMock(spec=Update)
    update_admin.callback_query = query_admin

    context_admin = MagicMock(spec=CallbackContext)
    context_admin.user_data = {"users": [regular_user, admin_user]}

    state_admin = await conversation.show_access_options(update_admin, context_admin)

    args_admin, kwargs_admin = query_admin.edit_message_text.await_args
    markup_admin = kwargs_admin["reply_markup"]
    callbacks_admin = [btn.callback_data for row in markup_admin.inline_keyboard[:-1] for btn in row]
    assert callbacks_admin == ["access:admin"]
    assert state_admin == SHOWING_ACCESS_OPTIONS


@pytest.mark.asyncio
async def test_choose_access_shows_confirmation(conversation):
    user = create_user(1, "Alice", AccessCategory.MEMBER)
    query = MagicMock(spec=CallbackQuery)
    query.data = "access:guest"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {"selected_user": user}

    state = await conversation.choose_access(update, context)

    args, kwargs = query.edit_message_text.await_args
    markup = kwargs["reply_markup"]
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert callbacks == ["confirm:set_access", "back:access"]
    assert context.user_data["selected_access"] == AccessCategory.GUEST
    assert state == CONFIRMING_ACCESS


@pytest.mark.asyncio
async def test_confirmation_sets_access(conversation, controller):
    user = create_user(1, "Alice", AccessCategory.MEMBER)
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = query

    context = MagicMock(spec=CallbackContext)
    context.user_data = {
        "selected_user": user,
        "selected_access": AccessCategory.ADMIN,
    }

    state = await conversation.confirm_access(update, context)

    controller.set_access.assert_called_once_with(user, AccessCategory.ADMIN)
    assert state == ConversationHandler.END


@pytest.mark.asyncio
async def test_back_navigation_restores_previous_state(conversation, controller):
    regular_user = create_user(1, "Alice", AccessCategory.MEMBER)
    controller.retrieve_access_categories.return_value = list(AccessCategory)

    # Prepare context as if access options were shown
    context = MagicMock(spec=CallbackContext)
    context.user_data = {
        "selected_user": regular_user,
        "users": [regular_user],
        "selected_category": AccessCategory.MEMBER,
        "access_options": list(AccessCategory),
    }

    # Back from confirmation to access options
    back_access_query = MagicMock(spec=CallbackQuery)
    back_access_query.answer = AsyncMock()
    back_access_query.edit_message_text = AsyncMock()

    back_access_update = MagicMock(spec=Update)
    back_access_update.callback_query = back_access_query

    state_access = await conversation.back_to_access_options(back_access_update, context)
    assert state_access == SHOWING_ACCESS_OPTIONS
    args_access, kwargs_access = back_access_query.edit_message_text.await_args
    markup_access = kwargs_access["reply_markup"]
    callbacks_access = [btn.callback_data for row in markup_access.inline_keyboard[:-1] for btn in row]
    assert set(callbacks_access) == {f"access:{c.value}" for c in AccessCategory}

    # Back from access options to users list
    back_users_query = MagicMock(spec=CallbackQuery)
    back_users_query.answer = AsyncMock()
    back_users_query.edit_message_text = AsyncMock()

    back_users_update = MagicMock(spec=Update)
    back_users_update.callback_query = back_users_query

    state_users = await conversation.back_to_users(back_users_update, context)
    assert state_users == SHOWING_USERS
    args_users, kwargs_users = back_users_query.edit_message_text.await_args
    markup_users = kwargs_users["reply_markup"]
    user_callbacks = [btn.callback_data for row in markup_users.inline_keyboard[:-1] for btn in row]
    assert user_callbacks == ["user:1"]
    assert markup_users.inline_keyboard[-1][0].callback_data == "back:categories"
