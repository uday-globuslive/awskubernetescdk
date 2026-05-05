# Chapter 12: Serverless, Containers & Messaging

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 4**: Deployment, Provisioning, and Automation (18%)
- Lambda, ECS, EKS, SQS, SNS, Kinesis — increasingly tested on SysOps

---

## 12.1 AWS Lambda — Serverless Compute

Lambda runs code **without provisioning servers**. You pay only for execution time (GB-seconds).

### Lambda Execution Model
```
Event Source → Lambda Service → Execution Environment (Container)
                                    │
                                    ├── Init Phase (cold start):
                                    │   - Download code/layer
                                    │   - Start runtime
                                    │   - Run init code (outside handler)
                                    │
                                    └── Invoke Phase (warm):
                                        - Run handler function
```

### Cold Start Mitigation
```python
# ✅ Best practice: initialize outside handler (runs once per container lifecycle)
import boto3
import json
import os

# These run during Init phase — reused for warm invocations
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
ssm_client = boto3.client('ssm')

# Pre-load config at init time
def _load_config():
    response = ssm_client.get_parameters_by_path(
        Path='/production/app/',
        WithDecryption=True
    )
    return {p['Name'].split('/')[-1]: p['Value'] for p in response['Parameters']}

config = _load_config()  # Only runs once per container

def lambda_handler(event, context):
    """This runs on every invocation — keep it lean."""
    
    # ✅ Reuse initialized resources
    result = table.get_item(Key={'id': event['itemId']})
    
    return {
        'statusCode': 200,
        'body': json.dumps(result.get('Item', {}))
    }
```

### Lambda Concurrency

```
┌─────────────────────────────────────────────────────────────┐
│                  LAMBDA CONCURRENCY                          │
│                                                             │
│  Account Limit: 1000 concurrent executions (default)       │
│                                                             │
│  Reserved Concurrency:                                      │
│  - Guarantees capacity for a function                       │
│  - Also acts as a throttle (max for that function)          │
│  aws lambda put-function-concurrency --reserved 100        │
│                                                             │
│  Provisioned Concurrency:                                   │
│  - Pre-initialized execution environments                   │
│  - Eliminates cold starts                                   │
│  - Costs more (billed for idle time)                        │
│  aws lambda put-provisioned-concurrency-config --count 10  │
│                                                             │
│  Throttling: When limit hit → Lambda returns 429           │
│  (Sync invocations fail; Async retries 2x, then DLQ)      │
└─────────────────────────────────────────────────────────────┘
```

```bash
# Set reserved concurrency
aws lambda put-function-concurrency \
  --function-name critical-api \
  --reserved-concurrent-executions 200

# Provisioned concurrency on a specific version/alias
aws lambda put-provisioned-concurrency-config \
  --function-name critical-api \
  --qualifier production \
  --provisioned-concurrent-executions 10

# Monitor throttles
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=critical-api \
  --start-time $(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

### Lambda Error Handling & Destinations
```python
# Lambda with proper error handling
import json
import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
    try:
        logger.info("Processing event", extra={"event": event})
        
        result = process_order(event['orderId'])
        
        metrics.add_metric(name="OrdersProcessed", unit=MetricUnit.Count, value=1)
        
        return {'status': 'success', 'orderId': result['id']}
    
    except ValueError as e:
        # Client error — don't retry
        logger.warning(f"Invalid input: {e}")
        raise  # Lambda will NOT retry this for async invocations
    
    except Exception as e:
        # Server error — should retry
        logger.error(f"Processing failed: {e}", exc_info=True)
        metrics.add_metric(name="OrderProcessingErrors", unit=MetricUnit.Count, value=1)
        raise
```

```bash
# Configure async destinations (on-success and on-failure)
aws lambda put-function-event-invoke-config \
  --function-name order-processor \
  --maximum-retry-attempts 2 \
  --maximum-event-age-in-seconds 3600 \
  --destination-config '{
    "OnSuccess": {
      "Destination": "arn:aws:sqs:us-east-1:123456789012:order-success-queue"
    },
    "OnFailure": {
      "Destination": "arn:aws:sqs:us-east-1:123456789012:order-dlq"
    }
  }'
```

### Lambda Layers
```bash
# Create a layer for common dependencies
cd my-layer
pip install requests boto3 psycopg2-binary -t python/
zip -r layer.zip python/

aws lambda publish-layer-version \
  --layer-name common-dependencies \
  --description "Common Python dependencies" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.9 python3.10 python3.11 \
  --compatible-architectures x86_64 arm64

