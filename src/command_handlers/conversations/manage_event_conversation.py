from datetime import datetime, date, timedelta
from typing import List, Optional

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
from custom_components.CalendarKeyboardMarkup import CalendarKeyboardMarkup
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
    Key.manage_event_title_preset_field_training,
    Key.manage_event_title_preset_scrim,
    Key.manage_event_title_preset_hardcourt,
    Key.manage_event_title_preset_track,
    Key.manage_event_title_preset_gym_pod,
    Key.manage_event_title_preset_cohesion,
]


class ManageEventConversation(ConversationFlow):
    @property
    def conversation_handler(self) -> ConversationHandler:
        date_pattern = rf"^{CalendarKeyboardMarkup.callback_data.date_prefix}\d{{4}}-\d{{2}}-\d{{2}}$"
        step_pattern = rf"^{CalendarKeyboardMarkup.callback_data.step_prefix}\d{{4}}-\d{{2}}$"
        access_pattern = rf"^({'|'.join(a.value for a in AccessCategory)})$"
        event_pattern = r"^event:.+$"

        return ConversationHandler(
            entry_points=[
                CommandHandler("manage_event", self.select_or_create_event),
            ],
            states={
                CHOOSING_EVENT: [
                    CallbackQueryHandler(self.selected_event, pattern=event_pattern),
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
                    CallbackQueryHandler(self.update_event_title),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_event_title),

                ],
                SETTING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_event_description),
                ],
                SETTING_DATE: [
                    CallbackQueryHandler(self.use_start_date, pattern="^use_start_date$"),
                    CallbackQueryHandler(self.apply_deadline_preset, pattern=r"^deadline_preset:.+$"),
                    CallbackQueryHandler(self.set_time, pattern=date_pattern),
                    CallbackQueryHandler(self.select_date, pattern=step_pattern),
                ],
                SETTING_TIME: [
                    CallbackQueryHandler(self.update_event_datetime),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_event_datetime),
                ],
                SETTING_ACCESS: [
                    CallbackQueryHandler(self.update_event_access, pattern=access_pattern)
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
                    f"{event.title} — {self._format_datetime(event.start)}",
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

        event_key = query.data.split(":", maxsplit=1)[1]
        upcoming_events = context.user_data.get("upcoming_events", [])
        selected_event = next(
            (event for event in upcoming_events if str(event.id) == event_key), None
        )

        context.user_data["selected_event"] = selected_event

        bot_message = await query.edit_message_text(text=Key.manage_event_loaded_event)

        return await self.manage_event_main_menu(update, context, bot_message)

    async def manage_event_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bot_message: Message | None) -> int:
        """Display the main configuration menu for the selected event."""
        selected_event: Event = context.user_data.get("selected_event")

        main_menu_text = self._main_menu_text(event=selected_event)
        main_menu_buttons = self._build_main_menu_buttons

        if bot_message:
            await bot_message.edit_text(text=main_menu_text, reply_markup=InlineKeyboardMarkup(main_menu_buttons))
        else:
            query = update.callback_query
            ensured = await self.ensure_message(query)
            await ensured.edit_text(text=main_menu_text, reply_markup=InlineKeyboardMarkup(main_menu_buttons))

        return SHOWING_EVENT_MENU

    async def select_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        if query.data.startswith(CalendarKeyboardMarkup.callback_data.step_prefix):
            year, month = CalendarKeyboardMarkup.parse_step(query.data)
            range_start, range_end = self._calendar_range_for_query(context)
            markup = self._build_calendar_markup(
                context=context,
                year=year,
                month=month,
                range_start=range_start,
                range_end=range_end,
            )
            await query.edit_message_reply_markup(reply_markup=markup)
            return SETTING_DATE

        query_type = query.data.split("_").pop()
        query_label = self._query_label(query_type)
        context.user_data["initial_calendar_query"] = query_type

        base_date = self._starting_date_for_query(context, query_type)
        range_start, range_end = self._calendar_range_for_query(context, query_type)
        markup = self._build_calendar_markup(
            context=context,
            year=base_date.year,
            month=base_date.month,
            query_type=query_type,
            range_start=range_start,
            range_end=range_end,
        )

        await query.edit_message_text(
            text=Key.manage_event_select_date_prompt.format(label=query_label),
            reply_markup=markup,
        )

        return SETTING_DATE

    async def set_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        selected_date = CalendarKeyboardMarkup.parse_date(query.data)
        context.user_data["selected_date"] = selected_date

        query_type = context.user_data.get("initial_calendar_query", "start")
        query_label = self._query_label(query_type)
        example_time = datetime.now().strftime("%H%M")

        await self._prompt_time_selection(query, context, query_label, example_time)

        return SETTING_TIME

    async def use_start_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        selected_event: Event | None = context.user_data.get("selected_event")
        initial_query = context.user_data.get("initial_calendar_query")
        if not selected_event or not selected_event.start:
            return await self.manage_event_main_menu(update, context, await self.ensure_message(query))

        context.user_data["selected_date"] = selected_event.start.date()
        query_label = self._query_label(initial_query)
        return await self._prompt_time_selection(query, context, query_label)

    async def apply_deadline_preset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        preset = query.data.split(":", maxsplit=1)[1]
        selected_event: Event | None = context.user_data.get("selected_event")
        if not selected_event or not selected_event.start:
            return await self.manage_event_main_menu(update, context, await self.ensure_message(query))

        target = self._deadline_from_preset(selected_event.start, preset)
        selected_event.attendance_deadline = target
        context.user_data["selected_event"] = selected_event

        bot_message = await self.ensure_message(query)
        return await self.manage_event_main_menu(update, context, bot_message)

    async def update_event_datetime(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = getattr(update, "message", None)
        bot_message: Message | None = None
        selected_date = context.user_data.get("selected_date")
        selected_event: Event | None = context.user_data.get("selected_event")

        if isinstance(message, Message) and message.text:
            time_text = message.text.strip()
            selected_time = self._parse_time(time_text)
            if not selected_time:
                example_time = datetime.now().strftime("%H%M")
                await message.reply_text(text=Key.manage_event_invalid_time.format(example_time=example_time))
                return SETTING_TIME

            bot_message = await message.reply_text(text=Key.manage_event_setting_time_from_text)
            time_message: Message = context.user_data.get("time_message")
            await time_message.edit_reply_markup(reply_markup=None)

        else:
            query = update.callback_query
            await query.answer()
            bot_message = await query.edit_message_text(text=Key.manage_event_setting_time)
            selected_time = self._parse_time(query.data)
            if not selected_time:
                example_time = datetime.now().strftime("%H%M")
                await query.edit_message_text(text=Key.manage_event_invalid_time.format(example_time=example_time))
                return SETTING_TIME

        selected_datetime = datetime.combine(selected_date, selected_time.time())

        initial_query = context.user_data.get("initial_calendar_query")

        if (
            initial_query == "end"
            and selected_event
            and selected_event.start
            and selected_datetime < selected_event.start
        ):
            return await self._handle_end_before_start(update, context, bot_message)

        if initial_query == "new":
            selected_event = self.controller.create_new_event(start_datetime=selected_datetime)
        elif initial_query == "start":
            selected_event.start = selected_datetime
        elif initial_query == "end":
            selected_event.end = selected_datetime
        elif initial_query == "deadline":
            selected_event.attendance_deadline = selected_datetime

        context.user_data["selected_event"] = selected_event

        return await self.manage_event_main_menu(update, context, bot_message)

    async def _handle_end_before_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        bot_message: Message | None,
    ) -> int:
        base_date = self._starting_date_for_query(context, "end")
        range_start, range_end = self._calendar_range_for_query(context, "end")
        markup = self._build_calendar_markup(
            context=context,
            year=base_date.year,
            month=base_date.month,
            query_type="end",
            range_start=range_start,
            range_end=range_end,
        )

        if bot_message:
            await bot_message.edit_text(text=Key.manage_event_end_before_start, reply_markup=markup)
        else:
            query = update.callback_query
            ensured = await self.ensure_message(query)
            await ensured.edit_text(text=Key.manage_event_end_before_start, reply_markup=markup)

        return SETTING_DATE

    async def set_event_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        title_buttons = [
            [InlineKeyboardButton(text=title, callback_data=title)]
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
            bot_message = await message.reply_text(text=Key.manage_event_updating_title_from_text)
            time_message: Message = context.user_data.get("title_message")
            await time_message.edit_reply_markup(reply_markup=None)

            title = message.text

        else:
            query = update.callback_query
            await query.answer()
            bot_message = await query.edit_message_text(text=Key.manage_event_updating_title_from_button)
            title = query.data

        selected_event.title = title
        context.user_data["selected_event"] = selected_event

        return await self.manage_event_main_menu(update, context, bot_message)

    async def set_event_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(text=Key.manage_event_description_prompt)

        return SETTING_DESCRIPTION

    async def update_event_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        description = update.message.text

        context.user_data["selected_event"].description = description

        bot_message = await update.message.reply_text(text=Key.manage_event_description_updated)
        return await self.manage_event_main_menu(update, context, bot_message)

    async def toggle_accountable_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        selected_event = context.user_data.get("selected_event")

        selected_event.is_accountable = not selected_event.is_accountable
        context.user_data["selected_event"] = selected_event

        bot_message = await self.ensure_message(query)

        return await self.manage_event_main_menu(update, context, bot_message)

    async def set_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        buttons = [
            [InlineKeyboardButton(text=category.value.title(), callback_data=category.value)]
            for category in AccessCategory
        ]

        await query.edit_message_text(
            text=Key.manage_event_access_prompt,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return SETTING_ACCESS

    async def update_event_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        selected_event = context.user_data.get("selected_event")
        selected_event.access_category = AccessCategory(query.data)

        context.user_data["selected_event"] = selected_event

        bot_message = await self.ensure_message(query)

        return await self.manage_event_main_menu(update, context, bot_message)

    async def commit_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        selected_event = context.user_data.get("selected_event")
        self.controller.update_event(selected_event)

        fields = self._event_display_fields(selected_event)
        await query.edit_message_text(text=Key.manage_event_confirm_changes_summary.format(**fields))
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
            Key.manage_event_main_menu_title.format(**ManageEventConversation._event_display_fields(event))
        )
        text_blocks.append(Key.manage_event_main_menu_instruction)

        menu_text = "\n\n".join(text_blocks)

        return menu_text

    @staticmethod
    async def ensure_message(
            query: CallbackQuery,
            placeholder_text: str = Key.manage_event_working_placeholder
    ) -> Message:
        msg = query.message

        if msg and isinstance(msg, Message):
            return msg

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
            [InlineKeyboardButton(text=Key.manage_event_set_access_button, callback_data="set_access")],
            [InlineKeyboardButton(text=Key.manage_event_confirm_changes_button, callback_data="confirm_changes")],
        ]

    def _build_time_keyboard(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        query_type: str,
    ) -> InlineKeyboardMarkup:
        raw_times = ["0800", "0900", "1130", "1300", "1330", "1400", "1500", "1800", "1900", "2200", "2330"]
        selected_event: Event | None = context.user_data.get("selected_event")
        selected_date: date | None = context.user_data.get("selected_date")

        if (
            query_type == "end"
            and selected_event
            and selected_event.start
            and selected_date
            and selected_date == selected_event.start.date()
        ):
            start_time = selected_event.start.time()
            raw_times = [
                time_text
                for time_text in raw_times
                if self._parse_time(time_text).time() >= start_time
            ]
            if not raw_times:
                raw_times = [selected_event.start.strftime("%H%M")]

        rows: List[List[InlineKeyboardButton]] = []
        for i in range(0, len(raw_times), 3):
            chunk = raw_times[i:i + 3]
            row: List[InlineKeyboardButton] = []
            for t in chunk:
                row.append(InlineKeyboardButton(text=t, callback_data=t))
            rows.append(row)
        return InlineKeyboardMarkup(rows)

    def _build_calendar_markup(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        year: int,
        month: int,
        query_type: Optional[str] = None,
        range_start: Optional[date] = None,
        range_end: Optional[date] = None,
    ) -> InlineKeyboardMarkup:
        query_type = query_type or context.user_data.get("initial_calendar_query", "start")
        markup = CalendarKeyboardMarkup.build(
            year=year,
            month=month,
            start_date=range_start,
            end_date=range_end,
        )
        extra_rows = self._extra_calendar_buttons(context, query_type)
        if extra_rows:
            markup = InlineKeyboardMarkup(list(markup.inline_keyboard) + extra_rows)
        return markup

    @staticmethod
    def _format_datetime(dt: datetime | None) -> str:
        if not dt:
            return str(Key.manage_event_not_set)
        fmt = str(Key.manage_event_datetime_format)
        return dt.strftime(fmt)

    @staticmethod
    def _event_display_fields(event: Event) -> dict[str, str]:
        description = event.description.strip() if event.description else str(Key.manage_event_no_description)
        deadline = ManageEventConversation._format_datetime(event.attendance_deadline) if event.attendance_deadline else str(Key.manage_event_no_deadline)

        return {
            "title": event.title or str(Key.manage_event_untitled),
            "description": description,
            "start": ManageEventConversation._format_datetime(event.start),
            "end": ManageEventConversation._format_datetime(event.end),
            "deadline": deadline,
            "access": event.access_category.value.title(),
            "accountable": Key.manage_event_reason_mandatory
            if event.is_accountable
            else Key.manage_event_reason_optional,
        }

    @staticmethod
    def _starting_date_for_query(context: ContextTypes.DEFAULT_TYPE, query_type: str) -> date:
        now_date = datetime.now().date()
        selected_event: Event | None = context.user_data.get("selected_event")

        if query_type in ("new", "start"):
            return now_date

        if query_type == "end" and selected_event and selected_event.start:
            return selected_event.start.date()

        if query_type == "deadline" and selected_event and selected_event.start:
            return selected_event.start.date()

        return now_date

    @staticmethod
    def _calendar_range_for_query(
        context: ContextTypes.DEFAULT_TYPE,
        query_type: Optional[str] = None,
    ) -> tuple[Optional[date], Optional[date]]:
        selected_event: Event | None = context.user_data.get("selected_event")
        query_type = query_type or context.user_data.get("initial_calendar_query", "start")
        now_date = datetime.now().date()

        if query_type in ("new", "start"):
            return now_date, None

        if query_type == "end":
            start_date = selected_event.start.date() if selected_event and selected_event.start else now_date
            return start_date, None

        if query_type == "deadline":
            start_date = selected_event.start.date() if selected_event and selected_event.start else now_date
            return None, start_date + timedelta(days=1)

        return now_date, None

    @staticmethod
    def _query_label(query_type: str) -> str:
        label_map = {
            "new": Key.manage_event_label_start,
            "start": Key.manage_event_label_start,
            "end": Key.manage_event_label_end,
            "deadline": Key.manage_event_label_deadline,
        }
        return label_map.get(query_type, Key.manage_event_label_start)

    @staticmethod
    def _parse_time(time_text: str) -> Optional[datetime]:
        """
        Parse a time string in HHMM format (optionally with a colon provided by the user).
        """
        if not time_text:
            return None

        clean = time_text.replace(":", "").strip()
        if len(clean) != 4 or not clean.isdigit():
            return None

        try:
            return datetime.strptime(clean, "%H%M")
        except ValueError:
            return None

    @staticmethod
    def _deadline_from_preset(start_dt: datetime, preset: str) -> datetime:
        if preset.endswith("d"):
            days_before = int(preset[:-1])
            target_date = start_dt.date() - timedelta(days=days_before)
            # set to end of that day (23:59)
            return datetime.combine(target_date, datetime.min.time().replace(hour=23, minute=59))
        if preset.endswith("h"):
            hours_before = int(preset[:-1])
            return start_dt - timedelta(hours=hours_before)
        if preset == "none":
            return None
        return start_dt

    def _extra_calendar_buttons(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        query_type: Optional[str] = None,
    ) -> List[List[InlineKeyboardButton]]:
        query_type = query_type or context.user_data.get("initial_calendar_query", "start")
        selected_event: Event | None = context.user_data.get("selected_event")
        buttons: List[List[InlineKeyboardButton]] = []

        if query_type in ("end", "deadline") and selected_event and selected_event.start:
            buttons.append(
                [InlineKeyboardButton(text=Key.manage_event_use_start_date_button, callback_data="use_start_date")]
            )

        if query_type == "deadline":
            preset_buttons = [
                InlineKeyboardButton(text=Key.manage_event_deadline_preset_1d, callback_data="deadline_preset:1d"),
                InlineKeyboardButton(text=Key.manage_event_deadline_preset_2d, callback_data="deadline_preset:2d"),
            ]
            preset_buttons_hours = [
                InlineKeyboardButton(text=Key.manage_event_deadline_preset_3h, callback_data="deadline_preset:3h"),
                InlineKeyboardButton(text=Key.manage_event_deadline_preset_6h, callback_data="deadline_preset:6h"),
            ]
            buttons.append(preset_buttons)
            buttons.append(preset_buttons_hours)
            buttons.append(
                [InlineKeyboardButton(text=Key.manage_event_deadline_clear_button, callback_data="deadline_preset:none")]
            )

        return buttons

    async def _prompt_time_selection(
        self,
        query: CallbackQuery,
        context: ContextTypes.DEFAULT_TYPE,
        query_label: str,
        example_time: Optional[str] = None,
    ) -> int:
        example = example_time or datetime.now().strftime("%H%M")
        query_type = context.user_data.get("initial_calendar_query", "start")
        time_message = await query.edit_message_text(
            text=Key.manage_event_set_time_prompt.format(label=query_label, example_time=example),
            reply_markup=self._build_time_keyboard(context, query_type),
        )
        context.user_data["time_message"] = time_message
        return SETTING_TIME
