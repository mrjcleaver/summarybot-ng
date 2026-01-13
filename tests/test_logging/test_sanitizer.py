"""
Tests for log sanitizer.
"""

import pytest
from src.logging.sanitizer import LogSanitizer
from src.logging.models import LoggingConfig


class TestLogSanitizer:
    """Test LogSanitizer class."""

    @pytest.fixture
    def sanitizer(self):
        """Create sanitizer with default config."""
        config = LoggingConfig()
        return LogSanitizer(config)

    def test_sanitize_simple_parameters(self, sanitizer):
        """Test sanitizing simple parameters."""
        params = {
            "count": 100,
            "format": "detailed",
            "user": "test_user"
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["count"] == 100
        assert result["format"] == "detailed"
        assert result["user"] == "test_user"

    def test_sanitize_api_key(self, sanitizer):
        """Test that API keys are redacted."""
        params = {
            "api_key": "sk-1234567890abcdef",
            "count": 100
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["api_key"] == "[REDACTED]"
        assert result["count"] == 100

    def test_sanitize_token(self, sanitizer):
        """Test that tokens are redacted."""
        params = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "bearer_token": "Bearer abc123",
            "discord_token": "MTk4NjIyNDgzNDcxOTI1MjQ4.Cl2FMQ.ZnCjm1XVW7vRze4b7Cq4se7kKWs"
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["access_token"] == "[REDACTED]"
        assert result["bearer_token"] == "[REDACTED]"
        assert result["discord_token"] == "[REDACTED]"

    def test_sanitize_password(self, sanitizer):
        """Test that passwords are redacted."""
        params = {
            "password": "super_secret_password",
            "user_password": "another_secret",
            "db_password": "db_secret"
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["password"] == "[REDACTED]"
        assert result["user_password"] == "[REDACTED]"
        assert result["db_password"] == "[REDACTED]"

    def test_sanitize_secret(self, sanitizer):
        """Test that secrets are redacted."""
        params = {
            "client_secret": "abc123xyz789",
            "webhook_secret": "webhook_secret_key",
            "secret_key": "my_secret"
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["client_secret"] == "[REDACTED]"
        assert result["webhook_secret"] == "[REDACTED]"
        assert result["secret_key"] == "[REDACTED]"

    def test_sanitize_nested_parameters(self, sanitizer):
        """Test sanitizing nested parameters."""
        params = {
            "config": {
                "api_key": "sk-secret",
                "count": 100,
                "nested": {
                    "password": "secret_password",
                    "value": 42
                }
            }
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["count"] == 100
        assert result["config"]["nested"]["password"] == "[REDACTED]"
        assert result["config"]["nested"]["value"] == 42

    def test_sanitize_case_insensitive(self, sanitizer):
        """Test that sanitization is case-insensitive."""
        params = {
            "API_KEY": "key1",
            "Password": "pass1",
            "ACCESS_TOKEN": "token1"
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["API_KEY"] == "[REDACTED]"
        assert result["Password"] == "[REDACTED]"
        assert result["ACCESS_TOKEN"] == "[REDACTED]"

    def test_sanitize_authorization_header(self, sanitizer):
        """Test that authorization headers are redacted."""
        params = {
            "headers": {
                "Authorization": "Bearer abc123",
                "Content-Type": "application/json"
            }
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["headers"]["Authorization"] == "[REDACTED]"
        assert result["headers"]["Content-Type"] == "application/json"

    def test_sanitize_error_message(self, sanitizer):
        """Test error message sanitization."""
        error_msg = "Failed to connect to API with key sk-1234567890 at /home/user/app/config.py:42"

        result = sanitizer.sanitize_error_message(error_msg)

        # Should remove file paths
        assert "/home/user/app/config.py" not in result
        # Should remove tokens
        assert "sk-1234567890" not in result

    def test_hash_signature(self, sanitizer):
        """Test signature hashing."""
        signature = "webhook_signature_abc123xyz789"

        hashed = sanitizer.hash_signature(signature)

        assert hashed.startswith("sha256:")
        assert signature not in hashed
        assert len(hashed) > len("sha256:")

        # Same signature should produce same hash
        hashed2 = sanitizer.hash_signature(signature)
        assert hashed == hashed2

    def test_mask_ip_address(self, sanitizer):
        """Test IP address masking."""
        # IPv4
        ipv4 = "192.168.1.100"
        masked_ipv4 = sanitizer.mask_ip_address(ipv4)
        assert masked_ipv4 == "192.168.*.*"

        # IPv6
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        masked_ipv6 = sanitizer.mask_ip_address(ipv6)
        assert "****" in masked_ipv6
        assert ipv6 not in masked_ipv6

    def test_truncate_long_error_message(self, sanitizer):
        """Test that long error messages are truncated."""
        long_message = "Error: " + ("x" * 1000)

        result = sanitizer.sanitize_error_message(long_message)

        assert len(result) <= sanitizer.config.max_message_length
        assert "..." in result or len(result) == sanitizer.config.max_message_length

    def test_custom_redact_patterns(self):
        """Test custom redaction patterns."""
        config = LoggingConfig(
            redact_patterns=["custom_field", "special_key"]
        )
        sanitizer = LogSanitizer(config)

        params = {
            "custom_field": "secret_value",
            "special_key": "another_secret",
            "normal_field": "normal_value"
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["custom_field"] == "[REDACTED]"
        assert result["special_key"] == "[REDACTED]"
        assert result["normal_field"] == "normal_value"

    def test_sanitize_list_parameters(self, sanitizer):
        """Test sanitizing list parameters."""
        params = {
            "tokens": [
                "token1",
                "token2",
                "token3"
            ],
            "users": [
                "user1",
                "user2"
            ]
        }

        result = sanitizer.sanitize_parameters(params)

        assert result["tokens"] == "[REDACTED]"
        assert result["users"] == ["user1", "user2"]

    def test_empty_parameters(self, sanitizer):
        """Test sanitizing empty parameters."""
        result = sanitizer.sanitize_parameters({})
        assert result == {}

        result = sanitizer.sanitize_parameters(None)
        assert result == {}

    def test_none_error_message(self, sanitizer):
        """Test sanitizing None error message."""
        result = sanitizer.sanitize_error_message(None)
        assert result is None or result == ""
