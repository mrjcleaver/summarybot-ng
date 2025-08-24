# Phase 2: Pseudocode Specification - Summary Bot NG

## 1. System Architecture Overview

### 1.1 High-Level Flow
```
START Application
├── Initialize Configuration
├── Setup Discord Bot Client
├── Initialize Claude API Client
├── Setup Webhook Server
├── Initialize Database Connection
└── Start Event Loops
    ├── Discord Message Handler
    ├── Webhook Request Handler
    └── Scheduled Task Handler
```

## 2. Core Algorithm Pseudocodes

### 2.1 Message Summarization Engine

#### 2.1.1 Main Summarization Algorithm
```pseudocode
FUNCTION summarize_messages(channel_id, start_time, end_time, options)
    // TDD Anchor: test_summarize_messages_basic_flow
    
    INPUT: channel_id (string), start_time (datetime), end_time (datetime), options (dict)
    OUTPUT: SummaryResult (object)
    
    BEGIN
        // Step 1: Validate inputs
        IF NOT validate_channel_access(channel_id) THEN
            THROW UnauthorizedChannelError
        
        IF start_time >= end_time THEN
            THROW InvalidTimeRangeError
            
        // Step 2: Fetch and filter messages
        raw_messages = fetch_discord_messages(channel_id, start_time, end_time)
        
        IF LENGTH(raw_messages) = 0 THEN
            RETURN create_empty_summary("No messages found in specified range")
        
        filtered_messages = filter_messages(raw_messages, options)
        
        IF LENGTH(filtered_messages) < options.min_messages THEN
            RETURN create_empty_summary("Insufficient content for summarization")
        
        // Step 3: Prepare context for Claude
        context_data = prepare_claude_context(filtered_messages)
        
        // Step 4: Generate summary using Claude API
        summary_response = call_claude_api(context_data, options)
        
        IF summary_response.error THEN
            THROW SummarizationError(summary_response.error_message)
        
        // Step 5: Process and structure results
        structured_summary = structure_summary_response(
            summary_response,
            filtered_messages,
            options
        )
        
        // Step 6: Store summary for future reference
        summary_id = store_summary(structured_summary, channel_id, start_time, end_time)
        structured_summary.id = summary_id
        
        RETURN structured_summary
    END
```

#### 2.1.2 Message Filtering Algorithm
```pseudocode
FUNCTION filter_messages(raw_messages, options)
    // TDD Anchor: test_filter_messages_comprehensive
    
    INPUT: raw_messages (list), options (dict)
    OUTPUT: filtered_messages (list)
    
    BEGIN
        filtered = []
        
        FOR each message IN raw_messages DO
            // Skip bot messages (unless explicitly included)
            IF message.author.is_bot AND NOT options.include_bots THEN
                CONTINUE
            
            // Skip system messages
            IF message.type IN [SYSTEM_MESSAGE_TYPES] THEN
                CONTINUE
            
            // Skip empty or emoji-only messages
            IF is_empty_content(message.content) THEN
                CONTINUE
            
            // Skip messages from excluded users
            IF message.author.id IN options.excluded_users THEN
                CONTINUE
            
            // Process and clean message content
            cleaned_message = {
                id: message.id,
                author: message.author.display_name,
                content: clean_message_content(message.content),
                timestamp: message.created_at,
                thread_info: extract_thread_info(message),
                attachments: process_attachments(message.attachments),
                references: extract_message_references(message)
            }
            
            filtered.APPEND(cleaned_message)
        END FOR
        
        // Sort by timestamp to maintain chronological order
        filtered = SORT(filtered, KEY=timestamp)
        
        RETURN filtered
    END
```

#### 2.1.3 Claude API Integration
```pseudocode
FUNCTION call_claude_api(context_data, options)
    // TDD Anchor: test_claude_api_integration
    
    INPUT: context_data (dict), options (dict)
    OUTPUT: ClaudeResponse (object)
    
    BEGIN
        // Prepare Claude prompt
        system_prompt = build_system_prompt(options)
        user_prompt = build_user_prompt(context_data, options)
        
        // Configure API parameters
        api_params = {
            model: options.claude_model OR "claude-3-sonnet-20240229",
            max_tokens: calculate_max_tokens(options.summary_length),
            temperature: options.temperature OR 0.3,
            system: system_prompt,
            messages: [
                {
                    role: "user",
                    content: user_prompt
                }
            ]
        }
        
        // Call Claude API with retry logic
        FOR attempt = 1 TO options.max_retries DO
            TRY
                response = claude_client.messages.create(**api_params)
                
                IF response.stop_reason = "max_tokens" THEN
                    // Handle token limit exceeded
                    RETURN handle_token_limit_exceeded(response, api_params)
                
                RETURN {
                    success: true,
                    content: response.content[0].text,
                    usage: response.usage,
                    model: response.model
                }
                
            CATCH RateLimitError as e DO
                wait_time = calculate_exponential_backoff(attempt)
                SLEEP(wait_time)
                CONTINUE
                
            CATCH APIError as e DO
                IF attempt = options.max_retries THEN
                    RETURN {
                        success: false,
                        error_message: e.message,
                        error_type: "API_ERROR"
                    }
                CONTINUE
        END FOR
        
        RETURN {
            success: false,
            error_message: "Max retries exceeded",
            error_type: "MAX_RETRIES_EXCEEDED"
        }
    END
```

