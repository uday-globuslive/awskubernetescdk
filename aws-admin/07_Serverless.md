# Chapter 7: Serverless — Lambda, API Gateway & Event-Driven Architecture
## Function Compute, API Management, and Serverless Patterns

---

## 7.1 AWS Lambda Overview

Lambda is a serverless compute service. You provide code; AWS handles servers, OS, runtime patches, scaling, and availability. You pay only for compute time consumed.

```
Lambda Execution Model:
┌────────────────────────────────────────────────────────────────────┐
│                         Lambda Service                             │
│                                                                    │
│  Event Source        Lambda Function          Output               │
│  ─────────────       ───────────────          ──────               │
│  API Gateway    →                             → Response           │
│  S3 Event       →   ┌─────────────────┐      → Async              │
│  DynamoDB       →   │  Your Code      │      → SQS/SNS            │
│  SQS            →   │  handler(event, │      → DynamoDB           │
│  EventBridge    →   │  context)       │      → Other Lambda       │
│  CloudWatch     →   │                 │                            │
│  IoT            →   │  Runtime:       │                            │
│  ALB            →   │  Python/Node/   │                            │
│  Kinesis        →   │  Java/Go/Ruby/  │                            │
│  Cognito        →   │  .NET/Custom    │                            │
│  ...            →   └─────────────────┘                            │
│                                                                    │
│  Concurrency: 1000 simultaneous executions per region (default)   │
│  Duration: up to 15 minutes per invocation                        │
│  Memory: 128MB - 10,240MB (CPU scales with memory)               │
│  Storage: /tmp up to 10GB ephemeral                               │
│  Package size: 50MB zipped, 250MB unzipped, 10GB container image  │
└────────────────────────────────────────────────────────────────────┘
```

### Lambda Pricing

```
Pricing components:
  1. Number of requests: $0.20 per 1 million requests
  2. Duration: $0.0000166667 per GB-second (memory GB × seconds)

Free Tier:
  1 million requests/month FREE forever
  400,000 GB-seconds/month FREE forever

Example: 128MB function, 1M invocations, 200ms each
  Cost = 1M × $0.0000002 + (0.128GB × 0.2s × 1M) × $0.0000166667
       = $0.20 + $0.43 = $0.63/month
```

---

## 7.2 Creating Lambda Functions

### Package and Deploy

```bash
# ── PYTHON LAMBDA ─────────────────────────────────────────────
mkdir -p my-function
cat > my-function/handler.py << 'EOF'
import json
import boto3
import os
import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event: dict, context: Any) -> dict:
    """Main Lambda handler."""
    logger.info(f"Event: {json.dumps(event)}")
    logger.info(f"RequestId: {context.aws_request_id}")
    logger.info(f"Remaining time: {context.get_remaining_time_in_millis()}ms")
    
    try:
        # Your business logic here
        result = process(event)
        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'headers': {'Content-Type': 'application/json'}
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise  # Re-raise to Lambda (marks as failure, triggers retry/DLQ)

def process(event):
    return {'message': 'Success', 'event_keys': list(event.keys())}
EOF

# Install dependencies to package directory
pip install requests boto3 -t my-function/

# Create deployment ZIP
cd my-function && zip -r ../my-function.zip . && cd ..

# Create function
aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --handler handler.handler \
  --role arn:aws:iam::123:role/LambdaExecutionRole \
  --zip-file fileb://my-function.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables='{
    "DB_HOST":"prod-postgres.abc.rds.amazonaws.com",
    "LOG_LEVEL":"INFO",
    "ENVIRONMENT":"production"
  }' \
  --vpc-config SubnetIds=$PRIV_SUB_1,$PRIV_SUB_2,SecurityGroupIds=$LAMBDA_SG \
  --dead-letter-config TargetArn=arn:aws:sqs:us-east-1:123:lambda-dlq \
  --tracing-config Mode=Active \         # Enable X-Ray tracing
  --ephemeral-storage '{"Size": 1024}' \ # 1GB /tmp
  --tags Environment=prod,Service=my-function

# Update function code (deploy new version)
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://my-function.zip

# Update configuration
aws lambda update-function-configuration \
  --function-name my-function \
  --timeout 60 \
  --memory-size 1024 \
  --environment Variables='{"LOG_LEVEL":"DEBUG"}'

# Invoke function manually
aws lambda invoke \
  --function-name my-function \
  --payload '{"test": "data"}' \
  --log-type Tail \
  response.json
cat response.json
```

