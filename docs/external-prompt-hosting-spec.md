# External Prompt Hosting Feature - Technical Specification

**Version:** 1.0.0
**Date:** 2026-01-14
**Status:** Draft

---

## 1. Executive Summary

This specification defines an external prompt hosting system for the Discord Summarization Bot that allows each Discord guild (server) to maintain custom summarization prompts in dedicated GitHub repositories. The system provides flexible, versioned, and maintainable prompt customization while maintaining backward compatibility with the existing in-code prompt system.

### 1.1 Key Goals

- **Per-Guild Customization**: Each Discord guild can maintain its own prompt repository
- **Optional Feature**: System continues to work with default prompts if no repository is configured
- **Schema Versioning**: Support for backward-compatible prompt schema evolution
- **Flexible Prompt Selection**: Dynamic prompt routing using template parameters
- **Zero Breaking Changes**: Existing bot functionality remains unchanged

---

## 2. Functional Requirements

### 2.1 Core Features

#### FR-001: GitHub Repository Integration
**Priority:** HIGH
**Description:** The system shall support fetching summarization prompts from GitHub repositories.

**Acceptance Criteria:**
- System can authenticate with GitHub using personal access tokens or GitHub Apps
- System can fetch files from public and private repositories
- Repository URLs follow the format: `https://github.com/{owner}/{repo}`
- Support for branch specification (default: `main`)
- Connection failures gracefully fallback to default prompts

#### FR-002: Per-Guild Configuration
**Priority:** HIGH
**Description:** Each Discord guild can configure its own prompt repository.

**Acceptance Criteria:**
- Guild administrators can set repository URL via bot command
- Configuration stored in bot database (guild_id -> repo_url mapping)
- Multiple guilds can share the same repository
- Configuration can be viewed and cleared by administrators
- Guilds without configuration use default prompts

#### FR-003: Schema Versioning
**Priority:** HIGH
**Description:** Prompt repositories support versioned schemas for backward compatibility.

**Acceptance Criteria:**
- Repository root contains a `schema-version` file (content: `v1`, `v2`, etc.)
- Bot supports multiple schema versions concurrently
- Missing schema version defaults to `v1`
- Schema validation occurs at fetch time
- Invalid schemas trigger fallback to default prompts with warning log

#### FR-004: Dynamic Prompt Selection (PATH System)
**Priority:** HIGH
**Description:** Prompts are selected dynamically based on context using a PATH file.

**Acceptance Criteria:**
- Repository contains a `PATH` file defining prompt routing rules
- PATH file supports template parameters: `{category}`, `{channel}`, `{guild}`, `{type}`
- Patterns matched in order of specificity (most specific first)
- First matching pattern determines prompt file path
- Missing PATH file results in fallback behavior

#### FR-005: Prompt Caching
**Priority:** MEDIUM
**Description:** Fetched prompts are cached to reduce API calls and improve performance.

**Acceptance Criteria:**
- Prompts cached in memory with TTL (default: 15 minutes)
- Cache invalidation on configuration change
- Manual cache refresh command for administrators
- Cache miss triggers fresh fetch from GitHub
- Cache statistics available via health check endpoint

#### FR-006: Fallback Mechanisms
**Priority:** HIGH
**Description:** System provides robust fallback for all failure scenarios.

**Acceptance Criteria:**
- GitHub fetch failure → use cached prompt if available → use default prompt
- Invalid schema → use default prompt with warning
- Missing prompt file → use default prompt
- Malformed PATH file → use default prompt selection logic
- All fallbacks logged for monitoring

#### FR-007: Configuration Commands
**Priority:** HIGH
**Description:** Bot provides slash commands for managing external prompt configuration.

**Acceptance Criteria:**
- `/prompt config set <repo_url>` - Set repository for current guild (admin only)
- `/prompt config view` - View current configuration
- `/prompt config clear` - Remove repository configuration (admin only)
- `/prompt config test` - Test repository connectivity and schema validation
- `/prompt cache refresh` - Force cache refresh (admin only)
- `/prompt cache stats` - View cache statistics

### 2.2 Prompt Repository Structure

#### FR-008: Repository File Organization
**Priority:** HIGH
**Description:** External repositories follow a defined structure.

**Acceptance Criteria:**
- Root directory contains `schema-version` file
- Root directory contains `PATH` file
- Prompts organized in directories by category
- System prompts and user prompts stored separately
- Support for template variables in prompts

**Example Structure:**
```
my-guild-prompts/
├── schema-version          # Contains: v1
├── PATH                    # Routing rules
├── system/                 # System prompts
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
├── user/                   # User prompts
│   ├── default.md
│   └── technical.md
├── categories/             # Category-specific prompts
│   ├── support/
│   │   ├── system.md
│   │   └── user.md
│   └── development/
│       ├── system.md
│       └── user.md
└── channels/               # Channel-specific overrides
    └── general/
        └── system.md
```

---

## 3. Non-Functional Requirements

### 3.1 Performance

#### NFR-001: Response Time
**Description:** Prompt fetching must not significantly impact summarization latency.

**Metrics:**
- Cache hit: <5ms to retrieve prompt
- Cache miss (GitHub fetch): <2 seconds for complete prompt retrieval
- Timeout after 5 seconds with fallback to cached/default prompt
- Overall summarization latency increase: <10%

#### NFR-002: API Rate Limits
**Description:** GitHub API usage must respect rate limits.

**Requirements:**
- Maximum 10 GitHub API requests per minute per guild
- Implement exponential backoff for rate limit errors
- Cache prompts aggressively to minimize API calls
- Use conditional requests (ETag/If-Modified-Since) when possible

#### NFR-003: Scalability
**Description:** System must handle multiple guilds efficiently.

**Requirements:**
- Support 1,000+ guilds with external prompts configured
- Shared cache across guilds using same repository
- Memory usage: <50MB for 1,000 cached prompts
- Concurrent prompt fetches: up to 20 simultaneous requests

### 3.2 Security

#### NFR-004: Authentication
**Description:** GitHub authentication must be secure.

**Requirements:**
- Support GitHub Personal Access Tokens (PAT) with minimal scopes
- Support GitHub Apps for better security and rate limits
- Tokens stored encrypted in database or environment variables
- No tokens exposed in logs or error messages
- Token rotation support without bot restart

#### NFR-005: Content Validation
**Description:** Fetched prompts must be validated for safety.

**Requirements:**
- Maximum prompt size: 50KB per file
- Character encoding validation (UTF-8 only)
- No executable code in prompts
- Sanitize template variables to prevent injection
- Reject prompts containing suspicious patterns (e.g., `eval()`, `exec()`)

#### NFR-006: Access Control
**Description:** Only authorized users can configure external prompts.

**Requirements:**
- Repository configuration requires `ADMINISTRATOR` permission or custom bot role
- Audit log for all configuration changes
- Guild-level isolation (no cross-guild access)
- Read-only access to GitHub repositories (no write operations)

### 3.3 Maintainability

#### NFR-007: Backward Compatibility
**Description:** Existing functionality must not break.

**Requirements:**
- Default prompts remain unchanged in codebase
- Guilds without configuration work exactly as before
- Schema v1 remains supported indefinitely
- Deprecation warnings for 6 months before removing old features

#### NFR-008: Observability
**Description:** System behavior must be observable and debuggable.

**Requirements:**
- Structured logging for all prompt fetches
- Metrics: cache hit rate, fetch latency, fallback frequency
- Health check endpoint includes GitHub connectivity status
- Detailed error messages for configuration issues
- Debug mode for verbose logging

#### NFR-009: Documentation
**Description:** Feature must be well-documented.

**Requirements:**
- User guide for guild administrators
- Template repository with examples
- API documentation for developers
- Migration guide from default to custom prompts
- Troubleshooting guide for common issues

