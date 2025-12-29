#!/bin/bash
# Test runner script for Summary Bot NG
# Sets up PYTHONPATH and runs tests with proper configuration

export PYTHONPATH=/workspaces/summarybot-ng:$PYTHONPATH

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Summary Bot NG Test Suite ===${NC}\n"

# Parse command line arguments
TEST_PATH="${1:-tests/}"
ARGS="${@:2}"

echo "Running tests from: $TEST_PATH"
echo "Additional args: $ARGS"
echo ""

# Run tests
pytest "$TEST_PATH" \
    -v \
    --tb=short \
    --maxfail=10 \
    --strict-markers \
    $ARGS

TEST_EXIT_CODE=$?

# Summary
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi

exit $TEST_EXIT_CODE
