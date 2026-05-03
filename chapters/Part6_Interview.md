# Part VI: Interview Preparation
## Complete Interview Guide

---

# Chapter 34: FastAPI Interview Questions

## Beginner Level

### Q1: What is FastAPI and why use it?
**Answer:**
FastAPI is a modern, fast Python web framework for building APIs. Key benefits:
- **Performance**: One of the fastest Python frameworks (comparable to Node.js/Go)
- **Type hints**: Uses Python type hints for validation
- **Auto documentation**: Generates Swagger/OpenAPI docs automatically
- **Async support**: Built-in async/await support
- **Pydantic**: Data validation using Pydantic models

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    name: str
    email: str

@app.post("/users")
async def create_user(user: User):
    return {"message": f"Created {user.name}"}
```

### Q2: Difference between path and query parameters?
**Answer:**
```python
# Path parameters - part of URL path
@app.get("/users/{user_id}")
def get_user(user_id: int):  # /users/123
    pass

# Query parameters - after ? in URL
@app.get("/users")
def list_users(skip: int = 0, limit: int = 10):  # /users?skip=0&limit=10
    pass
```

### Q3: What is dependency injection in FastAPI?
**Answer:**
Dependency injection is a way to share common logic across routes.

```python
from fastapi import Depends

# Dependency function
def get_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()

# Use in route
@app.get("/items")
def get_items(db: Database = Depends(get_db)):
    return db.get_all_items()
```

---

## Intermediate Level

### Q4: How does FastAPI handle authentication?
**Answer:**
```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"user": user.name}
```

### Q5: Explain middleware in FastAPI
**Answer:**
```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Q6: How to handle background tasks?
**Answer:**
```python
from fastapi import BackgroundTasks

def send_email(email: str, message: str):
    # Long running task
    pass

@app.post("/signup")
async def signup(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email, email, "Welcome!")
    return {"message": "Signup successful"}
```

---

## Advanced Level

### Q7: How to optimize FastAPI performance?
**Answer:**
1. **Use async routes** for I/O-bound operations
2. **Connection pooling** for databases
3. **Caching** with Redis
4. **Response streaming** for large data
5. **Proper pagination**

```python
# Async database operations
async def get_users():
    async with async_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()

# Caching
from fastapi_cache import FastAPICache

@app.get("/expensive")
@cache(expire=60)
async def expensive_operation():
    pass
```

### Q8: Testing strategies for FastAPI?
**Answer:**
```python
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def client():
    return TestClient(app)

def test_create_user(client):
    response = client.post(
        "/users",
        json={"name": "Test", "email": "test@example.com"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

---

# Chapter 35: AWS CDK Interview Questions

### Q1: What is Infrastructure as Code (IaC)?
**Answer:**
IaC is managing infrastructure using code files instead of manual configuration.
- **Benefits**: Version control, reproducibility, automation, consistency
- **Tools**: AWS CDK, Terraform, CloudFormation

### Q2: CDK vs CloudFormation vs Terraform?
**Answer:**
| Feature | CDK | CloudFormation | Terraform |
|---------|-----|----------------|-----------|
| Language | Python, TypeScript, etc. | YAML/JSON | HCL |
| Provider | AWS only | AWS only | Multi-cloud |
| Abstraction | High-level constructs | Low-level | Medium |
| State | CloudFormation | CloudFormation | Terraform state |

### Q3: Explain CDK constructs levels
**Answer:**
```
L1 (Cfn): Direct CloudFormation
   └── CfnBucket

L2 (Standard): With sensible defaults
   └── Bucket

L3 (Patterns): Multiple resources
   └── ApplicationLoadBalancedFargateService
```

### Q4: How to share resources between stacks?
**Answer:**
```python
# Stack A - Export
class DatabaseStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.table = dynamodb.Table(...)

# Stack B - Import
class AppStack(Stack):
    def __init__(self, scope, id, table, **kwargs):
        super().__init__(scope, id, **kwargs)
        table.grant_read_write_data(self.lambda_function)

# app.py
db_stack = DatabaseStack(app, "DB")
app_stack = AppStack(app, "App", table=db_stack.table)
```

### Q5: How to test CDK code?
**Answer:**
```python
from aws_cdk.assertions import Template

def test_resources_created():
    app = cdk.App()
    stack = MyStack(app, "test")
    template = Template.from_stack(stack)
    
    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.11"
    })
    template.resource_count_is("AWS::DynamoDB::Table", 1)
