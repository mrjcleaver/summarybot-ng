# Makefile for Summary Bot NG Test Suite
# Provides convenient commands for running different types of tests

.PHONY: help test unit integration e2e performance security coverage clean install lint format

# Default target
help:
	@echo "Summary Bot NG Test Suite"
	@echo ""
	@echo "Available targets:"
	@echo "  help        - Show this help message"
	@echo "  install     - Install test dependencies"
	@echo "  test        - Run all tests"
	@echo "  unit        - Run unit tests only"
	@echo "  integration - Run integration tests only"
	@echo "  e2e         - Run end-to-end tests only"
	@echo "  performance - Run performance tests only"
	@echo "  security    - Run security tests only"
	@echo "  coverage    - Generate coverage report"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code"
	@echo "  clean       - Clean test artifacts"

# Install test dependencies
install:
	@echo "Installing test dependencies..."
	pip install -r requirements-test.txt

# Run all tests with coverage
test:
	@echo "Running all tests with coverage..."
	pytest --cov=src --cov-config=tests/coverage.ini --cov-report=html:tests/coverage_html --cov-report=xml:tests/coverage.xml --cov-report=term-missing -v

# Run only unit tests
unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v -m unit

# Run only integration tests
integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v -m integration

# Run only end-to-end tests
e2e:
	@echo "Running end-to-end tests..."
	pytest tests/e2e/ -v -m e2e

# Run only performance tests
performance:
	@echo "Running performance tests..."
	pytest tests/performance/ -v -m performance --tb=short

# Run only security tests
security:
	@echo "Running security tests..."
	pytest tests/security/ -v -m security

# Generate coverage report
coverage:
	@echo "Generating coverage report..."
	pytest --cov=src --cov-config=tests/coverage.ini --cov-report=html:tests/coverage_html --cov-report=xml:tests/coverage.xml --cov-report=term-missing tests/unit/ tests/integration/
	@echo "Coverage report generated in tests/coverage_html/index.html"

# Run linting checks
lint:
	@echo "Running linting checks..."
	flake8 src/ tests/ --max-line-length=120 --exclude=__pycache__
	mypy src/ --ignore-missing-imports
	black --check src/ tests/

# Format code
format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/

# Clean test artifacts
clean:
	@echo "Cleaning test artifacts..."
	rm -rf tests/coverage_html/
	rm -f tests/coverage.xml
	rm -f tests/junit.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Quick test run (unit + integration, no performance/security)
quick:
	@echo "Running quick tests (unit + integration)..."
	pytest tests/unit/ tests/integration/ -v --tb=short

# Test with verbose output and no coverage
debug:
	@echo "Running tests in debug mode..."
	pytest -v -s --tb=long tests/

# Parallel test execution
parallel:
	@echo "Running tests in parallel..."
	pytest -n auto --cov=src --cov-config=tests/coverage.ini tests/unit/ tests/integration/

# Continuous integration test run
ci:
	@echo "Running CI test suite..."
	pytest --cov=src --cov-config=tests/coverage.ini --cov-report=xml:tests/coverage.xml --cov-fail-under=85 --junitxml=tests/junit.xml -v tests/unit/ tests/integration/

# Generate test report
report:
	@echo "Generating comprehensive test report..."
	pytest --html=tests/report.html --self-contained-html --cov=src --cov-config=tests/coverage.ini --cov-report=html:tests/coverage_html tests/

# Benchmark tests
benchmark:
	@echo "Running benchmark tests..."
	pytest tests/performance/ -v --benchmark-only --benchmark-sort=mean

# Memory profiling tests
profile:
	@echo "Running memory profiling tests..."
	pytest tests/performance/ -v --profile-svg --profile

# Watch mode for development
watch:
	@echo "Running tests in watch mode..."
	pytest-watch tests/ src/ -- tests/unit/ tests/integration/ -v --tb=short