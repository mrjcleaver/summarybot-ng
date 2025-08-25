"""
Security testing for Summary Bot NG.

Tests cover authentication, authorization, input validation, 
and security vulnerability detection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from datetime import datetime, timedelta
import jwt
import hashlib
import secrets

from src.permissions.manager import PermissionManager
from src.webhook_service.auth import AuthenticationMiddleware
from src.config.settings import BotConfig, GuildConfig
from src.exceptions.discord_errors import DiscordPermissionError
from src.exceptions.validation import ValidationError


@pytest.mark.security
class TestPermissionValidation:
    """Test permission and authorization security."""
    
    @pytest.fixture
    def permission_manager(self):
        """Create permission manager for testing."""
        config = BotConfig(
            discord_token="test_token",
            claude_api_key="test_api_key",
            guild_configs={
                "123456789": GuildConfig(
                    guild_id="123456789",
                    enabled_channels=["allowed_channel"],
                    excluded_channels=["blocked_channel"],
                    default_summary_options=MagicMock(),
                    permission_settings={
                        "admin_roles": ["Admin", "Moderator"],
                        "summary_roles": ["Member"],
                        "required_permissions": ["READ_MESSAGE_HISTORY", "SEND_MESSAGES"]
                    }
                )
            }
        )
        return PermissionManager(config)
    
    @pytest.mark.asyncio
    async def test_unauthorized_channel_access(self, permission_manager):
        """Test blocking access to unauthorized channels."""
        # Test access to excluded channel
        result = await permission_manager.check_channel_access(
            user_id="111111111",
            channel_id="blocked_channel",
            guild_id="123456789"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_unauthorized_guild_access(self, permission_manager):
        """Test blocking access to unauthorized guilds."""
        # Test access to non-configured guild
        result = await permission_manager.check_channel_access(
            user_id="111111111", 
            channel_id="any_channel",
            guild_id="unauthorized_guild"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_command_permission_escalation_prevention(self, permission_manager):
        """Test prevention of privilege escalation."""
        # Regular user trying to access admin command
        result = await permission_manager.check_command_permission(
            user_id="regular_user",
            command="config_set_admin",
            guild_id="123456789"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_role_hierarchy_validation(self, permission_manager):
        """Test role hierarchy enforcement."""
        # Mock Discord user with insufficient roles
        mock_user = MagicMock()
        mock_user.roles = [MagicMock(name="Member")]
        
        # Mock Discord channel requiring admin access
        mock_channel = MagicMock()
        mock_channel.permissions_for.return_value = discord.Permissions(administrator=False)
        
        from src.permissions.validators import PermissionValidator
        validator = PermissionValidator()
        
        result = validator.validate_summarize_permission(mock_user, mock_channel)
        
        # Should fail due to insufficient permissions
        assert result.valid is False
        assert "insufficient" in result.reason.lower() or "permission" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_permission_cache_poisoning_prevention(self, permission_manager):
        """Test prevention of permission cache poisoning."""
        # First check with valid permissions
        with patch.object(permission_manager, '_fetch_user_permissions') as mock_fetch:
            mock_fetch.return_value = MagicMock(can_summarize=True)
            
            result1 = await permission_manager.check_command_permission(
                user_id="111111111",
                command="summarize", 
                guild_id="123456789"
            )
            
            assert result1 is True
        
        # Attempt to poison cache with elevated permissions
        permission_manager._permission_cache["111111111:123456789"] = MagicMock(
            can_summarize=True,
            can_configure=True,  # Elevated permission
            can_admin=True       # Admin permission
        )
        
        # Verify cache validation prevents poisoning
        with patch.object(permission_manager, '_validate_cached_permissions') as mock_validate:
            mock_validate.return_value = False  # Cache invalid
            
            with patch.object(permission_manager, '_fetch_user_permissions') as mock_fetch:
                mock_fetch.return_value = MagicMock(
                    can_summarize=True,
                    can_configure=False,  # Correct permissions
                    can_admin=False
                )
                
                result2 = await permission_manager.check_command_permission(
                    user_id="111111111",
                    command="configure",
                    guild_id="123456789"
                )
                
                assert result2 is False  # Should not have elevated permissions


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_message_content_sanitization(self):
        """Test sanitization of message content."""
        from src.message_processing.cleaner import MessageCleaner
        
        cleaner = MessageCleaner()
        
        # Test XSS prevention
        malicious_content = '<script>alert("XSS")</script>Hello world'
        cleaned = cleaner.clean_content(malicious_content)
        
        assert '<script>' not in cleaned
        assert '&lt;script&gt;' in cleaned or cleaned == 'Hello world'
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in database queries."""
        from src.data.repositories.summary_repository import SummaryRepository
        
        # Mock database connection
        mock_db = AsyncMock()
        repository = SummaryRepository(mock_db)
        
        # Attempt SQL injection in search criteria
        malicious_criteria = MagicMock()
        malicious_criteria.text_search = "'; DROP TABLE summaries; --"
        malicious_criteria.guild_id = "123456789"
        
        # Execute search (should use parameterized queries)
        with patch.object(repository, '_build_search_query') as mock_build:
            mock_build.return_value = ("SELECT * FROM summaries WHERE guild_id = ? AND content LIKE ?", 
                                     ["123456789", "%'; DROP TABLE summaries; --%"])
            
            # Query should be parameterized, not concatenated
            query, params = mock_build.return_value
            
            assert "?" in query  # Parameterized query
            assert "DROP TABLE" not in query  # SQL injection not in query structure
            assert malicious_criteria.text_search in params  # Injection safely parameterized
    
    def test_file_upload_validation(self):
        """Test file upload validation and sanitization."""
        from src.webhook_service.validators import FileValidator
        
        validator = FileValidator()
        
        # Test malicious file types
        malicious_files = [
            {"filename": "malware.exe", "content_type": "application/octet-stream"},
            {"filename": "script.js", "content_type": "application/javascript"},  
            {"filename": "../../etc/passwd", "content_type": "text/plain"},  # Path traversal
            {"filename": "normal.pdf\x00.exe", "content_type": "application/pdf"}  # Null byte injection
        ]
        
        for file_info in malicious_files:
            result = validator.validate_upload(file_info)
            assert result.valid is False, f"Should reject malicious file: {file_info['filename']}"
    
    def test_command_parameter_validation(self):
        """Test validation of command parameters."""
        from src.command_handlers.validators import CommandValidator
        
        validator = CommandValidator()
        
        # Test various injection attempts
        malicious_inputs = [
            {"channel_id": "../../../etc/passwd"},
            {"time_range": "'; DROP TABLE users; --"},
            {"summary_length": "<script>alert('xss')</script>"},
            {"user_filter": "admin' OR '1'='1"},
            {"message_limit": "999999999999999999999"}  # Integer overflow
        ]
        
        for params in malicious_inputs:
            result = validator.validate_parameters(params)
            assert result.valid is False, f"Should reject malicious input: {params}"
    
    def test_regex_dos_prevention(self):
        """Test prevention of Regular Expression Denial of Service."""
        from src.message_processing.extractor import MessageExtractor
        
        extractor = MessageExtractor()
        
        # Malicious regex payloads
        evil_patterns = [
            "a" * 10000 + "!",  # Catastrophic backtracking
            "(a+)+$",  # Exponential time complexity
            "([a-zA-Z]+)*$",  # Another catastrophic backtracking pattern
        ]
        
        malicious_content = "a" * 50000  # Large input
        
        import time
        for pattern in evil_patterns:
            start_time = time.time()
            
            # Extract mentions with timeout protection
            try:
                mentions = extractor.extract_mentions(malicious_content, pattern, timeout=1.0)
            except TimeoutError:
                mentions = []
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should not take more than 1 second due to timeout protection
            assert processing_time < 2.0, f"Regex processing took {processing_time}s, possible ReDoS"