### 3.4 Reliability

#### NFR-010: Availability
**Description:** External prompt system must not reduce bot availability.

**Requirements:**
- Bot remains operational during GitHub outages
- Fallback to default prompts within 100ms of failure detection
- No single point of failure
- Graceful degradation under load
- Circuit breaker for repeated GitHub failures

#### NFR-011: Data Consistency
**Description:** Prompt caching must be consistent and correct.

**Requirements:**
- Cache invalidation within 1 minute of configuration change
- No stale prompts served after repository update
- Atomic cache updates (no partial prompt loads)
- Cache versioning to prevent mismatches

---

## 4. User Stories

### 4.1 Guild Administrator Stories

#### US-001: Configure Custom Prompts
**As a** guild administrator
**I want to** configure a custom prompt repository for my server
**So that** I can tailor summaries to my community's needs

**Acceptance:**
- I can run `/prompt config set <repo_url>` to configure the repository
- I receive confirmation that the configuration was saved
- I can test the configuration with `/prompt config test`
- Bot shows me a success/failure message with details

#### US-002: Update Prompts Without Bot Restart
**As a** guild administrator
**I want to** update prompts by pushing to my GitHub repository
**So that** I can iterate on prompts without involving bot developers

**Acceptance:**
- I push changes to my GitHub repository
- Within 15 minutes, the bot uses the new prompts
- I can force immediate refresh with `/prompt cache refresh`
- I see a confirmation that cache was cleared

#### US-003: Troubleshoot Configuration Issues
**As a** guild administrator
**I want to** see detailed error messages when my configuration fails
**So that** I can fix issues independently

**Acceptance:**
- Bot tells me if repository URL is invalid
- Bot tells me if schema version is unsupported
- Bot tells me if PATH file has syntax errors
- Bot provides suggestions for fixing issues
- I can view full error details in bot logs

#### US-004: View Current Configuration
**As a** guild administrator
**I want to** view my current prompt configuration
**So that** I can verify what repository is active

**Acceptance:**
- I run `/prompt config view`
- I see: repository URL, branch, schema version, last fetch time
- I see cache status (hit rate, size, last refresh)
- I see whether current configuration is working

#### US-005: Remove Custom Configuration
**As a** guild administrator
**I want to** remove my custom prompt repository
**So that** I can return to default prompts

**Acceptance:**
- I run `/prompt config clear`
- Bot asks for confirmation
- After confirmation, configuration is removed
- Bot immediately uses default prompts
- Cache is cleared automatically

### 4.2 Bot Developer Stories

#### US-006: Add New Template Parameters
**As a** bot developer
**I want to** add new template parameters to the PATH system
**So that** I can support more complex prompt routing

**Acceptance:**
- I modify the PATH parser to recognize new parameters
- Existing PATH files continue to work
- New parameters documented in spec
- Backward compatibility maintained

#### US-007: Evolve Prompt Schema
**As a** bot developer
**I want to** introduce a new schema version (v2)
**So that** I can support enhanced prompt features

**Acceptance:**
- I implement v2 schema parser
- v1 repositories continue to work unchanged
- Bot detects schema version automatically
- Migration guide available for users

#### US-008: Monitor External Prompt Usage
**As a** bot developer
**I want to** monitor GitHub API usage and errors
**So that** I can optimize the system and debug issues

**Acceptance:**
- Metrics available via `/prompt stats` command
- Logs include: fetch count, cache hit rate, error rate
- Health check endpoint shows GitHub API status
- Alerts trigger on high error rates

### 4.3 End User Stories

#### US-009: Receive Customized Summaries
**As a** Discord server member
**I want to** receive summaries tailored to my server's context
**So that** summaries are more relevant and useful

**Acceptance:**
- I run `/summarize` command
- Bot uses custom prompts if configured by admin
- Summary format matches my server's preferences
- No difference in command usage between default and custom prompts

#### US-010: Consistent Experience During Outages
**As a** Discord server member
**I want** summaries to work even when GitHub is down
**So that** I can rely on the bot consistently

**Acceptance:**
- GitHub outage occurs
- Bot still generates summaries using cached/default prompts
- I may see a notice about using cached prompts
- Functionality restored automatically when GitHub recovers

---

## 5. Edge Cases and Error Handling

### 5.1 Repository Access Errors

#### EC-001: Repository Not Found (404)
**Scenario:** Configured repository doesn't exist or is deleted

**Handling:**
- Log warning with guild_id and repository URL
- Use cached prompts if available (with expiry extension)
- Fall back to default prompts if cache unavailable
- Notify admin via DM (if notification preferences enabled)
- Display user-friendly message: "Using default prompts (custom repository unavailable)"

#### EC-002: Authentication Failure (401/403)
**Scenario:** GitHub token invalid or lacks permissions

**Handling:**
- Log error with token identifier (not token value)
- Mark configuration as invalid in database
- Use cached prompts with extended TTL
- Notify admin: "GitHub authentication failed. Please update repository configuration."
- Provide troubleshooting link

#### EC-003: Rate Limit Exceeded (429)
**Scenario:** GitHub API rate limit hit

**Handling:**
- Implement exponential backoff (initial: 60s, max: 15min)
- Extend cache TTL during rate limit period
- Log warning with retry time
- No user-facing error (seamless fallback)
- Monitor rate limit metrics

### 5.2 Schema and Validation Errors

#### EC-004: Invalid Schema Version
**Scenario:** `schema-version` file contains unsupported version (e.g., `v99`)

**Handling:**
- Log error: "Unsupported schema version: v99"
- Fall back to default prompts
- Admin notification: "Your prompt repository uses an unsupported schema version. Please upgrade to v1 or v2."
- Continue using cached prompts until issue resolved

#### EC-005: Malformed PATH File
**Scenario:** PATH file has syntax errors or invalid patterns

**Handling:**
- Parse with error recovery (skip invalid lines)
- Log specific line numbers with errors
- Use valid patterns, ignore malformed ones
- Fall back to default prompt selection if no valid patterns
- Admin notification with syntax error details

#### EC-006: Missing Required Files
**Scenario:** Repository lacks `schema-version`, `PATH`, or referenced prompt files

**Handling:**
- For `schema-version`: assume v1 and log warning
- For `PATH`: use default prompt selection logic
- For prompt files: fall back to next matching pattern or default prompt
- Comprehensive error logged for admin debugging

#### EC-007: Prompt File Too Large
**Scenario:** Prompt file exceeds 50KB limit

**Handling:**
- Reject file and log warning
- Fall back to default prompt
- Admin notification: "Prompt file 'system/detailed.md' exceeds size limit (50KB). Using default prompt."
- Provide guidance on splitting large prompts

### 5.3 Network and Timeout Errors

#### EC-008: GitHub API Timeout
**Scenario:** Request to GitHub times out after 5 seconds

**Handling:**
- Abort request and log timeout
- Use cached prompt (extend TTL)
- If no cache, use default prompt
- Retry with exponential backoff on next request
- No user-facing error

#### EC-009: Partial Fetch Failure
**Scenario:** Some files fetched successfully, others failed

**Handling:**
- Use successfully fetched prompts where available
- Fall back to defaults for failed files
- Log detailed failure information
- Cache partial results with shorter TTL
- Admin notification of partial failure

#### EC-010: Network Unavailable
**Scenario:** Bot has no internet connectivity

**Handling:**
- Detect network failure immediately (connection refused)
- Use cached prompts exclusively
- Log connectivity issue
- Retry every 5 minutes in background
- Admin notification after 30 minutes of persistent failure

### 5.4 Concurrency and Race Conditions

#### EC-011: Concurrent Configuration Changes
**Scenario:** Multiple admins change configuration simultaneously

**Handling:**
- Database transaction with optimistic locking
- Last write wins with conflict detection
- Clear cache after successful write
- Log all configuration changes with user_id and timestamp
- Conflict notification to both admins

