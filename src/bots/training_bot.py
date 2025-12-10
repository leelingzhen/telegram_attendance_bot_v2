from bots.bot_core import BotCore
from command_handlers.conversations.get_team_attendance_conversation import GetTeamAttendanceConversation
from command_handlers.conversations.manage_event_conversation import ManageEventConversation
from command_handlers.conversations.manage_access_conversation import ManageAccessConversation
from command_handlers.start_handler import StartHandler
from command_handlers.cancel_handler import CancelHandler
from command_handlers.conversations.attendance_conversation import MarkAttendanceConversation
from command_handlers.conversations.registration_conversation import RegistrationConversation
from controllers.attendance_controller import FakeAttendanceController
from controllers.manage_event_controller import FakeManageEventController
from controllers.registration_controller import FakeRegistrationController
from controllers.manage_access_controller import FakeManageAccessController

import logging

from controllers.team_attendance_controller import FakeTeamAttendanceController

logger = logging.getLogger(__name__)

class TrainingBot:
    """
    Training bot implementation that handles attendance marking functionality.
    
    This bot is responsible for:
    1. Setting up command handlers (/start, /cancel)
    2. Setting up conversation handlers for attendance marking
    3. Managing the bot lifecycle
    """
    
    def __init__(self, token: str):
        """
        Initialize the training bot.
        
        Args:
            token: Telegram bot token
        """
        logger.info("Initializing training bot...")
        # Initialize core bot with just the token
        self.core = BotCore(token=token)
        self._setup_command_handlers()
        logger.info("Training bot initialized")
    
    def _setup_command_handlers(self):
        """Setup handlers specific to the training bot.
        
        This method:
        1. Sets up basic command handlers (/start, /cancel)
        2. Sets up the attendance marking conversation handler
        """
        logger.info("Setting up command handlers...")
        # Add command handlers
        self.core.application.add_handler(StartHandler.get_handler())
        self.core.application.add_handler(CancelHandler.get_handler())
        logger.info("Command handlers set up")
        
        # Add attendance conversation handler
        attendance_conv = MarkAttendanceConversation(controller=FakeAttendanceController())
        team_attendance_conversation = GetTeamAttendanceConversation(controller=FakeTeamAttendanceController())
        registration_conversation = RegistrationConversation(controller=FakeRegistrationController())
        manage_event_conversation = ManageEventConversation(controller=FakeManageEventController())
        manage_access_conversation = ManageAccessConversation(controller=FakeManageAccessController())

        self.core.application.add_handler(attendance_conv.conversation_handler)
        self.core.application.add_handler(team_attendance_conversation.conversation_handler)
        self.core.application.add_handler(registration_conversation.conversation_handler)
        self.core.application.add_handler(manage_event_conversation.conversation_handler)
        self.core.application.add_handler(manage_access_conversation.conversation_handler)

    def run(self):
        """Run the bot"""
        logger.info("Starting training bot...")
        self.core.run()
    
    def stop(self):
        """Stop the bot"""
        logger.info("Stopping training bot...")
        self.core.stop() 
