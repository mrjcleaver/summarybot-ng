# Security Remediation Plan - Summary Bot NG
## Prioritized Action Plan for Security Implementation

### Implementation Timeline Overview

| Phase | Duration | Focus Area | Priority Level |
|-------|----------|------------|----------------|
| Phase 1 | Week 1-2 | Critical Security Architecture | P1 (Critical) |
| Phase 2 | Week 3-4 | Core Security Implementation | P1-P2 (High) |
| Phase 3 | Week 5-8 | Security Integration & Testing | P2-P3 (Medium) |
| Phase 4 | Ongoing | Monitoring & Maintenance | P3-P4 (Low) |

---

## Phase 1: Critical Security Architecture (Weeks 1-2)

### 1.1 Secrets Management Implementation [P1 - Critical]

**Objective:** Establish secure secrets management before any code implementation

**Deliverables:**
```python
# config/secrets_manager.py
import os
from typing import Optional
import hvac  # HashiCorp Vault client

class SecretsManager:
    def __init__(self):
        self.vault_client = hvac.Client(url=os.getenv('VAULT_URL'))
        self.vault_client.token = os.getenv('VAULT_TOKEN')
    
    def get_secret(self, path: str) -> Optional[str]:
        """Retrieve secret from Vault with fallback to environment"""
        try:
            response = self.vault_client.secrets.kv.v2.read_secret_version(path=path)
            return response['data']['data']['value']
        except Exception:
            return os.getenv(path.upper().replace('/', '_'))
    
    def get_discord_token(self) -> str:
        return self.get_secret('discord/bot_token')
    
    def get_openai_key(self) -> str:
        return self.get_secret('openai/api_key')
```

**Environment Configuration:**
```yaml
# docker-compose.yml security addition
services:
  summarybot:
    environment:
      - VAULT_URL=${VAULT_URL}
      - VAULT_TOKEN=${VAULT_TOKEN}
    secrets:
      - discord_token
      - openai_api_key

secrets:
  discord_token:
    external: true
  openai_api_key:
    external: true
```

**Acceptance Criteria:**
- [ ] No hardcoded secrets in any code files
- [ ] Environment-based secret injection working
- [ ] Vault integration tested (if using Vault)
- [ ] Secret rotation capability implemented
- [ ] Error handling for missing secrets

---

### 1.2 JWT Authentication Architecture [P1 - Critical]

**Objective:** Implement secure JWT authentication for webhook API

**Implementation:**
```python
# auth/jwt_manager.py
import jwt
import datetime
from typing import Optional, Dict
from config.secrets_manager import SecretsManager

class JWTManager:
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets = secrets_manager
        self.algorithm = 'RS256'  # Use RSA for better security
        
    def generate_token(self, payload: Dict, expires_hours: int = 24) -> str:
        """Generate JWT token with expiration"""
        payload.update({
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expires_hours),
            'iat': datetime.datetime.utcnow(),
            'iss': 'summarybot-ng'
        })
        private_key = self.secrets.get_secret('jwt/private_key')
        return jwt.encode(payload, private_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            public_key = self.secrets.get_secret('jwt/public_key')
            return jwt.decode(token, public_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

# middleware/auth_middleware.py
from functools import wraps
from flask import request, jsonify

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401
            
        payload = jwt_manager.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
            
        request.user = payload
        return f(*args, **kwargs)
    return decorated_function
```

**Key Generation Script:**
```bash
#!/bin/bash
# scripts/generate-jwt-keys.sh
openssl genpkey -algorithm RSA -out jwt_private_key.pem -pkcs8 -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in jwt_private_key.pem -out jwt_public_key.pem
echo "JWT keys generated. Store in secrets management system."
```

**Acceptance Criteria:**
- [ ] RSA-based JWT implementation
- [ ] Token expiration and refresh mechanism
- [ ] Secure key storage and rotation
- [ ] Authentication middleware implemented
- [ ] Error handling for invalid tokens

---

### 1.3 Webhook Security Framework [P1 - Critical]

**Objective:** Secure webhook endpoints with signature validation and rate limiting

**Implementation:**
```python
# webhooks/security.py
import hmac
import hashlib
from typing import Optional
from flask import request, abort
from config.secrets_manager import SecretsManager

class WebhookSecurity:
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets = secrets_manager
    
    def validate_webhook_signature(self, payload: bytes, signature: str, 
                                 webhook_secret: str) -> bool:
        """Validate webhook signature using HMAC-SHA256"""
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    def verify_github_webhook(self) -> bool:
        """Verify GitHub webhook signature"""
        signature = request.headers.get('X-Hub-Signature-256', '')
        webhook_secret = self.secrets.get_secret('github/webhook_secret')
        return self.validate_webhook_signature(request.data, signature, webhook_secret)

# Rate limiting implementation
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/webhook/summary', methods=['POST'])
@limiter.limit("10 per minute")
@require_auth
def webhook_summary():
    if not webhook_security.verify_github_webhook():
        abort(401)
    # Process webhook
```