#### EC-012: Concurrent Cache Refresh
**Scenario:** Multiple processes try to refresh cache simultaneously

**Handling:**
- Distributed lock (Redis-based or database-based)
- First process acquires lock and refreshes
- Other processes wait for completion
- Share refreshed cache across all processes
- Lock timeout: 10 seconds

#### EC-013: Cache Invalidation During Fetch
**Scenario:** Cache cleared while fetch in progress

**Handling:**
- Version cache entries
- Discard fetch result if version mismatch
- Trigger new fetch for updated version
- Prevent serving stale data
- Log cache version mismatches

### 5.5 Content and Security Issues

#### EC-014: Suspicious Prompt Content
**Scenario:** Prompt contains potential injection patterns

**Handling:**
- Scan for patterns: `eval(`, `exec(`, `{{`, `${`, `<script>`
- Reject suspicious prompts
- Log security warning with pattern matched
- Admin notification: "Prompt rejected due to security concerns"
- Use default prompts

#### EC-015: Non-UTF8 Encoding
**Scenario:** Prompt file uses invalid character encoding

**Handling:**
- Attempt to detect encoding
- Try common encodings (UTF-8, ISO-8859-1, UTF-16)
- If detection fails, reject file
- Log encoding error
- Fall back to default prompt

#### EC-016: Template Variable Injection
**Scenario:** User attempts to inject template variables via channel names

**Handling:**
- Sanitize all template variable values
- Escape special characters: `{`, `}`, `$`, `%`
- Validate channel names against Discord naming rules
- Reject suspicious patterns
- Log injection attempts

### 5.6 Data Consistency Issues

#### EC-017: Schema Version Mismatch
**Scenario:** Repository updated to v2 while bot still processing v1 cache

**Handling:**
- Include schema version in cache key
- Separate cache namespaces for v1 and v2
- Fetch new prompts when schema version changes
- Log schema upgrade
- Clear old schema cache after 24 hours

#### EC-018: Prompt Repository Moved
**Scenario:** Repository renamed or transferred to new owner

**Handling:**
- GitHub redirects (301) followed automatically
- Update configuration with new URL
- Log repository move with old and new URLs
- Admin notification of URL change
- Verify new URL works before updating

#### EC-019: Branch Deleted or Renamed
**Scenario:** Configured branch no longer exists

**Handling:**
- Fall back to default branch (`main` or `master`)
- Log branch failure
- Admin notification: "Configured branch not found, using default branch"
- Attempt to detect primary branch via GitHub API

---

## 6. Data Model

### 6.1 Database Schema

#### Table: `guild_prompt_config`

```sql
CREATE TABLE guild_prompt_config (
    guild_id VARCHAR(32) PRIMARY KEY,
    repository_url TEXT NOT NULL,
    repository_branch VARCHAR(255) DEFAULT 'main',
    github_token_id VARCHAR(64),  -- Reference to encrypted token storage
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(32),  -- Discord user_id
    last_fetch_at TIMESTAMP,
    last_fetch_status VARCHAR(20),  -- 'success', 'failed', 'partial'
    last_fetch_error TEXT,
    schema_version VARCHAR(10),
    fetch_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX idx_guild_prompt_enabled ON guild_prompt_config(enabled);
CREATE INDEX idx_guild_prompt_updated ON guild_prompt_config(updated_at);
```

#### Table: `prompt_cache`

```sql
CREATE TABLE prompt_cache (
    cache_key VARCHAR(128) PRIMARY KEY,  -- hash(guild_id, schema_version, file_path)
    guild_id VARCHAR(32),
    repository_url TEXT,
    file_path TEXT,
    content TEXT,
    schema_version VARCHAR(10),
    content_hash VARCHAR(64),  -- SHA256 of content
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    size_bytes INTEGER,
    FOREIGN KEY (guild_id) REFERENCES guild_prompt_config(guild_id) ON DELETE CASCADE
);

CREATE INDEX idx_prompt_cache_guild ON prompt_cache(guild_id);
CREATE INDEX idx_prompt_cache_expires ON prompt_cache(expires_at);
CREATE INDEX idx_prompt_cache_accessed ON prompt_cache(last_accessed_at);
```

#### Table: `prompt_fetch_log`

```sql
CREATE TABLE prompt_fetch_log (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(32),
    repository_url TEXT,
    fetch_type VARCHAR(20),  -- 'manual', 'auto', 'fallback'
    status VARCHAR(20),  -- 'success', 'failed', 'partial', 'cached'
    error_message TEXT,
    files_fetched INTEGER,
    files_failed INTEGER,
    duration_ms INTEGER,
    triggered_by VARCHAR(32),  -- Discord user_id or 'system'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guild_prompt_config(guild_id) ON DELETE CASCADE
);

CREATE INDEX idx_fetch_log_guild ON prompt_fetch_log(guild_id);
CREATE INDEX idx_fetch_log_created ON prompt_fetch_log(created_at);
CREATE INDEX idx_fetch_log_status ON prompt_fetch_log(status);
```

### 6.2 In-Memory Cache Structure

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

@dataclass
class CachedPrompt:
    """In-memory representation of cached prompt."""
    guild_id: str
    file_path: str
    content: str
    schema_version: str
    cached_at: datetime
    expires_at: datetime
    content_hash: str
    access_count: int = 0

@dataclass
class PromptRepositoryMetadata:
    """Metadata about a prompt repository."""
    guild_id: str
    repository_url: str
    branch: str
    schema_version: str
    path_patterns: Dict[str, str]  # pattern -> file_path
    last_fetch_at: datetime
    fetch_status: str
    etag: Optional[str] = None  # For HTTP caching
```

### 6.3 Configuration Models

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum

class SchemaVersion(Enum):
    """Supported schema versions."""
    V1 = "v1"
    V2 = "v2"  # Future use

@dataclass
class GitHubConfig:
    """GitHub API configuration."""
    token: Optional[str] = None
    timeout_seconds: int = 5
    max_file_size_kb: int = 50
    base_url: str = "https://api.github.com"

@dataclass
class PromptPathPattern:
    """Represents a PATH file pattern."""
    pattern: str  # e.g., "{category}/{type}/system.md"
    priority: int  # Lower = higher priority
    template_params: List[str]  # e.g., ["category", "type"]

    def matches(self, context: Dict[str, str]) -> bool:
        """Check if pattern matches given context."""
        # Implementation in PATH parser
        pass

    def resolve(self, context: Dict[str, str]) -> str:
        """Resolve pattern to file path."""
        # Implementation in PATH parser
        pass

@dataclass
class ExternalPromptConfig:
    """Complete external prompt configuration."""
    guild_id: str
    repository_url: str
    branch: str = "main"
    enabled: bool = True
    schema_version: SchemaVersion = SchemaVersion.V1
    path_patterns: List[PromptPathPattern] = field(default_factory=list)
    cache_ttl_minutes: int = 15
    github_config: GitHubConfig = field(default_factory=GitHubConfig)
```

---

## 7. PATH File Specification

### 7.1 Format Overview

The PATH file defines routing rules for selecting prompts based on context parameters. It uses a simple pattern-matching syntax with template variables.

### 7.2 Syntax

```
# Comments start with #
# Empty lines ignored
# Patterns matched in order (first match wins)

# Pattern format:
# {param1}/{param2}/file.md

# Supported parameters:
# {guild}    - Guild/server ID or name
# {channel}  - Channel name (without #)
# {category} - Channel category name
# {type}     - Summary type (brief, detailed, comprehensive)
# {role}     - Primary role of command executor

# Examples:
```

### 7.3 Example PATH File (v1 Schema)

