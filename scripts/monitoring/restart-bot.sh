#!/bin/bash
# Automated Bot Restart Script
# Used by monitoring system for auto-remediation

set -e

LOG_FILE="${LOG_FILE:-summarybot.log}"
BACKUP_LOG="${LOG_FILE}.$(date +%Y%m%d_%H%M%S)"

echo "================================================"
echo "Summary Bot NG - Automated Restart"
echo "================================================"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. Backup current log
if [ -f "$LOG_FILE" ]; then
    echo "Backing up log file to: $BACKUP_LOG"
    cp "$LOG_FILE" "$BACKUP_LOG"
fi

# 2. Stop current process
echo "Stopping bot process..."
BOT_PID=$(pgrep -f "python -m src.main" | head -1)

if [ -n "$BOT_PID" ]; then
    echo "Found bot process: PID $BOT_PID"
    kill -TERM "$BOT_PID" 2>/dev/null || true

    # Wait for graceful shutdown (max 10 seconds)
    for i in {1..10}; do
        if ! ps -p "$BOT_PID" > /dev/null 2>&1; then
            echo "Process stopped gracefully"
            break
        fi
        sleep 1
    done

    # Force kill if still running
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        echo "Force killing process..."
        kill -9 "$BOT_PID" 2>/dev/null || true
    fi
else
    echo "No running bot process found"
fi

# 3. Kill any processes on port 5000
echo "Cleaning up port 5000..."
lsof -ti:5000 | xargs -r kill -9 2>/dev/null || true
sleep 2

# 4. Start bot
echo "Starting bot..."
cd /workspaces/summarybot-ng
PYTHONPATH=/workspaces/summarybot-ng poetry run python -m src.main > "$LOG_FILE" 2>&1 &
NEW_PID=$!

echo "Bot started with PID: $NEW_PID"
sleep 3

# 5. Verify startup
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    echo "✓ Bot process is running"

    # Wait for health check
    echo "Waiting for health check..."
    for i in {1..30}; do
        if curl -s http://localhost:5000/health > /dev/null 2>&1; then
            echo "✓ Health check passed"
            echo ""
            echo "================================================"
            echo "Restart Complete - Bot is healthy"
            echo "================================================"
            exit 0
        fi
        sleep 1
    done

    echo "⚠ Warning: Health check timeout"
    exit 1
else
    echo "✗ Failed to start bot"
    exit 1
fi
