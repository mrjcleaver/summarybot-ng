# Configuration Guide

This guide covers all configuration options for Summary Bot NG, including environment variables, YAML configuration files, and runtime settings.

## 📁 Configuration Files Overview

Summary Bot NG uses a layered configuration approach:
- **Environment Variables**: Core settings and secrets
- **YAML Files**: Complex configurations and templates  
- **Database Settings**: User preferences and server-specific options
- **Runtime Parameters**: Command-line and API overrides

---

## 🔐 Environment Variables

### Required Variables

#### Discord Configuration
```env
# Discord Bot Token (Required)
DISCORD_BOT_TOKEN=your_bot_token_here

# Guild/Server ID (Optional - for guild-specific commands)
DISCORD_GUILD_ID=your_server_id

# Bot Application ID (Optional - auto-detected)
DISCORD_APPLICATION_ID=your_application_id
```

#### AI Provider Configuration

**Development vs Production:**
- **Development**: Use Claude Direct (Anthropic API)
- **Production/Runtime**: Use OpenRouter (Proxy)

##### Claude Direct (Development)
```env
# Use direct Anthropic API for development
LLM_ROUTE=anthropic
CLAUDE_API_KEY=sk-ant-your_api_key_here
```

##### OpenRouter (Production)
```env
# Use OpenRouter proxy for production
LLM_ROUTE=openrouter
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_api_key_here
OPENROUTER_MODEL=anthropic/claude-3-sonnet-20240229

# Optional: Claude key for fallback
CLAUDE_API_KEY=sk-ant-bypass-for-openrouter
```

**Auto-Detection**: If `LLM_ROUTE` is not set, the system automatically detects the environment:
- Development environments → Claude Direct
- Production environments (Railway, Render, Heroku, etc.) → OpenRouter

### Optional Variables

#### Bot Behavior
```env
# Command Prefix
BOT_PREFIX=/

# Default Summary Length
SUMMARY_MAX_LENGTH=2000

# Maximum Messages to Process
MAX_MESSAGE_COUNT=500

# Enable Debug Mode
DEBUG=false

# Log Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

#### API & Webhook Settings
```env
# Webhook Server Port
WEBHOOK_PORT=5000

# Webhook Base URL
WEBHOOK_BASE_URL=https://your-domain.com

# Webhook Secret for Signature Verification
WEBHOOK_SECRET=your_webhook_secret

# API Rate Limit (requests per hour)
API_RATE_LIMIT=100

# Enable API Authentication
API_AUTH_REQUIRED=true

# API Key for External Access
API_KEY=your_api_key
```

#### Database Configuration
```env
# Database URL (SQLite default)
DATABASE_URL=sqlite:///data/summarybot.db

# Alternative: PostgreSQL
# DATABASE_URL=postgresql://user:pass@host:port/dbname

# Connection Pool Size
DB_POOL_SIZE=10

# Connection Timeout (seconds)
DB_TIMEOUT=30
```

#### External Integrations
```env
# Confluence Integration
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_EMAIL=user@company.com
CONFLUENCE_API_TOKEN=your_confluence_token

# Notion Integration
NOTION_API_KEY=secret_notion_key
NOTION_DATABASE_ID=your_database_id

# GitHub Integration
GITHUB_TOKEN=your_github_token
GITHUB_REPO=owner/repository

# Slack Integration (Future)
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_SIGNING_SECRET=your_signing_secret
```

---

## 📝 YAML Configuration Files

### config/bot.yaml
Main bot configuration file:

```yaml
# Discord Bot Settings
discord:
  intents:
    - message_content      # Required for reading message content
    - guild_messages      # Required for accessing guild messages
    - guilds             # Required for guild information
    - dm_messages        # Optional: for direct message support
  
  commands:
    sync_on_startup: true    # Sync slash commands on bot start
    global_commands: false   # Use guild-specific commands (faster updates)
    delete_missing: true     # Remove old commands not in code
  
  presence:
    status: "online"         # online, idle, dnd, invisible
    activity:
      type: "watching"       # playing, streaming, listening, watching
      name: "for /summarize"
  
  permissions:
    default_role: null       # Default role required (null = no requirement)
    admin_roles:            # Roles with admin access
      - "Admin"
      - "Moderator"
    user_roles:             # Roles that can use summaries
      - "@everyone"

