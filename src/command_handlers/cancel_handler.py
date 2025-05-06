from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler
import logging

logger = logging.getLogger(__name__)

class CancelHandler:
    """Handler for the /cancel command."""
    
    @staticmethod
    def get_handler() -> CommandHandler:
        """Get the cancel command handler.
        
        Returns:
            CommandHandler: The cancel command handler
        """
        return CommandHandler("cancel", CancelHandler._cancel_command)
    
    @staticmethod
    async def _cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /cancel command.
        
        Args:
            update: The update object
            context: The context object
            
        Returns:
            int: ConversationHandler.END to end any active conversation
        """
        try:
            logger.info(f"Cancel command received from user {update.effective_user.id}")
            await update.message.reply_text("Operation cancelled. See you next time!")
            logger.info("Cancel command response sent")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error in cancel command: {str(e)}", exc_info=True)
            raise 