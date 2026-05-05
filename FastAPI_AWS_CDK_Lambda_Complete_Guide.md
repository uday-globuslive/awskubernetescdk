# Complete Guide: FastAPI, AWS CDK, Lambda & Kubernetes
## For Interviews and Real-World Projects

---

# 📚 Chapter Files Index

This guide is organized into detailed chapter files. Below is the complete index:

| File | Content |
|------|---------|
| **Part1_FastAPI_Fundamentals.md** | Chapters 1-3: FastAPI basics, core concepts, Pydantic |
| **Part1_FastAPI_Continued.md** | Chapters 4-5: Dependency injection, authentication, security |
| **Part1_FastAPI_Final.md** | Chapters 6-9: Databases, advanced features, testing, project structure |
| **Part2_AWS_CDK.md** | Chapters 10-11: CDK introduction, apps, stacks, constructs |
| **Part2_AWS_CDK_Continued.md** | Chapters 12-16: S3, DynamoDB, SQS, SNS, API Gateway, Lambda, ECS, VPC, IAM |
| **Part3_Lambda.md** | Chapters 17-22: Lambda fundamentals, configuration, triggers, Python, performance |
| **Part4_Integration.md** | Chapters 23-25: FastAPI on Lambda with Mangum, CDK deployment, architecture |
| **Part5_Kubernetes.md** | Chapters 26-33: Kubernetes fundamentals, workloads, networking, EKS, security |
| **Part6_Interview.md** | Chapters 34-38: Interview questions for FastAPI, CDK, Lambda, K8s, system design |
| **Part7_Projects.md** | 6 Complete projects with code |
| **Part8_Templates_Reference.md** | Production templates and cheat sheets |
| **Part9_Additional_Topics.md** | Docker, CI/CD, error handling, logging, AWS services deep dive |
| **Part10_Django_Microservices_CloudFormation.md** | Django + DRF, Microservices architecture & patterns, raw CloudFormation templates |

---

# Table of Contents

## Part I: FastAPI Fundamentals

### Chapter 1: Introduction to FastAPI
1.1 What is FastAPI?
1.2 Why FastAPI? (Performance, Type Hints, Auto Documentation)
1.3 FastAPI vs Flask vs Django
1.4 Installation and Setup
1.5 Your First FastAPI Application

### Chapter 2: Core Concepts
2.1 Path Operations (GET, POST, PUT, DELETE, PATCH)
2.2 Path Parameters
2.3 Query Parameters
2.4 Request Body with Pydantic Models
2.5 Response Models
2.6 Status Codes and HTTP Exceptions

### Chapter 3: Data Validation with Pydantic
3.1 Pydantic Models Deep Dive
3.2 Field Validation and Constraints
3.3 Custom Validators
3.4 Nested Models
3.5 Optional and Default Values
3.6 Config Classes and Schema Customization

### Chapter 4: Dependency Injection
4.1 Understanding Dependencies
4.2 Creating Dependencies
4.3 Sub-dependencies
4.4 Dependencies with Yield (Context Managers)
4.5 Global Dependencies
4.6 Dependency Overrides for Testing

### Chapter 5: Authentication & Security
5.1 OAuth2 with Password Flow
5.2 JWT Tokens
5.3 API Key Authentication
5.4 OAuth2 Scopes
5.5 CORS Configuration
5.6 Security Best Practices

### Chapter 6: Database Integration
6.1 SQLAlchemy Setup
6.2 Async Database with databases library
6.3 MongoDB with Motor
6.4 Database Migrations with Alembic
6.5 Repository Pattern
6.6 Unit of Work Pattern

### Chapter 7: Advanced Features
7.1 Background Tasks
7.2 WebSockets
7.3 File Uploads and Downloads
7.4 Streaming Responses
7.5 Middleware
7.6 Lifespan Events (startup/shutdown)
7.7 Custom Exception Handlers

### Chapter 8: Testing FastAPI
8.1 TestClient Basics
8.2 Testing with pytest
8.3 Async Testing
8.4 Mocking Dependencies
8.5 Integration Testing
8.6 Test Coverage

### Chapter 9: Project Structure & Best Practices
9.1 Recommended Project Layout
9.2 Router Organization
9.3 Settings Management with Pydantic Settings
9.4 Logging Configuration
9.5 Error Handling Patterns
9.6 API Versioning

---

## Part II: AWS CDK (Cloud Development Kit)

### Chapter 10: Introduction to AWS CDK
10.1 What is Infrastructure as Code (IaC)?
10.2 CDK vs CloudFormation vs Terraform
10.3 CDK Concepts: Apps, Stacks, Constructs
10.4 Installation and Prerequisites
10.5 CDK CLI Commands
10.6 Your First CDK App

### Chapter 11: CDK Fundamentals
11.1 Constructs (L1, L2, L3)
11.2 Stacks and Environments
11.3 Assets
11.4 Context and Parameters
11.5 Tokens and Lazy Values
11.6 Cross-Stack References

### Chapter 12: Core AWS Services with CDK
12.1 S3 Buckets
12.2 DynamoDB Tables
12.3 SQS Queues
12.4 SNS Topics
12.5 API Gateway
12.6 CloudWatch Logs and Alarms

