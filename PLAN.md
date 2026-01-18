# Plan: Refactor Model Variable Naming and Consolidate Defaults

## Current State Analysis

### Variable Names
- **Code**: `claude_model` (used in 19 files)
- **Environment Variable**: `SUMMARY_CLAUDE_MODEL`
- **Unused Variable**: `OPENROUTER_MODEL` (in main.py only, never actually used)

### Hardcoded Defaults (9 locations)
1. `src/models/summary.py:256` - `_get_default_model()` fallback: `'claude-3-sonnet-20240229'`
2. `src/config/settings.py:44` - `SummaryOptionsConfig` default: `'claude-3-sonnet-20240229'`
3. `src/config/environment.py:147` - env loader fallback: `'claude-3-sonnet-20240229'`
4. `src/config/manager.py:177` - deserialization fallback: `'claude-3-sonnet-20240229'`
5. `src/scheduling/persistence.py:234` - deserialization fallback: `'claude-3-sonnet-20240229'`
6. `src/webhook_service/endpoints.py:304` - webhook fallback: `'claude-3-sonnet-20240229'`
7. `src/main.py:186` - OPENROUTER_MODEL fallback: `'anthropic/claude-3-sonnet-20240229'`
8. `src/main.py:201` - OPENROUTER_MODEL fallback: `'anthropic/claude-3-sonnet-20240229'`
9. `src/models/summary.py:321` - BRIEF model hardcoded: `'claude-3-haiku-20240307'`

### Valid Models List
`src/config/validation.py:201-206` has hardcoded list that doesn't include `openrouter/auto`

## Goals

1. **Rename variable** from `claude_model` to `summarization_model`
2. **Rename environment variable** from `SUMMARY_CLAUDE_MODEL` to `SUMMARIZATION_MODEL`
3. **Remove unused variable** `OPENROUTER_MODEL`
4. **Single source of truth** for default model value: `openrouter/auto`
5. **Eliminate all hardcoded defaults** - read from single constants module
6. **Update validation** to include `openrouter/auto`

## Implementation Plan

### Phase 1: Create Configuration Constants Module

**File**: `src/config/constants.py` (NEW)

```python
"""
Configuration constants for the summarization bot.
Single source of truth for all default values.
"""

# Model Configuration
DEFAULT_SUMMARIZATION_MODEL = "openrouter/auto"

# Valid model choices
VALID_MODELS = [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "openrouter/auto"
]

# Model aliases for backward compatibility
MODEL_ALIASES = {
    "anthropic/claude-3-sonnet-20240229": "claude-3-sonnet-20240229",
    "anthropic/claude-3-haiku-20240307": "claude-3-haiku-20240307",
    "anthropic/claude-3-opus-20240229": "claude-3-opus-20240229"
}
```

### Phase 2: Update Core Models

**File**: `src/models/summary.py`

Changes:
1. Import from constants: `from ..config.constants import DEFAULT_SUMMARIZATION_MODEL`
2. Update `_get_default_model()`:
   ```python
   def _get_default_model() -> str:
       """Get default summarization model from environment or use fallback."""
       return os.getenv('SUMMARIZATION_MODEL', DEFAULT_SUMMARIZATION_MODEL)
   ```
3. Rename field: `claude_model` → `summarization_model`
4. Update `get_model_for_length()` to use constant for BRIEF model
5. Update `to_dict()` method to include both old and new key names for backward compatibility

**File**: `src/config/settings.py`

Changes:
1. Import constant
2. Rename: `claude_model` → `summarization_model`
3. Remove hardcoded default, use constant
4. Update `to_dict()` to include backward compatibility

### Phase 3: Update Configuration Loading

**File**: `src/config/environment.py`

Changes:
1. Import constant
2. Line 147: Replace hardcoded fallback with constant
3. Update parameter name: `claude_model` → `summarization_model`

**File**: `src/config/manager.py`

Changes:
1. Import constant
2. Line 177: Replace hardcoded fallback with constant
3. Update dict key reading: look for both `claude_model` (old) and `summarization_model` (new)
4. Store as: `summarization_model`

**File**: `src/config/validation.py`

Changes:
1. Import `VALID_MODELS` constant
2. Line 201-206: Replace hardcoded list with constant
3. Update field reference: `options.claude_model` → `options.summarization_model`

### Phase 4: Update Application Initialization

**File**: `src/main.py`

Changes:
1. Line 186: Remove OPENROUTER_MODEL usage
2. Line 201: Remove OPENROUTER_MODEL usage
3. The `model` variable returned by `_select_llm_provider()` is logged but never used - this is fine

### Phase 5: Update Usage Throughout Codebase

**File**: `src/summarization/engine.py`

Changes:
1. Line 314: `options.claude_model` → `options.summarization_model`
2. Line 328: `options.claude_model` → `options.summarization_model`
3. Line 338: `options.claude_model` → `options.summarization_model`
4. Line 397: `options.claude_model` → `options.summarization_model`

**File**: `src/command_handlers/config.py`

