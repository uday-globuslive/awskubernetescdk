# Part IV: Integration - FastAPI + CDK + Lambda
## Chapters 23-25: Deploying FastAPI as Lambda

---

# Chapter 23: FastAPI on Lambda with Mangum

## 23.1 What is Mangum?

Mangum is an adapter that allows ASGI applications (like FastAPI) to run on AWS Lambda.

```
Normal FastAPI:
Client → Uvicorn Server → FastAPI App

FastAPI on Lambda:
Client → API Gateway → Lambda → Mangum → FastAPI App

Mangum converts:
- API Gateway events → ASGI requests
- ASGI responses → API Gateway responses
```

### Why Use Mangum?

```
✅ Benefits:
- Write normal FastAPI code
- Use all FastAPI features (Pydantic, dependency injection, etc.)
- Zero server management
- Auto-scaling
- Pay per request

❌ Limitations:
- Cold starts affect latency
- 29-second timeout (API Gateway limit)
- No WebSockets (use API Gateway WebSocket instead)
- No background tasks after response
```

---

## 23.2 Setting Up Your Project

### Project Structure

```
my-fastapi-lambda/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── items.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── services/
│       ├── __init__.py
│       └── database.py
├── lambda_handler.py      # Lambda entry point
├── requirements.txt
├── cdk/                   # CDK infrastructure
│   ├── app.py
│   ├── cdk.json
│   └── stacks/
│       └── api_stack.py
└── tests/
    └── test_api.py
```

### FastAPI Application

```python
# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

# Create FastAPI app
app = FastAPI(
    title="My API",
    description="FastAPI running on Lambda",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Item(BaseModel):
    id: Optional[str] = None
    name: str
    price: float
    description: Optional[str] = None

class ItemResponse(BaseModel):
    items: List[Item]
    count: int

# In-memory storage (for demo - use DynamoDB in production)
items_db = {}

# Routes
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI on Lambda!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": os.getenv("ENVIRONMENT", "unknown")}

@app.get("/items", response_model=ItemResponse)
def list_items():
    items = list(items_db.values())
    return {"items": items, "count": len(items)}

@app.get("/items/{item_id}")
def get_item(item_id: str):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.post("/items", status_code=201)
def create_item(item: Item):
    import uuid
    item_id = str(uuid.uuid4())
    item.id = item_id
    items_db[item_id] = item
    return item

@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
    return {"message": "Item deleted"}
```

### Lambda Handler with Mangum

```python
# lambda_handler.py
from mangum import Mangum
from app.main import app

# Create Mangum handler
# This converts API Gateway events to ASGI and back
handler = Mangum(app, lifespan="off")

# That's it! Mangum handles everything else

# Optional: Custom handler with logging
def handler_with_logging(event, context):
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    logger.info(f"Received event: {event}")
    
    # Create Mangum instance and handle
    mangum_handler = Mangum(app, lifespan="off")
    response = mangum_handler(event, context)
    
    logger.info(f"Response: {response}")
    return response
```

### Requirements

```txt
# requirements.txt
fastapi==0.109.0
mangum==0.17.0
pydantic==2.5.0
python-multipart==0.0.6
```

---

## 23.3 Using DynamoDB with FastAPI

### Database Service

```python
# app/services/database.py
import boto3
import os
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError

class DynamoDBService:
    def __init__(self):
        # Initialize outside of request handling for connection reuse
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.environ['TABLE_NAME'])
    
    def get_item(self, pk: str) -> Optional[Dict[str, Any]]:
        """Get a single item by primary key."""
        try:
            response = self.table.get_item(Key={'id': pk})
            return response.get('Item')
        except ClientError as e:
            raise Exception(f"Error getting item: {e}")
    
    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an item."""
        self.table.put_item(Item=item)
        return item
    
    def delete_item(self, pk: str) -> bool:
        """Delete an item."""
        self.table.delete_item(Key={'id': pk})
        return True
    
    def scan_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scan all items (use with caution)."""
        response = self.table.scan(Limit=limit)
        return response.get('Items', [])

# Create singleton instance
db = DynamoDBService()

# FastAPI dependency
def get_db():
    return db
```