### Chapter 13: Compute Services
13.1 Lambda Functions
13.2 EC2 Instances
13.3 ECS and Fargate
13.4 Step Functions
13.5 EventBridge Rules

### Chapter 14: Networking with CDK
14.1 VPC Configuration
14.2 Subnets (Public, Private, Isolated)
14.3 Security Groups
14.4 NAT Gateways
14.5 Load Balancers (ALB, NLB)
14.6 Route 53 and DNS

### Chapter 15: Security and IAM
15.1 IAM Roles and Policies
15.2 Secrets Manager
15.3 Parameter Store
15.4 KMS Keys
15.5 WAF Configuration
15.6 Resource-Based Policies

### Chapter 16: CDK Patterns and Best Practices
16.1 Construct Libraries
16.2 Aspect-Oriented Programming
16.3 Testing CDK Apps
16.4 CDK Pipelines (CI/CD)
16.5 Multi-Environment Deployments
16.6 Cost Optimization

---

## Part III: AWS Lambda

### Chapter 17: Lambda Fundamentals
17.1 What is Serverless?
17.2 Lambda Execution Model
17.3 Cold Starts and Warm Starts
17.4 Lambda Pricing
17.5 Invocation Types (Sync, Async, Event Source)
17.6 Handler Function Structure

### Chapter 18: Lambda Configuration
18.1 Memory and Timeout Settings
18.2 Environment Variables
18.3 VPC Configuration
18.4 Layers
18.5 Provisioned Concurrency
18.6 Reserved Concurrency
18.7 Function URLs

### Chapter 19: Lambda Triggers
19.1 API Gateway Integration
19.2 S3 Event Triggers
19.3 DynamoDB Streams
19.4 SQS Triggers
19.5 SNS Triggers
19.6 EventBridge Rules
19.7 CloudWatch Events
19.8 Kinesis Streams

### Chapter 20: Lambda with Python
20.1 Python Runtime Versions
20.2 Packaging Dependencies
20.3 Using Lambda Layers for Dependencies
20.4 Powertools for AWS Lambda
20.5 Structured Logging
20.6 Tracing with X-Ray
20.7 Error Handling Patterns

### Chapter 21: Lambda Performance Optimization
21.1 Cold Start Mitigation
21.2 Connection Pooling
21.3 Caching Strategies
21.4 Memory Tuning
21.5 Code Optimization
21.6 Monitoring and Profiling

### Chapter 22: Lambda Security
22.1 Execution Roles
22.2 Resource Policies
22.3 VPC Security
22.4 Secrets Management
22.5 Input Validation
22.6 Logging Sensitive Data

---

## Part IV: Integration - FastAPI + CDK + Lambda

### Chapter 23: Deploying FastAPI on Lambda
23.1 Mangum Adapter
23.2 Lambda Handler Setup
23.3 API Gateway Configuration
23.4 Binary Responses
23.5 CORS Configuration
23.6 Custom Domain Setup

### Chapter 24: CDK for FastAPI Lambda
24.1 Project Structure
24.2 Lambda Function Construct
24.3 API Gateway REST API
24.4 HTTP API vs REST API
24.5 Lambda Layer for Dependencies
24.6 Environment Configuration

### Chapter 25: Complete Architecture Patterns
25.1 Microservices with Lambda
25.2 Event-Driven Architecture
25.3 CQRS Pattern
25.4 Saga Pattern
25.5 API Composition
25.6 Strangler Fig Pattern

---

## Part V: Kubernetes & Container Orchestration

### Chapter 26: Kubernetes Fundamentals
26.1 What is Kubernetes?
26.2 Kubernetes Architecture (Control Plane, Nodes)
26.3 Core Concepts: Pods, Services, Deployments
26.4 ConfigMaps and Secrets
26.5 Namespaces
26.6 Labels and Selectors
26.7 kubectl CLI Essentials

### Chapter 27: Kubernetes Workloads
27.1 Pods Deep Dive
27.2 ReplicaSets
27.3 Deployments and Rolling Updates
27.4 StatefulSets
27.5 DaemonSets
27.6 Jobs and CronJobs
27.7 Horizontal Pod Autoscaler (HPA)

### Chapter 28: Kubernetes Networking
28.1 Service Types (ClusterIP, NodePort, LoadBalancer)
28.2 Ingress Controllers
28.3 Network Policies
28.4 DNS in Kubernetes
28.5 Service Mesh Basics (Istio, Linkerd)

### Chapter 29: Kubernetes Storage
29.1 Volumes and Volume Mounts
29.2 Persistent Volumes (PV)
29.3 Persistent Volume Claims (PVC)
29.4 Storage Classes
29.5 StatefulSet Storage Patterns

### Chapter 30: AWS EKS (Elastic Kubernetes Service)
30.1 EKS Architecture
30.2 Creating EKS Clusters
30.3 Node Groups (Managed, Self-managed, Fargate)
30.4 EKS with CDK
30.5 IAM Roles for Service Accounts (IRSA)
30.6 EKS Add-ons
30.7 EKS Networking (VPC CNI)

