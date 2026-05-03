# Part VII: Complete Projects
## Production-Ready Implementations

---

# Project 1: URL Shortener Service

## Architecture
```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│   Client    │────▶│  API Gateway  │────▶│   Lambda     │
└─────────────┘     └───────────────┘     │  (FastAPI)   │
                                          └──────┬───────┘
                                                 │
                    ┌────────────────────────────┼────────┐
                    ▼                            ▼        │
              ┌──────────┐                ┌──────────┐    │
              │ DynamoDB │                │ CloudFront│◀──┘
              │ (URLs)   │                │ (Caching) │
              └──────────┘                └──────────┘
```

## Implementation

### FastAPI Application
```python
# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
import boto3
import hashlib
import os

app = FastAPI(title="URL Shortener")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
BASE_URL = os.environ.get('BASE_URL', 'https://short.url/')

class URLCreate(BaseModel):
    url: HttpUrl
    custom_code: str = None

class URLResponse(BaseModel):
    short_url: str
    original_url: str

def generate_code(url: str) -> str:
    """Generate short code from URL hash."""
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest()[:7]

@app.post("/shorten", response_model=URLResponse)
def create_short_url(data: URLCreate):
    code = data.custom_code or generate_code(str(data.url))
    
    # Check if custom code exists
    if data.custom_code:
        existing = table.get_item(Key={'code': code}).get('Item')
        if existing:
            raise HTTPException(400, "Code already exists")
    
    # Save to DynamoDB
    table.put_item(Item={
        'code': code,
        'url': str(data.url),
        'created_at': str(datetime.now())
    })
    
    return URLResponse(
        short_url=f"{BASE_URL}{code}",
        original_url=str(data.url)
    )

@app.get("/{code}")
def redirect(code: str):
    item = table.get_item(Key={'code': code}).get('Item')
    if not item:
        raise HTTPException(404, "URL not found")
    
    # Track click (async in production)
    return RedirectResponse(url=item['url'])
```

### CDK Stack
```python
# cdk/stacks/url_shortener.py
from aws_cdk import (
    Stack, Duration, CfnOutput, RemovalPolicy,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
)

class URLShortenerStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # DynamoDB
        table = dynamodb.Table(
            self, "URLs",
            partition_key=dynamodb.Attribute(
                name="code", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Lambda
        handler = _lambda.Function(
            self, "Handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset("../app"),
            environment={
                "TABLE_NAME": table.table_name,
                "BASE_URL": "https://your-domain.com/"
            }
        )
        
        table.grant_read_write_data(handler)
        
        # API Gateway
        api = apigw.LambdaRestApi(self, "API", handler=handler)
        
        CfnOutput(self, "ApiUrl", value=api.url)
```

---

# Project 2: Real-time Chat Application

## Architecture
```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│   Client    │────▶│  WebSocket    │────▶│   Lambda     │
│  (React)    │     │  API Gateway  │     │  (Connect/   │
└─────────────┘     └───────────────┘     │  Message)    │
                                          └──────┬───────┘
                                                 │
                              ┌──────────────────┼──────────────┐
                              ▼                  ▼              ▼
                        ┌──────────┐      ┌──────────┐   ┌──────────┐
                        │ DynamoDB │      │ DynamoDB │   │    SNS   │
                        │(Connections)│   │(Messages)│   │(Fanout)  │
                        └──────────┘      └──────────┘   └──────────┘
```

## Lambda Handlers
```python
# lambda/connect.py
import boto3
import os

dynamodb = boto3.resource('dynamodb')
connections = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    connections.put_item(Item={
        'connectionId': connection_id,
        'timestamp': str(datetime.now())
    })
    
    return {'statusCode': 200}

# lambda/disconnect.py
def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    connections.delete_item(Key={'connectionId': connection_id})
    return {'statusCode': 200}

# lambda/message.py
import boto3
import json

def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    
    body = json.loads(event['body'])
    message = body.get('message', '')
    
    # Get all connections
    response = connections.scan()
    
    # Send message to all
    apigw = boto3.client('apigatewaymanagementapi',
        endpoint_url=f"https://{domain}/{stage}")
    
    for item in response['Items']:
        try:
            apigw.post_to_connection(
                ConnectionId=item['connectionId'],
                Data=json.dumps({'message': message}).encode()
            )
        except:
            # Remove stale connection
            connections.delete_item(Key={'connectionId': item['connectionId']})
    
    return {'statusCode': 200}
```

---

# Project 3: E-commerce Backend API

## Architecture
```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│   Frontend  │────▶│  API Gateway  │────▶│   Lambda     │
└─────────────┘     └───────────────┘     │  (FastAPI)   │
                                          └──────┬───────┘
                    ┌─────────────────────────────┼────────────────┐
                    ▼                             ▼                ▼
              ┌──────────┐                  ┌──────────┐    ┌──────────┐
              │ DynamoDB │                  │    S3    │    │   SQS    │
              │(Products,│                  │ (Images) │    │ (Orders) │
              │ Orders)  │                  └──────────┘    └────┬─────┘
              └──────────┘                                       ▼
                                                          ┌──────────┐
                                                          │  Worker  │
                                                          │  Lambda  │
                                                          └──────────┘
```

