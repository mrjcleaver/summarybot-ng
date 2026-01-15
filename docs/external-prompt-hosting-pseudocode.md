# External Prompt Hosting System - Detailed Pseudocode

**Version:** 1.0.0
**Date:** 2026-01-14
**Phase:** SPARC Pseudocode
**Status:** Complete

---

## Table of Contents

1. [Prompt Resolution Algorithm](#1-prompt-resolution-algorithm)
2. [GitHub Repository Client](#2-github-repository-client)
3. [Cache Management](#3-cache-management)
4. [PATH File Parser](#4-path-file-parser)
5. [Fallback Chain Executor](#5-fallback-chain-executor)
6. [Schema Validator](#6-schema-validator)
7. [Supporting Data Structures](#7-supporting-data-structures)
8. [Error Types and Handling](#8-error-types-and-handling)
9. [Complexity Analysis](#9-complexity-analysis)

---

## 1. Prompt Resolution Algorithm

### 1.1 High-Level Overview

The prompt resolution algorithm is the main entry point for retrieving prompts. It coordinates cache checking, GitHub fetching, PATH parsing, and fallback logic.

```
FLOW:
User requests summary
  → resolve_prompt(guild_id, context)
    → Check if guild has external config
      → NO: Return default prompt (in-code)
      → YES: Continue to cache check
    → Check cache (memory → Redis → SQLite)
      → HIT: Return cached prompt
      → MISS: Fetch from GitHub
    → Parse PATH file and resolve file path
    → Fetch prompt file from GitHub
    → Validate content
    → Cache result
    → Return prompt
    ↓
  On any failure → Execute fallback chain
```

### 1.2 Main Entry Point Algorithm

```
ALGORITHM: ResolvePrompt
INPUT:
    guild_id (string) - Discord guild identifier
    context (PromptContext) - {
        channel_name: string,
        category_name: string,
        summary_type: string,  // "brief", "detailed", "comprehensive"
        prompt_type: string,   // "system" or "user"
        user_role: string      // highest role of user
    }
OUTPUT:
    prompt (string) - The resolved prompt text
    metadata (PromptMetadata) - Source information

DATA STRUCTURES:
    guildConfig: ExternalPromptConfig or null
    cacheKey: string
    promptContent: string
    fallbackChain: List<FallbackStrategy>

BEGIN
    // Step 1: Check if guild has external configuration
    guildConfig ← LoadGuildConfiguration(guild_id)

    IF guildConfig IS null OR NOT guildConfig.enabled THEN
        LOG("No external config for guild", guild_id, level=DEBUG)
        RETURN GetDefaultPrompt(context.summary_type, context.prompt_type)
    END IF

    // Step 2: Build cache key from context
    cacheKey ← BuildCacheKey(
        guild_id,
        guildConfig.schema_version,
        context.summary_type,
        context.prompt_type,
        context.channel_name,
        context.category_name
    )

    // Step 3: Try multi-level cache
    TRY
        cachedPrompt ← CheckMultiLevelCache(cacheKey)

        IF cachedPrompt IS NOT null THEN
            // Cache hit
            LOG("Cache hit", cache_key=cacheKey, tier=cachedPrompt.tier, level=DEBUG)
            IncrementMetric("prompt_cache_hits_total", tier=cachedPrompt.tier)
            UpdateAccessMetrics(cacheKey)

            RETURN {
                prompt: cachedPrompt.content,
                metadata: {
                    source: "cache",
                    tier: cachedPrompt.tier,
                    cached_at: cachedPrompt.cached_at,
                    guild_id: guild_id
                }
            }
        END IF

        LOG("Cache miss", cache_key=cacheKey, level=DEBUG)
        IncrementMetric("prompt_cache_misses_total", guild_id=guild_id)

    CATCH CacheError AS e
        LOG("Cache error, continuing to fetch", error=e, level=WARNING)
        // Continue to GitHub fetch even if cache fails
    END TRY

    // Step 4: Cache miss - fetch from GitHub
    TRY
        // Fetch PATH file to determine which prompt file to load
        pathFileContent ← FetchFromGitHub(
            repository_url=guildConfig.repository_url,
            file_path="PATH",
            branch=guildConfig.branch,
            timeout_seconds=5
        )

        // Parse PATH patterns
        pathPatterns ← ParsePathFile(pathFileContent)

        // Resolve context to specific file path
        resolvedFilePath ← ResolvePromptPath(pathPatterns, context)

        IF resolvedFilePath IS null THEN
            // No matching pattern, try default
            resolvedFilePath ← GetDefaultFilePath(context.prompt_type, context.summary_type)
        END IF

        // Fetch the actual prompt file
        startTime ← GetCurrentTime()
        promptContent ← FetchFromGitHub(
            repository_url=guildConfig.repository_url,
            file_path=resolvedFilePath,
            branch=guildConfig.branch,
            timeout_seconds=5
        )
        fetchDuration ← GetCurrentTime() - startTime

        // Validate content
        validationResult ← ValidatePromptContent(promptContent, resolvedFilePath)

        IF NOT validationResult.is_valid THEN
            THROW ValidationError(validationResult.error_message)
        END IF

        // Cache the result
        CachePrompt(
            cache_key=cacheKey,
            content=promptContent,
            guild_id=guild_id,
            file_path=resolvedFilePath,
            schema_version=guildConfig.schema_version,
            ttl_minutes=15
        )

        // Record metrics
        RecordHistogram("prompt_fetch_duration_seconds", fetchDuration)
        IncrementMetric("prompt_fetch_total", status="success", guild_id=guild_id)

        LOG("External prompt fetched",
            guild_id=guild_id,
            file_path=resolvedFilePath,
            duration_ms=fetchDuration * 1000,
            level=INFO)

        RETURN {
            prompt: promptContent,
            metadata: {
                source: "github",
                repository_url: guildConfig.repository_url,
                file_path: resolvedFilePath,
                fetch_duration_ms: fetchDuration * 1000,
                guild_id: guild_id
            }
        }

    CATCH GitHubError AS e
        LOG("GitHub fetch failed", error=e, guild_id=guild_id, level=WARNING)
        IncrementMetric("prompt_fetch_total", status="failed", guild_id=guild_id)
        IncrementMetric("github_api_errors_total", error_type=e.status_code)

        // Execute fallback chain
        fallbackPrompt ← ExecuteFallbackChain(
            guild_id=guild_id,
            cache_key=cacheKey,
            context=context,
            error=e
        )

        RETURN fallbackPrompt

    CATCH ValidationError AS e
        LOG("Prompt validation failed", error=e, guild_id=guild_id, level=WARNING)
        IncrementMetric("prompt_validation_failures_total", guild_id=guild_id)

        // Execute fallback chain
        fallbackPrompt ← ExecuteFallbackChain(
            guild_id=guild_id,
            cache_key=cacheKey,
            context=context,
            error=e
        )

        RETURN fallbackPrompt

    CATCH TimeoutError AS e
        LOG("GitHub fetch timeout", error=e, guild_id=guild_id, level=WARNING)
        IncrementMetric("github_api_errors_total", error_type="timeout")

        // Execute fallback chain
        fallbackPrompt ← ExecuteFallbackChain(
            guild_id=guild_id,
            cache_key=cacheKey,
            context=context,
            error=e
        )

        RETURN fallbackPrompt

    CATCH Exception AS e
        LOG("Unexpected error in prompt resolution",
            error=e,
            guild_id=guild_id,
            level=ERROR)
        IncrementMetric("prompt_resolution_errors_total", guild_id=guild_id)

        // Final fallback to default
        RETURN GetDefaultPrompt(context.summary_type, context.prompt_type)
    END TRY
END

COMPLEXITY ANALYSIS:
Time Complexity:
    - Best case (cache hit): O(1) - hash lookup in memory cache
    - Average case (GitHub fetch): O(n + m) where n = PATH patterns, m = prompt file size
    - Worst case (fallback chain): O(k) where k = number of fallback strategies

Space Complexity:
    - O(m) where m = size of prompt content
    - Cache storage bounded by eviction policy
```

### 1.3 Cache Key Generation

```
ALGORITHM: BuildCacheKey
INPUT:
    guild_id: string
    schema_version: string
    summary_type: string
    prompt_type: string
    channel_name: string (optional)
    category_name: string (optional)
OUTPUT:
    cache_key: string (256-bit hash)

BEGIN
    // Build deterministic string representation
    components ← [
        "prompt",                   // namespace
        guild_id,
        schema_version,
        prompt_type,                // "system" or "user"
        summary_type,               // "brief", "detailed", etc.
        category_name OR "none",
        channel_name OR "none"
    ]

    // Create canonical representation
    canonical ← JOIN(components, separator=":")

    // Hash to fixed-length key for efficient lookups
    // Using SHA-256 for collision resistance
    hash ← SHA256(canonical)
    cache_key ← HexEncode(hash)

    RETURN cache_key
END

EXAMPLE OUTPUT:
    Input: guild_id="123456", schema="v1", prompt_type="system",
           summary_type="brief", category="support", channel="help"
    Output: "a3f5b2c1e4d6f8a0b2c4e6f8a0b2c4e6f8a0b2c4e6f8a0b2c4e6f8a0b2c4"

COMPLEXITY:
    Time: O(n) where n = total length of input strings
    Space: O(1) - fixed 64-character hex string
```

### 1.4 Context Building

```
ALGORITHM: BuildPromptContext
INPUT:
    guild: DiscordGuild object
    channel: DiscordChannel object
    summary_options: SummaryOptions object
    user: DiscordUser object
OUTPUT:
    context: PromptContext

BEGIN
    context ← NEW PromptContext()

    // Extract channel information
    context.channel_name ← NormalizeChannelName(channel.name)

    // Extract category (if channel is in a category)
    IF channel.category IS NOT null THEN
        context.category_name ← NormalizeCategoryName(channel.category.name)
    ELSE
        context.category_name ← null
    END IF

    // Extract summary type from options
    context.summary_type ← summary_options.summary_length  // "brief", "detailed", etc.

    // Determine prompt type (always fetch both system and user)
    context.prompt_type ← "system"  // or "user" depending on what we're fetching

    // Extract user's highest role for role-based routing
    IF user.roles IS NOT empty THEN
        highest_role ← GetHighestRole(user.roles)
        context.user_role ← NormalizeRoleName(highest_role.name)
    ELSE
        context.user_role ← "member"  // default role
    END IF

    // Add guild identifier for {guild} template variable
    context.guild_id ← guild.id
    context.guild_name ← guild.name

    RETURN context
END

SUBROUTINE: NormalizeChannelName
INPUT: raw_name: string
OUTPUT: normalized: string
BEGIN
    // Remove # prefix if present
    normalized ← raw_name.TRIM("#")

    // Convert to lowercase
    normalized ← normalized.LOWERCASE()

    // Replace spaces with hyphens (Discord channel format)
    normalized ← normalized.REPLACE(" ", "-")

    // Remove invalid characters
    normalized ← REGEX_REPLACE(normalized, "[^a-z0-9-_]", "")

    RETURN normalized
END

SUBROUTINE: NormalizeCategoryName
INPUT: raw_name: string
OUTPUT: normalized: string
BEGIN
    // Trim whitespace
    normalized ← raw_name.TRIM()

    // Convert to lowercase for matching
    normalized ← normalized.LOWERCASE()

    // Preserve spaces (categories can have spaces)
    // Remove only truly invalid characters
    normalized ← REGEX_REPLACE(normalized, "[^a-z0-9 _-]", "")

    RETURN normalized
END

COMPLEXITY:
    Time: O(n) where n = length of channel/category names
    Space: O(n)
```

---

## 2. GitHub Repository Client

### 2.1 High-Level Architecture

```
GitHubPromptFetcher
    ├── Authentication Manager (handles tokens)
    ├── Rate Limiter (prevents API abuse)
    ├── HTTP Client (async requests)
    ├── Retry Logic (exponential backoff)
    └── Response Parser (decode and validate)
```

### 2.2 Main Fetch Algorithm

```
ALGORITHM: FetchFromGitHub
INPUT:
    repository_url: string  // "https://github.com/owner/repo"
    file_path: string       // "system/brief.md"
    branch: string          // "main"
    timeout_seconds: integer // 5
OUTPUT:
    content: string

DATA STRUCTURES:
    owner: string
    repo: string
    auth_token: string
    api_url: string
    response: HTTPResponse

BEGIN
    // Step 1: Parse repository URL
    TRY
        (owner, repo) ← ParseRepositoryURL(repository_url)
    CATCH InvalidURLError AS e
        THROW GitHubError("Invalid repository URL", status_code=400, details=e)
    END TRY

    // Step 2: Check rate limit before making request
    TRY
        RateLimitCheck(owner, repo)
    CATCH RateLimitExceeded AS e
        LOG("Rate limit exceeded", owner=owner, repo=repo, level=WARNING)
        THROW GitHubError("Rate limit exceeded", status_code=429, retry_after=e.retry_after)
    END TRY

    // Step 3: Get authentication token
    auth_token ← GetAuthToken()  // From environment or config

    // Step 4: Build GitHub API URL
    // Using Contents API: GET /repos/{owner}/{repo}/contents/{path}
    api_url ← BuildAPIURL(
        base="https://api.github.com",
        owner=owner,
        repo=repo,
        path=file_path,
        ref=branch
    )

    // Step 5: Make HTTP request with retry logic
    max_retries ← 3
    retry_count ← 0
    backoff_seconds ← 1

    WHILE retry_count < max_retries DO
        TRY
            LOG("Fetching from GitHub",
                url=api_url,
                retry=retry_count,
                level=DEBUG)

            headers ← {
                "Authorization": "Bearer " + auth_token,
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DiscordSummaryBot/1.0"
            }

            response ← HTTPClient.GET(
                url=api_url,
                headers=headers,
                timeout=timeout_seconds
            )

            // Step 6: Handle response status codes
            IF response.status_code == 200 THEN
                // Success - parse and decode content
                json_data ← ParseJSON(response.body)

                // GitHub returns file content base64-encoded
                IF json_data.encoding != "base64" THEN
                    THROW GitHubError("Unexpected encoding", status_code=500)
                END IF

                content ← Base64Decode(json_data.content)

                // Validate encoding is UTF-8
                TRY
                    content ← DecodeUTF8(content)
                CATCH EncodingError
                    THROW GitHubError("File is not valid UTF-8", status_code=400)
                END TRY

                // Update rate limit tracking
                UpdateRateLimitInfo(response.headers)

                LOG("Successfully fetched file",
                    file_path=file_path,
                    size_bytes=LENGTH(content),
                    level=DEBUG)

                RETURN content

            ELSE IF response.status_code == 404 THEN
                // File or repo not found
                THROW GitHubError(
                    "File not found: " + file_path,
                    status_code=404,
                    is_retryable=FALSE
                )

            ELSE IF response.status_code == 403 THEN
                // Forbidden - likely auth issue
                error_message ← ParseErrorMessage(response.body)

                IF "rate limit" IN error_message.LOWERCASE() THEN
                    retry_after ← response.headers.GET("X-RateLimit-Reset", 60)
                    THROW GitHubError(
                        "Rate limit exceeded",
                        status_code=429,
                        retry_after=retry_after,
                        is_retryable=TRUE
                    )
                ELSE
                    THROW GitHubError(
                        "Access forbidden: " + error_message,
                        status_code=403,
                        is_retryable=FALSE
                    )
                END IF

            ELSE IF response.status_code == 401 THEN
                // Unauthorized - bad token
                THROW GitHubError(
                    "Authentication failed - check GitHub token",
                    status_code=401,
                    is_retryable=FALSE
                )

            ELSE IF response.status_code >= 500 THEN
                // Server error - retry
                THROW GitHubError(
                    "GitHub server error",
                    status_code=response.status_code,
                    is_retryable=TRUE
                )

            ELSE
                // Unknown error
                THROW GitHubError(
                    "Unexpected status: " + response.status_code,
                    status_code=response.status_code,
                    is_retryable=FALSE
                )
            END IF

        CATCH NetworkError AS e
            // Network issue - retry
            LOG("Network error fetching file",
                error=e,
                retry=retry_count,
                level=WARNING)

            IF retry_count >= max_retries - 1 THEN
                THROW GitHubError("Network error after retries", status_code=0, details=e)
            END IF

        CATCH TimeoutError AS e
            // Timeout - retry with backoff
            LOG("Request timeout",
                timeout=timeout_seconds,
                retry=retry_count,
                level=WARNING)

            IF retry_count >= max_retries - 1 THEN
                THROW GitHubError("Timeout after retries", status_code=0, details=e)
            END IF

        CATCH GitHubError AS e
            // Re-throw GitHubError if not retryable
            IF NOT e.is_retryable THEN
                THROW e
            END IF

            IF retry_count >= max_retries - 1 THEN
                THROW e
            END IF
        END TRY

        // Exponential backoff before retry
        retry_count ← retry_count + 1
        SLEEP(backoff_seconds)
        backoff_seconds ← backoff_seconds * 2  // Double backoff each time
    END WHILE

    // Should never reach here (loop exits via RETURN or THROW)
    THROW GitHubError("Max retries exceeded", status_code=0)
END

COMPLEXITY ANALYSIS:
Time Complexity:
    - Best case: O(n) where n = file size (single successful request)
    - Average case: O(n)
    - Worst case: O(3n) with retries, still linear in file size

Space Complexity:
    - O(n) where n = file size (need to store entire file in memory)
    - Additional O(1) for headers and metadata
```

### 2.3 Batch Fetching Algorithm

```
ALGORITHM: FetchMultipleFiles
INPUT:
    repository_url: string
    file_paths: List<string>
    branch: string
    max_concurrent: integer = 5
OUTPUT:
    results: Map<file_path, content or error>

BEGIN
    results ← NEW Map()
    semaphore ← NEW Semaphore(max_concurrent)

    // Create async tasks for each file
    tasks ← []

    FOR EACH file_path IN file_paths DO
        task ← ASYNC BEGIN
            // Acquire semaphore to limit concurrency
            ACQUIRE semaphore

            TRY
                content ← FetchFromGitHub(
                    repository_url=repository_url,
                    file_path=file_path,
                    branch=branch,
                    timeout_seconds=5
                )
                results.SET(file_path, {success: TRUE, content: content})

            CATCH GitHubError AS e
                LOG("Failed to fetch file",
                    file_path=file_path,
                    error=e,
                    level=WARNING)
                results.SET(file_path, {success: FALSE, error: e})

            FINALLY
                RELEASE semaphore
            END TRY
        END ASYNC

        tasks.APPEND(task)
    END FOR

    // Wait for all tasks to complete
    AWAIT_ALL(tasks)

    RETURN results
END

COMPLEXITY:
    Time: O(n * m / c) where n = number of files, m = avg file size, c = concurrency
    Space: O(n * m) to store all file contents
```

### 2.4 Supporting Algorithms

```
ALGORITHM: ParseRepositoryURL
INPUT: url: string
OUTPUT: (owner: string, repo: string)

BEGIN
    // Support formats:
    // - https://github.com/owner/repo
    // - https://github.com/owner/repo.git
    // - git@github.com:owner/repo.git

    // Remove trailing .git
    url ← url.TRIM_SUFFIX(".git")

    // Extract from HTTPS URL
    IF url.STARTS_WITH("https://github.com/") THEN
        path ← url.SUBSTRING(19)  // Skip "https://github.com/"
        parts ← path.SPLIT("/")

        IF LENGTH(parts) < 2 THEN
            THROW InvalidURLError("Invalid repository URL format")
        END IF

        owner ← parts[0]
        repo ← parts[1]

        RETURN (owner, repo)
    END IF

    // Extract from SSH URL
    IF url.STARTS_WITH("git@github.com:") THEN
        path ← url.SUBSTRING(15)  // Skip "git@github.com:"
        parts ← path.SPLIT("/")

        IF LENGTH(parts) < 2 THEN
            THROW InvalidURLError("Invalid repository URL format")
        END IF

        owner ← parts[0]
        repo ← parts[1]

        RETURN (owner, repo)
    END IF

    THROW InvalidURLError("Unsupported repository URL format: " + url)
END

ALGORITHM: BuildAPIURL
INPUT:
    base: string
    owner: string
    repo: string
    path: string
    ref: string
OUTPUT:
    api_url: string

BEGIN
    // Encode path components for URL safety
    encoded_path ← URLEncode(path)
    encoded_ref ← URLEncode(ref)

    // Build URL: /repos/{owner}/{repo}/contents/{path}?ref={ref}
    api_url ← base + "/repos/" + owner + "/" + repo + "/contents/" + encoded_path

    IF ref IS NOT null AND ref != "" THEN
        api_url ← api_url + "?ref=" + encoded_ref
    END IF

    RETURN api_url
END

ALGORITHM: RateLimitCheck
INPUT: owner: string, repo: string
OUTPUT: void (throws if limit exceeded)

DATA STRUCTURES:
    rate_limiter: TokenBucket  // Per-repository rate limiter
    limit_key: string

BEGIN
    // Create key for this specific repository
    limit_key ← "github:" + owner + "/" + repo

    // Check token bucket
    IF NOT rate_limiter.TryConsume(limit_key, tokens=1) THEN
        retry_after ← rate_limiter.GetResetTime(limit_key)
        THROW RateLimitExceeded(retry_after=retry_after)
    END IF
END

SUBROUTINE: UpdateRateLimitInfo
INPUT: headers: Map<string, string>
OUTPUT: void

BEGIN
    // GitHub provides rate limit info in response headers
    limit ← headers.GET("X-RateLimit-Limit")
    remaining ← headers.GET("X-RateLimit-Remaining")
    reset_time ← headers.GET("X-RateLimit-Reset")  // Unix timestamp

    IF remaining IS NOT null AND reset_time IS NOT null THEN
        // Update our rate limiter with GitHub's current state
        rate_limiter.UpdateState(
            remaining=INTEGER(remaining),
            reset_at=INTEGER(reset_time)
        )

        // Log warning if running low on requests
        IF INTEGER(remaining) < 100 THEN
            LOG("GitHub rate limit running low",
                remaining=remaining,
                reset_at=reset_time,
                level=WARNING)
        END IF
    END IF
END
```

---

## 3. Cache Management

### 3.1 Multi-Level Cache Architecture

```
Cache Hierarchy:
    Level 1: In-Memory LRU Cache (fastest, limited size)
        ↓ miss
    Level 2: Redis Cache (fast, larger, shared across instances)
        ↓ miss
    Level 3: SQLite Database (persistent, unlimited, slower)
        ↓ miss
    Fetch from GitHub
```

### 3.2 Cache Lookup Algorithm

```
ALGORITHM: CheckMultiLevelCache
INPUT: cache_key: string
OUTPUT: CachedPrompt or null

DATA STRUCTURES:
    memory_cache: LRUCache  // In-process memory
    redis_client: RedisClient
    db: DatabaseConnection

BEGIN
    // Level 1: Check in-memory cache
    TRY
        cached ← memory_cache.GET(cache_key)

        IF cached IS NOT null THEN
            // Check if expired
            IF cached.expires_at > GetCurrentTime() THEN
                LOG("Memory cache hit", key=cache_key, level=DEBUG)
                RecordMetric("cache_hit", tier="memory")
                RETURN cached
            ELSE
                LOG("Memory cache expired", key=cache_key, level=DEBUG)
                memory_cache.DELETE(cache_key)  // Remove stale entry
            END IF
        END IF
    CATCH MemoryCacheError AS e
        LOG("Memory cache error", error=e, level=WARNING)
        // Continue to next level
    END TRY

    // Level 2: Check Redis cache
    TRY
        serialized ← redis_client.GET(cache_key)

        IF serialized IS NOT null THEN
            cached ← DeserializePrompt(serialized)

            // Check if expired
            IF cached.expires_at > GetCurrentTime() THEN
                LOG("Redis cache hit", key=cache_key, level=DEBUG)
                RecordMetric("cache_hit", tier="redis")

                // Promote to memory cache
                memory_cache.SET(cache_key, cached)

                RETURN cached
            ELSE
                LOG("Redis cache expired", key=cache_key, level=DEBUG)
                redis_client.DELETE(cache_key)
            END IF
        END IF
    CATCH RedisError AS e
        LOG("Redis cache error", error=e, level=WARNING)
        // Continue to next level
    END TRY

    // Level 3: Check SQLite database
    TRY
        query ← "
            SELECT content, expires_at, cached_at, schema_version, file_path
            FROM prompt_cache
            WHERE cache_key = ?
        "

        row ← db.QUERY_ONE(query, [cache_key])

        IF row IS NOT null THEN
            // Check if expired
            IF row.expires_at > GetCurrentTime() THEN
                LOG("Database cache hit", key=cache_key, level=DEBUG)
                RecordMetric("cache_hit", tier="database")

                cached ← NEW CachedPrompt(
                    content=row.content,
                    expires_at=row.expires_at,
                    cached_at=row.cached_at,
                    schema_version=row.schema_version,
                    file_path=row.file_path
                )

                // Promote to higher cache levels
                redis_client.SET(cache_key, SerializePrompt(cached), ex=TTLSeconds(cached))
                memory_cache.SET(cache_key, cached)

                RETURN cached
            ELSE
                LOG("Database cache expired", key=cache_key, level=DEBUG)
                // Don't delete yet - may be useful for stale-while-revalidate
            END IF
        END IF
    CATCH DatabaseError AS e
        LOG("Database cache error", error=e, level=WARNING)
    END TRY

    // All levels missed
    LOG("Complete cache miss", key=cache_key, level=DEBUG)
    RecordMetric("cache_miss")

    RETURN null
END

COMPLEXITY:
    Time:
        - Best case: O(1) - memory cache hit
        - Average case: O(log n) - Redis or DB lookup
        - Worst case: O(log n) - all levels checked
    Space: O(1) - only storing reference to cached data
```

### 3.3 Cache Storage Algorithm

```
ALGORITHM: CachePrompt
INPUT:
    cache_key: string
    content: string
    guild_id: string
    file_path: string
    schema_version: string
    ttl_minutes: integer
OUTPUT: void

DATA STRUCTURES:
    memory_cache: LRUCache
    redis_client: RedisClient
    db: DatabaseConnection
    cached_at: DateTime
    expires_at: DateTime

BEGIN
    // Calculate expiry time
    cached_at ← GetCurrentTime()
    expires_at ← cached_at + Duration(minutes=ttl_minutes)
    ttl_seconds ← ttl_minutes * 60

    // Create cached prompt object
    cached_prompt ← NEW CachedPrompt(
        content=content,
        cached_at=cached_at,
        expires_at=expires_at,
        schema_version=schema_version,
        file_path=file_path,
        guild_id=guild_id,
        cache_key=cache_key,
        size_bytes=LENGTH(content)
    )

    // Hash content for integrity checking
    content_hash ← SHA256(content)
    cached_prompt.content_hash ← content_hash

    // Level 1: Store in memory cache
    TRY
        memory_cache.SET(cache_key, cached_prompt)
        LOG("Stored in memory cache", key=cache_key, level=DEBUG)
    CATCH MemoryCacheError AS e
        LOG("Failed to store in memory cache", error=e, level=WARNING)
        // Continue - not critical
    END TRY

    // Level 2: Store in Redis
    TRY
        serialized ← SerializePrompt(cached_prompt)
        redis_client.SET(
            key=cache_key,
            value=serialized,
            ex=ttl_seconds  // Redis TTL in seconds
        )
        LOG("Stored in Redis cache", key=cache_key, ttl=ttl_seconds, level=DEBUG)
    CATCH RedisError AS e
        LOG("Failed to store in Redis cache", error=e, level=WARNING)
        // Continue - not critical
    END TRY

    // Level 3: Store in database (persistent)
    TRY
        // Use INSERT OR REPLACE for upsert behavior
        query ← "
            INSERT OR REPLACE INTO prompt_cache (
                cache_key,
                guild_id,
                file_path,
                content,
                schema_version,
                content_hash,
                cached_at,
                expires_at,
                size_bytes,
                access_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        "

        db.EXECUTE(query, [
            cache_key,
            guild_id,
            file_path,
            content,
            schema_version,
            content_hash,
            cached_at,
            expires_at,
            LENGTH(content)
        ])

        LOG("Stored in database cache", key=cache_key, level=DEBUG)

    CATCH DatabaseError AS e
        LOG("Failed to store in database cache", error=e, level=ERROR)
        // This is more critical - database should always work
        RecordMetric("cache_storage_failures_total", tier="database")
    END TRY

    // Update cache size metrics
    RecordGauge("prompt_cache_size_bytes", LENGTH(content), tier="database")
END

COMPLEXITY:
    Time: O(n) where n = content size (due to serialization and hashing)
    Space: O(n) to store content at each level
```

### 3.4 Stale-While-Revalidate Pattern

```
ALGORITHM: GetPromptWithStaleWhileRevalidate
INPUT:
    guild_id: string
    context: PromptContext
    cache_key: string
OUTPUT:
    prompt: string

DATA STRUCTURES:
    fresh_prompt: CachedPrompt or null
    stale_prompt: CachedPrompt or null
    background_task: AsyncTask

BEGIN
    // Try to get fresh prompt
    fresh_prompt ← CheckMultiLevelCache(cache_key)

    IF fresh_prompt IS NOT null AND fresh_prompt.expires_at > GetCurrentTime() THEN
        // Fresh cache hit - return immediately
        RETURN fresh_prompt.content
    END IF

    // Check for stale prompt (expired but still in cache)
    stale_prompt ← GetStaleFromCache(cache_key)

    IF stale_prompt IS NOT null THEN
        // We have a stale version - use it while revalidating in background
        LOG("Using stale cache while revalidating",
            key=cache_key,
            age_seconds=(GetCurrentTime() - stale_prompt.cached_at),
            level=INFO)

        RecordMetric("stale_while_revalidate_hits_total", guild_id=guild_id)

        // Start background revalidation (don't wait)
        background_task ← ASYNC BEGIN
            TRY
                new_content ← ResolvePrompt(guild_id, context)
                LOG("Background revalidation complete", key=cache_key, level=DEBUG)
            CATCH Exception AS e
                LOG("Background revalidation failed",
                    key=cache_key,
                    error=e,
                    level=WARNING)
            END TRY
        END ASYNC

        // Return stale content immediately
        RETURN stale_prompt.content
    END IF

    // No fresh or stale cache - must fetch synchronously
    RETURN ResolvePrompt(guild_id, context)
END

ALGORITHM: GetStaleFromCache
INPUT: cache_key: string
OUTPUT: CachedPrompt or null

BEGIN
    // Check database for stale entries (within reasonable staleness window)
    max_stale_age ← Duration(hours=24)  // Only use if less than 24h old
    oldest_acceptable ← GetCurrentTime() - max_stale_age

    query ← "
        SELECT content, cached_at, expires_at, schema_version, file_path
        FROM prompt_cache
        WHERE cache_key = ?
          AND cached_at > ?
        ORDER BY cached_at DESC
        LIMIT 1
    "

    row ← db.QUERY_ONE(query, [cache_key, oldest_acceptable])

    IF row IS NOT null THEN
        RETURN NEW CachedPrompt(
            content=row.content,
            cached_at=row.cached_at,
            expires_at=row.expires_at,
            schema_version=row.schema_version,
            file_path=row.file_path
        )
    END IF

    RETURN null
END

COMPLEXITY:
    Time: O(1) for cache lookup + O(1) to spawn background task
    Space: O(n) where n = prompt content size
```

### 3.5 Cache Invalidation

```
ALGORITHM: InvalidateGuildCache
INPUT: guild_id: string
OUTPUT: void

BEGIN
    LOG("Invalidating all cache for guild", guild_id=guild_id, level=INFO)

    // Step 1: Find all cache keys for this guild
    query ← "
        SELECT cache_key
        FROM prompt_cache
        WHERE guild_id = ?
    "

    cache_keys ← db.QUERY_ALL(query, [guild_id])

    // Step 2: Delete from all cache levels
    FOR EACH row IN cache_keys DO
        cache_key ← row.cache_key

        // Delete from memory
        TRY
            memory_cache.DELETE(cache_key)
        CATCH Exception AS e
            LOG("Error deleting from memory cache", key=cache_key, error=e)
        END TRY

        // Delete from Redis
        TRY
            redis_client.DELETE(cache_key)
        CATCH Exception AS e
            LOG("Error deleting from Redis", key=cache_key, error=e)
        END TRY
    END FOR

    // Step 3: Delete from database
    delete_query ← "DELETE FROM prompt_cache WHERE guild_id = ?"
    deleted_count ← db.EXECUTE(delete_query, [guild_id])

    LOG("Cache invalidation complete",
        guild_id=guild_id,
        keys_deleted=deleted_count,
        level=INFO)

    RecordMetric("cache_invalidations_total", guild_id=guild_id)
END

ALGORITHM: EvictOldestEntries
INPUT: target_size_mb: integer
OUTPUT: evicted_count: integer

BEGIN
    // Find total cache size
    current_size ← db.QUERY_ONE("SELECT SUM(size_bytes) FROM prompt_cache").total

    IF current_size <= target_size_mb * 1024 * 1024 THEN
        RETURN 0  // No eviction needed
    END IF

    // Calculate how much to evict
    bytes_to_evict ← current_size - (target_size_mb * 1024 * 1024)

    // Evict least recently accessed entries
    query ← "
        SELECT cache_key, size_bytes
        FROM prompt_cache
        ORDER BY last_accessed_at ASC
    "

    rows ← db.QUERY_ALL(query)
    evicted_count ← 0
    evicted_bytes ← 0

    FOR EACH row IN rows DO
        IF evicted_bytes >= bytes_to_evict THEN
            BREAK
        END IF

        // Delete this entry
        db.EXECUTE("DELETE FROM prompt_cache WHERE cache_key = ?", [row.cache_key])

        // Also delete from memory and Redis
        memory_cache.DELETE(row.cache_key)
        redis_client.DELETE(row.cache_key)

        evicted_bytes ← evicted_bytes + row.size_bytes
        evicted_count ← evicted_count + 1
    END FOR

    LOG("Cache eviction complete",
        evicted_count=evicted_count,
        evicted_mb=(evicted_bytes / 1024 / 1024),
        level=INFO)

    RETURN evicted_count
END

COMPLEXITY:
    InvalidateGuildCache:
        Time: O(n) where n = number of cached entries for guild
        Space: O(n) to store list of cache keys

    EvictOldestEntries:
        Time: O(m log m) where m = total cache entries (for sorting)
        Space: O(m)
```

---

## 4. PATH File Parser

### 4.1 PATH File Format

```
Example PATH file:
    # Comments start with #
    # Blank lines ignored

    # Specific overrides (highest priority)
    categories/support/channels/help/{type}/system.md

    # Category-level defaults
    categories/{category}/{type}/system.md
    categories/{category}/{type}/user.md

    # Type-level defaults
    {type}/system.md
    {type}/user.md

    # Final fallback
    system/default.md
    user/default.md
```

### 4.2 Parsing Algorithm

```
ALGORITHM: ParsePathFile
INPUT: content: string
OUTPUT: patterns: List<PromptPathPattern>

DATA STRUCTURES:
    lines: List<string>
    patterns: List<PromptPathPattern>
    line_number: integer

BEGIN
    patterns ← NEW List()
    lines ← content.SPLIT("\n")
    line_number ← 0

    FOR EACH raw_line IN lines DO
        line_number ← line_number + 1

        // Remove leading/trailing whitespace
        line ← raw_line.TRIM()

        // Skip empty lines
        IF line == "" THEN
            CONTINUE
        END IF

        // Skip comments
        IF line.STARTS_WITH("#") THEN
            CONTINUE
        END IF

        // Parse pattern
        TRY
            pattern ← ParsePathPattern(line, line_number)
            patterns.APPEND(pattern)

        CATCH PatternSyntaxError AS e
            LOG("Invalid PATH pattern",
                line_number=line_number,
                line=line,
                error=e,
                level=WARNING)
            // Continue parsing - don't fail on single bad line
        END TRY
    END FOR

    // Sort patterns by priority (most specific first)
    SortPatternsByPriority(patterns)

    LOG("Parsed PATH file",
        total_patterns=LENGTH(patterns),
        level=DEBUG)

    RETURN patterns
END

ALGORITHM: ParsePathPattern
INPUT:
    line: string
    line_number: integer
OUTPUT:
    pattern: PromptPathPattern

DATA STRUCTURES:
    template_params: List<string>
    priority: integer

BEGIN
    // Extract template parameters from pattern
    template_params ← ExtractTemplateParams(line)

    // Validate template parameters
    FOR EACH param IN template_params DO
        IF param NOT IN VALID_TEMPLATE_PARAMS THEN
            THROW PatternSyntaxError(
                "Invalid template parameter: {" + param + "}",
                line_number=line_number
            )
        END IF
    END FOR

    // Validate file path format
    IF NOT IsValidFilePath(line) THEN
        THROW PatternSyntaxError(
            "Invalid file path format",
            line_number=line_number
        )
    END IF

    // Calculate priority (lower number = higher priority)
    priority ← CalculatePatternPriority(line)

    // Create pattern object
    pattern ← NEW PromptPathPattern(
        pattern=line,
        priority=priority,
        template_params=template_params,
        line_number=line_number
    )

    RETURN pattern
END

ALGORITHM: ExtractTemplateParams
INPUT: pattern: string
OUTPUT: params: List<string>

BEGIN
    params ← NEW List()

    // Use regex to find all {param} patterns
    matches ← REGEX_FIND_ALL(pattern, r"\{([a-z_]+)\}")

    FOR EACH match IN matches DO
        param_name ← match.group(1)
        params.APPEND(param_name)
    END FOR

    // Remove duplicates while preserving order
    params ← RemoveDuplicates(params)

    RETURN params
END

ALGORITHM: CalculatePatternPriority
INPUT: pattern: string
OUTPUT: priority: integer

BEGIN
    // Priority factors (lower number = higher priority):
    // 1. Number of template variables (fewer = more specific)
    // 2. Path depth (deeper = more specific)
    // 3. Presence of wildcards

    template_count ← CountOccurrences(pattern, "{")
    path_depth ← CountOccurrences(pattern, "/")
    static_segments ← path_depth - template_count

    // Base priority on template count (more templates = lower priority)
    priority ← template_count * 100

    // Reduce priority (make higher) for deeper paths
    priority ← priority - (path_depth * 10)

    // Increase priority (make lower) for more static segments
    priority ← priority - (static_segments * 20)

    // Ensure non-negative
    priority ← MAX(0, priority)

    RETURN priority
END

EXAMPLES:
    Pattern: "categories/support/channels/help/brief/system.md"
    → template_count=0, path_depth=5, static_segments=5
    → priority = 0*100 - 5*10 - 5*20 = -150 → 0 (highest)

    Pattern: "categories/{category}/{type}/system.md"
    → template_count=2, path_depth=3, static_segments=1
    → priority = 2*100 - 3*10 - 1*20 = 150

    Pattern: "{type}/system.md"
    → template_count=1, path_depth=1, static_segments=0
    → priority = 1*100 - 1*10 - 0*20 = 90

    Pattern: "default.md"
    → template_count=0, path_depth=0, static_segments=0
    → priority = 0*100 - 0*10 - 0*20 = 0 (but should be lowest!)

    // Special case: if no slashes and no templates, it's a fallback (lowest priority)
    IF path_depth == 0 AND template_count == 0 THEN
        priority ← 1000  // Very low priority
    END IF

ALGORITHM: SortPatternsByPriority
INPUT: patterns: List<PromptPathPattern>
OUTPUT: void (sorts in-place)

BEGIN
    // Sort by priority ascending (lower number = higher priority = earlier in list)
    patterns.SORT(key=lambda p: p.priority)
END

COMPLEXITY:
    ParsePathFile: O(n) where n = number of lines
    ParsePathPattern: O(m) where m = length of pattern string
    CalculatePatternPriority: O(m)
    ExtractTemplateParams: O(m)
    Overall: O(n * m) where n = lines, m = avg pattern length
```

### 4.3 Pattern Matching and Resolution

```
ALGORITHM: ResolvePromptPath
INPUT:
    patterns: List<PromptPathPattern>
    context: PromptContext
OUTPUT:
    file_path: string or null

BEGIN
    // Patterns are already sorted by priority (most specific first)

    FOR EACH pattern IN patterns DO
        IF PatternMatches(pattern, context) THEN
            // Found a match - resolve template variables
            file_path ← ResolveTemplateVariables(pattern.pattern, context)

            LOG("Pattern matched",
                pattern=pattern.pattern,
                resolved_path=file_path,
                priority=pattern.priority,
                level=DEBUG)

            RETURN file_path
        END IF
    END FOR

    // No pattern matched
    LOG("No PATH pattern matched context", context=context, level=WARNING)
    RETURN null
END

ALGORITHM: PatternMatches
INPUT:
    pattern: PromptPathPattern
    context: PromptContext
OUTPUT:
    matches: boolean

BEGIN
    // Check if all required template parameters have values in context
    FOR EACH param IN pattern.template_params DO
        value ← GetContextValue(context, param)

        IF value IS null OR value == "" THEN
            // Required parameter missing - pattern doesn't match
            RETURN FALSE
        END IF
    END FOR

    // All required parameters present - pattern matches
    RETURN TRUE
END

ALGORITHM: ResolveTemplateVariables
INPUT:
    pattern: string
    context: PromptContext
OUTPUT:
    resolved: string

BEGIN
    resolved ← pattern

    // Replace each template variable with its value
    // Order matters - replace longer patterns first to avoid partial replacements
    template_vars ← [
        ("{category}", context.category_name),
        ("{channel}", context.channel_name),
        ("{type}", context.summary_type),
        ("{guild}", context.guild_id),
        ("{role}", context.user_role)
    ]

    FOR EACH (placeholder, value) IN template_vars DO
        IF value IS NOT null AND value != "" THEN
            // Sanitize value to prevent path traversal
            safe_value ← SanitizePathComponent(value)
            resolved ← resolved.REPLACE(placeholder, safe_value)
        END IF
    END FOR

    // Validate final path doesn't contain unreplaced templates
    IF resolved.CONTAINS("{") OR resolved.CONTAINS("}") THEN
        LOG("Warning: unresolved template variables in path",
            pattern=pattern,
            resolved=resolved,
            level=WARNING)
    END IF

    RETURN resolved
END

ALGORITHM: SanitizePathComponent
INPUT: value: string
OUTPUT: sanitized: string

BEGIN
    // Prevent path traversal attacks
    sanitized ← value

    // Remove path traversal sequences
    sanitized ← sanitized.REPLACE("..", "")
    sanitized ← sanitized.REPLACE("./", "")
    sanitized ← sanitized.REPLACE("/", "-")  // No slashes in values
    sanitized ← sanitized.REPLACE("\\", "-")

    // Remove null bytes
    sanitized ← sanitized.REPLACE("\0", "")

    // Ensure it's a valid filename component
    sanitized ← REGEX_REPLACE(sanitized, r"[^a-zA-Z0-9_-]", "-")

    // Trim and ensure not empty
    sanitized ← sanitized.TRIM("-")

    IF sanitized == "" THEN
        sanitized ← "unknown"
    END IF

    RETURN sanitized
END

ALGORITHM: GetContextValue
INPUT:
    context: PromptContext
    param_name: string
OUTPUT:
    value: string or null

BEGIN
    SWITCH param_name DO
        CASE "category":
            RETURN context.category_name
        CASE "channel":
            RETURN context.channel_name
        CASE "type":
            RETURN context.summary_type
        CASE "guild":
            RETURN context.guild_id
        CASE "role":
            RETURN context.user_role
        DEFAULT:
            LOG("Unknown template parameter", param=param_name, level=WARNING)
            RETURN null
    END SWITCH
END

COMPLEXITY:
    ResolvePromptPath: O(n * m) where n = patterns, m = params per pattern
    PatternMatches: O(p) where p = number of template params
    ResolveTemplateVariables: O(k) where k = number of template vars (constant)
    Overall: O(n * m) but typically n and m are small (<20 patterns, <5 params)
```

---

## 5. Fallback Chain Executor

### 5.1 Fallback Strategy Hierarchy

```
Fallback Chain (in order):
    1. Fresh cache (already tried in main algorithm)
    2. Stale cache (up to 24 hours old)
    3. Default prompts from different schema version
    4. Built-in default prompts (in-code)
    5. Emergency hardcoded prompt
```

### 5.2 Main Fallback Algorithm

```
ALGORITHM: ExecuteFallbackChain
INPUT:
    guild_id: string
    cache_key: string
    context: PromptContext
    error: Exception
OUTPUT:
    result: PromptResult

DATA STRUCTURES:
    fallback_strategies: List<FallbackStrategy>
    fallback_prompt: string

BEGIN
    LOG("Executing fallback chain",
        guild_id=guild_id,
        original_error=error.message,
        level=WARNING)

    IncrementMetric("prompt_fallback_total", guild_id=guild_id, reason=error.type)

    // Strategy 1: Try stale cache
    TRY
        LOG("Attempting fallback: stale cache", level=DEBUG)

        stale_prompt ← GetStaleFromCache(cache_key)

        IF stale_prompt IS NOT null THEN
            age_hours ← (GetCurrentTime() - stale_prompt.cached_at).total_hours

            LOG("Using stale cache as fallback",
                cache_key=cache_key,
                age_hours=age_hours,
                level=INFO)

            RecordMetric("fallback_stale_cache_used_total", guild_id=guild_id)

            // Trigger background revalidation
            TriggerBackgroundRevalidation(guild_id, context)

            RETURN {
                prompt: stale_prompt.content,
                metadata: {
                    source: "stale_cache",
                    age_hours: age_hours,
                    fallback_reason: error.message,
                    guild_id: guild_id
                }
            }
        END IF

    CATCH Exception AS e
        LOG("Stale cache fallback failed", error=e, level=WARNING)
    END TRY

    // Strategy 2: Try schema v1 defaults (if we were trying v2)
    TRY
        guildConfig ← LoadGuildConfiguration(guild_id)

        IF guildConfig IS NOT null AND guildConfig.schema_version == "v2" THEN
            LOG("Attempting fallback: v1 schema defaults", level=DEBUG)

            // Try to fetch default prompts from v1 path
            v1_path ← GetV1DefaultPath(context.prompt_type, context.summary_type)

            v1_prompt ← FetchFromGitHub(
                repository_url=guildConfig.repository_url,
                file_path=v1_path,
                branch=guildConfig.branch,
                timeout_seconds=3  // Shorter timeout for fallback
            )

            LOG("Using v1 schema defaults as fallback", level=INFO)
            RecordMetric("fallback_v1_schema_used_total", guild_id=guild_id)

            RETURN {
                prompt: v1_prompt,
                metadata: {
                    source: "v1_fallback",
                    file_path: v1_path,
                    fallback_reason: error.message,
                    guild_id: guild_id
                }
            }
        END IF

    CATCH Exception AS e
        LOG("v1 schema fallback failed", error=e, level=WARNING)
    END TRY

    // Strategy 3: Use built-in default prompts
    TRY
        LOG("Attempting fallback: built-in defaults", level=DEBUG)

        default_prompt ← GetDefaultPrompt(
            summary_type=context.summary_type,
            prompt_type=context.prompt_type
        )

        LOG("Using built-in default prompt as fallback",
            summary_type=context.summary_type,
            prompt_type=context.prompt_type,
            level=INFO)

        RecordMetric("fallback_default_prompt_used_total", guild_id=guild_id)

        // Optionally notify admin about fallback
        TryNotifyAdmin(guild_id, error)

        RETURN {
            prompt: default_prompt,
            metadata: {
                source: "default",
                fallback_reason: error.message,
                guild_id: guild_id
            }
        }

    CATCH Exception AS e
        LOG("Built-in default fallback failed", error=e, level=ERROR)
    END TRY

    // Strategy 4: Emergency hardcoded prompt (should never fail)
    LOG("All fallbacks failed, using emergency prompt",
        guild_id=guild_id,
        level=CRITICAL)

    RecordMetric("fallback_emergency_prompt_used_total", guild_id=guild_id)

    emergency_prompt ← GetEmergencyPrompt(context.prompt_type)

    RETURN {
        prompt: emergency_prompt,
        metadata: {
            source: "emergency",
            fallback_reason: "All fallback strategies failed",
            original_error: error.message,
            guild_id: guild_id
        }
    }
END

ALGORITHM: TriggerBackgroundRevalidation
INPUT:
    guild_id: string
    context: PromptContext
OUTPUT:
    void

BEGIN
    // Spawn async task to revalidate cache in background
    ASYNC BEGIN
        TRY
            LOG("Background revalidation started", guild_id=guild_id, level=DEBUG)

            // Wait a bit to avoid immediate retry
            SLEEP(5 seconds)

            // Try to fetch fresh version
            new_prompt ← ResolvePrompt(guild_id, context)

            LOG("Background revalidation succeeded", guild_id=guild_id, level=INFO)

        CATCH Exception AS e
            LOG("Background revalidation failed",
                guild_id=guild_id,
                error=e,
                level=WARNING)
            // Don't fail - user already got stale content
        END TRY
    END ASYNC
END

ALGORITHM: GetDefaultPrompt
INPUT:
    summary_type: string  // "brief", "detailed", "comprehensive"
    prompt_type: string   // "system" or "user"
OUTPUT:
    prompt: string

DATA STRUCTURES:
    default_prompts: Map<(type, length), string>

BEGIN
    // These are the built-in prompts from the codebase
    // They should match what's in src/summarization/prompt_builder.py

    IF prompt_type == "system" THEN
        default_prompts ← {
            "brief": "You are an expert at creating concise Discord conversation summaries...",
            "detailed": "You are an expert at creating comprehensive Discord summaries...",
            "comprehensive": "You are an expert at creating in-depth Discord analysis..."
        }
    ELSE IF prompt_type == "user" THEN
        default_prompts ← {
            "brief": "Summarize the following Discord conversation concisely...",
            "detailed": "Provide a detailed summary of this Discord conversation...",
            "comprehensive": "Create a comprehensive analysis of this conversation..."
        }
    ELSE
        THROW InvalidPromptTypeError("Unknown prompt type: " + prompt_type)
    END IF

    prompt ← default_prompts.GET(summary_type)

    IF prompt IS null THEN
        // Fallback to brief if unknown summary type
        LOG("Unknown summary type, using brief",
            summary_type=summary_type,
            level=WARNING)
        prompt ← default_prompts.GET("brief")
    END IF

    RETURN prompt
END

ALGORITHM: GetEmergencyPrompt
INPUT: prompt_type: string
OUTPUT: prompt: string

BEGIN
    // Absolute minimum prompts that should always work
    IF prompt_type == "system" THEN
        RETURN "Summarize the following Discord conversation in JSON format with a summary field and key_points array."
    ELSE
        RETURN "Please summarize this conversation."
    END IF
END

ALGORITHM: TryNotifyAdmin
INPUT:
    guild_id: string
    error: Exception
OUTPUT:
    void

BEGIN
    // Attempt to send DM to guild owner about external prompt failure
    TRY
        guildConfig ← LoadGuildConfiguration(guild_id)

        IF guildConfig IS null THEN
            RETURN  // No config, nothing to notify about
        END IF

        // Check if we've recently notified (don't spam)
        last_notification ← GetLastNotificationTime(guild_id, "external_prompt_failure")

        IF last_notification IS NOT null AND
           (GetCurrentTime() - last_notification) < Duration(hours=24) THEN
            // Already notified recently
            RETURN
        END IF

        // Get guild owner
        guild ← GetGuildObject(guild_id)
        owner ← guild.owner

        // Send notification
        message ← "⚠️ External Prompt Error\n\n" +
                  "Your custom prompt repository is currently unavailable.\n" +
                  "Repository: " + guildConfig.repository_url + "\n" +
                  "Error: " + error.message + "\n\n" +
                  "The bot is using default prompts as a fallback.\n" +
                  "Use `/prompt config test` to diagnose the issue."

        SendDM(owner, message)

        // Record that we sent notification
        RecordNotificationSent(guild_id, "external_prompt_failure")

        LOG("Sent admin notification", guild_id=guild_id, level=INFO)

    CATCH Exception AS e
        LOG("Failed to notify admin", error=e, level=WARNING)
        // Don't fail - notification is best-effort
    END TRY
END

COMPLEXITY:
    ExecuteFallbackChain:
        Time: O(1) to O(n) where n = file size if GitHub fetch succeeds
        Space: O(n) for prompt content

    Each fallback strategy has independent complexity, but worst-case
    is still bounded by prompt size (typically <50KB).
```

---

## 6. Schema Validator

### 6.1 Content Validation Algorithm

```
ALGORITHM: ValidatePromptContent
INPUT:
    content: string
    file_path: string
OUTPUT:
    result: ValidationResult {
        is_valid: boolean,
        error_message: string or null,
        security_issue: boolean,
        warnings: List<string>
    }

CONSTANTS:
    MAX_SIZE_KB = 50
    MAX_LINE_LENGTH = 10000
    SUSPICIOUS_PATTERNS = [
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"<script[^>]*>",
        r"\{\{\s*[^}]*exec",
        r"\$\{[^}]*exec",
        r"subprocess\.",
        r"os\.system"
    ]

DATA STRUCTURES:
    warnings: List<string>

BEGIN
    warnings ← []

    // Validation 1: Check size
    size_bytes ← LENGTH(content.encode("utf-8"))

    IF size_bytes > MAX_SIZE_KB * 1024 THEN
        RETURN ValidationResult(
            is_valid=FALSE,
            error_message="File too large: " + (size_bytes / 1024) + "KB (max: " + MAX_SIZE_KB + "KB)",
            security_issue=FALSE
        )
    END IF

    IF size_bytes == 0 THEN
        RETURN ValidationResult(
            is_valid=FALSE,
            error_message="File is empty",
            security_issue=FALSE
        )
    END IF

    // Validation 2: Check encoding
    TRY
        decoded ← content.decode("utf-8")
    CATCH UnicodeDecodeError AS e
        RETURN ValidationResult(
            is_valid=FALSE,
            error_message="Invalid UTF-8 encoding in file: " + file_path,
            security_issue=FALSE
        )
    END TRY

    // Validation 3: Check for null bytes
    IF "\0" IN content THEN
        RETURN ValidationResult(
            is_valid=FALSE,
            error_message="File contains null bytes (possibly binary file)",
            security_issue=TRUE
        )
    END IF

    // Validation 4: Check line length (detect binary data)
    lines ← content.SPLIT("\n")

    FOR EACH line IN lines DO
        IF LENGTH(line) > MAX_LINE_LENGTH THEN
            RETURN ValidationResult(
                is_valid=FALSE,
                error_message="Line exceeds maximum length (possibly binary data)",
                security_issue=FALSE
            )
        END IF
    END FOR

    // Validation 5: Security scan for suspicious patterns
    FOR EACH pattern IN SUSPICIOUS_PATTERNS DO
        matches ← REGEX_FIND_ALL(content, pattern, IGNORECASE)

        IF LENGTH(matches) > 0 THEN
            RETURN ValidationResult(
                is_valid=FALSE,
                error_message="Suspicious pattern detected: " + pattern + " in file: " + file_path,
                security_issue=TRUE
            )
        END IF
    END FOR

    // Validation 6: Check for excessive template variables (>20 might be suspicious)
    template_count ← CountOccurrences(content, "{{")

    IF template_count > 20 THEN
        warnings.APPEND("High number of template variables: " + template_count)
    END IF

    // Validation 7: Warn about very short prompts
    IF LENGTH(content) < 50 THEN
        warnings.APPEND("Prompt is very short (" + LENGTH(content) + " chars)")
    END IF

    // All validations passed
    RETURN ValidationResult(
        is_valid=TRUE,
        error_message=null,
        security_issue=FALSE,
        warnings=warnings
    )
END

COMPLEXITY:
    Time: O(n * p) where n = content length, p = number of patterns
    Space: O(n) to store content and split into lines
```

### 6.2 Schema Version Validation

```
ALGORITHM: ValidateSchemaVersion
INPUT:
    repository_url: string
    branch: string
OUTPUT:
    result: SchemaValidationResult {
        schema_version: string,
        is_valid: boolean,
        error_message: string or null
    }

BEGIN
    // Fetch schema-version file
    TRY
        content ← FetchFromGitHub(
            repository_url=repository_url,
            file_path="schema-version",
            branch=branch,
            timeout_seconds=3
        )

    CATCH GitHubError AS e
        IF e.status_code == 404 THEN
            // Missing schema-version file - assume v1
            LOG("No schema-version file found, defaulting to v1",
                repository_url=repository_url,
                level=WARNING)

            RETURN SchemaValidationResult(
                schema_version="v1",
                is_valid=TRUE,
                error_message=null
            )
        ELSE
            // Other error - can't validate
            RETURN SchemaValidationResult(
                schema_version=null,
                is_valid=FALSE,
                error_message="Failed to fetch schema-version: " + e.message
            )
        END IF
    END TRY

    // Parse and validate version
    version ← content.TRIM().LOWERCASE()

    // Remove any BOM or special characters
    version ← RemoveBOM(version)
    version ← REGEX_REPLACE(version, r"[^\w.-]", "")

    // Check if it's a supported version
    supported_versions ← ["v1", "v2"]

    IF version NOT IN supported_versions THEN
        LOG("Unsupported schema version",
            version=version,
            repository_url=repository_url,
            level=WARNING)

        RETURN SchemaValidationResult(
            schema_version=version,
            is_valid=FALSE,
            error_message="Unsupported schema version: " + version +
                         " (supported: " + JOIN(supported_versions, ", ") + ")"
        )
    END IF

    LOG("Schema version validated",
        version=version,
        repository_url=repository_url,
        level=INFO)

    RETURN SchemaValidationResult(
        schema_version=version,
        is_valid=TRUE,
        error_message=null
    )
END

ALGORITHM: ValidatePathFileSyntax
INPUT: path_content: string
OUTPUT: result: PathValidationResult

BEGIN
    errors ← []
    warnings ← []

    lines ← path_content.SPLIT("\n")
    line_number ← 0
    valid_pattern_count ← 0

    FOR EACH raw_line IN lines DO
        line_number ← line_number + 1
        line ← raw_line.TRIM()

        // Skip empty and comment lines
        IF line == "" OR line.STARTS_WITH("#") THEN
            CONTINUE
        END IF

        // Validate pattern syntax
        validation ← ValidatePathPattern(line, line_number)

        IF NOT validation.is_valid THEN
            errors.APPEND("Line " + line_number + ": " + validation.error_message)
        ELSE
            valid_pattern_count ← valid_pattern_count + 1

            IF validation.warnings IS NOT empty THEN
                FOR EACH warning IN validation.warnings DO
                    warnings.APPEND("Line " + line_number + ": " + warning)
                END FOR
            END IF
        END IF
    END FOR

    // Check if we have at least some valid patterns
    IF valid_pattern_count == 0 AND LENGTH(errors) > 0 THEN
        RETURN PathValidationResult(
            is_valid=FALSE,
            error_message="No valid PATH patterns found",
            errors=errors,
            warnings=warnings
        )
    END IF

    // PATH file is valid if we have at least one valid pattern
    // Even if some lines had errors, we can work with the valid ones
    RETURN PathValidationResult(
        is_valid=(valid_pattern_count > 0),
        error_message=null,
        valid_pattern_count=valid_pattern_count,
        errors=errors,
        warnings=warnings
    )
END

ALGORITHM: ValidatePathPattern
INPUT:
    pattern: string
    line_number: integer
OUTPUT:
    result: PatternValidationResult

BEGIN
    warnings ← []

    // Check for invalid characters
    IF REGEX_MATCH(pattern, r"[<>:\"|?*]") THEN
        RETURN PatternValidationResult(
            is_valid=FALSE,
            error_message="Pattern contains invalid characters: <>:\"|?*"
        )
    END IF

    // Check for path traversal attempts
    IF ".." IN pattern OR pattern.CONTAINS("./") THEN
        RETURN PatternValidationResult(
            is_valid=FALSE,
            error_message="Pattern contains path traversal sequences"
        )
    END IF

    // Check for absolute paths
    IF pattern.STARTS_WITH("/") OR pattern.CONTAINS(":\\") THEN
        RETURN PatternValidationResult(
            is_valid=FALSE,
            error_message="Pattern must be relative, not absolute"
        )
    END IF

    // Validate template parameters
    template_params ← ExtractTemplateParams(pattern)

    FOR EACH param IN template_params DO
        IF param NOT IN VALID_TEMPLATE_PARAMS THEN
            RETURN PatternValidationResult(
                is_valid=FALSE,
                error_message="Unknown template parameter: {" + param + "}"
            )
        END IF
    END FOR

    // Check for unclosed braces
    open_count ← CountOccurrences(pattern, "{")
    close_count ← CountOccurrences(pattern, "}")

    IF open_count != close_count THEN
        RETURN PatternValidationResult(
            is_valid=FALSE,
            error_message="Mismatched braces in pattern"
        )
    END IF

    // Warn about patterns with no template variables (might be overly specific)
    IF LENGTH(template_params) == 0 AND CountOccurrences(pattern, "/") > 2 THEN
        warnings.APPEND("Very specific pattern with no template variables")
    END IF

    // Warn about very long patterns
    IF LENGTH(pattern) > 200 THEN
        warnings.APPEND("Very long pattern (" + LENGTH(pattern) + " chars)")
    END IF

    RETURN PatternValidationResult(
        is_valid=TRUE,
        error_message=null,
        warnings=warnings
    )
END

COMPLEXITY:
    ValidatePromptContent: O(n * p) where n = content size, p = patterns
    ValidateSchemaVersion: O(1) - fixed small file
    ValidatePathFileSyntax: O(n * m) where n = lines, m = avg line length
```

---

## 7. Supporting Data Structures

### 7.1 Data Models

```
DATACLASS: PromptContext
FIELDS:
    guild_id: string
    guild_name: string
    channel_name: string
    category_name: string or null
    summary_type: string  // "brief", "detailed", "comprehensive"
    prompt_type: string   // "system" or "user"
    user_role: string

DATACLASS: CachedPrompt
FIELDS:
    content: string
    cached_at: DateTime
    expires_at: DateTime
    schema_version: string
    file_path: string
    guild_id: string
    cache_key: string
    content_hash: string  // SHA-256 hash
    size_bytes: integer
    tier: string  // "memory", "redis", "database"
    access_count: integer

DATACLASS: PromptPathPattern
FIELDS:
    pattern: string
    priority: integer
    template_params: List<string>
    line_number: integer

DATACLASS: ExternalPromptConfig
FIELDS:
    guild_id: string
    repository_url: string
    repository_branch: string
    github_token_id: string or null
    enabled: boolean
    created_at: DateTime
    updated_at: DateTime
    created_by: string  // Discord user_id
    last_fetch_at: DateTime or null
    last_fetch_status: string  // "success", "failed", "partial"
    last_fetch_error: string or null
    schema_version: string
    fetch_count: integer
    error_count: integer

DATACLASS: ValidationResult
FIELDS:
    is_valid: boolean
    error_message: string or null
    security_issue: boolean
    warnings: List<string>

DATACLASS: PromptMetadata
FIELDS:
    source: string  // "cache", "github", "default", "emergency"
    tier: string or null  // Cache tier if from cache
    repository_url: string or null
    file_path: string or null
    fetch_duration_ms: integer or null
    cached_at: DateTime or null
    fallback_reason: string or null
    guild_id: string

DATACLASS: GitHubError
EXTENDS: Exception
FIELDS:
    message: string
    status_code: integer
    is_retryable: boolean
    retry_after: integer or null  // seconds
    details: Exception or null
```

### 7.2 Constants and Configuration

```
CONSTANTS:
    // Cache configuration
    CACHE_TTL_MINUTES = 15
    CACHE_STALE_WINDOW_HOURS = 24
    MAX_CACHE_SIZE_MB = 100

    // GitHub configuration
    GITHUB_API_BASE_URL = "https://api.github.com"
    GITHUB_TIMEOUT_SECONDS = 5
    GITHUB_MAX_RETRIES = 3
    GITHUB_INITIAL_BACKOFF_SECONDS = 1
    MAX_FILE_SIZE_KB = 50

    // Rate limiting
    RATE_LIMIT_MAX_REQUESTS = 10
    RATE_LIMIT_WINDOW_SECONDS = 60

    // Validation
    MAX_LINE_LENGTH = 10000
    MAX_PATH_PATTERNS = 100

    // Template parameters
    VALID_TEMPLATE_PARAMS = {
        "guild": r"^[a-zA-Z0-9_-]+$",
        "channel": r"^[a-z0-9_-]+$",
        "category": r"^[a-zA-Z0-9_ -]+$",
        "type": r"^(brief|detailed|comprehensive)$",
        "role": r"^[a-z]+$"
    }

    // Default file paths
    DEFAULT_FILE_PATHS = {
        ("system", "brief"): "system/brief.md",
        ("system", "detailed"): "system/detailed.md",
        ("system", "comprehensive"): "system/comprehensive.md",
        ("user", "brief"): "user/brief.md",
        ("user", "detailed"): "user/detailed.md",
        ("user", "comprehensive"): "user/comprehensive.md"
    }
```

---

## 8. Error Types and Handling

### 8.1 Exception Hierarchy

```
Exception
├── GitHubError
│   ├── GitHubNotFoundError (404)
│   ├── GitHubAuthError (401, 403)
│   ├── GitHubRateLimitError (429)
│   ├── GitHubTimeoutError
│   └── GitHubServerError (5xx)
├── CacheError
│   ├── MemoryCacheError
│   ├── RedisCacheError
│   └── DatabaseCacheError
├── ValidationError
│   ├── ContentValidationError
│   ├── SchemaValidationError
│   └── PathValidationError
├── ConfigurationError
│   ├── InvalidRepositoryURLError
│   ├── UnsupportedSchemaError
│   └── MissingConfigurationError
└── TemplateError
    ├── InvalidTemplateParamError
    └── TemplateResolutionError
```

### 8.2 Error Handling Patterns

```
PATTERN: Retry with Exponential Backoff

ALGORITHM: RetryWithBackoff
INPUT:
    operation: Function
    max_retries: integer
    initial_backoff: float (seconds)
OUTPUT:
    result: any

BEGIN
    retry_count ← 0
    backoff ← initial_backoff

    WHILE retry_count < max_retries DO
        TRY
            result ← operation()
            RETURN result

        CATCH RetryableError AS e
            retry_count ← retry_count + 1

            IF retry_count >= max_retries THEN
                THROW e
            END IF

            LOG("Retrying operation",
                retry=retry_count,
                backoff=backoff,
                error=e.message,
                level=WARNING)

            SLEEP(backoff)
            backoff ← backoff * 2  // Exponential increase

        CATCH NonRetryableError AS e
            // Don't retry these errors
            THROW e
        END TRY
    END WHILE
END

PATTERN: Circuit Breaker

ALGORITHM: CircuitBreaker
STATE:
    state: "CLOSED" | "OPEN" | "HALF_OPEN"
    failure_count: integer
    success_count: integer
    last_failure_time: DateTime

CONFIGURATION:
    failure_threshold: integer = 5
    success_threshold: integer = 2
    timeout_seconds: integer = 60

ALGORITHM: ExecuteWithCircuitBreaker
INPUT: operation: Function
OUTPUT: result: any

BEGIN
    IF state == "OPEN" THEN
        // Check if timeout has passed
        IF (GetCurrentTime() - last_failure_time) > timeout_seconds THEN
            state ← "HALF_OPEN"
            success_count ← 0
            LOG("Circuit breaker entering half-open state", level=INFO)
        ELSE
            THROW CircuitBreakerOpenError("Service unavailable")
        END IF
    END IF

    TRY
        result ← operation()

        // Operation succeeded
        IF state == "HALF_OPEN" THEN
            success_count ← success_count + 1

            IF success_count >= success_threshold THEN
                state ← "CLOSED"
                failure_count ← 0
                LOG("Circuit breaker closed (service recovered)", level=INFO)
            END IF
        ELSE IF state == "CLOSED" THEN
            failure_count ← 0  // Reset on success
        END IF

        RETURN result

    CATCH Exception AS e
        // Operation failed
        IF state == "HALF_OPEN" THEN
            state ← "OPEN"
            last_failure_time ← GetCurrentTime()
            LOG("Circuit breaker reopened", level=WARNING)
        ELSE IF state == "CLOSED" THEN
            failure_count ← failure_count + 1

            IF failure_count >= failure_threshold THEN
                state ← "OPEN"
                last_failure_time ← GetCurrentTime()
                LOG("Circuit breaker opened due to failures",
                    failures=failure_count,
                    level=WARNING)
            END IF
        END IF

        THROW e
    END TRY
END
```

---

## 9. Complexity Analysis

### 9.1 Overall System Complexity

```
OPERATION: ResolvePrompt (end-to-end)

Best Case (Cache Hit):
    Time: O(1) - hash lookup in memory
    Space: O(1) - return reference to cached content

Average Case (GitHub Fetch):
    Time: O(n + m + p)
        n = size of PATH file (~1-5KB)
        m = size of prompt file (~1-50KB)
        p = number of PATH patterns (~10-50)
    Space: O(m) - store prompt content

Worst Case (Fallback Chain):
    Time: O(k * (n + m + p))
        k = number of fallback attempts (~3-4)
    Space: O(m)

OPERATION: CachePrompt

Time: O(m)
    m = prompt content size (for serialization and hashing)
Space: O(3m)
    Stored in 3 cache levels (memory, Redis, database)

OPERATION: ParsePathFile

Time: O(n * m)
    n = number of lines in PATH file
    m = average line length
Space: O(n) - store list of patterns

OPERATION: ValidatePromptContent

Time: O(m * p)
    m = content size
    p = number of suspicious patterns to check
Space: O(m) - split content into lines
```

### 9.2 Scalability Analysis

```
SCENARIO: 1000 guilds, 50% using external prompts

Cache Memory Usage:
    - Average prompt size: 5KB
    - Prompts per guild: 6 (3 types × 2 prompt types)
    - Total: 500 guilds × 6 prompts × 5KB = 15MB
    - With overhead: ~20MB
    ✓ Well within 100MB limit

Database Storage:
    - Same as above but persistent
    - Total: ~15MB uncompressed
    - With indexes and metadata: ~30MB
    ✓ Negligible for SQLite

GitHub API Requests:
    - Cache TTL: 15 minutes
    - Requests per guild per hour: 6 prompts × 4 cache refreshes = 24
    - Total per hour: 500 × 24 = 12,000
    - Per minute: 200 requests/min
    ✓ Requires careful rate limiting and caching

SCENARIO: Cache hit rate optimization

Target: 85% cache hit rate

With 15-minute TTL:
    - Fresh requests: 15% (cache misses)
    - Cached requests: 85% (cache hits)

If average guild requests summary 10 times/hour:
    - Cache misses per hour per guild: 1.5
    - Total GitHub requests for 500 guilds: 750/hour
    ✓ Much more manageable

RECOMMENDATION: Implement adaptive TTL based on:
    - Update frequency of repository
    - Guild activity level
    - Historical fetch success rate
```

### 9.3 Performance Targets

```
METRIC: Cache hit latency
Target: <5ms (p95)
Implementation: In-memory LRU cache with O(1) lookups

METRIC: GitHub fetch latency
Target: <1.5s (p95)
Implementation: 5s timeout, parallel fetches, exponential backoff

METRIC: Fallback latency
Target: <100ms (p99)
Implementation: Stale cache available immediately, default prompts in-memory

METRIC: Memory per guild
Target: <50KB average
Implementation: LRU eviction, shared cache for same repository

METRIC: Database queries per operation
Target: <3 queries
Implementation: Single query for cache lookup, single query for storage

METRIC: Concurrent GitHub requests
Target: Support 20 simultaneous
Implementation: Async I/O, semaphore-based concurrency limiting
```

---

## End of Pseudocode Document

This pseudocode provides a complete algorithmic blueprint for implementing the external prompt hosting system. Each algorithm includes:

1. Clear input/output specifications
2. Step-by-step logic with error handling
3. Edge case considerations
4. Complexity analysis
5. Supporting data structures

The pseudocode is language-agnostic but detailed enough for direct implementation in Python (or any language) without major design decisions remaining.

**Next Steps:**
1. Review and validate algorithms with team
2. Implement unit tests based on algorithms
3. Code implementation following pseudocode structure
4. Integration testing per specification
5. Performance benchmarking against targets
