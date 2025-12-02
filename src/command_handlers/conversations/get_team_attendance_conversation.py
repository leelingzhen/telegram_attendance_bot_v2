from telegram import Update
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, CallbackContext

from command_handlers.conversations.conversation_flow import ConversationFlow
from controllers.team_attendance_controller import TeamAttendanceControlling

CHOOSING_EVENT = 1

class GetTeamAttendanceConversation(ConversationFlow):
    @property
    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler("kaypoh", self.upcoming_events)],
            states={CHOOSING_EVENT: [
                CallbackQueryHandler(self.return_team_attendance),
            ]}
        )

    def __init__(self, controller: TeamAttendanceControlling):
        self.controller = controller

    async def upcoming_events(self,update: Update, context: CallbackContext) -> int:
        return CHOOSING_EVENT

    async def return_team_attendance(self,update: Update, context: CallbackContext) -> int:
        return ConversationHandler.END