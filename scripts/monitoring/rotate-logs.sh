#!/bin/bash
# Log Rotation Script
# Compresses and archives old log files

set -e

LOG_FILE="${LOG_FILE:-summarybot.log}"
LOG_DIR="./logs/archive"
KEEP_FILES="${KEEP_FILES:-10}"
MAX_SIZE_MB="${MAX_SIZE_MB:-100}"

mkdir -p "$LOG_DIR"

echo "================================================"
echo "Summary Bot NG - Log Rotation"
echo "================================================"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check if log file exists and needs rotation
if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    exit 0
fi

# Get current log size
LOG_SIZE=$(du -m "$LOG_FILE" | cut -f1)
echo "Current log size: ${LOG_SIZE}MB"

if [ "$LOG_SIZE" -lt "$MAX_SIZE_MB" ]; then
    echo "Log size below threshold (${MAX_SIZE_MB}MB), skipping rotation"
    exit 0
fi

# Rotate log
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
ARCHIVE_NAME="summarybot_${TIMESTAMP}.log"

echo "Rotating log file..."
cp "$LOG_FILE" "$LOG_DIR/$ARCHIVE_NAME"

# Compress archived log
if command -v gzip &> /dev/null; then
    echo "Compressing archive..."
    gzip "$LOG_DIR/$ARCHIVE_NAME"
    ARCHIVE_NAME="${ARCHIVE_NAME}.gz"
fi

# Truncate current log
echo "" > "$LOG_FILE"

echo "✓ Log rotated to: $LOG_DIR/$ARCHIVE_NAME"
echo ""

# Clean up old archives
echo "Cleaning up old archives (keeping last $KEEP_FILES)..."
cd "$LOG_DIR"
ls -t summarybot_*.log* | tail -n +$((KEEP_FILES + 1)) | xargs -r rm -v

echo ""
echo "================================================"
echo "Log Rotation Complete"
echo "================================================"