### Chapter 31: Deploying FastAPI on Kubernetes
31.1 Containerizing FastAPI (Dockerfile Best Practices)
31.2 Creating Kubernetes Manifests
31.3 Health Checks (Liveness, Readiness)
31.4 Resource Requests and Limits
31.5 Scaling Strategies
31.6 Blue-Green and Canary Deployments
31.7 Monitoring with Prometheus/Grafana

### Chapter 32: Kubernetes Security
32.1 RBAC (Role-Based Access Control)
32.2 Pod Security Standards
32.3 Network Policies for Isolation
32.4 Secrets Management
32.5 Image Security and Scanning
32.6 Service Accounts

### Chapter 33: Helm & GitOps
33.1 Helm Charts Introduction
33.2 Creating Custom Helm Charts
33.3 Helm Values and Templating
33.4 ArgoCD for GitOps
33.5 Flux CD
33.6 CI/CD Pipelines for Kubernetes

---

## Part VI: Interview Preparation

### Chapter 34: FastAPI Interview Questions

#### Beginner Level
1. What is FastAPI and what are its main features?
2. Explain the difference between path parameters and query parameters.
3. What is Pydantic and how does FastAPI use it?
4. How do you handle different HTTP methods in FastAPI?
5. What is automatic API documentation in FastAPI?

#### Intermediate Level
6. Explain dependency injection in FastAPI.
7. How do you implement authentication in FastAPI?
8. What are background tasks and when would you use them?
9. Explain the difference between sync and async endpoints.
10. How do you handle database connections in FastAPI?

#### Advanced Level
11. How would you implement rate limiting in FastAPI?
12. Explain middleware in FastAPI and give examples.
13. How do you handle file uploads efficiently for large files?
14. Describe strategies for API versioning.
15. How would you implement caching in a FastAPI application?

### Chapter 35: AWS CDK Interview Questions

#### Beginner Level
1. What is AWS CDK and how does it differ from CloudFormation?
2. Explain the concept of constructs in CDK.
3. What are L1, L2, and L3 constructs?
4. How do you deploy a CDK application?
5. What is the difference between `cdk synth` and `cdk deploy`?

#### Intermediate Level
6. How do you manage multiple environments with CDK?
7. Explain cross-stack references.
8. How do you test CDK applications?
9. What are CDK aspects and when would you use them?
10. How do you handle secrets in CDK?

#### Advanced Level
11. Explain CDK Pipelines and their benefits.
12. How do you implement blue-green deployments with CDK?
13. Describe strategies for CDK construct library design.
14. How do you handle circular dependencies in CDK?
15. Explain escape hatches in CDK.

### Chapter 36: Lambda Interview Questions

#### Beginner Level
1. What is AWS Lambda and what are its benefits?
2. Explain cold starts in Lambda.
3. What triggers can invoke a Lambda function?
4. What is the maximum execution time for a Lambda function?
5. How is Lambda pricing calculated?

#### Intermediate Level
6. How do you package dependencies for Lambda?
7. Explain Lambda layers and their use cases.
8. What is provisioned concurrency?
9. How do you handle errors in Lambda?
10. Explain the difference between sync and async invocation.

#### Advanced Level
11. How would you optimize Lambda cold starts?
12. Explain connection pooling in Lambda.
13. How do you implement idempotency in Lambda?
14. Describe strategies for Lambda testing.
15. How would you implement distributed tracing across Lambdas?

### Chapter 37: Kubernetes Interview Questions

#### Beginner Level
1. What is Kubernetes and why is it used?
2. Explain the difference between a Pod and a Container.
3. What is a Deployment in Kubernetes?
4. What are Services and what types exist?
5. What is a Namespace?
6. Explain ConfigMaps and Secrets.
7. What is kubectl?

#### Intermediate Level
8. Explain the difference between ReplicaSet and Deployment.
9. What are liveness and readiness probes?
10. How does Horizontal Pod Autoscaler work?
11. Explain Ingress and Ingress Controllers.
12. What is a StatefulSet and when would you use it?
13. How do you handle persistent storage in Kubernetes?
14. Explain the difference between ClusterIP, NodePort, and LoadBalancer.
15. What are Init Containers?

#### Advanced Level
16. Explain RBAC in Kubernetes.
17. How do you implement blue-green deployments in Kubernetes?
18. What is a Service Mesh and why use one?
19. Explain Pod Disruption Budgets.
20. How do you debug a failing Pod?
21. What are Operators in Kubernetes?
22. Explain the Sidecar pattern.
23. How do you handle secrets rotation in Kubernetes?
24. What is Helm and how does it help?
25. Explain GitOps and ArgoCD.

### Chapter 38: EKS Interview Questions

#### Beginner Level
1. What is Amazon EKS?
2. What are the benefits of using EKS over self-managed Kubernetes?
3. What are EKS node groups?
4. Explain the difference between managed and self-managed node groups.

#### Intermediate Level
5. What is AWS Fargate for EKS?
6. Explain IAM Roles for Service Accounts (IRSA).
7. How do you expose services externally in EKS?
8. What are EKS add-ons?
9. How do you handle logging in EKS?