**Acceptance Criteria:**
- [ ] HMAC signature validation implemented
- [ ] Rate limiting per IP and per API key
- [ ] IP whitelisting capability
- [ ] Webhook replay attack prevention
- [ ] Comprehensive logging without sensitive data

---

## Phase 2: Core Security Implementation (Weeks 3-4)

### 2.1 Input Validation Framework [P2 - High]

**Implementation:**
```python
# validation/input_validator.py
from typing import Any, Dict
from pydantic import BaseModel, validator, ValidationError
import bleach

class SummaryRequest(BaseModel):
    channel_id: str
    message_count: int = 50
    time_range_hours: int = 24
    include_threads: bool = False
    
    @validator('channel_id')
    def validate_channel_id(cls, v):
        if not v or not v.isdigit() or len(v) < 17:
            raise ValueError('Invalid Discord channel ID')
        return v
    
    @validator('message_count')
    def validate_message_count(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('Message count must be between 1 and 1000')
        return v

class InputSanitizer:
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Remove potentially dangerous HTML/JS"""
        return bleach.clean(text, tags=[], strip=True)
    
    @staticmethod
    def validate_discord_content(content: str) -> str:
        """Sanitize Discord message content"""
        if len(content) > 4000:  # Discord limit
            raise ValueError('Content too long')
        return InputSanitizer.sanitize_html(content)
```

### 2.2 Secure Error Handling [P2 - High]

**Implementation:**
```python
# error/secure_handler.py
import logging
from flask import jsonify
from typing import Dict, Any

class SecureErrorHandler:
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.logger = logging.getLogger('security')
    
    def handle_error(self, error: Exception, request_id: str) -> Dict[str, Any]:
        """Handle errors without exposing sensitive information"""
        self.logger.error(f"Request {request_id}: {str(error)}", exc_info=True)
        
        if self.debug_mode:
            return {
                'error': str(error),
                'request_id': request_id,
                'type': type(error).__name__
            }
        
        # Production mode - generic error messages
        error_map = {
            'ValidationError': 'Invalid request data',
            'AuthenticationError': 'Authentication required',
            'RateLimitError': 'Rate limit exceeded',
            'APIError': 'External service unavailable'
        }
        
        return {
            'error': error_map.get(type(error).__name__, 'Internal server error'),
            'request_id': request_id
        }
```

### 2.3 Secure Logging Implementation [P2 - High]

**Implementation:**
```python
# logging/secure_logger.py
import logging
import json
import re
from typing import Any, Dict

class SecureLogger:
    def __init__(self):
        self.sensitive_patterns = [
            r'token["\s]*[:=]["\s]*([^"\s]+)',
            r'key["\s]*[:=]["\s]*([^"\s]+)',
            r'password["\s]*[:=]["\s]*([^"\s]+)',
            r'secret["\s]*[:=]["\s]*([^"\s]+)',
        ]
    
    def sanitize_log_data(self, data: Any) -> Any:
        """Remove sensitive information from logs"""
        if isinstance(data, dict):
            return {k: self._sanitize_value(k, v) for k, v in data.items()}
        elif isinstance(data, str):
            return self._sanitize_string(data)
        return data
    
    def _sanitize_value(self, key: str, value: Any) -> Any:
        sensitive_keys = ['token', 'key', 'password', 'secret', 'authorization']
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            return '[REDACTED]'
        return self.sanitize_log_data(value)
    
    def _sanitize_string(self, text: str) -> str:
        for pattern in self.sensitive_patterns:
            text = re.sub(pattern, r'\1[REDACTED]', text, flags=re.IGNORECASE)
        return text
```

---

## Phase 3: Security Integration & Testing (Weeks 5-8)

### 3.1 Dependency Security Scanning [P3 - Medium]

**CI/CD Integration:**
```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Python Security Scan
      run: |
        pip install safety bandit
        safety check
        bandit -r src/ -f json -o bandit-report.json
    
    - name: Dependency Check
      uses: pyupio/safety-action@v1
      with:
        api-key: ${{ secrets.SAFETY_API_KEY }}
    
    - name: Secret Scan
      uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        base: main
        head: HEAD
```

### 3.2 Security Testing Suite [P3 - Medium]

**Test Implementation:**
```python
# tests/security/test_auth.py
import pytest
import jwt
from auth.jwt_manager import JWTManager
from unittest.mock import Mock

class TestJWTSecurity:
    def test_token_expiration(self):
        """Test that expired tokens are rejected"""
        # Implementation
    
    def test_invalid_signature(self):
        """Test invalid signature rejection"""
        # Implementation
    
    def test_token_tampering(self):
        """Test token tampering detection"""
        # Implementation

# tests/security/test_webhooks.py
class TestWebhookSecurity:
    def test_signature_validation(self):
        """Test webhook signature validation"""
        # Implementation
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Implementation
    
    def test_replay_attack_prevention(self):
        """Test replay attack prevention"""
        # Implementation
```