```
# PATH file for custom prompts
# Schema: v1

# Technical channels use specialized prompts
categories/development/{type}/system.md
categories/development/{type}/user.md

# Support channels
categories/support/brief/system.md
categories/support/brief/user.md

# Channel-specific overrides
channels/announcements/{type}/system.md

# Type-specific defaults
{type}/system.md
{type}/user.md

# Fallback to generic prompts
system/default.md
user/default.md
```

### 7.4 Pattern Matching Logic

```python
def select_prompt(context: Dict[str, str], patterns: List[PromptPathPattern]) -> str:
    """
    Select appropriate prompt file based on context.

    Args:
        context: {
            "guild": "123456789",
            "channel": "general",
            "category": "support",
            "type": "brief",
            "role": "moderator"
        }
        patterns: List of PATH patterns

    Returns:
        File path to use (e.g., "categories/support/brief/system.md")
    """
    # Sort patterns by priority (more specific = higher priority)
    sorted_patterns = sorted(patterns, key=lambda p: p.priority)

    for pattern in sorted_patterns:
        if pattern.matches(context):
            return pattern.resolve(context)

    # No match - use default
    return f"system.md"
```

### 7.5 Pattern Priority Calculation

```python
def calculate_priority(pattern: str) -> int:
    """
    Calculate pattern priority based on specificity.
    Lower number = higher priority (more specific)

    Priority factors:
    - Fewer template variables = more specific
    - Longer static paths = more specific
    - Earlier in file = higher priority (tie-breaker)

    Examples:
        "categories/dev/brief/system.md" -> priority 1 (very specific)
        "categories/{category}/{type}/system.md" -> priority 5 (medium)
        "{type}/system.md" -> priority 10 (low)
        "default.md" -> priority 100 (fallback)
    """
    # Count template variables
    template_count = pattern.count('{')

    # Count path segments
    segment_count = pattern.count('/')

    # Calculate priority
    priority = template_count * 10 - segment_count

    return max(0, priority)
```

### 7.6 Template Variable Validation

```python
VALID_TEMPLATE_PARAMS = {
    "guild": r"^[a-zA-Z0-9_-]+$",
    "channel": r"^[a-z0-9_-]+$",
    "category": r"^[a-zA-Z0-9_ -]+$",
    "type": r"^(brief|detailed|comprehensive)$",
    "role": r"^[a-z]+$"
}

def validate_template_value(param: str, value: str) -> bool:
    """Validate template parameter value against regex."""
    if param not in VALID_TEMPLATE_PARAMS:
        return False

    import re
    pattern = VALID_TEMPLATE_PARAMS[param]
    return bool(re.match(pattern, value))
```

---

## 8. Schema Versioning

### 8.1 Schema v1 Specification

**File:** `schema-version`
**Content:** `v1`

**Features:**
- Basic PATH file with template variables
- System and user prompt separation
- Category and channel-based routing
- Simple text file format for prompts

**Prompt File Format:**
```
Plain text prompt content.
No special formatting required.
Template variables supported: {{guild_name}}, {{channel_name}}, {{user_count}}
```

**Required Files:**
- `schema-version` - Contains "v1"
- `PATH` - Routing rules
- At least one prompt file in `system/default.md` or `user/default.md`

**Optional Files:**
- Any prompt files referenced in PATH
- README.md for documentation

### 8.2 Schema v2 Specification (Future)

**File:** `schema-version`
**Content:** `v2`

**Proposed Features:**
- YAML-based PATH file with advanced conditions
- Prompt composition (combine multiple prompt fragments)
- Per-prompt metadata (author, version, description)
- Conditional logic in PATH (if/else)
- Include directives for reusable prompt snippets

**Prompt File Format (YAML):**
```yaml
# system/detailed.yaml (v2 format)
metadata:
  version: "1.2.0"
  author: "guild_admin"
  description: "Detailed summary prompt for technical channels"

prompt: |
  You are an expert at creating comprehensive summaries...

  Template variables: {{guild_name}}, {{channel_name}}

parameters:
  temperature: 0.3
  max_tokens: 4000

includes:
  - "fragments/technical-terms.md"
  - "fragments/action-items.md"
```

### 8.3 Version Detection

```python
async def detect_schema_version(repo: GitHubRepository) -> SchemaVersion:
    """
    Detect schema version from repository.

    Steps:
    1. Fetch schema-version file from repo root
    2. Parse content (strip whitespace)
    3. Validate against known versions
    4. Default to v1 if missing
    """
    try:
        content = await repo.fetch_file("schema-version")
        version_str = content.strip().lower()

        if version_str == "v1":
            return SchemaVersion.V1
        elif version_str == "v2":
            return SchemaVersion.V2
        else:
            logger.warning(f"Unknown schema version: {version_str}, defaulting to v1")
            return SchemaVersion.V1

    except FileNotFoundError:
        logger.warning("No schema-version file found, defaulting to v1")
        return SchemaVersion.V1
```

### 8.4 Migration Path (v1 → v2)

When v2 is introduced, users can migrate incrementally:

1. **Add v2 files alongside v1:** Repository can contain both formats
2. **Update schema-version:** Change file to `v2` when ready
3. **Bot supports both:** Bot reads v1 or v2 based on schema-version
4. **Gradual migration:** Convert prompts one at a time
5. **Validation tool:** CLI tool to validate v2 format before deployment

---

## 9. Implementation Components

### 9.1 Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Command Handler Layer                  │
│  (/prompt config set/view/clear/test, /prompt cache)   │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│           ExternalPromptManager (Orchestrator)          │
│  - Guild config management                              │
│  - Prompt selection logic                               │
│  - Fallback coordination                                │
└─────────┬───────────────┬───────────────┬───────────────┘
          │               │               │
┌─────────▼─────┐ ┌───────▼──────┐ ┌──────▼─────────┐
│ GitHub Fetcher│ │ Prompt Cache │ │ PATH Parser    │
│ - API client  │ │ - Memory LRU │ │ - Pattern match│
│ - Auth mgmt   │ │ - DB persist │ │ - Resolution   │
│ - Rate limit  │ │ - TTL mgmt   │ │ - Validation   │
└───────────────┘ └──────────────┘ └────────────────┘
          │               │               │
┌─────────▼───────────────▼───────────────▼─────────────┐
│              Existing PromptBuilder                    │
│  (Modified to accept external prompts)                 │
└────────────────────────────────────────────────────────┘
```

### 9.2 Key Classes

#### 9.2.1 ExternalPromptManager

```python
class ExternalPromptManager:
    """
    Main orchestrator for external prompt system.
    Coordinates fetching, caching, and fallback logic.
    """

    def __init__(
        self,
        github_fetcher: GitHubPromptFetcher,
        prompt_cache: PromptCache,
        path_parser: PathParser,
        config_repository: PromptConfigRepository
    ):
        self.github_fetcher = github_fetcher
        self.prompt_cache = prompt_cache
        self.path_parser = path_parser
        self.config_repository = config_repository

    async def get_prompt(
        self,
        guild_id: str,
        prompt_type: str,  # "system" or "user"
        context: Dict[str, str]
    ) -> str:
        """
        Get appropriate prompt for given context.

        Flow:
        1. Check if guild has external config
        2. If not, return default prompt
        3. If yes, try cache
        4. If cache miss, fetch from GitHub
        5. Parse PATH and select appropriate file
        6. Return prompt content with fallback
        """
        pass

    async def set_repository(
        self,
        guild_id: str,
        repository_url: str,
        branch: str = "main",
        user_id: str = None
    ) -> ConfigResult:
        """Configure external repository for guild."""
        pass

    async def test_repository(
        self,
        guild_id: str
    ) -> TestResult:
        """Test repository connectivity and validate schema."""
        pass

    async def refresh_cache(
        self,
        guild_id: str
    ) -> RefreshResult:
        """Force cache refresh for guild."""
        pass