#### Advanced Level
10. How do you implement multi-cluster strategies with EKS?
11. Explain EKS security best practices.
12. How do you handle EKS upgrades?
13. What is the AWS Load Balancer Controller?
14. How do you optimize costs in EKS?
15. Explain EKS networking with VPC CNI.

---

## Part VII: Hands-On Projects

### Project 1: REST API with FastAPI (Beginner)
**Description:** Build a complete CRUD API for a task management system.

**Features:**
- User registration and authentication
- Task creation, reading, updating, deletion
- Task categories and tags
- Due date filtering
- Pagination and sorting

**Tech Stack:**
- FastAPI
- SQLAlchemy + PostgreSQL
- JWT Authentication
- Pydantic validation

**Learning Outcomes:**
- REST API design
- Database integration
- Authentication flow
- Input validation

### Project 2: Serverless Image Processing Pipeline (Intermediate)
**Description:** Build an image processing service that automatically resizes and optimizes images.

**Architecture:**
```
S3 Upload → Lambda → Process Image → S3 Output → SNS Notification
```

**Features:**
- Automatic thumbnail generation
- Multiple output sizes
- Format conversion (JPEG, PNG, WebP)
- Metadata extraction
- Processing status notifications

**Tech Stack:**
- AWS CDK (Python)
- Lambda with Pillow
- S3 for storage
- SNS for notifications
- DynamoDB for metadata

**Learning Outcomes:**
- Event-driven architecture
- Lambda triggers
- S3 operations
- CDK infrastructure

### Project 3: Real-time Chat API with WebSockets (Intermediate)
**Description:** Build a real-time chat application with FastAPI WebSockets.

**Features:**
- Real-time messaging
- Chat rooms
- User presence
- Message history
- File sharing

**Tech Stack:**
- FastAPI WebSockets
- Redis for pub/sub
- PostgreSQL for persistence
- JWT authentication

**Learning Outcomes:**
- WebSocket handling
- Real-time communication
- Message queuing
- Scaling considerations

### Project 4: Microservices E-commerce Platform (Advanced)
**Description:** Build a complete e-commerce backend using microservices architecture.

**Services:**
1. **User Service** - Authentication, profiles
2. **Product Service** - Catalog, inventory
3. **Order Service** - Cart, checkout
4. **Payment Service** - Payment processing
5. **Notification Service** - Email, SMS

**Architecture:**
```
API Gateway → Lambda Functions → DynamoDB/RDS
                    ↓
            EventBridge/SQS
                    ↓
            Notification Lambda
```

**Tech Stack:**
- FastAPI for each service
- AWS CDK for infrastructure
- Lambda for compute
- DynamoDB for data
- EventBridge for events
- Step Functions for orchestration

**Learning Outcomes:**
- Microservices design
- Event-driven architecture
- Saga pattern
- Service communication

### Project 5: Serverless Data Pipeline (Advanced)
**Description:** Build an ETL pipeline for processing and analyzing data.

**Features:**
- CSV/JSON file ingestion
- Data transformation
- Data validation
- Aggregation and reporting
- Scheduled and on-demand processing

**Architecture:**
```
S3 → Lambda → Transform → DynamoDB → Lambda → Report → S3
         ↓
    Step Functions (Orchestration)
```

**Tech Stack:**
- AWS CDK
- Lambda with pandas
- Step Functions
- DynamoDB/Athena
- S3 for storage
- EventBridge for scheduling

**Learning Outcomes:**
- Data pipeline design
- Step Functions orchestration
- Error handling and retries
- Cost optimization

### Project 6: API Gateway with Rate Limiting and Caching (Intermediate)
**Description:** Build a production-ready API gateway with enterprise features.

**Features:**
- Request rate limiting
- Response caching
- API key management
- Usage plans and quotas
- Request/response logging
- Custom authorizers

**Tech Stack:**
- FastAPI
- AWS CDK
- API Gateway
- Lambda
- ElastiCache (Redis)
- CloudWatch

**Learning Outcomes:**
- API Gateway features
- Caching strategies
- Security implementation
- Monitoring and logging

### Project 7: Document Processing Service (Advanced)
**Description:** Build a service that processes documents (PDF, DOCX) and extracts text.

**Features:**
- Document upload
- Text extraction
- OCR for images
- Full-text search
- Document summarization

**Architecture:**
```
Upload API → S3 → Lambda → Textract/Comprehend → OpenSearch
```

**Tech Stack:**
- FastAPI for upload API
- AWS CDK
- Lambda
- Amazon Textract
- Amazon Comprehend
- OpenSearch

**Learning Outcomes:**
- AWS AI services
- Document processing
- Search implementation
- Async processing

### Project 8: FastAPI Microservices on Kubernetes (Advanced)
**Description:** Deploy a complete microservices application on EKS with production-ready features.

**Services:**
1. **API Gateway Service** - Request routing, authentication
2. **User Service** - User management
3. **Product Service** - Product catalog
4. **Order Service** - Order processing

**Architecture:**
```
Internet → ALB → Ingress Controller → Services
                        ↓
    ┌─────────┬─────────┬─────────┐
    │  User   │ Product │  Order  │
    │  Pods   │  Pods   │  Pods   │
    └────┬────┴────┬────┴────┬────┘
         │         │         │
    ┌────┴─────────┴─────────┴────┐
    │      PostgreSQL / Redis     │
    └─────────────────────────────┘
```

