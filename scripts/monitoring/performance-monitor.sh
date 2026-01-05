#!/bin/bash
# Performance Monitoring Script for Summary Bot NG
# Tracks metrics over time and generates reports

set -e

# Configuration
METRICS_DIR="${METRICS_DIR:-./metrics}"
INTERVAL="${INTERVAL:-60}"  # seconds between samples
DURATION="${DURATION:-3600}"  # total monitoring duration (1 hour default)
LOG_FILE="${LOG_FILE:-summarybot.log}"

mkdir -p "$METRICS_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
METRICS_FILE="$METRICS_DIR/metrics_${TIMESTAMP}.csv"

echo "================================================"
echo "Summary Bot NG - Performance Monitor"
echo "================================================"
echo "Metrics file: $METRICS_FILE"
echo "Interval: ${INTERVAL}s"
echo "Duration: ${DURATION}s"
echo ""

# CSV Header
echo "timestamp,bot_pid,cpu_percent,mem_percent,rss_mb,vsz_mb,threads,open_files,api_requests,errors,warnings" > "$METRICS_FILE"

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))
SAMPLE_COUNT=0

echo "Starting monitoring... (Press Ctrl+C to stop)"
echo ""

trap 'echo ""; echo "Monitoring stopped. Collected $SAMPLE_COUNT samples."; exit 0' INT TERM

while [ $(date +%s) -lt $END_TIME ]; do
    CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')

    # Find bot process
    BOT_PID=$(pgrep -f "python -m src.main" | head -1)

    if [ -z "$BOT_PID" ]; then
        echo "[$(date '+%H:%M:%S')] WARNING: Bot process not found"
        sleep "$INTERVAL"
        continue
    fi

    # Collect metrics
    CPU=$(ps -p $BOT_PID -o %cpu= | xargs)
    MEM=$(ps -p $BOT_PID -o %mem= | xargs)
    RSS=$(ps -p $BOT_PID -o rss= | xargs)
    RSS_MB=$((RSS / 1024))
    VSZ=$(ps -p $BOT_PID -o vsz= | xargs)
    VSZ_MB=$((VSZ / 1024))
    THREADS=$(ps -p $BOT_PID -o nlwp= | xargs)

    # Count open files
    if command -v lsof &> /dev/null; then
        OPEN_FILES=$(lsof -p $BOT_PID 2>/dev/null | wc -l)
    else
        OPEN_FILES="N/A"
    fi

    # Count API requests and errors from logs
    if [ -f "$LOG_FILE" ]; then
        API_REQUESTS=$(grep -c "openrouter.ai.*200 OK" "$LOG_FILE" || echo "0")
        ERRORS=$(grep -c "ERROR" "$LOG_FILE" || echo "0")
        WARNINGS=$(grep -c "WARNING" "$LOG_FILE" || echo "0")
    else
        API_REQUESTS="0"
        ERRORS="0"
        WARNINGS="0"
    fi

    # Write to CSV
    echo "$CURRENT_TIME,$BOT_PID,$CPU,$MEM,$RSS_MB,$VSZ_MB,$THREADS,$OPEN_FILES,$API_REQUESTS,$ERRORS,$WARNINGS" >> "$METRICS_FILE"

    # Display current metrics
    SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    echo "[$(date '+%H:%M:%S')] Sample $SAMPLE_COUNT: CPU=${CPU}% MEM=${MEM}% RSS=${RSS_MB}MB Threads=$THREADS API=$API_REQUESTS"

    sleep "$INTERVAL"
done

echo ""
echo "================================================"
echo "Performance Monitoring Complete"
echo "================================================"
echo "Samples collected: $SAMPLE_COUNT"
echo "Metrics file: $METRICS_FILE"
echo ""

# Generate summary statistics
if command -v awk &> /dev/null; then
    echo "Summary Statistics:"
    echo "-------------------"

    awk -F',' 'NR>1 {
        cpu+=$3; mem+=$4; rss+=$5;
        if(NR==2 || $3>max_cpu) max_cpu=$3;
        if(NR==2 || $3<min_cpu) min_cpu=$3;
        if(NR==2 || $4>max_mem) max_mem=$4;
        if(NR==2 || $4<min_mem) min_mem=$4;
        count++
    } END {
        if(count>0) {
            printf "CPU: avg=%.2f%%, min=%.2f%%, max=%.2f%%\n", cpu/count, min_cpu, max_cpu;
            printf "Memory: avg=%.2f%%, min=%.2f%%, max=%.2f%%\n", mem/count, min_mem, max_mem;
            printf "RSS: avg=%.0fMB\n", rss/count;
        }
    }' "$METRICS_FILE"
fi