### 2.2 Discord Bot Event Handlers

#### 2.2.1 Slash Command Handler
```pseudocode
FUNCTION handle_slash_command(interaction)
    // TDD Anchor: test_slash_command_handling
    
    INPUT: interaction (DiscordInteraction)
    OUTPUT: None (sends response to Discord)
    
    BEGIN
        command_name = interaction.command.name
        
        CASE command_name OF
            "summarize":
                handle_summarize_command(interaction)
            "schedule_summary":
                handle_schedule_command(interaction)
            "get_summary":
                handle_get_summary_command(interaction)
            "config":
                handle_config_command(interaction)
            DEFAULT:
                respond_with_error(interaction, "Unknown command")
        END CASE
    END
    
FUNCTION handle_summarize_command(interaction)
    // TDD Anchor: test_summarize_command_execution
    
    BEGIN
        // Defer response for long-running operation
        AWAIT interaction.response.defer()
        
        // Extract command parameters
        channel = interaction.options.get("channel") OR interaction.channel
        hours = interaction.options.get("hours") OR 24
        summary_type = interaction.options.get("type") OR "detailed"
        
        // Validate permissions
        IF NOT check_user_permissions(interaction.user, channel) THEN
            AWAIT interaction.followup.send("Insufficient permissions")
            RETURN
        
        // Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        // Generate summary
        TRY
            options = build_summary_options(summary_type, interaction.guild_id)
            summary = summarize_messages(channel.id, start_time, end_time, options)
            
            // Format and send response
            embed = create_summary_embed(summary, channel, start_time, end_time)
            AWAIT interaction.followup.send(embed=embed)
            
        CATCH SummarizationError as e DO
            AWAIT interaction.followup.send(f"Error generating summary: {e.message}")
            
        CATCH Exception as e DO
            LOG_ERROR("Unexpected error in summarize command", e)
            AWAIT interaction.followup.send("An unexpected error occurred")
    END
```

#### 2.2.2 Scheduled Task Handler
```pseudocode
FUNCTION run_scheduled_tasks()
    // TDD Anchor: test_scheduled_task_execution
    
    BEGIN
        WHILE application_running DO
            current_time = datetime.now()
            
            // Get all scheduled tasks due for execution
            due_tasks = get_scheduled_tasks_due(current_time)
            
            FOR each task IN due_tasks DO
                TRY
                    execute_scheduled_summary(task)
                    mark_task_completed(task.id, current_time)
                    
                CATCH Exception as e DO
                    LOG_ERROR(f"Scheduled task {task.id} failed", e)
                    mark_task_failed(task.id, e.message)
            END FOR
            
            // Sleep until next check interval
            SLEEP(SCHEDULED_TASK_CHECK_INTERVAL)
        END WHILE
    END

FUNCTION execute_scheduled_summary(task)
    // TDD Anchor: test_scheduled_summary_execution
    
    BEGIN
        // Determine time range based on task schedule
        IF task.schedule_type = "daily" THEN
            start_time = datetime.now() - timedelta(days=1)
        ELSIF task.schedule_type = "weekly" THEN
            start_time = datetime.now() - timedelta(weeks=1)
        END IF
        
        end_time = datetime.now()
        
        // Generate summary
        summary = summarize_messages(
            task.channel_id,
            start_time,
            end_time,
            task.options
        )
        
        // Send summary to configured destinations
        FOR each destination IN task.destinations DO
            CASE destination.type OF
                "discord_channel":
                    send_summary_to_discord(summary, destination.channel_id)
                "webhook":
                    send_summary_to_webhook(summary, destination.webhook_url)
                "email":
                    send_summary_via_email(summary, destination.email)
            END CASE
        END FOR
    END
```

### 2.3 Webhook Server

