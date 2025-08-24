# Configuration and Deployment Specifications
## Summary Bot NG - Environment Setup & Production Deployment

### 1. Environment Configuration

#### 1.1 Environment Variables

**Required Environment Variables**:
```bash
# Core API Keys
OPENAI_API_KEY=sk-...                    # OpenAI API key for GPT-4 access
DISCORD_TOKEN=MTI...                     # Discord bot token
DISCORD_APPLICATION_ID=123456789...      # Discord application ID

# Server Configuration
HOST=0.0.0.0                            # Server bind address
PORT=5000                               # Server port (default: 5000)
ENV=production                          # Environment: development, staging, production

# Database Configuration
DATABASE_URL=postgresql://...            # Database connection string
DATABASE_POOL_SIZE=10                   # Connection pool size
DATABASE_POOL_TIMEOUT=30                # Pool timeout in seconds

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0      # Redis connection for caching/queues
REDIS_PASSWORD=...                      # Redis password if required

# Security
SECRET_KEY=your-secret-key-here         # Application secret key
API_KEY_SALT=random-salt-string         # Salt for API key hashing
WEBHOOK_SECRET=webhook-signing-secret   # Secret for webhook signature validation

# Logging
LOG_LEVEL=INFO                          # Logging level: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                         # Log format: json, text
SENTRY_DSN=https://...                  # Sentry DSN for error tracking (optional)

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100              # API requests per minute per key
DISCORD_RATE_LIMIT_BUFFER=0.1          # Buffer for Discord rate limits (10%)

# OpenAI Configuration
OPENAI_ORGANIZATION_ID=org-...          # OpenAI organization ID (optional)
OPENAI_MODEL_PRIMARY=gpt-4             # Primary model
OPENAI_MODEL_FALLBACK=gpt-3.5-turbo    # Fallback model
OPENAI_MAX_TOKENS=1500                 # Maximum tokens per request
OPENAI_TEMPERATURE=0.3                 # Model temperature
OPENAI_TIMEOUT=120                     # Request timeout in seconds

# Feature Flags
ENABLE_SCHEDULED_SUMMARIES=true        # Enable scheduled summarization
ENABLE_WEBHOOK_API=true                # Enable webhook endpoints
ENABLE_METRICS=true                    # Enable Prometheus metrics
ENABLE_HEALTH_CHECKS=true              # Enable health check endpoints

# Resource Limits
MAX_MESSAGE_HISTORY_HOURS=168          # Maximum hours for message history (7 days)
MAX_CONCURRENT_JOBS=5                  # Maximum concurrent processing jobs
MAX_SUMMARY_LENGTH=2000                # Maximum summary length in characters
MAX_REQUEST_SIZE_MB=10                 # Maximum HTTP request size
```

**Environment-Specific Overrides**:
```bash
# Development
DATABASE_URL=sqlite:///dev.db
LOG_LEVEL=DEBUG
ENABLE_DEBUG_ROUTES=true

# Staging
DATABASE_URL=postgresql://staging...
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=50

# Production
DATABASE_URL=postgresql://prod...
LOG_LEVEL=WARNING
ENABLE_DEBUG_ROUTES=false
```

#### 1.2 Configuration File Structure

**config.json** (Optional - for non-sensitive settings):
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "workers": 4,
    "keepalive": 120,
    "max_requests": 1000,
    "max_requests_jitter": 100
  },
  "discord": {
    "intents": ["guilds", "guild_messages", "message_content"],
    "command_prefix": "/",
    "status": "Summarizing conversations...",
    "activity_type": "listening"
  },
  "openai": {
    "model_config": {
      "gpt-4": {
        "max_tokens": 1500,
        "temperature": 0.3,
        "top_p": 1.0,
        "frequency_penalty": 0,
        "presence_penalty": 0
      },
      "gpt-3.5-turbo": {
        "max_tokens": 1200,
        "temperature": 0.4,
        "top_p": 0.9
      }
    },
    "retry_config": {
      "max_retries": 3,
      "backoff_factor": 2,
      "max_wait": 60
    }
  },
  "database": {
    "pool_config": {
      "min_connections": 5,
      "max_connections": 20,
      "pool_recycle": 3600,
      "pool_timeout": 30
    },
    "migration_config": {
      "auto_migrate": false,
      "backup_before_migrate": true
    }
  },
  "caching": {
    "message_cache_ttl": 3600,
    "summary_cache_ttl": 86400,
    "max_cache_size": "100MB"
  },
  "processing": {
    "job_queue_size": 1000,
    "worker_threads": 4,
    "job_timeout": 300,
    "cleanup_interval": 3600
  },
  "monitoring": {
    "metrics_enabled": true,
    "health_check_interval": 60,
    "performance_monitoring": true
  }
}
```

#### 1.3 Configuration Management

**Configuration Loader**:
```python
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    workers: int = 4
    max_requests: int = 1000