```

#### 9.2.2 GitHubPromptFetcher

```python
class GitHubPromptFetcher:
    """
    Handles GitHub API interactions for fetching prompt files.
    """

    def __init__(self, github_config: GitHubConfig):
        self.config = github_config
        self.client = httpx.AsyncClient(timeout=github_config.timeout_seconds)
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

    async def fetch_file(
        self,
        repository_url: str,
        file_path: str,
        branch: str = "main"
    ) -> str:
        """
        Fetch single file from repository.

        Returns:
            File content as string

        Raises:
            GitHubFetchError: On any failure
        """
        pass

    async def fetch_multiple_files(
        self,
        repository_url: str,
        file_paths: List[str],
        branch: str = "main"
    ) -> Dict[str, str]:
        """
        Fetch multiple files concurrently.

        Returns:
            Dict mapping file_path -> content
        """
        pass

    async def check_connectivity(
        self,
        repository_url: str
    ) -> bool:
        """Test if repository is accessible."""
        pass
```

#### 9.2.3 PromptCache

```python
class PromptCache:
    """
    Multi-tier caching for prompts (memory + database).
    """

    def __init__(
        self,
        memory_cache: LRUCache,
        db: DatabaseConnection,
        default_ttl_minutes: int = 15
    ):
        self.memory_cache = memory_cache
        self.db = db
        self.default_ttl = timedelta(minutes=default_ttl_minutes)

    async def get(
        self,
        guild_id: str,
        file_path: str,
        schema_version: str
    ) -> Optional[str]:
        """
        Get cached prompt.

        Flow:
        1. Check memory cache
        2. If miss, check database
        3. If found in DB, populate memory cache
        4. Check expiry
        5. Return content or None
        """
        pass

    async def set(
        self,
        guild_id: str,
        file_path: str,
        content: str,
        schema_version: str,
        ttl: Optional[timedelta] = None
    ):
        """Store prompt in cache."""
        pass

    async def invalidate_guild(self, guild_id: str):
        """Clear all cached prompts for guild."""
        pass

    async def get_stats(self, guild_id: str) -> CacheStats:
        """Get cache statistics."""
        pass
```

#### 9.2.4 PathParser

```python
class PathParser:
    """
    Parses PATH files and resolves patterns to file paths.
    """

    def parse_path_file(self, content: str) -> List[PromptPathPattern]:
        """
        Parse PATH file content into patterns.

        Returns:
            List of patterns sorted by priority
        """
        pass

    def resolve_prompt_path(
        self,
        patterns: List[PromptPathPattern],
        context: Dict[str, str]
    ) -> Optional[str]:
        """
        Resolve context to specific prompt file path.

        Returns:
            File path or None if no match
        """
        pass

    def validate_pattern(self, pattern: str) -> ValidationResult:
        """Validate pattern syntax."""
        pass
```

### 9.3 Integration with Existing Code

#### Modify: `src/summarization/prompt_builder.py`

```python
class PromptBuilder:
    """Builds optimized prompts for Claude API summarization."""

    def __init__(self, external_prompt_manager: Optional[ExternalPromptManager] = None):
        # Existing code...
        self.external_prompt_manager = external_prompt_manager
        self.system_prompts = {
            # Existing default prompts...
        }

    async def build_system_prompt(
        self,
        options: SummaryOptions,
        guild_id: Optional[str] = None,
        context: Optional[Dict[str, str]] = None
    ) -> str:
        """Build system prompt, checking for external overrides."""

        # Try external prompt first
        if self.external_prompt_manager and guild_id:
            try:
                external_prompt = await self.external_prompt_manager.get_prompt(
                    guild_id=guild_id,
                    prompt_type="system",
                    context=context or {}
                )
                if external_prompt:
                    logger.info(f"Using external system prompt for guild {guild_id}")
                    return external_prompt
            except Exception as e:
                logger.warning(f"Failed to fetch external prompt, using default: {e}")

        # Fall back to default prompt
        base_prompt = self.system_prompts[options.summary_length]
        # ... existing code ...
        return base_prompt
```

---

## 10. Configuration Workflow

### 10.1 Admin Configuration Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Admin runs: /prompt config set <repo_url>           │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 2. Bot validates repository URL format                 │
│    - Check URL format                                   │
│    - Extract owner/repo                                 │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ 3. Bot tests GitHub connectivity                        │
│    - Attempt to fetch schema-version file              │
│    - Verify authentication                              │
│    - Check repository accessibility                     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ├─── [Test Failed] ───┐
                  │                      │
                  │    ┌─────────────────▼─────────────┐
                  │    │ Return error to admin:        │
                  │    │ "Cannot access repository.    │
                  │    │  Please verify URL and        │
                  │    │  repository permissions."     │
                  │    └───────────────────────────────┘
                  │
                  └─── [Test Passed] ───┐
                                         │
               ┌─────────────────────────▼─────────────────┐
               │ 4. Bot fetches and validates schema      │
               │    - Download schema-version file        │
               │    - Parse and validate version           │
               │    - Fetch PATH file                      │
               │    - Validate PATH syntax                 │
               └─────────────────┬─────────────────────────┘
                                 │
               ┌─────────────────▼─────────────────────────┐
               │ 5. Bot saves configuration                │
               │    - Insert/update guild_prompt_config    │
               │    - Clear existing cache for guild       │
               │    - Log configuration change             │
               └─────────────────┬─────────────────────────┘
                                 │
               ┌─────────────────▼─────────────────────────┐
               │ 6. Bot returns success message            │
               │    "✅ Repository configured successfully! │
               │     Schema: v1                            │
               │     Prompts will be fetched on next use." │
               └───────────────────────────────────────────┘
```

### 10.2 Prompt Fetch Flow

```
┌─────────────────────────────────────────────────────────┐
│ User runs: /summarize                                   │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ Bot needs system prompt for guild_id                    │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│ Check if guild has external config                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ├─── [No config] ─────────┐
                  │                          │
                  │          ┌───────────────▼─────────────┐
                  │          │ Use default in-code prompt  │
                  │          └─────────────────────────────┘
                  │
                  └─── [Has config] ────┐
                                         │
               ┌─────────────────────────▼─────────────────┐
               │ Build context dict:                       │
               │   - guild: "MyGuild"                      │
               │   - channel: "general"                    │
               │   - category: "support"                   │
               │   - type: "brief"                         │
               └─────────────────┬─────────────────────────┘
                                 │
               ┌─────────────────▼─────────────────────────┐
               │ Check memory cache                        │
               └─────────────────┬─────────────────────────┘
                                 │
                  ┌──────────────┼───────────────┐
                  │              │               │
         [Cache Hit]    [Cache Miss]    [Cache Expired]
                  │              │               │
                  │              │               │
      ┌───────────▼────┐  ┌──────▼──────────────▼──────┐
      │ Return cached  │  │ Fetch from GitHub:          │
      │ prompt         │  │ 1. Get PATH patterns        │
      └────────────────┘  │ 2. Resolve to file path     │
                          │ 3. Fetch file content       │
                          │ 4. Validate content         │
                          │ 5. Cache result             │
                          └──────┬──────────────────────┘
                                 │
                  ┌──────────────┼───────────────┐
                  │              │               │
          [Fetch Success]  [Fetch Failed]  [Partial Fetch]
                  │              │               │
                  │              │               │
      ┌───────────▼────┐  ┌──────▼───────┐  ┌───▼────────┐
      │ Return external│  │ Check DB     │  │ Use fetched│
      │ prompt         │  │ cache        │  │ files +    │
      └────────────────┘  └──────┬───────┘  │ defaults   │
                                 │          └────────────┘
                          ┌──────▼────────┐
                          │ If DB cached: │
                          │   Return it   │
                          │ Else:         │
                          │   Use default │
                          └───────────────┘
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

#### Test: GitHub Fetcher
```python
# tests/test_github_fetcher.py

