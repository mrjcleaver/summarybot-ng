# External Prompt Hosting - User Guide

Version: 1.0.0
Last Updated: 2026-01-14
Target Audience: Discord Server Administrators

---

## Table of Contents

1. [What is External Prompt Hosting?](#what-is-external-prompt-hosting)
2. [Why Use Custom Prompts?](#why-use-custom-prompts)
3. [Quick Start Guide](#quick-start-guide-5-minutes)
4. [Step-by-Step Configuration](#step-by-step-configuration)
5. [Creating Your First PATH File](#creating-your-first-path-file)
6. [Writing Effective Prompt Templates](#writing-effective-prompt-templates)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)
8. [Best Practices and Tips](#best-practices-and-tips)

---

## What is External Prompt Hosting?

External prompt hosting allows you to customize how the Discord Summarization Bot summarizes conversations in your server. Instead of using the bot's built-in prompts, you can store your own custom prompts in a GitHub repository and have the bot use them automatically.

### Key Features

- **Per-Server Customization**: Each Discord server can have its own unique prompts
- **Version Control**: All changes to your prompts are tracked in Git
- **Live Updates**: Update your prompts anytime by editing your repository
- **Automatic Fallback**: If something goes wrong, the bot automatically uses default prompts
- **Context-Aware**: Different prompts for different channels, categories, or summary types

### How It Works

```
┌─────────────────────┐
│  Your Discord       │
│  Server             │
└──────────┬──────────┘
           │
           │ /summarize command
           │
┌──────────▼──────────┐
│  SummaryBot         │
│  1. Checks config   │
│  2. Fetches prompts │
│  3. Generates       │
│     summary         │
└──────────┬──────────┘
           │
           │ Reads prompts from
           │
┌──────────▼──────────┐
│  Your GitHub        │
│  Repository         │
│  - system/brief.md │
│  - PATH             │
│  - schema-version   │
└─────────────────────┘
```

---

## Why Use Custom Prompts?

### Use Cases

#### Technical Development Teams
Customize summaries to focus on code changes, bug fixes, and technical decisions:
- Highlight code snippets and file names
- Extract technical terminology accurately
- Emphasize action items and implementation details

#### Community Support Servers
Tailor summaries for customer support:
- Focus on user issues and solutions
- Track unresolved problems requiring follow-up
- Note escalations to development team

#### Gaming Communities
Adjust tone and focus for casual conversations:
- Highlight events and announcements
- Track player meetups and team formations
- Use casual, friendly language

#### Educational Institutions
Optimize for academic discussions:
- Emphasize learning objectives and key concepts
- Extract questions and answers
- Highlight resources and references shared

---

## Quick Start Guide (5 Minutes)

### Prerequisites

- Administrator permissions in your Discord server
- A GitHub account (free)
- 5 minutes of your time

### Steps

#### 1. Create a GitHub Repository (2 minutes)

1. Go to [GitHub](https://github.com) and log in
2. Click the "+" icon → "New repository"
3. Name it something like `my-server-prompts`
4. Make it **Public** (or Private if you have a GitHub token)
5. Check "Add a README file"
6. Click "Create repository"

#### 2. Add Required Files (2 minutes)

Create three files in your repository:

**File 1: `schema-version`**
```
v1
```

**File 2: `PATH`**
```
# Default prompt routing
system/{type}.md
user/{type}.md
```

**File 3: `system/brief.md`**
```
You are an expert at creating concise Discord conversation summaries.

For BRIEF summaries:
- Focus on the main topics discussed
- Keep it under 200 words
- Highlight key decisions or action items
- Use clear, professional language

Response format: Return JSON with "summary" and "key_points" fields.
```

#### 3. Configure the Bot (1 minute)

1. In your Discord server, run:
   ```
   /prompt-config set https://github.com/yourusername/my-server-prompts
   ```

2. The bot will test the connection and confirm:
   ```
   ✅ Repository configured successfully!
   Schema: v1
   Valid patterns found in PATH file
   Prompts will be fetched on next use.
   ```

#### 4. Test It!

Run `/summarize` in any channel. The bot will now use your custom prompt!

---

## Step-by-Step Configuration

### Part 1: Setting Up Your GitHub Repository

#### Create the Repository

1. **Navigate to GitHub**
   - Go to https://github.com
   - Sign in to your account

2. **Create New Repository**
   - Click the "+" icon in the top-right corner
   - Select "New repository"

   ![Creating a new repository](images/github-new-repo.png)

3. **Configure Repository Settings**
   ```
   Repository name: my-discord-prompts
   Description: Custom prompts for Discord SummaryBot
   Visibility: Public (recommended) or Private

   ✓ Add a README file
   ✓ Add .gitignore: None
   ✓ Choose a license: MIT (optional)
   ```

4. **Click "Create repository"**

#### Set Up the Directory Structure

Create the following file structure:

```
my-discord-prompts/
├── schema-version          # Required: Tells bot which format version
├── PATH                    # Required: Routes contexts to prompt files
├── README.md              # Optional: Document your prompts
├── system/                # System prompts directory
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
└── user/                  # User prompts directory
    ├── brief.md
    ├── detailed.md
    └── comprehensive.md
```

### Part 2: Creating Required Files

#### File 1: `schema-version`

This file tells the bot which prompt format version you're using.

**Create the file:**
1. Click "Add file" → "Create new file"
2. Name: `schema-version`
3. Content:
   ```
   v1
   ```
4. Commit the file

**What it does:**
- Ensures compatibility between your prompts and the bot
- Currently only `v1` is supported
- Future versions will add more features

#### File 2: `PATH`

This file determines which prompt file to use based on context.

**Create the file:**
1. Click "Add file" → "Create new file"
2. Name: `PATH`
3. Content:
   ```
   # PATH file - determines which prompts to use

   # Route system prompts by summary type
   system/{type}.md

   # Route user prompts by summary type
   user/{type}.md

   # Fallback if nothing matches
   system/default.md
   ```

**Understanding PATH patterns:**
- `{type}` is replaced with: `brief`, `detailed`, or `comprehensive`
- Patterns are matched from top to bottom
- First matching pattern wins

#### File 3: Create Prompt Files

**Create `system/brief.md`:**
1. Click "Add file" → "Create new file"
2. Name: `system/brief.md` (GitHub auto-creates the `system/` folder)
3. Content:
   ```
   You are an expert at creating concise Discord conversation summaries.

   For BRIEF summaries:
   - Summarize in 2-3 sentences maximum
   - Focus on the main topic and outcome
   - Highlight any decisions made or action items
   - Keep it under 200 words
   - Use professional but friendly language

   Response Format:
   Return a JSON object with the following structure:
   {
     "summary": "2-3 sentence overview of the conversation",
     "key_points": ["Point 1", "Point 2", "Point 3"],
     "action_items": ["Action 1", "Action 2"],
     "participants_count": number,
     "topics": ["Topic 1", "Topic 2"]
   }

   Important:
   - Be factual and objective
   - Don't include timestamps or usernames in the summary
   - Focus on content, not metadata
   ```

Repeat for other files:
- `system/detailed.md`
- `system/comprehensive.md`
- `user/brief.md` (if needed)

### Part 3: Configure the Bot

#### Run the Configuration Command

In your Discord server, use the `/prompt-config set` command:

```
/prompt-config set https://github.com/yourusername/my-discord-prompts
```

**Optional: Specify a branch**
```
/prompt-config set https://github.com/yourusername/my-discord-prompts dev
```
(Defaults to `main` branch if not specified)

#### Verify Configuration

The bot will test your repository and respond with:

**Success:**
```
✅ Repository configured successfully!

Schema Version: v1
Repository: https://github.com/yourusername/my-discord-prompts
Branch: main
Status: All checks passed

Your server will now use custom prompts for summaries.
Cache will refresh automatically every 15 minutes.
```

**Error:**
```
❌ Configuration failed

Error: Cannot access repository
Reason: Repository not found or private without access token

Please check:
- Repository URL is correct
- Repository is public (or you've provided a GitHub token)
- Repository contains required files: schema-version, PATH

Need help? Run /prompt-config test for detailed diagnostics.
```

#### Test Your Configuration

Run the test command to verify everything works:

```
/prompt-config test
```

**Successful test output:**
```
🧪 Testing repository configuration...

✅ Repository accessible
✅ schema-version found: v1
✅ PATH file found and valid
✅ Sample prompt files found
✅ Prompts pass validation

Your configuration is working correctly!
```

---

## Creating Your First PATH File

The PATH file is the routing table that determines which prompt file to use based on the context of the summary request.

### Basic Syntax

```
# Comments start with #
# Empty lines are ignored

# Pattern format: path/to/{variable}/file.md
# Variables are replaced with actual values
```

### Available Template Variables

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `{type}` | Summary length | `brief`, `detailed`, `comprehensive` |
| `{channel}` | Channel name | `general`, `support`, `announcements` |
| `{category}` | Category name | `Support`, `Development`, `Gaming` |
| `{guild}` | Server ID | `123456789` |
| `{role}` | User's highest role | `admin`, `moderator`, `member` |

### Pattern Matching Rules

1. **Patterns are matched top-to-bottom**
   - The first matching pattern is used
   - Put more specific patterns at the top

2. **More specific patterns have priority**
   - `categories/support/channels/help/{type}/system.md` beats
   - `categories/{category}/{type}/system.md` beats
   - `{type}/system.md`

3. **Variables must have values**
   - If a pattern uses `{channel}` but there's no channel context, it won't match

### Examples

#### Example 1: Simple Type-Based Routing

```
# Use different prompts for each summary type
system/brief.md
system/detailed.md
system/comprehensive.md
```

#### Example 2: Type Variable Routing

```
# Use {type} variable for dynamic routing
system/{type}.md
user/{type}.md
```

#### Example 3: Category-Based Routing

```
# Different prompts for different channel categories
categories/support/{type}/system.md
categories/development/{type}/system.md
categories/gaming/{type}/system.md

# Fallback for uncategorized channels
{type}/system.md
```

#### Example 4: Channel-Specific Overrides

```
# Specific override for announcements channel
channels/announcements/system.md

# Category-level defaults
categories/{category}/{type}/system.md

# Type-level fallback
{type}/system.md

# Final fallback
system/default.md
```

#### Example 5: Complex Multi-Level Routing

```
# Most specific: category + channel + type
categories/support/channels/help/{type}/system.md
categories/support/channels/bug-reports/{type}/system.md

# Medium specific: category + type
categories/support/{type}/system.md
categories/development/{type}/system.md
categories/community/{type}/system.md

# Less specific: channel only
channels/announcements/system.md
channels/rules/system.md

# Generic: type only
{type}/system.md
{type}/user.md

# Final fallback
system/default.md
user/default.md
```

### Testing Your PATH File

1. **Validate syntax** using `/prompt-config test`
2. **Test with different contexts**:
   - Try `/summarize` in different channels
   - Try different summary types
   - Check which prompt file gets used in logs

---

## Writing Effective Prompt Templates

### Anatomy of a Good Prompt

#### 1. Clear Role Definition

Start by defining what the AI should be:

```
You are an expert at summarizing technical Discord conversations for software development teams.
```

#### 2. Specific Instructions

Be explicit about what you want:

```
For BRIEF technical summaries:
- Focus on code changes and technical decisions
- Extract specific technical terms and concepts
- Highlight any bugs discussed or fixed
- Note any breaking changes or deprecations
- Keep summary under 200 words
```

#### 3. Format Specification

Define the exact output format:

```
Response Format:
Return a JSON object with this structure:
{
  "summary": "2-3 sentence overview",
  "key_points": ["point 1", "point 2"],
  "code_changes": ["change 1", "change 2"],
  "action_items": ["action 1"]
}
```

#### 4. Constraints and Guidelines

Set boundaries:

```
Important:
- Be factual and objective
- Don't make assumptions about code quality
- Include file names and function names when mentioned
- Don't include usernames or timestamps
```

### Template Variables in Prompts

You can use template variables inside your prompt files:

```
You are summarizing a conversation in the {{channel_name}} channel
of the {{guild_name}} server.

The channel has approximately {{user_count}} active participants.
Category: {{category_name}}
```

**Available variables:**
- `{{guild_name}}` - Server name
- `{{channel_name}}` - Channel name
- `{{category_name}}` - Category name
- `{{user_count}}` - Number of users in conversation

### Examples by Use Case

#### Technical Development Team

```
You are an expert at summarizing technical Discord conversations for software developers.

For DETAILED technical summaries:

Focus Areas:
- Code changes discussed (file names, functions, classes)
- Technical decisions and rationale
- Bugs reported, investigated, or fixed
- Performance considerations or optimizations
- Dependencies added, updated, or removed
- Breaking changes or API modifications

Format Requirements:
- Technical accuracy is paramount
- Include specific terminology
- Extract code snippets if mentioned
- Note testing status
- Highlight security concerns
- Keep summary under 500 words

Response Format:
{
  "summary": "Comprehensive overview of technical discussion",
  "code_changes": ["List of code-related items"],
  "bugs": ["Bugs discussed or fixed"],
  "decisions": ["Technical decisions made"],
  "action_items": ["Implementation tasks"],
  "technologies": ["Technologies/libraries mentioned"]
}

Style:
- Professional technical writing
- Assume reader has technical background
- Use industry-standard terminology
```

#### Customer Support Server

```
You are an expert at summarizing customer support conversations in Discord.

For BRIEF support summaries:

Focus Areas:
- User issues and problems reported
- Solutions provided by support staff
- Workarounds suggested
- Escalations to development team
- Follow-up required
- User satisfaction indicators

Format Requirements:
- Empathetic and customer-focused tone
- Clear problem → solution format
- Note unresolved issues prominently
- Track recurring problems
- Keep summary under 200 words

Response Format:
{
  "summary": "Overview of support interactions",
  "issues_reported": ["Issue 1", "Issue 2"],
  "solutions_provided": ["Solution 1", "Solution 2"],
  "unresolved": ["Unresolved issue 1"],
  "escalations": ["Escalated to dev team"],
  "follow_up_required": true/false
}

Style:
- Professional but friendly
- Focus on outcomes
- Highlight outstanding items
```

#### Gaming Community

```
You are summarizing conversations in a gaming Discord community.

For BRIEF casual summaries:

Focus Areas:
- Events discussed or planned
- Team formations or LFG requests
- Game updates or patch discussions
- Community announcements
- Tournaments or competitions
- Fun moments and highlights

Format Requirements:
- Casual, friendly tone
- Highlight exciting or fun moments
- Note upcoming events
- Keep it engaging
- Keep summary under 150 words

Response Format:
{
  "summary": "Quick overview of the conversation",
  "events": ["Upcoming events"],
  "highlights": ["Fun or notable moments"],
  "lfg": ["Team formation requests"],
  "announcements": ["Important news"]
}

Style:
- Casual and enthusiastic
- Use gaming terminology
- Keep it light and fun
```

### Dos and Don'ts

#### Do:
- Be specific about what you want
- Define the exact output format
- Set clear constraints (word count, tone, focus)
- Test your prompts with real conversations
- Iterate based on results

#### Don't:
- Make prompts too long (>50KB)
- Use executable code patterns (`eval`, `exec`, etc.)
- Include personal information
- Make assumptions about users
- Over-complicate the instructions

---

## Troubleshooting Common Issues

### Issue 1: "Repository not found"

**Error message:**
```
❌ Cannot access repository
Repository not found or private without access token
```

**Possible causes:**
1. Repository URL is incorrect
2. Repository is private and bot doesn't have access
3. Repository was deleted

**Solutions:**
1. **Verify the URL**
   - Copy URL from browser address bar
   - Format: `https://github.com/username/repository`
   - No `.git` extension needed

2. **Check repository visibility**
   - Go to your repository settings
   - Under "Danger Zone" check if it's private
   - Either make it public or configure a GitHub token

3. **Test manually**
   - Try opening the repository URL in a private browser window
   - If you can't see it, neither can the bot

### Issue 2: "Invalid schema version"

**Error message:**
```
❌ Configuration failed
Unsupported schema version: v2
```

**Possible causes:**
1. Schema version file contains unsupported version
2. File contains extra whitespace or characters

**Solutions:**
1. **Check `schema-version` file**
   ```
   v1
   ```
   - Should contain only `v1` (no extra lines, spaces, or characters)

2. **Verify file encoding**
   - Use UTF-8 encoding
   - No BOM (Byte Order Mark)

3. **Re-create the file**
   - Delete and recreate `schema-version`
   - Copy `v1` exactly

### Issue 3: "PATH file syntax error"

**Error message:**
```
❌ PATH file has syntax errors on line 5
Invalid template parameter: {custom}
```

**Possible causes:**
1. Using invalid template variables
2. Typos in variable names
3. Malformed file paths

**Solutions:**
1. **Use only valid variables**
   - `{type}`, `{channel}`, `{category}`, `{guild}`, `{role}`
   - Not: `{custom}`, `{user}`, `{date}`

2. **Check for typos**
   ```
   # Wrong
   system/{typ}.md

   # Correct
   system/{type}.md
   ```

3. **Validate path format**
   ```
   # Wrong - absolute path
   /system/brief.md

   # Correct - relative path
   system/brief.md
   ```

### Issue 4: "Prompt file not found"

**Error message:**
```
⚠️ Using default prompt
Configured prompt file not found: system/brief.md
```

**Possible causes:**
1. File doesn't exist in repository
2. File path in PATH doesn't match actual file
3. Case sensitivity mismatch

**Solutions:**
1. **Verify file exists**
   - Check repository on GitHub
   - Confirm exact path: `system/brief.md`

2. **Check case sensitivity**
   - GitHub is case-sensitive
   - `System/Brief.md` ≠ `system/brief.md`

3. **Match PATH patterns**
   - If PATH says `system/{type}.md`
   - You need `system/brief.md`, `system/detailed.md`, etc.

### Issue 5: "Using default prompts"

**Error message:**
```
ℹ️ Using default prompts (custom repository unavailable)
```

**Possible causes:**
1. GitHub is temporarily down
2. Repository was deleted
3. Network connectivity issue
4. Rate limit exceeded

**Solutions:**
1. **Check GitHub status**
   - Visit https://www.githubstatus.com
   - Wait for service restoration

2. **Verify repository exists**
   - Open repository URL in browser
   - Confirm it wasn't deleted

3. **Check rate limits**
   - Run `/prompt-config status`
   - Wait if rate limited (resets every hour)

4. **Force refresh**
   ```
   /prompt-config refresh
   ```

### Issue 6: "Prompt validation failed"

**Error message:**
```
❌ Prompt file rejected
Suspicious pattern detected: eval(
```

**Possible causes:**
1. Prompt contains security-sensitive patterns
2. Accidentally included code
3. File is corrupted or binary

**Solutions:**
1. **Remove suspicious patterns**
   - No `eval()`, `exec()`, `__import__`
   - No `<script>` tags
   - No system commands

2. **Verify file is text**
   - Open in text editor
   - Should be readable text
   - No binary or compiled code

3. **Check file size**
   - Must be under 50KB
   - If larger, split into multiple files

### Getting More Help

#### Diagnostic Command

Run comprehensive diagnostics:
```
/prompt-config test
```

This checks:
- Repository accessibility
- File existence
- Schema validation
- PATH syntax
- Prompt content validation

#### Status Command

Check current configuration:
```
/prompt-config status
```

Shows:
- Repository URL and branch
- Schema version
- Last fetch status
- Cache statistics
- Error count

#### Support Resources

- Documentation: `/docs/external-prompts-*.md`
- Example repository: https://github.com/discord-summary-bot/prompt-templates
- Discord support server: [link]
- GitHub issues: [link]

---

## Best Practices and Tips

### Organization

#### 1. Use Clear Directory Structure

```
my-prompts/
├── schema-version
├── PATH
├── README.md              ← Document your prompts
├── system/                ← System prompts
│   ├── brief.md
│   ├── detailed.md
│   └── comprehensive.md
├── user/                  ← User prompts
│   └── default.md
├── categories/            ← Category-specific
│   ├── support/
│   └── development/
└── channels/              ← Channel-specific
    └── announcements/
```

#### 2. Document Your Prompts

Create a `README.md` in your repository:

```markdown
# My Server's Custom Prompts

## Overview
These prompts are optimized for [your use case].

## File Structure
- `system/brief.md` - Short summaries for quick updates
- `system/detailed.md` - Comprehensive summaries
- `categories/support/` - Customer support specific prompts

## Template Variables
- We use {category} for category-based routing
- We use {type} for summary length

## Maintenance
- Updated: Monthly
- Owner: @username
- Questions: #admin-channel
```

### Testing

#### 1. Test Before Deploying

1. Create a test branch:
   ```bash
   git checkout -b test-prompts
   ```

2. Configure bot to use test branch:
   ```
   /prompt-config set https://github.com/user/repo test-prompts
   ```

3. Test thoroughly, then merge to main:
   ```bash
   git checkout main
   git merge test-prompts
   ```

4. Update bot to main branch:
   ```
   /prompt-config set https://github.com/user/repo main
   ```

#### 2. Use Different Branches for Environments

```
main         → Production prompts
development  → Testing new prompts
experimental → Radical changes
```

### Performance

#### 1. Minimize Prompt Size

- Keep prompts under 10KB when possible
- Smaller prompts = faster loading
- Remove unnecessary whitespace

#### 2. Use Caching Effectively

- Bot caches prompts for 15 minutes
- Changes take effect after cache expires
- Force refresh: `/prompt-config refresh`

#### 3. Optimize PATH Patterns

- Put most common patterns first
- Use variables instead of hardcoding
- Fewer patterns = faster matching

### Security

#### 1. Review Changes Carefully

- Never include secrets or tokens
- Review all commits before merging
- Use pull requests for team review

#### 2. Use Branch Protection

In GitHub repository settings:
- Enable "Require pull request reviews"
- Enable "Require status checks to pass"
- Protect main branch from direct commits

#### 3. Monitor Usage

- Check `/prompt-config status` regularly
- Watch for unexpected errors
- Review bot logs if available

### Maintenance

#### 1. Regular Updates

- Review prompt effectiveness monthly
- Update based on user feedback
- Keep up with bot feature updates

#### 2. Version Your Prompts

Use git tags for major versions:

```bash
git tag -a v1.0 -m "Initial production prompts"
git tag -a v1.1 -m "Added support category prompts"
git push --tags
```

#### 3. Backup Your Prompts

- Git provides automatic backup
- Consider forking to personal account
- Export prompts locally periodically

### Collaboration

#### 1. Team Workflow

1. **Create issues for prompt changes**
   ```
   Title: Improve technical summary prompts
   Description: Current prompts don't emphasize code changes enough
   ```

2. **Use pull requests**
   - Branch: `feature/improve-tech-prompts`
   - Make changes
   - Open PR for review
   - Test using PR branch
   - Merge when approved

3. **Document decisions**
   - Why certain prompts were chosen
   - What problems they solve
   - Expected outcomes

#### 2. Share Templates

- Create reusable prompt fragments
- Share with community
- Contribute to example repository

### Advanced Tips

#### 1. A/B Testing Prompts

Use branches to test different approaches:

```bash
# Create two test branches
git checkout -b variant-a
# Edit prompts...
git commit -m "Variant A: Focus on decisions"

git checkout main
git checkout -b variant-b
# Edit prompts differently...
git commit -m "Variant B: Focus on outcomes"
```

Switch bot between branches and compare results.

#### 2. Prompt Templates Repository

Create a library of reusable fragments:

```
templates/
├── headers/
│   ├── technical.md
│   └── casual.md
├── formats/
│   ├── json-format.md
│   └── markdown-format.md
└── constraints/
    ├── word-limits.md
    └── style-guides.md
```

Copy and combine as needed for specific prompts.

#### 3. Automated Testing

Create test cases in your repository:

```
tests/
├── test-cases.md
└── expected-outputs/
    ├── case-1-expected.json
    └── case-2-expected.json
```

Compare actual bot output against expected output.

---

## Next Steps

Now that you understand the basics:

1. **Create your repository** using the Quick Start guide
2. **Customize your prompts** for your specific use case
3. **Test thoroughly** before rolling out to your server
4. **Monitor and iterate** based on results
5. **Share your learnings** with the community

### Additional Resources

- **Administrator Reference**: `docs/external-prompts-admin-reference.md`
- **Template Repository Guide**: `docs/external-prompts-template-repo.md`
- **FAQ**: `docs/external-prompts-faq.md`
- **Technical Specification**: `docs/external-prompt-hosting-spec.md`

### Getting Help

- Discord support server: [link]
- GitHub discussions: [link]
- Report bugs: [link]

---

**Happy Prompting!** 🎉

If you create interesting prompt templates, consider sharing them with the community!