### Container Image Lambda

```dockerfile
# Dockerfile for Lambda
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
```

```bash
# Build and push to ECR
aws ecr create-repository --repository-name my-lambda

ECR_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda

docker build -t $ECR_URI:latest .
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker push $ECR_URI:latest

# Create Lambda from container image
aws lambda create-function \
  --function-name my-container-function \
  --package-type Image \
  --code ImageUri=$ECR_URI:latest \
  --role arn:aws:iam::123:role/LambdaExecutionRole \
  --timeout 300 \
  --memory-size 3008
```

---

## 7.3 Lambda Versions and Aliases

```bash
# Publish a version (immutable snapshot of code + config)
VERSION=$(aws lambda publish-version \
  --function-name my-function \
  --description "v1.0.0 production release" \
  --query "Version" --output text)
# Version ARN: arn:aws:lambda:...:my-function:5

# Create/update alias (named pointer to version)
aws lambda create-alias \
  --function-name my-function \
  --name production \
  --function-version $VERSION \
  --description "Production stable"

# Alias with weighted traffic (canary deployment: 90% v5, 10% v6)
aws lambda update-alias \
  --function-name my-function \
  --name production \
  --function-version 6 \
  --routing-config AdditionalVersionWeights={"5"=0.9}
  # 90% of traffic still goes to v5, 10% to v6 (the new $LATEST)

# Shift all traffic to new version
aws lambda update-alias \
  --function-name my-function \
  --name production \
  --function-version 6 \
  --routing-config AdditionalVersionWeights={}
```

---

## 7.4 Lambda Concurrency

```
Concurrency Types:
┌──────────────────────────────────────────────────────────────────┐
│ Unreserved concurrency: shared pool (default 1000 per region)   │
│ Reserved concurrency: guaranteed capacity, prevents noisy neighbor│
│ Provisioned concurrency: pre-warmed instances (no cold start)   │
└──────────────────────────────────────────────────────────────────┘

Cold Start Problem:
  First invocation (or after idle): Lambda must:
    1. Download code from S3 (~100-500ms)
    2. Start container (~100-200ms)
    3. Initialize runtime (~100-500ms Python)
    4. Run any module-level initialization code
  = Total cold start: 200ms to 2+ seconds (Java worst)
  
  Subsequent invocations reuse warm container: < 1ms overhead
  
Solutions:
  1. Provisioned Concurrency: keeps N instances warm (costs extra)
  2. Scheduled warm-up: ping function every 5 minutes
  3. Choose runtime: Python/Node faster cold starts than Java
  4. Keep package small (less download time)
  5. Use /tmp caching to amortize init cost
```

```bash
# Reserve concurrency (also acts as throttle limit)
aws lambda put-function-concurrency \
  --function-name my-function \
  --reserved-concurrent-executions 100
  # 0 = throttle all invocations (emergency kill switch)

# Enable provisioned concurrency (no cold starts!)
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier production \   # Use alias or version
  --provisioned-concurrent-executions 10

# Auto-scaling for provisioned concurrency
aws application-autoscaling register-scalable-target \
  --service-namespace lambda \
  --resource-id function:my-function:production \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --min-capacity 5 \
  --max-capacity 50

aws application-autoscaling put-scaling-policy \
  --service-namespace lambda \
  --resource-id function:my-function:production \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --policy-name LambdaProvisionedScaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    "TargetValue=0.7,PredefinedMetricSpecification={PredefinedMetricType=LambdaProvisionedConcurrencyUtilization}"
```

