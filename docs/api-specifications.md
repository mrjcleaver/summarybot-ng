# API Specifications
## Summary Bot NG - Discord Commands & Webhook Endpoints

### 1. Discord Bot API

#### 1.1 Slash Commands

##### 1.1.1 `/summarize` Command

**Description**: Generate a summary of recent messages in the current channel

**Syntax**: `/summarize [hours] [format] [details]`

**Parameters**:
```yaml
hours:
  type: integer
  description: Number of hours to look back for messages
  required: false
  default: 24
  range: 1-168 (7 days maximum)
  
format:
  type: string
  description: Output format for the summary
  required: false
  default: "structured"
  choices: ["brief", "structured", "detailed", "technical"]
  
details:
  type: boolean
  description: Include detailed message metadata
  required: false
  default: false
```

**Response Format**:
```json
{
  "type": "summary",
  "status": "completed",
  "channel": {
    "id": "channel_id",
    "name": "channel_name"
  },
  "timeRange": {
    "start": "2024-01-20T10:00:00Z",
    "end": "2024-01-21T10:00:00Z"
  },
  "messageCount": 45,
  "participantCount": 8,
  "summary": {
    "overview": "Brief overview of the conversation",
    "keyPoints": [
      "Key point 1",
      "Key point 2"
    ],
    "decisions": [
      "Decision made during the conversation"
    ],
    "actionItems": [
      "Action item identified"
    ]
  },
  "links": [
    {
      "text": "Original discussion",
      "url": "https://discord.com/channels/server/channel/message"
    }
  ]
}
```

**Error Responses**:
```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "You don't have permission to access message history",
    "details": "Required permission: READ_MESSAGE_HISTORY"
  }
}
```

##### 1.1.2 `/summarize-channel` Command

**Description**: Generate a summary of messages from a specific channel

**Syntax**: `/summarize-channel <channel> [hours] [format]`

**Parameters**:
```yaml
channel:
  type: channel
  description: Target channel to summarize
  required: true
  
hours:
  type: integer
  description: Number of hours to look back
  required: false
  default: 24
  range: 1-168
  
format:
  type: string
  description: Output format for the summary
  required: false
  default: "structured"
  choices: ["brief", "structured", "detailed", "technical"]
```

##### 1.1.3 `/summarize-thread` Command

**Description**: Generate a summary of a specific thread conversation

**Syntax**: `/summarize-thread <thread_id> [format]`

**Parameters**:
```yaml
thread_id:
  type: string
  description: Thread ID to summarize
  required: true
  
format:
  type: string
  description: Output format for the summary
  required: false
  default: "structured"
  choices: ["brief", "structured", "detailed", "technical"]
```

##### 1.1.4 `/summarize-schedule` Command

**Description**: Configure scheduled summarization for a channel

**Syntax**: `/summarize-schedule <action> [channel] [frequency] [format]`

**Parameters**:
```yaml
action:
  type: string
  description: Schedule action
  required: true
  choices: ["create", "modify", "delete", "list"]
  
channel:
  type: channel
  description: Target channel (required for create/modify)
  required: false
  
frequency:
  type: string
  description: Summary frequency
  required: false
  choices: ["daily", "weekly", "monthly", "custom"]
  
format:
  type: string
  description: Output format for scheduled summaries
  required: false
  default: "structured"
```

##### 1.1.5 `/summarize-config` Command

**Description**: Configure bot settings for the current server

**Syntax**: `/summarize-config <setting> <value>`

**Parameters**:
```yaml
setting:
  type: string
  description: Configuration setting to modify
  required: true
  choices: ["default_format", "max_hours", "excluded_channels", "auto_delete"]
  
value:
  type: string
  description: New value for the setting
  required: true
```

#### 1.2 Discord Bot Events

##### 1.2.1 Message Reactions

**Event**: `on_reaction_add`

**Trigger**: User adds 📝 (memo) reaction to a message

**Action**: Generate summary of the thread or recent context around the message

##### 1.2.2 Scheduled Events

**Event**: `scheduled_summary`

**Trigger**: Cron-based scheduling system

**Action**: Generate and deliver scheduled summaries

#### 1.3 Permission Requirements

**Required Bot Permissions**:
- `READ_MESSAGE_HISTORY`: Access historical messages
- `SEND_MESSAGES`: Send summary responses
- `USE_SLASH_COMMANDS`: Register and respond to slash commands
- `EMBED_LINKS`: Send rich embed responses
- `ADD_REACTIONS`: React to messages for feedback

