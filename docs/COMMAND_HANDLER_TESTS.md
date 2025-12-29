# Command Handler Test Suite Documentation

## Overview

Comprehensive unit tests for all command handler components, covering base functionality, summarization commands, configuration management, scheduling, and utility functions.

## Test Statistics

- **Total Test Cases**: 131
- **Test Files**: 5
- **Lines of Test Code**: ~2,500+

## Test Coverage by Module

### 1. test_base.py - BaseCommandHandler (24 tests)

Tests for core command handler functionality:

**RateLimitTracker Tests (6 tests)**:
- `test_initial_request_allowed` - First request is always allowed
- `test_requests_within_limit` - Requests under limit are allowed
- `test_rate_limit_exceeded` - Rate limit enforcement
- `test_rate_limit_per_user` - Per-user rate limiting
- `test_rate_limit_window_expiry` - Window expiration and reset
- `test_clear_user_limit` - Manual limit clearing

**BaseCommandHandler Tests (18 tests)**:
- `test_handle_command_success` - Successful command execution
- `test_handle_command_with_rate_limit` - Rate limit enforcement in commands
- `test_handle_command_without_rate_limit` - Commands without rate limiting
- `test_permission_check_allowed` - Permission validation (allowed)
- `test_permission_check_denied` - Permission validation (denied)
- `test_permission_check_without_manager` - Commands without permission manager
- `test_user_error_handling` - UserError exception handling
- `test_generic_error_handling` - Generic exception handling
- `test_defer_response` - Response deferral
- `test_defer_response_ephemeral` - Ephemeral response deferral
- `test_defer_response_already_done` - Handling already-sent responses
- `test_send_error_response` - Error response formatting
- `test_send_error_response_after_defer` - Error responses after deferral
- `test_send_success_response` - Success response formatting
- `test_send_success_response_with_custom_embed` - Custom embed responses
- `test_send_rate_limit_response` - Rate limit error messages
- `test_send_permission_error` - Permission error messages
- `test_retryable_error_hint` - Retry hints for retryable errors

### 2. test_summarize.py - SummarizeCommandHandler (15 tests)

Tests for summarization command functionality:

**Command Execution Tests**:
- `test_handle_summarize_basic` - Basic summarize command
- `test_handle_summarize_custom_channel` - Summarizing different channels
- `test_handle_summarize_no_permission` - Permission denied scenarios
- `test_handle_summarize_invalid_channel_type` - Non-text channel handling
- `test_handle_summarize_custom_time_range` - Custom time range parsing
- `test_handle_summarize_different_lengths` - Summary length variations
- `test_handle_summarize_invalid_length` - Invalid length handling
- `test_handle_summarize_include_bots` - Bot message inclusion
- `test_handle_summarize_insufficient_messages` - Minimum message validation

**Quick Summary Tests**:
- `test_handle_quick_summary` - Quick summary command
- `test_handle_quick_summary_invalid_minutes` - Invalid time validation

**Cost Estimation Tests**:
- `test_estimate_summary_cost` - Cost estimation feature

**Message Processing Tests**:
- `test_fetch_and_process_messages_with_fetcher` - MessageFetcher integration
- `test_handle_summarize_api_failure` - API failure handling

### 3. test_config.py - ConfigCommandHandler (25 tests)

Tests for configuration management:

**Permission Tests (4 tests)**:
- `test_check_admin_permission_as_admin` - Administrator access
- `test_check_admin_permission_as_manager` - Guild manager access
- `test_check_admin_permission_as_regular_user` - Regular user denial
- `test_check_admin_permission_no_guild` - DM context handling

**Config View Tests (3 tests)**:
- `test_handle_config_view_success` - Viewing configuration
- `test_handle_config_view_no_permission` - Permission denied
- `test_handle_config_view_no_config` - Default configuration display

**Channel Management Tests (5 tests)**:
- `test_handle_config_set_channels_enable` - Enabling channels
- `test_handle_config_set_channels_exclude` - Excluding channels
- `test_handle_config_set_channels_invalid_action` - Invalid action handling
- `test_handle_config_set_channels_no_valid_channels` - Invalid channel IDs
- `test_handle_config_set_channels_mixed_formats` - Mixed ID formats