**Features:**
- Service discovery with Kubernetes DNS
- Horizontal Pod Autoscaling
- Rolling deployments
- Health checks (liveness/readiness)
- Centralized logging (Fluent Bit → CloudWatch)
- Distributed tracing (X-Ray)
- Service mesh with Istio (optional)

**Tech Stack:**
- FastAPI for each microservice
- AWS CDK for EKS infrastructure
- Kubernetes manifests / Helm charts
- Amazon RDS PostgreSQL
- Amazon ElastiCache Redis
- AWS ALB Ingress Controller
- Prometheus + Grafana for monitoring

**Learning Outcomes:**
- Kubernetes deployment strategies
- Service mesh concepts
- Container orchestration
- Production monitoring

### Project 9: CI/CD Pipeline with GitOps for EKS (Intermediate)
**Description:** Build a complete CI/CD pipeline using GitOps principles.

**Pipeline Flow:**
```
GitHub Push → GitHub Actions → Build & Test → Push to ECR
                                    ↓
                            Update Helm Values
                                    ↓
                        ArgoCD Sync → EKS Deploy
```

**Features:**
- Automated testing on PR
- Container image building
- Image vulnerability scanning
- GitOps-based deployments
- Automatic rollbacks
- Multi-environment support (dev, staging, prod)

**Tech Stack:**
- GitHub Actions
- Amazon ECR
- ArgoCD
- Helm
- AWS CDK for infrastructure
- EKS

**Learning Outcomes:**
- CI/CD best practices
- GitOps workflow
- Container security
- Multi-environment management

### Project 10: Event-Driven Microservices on Kubernetes (Advanced)
**Description:** Build an event-driven architecture using Kubernetes and message queues.

**Architecture:**
```
FastAPI Services → Amazon SQS/SNS → Consumer Pods
        ↓                              ↓
   DynamoDB ←─────── Processing ───────┘
```

**Features:**
- Asynchronous message processing
- Event sourcing
- Dead letter queues
- Retry mechanisms
- Event replay capabilities
- Saga pattern implementation

**Tech Stack:**
- FastAPI producers
- Amazon SQS/SNS
- Kubernetes Jobs for consumers
- DynamoDB for event store
- KEDA for event-driven autoscaling

**Learning Outcomes:**
- Event-driven design patterns
- Message queue integration
- KEDA autoscaling
- Distributed transactions

### Project 11: Kubernetes-based ML Model Serving (Advanced)
**Description:** Deploy and serve ML models using FastAPI on Kubernetes.

**Architecture:**
```
Request → Ingress → FastAPI Pod → Model Inference
                         ↓
                 Model Store (S3)
                         ↓
                 Prediction Response
```

**Features:**
- Model versioning
- A/B testing for models
- Canary deployments
- GPU support (optional)
- Batch prediction support
- Model monitoring

**Tech Stack:**
- FastAPI for serving
- Kubernetes with GPU nodes (optional)
- S3 for model storage
- MLflow for model registry
- Prometheus for metrics

**Learning Outcomes:**
- ML model deployment
- Model versioning strategies
- A/B testing implementation
- Resource optimization for ML

### Project 12: Multi-Region Kubernetes Deployment (Expert)
**Description:** Deploy a globally distributed application across multiple EKS clusters.

**Architecture:**
```
Route 53 (Geo DNS)
    ├── us-east-1 EKS Cluster
    ├── eu-west-1 EKS Cluster
    └── ap-southeast-1 EKS Cluster
            ↓
    Global DynamoDB / Aurora Global
```

**Features:**
- Multi-region failover
- Global load balancing
- Data replication
- Disaster recovery
- Region-specific configurations

**Tech Stack:**
- Multiple EKS clusters
- Route 53 with health checks
- Aurora Global Database
- DynamoDB Global Tables
- AWS CDK for multi-region deployment

**Learning Outcomes:**
- Multi-region architecture
- Disaster recovery planning
- Global data consistency
- High availability patterns

---

## Part VIII: Code Examples and Templates

### Chapter 39: FastAPI Code Templates

#### Basic CRUD Application
```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

app = FastAPI()

# Pydantic Models
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    
    class Config:
        from_attributes = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.post("/items/", response_model=Item)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = ItemModel(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/", response_model=List[Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(ItemModel).offset(skip).limit(limit).all()
    return items

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted"}
```

#### JWT Authentication
```python
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

### Chapter 40: AWS CDK Templates

#### Lambda with API Gateway
```python
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    Duration,
)
from constructs import Construct

class ApiLambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Lambda function
        handler = _lambda.Function(
            self, "ApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("lambda"),
            handler="main.handler",
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "ENV": "production"
            }
        )

        # API Gateway
        api = apigw.RestApi(
            self, "Api",
            rest_api_name="My API",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=1000,
                throttling_burst_limit=500
            )
        )

        # Integration
        integration = apigw.LambdaIntegration(handler)
        
        # Resources and methods
        items = api.root.add_resource("items")
        items.add_method("GET", integration)
        items.add_method("POST", integration)
        
        item = items.add_resource("{id}")
        item.add_method("GET", integration)
        item.add_method("PUT", integration)
        item.add_method("DELETE", integration)