#### 2.3.1 Webhook Request Handler
```pseudocode
FUNCTION handle_webhook_request(request)
    // TDD Anchor: test_webhook_request_processing
    
    INPUT: request (HTTPRequest)
    OUTPUT: HTTPResponse
    
    BEGIN
        // Validate authentication
        IF NOT validate_webhook_auth(request.headers) THEN
            RETURN http_response(401, "Unauthorized")
        
        // Parse request body
        TRY
            payload = parse_json(request.body)
        CATCH JSONParseError DO
            RETURN http_response(400, "Invalid JSON payload")
        
        // Validate required fields
        IF NOT validate_webhook_payload(payload) THEN
            RETURN http_response(400, "Missing required fields")
        
        // Extract parameters
        action = payload.get("action")
        
        CASE action OF
            "summarize":
                result = handle_webhook_summarize(payload)
            "schedule":
                result = handle_webhook_schedule(payload)
            "get_summary":
                result = handle_webhook_get_summary(payload)
            DEFAULT:
                RETURN http_response(400, "Unknown action")
        END CASE
        
        IF result.success THEN
            RETURN http_response(200, result.data)
        ELSE
            RETURN http_response(500, result.error)
    END

FUNCTION handle_webhook_summarize(payload)
    // TDD Anchor: test_webhook_summarize_processing
    
    BEGIN
        channel_id = payload.get("channel_id")
        start_time = parse_datetime(payload.get("start_time"))
        end_time = parse_datetime(payload.get("end_time"))
        options = payload.get("options", {})
        
        // Validate channel access for webhook
        IF NOT validate_webhook_channel_access(channel_id, payload.get("guild_id")) THEN
            RETURN {
                success: false,
                error: "Insufficient permissions for channel access"
            }
        
        TRY
            summary = summarize_messages(channel_id, start_time, end_time, options)
            
            RETURN {
                success: true,
                data: {
                    summary_id: summary.id,
                    summary: format_summary_for_api(summary),
                    generated_at: datetime.now().isoformat()
                }
            }
            
        CATCH Exception as e DO
            RETURN {
                success: false,
                error: str(e)
            }
    END
```

## 3. Data Structure Definitions

### 3.1 Core Data Models
```pseudocode
STRUCTURE SummaryResult
    id: string
    channel_id: string
    guild_id: string
    start_time: datetime
    end_time: datetime
    message_count: integer
    key_points: list[string]
    action_items: list[ActionItem]
    technical_terms: list[TechnicalTerm]
    participants: list[Participant]
    summary_text: string
    metadata: dict
    created_at: datetime
END STRUCTURE

STRUCTURE ActionItem
    description: string
    assignee: string (optional)
    deadline: datetime (optional)
    priority: string (high/medium/low)
    source_message_ids: list[string]
END STRUCTURE

STRUCTURE TechnicalTerm
    term: string
    definition: string
    context: string
    source_message_id: string
END STRUCTURE

STRUCTURE Participant
    user_id: string
    display_name: string
    message_count: integer
    key_contributions: list[string]
END STRUCTURE
```

### 3.2 Configuration Models
```pseudocode
STRUCTURE GuildConfiguration
    guild_id: string
    enabled_channels: list[string]
    excluded_channels: list[string]
    default_summary_options: SummaryOptions
    scheduled_tasks: list[ScheduledTask]
    webhook_settings: WebhookSettings
    permissions: PermissionSettings
END STRUCTURE

STRUCTURE SummaryOptions
    summary_length: string (brief/detailed/comprehensive)
    include_bots: boolean
    include_attachments: boolean
    excluded_users: list[string]
    min_messages: integer
    claude_model: string
    temperature: float
    max_tokens: integer
END STRUCTURE

STRUCTURE ScheduledTask
    id: string
    channel_id: string
    schedule_type: string (daily/weekly/custom)
    schedule_time: time
    destinations: list[Destination]
    options: SummaryOptions
    is_active: boolean
    last_run: datetime (optional)
    next_run: datetime
END STRUCTURE
```

## 4. Error Handling Strategies

### 4.1 Error Classification
```pseudocode
ABSTRACT_CLASS SummaryBotException
    message: string
    error_code: string
    timestamp: datetime
    context: dict
END CLASS

CLASS UnauthorizedChannelError EXTENDS SummaryBotException
    // User doesn't have access to requested channel
END CLASS

CLASS InvalidTimeRangeError EXTENDS SummaryBotException
    // Start time is after end time or range is invalid
END CLASS

CLASS SummarizationError EXTENDS SummaryBotException
    // Error during Claude API call or processing
END CLASS

CLASS RateLimitError EXTENDS SummaryBotException
    // API rate limit exceeded
    retry_after: integer
END CLASS

CLASS ConfigurationError EXTENDS SummaryBotException
    // Invalid configuration settings
END CLASS
```

