from abc import ABC, abstractmethod
from telegram.ext import ConversationHandler
from services.base import BaseService

class ConversationFlow(ABC):
    """
    Abstract base class for all conversation flows in the Telegram bot.
    
    This class defines the interface that all conversation handlers must implement.
    Each conversation flow represents a specific interaction sequence with the user,
    such as attendance marking, event creation, or user registration.
    
    Attributes:
        service (BaseService): The service instance used for data operations
    """
    
    @property
    @abstractmethod
    def conversation_handler(self) -> ConversationHandler:
        """
        The conversation handler for this conversation flow.
        
        This property should define the entry points, states, and fallbacks
        for the conversation flow. It is a characteristic of the conversation
        flow rather than a method that takes arguments.
        
        Returns:
            ConversationHandler: The conversation handler instance that manages
                               the flow of conversation with the user
        """
        pass 