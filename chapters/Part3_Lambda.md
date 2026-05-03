# Part III: AWS Lambda
## Complete Detailed Guide for Beginners

---

# Chapter 17: Lambda Fundamentals

## 17.1 What is Serverless?

### Traditional Servers vs Serverless

```
TRADITIONAL (You manage everything):
┌─────────────────────────────────────────────────┐
│  You handle:                                    │
│  ✗ Buying/renting servers                       │
│  ✗ Installing operating systems                 │
│  ✗ Security patches                             │
│  ✗ Scaling up/down                              │
│  ✗ Load balancing                               │
│  ✗ Paying 24/7 even when idle                   │
└─────────────────────────────────────────────────┘

SERVERLESS (AWS handles everything):
┌─────────────────────────────────────────────────┐
│  You handle:                                    │
│  ✓ Just your code!                              │
│                                                 │
│  AWS handles:                                   │
│  • Server management                            │
│  • Scaling                                      │
│  • High availability                            │
│  • Pay only when code runs                      │
└─────────────────────────────────────────────────┘
```

### Why "Serverless"?

There ARE servers - you just don't see or manage them. AWS handles everything behind the scenes.

**Analogy:** 
- Traditional: You buy a car, maintain it, pay insurance
- Serverless: You use Uber - just pay for rides, no car ownership

### Benefits of Serverless

```
┌─────────────────────────────────────────────┐
│           SERVERLESS BENEFITS               │
├─────────────────────────────────────────────┤
│                                             │
│  💰 Cost: Pay only when code runs          │
│     - No idle server costs                  │
│     - Scale to zero                         │
│                                             │
│  📈 Scaling: Automatic                      │
│     - Handles 1 to 1,000,000 requests      │
│     - No capacity planning                  │
│                                             │
│  🔧 Operations: Zero                        │
│     - No patching                           │
│     - No maintenance                        │
│                                             │
│  ⚡ Speed: Fast deployment                  │
│     - Deploy in seconds                     │
│     - Focus on code                         │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 17.2 Lambda Execution Model

### How Lambda Works

```
Request comes in
        │
        ▼
┌───────────────────┐
│  Is there a warm  │──No──→ Create new container
│    container?     │        (COLD START)
└───────────────────┘            │
        │                        │
       Yes                       │
        │                        ▼
        ▼               ┌────────────────┐
┌───────────────────┐   │ Download code  │
│  Use existing     │   │ Start runtime  │
│    container      │   │ Load libraries │
└───────────────────┘   └────────────────┘
        │                        │
        │◄───────────────────────┘
        ▼
┌───────────────────┐
│  Execute your     │
│    handler()      │
└───────────────────┘
        │
        ▼
    Response sent
        │
        ▼
Container stays warm for ~15 minutes
(ready for next request)
```

### Lambda Lifecycle

```
1. INIT (Cold Start)
   - Download your code
   - Start the runtime (Python, Node.js, etc.)
   - Run code OUTSIDE the handler
   
2. INVOKE
   - Execute your handler function
   - Process the event
   - Return response
   
3. SHUTDOWN (after idle timeout)
   - Container destroyed
   - Next request = new cold start
```

---

## 17.3 Cold Starts and Warm Starts

### What's the Difference?

```
COLD START (First request or after idle):
┌─────────────────────────────────────────────┐
│                                             │
│  Download code     → 50-200ms               │
│  Start runtime     → 100-500ms              │
│  Initialize code   → varies                 │
│  Run handler       → your code time         │
│                                             │
│  TOTAL: 200ms - 5 seconds                   │
│                                             │
└─────────────────────────────────────────────┘

WARM START (Container already running):
┌─────────────────────────────────────────────┐
│                                             │
│  Run handler       → your code time         │
│                                             │
│  TOTAL: Few milliseconds                    │
│                                             │
└─────────────────────────────────────────────┘
```

### Factors Affecting Cold Start

| Factor | Impact |
|--------|--------|
| Code size | Larger = slower |
| Runtime | Java slowest, Python/Node fast |
| VPC | Adds 1-5 seconds |
| Memory | More memory = faster |
| Dependencies | More = slower |

### Minimizing Cold Starts

```python
# ❌ BAD - Initialize inside handler (runs every time)
def handler(event, context):
    import boto3  # Imported on every call!
    dynamodb = boto3.resource('dynamodb')  # Created on every call!
    table = dynamodb.Table('users')
    return table.get_item(Key={'id': '123'})

