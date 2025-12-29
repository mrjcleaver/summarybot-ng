# Performance and Security Test Suite

## Overview

Comprehensive test suite for Summary Bot NG covering performance benchmarks, load testing, security validation, and audit logging.

## Test Statistics

- **Total Tests**: 42+
- **Performance Tests**: 20+
- **Security Tests**: 22+
- **Coverage Areas**: 8 major categories

## Performance Tests

### 1. Load Testing (`tests/performance/test_load_testing.py`)

#### Concurrent Command Handling
- **Test**: `test_concurrent_discord_command_handling`
- **Target**: Handle 10+ simultaneous Discord commands
- **Success Criteria**: Complete 15 concurrent commands in <0.5s

#### Concurrent API Requests
- **Test**: `test_concurrent_api_requests`
- **Target**: Handle 50+ simultaneous API requests
- **Success Criteria**: Complete 50 requests in <1.0s

#### Message Processing Throughput
- **Test**: `test_message_processing_throughput`
- **Target**: Process 1000+ messages/minute
- **Success Criteria**: Achieve ≥1000 msg/min throughput

#### Summary Generation Time Targets
- **Test**: `test_summary_generation_time_targets`
- **Batch Sizes**:
  - Small (<100 messages): Target <30s
  - Medium (100-1000): Target <2min
  - Large (1000-10000): Target <5min

#### Memory and Performance
- **Test**: `test_large_batch_summarization_performance`
- **Target**: Process 10K messages with <500MB memory increase
- **Test**: `test_memory_leak_detection`
- **Target**: <10MB memory per cycle over 20 iterations

### 2. Performance Optimization (`tests/performance/test_performance_optimization.py`)

#### Cache Performance
- **Test**: `test_cache_hit_rate_optimization`
- **Target**: Achieve ≥80% cache hit rate
- **Test**: `test_cache_performance_improvement`
- **Target**: ≥10x speedup from cache hits

#### Batch Processing
- **Test**: `test_batch_processing_efficiency`
- **Target**: ≥3x speedup from batch processing
- **Test**: `test_batch_size_optimization`
- **Target**: Identify optimal batch size (≥10)

#### Connection Pooling
- **Test**: `test_connection_pool_efficiency`
- **Target**: Limit connections to pool size
- **Test**: `test_concurrent_request_handling`
- **Target**: Handle ≥3 concurrent requests efficiently

#### Critical Path Optimization
- **Test**: `test_prompt_building_performance`
- **Target**: Build prompts for 5K messages in <1s
- **Test**: `test_response_parsing_performance`
- **Target**: Parse responses in <100ms
- **Test**: `test_message_filtering_performance`
- **Target**: Filter 10K messages in <500ms
- **Test**: `test_token_counting_performance`
- **Target**: Count tokens in <10ms avg, <50ms max

## Security Tests

### 1. Security Validation (`tests/security/test_security_validation.py`)

#### Permission Validation
- **Test**: `test_unauthorized_channel_access`
- **Purpose**: Block access to unauthorized channels
- **Test**: `test_command_permission_escalation_prevention`
- **Purpose**: Prevent privilege escalation attempts

#### Input Validation
- **Test**: `test_message_content_sanitization`
- **Purpose**: Sanitize XSS and malicious content
- **Test**: `test_sql_injection_prevention`
- **Purpose**: Use parameterized queries
- **Test**: `test_command_parameter_validation`
- **Purpose**: Validate all command parameters
- **Test**: `test_regex_dos_prevention`
- **Purpose**: Prevent ReDoS attacks with timeouts

#### Authentication Security
- **Test**: `test_jwt_token_validation`
- **Purpose**: Validate JWT tokens correctly
- **Test**: `test_expired_token_rejection`
- **Purpose**: Reject expired tokens
- **Test**: `test_tampered_token_rejection`
- **Purpose**: Detect token tampering
- **Test**: `test_timing_attack_resistance`
- **Purpose**: Prevent timing-based attacks

#### Rate Limiting and DOS Protection
- **Test**: `test_rate_limit_enforcement`
- **Purpose**: Enforce rate limits (60 req/min)
- **Test**: `test_per_client_rate_limiting`
- **Purpose**: Apply limits per client
- **Test**: `test_dos_protection_burst_requests`
- **Purpose**: Block burst attack patterns
- **Test**: `test_slowloris_protection`
- **Purpose**: Timeout slow requests (30s)

#### Command Injection Prevention
- **Test**: `test_webhook_url_command_injection`
- **Purpose**: Prevent command injection in URLs
- **Test**: `test_shell_metacharacter_filtering`
- **Purpose**: Filter shell metacharacters
- **Test**: `test_subprocess_injection_prevention`
- **Purpose**: Use proper escaping (shlex.quote)

#### Path Traversal Prevention
- **Test**: `test_directory_traversal_prevention`
- **Purpose**: Block path traversal attempts
- **Test**: `test_safe_path_resolution`
- **Purpose**: Validate paths within base directory
- **Test**: `test_symlink_attack_prevention`
- **Purpose**: Detect symlink escape attempts

#### Advanced Input Validation
- **Test**: `test_unicode_normalization_bypass_prevention`
- **Purpose**: Prevent unicode bypass attacks
- **Test**: `test_json_injection_prevention`
- **Purpose**: Prevent JSON injection/pollution
- **Test**: `test_xml_entity_expansion_prevention`
- **Purpose**: Prevent Billion Laughs attack
- **Test**: `test_ldap_injection_prevention`
- **Purpose**: Escape LDAP special characters

