"""
Message content cleaning and normalization.
"""

import re
import discord
from ..models.message import ProcessedMessage, MessageType


class MessageCleaner:
    """Cleans and normalizes Discord message content."""
    
    def clean_message(self, message: discord.Message) -> ProcessedMessage:
        """Clean a Discord message into ProcessedMessage format."""
        return ProcessedMessage(
            id=str(message.id),
            author_name=message.author.display_name,
            author_id=str(message.author.id),
            content=self._clean_content(message.content or ""),
            timestamp=message.created_at,
            message_type=MessageType(message.type.value) if message.type.value < 22 else MessageType.DEFAULT,
            is_edited=message.edited_at is not None,
            is_pinned=message.pinned,
            channel_id=str(message.channel.id),
            channel_name=getattr(message.channel, 'name', None),
        )
    
    def _clean_content(self, content: str) -> str:
        """Clean message content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Keep mentions but make them readable
        content = re.sub(r'<@!?(\d+)>', r'@user', content)
        content = re.sub(r'<@&(\d+)>', r'@role', content)  
        content = re.sub(r'<#(\d+)>', r'#channel', content)
        
        # Keep custom emojis but make them readable
        content = re.sub(r'<a?:[a-zA-Z0-9_]+:(\d+)>', r':emoji:', content)
        
        return content