## FastAPI Implementation
```python
# app/main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import boto3
import uuid
import os

app = FastAPI(title="E-commerce API")

# Initialize services
dynamodb = boto3.resource('dynamodb')
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])
orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])
sqs = boto3.client('sqs')
order_queue_url = os.environ['ORDER_QUEUE_URL']

# Models
class Product(BaseModel):
    id: Optional[str] = None
    name: str
    price: float
    description: str
    stock: int

class OrderItem(BaseModel):
    product_id: str
    quantity: int

class Order(BaseModel):
    id: Optional[str] = None
    items: List[OrderItem]
    total: Optional[float] = None
    status: str = "pending"

# Products
@app.get("/products", response_model=List[Product])
def list_products():
    response = products_table.scan()
    return response.get('Items', [])

@app.get("/products/{product_id}")
def get_product(product_id: str):
    response = products_table.get_item(Key={'id': product_id})
    item = response.get('Item')
    if not item:
        raise HTTPException(404, "Product not found")
    return item

@app.post("/products", status_code=201)
def create_product(product: Product):
    product.id = str(uuid.uuid4())
    products_table.put_item(Item=product.dict())
    return product

# Orders
@app.post("/orders", status_code=201)
def create_order(order: Order):
    order.id = str(uuid.uuid4())
    
    # Calculate total
    total = 0
    for item in order.items:
        product = products_table.get_item(Key={'id': item.product_id}).get('Item')
        if not product:
            raise HTTPException(400, f"Product {item.product_id} not found")
        if product['stock'] < item.quantity:
            raise HTTPException(400, f"Insufficient stock for {product['name']}")
        total += product['price'] * item.quantity
    
    order.total = total
    
    # Save order
    orders_table.put_item(Item={
        'id': order.id,
        'items': [i.dict() for i in order.items],
        'total': total,
        'status': 'pending'
    })
    
    # Send to queue for processing
    sqs.send_message(
        QueueUrl=order_queue_url,
        MessageBody=json.dumps({'order_id': order.id})
    )
    
    return order

@app.get("/orders/{order_id}")
def get_order(order_id: str):
    response = orders_table.get_item(Key={'id': order_id})
    item = response.get('Item')
    if not item:
        raise HTTPException(404, "Order not found")
    return item
```

---

# Project 4: Image Processing Pipeline

## Architecture
```
Upload → S3 → Lambda → Process → S3 (Processed)
          │                         │
          └── SNS Notification ─────┘
```

## Implementation
```python
# lambda/image_processor.py
from PIL import Image
import boto3
import os
from io import BytesIO

s3 = boto3.client('s3')
sns = boto3.client('sns')

DEST_BUCKET = os.environ['DEST_BUCKET']
SNS_TOPIC = os.environ['SNS_TOPIC']

def handler(event, context):
    for record in event['Records']:
        source_bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Download image
        response = s3.get_object(Bucket=source_bucket, Key=key)
        image_content = response['Body'].read()
        
        # Process image (resize, thumbnail)
        image = Image.open(BytesIO(image_content))
        
        # Create thumbnail
        thumbnail = image.copy()
        thumbnail.thumbnail((200, 200))
        
        # Save thumbnail
        thumb_buffer = BytesIO()
        thumbnail.save(thumb_buffer, format='JPEG')
        thumb_buffer.seek(0)
        
        thumb_key = f"thumbnails/{key}"
        s3.put_object(
            Bucket=DEST_BUCKET,
            Key=thumb_key,
            Body=thumb_buffer,
            ContentType='image/jpeg'
        )
        
        # Notify
        sns.publish(
            TopicArn=SNS_TOPIC,
            Message=f"Processed: {key}",
            Subject="Image Processing Complete"
        )
    
    return {'statusCode': 200}
```

---

# Project 5: FastAPI on Kubernetes

## Complete K8s Deployment
```yaml
# k8s/full-deployment.yaml

# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: fastapi-app

---
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: fastapi-app
data:
  ENVIRONMENT: production
  LOG_LEVEL: INFO

---
# Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: fastapi-app
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@host:5432/db"

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
  namespace: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
        - name: fastapi
          image: your-registry/fastapi:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: fastapi
  namespace: fastapi-app
spec:
  selector:
    app: fastapi
  ports:
    - port: 80
      targetPort: 8000

---
# Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi
  namespace: fastapi-app
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi
                port:
                  number: 80

---
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-hpa
  namespace: fastapi-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

# Project 6: Serverless Data Pipeline

## Architecture
```
S3 (Raw) → Lambda → DynamoDB
    │
    └── Kinesis → Lambda → S3 (Analytics)
                    │
                    └── Athena (Query)
```

## Implementation
```python
# ETL Lambda
import boto3
import json

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('processed_data')

def handler(event, context):
    for record in event['Records']:
        # Get data from Kinesis
        payload = json.loads(
            base64.b64decode(record['kinesis']['data'])
        )
        
        # Transform
        transformed = {
            'id': payload['event_id'],
            'timestamp': payload['timestamp'],
            'user_id': payload['user']['id'],
            'action': payload['action'],
            'metadata': json.dumps(payload.get('metadata', {}))
        }
        
        # Load to DynamoDB
        table.put_item(Item=transformed)
        
    return {'statusCode': 200}
```

---

*Continue to Part 8 for Code Templates and Part 9 for Quick Reference...*
