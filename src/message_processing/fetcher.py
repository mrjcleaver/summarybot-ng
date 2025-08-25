"""
Discord message fetching functionality.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, AsyncGenerator
import discord

from ..exceptions import (
    MessageFetchError, ChannelAccessError, RateLimitExceededError,
    create_error_context
)


class MessageFetcher:
    """Fetches messages from Discord channels with proper error handling."""
    
    def __init__(self, discord_client: discord.Client, rate_limit_delay: float = 0.1):
        """Initialize message fetcher.
        
        Args:
            discord_client: Discord client instance
            rate_limit_delay: Delay between requests to avoid rate limits
        """
        self.client = discord_client
        self.rate_limit_delay = rate_limit_delay
        
    async def fetch_messages(self,
                           channel_id: str,
                           start_time: datetime,
                           end_time: datetime,
                           limit: Optional[int] = None) -> List[discord.Message]:
        """Fetch messages from a channel within a time range.
        
        Args:
            channel_id: Discord channel ID
            start_time: Start of time range
            end_time: End of time range
            limit: Optional limit on number of messages
            
        Returns:
            List of Discord messages
            
        Raises:
            ChannelAccessError: If channel cannot be accessed
            MessageFetchError: If message fetching fails
            RateLimitExceededError: If rate limit is exceeded
        """
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                # Try fetching channel
                channel = await self.client.fetch_channel(int(channel_id))
            
            if not channel:
                raise ChannelAccessError(
                    channel_id=channel_id,
                    reason="Channel not found or not accessible",
                    context=create_error_context(channel_id=channel_id, operation="fetch_channel")
                )
            
            # Check if we can read messages
            if isinstance(channel, discord.TextChannel):
                if not channel.permissions_for(channel.guild.me).read_message_history:
                    raise ChannelAccessError(
                        channel_id=channel_id,
                        reason="Bot lacks permission to read message history",
                        context=create_error_context(
                            channel_id=channel_id,
                            guild_id=str(channel.guild.id),
                            operation="check_permissions"
                        )
                    )
            
            messages = []
            async for message in self._fetch_messages_with_pagination(channel, start_time, end_time, limit):
                messages.append(message)
                
                # Apply rate limiting
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
            
            return messages
            
        except discord.Forbidden as e:
            raise ChannelAccessError(
                channel_id=channel_id,
                reason="Access forbidden by Discord",
                context=create_error_context(channel_id=channel_id, operation="fetch_messages")
            )
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = getattr(e, 'retry_after', 60)
                raise RateLimitExceededError(
                    retry_after=retry_after,
                    context=create_error_context(channel_id=channel_id, operation="fetch_messages")
                )
            else:
                raise MessageFetchError(
                    channel_id=channel_id,
                    error_details=f"HTTP {e.status}: {e.text}",
                    context=create_error_context(channel_id=channel_id, operation="fetch_messages"),
                    cause=e
                )
        except Exception as e:
            raise MessageFetchError(
                channel_id=channel_id,
                error_details=str(e),
                context=create_error_context(channel_id=channel_id, operation="fetch_messages"),
                cause=e
            )
    
    async def fetch_thread_messages(self,
                                  thread_id: str,
                                  include_parent: bool = True,
                                  limit: Optional[int] = None) -> List[discord.Message]:
        """Fetch messages from a thread.
        
        Args:
            thread_id: Discord thread ID
            include_parent: Whether to include the parent message
            limit: Optional limit on number of messages
            
        Returns:
            List of Discord messages from the thread
        """
        try:
            thread = self.client.get_channel(int(thread_id))
            if not thread:
                thread = await self.client.fetch_channel(int(thread_id))
            
            if not isinstance(thread, discord.Thread):
                raise MessageFetchError(
                    channel_id=thread_id,
                    error_details="Channel is not a thread",
                    context=create_error_context(channel_id=thread_id, operation="fetch_thread")
                )
            
            messages = []
            
            # Add parent message if requested
            if include_parent and thread.starter_message:
                messages.append(thread.starter_message)
            elif include_parent:
                # Fetch starter message if not cached
                try:
                    starter = await thread.parent.fetch_message(thread.id)
                    messages.append(starter)
                except discord.NotFound:
                    pass  # Starter message might be deleted
            
            # Fetch thread messages
            count = 0
            async for message in thread.history(limit=None, oldest_first=True):
                if limit and count >= limit:
                    break
                messages.append(message)
                count += 1
                
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
            
            return messages
            
        except Exception as e:
            raise MessageFetchError(
                channel_id=thread_id,
                error_details=str(e),
                context=create_error_context(channel_id=thread_id, operation="fetch_thread_messages"),
                cause=e
            )
    
    async def fetch_around_message(self,
                                 channel_id: str,
                                 message_id: str,
                                 context_size: int = 10) -> List[discord.Message]:
        """Fetch messages around a specific message for context.
        
        Args:
            channel_id: Discord channel ID
            message_id: Target message ID
            context_size: Number of messages before and after to fetch
            
        Returns:
            List of messages around the target message
        """
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                channel = await self.client.fetch_channel(int(channel_id))
            
            target_message = await channel.fetch_message(int(message_id))
            
            messages = []
            
            # Fetch messages before
            async for message in channel.history(limit=context_size, before=target_message, oldest_first=False):
                messages.append(message)
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
            
            # Reverse to get chronological order
            messages.reverse()
            
            # Add target message
            messages.append(target_message)
            
            # Fetch messages after
            async for message in channel.history(limit=context_size, after=target_message, oldest_first=True):
                messages.append(message)
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
            
            return messages
            
        except discord.NotFound:
            raise MessageFetchError(
                channel_id=channel_id,
                error_details=f"Message {message_id} not found",
                context=create_error_context(
                    channel_id=channel_id,
                    operation="fetch_around_message",
                    message_id=message_id
                )
            )
        except Exception as e:
            raise MessageFetchError(
                channel_id=channel_id,
                error_details=str(e),
                context=create_error_context(
                    channel_id=channel_id,
                    operation="fetch_around_message",
                    message_id=message_id
                ),
                cause=e
            )
    
    async def _fetch_messages_with_pagination(self,
                                            channel: discord.TextChannel,
                                            start_time: datetime,
                                            end_time: datetime,
                                            limit: Optional[int] = None) -> AsyncGenerator[discord.Message, None]:
        """Fetch messages with proper pagination and time filtering."""
        total_fetched = 0
        
        # Use discord.py's history method with time-based filtering
        async for message in channel.history(
            limit=None,
            before=end_time,
            after=start_time,
            oldest_first=True
        ):
            if limit and total_fetched >= limit:
                break
                
            # Double-check time bounds (discord.py filtering isn't always precise)
            if start_time <= message.created_at <= end_time:
                yield message
                total_fetched += 1
    
    async def get_channel_info(self, channel_id: str) -> dict:
        """Get basic information about a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Dictionary with channel information
        """
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                channel = await self.client.fetch_channel(int(channel_id))
            
            info = {
                "id": str(channel.id),
                "name": channel.name,
                "type": str(channel.type),
                "created_at": channel.created_at,
            }
            
            if hasattr(channel, 'guild'):
                info["guild_id"] = str(channel.guild.id)
                info["guild_name"] = channel.guild.name
            
            if hasattr(channel, 'topic'):
                info["topic"] = channel.topic
            
            if hasattr(channel, 'category'):
                info["category"] = channel.category.name if channel.category else None
            
            return info
            
        except Exception as e:
            raise MessageFetchError(
                channel_id=channel_id,
                error_details=f"Failed to get channel info: {str(e)}",
                context=create_error_context(channel_id=channel_id, operation="get_channel_info"),
                cause=e
            )