### 4.2 Error Recovery Algorithms
```pseudocode
FUNCTION handle_claude_api_error(error, context)
    // TDD Anchor: test_claude_api_error_recovery
    
    CASE error.type OF
        RATE_LIMIT_ERROR:
            // Implement exponential backoff
            wait_time = min(error.retry_after * 1.5, MAX_BACKOFF_TIME)
            SLEEP(wait_time)
            RETURN RETRY
            
        TOKEN_LIMIT_ERROR:
            // Reduce context size and retry
            reduced_context = reduce_message_context(context, 0.7)
            RETURN RETRY_WITH_REDUCED_CONTEXT(reduced_context)
            
        API_UNAVAILABLE:
            // Use cached summary if available, otherwise fail gracefully
            cached_summary = check_cache_for_similar_request(context)
            IF cached_summary THEN
                RETURN USE_CACHED_RESULT(cached_summary)
            ELSE
                RETURN FAIL_GRACEFULLY("AI service temporarily unavailable")
            
        AUTHENTICATION_ERROR:
            // Log security event and fail
            LOG_SECURITY_EVENT("Claude API authentication failed", context)
            RETURN FAIL_HARD("Authentication error")
            
        DEFAULT:
            RETURN FAIL_WITH_RETRY
    END CASE
END
```

## 5. Performance Optimization Strategies

### 5.1 Caching Algorithms
```pseudocode
FUNCTION get_cached_summary(channel_id, start_time, end_time, options_hash)
    // TDD Anchor: test_summary_caching
    
    cache_key = generate_cache_key(channel_id, start_time, end_time, options_hash)
    
    cached_result = cache.get(cache_key)
    IF cached_result AND not_expired(cached_result) THEN
        RETURN cached_result.summary
    
    RETURN null
END

FUNCTION cache_summary(summary, cache_duration)
    // TDD Anchor: test_summary_cache_storage
    
    cache_key = generate_cache_key(
        summary.channel_id,
        summary.start_time,
        summary.end_time,
        hash(summary.options)
    )
    
    cache_entry = {
        summary: summary,
        created_at: datetime.now(),
        expires_at: datetime.now() + timedelta(seconds=cache_duration)
    }
    
    cache.set(cache_key, cache_entry, ttl=cache_duration)
END
```

### 5.2 Batch Processing
```pseudocode
FUNCTION process_multiple_summaries(requests)
    // TDD Anchor: test_batch_summary_processing
    
    // Group requests by similar parameters to optimize API calls
    grouped_requests = group_by_similarity(requests)
    results = []
    
    FOR each group IN grouped_requests DO
        // Process similar requests in parallel
        batch_results = PARALLEL_MAP(process_single_summary, group)
        results.EXTEND(batch_results)
    END FOR
    
    RETURN results
END
```

## 6. TDD Testing Anchors

### 6.1 Unit Test Categories
```pseudocode
// Core Engine Tests
test_summarize_messages_basic_flow()
test_filter_messages_comprehensive()
test_claude_api_integration()
test_summary_caching()
test_error_handling_scenarios()

// Discord Integration Tests
test_slash_command_handling()
test_summarize_command_execution()
test_scheduled_task_execution()
test_permission_validation()

// Webhook Tests
test_webhook_request_processing()
test_webhook_summarize_processing()
test_webhook_authentication()
test_webhook_error_responses()

// Data Processing Tests
test_message_filtering_edge_cases()
test_content_cleaning()
test_thread_extraction()
test_attachment_processing()

// Performance Tests
test_batch_summary_processing()
test_rate_limit_handling()
test_memory_usage_optimization()
test_concurrent_request_handling()
```

### 6.2 Integration Test Scenarios
```pseudocode
// End-to-End Workflow Tests
test_complete_summarization_workflow()
test_scheduled_summary_generation()
test_webhook_to_discord_flow()
test_error_recovery_workflows()

// API Integration Tests
test_discord_api_integration()
test_claude_api_integration()
test_database_operations()
test_cache_operations()

// Configuration Tests
test_guild_configuration_management()
test_permission_enforcement()
test_rate_limiting()
test_data_retention_policies()
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-08-24  
**Next Phase**: Modular Architecture Design (Phase 3)  
**TDD Test Count**: 35+ test anchors defined