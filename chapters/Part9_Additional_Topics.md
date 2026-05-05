# Part IX: Additional Topics & Deep Dives
## Missing Concepts and Extended Explanations

---

# Chapter 39: Docker Fundamentals for FastAPI

## 39.1 What is Docker?

Docker packages your application and all its dependencies into a "container" - a lightweight, portable unit that runs anywhere.

```
Without Docker:
┌─────────────────────────────────────────────────────────┐
│  "It works on my machine!"                              │
│                                                         │
│  Developer Machine    Production Server                 │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Python 3.11     │  │ Python 3.9      │ ← Different! │
│  │ FastAPI 0.109   │  │ FastAPI 0.100   │ ← Different! │
│  │ Ubuntu 22.04    │  │ Amazon Linux 2  │ ← Different! │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
│  Result: Bugs, crashes, "works for me" syndrome         │
└─────────────────────────────────────────────────────────┘

With Docker:
┌─────────────────────────────────────────────────────────┐
│  Same container everywhere!                             │
│                                                         │
│  Developer Machine    Production Server                 │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │              │
│  │ │  Container  │ │  │ │  Container  │ │              │
│  │ │ Python 3.11 │ │  │ │ Python 3.11 │ │ ← Same!     │
│  │ │ FastAPI 0.109│ │  │ │ FastAPI 0.109│ │ ← Same!     │
│  │ │ Your Code   │ │  │ │ Your Code   │ │ ← Same!     │
│  │ └─────────────┘ │  │ └─────────────┘ │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 39.2 Docker Terminology

```
┌──────────────────────────────────────────────────────────┐
│                    DOCKER CONCEPTS                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  IMAGE                                                    │
│  └── Blueprint/recipe for your container                  │
│      Like a "class" in programming                        │
│      Immutable - doesn't change                           │
│                                                           │
│  CONTAINER                                                │
│  └── Running instance of an image                         │
│      Like an "object" created from a class                │
│      Can have multiple containers from one image          │
│                                                           │
│  DOCKERFILE                                               │
│  └── Text file with instructions to build an image        │
│      Recipe for creating the image                        │
│                                                           │
│  REGISTRY (Docker Hub, ECR)                               │
│  └── Storage for images                                   │
│      Like GitHub but for Docker images                    │
│                                                           │
│  VOLUME                                                   │
│  └── Persistent storage that survives container restart   │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 39.3 Dockerfile for FastAPI - Complete Guide

### Basic Dockerfile (Development)

```dockerfile
# Dockerfile.dev
# Use official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Expose port (documentation - doesn't actually open port)
EXPOSE 8000

# Command to run when container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Production Dockerfile (Optimized)

```dockerfile
# Dockerfile
# ========================================
# Stage 1: Builder (install dependencies)
# ========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Runtime (final image)
# ========================================
FROM python:3.11-slim AS runtime

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup ./app ./app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with production server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Understanding Each Line

```dockerfile
# FROM - Base image to start from
FROM python:3.11-slim
# "slim" variants are smaller, good for production
# Options: python:3.11 (full), python:3.11-slim, python:3.11-alpine (smallest but has issues)

# WORKDIR - Sets the working directory (like cd)
WORKDIR /app
# All following commands run from /app

# COPY - Copy files from your machine to container
COPY requirements.txt .
# Copies requirements.txt to /app/requirements.txt
# The "." means current WORKDIR

# RUN - Execute commands during image BUILD
RUN pip install -r requirements.txt
# This happens once when building the image

# EXPOSE - Document which port the app uses
EXPOSE 8000
# Doesn't actually open the port - just documentation

# CMD - Command to run when container STARTS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
# Use array format for proper signal handling
```

---

## 39.4 Docker Commands Cheat Sheet

```bash
# Build an image
docker build -t my-fastapi:1.0 .
# -t = tag/name the image
# . = use Dockerfile in current directory

# Run a container
docker run -p 8000:8000 my-fastapi:1.0
# -p 8000:8000 = map host port 8000 to container port 8000

# Run with environment variables
docker run -p 8000:8000 -e DATABASE_URL=postgres://... my-fastapi:1.0

# Run in background (detached)
docker run -d -p 8000:8000 my-fastapi:1.0

# Run with volume (for development)
docker run -v $(pwd)/app:/app/app -p 8000:8000 my-fastapi:1.0
# Changes to local files reflect in container

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop a container
docker stop <container_id>

# View logs
docker logs <container_id>
docker logs -f <container_id>  # Follow/stream logs

# Shell into container
docker exec -it <container_id> bash

# Remove container
docker rm <container_id>

# List images
docker images

# Remove image
docker rmi <image_id>

# Push to registry
docker tag my-fastapi:1.0 myregistry/my-fastapi:1.0
docker push myregistry/my-fastapi:1.0
```