# ✅ GOOD - Initialize outside handler (runs once per container)
import boto3  # Imported once

dynamodb = boto3.resource('dynamodb')  # Created once
table = dynamodb.Table('users')  # Created once

def handler(event, context):
    # Handler just uses the pre-initialized resources
    return table.get_item(Key={'id': '123'})
```

---

## 17.4 Lambda Pricing

### How You're Charged

```
Lambda Cost = Number of Requests × Duration × Memory

┌─────────────────────────────────────────────┐
│              PRICING COMPONENTS             │
├─────────────────────────────────────────────┤
│                                             │
│  1. REQUESTS                                │
│     First 1 million: FREE                   │
│     After: $0.20 per 1 million requests     │
│                                             │
│  2. DURATION (GB-seconds)                   │
│     First 400,000 GB-seconds: FREE          │
│     After: $0.0000166667 per GB-second      │
│                                             │
│  GB-second = (Memory in GB) × (Duration)    │
│                                             │
└─────────────────────────────────────────────┘
```

### Cost Example

```
Your Lambda:
- Memory: 256 MB (0.25 GB)
- Duration: 200ms per request
- Requests: 10 million per month

Calculation:
1. Requests: (10M - 1M free) × $0.20/M = $1.80

2. Duration:
   GB-seconds = 10M × 0.25 GB × 0.2 sec = 500,000 GB-sec
   Billable = 500,000 - 400,000 free = 100,000 GB-sec
   Cost = 100,000 × $0.0000166667 = $1.67

TOTAL: $1.80 + $1.67 = $3.47/month

Compare to EC2:
- t3.small running 24/7 ≈ $15/month
- Plus you manage it yourself!
```

---

## 17.5 Invocation Types

### Three Ways to Invoke Lambda

```
1. SYNCHRONOUS (Request-Response)
┌─────────────────────────────────────────────┐
│  Client → Lambda → Waits → Response         │
│                                             │
│  Use when: You need the result immediately  │
│  Examples: API Gateway, Direct invoke       │
└─────────────────────────────────────────────┘

2. ASYNCHRONOUS (Fire and Forget)
┌─────────────────────────────────────────────┐
│  Client → Lambda → Immediate "accepted"     │
│                 ↓                           │
│           (Lambda runs later)               │
│                                             │
│  Use when: You don't need immediate result  │
│  Examples: S3 events, SNS, EventBridge      │
└─────────────────────────────────────────────┘

3. EVENT SOURCE MAPPING (Polling)
┌─────────────────────────────────────────────┐
│  SQS/Kinesis → Lambda polls → Processes     │
│                                             │
│  Use when: Processing queue messages        │
│  Examples: SQS, Kinesis, DynamoDB Streams   │
└─────────────────────────────────────────────┘
```

---

## 17.6 Handler Function Structure

### Basic Handler

```python
def handler(event, context):
    """
    Lambda handler function.
    
    Parameters:
    - event: Input data (JSON automatically parsed to dict)
    - context: Runtime information
    
    Returns:
    - For API Gateway: dict with statusCode, body
    - For other triggers: any serializable value
    """
    
    # Your logic here
    name = event.get('name', 'World')
    
    # Return response
    return {
        'statusCode': 200,
        'body': f'Hello, {name}!'
    }
```

### Understanding the Event

```python
# API Gateway event
event = {
    "httpMethod": "GET",
    "path": "/users",
    "queryStringParameters": {"limit": "10"},
    "pathParameters": {"id": "123"},
    "headers": {"Authorization": "Bearer xxx"},
    "body": '{"name": "Alice"}'  # JSON string
}

# S3 event
event = {
    "Records": [{
        "s3": {
            "bucket": {"name": "my-bucket"},
            "object": {"key": "uploads/file.jpg"}
        }
    }]
}