```

#### DynamoDB with Lambda
```python
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
)
from constructs import Construct

class DynamoLambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # DynamoDB Table
        table = dynamodb.Table(
            self, "ItemsTable",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # GSI
        table.add_global_secondary_index(
            index_name="gsi1",
            partition_key=dynamodb.Attribute(
                name="gsi1pk",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="gsi1sk",
                type=dynamodb.AttributeType.STRING
            ),
        )

        # Lambda
        handler = _lambda.Function(
            self, "Handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("lambda"),
            handler="main.handler",
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        # Grant permissions
        table.grant_read_write_data(handler)
```

#### S3 Event-Driven Lambda
```python
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
)
from constructs import Construct

class S3LambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # S3 Bucket
        bucket = s3.Bucket(
            self, "UploadBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Lambda
        processor = _lambda.Function(
            self, "Processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("lambda"),
            handler="processor.handler",
            environment={
                "BUCKET_NAME": bucket.bucket_name
            }
        )

        # Grant permissions
        bucket.grant_read_write(processor)

        # S3 Event notification
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor),
            s3.NotificationKeyFilter(prefix="uploads/")
        )
```

### Chapter 41: Lambda Handler Templates

#### FastAPI on Lambda with Mangum
```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from Lambda!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

# Lambda handler
handler = Mangum(app, lifespan="off")
```

#### DynamoDB CRUD Handler
```python
import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

def handler(event, context):
    http_method = event['httpMethod']
    path = event['path']
    
    try:
        if http_method == 'GET' and path == '/items':
            response = table.scan()
            return {
                'statusCode': 200,
                'body': json.dumps(response['Items'], cls=DecimalEncoder)
            }
        
        elif http_method == 'GET' and path.startswith('/items/'):
            item_id = path.split('/')[-1]
            response = table.get_item(Key={'id': item_id})
            if 'Item' not in response:
                return {'statusCode': 404, 'body': 'Not found'}
            return {
                'statusCode': 200,
                'body': json.dumps(response['Item'], cls=DecimalEncoder)
            }
        
        elif http_method == 'POST' and path == '/items':
            body = json.loads(event['body'])
            table.put_item(Item=body)
            return {
                'statusCode': 201,
                'body': json.dumps(body)
            }
        
        elif http_method == 'DELETE' and path.startswith('/items/'):
            item_id = path.split('/')[-1]
            table.delete_item(Key={'id': item_id})
            return {'statusCode': 204, 'body': ''}
        
        return {'statusCode': 400, 'body': 'Bad request'}
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

#### S3 Event Handler
```python
import json
import boto3
import urllib.parse

s3 = boto3.client('s3')

def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        
        print(f"Processing {key} from {bucket}")
        
        # Get object
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Process content
        processed = process_file(content)
        
        # Save processed result
        output_key = f"processed/{key}"
        s3.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=processed
        )
        
        print(f"Saved processed file to {output_key}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }

def process_file(content):
    # Your processing logic here
    return content
```

### Chapter 42: Kubernetes & EKS Templates

#### FastAPI Dockerfile
```dockerfile
# Multi-stage build for FastAPI
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY ./app ./app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
  labels:
    app: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
      - name: fastapi
        image: your-ecr-repo/fastapi-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Kubernetes Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
spec:
  selector:
    app: fastapi-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Ingress with ALB
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: fastapi-service
            port:
              number: 80
```

#### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### ConfigMap and Secrets
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  CORS_ORIGINS: "https://example.com"

---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  database-url: cG9zdGdyZXNxbDovL3VzZXI6cGFzc0Bob3N0OjU0MzIvZGI=  # base64 encoded
  jwt-secret: c2VjcmV0LWtleQ==
```

#### CDK EKS Cluster
```python
from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct

class EksStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # VPC
        vpc = ec2.Vpc(
            self, "EksVpc",
            max_azs=3,
            nat_gateways=1,
        )

        # EKS Cluster
        cluster = eks.Cluster(
            self, "EksCluster",
            cluster_name="my-cluster",
            version=eks.KubernetesVersion.V1_29,
            vpc=vpc,
            default_capacity=0,  # We'll add managed node groups
        )

        # Managed Node Group
        cluster.add_nodegroup_capacity(
            "ManagedNodeGroup",
            instance_types=[ec2.InstanceType("t3.medium")],
            min_size=2,
            max_size=10,
            desired_size=3,
            disk_size=50,
        )

        # Fargate Profile (optional)
        cluster.add_fargate_profile(
            "FargateProfile",
            selectors=[
                eks.Selector(namespace="fargate-workloads")
            ]
        )
```

#### Helm Chart CDK Integration
```python
from aws_cdk import (
    Stack,
    aws_eks as eks,
)
from constructs import Construct