**User Permissions**:
- `MANAGE_GUILD`: Configure server-wide settings
- `MANAGE_CHANNELS`: Configure channel-specific settings
- `READ_MESSAGE_HISTORY`: Use summarization commands

### 2. Webhook REST API

#### 2.1 Base Configuration

**Base URL**: `http://localhost:5000/api/v1`

**Authentication**: API Key Header
```http
Authorization: Bearer <api_key>
```

**Content-Type**: `application/json`

**Rate Limiting**: 
- 100 requests per minute per API key
- 10 concurrent requests per API key

#### 2.2 Endpoints

##### 2.2.1 POST /webhook/summarize

**Description**: Request a summary generation via webhook

**Request Body**:
```json
{
  "guildId": "discord_server_id",
  "channelId": "discord_channel_id",
  "timeRange": {
    "start": "2024-01-20T10:00:00Z",
    "end": "2024-01-21T10:00:00Z"
  },
  "options": {
    "format": "structured",
    "includeMetadata": true,
    "excludeUsers": ["user_id_1", "user_id_2"],
    "keywords": ["deployment", "bug", "feature"]
  },
  "delivery": {
    "method": "webhook",
    "url": "https://your-system.com/webhook/receive",
    "headers": {
      "Authorization": "Bearer your-token"
    }
  }
}
```

**Response**:
```json
{
  "jobId": "summary-job-12345",
  "status": "accepted",
  "estimatedCompletion": "2024-01-21T10:05:00Z",
  "statusUrl": "/webhook/status/summary-job-12345"
}
```

**Status Codes**:
- `202`: Request accepted and queued
- `400`: Invalid request parameters
- `401`: Authentication failed
- `403`: Insufficient permissions
- `429`: Rate limit exceeded

##### 2.2.2 GET /webhook/status/{job_id}

**Description**: Check the status of a summary generation job

**Response**:
```json
{
  "jobId": "summary-job-12345",
  "status": "processing",
  "progress": {
    "current": 150,
    "total": 300,
    "percentage": 50
  },
  "startedAt": "2024-01-21T10:00:30Z",
  "estimatedCompletion": "2024-01-21T10:05:00Z",
  "result": null
}
```

**Status Values**:
- `queued`: Job is waiting to be processed
- `processing`: Job is currently being processed
- `completed`: Job completed successfully
- `failed`: Job failed with error
- `cancelled`: Job was cancelled

##### 2.2.3 POST /webhook/cancel/{job_id}

**Description**: Cancel a pending or running summary job

**Response**:
```json
{
  "jobId": "summary-job-12345",
  "status": "cancelled",
  "message": "Job successfully cancelled"
}
```

##### 2.2.4 GET /webhook/results/{job_id}

**Description**: Retrieve the results of a completed summary job

**Response**:
```json
{
  "jobId": "summary-job-12345",
  "status": "completed",
  "completedAt": "2024-01-21T10:04:32Z",
  "result": {
    "summary": {
      "overview": "Summary overview text",
      "keyPoints": ["Point 1", "Point 2"],
      "decisions": ["Decision 1"],
      "actionItems": ["Action 1", "Action 2"]
    },
    "metadata": {
      "messageCount": 45,
      "participantCount": 8,
      "timeRange": {
        "start": "2024-01-20T10:00:00Z",
        "end": "2024-01-21T10:00:00Z"
      },
      "processingTime": 42.5
    },
    "links": [
      {
        "text": "Original discussion",
        "url": "https://discord.com/channels/server/channel/message"
      }
    ]
  }
}
```

#### 2.3 Webhook Delivery

##### 2.3.1 Outbound Webhook Format

When results are ready, if webhook delivery was specified:

**POST to configured URL**:
```json
{
  "event": "summary_completed",
  "jobId": "summary-job-12345",
  "timestamp": "2024-01-21T10:04:32Z",
  "data": {
    "summary": {
      "overview": "Summary overview text",
      "keyPoints": ["Point 1", "Point 2"],
      "decisions": ["Decision 1"],
      "actionItems": ["Action 1", "Action 2"]
    },
    "metadata": {
      "guildId": "discord_server_id",
      "channelId": "discord_channel_id",
      "messageCount": 45,
      "participantCount": 8,
      "processingTime": 42.5
    }
  }
}
```

##### 2.3.2 Retry Policy

**Retry Configuration**:
- Maximum 3 retry attempts
- Exponential backoff: 1s, 4s, 16s
- Timeout: 30 seconds per attempt
- Failed deliveries logged for manual review

