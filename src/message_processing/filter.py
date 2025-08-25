"""
Message filtering logic.
"""

from typing import List
import discord
from ..models.summary import SummaryOptions


class MessageFilter:
    """Filters Discord messages based on summarization options."""
    
    def filter_messages(self, 
                       messages: List[discord.Message],
                       options: SummaryOptions) -> List[discord.Message]:
        """Filter messages based on options."""
        filtered = []
        
        for message in messages:
            if self._should_include_message(message, options):
                filtered.append(message)
        
        # Sort by timestamp to maintain chronological order
        filtered.sort(key=lambda m: m.created_at)
        return filtered
    
    def _should_include_message(self, 
                               message: discord.Message,
                               options: SummaryOptions) -> bool:
        """Check if message should be included."""
        # Skip bot messages unless explicitly included
        if message.author.bot and not options.include_bots:
            return False
        
        # Skip system messages
        if message.type not in [discord.MessageType.default, discord.MessageType.reply]:
            return False
        
        # Skip empty messages without attachments
        if not message.content and not message.attachments:
            return False
        
        # Skip messages from excluded users
        if str(message.author.id) in options.excluded_users:
            return False
        
        return True