# Attach layer to function
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:common-dependencies:1
```

---

## 12.2 API Gateway

### REST API vs HTTP API vs WebSocket API

| Feature | REST API | HTTP API | WebSocket API |
|---------|---------|---------|---------------|
| **Cost** | $3.50/M | $1.00/M | $1.00/M + $0.25/M msgs |
| **Latency** | Higher | Lower | N/A |
| **Features** | Full | Subset | Real-time |
| **Caching** | Yes | No | No |
| **WAF** | Yes | No | No |
| **Request/Response Transform** | Yes | Limited | Yes |
| **Use Case** | Complex APIs, caching | Simple/fast APIs | Chat, live updates |

```bash
# Create an HTTP API with Lambda integration
aws apigatewayv2 create-api \
  --name my-http-api \
  --protocol-type HTTP \
  --cors-configuration '{
    "AllowOrigins": ["https://example.com"],
    "AllowMethods": ["GET","POST","PUT","DELETE"],
    "AllowHeaders": ["Content-Type","Authorization"]
  }'

# Add Lambda route
aws apigatewayv2 create-integration \
  --api-id API_ID \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:123456789012:function:my-api \
  --payload-format-version 2.0

aws apigatewayv2 create-route \
  --api-id API_ID \
  --route-key 'ANY /api/{proxy+}' \
  --target integrations/INTEGRATION_ID

# Deploy
aws apigatewayv2 create-stage \
  --api-id API_ID \
  --stage-name production \
  --auto-deploy

# Enable throttling
aws apigatewayv2 update-stage \
  --api-id API_ID \
  --stage-name production \
  --default-route-settings \
    ThrottlingBurstLimit=100,ThrottlingRateLimit=50
```

---

## 12.3 Amazon ECS — Elastic Container Service

### ECS Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    ECS CLUSTER                               │
│                                                             │
│  Fargate Launch Type          EC2 Launch Type               │
│  ┌─────────────────┐          ┌─────────────────────────┐   │
│  │ Task 1          │          │ EC2 Instance (with ECS  │   │
│  │ ┌─────────────┐ │          │  agent installed)       │   │
│  │ │ Container 1 │ │          │ ┌───────┐  ┌───────┐   │   │
│  │ │ Container 2 │ │          │ │Task 1 │  │Task 2 │   │   │
│  │ └─────────────┘ │          │ └───────┘  └───────┘   │   │
│  └─────────────────┘          └─────────────────────────┘   │
│                                                             │
│  SERVICE: Maintains desired count of tasks                  │
│  TASK DEFINITION: Container specs (image, CPU, memory,      │
│                   env vars, volumes, port mappings)         │
└─────────────────────────────────────────────────────────────┘
```

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name production \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=3

# Create task definition
aws ecs register-task-definition \
  --family my-api \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn arn:aws:iam::123456789012:role/ecsTaskExecutionRole \
  --task-role-arn arn:aws:iam::123456789012:role/ecsTaskRole \
  --container-definitions '[{
    "name": "api",
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:v1.2.3",
    "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
    "environment": [
      {"name": "ENVIRONMENT", "value": "production"}
    ],
    "secrets": [
      {
        "name": "DB_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/db-password"
      }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/production/api",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 60
    }
  }]'

# Create ECS service with ALB integration
aws ecs create-service \
  --cluster production \
  --service-name api-service \
  --task-definition my-api:1 \
  --desired-count 4 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-app-az1","subnet-app-az2"],
      "securityGroups": ["sg-ecs-app"],
      "assignPublicIp": "DISABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "arn:aws:elasticloadbalancing:...",
    "containerName": "api",
    "containerPort": 8000
  }]' \
  --deployment-configuration '{
    "minimumHealthyPercent": 50,
    "maximumPercent": 200,
    "deploymentCircuitBreaker": {"enable": true, "rollback": true}
  }' \
  --enable-execute-command  # ECS Exec (like SSM Session Manager for containers)
```

### ECS Exec (Debug running containers)
```bash
# Get a shell in a running ECS task
aws ecs execute-command \
  --cluster production \
  --task TASK_ARN \
  --container api \
  --interactive \
  --command "/bin/bash"
```

---

## 12.4 Amazon ECR — Elastic Container Registry

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository \
  --repository-name my-api \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS

# Build and push image
docker build -t my-api .
docker tag my-api:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:v1.2.3
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-api:v1.2.3

# Set lifecycle policy (keep only last 10 images per tag prefix)
aws ecr put-lifecycle-policy \
  --repository-name my-api \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 production images",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["v"],
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {"type": "expire"}
    },{
      "rulePriority": 2,
      "description": "Remove untagged after 1 day",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 1
      },
      "action": {"type": "expire"}
    }]
  }'
```