---

## 7.5 Lambda Triggers & Event Sources

### SQS Trigger

```bash
# Create SQS event source mapping
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:123:orders-queue \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \  # Wait up to 5s to fill batch
  --function-response-types ReportBatchItemFailures  # Partial batch failure
```

```python
# Lambda handling SQS messages with partial batch failure support
def handler(event, context):
    batch_item_failures = []
    
    for record in event['Records']:
        message_id = record['messageId']
        body = json.loads(record['body'])
        
        try:
            process_order(body)
        except Exception as e:
            logger.error(f"Failed to process {message_id}: {e}")
            batch_item_failures.append({'itemIdentifier': message_id})
    
    # Return failed items — Lambda will retry only those
    return {'batchItemFailures': batch_item_failures}
```

### Kinesis Trigger

```bash
aws lambda create-event-source-mapping \
  --function-name stream-processor \
  --event-source-arn arn:aws:kinesis:us-east-1:123:stream/my-stream \
  --starting-position LATEST \
  --batch-size 100 \
  --maximum-batching-window-in-seconds 5 \
  --parallelization-factor 10 \    # Process 10 shards in parallel per shard
  --bisect-batch-on-function-error \
  --destination-config '{"OnFailure": {"Destination": "arn:aws:sqs:...:stream-failures"}}'
```

### Lambda Destinations

```bash
# Configure async invocation destinations
aws lambda put-function-event-invoke-config \
  --function-name my-function \
  --maximum-retry-attempts 2 \
  --maximum-event-age-in-seconds 3600 \
  --destination-config '{
    "OnSuccess": {"Destination": "arn:aws:sqs:us-east-1:123:success-queue"},
    "OnFailure": {"Destination": "arn:aws:sns:us-east-1:123:failure-alerts"}
  }'
```

### EventBridge Rule Trigger

```bash
# Trigger Lambda on schedule (every 5 minutes)
aws events put-rule \
  --name HealthCheckRule \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED

aws events put-targets \
  --rule HealthCheckRule \
  --targets "Id=LambdaTarget,Arn=arn:aws:lambda:us-east-1:123:function:health-checker"

# Give EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name health-checker \
  --principal events.amazonaws.com \
  --statement-id HealthCheckRule \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:events:us-east-1:123:rule/HealthCheckRule
```

---

## 7.6 Lambda Layers

Layers allow sharing common code and dependencies across multiple Lambda functions:

```bash
# Create a layer (shared dependencies)
mkdir python && pip install boto3 requests psycopg2-binary -t python/
zip -r my-layer.zip python/

aws lambda publish-layer-version \
  --layer-name common-dependencies \
  --description "Shared Python packages" \
  --zip-file fileb://my-layer.zip \
  --compatible-runtimes python3.12 python3.11 \
  --compatible-architectures x86_64 arm64

# Use layer in function
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123:layer:common-dependencies:3

# AWS provides managed layers (e.g., AWS SDK data plane)
# Powertools for Lambda (Python) - AWS recommended observability layer
POWERTOOLS_ARN="arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:67"
```

### Lambda Powertools

AWS Lambda Powertools provides structured logging, tracing, metrics, and more:

```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent

logger = Logger(service="order-service")
tracer = Tracer(service="order-service")
metrics = Metrics(namespace="OrderService", service="order-service")

@logger.inject_lambda_context(correlation_id_path="requestContext.requestId")
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: APIGatewayProxyEvent, context: LambdaContext) -> dict:
    logger.info("Processing order", extra={"order_id": event.get("pathParameters", {}).get("id")})
    
    with tracer.capture_method():
        result = process_order(event)
    
    metrics.add_metric(name="OrderProcessed", unit=MetricUnit.Count, value=1)
    
    return {"statusCode": 200, "body": json.dumps(result)}
```

