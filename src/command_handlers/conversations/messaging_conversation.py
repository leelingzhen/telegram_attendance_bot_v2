import logging
from datetime import datetime
from typing import List, Optional, Tuple

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from command_handlers.conversations.conversation_flow import ConversationFlow
from localization import Key
from models.models import Event, User
from providers.messaging_provider import MessagingProviding

SELECT_EVENT = 1
COLLECT_MESSAGE = 2
CONFIRM_MESSAGE = 3
logger = logging.getLogger(__name__)


class MessagingConversation(ConversationFlow):
    """
    Conversation flows for messaging-related commands:
      - /remind: choose an event then send reminders
      - /announce: collect a message and send to all
      - /announce_event: choose an event, collect a message, then send
    """

    def __init__(self, messaging_provider: MessagingProviding):
        self.messaging_provider = messaging_provider

    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("remind", self.start_send_reminders),
                CommandHandler("announce", self.start_announce),
                CommandHandler("announce_event", self.start_announce_event),
            ],
            states={
                SELECT_EVENT: [CallbackQueryHandler(self.event_selected)],
                COLLECT_MESSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_collected),
                ],
                CONFIRM_MESSAGE: [
                    CallbackQueryHandler(self.message_confirmed, pattern="^(confirm|edit|cancel)$"),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            allow_reentry=True,
            per_message=False,
        )

    async def start_send_reminders(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["mode"] = "reminders"
        return await self._prompt_event_selection(update, context)

    async def start_announce_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["mode"] = "announce_event"
        return await self._prompt_event_selection(update, context)

    async def start_announce(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["mode"] = "announce"
        await update.message.reply_text(Key.messaging_announce_prompt)
        return COLLECT_MESSAGE

    async def _prompt_event_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        events = await self.messaging_provider.retrieve_events(datetime.now())
        context.user_data["events"] = events

        if not events:
            await update.message.reply_text(Key.no_upcoming_events_found)
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton(
                    f"{event.title} — {self._format_datetime(event.start)}",
                    callback_data=str(event.id),
                )
            ]
            for event in events
        ]
        await update.message.reply_text(
            Key.choose_event_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_EVENT

    async def event_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        event_id = int(query.data)
        events: List[Event] = context.user_data.get("events", [])
        selected_event = next((evt for evt in events if evt.id == event_id), None)

        if not selected_event:
            await query.edit_message_text("Event not found.")
            return ConversationHandler.END

        context.user_data["selected_event"] = selected_event
        mode = context.user_data.get("mode")

        if mode == "reminders":
            progress_message = await query.edit_message_text(Key.messaging_sending_reminders)
            on_progress = self._make_progress_callback(
                progress_message=progress_message,
                label=Key.messaging_sending_reminders,
                percent_step=30,
            )

            failed = await self.messaging_provider.send_reminders(selected_event, on_progress=on_progress)
            if failed:
                failed_list = self._format_failed_users(failed)
                await progress_message.edit_text(
                    Key.messaging_reminders_failed.format(failed_list=failed_list)
                )
            else:
                await progress_message.edit_text(
                    Key.messaging_reminders_sent.format(event_title=selected_event.title)
                )
            return ConversationHandler.END

        await query.edit_message_text(
            Key.messaging_announce_event_prompt.format(event_title=selected_event.title)
        )
        return COLLECT_MESSAGE

    async def message_collected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text, parse_mode, entities = self._extract_message_payload(update)
        context.user_data["pending_message"] = (text, parse_mode, entities)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Send", callback_data="confirm"),
                    InlineKeyboardButton("Edit", callback_data="edit"),
                ],
                [InlineKeyboardButton("Cancel", callback_data="cancel")],
            ]
        )
        preview = f"{text}\n\nConfirm send?"
        await update.message.reply_text(
            preview,
            reply_markup=keyboard,
            parse_mode=parse_mode,
            entities=entities,
        )
        return CONFIRM_MESSAGE

    async def message_confirmed(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        await query.answer()
        action = query.data

        if action == "cancel":
            await query.edit_message_text(Key.operation_cancelled)
            return ConversationHandler.END

        if action == "edit":
            await query.edit_message_text(Key.messaging_edit_prompt)
            return COLLECT_MESSAGE

        pending_message: Tuple[str, Optional[str], Optional[Tuple]] = context.user_data.get("pending_message", ("", None, None))
        pending_text, pending_parse_mode, pending_entities = pending_message
        mode = context.user_data.get("mode")
        event: Optional[Event] = context.user_data.get("selected_event")

        from_user = self._from_handle(update)
        progress_message = await query.edit_message_text(Key.messaging_sending_announcement)
        on_progress = self._make_progress_callback(
            progress_message=progress_message,
            label=Key.messaging_sending_announcement,
            percent_step=30,
        )

        if mode == "announce_event":
            failed = await self.messaging_provider.send_announcement(
                from_user,
                pending_text,
                event,
                parse_mode=pending_parse_mode,
                entities=pending_entities,
                on_progress=on_progress,
            )
            await progress_message.edit_text(
                Key.messaging_announcement_sent_for_event.format(event_title=event.title)
                if not failed
                else Key.messaging_announcement_failed.format(
                    failed_list=self._format_failed_users(failed)
                )
            )
        else:
            failed = await self.messaging_provider.send_announcement(
                from_user,
                pending_text,
                parse_mode=pending_parse_mode,
                entities=pending_entities,
                on_progress=on_progress,
            )
            await progress_message.edit_text(
                Key.messaging_announcement_sent
                if not failed
                else Key.messaging_announcement_failed.format(
                    failed_list=self._format_failed_users(failed)
                )
            )

        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Cancelled.")
        return ConversationHandler.END

    def _from_handle(self, update: Update) -> str:
        tg_user = update.effective_user
        handle = tg_user.username or (tg_user.full_name or "").replace(" ", "_") or str(tg_user.id)
        return handle

    def _format_datetime(self, dt: datetime) -> str:
        return dt.strftime("%d-%b-%y, %a @ %I:%M%p")

    def _extract_message_payload(
        self, update: Update
    ) -> Tuple[str, Optional[str], Optional[Tuple]]:
        msg = update.message
        text = msg.text or ""
        entities = msg.entities if msg.entities else None
        return text, None, entities

    def _format_failed_users(self, users: List[User]) -> str:
        handles = []
        for user in users:
            handle = getattr(user, "telegram_user", None)
            if handle:
                handle = handle.lstrip("@")
                handles.append(f"@{handle}")
            elif hasattr(user, "telegram_handle"):
                handles.append(user.telegram_handle)
            else:
                handles.append(str(user.id))
        return ", ".join(handles)

    def _make_progress_callback(
        self,
        progress_message,
        label: str,
        percent_step: int = 30,
    ):
        """
        Create a throttled progress callback that updates the given message.
        """
        last_percent = 0

        async def on_progress(done: int, total: int):
            nonlocal last_percent
            percent = int(done * 100 / total) if total else 100
            if percent - last_percent >= percent_step or done == total:
                last_percent = percent
                try:
                    await progress_message.edit_text(
                        f"{label}... {done}/{total} complete"
                    )
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Progress update failed: %s", exc)

        return on_progress