---

## 12.5 Amazon SQS — Simple Queue Service

SQS is a **managed message queue** for decoupling services.

### SQS Queue Types

| Feature | Standard | FIFO |
|---------|---------|------|
| **Throughput** | Unlimited | 300 msg/sec (3000 with batching) |
| **Ordering** | Best-effort | Strict FIFO |
| **Delivery** | At-least-once | Exactly-once |
| **Deduplication** | No | Yes (5-minute window) |
| **Use Case** | Scale, decouple | Financial, inventory |

### SQS Key Concepts
```
Visibility Timeout: Time message is hidden after consumer receives it
                   (consumer must delete before timeout or message re-appears)

Message Retention: 1 minute to 14 days (default 4 days)

Dead-Letter Queue (DLQ): Receives messages that fail processing N times
  → Set maxReceiveCount on source queue's redrive policy

Long Polling: Wait up to 20 seconds for messages (reduces empty calls)
  → Always use WaitTimeSeconds=20

Message Groups (FIFO): Messages with same MessageGroupId processed in order
```

```bash
# Create SQS queue with DLQ
DLQ_ARN=$(aws sqs create-queue \
  --queue-name orders-dlq \
  --attributes MessageRetentionPeriod=1209600 \  # 14 days
  --query QueueUrl --output text | \
  xargs aws sqs get-queue-attributes \
    --attribute-names QueueArn \
    --query Attributes.QueueArn --output text)

aws sqs create-queue \
  --queue-name orders-queue \
  --attributes '{
    "VisibilityTimeout": "60",
    "MessageRetentionPeriod": "86400",
    "ReceiveMessageWaitTimeSeconds": "20",
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":\"3\"}"
  }'

# Create FIFO queue
aws sqs create-queue \
  --queue-name payments.fifo \
  --attributes '{
    "FifoQueue": "true",
    "ContentBasedDeduplication": "true",
    "VisibilityTimeout": "30"
  }'

# Send message
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/orders-queue \
  --message-body '{"orderId": "ORD-001", "amount": 99.99}' \
  --message-attributes '{"OrderType":{"DataType":"String","StringValue":"premium"}}'

# Receive and process
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/orders-queue \
  --wait-time-seconds 20 \
  --max-number-of-messages 10 \
  --message-attribute-names All
```

### SQS Consumer in Python
```python
import boto3
import json
import logging

sqs = boto3.client('sqs')
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/orders-queue'

def process_messages():
    """Long-polling message consumer."""
    
    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,      # Long polling
            VisibilityTimeout=60,    # Time to process
            MessageAttributeNames=['All']
        )
        
        messages = response.get('Messages', [])
        
        for message in messages:
            try:
                body = json.loads(message['Body'])
                
                # Process the message
                process_order(body['orderId'])
                
                # Delete only on success
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
                logging.info(f"Processed order: {body['orderId']}")
                
            except Exception as e:
                logging.error(f"Failed to process message: {e}")
                # Don't delete — message will reappear after visibility timeout
                # After maxReceiveCount retries, goes to DLQ
```

---

## 12.6 Amazon SNS — Simple Notification Service

SNS is a **pub/sub messaging** service — publish once, deliver to multiple subscribers.

### SNS Fan-Out Pattern
```
         SNS Topic
              │
    ┌─────────┼─────────┐
    │         │         │
   SQS       SQS     Lambda
  Queue 1   Queue 2  (real-time)
  (email)   (analytics) (processing)
```

```bash
# Create SNS topic
aws sns create-topic --name order-events

# Subscribe SQS queue to SNS topic (fan-out)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:123456789012:orders-email-queue

# Subscribe Lambda
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456789012:function:OrderProcessor

# Subscribe email (human notification)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:order-events \
  --protocol email \
  --notification-endpoint ops@example.com

# Publish message
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:order-events \
  --message '{"orderId":"ORD-001","status":"confirmed"}' \
  --message-attributes '{"eventType":{"DataType":"String","StringValue":"OrderConfirmed"}}'

# SNS filter policy (subscriber only gets matching messages)
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:... \
  --attribute-name FilterPolicy \
  --attribute-value '{"eventType": ["OrderConfirmed", "OrderShipped"]}'
```

---

## 12.7 Amazon Kinesis

For **real-time streaming data** at high throughput.

### Kinesis Services Comparison

| Service | Use Case | Throughput |
|---------|---------|-----------|
| **Data Streams** | Real-time custom processing | 1MB/shard/sec in, 2MB/shard/sec out |
| **Data Firehose** | Load streaming data to S3/Redshift/OpenSearch | Auto-scaling |
| **Data Analytics** | Real-time SQL on streaming data | Auto-scaling |