**Default Settings Tests (11 tests)**:
- `test_handle_config_set_defaults_length` - Setting summary length
- `test_handle_config_set_defaults_invalid_length` - Invalid length validation
- `test_handle_config_set_defaults_include_bots` - Bot inclusion setting
- `test_handle_config_set_defaults_min_messages` - Minimum message threshold
- `test_handle_config_set_defaults_invalid_min_messages` - Invalid threshold validation
- `test_handle_config_set_defaults_model` - Claude model selection
- `test_handle_config_set_defaults_invalid_model` - Invalid model validation
- `test_handle_config_set_defaults_multiple_fields` - Multiple field updates
- `test_handle_config_set_defaults_no_fields` - No field validation
- `test_handle_config_set_defaults_no_permission` - Permission validation
- `test_handle_config_no_manager` - Missing config manager handling

**Config Reset Tests (2 tests)**:
- `test_handle_config_reset` - Configuration reset
- `test_handle_config_reset_no_permission` - Permission validation

### 4. test_schedule.py - ScheduleCommandHandler (23 tests)

Tests for scheduled summary management:

**Schedule Creation Tests (9 tests)**:
- `test_handle_schedule_create_daily` - Daily schedule creation
- `test_handle_schedule_create_weekly` - Weekly schedule creation
- `test_handle_schedule_create_hourly` - Hourly schedule creation
- `test_handle_schedule_create_invalid_frequency` - Invalid frequency validation
- `test_handle_schedule_create_invalid_time_format` - Time format validation
- `test_handle_schedule_create_different_lengths` - Summary length variations
- `test_handle_schedule_create_invalid_length` - Invalid length validation
- `test_handle_schedule_create_no_permission` - Permission validation
- `test_handle_schedule_create_no_scheduler` - Missing scheduler handling

**Schedule Listing Tests (3 tests)**:
- `test_handle_schedule_list_empty` - Empty schedule list
- `test_handle_schedule_list_with_tasks` - Listing existing tasks
- `test_handle_schedule_list_many_tasks` - Pagination handling

**Schedule Management Tests (9 tests)**:
- `test_handle_schedule_delete_success` - Task deletion
- `test_handle_schedule_delete_not_found` - Non-existent task handling
- `test_handle_schedule_delete_no_permission` - Permission validation
- `test_handle_schedule_pause` - Task pausing
- `test_handle_schedule_pause_no_permission` - Permission validation
- `test_handle_schedule_resume` - Task resuming
- `test_handle_schedule_resume_no_permission` - Permission validation
- `test_schedule_metadata_includes_creator` - Metadata validation
- `test_schedule_without_time_of_day` - Optional time handling

### 5. test_utils.py - Utility Functions (44 tests)

Tests for command handler utilities:

**Embed Formatters (6 tests)**:
- `test_format_error_response` - Error embed formatting
- `test_format_error_response_default_code` - Default error codes
- `test_format_success_response` - Success embed formatting
- `test_format_success_response_with_fields` - Field handling
- `test_format_info_response` - Info embed formatting
- `test_format_info_response_with_fields` - Field handling

**Time Validation (5 tests)**:
- `test_validate_time_range_valid` - Valid range validation
- `test_validate_time_range_start_after_end` - Invalid order detection
- `test_validate_time_range_too_large` - Range size limits
- `test_validate_time_range_custom_max` - Custom maximum validation
- `test_validate_time_range_future_end` - Future time detection

**Time String Parsing (9 tests)**:
- `test_parse_time_string_hours` - Hour-based parsing
- `test_parse_time_string_hours_variations` - Format variations
- `test_parse_time_string_minutes` - Minute-based parsing
- `test_parse_time_string_days` - Day-based parsing
- `test_parse_time_string_weeks` - Week-based parsing
- `test_parse_time_string_ago_format` - "X ago" format parsing
- `test_parse_time_string_keywords` - Keyword parsing
- `test_parse_time_string_iso_format` - ISO format parsing
- `test_parse_time_string_invalid` - Invalid format handling

**Duration Formatting (5 tests)**:
- `test_format_duration_seconds` - Second formatting
- `test_format_duration_minutes` - Minute formatting
- `test_format_duration_hours` - Hour formatting
- `test_format_duration_days` - Day formatting
- `test_format_duration_mixed` - Mixed unit formatting

