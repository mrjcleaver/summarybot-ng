"""
Discord API-related exceptions.
"""

from typing import Optional, List
from .base import SummaryBotException, RecoverableError, UserError, ErrorContext


class DiscordError(SummaryBotException):
    """Base class for Discord-related errors."""
    pass


class DiscordPermissionError(UserError):
    """Raised when user lacks required Discord permissions."""
    
    def __init__(self, required_permission: str, context: Optional[ErrorContext] = None):
        self.required_permission = required_permission
        
        super().__init__(
            message=f"User lacks required permission: {required_permission}",
            error_code="DISCORD_PERMISSION_DENIED",
            user_message=f"You don't have the required permission ({required_permission}) to perform this action.",
            context=context
        )


class BotPermissionError(RecoverableError):
    """Raised when bot lacks required Discord permissions."""
    
    def __init__(self, required_permissions: List[str], channel_id: str = None, 
                 context: Optional[ErrorContext] = None):
        self.required_permissions = required_permissions
        self.channel_id = channel_id
        
        permissions_text = ", ".join(required_permissions)
        location = f" in channel {channel_id}" if channel_id else ""
        
        super().__init__(
            message=f"Bot lacks required permissions{location}: {permissions_text}",
            error_code="BOT_PERMISSION_DENIED",
            context=context,
            user_message=f"I don't have the required permissions ({permissions_text}) to perform this action{location}. "
                        "Please ask a server administrator to grant these permissions."
        )


class ChannelAccessError(UserError):
    """Raised when channel cannot be accessed."""
    
    def __init__(self, channel_id: str, reason: str = "Access denied", 
                 context: Optional[ErrorContext] = None):
        self.channel_id = channel_id
        self.reason = reason
        
        super().__init__(
            message=f"Cannot access channel {channel_id}: {reason}",
            error_code="CHANNEL_ACCESS_DENIED",
            user_message=f"Cannot access the specified channel. {reason}",
            context=context
        )


class MessageFetchError(RecoverableError):
    """Raised when message fetching fails."""
    
    def __init__(self, channel_id: str, error_details: str, 
                 context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        self.channel_id = channel_id
        self.error_details = error_details
        
        super().__init__(
            message=f"Failed to fetch messages from channel {channel_id}: {error_details}",
            error_code="MESSAGE_FETCH_FAILED",
            context=context,
            user_message="Failed to fetch messages from the channel. This might be due to permissions or connectivity issues."
        )
        self.cause = cause


class RateLimitExceededError(RecoverableError):
    """Raised when Discord API rate limit is exceeded."""
    
    def __init__(self, retry_after: float, context: Optional[ErrorContext] = None):
        self.retry_after = retry_after
        
        super().__init__(
            message=f"Discord API rate limit exceeded, retry after {retry_after} seconds",
            error_code="DISCORD_RATE_LIMIT",
            context=context,
            user_message=f"Discord API rate limit reached. Please wait {int(retry_after)} seconds before trying again."
        )


class GuildNotFoundError(UserError):
    """Raised when guild (server) is not found or not accessible."""
    
    def __init__(self, guild_id: str, context: Optional[ErrorContext] = None):
        self.guild_id = guild_id
        
        super().__init__(
            message=f"Guild {guild_id} not found or not accessible",
            error_code="GUILD_NOT_FOUND",
            user_message="Server not found or the bot is not a member of this server.",
            context=context
        )


class ChannelNotFoundError(UserError):
    """Raised when channel is not found or not accessible."""
    
    def __init__(self, channel_id: str, context: Optional[ErrorContext] = None):
        self.channel_id = channel_id
        
        super().__init__(
            message=f"Channel {channel_id} not found or not accessible",
            error_code="CHANNEL_NOT_FOUND",
            user_message="Channel not found or not accessible. It might be deleted or I don't have access to it.",
            context=context
        )


class InvalidMessageRangeError(UserError):
    """Raised when message time range is invalid."""
    
    def __init__(self, start_time: str, end_time: str, context: Optional[ErrorContext] = None):
        self.start_time = start_time
        self.end_time = end_time
        
        super().__init__(
            message=f"Invalid message range: {start_time} to {end_time}",
            error_code="INVALID_MESSAGE_RANGE",
            user_message="Invalid time range specified. Start time must be before end time.",
            context=context
        )


class MessageTooOldError(UserError):
    """Raised when trying to access messages that are too old."""
    
    def __init__(self, days_old: int, max_days: int = 90, context: Optional[ErrorContext] = None):
        self.days_old = days_old
        self.max_days = max_days
        
        super().__init__(
            message=f"Messages are {days_old} days old, exceeding limit of {max_days} days",
            error_code="MESSAGES_TOO_OLD",
            user_message=f"Messages are too old to access ({days_old} days). "
                        f"I can only access messages from the last {max_days} days.",
            context=context
        )


class ThreadAccessError(UserError):
    """Raised when thread cannot be accessed."""
    
    def __init__(self, thread_id: str, reason: str = "Access denied", 
                 context: Optional[ErrorContext] = None):
        self.thread_id = thread_id
        self.reason = reason
        
        super().__init__(
            message=f"Cannot access thread {thread_id}: {reason}",
            error_code="THREAD_ACCESS_DENIED",
            user_message=f"Cannot access the specified thread. {reason}",
            context=context
        )