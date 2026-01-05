# Summary Bot NG - Deployment Guide

Complete deployment guide for Summary Bot NG across multiple platforms.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Platforms](#cloud-platforms)
  - [Railway](#railway)
  - [Render](#render)
  - [Fly.io](#flyio)
- [CI/CD](#cicd)
- [Environment Variables](#environment-variables)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required
- Python 3.9+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- OpenRouter API Key ([OpenRouter](https://openrouter.ai/))

### Optional
- Docker & Docker Compose (for containerized deployment)
- Git (for version control)
- Cloud platform account (Railway/Render/Fly.io)

## Local Development

### 1. Clone Repository
```bash
git clone https://github.com/mrjcleaver/summarybot-ng.git
cd summarybot-ng
```

### 2. Install Dependencies
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Run Bot
```bash
# Activate virtual environment
poetry shell

# Run bot
python -m src.main
```

## Docker Deployment

### Quick Start with Docker Compose

```bash
# 1. Create .env file
cp .env.example .env

# 2. Edit .env with your secrets
nano .env

# 3. Start all services
docker-compose up -d

# 4. View logs
docker-compose logs -f bot

# 5. Stop services
docker-compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t summarybot-ng:latest .

# Run container
docker run -d \
  --name summarybot-ng \
  --env-file .env \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  summarybot-ng:latest
```

### Docker Commands

```bash
# View logs
docker logs -f summarybot-ng

# Restart container
docker restart summarybot-ng

# Stop container
docker stop summarybot-ng

# Remove container
docker rm summarybot-ng

# Build with cache clearing
docker build --no-cache -t summarybot-ng:latest .
```

## Cloud Platforms

### Railway

#### Initial Setup

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
railway login
```

2. **Create Project:**
```bash
railway init
```

3. **Configure Environment Variables:**
```bash
railway variables set DISCORD_TOKEN="your-token"
railway variables set OPENROUTER_API_KEY="your-key"
railway variables set LLM_ROUTE="openrouter"
```

4. **Deploy:**
```bash
railway up
```

#### Railway Dashboard
- Access: https://railway.app/dashboard
- Set environment variables in Settings → Variables
- Configure domains in Settings → Domains
- View logs in Deployments tab

### Render

#### Initial Setup

1. **Connect Repository:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Blueprint"
   - Connect GitHub repository
   - Select `render.yaml`

2. **Configure Environment Variables:**
   - Add in Render Dashboard under Environment
   - Or use `render.yaml` (without secrets)

3. **Deploy:**
   - Automatic deployment on git push
   - Or manual deploy from dashboard

#### Render Commands
```bash
# Trigger deployment via webhook
curl -X POST $RENDER_DEPLOY_HOOK
```

### Fly.io

#### Initial Setup

1. **Install Fly CLI:**
```bash
curl -L https://fly.io/install.sh | sh
flyctl auth login
```

2. **Create App:**
```bash
flyctl launch --no-deploy
```

3. **Set Secrets:**
```bash
flyctl secrets set DISCORD_TOKEN="your-token"
flyctl secrets set OPENROUTER_API_KEY="your-key"
```

4. **Create Volume:**
```bash
flyctl volumes create summarybot_data --size 1
```

5. **Deploy:**
```bash
flyctl deploy
```

#### Fly.io Commands
```bash
# View logs
flyctl logs

# SSH into instance
flyctl ssh console

# Scale instances
flyctl scale count 1

# View status
flyctl status

# Restart app
flyctl apps restart

# Deploy specific version
flyctl deploy --image ghcr.io/mrjcleaver/summarybot-ng:v1.0.0
```

## CI/CD

### GitHub Actions

The repository includes three workflows:

#### 1. CI - Test & Lint (`.github/workflows/ci.yml`)
- Runs on: Push to main/develop, Pull Requests
- Actions:
  - Linting (pylint)
  - Type checking (mypy)
  - Unit tests (pytest)
  - Security scanning (Trivy)

#### 2. Docker Build & Publish (`.github/workflows/docker.yml`)
- Runs on: Push to main, Tags
- Actions:
  - Multi-platform build (amd64, arm64)
  - Push to GitHub Container Registry
  - Tag with version/branch/sha

#### 3. Deploy to Production (`.github/workflows/deploy.yml`)
- Runs on: Push to main, Manual trigger
- Actions:
  - Deploy to Railway
  - Deploy to Render
  - Deploy to Fly.io
  - Send Discord notification

### Required GitHub Secrets

Configure in: Repository Settings → Secrets and variables → Actions

```
DISCORD_TOKEN              # Discord bot token
OPENROUTER_API_KEY        # OpenRouter API key
RAILWAY_TOKEN             # Railway deployment token (optional)
RENDER_DEPLOY_HOOK        # Render webhook URL (optional)
FLY_API_TOKEN             # Fly.io API token (optional)
DISCORD_WEBHOOK_DEPLOYMENTS  # Discord webhook for notifications (optional)
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | `MTkxNzQ5ODU...` |
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-v1-...` |

### Optional Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_ROUTE` | LLM provider (openrouter/anthropic) | `openrouter` |
| `OPENROUTER_MODEL` | Model to use | `anthropic/claude-3.5-sonnet` |
| `CACHE_BACKEND` | Cache backend (memory/redis) | `memory` |
| `REDIS_URL` | Redis connection URL | - |
| `WEBHOOK_ENABLED` | Enable webhook API | `true` |
| `WEBHOOK_PORT` | Webhook API port | `5000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | Database connection URL | `sqlite:///data/summarybot.db` |

## Monitoring & Logs

### Health Check
```bash
curl http://localhost:5000/health
```

Response:
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

### Logs Location

- **Local:** `summarybot.log`
- **Docker:** `docker logs -f summarybot-ng`
- **Railway:** Dashboard → Deployments → Logs
- **Render:** Dashboard → Logs tab
- **Fly.io:** `flyctl logs`

### API Documentation

Interactive API docs available at:
- Local: http://localhost:5000/docs
- Production: https://your-domain.com/docs

## Troubleshooting

### Bot Not Connecting to Discord

**Symptoms:** Bot doesn't appear online
**Causes:**
- Invalid DISCORD_TOKEN
- Missing bot intents
- Network issues

**Solutions:**
```bash
# Verify token
echo $DISCORD_TOKEN

# Check logs
docker logs summarybot-ng | grep -i error

# Verify bot permissions in Discord Developer Portal
```

### OpenRouter API Errors

**Symptoms:** 404 errors, authentication failures
**Causes:**
- Invalid API key
- Incorrect model name
- Rate limiting

**Solutions:**
```bash
# Test API key
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check model name in logs
docker logs summarybot-ng | grep "ClaudeClient:"
```

### Database Errors

**Symptoms:** SQLite errors, data not persisting
**Causes:**
- Permission issues
- Volume not mounted
- Disk full

**Solutions:**
```bash
# Check volume mounts
docker inspect summarybot-ng | grep -A 10 Mounts

# Check disk space
df -h

# Reset database
docker-compose down -v
docker-compose up -d
```

### High Memory Usage

**Symptoms:** Container OOM, slow performance
**Causes:**
- Cache size too large
- Memory leaks
- Too many concurrent requests

**Solutions:**
```bash
# Reduce cache size
export CACHE_MAX_SIZE=500

# Monitor memory
docker stats summarybot-ng

# Restart container
docker restart summarybot-ng
```

## Rollback Procedures

### Docker
```bash
# List images
docker images summarybot-ng

# Run previous version
docker run -d \
  --name summarybot-ng \
  --env-file .env \
  summarybot-ng:previous-tag
```

### Railway
```bash
# List deployments
railway logs

# Rollback to previous deployment
railway rollback
```

### Fly.io
```bash
# List releases
flyctl releases

# Rollback to specific version
flyctl releases rollback <version>
```

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use environment variables** for all sensitive data
3. **Enable 2FA** on all platform accounts
4. **Rotate API keys** regularly
5. **Monitor access logs** for suspicious activity
6. **Keep dependencies updated** with `poetry update`
7. **Run security scans** before deployment

## Support

- **Issues:** https://github.com/mrjcleaver/summarybot-ng/issues
- **Documentation:** https://github.com/mrjcleaver/summarybot-ng/docs
- **API Docs:** http://localhost:5000/docs

---

**Last Updated:** 2026-01-05
**Version:** 1.0.0