class HelmDeploymentStack(Stack):
    def __init__(self, scope: Construct, id: str, cluster: eks.Cluster, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Deploy AWS Load Balancer Controller
        cluster.add_helm_chart(
            "AwsLoadBalancerController",
            chart="aws-load-balancer-controller",
            repository="https://aws.github.io/eks-charts",
            namespace="kube-system",
            values={
                "clusterName": cluster.cluster_name,
                "serviceAccount": {
                    "create": False,
                    "name": "aws-load-balancer-controller"
                }
            }
        )

        # Deploy application using Helm
        cluster.add_helm_chart(
            "FastApiApp",
            chart="./helm/fastapi-app",
            namespace="default",
            values={
                "image": {
                    "repository": "your-ecr-repo/fastapi-app",
                    "tag": "latest"
                },
                "replicas": 3,
                "resources": {
                    "requests": {"memory": "256Mi", "cpu": "250m"},
                    "limits": {"memory": "512Mi", "cpu": "500m"}
                }
            }
        )
```

#### Basic Helm Chart Structure
```yaml
# Chart.yaml
apiVersion: v2
name: fastapi-app
description: A Helm chart for FastAPI application
version: 1.0.0
appVersion: "1.0.0"

---
# values.yaml
replicaCount: 3

image:
  repository: your-ecr-repo/fastapi-app
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

env:
  - name: ENVIRONMENT
    value: production
```

---

## Part IX: Quick Reference

### Chapter 43: FastAPI Cheat Sheet

#### Common Imports
```python
from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union
```

#### Route Decorators
```python
@app.get("/")           # GET request
@app.post("/")          # POST request
@app.put("/")           # PUT request
@app.delete("/")        # DELETE request
@app.patch("/")         # PATCH request
@app.options("/")       # OPTIONS request
@app.head("/")          # HEAD request
```

#### Parameter Types
```python
# Path parameters
@app.get("/items/{item_id}")
def read_item(item_id: int):

# Query parameters
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):

# Request body
@app.post("/items/")
def create_item(item: Item):

# All combined
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item, q: Optional[str] = None):
```

### Chapter 44: CDK CLI Commands

```bash
# Initialize
cdk init app --language python

# Synthesize CloudFormation
cdk synth

# Deploy
cdk deploy
cdk deploy --all
cdk deploy StackName

# Diff
cdk diff

# Destroy
cdk destroy

# Bootstrap
cdk bootstrap aws://ACCOUNT/REGION

# List stacks
cdk list
```

### Chapter 45: Lambda Limits Reference

| Resource | Limit |
|----------|-------|
| Memory | 128 MB - 10,240 MB |
| Timeout | 15 minutes max |
| Deployment package (direct) | 50 MB (zipped) |
| Deployment package (S3) | 250 MB (unzipped) |
| Environment variables | 4 KB total |
| /tmp storage | 512 MB - 10,240 MB |
| Concurrent executions | 1,000 (default) |
| Burst concurrency | 500-3000 (region) |

### Chapter 46: Kubernetes Cheat Sheet

#### kubectl Basic Commands
```bash
# Cluster Info
kubectl cluster-info
kubectl get nodes
kubectl get namespaces

# Pods
kubectl get pods
kubectl get pods -n <namespace>
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl logs -f <pod-name>              # Follow logs
kubectl exec -it <pod-name> -- /bin/sh  # Shell into pod
kubectl delete pod <pod-name>

# Deployments
kubectl get deployments
kubectl describe deployment <name>
kubectl scale deployment <name> --replicas=5
kubectl rollout status deployment/<name>
kubectl rollout history deployment/<name>
kubectl rollout undo deployment/<name>

# Services
kubectl get services
kubectl describe service <name>
kubectl expose deployment <name> --port=80 --type=LoadBalancer

# ConfigMaps & Secrets
kubectl get configmaps
kubectl get secrets
kubectl create configmap <name> --from-file=<path>
kubectl create secret generic <name> --from-literal=key=value

# Apply manifests
kubectl apply -f <file.yaml>
kubectl apply -f <directory>/
kubectl delete -f <file.yaml>

# Debugging
kubectl get events
kubectl top pods
kubectl top nodes
```

#### Kubernetes Resource Limits Reference

| Resource | Description |
|----------|-------------|
| Pods per node | ~110 (EKS default) |
| Services per cluster | 10,000 |
| Pods per namespace | No hard limit |
| ConfigMap size | 1 MB |
| Secret size | 1 MB |
| Container image size | Varies by node storage |

#### EKS Specific Commands
```bash
# Update kubeconfig
aws eks update-kubeconfig --name <cluster-name> --region <region>

# Get cluster info
aws eks describe-cluster --name <cluster-name>

# List node groups
aws eks list-nodegroups --cluster-name <cluster-name>

# Update node group
aws eks update-nodegroup-config --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --scaling-config minSize=2,maxSize=10,desiredSize=5
```

#### Helm Commands
```bash
# Repository management
helm repo add <name> <url>
helm repo update
helm search repo <keyword>

# Install/Upgrade
helm install <release-name> <chart>
helm install <release-name> <chart> -f values.yaml
helm upgrade <release-name> <chart>
helm upgrade --install <release-name> <chart>

# List and status
helm list
helm status <release-name>
helm history <release-name>