async def test_fetch_file_success():
    """Test successful file fetch from GitHub."""
    pass

async def test_fetch_file_not_found():
    """Test handling of 404 errors."""
    pass

async def test_fetch_file_rate_limit():
    """Test rate limit handling with retry."""
    pass

async def test_fetch_file_timeout():
    """Test timeout handling."""
    pass

async def test_fetch_file_too_large():
    """Test rejection of oversized files."""
    pass
```

#### Test: PATH Parser
```python
# tests/test_path_parser.py

def test_parse_simple_path():
    """Test parsing basic PATH file."""
    pass

def test_parse_with_comments():
    """Test ignoring comments and empty lines."""
    pass

def test_pattern_priority_calculation():
    """Test priority sorting of patterns."""
    pass

def test_resolve_specific_pattern():
    """Test resolving to specific file."""
    pass

def test_resolve_with_fallback():
    """Test fallback when no pattern matches."""
    pass

def test_invalid_template_param():
    """Test handling of invalid template parameters."""
    pass
```

#### Test: Prompt Cache
```python
# tests/test_prompt_cache.py

async def test_cache_set_and_get():
    """Test basic cache operations."""
    pass

async def test_cache_expiry():
    """Test TTL expiration."""
    pass

async def test_cache_invalidation():
    """Test cache clearing."""
    pass

async def test_memory_and_db_sync():
    """Test two-tier cache synchronization."""
    pass
```

### 11.2 Integration Tests

#### Test: End-to-End Configuration
```python
# tests/integration/test_external_prompts.py

async def test_full_configuration_flow(discord_bot, test_repository):
    """
    Test complete flow from configuration to usage.

    Steps:
    1. Configure repository for test guild
    2. Trigger summarization command
    3. Verify external prompt was used
    4. Check cache was populated
    5. Verify fallback on failure
    """
    pass

async def test_multi_guild_isolation(discord_bot):
    """
    Test that different guilds have isolated configurations.
    """
    pass
```

#### Test: Fallback Scenarios
```python
async def test_fallback_on_github_outage(discord_bot, mock_github_unavailable):
    """Test fallback to default prompts when GitHub is down."""
    pass

async def test_fallback_on_invalid_schema(discord_bot, test_repo_invalid_schema):
    """Test fallback when schema is invalid."""
    pass
```

### 11.3 Performance Tests

```python
# tests/performance/test_prompt_performance.py

async def test_cache_hit_latency():
    """Verify cache hits are <5ms."""
    pass

async def test_concurrent_fetches():
    """Test handling of 50 concurrent prompt requests."""
    pass

async def test_memory_usage_at_scale():
    """Verify memory usage with 1000 cached prompts."""
    pass
```

### 11.4 Security Tests

```python
# tests/security/test_prompt_security.py

async def test_template_injection_prevention():
    """Test prevention of template variable injection."""
    pass

async def test_suspicious_content_detection():
    """Test rejection of prompts with suspicious patterns."""
    pass

async def test_token_not_in_logs():
    """Verify GitHub tokens never appear in logs."""
    pass
```

---

## 12. Migration and Rollout

### 12.1 Phase 1: Infrastructure (Week 1-2)

**Goals:**
- Implement core components without breaking existing functionality
- Add database tables and migrations
- Implement GitHub fetcher with error handling

**Tasks:**
1. Create database schema and migrations
2. Implement `GitHubPromptFetcher` class
3. Implement `PromptCache` with memory and DB tiers
4. Implement `PathParser` for v1 schema
5. Add configuration commands (set/view/clear/test)
6. Write unit tests for all components

**Success Criteria:**
- All tests pass
- No impact on existing summarization functionality
- Configuration commands work in test environment

### 12.2 Phase 2: Integration (Week 3)

**Goals:**
- Integrate external prompts into summarization flow
- Add fallback mechanisms
- Test end-to-end flows

**Tasks:**
1. Modify `PromptBuilder` to support external prompts
2. Implement `ExternalPromptManager` orchestration
3. Add comprehensive error handling and fallbacks
4. Add monitoring and logging
5. Write integration tests
6. Create template repository with examples

**Success Criteria:**
- External prompts work for configured guilds
- Unconfigured guilds use defaults unchanged
- All fallback scenarios tested

### 12.3 Phase 3: Beta Testing (Week 4)

**Goals:**
- Test with real guilds
- Gather feedback
- Fix bugs and optimize performance

**Tasks:**
1. Deploy to staging environment
2. Invite 5-10 friendly guilds to beta test
3. Monitor error rates and performance
4. Collect user feedback
5. Create user documentation
6. Fix identified bugs

**Success Criteria:**
- Zero breaking changes to production users
- Beta testers successfully configure repositories
- Cache hit rate >80%
- GitHub fetch latency <1s (p95)

### 12.4 Phase 4: Production Rollout (Week 5)

**Goals:**
- Deploy to production
- Monitor closely
- Support early adopters

**Tasks:**
1. Deploy to production environment
2. Announce feature in bot update channel
3. Publish documentation and examples
4. Monitor metrics dashboards
5. Provide support to early adopters
6. Create video tutorial

**Success Criteria:**
- No incidents or rollbacks
- 95% of external prompt requests succeed
- User satisfaction survey >4/5 stars

---

## 13. Monitoring and Observability

### 13.1 Metrics to Track

```python
# Prometheus-style metrics

# Request metrics
prompt_fetch_total = Counter(
    "prompt_fetch_total",
    "Total number of prompt fetch attempts",
    ["guild_id", "status"]  # status: success, failed, cached
)

prompt_fetch_duration_seconds = Histogram(
    "prompt_fetch_duration_seconds",
    "Time to fetch prompt from GitHub",
    ["guild_id"]
)

# Cache metrics
prompt_cache_hits_total = Counter(
    "prompt_cache_hits_total",
    "Total cache hits",
    ["guild_id", "tier"]  # tier: memory, db
)

prompt_cache_misses_total = Counter(
    "prompt_cache_misses_total",
    "Total cache misses",
    ["guild_id"]
)

prompt_cache_size_bytes = Gauge(
    "prompt_cache_size_bytes",
    "Total size of cached prompts",
    ["tier"]
)

# Error metrics
github_api_errors_total = Counter(
    "github_api_errors_total",
    "Total GitHub API errors",
    ["error_type"]  # 404, 403, 429, timeout, etc.
)

prompt_fallback_total = Counter(
    "prompt_fallback_total",
    "Total fallbacks to default prompts",
    ["guild_id", "reason"]
)

# Configuration metrics
external_prompt_configs_total = Gauge(
    "external_prompt_configs_total",
    "Number of guilds with external prompts configured"
)
```

### 13.2 Logging Strategy

```python
import structlog

logger = structlog.get_logger()

# Example log entries

# Successful fetch
logger.info(
    "external_prompt_fetched",
    guild_id=guild_id,
    repository_url=repo_url,
    file_path=file_path,
    duration_ms=duration,
    source="github"
)

# Cache hit
logger.debug(
    "prompt_cache_hit",
    guild_id=guild_id,
    file_path=file_path,
    tier="memory",
    age_seconds=age
)

# Fallback
logger.warning(
    "prompt_fallback_used",
    guild_id=guild_id,
    reason="github_timeout",
    repository_url=repo_url,
    fallback_type="default"
)

# Configuration change
logger.info(
    "prompt_config_updated",
    guild_id=guild_id,
    repository_url=repo_url,
    changed_by=user_id,
    action="set"
)

# Security warning
logger.warning(
    "suspicious_prompt_rejected",
    guild_id=guild_id,
    repository_url=repo_url,
    pattern_matched="eval(",
    file_path=file_path
)
```

### 13.3 Alerts

```yaml
# alerts.yaml

