"""
Audit logging security tests for Summary Bot NG.

Tests logging of security events, failed authentications,
permission denials, and sensitive data protection in logs.
"""

import pytest
import logging
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List, Dict, Any

from src.exceptions.discord_errors import DiscordPermissionError
from src.exceptions.webhook import WebhookAuthError


@pytest.mark.security
class TestSecurityEventLogging:
    """Test logging of security-related events."""

    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing."""
        # Create in-memory audit log
        class AuditLogger:
            def __init__(self):
                self.logs: List[Dict[str, Any]] = []

            def log_security_event(self, event_type: str, user_id: str,
                                 resource: str, success: bool,
                                 metadata: Dict[str, Any] = None):
                """Log security event."""
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event_type": event_type,
                    "user_id": user_id,
                    "resource": resource,
                    "success": success,
                    "metadata": self._sanitize_metadata(metadata or {})
                }
                self.logs.append(log_entry)

            def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
                """Remove sensitive data from metadata."""
                sanitized = {}
                sensitive_keys = ["password", "token", "secret", "api_key", "private_key"]

                for key, value in metadata.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        sanitized[key] = "[REDACTED]"
                    else:
                        sanitized[key] = value

                return sanitized

            def get_logs(self, event_type: str = None, user_id: str = None) -> List[Dict]:
                """Retrieve audit logs."""
                filtered = self.logs

                if event_type:
                    filtered = [log for log in filtered if log["event_type"] == event_type]

                if user_id:
                    filtered = [log for log in filtered if log["user_id"] == user_id]

                return filtered

            def get_failed_attempts(self, user_id: str, since: datetime) -> int:
                """Get count of failed attempts."""
                since_iso = since.isoformat()
                return len([
                    log for log in self.logs
                    if log["user_id"] == user_id
                    and log["success"] is False
                    and log["timestamp"] >= since_iso
                ])

        return AuditLogger()

    def test_successful_authentication_logging(self, audit_logger):
        """Test logging of successful authentication."""
        # Simulate successful authentication
        audit_logger.log_security_event(
            event_type="authentication",
            user_id="user123",
            resource="api_endpoint",
            success=True,
            metadata={
                "method": "api_key",
                "ip_address": "192.168.1.100",
                "user_agent": "DiscordBot/1.0"
            }
        )

        # Verify log entry
        logs = audit_logger.get_logs(event_type="authentication")
        assert len(logs) == 1

        log = logs[0]
        assert log["user_id"] == "user123"
        assert log["success"] is True
        assert log["metadata"]["method"] == "api_key"
        assert "timestamp" in log

    def test_failed_authentication_logging(self, audit_logger):
        """Test logging of failed authentication attempts."""
        # Simulate multiple failed attempts
        for i in range(5):
            audit_logger.log_security_event(
                event_type="authentication_failed",
                user_id="attacker123",
                resource="api_endpoint",
                success=False,
                metadata={
                    "method": "api_key",
                    "ip_address": "10.0.0.1",
                    "reason": "invalid_credentials",
                    "attempt_number": i + 1
                }
            )

        # Verify all attempts logged
        logs = audit_logger.get_logs(event_type="authentication_failed")
        assert len(logs) == 5

        # Verify increasing attempt numbers
        for i, log in enumerate(logs):
            assert log["metadata"]["attempt_number"] == i + 1
            assert log["success"] is False

    def test_brute_force_detection_logging(self, audit_logger):
        """Test detection and logging of brute force attempts."""
        user_id = "brute_force_attacker"

        # Simulate rapid failed attempts
        for i in range(10):
            audit_logger.log_security_event(
                event_type="authentication_failed",
                user_id=user_id,
                resource="login",
                success=False,
                metadata={
                    "ip_address": "10.0.0.1",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        # Check for brute force pattern
        recent_failures = audit_logger.get_failed_attempts(
            user_id=user_id,
            since=datetime.utcnow() - timedelta(minutes=5)
        )

        # Should detect brute force (>5 failures in 5 minutes)
        assert recent_failures >= 10, "Failed to detect brute force"

        # Log brute force detection
        if recent_failures > 5:
            audit_logger.log_security_event(
                event_type="brute_force_detected",
                user_id=user_id,
                resource="login",
                success=False,
                metadata={
                    "failed_attempts": recent_failures,
                    "action": "account_locked"
                }
            )

        # Verify brute force logged
        brute_force_logs = audit_logger.get_logs(event_type="brute_force_detected")
        assert len(brute_force_logs) == 1

    def test_sensitive_data_redaction_in_logs(self, audit_logger):
        """Test sensitive data is redacted in logs."""
        # Log event with sensitive data
        audit_logger.log_security_event(
            event_type="api_call",
            user_id="user123",
            resource="summarize",
            success=True,
            metadata={
                "api_key": "sk_live_1234567890abcdef",
                "discord_token": "MTk4NjIyNDgzNDcxOTI1MjQ4.Cl2FMQ.ZnCjm1XVW7vRze4b7Cq4se7kKWs",
                "password": "super_secret_password",
                "user_email": "user@example.com",  # Not sensitive in this context
                "message_count": 100
            }
        )

        # Verify sensitive data redacted
        logs = audit_logger.get_logs(user_id="user123")
        assert len(logs) == 1

        log = logs[0]
        metadata = log["metadata"]

        # Sensitive fields should be redacted
        assert metadata["api_key"] == "[REDACTED]"
        assert metadata["discord_token"] == "[REDACTED]"
        assert metadata["password"] == "[REDACTED]"

        # Non-sensitive fields should remain
        assert metadata["user_email"] == "user@example.com"
        assert metadata["message_count"] == 100

    def test_permission_denial_logging(self, audit_logger):
        """Test logging of permission denials."""
        # Simulate permission denial
        audit_logger.log_security_event(
            event_type="permission_denied",
            user_id="user123",
            resource="admin_panel",
            success=False,
            metadata={
                "required_permission": "admin",
                "user_permissions": ["read", "write"],
                "ip_address": "192.168.1.100"
            }
        )

        # Verify logged
        logs = audit_logger.get_logs(event_type="permission_denied")
        assert len(logs) == 1

        log = logs[0]
        assert log["success"] is False
        assert log["metadata"]["required_permission"] == "admin"

    def test_suspicious_activity_logging(self, audit_logger):
        """Test logging of suspicious activities."""
        suspicious_activities = [
            {
                "event_type": "suspicious_sql_query",
                "user_id": "user123",
                "resource": "database",
                "metadata": {
                    "query_pattern": "DROP TABLE",
                    "blocked": True
                }
            },
            {
                "event_type": "suspicious_file_access",
                "user_id": "user456",
                "resource": "/etc/passwd",
                "metadata": {
                    "path_traversal_detected": True,
                    "blocked": True
                }
            },
            {
                "event_type": "suspicious_api_usage",
                "user_id": "user789",
                "resource": "api",
                "metadata": {
                    "rate_limit_exceeded": True,
                    "requests_per_second": 1000
                }
            }
        ]

        # Log all suspicious activities
        for activity in suspicious_activities:
            audit_logger.log_security_event(
                event_type=activity["event_type"],
                user_id=activity["user_id"],
                resource=activity["resource"],
                success=False,
                metadata=activity["metadata"]
            )

        # Verify all logged
        all_logs = audit_logger.get_logs()
        suspicious_logs = [log for log in all_logs if "suspicious" in log["event_type"]]

        assert len(suspicious_logs) == 3
        assert all(log["success"] is False for log in suspicious_logs)


@pytest.mark.security
class TestFailedAuthenticationLogging:
    """Test comprehensive failed authentication logging."""

    @pytest.fixture
    def auth_logger(self):
        """Authentication-specific logger."""
        class AuthLogger:
            def __init__(self):
                self.auth_attempts = []

            def log_auth_attempt(self, user_id: str, method: str,
                               success: bool, failure_reason: str = None,
                               metadata: Dict = None):
                """Log authentication attempt."""
                entry = {
                    "timestamp": datetime.utcnow(),
                    "user_id": user_id,
                    "method": method,
                    "success": success,
                    "failure_reason": failure_reason,
                    "metadata": metadata or {},
                    "ip_address": metadata.get("ip_address") if metadata else None
                }
                self.auth_attempts.append(entry)

            def get_recent_failures(self, user_id: str, minutes: int = 15) -> List[Dict]:
                """Get recent failed attempts for user."""
                cutoff = datetime.utcnow() - timedelta(minutes=minutes)
                return [
                    attempt for attempt in self.auth_attempts
                    if attempt["user_id"] == user_id
                    and not attempt["success"]
                    and attempt["timestamp"] >= cutoff
                ]

            def get_failures_by_ip(self, ip_address: str, minutes: int = 15) -> List[Dict]:
                """Get failed attempts from IP address."""
                cutoff = datetime.utcnow() - timedelta(minutes=minutes)
                return [
                    attempt for attempt in self.auth_attempts
                    if attempt["ip_address"] == ip_address
                    and not attempt["success"]
                    and attempt["timestamp"] >= cutoff
                ]

        return AuthLogger()

    def test_invalid_api_key_logging(self, auth_logger):
        """Test logging of invalid API key attempts."""
        # Simulate invalid API key
        auth_logger.log_auth_attempt(
            user_id="unknown",
            method="api_key",
            success=False,
            failure_reason="invalid_api_key",
            metadata={
                "ip_address": "10.0.0.1",
                "provided_key": "invalid_key_abc123"[:10] + "..."  # Truncate for security
            }
        )

        failures = auth_logger.get_recent_failures("unknown")
        assert len(failures) == 1
        assert failures[0]["failure_reason"] == "invalid_api_key"

    def test_expired_token_logging(self, auth_logger):
        """Test logging of expired token usage."""
        auth_logger.log_auth_attempt(
            user_id="user123",
            method="jwt",
            success=False,
            failure_reason="token_expired",
            metadata={
                "ip_address": "192.168.1.100",
                "token_age_hours": 25,
                "max_age_hours": 24
            }
        )

        failures = auth_logger.get_recent_failures("user123")
        assert len(failures) == 1
        assert failures[0]["metadata"]["token_age_hours"] > failures[0]["metadata"]["max_age_hours"]

    def test_missing_credentials_logging(self, auth_logger):
        """Test logging of requests with missing credentials."""
        auth_logger.log_auth_attempt(
            user_id="anonymous",
            method="none",
            success=False,
            failure_reason="missing_credentials",
            metadata={
                "ip_address": "203.0.113.1",
                "endpoint": "/api/summarize"
            }
        )

        failures = auth_logger.get_recent_failures("anonymous")
        assert len(failures) == 1
        assert failures[0]["failure_reason"] == "missing_credentials"

    def test_ip_based_attack_detection(self, auth_logger):
        """Test detection of attacks from single IP."""
        attacker_ip = "10.0.0.1"

        # Simulate multiple failed attempts from same IP
        for i in range(20):
            auth_logger.log_auth_attempt(
                user_id=f"user{i}",
                method="api_key",
                success=False,
                failure_reason="invalid_credentials",
                metadata={"ip_address": attacker_ip}
            )

        # Check failures from this IP
        ip_failures = auth_logger.get_failures_by_ip(attacker_ip, minutes=5)

        # Should detect distributed attack (multiple users from one IP)
        assert len(ip_failures) >= 20
        unique_users = len(set(f["user_id"] for f in ip_failures))
        assert unique_users >= 10, "Should detect distributed attack pattern"


@pytest.mark.security
class TestPermissionDenialLogging:
    """Test logging of permission denial events."""

    @pytest.fixture
    def permission_logger(self):
        """Permission-specific logger."""
        class PermissionLogger:
            def __init__(self):
                self.denials = []

            def log_permission_denial(self, user_id: str, resource: str,
                                    action: str, required_permission: str,
                                    user_permissions: List[str],
                                    metadata: Dict = None):
                """Log permission denial."""
                entry = {
                    "timestamp": datetime.utcnow(),
                    "user_id": user_id,
                    "resource": resource,
                    "action": action,
                    "required_permission": required_permission,
                    "user_permissions": user_permissions,
                    "metadata": metadata or {}
                }
                self.denials.append(entry)

            def get_denials(self, user_id: str = None, resource: str = None) -> List[Dict]:
                """Get permission denials."""
                filtered = self.denials

                if user_id:
                    filtered = [d for d in filtered if d["user_id"] == user_id]

                if resource:
                    filtered = [d for d in filtered if d["resource"] == resource]

                return filtered

        return PermissionLogger()

    def test_admin_action_denial_logging(self, permission_logger):
        """Test logging when non-admin tries admin action."""
        permission_logger.log_permission_denial(
            user_id="user123",
            resource="guild_config",
            action="update",
            required_permission="admin",
            user_permissions=["read", "write"],
            metadata={
                "guild_id": "guild123",
                "attempted_change": "max_message_limit"
            }
        )

        denials = permission_logger.get_denials(user_id="user123")
        assert len(denials) == 1
        assert denials[0]["required_permission"] == "admin"
        assert "admin" not in denials[0]["user_permissions"]

    def test_channel_access_denial_logging(self, permission_logger):
        """Test logging of unauthorized channel access."""
        permission_logger.log_permission_denial(
            user_id="user456",
            resource="private_channel",
            action="read_messages",
            required_permission="channel_access",
            user_permissions=[],
            metadata={
                "channel_id": "channel789",
                "channel_name": "admin-only"
            }
        )

        denials = permission_logger.get_denials(resource="private_channel")
        assert len(denials) == 1

    def test_privilege_escalation_attempt_logging(self, permission_logger):
        """Test logging of privilege escalation attempts."""
        # User tries to grant themselves admin
        permission_logger.log_permission_denial(
            user_id="user123",
            resource="user_permissions",
            action="grant_admin",
            required_permission="super_admin",
            user_permissions=["read", "write"],
            metadata={
                "target_user": "user123",  # Trying to elevate self
                "requested_permission": "admin",
                "severity": "high",
                "potential_escalation": True
            }
        )

        denials = permission_logger.get_denials(user_id="user123")
        escalation_attempts = [
            d for d in denials
            if d["metadata"].get("potential_escalation")
        ]

        assert len(escalation_attempts) == 1
        assert escalation_attempts[0]["metadata"]["severity"] == "high"

    def test_repeated_denial_pattern_detection(self, permission_logger):
        """Test detection of repeated permission denial patterns."""
        user_id = "persistent_attacker"

        # Simulate repeated attempts to access restricted resource
        for i in range(15):
            permission_logger.log_permission_denial(
                user_id=user_id,
                resource="admin_panel",
                action="access",
                required_permission="admin",
                user_permissions=["read"],
                metadata={"attempt_number": i + 1}
            )

        # Analyze pattern
        denials = permission_logger.get_denials(user_id=user_id)

        # Should detect persistent unauthorized access attempts
        assert len(denials) >= 15

        # Check if all attempts target same protected resource
        unique_resources = set(d["resource"] for d in denials)
        assert len(unique_resources) == 1
        assert "admin_panel" in unique_resources
