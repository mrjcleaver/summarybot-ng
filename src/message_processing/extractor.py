"""
Information extraction from Discord messages.
"""

import discord
from ..models.message import ProcessedMessage, AttachmentInfo


class MessageExtractor:
    """Extracts additional information from Discord messages."""
    
    def extract_information(self, 
                          processed: ProcessedMessage,
                          original: discord.Message) -> ProcessedMessage:
        """Extract additional information from original Discord message."""
        # Extract attachments
        if original.attachments:
            processed.attachments = [
                AttachmentInfo.from_discord_attachment(att)
                for att in original.attachments
            ]
        
        # Extract code blocks
        processed.code_blocks = processed.extract_code_blocks()
        
        # Count embeds and reactions
        processed.embeds_count = len(original.embeds)
        processed.reactions_count = len(original.reactions)
        
        return processed