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
        self.application = Application.builder().token(token).build()
        logger.info("Bot core initialized")
    
    def run(self):
        """Run the bot"""
        logger.info("Starting bot...")
        self.application.run_polling()
    
    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        self.application.stop() 