Changes:
1. Line 152: Display `options.summarization_model`
2. Line 347: Set `config.default_summary_options.summarization_model`
3. Import and use `VALID_MODELS` constant for validation

**File**: `src/webhook_service/endpoints.py`

Changes:
1. Import constant
2. Line 304: Replace hardcoded fallback with constant
3. Update parameter: `claude_model` → `summarization_model`

**File**: `src/scheduling/persistence.py`

Changes:
1. Import constant
2. Line 187: `claude_model` → `summarization_model`
3. Line 234: Replace hardcoded fallback with constant
4. Read from dict: try `summarization_model` first, fallback to `claude_model` for backward compatibility

**File**: `src/scheduling/tasks.py`

Changes:
1. Line 103: `claude_model` → `summarization_model`

**File**: `src/summarization/cache.py`

Changes:
1. Line 265: `claude_model` → `summarization_model` in metadata

**File**: `src/summarization/optimization.py`

Changes:
1. Line 284: `claude_model` → `summarization_model`

### Phase 6: Update Tests

Update all test files that reference `claude_model`:
- `tests/unit/test_config/test_settings.py`
- `tests/unit/test_summarization/test_engine.py`
- `tests/unit/test_summarization/test_cache.py`
- `tests/performance/test_load_testing.py`
- `tests/unit/test_scheduling/test_persistence.py`
- `tests/unit/test_command_handlers/test_config.py`

### Phase 7: Environment Variable Migration

**Update documentation** to instruct users:
1. Rename `SUMMARY_CLAUDE_MODEL` → `SUMMARIZATION_MODEL`
2. Remove `OPENROUTER_MODEL` if set

**Backward compatibility**:
- Code will check `SUMMARIZATION_MODEL` first
- If not found, fall back to `SUMMARY_CLAUDE_MODEL` temporarily
- Log deprecation warning when old variable is used

### Phase 8: Database Migration (Optional - for serialized data)

Since guild configs and scheduled tasks are serialized with `claude_model` key:
- When deserializing, try `summarization_model` first
- Fall back to `claude_model` if not found
- When serializing, write both keys temporarily for rollback safety
- After migration period, write only `summarization_model`

## Migration Strategy

### Rollout Approach

**Option A: Big Bang (Recommended)**
- All changes in one deployment
- Backward compatibility in deserialization
- Old configs continue to work
- New configs use new field names

**Option B: Gradual Migration**
- Phase 1: Add new field alongside old field
- Phase 2: Update all writes to use new field
- Phase 3: Update all reads to prefer new field
- Phase 4: Remove old field support

**Recommendation**: Option A - code is not heavily used in production yet, clean break is better

### Rollback Plan

If issues arise:
1. All deserialization has fallbacks to old field names
2. Can quickly revert by restoring previous version
3. Data in database remains compatible

## Testing Strategy

1. **Unit Tests**: Update all model references
2. **Integration Tests**: Test environment variable loading
3. **Manual Tests**:
   - Create new guild config with new defaults
   - Load old guild config (should still work)
   - Test /config reset command
   - Test summary creation with different models

## Files Requiring Changes

### Create (1 file)
- `src/config/constants.py`

### Modify (15 files)
1. `src/models/summary.py`
2. `src/config/settings.py`
3. `src/config/environment.py`
4. `src/config/manager.py`
5. `src/config/validation.py`
6. `src/main.py`
7. `src/summarization/engine.py`
8. `src/command_handlers/config.py`
9. `src/webhook_service/endpoints.py`
10. `src/scheduling/persistence.py`
11. `src/scheduling/tasks.py`
12. `src/summarization/cache.py`
13. `src/summarization/optimization.py`
14. `.env.example` (if exists)
15. `README.md` or `docs/` (update environment variable documentation)

### Update Tests (6 files)
1. `tests/unit/test_config/test_settings.py`
2. `tests/unit/test_summarization/test_engine.py`
3. `tests/unit/test_summarization/test_cache.py`
4. `tests/performance/test_load_testing.py`
5. `tests/unit/test_scheduling/test_persistence.py`
6. `tests/unit/test_command_handlers/test_config.py`

## Risks and Mitigation

### Risk 1: Breaking existing configurations
**Mitigation**: Backward compatibility in all deserialization code

### Risk 2: Environment variable not updated in production
**Mitigation**: Fallback to old variable name with deprecation warning

### Risk 3: Tests fail after rename
**Mitigation**: Comprehensive test updates in same PR

### Risk 4: Database serialization issues
**Mitigation**: Support both field names during read, write both during transition

## Success Criteria

- [ ] All references to `claude_model` renamed to `summarization_model`
- [ ] Environment variable `SUMMARIZATION_MODEL` is primary
- [ ] Single source of truth in `src/config/constants.py`
- [ ] Zero hardcoded model defaults (except in constants file)
- [ ] All tests pass
- [ ] `/config reset` uses `openrouter/auto` by default
- [ ] Old guild configs still load correctly
- [ ] Documentation updated
