"""
Message validation logic.
"""

from ..models.message import ProcessedMessage


class MessageValidator:
    """Validates processed messages for quality."""
    
    def is_valid_message(self, message: ProcessedMessage) -> bool:
        """Check if processed message is valid for summarization."""
        return message.has_substantial_content()