---

## 7.7 Lambda@Edge & CloudFront Functions

### Lambda@Edge

Runs Lambda at CloudFront edge locations to customize content delivery:

```
Lambda@Edge Trigger Points:
  Viewer Request  →  CloudFront  →  Origin Request
                         ↓               ↑
  Viewer Response ←      ←      ←  Origin Response

  Viewer Request:  Runs before checking cache (every request!)
  Origin Request:  Runs only on cache miss before forwarding to origin
  Origin Response: Runs after receiving response from origin
  Viewer Response: Runs before CloudFront returns response to viewer
```

```python
# Lambda@Edge — Add security headers (Viewer Response)
def handler(event, context):
    response = event['Records'][0]['cf']['response']
    headers = response['headers']
    
    # Add security headers
    headers['strict-transport-security'] = [{
        'key': 'Strict-Transport-Security',
        'value': 'max-age=63072000; includeSubdomains; preload'
    }]
    headers['x-content-type-options'] = [{'key': 'X-Content-Type-Options', 'value': 'nosniff'}]
    headers['x-frame-options'] = [{'key': 'X-Frame-Options', 'value': 'DENY'}]
    headers['x-xss-protection'] = [{'key': 'X-XSS-Protection', 'value': '1; mode=block'}]
    headers['referrer-policy'] = [{'key': 'Referrer-Policy', 'value': 'same-origin'}]
    headers['content-security-policy'] = [{
        'key': 'Content-Security-Policy',
        'value': "default-src 'self'; img-src 'self' data: https:; script-src 'self'"
    }]
    
    return response

# Lambda@Edge — A/B testing (Viewer Request)
import random

def handler(event, context):
    request = event['Records'][0]['cf']['request']
    
    # Check if user already has variant assigned
    cookies = request.get('headers', {}).get('cookie', [])
    existing_variant = None
    
    for cookie in cookies:
        for cookie_part in cookie['value'].split(';'):
            if 'variant=' in cookie_part.strip():
                existing_variant = cookie_part.strip().split('=')[1]
    
    # Assign variant if not set
    if not existing_variant:
        existing_variant = 'A' if random.random() < 0.5 else 'B'
    
    # Route to different origin based on variant
    if existing_variant == 'B':
        request['origin'] = {
            'custom': {
                'domainName': 'v2.example.com',
                'protocol': 'https',
                'port': 443,
                'path': '',
                'sslProtocols': ['TLSv1.2'],
                'readTimeout': 30,
                'keepaliveTimeout': 5
            }
        }
    
    return request
```

---

## 7.8 API Gateway

API Gateway allows you to create, publish, maintain, and secure APIs. Three types:

```
┌──────────────────────────────────────────────────────────────────┐
│           API GATEWAY TYPES                                      │
├────────────────────┬─────────────────────────────────────────────┤
│ REST API           │ Full-featured, more complex, more expensive │
│                    │ Usage plans, API keys, request validation   │
│                    │ Per-request throttling, caching             │
├────────────────────┼─────────────────────────────────────────────┤
│ HTTP API           │ Low latency, simpler, cheaper (70%)         │
│                    │ JWT authorization, CORS, Lambda/HTTP proxy  │
│                    │ Best for: Lambda proxy, microservices       │
├────────────────────┼─────────────────────────────────────────────┤
│ WebSocket API      │ Persistent connections, real-time apps      │
│                    │ Route messages to Lambda/HTTP backends      │
│                    │ Best for: chat, live dashboards, gaming     │
└────────────────────┴─────────────────────────────────────────────┘
```

### HTTP API (Recommended for most uses)

