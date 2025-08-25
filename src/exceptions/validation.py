"""
Validation-related exceptions.
"""

from typing import Optional, List, Dict, Any
from .base import UserError, ErrorContext


class ValidationError(UserError):
    """Base class for validation errors."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, 
                 field_value: Optional[Any] = None, context: Optional[ErrorContext] = None):
        self.field_name = field_name
        self.field_value = field_value
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            user_message=message,
            context=context
        )


class ConfigurationError(ValidationError):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_key: str, issue: str, context: Optional[ErrorContext] = None):
        self.config_key = config_key
        self.issue = issue
        
        super().__init__(
            message=f"Configuration error for '{config_key}': {issue}",
            field_name=config_key,
            context=context
        )
        
        self.user_message = f"Configuration issue: {issue}. Please contact an administrator."


class InvalidInputError(ValidationError):
    """Raised when user input is invalid."""
    
    def __init__(self, input_name: str, input_value: Any, reason: str,
                 suggestions: Optional[List[str]] = None, context: Optional[ErrorContext] = None):
        self.input_name = input_name
        self.input_value = input_value
        self.reason = reason
        self.suggestions = suggestions or []
        
        super().__init__(
            message=f"Invalid {input_name}: {input_value} - {reason}",
            field_name=input_name,
            field_value=input_value,
            context=context
        )
        
        # Build user message with suggestions
        user_msg = f"Invalid {input_name}: {reason}"
        if self.suggestions:
            user_msg += f" Valid options: {', '.join(self.suggestions)}"
        
        self.user_message = user_msg


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing."""
    
    def __init__(self, field_name: str, context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Required field missing: {field_name}",
            field_name=field_name,
            context=context
        )
        
        self.user_message = f"Missing required field: {field_name}"


class InvalidDateRangeError(ValidationError):
    """Raised when date range is invalid."""
    
    def __init__(self, start_date: str, end_date: str, issue: str,
                 context: Optional[ErrorContext] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.issue = issue
        
        super().__init__(
            message=f"Invalid date range {start_date} to {end_date}: {issue}",
            context=context
        )
        
        self.user_message = f"Invalid date range: {issue}"


class InvalidChannelError(ValidationError):
    """Raised when channel ID or reference is invalid."""
    
    def __init__(self, channel_id: str, reason: str, context: Optional[ErrorContext] = None):
        self.channel_id = channel_id
        self.reason = reason
        
        super().__init__(
            message=f"Invalid channel {channel_id}: {reason}",
            field_name="channel_id",
            field_value=channel_id,
            context=context
        )
        
        self.user_message = f"Invalid channel: {reason}"


class InvalidUserError(ValidationError):
    """Raised when user ID or reference is invalid."""
    
    def __init__(self, user_id: str, reason: str, context: Optional[ErrorContext] = None):
        self.user_id = user_id
        self.reason = reason
        
        super().__init__(
            message=f"Invalid user {user_id}: {reason}",
            field_name="user_id", 
            field_value=user_id,
            context=context
        )
        
        self.user_message = f"Invalid user: {reason}"


class InvalidTimeRangeError(ValidationError):
    """Raised when time range parameters are invalid."""
    
    def __init__(self, range_type: str, value: Any, min_value: Any = None, 
                 max_value: Any = None, context: Optional[ErrorContext] = None):
        self.range_type = range_type
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        
        if min_value and max_value:
            bounds = f"must be between {min_value} and {max_value}"
        elif min_value:
            bounds = f"must be at least {min_value}"
        elif max_value:
            bounds = f"must be at most {max_value}"
        else:
            bounds = "is invalid"
        
        super().__init__(
            message=f"Invalid {range_type}: {value} {bounds}",
            field_name=range_type,
            field_value=value,
            context=context
        )
        
        self.user_message = f"{range_type.title()} {bounds}"


class InvalidSummaryOptionsError(ValidationError):
    """Raised when summary options are invalid."""
    
    def __init__(self, option_name: str, option_value: Any, reason: str,
                 context: Optional[ErrorContext] = None):
        self.option_name = option_name
        self.option_value = option_value
        self.reason = reason
        
        super().__init__(
            message=f"Invalid summary option '{option_name}' = {option_value}: {reason}",
            field_name=option_name,
            field_value=option_value,
            context=context
        )
        
        self.user_message = f"Invalid summary option '{option_name}': {reason}"


class SchemaValidationError(ValidationError):
    """Raised when data doesn't match expected schema."""
    
    def __init__(self, schema_name: str, errors: List[str], data: Optional[Dict[str, Any]] = None,
                 context: Optional[ErrorContext] = None):
        self.schema_name = schema_name
        self.validation_errors = errors
        self.data = data
        
        errors_text = "; ".join(errors)
        
        super().__init__(
            message=f"Schema validation failed for {schema_name}: {errors_text}",
            context=context
        )
        
        self.user_message = f"Invalid data format: {errors_text}"


class DuplicateValueError(ValidationError):
    """Raised when a value must be unique but isn't."""
    
    def __init__(self, field_name: str, value: Any, context: Optional[ErrorContext] = None):
        super().__init__(
            message=f"Duplicate value for {field_name}: {value}",
            field_name=field_name,
            field_value=value,
            context=context
        )
        
        self.user_message = f"Duplicate {field_name}: {value} already exists"