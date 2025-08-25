"""
Summarization-specific exceptions.
"""

from typing import Optional
from .base import SummaryBotException, RecoverableError, UserError, ErrorContext


class SummarizationError(SummaryBotException):
    """Base class for summarization-related errors."""
    pass


class ClaudeAPIError(RecoverableError):
    """Error when Claude API call fails."""
    
    def __init__(self, message: str, api_error_code: Optional[str] = None, 
                 context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        self.api_error_code = api_error_code
        
        # Determine user message based on API error
        user_message = self._get_user_message_for_api_error(api_error_code, message)
        
        super().__init__(
            message=f"Claude API error: {message}",
            error_code="CLAUDE_API_ERROR",
            context=context,
            user_message=user_message
        )
        self.cause = cause
    
    def _get_user_message_for_api_error(self, api_error_code: Optional[str], message: str) -> str:
        """Get user-friendly message based on API error code."""
        error_messages = {
            "rate_limit_exceeded": "Too many requests to the AI service. Please wait a moment and try again.",
            "authentication_failed": "AI service authentication failed. Please contact support.",
            "model_overloaded": "AI service is temporarily overloaded. Please try again in a few minutes.",
            "content_policy_violation": "The content couldn't be summarized due to policy restrictions.",
            "token_limit_exceeded": "The content is too long to summarize. Please try with fewer messages.",
            "service_unavailable": "AI service is temporarily unavailable. Please try again later."
        }
        
        return error_messages.get(api_error_code, 
                                "AI summarization service encountered an error. Please try again.")


class InsufficientContentError(UserError):
    """Raised when there's not enough content to summarize."""
    
    def __init__(self, message_count: int, min_required: int, context: Optional[ErrorContext] = None):
        self.message_count = message_count
        self.min_required = min_required
        
        super().__init__(
            message=f"Insufficient content: {message_count} messages (minimum {min_required} required)",
            error_code="INSUFFICIENT_CONTENT",
            user_message=f"Not enough messages to summarize. Found {message_count} messages, "
                        f"but at least {min_required} are required for a meaningful summary.",
            context=context
        )


class PromptTooLongError(RecoverableError):
    """Raised when the prompt exceeds API limits."""
    
    def __init__(self, prompt_length: int, max_length: int, context: Optional[ErrorContext] = None):
        self.prompt_length = prompt_length
        self.max_length = max_length
        
        super().__init__(
            message=f"Prompt too long: {prompt_length} tokens (max {max_length})",
            error_code="PROMPT_TOO_LONG",
            context=context,
            user_message="The content is too long to summarize in one request. "
                        "Try summarizing a shorter time period or fewer messages."
        )


class TokenLimitExceededError(RecoverableError):
    """Raised when response token limit is exceeded."""
    
    def __init__(self, context: Optional[ErrorContext] = None):
        super().__init__(
            message="Claude API response exceeded token limit",
            error_code="TOKEN_LIMIT_EXCEEDED",
            context=context,
            user_message="The summary was too long for the AI to generate completely. "
                        "Try requesting a shorter summary or fewer messages."
        )


class ContentFilterError(UserError):
    """Raised when content violates filtering rules."""
    
    def __init__(self, reason: str, context: Optional[ErrorContext] = None):
        self.reason = reason
        
        super().__init__(
            message=f"Content filtered: {reason}",
            error_code="CONTENT_FILTERED",
            user_message="The content couldn't be summarized due to content policy restrictions.",
            context=context
        )


class SummaryGenerationError(SummarizationError):
    """Raised when summary generation fails for unknown reasons."""
    
    def __init__(self, stage: str, details: str, context: Optional[ErrorContext] = None):
        self.stage = stage
        self.details = details
        
        super().__init__(
            message=f"Summary generation failed at stage '{stage}': {details}",
            error_code="SUMMARY_GENERATION_FAILED",
            context=context,
            user_message="Summary generation failed. Please try again or contact support if the problem persists.",
            retryable=True
        )


class ModelUnavailableError(RecoverableError):
    """Raised when the requested Claude model is unavailable."""
    
    def __init__(self, model_name: str, context: Optional[ErrorContext] = None):
        self.model_name = model_name
        
        super().__init__(
            message=f"Claude model '{model_name}' is unavailable",
            error_code="MODEL_UNAVAILABLE",
            context=context,
            user_message=f"The requested AI model ({model_name}) is currently unavailable. "
                        "Using the default model instead."
        )