```bash
# Create HTTP API
API_ID=$(aws apigatewayv2 create-api \
  --name prod-api \
  --protocol-type HTTP \
  --cors-configuration \
    "AllowOrigins=https://example.com,AllowMethods=GET POST PUT DELETE,AllowHeaders=Content-Type Authorization,MaxAge=300" \
  --query "ApiId" --output text)

# Create Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:123:function:my-function \
  --payload-format-version 2.0 \
  --query "IntegrationId" --output text)

# Create routes
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "GET /users" \
  --target "integrations/$INTEGRATION_ID"

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "POST /users" \
  --target "integrations/$INTEGRATION_ID"

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "GET /users/{userId}" \
  --target "integrations/$INTEGRATION_ID"

# Add JWT authorizer
AUTHORIZER_ID=$(aws apigatewayv2 create-authorizer \
  --api-id $API_ID \
  --name JWTAuthorizer \
  --authorizer-type JWT \
  --identity-source '$request.header.Authorization' \
  --jwt-configuration \
    "Audience=my-app-client-id,Issuer=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_POOLID" \
  --query "AuthorizerId" --output text)

# Secure route with JWT auth
aws apigatewayv2 update-route \
  --api-id $API_ID \
  --route-key "POST /users" \
  --authorization-type JWT \
  --authorizer-id $AUTHORIZER_ID \
  --authorization-scopes "openid email"

# Create stage (deployment)
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy \
  --default-route-settings \
    "ThrottlingBurstLimit=100,ThrottlingRateLimit=50"

# Allow API Gateway to invoke Lambda
aws lambda add-permission \
  --function-name my-function \
  --statement-id allow-api-gateway \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:123:$API_ID/*/*"

echo "API URL: https://$API_ID.execute-api.us-east-1.amazonaws.com/prod"
```

### REST API (Full-featured)

```bash
# Create REST API
REST_API_ID=$(aws apigateway create-rest-api \
  --name prod-rest-api \
  --endpoint-configuration Types=REGIONAL \
  --query "id" --output text)

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id $REST_API_ID \
  --query "items[?path=='/'].id" --output text)

# Create resource
USERS_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $REST_API_ID \
  --parent-id $ROOT_RESOURCE_ID \
  --path-part users \
  --query "id" --output text)

# Create method (GET /users)
aws apigateway put-method \
  --rest-api-id $REST_API_ID \
  --resource-id $USERS_RESOURCE_ID \
  --http-method GET \
  --authorization-type COGNITO_USER_POOLS \
  --authorizer-id $COGNITO_AUTH_ID \
  --request-validator-id $VALIDATOR_ID

# Create Lambda integration
aws apigateway put-integration \
  --rest-api-id $REST_API_ID \
  --resource-id $USERS_RESOURCE_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123:function:get-users/invocations"

# Enable caching on stage
aws apigateway create-deployment \
  --rest-api-id $REST_API_ID \
  --stage-name prod \
  --stage-description "Production" \
  --description "v1.0 deployment"

aws apigateway update-stage \
  --rest-api-id $REST_API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/cacheClusterEnabled,value=true \
    op=replace,path=/cacheClusterSize,value=0.5 \
    op=replace,path=//*/*/caching/ttlInSeconds,value=300

# Create usage plan and API key
aws apigateway create-usage-plan \
  --name prod-usage-plan \
  --api-stages "apiId=$REST_API_ID,stage=prod" \
  --throttle "burstLimit=1000,rateLimit=500" \
  --quota "limit=1000000,period=MONTH"

aws apigateway create-api-key \
  --name partner-api-key \
  --enabled
```

### Lambda Handler for API Gateway

