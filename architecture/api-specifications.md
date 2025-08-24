# API Specifications - Summary Bot NG
## Enhanced REST API & GraphQL Specifications

### 1. OpenAPI 3.0 Specification

```yaml
openapi: 3.0.0
info:
  title: Summary Bot NG API
  version: 2.0.0
  description: |
    Comprehensive API for document processing and AI summarization.
    Supports Discord integration, multi-format document processing, and external webhooks.
  contact:
    name: Summary Bot NG Team
    email: support@summarybot.example.com
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.summarybot.example.com/v2
    description: Production API
  - url: https://staging-api.summarybot.example.com/v2
    description: Staging API
  - url: http://localhost:8080/v2
    description: Development API

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT token for authenticated users
    
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: API key for service-to-service authentication
    
    DiscordOAuth:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://discord.com/api/oauth2/authorize
          tokenUrl: https://discord.com/api/oauth2/token
          scopes:
            bot: Bot permissions
            guilds: Access to user's Discord servers

  schemas:
    Document:
      type: object
      required: [id, type, content, created_at]
      properties:
        id:
          type: string
          format: uuid
          description: Unique document identifier
        type:
          type: string
          enum: [discord_message, discord_thread, pdf_document, word_document, markdown_file, web_content]
          description: Type of document
        title:
          type: string
          maxLength: 500
          description: Document title or summary
        content:
          type: string
          description: Document content (may be truncated for large documents)
        source_id:
          type: string
          description: Original source identifier (Discord message ID, file path, etc.)
        metadata:
          type: object
          additionalProperties: true
          description: Additional document metadata
        created_at:
          type: string
          format: date-time
          description: Document creation timestamp
        size_bytes:
          type: integer
          minimum: 0
          description: Document size in bytes
        language:
          type: string
          pattern: '^[a-z]{2}(-[A-Z]{2})?$'
          description: Detected language (ISO 639-1)
        tags:
          type: array
          items:
            type: string
          description: Document tags for categorization

    ProcessedDocument:
      allOf:
        - $ref: '#/components/schemas/Document'
        - type: object
          properties:
            processing_status:
              type: string
              enum: [pending, processing, completed, failed, retrying]
              description: Document processing status
            processed_content:
              $ref: '#/components/schemas/ProcessedContent'
            embeddings:
              type: array
              items:
                type: number
              description: Vector embeddings for semantic search
            processing_time_ms:
              type: integer
              minimum: 0
              description: Processing time in milliseconds
            error_message:
              type: string
              nullable: true
              description: Error message if processing failed

    ProcessedContent:
      type: object
      required: [text, summary, topics, sentiment_score, language]
      properties:
        text:
          type: string
          description: Processed and normalized text
        summary:
          type: string
          description: Brief content summary
        topics:
          type: array
          items:
            type: string
          description: Identified topics and themes
        entities:
          type: array
          items:
            type: string
          description: Named entities (people, places, organizations)
        key_phrases:
          type: array
          items:
            type: string
          description: Important phrases and keywords
        sentiment_score:
          type: number
          minimum: -1.0
          maximum: 1.0
          description: Sentiment analysis score (-1 negative, 0 neutral, +1 positive)
        language:
          type: string
          description: Detected language
        technical_terms:
          type: array
          items:
            type: string
          description: Technical terms and jargon
        action_items:
          type: array
          items:
            type: string
          description: Identified action items and tasks

    SummaryRequest:
      type: object
      required: [document_ids, summary_type, output_format]
      properties:
        document_ids:
          type: array
          items:
            type: string
            format: uuid
          minItems: 1
          maxItems: 1000
          description: List of document IDs to summarize
        summary_type:
          type: string
          enum: [brief, detailed, comprehensive, technical, executive]
          description: Type of summary to generate
        custom_prompt:
          type: string
          maxLength: 2000
          description: Custom summarization prompt
        output_format:
          type: string
          enum: [json, markdown, html, plain_text]
          default: json
          description: Output format for the summary
        max_length:
          type: integer
          minimum: 50
          maximum: 10000
          default: 500
          description: Maximum summary length in words
        include_technical_terms:
          type: boolean
          default: true
          description: Include technical terms in summary
        include_action_items:
          type: boolean
          default: true
          description: Extract and include action items
        webhook_url:
          type: string
          format: uri
          description: Webhook URL for async result delivery
        priority:
          type: integer
          minimum: 1
          maximum: 10
          default: 5
          description: Processing priority (1 lowest, 10 highest)

    Summary:
      type: object
      required: [id, request_id, content, created_at]
      properties:
        id:
          type: string
          format: uuid
          description: Unique summary identifier
        request_id:
          type: string
          format: uuid
          description: Original request identifier
        content:
          type: string
          description: Generated summary content
        technical_terms:
          type: array
          items:
            type: string
          description: Technical terms found in content
        key_decisions:
          type: array
          items:
            type: string
          description: Key decisions identified
        action_items:
          type: array
          items:
            type: string
          description: Action items extracted
        topics:
          type: array
          items:
            type: string
          description: Main topics covered
        sentiment:
          type: string
          enum: [positive, negative, neutral, mixed]
          description: Overall sentiment
        confidence_score:
          type: number
          minimum: 0.0
          maximum: 1.0
          description: Confidence in summary quality
        document_count:
          type: integer
          minimum: 1
          description: Number of documents summarized
        word_count:
          type: integer
          minimum: 0
          description: Summary word count
        processing_time_ms:
          type: integer
          minimum: 0
          description: Processing time in milliseconds
        model_used:
          type: string
          description: AI model used for summarization
        cost_usd:
          type: number
          minimum: 0
          description: Processing cost in USD
        created_at:
          type: string
          format: date-time
          description: Summary creation timestamp
        metadata:
          type: object
          additionalProperties: true
          description: Additional summary metadata

    ProcessingJob:
      type: object
      required: [id, status, created_at]
      properties:
        id:
          type: string
          format: uuid
          description: Job identifier
        status:
          type: string
          enum: [queued, processing, completed, failed, cancelled]
          description: Job status
        progress:
          type: number
          minimum: 0.0
          maximum: 1.0
          description: Job progress (0.0 to 1.0)
        estimated_completion:
          type: string
          format: date-time
          nullable: true
          description: Estimated completion time
        created_at:
          type: string
          format: date-time
          description: Job creation timestamp
        completed_at:
          type: string
          format: date-time
          nullable: true
          description: Job completion timestamp
        error_message:
          type: string
          nullable: true
          description: Error message if job failed
        result:
          oneOf:
            - $ref: '#/components/schemas/Summary'
            - type: object
          nullable: true
          description: Job result when completed

    Error:
      type: object
      required: [code, message]
      properties:
        code:
          type: string
          description: Error code
        message:
          type: string
          description: Human-readable error message
        details:
          type: object
          additionalProperties: true
          description: Additional error details
        request_id:
          type: string
          format: uuid
          description: Request ID for tracking

paths:
  # Document Management
  /documents:
    get:
      summary: List documents
      description: Retrieve a paginated list of documents
      tags: [Documents]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
          description: Maximum number of documents to return
        - name: offset
          in: query
          schema:
            type: integer
            minimum: 0
            default: 0
          description: Number of documents to skip
        - name: type
          in: query
          schema:
            type: string
            enum: [discord_message, discord_thread, pdf_document, word_document, markdown_file, web_content]
          description: Filter by document type
        - name: created_after
          in: query
          schema:
            type: string
            format: date-time
          description: Filter documents created after this timestamp
        - name: search
          in: query
          schema:
            type: string
            maxLength: 200
          description: Search query for document content
      responses:
        200:
          description: Documents retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  documents:
                    type: array
                    items:
                      $ref: '#/components/schemas/Document'
                  total:
                    type: integer
                    description: Total number of documents
                  limit:
                    type: integer
                    description: Applied limit
                  offset:
                    type: integer
                    description: Applied offset
        400:
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        401:
          description: Unauthorized
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

    post:
      summary: Create document
      description: Create a new document for processing
      tags: [Documents]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [type, content]
              properties:
                type:
                  type: string
                  enum: [discord_message, discord_thread, pdf_document, word_document, markdown_file, web_content]
                title:
                  type: string
                  maxLength: 500
                content:
                  type: string
                  maxLength: 1000000
                source_id:
                  type: string
                metadata:
                  type: object
                  additionalProperties: true
                tags:
                  type: array
                  items:
                    type: string
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                type:
                  type: string
                  enum: [pdf_document, word_document, markdown_file]
                title:
                  type: string
                metadata:
                  type: string
                  description: JSON-encoded metadata
      responses:
        201:
          description: Document created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
        400:
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        413:
          description: Document too large
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /documents/{document_id}:
    get:
      summary: Get document
      description: Retrieve a specific document by ID
      tags: [Documents]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: document_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: Document identifier
      responses:
        200:
          description: Document retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProcessedDocument'
        404:
          description: Document not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

    delete:
      summary: Delete document
      description: Delete a specific document
      tags: [Documents]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: document_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: Document identifier
      responses:
        204:
          description: Document deleted successfully
        404:
          description: Document not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Summarization
  /summaries:
    post:
      summary: Create summary
      description: Generate a summary from documents
      tags: [Summaries]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SummaryRequest'
      responses:
        201:
          description: Summary created successfully (synchronous processing)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Summary'
        202:
          description: Summary request accepted for processing (asynchronous)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProcessingJob'
        400:
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        429:
          description: Rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

    get:
      summary: List summaries
      description: Retrieve a paginated list of summaries
      tags: [Summaries]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
          description: Maximum number of summaries to return
        - name: offset
          in: query
          schema:
            type: integer
            minimum: 0
            default: 0
          description: Number of summaries to skip
        - name: created_after
          in: query
          schema:
            type: string
            format: date-time
          description: Filter summaries created after this timestamp
      responses:
        200:
          description: Summaries retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  summaries:
                    type: array
                    items:
                      $ref: '#/components/schemas/Summary'
                  total:
                    type: integer
                    description: Total number of summaries
                  limit:
                    type: integer
                    description: Applied limit
                  offset:
                    type: integer
                    description: Applied offset

  /summaries/{summary_id}:
    get:
      summary: Get summary
      description: Retrieve a specific summary by ID
      tags: [Summaries]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: summary_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: Summary identifier
      responses:
        200:
          description: Summary retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Summary'
        404:
          description: Summary not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Discord Integration
  /discord/channels/{channel_id}/summarize:
    post:
      summary: Summarize Discord channel
      description: Generate a summary of Discord channel messages
      tags: [Discord]
      security:
        - BearerAuth: []
        - DiscordOAuth: [bot, guilds]
      parameters:
        - name: channel_id
          in: path
          required: true
          schema:
            type: string
          description: Discord channel ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                time_range:
                  type: object
                  required: [start, end]
                  properties:
                    start:
                      type: string
                      format: date-time
                      description: Start time for message retrieval
                    end:
                      type: string
                      format: date-time
                      description: End time for message retrieval
                summary_type:
                  type: string
                  enum: [brief, detailed, comprehensive, technical, executive]
                  default: brief
                include_threads:
                  type: boolean
                  default: true
                  description: Include thread messages in summary
                exclude_bots:
                  type: boolean
                  default: true
                  description: Exclude bot messages from summary
      responses:
        201:
          description: Channel summary created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Summary'
        202:
          description: Summary request queued for processing
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProcessingJob'
        403:
          description: Insufficient permissions
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Job Management
  /jobs/{job_id}:
    get:
      summary: Get job status
      description: Retrieve the status of a processing job
      tags: [Jobs]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: Job identifier
      responses:
        200:
          description: Job status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProcessingJob'
        404:
          description: Job not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

    delete:
      summary: Cancel job
      description: Cancel a processing job
      tags: [Jobs]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: Job identifier
      responses:
        204:
          description: Job cancelled successfully
        400:
          description: Job cannot be cancelled
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        404:
          description: Job not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Health & Monitoring
  /health:
    get:
      summary: Health check
      description: Check API health status
      tags: [Health]
      responses:
        200:
          description: API is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [healthy, degraded, unhealthy]
                  timestamp:
                    type: string
                    format: date-time
                  version:
                    type: string
                  services:
                    type: object
                    properties:
                      database:
                        type: string
                        enum: [healthy, unhealthy]
                      cache:
                        type: string
                        enum: [healthy, unhealthy]
                      ai_service:
                        type: string
                        enum: [healthy, unhealthy]
                      discord_api:
                        type: string
                        enum: [healthy, unhealthy]
        503:
          description: API is unhealthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /metrics:
    get:
      summary: System metrics
      description: Retrieve system performance metrics
      tags: [Health]
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Metrics retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  timestamp:
                    type: string
                    format: date-time
                  requests_per_minute:
                    type: integer
                  average_response_time_ms:
                    type: number
                  active_jobs:
                    type: integer
                  queue_size:
                    type: integer
                  cache_hit_rate:
                    type: number
                    minimum: 0.0
                    maximum: 1.0
                  ai_model_usage:
                    type: object
                    additionalProperties:
                      type: integer
                  error_rate:
                    type: number
                    minimum: 0.0
                    maximum: 1.0
```