groups:
  - name: external_prompts
    rules:
      - alert: HighPromptFetchFailureRate
        expr: |
          rate(prompt_fetch_total{status="failed"}[5m])
          / rate(prompt_fetch_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High failure rate for external prompt fetches"
          description: "{{ $value | humanizePercentage }} of prompt fetches are failing"

      - alert: GitHubAPIRateLimitExceeded
        expr: github_api_errors_total{error_type="429"} > 10
        for: 1m
        annotations:
          summary: "GitHub API rate limit exceeded"
          description: "Consider implementing more aggressive caching"

      - alert: PromptCacheSizeExceeded
        expr: prompt_cache_size_bytes{tier="memory"} > 100000000  # 100MB
        for: 5m
        annotations:
          summary: "Prompt cache exceeding memory limit"
          description: "Cache size: {{ $value | humanize1024 }}B"

      - alert: FrequentFallbacksDetected
        expr: rate(prompt_fallback_total[10m]) > 5
        for: 5m
        annotations:
          summary: "Frequent fallbacks to default prompts"
          description: "Investigate GitHub connectivity or configuration issues"
```

---

## 14. Security Considerations

### 14.1 GitHub Token Security

**Requirements:**
- Tokens encrypted at rest using AES-256
- Tokens never logged or exposed in error messages
- Tokens stored in dedicated secrets table
- Support for token rotation without downtime
- Minimum required permissions: `repo:read` (or `public_repo` for public repos)

**Implementation:**
```python
class SecureTokenStorage:
    """Handles encrypted storage of GitHub tokens."""

    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)

    async def store_token(self, guild_id: str, token: str) -> str:
        """
        Store encrypted token and return token_id.

        Returns:
            token_id: Unique identifier for retrieving token
        """
        encrypted = self.cipher.encrypt(token.encode())
        token_id = generate_id()

        await db.execute(
            "INSERT INTO github_tokens (token_id, guild_id, encrypted_token) VALUES (?, ?, ?)",
            (token_id, guild_id, encrypted)
        )

        return token_id

    async def retrieve_token(self, token_id: str) -> str:
        """Retrieve and decrypt token."""
        result = await db.fetch_one(
            "SELECT encrypted_token FROM github_tokens WHERE token_id = ?",
            (token_id,)
        )

        if not result:
            raise TokenNotFoundError(token_id)

        return self.cipher.decrypt(result["encrypted_token"]).decode()
```

### 14.2 Content Validation

```python
import re

class PromptContentValidator:
    """Validates fetched prompt content for security."""

    SUSPICIOUS_PATTERNS = [
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"<script[^>]*>",
        r"\{\{\s*[^}]*\s*exec",
        r"\$\{[^}]*exec",
    ]

    MAX_SIZE_KB = 50

    def validate(self, content: str, file_path: str) -> ValidationResult:
        """
        Validate prompt content.

        Returns:
            ValidationResult with is_valid and error_message
        """
        # Check size
        if len(content.encode('utf-8')) > self.MAX_SIZE_KB * 1024:
            return ValidationResult(
                is_valid=False,
                error_message=f"File too large: {file_path}"
            )

        # Check encoding
        try:
            content.encode('utf-8')
        except UnicodeEncodeError:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid UTF-8 encoding: {file_path}"
            )

        # Check for suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Suspicious pattern detected in {file_path}: {pattern}",
                    security_issue=True
                )

        return ValidationResult(is_valid=True)
```

### 14.3 Access Control

```python
async def check_prompt_config_permission(
    interaction: discord.Interaction,
    required_permission: str = "ADMINISTRATOR"
) -> bool:
    """
    Check if user has permission to configure external prompts.

    Permissions hierarchy:
    1. Server owner: Always allowed
    2. ADMINISTRATOR permission: Allowed
    3. Custom bot role (configured): Allowed
    4. Everyone else: Denied
    """
    # Server owner
    if interaction.user.id == interaction.guild.owner_id:
        return True

    # Check for administrator permission
    if interaction.user.guild_permissions.administrator:
        return True

    # Check for custom bot management role
    bot_manager_role = await get_bot_manager_role(interaction.guild.id)
    if bot_manager_role and bot_manager_role in [r.id for r in interaction.user.roles]:
        return True

    return False
```

---

## 15. Documentation Requirements

### 15.1 User Documentation

#### 15.1.1 Quick Start Guide

**File:** `/docs/external-prompts-quickstart.md`

**Contents:**
1. What are external prompts?
2. Why use them?
3. Prerequisites (GitHub account, repository)
4. Step-by-step setup
5. Testing your configuration
6. Troubleshooting common issues

#### 15.1.2 Template Repository

**Repository:** `discord-summary-bot/prompt-templates`

**Structure:**
```
prompt-templates/
├── README.md                    # Comprehensive guide
├── schema-version               # v1
├── PATH.example                 # Commented example
├── PATH                         # Working example
├── system/
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
├── user/
│   └── default.md
├── examples/
│   ├── technical-community/    # Example for dev server
│   ├── support-server/         # Example for support
│   └── gaming-community/       # Example for gaming
└── docs/
    ├── path-syntax.md
    ├── template-variables.md
    └── best-practices.md
```

#### 15.1.3 Command Reference

**File:** `/docs/slash-commands.md` (update)

Add section:
```markdown
## External Prompt Configuration

### /prompt config set
Configure external prompt repository for this server.

**Usage:** `/prompt config set <repository_url> [branch]`

**Parameters:**
- `repository_url`: GitHub repository URL (e.g., `https://github.com/yourname/prompts`)
- `branch`: Git branch to use (optional, default: `main`)

**Permissions:** Administrator or Bot Manager role

**Example:**
```
/prompt config set https://github.com/myorg/our-prompts
/prompt config set https://github.com/myorg/our-prompts dev
```

### /prompt config view
View current prompt configuration.

**Usage:** `/prompt config view`

**Output:**
- Repository URL
- Branch
- Schema version
- Last fetch status
- Cache statistics

### /prompt config clear
Remove external prompt configuration and return to defaults.

**Usage:** `/prompt config clear`

**Permissions:** Administrator or Bot Manager role

### /prompt config test
Test repository connectivity and configuration.

**Usage:** `/prompt config test`

**Checks:**
- Repository accessibility
- Schema version validity
- PATH file syntax
- Required files present

### /prompt cache refresh
Force immediate cache refresh.

**Usage:** `/prompt cache refresh`

**Permissions:** Administrator or Bot Manager role

### /prompt cache stats
View cache statistics.

**Usage:** `/prompt cache stats`

