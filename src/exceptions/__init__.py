"""
Custom exception hierarchy for Summary Bot NG.

This module provides structured error handling with context-aware exceptions
and proper error reporting capabilities.
"""

from .base import SummaryBotException, ErrorContext
from .summarization import (
    SummarizationError, ClaudeAPIError, InsufficientContentError,
    PromptTooLongError, TokenLimitExceededError
)
from .discord_errors import (
    DiscordPermissionError, ChannelAccessError, MessageFetchError,
    BotPermissionError, RateLimitExceededError
)
from .api_errors import (
    APIError, AuthenticationError, RateLimitError, 
    NetworkError, TimeoutError
)
from .validation import (
    ValidationError, ConfigurationError, InvalidInputError,
    MissingRequiredFieldError
)
from .webhook import WebhookError, WebhookAuthError, WebhookDeliveryError

__all__ = [
    # Base exceptions
    'SummaryBotException',
    'ErrorContext',
    
    # Summarization errors
    'SummarizationError',
    'ClaudeAPIError', 
    'InsufficientContentError',
    'PromptTooLongError',
    'TokenLimitExceededError',
    
    # Discord errors
    'DiscordPermissionError',
    'ChannelAccessError',
    'MessageFetchError',
    'BotPermissionError',
    'RateLimitExceededError',
    
    # API errors
    'APIError',
    'AuthenticationError',
    'RateLimitError',
    'NetworkError',
    'TimeoutError',
    
    # Validation errors
    'ValidationError',
    'ConfigurationError',
    'InvalidInputError',
    'MissingRequiredFieldError',
    
    # Webhook errors
    'WebhookError',
    'WebhookAuthError',
    'WebhookDeliveryError'
]