# Uninstall
helm uninstall <release-name>

# Create chart
helm create <chart-name>
helm package <chart-directory>
helm template <chart>  # Preview manifests
```

---

## Part X: Additional Topics (Deep Dives)

### Chapter 47: Docker Fundamentals for FastAPI
47.1 What is Docker?
47.2 Docker Terminology
47.3 Dockerfile for FastAPI (Development & Production)
47.4 Docker Commands Cheat Sheet
47.5 Docker Compose for Local Development

### Chapter 48: CI/CD Pipelines
48.1 What is CI/CD?
48.2 GitHub Actions for FastAPI
48.3 Build and Push Docker Image
48.4 Deploy to AWS Lambda via CI/CD
48.5 Deploy to EKS via CI/CD

### Chapter 49: Error Handling Deep Dive
49.1 Comprehensive Error Classes
49.2 Custom Exception Handlers
49.3 Structured Error Responses

### Chapter 50: Logging and Monitoring
50.1 Structured Logging with Python
50.2 Request Logging Middleware
50.3 CloudWatch Integration for Lambda

### Chapter 51: AWS Services Deep Dive
51.1 Route 53 (DNS) with CDK
51.2 CloudFront (CDN) with CDK
51.3 Cognito (Authentication) with CDK
51.4 RDS (PostgreSQL) with CDK

### Chapter 52: Performance Testing
52.1 Load Testing with Locust
52.2 Profiling FastAPI Applications

---

## Appendices

### Appendix A: Recommended Resources
- FastAPI Documentation: https://fastapi.tiangolo.com/
- AWS CDK Documentation: https://docs.aws.amazon.com/cdk/
- AWS Lambda Documentation: https://docs.aws.amazon.com/lambda/
- Kubernetes Documentation: https://kubernetes.io/docs/
- Amazon EKS Documentation: https://docs.aws.amazon.com/eks/
- Helm Documentation: https://helm.sh/docs/
- Pydantic Documentation: https://docs.pydantic.dev/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/

### Appendix B: Common Error Solutions

| Error | Solution |
|-------|----------|
| 422 Unprocessable Entity | Check request body matches Pydantic model |
| CORS errors | Add CORSMiddleware with correct origins |
| Lambda timeout | Increase timeout or optimize code |
| Cold start issues | Use provisioned concurrency |
| CDK bootstrap error | Run `cdk bootstrap` for the region |
| Pod CrashLoopBackOff | Check logs with `kubectl logs`, verify health checks |
| ImagePullBackOff | Verify image exists and credentials are correct |
| Pending Pod | Check node resources, PVC bindings |
| Service not reachable | Verify selector matches pod labels |
| HPA not scaling | Check metrics-server is running |

### Appendix C: Performance Benchmarks

| Scenario | Typical Response Time |
|----------|----------------------|
| FastAPI simple GET | < 10ms |
| Lambda cold start (Python) | 200-500ms |
| Lambda warm request | < 100ms |
| DynamoDB read | < 10ms |
| S3 small object read | < 50ms |
| Kubernetes pod startup | 2-10 seconds |
| EKS Fargate pod startup | 30-60 seconds |
| Kubernetes service DNS | < 5ms |

---

## Glossary

- **ASGI**: Asynchronous Server Gateway Interface
- **CDK**: Cloud Development Kit
- **Construct**: Basic building block in CDK
- **Cold Start**: Initial invocation delay when Lambda creates new execution environment
- **ConfigMap**: Kubernetes object for storing non-confidential configuration data
- **DaemonSet**: Ensures all nodes run a copy of a Pod
- **Deployment**: Kubernetes object that manages ReplicaSets and provides declarative updates
- **Dependency Injection**: Design pattern for providing dependencies to components
- **EKS**: Elastic Kubernetes Service - AWS managed Kubernetes
- **Fargate**: AWS serverless compute for containers
- **Helm**: Package manager for Kubernetes
- **HPA**: Horizontal Pod Autoscaler
- **IaC**: Infrastructure as Code
- **Ingress**: Kubernetes API object for managing external access to services
- **IRSA**: IAM Roles for Service Accounts
- **JWT**: JSON Web Token
- **kubectl**: Kubernetes command-line tool
- **Lambda Layer**: Shared code/libraries for Lambda functions
- **Liveness Probe**: Health check to know when to restart a container
- **Mangum**: ASGI adapter for AWS Lambda
- **Namespace**: Virtual cluster within a Kubernetes cluster
- **Node**: Worker machine in Kubernetes
- **Pod**: Smallest deployable unit in Kubernetes
- **Pydantic**: Data validation library using Python type hints
- **Readiness Probe**: Health check to know when a container is ready for traffic
- **ReplicaSet**: Maintains a stable set of replica Pods
- **REST**: Representational State Transfer
- **Secret**: Kubernetes object for storing sensitive data
- **Serverless**: Computing model where cloud provider manages servers
- **Service**: Kubernetes abstraction for exposing applications
- **Service Mesh**: Infrastructure layer for service-to-service communication
- **Stack**: Unit of deployment in CDK
- **StatefulSet**: Kubernetes workload for stateful applications

---

*End of Guide*