### Updated FastAPI with DynamoDB

```python
# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from app.services.database import DynamoDBService, get_db
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI()

class ItemCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

class Item(ItemCreate):
    id: str

@app.post("/items", response_model=Item, status_code=201)
def create_item(item: ItemCreate, db: DynamoDBService = Depends(get_db)):
    item_id = str(uuid.uuid4())
    item_dict = {
        "id": item_id,
        **item.model_dump()
    }
    db.put_item(item_dict)
    return Item(**item_dict)

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str, db: DynamoDBService = Depends(get_db)):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item(**item)

@app.delete("/items/{item_id}")
def delete_item(item_id: str, db: DynamoDBService = Depends(get_db)):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete_item(item_id)
    return {"message": "Item deleted"}
```

---

# Chapter 24: CDK for FastAPI Lambda

## 24.1 Complete CDK Stack

```python
# cdk/stacks/api_stack.py
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_iam as iam,
)
from constructs import Construct

class FastAPILambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # DynamoDB Table
        table = dynamodb.Table(
            self, "ItemsTable",
            table_name="items",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev only!
        )
        
        # Lambda Function
        api_handler = _lambda.Function(
            self, "FastAPIHandler",
            function_name="fastapi-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset(
                "../",  # Path to your app code
                exclude=[
                    "cdk",
                    "*.pyc",
                    "__pycache__",
                    ".git",
                    ".venv",
                    "tests"
                ]
            ),
            memory_size=512,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": table.table_name,
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            tracing=_lambda.Tracing.ACTIVE,
        )
        
        # Grant DynamoDB permissions
        table.grant_read_write_data(api_handler)
        
        # API Gateway
        api = apigw.RestApi(
            self, "FastAPI",
            rest_api_name="FastAPI Service",
            description="FastAPI running on Lambda",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                throttling_rate_limit=1000,
                throttling_burst_limit=500,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"],
            )
        )
        
        # Proxy all requests to Lambda
        api.root.add_proxy(
            default_integration=apigw.LambdaIntegration(
                api_handler,
                proxy=True
            ),
            any_method=True
        )
        
        # Also handle root path
        api.root.add_method(
            "ANY",
            apigw.LambdaIntegration(api_handler)
        )
        
        # Outputs
        CfnOutput(
            self, "ApiUrl",
            value=api.url,
            description="API Gateway URL"
        )
        
        CfnOutput(
            self, "TableName",
            value=table.table_name,
            description="DynamoDB Table Name"
        )
```

### CDK App Entry Point

```python
# cdk/app.py
#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.api_stack import FastAPILambdaStack

app = cdk.App()

FastAPILambdaStack(
    app, "FastAPILambdaStack",
    env=cdk.Environment(
        account="123456789012",  # Your AWS account
        region="us-east-1"
    )
)

app.synth()
```

### CDK Configuration

```json
// cdk/cdk.json
{
  "app": "python app.py",
  "context": {
    "@aws-cdk/aws-apigateway:usagePlanKeyOrderInsensitiveId": true,
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true
  }
}
```

---

## 24.2 Deploying with Lambda Layers

For faster deployments and smaller code packages:

```python
# cdk/stacks/api_stack.py

class FastAPILambdaStackWithLayers(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Dependencies layer
        dependencies_layer = _lambda.LayerVersion(
            self, "DependenciesLayer",
            code=_lambda.Code.from_asset(
                "../layers/dependencies",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output/python"
                    ]
                )
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="FastAPI and dependencies"
        )
        
        # Lambda function (just your code, small!)
        api_handler = _lambda.Function(
            self, "FastAPIHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset(
                "../app"  # Just your application code
            ),
            layers=[dependencies_layer],  # Add the layer
            memory_size=512,
            timeout=Duration.seconds(30),
        )
```

