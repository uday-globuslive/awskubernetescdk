
content = r"""# Chapter 12: Serverless, Containers & Messaging
## (Modern Application Architectures)

---

## 12.1 Introduction: The Shift Toward Serverless

### The Evolution of Computing

```
                        Traditional          Containers        Serverless
                        (EC2)                (ECS/EKS)         (Lambda)
                        
You manage:
  OS patching          YES                  Partial           NO
  Runtime updates      YES                  Partial           NO
  Capacity planning    YES                  Partial           NO
  Scaling config       YES                  YES               NO (auto)
  Server provisioning  YES                  YES               NO
  
You focus on:          Managing servers     Managing clusters  Just code

Cost model:            Pay/hour running     Pay/hour running  Pay/invocation
                       (even when idle)     (even when idle)  (no idle cost)
                       
Best for:              Full control,        Microservices,    Event-driven,
                       stateful apps,       complex apps,     APIs, automation,
                       databases            DevOps teams      short-lived tasks
```

---

## 12.2 AWS Lambda — Serverless Functions

### What is Lambda?

**Lambda** lets you run code without managing servers. You upload a function, and Lambda runs it in response to events.

**Analogy:** Lambda is like a vending machine. You don't need to staff the vending machine (no server to manage). When someone presses a button (event occurs), the machine automatically dispenses the item (runs your code) and charges only for that transaction (per-invocation pricing). When nobody is using it, there is no cost.

### Lambda Execution Model

```
Event occurs:
  API Gateway receives HTTP request
  S3 object uploaded
  DynamoDB table changed
  SQS message arrives
  CloudWatch alarm triggers
  EventBridge schedule fires
  SNS notification sent
             │
             ▼
  Lambda service receives event
             │
             ▼
  Is there a warm container available? ─── YES → Reuse container (fast!)
             │                                    Execute function (~1ms overhead)
             NO
             │
             ▼
  Cold start: Download code (one-time)
              Initialize runtime (Python/Node/Java)
              Initialize function (database connections, imports)
              Execute function
              
  Cold start overhead:
    Python/Node.js: 100-500ms extra
    Java/C# (.NET): 1-10 seconds extra
    
  After execution: Container stays warm for ~15 minutes
  Next invocation within 15 min: No cold start
  After 15 min idle: Container recycled → next call gets cold start
```

### Lambda Configuration

```
Memory:      128 MB – 10,240 MB (10 GB)
             More memory = more CPU (they scale together!)
             
Timeout:     Maximum 15 minutes
             Default: 3 seconds (increase for long-running tasks)
             
Storage:     /tmp directory: 512 MB – 10,240 MB temporary storage
             Cleared between invocations (cannot use for persistent storage)
             
Concurrency: Default: 1,000 concurrent executions per account per region
             Reserve concurrency: Guarantee capacity for critical functions
             Provision concurrency: Pre-warm containers to eliminate cold start
             
Cost:        $0.0000000021 per GB-millisecond
             $0.20 per 1 million requests
             First 1 million requests/month FREE
             
Math example:
  Function: 512 MB memory, runs 100ms average
  Invocations: 1 million/month
  
  Compute cost: 1,000,000 × 0.512 GB × 0.1s × $0.0000166667/GB-s = $0.85/month
  Request cost: 1,000,000 × $0.0000002 = $0.20/month
  Total: ~$1.05/month for 1 million executions!
```

### Lambda Function Example

```python
import json
import boto3
import os
from datetime import datetime

# Initialize outside handler = reused across warm invocations (cost savings!)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    # context.remaining_time_in_millis() → how long before timeout
    # context.function_name → name of this Lambda function
    
    # Process API Gateway event
    http_method = event['httpMethod']
    path = event['path']
    
    if http_method == 'GET' and path == '/users':
        return get_users()
    elif http_method == 'POST' and path == '/users':
        body = json.loads(event['body'])
        return create_user(body)
    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not found'})
        }

def get_users():
    response = table.scan(Limit=100)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response['Items'])
    }

def create_user(user_data):
    user_data['created_at'] = datetime.utcnow().isoformat()
    table.put_item(Item=user_data)
    return {
        'statusCode': 201,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'User created', 'user': user_data})
    }
```

### Lambda Triggers — What Can Invoke Lambda

```bash
# Common Lambda event sources:

# 1. API Gateway (HTTP requests → Lambda)
#    REST API, HTTP API, WebSocket API
#    Every HTTP request invokes Lambda function

# 2. S3 events (file uploads → Lambda)
#    ObjectCreated, ObjectDeleted, ObjectTagged
#    Example: Resize uploaded images automatically

# 3. DynamoDB Streams (table changes → Lambda)
#    INSERT, MODIFY, REMOVE events
#    Example: Keep ElasticSearch in sync with DynamoDB

# 4. SQS (queue messages → Lambda)
#    Lambda polls SQS, invokes function with batches
#    Example: Process orders from a queue

# 5. SNS (notifications → Lambda)
#    Fan-out pattern: SNS → multiple Lambda subscriptions
#    Example: Send email AND log to database

# 6. EventBridge (scheduled and event-driven)
#    Schedule: "Run every Monday 9am" → Lambda
#    Event pattern: "EC2 instance started" → Lambda

# 7. CloudWatch Logs (log data → Lambda)
#    Process log data, filter errors, forward to SIEM

# Deploy Lambda function
aws lambda create-function \
  --function-name process-image-upload \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/LambdaExecutionRole \
  --handler main.handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables='{TABLE_NAME=users,BUCKET_NAME=images}' \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:PIL:3

# Enable S3 trigger
aws lambda add-permission \
  --function-name process-image-upload \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::upload-bucket \
  --source-account 123456789012

aws s3api put-bucket-notification-configuration \
  --bucket upload-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:process-image-upload",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [{"Name": "suffix", "Value": ".jpg"}]
        }
      }
    }]
  }'
```

### Lambda Layers — Sharing Code Between Functions

**Layers** let you package common dependencies (libraries, shared code) separately from your function code.

```bash
# Create a layer with Python dependencies
mkdir -p layer/python
pip install boto3 requests pillow -t layer/python/
cd layer
zip -r layer.zip python/

# Publish the layer
aws lambda publish-layer-version \
  --layer-name common-python-libs \
  --description "Common Python dependencies" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11 python3.12

# Attach layer to function
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:common-python-libs:3
```

---

## 12.3 Amazon ECS — Elastic Container Service

### What are Containers?

**Containers** package your application code with all its dependencies (libraries, config) into a portable, consistent unit.

**Problem without containers:**
```
Developer's laptop:  Python 3.9, Library v2.1 → Works!
Staging server:      Python 3.7, Library v1.8 → Breaks!
Production server:   Python 3.11, Library v2.0 → Sometimes works?

"It works on my machine!" — every developer, ever
```

**With containers:**
```
Container image: Python 3.9 + Library v2.1 + Your Code
                 Always runs the same, everywhere
                 
Developer laptop:  docker run my-app → Works!
Staging server:    docker run my-app → Works identically!
Production server: docker run my-app → Works identically!
```

### ECS Launch Types

**ECS with Fargate (Serverless Containers):**
```
You define: CPU, Memory, container image
AWS manages: The servers running your containers

No EC2 instances to manage!
Pay per vCPU/hour and GB memory/hour
Perfect for: variable workloads, microservices, batch jobs
```

**ECS with EC2 (You manage the servers):**
```
You define: EC2 instance type, instance count (the cluster)
You manage: EC2 instances (patching, scaling the cluster)
AWS manages: Container placement on instances

More control, lower cost at large scale
Perfect for: predictable workloads, GPU containers, custom config
```

```bash
# Create ECS cluster (Fargate)
aws ecs create-cluster \
  --cluster-name production-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=3

# Register a task definition (what to run)
aws ecs register-task-definition \
  --family web-app \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn arn:aws:iam::123456789012:role/ecsTaskExecutionRole \
  --task-role-arn arn:aws:iam::123456789012:role/ecsTaskRole \
  --container-definitions '[{
    "name": "web",
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest",
    "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
    "essential": true,
    "environment": [
      {"name": "NODE_ENV", "value": "production"}
    ],
    "secrets": [
      {"name": "DB_PASSWORD", "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/prod/db/password"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/web-app",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "web"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3
    }
  }]'

# Create a service (keep N tasks running, register with load balancer)
aws ecs create-service \
  --cluster production-cluster \
  --service-name web-app-service \
  --task-definition web-app:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-private1", "subnet-private2"],
      "securityGroups": ["sg-app"],
      "assignPublicIp": "DISABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:...",
    "containerName": "web",
    "containerPort": 8080
  }]'
```

### Amazon ECR — Elastic Container Registry

**ECR** is AWS's private container image registry (like Docker Hub, but private and integrated with IAM).

```bash
# Authenticate Docker with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository \
  --repository-name my-app \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS

# Build, tag, and push Docker image
docker build -t my-app:latest .
docker tag my-app:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Set lifecycle policy (delete old images to reduce storage costs)
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep only 5 tagged images",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["v"],
        "countType": "imageCountMoreThan",
        "countNumber": 5
      },
      "action": {"type": "expire"}
    }]
  }'
```

---

## 12.4 Amazon SQS — Simple Queue Service

### What is a Queue?

**Analogy:** SQS is like a to-do list between two people. Person A writes tasks on sticky notes and puts them on the list. Person B picks up and completes tasks at their own pace. A doesn't need to wait for B to finish — they just leave the note and move on.

**Why use a queue?**
```
WITHOUT SQS (direct call):
  Web server → directly calls → Order processor
  
  Problem 1: If Order processor is down, orders are LOST
  Problem 2: If traffic spikes, Order processor gets overwhelmed
  Problem 3: Web server waits for Order processor (slow response to user)

WITH SQS:
  Web server → puts message in SQS queue → returns immediately to user
              Order processor polls queue → processes at its own pace
              
  Benefit 1: Messages stored in SQS even if processor is down
  Benefit 2: Processor scales based on queue depth, not traffic spikes
  Benefit 3: Web server is fast (no waiting for processor)
```

### SQS Types

**Standard Queue:**
```
Delivery: At-least-once (rarely delivered more than once)
Ordering: Best-effort (nearly always in order, but not guaranteed)
Throughput: Nearly unlimited
Use for: Order processing, image processing, email sending
         (can handle occasional duplicate message processing)
```

**FIFO Queue:**
```
Delivery: Exactly-once (messages processed exactly once)
Ordering: First-In-First-Out (guaranteed strict ordering)
Throughput: 3,000 messages/second (with batching), 300 without
Use for: Financial transactions, booking systems, inventory updates
         (ordering and exactly-once processing is critical)
Name suffix: must end in .fifo
```

```bash
# Create a standard SQS queue
aws sqs create-queue \
  --queue-name order-processing-queue \
  --attributes '{
    "VisibilityTimeout": "300",
    "MessageRetentionPeriod": "86400",
    "ReceiveMessageWaitTimeSeconds": "20",
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:123456789012:order-processing-dlq\",\"maxReceiveCount\":\"3\"}"
  }'

# Create Dead Letter Queue (DLQ) first
aws sqs create-queue --queue-name order-processing-dlq

# Send a message
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-processing-queue \
  --message-body '{"order_id": "12345", "user_id": "user_abc", "items": [{"product": "Widget", "qty": 2}]}' \
  --message-attributes '{"priority": {"DataType": "String", "StringValue": "high"}}'

# Process messages (poll for messages)
QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/order-processing-queue"

# Long polling (more efficient — waits up to 20 seconds for messages)
aws sqs receive-message \
  --queue-url $QUEUE_URL \
  --max-number-of-messages 10 \
  --wait-time-seconds 20 \
  --visibility-timeout 300

# After processing successfully, delete the message
aws sqs delete-message \
  --queue-url $QUEUE_URL \
  --receipt-handle "AQEBxyz..."  # From receive-message response
```

### SQS Key Concepts

```
Visibility Timeout:
  After a consumer receives a message, it becomes "invisible" to other consumers
  If consumer processes and deletes → gone forever
  If consumer crashes before deleting → timeout expires → message reappears
  Timeout should be longer than your processing time!

Dead Letter Queue (DLQ):
  After maxReceiveCount failed attempts → message moved to DLQ
  DLQ lets you inspect failed messages without losing them
  Monitor DLQ depth with CloudWatch alarms

Long Polling vs Short Polling:
  Short: Returns immediately (even if no messages) → wastes API calls, costs money
  Long: Waits up to 20 seconds → much more efficient, reduces costs
  Always use long polling!

Message Retention:
  Default: 4 days
  Maximum: 14 days
  Messages not processed within retention period are deleted!
```

---

## 12.5 Amazon SNS — Simple Notification Service

### What is SNS?

**SNS (Simple Notification Service)** is a pub/sub messaging service. Publishers send messages to a topic; all subscribers receive the message.

**Analogy:** SNS is like a company-wide broadcast email. The CEO sends one email to the "All Employees" mailing list. Every employee receives their own copy. The CEO doesn't send individual emails to each person.

```
Publisher (1 message) → SNS Topic → Lambda Function 1 (processes order)
                                   → SQS Queue (archives for analytics)
                                   → Email (notifies team)
                                   → SMS (alerts on-call engineer)
                                   → HTTP/HTTPS endpoint (webhook)
                                   
This pattern is called "Fan-Out" — one message, many consumers
```

```bash
# Create an SNS topic
TOPIC_ARN=$(aws sns create-topic \
  --name order-events \
  --attributes DisplayName="Order Events" \
  --query 'TopicArn' --output text)

# Subscribe an email to the topic
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint ops-team@company.com

# Subscribe a Lambda function
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456789012:function:process-order

# Subscribe an SQS queue (fan-out: SNS → multiple SQS queues)
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:123456789012:order-analytics-queue

# Publish a message to all subscribers
aws sns publish \
  --topic-arn $TOPIC_ARN \
  --subject "New Order Placed" \
  --message '{"order_id": "12345", "amount": 99.99, "user_id": "user_abc"}' \
  --message-attributes '{
    "order_type": {"DataType": "String", "StringValue": "premium"}
  }'
```

---

## 12.6 Amazon Kinesis — Real-Time Data Streaming

### Kinesis vs SQS — When to Use Which

```
SQS (Queue):                         Kinesis (Stream):
  Message consumed → deleted           Data retained for 1-7 days
  Consumer processes "jobs"            Multiple consumers, each read independently
  Order processing, task queuing       Real-time analytics, log processing
  Throughput: unlimited (standard)     Throughput: 1 MB/s per shard
  Max message size: 256 KB             Max record size: 1 MB
  Message retention: up to 14 days     Data retention: 1-7 days
  Use: task queues, work distribution  Use: analytics, real-time dashboards
```

### Kinesis Data Streams

```bash
# Create a Kinesis Data Stream (2 shards = 2 MB/s write, 4 MB/s read)
aws kinesis create-stream \
  --stream-name application-events \
  --shard-count 2

# Send records to the stream
aws kinesis put-records \
  --stream-name application-events \
  --records '[
    {
      "Data": "eyJ1c2VyX2lkIjogIjEyMyIsICJldmVudCI6ICJwYWdlX3ZpZXcifQ==",
      "PartitionKey": "user-123"
    }
  ]'

# Kinesis Data Firehose (fully managed, no consumer code needed)
# Streams data to: S3, Redshift, OpenSearch, Splunk, HTTP endpoint
aws firehose create-delivery-stream \
  --delivery-stream-name app-logs-to-s3 \
  --delivery-stream-type KinesisStreamAsSource \
  --kinesis-stream-source-configuration '{
    "KinesisStreamARN": "arn:aws:kinesis:us-east-1:123456789012:stream/application-events",
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseRole"
  }' \
  --s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseRole",
    "BucketARN": "arn:aws:s3:::my-data-lake",
    "Prefix": "application-events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "BufferingHints": {"SizeInMBs": 128, "IntervalInSeconds": 300},
    "CompressionFormat": "GZIP"
  }'
```

---

## 12.7 Architecture Patterns

### Serverless API Pattern

```
Client Request
     │
     ▼
  Route 53 (DNS)
     │
     ▼
  CloudFront (CDN + HTTPS termination + WAF)
     │
     ▼
  API Gateway (routing, rate limiting, auth)
     │
     ├── GET /users → Lambda (read from DynamoDB)
     ├── POST /orders → Lambda (write to DynamoDB → SQS → email/SNS)
     └── GET /static/* → S3 bucket (static content)
     
Benefits:
  - Lambda scales to 0 (no idle cost)
  - Lambda scales to thousands automatically
  - No EC2 to manage or patch
  - Pay only for actual requests
```

### Event-Driven Microservices Pattern

```
Service A (Order Service)
     │
     │ Publishes: OrderPlaced event
     ▼
  SNS Topic (order-events)
     │
     ├─── SQS Queue ──► Service B (Inventory Service)
     │                   Decrements inventory
     │
     ├─── SQS Queue ──► Service C (Payment Service)  
     │                   Charges customer card
     │
     ├─── SQS Queue ──► Service D (Notification Service)
     │                   Sends confirmation email
     │
     └─── Kinesis ────► Analytics Service
                        Real-time dashboards

Benefits:
  - Services are completely decoupled
  - Failure of Service B doesn't affect C or D
  - Each service scales independently
  - Easy to add new services (just subscribe to SNS)
```

---

## 12.8 Practice Questions

**Q1:** Your Lambda function is timing out. Investigation shows the function waits 200ms for a DynamoDB response but your timeout is set to 3 seconds (default). You add more logic and the function now needs up to 8 seconds. What should you do?

- A) Increase Lambda timeout to 15 seconds and memory to 3008 MB
- B) Increase Lambda timeout to 10 seconds
- C) Rewrite the Lambda function in Java for speed
- D) Move to ECS containers instead

**Answer: B**

Explanation: Simply increase the timeout to accommodate your function's actual runtime. Lambda timeout can be set up to 15 minutes. Increasing memory (A) is also good for CPU-intensive work (memory and CPU scale together), but 3008 MB is too high for a DynamoDB I/O-bound function — 512 MB or 1024 MB would be more appropriate. The root cause is a timeout configuration issue, not a memory or language issue. Always set timeout slightly higher than worst-case execution time to handle occasional slow responses.

---

**Q2:** You process orders via a direct API call from your web app to your processing service. When the processing service has outages, orders are lost. What is the BEST fix?

- A) Add retry logic with exponential backoff in the web app
- B) Put an SQS queue between the web app and processing service
- C) Deploy the processing service in multiple AZs
- D) Use RDS to store orders temporarily

**Answer: B**

Explanation: An SQS queue decouples the web app from the processing service. When the web app receives an order, it puts a message in SQS and returns success to the user. The processing service reads from SQS when it is healthy. If the processing service is down, messages safely accumulate in SQS (up to 14 days). When the service recovers, it processes the backlog. This is the fundamental benefit of message queuing: durability and decoupling. Retry logic (A) doesn't help if the processing service is down for hours — the web app would exhaust retries and still lose orders.

---

**Q3:** You have 5 services that all need to react when a new user registers: send welcome email, create analytics record, provision a trial account, log to audit system, sync to CRM. What messaging pattern should you use?

- A) Each service calls the next in a chain
- B) SNS topic with 5 SQS queue subscribers (fan-out pattern)
- C) One large Lambda function that calls all 5 operations
- D) Direct API calls from registration service to all 5 services

**Answer: B**

Explanation: The fan-out pattern using SNS + SQS is ideal for this scenario: (1) Registration service publishes one message to SNS topic. (2) SNS delivers to 5 SQS queues (one per service). (3) Each service processes its own SQS queue independently. Benefits: Each service is independent (failure of email service doesn't affect analytics). Each service scales independently. Adding a 6th service is just adding a subscription. Compared to a chain (A) or monolithic Lambda (C), services are fully decoupled and failure-isolated.

---

**Q4:** You are processing financial transactions that must be processed in the exact order received and must not be processed twice. Which SQS type should you use?

- A) Standard SQS queue
- B) SQS FIFO queue
- C) Standard SQS with deduplication at application level
- D) Kinesis Data Stream

**Answer: B**

Explanation: SQS FIFO queues provide: (1) FIFO ordering — messages processed in exact order they were sent. (2) Exactly-once processing — content-based deduplication prevents duplicate processing. This is critical for financial transactions where processing a payment twice or out of order would cause errors. Standard SQS (A) provides best-effort ordering and at-least-once delivery — not suitable for financial transactions. While (C) could work technically, it adds complexity and risk to your application code.

---

**Q5:** Your Lambda function is cold-starting too slowly (5 seconds) because it connects to a database and loads models during initialization. Users experience 5-second delays. What is the BEST solution?

- A) Switch to Fargate containers instead of Lambda
- B) Use Lambda Provisioned Concurrency to pre-warm containers
- C) Increase Lambda memory to 10 GB
- D) Rewrite in Rust for faster startup

**Answer: B**

Explanation: Lambda Provisioned Concurrency pre-initializes a specified number of Lambda execution environments, keeping them always-warm. When requests arrive, they are handled without cold start latency. For latency-sensitive APIs with unpredictable traffic patterns, Provisioned Concurrency is the correct solution. It has an additional cost (you pay for the pre-warmed instances even when idle), but for critical user-facing APIs, the improved UX justifies it. Increasing memory (C) reduces execution time but doesn't eliminate cold start. Fargate (A) adds operational complexity.

---

## Chapter 12 Summary

| Service/Concept | Purpose | Key Fact |
|----------------|---------|----------|
| Lambda | Serverless functions | Pay per invocation; 15-min max timeout; 10 GB RAM max |
| Lambda Provisioned Concurrency | Eliminate cold starts | Pre-warmed environments; extra cost |
| Lambda Layers | Shared dependencies | Up to 5 layers; reduces deployment package size |
| ECS Fargate | Serverless containers | No EC2 management; pay per vCPU/memory/hour |
| ECS EC2 | EC2-backed containers | More control; cheaper at scale |
| ECR | Container registry | Private; integrated with IAM; scan on push |
| SQS Standard | Task queue | At-least-once; near FIFO; unlimited throughput |
| SQS FIFO | Ordered queue | Exactly-once; strict ordering; 3000 msg/sec |
| DLQ | Failed message handling | After N failures → moves to DLQ for inspection |
| SNS | Pub/sub messaging | Fan-out; one publish → many subscribers |
| Kinesis Streams | Real-time streaming | Multiple consumers; 7-day retention |
| Kinesis Firehose | Managed delivery | Streams to S3/Redshift/OpenSearch |
"""

with open(r"e:\fastapi\aws-admin\12_Serverless_Containers_Messaging.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