```python
import json
import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event: dict, context: Any) -> dict:
    """Handler for both HTTP API (v2) and REST API (v1) formats."""
    
    # Detect format version
    version = event.get('version', '1.0')
    
    if version == '2.0':
        # HTTP API format
        method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']
        path_params = event.get('pathParameters', {})
        query_params = event.get('queryStringParameters', {})
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')
    else:
        # REST API format
        method = event['httpMethod']
        path = event['path']
        path_params = event.get('pathParameters', {})
        query_params = event.get('queryStringParameters', {})
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    
    logger.info(f"{method} {path} user={user_id}")
    
    try:
        result = route_request(method, path, path_params, query_params, body, user_id)
        return success_response(result)
    except ValueError as e:
        return error_response(400, str(e))
    except PermissionError as e:
        return error_response(403, str(e))
    except KeyError as e:
        return error_response(404, f"Not found: {e}")
    except Exception as e:
        logger.exception("Unhandled error")
        return error_response(500, "Internal server error")

def route_request(method, path, path_params, query_params, body, user_id):
    if method == 'GET' and path.startswith('/users') and 'userId' in (path_params or {}):
        return get_user(path_params['userId'], user_id)
    elif method == 'GET' and path == '/users':
        return list_users(query_params)
    elif method == 'POST' and path == '/users':
        return create_user(body, user_id)
    else:
        raise KeyError(f"No route for {method} {path}")

def success_response(data, status_code=200):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-ID': str(import_uuid().uuid4())
        },
        'body': json.dumps(data, default=str)
    }

def error_response(status_code, message):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }
```

---

## 7.9 WebSocket API

```python
import boto3
import json

apigateway = boto3.client('apigatewaymanagementapi',
    endpoint_url='https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod'
)

def connection_handler(event, context):
    """Handle $connect, $disconnect, and custom routes."""
    route = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']
    
    if route == '$connect':
        # Store connection ID (e.g., in DynamoDB)
        save_connection(connection_id, event.get('queryStringParameters', {}))
        return {'statusCode': 200}
    
    elif route == '$disconnect':
        remove_connection(connection_id)
        return {'statusCode': 200}
    
    elif route == 'sendMessage':
        body = json.loads(event.get('body', '{}'))
        broadcast_message(body['message'], connection_id)
        return {'statusCode': 200}

def broadcast_message(message, sender_id):
    """Send message to all connected clients."""
    connections = get_all_connections()
    
    for conn_id in connections:
        try:
            apigateway.post_to_connection(
                ConnectionId=conn_id,
                Data=json.dumps({
                    'sender': sender_id,
                    'message': message
                }).encode()
            )
        except apigateway.exceptions.GoneException:
            # Client disconnected — remove from DB
            remove_connection(conn_id)
```

---

## 7.10 Serverless Application Model (SAM)

AWS SAM simplifies defining serverless applications. Template extends CloudFormation.

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Production Serverless API

Globals:
  Function:
    Runtime: python3.12
    MemorySize: 512
    Timeout: 30
    Tracing: Active
    Layers:
      - !Ref CommonLayer
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        LOG_LEVEL: INFO

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

Resources:
  # API definition
  MyApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Environment
      Auth:
        DefaultAuthorizer: JWTAuthorizer
        Authorizers:
          JWTAuthorizer:
            IdentitySource: $request.header.Authorization
            JwtConfiguration:
              audience:
                - !Ref UserPoolClientId
              issuer: !Sub "https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPoolId}"
      CorsConfiguration:
        AllowOrigins:
          - https://example.com
        AllowHeaders:
          - Content-Type
          - Authorization
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE

  # Lambda Functions
  GetUsersFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: users.get_handler
      Events:
        GetUsers:
          Type: HttpApi
          Properties:
            ApiId: !Ref MyApi
            Method: GET
            Path: /users
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UsersTable

  CreateUserFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: users.create_handler
      ReservedConcurrentExecutions: 50
      DeadLetterQueue:
        Type: SQS
        TargetArn: !GetAtt DLQ.Arn
      Events:
        CreateUser:
          Type: HttpApi
          Properties:
            ApiId: !Ref MyApi
            Method: POST
            Path: /users
        SQSTrigger:
          Type: SQS
          Properties:
            Queue: !GetAtt OrdersQueue.Arn
            BatchSize: 10
            FunctionResponseTypes:
              - ReportBatchItemFailures

  # Shared layer
  CommonLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: common-dependencies
      ContentUri: layers/common/
      CompatibleRuntimes:
        - python3.12
    Metadata:
      BuildMethod: python3.12

  # DynamoDB table
  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH

  OrdersQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 180
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DLQ.Arn
        maxReceiveCount: 3

  DLQ:
    Type: AWS::SQS::Queue

