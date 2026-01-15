# External Prompt Hosting - Administrator Reference

Version: 1.0.0
Last Updated: 2026-01-14
Target Audience: Discord Server Administrators, Technical Users

---

## Table of Contents

1. [Command Reference](#command-reference)
2. [Configuration Options](#configuration-options)
3. [Security Considerations](#security-considerations)
4. [Performance Optimization](#performance-optimization)
5. [Monitoring and Diagnostics](#monitoring-and-diagnostics)
6. [Advanced Configuration](#advanced-configuration)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## Command Reference

All external prompt commands require Administrator permissions or a custom Bot Manager role.

### `/prompt-config set`

Configure external prompt repository for your server.

**Syntax:**
```
/prompt-config set <repository_url> [branch]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repository_url` | string | Yes | GitHub repository URL |
| `branch` | string | No | Git branch (default: `main`) |

**Examples:**
```
/prompt-config set https://github.com/myorg/prompts

/prompt-config set https://github.com/myorg/prompts development

/prompt-config set https://github.com/myorg/prompts feature/new-prompts
```

**Behavior:**
1. Validates repository URL format
2. Tests GitHub connectivity
3. Fetches and validates `schema-version` file
4. Fetches and validates `PATH` file
5. Validates at least one prompt file exists
6. Saves configuration to database
7. Clears existing cache for guild
8. Returns detailed status message

**Response (Success):**
```
✅ Repository configured successfully!

Repository: https://github.com/myorg/prompts
Branch: main
Schema Version: v1
Status: All checks passed

Found:
- system/brief.md
- system/detailed.md
- system/comprehensive.md

Your server will now use custom prompts for summaries.
Cache refreshes automatically every 15 minutes.

Use /prompt-config test to run full diagnostics.
```

**Response (Failure):**
```
❌ Configuration failed

Error: Repository not found
URL: https://github.com/myorg/invalid-repo

Possible causes:
- Repository doesn't exist
- Repository is private (requires GitHub token)
- URL contains typo

Fix:
1. Verify repository exists on GitHub
2. Check URL is correct: https://github.com/owner/repo
3. For private repos, contact bot administrator for token setup

Use /prompt-config test for detailed diagnostics.
```

**Permissions:**
- Requires `ADMINISTRATOR` permission OR
- Requires custom Bot Manager role (configured per server)

**Rate Limits:**
- Maximum 5 configuration changes per hour per server
- Prevents rapid toggling that could cause GitHub rate limits

---

### `/prompt-config status`

View current configuration and statistics.

**Syntax:**
```
/prompt-config status
```

**Parameters:** None

**Example:**
```
/prompt-config status
```

**Response:**
```
📊 External Prompt Configuration Status

Repository: https://github.com/myorg/prompts
Branch: main
Schema Version: v1
Enabled: Yes

Last Fetch:
- Time: 2026-01-14 10:45:32 UTC (12 minutes ago)
- Status: Success
- Duration: 847ms
- Files Fetched: 6

Cache Statistics:
- Cached Prompts: 6 files
- Total Size: 28.4 KB
- Hit Rate: 87.3% (last hour)
- Next Refresh: in 3 minutes

Health:
- Total Fetches: 142
- Success Rate: 99.3%
- Average Latency: 654ms
- Errors (24h): 1

Recent Errors: None

Last Updated: 2026-01-14 10:45:32 UTC
```

**Permission:** Any user can view status (read-only)

---

### `/prompt-config remove`

Remove external prompt configuration and return to default prompts.

**Syntax:**
```
/prompt-config remove
```

**Parameters:** None

**Example:**
```
/prompt-config remove
```

**Behavior:**
1. Shows confirmation prompt
2. On confirmation:
   - Removes configuration from database
   - Clears all cached prompts for guild
   - Logs configuration removal
3. Server immediately reverts to default prompts

**Response:**
```
⚠️ Remove External Prompt Configuration?

This will:
- Remove repository configuration
- Clear all cached prompts
- Revert to default bot prompts

This action cannot be undone.

[Confirm] [Cancel]
```

**After confirmation:**
```
✅ Configuration Removed

Your server is now using default bot prompts.
All cached custom prompts have been cleared.

To reconfigure later, use:
/prompt-config set <repository_url>
```

**Permissions:** Requires `ADMINISTRATOR` permission

---

### `/prompt-config refresh`

Force immediate cache refresh from repository.

**Syntax:**
```
/prompt-config refresh
```

**Parameters:** None

**Example:**
```
/prompt-config refresh
```

**Behavior:**
1. Clears all cached prompts for guild
2. Immediately fetches fresh prompts from GitHub
3. Validates and caches new prompts
4. Returns fetch statistics

**Response:**
```
🔄 Cache Refresh Started...

Fetching from: https://github.com/myorg/prompts
Branch: main

✅ Refresh Complete

Fetched Files: 6
Duration: 1,234ms
Cache Cleared: 6 old entries
Cache Populated: 6 new entries

Status: All prompts updated successfully
Next auto-refresh: in 15 minutes
```

**Use Cases:**
- You just pushed changes to your repository
- Want to test new prompts immediately
- Cached prompts seem outdated
- Troubleshooting configuration issues

**Rate Limits:**
- Maximum 10 manual refreshes per hour per server
- Prevents GitHub API abuse

**Permissions:** Requires `ADMINISTRATOR` permission

---

### `/prompt-config test`

Run comprehensive diagnostics on repository configuration.

**Syntax:**
```
/prompt-config test
```

**Parameters:** None

**Example:**
```
/prompt-config test
```

**Behavior:**
Performs complete validation:
1. Repository accessibility test
2. Schema version validation
3. PATH file syntax validation
4. Prompt file existence checks
5. Content validation (security scan)
6. Template variable validation
7. Pattern matching tests

**Response (All Tests Pass):**
```
🧪 Repository Diagnostics

Testing: https://github.com/myorg/prompts
Branch: main

✅ Repository Accessible
   Response time: 342ms
   Status: 200 OK

✅ Schema Version
   Version: v1
   Status: Supported

✅ PATH File
   File: Found (1.2 KB)
   Patterns: 8 valid, 0 errors
   Syntax: Valid

✅ Required Files
   system/brief.md: Found (4.3 KB)
   system/detailed.md: Found (6.8 KB)
   system/comprehensive.md: Found (9.1 KB)

✅ Content Validation
   All files pass security checks
   No suspicious patterns detected
   Encoding: UTF-8

✅ Template Variables
   All variables valid
   No undefined parameters

Overall: Configuration is healthy ✅
Your prompts are working correctly.
```

**Response (With Issues):**
```
🧪 Repository Diagnostics

Testing: https://github.com/myorg/prompts
Branch: main

✅ Repository Accessible
   Response time: 423ms

❌ Schema Version
   Error: Unsupported version 'v3'
   Fix: Change schema-version file to 'v1'

⚠️ PATH File
   File: Found (2.1 KB)
   Patterns: 6 valid, 2 errors
   Line 5: Invalid template parameter {custom}
   Line 8: Path traversal detected '../system'
   Fix: Review PATH file syntax

✅ Required Files
   system/brief.md: Found
   system/detailed.md: Missing ❌
   Fix: Create missing file

⚠️ Content Validation
   system/brief.md: Warning - Very short (45 chars)
   Recommendation: Add more detailed instructions

Overall: 2 errors, 2 warnings ⚠️
Configuration needs fixes before use.
```

**Permissions:** Any user can run diagnostics (helpful for troubleshooting)

---

### `/prompt-cache stats`

View detailed cache performance statistics.

**Syntax:**
```
/prompt-cache stats [period]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | No | Time period: `1h`, `24h`, `7d` (default: `1h`) |

**Examples:**
```
/prompt-cache stats

/prompt-cache stats 24h

/prompt-cache stats 7d
```

**Response:**
```
📈 Cache Performance Statistics (Last 24 Hours)

Cache Hits:
- Memory: 1,234 (85.2%)
- Redis: 156 (10.8%)
- Database: 42 (2.9%)
- Total: 1,432 (98.9% hit rate)

Cache Misses:
- Total: 16 (1.1%)
- Resulted in GitHub fetches: 16

Cache Contents:
- Stored Prompts: 6 files
- Total Size: 28.4 KB
- Oldest Entry: 14 minutes ago
- Newest Entry: 2 minutes ago

Performance:
- Avg Hit Latency: 2.3ms
- Avg Miss Latency: 847ms
- Cache Efficiency: 99.4%

GitHub API Usage:
- Requests (24h): 16
- Success Rate: 100%
- Avg Response Time: 654ms
- Rate Limit Remaining: 4,984 / 5,000

Last Refresh: 3 minutes ago
Next Refresh: in 12 minutes
```

**Permissions:** Any user can view stats

---

## Configuration Options

### Repository Visibility

#### Public Repositories
**Recommended for most users**

Advantages:
- No authentication required
- Simple setup
- Easy sharing with community
- Free on GitHub

Setup:
```
1. Create repository
2. Set visibility to "Public"
3. Configure bot: /prompt-config set <url>
```

#### Private Repositories
**For sensitive or proprietary prompts**

Advantages:
- Keep prompts confidential
- Control who can view
- Suitable for commercial use

Requirements:
- GitHub Personal Access Token (PAT)
- Token configured by bot administrator
- May have API rate limit benefits

Setup:
```
1. Create private repository
2. Generate GitHub PAT with 'repo:read' scope
3. Contact bot administrator to configure token
4. Configure bot: /prompt-config set <url>
```

### Branch Configuration

#### Using Main Branch (Recommended)
```
/prompt-config set https://github.com/user/repo main
```

Best for:
- Production use
- Stable prompts
- Most servers

#### Using Development Branch
```
/prompt-config set https://github.com/user/repo development
```

Best for:
- Testing new prompts
- Frequent updates
- Experimental changes

#### Using Feature Branches
```
/prompt-config set https://github.com/user/repo feature/new-format
```

Best for:
- Testing specific features
- A/B testing
- Temporary experiments

### Schema Version Selection

Currently supported: `v1`

**v1 Features:**
- Basic PATH file routing
- Template variable support
- Text-based prompt files
- System and user prompt separation

**Future: v2** (Planned)
- YAML-based configuration
- Prompt composition
- Conditional logic
- Advanced metadata

---

## Security Considerations

### Access Control

#### Guild-Level Isolation

Each Discord guild's configuration is completely isolated:
- Guild A cannot access Guild B's prompts
- Configuration changes only affect your guild
- Cache is guild-specific

#### Command Permissions

Permission hierarchy for commands:

| Command | Guild Owner | Administrator | Bot Manager | Everyone |
|---------|------------|---------------|-------------|----------|
| `/prompt-config set` | ✅ | ✅ | ✅ | ❌ |
| `/prompt-config remove` | ✅ | ✅ | ✅ | ❌ |
| `/prompt-config refresh` | ✅ | ✅ | ✅ | ❌ |
| `/prompt-config status` | ✅ | ✅ | ✅ | ✅ |
| `/prompt-config test` | ✅ | ✅ | ✅ | ✅ |
| `/prompt-cache stats` | ✅ | ✅ | ✅ | ✅ |

**Configuring Bot Manager Role:**
```
/bot-config set-manager-role @BotManagers
```

### Content Validation

All fetched prompts undergo security validation:

#### Prohibited Patterns

Prompts are rejected if they contain:
```
eval(
exec(
__import__
<script>
subprocess.
os.system
${...exec
{{...exec
```

**Reason:** Prevent code injection attempts

#### File Size Limits

- Maximum file size: 50 KB
- Maximum line length: 10,000 characters
- Total cached size per guild: ~100 MB

**Reason:** Prevent resource exhaustion

#### Encoding Validation

- Only UTF-8 encoding accepted
- No binary files
- No null bytes

**Reason:** Ensure text-only content

### GitHub Token Security

If using private repositories:

#### Token Storage
- Tokens encrypted at rest using AES-256
- Tokens never logged or exposed in errors
- Tokens never sent to Discord client

#### Token Permissions

Minimum required GitHub PAT scopes:
- `repo` (read access) for private repositories
- OR no token for public repositories

**Generate PAT:**
1. GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (or `public_repo` if only public)
4. Generate and copy token
5. Provide to bot administrator securely

#### Token Rotation

Best practices:
- Rotate tokens every 90 days
- Immediately rotate if compromised
- Use different tokens for different bots

### Audit Logging

All configuration changes are logged:
- Timestamp
- Guild ID
- User ID
- Action (set/remove/refresh)
- Old configuration
- New configuration

**Viewing audit logs** (bot administrator only):
```sql
SELECT * FROM guild_prompt_config_audit
WHERE guild_id = ?
ORDER BY created_at DESC;
```

---

## Performance Optimization

### Cache Configuration

#### Cache Levels

```
Level 1: In-Memory Cache (Fastest)
  ↓ miss
Level 2: Redis Cache (Fast)
  ↓ miss
Level 3: Database Cache (Persistent)
  ↓ miss
Fetch from GitHub
```

#### Cache TTL

Default: 15 minutes

**Why 15 minutes?**
- Balance between freshness and API usage
- Most servers don't update prompts frequently
- Prevents GitHub rate limit issues

**Effective TTL:**
- Fresh cache: Instant response (<5ms)
- Expired cache: Fetch from GitHub (~500-1000ms)
- Stale cache (GitHub down): Use cached up to 24 hours old

### Optimizing Hit Rate

Current target: 85% cache hit rate

**Strategies to improve:**

1. **Increase TTL** (if prompts rarely change)
   ```
   Requires bot configuration change (contact administrator)
   ```

2. **Pre-warm cache**
   ```
   /prompt-config refresh
   ```
   Run after making changes to populate cache

3. **Minimize prompt file count**
   ```
   # Less efficient (12 files)
   system/{type}/{category}/prompt.md

   # More efficient (3 files)
   system/{type}.md
   ```

4. **Use consistent summary types**
   - Encourage users to use same summary types
   - Popular types stay cached longer

### GitHub API Rate Limits

#### Public Repositories (No Token)
- Limit: 60 requests per hour per IP
- Bot shares IP with all guilds on same server
- Very limited for production use

#### Authenticated (With Token)
- Limit: 5,000 requests per hour per token
- Sufficient for most deployments
- Rate limit info in headers

#### Rate Limit Management

Bot implements:
- Exponential backoff on 429 errors
- Rate limit header tracking
- Per-guild request limiting (10 requests/minute)
- Cache-first strategy

**Monitoring rate limits:**
```
/prompt-cache stats
```
Shows: "Rate Limit Remaining: 4,984 / 5,000"

#### If Rate Limited

Bot behavior:
1. Extend cache TTL temporarily
2. Use stale cache if available
3. Fall back to default prompts
4. Log warning
5. Retry after rate limit reset

User sees:
```
ℹ️ Using cached prompts (GitHub rate limit reached)
```

### Network Performance

#### Fetch Timeouts

Default timeout: 5 seconds per file

**If fetches timeout frequently:**
1. Check repository size
2. Reduce prompt file sizes
3. Check GitHub status
4. Consider using CDN/mirror

#### Concurrent Fetches

Bot fetches multiple files in parallel:
- Maximum concurrent: 5 files at once
- Reduces total fetch time
- Doesn't overwhelm GitHub API

**Example:**
```
Sequential: 500ms × 6 files = 3000ms
Parallel:   max(500ms files) ≈ 600ms
```

### Optimization Checklist

- [ ] Public repository (unless privacy required)
- [ ] Minimize number of prompt files
- [ ] Keep prompt files under 10 KB each
- [ ] Use PATH patterns efficiently
- [ ] Monitor cache hit rate
- [ ] Use manual refresh sparingly
- [ ] Configure during low-traffic periods

---

## Monitoring and Diagnostics

### Health Checks

#### Automated Monitoring

Bot performs automatic health checks:
- Every 5 minutes: Check cache validity
- Every 15 minutes: Test GitHub connectivity
- Every hour: Validate configuration
- Every day: Cache cleanup and optimization

#### Health Indicators

**Healthy Configuration:**
```
- Success rate: >95%
- Avg fetch latency: <1000ms
- Cache hit rate: >80%
- Error rate: <5%
```

**Warning Signs:**
```
- Success rate: 90-95%
- Avg fetch latency: 1000-2000ms
- Cache hit rate: 70-80%
- Error rate: 5-10%
```

**Critical Issues:**
```
- Success rate: <90%
- Avg fetch latency: >2000ms
- Cache hit rate: <70%
- Error rate: >10%
```

### Log Analysis

#### Important Log Events

**Configuration Changes:**
```
[INFO] Guild 123456: External prompt config set
Repository: https://github.com/user/repo
User: 789012
```

**Fetch Success:**
```
[INFO] Guild 123456: External prompt fetched
File: system/brief.md
Duration: 654ms
Source: github
```

**Fetch Failure:**
```
[WARNING] Guild 123456: GitHub fetch failed
Error: Repository not found (404)
Fallback: Using cached prompt
```

**Cache Hit:**
```
[DEBUG] Guild 123456: Prompt cache hit
Key: prompt:123456:v1:system:brief:support:help
Tier: memory
Age: 5m32s
```

**Fallback Used:**
```
[WARNING] Guild 123456: Using default prompt fallback
Reason: GitHub timeout after 5s
```

### Metrics Dashboard

Key metrics to monitor:

#### Request Metrics
```
Total Requests:       1,432 / day
Cache Hits:          1,416 (98.9%)
GitHub Fetches:         16 (1.1%)
Fallbacks:               2 (0.1%)
```

#### Performance Metrics
```
Avg Cache Hit Latency:     2.3ms
Avg GitHub Fetch Latency: 847ms
p95 Latency:              1.2s
p99 Latency:              2.4s
```

#### Error Metrics
```
Total Errors:               3 / day
Timeout Errors:             1
404 Not Found:              1
Rate Limit:                 0
Validation Failures:        1
```

#### Resource Metrics
```
Cache Memory Usage:      28.4 KB / guild
Total Cached Guilds:        150
Database Size:            4.2 MB
GitHub API Remaining:    4,984 / 5,000
```

### Troubleshooting Tools

#### Command: `/prompt-config test`
**Use when:** Configuration not working as expected

**Checks:**
- Repository accessibility
- File existence
- Content validation
- Pattern matching

#### Command: `/prompt-config status`
**Use when:** Checking current state

**Shows:**
- Active configuration
- Last fetch status
- Cache statistics
- Error history

#### Command: `/prompt-cache stats`
**Use when:** Investigating performance issues

**Shows:**
- Cache hit/miss rates
- Latency metrics
- GitHub API usage
- Cache efficiency

#### Bot Logs (Administrator)
**Use when:** Deep troubleshooting needed

**Access:** Server logs or log aggregation system

**Filter by:**
- Guild ID
- Log level (ERROR, WARNING, INFO)
- Time range
- Component (external_prompts)

---

## Advanced Configuration

### Multi-Environment Setup

Use branches for different environments:

```
Production:  /prompt-config set repo main
Staging:     /prompt-config set repo staging
Development: /prompt-config set repo dev
```

### Shared Repositories

Multiple guilds can share the same repository:

**Advantages:**
- Centralized prompt management
- Consistent experience across guilds
- Reduced maintenance

**Implementation:**
1. Create organization repository
2. Configure each guild:
   ```
   /prompt-config set https://github.com/org/shared-prompts
   ```

### Path-Based Guild Customization

Use `{guild}` variable for guild-specific overrides:

**PATH file:**
```
# Guild-specific overrides
guilds/{guild}/system/{type}.md

# Fallback to shared prompts
system/{type}.md
```

**Directory structure:**
```
prompts/
├── guilds/
│   ├── 123456/
│   │   └── system/
│   └── 789012/
│       └── system/
└── system/              ← Shared defaults
    ├── brief.md
    ├── detailed.md
    └── comprehensive.md
```

### Webhook Integration (Future)

Planned: Automatic cache refresh on repository push

**Configuration:**
1. Set up GitHub webhook
2. Configure webhook URL: `https://bot.example.com/webhook/prompts`
3. On push event: Bot automatically refreshes cache

**Benefits:**
- Zero-latency updates
- No manual refresh needed
- Efficient API usage

---

## Troubleshooting Guide

### Diagnostic Flowchart

```
Start: /prompt-config test
    ↓
[Repository Accessible?]
    ↓ No → Check URL, GitHub status
    ↓ Yes
[Schema Version Valid?]
    ↓ No → Fix schema-version file
    ↓ Yes
[PATH File Valid?]
    ↓ No → Fix PATH syntax
    ↓ Yes
[Required Files Exist?]
    ↓ No → Create missing files
    ↓ Yes
[Content Passes Validation?]
    ↓ No → Remove suspicious patterns
    ↓ Yes
[Success! Configuration OK]
```

### Common Error Codes

| Error | Cause | Solution |
|-------|-------|----------|
| `ERR_REPO_NOT_FOUND` | Repository doesn't exist or is private | Verify URL, check visibility |
| `ERR_SCHEMA_UNSUPPORTED` | Schema version not supported | Use `v1` in schema-version |
| `ERR_PATH_SYNTAX` | PATH file has syntax errors | Validate PATH patterns |
| `ERR_FILE_NOT_FOUND` | Prompt file missing | Create referenced file |
| `ERR_CONTENT_INVALID` | Prompt content validation failed | Remove suspicious patterns |
| `ERR_RATE_LIMIT` | GitHub rate limit exceeded | Wait or configure token |
| `ERR_TIMEOUT` | GitHub request timed out | Retry or check GitHub status |
| `ERR_AUTH_FAILED` | GitHub authentication failed | Verify token validity |

### Emergency Procedures

#### Complete Failure Scenario

If external prompts completely fail:

1. **Bot automatically falls back to defaults**
   - No manual intervention needed
   - Summaries continue working

2. **Investigation:**
   ```
   /prompt-config status
   /prompt-config test
   /prompt-cache stats
   ```

3. **Temporary fix:**
   ```
   /prompt-config remove
   ```
   (Revert to defaults while fixing)

4. **Fix repository issues**

5. **Reconfigure:**
   ```
   /prompt-config set <url>
   ```

#### GitHub Outage

If GitHub is down:
- Bot uses cached prompts (up to 24 hours old)
- No action required
- Automatically recovers when GitHub returns

#### Corrupted Cache

If cache seems corrupted:
```
/prompt-config refresh
```
Forces fresh fetch and cache rebuild

---

## Best Practices Summary

### Configuration
- ✅ Use public repositories when possible
- ✅ Keep prompts in version control
- ✅ Use descriptive commit messages
- ✅ Test before deploying to main branch
- ✅ Document your prompts in README

### Security
- ✅ Review all changes before merging
- ✅ Never commit secrets or tokens
- ✅ Use branch protection on main
- ✅ Audit configuration changes regularly
- ✅ Rotate GitHub tokens periodically

### Performance
- ✅ Minimize number of prompt files
- ✅ Keep files under 10 KB
- ✅ Use efficient PATH patterns
- ✅ Monitor cache hit rates
- ✅ Leverage caching effectively

### Monitoring
- ✅ Check `/prompt-config status` weekly
- ✅ Monitor error rates
- ✅ Review cache statistics
- ✅ Set up alerts for critical issues
- ✅ Keep configuration documented

---

## Additional Resources

- **User Guide**: `docs/external-prompts-user-guide.md`
- **Template Repository**: `docs/external-prompts-template-repo.md`
- **FAQ**: `docs/external-prompts-faq.md`
- **Technical Specification**: `docs/external-prompt-hosting-spec.md`
- **Pseudocode**: `docs/external-prompt-hosting-pseudocode.md`

---

For questions or support:
- Discord: [Support Server]
- GitHub: [Issues]
- Documentation: [Docs Site]