### 2. GraphQL Schema (Optional Advanced API)

```graphql
scalar DateTime
scalar JSON
scalar Upload

enum DocumentType {
  DISCORD_MESSAGE
  DISCORD_THREAD
  PDF_DOCUMENT
  WORD_DOCUMENT
  MARKDOWN_FILE
  WEB_CONTENT
}

enum SummaryType {
  BRIEF
  DETAILED
  COMPREHENSIVE
  TECHNICAL
  EXECUTIVE
}

enum ProcessingStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
  RETRYING
}

type Document {
  id: ID!
  type: DocumentType!
  title: String!
  content: String!
  sourceId: String
  metadata: JSON
  createdAt: DateTime!
  updatedAt: DateTime!
  sizeBytes: Int!
  language: String
  tags: [String!]!
  processedContent: ProcessedContent
  summaries: [Summary!]!
}

type ProcessedContent {
  text: String!
  summary: String!
  topics: [String!]!
  entities: [String!]!
  keyPhrases: [String!]!
  sentimentScore: Float!
  language: String!
  technicalTerms: [String!]!
  actionItems: [String!]!
}

type Summary {
  id: ID!
  requestId: ID!
  content: String!
  technicalTerms: [String!]!
  keyDecisions: [String!]!
  actionItems: [String!]!
  topics: [String!]!
  sentiment: String!
  confidenceScore: Float!
  documentCount: Int!
  wordCount: Int!
  processingTimeMs: Int!
  modelUsed: String!
  costUsd: Float!
  createdAt: DateTime!
  metadata: JSON
  documents: [Document!]!
}

type ProcessingJob {
  id: ID!
  status: ProcessingStatus!
  progress: Float!
  estimatedCompletion: DateTime
  createdAt: DateTime!
  completedAt: DateTime
  errorMessage: String
  result: Summary
}

type Query {
  # Documents
  documents(
    limit: Int = 20
    offset: Int = 0
    type: DocumentType
    createdAfter: DateTime
    search: String
  ): DocumentConnection!
  
  document(id: ID!): Document
  
  # Summaries
  summaries(
    limit: Int = 20
    offset: Int = 0
    createdAfter: DateTime
  ): SummaryConnection!
  
  summary(id: ID!): Summary
  
  # Jobs
  job(id: ID!): ProcessingJob
  
  # Search
  searchDocuments(query: String!, limit: Int = 10): [Document!]!
  searchSummaries(query: String!, limit: Int = 10): [Summary!]!
}

type Mutation {
  # Documents
  createDocument(input: CreateDocumentInput!): Document!
  uploadDocument(file: Upload!, type: DocumentType!, title: String): Document!
  deleteDocument(id: ID!): Boolean!
  
  # Summaries
  createSummary(input: CreateSummaryInput!): CreateSummaryResult!
  
  # Discord
  summarizeDiscordChannel(input: DiscordChannelSummaryInput!): CreateSummaryResult!
  
  # Jobs
  cancelJob(id: ID!): Boolean!
}

type Subscription {
  # Real-time job updates
  jobStatusUpdated(jobId: ID!): ProcessingJob!
  
  # Real-time document processing
  documentProcessed: Document!
  
  # Real-time summary creation
  summaryCreated: Summary!
}

# Input types
input CreateDocumentInput {
  type: DocumentType!
  title: String!
  content: String!
  sourceId: String
  metadata: JSON
  tags: [String!]
}

input CreateSummaryInput {
  documentIds: [ID!]!
  summaryType: SummaryType!
  customPrompt: String
  outputFormat: String = "json"
  maxLength: Int = 500
  includeTechnicalTerms: Boolean = true
  includeActionItems: Boolean = true
  webhookUrl: String
  priority: Int = 5
}

input DiscordChannelSummaryInput {
  channelId: String!
  timeRange: TimeRangeInput!
  summaryType: SummaryType = BRIEF
  includeThreads: Boolean = true
  excludeBots: Boolean = true
}

input TimeRangeInput {
  start: DateTime!
  end: DateTime!
}

# Connection types for pagination
type DocumentConnection {
  edges: [DocumentEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type DocumentEdge {
  node: Document!
  cursor: String!
}

type SummaryConnection {
  edges: [SummaryEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type SummaryEdge {
  node: Summary!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

# Union types for flexible responses
union CreateSummaryResult = Summary | ProcessingJob
```