# Summarization Settings
summarization:
  default_template: "default"
  max_length: 2000
  max_messages: 500
  include_links: true
  preserve_formatting: true
  
  filters:
    exclude_bots: true
    min_message_length: 5
    exclude_commands: true
    exclude_mentions_only: true
  
  processing:
    timeout_seconds: 120
    retry_attempts: 3
    batch_size: 50

# API Server Settings
api:
  enabled: true
  host: "0.0.0.0"
  port: 5000
  cors_origins:
    - "http://localhost:3000"
    - "https://your-frontend.com"
  
  rate_limiting:
    enabled: true
    requests_per_minute: 10
    burst_limit: 5
  
  authentication:
    required: true
    api_key_header: "Authorization"
    api_key_prefix: "Bearer "

# Webhook Configuration
webhooks:
  enabled: true
  timeout: 30
  retry_attempts: 3
  
  endpoints:
    - name: "confluence"
      url: "${CONFLUENCE_WEBHOOK_URL}"
      secret: "${CONFLUENCE_WEBHOOK_SECRET}"
      events: ["summary.created", "summary.updated"]
    
    - name: "notion"
      url: "${NOTION_WEBHOOK_URL}"
      secret: "${NOTION_WEBHOOK_SECRET}"
      events: ["summary.created"]

# Logging Configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  handlers:
    console:
      enabled: true
      level: "INFO"
    
    file:
      enabled: true
      level: "DEBUG"
      filename: "logs/summarybot.log"
      max_bytes: 10485760  # 10MB
      backup_count: 5
    
    error_file:
      enabled: true
      level: "ERROR" 
      filename: "logs/error.log"

# Performance Settings
performance:
  cache:
    enabled: true
    ttl_seconds: 3600
    max_entries: 1000
  
  async:
    max_workers: 4
    task_timeout: 300
  
  memory:
    max_message_cache: 10000
    cleanup_interval: 3600