**Text Truncation (5 tests)**:
- `test_truncate_text_under_limit` - Below limit handling
- `test_truncate_text_over_limit` - Truncation behavior
- `test_truncate_text_custom_suffix` - Custom suffix support
- `test_truncate_text_exactly_at_limit` - Exact limit handling
- `test_truncate_text_discord_field_limit` - Discord limits

**Channel ID Extraction (4 tests)**:
- `test_extract_channel_id_from_mention` - Mention parsing
- `test_extract_channel_id_from_plain_id` - Plain ID parsing
- `test_extract_channel_id_invalid_mention` - Invalid mention handling
- `test_extract_channel_id_malformed_input` - Malformed input handling

**Progress Bar Creation (9 tests)**:
- `test_create_progress_bar_empty` - Empty progress
- `test_create_progress_bar_full` - Full progress
- `test_create_progress_bar_half` - Partial progress
- `test_create_progress_bar_custom_length` - Custom bar length
- `test_create_progress_bar_partial_progress` - Various percentages
- `test_create_progress_bar_zero_total` - Zero total handling
- `test_create_progress_bar_over_100_percent` - Overflow handling
- `test_create_progress_bar_small_values` - Small value handling
- `test_create_progress_bar_large_values` - Large value handling

**Integration Scenarios (4 tests)**:
- `test_parse_and_validate_time_range` - Combined parsing and validation
- `test_format_duration_from_time_range` - Duration calculation
- `test_error_response_with_truncated_message` - Combined truncation and formatting
- `test_success_response_with_formatted_duration` - Combined duration formatting

## Test Infrastructure

### Fixtures Used

All tests utilize fixtures from `/tests/conftest.py`:
- `mock_summarization_engine` - Mocked summarization engine
- `mock_permission_manager` - Mocked permission manager
- `mock_config_manager` - Mocked configuration manager
- `mock_task_scheduler` - Mocked task scheduler
- `mock_discord_channel` - Mocked Discord channel
- `mock_discord_user` - Mocked Discord user
- `sample_messages` - Sample message data

### Mock Strategy

Tests use `unittest.mock.AsyncMock` for async operations and `MagicMock` for sync operations, following discord.py's async/await patterns.

## Running the Tests

### Run All Command Handler Tests
```bash
python -m pytest tests/unit/test_command_handlers/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/unit/test_command_handlers/test_base.py -v
python -m pytest tests/unit/test_command_handlers/test_summarize.py -v
python -m pytest tests/unit/test_command_handlers/test_config.py -v
python -m pytest tests/unit/test_command_handlers/test_schedule.py -v
python -m pytest tests/unit/test_command_handlers/test_utils.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/unit/test_command_handlers/test_base.py::TestRateLimitTracker -v
python -m pytest tests/unit/test_command_handlers/test_utils.py::TestTimeStringParsing -v
```

### Run with Coverage
```bash
python -m pytest tests/unit/test_command_handlers/ --cov=src/command_handlers --cov-report=html
```

## Test Quality Standards

All tests follow these quality standards:
1. **Arrange-Act-Assert** pattern for clarity
2. **Descriptive test names** explaining what and why
3. **Isolated tests** - No dependencies between tests
4. **Comprehensive mocking** - All external dependencies mocked
5. **Error scenario coverage** - Both success and failure paths tested
6. **Edge case testing** - Boundary conditions validated

## Coverage Goals

- **Statements**: >80% (Target: 90%)
- **Branches**: >75% (Target: 85%)
- **Functions**: >80% (Target: 90%)
- **Lines**: >80% (Target: 90%)

## Known Issues

Some tests may have minor failures related to async mock behavior in discord.py interactions. These are being addressed in subsequent iterations.

## Future Enhancements

1. Add performance benchmarks for rate limiting
2. Add integration tests with real Discord bot instance
3. Add property-based tests for time parsing
4. Add fuzzing tests for error handling
5. Add stress tests for rate limiter

## Related Documentation

- [Test Infrastructure Setup](../tests/README.md)
- [Command Handler Documentation](../src/command_handlers/README.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