---

## 39.5 Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app  # Hot reload
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    networks:
      - app-network

  # PostgreSQL Database
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=mydb
    ports:
      - "5432:5432"
    networks:
      - app-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - app-network

  # PgAdmin (database GUI)
  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@admin.com
      - PGADMIN_DEFAULT_PASSWORD=admin
    ports:
      - "5050:80"
    depends_on:
      - db
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### Docker Compose Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Rebuild and start
docker-compose up --build

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs api
docker-compose logs -f api  # Follow

# Run command in service
docker-compose exec api bash
docker-compose exec db psql -U user -d mydb

# Scale service
docker-compose up --scale api=3
```

---

# Chapter 40: CI/CD Pipelines

## 40.1 What is CI/CD?

```
CI (Continuous Integration):
┌─────────────────────────────────────────────────────────┐
│  Every code push triggers automatic:                    │
│                                                         │
│  1. Build the code                                      │
│  2. Run tests                                           │
│  3. Check code quality (lint)                           │
│  4. Build Docker image                                  │
│                                                         │
│  Purpose: Find bugs early, before they reach production │
└─────────────────────────────────────────────────────────┘

CD (Continuous Deployment/Delivery):
┌─────────────────────────────────────────────────────────┐
│  After CI passes, automatically:                        │
│                                                         │
│  Delivery: Deploy to staging (manual approval for prod) │
│  Deployment: Deploy directly to production              │
│                                                         │
│  Purpose: Fast, reliable releases                       │
└─────────────────────────────────────────────────────────┘
```

---

## 40.2 GitHub Actions for FastAPI

### Basic CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov httpx

      - name: Run linting
        run: |
          pip install ruff
          ruff check app/

      - name: Run type checking
        run: |
          pip install mypy
          mypy app/ --ignore-missing-imports

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
        run: |
          pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Build and Push Docker Image

```yaml
# .github/workflows/docker.yml
name: Build and Push Docker

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
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
            type=semver,pattern={{version}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Deploy to AWS Lambda

```yaml
# .github/workflows/deploy-lambda.yml
name: Deploy to Lambda

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install AWS CDK
        run: npm install -g aws-cdk

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install aws-cdk-lib constructs

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy with CDK
        run: |
          cd cdk
          cdk deploy --require-approval never
```

### Deploy to EKS

```yaml
# .github/workflows/deploy-eks.yml
name: Deploy to EKS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  EKS_CLUSTER: my-cluster
  ECR_REPOSITORY: my-fastapi

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name $EKS_CLUSTER --region $AWS_REGION

      - name: Deploy to EKS
        env:
          IMAGE: ${{ steps.build-image.outputs.image }}
        run: |
          # Update image in deployment
          kubectl set image deployment/fastapi \
            fastapi=$IMAGE \
            -n production
          
          # Wait for rollout
          kubectl rollout status deployment/fastapi -n production
```

---

# Chapter 41: Error Handling Deep Dive

## 41.1 Comprehensive Error Handling

```python
# app/exceptions.py
from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class AppException(Exception):
    """Base exception for application errors."""
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class NotFoundError(AppException):
    """Resource not found."""
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with id '{resource_id}' not found",
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": resource_id}
        )

class ValidationError(AppException):
    """Validation error."""
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error: {message}",
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, "error": message}
        )

class AuthenticationError(AppException):
    """Authentication failed."""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )

class AuthorizationError(AppException):
    """Not authorized to perform action."""
    def __init__(self, action: str):
        super().__init__(
            message=f"Not authorized to {action}",
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details={"action": action}
        )

class ConflictError(AppException):
    """Resource conflict."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409
        )

class RateLimitError(AppException):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after_seconds": retry_after}
        )

class ExternalServiceError(AppException):
    """External service error."""
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error: {service}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service, "error": message}
        )
```

## 41.2 Exception Handlers

```python
# app/handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions import AppException
import logging
import traceback

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI):
    """Register all exception handlers."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application-specific exceptions."""
        logger.warning(
            f"AppException: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "path": request.url.path,
                "details": exc.details
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError as validation error."""
        logger.warning(f"ValueError: {exc}")
        
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc)
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            f"Unexpected error: {exc}",
            extra={
                "path": request.url.path,
                "traceback": traceback.format_exc()
            }
        )
        
        # In production, don't expose internal errors
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            }
        )

# app/main.py
from fastapi import FastAPI
from app.handlers import setup_exception_handlers

app = FastAPI()
setup_exception_handlers(app)
```

## 41.3 Using Error Classes

```python
# app/services/user_service.py
from app.exceptions import NotFoundError, ConflictError, ValidationError

class UserService:
    async def get_user(self, user_id: str) -> User:
        user = await self.repository.get(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    async def create_user(self, data: UserCreate) -> User:
        # Check if email already exists
        existing = await self.repository.get_by_email(data.email)
        if existing:
            raise ConflictError(f"User with email '{data.email}' already exists")
        
        # Validate age
        if data.age < 18:
            raise ValidationError("age", "Must be at least 18 years old")
        
        return await self.repository.create(data)
```

---

# Chapter 42: Logging and Monitoring

## 42.1 Structured Logging with Python

```python
# app/logging_config.py
import logging
import json
import sys
from datetime import datetime
from typing import Any
import os

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for better parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)

def setup_logging(level: str = "INFO"):
    """Configure application logging."""
    
    # Create formatter based on environment
    if os.getenv("ENVIRONMENT") == "production":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

# Usage
setup_logging()
logger = logging.getLogger(__name__)

# Log with context
logger.info(
    "User created",
    extra={"extra_data": {"user_id": "123", "email": "test@example.com"}}
)
```

## 42.2 Request Logging Middleware

```python
# app/middleware/logging.py
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={"extra_data": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            }}
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed",
                extra={"extra_data": {
                    "request_id": request_id,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                }}
            )
            raise
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={"extra_data": {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }}
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response

# app/main.py
from app.middleware.logging import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
```

## 42.3 CloudWatch Integration (Lambda)

```python
# For Lambda - automatic CloudWatch integration
import logging
import json

# AWS Lambda automatically captures stdout/stderr to CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    # Structured log for CloudWatch Insights
    logger.info(json.dumps({
        "event": "processing_started",
        "request_id": context.aws_request_id,
        "function_name": context.function_name,
        "input_size": len(json.dumps(event))
    }))
    
    try:
        result = process(event)
        logger.info(json.dumps({
            "event": "processing_completed",
            "request_id": context.aws_request_id,
            "result_count": len(result)
        }))
        return result
    except Exception as e:
        logger.error(json.dumps({
            "event": "processing_failed",
            "request_id": context.aws_request_id,
            "error": str(e)
        }))
        raise
```

---

# Chapter 43: AWS Services Deep Dive

## 43.1 Route 53 (DNS) with CDK

```python
from aws_cdk import (
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
)

class DNSStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Import existing hosted zone
        zone = route53.HostedZone.from_lookup(
            self, "Zone",
            domain_name="example.com"
        )
        
        # OR create new hosted zone
        zone = route53.HostedZone(
            self, "HostedZone",
            zone_name="example.com"
        )
        
        # SSL Certificate
        certificate = acm.Certificate(
            self, "Certificate",
            domain_name="api.example.com",
            validation=acm.CertificateValidation.from_dns(zone)
        )
        
        # A Record pointing to API Gateway
        route53.ARecord(
            self, "ApiRecord",
            zone=zone,
            record_name="api",  # api.example.com
            target=route53.RecordTarget.from_alias(
                targets.ApiGateway(api_gateway)
            )
        )
        
        # A Record pointing to ALB (Kubernetes)
        route53.ARecord(
            self, "AppRecord",
            zone=zone,
            record_name="app",
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(alb)
            )
        )
```

## 43.2 CloudFront (CDN) with CDK

```python
from aws_cdk import (
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)

class CDNStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # CloudFront for S3 (static content)
        distribution = cloudfront.Distribution(
            self, "StaticDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(static_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            domain_names=["static.example.com"],
            certificate=certificate,
        )
        
        # CloudFront for API Gateway (API caching)
        api_distribution = cloudfront.Distribution(
            self, "ApiDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    f"{api.rest_api_id}.execute-api.{self.region}.amazonaws.com",
                    origin_path=f"/{api.deployment_stage.stage_name}"
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,  # Don't cache API
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
            domain_names=["api.example.com"],
            certificate=certificate,
        )
```

## 43.3 Cognito (Authentication) with CDK

```python
from aws_cdk import (
    aws_cognito as cognito,
)

class AuthStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # User Pool
        user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name="my-app-users",
            
            # Sign-in options
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            
            # Password policy
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False
            ),
            
            # Email verification
            self_sign_up_enabled=True,
            user_verification=cognito.UserVerificationConfig(
                email_subject="Verify your email",
                email_body="Your verification code is {####}",
                email_style=cognito.VerificationEmailStyle.CODE
            ),
            
            # Account recovery
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            
            # Standard attributes
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                fullname=cognito.StandardAttribute(required=True, mutable=True)
            ),
        )
        
        # App Client
        client = user_pool.add_client(
            "AppClient",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True
                ),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID],
                callback_urls=["https://myapp.com/callback"],
                logout_urls=["https://myapp.com/logout"],
            ),
            generate_secret=False,
        )
        
        # Domain for hosted UI
        user_pool.add_domain(
            "Domain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="my-app-auth"
            )
        )
```

## 43.4 RDS (PostgreSQL) with CDK

```python
from aws_cdk import (
    aws_rds as rds,
    aws_ec2 as ec2,
    Duration,
    RemovalPolicy,
)

class DatabaseStack(Stack):
    def __init__(self, scope, id, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Security group for RDS
        db_security_group = ec2.SecurityGroup(
            self, "DbSecurityGroup",
            vpc=vpc,
            description="Security group for RDS"
        )
        
        # Allow Lambda/ECS to connect
        db_security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(5432),
            "Allow PostgreSQL from VPC"
        )
        
        # RDS Instance
        database = rds.DatabaseInstance(
            self, "Database",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[db_security_group],
            
            database_name="myapp",
            credentials=rds.Credentials.from_generated_secret("postgres"),
            
            multi_az=False,  # True for production
            allocated_storage=20,
            max_allocated_storage=100,  # Auto-scaling
            
            backup_retention=Duration.days(7),
            delete_automated_backups=True,
            removal_policy=RemovalPolicy.DESTROY,  # RETAIN for production
            
            cloudwatch_logs_exports=["postgresql"],
        )
        
        # Store connection info in Secrets Manager
        # (Automatically created by credentials.from_generated_secret)
        self.db_secret = database.secret
```

---

# Chapter 44: Performance Testing and Optimization

## 44.1 Load Testing with Locust

```python
# locustfile.py
from locust import HttpUser, task, between
import random

class FastAPIUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when user starts - login."""
        response = self.client.post("/token", data={
            "username": "testuser",
            "password": "testpass"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)  # Weight 3 - runs more often
    def list_items(self):
        """List items - most common operation."""
        self.client.get("/items", headers=self.headers)
    
    @task(2)
    def get_item(self):
        """Get single item."""
        item_id = random.randint(1, 100)
        self.client.get(f"/items/{item_id}", headers=self.headers)
    
    @task(1)
    def create_item(self):
        """Create item - less common."""
        self.client.post(
            "/items",
            json={"name": "Test Item", "price": 9.99},
            headers=self.headers
        )

# Run: locust -f locustfile.py --host=http://localhost:8000
```

## 44.2 Profiling FastAPI

```python
# Middleware for profiling
import cProfile
import pstats
import io
from fastapi import Request

class ProfilingMiddleware:
    def __init__(self, app, profile_all: bool = False):
        self.app = app
        self.profile_all = profile_all
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if profiling requested
        request = Request(scope, receive, send)
        should_profile = self.profile_all or request.query_params.get("profile")
        
        if not should_profile:
            await self.app(scope, receive, send)
            return
        
        # Profile the request
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            await self.app(scope, receive, send)
        finally:
            profiler.disable()
            
            # Print stats
            s = io.StringIO()
            stats = pstats.Stats(profiler, stream=s)
            stats.sort_stats("cumulative")
            stats.print_stats(20)  # Top 20
            print(s.getvalue())
```

---

# Summary: Missing Topics Checklist

After reviewing, these topics are now covered:

| Topic | Status | Chapter |
|-------|--------|---------|
| Docker Fundamentals | ✅ Added | Chapter 39 |
| Dockerfile Best Practices | ✅ Added | Chapter 39 |
| Docker Compose | ✅ Added | Chapter 39 |
| CI/CD with GitHub Actions | ✅ Added | Chapter 40 |
| Deploy to Lambda via CI/CD | ✅ Added | Chapter 40 |
| Deploy to EKS via CI/CD | ✅ Added | Chapter 40 |
| Comprehensive Error Handling | ✅ Added | Chapter 41 |
| Structured Logging | ✅ Added | Chapter 42 |
| CloudWatch Integration | ✅ Added | Chapter 42 |
| Route 53 (DNS) | ✅ Added | Chapter 43 |
| CloudFront (CDN) | ✅ Added | Chapter 43 |
| Cognito (Authentication) | ✅ Added | Chapter 43 |
| RDS (PostgreSQL) | ✅ Added | Chapter 43 |
| Performance Testing | ✅ Added | Chapter 44 |
| Django Framework (DRF, ORM, Admin) | ✅ Added | Chapter 45 (Part 10) |
| Microservices Architecture & Patterns | ✅ Added | Chapter 46 (Part 10) |
| CloudFormation Templates (raw YAML) | ✅ Added | Chapter 47 (Part 10) |

---

*This completes the additional topics for the comprehensive guide.*
