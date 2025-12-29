# Test Execution Guide

## Quick Reference

### Run All Tests
```bash
# All performance and security tests
pytest tests/performance/ tests/security/ -v

# With coverage report
pytest tests/performance/ tests/security/ --cov=src --cov-report=html --cov-report=term
```

### Run by Category
```bash
# Performance tests only
pytest tests/performance/ -v -m performance

# Security tests only  
pytest tests/security/ -v -m security

# Load testing only
pytest tests/performance/test_load_testing.py -v

# Security validation only
pytest tests/security/test_security_validation.py -v
```

### Run Specific Tests
```bash
# Single test file
pytest tests/performance/test_performance_optimization.py -v

# Single test class
pytest tests/performance/test_load_testing.py::TestSummarizationPerformance -v

# Single test method
pytest tests/security/test_audit_logging.py::TestSecurityEventLogging::test_brute_force_detection_logging -v
```

## Test Count: 71 Tests

- Performance Tests: 38 tests
- Security Tests: 33 tests

## File Locations

All test files are properly organized:

```
/workspaces/summarybot-ng/tests/
├── performance/
│   ├── __init__.py
│   ├── test_load_testing.py (14 tests)
│   └── test_performance_optimization.py (24 tests)
└── security/
    ├── __init__.py
    ├── test_audit_logging.py (14 tests)
    └── test_security_validation.py (19 tests)
```

## Documentation

- `/docs/PERFORMANCE_SECURITY_TESTS.md` - Complete test documentation
- `/docs/TEST_IMPLEMENTATION_SUMMARY.md` - Implementation summary
- `/docs/TEST_EXECUTION_GUIDE.md` - This file

## Success Criteria

All tests follow TDD best practices and validate:

Performance:
✓ Concurrent command handling (10+ simultaneous)
✓ API request handling (50+ simultaneous)  
✓ Message throughput (1000+ msgs/min)
✓ Summary generation times (small/medium/large)
✓ Cache efficiency (≥80% hit rate)
✓ Batch processing (≥3x speedup)
✓ Memory management (<500MB increase)

Security:
✓ Authentication and authorization
✓ Input validation and sanitization
✓ SQL injection prevention
✓ XSS prevention
✓ Command injection prevention
✓ Path traversal prevention
✓ Rate limiting and DOS protection
✓ Audit logging and security events

Total: 71 comprehensive tests covering all requirements!