### 3.3 Security Configuration Templates [P3 - Medium]

**Docker Security Configuration:**
```dockerfile
# Dockerfile.security
FROM python:3.11-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash summarybot

# Security hardening
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

USER summarybot
WORKDIR /home/summarybot/app

# Copy and install dependencies
COPY --chown=summarybot:summarybot requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=summarybot:summarybot src/ .

# Security: Run as non-root, read-only filesystem
USER summarybot
EXPOSE 5000

CMD ["python", "main.py"]
```

---

## Phase 4: Monitoring & Maintenance (Ongoing)

### 4.1 Security Monitoring Setup [P4 - Low]

**Monitoring Configuration:**
```python
# monitoring/security_monitor.py
import logging
from typing import Dict, Any
from datetime import datetime

class SecurityMonitor:
    def __init__(self):
        self.security_logger = logging.getLogger('security_events')
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events for monitoring"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'severity': self._get_severity(event_type)
        }
        self.security_logger.warning(f"SECURITY_EVENT: {json.dumps(event)}")
    
    def _get_severity(self, event_type: str) -> str:
        severity_map = {
            'failed_auth': 'HIGH',
            'rate_limit_exceeded': 'MEDIUM',
            'invalid_webhook': 'MEDIUM',
            'token_expired': 'LOW'
        }
        return severity_map.get(event_type, 'MEDIUM')
```

### 4.2 Security Checklist for Development

**Pre-Commit Checklist:**
- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented for all user inputs
- [ ] Error handling doesn't expose sensitive information
- [ ] Authentication required for all sensitive endpoints
- [ ] Rate limiting implemented where appropriate
- [ ] Logging doesn't contain sensitive data
- [ ] Dependencies scanned for vulnerabilities

**Pre-Deployment Checklist:**
- [ ] All secrets stored in secure management system
- [ ] JWT keys properly generated and stored
- [ ] Webhook signature validation working
- [ ] Security tests passing
- [ ] Dependency vulnerability scan clean
- [ ] Security monitoring configured
- [ ] Incident response plan documented

---

## Implementation Priority Matrix

### Immediate (Week 1)
1. **Secrets Management** - Block all other development
2. **Environment Configuration** - Required for any deployment
3. **Basic Authentication** - Required for API security

### High Priority (Week 2-3)
1. **JWT Implementation** - Required for webhook security
2. **Input Validation** - Required before handling user data
3. **Webhook Security** - Required for external integrations

### Medium Priority (Week 4-6)
1. **Security Testing** - Required before production
2. **Error Handling** - Important for production stability
3. **Dependency Scanning** - Important for ongoing security

### Low Priority (Ongoing)
1. **Advanced Monitoring** - Enhancement after basic security
2. **Security Headers** - Additional protection layer
3. **Performance Security** - Optimization after functionality

---

## Success Metrics

### Security Implementation KPIs:
- **Zero** hardcoded secrets in codebase
- **100%** of API endpoints with authentication
- **<5 seconds** average authentication response time
- **Zero** high-severity vulnerabilities in dependencies
- **90%+** security test coverage

### Monitoring KPIs:
- **<1 minute** security incident detection time
- **<5 minutes** security alert response time
- **Zero** unauthorized access attempts success rate
- **100%** webhook signature validation rate

---

## Budget & Resource Estimation

### Development Time:
- **Phase 1:** 40-60 hours (1-2 developers)
- **Phase 2:** 60-80 hours (1-2 developers)
- **Phase 3:** 40-60 hours (1-2 developers + security reviewer)
- **Phase 4:** 20-40 hours (ongoing maintenance)

### Tools & Services:
- **Secrets Management:** $0-200/month (depending on solution)
- **Security Scanning:** $0-100/month (depending on tools)
- **Monitoring:** $0-150/month (depending on scale)

**Total Estimated Implementation Cost:** 160-240 development hours + $0-450/month operational costs

---

## Risk Mitigation Timeline

| Week | Risk Reduced | Mitigation Completed |
|------|-------------|---------------------|
| 1 | Critical (90%) | Secrets management + basic auth |
| 2 | High (80%) | JWT implementation + webhook security |
| 4 | Medium (70%) | Input validation + error handling |
| 6 | Low (60%) | Security testing + monitoring |
| 8 | Minimal (90%) | Full security implementation |

---

*Document prepared by Security Review Agent*  
*Last updated: August 24, 2025*  
*Next review scheduled: After Phase 1 completion*