**Output:**
- Total cached prompts
- Cache hit rate
- Memory usage
- Last refresh time
```

### 15.2 Developer Documentation

#### 15.2.1 Architecture Documentation

**File:** `/docs/architecture/external-prompts.md`

**Contents:**
- Component diagram
- Data flow diagrams
- Class hierarchy
- Sequence diagrams for key operations
- Design decisions and rationale

#### 15.2.2 API Documentation

Auto-generated from docstrings using Sphinx.

#### 15.2.3 Schema Evolution Guide

**File:** `/docs/schema-evolution.md`

**Contents:**
- How to add new schema version
- Backward compatibility requirements
- Migration testing checklist
- Version detection logic

---

## 16. Success Metrics

### 16.1 Adoption Metrics

- **Configuration Rate:** % of active guilds with external prompts configured
  - Target: 15% within 3 months
- **Active Repositories:** Number of unique repositories in use
  - Target: 50+ repositories after 6 months
- **Retention:** % of configured guilds still active after 30 days
  - Target: >80%

### 16.2 Performance Metrics

- **Cache Hit Rate:** % of prompt requests served from cache
  - Target: >85%
- **Fetch Latency (p95):** Time to fetch prompt from GitHub
  - Target: <1.5s
- **Fallback Rate:** % of requests falling back to default prompts
  - Target: <5%

### 16.3 Reliability Metrics

- **Availability:** % of time external prompt system is functional
  - Target: 99.5%
- **Error Rate:** % of prompt fetches that fail
  - Target: <2%
- **Zero Impact:** No increase in summarization failures for unconfigured guilds
  - Target: 0 incidents

### 16.4 User Satisfaction

- **Admin Satisfaction:** Survey rating for configuration experience
  - Target: >4.2/5 stars
- **Support Tickets:** Number of external prompt related tickets
  - Target: <10 per month
- **Documentation Clarity:** % of users who can configure without help
  - Target: >70%

---

## 17. Risks and Mitigations

### 17.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GitHub API rate limits exceeded | High | Medium | Aggressive caching, exponential backoff, consider GitHub App for higher limits |
| Cache invalidation bugs | Medium | Low | Comprehensive testing, cache versioning, manual refresh command |
| Schema migration breaks old configs | High | Low | Maintain v1 support indefinitely, extensive backward compatibility tests |
| External prompts inject malicious content | High | Very Low | Content validation, pattern blacklist, size limits, security audits |
| Database performance degradation | Medium | Low | Indexed queries, cache eviction policy, monitoring |

### 17.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users misconfigure repositories | Low | High | Clear documentation, `/prompt config test` command, error messages with guidance |
| GitHub outages affect bot availability | Medium | Low | Robust fallback to cached/default prompts, circuit breaker pattern |
| Support burden from feature complexity | Medium | Medium | Comprehensive documentation, template repository, troubleshooting guide |
| Token management complexity | Medium | Low | Secure by default, clear rotation procedure, audit logging |

### 17.3 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Low adoption rate | Low | Medium | User education, examples for common use cases, showcase successful configs |
| Feature bloat / maintenance burden | Medium | Medium | Keep scope minimal for v1, automated testing, monitoring for issues |
| Increased cloud costs (storage) | Low | Low | Cache size limits, LRU eviction, monitor storage metrics |

---

## 18. Future Enhancements (Post-v1)

### 18.1 Planned Features for v2

1. **Prompt Composition**
   - Combine multiple prompt fragments
   - Include directives for reusable components
   - Conditional logic in PATH file

2. **Advanced Template Variables**
   - User roles and permissions
   - Channel topics and descriptions
   - Custom guild metadata

3. **Prompt Analytics**
   - Track which prompts produce best summaries
   - A/B testing for prompt variations
   - User feedback integration

4. **Web UI for Configuration**
   - Browser-based repository configuration
   - Visual PATH editor
   - Prompt preview and testing

5. **Multi-Repository Support**
   - Inherit from base repository + guild overrides
   - Shared prompt libraries
   - Versioned prompt packages

### 18.2 Potential Integrations

- **GitLab/Bitbucket Support:** Extend beyond GitHub
- **S3/Cloud Storage:** Alternative to Git repositories
- **Prompt Marketplace:** Community-shared prompt templates
- **Version Control UI:** View prompt history, rollback changes
- **Prompt Templates SDK:** Library for programmatic prompt generation

---

## 19. Appendices

### Appendix A: Example Configurations

#### A.1 Technical Community Server

**PATH file:**
```
# Technical community prompts
# Emphasize code, technical terms, and precise language

categories/development/{type}/system.md
categories/development/{type}/user.md

channels/code-review/{type}/system.md
channels/help/{type}/system.md

{type}/system-technical.md
{type}/user-technical.md

system/default.md
```

**system/brief-technical.md:**
```
You are an expert at summarizing technical discussions in Discord servers for software developers.

For BRIEF technical summaries:
- Focus on code changes, technical decisions, and solutions
- Extract specific technical terms with accurate definitions
- Include code snippets or file names when relevant
- Prioritize action items related to implementation
- Keep explanations precise and concise

Response Format: [JSON structure as defined in base spec]

Keep summary focused, technical, and under 200 words.
```

#### A.2 Support Server

**PATH file:**
```
# Customer support server prompts
# Emphasize user issues, resolutions, and follow-ups

categories/support/{type}/system.md
channels/bug-reports/{type}/system.md
channels/feature-requests/{type}/system.md

{type}/system-support.md
system/default.md
```

**system/brief-support.md:**
```
You are an expert at summarizing customer support conversations in Discord.

For BRIEF support summaries:
- Identify user issues and questions
- Highlight solutions and resolutions provided
- Track unresolved issues requiring follow-up
- Note any escalations to development team
- Keep language clear and customer-focused

Response Format: [JSON structure as defined in base spec]

Focus on outcomes and next steps. Under 200 words.
```

#### A.3 Gaming Community

**PATH file:**
```
# Gaming community prompts
# Casual tone, events, and player interactions

channels/events/{type}/system.md
channels/lfg/{type}/system.md

{type}/system-casual.md
system/default.md
```

### Appendix B: PATH Syntax Reference

#### B.1 Pattern Syntax

```
# Comments (ignored)

# Literal paths
system/brief.md

# Template variables
{type}/system.md
categories/{category}/{type}/system.md

# Multiple variables
{category}/{channel}/{type}/user.md

# Deep nesting
categories/{category}/channels/{channel}/types/{type}/system.md
```

#### B.2 Supported Template Variables (v1)

| Variable | Description | Example Values | Source |
|----------|-------------|----------------|--------|
| `{guild}` | Guild/server name or ID | `"MyServer"`, `"123456789"` | Discord guild metadata |
| `{channel}` | Channel name (without #) | `"general"`, `"support"` | Discord channel metadata |
| `{category}` | Channel category name | `"Support"`, `"Development"` | Discord category metadata |
| `{type}` | Summary type/length | `"brief"`, `"detailed"`, `"comprehensive"` | Command parameter |
| `{role}` | User's highest role | `"admin"`, `"moderator"`, `"member"` | Discord user roles |

#### B.3 Pattern Priority Examples

```
# Higher priority (more specific)
categories/support/channels/help/brief/system.md       # Priority: 1
categories/support/channels/{channel}/{type}/system.md # Priority: 5
categories/{category}/{type}/system.md                 # Priority: 10
{type}/system.md                                       # Priority: 20
system/default.md                                      # Priority: 100

# Resolution order:
# 1. Most specific match (fewest wildcards, longest path)
# 2. First matching pattern in file (top to bottom)
# 3. Fallback to default
```

### Appendix C: Glossary

- **External Prompt:** Custom summarization prompt stored in an external repository
- **Guild:** Discord server
- **PATH File:** Configuration file defining prompt routing rules
- **Schema Version:** Version of the prompt repository format (v1, v2, etc.)
- **Template Variable:** Placeholder in PATH patterns (e.g., `{type}`, `{channel}`)
- **Fallback:** Using default prompts when external fetch fails
- **Cache Hit:** Successfully retrieving prompt from cache without fetching
- **Cache Miss:** Prompt not in cache, requiring fetch from GitHub
- **TTL (Time To Live):** Duration before cached prompt expires
- **Rate Limit:** GitHub API request limit (typically 5,000/hour for authenticated)
- **Circuit Breaker:** Pattern to prevent cascading failures by stopping requests to failing service

---

## 20. Approval and Sign-off

### Document Reviewers

- [ ] **Lead Developer:** [Name] - Technical accuracy
- [ ] **Product Manager:** [Name] - Requirements completeness
- [ ] **DevOps Engineer:** [Name] - Operational feasibility
- [ ] **Security Engineer:** [Name] - Security review
- [ ] **Technical Writer:** [Name] - Documentation quality

### Approval Status

- **Status:** Draft
- **Version:** 1.0.0
- **Last Updated:** 2026-01-14
- **Next Review:** 2026-02-01

### Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-14 | Claude Sonnet 4.5 | Initial specification |

---

**End of Specification**