#### 2.4 Health and Monitoring

##### 2.4.1 GET /health

**Description**: System health check

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-21T10:00:00Z",
  "version": "1.0.0",
  "dependencies": {
    "discord": {
      "status": "connected",
      "latency": 45
    },
    "openai": {
      "status": "available",
      "lastCheck": "2024-01-21T09:59:30Z"
    },
    "database": {
      "status": "connected",
      "responseTime": 12
    }
  }
}
```

##### 2.4.2 GET /metrics

**Description**: System metrics (Prometheus format)

**Response**: Prometheus metrics format

### 3. Error Handling

#### 3.1 Standard Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional error details",
    "timestamp": "2024-01-21T10:00:00Z",
    "requestId": "req-12345"
  }
}
```

#### 3.2 Error Codes

**Authentication Errors**:
- `AUTH_INVALID_TOKEN`: Invalid or expired API token
- `AUTH_MISSING_TOKEN`: Authentication token not provided
- `AUTH_INSUFFICIENT_PERMISSIONS`: Token lacks required permissions

**Request Errors**:
- `REQ_INVALID_PARAMETERS`: Invalid request parameters
- `REQ_MISSING_REQUIRED_FIELD`: Required field missing
- `REQ_INVALID_TIME_RANGE`: Invalid time range specified
- `REQ_RATE_LIMITED`: Rate limit exceeded

**Processing Errors**:
- `PROC_CHANNEL_NOT_FOUND`: Specified channel not found
- `PROC_NO_MESSAGES`: No messages found in specified range
- `PROC_OPENAI_ERROR`: OpenAI API error
- `PROC_DISCORD_ERROR`: Discord API error

**System Errors**:
- `SYS_SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `SYS_INTERNAL_ERROR`: Internal server error
- `SYS_TIMEOUT`: Operation timed out

### 4. SDK and Integration Examples

#### 4.1 Python SDK Example

```python
import requests
import json

class SummaryBotClient:
    def __init__(self, api_key, base_url="http://localhost:5000/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def request_summary(self, guild_id, channel_id, hours=24):
        url = f"{self.base_url}/webhook/summarize"
        payload = {
            "guildId": guild_id,
            "channelId": channel_id,
            "timeRange": {
                "hours": hours
            },
            "options": {
                "format": "structured"
            }
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()
    
    def get_job_status(self, job_id):
        url = f"{self.base_url}/webhook/status/{job_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
```

#### 4.2 JavaScript/Node.js Example

```javascript
class SummaryBotClient {
    constructor(apiKey, baseUrl = 'http://localhost:5000/api/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async requestSummary(guildId, channelId, hours = 24) {
        const response = await fetch(`${this.baseUrl}/webhook/summarize`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                guildId,
                channelId,
                timeRange: { hours },
                options: { format: 'structured' }
            })
        });
        return response.json();
    }
    
    async getJobStatus(jobId) {
        const response = await fetch(`${this.baseUrl}/webhook/status/${jobId}`, {
            headers: this.headers
        });
        return response.json();
    }
}
```

### 5. OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Summary Bot NG API
  version: 1.0.0
  description: AI-powered Discord conversation summarization service
  
servers:
  - url: http://localhost:5000/api/v1
    description: Local development server
    
security:
  - bearerAuth: []
    
paths:
  /webhook/summarize:
    post:
      summary: Request conversation summary
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SummaryRequest'
      responses:
        '202':
          description: Summary request accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JobResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
          
  /webhook/status/{jobId}:
    get:
      summary: Get job status
      parameters:
        - name: jobId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Job status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JobStatus'
                
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      
  schemas:
    SummaryRequest:
      type: object
      required:
        - guildId
        - channelId
      properties:
        guildId:
          type: string
          description: Discord server ID
        channelId:
          type: string
          description: Discord channel ID
        timeRange:
          $ref: '#/components/schemas/TimeRange'
        options:
          $ref: '#/components/schemas/SummaryOptions'
          
    TimeRange:
      type: object
      properties:
        start:
          type: string
          format: date-time
        end:
          type: string
          format: date-time
        hours:
          type: integer
          minimum: 1
          maximum: 168
          
    SummaryOptions:
      type: object
      properties:
        format:
          type: string
          enum: [brief, structured, detailed, technical]
        includeMetadata:
          type: boolean
        excludeUsers:
          type: array
          items:
            type: string
```