# Post-Deployment Monitoring Guide

## Overview

This guide provides comprehensive monitoring procedures for Summary Bot NG in production environments. It covers health checks, performance monitoring, alerting, and incident response.

## Table of Contents

- [Quick Start](#quick-start)
- [Monitoring Scripts](#monitoring-scripts)
- [Health Checks](#health-checks)
- [Performance Metrics](#performance-metrics)
- [Alerting Configuration](#alerting-configuration)
- [Incident Response](#incident-response)
- [Log Management](#log-management)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Run Health Check

```bash
# Quick health status
./scripts/monitoring/health-check.sh

# Health check with custom webhook URL
WEBHOOK_URL=http://localhost:8080 ./scripts/monitoring/health-check.sh
```

### Start Performance Monitoring

```bash
# Monitor for 1 hour (default)
./scripts/monitoring/performance-monitor.sh

# Custom monitoring duration (30 minutes)
DURATION=1800 ./scripts/monitoring/performance-monitor.sh

# Custom sampling interval (30 seconds)
INTERVAL=30 DURATION=600 ./scripts/monitoring/performance-monitor.sh
```

### Manual Bot Restart

```bash
# Graceful restart with health verification
./scripts/monitoring/restart-bot.sh
```

## Monitoring Scripts

### 1. Health Check Script

**Location:** `scripts/monitoring/health-check.sh`

**Purpose:** Comprehensive system health verification

**Checks Performed:**
- Discord bot process status (PID, CPU, memory)
- Webhook API health endpoint
- Discord gateway connection
- Log file analysis (errors, warnings)
- Network port status
- OpenRouter API connectivity

**Usage:**

```bash
# Basic health check
./scripts/monitoring/health-check.sh

# Custom configuration
LOG_FILE=./logs/bot.log WEBHOOK_URL=http://localhost:5000 ./scripts/monitoring/health-check.sh
```

**Output:**

```
================================================
Summary Bot NG - Health Check
================================================
Timestamp: 2026-01-05 15:04:00

1. Discord Bot Process
✓ Process: OK (PID: 30061, CPU: 0.2%, MEM: 1.5%, RSS: 89MB)

2. Webhook API
✓ Health Endpoint: OK (HTTP 200)
✓ API Status: OK (healthy, v2.0.0)
✓ Summarization: OK
✓ Claude API: OK
⚠ Cache: WARNING (disabled)

3. Discord Gateway
✓ Gateway Connection: OK (Last ready: 2026-01-05 15:04:21)

4. Log Management
✓ Log Size: OK (15MB)

5. Network Ports
✓ Port 5000: OK (Webhook API listening)

6. External APIs
✓ OpenRouter API: OK (Last success: 2026-01-05 15:04:48)

================================================
Health Check Complete
================================================
```

### 2. Performance Monitor Script

**Location:** `scripts/monitoring/performance-monitor.sh`

**Purpose:** Continuous performance metrics collection

**Metrics Collected:**
- CPU usage percentage
- Memory usage percentage (physical and virtual)
- Thread count
- Open file descriptors
- API request count
- Error/warning counts

**Usage:**

```bash
# Monitor for 1 hour with 60-second samples
./scripts/monitoring/performance-monitor.sh

# Monitor for 10 minutes with 30-second samples
DURATION=600 INTERVAL=30 ./scripts/monitoring/performance-monitor.sh

# Custom metrics directory
METRICS_DIR=./data/metrics ./scripts/monitoring/performance-monitor.sh
```

**Output Files:**

Metrics are saved to CSV files in `./metrics/`:

```csv
timestamp,bot_pid,cpu_percent,mem_percent,rss_mb,vsz_mb,threads,open_files,api_requests,errors,warnings
2026-01-05 15:00:00,30061,0.2,1.5,89,523,12,45,127,0,3
2026-01-05 15:01:00,30061,0.3,1.6,91,523,12,47,135,0,3
```

**Summary Statistics:**

```
Summary Statistics:
-------------------
CPU: avg=0.25%, min=0.10%, max=0.50%
Memory: avg=1.55%, min=1.50%, max=1.65%
RSS: avg=90MB
```

### 3. Restart Script

**Location:** `scripts/monitoring/restart-bot.sh`

**Purpose:** Automated bot restart with health verification

**Process:**
1. Backup current log file
2. Graceful shutdown (SIGTERM, 10s timeout)
3. Force kill if necessary (SIGKILL)
4. Clean up port 5000
5. Start new bot process
6. Verify health endpoint

**Usage:**

```bash
# Restart with default log file
./scripts/monitoring/restart-bot.sh

# Custom log file
LOG_FILE=./logs/bot.log ./scripts/monitoring/restart-bot.sh
```

### 4. Log Rotation Script

**Location:** `scripts/monitoring/rotate-logs.sh`

**Purpose:** Automatic log file rotation and archiving

**Features:**
- Size-based rotation (default: 100MB threshold)
- Gzip compression
- Archive retention (default: keep 10 files)
- Automatic cleanup of old archives

**Usage:**

```bash
# Rotate if log exceeds 100MB
./scripts/monitoring/rotate-logs.sh

# Custom threshold and retention
MAX_SIZE_MB=50 KEEP_FILES=20 ./scripts/monitoring/rotate-logs.sh
```

## Health Checks

### Manual Health Verification

**1. Check Bot Process:**

```bash
ps aux | grep "python -m src.main" | grep -v grep
```

Expected output:
```
vscode    30061  0.2  1.5  535312  91284  Sl   15:04   0:02 python -m src.main
```

**2. Test Health Endpoint:**

```bash
curl http://localhost:5000/health | jq .
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "summarization_engine": "healthy",
    "claude_api": true,
    "cache": true
  }
}
```

**3. Check Discord Connection:**

```bash
tail -f summarybot.log | grep -i "gateway\|ready"
```

Expected logs:
```
discord.gateway - INFO - Shard ID None has connected to Gateway
src.discord_bot.events - INFO - Bot is ready! Logged in as summarizer-ng#1378
```

**4. Test Summarization:**

```bash
# Via Discord: Use /summarize command in a channel
# Via API:
curl -X POST http://localhost:5000/api/v1/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "messages": [
      {"role": "user", "content": "Test message 1"},
      {"role": "user", "content": "Test message 2"}
    ]
  }'
```

### Automated Health Monitoring

**Cron Job Setup:**

```bash
# Add to crontab (check every 5 minutes)
*/5 * * * * /workspaces/summarybot-ng/scripts/monitoring/health-check.sh >> /var/log/summarybot-health.log 2>&1
```

**Docker Healthcheck:**

Already configured in `Dockerfile`:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
```

## Performance Metrics

### Key Metrics to Monitor

**1. Resource Usage:**
- **CPU Usage:** Normal: 0.1-2%, Warning: >70%, Critical: >85%
- **Memory (RSS):** Normal: 80-120MB, Warning: >500MB, Critical: >1GB
- **Thread Count:** Normal: 10-20, Warning: >50, Critical: >100

**2. API Performance:**
- **Health Check Response Time:** Normal: <100ms, Warning: >2s, Critical: >5s
- **Summarization Response Time:** Normal: 1-3s, Warning: >10s, Critical: >30s
- **OpenRouter API Success Rate:** Normal: >99%, Warning: <95%, Critical: <90%

**3. Error Rates:**
- **Application Errors:** Normal: 0-1/hour, Warning: >5/hour, Critical: >20/hour
- **API Errors:** Normal: 0-2/hour, Warning: >10/hour, Critical: >50/hour
- **Gateway Disconnections:** Normal: 0/day, Warning: >1/day, Critical: >5/day

### Performance Analysis

**Analyze Collected Metrics:**

```bash
# View metrics from specific time period
cat metrics/metrics_20260105_150000.csv | grep "15:30:"

# Calculate average CPU over time
awk -F',' 'NR>1 {sum+=$3; count++} END {print "Avg CPU:", sum/count "%"}' metrics/metrics_*.csv

# Find peak memory usage
awk -F',' 'NR>1 {if($5>max) max=$5} END {print "Peak RSS:", max "MB"}' metrics/metrics_*.csv

# Count API requests per hour
awk -F',' 'NR>1 {print $1}' metrics/metrics_*.csv | cut -d' ' -f2 | cut -d: -f1 | sort | uniq -c
```

## Alerting Configuration

### Alert Configuration File

**Location:** `scripts/monitoring/alert-config.yml`

**Key Thresholds:**

```yaml
thresholds:
  cpu_usage:
    warning: 70
    critical: 85
    duration_seconds: 300

  memory_usage:
    warning: 75
    critical: 90
    duration_seconds: 300

  error_rate:
    warning: 5
    critical: 20
    window_minutes: 5
```

### Notification Channels

**1. Discord Webhook:**

```yaml
discord:
  enabled: true
  webhook_url: "${DISCORD_ALERT_WEBHOOK_URL}"
  alert_levels: ["warning", "critical"]
```

Setup:
1. Create webhook in Discord Server Settings → Integrations
2. Set environment variable: `export DISCORD_ALERT_WEBHOOK_URL="https://discord.com/api/webhooks/..."`

**2. Email Notifications:**

```yaml
email:
  enabled: true
  smtp_host: "${SMTP_HOST}"
  smtp_port: 587
  from_address: "alerts@summarybot.local"
  to_addresses: ["admin@example.com"]
```

**3. Slack Integration:**

```yaml
slack:
  enabled: true
  webhook_url: "${SLACK_WEBHOOK_URL}"
  channel: "#summarybot-alerts"
```

**4. PagerDuty:**

```yaml
pagerduty:
  enabled: true
  routing_key: "${PAGERDUTY_ROUTING_KEY}"
  alert_levels: ["critical"]
```

### Alert Rules

**Built-in Rules:**

1. **bot_process_down:** Bot process not running → auto-restart
2. **high_cpu_usage:** CPU >85% for 5 minutes → investigate
3. **high_memory_usage:** Memory >90% for 5 minutes → investigate
4. **api_health_failure:** Health check fails → auto-restart
5. **high_error_rate:** >20 errors/min → investigate
6. **discord_gateway_disconnected:** No heartbeat for 60s → auto-restart
7. **log_file_size:** Log >100MB → auto-rotate

## Incident Response

### Incident Severity Levels

**P1 - Critical:**
- Bot completely down
- Cannot connect to Discord
- No response from health endpoint
- **Response Time:** Immediate
- **Action:** Auto-restart + escalate

**P2 - High:**
- High error rate (>20 errors/min)
- Performance degradation (>85% CPU/memory)
- Frequent restarts (>3 per hour)
- **Response Time:** <15 minutes
- **Action:** Investigate + manual intervention

**P3 - Medium:**
- Intermittent errors
- Moderate performance issues (>70% CPU/memory)
- Log file growing rapidly
- **Response Time:** <1 hour
- **Action:** Monitor + schedule fix

**P4 - Low:**
- Minor warnings
- Non-critical configuration issues
- **Response Time:** <24 hours
- **Action:** Document + fix in next deployment

### Incident Response Procedures

**1. Bot Process Down (P1):**

```bash
# Check if process exists
pgrep -f "python -m src.main"

# Check recent logs for crash reason
tail -100 summarybot.log | grep -i "error\|exception\|traceback"

# Restart bot
./scripts/monitoring/restart-bot.sh

# Verify health
./scripts/monitoring/health-check.sh

# If restart fails, check:
# - Discord token validity
# - API key configuration
# - Network connectivity
# - Disk space
```

**2. High Error Rate (P2):**

```bash
# Identify error patterns
grep "ERROR" summarybot.log | tail -50

# Check OpenRouter API status
curl -I https://openrouter.ai/api/v1/models

# Check rate limits
grep "rate limit" summarybot.log -i

# Monitor real-time logs
tail -f summarybot.log | grep -i "error\|warning"
```

**3. Performance Degradation (P2):**

```bash
# Check resource usage
top -p $(pgrep -f "python -m src.main")

# Analyze metrics
./scripts/monitoring/performance-monitor.sh

# Check for memory leaks
ps -p $(pgrep -f "python -m src.main") -o pid,rss,vsz,cmd

# Consider restart if memory usage excessive
```

**4. Discord Gateway Disconnection (P2):**

```bash
# Check connection status
grep "gateway" summarybot.log -i | tail -20

# Check network connectivity
ping -c 5 discord.com

# Restart bot to reconnect
./scripts/monitoring/restart-bot.sh
```

### Runbook: Common Scenarios

**Scenario 1: Bot Not Responding to Commands**

1. Check bot is online: `./scripts/monitoring/health-check.sh`
2. Verify Discord connection: `grep "Bot is ready" summarybot.log | tail -1`
3. Check command sync: `grep "Synced.*commands" summarybot.log | tail -1`
4. Test health endpoint: `curl http://localhost:5000/health`
5. If all pass, check Discord API status: https://discordstatus.com
6. Try re-syncing commands by restarting bot

**Scenario 2: Summarization Failures**

1. Check recent errors: `grep "summarize" summarybot.log -i | grep -i error | tail -20`
2. Verify OpenRouter API key: `echo $OPENROUTER_API_KEY | wc -c` (should be >10)
3. Test OpenRouter directly:
   ```bash
   curl -X POST https://openrouter.ai/api/v1/chat/completions \
     -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"anthropic/claude-3.5-sonnet","messages":[{"role":"user","content":"test"}]}'
   ```
4. Check model normalization: `grep "Normalized model" summarybot.log | tail -5`
5. Verify no rate limiting: `grep "rate limit" summarybot.log -i`

**Scenario 3: High Memory Usage**

1. Check current usage: `ps -p $(pgrep -f "python -m src.main") -o pid,rss,vsz`
2. Enable memory profiling (add to code if needed)
3. Check for cache issues: `grep "cache" summarybot.log -i | tail -20`
4. Restart bot to clear memory: `./scripts/monitoring/restart-bot.sh`
5. If persists, investigate memory leak with profiling tools

## Log Management

### Log Locations

- **Main Bot Log:** `summarybot.log` (or custom path via `LOG_FILE` env var)
- **Archived Logs:** `./logs/archive/summarybot_YYYYMMDD_HHMMSS.log.gz`
- **Health Check Logs:** `./logs/health-check.log` (if using cron)
- **Alert Logs:** `./logs/alerts.log`
- **Performance Metrics:** `./metrics/metrics_YYYYMMDD_HHMMSS.csv`

### Log Rotation

**Automatic Rotation:**

```bash
# Via cron (daily at 2 AM)
0 2 * * * /workspaces/summarybot-ng/scripts/monitoring/rotate-logs.sh >> /var/log/summarybot-rotation.log 2>&1

# Via size threshold
*/30 * * * * MAX_SIZE_MB=100 /workspaces/summarybot-ng/scripts/monitoring/rotate-logs.sh
```

**Manual Rotation:**

```bash
./scripts/monitoring/rotate-logs.sh
```

### Log Analysis

**Search for Errors:**

```bash
# All errors today
grep "ERROR" summarybot.log | grep "$(date +%Y-%m-%d)"

# Specific error types
grep "APIError\|ConnectionError\|TimeoutError" summarybot.log

# Error frequency by hour
grep "ERROR" summarybot.log | awk '{print $2}' | cut -d: -f1 | sort | uniq -c
```

**Track API Calls:**

```bash
# OpenRouter API calls
grep "openrouter.ai" summarybot.log | grep "200 OK" | wc -l

# Failed API calls
grep "openrouter.ai" summarybot.log | grep -v "200 OK"

# Average response time (if logged)
grep "response_time" summarybot.log | awk '{sum+=$NF; count++} END {print sum/count}'
```

**Monitor Summarization Usage:**

```bash
# Summarization requests
grep "create_summary" summarybot.log | wc -l

# By user/channel (if logged)
grep "create_summary" summarybot.log | grep -o "channel=[^ ]*" | sort | uniq -c
```

## Troubleshooting

### Common Issues

**1. Port 5000 Already in Use**

```bash
# Find process using port
lsof -i:5000

# Kill process
lsof -ti:5000 | xargs kill -9

# Restart bot
./scripts/monitoring/restart-bot.sh
```

**2. Health Check Returns 503/500**

```bash
# Check bot logs
tail -50 summarybot.log

# Verify Discord token
echo $DISCORD_TOKEN | wc -c  # Should be >50

# Verify API keys
echo $OPENROUTER_API_KEY | wc -c  # Should be >10

# Restart bot
./scripts/monitoring/restart-bot.sh
```

**3. Bot Connects but Commands Don't Work**

```bash
# Check command sync
grep "Synced.*commands" summarybot.log

# Commands take up to 1 hour to propagate globally
# Check if local testing needed:
# Discord Server → Integrations → Check bot permissions
```

**4. OpenRouter API Errors**

```bash
# Check model availability
curl https://openrouter.ai/api/v1/models | jq '.data[] | select(.id | contains("claude"))'

# Verify API key
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key

# Check recent errors
grep "openrouter" summarybot.log -i | grep -i error | tail -20
```

**5. High CPU Usage**

```bash
# Check what's consuming CPU
top -p $(pgrep -f "python -m src.main")

# Profile the application (add cProfile if needed)
# Check for infinite loops in logs
grep "loop\|infinite\|stuck" summarybot.log -i

# Restart as temporary fix
./scripts/monitoring/restart-bot.sh
```

### Diagnostic Commands

```bash
# Full system status
./scripts/monitoring/health-check.sh

# Real-time monitoring
watch -n 5 ./scripts/monitoring/health-check.sh

# Start performance collection
./scripts/monitoring/performance-monitor.sh &

# Check all components
echo "=== Bot Process ===" && pgrep -fa "python -m src.main"
echo "=== Health Check ===" && curl -s http://localhost:5000/health | jq .
echo "=== Recent Logs ===" && tail -20 summarybot.log
echo "=== Error Count ===" && grep -c "ERROR" summarybot.log
```

### Getting Help

**Collect Diagnostic Information:**

```bash
# Create diagnostic bundle
mkdir -p diagnostics
./scripts/monitoring/health-check.sh > diagnostics/health.txt 2>&1
tail -500 summarybot.log > diagnostics/logs.txt
ps aux | grep python > diagnostics/processes.txt
netstat -tulpn > diagnostics/network.txt 2>&1
env | grep -E "DISCORD|LLM|OPENROUTER|CACHE" > diagnostics/env.txt
tar -czf diagnostics_$(date +%Y%m%d_%H%M%S).tar.gz diagnostics/
```

**Report Issue:**

Include in your report:
1. Diagnostic bundle
2. Steps to reproduce
3. Expected vs actual behavior
4. Recent changes or deployments
5. Frequency and severity
6. Impact on users

**Support Resources:**

- GitHub Issues: https://github.com/yourusername/summarybot-ng/issues
- Documentation: `/workspaces/summarybot-ng/docs/`
- Health Check Script: `./scripts/monitoring/health-check.sh`

---

## Monitoring Best Practices

1. **Run health checks regularly** (every 5-15 minutes)
2. **Collect performance metrics** during peak usage times
3. **Set up automated alerts** for critical issues
4. **Rotate logs** to prevent disk space issues
5. **Monitor OpenRouter API quota** to avoid rate limits
6. **Keep bot updated** with latest security patches
7. **Test monitoring scripts** after each deployment
8. **Document all incidents** for pattern analysis
9. **Review metrics weekly** to identify trends
10. **Maintain runbooks** for common scenarios

---

**Last Updated:** 2026-01-05
**Version:** 2.0.0
