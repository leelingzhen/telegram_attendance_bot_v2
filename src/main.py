import os
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = str(Path(__file__).parent)
if src_dir not in sys.path:
    sys.path.append(src_dir)

from dotenv import load_dotenv
from bots.training_bot import TrainingBot
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Load environment variables
    load_dotenv()
    
    # Get bot token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    logger.debug(f"Token value: {token}")
    
    if not token:
        logger.error("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # Create and run bot
    bot = TrainingBot(token)
    logger.info("Starting bot...")
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 