from datetime import datetime
from typing import Iterable, List, Optional

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from command_handlers.conversations.conversation_flow import ConversationFlow
from controllers.manage_event_controller import ManageEventControlling
from models.models import Event
from localization import Key

SELECTING_EVENT = 1
EVENT_MENU = 2
CHOOSING_TITLE = 3
WAITING_CUSTOM_TITLE = 4
WAITING_START_DATETIME = 5


TITLE_PRESETS = [
    "Field Training",
    "Scrim",
    "Hardcourt",
    "Track",
    "Gym/Pod",
    "Cohesion",
    "Custom",
]

class ManageEventConversation(ConversationFlow):
    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("manage_event", self.select_or_create_event),
            ],
            states={
                SELECTING_EVENT: [
                    CallbackQueryHandler(self.handle_event_chosen, pattern="^(event:|create_new_event)"),
                ],
                EVENT_MENU: [
                    CallbackQueryHandler(self.prompt_title_selection, pattern="^set_title$"),
                    CallbackQueryHandler(self.choose_another_event, pattern="^choose_another_event$"),
                    CallbackQueryHandler(
                        self.handle_unimplemented_option,
                        pattern="^(set_description|set_start_datetime|set_end_datetime|set_deadline_datetime|set_accountability|set_access_level)$",
                    ),
                ],
                CHOOSING_TITLE: [
                    CallbackQueryHandler(self.handle_title_choice, pattern="^title:"),
                ],
                WAITING_CUSTOM_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_custom_title),
                    CallbackQueryHandler(self.manage_event_main_menu, pattern="^back_to_menu$"),
                ],
                WAITING_START_DATETIME: [
                    CallbackQueryHandler(self.use_current_start, pattern="^use_start_now$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_start_datetime_text),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

    def __init__(self, controller: ManageEventControlling):
        self.controller = controller

    async def select_or_create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Entry point for /manage_event - show existing events and create button."""
        target = getattr(update, "message", None) or getattr(update, "callback_query", None)
        if isinstance(target, CallbackQuery):
            await target.answer()
        return await self._show_event_selection(target=target, context=context)

    async def handle_event_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        if query.data == "create_new_event":
            context.user_data["is_new_event"] = True
            return await self.prompt_start_datetime(update, context)

        selected_event_id = int(query.data.split("event:")[1])
        upcoming_events = context.user_data.get("upcoming_events", [])
        selected_event = next((event for event in upcoming_events if event.id == selected_event_id), None)

        if selected_event is None:
            await query.edit_message_text(Key.event_not_found_retry)
            return await self._show_event_selection(target=query, context=context)

        context.user_data["is_new_event"] = False
        context.user_data["selected_event"] = selected_event

        return await self.manage_event_main_menu(update, context)

    async def prompt_start_datetime(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Prompt the user to pick a start datetime for the new event."""
        query = update.callback_query
        await query.answer()

        buttons = [
            [InlineKeyboardButton(Key.manage_event_use_now_button, callback_data="use_start_now")],
        ]
        await query.edit_message_text(
            text=Key.manage_event_prompt_start_datetime,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return WAITING_START_DATETIME

    async def use_current_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        start_datetime = datetime.now()
        return await self._finalize_new_event(update=query, context=context, start_datetime=start_datetime)

    async def handle_start_datetime_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Parse typed datetime when calendar picker is unavailable."""
        try:
            start_datetime = datetime.strptime(update.message.text.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text(Key.manage_event_invalid_datetime)
            return WAITING_START_DATETIME

        return await self._finalize_new_event(update=update.message, context=context, start_datetime=start_datetime)

    async def _finalize_new_event(
        self,
        update: Message | CallbackQuery,
        context: ContextTypes.DEFAULT_TYPE,
        start_datetime: datetime,
    ) -> int:
        new_event = self.controller.create_new_event(start_datetime=start_datetime)
        context.user_data["selected_event"] = new_event
        context.user_data["is_new_event"] = True

        prefix = Key.manage_event_new_event_created.format(
            start=start_datetime.strftime("%Y-%m-%d %H:%M")
        )
        return await self._send_main_menu(target=update, context=context, event=new_event, prefix=prefix)

    async def manage_event_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Display the main configuration menu for the selected event."""
        selected_event: Optional[Event] = context.user_data.get("selected_event")
        if selected_event is None:
            target = getattr(update, "callback_query", None) or getattr(update, "message", None)
            if isinstance(target, CallbackQuery):
                await target.answer()
            return await self._show_event_selection(target=target, context=context)

        if isinstance(update, Update) and update.callback_query:
            await update.callback_query.answer()
            target = update.callback_query
        else:
            target = getattr(update, "message", None)

        return await self._send_main_menu(target=target, context=context, event=selected_event)

    async def prompt_title_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        title_buttons = [
            [InlineKeyboardButton(text=title, callback_data=f"title:{title}")]
            for title in TITLE_PRESETS
        ]
        title_buttons.append(
            [InlineKeyboardButton(text=Key.manage_event_back_to_menu_button, callback_data="back_to_menu")]
        )

        await query.edit_message_text(
            text=Key.manage_event_choose_title,
            reply_markup=InlineKeyboardMarkup(title_buttons),
        )
        return CHOOSING_TITLE

    async def handle_title_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        selected_event: Event | None = context.user_data.get("selected_event")
        if selected_event is None:
            return await self.select_or_create_event(update, context)

        choice = query.data.split("title:")[1]
        if choice == "Custom":
            await query.edit_message_text(
                text=Key.manage_event_custom_title_prompt,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(Key.manage_event_back_to_menu_button, callback_data="back_to_menu")]]
                ),
            )
            return WAITING_CUSTOM_TITLE

        updated_event = selected_event.model_copy(update={"title": choice})
        context.user_data["selected_event"] = updated_event
        self.controller.update_event(updated_event)

        prefix = Key.manage_event_title_updated.format(title=choice)
        return await self._send_main_menu(target=query, context=context, event=updated_event, prefix=prefix)

    async def save_custom_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        custom_title = update.message.text.strip()
        selected_event: Event | None = context.user_data.get("selected_event")
        if selected_event is None:
            return await self.select_or_create_event(update, context)

        updated_event = selected_event.model_copy(update={"title": custom_title})
        context.user_data["selected_event"] = updated_event
        self.controller.update_event(updated_event)

        prefix = Key.manage_event_title_updated.format(title=custom_title)
        return await self._send_main_menu(target=update.message, context=context, event=updated_event, prefix=prefix)

    async def choose_another_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        return await self._show_event_selection(target=query, context=context)

    async def handle_unimplemented_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer(text=Key.manage_event_stub_option_not_ready)
        return EVENT_MENU

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(Key.operation_cancelled)
        return ConversationHandler.END

    async def _show_event_selection(
        self, target: Message | CallbackQuery | None, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        upcoming_events: List[Event] = self.controller.retrieve_events(from_date=datetime.now())
        context.user_data["upcoming_events"] = upcoming_events

        buttons: List[List[InlineKeyboardButton]] = [
            [
                InlineKeyboardButton(
                    f"{event.title} — {event.start.strftime('%Y-%m-%d %H:%M')}",
                    callback_data=f"event:{event.id}",
                )
            ]
            for event in upcoming_events
        ]
        buttons.append([InlineKeyboardButton(Key.manage_event_create_button, callback_data="create_new_event")])

        reply_markup = InlineKeyboardMarkup(buttons)
        text = Key.manage_event_choose_event if upcoming_events else Key.manage_event_no_events

        if target and hasattr(target, "edit_message_text"):
            await target.edit_message_text(text=text, reply_markup=reply_markup)
        elif target:
            await target.reply_text(text=text, reply_markup=reply_markup)

        return SELECTING_EVENT

    async def _send_main_menu(
        self,
        target,
        context: ContextTypes.DEFAULT_TYPE,
        event: Event,
        prefix: Optional[str] = None,
    ) -> int:
        context.user_data["selected_event"] = event

        text_blocks = []
        if prefix:
            text_blocks.append(prefix)

        text_blocks.append(
            Key.manage_event_main_menu_title.format(
                title=event.title,
                start=event.start.strftime("%Y-%m-%d %H:%M"),
                end=event.end.strftime("%Y-%m-%d %H:%M"),
                access=event.access_category.value,
                accountable="Yes" if event.is_accountable else "No",
            )
        )
        text_blocks.append(Key.manage_event_main_menu_instruction)

        menu_text = "\n\n".join(text_blocks)
        keyboard = InlineKeyboardMarkup(self._build_main_menu_buttons())

        if hasattr(target, "edit_message_text"):
            await target.edit_message_text(menu_text, reply_markup=keyboard)
        else:
            await target.reply_text(menu_text, reply_markup=keyboard)

        return EVENT_MENU

    def _build_main_menu_buttons(self) -> Iterable[List[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton(text=Key.manage_event_set_title_button, callback_data="set_title")],
            [InlineKeyboardButton(text=Key.manage_event_set_description_button, callback_data="set_description")],
            [InlineKeyboardButton(text=Key.manage_event_set_start_button, callback_data="set_start_datetime")],
            [InlineKeyboardButton(text=Key.manage_event_set_end_button, callback_data="set_end_datetime")],
            [InlineKeyboardButton(text=Key.manage_event_set_deadline_button, callback_data="set_deadline_datetime")],
            [InlineKeyboardButton(text=Key.manage_event_set_accountability_button, callback_data="set_accountability")],
            [InlineKeyboardButton(text=Key.manage_event_set_access_button, callback_data="set_access_level")],
            [InlineKeyboardButton(text=Key.manage_event_back_to_list, callback_data="choose_another_event")],
        ]
