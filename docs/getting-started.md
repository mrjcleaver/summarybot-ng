# Getting Started with Summary Bot NG

This guide will walk you through setting up Summary Bot NG from installation to your first summary.

## 📋 Prerequisites

Before installing Summary Bot NG, ensure you have:

### Required Software
- **Python 3.8+**: Check with `python --version`
- **Poetry**: Python dependency management tool
- **Git**: For cloning the repository

### Required Accounts & Keys
- **Discord Developer Account**: For creating the bot application
- **Anthropic Account**: For Claude API access (development)
- **OpenRouter Account**: For Claude API access via OpenRouter (production)

### System Requirements
- **Memory**: Minimum 512MB RAM
- **Storage**: 100MB free space
- **Network**: Internet connection for API calls

## 🔧 Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd summarybot-ng
```

### Step 2: Install Poetry (if not already installed)
```bash
# On macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# On Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Verify installation
poetry --version
```

### Step 3: Install Dependencies
```bash
# Install all dependencies
poetry install

# Verify installation
poetry show
```

## 🔑 Configuration

### Step 1: Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit the environment file
nano .env  # or your preferred editor
```

### Step 2: Required Environment Variables
```env
# Discord Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_server_id_here

# AI Configuration (Choose one based on environment)
# Production (recommended): OpenRouter
LLM_ROUTE=openrouter
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here
OPENROUTER_MODEL=anthropic/claude-3-sonnet-20240229

# Development: Direct Claude API
# LLM_ROUTE=anthropic
# CLAUDE_API_KEY=sk-ant-your_claude_key_here

# Bot Configuration
BOT_PREFIX=/
SUMMARY_MAX_LENGTH=2000
WEBHOOK_PORT=5000

# Optional: Webhook Configuration
WEBHOOK_URL=https://your-webhook-endpoint.com
WEBHOOK_SECRET=your_webhook_secret
```

### Step 3: Discord Bot Setup

#### Create Discord Application
1. Visit https://discord.com/developers/applications
2. Click "New Application"
3. Enter application name: "Summary Bot NG"
4. Go to the "Bot" section
5. Click "Add Bot"
6. Copy the token and add it to your `.env` file

#### Set Bot Permissions
Required permissions:
- `Send Messages` (2048)
- `Read Message History` (65536)
- `Use Slash Commands` (2147483648)

Permission integer: `2147551296`

#### Invite Bot to Server
1. Go to "OAuth2" > "URL Generator"
2. Select scopes: `bot` and `applications.commands`
3. Select permissions listed above
4. Copy the generated URL and visit it
5. Select your server and authorize

### Step 4: AI API Setup

#### Option A: OpenRouter (Recommended for Production)
1. Visit https://openrouter.ai
2. Create account or log in
3. Go to API Keys section
4. Create new API key
5. Copy key to `.env` file as `OPENROUTER_API_KEY`
6. Set `LLM_ROUTE=openrouter` in `.env`
7. Ensure you have sufficient credits

#### Option B: Direct Claude API (Development)
1. Visit https://console.anthropic.com
2. Create account or log in
3. Go to API Keys section
4. Create new API key
5. Copy key to `.env` file as `CLAUDE_API_KEY`
6. Set `LLM_ROUTE=anthropic` in `.env`

## 🚀 Running the Bot

### Development Mode
```bash
# Run with Poetry
poetry run python src/main.py

# Or activate virtual environment first
poetry shell
python src/main.py
```

### Production Mode
```bash
# Using systemd (Linux)
sudo systemctl start summarybot-ng

# Using Docker
docker-compose up -d

# Using PM2 (Node.js process manager)
pm2 start ecosystem.config.js
```

## 🧪 Testing the Installation

### Test Discord Connection
1. Check bot appears online in your Discord server
2. Bot should show as "Summary Bot NG" with online status
3. Look for successful connection logs in console

### Test Basic Functionality
```bash
# In Discord, try these commands:
/summarize
/summarize channel:#general
/summarize last:10
```

### Test Webhook Endpoint (Optional)
```bash
# Test webhook server
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "message"}'
```

## 🎯 First Summary

### Using Slash Commands
```bash
# Basic summary of recent messages
/summarize

# Summarize specific channel
/summarize channel:#development

# Summarize last N messages
/summarize last:50

# Summarize with custom prompt
/summarize prompt:"Focus on technical decisions"
```

### Using Webhook API
```bash
# POST to webhook endpoint
curl -X POST http://localhost:5000/summary \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "123456789",
    "message_count": 25,
    "prompt_template": "default"
  }'
```

## 📊 Monitoring & Logs

### Log Locations
- **Application Logs**: `logs/summarybot.log`
- **Error Logs**: `logs/error.log`
- **API Logs**: `logs/api.log`

### Log Levels
```bash
# Set log level in .env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Health Checks
```bash
# Check bot status
curl http://localhost:5000/health

# Check API status
curl http://localhost:5000/api/status
```

## 🔧 Configuration Files

### config/bot.yaml
```yaml
discord:
  intents:
    - message_content
    - guild_messages
    - guilds
  
  commands:
    sync_on_startup: true
    global_commands: false

summarization:
  default_length: 2000
  max_messages: 100
  include_links: true
  
webhook:
  enabled: true
  port: 5000
  timeout: 30
```

### config/prompts.yaml
```yaml
default: |
  Summarize the following Discord conversation into a structured format with:
  - H2 headers for main topics
  - Nested bullet points for details
  - Preserve important message links
  - Focus on actionable items and decisions

technical: |
  Create a technical summary focusing on:
  - Code changes and decisions
  - Architecture discussions
  - Bug reports and solutions
  - Performance considerations

meeting: |
  Generate a meeting-style summary with:
  - Agenda items discussed
  - Decisions made
  - Action items assigned
  - Next steps identified
```

## 🛠️ Troubleshooting

### Common Issues

#### Bot Not Responding
```bash
# Check bot token
echo $DISCORD_BOT_TOKEN

# Verify bot permissions
# Ensure bot has required permissions in Discord server

# Check logs
tail -f logs/summarybot.log
```

#### AI API Errors
```bash
# For OpenRouter
echo $OPENROUTER_API_KEY
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# For Claude Direct
echo $CLAUDE_API_KEY
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $CLAUDE_API_KEY" \
  -H "anthropic-version: 2023-06-01"

# Check usage/limits at respective platform dashboards
```

#### Permission Errors
```bash
# Check file permissions
ls -la .env
chmod 600 .env

# Check directory permissions
ls -la logs/
chmod 755 logs/
```

### Getting Help

1. **Check Logs**: Always start by examining the log files
2. **Verify Configuration**: Ensure all environment variables are set
3. **Test API Keys**: Verify Discord and OpenAI API keys work
4. **Check Permissions**: Ensure bot has necessary Discord permissions
5. **Consult Documentation**: See [Troubleshooting Guide](troubleshooting.md)

## 🎉 Next Steps

Now that your bot is running:

1. **Configure Channels**: Set up channel-specific settings
2. **Customize Prompts**: Create custom summary templates
3. **Set Up Webhooks**: Configure external integrations
4. **Monitor Usage**: Track API usage and bot performance
5. **Explore Advanced Features**: Check out the [Examples](examples.md)

For detailed configuration options, see the [Configuration Guide](configuration.md).