```
SQS vs Kinesis:
  SQS: Message queue — each message processed by ONE consumer
  Kinesis: Data stream — ALL consumer groups see ALL messages
           Multiple apps can read from same stream independently
```

```bash
# Create Kinesis Data Stream
aws kinesis create-stream \
  --stream-name clickstream-events \
  --shard-count 4  # Each shard: 1MB/s write, 2MB/s read

# Put records
aws kinesis put-records \
  --stream-name clickstream-events \
  --records '[
    {
      "Data": "eyJ1c2VySWQiOiAiVTAwMSJ9",
      "PartitionKey": "U001"
    }
  ]'

# Create Firehose delivery stream (stream to S3)
aws firehose create-delivery-stream \
  --delivery-stream-name clickstream-to-s3 \
  --kinesis-stream-source-configuration '{
    "KinesisStreamARN": "arn:aws:kinesis:us-east-1:123456789012:stream/clickstream-events",
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseRole"
  }' \
  --s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseRole",
    "BucketARN": "arn:aws:s3:::clickstream-data-lake",
    "Prefix": "year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "ErrorOutputPrefix": "errors/",
    "BufferingHints": {"SizeInMBs": 128, "IntervalInSeconds": 300},
    "CompressionFormat": "GZIP"
  }'
```

### Python Kinesis Producer
```python
import boto3
import json
import uuid

kinesis = boto3.client('kinesis')

def publish_event(stream_name: str, partition_key: str, data: dict):
    """Publish event to Kinesis with retry."""
    kinesis.put_record(
        StreamName=stream_name,
        Data=json.dumps(data),
        PartitionKey=partition_key  # Determines which shard (keep high cardinality)
    )

# Batch publish for higher throughput
def publish_events_batch(stream_name: str, events: list):
    """Publish multiple events in one API call (max 500 records, 5MB)."""
    records = [
        {
            'Data': json.dumps(event),
            'PartitionKey': event.get('userId', str(uuid.uuid4()))
        }
        for event in events
    ]
    
    response = kinesis.put_records(
        StreamName=stream_name,
        Records=records
    )
    
    if response['FailedRecordCount'] > 0:
        # Handle failed records
        for i, record in enumerate(response['Records']):
            if 'ErrorCode' in record:
                print(f"Failed: {records[i]} — {record['ErrorMessage']}")
```

---

## 12.8 Real-World Project: Event-Driven Order Processing

### Architecture
```
Client → API Gateway → Lambda (order-api)
                              │
                              ▼
                        SQS (orders-queue)
                              │
                              ▼
                     Lambda (order-processor)
                     ├─► DynamoDB (orders table)
                     ├─► SNS (order-events topic)
                     │     ├─► SQS (email-queue) → Lambda (send-email)
                     │     └─► SQS (analytics-queue) → Lambda (analytics)
                     └─► Kinesis (audit-stream) → Firehose → S3
```

```python
# order-api Lambda
import boto3
import json
import uuid

sqs = boto3.client('sqs')
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/orders-queue'

def lambda_handler(event, context):
    body = json.loads(event['body'])
    
    order = {
        'orderId': str(uuid.uuid4()),
        'customerId': body['customerId'],
        'items': body['items'],
        'total': body['total'],
        'status': 'pending'
    }
    
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(order),
        MessageGroupId=body['customerId'],  # FIFO by customer
        MessageDeduplicationId=order['orderId']
    )
    
    return {
        'statusCode': 202,
        'body': json.dumps({'orderId': order['orderId'], 'status': 'accepted'})
    }
```

```python
# order-processor Lambda (triggered by SQS)
import boto3
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
table = dynamodb.Table('orders')

def lambda_handler(event, context):
    """Process orders from SQS — handles batch of messages."""
    
    batch_item_failures = []
    
    for record in event['Records']:
        try:
            order = json.loads(record['body'])
            
            # Save to DynamoDB
            table.put_item(Item={
                **order,
                'total': Decimal(str(order['total'])),
                'status': 'processing'
            })
            
            # Notify via SNS
            sns.publish(
                TopicArn='arn:aws:sns:us-east-1:123456789012:order-events',
                Message=json.dumps(order),
                MessageAttributes={
                    'eventType': {'DataType': 'String', 'StringValue': 'OrderProcessed'}
                }
            )
            
        except Exception as e:
            print(f"Failed to process {record['messageId']}: {e}")
            batch_item_failures.append({'itemIdentifier': record['messageId']})
    
    # Report partial batch failures (allows retry only failed messages)
    return {'batchItemFailures': batch_item_failures}
```

