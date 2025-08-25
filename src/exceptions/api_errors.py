"""
External API-related exceptions.
"""

from typing import Optional, Dict, Any
from .base import SummaryBotException, RecoverableError, ErrorContext


class APIError(SummaryBotException):
    """Base class for external API errors."""
    
    def __init__(self, message: str, error_code: str, api_name: str,
                 status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None,
                 context: Optional[ErrorContext] = None, retryable: bool = True):
        self.api_name = api_name
        self.status_code = status_code
        self.response_data = response_data or {}
        
        super().__init__(
            message=f"{api_name} API error: {message}",
            error_code=error_code,
            context=context,
            user_message=f"External service ({api_name}) is currently unavailable. Please try again later.",
            retryable=retryable
        )


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    
    def __init__(self, api_name: str, details: str = "", context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Authentication failed: {details}",
            error_code="API_AUTH_FAILED",
            api_name=api_name,
            status_code=401,
            context=context,
            retryable=False
        )
        self.user_message = "Service authentication failed. Please contact support."


class RateLimitError(RecoverableError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, api_name: str, retry_after: Optional[int] = None,
                 limit_type: str = "requests", context: Optional[ErrorContext] = None):
        self.api_name = api_name
        self.retry_after = retry_after
        self.limit_type = limit_type
        
        retry_text = f" Retry after {retry_after} seconds." if retry_after else ""
        
        super().__init__(
            message=f"{api_name} {limit_type} rate limit exceeded.{retry_text}",
            error_code="API_RATE_LIMIT",
            context=context,
            user_message=f"Rate limit reached for {api_name}. Please wait a moment and try again."
        )


class NetworkError(RecoverableError):
    """Raised when network connectivity issues occur."""
    
    def __init__(self, api_name: str, details: str, context: Optional[ErrorContext] = None):
        self.api_name = api_name
        self.details = details
        
        super().__init__(
            message=f"Network error connecting to {api_name}: {details}",
            error_code="NETWORK_ERROR",
            context=context,
            user_message=f"Network connectivity issue with {api_name}. Please try again in a moment."
        )


class TimeoutError(RecoverableError):
    """Raised when API request times out."""
    
    def __init__(self, api_name: str, timeout_seconds: int, context: Optional[ErrorContext] = None):
        self.api_name = api_name
        self.timeout_seconds = timeout_seconds
        
        super().__init__(
            message=f"{api_name} request timed out after {timeout_seconds} seconds",
            error_code="API_TIMEOUT",
            context=context,
            user_message=f"Request to {api_name} timed out. Please try again."
        )


class ServiceUnavailableError(RecoverableError):
    """Raised when external service is unavailable."""
    
    def __init__(self, api_name: str, status_code: int = 503, 
                 context: Optional[ErrorContext] = None):
        self.api_name = api_name
        self.status_code = status_code
        
        super().__init__(
            message=f"{api_name} service unavailable (status {status_code})",
            error_code="SERVICE_UNAVAILABLE",
            context=context,
            user_message=f"{api_name} is temporarily unavailable. Please try again later."
        )


class QuotaExceededError(APIError):
    """Raised when API quota is exceeded."""
    
    def __init__(self, api_name: str, quota_type: str = "requests", 
                 reset_time: Optional[str] = None, context: Optional[ErrorContext] = None):
        self.quota_type = quota_type
        self.reset_time = reset_time
        
        reset_text = f" Quota resets at {reset_time}." if reset_time else ""
        
        super().__init__(
            message=f"{api_name} {quota_type} quota exceeded.{reset_text}",
            error_code="QUOTA_EXCEEDED",
            api_name=api_name,
            context=context,
            retryable=bool(reset_time)
        )
        
        if reset_time:
            self.user_message = f"Daily quota for {api_name} has been exceeded. Please try again later."
        else:
            self.user_message = f"Quota for {api_name} has been exceeded. Please contact support."


class InvalidResponseError(APIError):
    """Raised when API returns invalid or unexpected response."""
    
    def __init__(self, api_name: str, expected: str, received: str,
                 context: Optional[ErrorContext] = None):
        self.expected = expected
        self.received = received
        
        super().__init__(
            message=f"Invalid response from {api_name}: expected {expected}, got {received}",
            error_code="INVALID_API_RESPONSE",
            api_name=api_name,
            context=context,
            retryable=True
        )


class PayloadTooLargeError(APIError):
    """Raised when request payload exceeds API limits."""
    
    def __init__(self, api_name: str, payload_size: int, max_size: int,
                 context: Optional[ErrorContext] = None):
        self.payload_size = payload_size
        self.max_size = max_size
        
        super().__init__(
            message=f"Payload too large for {api_name}: {payload_size} bytes (max {max_size})",
            error_code="PAYLOAD_TOO_LARGE",
            api_name=api_name,
            status_code=413,
            context=context,
            retryable=False
        )
        
        self.user_message = "Request is too large. Please try with fewer messages or shorter content."