### 3. WebSocket API for Real-time Updates

```javascript
// WebSocket Event Types
const WS_EVENTS = {
  // Connection
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  AUTHENTICATE: 'authenticate',
  
  // Document Processing
  DOCUMENT_PROCESSING_STARTED: 'document.processing.started',
  DOCUMENT_PROCESSING_PROGRESS: 'document.processing.progress',
  DOCUMENT_PROCESSING_COMPLETED: 'document.processing.completed',
  DOCUMENT_PROCESSING_FAILED: 'document.processing.failed',
  
  // Summarization
  SUMMARY_GENERATION_STARTED: 'summary.generation.started',
  SUMMARY_GENERATION_PROGRESS: 'summary.generation.progress',
  SUMMARY_GENERATION_COMPLETED: 'summary.generation.completed',
  SUMMARY_GENERATION_FAILED: 'summary.generation.failed',
  
  // Discord Events
  DISCORD_MESSAGE_RECEIVED: 'discord.message.received',
  DISCORD_CHANNEL_UPDATED: 'discord.channel.updated',
  
  // System Events
  SYSTEM_MAINTENANCE: 'system.maintenance',
  RATE_LIMIT_WARNING: 'system.rate_limit.warning'
};

// Example WebSocket message formats
const wsMessageExamples = {
  documentProcessingProgress: {
    event: 'document.processing.progress',
    data: {
      jobId: 'uuid-here',
      documentId: 'uuid-here',
      progress: 0.65,
      stage: 'content_analysis',
      estimatedCompletion: '2024-01-01T12:30:00Z'
    },
    timestamp: '2024-01-01T12:00:00Z'
  },
  
  summaryCompleted: {
    event: 'summary.generation.completed',
    data: {
      summaryId: 'uuid-here',
      requestId: 'uuid-here',
      summary: {
        content: 'Generated summary content...',
        wordCount: 256,
        processingTimeMs: 15000,
        confidenceScore: 0.92
      }
    },
    timestamp: '2024-01-01T12:00:30Z'
  }
};
```

This comprehensive API specification provides:

1. **RESTful API**: Complete CRUD operations with proper HTTP status codes
2. **GraphQL API**: Flexible querying with real-time subscriptions
3. **WebSocket API**: Real-time updates for long-running operations
4. **Authentication**: Multiple auth methods (JWT, API keys, OAuth)
5. **Error Handling**: Standardized error responses with detailed information
6. **Pagination**: Cursor and offset-based pagination support
7. **File Uploads**: Multipart form data support for document uploads
8. **Rate Limiting**: Built-in rate limiting and quota management
9. **Monitoring**: Health checks and metrics endpoints