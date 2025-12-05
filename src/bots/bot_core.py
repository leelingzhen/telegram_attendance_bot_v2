from telegram import BotCommand
from telegram.ext import Application
import logging

logger = logging.getLogger(__name__)

class BotCore:
    """
    Core bot implementation with common functionality.
    
    This class handles:
    1. Bot initialization
    2. Application setup
    3. Basic error handling
    """
    
    def __init__(self, token: str):
        """
        Initialize the bot core.
        
        Args:
            token: Telegram bot token
        """
        logger.info("Initializing bot core...")
        builder = Application.builder().token(token)
        builder.post_init(self._register_bot_commands)
        self.application = builder.build()
        logger.info("Bot core initialized")
    
    def run(self):
        """Run the bot"""
        logger.info("Starting bot...")
        self.application.run_polling()

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        self.application.stop()

    async def _register_bot_commands(self, application: Application):
        """Register bot commands once the application is ready."""

        bot_commands = [
            BotCommand("start", "[Public] to start the bot"),
            BotCommand("cancel", "[Public] cancel/clear any process"),
            BotCommand("attendance", "[Guest and above] update attendance"),
            BotCommand("kaypoh", "[Member] Your friend never go u dw go is it??"),
            BotCommand("register", "[Public] register your details"),
        ]

        await application.bot.set_my_commands(commands=bot_commands)