```

### config/prompts.yaml
Custom prompt templates:

```yaml
# Default prompt template
default: |
  Summarize the following Discord conversation into a structured, professional format:
  
  Requirements:
  - Use H2 headers (##) for main topics
  - Use nested bullet points for supporting details
  - Preserve important message links: {links}
  - Focus on actionable items and key decisions
  - Maintain chronological flow where relevant
  - Exclude off-topic conversations and casual chat
  
  Conversation:
  {messages}

# Technical discussion prompt
technical: |
  Create a technical summary of this Discord conversation:
  
  Focus on:
  - Code changes and technical decisions
  - Architecture discussions and proposals
  - Bug reports, issues, and their resolutions
  - Performance considerations and optimizations
  - API changes and breaking changes
  - Testing strategies and results
  
  Format:
  ## Technical Summary
  ### Key Decisions
  - Decision points and rationale
  
  ### Code Changes
  - Implementation details and impacts
  
  ### Issues & Resolutions
  - Problems identified and solutions implemented
  
  ### Action Items
  - Next steps and assignments
  
  Links: {links}
  Messages: {messages}

# Meeting-style prompt
meeting: |
  Generate a professional meeting summary from this Discord conversation:
  
  ## Meeting Summary - {channel_name}
  **Date:** {date}
  **Participants:** {participants}
  
  ### Agenda Items Discussed
  - [List main topics covered]
  
  ### Key Decisions Made
  - [Important decisions and their context]
  
  ### Action Items
  - [ ] [Action item] - Assigned to [Person] - Due: [Date]
  
  ### Next Steps
  - [Follow-up items and future plans]
  
  ### Resources & Links
  {links}
  
  **Messages Processed:** {message_count}
  **Conversation:** {messages}

# Brief/executive summary prompt  
brief: |
  Create a concise executive summary (max 500 words):
  
  ## Executive Summary
  
  **Key Points:**
  - [Most important outcomes]
  - [Critical decisions made]
  - [Urgent action items]
  
  **Impact:** [Brief impact assessment]
  
  **Next Steps:** [Immediate priorities]
  
  Source: {channel_name} | Messages: {message_count} | Links: {links}
  
  {messages}

# Research/analysis prompt
research: |
  Analyze this conversation for research insights:
  
  ## Research Summary
  
  ### Key Findings
  - [Important discoveries or insights]
  
  ### Methodologies Discussed
  - [Approaches, tools, techniques mentioned]
  
  ### Data & Evidence
  - [Statistics, examples, case studies referenced]
  
  ### Conclusions & Implications
  - [What this means for the project/research]
  
  ### Open Questions
  - [Unresolved issues requiring further investigation]
  
  ### References
  {links}
  
  **Source Material:** {messages}
```

### config/integrations.yaml
External platform configurations:

```yaml
# Confluence Integration
confluence:
  enabled: false
  base_url: "${CONFLUENCE_URL}"
  email: "${CONFLUENCE_EMAIL}"
  api_token: "${CONFLUENCE_API_TOKEN}"
  
  space_key: "TEAM"
  parent_page_id: "123456789"
  
  template:
    title_format: "Discord Summary - {channel_name} - {date}"
    labels: ["discord", "summary", "automated"]
    
  auto_publish:
    enabled: false
    channels: ["#important", "#announcements"]

# Notion Integration  
notion:
  enabled: false
  api_key: "${NOTION_API_KEY}"
  database_id: "${NOTION_DATABASE_ID}"
  
  properties:
    title: "Name"
    channel: "Channel" 
    date: "Date"
    summary: "Summary"
    tags: "Tags"
  
  auto_create:
    enabled: false
    channels: ["#planning", "#decisions"]

# GitHub Wiki Integration
github:
  enabled: false
  token: "${GITHUB_TOKEN}"
  repository: "${GITHUB_REPO}"
  
  wiki:
    enabled: true
    page_format: "Discord-Summary-{date}"
    sidebar_update: true
  
  issues:
    create_from_summary: false
    labels: ["documentation", "discord-summary"]

# Slack Integration (Future)
slack:
  enabled: false
  bot_token: "${SLACK_BOT_TOKEN}"
  signing_secret: "${SLACK_SIGNING_SECRET}"
  
  cross_post:
    enabled: false
    channel_mapping:
      "#general": "C1234567890"  # Discord to Slack channel mapping
```

---

## 🗄️ Database Configuration

### SQLite (Default)
```env
DATABASE_URL=sqlite:///data/summarybot.db
```

### PostgreSQL (Production)
```env
DATABASE_URL=postgresql://username:password@hostname:port/database_name

# Connection pool settings
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Database Schema
The bot automatically creates these tables:
- `summaries` - Generated summaries and metadata
- `channels` - Channel configurations and preferences
- `users` - User preferences and permissions
- `webhooks` - Webhook delivery logs
- `api_keys` - API authentication tokens

---

## ⚙️ Runtime Configuration

### Command Line Arguments
```bash
# Start with custom config file
python src/main.py --config /path/to/config.yaml

# Override log level
python src/main.py --log-level DEBUG

# Disable webhooks
python src/main.py --no-webhooks

# Run in development mode
python src/main.py --dev

# Custom port for API server
python src/main.py --port 8080
```

### Environment-Specific Configs
```bash
# Development
export CONFIG_ENV=development
python src/main.py  # Loads config/development.yaml

# Production
export CONFIG_ENV=production
python src/main.py  # Loads config/production.yaml

# Testing
export CONFIG_ENV=testing
python src/main.py  # Loads config/testing.yaml
```

---

## 🔧 Advanced Configuration

### Custom Message Filters
```yaml
# config/filters.yaml
message_filters:
  - name: "exclude_short"
    type: "length"
    min_length: 10
    
  - name: "exclude_bots" 
    type: "author"
    exclude_bots: true
    
  - name: "include_roles"
    type: "role"
    required_roles: ["Member", "VIP"]
    
  - name: "time_range"
    type: "temporal"
    max_age_hours: 24
    
  - name: "content_filter"
    type: "regex"
    pattern: "^(?!\\+\\+|--|!|\\?).*"  # Exclude reactions and commands
```

### Custom Output Formats
```yaml
# config/formats.yaml
output_formats:
  markdown:
    extension: ".md"
    template: "markdown_template.j2"
    
  html:
    extension: ".html" 
    template: "html_template.j2"
    css_file: "styles.css"
    
  json:
    extension: ".json"
    include_metadata: true
    pretty_print: true
    
  plain:
    extension: ".txt"
    strip_formatting: true
```

### Performance Tuning
```yaml
# config/performance.yaml
performance:
  openai:
    request_timeout: 60
    max_retries: 3
    backoff_factor: 2
    
  discord:
    message_cache_size: 10000
    rate_limit_buffer: 0.1
    
  processing:
    max_concurrent_summaries: 3
    chunk_size: 50
    memory_limit_mb: 512
```

---

## 📊 Monitoring Configuration

### Metrics Collection
```yaml
# config/monitoring.yaml
metrics:
  enabled: true
  endpoint: "/metrics"
  
  collectors:
    - summaries_generated
    - api_requests_total
    - discord_events_processed
    - openai_tokens_used
    - webhook_deliveries

# Prometheus configuration
prometheus:
  enabled: false
  push_gateway: "http://prometheus:9091"
  job_name: "summarybot-ng"
  
# Health checks
health_checks:
  discord_connection: 30  # seconds
  openai_api: 60
  database: 10
  webhook_endpoints: 120
```

---

## 🛡️ Security Configuration

### API Security
```yaml
security:
  api_keys:
    length: 32
    prefix: "sk-summarybot-"
    expiration_days: 90
    
  rate_limiting:
    window_minutes: 60
    max_requests: 100
    block_duration_minutes: 10
    
  cors:
    enabled: true
    origins: ["https://yourdomain.com"]
    methods: ["GET", "POST", "PUT", "DELETE"]
    headers: ["Authorization", "Content-Type"]

# Webhook security
webhook_security:
  signature_validation: true
  timestamp_tolerance: 300  # 5 minutes
  require_https: true
  
  ip_whitelist:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
```

---

## 🔄 Configuration Validation

### Validation Script
```bash
# Validate configuration
python scripts/validate_config.py

# Test integrations
python scripts/test_integrations.py

# Check permissions
python scripts/check_permissions.py
```

### Configuration Schema
The bot validates all configuration files against JSON schemas located in `schemas/`:
- `schemas/bot.json` - Main bot configuration
- `schemas/prompts.json` - Prompt templates
- `schemas/integrations.json` - External integrations

---

## 📋 Configuration Best Practices

### Security
1. **Never commit secrets**: Use environment variables for API keys
2. **Rotate API keys**: Regularly update authentication tokens
3. **Restrict permissions**: Grant minimum required Discord permissions
4. **Enable authentication**: Require API keys for external access
5. **Use HTTPS**: Always use secure connections in production

### Performance
1. **Optimize cache settings**: Balance memory usage with performance
2. **Configure rate limits**: Prevent API quota exhaustion
3. **Monitor resource usage**: Set appropriate limits for processing
4. **Use database indexes**: Ensure fast query performance
5. **Enable compression**: Reduce network overhead

### Maintenance
1. **Use version control**: Track configuration changes
2. **Document customizations**: Comment complex configurations
3. **Test configurations**: Validate before deploying
4. **Monitor logs**: Watch for configuration warnings
5. **Regular backups**: Backup configuration and data files

---

## 🆘 Configuration Troubleshooting

### Common Issues

#### Environment Variables Not Loading
```bash
# Check if variables are set
env | grep DISCORD
env | grep OPENAI

# Source environment file
source .env

# Check file permissions
ls -la .env
```

#### YAML Parsing Errors
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/bot.yaml'))"

# Check indentation (YAML is sensitive to spaces)
cat -A config/bot.yaml
```

#### Database Connection Issues
```bash
# Test database connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('${DATABASE_URL}')
print('Connection successful!')
"
```

#### Permission Problems
```bash
# Check file permissions
ls -la config/
ls -la logs/

# Fix permissions
chmod 755 config/
chmod 644 config/*.yaml
chmod 755 logs/
```

For additional troubleshooting help, see the [Troubleshooting Guide](troubleshooting.md).