---

## 24.3 Multi-Environment Setup

```python
# cdk/stacks/api_stack.py
from dataclasses import dataclass

@dataclass
class EnvironmentConfig:
    name: str
    memory_size: int
    timeout_seconds: int
    log_retention_days: int
    
ENVIRONMENTS = {
    "dev": EnvironmentConfig(
        name="dev",
        memory_size=256,
        timeout_seconds=30,
        log_retention_days=7
    ),
    "prod": EnvironmentConfig(
        name="prod",
        memory_size=1024,
        timeout_seconds=30,
        log_retention_days=30
    )
}

class FastAPIStack(Stack):
    def __init__(self, scope: Construct, id: str, env_name: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        config = ENVIRONMENTS[env_name]
        
        # Use config values
        api_handler = _lambda.Function(
            self, "FastAPIHandler",
            memory_size=config.memory_size,
            timeout=Duration.seconds(config.timeout_seconds),
            environment={
                "ENVIRONMENT": config.name
            }
        )
```

---

# Chapter 25: Architecture Patterns

## 25.1 Simple CRUD API Pattern

```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│   Client    │────▶│  API Gateway  │────▶│    Lambda    │
└─────────────┘     └───────────────┘     │   (FastAPI)  │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   DynamoDB   │
                                          └──────────────┘
```

## 25.2 Async Processing Pattern

```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│   Client    │────▶│  API Gateway  │────▶│  API Lambda  │
└─────────────┘     └───────────────┘     │  (FastAPI)   │
                                          └──────┬───────┘
                                                 │
                           Quick response ◀──────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │     SQS      │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   Worker     │
                                          │   Lambda     │
                                          └──────────────┘
```

## 25.3 API with Authentication

```python
# app/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            os.environ['JWT_SECRET'],
            algorithms=["HS256"]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Use in routes
@app.get("/protected")
def protected_route(user: dict = Depends(verify_token)):
    return {"message": f"Hello, {user['sub']}"}
```

## 25.4 File Upload Pattern

```python
# For file uploads to S3
from fastapi import UploadFile, File
import boto3
import uuid

s3 = boto3.client('s3')
BUCKET = os.environ['UPLOAD_BUCKET']

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Generate unique filename
    file_id = str(uuid.uuid4())
    key = f"uploads/{file_id}/{file.filename}"
    
    # Upload to S3
    content = await file.read()
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=content,
        ContentType=file.content_type
    )
    
    # Return presigned URL for download
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': key},
        ExpiresIn=3600
    )
    
    return {"file_id": file_id, "download_url": url}
```

---

## 25.5 Complete Production-Ready Template

```python
# A complete template combining everything

# app/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel
import boto3
import os
import uuid
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients (outside handler for reuse)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'items'))

# FastAPI app
app = FastAPI(
    title="Production API",
    version="1.0.0",
    docs_url="/docs" if os.environ.get('ENVIRONMENT') != 'prod' else None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('ALLOWED_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ItemCreate(BaseModel):
    name: str
    price: float

class Item(ItemCreate):
    id: str

# Health check
@app.get("/health")
def health():
    return {"status": "healthy"}

# CRUD
@app.post("/items", response_model=Item, status_code=201)
def create_item(item: ItemCreate):
    item_id = str(uuid.uuid4())
    item_data = {"id": item_id, **item.model_dump()}
    table.put_item(Item=item_data)
    logger.info(f"Created item {item_id}")
    return item_data

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str):
    response = table.get_item(Key={"id": item_id})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    table.delete_item(Key={"id": item_id})
    return {"message": "Deleted"}

# Lambda handler
handler = Mangum(app, lifespan="off")
```

---

*Continue to Part 5 for Kubernetes Chapters...*
