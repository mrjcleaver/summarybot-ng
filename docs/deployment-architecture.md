# Summary Bot NG - Deployment Architecture

## 6. Deployment Architecture

### 6.1 Container Architecture

```dockerfile
# Multi-stage Dockerfile for Summary Bot NG
FROM python:3.11-slim as base

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM base as production
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["poetry", "run", "python", "-m", "src.main"]
```

### 6.2 Kubernetes Deployment

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: summarybot-ng
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: summarybot-config
  namespace: summarybot-ng
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  WEBHOOK_PORT: "5000"
  REDIS_URL: "redis://redis-service:6379"
  POSTGRES_URL: "postgresql://summarybot:password@postgres-service:5432/summarybot"
  RABBITMQ_URL: "amqp://rabbitmq-service:5672"
---
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: summarybot-secrets
  namespace: summarybot-ng
type: Opaque
stringData:
  DISCORD_TOKEN: "${DISCORD_TOKEN}"
  OPENAI_API_KEY: "${OPENAI_API_KEY}"
  JWT_SECRET: "${JWT_SECRET}"
  DATABASE_PASSWORD: "${DATABASE_PASSWORD}"
---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: summarybot-app
  namespace: summarybot-ng
  labels:
    app: summarybot-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: summarybot-app
  template:
    metadata:
      labels:
        app: summarybot-app
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: summarybot-service-account
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
      containers:
      - name: summarybot-app
        image: summarybot-ng:latest
        ports:
        - name: http
          containerPort: 5000
          protocol: TCP
        - name: metrics
          containerPort: 8080
          protocol: TCP
        env:
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: summarybot-config
              key: ENVIRONMENT
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: summarybot-secrets
              key: DISCORD_TOKEN
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: summarybot-secrets
              key: OPENAI_API_KEY
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
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
        - name: logs-volume
          mountPath: /app/logs
      volumes:
      - name: config-volume
        configMap:
          name: summarybot-config
      - name: logs-volume
        emptyDir: {}
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: summarybot-service
  namespace: summarybot-ng
  labels:
    app: summarybot-app
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 80
    targetPort: 5000
    protocol: TCP
  - name: metrics
    port: 8080
    targetPort: 8080
    protocol: TCP
  selector:
    app: summarybot-app
---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: summarybot-ingress
  namespace: summarybot-ng
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
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

### 6.3 Infrastructure as Code (Terraform)

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
  }
  
  backend "s3" {
    bucket = "summarybot-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "summarybot-ng"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "summarybot-${var.environment}"
  cluster_version = "1.27"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    main = {
      name = "summarybot-nodes"

      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3

      disk_size      = 50
      disk_type      = "gp3"
      disk_encrypted = true
    }
  }

  tags = {
    Environment = var.environment
  }
}

# RDS PostgreSQL
module "rds" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "summarybot-${var.environment}"

  engine            = "postgres"
  engine_version    = "14.9"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_encrypted = true

  db_name  = "summarybot"
  username = "summarybot"
  password = var.database_password
  port     = "5432"

  vpc_security_group_ids = [module.database_security_group.security_group_id]
  
  create_db_subnet_group = true
  subnet_ids             = module.vpc.database_subnets

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  deletion_protection = true
  skip_final_snapshot = false

  tags = {
    Environment = var.environment
  }
}

# ElastiCache Redis
module "redis" {
  source = "terraform-aws-modules/elasticache/aws"

  cluster_id           = "summarybot-${var.environment}"
  description          = "Redis cluster for summarybot"
  
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name = module.vpc.elasticache_subnet_group_name
  security_group_ids = [module.redis_security_group.security_group_id]

  tags = {
    Environment = var.environment
  }
}

# Application Load Balancer
module "alb" {
  source = "terraform-aws-modules/alb/aws"

  name = "summarybot-${var.environment}"

  load_balancer_type = "application"

  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets
  security_groups    = [module.alb_security_group.security_group_id]