Outputs:
  ApiUrl:
    Value: !Sub "https://${MyApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
```

```bash
# SAM CLI commands
sam build                        # Build Lambda packages
sam local invoke GetUsersFunction --event events/test.json  # Test locally
sam local start-api              # Start local API Gateway
sam validate                     # Validate template
sam deploy --guided              # Deploy with interactive prompts
sam deploy --stack-name prod-api --resolve-s3  # Deploy
sam logs --name GetUsersFunction --tail  # Stream logs
sam delete                       # Delete stack
```

---

## 7.11 Interview Q&A

**Q: What is a Lambda cold start and how do you mitigate it?**
A: A cold start occurs on the first Lambda invocation when AWS must provision a new container, download code, start the runtime, and run initialization code — taking 200ms to several seconds. Mitigation strategies: (1) Provisioned Concurrency — keeps N instances warm (costs extra); (2) scheduled pings to keep containers warm; (3) choose faster runtimes like Python/Node over Java; (4) minimize package size and dependencies; (5) move initialization code outside the handler to amortize across invocations.

**Q: What is the difference between reserved and provisioned concurrency?**
A: Reserved concurrency sets a maximum limit of simultaneous executions for a function — it guarantees capacity (won't be throttled by other functions) and also acts as a throttle ceiling. Provisioned concurrency pre-initializes a specified number of execution environments to eliminate cold starts. Both can be configured together: provisioned < reserved.

**Q: How does Lambda@Edge differ from regular Lambda?**
A: Lambda@Edge runs at CloudFront's 400+ edge locations closest to users, triggered by CloudFront events (viewer request/response, origin request/response). Constraints: max 5 seconds (viewer) or 30 seconds (origin) timeout, max 128MB memory, no VPC access, no environment variables (use SSM Parameter Store), code must be in us-east-1 region. Use for personalization, A/B testing, authentication at the edge, adding security headers.

**Q: What is the difference between HTTP API and REST API in API Gateway?**
A: HTTP API is simpler, lower latency (~60% lower), and cheaper (about 70% less) but has fewer features. REST API supports: request/response transformation with mapping templates, request validation, caching, usage plans and API keys, private APIs, custom gateway responses, canary deployments. Use HTTP API for Lambda proxy, JWT auth, simple CRUD. Use REST API when you need those additional features.

**Q: When should you use Lambda vs EC2/ECS?**
A: Use Lambda when: function runs < 15 minutes; workload is event-driven and sporadic; you want zero idle cost (pay only for invocations); you don't need persistent connections (Lambda can use RDS Proxy); code is stateless. Use EC2/ECS when: long-running workloads (> 15 min); persistent database connections without proxy; GPU compute; very high memory (> 10GB); workloads requiring specific OS or software.

**Q: How do Lambda layers work?**
A: Lambda Layers are ZIP archives containing dependencies, custom runtimes, or configuration that can be referenced by multiple Lambda functions. A function can have up to 5 layers. Layers are extracted to /opt/ in the execution environment. Benefits: separate code from dependencies (faster deployments), share packages across functions, use Lambda's managed layers (AWS X-Ray SDK, AWS SDK for JavaScript). Layers are versioned — update the version number to use newer versions.

**Q: What is SAM and why use it over raw CloudFormation?**
A: AWS Serverless Application Model (SAM) is a shorthand extension of CloudFormation that simplifies defining serverless resources. SAM automatically creates API Gateway + Lambda integrations with less YAML, provides `sam local` for local testing, handles packaging and deploying Lambda code, and includes built-in best practices like permissions. `Transform: AWS::Serverless-2016-10-31` makes CloudFormation process SAM syntax.
