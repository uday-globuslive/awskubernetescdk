# Part 3: AWS Lambda — Serverless Functions Deep Dive

---

## 6.1 Lambda Execution Model

```
┌─────────────────────────────────────────────────────────┐
│                    Lambda Lifecycle                      │
│                                                          │
│  INIT Phase (cold start):                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. Download code/container image (~100ms-2s)    │   │
│  │ 2. Start execution environment                  │   │
│  │ 3. Run initialization code (imports, globals)  │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                 │
│  INVOKE Phase (warm):  ▼                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 4. Run handler function                         │   │
│  │ 5. Return response                              │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                 │
│  Container reused for next invoke (~15 min idle timeout)│
└─────────────────────────────────────────────────────────┘
```

**Cold Start Mitigation**:
- Use Provisioned Concurrency (pre-warm containers)
- SnapStart for Java (snapshot initialized state)
- Minimize package size (only import needed modules)
- Use Lambda Layers for large dependencies
- Prefer Python/Node.js over Java for cold-start-sensitive paths

---

## 6.2 Lambda Handler Patterns

```python
# src/api/app.py — FastAPI on Lambda with Mangum
from mangum import Mangum
from fastapi import FastAPI

app = FastAPI(root_path="/prod")   # Match API Gateway stage name

@app.get("/orders")
async def list_orders():
    return {"orders": []}

# Mangum wraps FastAPI ASGI app as Lambda handler
handler = Mangum(app, lifespan="off")
```

```python
# src/worker/worker.py — SQS event handler
import json
import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="MyApp")
processor = BatchProcessor(event_type=EventType.SQS)


@tracer.capture_method
def process_order(record: dict) -> None:
    """Process a single SQS record."""
    body = json.loads(record["body"])
    order_id = body["order_id"]
    
    logger.info("Processing order", order_id=order_id)
    metrics.add_metric(name="OrdersProcessed", unit=MetricUnit.Count, value=1)
    
    # Business logic
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    
    table.update_item(
        Key={"PK": f"ORDER#{order_id}", "SK": "STATUS"},
        UpdateExpression="SET #status = :status, updatedAt = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "PROCESSING",
            ":now": datetime.utcnow().isoformat(),
        },
    )


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """Handle SQS batch with partial failure support."""
    return process_partial_response(
        event=event,
        record_handler=process_order,
        processor=processor,
        context=context,
    )
```

---

## 6.3 Lambda Powertools

```python
# Structured logging with correlation IDs
from aws_lambda_powertools import Logger

logger = Logger(service="orders-api")

@logger.inject_lambda_context(correlation_id_path="requestContext.requestId")
def handler(event, context):
    order_id = event["pathParameters"]["orderId"]
    logger.info("Fetching order", order_id=order_id, user_id=event["requestContext"]["authorizer"]["claims"]["sub"])
    
    # Logs will include: service, level, timestamp, correlation_id, order_id, user_id
    return {"statusCode": 200, "body": "..."}


# Distributed tracing with X-Ray
from aws_lambda_powertools import Tracer

tracer = Tracer(service="orders-api")

@tracer.capture_lambda_handler
def handler(event, context):
    order = get_order(event["pathParameters"]["orderId"])
    return {"statusCode": 200}

@tracer.capture_method(capture_response=False)   # Don't log sensitive return value
def get_order(order_id: str) -> dict:
    # Creates X-Ray subsegment automatically
    table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return table.get_item(Key={"PK": f"ORDER#{order_id}"}).get("Item")


# Feature flags with AppConfig
from aws_lambda_powertools.utilities.feature_flags import FeatureFlags, AppConfigStore

app_config = AppConfigStore(
    environment="prod",
    application="MyApp",
    name="features",
)
feature_flags = FeatureFlags(store=app_config)

def is_new_checkout_enabled(user_id: str) -> bool:
    return feature_flags.evaluate(
        name="new_checkout",
        context={"user_id": user_id},
        default=False,
    )
```

---

## 6.4 Lambda Environment — Connections and Caching

```python
# Optimize: initialize heavy clients outside the handler
import boto3
import os
from functools import lru_cache

# Initialized once per execution environment (reused across warm invocations)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["ORDERS_TABLE"])

secrets_client = boto3.client("secretsmanager")


@lru_cache(maxsize=None)
def get_db_password() -> str:
    """Cache secret across invocations — refresh handled by LRU cache TTL."""
    response = secrets_client.get_secret_value(
        SecretId=os.environ["DB_SECRET_ARN"]
    )
    return response["SecretString"]


# Connection pooling for databases (reuse across warm invocations)
import psycopg2
from psycopg2 import pool

_db_pool = None

def get_db_connection():
    global _db_pool
    if _db_pool is None:
        _db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=get_db_password(),
        )
    return _db_pool.getconn()
```

---

## 6.5 Lambda Error Handling and Retries