  target_groups = [
    {
      name     = "summarybot-tg"
      protocol = "HTTP"
      port     = 80
      target_type = "ip"
      
      health_check = {
        enabled             = true
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        port                = "traffic-port"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
  ]

  https_listeners = [
    {
      port               = 443
      protocol           = "HTTPS"
      certificate_arn    = module.acm.acm_certificate_arn
      target_group_index = 0
    }
  ]

  http_tcp_listeners = [
    {
      port        = 80
      protocol    = "HTTP"
      action_type = "redirect"
      redirect = {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  ]

  tags = {
    Environment = var.environment
  }
}
```

### 6.4 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: latest
        virtualenvs-create: true
        virtualenvs-in-project: true
    
    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v3
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('**/poetry.lock') }}
    
    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      run: poetry install --no-interaction --no-root
    
    - name: Run tests
      run: |
        poetry run pytest --cov=src --cov-report=xml
    
    - name: Run linting
      run: |
        poetry run flake8 src/
        poetry run black --check src/
        poetry run mypy src/

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha
          type=raw,value=latest,enable={{is_default_branch}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --name summarybot-production --region us-east-1
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/summarybot-app summarybot-app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} -n summarybot-ng
        kubectl rollout status deployment/summarybot-app -n summarybot-ng --timeout=300s
    
    - name: Run smoke tests
      run: |
        kubectl run smoke-test --image=curlimages/curl --rm -i --restart=Never -- \
          curl -f http://summarybot-service.summarybot-ng.svc.cluster.local/health
```

## 7. Infrastructure Requirements

### 7.1 Production Environment

```yaml
production_requirements:
  compute:
    kubernetes_cluster:
      nodes: 3
      instance_type: "t3.medium"
      cpu: "2 vCPU per node"
      memory: "4 GB per node"
      disk: "50 GB SSD per node"
    
    application_pods:
      replicas: 3
      resources:
        requests:
          cpu: "250m"
          memory: "512Mi"
        limits:
          cpu: "500m"
          memory: "1Gi"
  
  database:
    postgres:
      instance_type: "db.t3.small"
      storage: "100 GB SSD"
      backup_retention: "7 days"
      multi_az: true
    
    redis:
      instance_type: "cache.t3.micro"
      memory: "1 GB"
      persistence: false
  
  networking:
    load_balancer: "Application Load Balancer"
    ssl_certificate: "ACM managed"
    cdn: "CloudFront"
    waf: "AWS WAF v2"
  
  monitoring:
    prometheus: "Managed Prometheus"
    grafana: "Managed Grafana"
    log_aggregation: "AWS CloudWatch"
    alerting: "AWS SNS + PagerDuty"

estimated_costs:
  monthly_aws_costs:
    eks_cluster: "$73"
    rds_postgres: "$25"
    elasticache_redis: "$15"
    application_load_balancer: "$22"
    cloudwatch_logs: "$10"
    data_transfer: "$20"
    total_estimated: "$165/month"
```

### 7.2 Development Environment

```yaml
development_setup:
  local_development:
    docker_compose:
      - postgres: "14-alpine"
      - redis: "7-alpine"
      - rabbitmq: "3-management-alpine"
      - application: "summarybot:dev"
    
    requirements:
      python: "3.11+"
      poetry: "1.8+"
      docker: "20+"
      docker_compose: "2+"
  
  staging_environment:
    kubernetes_cluster:
      nodes: 1
      instance_type: "t3.small"
    
    database:
      postgres: "db.t3.micro"
      storage: "20 GB"
    
    redis: "cache.t2.micro"
```

## 8. Monitoring and Observability

### 8.1 Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from functools import wraps

# Metrics definitions
discord_commands_total = Counter(
    'discord_commands_total',
    'Total Discord commands processed',
    ['command', 'status']
)

webhook_requests_total = Counter(
    'webhook_requests_total',
    'Total webhook requests processed',
    ['endpoint', 'status']
)

openai_requests_total = Counter(
    'openai_requests_total',
    'Total OpenAI API requests',
    ['model', 'status']
)

summary_generation_duration = Histogram(
    'summary_generation_duration_seconds',
    'Time spent generating summaries',
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))
)

active_discord_connections = Gauge(
    'active_discord_connections',
    'Number of active Discord connections'
)

message_processing_queue_size = Gauge(
    'message_processing_queue_size',
    'Number of messages waiting to be processed'
)

def track_performance(metric_name: str):
    """Decorator to track function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                if metric_name == 'summary_generation':
                    summary_generation_duration.observe(duration)
        return wrapper
    return decorator

# Usage in service classes
class SummarizationService:
    @track_performance('summary_generation')
    async def summarize_messages(self, messages: List[Message]) -> Summary:
        # Implementation
        pass

# Start metrics server
start_http_server(8080)
```

### 8.2 Health Checks

```python
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import asyncio
import aioredis
import asyncpg

app = FastAPI()

class HealthChecker:
    def __init__(self, config):
        self.config = config
        self.checks = {
            'database': self.check_database,
            'redis': self.check_redis,
            'discord_api': self.check_discord_api,
            'openai_api': self.check_openai_api,
        }
    
    async def check_database(self) -> dict:
        try:
            conn = await asyncpg.connect(self.config.database_url)
            await conn.fetchval('SELECT 1')
            await conn.close()
            return {'status': 'healthy', 'latency_ms': 0}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def check_redis(self) -> dict:
        try:
            redis = aioredis.from_url(self.config.redis_url)
            await redis.ping()
            await redis.close()
            return {'status': 'healthy'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def run_all_checks(self) -> dict:
        results = {}
        overall_status = 'healthy'
        
        for name, check_func in self.checks.items():
            try:
                result = await asyncio.wait_for(check_func(), timeout=5.0)
                results[name] = result
                if result['status'] != 'healthy':
                    overall_status = 'unhealthy'
            except asyncio.TimeoutError:
                results[name] = {'status': 'timeout'}
                overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'checks': results,
            'timestamp': datetime.utcnow().isoformat()
        }

health_checker = HealthChecker(config)

@app.get('/health')
async def health_check():
    """Basic health check - returns 200 if app is running"""
    return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}

@app.get('/ready')
async def readiness_check():
    """Comprehensive readiness check"""
    results = await health_checker.run_all_checks()
    
    if results['status'] == 'healthy':
        return JSONResponse(content=results, status_code=200)
    else:
        return JSONResponse(content=results, status_code=503)
```

This deployment architecture provides:

1. **Scalable Infrastructure**: Auto-scaling Kubernetes deployment
2. **High Availability**: Multi-AZ database, load balancing
3. **Security**: Network isolation, secret management, SSL/TLS
4. **Monitoring**: Comprehensive metrics and health checks
5. **CI/CD**: Automated testing and deployment pipeline
6. **Cost Optimization**: Right-sized resources for different environments
7. **Disaster Recovery**: Automated backups and recovery procedures