from datetime import datetime
from typing import Iterable, List, Optional
from xmlrpc.client import DateTime

from pygments.lexers.robotframework import SETTING
from setuptools.config._validate_pyproject import formats
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
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
from models.enums import AccessCategory
from models.models import Event
from localization import Key

CHOOSING_EVENT = 1
SHOWING_EVENT_MENU = 2
SETTING_TITLE = 3
SETTING_DESCRIPTION = 5
SETTING_DATE = 6
SETTING_TIME = 7
SETTING_ACCESS = 8


TITLE_PRESETS = [
    "Field Training",
    "Scrim",
    "Hardcourt",
    "Track",
    "Gym/Pod",
    "Cohesion",
]

class ManageEventConversation(ConversationFlow):
    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("manage_event", self.select_or_create_event),
            ],
            states={
                CHOOSING_EVENT: [
                    CallbackQueryHandler(self.selected_event, pattern="^[1-9]\d*$"),
                    CallbackQueryHandler(self.select_date, pattern="^set_datetime_new$"),
                ],
                SHOWING_EVENT_MENU: [
                    CallbackQueryHandler(self.set_event_title, pattern="^set_title$"),
                    CallbackQueryHandler(self.set_event_description, pattern="^set_description$"),
                    CallbackQueryHandler(self.select_date, pattern=r"^set_datetime_.+"),
                    CallbackQueryHandler(self.toggle_accountable_event, pattern="^set_accountability$"),
                    CallbackQueryHandler(self.set_access, pattern="^set_access$"),
                    CallbackQueryHandler(self.commit_event, pattern="^confirm_changes$"),
                ],
                SETTING_TITLE: [
                    CallbackQueryHandler(self.set_event_title),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_event_title),

                ],
                SETTING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_event_description),
                ],
                SETTING_DATE: [
                    CallbackQueryHandler(self.set_time, pattern=""), ## TODO input date format callback handler for custom calendar component
                    CallbackQueryHandler(self.select_date, pattern="^step$"),
                ],
                SETTING_TIME: [
                    CallbackQueryHandler(self.update_event_datetime),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_event_datetime),
                ],
                SETTING_ACCESS: [
                    CallbackQueryHandler(self.update_event_access)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

    def __init__(self, controller: ManageEventControlling):
        self.controller = controller


    async def select_or_create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Entry point for /manage_event - show existing events and create button."""

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
        buttons.append([InlineKeyboardButton(Key.manage_event_create_button, callback_data="set_datetime_new")])

        reply_markup = InlineKeyboardMarkup(buttons)
        text = Key.manage_event_choose_event if upcoming_events else Key.manage_event_no_events

        await update.message.reply_text(text=text, reply_markup=reply_markup)

        return CHOOSING_EVENT

    async def selected_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        event_id = int(query.data)
        upcoming_events = context.user_data.get("upcoming_events", [])
        selected_event = next((event for event in upcoming_events if event.id == event_id), None)

        context.user_data["selected_event"] = selected_event

        bot_message = await query.edit_message_text(text="existing event selected")

        return await self.manage_event_main_menu(update, context, bot_message)

    async def create_new_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        ## in here we do not want to answer the query, let the next handler handle the query, we just want to instantiate
        ##

        return await self.select_date(update, context)

    async def manage_event_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bot_message: Message) -> int:
        """Display the main configuration menu for the selected event."""
        selected_event: Event = context.user_data.get("selected_event")

        main_menu_text = self._main_menu_text(event=selected_event)
        maim_menu_buttons = self._build_main_menu_buttons

        await bot_message.edit_text(text=main_menu_text, reply_markup=InlineKeyboardMarkup(maim_menu_buttons))

        return SHOWING_EVENT_MENU

    async def select_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # TODO: create the calendar keyboard markup and put it here

        query = update.callback_query
        await query.answer()

        try:
            # store initial query first
            query_type = query.data.split("_").pop()
            context.user_data["initial_calendar_query"] = query_type
        except IndexError:
            # TODO show the next corresponding months calendar
            # here the query probably is returned as "step" so show that corresponding month's calendar
            raise NotImplementedError

        return SETTING_DATE

    async def set_time(self, update: Update,context: ContextTypes.DEFAULT_TYPE) -> int:
        # TODO: prompt for time, give keyboard markup in 24 hour format
        # or else can reply message to set a custom time in 24 hour format
        query = update.callback_query
        await query.answer()

        # get the date from the query
        selected_date = datetime.strptime(query.data, "")

        context.user_data["selected_date"] = selected_date

        query_type = context.user_data.get("initial_calendar_query")

        # build buttons here for time format
        time_message = await query.edit_message_text(text=f"set the {query_type} time, you may use the following or reply a custom timing in 24h hhmm format ")
        context.user_data["time_message"] = time_message

        return SETTING_TIME

    async def update_event_datetime(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        message = getattr(update, "message", None)
        bot_message: Message | None = None
        selected_date = context.user_data.get("selected_date")
        selected_event: Event | None = context.user_data.get("selected_event")


        if message and message.text:
            bot_message = await message.reply_text(text="ingesting custom format...")
            time_message: Message = context.user_data.get("time_message")
            await time_message.edit_reply_markup(reply_markup=None)

            selected_time = datetime.strptime(message.text, "%H:%M")

        else:
            query = update.callback_query
            await query.answer()
            bot_message = await query.edit_message_text(text="ingesting time...")
            selected_time = datetime.strptime(query.data, "%H:%M")

        selected_datetime = datetime.combine(selected_date, selected_time.time())

        initial_query = context.user_data.get("initial_calendar_query")

        if initial_query == "new":
            selected_event = self.controller.create_new_event(start_datetime=selected_datetime)
        elif initial_query == "start":
            selected_event.start = selected_datetime
        elif initial_query == "end":
            selected_event.end = selected_datetime
        elif initial_query == "deadline":
            selected_event.deadline = selected_datetime

        context.user_data["selected_event"] = selected_event

        return await self.manage_event_main_menu(update, context, bot_message)

    async def set_event_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        title_buttons = [
            [InlineKeyboardButton(text=title, callback_data=f"title:{title}")]
            for title in TITLE_PRESETS
        ]

        title_message = await query.edit_message_text(
            text=Key.manage_event_choose_title,
            reply_markup=InlineKeyboardMarkup(title_buttons),
        )
        context.user_data["title_message"] = title_message

        return SETTING_TITLE

    async def update_event_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = getattr(update, "message", None)
        bot_message: Message | None = None
        selected_event: Event = context.user_data.get("selected_event")

        if message and message.text:
            bot_message = await message.reply_text(text="ingesting custom title...")
            time_message: Message = context.user_data.get("title_message")
            await time_message.edit_reply_markup(reply_markup=None)

            title = message.text

        else:
            query = update.callback_query
            await query.answer()
            bot_message = await query.edit_message_text(text="ingesting title...")
            title = query.data

        selected_event.title = title
        context.user_data["selected_event"] = selected_event

        return await self.manage_event_main_menu(update, context, bot_message)

    async def set_event_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

        # TODO give template description to expect a reply from the user

        return SETTING_DESCRIPTION

    async def update_event_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        description = update.message.text

        context.user_data["selected_event"].description = description

        bot_message = await update.message.reply_text(text="ingesting description")
        return await self.manage_event_main_menu(update, context, bot_message)

    async def toggle_accountable_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        selected_event = context.user_data.get("selected_event")

        selected_event.accountable_event = not selected_event.accountable_event
        context.user_data["selected_event"] = selected_event

        bot_message = await self.ensure_message(query)

        return await self.manage_event_main_menu(update, context, bot_message)

    async def set_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # TODO craft message to show the access categories, each access level correspond to the AccessCategory Enum
        query = update.callback_query
        await query.answer()
        return SETTING_ACCESS

    async def update_event_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        selected_event = context.user_data.get("selected_event")
        selected_event.access = AccessCategory(query.data)

        context.user_data["selected_event"] = selected_event

        bot_message = await self.ensure_message(query)

        return await self.manage_event_main_menu(update, context, bot_message)

    async def commit_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # TODO call the controller update event here, give a receipt of the event that was sent
        return ConversationHandler.END


    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(Key.operation_cancelled)
        return ConversationHandler.END

    @staticmethod
    def _main_menu_text(
        event: Event,
        prefix: Optional[str] = None,
    ) -> str:

        text_blocks = []
        if prefix:
            text_blocks.append(prefix)

        text_blocks.append(
            Key.manage_event_main_menu_title.format(
                title=event.title,
                start=event.start.strftime("%Y-%m-%d %H:%M"),
                end=event.end.strftime("%Y-%m-%d %H:%M"),
                access=event.access_category.value,
                accountable=Key.manage_event_reason_mandatory
                if event.is_accountable
                else Key.manage_event_reason_optional,
            )
        )
        text_blocks.append(Key.manage_event_main_menu_instruction)

        menu_text = "\n\n".join(text_blocks)

        return menu_text

    @staticmethod
    async def ensure_message(
            query: CallbackQuery,
            placeholder_text: str = "Working..."
    ) -> Message:
        msg = query.message

        if msg and isinstance(msg, Message):
            return msg

        # If message is None or MaybeInaccessibleMessage,
        # replace it with a fresh bot message
        edited = await query.edit_message_text(placeholder_text)
        return edited

    @property
    def _build_main_menu_buttons(self) -> List[List[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton(text=Key.manage_event_set_title_button, callback_data="set_title")],
            [InlineKeyboardButton(text=Key.manage_event_set_description_button, callback_data="set_description")],
            [InlineKeyboardButton(text=Key.manage_event_set_start_button, callback_data="set_datetime_start")],
            [InlineKeyboardButton(text=Key.manage_event_set_end_button, callback_data="set_datetime_end")],
            [InlineKeyboardButton(text=Key.manage_event_set_deadline_button, callback_data="set_datetime_deadline")],
            [InlineKeyboardButton(text=Key.manage_event_set_accountability_button, callback_data="set_accountability")],
            [InlineKeyboardButton(text=Key.manage_event_set_access_button, callback_data="set_access_level")],
            [InlineKeyboardButton(text=Key.manage_event_confirm_changes, callback_data="confirm_changes")],
        ]
