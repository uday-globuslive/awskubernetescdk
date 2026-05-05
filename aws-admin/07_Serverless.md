# Chapter 7: Serverless — Lambda, API Gateway, Step Functions & SAM
## Event-Driven, Zero-Infrastructure Computing

---

## 7.1 Lambda Overview

Lambda runs your code in response to events — no servers to manage, no idle cost.

```
┌──────────────────────────────────────────────────────────┐
│                  LAMBDA KEY FACTS                        │
│                                                          │
│  Languages: Python, Node.js, Java, Go, Ruby, .NET,      │
│             any via custom runtime                       │
│  Max timeout: 15 minutes                                 │
│  Memory: 128 MB to 10 GB (CPU scales with memory)       │
│  Ephemeral storage: 512 MB to 10 GB (/tmp)              │
│  Deployment: ZIP (250 MB) or container image (10 GB)    │
│  Concurrency: 1000 per region (default, can increase)   │
│  Pricing: $0.0000002 per request + $0.0000166/GB-second │
│  Free tier: 1M requests/month + 400,000 GB-seconds      │
└──────────────────────────────────────────────────────────┘
```

### Lambda Function Anatomy

```python
# handler.py
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    event   → input data from the trigger (API Gateway, SQS, S3, etc.)
    context → runtime info (function name, memory limit, time remaining)
    """
    logger.info("Event: %s", json.dumps(event))
    logger.info("Function name: %s", context.function_name)
    logger.info("Time remaining: %d ms", context.get_remaining_time_in_millis())
    
    # Process event
    body = json.loads(event.get("body", "{}"))
    name = body.get("name", "World")
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({"message": f"Hello, {name}!"})
    }
```

### Deploying Lambda

```bash
# Package and deploy via ZIP
zip -r function.zip handler.py requirements/

aws lambda create-function \
  --function-name my-function \
  --runtime python3.11 \
  --handler handler.handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::123456789012:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables='{ENVIRONMENT=prod,TABLE_NAME=users}' \
  --layers arn:aws:lambda:us-east-1:123456:layer:my-deps:3

# Update function code
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip

# Publish a version (immutable snapshot)
aws lambda publish-version \
  --function-name my-function \
  --description "v1.2.0"

# Create alias pointing to version
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version 5

# Canary deployment: 90% v5, 10% v6
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 6 \
  --routing-config AdditionalVersionWeights={"5"=0.9}

# Invoke manually
aws lambda invoke \
  --function-name my-function \
  --payload '{"body": "{\"name\": \"Alice\"}"}' \
  --log-type Tail \
  response.json

# View logs
aws logs tail /aws/lambda/my-function --follow
```

### Lambda Triggers / Event Sources

```
┌──────────────────────────────────────────────────────────────┐
│                LAMBDA EVENT SOURCES                          │
├────────────────────────┬─────────────────────────────────────┤
│ API Gateway / ALB      │ HTTP requests → REST API            │
│ S3                     │ Object uploaded/deleted             │
│ SQS                    │ Queue message (batch)               │
│ SNS                    │ Topic notification                  │
│ EventBridge            │ Scheduled (cron) or event bus       │
│ DynamoDB Streams       │ Table changes (CDC)                 │
│ Kinesis                │ Stream records                      │
│ CloudWatch Logs        │ Log subscription filter             │
│ Cognito                │ Auth events (pre/post signup)       │
│ IoT Core               │ Device messages                     │
└────────────────────────┴─────────────────────────────────────┘
```

### Lambda Concurrency

```
┌──────────────────────────────────────────────────────────┐
│                LAMBDA CONCURRENCY                        │
│                                                          │
│  Reserved Concurrency                                    │
│  • Limits maximum concurrent executions for a function  │
│  • Prevents one function from using all 1000 limit      │
│  • Setting to 0 = disable the function                  │
│                                                          │
│  Provisioned Concurrency                                 │
│  • Pre-warms N instances — eliminates cold start        │
│  • Pay for pre-warmed instances even if idle            │
│  • Use for latency-sensitive functions                   │
│                                                          │
│  Cold Start:                                             │
│  New container → Init runtime → Load code → Run handler │
│  Python: ~100-500ms   Java: ~1-5s (use SnapStart)       │
│                                                          │
│  Warm Start:                                             │
│  Existing container → Run handler (milliseconds)        │
└──────────────────────────────────────────────────────────┘
```

