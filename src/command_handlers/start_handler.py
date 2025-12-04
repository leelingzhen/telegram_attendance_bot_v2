from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from localization import Key
import logging

logger = logging.getLogger(__name__)

class StartHandler:
    """Handler for the /start command."""
    
    @staticmethod
    def get_handler() -> CommandHandler:
        """Get the start command handler.
        
        Returns:
            CommandHandler: The start command handler
        """
        return CommandHandler("start", StartHandler._start_command)
    
    @staticmethod
    async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command.
        
        Args:
            update: The update object
            context: The context object
        """
        try:
            logger.info(f"Start command received from user {update.effective_user.id}")
            await update.message.reply_text(Key.start_training_bot)
            logger.info("Start command response sent")
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}", exc_info=True)
            raise 