### 2. Audit Logging (`tests/security/test_audit_logging.py`)

#### Security Event Logging
- **Test**: `test_successful_authentication_logging`
- **Purpose**: Log successful auth events
- **Test**: `test_failed_authentication_logging`
- **Purpose**: Log all failed auth attempts
- **Test**: `test_brute_force_detection_logging`
- **Purpose**: Detect and log brute force (>5 failures/5min)
- **Test**: `test_sensitive_data_redaction_in_logs`
- **Purpose**: Redact passwords, tokens, API keys

#### Permission Denial Logging
- **Test**: `test_admin_action_denial_logging`
- **Purpose**: Log unauthorized admin attempts
- **Test**: `test_privilege_escalation_attempt_logging`
- **Purpose**: Log privilege escalation attempts
- **Test**: `test_repeated_denial_pattern_detection`
- **Purpose**: Detect persistent access attempts

#### Attack Detection
- **Test**: `test_ip_based_attack_detection`
- **Purpose**: Detect distributed attacks from single IP
- **Test**: `test_suspicious_activity_logging`
- **Purpose**: Log SQL injection, XSS, rate limit violations

## Running Tests

### Run All Performance Tests
```bash
pytest tests/performance/ -v --benchmark-only
```

### Run All Security Tests
```bash
pytest tests/security/ -v -m security
```

### Run Specific Test Categories
```bash
# Load testing only
pytest tests/performance/test_load_testing.py -v

# Cache performance only
pytest tests/performance/test_performance_optimization.py::TestCachePerformance -v

# Authentication security only
pytest tests/security/test_security_validation.py::TestAuthenticationSecurity -v

# Audit logging only
pytest tests/security/test_audit_logging.py -v
```

### Run with Coverage
```bash
pytest tests/performance/ tests/security/ --cov=src --cov-report=html
```

### Run Performance Benchmarks
```bash
pytest tests/performance/ --benchmark-autosave --benchmark-compare
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.slow` - Long-running tests

## Performance Targets Summary

| Category | Metric | Target |
|----------|--------|--------|
| Concurrent Commands | Simultaneous | 10+ |
| Concurrent API Requests | Simultaneous | 50+ |
| Message Throughput | Messages/min | 1000+ |
| Small Batch Summary | Time | <30s |
| Medium Batch Summary | Time | <2min |
| Large Batch Summary | Time | <5min |
| Cache Hit Rate | Percentage | ≥80% |
| Batch Processing Speedup | Factor | ≥3x |
| Memory Usage | Increase | <500MB |
| Database Queries | Time | <500ms |

## Security Coverage

### Threat Categories Tested

1. **Authentication Attacks**
   - Brute force
   - Token tampering
   - Timing attacks
   - Credential stuffing

2. **Injection Attacks**
   - SQL injection
   - Command injection
   - XSS
   - LDAP injection
   - JSON injection
   - XML entity expansion

3. **Authorization Attacks**
   - Privilege escalation
   - Permission bypass
   - Cache poisoning

4. **DOS Attacks**
   - Rate limiting bypass
   - Burst requests
   - Slowloris
   - ReDoS

5. **File System Attacks**
   - Path traversal
   - Symlink attacks
   - File upload bypass

6. **Input Validation**
   - Unicode normalization bypass
   - Shell metacharacters
   - Parameter tampering

## Continuous Monitoring

### Performance Regression Detection

Tests include benchmarks to detect performance regressions:

```bash
# Establish baseline
pytest tests/performance/ --benchmark-save=baseline

# Compare against baseline
pytest tests/performance/ --benchmark-compare=baseline
```

### Security Audit Schedule

- **Daily**: Run full security test suite
- **Pre-commit**: Run input validation tests
- **Pre-deployment**: Run complete test suite with coverage
- **Post-incident**: Review and update relevant tests

## Dependencies

Required packages (from `requirements-test.txt`):

```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-benchmark>=4.0.0
pytest-xdist>=3.3.0
psutil>=5.9.0
pyjwt>=2.8.0
cryptography>=41.0.0
```

## Best Practices

### Writing New Tests

1. **Isolation**: Each test should be independent
2. **Clarity**: Use descriptive names and docstrings
3. **Assertions**: Clear success/failure criteria
4. **Performance**: Include timing assertions
5. **Security**: Test both positive and negative cases
6. **Documentation**: Document attack vectors tested

### Test Maintenance

1. Update tests when adding new features
2. Review security tests after incidents
3. Adjust performance targets based on metrics
4. Keep attack patterns current
5. Document known limitations

## Known Limitations

1. Some tests use mocks - supplement with integration tests
2. Performance targets may vary by hardware
3. Security tests don't cover all possible attack vectors
4. Rate limiting tests use in-memory storage

## Future Enhancements

1. Add load testing with realistic Discord traffic patterns
2. Implement chaos engineering tests
3. Add penetration testing scenarios
4. Create performance regression tracking
5. Add security compliance validation (OWASP Top 10)
6. Implement fuzzing tests for input validation

## References

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Security Testing Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Application_Security_Testing_Cheat_Sheet.html)
