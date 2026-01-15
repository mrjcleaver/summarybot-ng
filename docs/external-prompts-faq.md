# External Prompt Hosting - Frequently Asked Questions

Version: 1.0.0
Last Updated: 2026-01-14

---

## Table of Contents

- [General Questions](#general-questions)
- [Getting Started](#getting-started)
- [Repository Setup](#repository-setup)
- [Configuration](#configuration)
- [PATH File](#path-file)
- [Prompt Writing](#prompt-writing)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)
- [Security](#security)
- [Advanced Usage](#advanced-usage)

---

## General Questions

### What is external prompt hosting?

External prompt hosting allows you to store custom summarization prompts in a GitHub repository instead of using the bot's built-in prompts. The bot fetches your prompts from GitHub when generating summaries.

**Benefits:**
- Customize summaries for your server's needs
- Update prompts anytime without bot restart
- Version control your prompts with git
- Share prompts across multiple servers
- A/B test different prompt approaches

### Do I need to know programming to use this feature?

**No!** You only need to:
1. Create a GitHub account (free)
2. Create files with text instructions
3. Run a Discord command to configure it

No coding required. Basic text editing skills are sufficient.

### Is this feature free?

**Yes!** External prompt hosting is completely free:
- Free GitHub account
- Free public repositories
- No additional bot fees
- Optional: Private repositories require GitHub account upgrade

### Will my summaries still work if my repository is down?

**Yes!** The bot has multiple fallback mechanisms:
1. Uses cached prompts (up to 24 hours old)
2. Falls back to default prompts automatically
3. Summaries continue working seamlessly

You'll see a notice if using fallback prompts.

---

## Getting Started

### How do I create my first prompt repository?

**Quick version:**

1. Create GitHub repository (public)
2. Add three files:
   - `schema-version` containing `v1`
   - `PATH` containing routing rules
   - `system/brief.md` containing your prompt
3. Run `/prompt-config set https://github.com/your/repo` in Discord

See the [User Guide](external-prompts-user-guide.md#quick-start-guide-5-minutes) for detailed steps.

### What files are required at minimum?

**Absolute minimum:**
```
my-repo/
├── schema-version    # Contains: v1
├── PATH              # Contains: system/{type}.md
└── system/
    └── brief.md     # Your custom prompt
```

**Recommended minimum:**
```
my-repo/
├── README.md         # Documentation
├── schema-version
├── PATH
└── system/
    ├── brief.md
    ├── detailed.md
    └── comprehensive.md
```

### Can I see an example repository?

**Yes!** We provide a template repository:
https://github.com/discord-summary-bot/prompt-templates

You can:
- View it for reference
- Fork it as a starting point
- Copy patterns you like

### How long does setup take?

**First time:** ~10-15 minutes
- Create GitHub account: 2 minutes
- Create repository: 2 minutes
- Add required files: 5 minutes
- Configure bot: 1 minute
- Test: 2 minutes

**After first time:** ~5 minutes to create new repositories

---

## Repository Setup

### Should I make my repository public or private?

**Public (Recommended):**
- ✅ No authentication needed
- ✅ Easy to share
- ✅ Free on GitHub
- ✅ Community can learn from your prompts
- ❌ Anyone can view your prompts

**Private:**
- ✅ Prompts stay confidential
- ✅ Suitable for commercial use
- ✅ Control access
- ❌ Requires GitHub token setup
- ❌ May require paid GitHub account

**Recommendation:** Start with public, switch to private if needed.

### Can multiple servers use the same repository?

**Yes!** Multiple Discord servers can share one repository.

**Use cases:**
- Organization with multiple Discord servers
- Community network
- Testing across servers

**Per-server customization:**
Use `{guild}` variable in PATH:
```
guilds/{guild}/system/{type}.md    # Server-specific
system/{type}.md                   # Shared default
```

### How do I organize prompts for multiple use cases?

**By category:**
```
categories/
├── support/
├── development/
├── community/
└── events/
```

**By channel:**
```
channels/
├── announcements/
├── help/
└── general/
```

**By type:**
```
system/
├── brief.md
├── detailed.md
└── comprehensive.md
```

**Combined:**
```
categories/support/
├── brief.md
└── detailed.md
categories/development/
├── brief.md
└── comprehensive.md
```

### Can I have multiple branches for testing?

**Yes! Recommended workflow:**

```
main         → Production (stable)
staging      → Testing before production
dev          → Active development
feature/*    → Experimental changes
```

**Switch branches:**
```
# Use development branch
/prompt-config set https://github.com/user/repo dev

# Switch back to production
/prompt-config set https://github.com/user/repo main
```

---

## Configuration

### How do I configure the bot to use my repository?

Run this command in your Discord server:
```
/prompt-config set https://github.com/yourusername/your-repo
```

Optionally specify branch:
```
/prompt-config set https://github.com/yourusername/your-repo dev
```

Requires Administrator permission.

### How do I check if my configuration is working?

**Three commands:**

1. **Status check:**
   ```
   /prompt-config status
   ```
   Shows current configuration and statistics

2. **Test configuration:**
   ```
   /prompt-config test
   ```
   Runs diagnostics on your repository

3. **Test actual summary:**
   ```
   /summarize
   ```
   Generate a summary and check which prompt was used

### How long does it take for changes to appear?

**Automatic:** 15 minutes (cache TTL)
- Bot caches prompts for 15 minutes
- After 15 minutes, changes automatically appear

**Manual refresh:**
```
/prompt-config refresh
```
Changes appear immediately (within seconds)

### Can I switch back to default prompts?

**Yes, easily:**

**Temporary:** Wait for your repository to be unavailable
- Bot automatically falls back to defaults

**Permanent:**
```
/prompt-config remove
```
Removes configuration and returns to defaults

You can reconfigure anytime later.

### What happens if I change the repository URL?

Run the set command again with new URL:
```
/prompt-config set https://github.com/newuser/newrepo
```

**What happens:**
1. Old configuration removed
2. New repository validated
3. Cache cleared
4. New prompts fetched
5. New configuration saved

Old prompts immediately replaced.

---

## PATH File

### What is the PATH file?

The PATH file is a configuration file that tells the bot which prompt file to use based on context (channel, category, summary type, etc.).

**Think of it as a routing table:**
```
If in Support category + brief → categories/support/brief.md
If in #announcements → channels/announcements/system.md
Otherwise → system/default.md
```

### What variables can I use in PATH patterns?

**Available variables (v1):**

| Variable | Description | Example |
|----------|-------------|---------|
| `{type}` | Summary length | `brief`, `detailed`, `comprehensive` |
| `{channel}` | Channel name | `general`, `support` |
| `{category}` | Category name | `support`, `development` |
| `{guild}` | Server ID | `123456789` |
| `{role}` | User's highest role | `admin`, `member` |

See [Template Variable Reference](external-prompts-template-repo.md#template-variable-reference) for details.

### How does pattern matching work?

**Top to bottom, first match wins:**

```
# PATH file
categories/support/channels/help/{type}/system.md  # Most specific
categories/{category}/{type}/system.md             # Less specific
{type}/system.md                                   # Generic
system/default.md                                  # Fallback
```

**For a summary in #help in Support category:**
1. Check: `categories/support/channels/help/brief/system.md` ✅ Match!
2. Stop here, use this file

**For a summary in #general (no category):**
1. Check: `categories/support/channels/help/brief/system.md` ❌ No category
2. Check: `categories/{category}/brief/system.md` ❌ No category
3. Check: `brief/system.md` ✅ Match!
4. Stop here, use this file

### Can I use wildcards or regex?

**No, but template variables are similar:**

**Not supported:**
```
system/*.md           # Wildcards
system/[a-z]+.md      # Regex
system/brief?.md      # Globbing
```

**Use template variables instead:**
```
system/{type}.md      # Matches brief, detailed, comprehensive
categories/{category}/{type}/system.md  # Matches any category + type
```

### What if no pattern matches?

**Bot tries fallback chain:**
1. Default file for summary type: `system/{type}.md`
2. Generic default: `system/default.md`
3. Built-in default prompt (always works)

**You always get a summary**, even if PATH has errors.

---

## Prompt Writing

### What makes a good prompt?

**Four key elements:**

1. **Clear role:**
   ```
   You are an expert at summarizing technical Discord conversations.
   ```

2. **Specific instructions:**
   ```
   For BRIEF summaries:
   - Focus on main decisions
   - Keep under 200 words
   - Highlight action items
   ```

3. **Format definition:**
   ```
   Response Format:
   {
     "summary": "text",
     "key_points": ["point1", "point2"]
   }
   ```

4. **Constraints:**
   ```
   Important:
   - Be factual and objective
   - Don't include usernames
   - Keep under 200 words
   ```

### How long should a prompt be?

**Recommendations:**

- **Minimum:** 50 characters (too short is ineffective)
- **Optimal:** 500-2000 characters (clear and detailed)
- **Maximum:** 50 KB (technical limit)

**For different summary types:**
- Brief: 500-1000 characters
- Detailed: 1000-2000 characters
- Comprehensive: 2000-4000 characters

### Can I use special formatting in prompts?

**Plain text only:**
- ✅ Line breaks
- ✅ Spaces and indentation
- ✅ Basic punctuation
- ❌ Markdown formatting (processed as text)
- ❌ HTML tags (security risk)
- ❌ Code execution (blocked)

**Example:**
```
You are summarizing Discord conversations.

For BRIEF summaries:
- Point 1
- Point 2
- Point 3

Response Format:
{
  "summary": "text"
}
```

### Can I use template variables inside prompts?

**Yes!** Use double curly braces:

```
You are summarizing a conversation in the {{channel_name}} channel
of the {{guild_name}} server.

This channel has approximately {{user_count}} active participants.
```

**Available prompt variables:**
- `{{guild_name}}` - Server name
- `{{channel_name}}` - Channel name (with #)
- `{{category_name}}` - Category name
- `{{user_count}}` - Number of participants
- `{{message_count}}` - Number of messages

### How do I test if my prompts are effective?

**Testing strategies:**

1. **Try with real conversations:**
   ```
   /summarize brief
   ```
   Check if output matches expectations

2. **Compare with default:**
   - Remove configuration temporarily
   - Generate summary with default prompt
   - Reconfigure with your prompt
   - Generate summary with your prompt
   - Compare results

3. **A/B testing:**
   - Create branch A with prompt variant 1
   - Create branch B with prompt variant 2
   - Switch between branches
   - Compare results

4. **Collect feedback:**
   - Ask server members for feedback
   - Iterate based on responses

---

## Troubleshooting

### "Repository not found" error

**Causes:**
1. Repository URL incorrect
2. Repository is private (requires token)
3. Repository was deleted
4. Typo in URL

**Solutions:**
1. Verify URL format: `https://github.com/username/repo`
2. Check repository exists (open in browser)
3. Make repository public OR configure token
4. Copy URL from browser address bar

### "Invalid schema version" error

**Cause:** `schema-version` file contains invalid content

**Solution:**
1. Edit `schema-version` file
2. Make it contain exactly: `v1`
3. No extra lines, spaces, or characters
4. Save with UTF-8 encoding

**Correct format:**
```
v1
```

### "PATH file syntax error" error

**Causes:**
1. Invalid template variables
2. Path traversal attempt (`../`)
3. Invalid characters
4. Unclosed braces

**Solutions:**
1. Use only valid variables: `{type}`, `{channel}`, `{category}`, `{guild}`, `{role}`
2. Use relative paths only (no `../` or absolute paths)
3. Use only letters, numbers, hyphens, slashes, dots
4. Check all `{` have matching `}`

**Validate syntax:**
```
/prompt-config test
```

### "Prompt file not found" error

**Causes:**
1. File doesn't exist in repository
2. Filename case mismatch
3. PATH references wrong file

**Solutions:**
1. Check file exists on GitHub
2. Verify exact filename (case-sensitive)
3. Update PATH to match actual files

**Example:**
```
# PATH says:
system/{type}.md

# You need files:
system/brief.md
system/detailed.md
system/comprehensive.md
```

### Bot using default prompts instead of mine

**Causes:**
1. Cache still fresh (wait 15 min)
2. GitHub API error (temporary)
3. Configuration not saved
4. Prompt validation failed

**Solutions:**
1. Force refresh: `/prompt-config refresh`
2. Check status: `/prompt-config status`
3. Run diagnostics: `/prompt-config test`
4. Check logs for errors

### Changes not appearing

**Likely cause:** Cache not refreshed yet

**Solutions:**

**Wait 15 minutes:**
Cache automatically expires and refreshes

**Manual refresh:**
```
/prompt-config refresh
```

**Verify cache cleared:**
```
/prompt-cache stats
```
Check "Last Refresh" time

---

## Performance

### How fast are external prompts?

**Cache hit (85% of requests):**
- Latency: <5ms
- Same as built-in prompts
- No noticeable delay

**Cache miss (15% of requests):**
- Latency: 500-1000ms
- GitHub fetch + validation
- Slightly slower but acceptable

**First request after cache clear:**
- Latency: 1000-2000ms
- Fetches multiple files
- Subsequent requests fast

### How often does the bot fetch from GitHub?

**Automatic fetching:**
- Every 15 minutes when cache expires
- Only when summaries are requested
- Shared across multiple servers using same repo

**Manual fetching:**
- When you run `/prompt-config refresh`
- When configuration changes
- When testing with `/prompt-config test`

### Will this use a lot of GitHub API requests?

**Typical usage:**
- 4 automatic refreshes per hour
- ~100 requests per day per active server
- Well within GitHub limits (5,000/hour with token)

**GitHub rate limits:**
- Without token: 60 requests/hour (not recommended for production)
- With token: 5,000 requests/hour (sufficient for most use cases)

### How much GitHub API quota does my server use?

Check current usage:
```
/prompt-cache stats 24h
```

Look for: "GitHub API Usage: X requests (24h)"

**Typical usage:**
- Low activity server: 20-50 requests/day
- Medium activity: 50-100 requests/day
- High activity: 100-300 requests/day

### Can I optimize for faster performance?

**Yes! Several strategies:**

1. **Minimize file count:**
   ```
   # Instead of:
   categories/A/brief.md
   categories/A/detailed.md
   categories/B/brief.md
   categories/B/detailed.md

   # Use:
   system/brief.md
   system/detailed.md
   ```

2. **Reduce file sizes:**
   - Keep prompts under 10 KB
   - Remove unnecessary text
   - Be concise

3. **Use public repository:**
   - Faster than private (no auth overhead)
   - Better for high-traffic servers

4. **Optimize PATH patterns:**
   - Fewer patterns = faster matching
   - Most common patterns first

---

## Security

### Is it safe to store prompts on GitHub?

**Yes, if you follow best practices:**

**Safe:**
- ✅ Prompt instructions
- ✅ Format specifications
- ✅ Style guidelines
- ✅ Template configurations

**Never include:**
- ❌ API keys or tokens
- ❌ Passwords
- ❌ Personal information
- ❌ Confidential business data
- ❌ Executable code

### What if someone malicious edits my repository?

**Protection measures:**

1. **Repository permissions:**
   - Only trusted contributors
   - Enable branch protection
   - Require pull request reviews

2. **Validation:**
   - Bot validates all content
   - Blocks suspicious patterns
   - Rejects files with code execution

3. **Audit trail:**
   - Git tracks all changes
   - View history: `git log`
   - Revert bad changes: `git revert`

4. **Worst case:**
   - Bot falls back to safe defaults
   - No code execution possible
   - Summaries continue working

### What security checks does the bot perform?

**Content validation:**
```
✓ Check file size (<50 KB)
✓ Verify UTF-8 encoding
✓ Scan for executable code patterns
✓ Block eval(), exec(), system commands
✓ Prevent path traversal
✓ Sanitize template variables
```

**Rejected patterns:**
- `eval(`
- `exec(`
- `subprocess.`
- `os.system`
- `<script>`
- `../` path traversal

### Can I use private repositories securely?

**Yes, with proper token management:**

1. **Generate GitHub PAT (Personal Access Token):**
   - GitHub Settings → Developer settings
   - Generate token with `repo:read` scope
   - Copy token

2. **Provide to bot administrator:**
   - Don't share in Discord channels
   - Use secure direct message
   - Bot encrypts and stores safely

3. **Token security:**
   - Stored encrypted (AES-256)
   - Never logged or exposed
   - Rotate every 90 days

### Who can change my server's prompt configuration?

**Permission requirements:**

1. **Server Owner:** Always allowed
2. **Administrator permission:** Allowed
3. **Bot Manager role:** Allowed (if configured)
4. **Everyone else:** Denied

**Check permissions:**
```
/prompt-config status
```
Only authorized users can run set/remove commands.

---

## Advanced Usage

### Can I test prompts locally before deploying?

**Yes! Use branches:**

1. Create test branch:
   ```bash
   git checkout -b test-new-prompts
   ```

2. Make changes and commit:
   ```bash
   git add .
   git commit -m "Test: New technical prompts"
   git push origin test-new-prompts
   ```

3. Configure bot to use test branch:
   ```
   /prompt-config set https://github.com/user/repo test-new-prompts
   ```

4. Test in Discord

5. If good, merge to main:
   ```bash
   git checkout main
   git merge test-new-prompts
   git push origin main
   ```

6. Switch bot back to main:
   ```
   /prompt-config set https://github.com/user/repo main
   ```

### How do I version my prompts?

**Use git tags:**

```bash
# Tag major versions
git tag -a v1.0 -m "Initial production prompts"
git tag -a v1.1 -m "Added support category prompts"
git tag -a v2.0 -m "Complete redesign for v2"

# Push tags
git push --tags

# Configure bot to use specific version
/prompt-config set https://github.com/user/repo
git checkout v1.0
```

**Version in filenames:**
```
system/
├── brief-v1.md
├── brief-v2.md
└── brief-v3.md
```

### Can I share prompts between multiple repositories?

**Not directly, but you can:**

1. **Fork and customize:**
   - Fork base repository
   - Customize for your needs
   - Configure bot to use your fork

2. **Copy files:**
   - Copy prompt files to your repository
   - Modify as needed
   - Maintain separately

3. **Future: Include directives (v2):**
   - Reference external prompts
   - Compose from multiple sources

### How do I migrate from v1 to v2 when it's released?

**Migration will be gradual and backwards-compatible:**

1. **v1 prompts continue working**
   - No breaking changes
   - No forced migration
   - Upgrade when ready

2. **Test v2 in branch:**
   - Create v2 branch
   - Update schema-version to v2
   - Add v2 features
   - Test thoroughly

3. **Gradual adoption:**
   - Keep v1 as fallback
   - Add v2 features incrementally
   - Merge when stable

See [Migration Guide](external-prompts-template-repo.md#migration-guide-v1-to-v2) for details.

### Can I automate prompt updates?

**Current:** Manual updates via git push + wait 15 min or refresh

**Planned (Future):**
- GitHub webhook integration
- Automatic cache refresh on push
- Zero-delay updates

**Workaround:** Script to push and refresh:
```bash
#!/bin/bash
git add .
git commit -m "Update prompts"
git push

# Then manually run in Discord:
# /prompt-config refresh
```

### How do I monitor prompt performance?

**Metrics to track:**

1. **Cache hit rate:**
   ```
   /prompt-cache stats
   ```
   Target: >85%

2. **Fetch latency:**
   ```
   /prompt-config status
   ```
   Target: <1000ms

3. **Error rate:**
   ```
   /prompt-config status
   ```
   Target: <5%

4. **User feedback:**
   - Ask users if summaries improved
   - Compare before/after
   - Iterate based on feedback

---

## Getting Help

### Where can I find more documentation?

**Core documentation:**
- **User Guide:** `docs/external-prompts-user-guide.md`
- **Admin Reference:** `docs/external-prompts-admin-reference.md`
- **Template Guide:** `docs/external-prompts-template-repo.md`
- **This FAQ:** `docs/external-prompts-faq.md`

**Technical documentation:**
- **Specification:** `docs/external-prompt-hosting-spec.md`
- **Pseudocode:** `docs/external-prompt-hosting-pseudocode.md`

### How do I report a bug?

**Steps:**
1. Run diagnostics: `/prompt-config test`
2. Check status: `/prompt-config status`
3. Gather information:
   - Error messages
   - Repository URL
   - When it started
4. Report:
   - Discord support server: [link]
   - GitHub issues: [link]

### Where can I get help with my prompts?

**Resources:**
- Discord support server: [link]
- Example repository: https://github.com/discord-summary-bot/prompt-templates
- Community discussions: [link]
- GitHub discussions: [link]

### Can I contribute my prompts to the community?

**Yes! We encourage it:**

1. **Share your repository:**
   - Make it public
   - Add good documentation
   - Share link in community

2. **Submit to examples:**
   - Fork template repository
   - Add your prompts as example
   - Submit pull request

3. **Write guide:**
   - Document your approach
   - Share lessons learned
   - Help others

**Your prompts could help hundreds of servers!**

---

## Still have questions?

- **Discord support server:** [link]
- **GitHub discussions:** [link]
- **Email support:** [email]
- **Documentation:** https://docs.discord-summary-bot.com

**We're here to help!** 🚀
