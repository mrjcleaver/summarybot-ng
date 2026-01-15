# External Prompt Hosting - Template Repository Guide

Version: 1.0.0
Last Updated: 2026-01-14
Target Audience: Bot Users, Template Creators

---

## Table of Contents

1. [Repository Structure Requirements](#repository-structure-requirements)
2. [PATH File Syntax Reference](#path-file-syntax-reference)
3. [Template Variable Reference](#template-variable-reference)
4. [Example Repositories](#example-repositories-for-different-use-cases)
5. [Template Best Practices](#template-best-practices)
6. [Migration Guide](#migration-guide-v1-to-v2)

---

## Repository Structure Requirements

### Minimum Required Files

Every prompt repository must contain:

```
my-prompts/
├── schema-version        # REQUIRED: Version identifier
├── PATH                  # REQUIRED: Routing rules
└── system/               # REQUIRED: At least one prompt file
    └── brief.md         # or detailed.md or comprehensive.md
```

### Recommended Structure

A well-organized repository:

```
my-prompts/
├── README.md                 # Repository documentation
├── schema-version            # v1
├── PATH                      # Routing configuration
├── .gitignore               # Ignore temp files
├── LICENSE                  # Optional: MIT, Apache, etc.
│
├── system/                  # System prompts (AI instructions)
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
│
├── user/                    # User prompts (optional)
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
│
├── categories/              # Category-specific prompts
│   ├── support/
│   │   ├── brief.md
│   │   ├── detailed.md
│   │   └── comprehensive.md
│   ├── development/
│   │   └── ...
│   └── community/
│       └── ...
│
├── channels/                # Channel-specific overrides
│   ├── announcements/
│   │   └── system.md
│   └── help/
│       └── system.md
│
├── templates/               # Reusable fragments (optional)
│   ├── headers/
│   ├── formats/
│   └── constraints/
│
└── docs/                    # Additional documentation
    ├── CHANGELOG.md
    ├── CONTRIBUTING.md
    └── prompt-philosophy.md
```

### File Naming Conventions

#### Prompt Files

**Pattern:** `{type}.md` or `{prompt_type}.md`

Valid names:
```
✅ brief.md
✅ detailed.md
✅ comprehensive.md
✅ system.md
✅ user.md
✅ system-brief.md
✅ user-detailed.md
```

Invalid names:
```
❌ Brief.md          # Case sensitive
❌ brief.md           # Wrong extension
❌ brief_summary.md  # Doesn't match routing
❌ system prompt.md  # No spaces
```

#### Directory Names

Use lowercase with hyphens:
```
✅ support/
✅ development/
✅ bug-reports/
✅ feature-requests/

❌ Support/           # Case sensitive
❌ Bug Reports/       # Spaces not recommended
❌ feature_requests/  # Use hyphens, not underscores
```

### File Size Limits

- **Maximum file size:** 50 KB per file
- **Recommended size:** Under 10 KB per file
- **Minimum size:** At least 50 characters

### Encoding Requirements

- **Encoding:** UTF-8 (without BOM)
- **Line endings:** LF (Unix) or CRLF (Windows) both accepted
- **Characters:** Text only, no binary data

---

## PATH File Syntax Reference

### Format Version: v1

### Basic Syntax

```
# Comments start with hash
# Empty lines are ignored

# Pattern format:
relative/path/to/{variable}/file.md

# Patterns matched top-to-bottom, first match wins
```

### Complete Syntax Rules

#### Comments
```
# This is a comment
  # Indented comments are fine
# Can span multiple lines

# Inline comments not supported:
system/brief.md # This part will cause an error
```

#### Pattern Structure

```
[directory/]...[{variable}/]...filename.md
 └─────┬────┘    └────┬────┘   └────┬────┘
       │              │             │
   Optional      Optional      Required
   directories   template      filename
                variables
```

#### Valid Patterns

```
# Simple filename
system.md

# Directory + filename
system/brief.md

# Single variable
{type}.md

# Directory + variable + filename
system/{type}.md

# Multiple directories
categories/support/system.md

# Multiple variables
categories/{category}/{type}.md

# Complex paths
categories/{category}/channels/{channel}/{type}/system.md
```

#### Invalid Patterns

```
# Absolute paths
/system/brief.md
C:\system\brief.md

# Path traversal
../system/brief.md
system/../brief.md

# Invalid characters
system\brief.md        # Use forward slashes
system/brief?.md       # No special chars: ? * : | < >
system/brief*.md

# Unclosed braces
{type.md
system/{type.md

# Unknown variables
{custom_var}/system.md
system/{myvar}.md
```

### Variable Syntax

#### Braces

Variables must use curly braces:
```
✅ {type}
✅ {channel}
✅ {category}

❌ $type
❌ <type>
❌ %type%
```

#### Case Sensitivity

Variables are case-sensitive:
```
✅ {type}
❌ {Type}
❌ {TYPE}
```

#### Multiple Variables

Allowed in same pattern:
```
✅ {category}/{channel}/{type}.md
✅ {type}/{role}/system.md

❌ {type}{role}.md     # No separator
❌ {type-role}.md      # Must be separate
```

### Priority and Matching

#### Priority Calculation

Patterns are automatically sorted by specificity:

```
Priority = (template_vars × 100) - (path_depth × 10) - (static_segments × 20)
```

Lower number = higher priority = matched first

**Examples:**

```
Pattern: "categories/support/channels/help/brief/system.md"
template_vars = 0, path_depth = 5, static_segments = 5
priority = 0 - 50 - 100 = -150 → 0 (highest priority)

Pattern: "categories/{category}/{type}/system.md"
template_vars = 2, path_depth = 3, static_segments = 1
priority = 200 - 30 - 20 = 150

Pattern: "{type}/system.md"
template_vars = 1, path_depth = 1, static_segments = 0
priority = 100 - 10 - 0 = 90

Pattern: "system.md"
template_vars = 0, path_depth = 0, static_segments = 0
priority = 1000 (special case: fallback)
```

#### Matching Algorithm

```
1. For each pattern (in priority order):
   a. Check if all template variables have values
   b. If yes, resolve variables to actual values
   c. Return resolved file path
   d. If no, try next pattern

2. If no pattern matches:
   a. Try default file path for summary type
   b. If not found, use built-in default
```

### Complete Examples

#### Example 1: Simple Type Routing

```
# PATH file
system/{type}.md
```

**Matches:**
- `/summarize brief` → `system/brief.md`
- `/summarize detailed` → `system/detailed.md`
- `/summarize comprehensive` → `system/comprehensive.md`

#### Example 2: Category-Based Routing

```
# PATH file
categories/{category}/{type}/system.md
system/{type}.md
```

**Matches:**
- Channel in "Support" category, brief → `categories/support/brief/system.md`
- Channel in "Development" category, detailed → `categories/development/detailed/system.md`
- Channel not in category, brief → `system/brief.md`

#### Example 3: Channel Override

```
# PATH file
channels/announcements/system.md
channels/{channel}/{type}/system.md
categories/{category}/{type}/system.md
system/{type}.md
```

**Matches:**
- In #announcements, any type → `channels/announcements/system.md`
- In #help, brief → `channels/help/brief/system.md`
- In uncategorized channel in "Support" category → `categories/support/brief/system.md`
- In uncategorized, unnamed channel → `system/brief.md`

---

## Template Variable Reference

### Available Variables (v1)

| Variable | Description | Source | Format | Examples |
|----------|-------------|--------|--------|----------|
| `{type}` | Summary length | Command parameter | `brief`, `detailed`, `comprehensive` | See below |
| `{channel}` | Channel name | Discord channel | Lowercase, hyphens, no spaces | `general`, `bug-reports` |
| `{category}` | Category name | Discord category | Lowercase, spaces allowed | `support`, `development` |
| `{guild}` | Guild/Server ID | Discord guild | Numeric string | `123456789012345678` |
| `{role}` | User's highest role | Discord user | Lowercase | `admin`, `moderator`, `member` |

### Variable: `{type}`

**Summary length requested by user**

**Possible values:**
- `brief` - Short, concise summary (2-3 sentences)
- `detailed` - Medium-length summary (1-2 paragraphs)
- `comprehensive` - Extensive summary (multiple paragraphs)

**Usage:**
```
# Route by summary type
system/{type}.md

# Results in:
# - system/brief.md
# - system/detailed.md
# - system/comprehensive.md
```

**Always available:** Yes

### Variable: `{channel}`

**Discord channel name (without # prefix)**

**Format:**
- Lowercase
- Spaces converted to hyphens
- Special characters removed
- Example: `#Bug Reports` → `bug-reports`

**Usage:**
```
# Channel-specific prompts
channels/{channel}/system.md

# Specific override
channels/announcements/system.md
```

**Always available:** Yes (except DMs)

### Variable: `{category}`

**Discord channel category name**

**Format:**
- Lowercase
- Spaces preserved
- Special characters removed
- Example: `Support Tickets` → `support tickets`

**Usage:**
```
# Category-based routing
categories/{category}/{type}/system.md

# Example matches:
# - categories/support/brief/system.md
# - categories/development/detailed/system.md
```

**Always available:** No (only if channel is in a category)

**Handling missing category:**
```
# Pattern requires category
categories/{category}/{type}/system.md  # Won't match if no category

# Include fallback
categories/{category}/{type}/system.md
{type}/system.md                        # Fallback for uncategorized
```

### Variable: `{guild}`

**Discord server/guild ID**

**Format:**
- 18-digit numeric string
- Example: `123456789012345678`

**Usage:**
```
# Guild-specific overrides in shared repository
guilds/{guild}/system/{type}.md
system/{type}.md
```

**Use cases:**
- Multiple servers sharing one repository
- Per-server customization
- Guild-specific experiments

**Always available:** Yes

### Variable: `{role}`

**User's highest role name**

**Format:**
- Lowercase
- Simplified role name
- Example: `@Server Admin` → `admin`

**Common values:**
- `owner` - Server owner
- `admin` - Administrator role
- `moderator` - Moderator role
- `member` - Regular member

**Usage:**
```
# Role-based prompts (advanced)
roles/{role}/{type}/system.md
{type}/system.md
```

**Use cases:**
- Different detail levels for different roles
- Admin-specific summaries
- Moderator-focused summaries

**Always available:** Yes (defaults to `member`)

### Variable Validation

Each variable value is validated:

#### `{type}` Validation
```regex
^(brief|detailed|comprehensive)$
```

#### `{channel}` Validation
```regex
^[a-z0-9_-]+$
```

#### `{category}` Validation
```regex
^[a-z0-9_ -]+$
```

#### `{guild}` Validation
```regex
^[0-9]{17,19}$
```

#### `{role}` Validation
```regex
^[a-z]+$
```

### Template Variables in Prompts

Variables can also be used **inside prompt files**:

```
You are summarizing a conversation in the {{channel_name}} channel
of the {{guild_name}} server.

Channel category: {{category_name}}
Active participants: {{user_count}}
```

**Available prompt variables:**
- `{{guild_name}}` - Server name (text)
- `{{channel_name}}` - Channel name with # (text)
- `{{category_name}}` - Category name (text)
- `{{user_count}}` - Number of participants (number)
- `{{message_count}}` - Number of messages (number)

---

## Example Repositories for Different Use Cases

### 1. Software Development Team

**Use case:** Technical discussions, code reviews, bug reports

**Repository: `dev-team-prompts`**

```
dev-team-prompts/
├── README.md
├── schema-version            # v1
├── PATH
├── system/
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
└── categories/
    ├── code-review/
    │   ├── brief.md
    │   └── detailed.md
    ├── bug-reports/
    │   └── detailed.md
    └── architecture/
        └── comprehensive.md
```

**PATH:**
```
# Category-specific prompts for different discussion types
categories/code-review/{type}/system.md
categories/bug-reports/{type}/system.md
categories/architecture/{type}/system.md

# Generic technical prompts
system/{type}.md
```

**`system/brief.md`:**
```
You are an expert at summarizing technical Discord conversations for software developers.

For BRIEF technical summaries:
- Focus on code changes, decisions, and implementations
- Extract specific technical terms, file names, function names
- Highlight any bugs discussed or fixed
- Note dependencies, libraries, or tools mentioned
- Emphasize action items for developers
- Keep under 200 words

Technical Accuracy:
- Use precise terminology
- Include version numbers if mentioned
- Note breaking changes
- Preserve technical context

Response Format:
{
  "summary": "Concise overview of technical discussion",
  "key_points": ["Technical point 1", "Technical point 2"],
  "code_changes": ["File/function changes discussed"],
  "bugs": ["Bugs mentioned or fixed"],
  "action_items": ["Developer tasks"],
  "technologies": ["Languages, frameworks, tools mentioned"]
}

Style: Professional technical writing for engineers.
```

**`categories/code-review/detailed.md`:**
```
You are summarizing a code review discussion in a software development Discord.

For DETAILED code review summaries:
- Identify what code is being reviewed (PR, commit, files)
- Summarize feedback provided by reviewers
- Note suggested improvements or required changes
- Highlight security concerns or performance issues
- Track approval status if mentioned
- Include specific code suggestions or alternatives
- Note testing requirements or coverage concerns

Focus Areas:
- Code quality feedback
- Architecture and design comments
- Security and performance considerations
- Testing and validation requirements
- Documentation needs

Response Format:
{
  "summary": "Comprehensive overview of code review discussion",
  "code_reviewed": "Description of code under review",
  "feedback": ["Reviewer comment 1", "Comment 2"],
  "required_changes": ["Must-fix item 1", "Must-fix item 2"],
  "suggestions": ["Optional improvement 1", "Improvement 2"],
  "security_concerns": ["Concern 1"],
  "performance_notes": ["Performance consideration 1"],
  "approval_status": "approved/changes_requested/pending"
}

Style: Detailed, technical, focused on actionable feedback.
```

### 2. Community Support Server

**Use case:** Customer support, troubleshooting, issue resolution

**Repository: `support-prompts`**

```
support-prompts/
├── schema-version
├── PATH
├── system/
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
├── categories/
│   ├── technical-support/
│   │   └── detailed.md
│   ├── billing/
│   │   └── brief.md
│   └── feature-requests/
│       └── detailed.md
└── channels/
    └── announcements/
        └── system.md
```

**PATH:**
```
# Announcements always use specific prompt
channels/announcements/system.md

# Category-specific support prompts
categories/technical-support/{type}/system.md
categories/billing/{type}/system.md
categories/feature-requests/{type}/system.md

# General support prompts
system/{type}.md
```

**`system/brief.md`:**
```
You are summarizing customer support conversations in a Discord support server.

For BRIEF support summaries:
- Identify user issues or questions
- Highlight solutions provided
- Note any unresolved issues requiring follow-up
- Track escalations to development or management
- Keep customer-focused and empathetic tone

Support Focus:
- What problems were reported?
- What solutions were provided?
- What's still outstanding?
- Is follow-up needed?

Response Format:
{
  "summary": "Overview of support interactions",
  "issues": ["Issue 1", "Issue 2"],
  "solutions": ["Solution provided 1", "Solution 2"],
  "unresolved": ["Outstanding issue 1"],
  "escalations": ["Escalated to team X"],
  "follow_up_required": true/false,
  "user_satisfaction": "positive/neutral/negative (if indicated)"
}

Style: Professional, empathetic, customer-focused. Under 200 words.
```

### 3. Gaming Community

**Use case:** Casual discussions, events, team formation

**Repository: `gaming-community-prompts`**

```
gaming-community-prompts/
├── schema-version
├── PATH
├── system/
│   ├── brief.md
│   └── detailed.md
└── categories/
    ├── events/
    │   └── detailed.md
    ├── lfg/
    │   └── brief.md
    └── general/
        └── brief.md
```

**PATH:**
```
categories/events/{type}/system.md
categories/lfg/{type}/system.md
system/{type}.md
```

**`system/brief.md`:**
```
You are summarizing conversations in a gaming Discord community.

For BRIEF casual summaries:
- Capture the vibe and energy of the conversation
- Highlight events discussed or planned
- Note team formations or LFG (Looking For Group) requests
- Mention game updates, patches, or news discussed
- Include fun moments or highlights
- Keep it casual, friendly, and enthusiastic

Gaming Focus:
- Upcoming events or raids
- Team recruitment
- Game news and updates
- Fun moments
- Community activities

Response Format:
{
  "summary": "Fun, casual overview of the conversation",
  "events": ["Upcoming event 1", "Event 2"],
  "lfg_requests": ["Player looking for team", "Another LFG"],
  "game_news": ["Patch notes", "Update info"],
  "highlights": ["Funny moment", "Epic play discussed"],
  "vibe": "excited/chill/competitive/supportive"
}

Style: Casual, enthusiastic, gaming-friendly language. Use gamer terminology.
Under 150 words.
```

**`categories/events/detailed.md`:**
```
You are summarizing event planning discussions in a gaming Discord.

For DETAILED event summaries:
- Event name, type, and purpose
- Date, time, and duration planned
- Participants and roles needed
- Requirements (gear, level, skills)
- Preparation needed
- Rewards or objectives
- Sign-up status or attendance

Event Details to Capture:
- What: Event name and type (raid, tournament, meetup)
- When: Scheduled date and time
- Who: Organizer, participants, roles needed
- Requirements: Level, gear, prep needed
- Goals: Objectives and rewards

Response Format:
{
  "summary": "Detailed event planning overview",
  "event_name": "Name of event",
  "event_type": "raid/tournament/casual/competitive",
  "date_time": "Scheduled date and time",
  "organizer": "Who's organizing",
  "participants": ["Player 1", "Player 2"],
  "roles_needed": ["Tank", "Healer"],
  "requirements": ["Level 50+", "Specific gear"],
  "objectives": ["Goal 1", "Goal 2"],
  "sign_up_status": "Open/Closed/Waitlist"
}

Style: Organized, clear, gaming-focused. Include all planning details.
```

### 4. Educational Institution

**Use case:** Study groups, lectures, Q&A sessions

**Repository: `edu-server-prompts`**

```
edu-server-prompts/
├── schema-version
├── PATH
├── system/
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
└── categories/
    ├── lectures/
    │   └── comprehensive.md
    ├── study-groups/
    │   └── detailed.md
    └── qa-sessions/
        └── detailed.md
```

**PATH:**
```
categories/lectures/{type}/system.md
categories/study-groups/{type}/system.md
categories/qa-sessions/{type}/system.md
system/{type}.md
```

**`categories/lectures/comprehensive.md`:**
```
You are summarizing educational lecture discussions in an academic Discord server.

For COMPREHENSIVE lecture summaries:
- Main topics and concepts covered
- Learning objectives achieved
- Key definitions and terminology
- Examples or case studies discussed
- Questions asked by students
- Resources or materials referenced
- Follow-up assignments or readings

Academic Focus:
- Educational content accuracy
- Conceptual understanding
- Learning outcomes
- Study materials
- Student engagement

Response Format:
{
  "summary": "Comprehensive lecture overview",
  "topics_covered": ["Topic 1", "Topic 2"],
  "key_concepts": ["Concept 1 with definition", "Concept 2"],
  "learning_objectives": ["Objective 1", "Objective 2"],
  "examples": ["Example or case study discussed"],
  "student_questions": ["Question and answer"],
  "resources": ["Textbook chapters", "Articles", "Videos"],
  "assignments": ["Homework", "Reading assignments"],
  "difficulty_level": "introductory/intermediate/advanced"
}

Style: Academic, educational, clear and structured. Maintain educational tone.
```

---

## Template Best Practices

### 1. Start Simple

Begin with basic structure:
```
my-prompts/
├── schema-version
├── PATH
└── system/
    ├── brief.md
    ├── detailed.md
    └── comprehensive.md
```

**PATH:**
```
system/{type}.md
```

Test this first, then expand.

### 2. Gradual Complexity

Add features incrementally:

**Phase 1: Basic**
```
system/{type}.md
```

**Phase 2: Categories**
```
categories/{category}/{type}/system.md
system/{type}.md
```

**Phase 3: Channel overrides**
```
channels/announcements/system.md
categories/{category}/{type}/system.md
system/{type}.md
```

### 3. Documentation

Always include `README.md`:

```markdown
# My Server Prompts

## Purpose
Custom prompts for [your use case]

## Structure
- `system/` - Main prompts
- `categories/` - Category-specific prompts

## Variables Used
- `{type}` - Summary length
- `{category}` - Channel category

## Maintenance
- Owner: @username
- Last updated: 2026-01-14
- Update frequency: Monthly
```

### 4. Version Control

Use git tags for versions:
```bash
git tag -a v1.0 -m "Initial production prompts"
git tag -a v1.1 -m "Added category-specific prompts"
```

### 5. Testing

Create `tests/` directory with test cases:

```
tests/
├── test-cases.md
├── sample-conversations/
│   ├── case-1-technical.md
│   ├── case-2-support.md
│   └── case-3-casual.md
└── expected-outputs/
    ├── case-1-expected.json
    ├── case-2-expected.json
    └── case-3-expected.json
```

### 6. Prompt Quality Guidelines

**Be Specific:**
```
❌ "Summarize the conversation"
✅ "Summarize in 2-3 sentences focusing on main decisions made and action items identified"
```

**Define Format:**
```
❌ "Return a summary"
✅ "Return JSON with: {summary: string, key_points: array, action_items: array}"
```

**Set Constraints:**
```
❌ "Keep it short"
✅ "Keep under 200 words, 2-3 sentences maximum"
```

### 7. Reusable Components

Create template fragments:

```
templates/
├── json-format.md
├── word-limit-brief.md
├── word-limit-detailed.md
└── technical-style.md
```

Combine when needed:
```
You are summarizing technical Discord conversations.

<!-- Include: templates/technical-style.md -->
<!-- Include: templates/word-limit-brief.md -->
<!-- Include: templates/json-format.md -->
```

---

## Migration Guide (v1 to v2)

> **Note:** v2 is planned for future release. This section prepares you for the upgrade.

### What's New in v2

- YAML-based PATH configuration
- Prompt metadata and versioning
- Prompt composition (combine multiple files)
- Conditional logic in PATH
- Include directives

### Migration Steps

#### 1. Backup Current Repository

```bash
git tag -a v1-final -m "Last v1 version before migration"
git push --tags
```

#### 2. Update schema-version

Change from:
```
v1
```

To:
```
v2
```

#### 3. Convert PATH to YAML

**v1 PATH:**
```
categories/{category}/{type}/system.md
system/{type}.md
```

**v2 PATH.yaml:**
```yaml
version: v2
patterns:
  - pattern: "categories/{category}/{type}/system"
    priority: 10
    conditions:
      - category: exists
  - pattern: "system/{type}"
    priority: 20
fallback: "system/default"
```

#### 4. Add Prompt Metadata

**v1 format (plain text):**
```
system/brief.md:
  [Prompt content...]
```

**v2 format (YAML with metadata):**
```yaml
# system/brief.yaml
metadata:
  version: "1.0.0"
  author: "username"
  description: "Brief technical summary prompt"
  last_updated: "2026-01-14"

prompt: |
  [Prompt content...]

parameters:
  max_tokens: 4000
  temperature: 0.3
```

#### 5. Test Migration

```
1. Update schema-version to v2
2. Keep v1 prompts as fallback
3. Add v2 prompts gradually
4. Test with bot:
   /prompt-config set <url> v2-test
5. Validate all features work
6. Merge v2-test to main
```

### Backward Compatibility

v2 will support v1 prompts:
- v1 PATH files will continue working
- v1 .md prompts will be read
- Gradual migration supported
- No breaking changes for existing users

---

## Additional Resources

- **User Guide**: `docs/external-prompts-user-guide.md`
- **Admin Reference**: `docs/external-prompts-admin-reference.md`
- **FAQ**: `docs/external-prompts-faq.md`
- **Example Repository**: https://github.com/discord-summary-bot/prompt-templates

---

**Ready to create your template? Start with the Quick Start guide!**