# SQS event
event = {
    "Records": [{
        "body": '{"order_id": "123"}',
        "messageId": "xxx"
    }]
}
```

### Understanding the Context

```python
def handler(event, context):
    # Useful context properties
    print(f"Function name: {context.function_name}")
    print(f"Memory limit: {context.memory_limit_in_mb} MB")
    print(f"Time remaining: {context.get_remaining_time_in_millis()} ms")
    print(f"Request ID: {context.aws_request_id}")
    
    return {"status": "ok"}
```

---

# Chapter 18: Lambda Configuration

## 18.1 Memory and Timeout Settings

### Memory

```
Memory range: 128 MB to 10,240 MB (10 GB)

More memory = More CPU = Faster execution = Higher cost

┌─────────────────────────────────────────────┐
│              MEMORY SELECTION               │
├─────────────────────────────────────────────┤
│  128 MB  - Simple functions, low traffic    │
│  256 MB  - Small API handlers               │
│  512 MB  - Standard workloads               │
│  1024 MB - Data processing                  │
│  2048 MB - ML inference, heavy compute      │
│  3008 MB - 2 vCPUs (full CPU)               │
│  10240 MB - Maximum                         │
└─────────────────────────────────────────────┘
```

### Timeout

```
Range: 1 second to 15 minutes

Recommendations:
- API Gateway trigger: 30 seconds max (API GW times out at 29s)
- Async processing: Up to 15 minutes
- Simple operations: 10-30 seconds
```

### Finding Optimal Memory

```python
# Use AWS Lambda Power Tuning tool
# Or check CloudWatch metrics after deployment

# Look for:
# - Duration decreases as memory increases
# - Find the sweet spot where cost is lowest
```

---

## 18.2 Environment Variables

### Setting Environment Variables

```python
# In CDK
lambda_fn = _lambda.Function(
    self, "MyFunction",
    environment={
        "DATABASE_URL": "postgresql://...",
        "API_KEY": "xxx",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO"
    }
)

# Accessing in Lambda
import os

def handler(event, context):
    database_url = os.environ['DATABASE_URL']
    api_key = os.environ['API_KEY']
    env = os.environ.get('ENVIRONMENT', 'development')
    
    return {"status": "ok"}
```

### Best Practices

```
✅ DO:
- Use for configuration that changes between environments
- Reference secrets ARN (not actual values)
- Use descriptive names

❌ DON'T:
- Store actual secrets (use Secrets Manager instead)
- Store large data
- Exceed 4 KB total size
```

---

## 18.3 VPC Configuration

### When to Use VPC

```
Lambda in VPC = Lambda can access private resources

Use VPC when:
✓ Accessing RDS database
✓ Accessing ElastiCache
✓ Accessing private APIs
✓ Security requirements

Don't use VPC when:
✗ Only using public AWS services
✗ Only using DynamoDB, S3, etc.
✗ You want fastest cold starts
```

### VPC Lambda Architecture

```
┌─────────────────────────────────────────────────────────┐
│                         VPC                              │
│  ┌─────────────────────┐  ┌─────────────────────┐       │
│  │   Private Subnet    │  │   Private Subnet    │       │
│  │   ┌───────────┐     │  │   ┌───────────┐     │       │
│  │   │  Lambda   │     │  │   │    RDS    │     │       │
│  │   └───────────┘     │  │   └───────────┘     │       │
│  │         │           │  │                     │       │
│  │         ▼           │  │                     │       │
│  │   ┌───────────┐     │  │                     │       │
│  │   │    ENI    │─────┼──┼──► Private access   │       │
│  │   └───────────┘     │  │                     │       │
│  └─────────────────────┘  └─────────────────────┘       │
│                                                          │
│  For internet access, add NAT Gateway                    │
└─────────────────────────────────────────────────────────┘
```

---

## 18.4 Layers

### What are Lambda Layers?

Layers contain shared code and dependencies that multiple functions can use.

```
Without Layers:
┌───────────────────┐  ┌───────────────────┐
│ Function A        │  │ Function B        │
│ ┌───────────────┐ │  │ ┌───────────────┐ │
│ │ boto3 (10MB)  │ │  │ │ boto3 (10MB)  │ │
│ │ pandas (50MB) │ │  │ │ pandas (50MB) │ │
│ │ numpy (30MB)  │ │  │ │ numpy (30MB)  │ │
│ │ your code     │ │  │ │ your code     │ │
│ └───────────────┘ │  │ └───────────────┘ │
└───────────────────┘  └───────────────────┘
Total: 180 MB (duplicated!)

