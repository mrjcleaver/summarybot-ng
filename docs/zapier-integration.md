# Zapier Integration Guide for SummaryBot-NG

## Overview
This guide shows how to trigger Discord message summarizations from Zapier using the webhook API.

## Quick Setup

### Step 1: Choose Your Zapier Trigger
Pick any Zapier trigger event that should create a summary:
- **Schedule by Zapier** - Daily/weekly summary generation
- **Gmail** - Summarize when new email arrives
- **Slack** - Summarize Slack conversations
- **Google Sheets** - Trigger from spreadsheet updates
- **Webhooks** - Custom webhook triggers
- **Any other Zapier app**

### Step 2: Add Webhooks by Zapier Action

1. Click **+ Add Step** in your Zap
2. Search for **Webhooks by Zapier**
3. Choose **POST** as the action event
4. Click **Continue**

### Step 3: Configure the Webhook

**URL:**
```
https://summarybot-ng.fly.dev/api/v1/summaries
```

**Payload Type:** `json`

**Data:** (See templates below)

**Headers:**
```
Content-Type: application/json
X-API-Key: test-api-key-12345
```

### Step 4: Choose Your Template

## Template 1: Simple Summary (Minimum Fields)

```json
{
  "messages": [
    {
      "id": "msg-001",
      "author_name": "User1",
      "author_id": "123456",
      "content": "First message content",
      "timestamp": "2026-01-06T10:00:00"
    },
    {
      "id": "msg-002",
      "author_name": "User2",
      "author_id": "234567",
      "content": "Second message content",
      "timestamp": "2026-01-06T10:01:00"
    }
  ],
  "channel_id": "zapier-channel",
  "guild_id": "zapier-guild"
}
```

## Template 2: Full Options

```json
{
  "messages": [
    {
      "id": "msg-001",
      "author_name": "Alice",
      "author_id": "111111",
      "content": "Message content here",
      "timestamp": "2026-01-06T10:00:00"
    }
  ],
  "channel_id": "zapier-channel-123",
  "guild_id": "zapier-guild-456",
  "options": {
    "summary_length": "brief",
    "include_bots": false,
    "min_messages": 3
  }
}
```

### Summary Length Options:
- `"brief"` - Short, concise summary (2-3 sentences)
- `"detailed"` - Medium-length summary (1 paragraph)
- `"comprehensive"` - Detailed summary with full context

## Template 3: Dynamic Data from Zapier Fields

Use Zapier's field mapping to populate dynamic data:

```json
{
  "messages": [
    {
      "id": "{{trigger.message_id}}",
      "author_name": "{{trigger.author_name}}",
      "author_id": "{{trigger.author_id}}",
      "content": "{{trigger.message_content}}",
      "timestamp": "{{trigger.timestamp}}"
    }
  ],
  "channel_id": "{{trigger.channel_id}}",
  "guild_id": "zapier-integration",
  "options": {
    "summary_length": "detailed",
    "include_bots": false
  }
}
```

## Common Use Cases

### 1. Daily Digest Zap
**Trigger:** Schedule by Zapier (Daily at 5 PM)
**Action:** Webhook POST to generate summary
**Use Case:** Daily summary of all messages from the day

### 2. Email-Triggered Summary
**Trigger:** Gmail - New Email Matching Search
**Action:** Webhook POST with email content as messages
**Use Case:** Summarize email threads automatically

### 3. Slack Channel Digest
**Trigger:** Slack - New Message Posted to Channel
**Action:** Webhook POST to summarize conversation
**Use Case:** Cross-post Slack summaries to Discord

### 4. Meeting Notes Summary
**Trigger:** Google Calendar - Event Ended
**Action:** Webhook POST to summarize meeting notes
**Use Case:** Auto-generate meeting summaries

## Response Format

The API returns a summary object:

```json
{
  "id": "sum_1767657814",
  "channel_id": "zapier-channel-123",
  "guild_id": "zapier-guild-456",
  "summary_text": "Brief overview of the conversation...",
  "key_points": [
    "First key point",
    "Second key point"
  ],
  "action_items": [],
  "message_count": 5,
  "start_time": "2026-01-06T10:00:00",
  "end_time": "2026-01-06T10:05:00",
  "metadata": {
    "input_tokens": 488,
    "output_tokens": 293,
    "total_tokens": 781
  }
}
```

## Using the Response in Zapier

After the webhook action, you can:
1. **Send to Slack** - Post the summary to a Slack channel
2. **Email** - Send summary via Gmail/Outlook
3. **Google Sheets** - Log summaries to a spreadsheet
4. **Discord** - Post back to Discord using Discord webhook
5. **Notion** - Save to a Notion database
6. **Any other Zapier action**

### Example: Post Summary to Slack

1. Add **Slack** action after webhook
2. Choose **Send Channel Message**
3. Map fields:
   - **Message Text:** `{{webhook.summary_text}}`
   - **Additional Info:** `Key Points: {{webhook.key_points}}`

## Authentication

### Development/Testing
Use any API key with 10+ characters:
```
X-API-Key: test-api-key-12345
```

### Production
Request a secure API key and store it in Zapier's secure storage:
1. Go to Zap settings
2. Store API key as a secret
3. Reference it in headers: `{{secret.API_KEY}}`

## Troubleshooting

### Error: "Authentication required"
- Ensure `X-API-Key` header is set
- Key must be at least 10 characters

### Error: "'concise' is not a valid SummaryLength"
- Change `summary_length` to: `"brief"`, `"detailed"`, or `"comprehensive"`

### Error: "Validation error"
- Check all required fields are present: `messages`, `channel_id`, `guild_id`
- Each message needs: `id`, `author_name`, `author_id`, `content`, `timestamp`
- Timestamps must be in ISO 8601 format: `2026-01-06T10:00:00`

### Rate Limiting
- Default: 100 requests per minute
- If exceeded, wait 60 seconds and retry

## Advanced: Multi-Step Zap Example

### Zap: "Daily Discord Summary from Google Sheets"

1. **Trigger:** Schedule by Zapier (Daily at 9 AM)
2. **Action 1:** Google Sheets - Lookup Spreadsheet Rows
   - Find all messages from yesterday
3. **Action 2:** Code by Zapier (JavaScript)
   - Transform rows into message array format
4. **Action 3:** Webhooks by Zapier (POST)
   - Send to summary API
5. **Action 4:** Discord Webhook
   - Post summary back to Discord channel

## Testing Your Zap

1. Click **Test & Continue** in Zapier
2. Verify the webhook response appears
3. Check that `summary_text` contains content
4. Ensure no error fields in response
5. Turn on your Zap!

## Support

- API Endpoint: https://summarybot-ng.fly.dev
- Health Check: https://summarybot-ng.fly.dev/health
- Documentation: /workspaces/summarybot-ng/docs/

## Next Steps

After setting up Zapier:
1. Test with sample data
2. Monitor token usage in responses
3. Adjust `summary_length` based on needs
4. Set up error notifications in Zapier
5. Create multiple Zaps for different use cases