```bash
# Set reserved concurrency
aws lambda put-function-concurrency \
  --function-name my-function \
  --reserved-concurrent-executions 50

# Set provisioned concurrency on alias
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

---

## 7.2 API Gateway

API Gateway creates, deploys, and manages REST/HTTP/WebSocket APIs.

### HTTP API vs REST API

```
┌──────────────────────────────────────────────────────────┐
│           HTTP API vs REST API                           │
├──────────────────────┬───────────────────────────────────┤
│ HTTP API             │ REST API                          │
├──────────────────────┼───────────────────────────────────┤
│ Newer, recommended   │ Older, more features              │
│ 70% cheaper          │ More expensive                    │
│ Lower latency        │ Higher latency                    │
│ JWT auth built-in    │ Cognito, Lambda authorizers       │
│ No usage plans       │ Usage plans, API keys             │
│ No request transform │ Request/response transforms       │
│ Use for most APIs    │ Use for API keys / transforms     │
└──────────────────────┴───────────────────────────────────┘
```

### Creating an HTTP API

```bash
# Create HTTP API
API_ID=$(aws apigatewayv2 create-api \
  --name my-http-api \
  --protocol-type HTTP \
  --cors-configuration \
    AllowOrigins="*",AllowMethods="GET,POST,PUT,DELETE",AllowHeaders="Content-Type,Authorization" \
  --query ApiId --output text)

# Create Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:123456:function:my-function \
  --payload-format-version 2.0 \
  --query IntegrationId --output text)

# Create route
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "ANY /{proxy+}" \
  --target "integrations/$INTEGRATION_ID"