@dataclass
class DatabaseConfig:
    url: str
    pool_size: int = 10
    pool_timeout: int = 30
    auto_migrate: bool = False

@dataclass
class OpenAIConfig:
    api_key: str
    organization_id: Optional[str] = None
    model_primary: str = "gpt-4"
    model_fallback: str = "gpt-3.5-turbo"
    max_tokens: int = 1500
    temperature: float = 0.3
    timeout: int = 120

@dataclass
class DiscordConfig:
    token: str
    application_id: str
    intents: list = field(default_factory=lambda: ["guilds", "guild_messages", "message_content"])

@dataclass
class AppConfig:
    server: ServerConfig
    database: DatabaseConfig
    openai: OpenAIConfig
    discord: DiscordConfig
    environment: str = "development"
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables and files"""
        
        # Load from config file if exists
        config_file = Path("config.json")
        file_config = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                file_config = json.load(f)
        
        return cls(
            environment=os.getenv("ENV", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            
            server=ServerConfig(
                host=os.getenv("HOST", file_config.get("server", {}).get("host", "0.0.0.0")),
                port=int(os.getenv("PORT", file_config.get("server", {}).get("port", 5000))),
                workers=int(os.getenv("WORKERS", file_config.get("server", {}).get("workers", 4))),
                max_requests=int(os.getenv("MAX_REQUESTS", file_config.get("server", {}).get("max_requests", 1000)))
            ),
            
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///summarybot.db"),
                pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
                pool_timeout=int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
                auto_migrate=os.getenv("AUTO_MIGRATE", "false").lower() == "true"
            ),
            
            openai=OpenAIConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                organization_id=os.getenv("OPENAI_ORGANIZATION_ID"),
                model_primary=os.getenv("OPENAI_MODEL_PRIMARY", "gpt-4"),
                model_fallback=os.getenv("OPENAI_MODEL_FALLBACK", "gpt-3.5-turbo"),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1500")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
                timeout=int(os.getenv("OPENAI_TIMEOUT", "120"))
            ),
            
            discord=DiscordConfig(
                token=os.getenv("DISCORD_TOKEN"),
                application_id=os.getenv("DISCORD_APPLICATION_ID"),
                intents=file_config.get("discord", {}).get("intents", ["guilds", "guild_messages", "message_content"])
            )
        )
    
    def validate(self) -> bool:
        """Validate required configuration values"""
        required_fields = [
            self.openai.api_key,
            self.discord.token,
            self.discord.application_id,
            self.database.url
        ]
        
        missing_fields = [field for field in required_fields if not field]
        if missing_fields:
            raise ValueError(f"Missing required configuration: {missing_fields}")
        
        return True
```

### 2. Deployment Specifications

#### 2.1 Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.6.1

# Set work directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r summarybot && useradd -r -g summarybot summarybot

# Set work directory and copy virtual environment
WORKDIR /app
COPY --from=builder --chown=summarybot:summarybot /app/.venv /app/.venv

# Copy application code
COPY --chown=summarybot:summarybot . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R summarybot:summarybot /app/logs /app/data

# Switch to non-root user
USER summarybot

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# Expose port
EXPOSE 5000

# Default command
CMD ["python", "-m", "summarybot"]
```

**docker-compose.yml** (Development):
```yaml
version: '3.8'

services:
  summarybot:
    build: .
    ports:
      - "5000:5000"
    environment:
      - ENV=development
      - DATABASE_URL=postgresql://postgres:password@db:5432/summarybot
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=DEBUG
    env_file:
      - .env.local
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./config.json:/app/config.json:ro
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: summarybot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

**docker-compose.prod.yml** (Production):
```yaml
version: '3.8'

services:
  summarybot:
    image: summarybot-ng:latest
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
    environment:
      - ENV=production
    env_file:
      - .env.production
    ports:
      - "5000:5000"
    volumes:
      - /var/log/summarybot:/app/logs
      - /etc/summarybot/config.json:/app/config.json:ro
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - summarybot
    restart: always
```

#### 2.2 Kubernetes Deployment

**k8s/namespace.yaml**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: summarybot-ng
  labels:
    app: summarybot-ng
```

**k8s/configmap.yaml**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: summarybot-config
  namespace: summarybot-ng
data:
  config.json: |
    {
      "server": {
        "host": "0.0.0.0",
        "port": 5000,
        "workers": 4
      },
      "processing": {
        "job_queue_size": 1000,
        "worker_threads": 4
      }
    }
```

**k8s/secret.yaml**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: summarybot-secrets
  namespace: summarybot-ng
type: Opaque
stringData:
  openai-api-key: "sk-your-api-key"
  discord-token: "your-discord-token"
  database-url: "postgresql://user:pass@postgres:5432/summarybot"
  redis-url: "redis://redis:6379/0"
```

**k8s/deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: summarybot-ng
  namespace: summarybot-ng
  labels:
    app: summarybot-ng
spec:
  replicas: 3
  selector:
    matchLabels:
      app: summarybot-ng
  template:
    metadata:
      labels:
        app: summarybot-ng
    spec:
      containers:
      - name: summarybot
        image: summarybot-ng:latest
        ports:
        - containerPort: 5000
          name: http
        env:
        - name: ENV
          value: "production"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: summarybot-secrets
              key: openai-api-key
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: summarybot-secrets
              key: discord-token
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: summarybot-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: summarybot-secrets
              key: redis-url
        volumeMounts:
        - name: config
          mountPath: /app/config.json
          subPath: config.json
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: summarybot-config
---
apiVersion: v1
kind: Service
metadata:
  name: summarybot-service
  namespace: summarybot-ng
spec:
  selector:
    app: summarybot-ng
  ports:
  - port: 80
    targetPort: 5000
    name: http
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: summarybot-ingress
  namespace: summarybot-ng
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.summarybot.example.com
    secretName: summarybot-tls
  rules:
  - host: api.summarybot.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: summarybot-service
            port:
              number: 80
```

#### 2.3 Database Deployment

**PostgreSQL with High Availability**:
```yaml
# k8s/postgres-ha.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
  namespace: summarybot-ng
spec:
  instances: 3
  
  postgresql:
    parameters:
      max_connections: "200"
      shared_preload_libraries: "pg_stat_statements"
      pg_stat_statements.max: "10000"
      pg_stat_statements.track: "all"
      
  bootstrap:
    initdb:
      database: summarybot
      owner: summarybot
      secret:
        name: postgres-credentials
        
  storage:
    size: "50Gi"
    storageClass: "fast-ssd"
    
  monitoring:
    enabled: true
    
  backup:
    target: "primary"
    schedule: "0 2 * * *"  # Daily at 2 AM
    cluster: "postgres-cluster"
```

#### 2.4 Monitoring & Observability

**Prometheus Configuration**:
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "summarybot_rules.yml"

scrape_configs:
  - job_name: 'summarybot'
    static_configs:
      - targets: ['summarybot:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

**Grafana Dashboard Configuration**:
```json
{
  "dashboard": {
    "title": "Summary Bot NG Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(summary_requests_total[5m])",
            "legendFormat": "{{type}} - {{status}}"
          }
        ]
      },
      {
        "title": "Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(summary_processing_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Queue Size",
        "type": "stat",
        "targets": [
          {
            "expr": "job_queue_size",
            "legendFormat": "Jobs in Queue"
          }
        ]
      }
    ]
  }
}
```

### 3. Infrastructure Requirements

#### 3.1 Minimum System Requirements

**Development Environment**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- Network: Broadband internet

**Production Environment (Single Instance)**:
- CPU: 4 cores (2.0GHz+)
- RAM: 8GB
- Storage: 100GB SSD
- Network: 1Gbps with low latency

**Production Environment (High Availability)**:
- Load Balancer: 2 cores, 4GB RAM
- Application Servers: 3x (4 cores, 8GB RAM each)
- Database Server: 8 cores, 16GB RAM, 500GB SSD
- Redis Server: 2 cores, 4GB RAM, 50GB SSD

#### 3.2 Cloud Provider Specifications

**AWS Deployment**:
```yaml
# terraform/aws/main.tf
resource "aws_ecs_cluster" "summarybot_cluster" {
  name = "summarybot-ng"
  
  capacity_providers = ["FARGATE"]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
  }
}

resource "aws_ecs_service" "summarybot_service" {
  name            = "summarybot-ng"
  cluster         = aws_ecs_cluster.summarybot_cluster.id
  task_definition = aws_ecs_task_definition.summarybot_task.arn
  desired_count   = 2
  
  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.summarybot_sg.id]
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.summarybot_tg.arn
    container_name   = "summarybot"
    container_port   = 5000
  }
}

resource "aws_rds_instance" "postgres" {
  identifier = "summarybot-postgres"
  
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  db_name  = "summarybot"
  username = var.db_username
  password = var.db_password
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Sun:04:00-Sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "summarybot-final-snapshot"
}
```

**Google Cloud Platform Deployment**:
```yaml
# k8s-gcp/cluster.yaml
apiVersion: container.v1
kind: Cluster
metadata:
  name: summarybot-cluster
spec:
  location: us-central1
  initialNodeCount: 3
  nodeConfig:
    machineType: e2-standard-4
    diskSizeGb: 100
    oauthScopes:
      - https://www.googleapis.com/auth/cloud-platform
  addonsConfig:
    httpLoadBalancing:
      disabled: false
    horizontalPodAutoscaling:
      disabled: false
```

#### 3.3 Security Hardening

**Security Checklist**:
```yaml
security_requirements:
  - name: "Container Security"
    items:
      - "Run containers as non-root user"
      - "Use minimal base images"
      - "Scan images for vulnerabilities"
      - "Keep images updated"
      
  - name: "Network Security"
    items:
      - "Use TLS for all connections"
      - "Implement network policies"
      - "Use private subnets for databases"
      - "Configure firewalls/security groups"
      
  - name: "Secrets Management"
    items:
      - "Use external secret management (AWS Secrets Manager, etc.)"
      - "Rotate secrets regularly"
      - "Never store secrets in code or images"
      - "Use encrypted storage for secrets"
      
  - name: "Access Control"
    items:
      - "Implement RBAC for Kubernetes"
      - "Use service accounts with minimal permissions"
      - "Enable audit logging"
      - "Regular access reviews"
```

### 4. Deployment Automation

#### 4.1 CI/CD Pipeline

**GitHub Actions Workflow**:
```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH
    - name: Install dependencies
      run: poetry install
    - name: Run tests
      run: poetry run pytest
    - name: Run linting
      run: |
        poetry run black --check .
        poetry run isort --check-only .
        poetry run flake8
    - name: Run security scan
      run: poetry run bandit -r summarybot/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    - name: Login to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ghcr.io/${{ github.repository }}:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Deploy to Kubernetes
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
        kubectl set image deployment/summarybot-ng summarybot=ghcr.io/${{ github.repository }}:latest
        kubectl rollout status deployment/summarybot-ng
```

#### 4.2 Health Checks & Monitoring

**Health Check Endpoints**:
```python
from fastapi import FastAPI, HTTPException
from datetime import datetime
import asyncio

app = FastAPI()

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check with dependency verification"""
    checks = {
        "database": await check_database(),
        "discord": await check_discord_connection(),
        "openai": await check_openai_api(),
        "redis": await check_redis_connection()
    }
    
    all_healthy = all(checks.values())
    
    if not all_healthy:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {
        "status": "ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

async def check_database() -> bool:
    """Check database connectivity"""
    try:
        # Perform simple query
        result = await db.execute("SELECT 1")
        return result is not None
    except Exception:
        return False
```

This comprehensive configuration and deployment specification provides everything needed to properly deploy and manage the Summary Bot NG in various environments, from local development to production-grade Kubernetes clusters.