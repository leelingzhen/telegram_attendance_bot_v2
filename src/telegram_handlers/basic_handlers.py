from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler

class BasicCommandHandlers:
    """Base class for basic command handlers that can be used across different bots."""
    
    @staticmethod
    def get_handlers():
        """Get all basic command handlers.
        
        Returns:
            list: List of command handlers
        """
        return [
            CommandHandler("start", BasicCommandHandlers._start_command),
            CommandHandler("cancel", BasicCommandHandlers._cancel_command)
        ]
    
    @staticmethod
    async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command.
        
        Args:
            update: The update object
            context: The context object
        """
        await update.message.reply_text("Hello please use the commands to talk to me")
    
    @staticmethod
    async def _cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /cancel command.
        
        Args:
            update: The update object
            context: The context object
            
        Returns:
            int: ConversationHandler.END to end any active conversation
        """
        await update.message.reply_text("process cancelled, see you next time!")
        return ConversationHandler.END 