```

---

# Chapter 36: AWS Lambda Interview Questions

### Q1: What is cold start and how to minimize it?
**Answer:**
Cold start occurs when Lambda creates a new container. Minimize by:
- Initialize outside handler
- Use provisioned concurrency
- Keep functions warm
- Minimize package size
- Use Lambda layers

```python
# Initialize outside handler
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')

def handler(event, context):
    # Use pre-initialized resources
    return table.get_item(Key={'id': '123'})
```

### Q2: Lambda concurrency types?
**Answer:**
```
Reserved Concurrency:
- Guarantees AND limits concurrent executions
- Protects downstream resources

Provisioned Concurrency:
- Pre-warms containers
- Eliminates cold starts
- Higher cost
```

### Q3: How does Lambda scale?
**Answer:**
- Scales automatically (up to account limits)
- Default: 1000 concurrent executions
- Burst scaling: Immediate, then linear
- No manual intervention needed

### Q4: Lambda best practices?
**Answer:**
1. **Single responsibility** - One function per task
2. **Initialize outside handler** - Connection reuse
3. **Use environment variables** - Configuration
4. **Minimize package size** - Faster cold starts
5. **Set appropriate timeout** - Don't waste money
6. **Use structured logging** - Debugging
7. **Handle errors gracefully** - Retry logic

---

# Chapter 37: Kubernetes Interview Questions

### Q1: Pod vs Container?
**Answer:**
- **Container**: Single running process (Docker)
- **Pod**: One or more containers sharing network/storage
- Pod is the smallest deployable unit in K8s

### Q2: Deployment vs StatefulSet?
**Answer:**
| Deployment | StatefulSet |
|------------|-------------|
| Stateless apps | Stateful apps |
| Random pod names | Ordered names (pod-0, pod-1) |
| Shared storage | Unique storage per pod |
| Web servers, APIs | Databases, Kafka |

### Q3: How does service discovery work?
**Answer:**
```
1. Service gets stable DNS name
2. Pods register with Service
3. Service load balances to healthy pods

DNS: my-service.namespace.svc.cluster.local
```

### Q4: Explain liveness vs readiness probes
**Answer:**
```yaml
livenessProbe:   # Is container alive? Restart if not
  httpGet:
    path: /health
    port: 8000

readinessProbe:  # Is container ready for traffic?
  httpGet:
    path: /ready
    port: 8000
```

### Q5: Horizontal Pod Autoscaler?
**Answer:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

# Chapter 38: System Design Questions

### Q1: Design a URL Shortener with Lambda
**Architecture:**
```
Client → API Gateway → Lambda → DynamoDB
                           ↓
                     S3 (analytics)
```

**Components:**
- Lambda for create/redirect
- DynamoDB for URL mappings
- CloudFront for caching

### Q2: Design a Scalable Notification System
**Architecture:**
```
API → SQS → Lambda → SNS → Email/SMS/Push
        ↓
    DLQ for failures
```

### Q3: Design Microservices on EKS
**Architecture:**
```
Internet → ALB → Ingress Controller
                      ↓
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    User Service  Order Service  Payment Service
        │             │             │
        └─────────────┴─────────────┘
                      ↓
              Service Mesh (Istio)
```

### Q4: Compare Lambda vs EKS
| Factor | Lambda | EKS |
|--------|--------|-----|
| Cost | Pay per invocation | Pay for cluster |
| Scaling | Automatic | HPA required |
| Cold start | Yes | No |
| Long running | 15 min max | Unlimited |
| Complexity | Low | High |
| Control | Limited | Full |

**Use Lambda:** Short tasks, variable traffic, simple apps
**Use EKS:** Long-running, consistent traffic, complex apps

---

# Behavioral Questions

### Q: Tell me about a challenging project
**Structure:**
1. **Situation**: What was the context?
2. **Task**: What were you responsible for?
3. **Action**: What did you do?
4. **Result**: What was the outcome?

**Example:**
"In my previous role, we needed to migrate a monolithic application to serverless. I led the design of Lambda functions with API Gateway. I implemented proper error handling and monitoring with CloudWatch. The result was 60% cost reduction and 5x better scalability."

### Q: How do you stay updated with technology?
- Follow AWS blogs and announcements
- Participate in communities
- Build personal projects
- Get certifications
- Attend conferences/webinars

---

*Continue to Part 7 for Complete Projects...*
