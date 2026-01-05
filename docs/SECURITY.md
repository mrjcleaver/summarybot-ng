# Security & Secrets Management

## Overview

This document outlines security best practices and secrets management for Summary Bot NG.

## Secrets Management

### Environment Variables (Development)

**Never commit `.env` files!**

```bash
# ✅ GOOD - Use .env for local development
cp .env.example .env
# Edit .env with your secrets
# .env is in .gitignore

# ❌ BAD - Never commit secrets
git add .env  # DON'T DO THIS
```

### Secrets in CI/CD

#### GitHub Secrets

Store secrets in: Repository Settings → Secrets and variables → Actions

Required secrets:
```
DISCORD_TOKEN
OPENROUTER_API_KEY
```

Optional secrets:
```
RAILWAY_TOKEN
RENDER_DEPLOY_HOOK
FLY_API_TOKEN
DISCORD_WEBHOOK_DEPLOYMENTS
```

#### Accessing in Workflows

```yaml
env:
  DISCORD_TOKEN: ${{ secrets.DISCORD_TOKEN }}
  OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

### Cloud Platform Secrets

#### Railway
```bash
# Set secret
railway variables set DISCORD_TOKEN="your-token"

# View variables (values hidden)
railway variables

# Delete variable
railway variables delete DISCORD_TOKEN
```

#### Render
- Go to Dashboard → Service → Environment
- Add variables (marked as secret)
- Secrets are encrypted at rest

#### Fly.io
```bash
# Set secret
flyctl secrets set DISCORD_TOKEN="your-token"

# List secrets (values hidden)
flyctl secrets list

# Remove secret
flyctl secrets unset DISCORD_TOKEN
```

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in environment variables
- [ ] No hardcoded credentials in code
- [ ] `.env` files in `.gitignore`
- [ ] `.env.example` has placeholder values only
- [ ] Dependencies updated (`poetry update`)
- [ ] Security scan passed (`trivy`)
- [ ] HTTPS enabled for webhook API
- [ ] Rate limiting configured
- [ ] Input validation implemented

### Production

- [ ] 2FA enabled on all accounts
- [ ] Bot token rotated from development
- [ ] API keys have appropriate scopes
- [ ] CORS configured correctly
- [ ] Logs don't contain secrets
- [ ] Error messages don't expose internals
- [ ] Database access restricted
- [ ] Monitoring and alerting configured

### Post-Deployment

- [ ] Monitor access logs
- [ ] Set up security alerts
- [ ] Regular dependency updates
- [ ] Quarterly security audit
- [ ] Incident response plan documented

## Discord Bot Permissions

### Required Intents

```python
intents = discord.Intents.default()
intents.message_content = True  # Required for message summarization
intents.guilds = True
intents.guild_messages = True
```

### OAuth2 Scopes

Minimum required:
- `bot`
- `applications.commands`

### Bot Permissions

Minimum required (integer: `274877975552`):
- Read Messages/View Channels
- Send Messages
- Embed Links
- Read Message History
- Use Slash Commands

### Adding Bot to Server

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=274877975552&scope=bot%20applications.commands
```

## API Security

### Webhook Authentication

The webhook API supports two authentication methods:

#### 1. API Key Header

```bash
curl -X POST http://localhost:5000/api/v1/summarize \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "123"}'
```

#### 2. Bearer Token

```bash
curl -X POST http://localhost:5000/api/v1/summarize \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "123"}'
```

### Generating API Keys

```bash
# Generate random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to environment
export WEBHOOK_API_KEY="generated-key"
```

### Rate Limiting

Default: 100 requests per minute per IP

Configure in `.env`:
```bash
WEBHOOK_RATE_LIMIT=100
```

### CORS Configuration

Restrict webhook API access:

```bash
# Allow specific origins
WEBHOOK_CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Allow all (development only)
WEBHOOK_CORS_ORIGINS=*
```

## Data Privacy

### Message Storage

- Messages are processed in-memory
- Summaries stored in SQLite database
- No message content persisted by default
- Configurable retention policy

### PII Handling

- No automatic PII extraction
- User IDs stored as Discord IDs
- No email/phone collection
- GDPR compliant data deletion

### Data Encryption

- Secrets encrypted in cloud platforms
- HTTPS for all API communications
- Database encryption at rest (cloud provider)

## Vulnerability Management

### Dependency Scanning

Automated via GitHub Actions:
```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
```

Manual scan:
```bash
# Install trivy
brew install aquasecurity/trivy/trivy

# Scan project
trivy fs .

# Scan Docker image
trivy image summarybot-ng:latest
```

### Updating Dependencies

```bash
# Check for outdated packages
poetry show --outdated

# Update all dependencies
poetry update

# Update specific package
poetry update discord.py

# Rebuild lock file
poetry lock --no-update
```

### Security Advisories

Monitor:
- GitHub Dependabot alerts
- PyPI security advisories
- Discord.py security announcements
- OpenRouter status updates

## Incident Response

### Security Incident Procedure

1. **Detect:** Monitor logs and alerts
2. **Contain:** Disable affected services
3. **Investigate:** Analyze logs and traces
4. **Remediate:** Patch vulnerabilities
5. **Recover:** Restore services
6. **Learn:** Document and improve

### Emergency Contacts

- **Repository Owner:** @mrjcleaver
- **Security Email:** security@example.com
- **Discord Support:** https://discord.gg/your-server

### Rollback Procedure

See [DEPLOYMENT.md](./DEPLOYMENT.md#rollback-procedures)

## Compliance

### Data Retention

- Summaries: 30 days (configurable)
- Logs: 7 days (rotated)
- Metrics: 90 days
- Audit logs: 1 year

### Right to Deletion

Users can request data deletion:
1. Contact bot administrator
2. Provide Discord user ID
3. Data purged within 72 hours

### Terms of Service

- Bot must comply with Discord ToS
- Users must consent to message processing
- Clear privacy policy required
- Data processing agreement for EU users

## Security Resources

- **Discord Developer Terms:** https://discord.com/developers/docs/policies-and-agreements/terms-of-service
- **OpenRouter Security:** https://openrouter.ai/docs/security
- **Python Security:** https://python.org/dev/security
- **Docker Security:** https://docs.docker.com/engine/security

## Reporting Vulnerabilities

Please report security vulnerabilities to:
- **Email:** security@example.com
- **GitHub:** Security tab → Report a vulnerability
- **Response time:** Within 48 hours

**Do not** disclose vulnerabilities publicly until patched.

---

**Last Updated:** 2026-01-05
**Version:** 1.0.0
