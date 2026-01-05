#!/bin/bash
# Health Check Script for Summary Bot NG
# Monitors bot status, API health, and system resources

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5000}"
HEALTH_ENDPOINT="${WEBHOOK_URL}/health"
LOG_FILE="${LOG_FILE:-summarybot.log}"
MAX_LOG_SIZE_MB=100
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=80

echo "================================================"
echo "Summary Bot NG - Health Check"
echo "================================================"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Function to print status
print_status() {
    local service=$1
    local status=$2
    local details=$3

    if [ "$status" == "OK" ]; then
        echo -e "${GREEN}✓${NC} $service: ${GREEN}$status${NC} $details"
    elif [ "$status" == "WARNING" ]; then
        echo -e "${YELLOW}⚠${NC} $service: ${YELLOW}$status${NC} $details"
    else
        echo -e "${RED}✗${NC} $service: ${RED}$status${NC} $details"
    fi
}

# 1. Check Bot Process
echo "1. Discord Bot Process"
BOT_PID=$(pgrep -f "python -m src.main" | head -1)
if [ -n "$BOT_PID" ]; then
    # Get process details
    BOT_CPU=$(ps -p $BOT_PID -o %cpu= | xargs)
    BOT_MEM=$(ps -p $BOT_PID -o %mem= | xargs)
    BOT_RSS=$(ps -p $BOT_PID -o rss= | xargs)
    BOT_RSS_MB=$((BOT_RSS / 1024))

    print_status "Process" "OK" "(PID: $BOT_PID, CPU: ${BOT_CPU}%, MEM: ${BOT_MEM}%, RSS: ${BOT_RSS_MB}MB)"

    # Check resource thresholds
    if (( $(echo "$BOT_CPU > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        print_status "CPU Usage" "WARNING" "High CPU usage detected: ${BOT_CPU}%"
    fi

    if (( $(echo "$BOT_MEM > $ALERT_THRESHOLD_MEM" | bc -l) )); then
        print_status "Memory Usage" "WARNING" "High memory usage detected: ${BOT_MEM}%"
    fi
else
    print_status "Process" "FAILED" "Bot process not running"
    exit 1
fi

echo ""

# 2. Check Webhook API Health
echo "2. Webhook API"
if command -v curl &> /dev/null; then
    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 5 "$HEALTH_ENDPOINT" 2>/dev/null || echo "000")
    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
    HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" == "200" ]; then
        print_status "Health Endpoint" "OK" "(HTTP 200)"

        # Parse JSON response if jq is available
        if command -v jq &> /dev/null && [ -n "$HEALTH_BODY" ]; then
            STATUS=$(echo "$HEALTH_BODY" | jq -r '.status' 2>/dev/null || echo "unknown")
            VERSION=$(echo "$HEALTH_BODY" | jq -r '.version' 2>/dev/null || echo "unknown")
            print_status "API Status" "OK" "($STATUS, v$VERSION)"

            # Check services
            SUMMARIZATION=$(echo "$HEALTH_BODY" | jq -r '.services.summarization_engine' 2>/dev/null)
            CLAUDE_API=$(echo "$HEALTH_BODY" | jq -r '.services.claude_api' 2>/dev/null)
            CACHE=$(echo "$HEALTH_BODY" | jq -r '.services.cache' 2>/dev/null)

            [ "$SUMMARIZATION" == "healthy" ] && print_status "Summarization" "OK" "" || print_status "Summarization" "FAILED" ""
            [ "$CLAUDE_API" == "true" ] && print_status "Claude API" "OK" "" || print_status "Claude API" "FAILED" ""
            [ "$CACHE" == "true" ] && print_status "Cache" "OK" "" || print_status "Cache" "WARNING" "(disabled)"
        fi
    else
        print_status "Health Endpoint" "FAILED" "(HTTP $HTTP_CODE)"
    fi
else
    print_status "Health Endpoint" "SKIPPED" "(curl not available)"
fi

echo ""

# 3. Check Discord Gateway Connection
echo "3. Discord Gateway"
if [ -f "$LOG_FILE" ]; then
    LAST_CONNECT=$(grep "connected to Gateway" "$LOG_FILE" | tail -1)
    LAST_READY=$(grep "Bot is ready" "$LOG_FILE" | tail -1)

    if [ -n "$LAST_READY" ]; then
        READY_TIME=$(echo "$LAST_READY" | awk '{print $1, $2}')
        print_status "Gateway Connection" "OK" "(Last ready: $READY_TIME)"
    elif [ -n "$LAST_CONNECT" ]; then
        print_status "Gateway Connection" "WARNING" "Connected but not ready"
    else
        print_status "Gateway Connection" "UNKNOWN" "No connection logs found"
    fi

    # Check for recent errors
    ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE" | tail -1 || echo "0")
    WARNING_COUNT=$(grep -c "WARNING" "$LOG_FILE" | tail -1 || echo "0")

    if [ "$ERROR_COUNT" -gt 0 ]; then
        print_status "Error Count" "WARNING" "($ERROR_COUNT errors in log)"
    fi
else
    print_status "Log File" "WARNING" "Log file not found: $LOG_FILE"
fi

echo ""

# 4. Check Log File Size
echo "4. Log Management"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -m "$LOG_FILE" | cut -f1)
    if [ "$LOG_SIZE" -gt "$MAX_LOG_SIZE_MB" ]; then
        print_status "Log Size" "WARNING" "(${LOG_SIZE}MB, threshold: ${MAX_LOG_SIZE_MB}MB)"
    else
        print_status "Log Size" "OK" "(${LOG_SIZE}MB)"
    fi
else
    print_status "Log File" "WARNING" "Not found"
fi

echo ""

# 5. Check Network Ports
echo "5. Network Ports"
if command -v lsof &> /dev/null; then
    PORT_5000=$(lsof -ti:5000 | head -1)
    if [ -n "$PORT_5000" ]; then
        print_status "Port 5000" "OK" "(Webhook API listening)"
    else
        print_status "Port 5000" "WARNING" "(No process listening)"
    fi
else
    print_status "Port Check" "SKIPPED" "(lsof not available)"
fi

echo ""

# 6. Check OpenRouter API Connectivity
echo "6. External APIs"
if [ -f "$LOG_FILE" ]; then
    LAST_OPENROUTER=$(grep "openrouter.ai" "$LOG_FILE" | grep "200 OK" | tail -1)
    if [ -n "$LAST_OPENROUTER" ]; then
        API_TIME=$(echo "$LAST_OPENROUTER" | awk '{print $1, $2}')
        print_status "OpenRouter API" "OK" "(Last success: $API_TIME)"
    else
        LAST_OPENROUTER_ERROR=$(grep "openrouter.ai" "$LOG_FILE" | tail -1)
        if [ -n "$LAST_OPENROUTER_ERROR" ]; then
            print_status "OpenRouter API" "WARNING" "Check logs for details"
        else
            print_status "OpenRouter API" "UNKNOWN" "No recent API calls"
        fi
    fi
fi

echo ""
echo "================================================"
echo "Health Check Complete"
echo "================================================"
