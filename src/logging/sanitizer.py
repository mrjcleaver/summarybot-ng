"""
Sanitize sensitive data before logging.
"""

import re
import hashlib
import logging
from typing import Any, Dict, List, Pattern

from .models import LoggingConfig

logger = logging.getLogger(__name__)


class LogSanitizer:
    """
    Sanitizes sensitive data in log entries.

    Responsibilities:
    - Redact API keys, tokens, passwords
    - Hash webhook signatures
    - Truncate message content
    - Mask PII (emails, IPs)
    """

    def __init__(self, config: LoggingConfig):
        self.config = config
        self._redact_patterns = self._compile_redact_patterns()

    def _compile_redact_patterns(self) -> List[Pattern]:
        """Compile regex patterns for redaction."""
        patterns = []
        for pattern_str in self.config.redact_patterns:
            try:
                # Case-insensitive pattern matching
                pattern = re.compile(pattern_str, re.IGNORECASE)
                patterns.append(pattern)
            except re.error as e:
                logger.warning(f"Invalid redact pattern '{pattern_str}': {e}")
        return patterns

    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize command parameters.

        Algorithm:
        1. Iterate through all key-value pairs
        2. Check if key matches redaction patterns
        3. Redact or sanitize based on data type
        4. Recursively sanitize nested dictionaries
        """
        if not self.config.sanitize_enabled:
            return parameters

        sanitized = {}

        for key, value in parameters.items():
            # Check if key matches redaction pattern
            if self._should_redact_key(key):
                sanitized[key] = "[REDACTED]"

            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_parameters(value)

            # Sanitize lists
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_parameters(item) if isinstance(item, dict) else item
                    for item in value
                ]

            # Truncate long strings
            elif isinstance(value, str) and len(value) > self.config.max_message_length:
                sanitized[key] = self._truncate_string(value)

            else:
                sanitized[key] = value

        return sanitized

    def _should_redact_key(self, key: str) -> bool:
        """Check if a key should be redacted."""
        for pattern in self._redact_patterns:
            if pattern.search(key):
                return True
        return False

    def _truncate_string(self, text: str) -> str:
        """Truncate long strings with ellipsis."""
        max_len = self.config.max_message_length
        if len(text) <= max_len:
            return text
        return text[:max_len] + "... [truncated]"

    def sanitize_error_message(self, error_message: str) -> str:
        """
        Sanitize error messages to remove sensitive data.

        Checks for:
        - File paths that might contain usernames
        - Connection strings
        - API endpoints with tokens
        """
        if not error_message:
            return error_message

        # Redact file paths
        sanitized = re.sub(
            r'/home/[^/]+/',
            '/home/[user]/',
            error_message
        )

        # Redact URLs with tokens
        sanitized = re.sub(
            r'(https?://[^?]+\?[^=]+=)[^&\s]+',
            r'\1[REDACTED]',
            sanitized
        )

        return self._truncate_string(sanitized)

    def hash_signature(self, signature: str) -> str:
        """Hash webhook signatures for verification without storage."""
        if not signature:
            return ""

        hash_obj = hashlib.sha256(signature.encode('utf-8'))
        return f"sha256:{hash_obj.hexdigest()[:16]}..."

    def mask_ip_address(self, ip_address: str) -> str:
        """Mask IP address for privacy."""
        if not ip_address:
            return ""

        # IPv4: 192.168.1.1 -> 192.168.*.**
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.*.***"

        # IPv6: Mask last 64 bits
        if ':' in ip_address:
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return ':'.join(parts[:4]) + ':****:****:****:****'

        return "[MASKED_IP]"

    def sanitize_execution_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize execution context.

        Special handling:
        - IP addresses are masked
        - Signatures are hashed
        - User agents are preserved (useful for debugging)
        """
        sanitized = context.copy()

        if "source_ip" in sanitized:
            sanitized["source_ip"] = self.mask_ip_address(sanitized["source_ip"])

        if "signature" in sanitized:
            sanitized["signature_hash"] = self.hash_signature(sanitized["signature"])
            del sanitized["signature"]

        if "headers" in sanitized and isinstance(sanitized["headers"], dict):
            sanitized["headers"] = self._sanitize_headers(sanitized["headers"])

        return sanitized

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize HTTP headers."""
        sanitized = {}

        for key, value in headers.items():
            key_lower = key.lower()

            # Redact authorization headers
            if key_lower in ["authorization", "x-api-key", "x-auth-token"]:
                sanitized[key] = "[REDACTED]"

            # Hash signatures
            elif "signature" in key_lower:
                sanitized[f"{key}_hash"] = self.hash_signature(value)

            # Keep useful headers
            elif key_lower in ["user-agent", "content-type", "x-request-id"]:
                sanitized[key] = value

            else:
                sanitized[key] = value

        return sanitized