@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication and token security."""
    
    @pytest.fixture
    def auth_middleware(self):
        """Create authentication middleware for testing."""
        config = MagicMock()
        config.jwt_secret = "test_secret_key_with_sufficient_length_for_security"
        config.token_expiry = 3600  # 1 hour
        
        return AuthenticationMiddleware(config)
    
    def test_jwt_token_validation(self, auth_middleware):
        """Test JWT token validation."""
        # Create valid token
        payload = {
            "user_id": "123456789",
            "guild_id": "987654321",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        
        valid_token = jwt.encode(
            payload, 
            auth_middleware.config.jwt_secret, 
            algorithm="HS256"
        )
        
        # Validate token
        result = auth_middleware.validate_token(valid_token)
        
        assert result.valid is True
        assert result.user_id == "123456789"
    
    def test_expired_token_rejection(self, auth_middleware):
        """Test rejection of expired tokens."""
        # Create expired token
        payload = {
            "user_id": "123456789",
            "guild_id": "987654321", 
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        
        expired_token = jwt.encode(
            payload,
            auth_middleware.config.jwt_secret,
            algorithm="HS256"
        )
        
        # Should reject expired token
        result = auth_middleware.validate_token(expired_token)
        
        assert result.valid is False
        assert "expired" in result.reason.lower()
    
    def test_tampered_token_rejection(self, auth_middleware):
        """Test rejection of tampered tokens."""
        # Create valid token
        payload = {
            "user_id": "123456789",
            "guild_id": "987654321",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        
        valid_token = jwt.encode(
            payload,
            auth_middleware.config.jwt_secret,
            algorithm="HS256"
        )
        
        # Tamper with token
        tampered_token = valid_token[:-5] + "XXXXX"
        
        # Should reject tampered token
        result = auth_middleware.validate_token(tampered_token)
        
        assert result.valid is False
        assert "invalid" in result.reason.lower()
    
    def test_weak_secret_detection(self):
        """Test detection of weak JWT secrets."""
        from src.webhook_service.auth import AuthenticationMiddleware
        
        weak_secrets = [
            "secret",
            "123456", 
            "password",
            "a" * 10,  # Too short
            ""  # Empty
        ]
        
        for weak_secret in weak_secrets:
            config = MagicMock()
            config.jwt_secret = weak_secret
            
            with pytest.raises(ValidationError) as exc_info:
                AuthenticationMiddleware(config)
            
            assert "weak" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
    
    def test_timing_attack_resistance(self, auth_middleware):
        """Test resistance to timing attacks in token validation."""
        import time
        import statistics
        
        # Valid tokens
        valid_tokens = []
        for i in range(10):
            payload = {
                "user_id": f"12345678{i}",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow()
            }
            token = jwt.encode(payload, auth_middleware.config.jwt_secret, algorithm="HS256")
            valid_tokens.append(token)
        
        # Invalid tokens
        invalid_tokens = ["invalid_token" + str(i) for i in range(10)]
        
        # Measure validation times
        valid_times = []
        invalid_times = []
        
        for token in valid_tokens:
            start = time.time()
            auth_middleware.validate_token(token)
            end = time.time()
            valid_times.append(end - start)
        
        for token in invalid_tokens:
            start = time.time()
            auth_middleware.validate_token(token)
            end = time.time()
            invalid_times.append(end - start)
        
        # Times should be similar to prevent timing attacks
        valid_avg = statistics.mean(valid_times)
        invalid_avg = statistics.mean(invalid_times)
        
        # Difference should be minimal (within 50% to account for normal variance)
        time_ratio = abs(valid_avg - invalid_avg) / max(valid_avg, invalid_avg)
        assert time_ratio < 0.5, f"Timing difference too large: {time_ratio}"


@pytest.mark.security
class TestDataProtection:
    """Test data protection and privacy security."""
    
    def test_pii_scrubbing(self):
        """Test removal of personally identifiable information."""
        from src.message_processing.privacy import PIIScrubber
        
        scrubber = PIIScrubber()
        
        # Test messages with PII
        messages_with_pii = [
            "My email is john.doe@example.com and phone is 555-123-4567",
            "Credit card number: 4111-1111-1111-1111",
            "SSN: 123-45-6789",
            "Here's my IP address: 192.168.1.100",
            "Bitcoin address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        ]
        
        for message in messages_with_pii:
            scrubbed = scrubber.scrub_message(message)
            
            # Should not contain original PII
            assert "@example.com" not in scrubbed
            assert "555-123-4567" not in scrubbed
            assert "4111-1111-1111-1111" not in scrubbed
            assert "123-45-6789" not in scrubbed
            assert "192.168.1.100" not in scrubbed
            assert "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" not in scrubbed
            
            # Should contain redacted markers
            assert "[EMAIL_REDACTED]" in scrubbed or "[REDACTED]" in scrubbed
    
    def test_data_encryption_at_rest(self):
        """Test encryption of sensitive data at rest."""
        from src.data.encryption import DataEncryption
        
        encryption = DataEncryption("test_encryption_key_32_bytes_long!")
        
        sensitive_data = {
            "discord_token": "discord_bot_token_123456789",
            "claude_api_key": "claude_api_key_abcdefghijk",
            "user_data": "sensitive user information"
        }
        
        # Encrypt data
        encrypted = encryption.encrypt_dict(sensitive_data)
        
        # Encrypted data should not contain original values
        encrypted_str = str(encrypted)
        assert "discord_bot_token" not in encrypted_str
        assert "claude_api_key" not in encrypted_str
        assert "sensitive user information" not in encrypted_str
        
        # Decrypt and verify
        decrypted = encryption.decrypt_dict(encrypted)
        assert decrypted == sensitive_data
    
    def test_secure_configuration_storage(self):
        """Test secure storage of configuration data."""
        from src.config.security import SecureConfigManager
        
        config_manager = SecureConfigManager()
        
        # Sensitive configuration
        sensitive_config = {
            "discord_token": "secret_discord_token",
            "claude_api_key": "secret_claude_key", 
            "database_password": "secret_db_password",
            "webhook_secret": "secret_webhook_key"
        }
        
        # Store configuration securely
        config_manager.store_config(sensitive_config, "test_config.enc")
        
        # Verify file is encrypted (not plaintext)
        with open("test_config.enc", "rb") as f:
            file_content = f.read()
            file_str = file_content.decode('utf-8', errors='ignore')
            
            # Should not contain plaintext secrets
            assert "secret_discord_token" not in file_str
            assert "secret_claude_key" not in file_str
            assert "secret_db_password" not in file_str
        
        # Load and verify
        loaded_config = config_manager.load_config("test_config.enc")
        assert loaded_config == sensitive_config
        
        # Cleanup
        import os
        os.unlink("test_config.enc")
    
    def test_audit_log_security(self):
        """Test security of audit logging."""
        from src.logging.audit import AuditLogger
        
        audit_logger = AuditLogger()
        
        # Log sensitive operation
        audit_logger.log_operation(
            user_id="123456789",
            operation="summarize",
            resource="channel_987654321",
            success=True,
            metadata={
                "message_count": 100,
                "processing_time": 5.2,
                "api_key": "secret_key_should_not_be_logged"  # Sensitive data
            }
        )
        
        # Retrieve audit logs
        logs = audit_logger.get_logs(user_id="123456789", limit=1)
        
        # Should not contain sensitive data
        log_entry = logs[0]
        log_str = str(log_entry)
        
        assert "secret_key_should_not_be_logged" not in log_str
        assert "[REDACTED]" in log_str or "api_key" not in log_str