# Create stage and deploy
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name my-function \
  --statement-id api-gateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:123456:$API_ID/*"

# API URL: https://$API_ID.execute-api.us-east-1.amazonaws.com/prod/
```

### Lambda Authorizer (Custom Auth)

```python
# authorizer/handler.py — validates JWT token
import jwt
import os


def handler(event, context):
    token = event.get("headers", {}).get("authorization", "").replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        return {
            "isAuthorized": True,
            "context": {
                "userId": payload["sub"],
                "email": payload["email"]
            }
        }
    except jwt.InvalidTokenError:
        return {"isAuthorized": False}
```

---

## 7.3 Step Functions — Workflow Orchestration

Step Functions orchestrates multi-step workflows as state machines.

```
Order Processing Workflow:
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Validate │ →  │  Charge  │ →  │ Reserve  │ →  │  Send    │
│  Order   │    │ Payment  │    │ Stock    │    │  Email   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      │               │               │
   Invalid         Failed          Out of
      │               │              Stock
      ▼               ▼               ▼
  Reject          Refund          Notify User
```

```json
// state-machine.json
{
  "Comment": "Order processing workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456:function:validate-order",
      "Next": "ChargePayment",
      "Catch": [{
        "ErrorEquals": ["ValidationError"],
        "Next": "RejectOrder"
      }]
    },
    "ChargePayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456:function:charge-payment",
      "Next": "CheckPaymentResult",
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }]
    },
    "CheckPaymentResult": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.payment.status",
          "StringEquals": "SUCCESS",
          "Next": "ReserveStock"
        },
        {
          "Variable": "$.payment.status",
          "StringEquals": "FAILED",
          "Next": "RefundAndNotify"
        }
      ]
    },
    "ReserveStock": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456:function:reserve-stock",
      "Next": "SendConfirmationEmail"
    },
    "SendConfirmationEmail": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:us-east-1:123456:order-notifications",
        "Message.$": "States.Format('Order {} confirmed!', $.orderId)"
      },
      "End": true
    },
    "RejectOrder": {
      "Type": "Fail",
      "Error": "OrderRejected",
      "Cause": "Order validation failed"
    },
    "RefundAndNotify": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456:function:refund",
      "End": true
    }
  }
}
```

---

## 7.4 EventBridge — Event Bus

EventBridge routes events from AWS services, SaaS apps, or your own apps to targets.

```
Sources:                    EventBridge           Targets:
────────                    ───────────           ────────
AWS Services (EC2, RDS) →   Event Bus    →        Lambda
Your App (PutEvents)    →   + Rules      →        SQS
SaaS (Salesforce, etc.) →   + Patterns   →        SNS
                                                  Step Functions
                                                  API Gateway
```

```bash
# Put custom event
aws events put-events \
  --entries '[{
    "Source": "myapp.orders",
    "DetailType": "OrderCreated",
    "Detail": "{\"orderId\": \"123\", \"userId\": \"456\", \"amount\": 99.99}",
    "EventBusName": "default"
  }]'

# Create rule — trigger Lambda when OrderCreated event
aws events put-rule \
  --name trigger-order-processor \
  --event-pattern '{
    "source": ["myapp.orders"],
    "detail-type": ["OrderCreated"]
  }' \
  --state ENABLED

# Scheduled rule — run every day at 8am UTC (cron)
aws events put-rule \
  --name daily-report \
  --schedule-expression "cron(0 8 * * ? *)" \
  --state ENABLED

# Set Lambda as target
aws events put-targets \
  --rule trigger-order-processor \
  --targets 'Id=order-processor,Arn=arn:aws:lambda:us-east-1:123456:function:process-order'
```

---

## 7.5 AWS SAM — Serverless Application Model

SAM is a framework to define serverless apps as code (a superset of CloudFormation).

```yaml
# template.yaml (SAM template)
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: Serverless FastAPI Application

Globals:
  Function:
    Runtime: python3.11
    Timeout: 30
    MemorySize: 512
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment

Parameters:
  Environment:
    Type: String
    Default: dev

Resources:

  FastAPIFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub "fastapi-${Environment}"
      Handler: lambda_handler.handler
      CodeUri: src/
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UsersTable
        - SSMParameterReadPolicy:
            ParameterName: !Sub "/myapp/${Environment}/*"
      Events:
        Api:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /{proxy+}
            Method: ANY
        ApiRoot:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /
            Method: ANY

  HttpApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Environment
      CorsConfiguration:
        AllowOrigins:
          - "*"
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
        AllowHeaders:
          - Content-Type
          - Authorization

  UsersTable:
    Type: AWS::Serverless::SimpleTable
    Properties:
      TableName: !Sub "users-${Environment}"
      PrimaryKey:
        Name: user_id
        Type: String

Outputs:
  ApiEndpoint:
    Value: !Sub "https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
```

```bash
# Install SAM CLI
pip install aws-sam-cli

# Build (packages dependencies)
sam build

# Test locally
sam local invoke FastAPIFunction --event events/api-event.json
sam local start-api --port 3000      # Full local API

# Deploy (guided first time)
sam deploy --guided

# Deploy to specific environment
sam deploy \
  --stack-name my-app-prod \
  --parameter-overrides Environment=prod \
  --capabilities CAPABILITY_IAM

# View logs
sam logs --name FastAPIFunction --stack-name my-app-prod --tail
```

---

## 7.6 Interview Questions

**Q: What is a Lambda cold start and how do you reduce it?**
> A cold start happens when Lambda needs to create a new execution environment — download the code, initialise the runtime, and load the handler. This adds 100ms–5s (varies by language and package size). To reduce it: (1) Use Provisioned Concurrency to pre-warm instances. (2) Use Lambda SnapStart for Java. (3) Keep deployment packages small (only needed dependencies). (4) Put connection setup (DB client, Redis) outside the handler function (in global scope) so it reuses on warm invocations. (5) Use Python or Node.js (faster cold starts than Java).

**Q: What happens when Lambda concurrency reaches the limit?**
> When the account/function limit is hit, new invocations are throttled and receive a 429 TooManyRequestsException. For synchronous invocations (API Gateway), this error is returned to the caller. For asynchronous invocations (S3, SNS), Lambda retries with exponential backoff for up to 6 hours. For SQS triggers, messages stay in the queue. To fix: request limit increase, or use reserved concurrency to protect critical functions.

**Q: What is the difference between EventBridge and SQS?**
> SQS is a queue — messages are consumed by one consumer (point-to-point). Good for work queues where one worker processes each item. EventBridge is an event bus — events can be routed to multiple targets based on patterns (pub/sub, fan-out). Good for event-driven architectures where one event needs to trigger multiple actions. They're complementary: EventBridge often routes events to SQS queues, which Lambda then processes.