With Layers:
┌─────────────────────────────────────────────┐
│              Shared Layer                    │
│   boto3 + pandas + numpy (90 MB once)       │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────────┐  ┌───────────────────┐
│ Function A        │  │ Function B        │
│ │ your code (1KB) │  │ │ your code (1KB) │
└───────────────────┘  └───────────────────┘
Total: 92 MB (shared!)
```

### Creating and Using Layers

```python
# Create layer for dependencies
# 1. Create folder structure:
# layers/
# └── python/           # MUST be named 'python'
#     └── lib/
#         └── python3.9/
#             └── site-packages/
#                 └── (your packages here)

# 2. Install packages to layer
# pip install pandas -t layers/python/

# 3. Create layer in CDK
layer = _lambda.LayerVersion(
    self, "DependenciesLayer",
    code=_lambda.Code.from_asset("./layers"),
    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
    description="Python dependencies"
)

# 4. Use layer in function
function = _lambda.Function(
    self, "MyFunction",
    runtime=_lambda.Runtime.PYTHON_3_9,
    code=_lambda.Code.from_asset("./lambda"),
    handler="main.handler",
    layers=[layer]  # Attach layer
)
```

---

## 18.5 Provisioned Concurrency

### The Cold Start Problem

```
Normal Lambda:
Request 1 → Cold Start (500ms) + Execution
Request 2 → Warm (fast)
Request 3 → Warm (fast)
... 15 min idle ...
Request 4 → Cold Start (500ms) + Execution
```

### Provisioned Concurrency Solution

```
With Provisioned Concurrency:
Always keep N containers warm

Request 1 → Warm (fast) ← Pre-warmed
Request 2 → Warm (fast) ← Pre-warmed
Request 3 → Warm (fast) ← Pre-warmed
... any idle time ...
Request 4 → Warm (fast) ← Still pre-warmed
```

### Configuration

```python
# CDK
fn_with_provisioned = _lambda.Function(
    self, "MyFunction",
    runtime=_lambda.Runtime.PYTHON_3_9,
    handler="main.handler",
    code=_lambda.Code.from_asset("./lambda")
)

# Add provisioned concurrency
version = fn_with_provisioned.current_version
version.add_alias(
    "live",
    provisioned_concurrent_executions=10  # Keep 10 warm
)
```

### Cost Consideration

```
Provisioned Concurrency:
- You pay for the pre-warmed containers
- Even when not in use
- Good for consistent, predictable traffic

Use when:
- Low latency is critical
- You have consistent traffic patterns
- Cold starts are unacceptable
```

---

## 18.6 Reserved Concurrency

### What is Reserved Concurrency?

Limits how many concurrent executions your function can have.

```
Account Limit: 1000 concurrent executions (default)

Without reserved:
Function A could use all 1000, starving others

With reserved:
Function A: Reserved 100 (guaranteed, max)
Function B: Reserved 200 (guaranteed, max)
Other functions: Share remaining 700
```

### Use Cases

```
Reserve concurrency when:
1. Protect downstream resources (DB connections)
2. Prevent one function from hogging all capacity
3. Limit impact of runaway functions

Example:
- Database allows 100 connections
- Set Lambda reserved concurrency to 100
- Prevents too many DB connections
```

---

## 18.7 Function URLs

### What are Function URLs?

Direct HTTP endpoints for Lambda functions - no API Gateway needed!

```
Traditional:
Client → API Gateway → Lambda
(More features, more cost, more complexity)

Function URL:
Client → Lambda (direct!)
(Simple, free, limited features)
```

### Creating Function URLs

```python
# CDK
function = _lambda.Function(
    self, "MyFunction",
    runtime=_lambda.Runtime.PYTHON_3_9,
    handler="main.handler",
    code=_lambda.Code.from_asset("./lambda")
)