```python
# Structured error handling
class OrderNotFoundError(Exception):
    pass

class ValidationError(Exception):
    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.field = field


def handler(event: dict, context) -> dict:
    try:
        order_id = event["pathParameters"].get("orderId")
        if not order_id:
            raise ValidationError("orderId is required", field="orderId")
        
        order = get_order(order_id)
        if not order:
            raise OrderNotFoundError(f"Order {order_id} not found")
        
        return {
            "statusCode": 200,
            "body": json.dumps(order),
            "headers": {"Content-Type": "application/json"},
        }
    
    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e), "field": e.field}),
        }
    except OrderNotFoundError as e:
        return {"statusCode": 404, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        logger.exception("Unhandled error", error=str(e))
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
```

---

## 6.6 Lambda with EventBridge (Event-Driven Architecture)

```python
# Lambda consuming EventBridge events
import boto3
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from aws_lambda_powertools.utilities.typing import LambdaContext


def handler(event: dict, context: LambdaContext) -> None:
    bridge_event = EventBridgeEvent(event)
    
    detail = bridge_event.detail
    event_type = bridge_event.detail_type
    
    if event_type == "OrderPlaced":
        handle_order_placed(detail)
    elif event_type == "PaymentConfirmed":
        handle_payment_confirmed(detail)
    else:
        logger.warning("Unknown event type", event_type=event_type)


# Publishing to EventBridge from Lambda
def publish_event(detail_type: str, detail: dict) -> None:
    events = boto3.client("events")
    events.put_events(
        Entries=[{
            "Source": "myapp.orders",
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": os.environ["EVENT_BUS_NAME"],
        }]
    )
```

---

## 6.7 SAM (Serverless Application Model)

```yaml
# template.yaml — SAM template
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Serverless order processing API

Globals:
  Function:
    Runtime: python3.11
    Architectures: [arm64]
    Tracing: Active
    Layers:
      - !Ref PowertoolsLayer
    Environment:
      Variables:
        POWERTOOLS_SERVICE_NAME: orders
        LOG_LEVEL: INFO
    Tags:
      Environment: !Ref Environment

Parameters:
  Environment:
    Type: String
    Default: dev

Resources:
  OrdersFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub 'orders-api-${Environment}'
      Handler: app.handler
      CodeUri: src/api/
      MemorySize: 512
      Timeout: 29
      Environment:
        Variables:
          ORDERS_TABLE: !Ref OrdersTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
      Events:
        ApiEvent:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /{proxy+}
            Method: ANY

  HttpApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      Name: !Sub 'orders-${Environment}'
      CorsConfiguration:
        AllowMethods: ["*"]
        AllowHeaders: ["*"]
        AllowOrigins: ["*"]

  OrdersTable:
    Type: AWS::Serverless::SimpleTable
    Properties:
      PrimaryKey:
        Name: PK
        Type: String
      TableName: !Sub 'orders-${Environment}'

  PowertoolsLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: aws-lambda-powertools
      ContentUri: layers/powertools/
      CompatibleRuntimes: [python3.11]
      CompatibleArchitectures: [arm64]
    Metadata:
      BuildMethod: python3.11
```

```bash
# SAM commands
sam build
sam local invoke OrdersFunction --event events/test-event.json
sam local start-api --port 3000
sam deploy --guided
sam deploy --stack-name orders-prod --parameter-overrides Environment=prod
```

---

## 6.8 Interview Q&A

**Q: How do you minimize Lambda cold starts?**
A: (1) **Reduce package size** — use Lambda Layers for large dependencies, import only needed modules (not `import boto3` if only using S3 — import just `from boto3 import client`); (2) **Provisioned Concurrency** — pre-warms containers, eliminates cold starts entirely but costs money; (3) **SnapStart** (Java only) — snapshots initialized JVM state; (4) **Use Python/Node.js** — faster cold starts than Java/Go; (5) **Optimize init code** — move heavy initialization outside handler but keep it lightweight; (6) **arm64 (Graviton)** — comparable cold start to x86 but cheaper and often faster; (7) **Keep Lambda warm** — schedule EventBridge ping every 5 minutes (hacky but effective for single function).

**Q: What is the difference between Lambda concurrency types?**
A: **Reserved Concurrency**: Sets the max concurrent executions for a function. Guarantees capacity (other functions can't use it) but also throttles the function at that limit. **Provisioned Concurrency**: Pre-initializes execution environments to eliminate cold starts. More expensive. **Unreserved Concurrency**: The account-level default pool (1000 per region by default). If you don't set reserved concurrency, your function uses from the pool. A function without reserved concurrency can consume the entire pool, starving other functions — use reserved concurrency to isolate critical functions. Provisioned concurrency is charged per GB-hour even when not invoked.

**Q: How does Lambda handle SQS failures and what is partial batch failure?**
A: Without partial batch failure: if processing item #5 of 10 fails, Lambda retries the entire batch — items 1-4 get reprocessed (duplication). **Partial batch failure** (`ReportBatchItemFailures`) allows returning which specific items failed: `{"batchItemFailures": [{"itemIdentifier": "messageId"}]}`. Only failed items are retried. Best practice: use `aws_lambda_powertools`' `BatchProcessor` which handles this automatically. After `maxReceiveCount` retries, messages go to the Dead Letter Queue. Always set a DLQ on SQS queues used with Lambda — without it, failed messages are lost after max retries.
