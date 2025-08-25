"""
Webhook-related exceptions.
"""

from typing import Optional, Dict, Any
from .base import SummaryBotException, RecoverableError, UserError, ErrorContext


class WebhookError(SummaryBotException):
    """Base class for webhook-related errors."""
    pass


class WebhookAuthError(UserError):
    """Raised when webhook authentication fails."""
    
    def __init__(self, reason: str = "Authentication failed", 
                 context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Webhook authentication error: {reason}",
            error_code="WEBHOOK_AUTH_FAILED",
            user_message="Webhook authentication failed. Please check your credentials.",
            context=context
        )


class WebhookDeliveryError(RecoverableError):
    """Raised when webhook delivery fails."""
    
    def __init__(self, webhook_url: str, status_code: Optional[int] = None,
                 error_details: str = "", context: Optional[ErrorContext] = None):
        self.webhook_url = webhook_url
        self.status_code = status_code
        self.error_details = error_details
        
        message_parts = [f"Webhook delivery failed to {webhook_url}"]
        if status_code:
            message_parts.append(f"Status: {status_code}")
        if error_details:
            message_parts.append(f"Details: {error_details}")
        
        super().__init__(
            message=" - ".join(message_parts),
            error_code="WEBHOOK_DELIVERY_FAILED",
            context=context,
            user_message="Webhook delivery failed. The endpoint might be temporarily unavailable."
        )


class InvalidWebhookPayloadError(UserError):
    """Raised when webhook payload is invalid."""
    
    def __init__(self, missing_fields: list = None, invalid_fields: Dict[str, str] = None,
                 context: Optional[ErrorContext] = None):
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or {}
        
        error_parts = []
        if self.missing_fields:
            error_parts.append(f"Missing fields: {', '.join(self.missing_fields)}")
        if self.invalid_fields:
            invalid_details = [f"{field}: {reason}" for field, reason in self.invalid_fields.items()]
            error_parts.append(f"Invalid fields: {'; '.join(invalid_details)}")
        
        error_message = " | ".join(error_parts) if error_parts else "Invalid payload format"
        
        super().__init__(
            message=f"Invalid webhook payload: {error_message}",
            error_code="INVALID_WEBHOOK_PAYLOAD",
            user_message=f"Invalid webhook payload: {error_message}",
            context=context
        )


class WebhookTimeoutError(RecoverableError):
    """Raised when webhook request times out."""
    
    def __init__(self, webhook_url: str, timeout_seconds: int,
                 context: Optional[ErrorContext] = None):
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        
        super().__init__(
            message=f"Webhook request to {webhook_url} timed out after {timeout_seconds} seconds",
            error_code="WEBHOOK_TIMEOUT",
            context=context,
            user_message="Webhook request timed out. The endpoint might be slow or unavailable."
        )


class WebhookConfigurationError(UserError):
    """Raised when webhook configuration is invalid."""
    
    def __init__(self, config_issue: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Webhook configuration error: {config_issue}",
            error_code="WEBHOOK_CONFIG_ERROR",
            user_message=f"Webhook configuration issue: {config_issue}",
            context=context
        )


class WebhookRateLimitError(RecoverableError):
    """Raised when webhook rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60, context: Optional[ErrorContext] = None):
        self.retry_after = retry_after
        
        super().__init__(
            message=f"Webhook rate limit exceeded, retry after {retry_after} seconds",
            error_code="WEBHOOK_RATE_LIMIT",
            context=context,
            user_message=f"Webhook rate limit exceeded. Please wait {retry_after} seconds before retrying."
        )


class WebhookSignatureError(UserError):
    """Raised when webhook signature verification fails."""
    
    def __init__(self, context: Optional[ErrorContext] = None):
        super().__init__(
            message="Webhook signature verification failed",
            error_code="WEBHOOK_SIGNATURE_INVALID",
            user_message="Webhook signature verification failed. Please check your secret key.",
            context=context
        )


class WebhookSecurityError(UserError):
    """Raised when webhook request fails security checks."""
    
    def __init__(self, security_issue: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Webhook security check failed: {security_issue}",
            error_code="WEBHOOK_SECURITY_VIOLATION",
            user_message="Webhook request failed security validation.",
            context=context
        )