# Add function URL
function_url = function.add_function_url(
    auth_type=_lambda.FunctionUrlAuthType.NONE,  # Public
    cors=_lambda.FunctionUrlCorsOptions(
        allowed_origins=["*"],
        allowed_methods=[_lambda.HttpMethod.GET, _lambda.HttpMethod.POST]
    )
)

# URL format: https://<url-id>.lambda-url.<region>.on.aws/
```

---

# Chapter 19: Lambda Triggers

## 19.1 API Gateway Integration

```python
# CDK - REST API
from aws_cdk import aws_apigateway as apigw

api = apigw.RestApi(self, "MyApi")

# Add Lambda integration
items = api.root.add_resource("items")
items.add_method("GET", apigw.LambdaIntegration(get_handler))
items.add_method("POST", apigw.LambdaIntegration(create_handler))

# Lambda handler for API Gateway
def handler(event, context):
    http_method = event['httpMethod']
    path = event['path']
    query_params = event.get('queryStringParameters') or {}
    body = event.get('body')
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'Success'})
    }
```

## 19.2 S3 Event Triggers

```python
# CDK
from aws_cdk import aws_s3_notifications as s3n

bucket.add_event_notification(
    s3.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(processor_lambda),
    s3.NotificationKeyFilter(prefix="uploads/", suffix=".jpg")
)

# Lambda handler
def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Process the file
        print(f"Processing {key} from {bucket}")
```

## 19.3 SQS Triggers

```python
# CDK
from aws_cdk import aws_lambda_event_sources as sources

processor.add_event_source(
    sources.SqsEventSource(
        queue,
        batch_size=10,
        max_batching_window=Duration.seconds(30)
    )
)

# Lambda handler
def handler(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        message_id = record['messageId']
        
        # Process message
        process_order(body)
        
    # Return nothing = success (messages deleted from queue)
```

---

# Chapter 20: Lambda with Python

## 20.1 Best Practices

```python
# Initialize outside handler (for connection reuse)
import boto3
import os

# These run once per container (cold start only)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    """
    Handler runs on every invocation.
    """
    # Use pre-initialized resources
    response = table.get_item(Key={'id': event['id']})
    return response.get('Item')
```

## 20.2 Powertools for AWS Lambda

AWS Lambda Powertools provides utilities for common patterns:

```python
# Install: pip install aws-lambda-powertools

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize
logger = Logger()
tracer = Tracer()
metrics = Metrics()
app = APIGatewayRestResolver()

@app.get("/users/<user_id>")
@tracer.capture_method
def get_user(user_id: str):
    logger.info(f"Getting user {user_id}")
    metrics.add_metric(name="UserRequests", unit="Count", value=1)
    
    user = table.get_item(Key={'id': user_id})
    return user.get('Item', {})

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
```

---

# Chapter 21-22: Performance & Security

## Performance Optimization

```python
# 1. Connection pooling
from urllib3 import HTTPConnectionPool
pool = HTTPConnectionPool('api.example.com', maxsize=10)

def handler(event, context):
    response = pool.request('GET', '/data')
    return response.data

# 2. Lazy loading
_heavy_model = None

def get_model():
    global _heavy_model
    if _heavy_model is None:
        _heavy_model = load_ml_model()  # Only load when needed
    return _heavy_model

def handler(event, context):
    model = get_model()  # Reused across invocations
    return model.predict(event['data'])

# 3. Minimize package size
# Use Lambda layers for large dependencies
# Only include necessary files
```

## Security Best Practices

```python
# 1. Least privilege IAM
# Only grant permissions the function needs

# 2. Input validation
from pydantic import BaseModel, ValidationError

class UserInput(BaseModel):
    name: str
    email: str

def handler(event, context):
    try:
        user = UserInput(**event)
    except ValidationError as e:
        return {'statusCode': 400, 'body': str(e)}

# 3. Use Secrets Manager for secrets
import boto3

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='my-secret')
    return response['SecretString']

# 4. Never log sensitive data
logger.info(f"Processing user {user_id}")  # OK
logger.info(f"Password: {password}")  # NEVER!
```

---

*Continue to Part 4 for Kubernetes Chapters...*