---

## 12.9 Practice Questions (SysOps Exam Level)

**Q1:** A Lambda function processes SQS messages and fails 30% of the time due to a bug in the code. The messages keep reappearing in the queue and the same messages are failing. What should you do?

**A:**
1. **Immediate**: Fix the code bug
2. **Configure DLQ** on the SQS queue with `maxReceiveCount=3` — failed messages after 3 attempts go to DLQ
3. **Monitor DLQ** with CloudWatch alarm to detect issues early
4. **Implement partial batch response** in Lambda to only fail the specific message, not the whole batch

---

**Q2:** Your ECS Fargate tasks need to call S3 and DynamoDB. What is the most secure way to grant permissions?

**A:** Use an **ECS Task IAM Role** (not instance role, not hardcoded credentials):

```bash
# Create task role
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"ecs-tasks.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name ecsTaskRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Reference in task definition
# "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole"
```

---

**Q3:** How is Amazon Kinesis different from SQS?

**A:**

| | SQS | Kinesis |
|---|---|---|
| Delivery | Each message to ONE consumer | All consumers read same data |
| Retention | Up to 14 days | 24 hours default, up to 7 days (or 365 with extended) |
| Ordering | FIFO queue only | Per shard (partition key) |
| Replay | No (message deleted after processing) | Yes (seek to any offset) |
| Throughput | Unlimited | 1MB/shard/sec |
| Use Case | Task queue, decoupling | Real-time analytics, audit log |

---

**Q4:** Lambda function invocations are failing with timeout errors. The function has a 3-second timeout. What should you check?

**A:**
1. **Increase timeout** if legitimate (up to 15 minutes)
2. **Check VPC**: If Lambda is in a VPC without NAT Gateway, it can't reach internet services
3. **Check external dependencies**: Database, API calls that are slow
4. **Add X-Ray tracing** to identify where time is spent
5. **Connection pooling**: Are you creating new DB connections on each invocation?

```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name my-function \
  --timeout 30

# Enable X-Ray tracing
aws lambda update-function-configuration \
  --function-name my-function \
  --tracing-config Mode=Active
```

---

**Q5:** You have 1000 messages in an SQS queue. Each message takes 5 seconds to process. You need to process all messages in 30 minutes. How?

**A:**
- Need concurrent processing: 1000 messages / 30 min = ~33 messages/min ≈ 3 messages/min × ~11 concurrent workers
- Use **Lambda with SQS trigger** — Lambda scales concurrency automatically
- Set **batch size** to 10 (process 10 messages per Lambda invocation)
- Set **concurrency**: 1000 messages / 10 per invocation × 5 sec each = ~8 concurrent Lambda needed
- Lambda scales automatically — 1000 messages will likely finish well within 30 min

```bash
aws lambda create-event-source-mapping \
  --function-name message-processor \
  --event-source-arn arn:aws:sqs:us-east-1:123456789012:jobs-queue \
  --batch-size 10 \
  --function-response-types ReportBatchItemFailures
```

---

## Key Serverless & Messaging Terms for Exam

| Term | Definition |
|------|-----------|
| Lambda Cold Start | Initialization time when new container created |
| Reserved Concurrency | Max concurrent executions for one function |
| Provisioned Concurrency | Pre-initialized containers (no cold start) |
| Lambda Layers | Shared code/dependencies across functions |
| Lambda Destination | Target for async success/failure outcomes |
| ECS | Elastic Container Service — managed container orchestration |
| Task Definition | Container spec (image, CPU, memory, env, ports) |
| ECS Service | Maintains desired task count, integrates with ALB |
| Fargate | Serverless compute for containers (no EC2 to manage) |
| ECS Exec | Get terminal access to running container |
| ECR | Elastic Container Registry — Docker image storage |
| SQS | Simple Queue Service — message queue for decoupling |
| Visibility Timeout | Time message hidden after receipt (process or requeue) |
| Dead-Letter Queue | Receives messages that fail after maxReceiveCount |
| Long Polling | Wait up to 20s for messages (reduces empty API calls) |
| SNS | Simple Notification Service — pub/sub message bus |
| SNS Filter Policy | Subscriber receives only matching messages |
| Kinesis Data Streams | Real-time data stream (multiple consumers) |
| Kinesis Firehose | Load streaming data to S3/Redshift/OpenSearch |
| Shard | Unit of capacity in Kinesis (1MB/s in, 2MB/s out) |
| Partition Key | Determines which Kinesis shard receives the record |
