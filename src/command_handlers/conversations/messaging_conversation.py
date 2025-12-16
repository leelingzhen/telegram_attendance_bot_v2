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
from models.models import Event, User
from providers.messaging_provider import MessagingProviding

SELECT_EVENT = 1
COLLECT_MESSAGE = 2
CONFIRM_MESSAGE = 3


class MessagingConversation(ConversationFlow):
    """
    Conversation flows for messaging-related commands:
      - /send_reminders: choose an event then send reminders
      - /announce: collect a message and send to all
      - /announce_event: choose an event, collect a message, then send
    """

    def __init__(self, messaging_provider: MessagingProviding):
        self.messaging_provider = messaging_provider

    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("send_reminders", self.start_send_reminders),
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
        await update.message.reply_text("Send the announcement message.")
        return COLLECT_MESSAGE

    async def _prompt_event_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        events = await self.messaging_provider.retrieve_events(datetime.now())
        context.user_data["events"] = events

        if not events:
            await update.message.reply_text("No upcoming events found.")
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
            "Choose an event:",
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
            failed = await self.messaging_provider.send_reminders(selected_event)
            if failed:
                failed_list = self._format_failed_users(failed)
                await query.edit_message_text(
                    f"Reminders sent with failures to: {failed_list}"
                )
            else:
                await query.edit_message_text(f"Reminders sent for {selected_event.title}.")
            return ConversationHandler.END

        await query.edit_message_text(f"Send the announcement message for {selected_event.title}.")
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
            await query.edit_message_text("Cancelled.")
            return ConversationHandler.END

        if action == "edit":
            await query.edit_message_text("Send the updated message.")
            return COLLECT_MESSAGE

        pending_message: Tuple[str, Optional[str], Optional[Tuple]] = context.user_data.get("pending_message", ("", None, None))
        pending_text, pending_parse_mode, pending_entities = pending_message
        mode = context.user_data.get("mode")
        event: Optional[Event] = context.user_data.get("selected_event")

        from_user = self._from_handle(update)
        if mode == "announce_event":
            failed = await self.messaging_provider.send_announcement(
                from_user,
                pending_text,
                event,
                parse_mode=pending_parse_mode,
                entities=pending_entities,
            )
            await query.edit_message_text(
                f"Announcement sent for {event.title}."
                if not failed
                else f"Announcement sent with failures to: {self._format_failed_users(failed)}"
            )
        else:
            failed = await self.messaging_provider.send_announcement(
                from_user,
                pending_text,
                parse_mode=pending_parse_mode,
                entities=pending_entities,
            )
            await query.edit_message_text(
                "Announcement sent."
                if not failed
                else f"Announcement sent with failures to: {self._format_failed_users(failed)}"
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
