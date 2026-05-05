# Chapter 9: Messaging & Events — SQS, SNS, Kinesis & EventBridge
## Decoupled, Asynchronous Communication Between Services

---

## 9.1 Messaging Services Overview

```
┌──────────────────────────────────────────────────────────────┐
│               AWS MESSAGING SERVICES                         │
├──────────────────────────┬───────────────────────────────────┤
│ SQS (Simple Queue)       │ Point-to-point queue              │
│                          │ One consumer per message          │
│                          │ Work queue pattern                │
├──────────────────────────┼───────────────────────────────────┤
│ SNS (Pub/Sub Topic)      │ Fan-out to many subscribers       │
│                          │ One publisher, many consumers     │
│                          │ Push-based                        │
├──────────────────────────┼───────────────────────────────────┤
│ EventBridge              │ Event bus with routing rules      │
│                          │ Complex event filtering           │
│                          │ SaaS and AWS service events       │
├──────────────────────────┼───────────────────────────────────┤
│ Kinesis                  │ Real-time streaming               │
│                          │ Ordered, replayable               │
│                          │ High-throughput analytics         │
├──────────────────────────┼───────────────────────────────────┤
│ MSK (Managed Kafka)      │ Fully managed Apache Kafka        │
│                          │ Open-source Kafka workloads       │
└──────────────────────────┴───────────────────────────────────┘
```

---

## 9.2 SQS — Simple Queue Service

SQS is a fully managed message queue. Producers send messages; consumers poll and process them.

### Queue Types

```
Standard Queue:
• At-least-once delivery (duplicates possible)
• Best-effort ordering
• Unlimited throughput
• Use for most workloads

FIFO Queue:
• Exactly-once delivery
• Strict ordering (first-in, first-out)
• Limited to 300 msg/sec (or 3000 with batching)
• Suffix: .fifo
• Use when order matters (payments, inventory)
```

### SQS Fundamentals

```bash
# Create standard queue
aws sqs create-queue \
  --queue-name order-processing \
  --attributes '{
    "VisibilityTimeout": "30",
    "MessageRetentionPeriod": "86400",
    "ReceiveMessageWaitTimeSeconds": "20"
  }'

# Create FIFO queue
aws sqs create-queue \
  --queue-name payments.fifo \
  --attributes '{
    "FifoQueue": "true",
    "ContentBasedDeduplication": "true",
    "VisibilityTimeout": "30"
  }'

# Create Dead Letter Queue (DLQ)
DLQ_ARN=$(aws sqs create-queue \
  --queue-name order-processing-dlq \
  --query QueueUrl --output text | \
  xargs -I {} aws sqs get-queue-attributes \
  --queue-url {} --attribute-names QueueArn \
  --query Attributes.QueueArn --output text)

# Attach DLQ to main queue (after 3 failures → move to DLQ)
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456/order-processing \
  --attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }"

# Send message
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456/order-processing \
  --message-body '{"orderId": "123", "userId": "456", "amount": 99.99}'

# Receive and process messages
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456/order-processing \
  --max-number-of-messages 10 \
  --wait-time-seconds 20 \
  --visibility-timeout 30

# Delete message after processing (required — SQS does not auto-delete)
aws sqs delete-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456/order-processing \
  --receipt-handle <receipt-handle-from-receive>
```

### SQS with Lambda

```python
# Lambda triggered by SQS — processes messages in batches
import json
import logging

logger = logging.getLogger()


def handler(event, context):
    """
    event["Records"] = list of SQS messages (batch)
    """
    failed_messages = []
    
    for record in event["Records"]:
        message_id = record["messageId"]
        body = json.loads(record["body"])
        
        try:
            process_order(body)
            logger.info("Processed order: %s", body["orderId"])
        except Exception as e:
            logger.error("Failed to process %s: %s", message_id, str(e))
            # Report individual failure — other messages still succeed
            failed_messages.append({"itemIdentifier": message_id})
    
    # Return failed message IDs — Lambda will retry those only
    return {"batchItemFailures": failed_messages}


def process_order(order: dict):
    # Business logic
    pass
```

```bash
# Create SQS → Lambda trigger
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn arn:aws:sqs:us-east-1:123456:order-processing \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --function-response-types ReportBatchItemFailures
```

### Key SQS Concepts

```
┌──────────────────────────────────────────────────────────┐
│                SQS KEY CONCEPTS                          │
│                                                          │
│  Visibility Timeout                                      │
│  After a message is received, it's hidden for this      │
│  duration. If not deleted in time, it reappears.        │
│  Default: 30s. Set >= your processing time.             │
│                                                          │
│  Message Retention                                       │
│  How long messages stay in queue if not consumed.       │
│  Default: 4 days. Max: 14 days.                         │
│                                                          │
│  Long Polling (ReceiveMessageWaitTimeSeconds > 0)        │
│  Wait up to 20s for messages before returning empty.    │
│  Reduces empty receives, lowers cost.                   │
│  Always use long polling in production.                 │
│                                                          │
│  Dead Letter Queue (DLQ)                                 │
│  Messages that fail N times get moved to DLQ.           │
│  Allows inspection of failed messages.                  │
│  Set up CloudWatch alarm on DLQ depth.                  │
└──────────────────────────────────────────────────────────┘
```

---

## 9.3 SNS — Simple Notification Service

SNS is a pub/sub service — one message published to a topic fans out to all subscribers.

```
┌──────────────────────────────────────────────────────────┐
│                   SNS FAN-OUT                            │
│                                                          │
│  Publisher                                               │
│      │                                                   │
│      ▼                                                   │
│  ┌──────────┐                                            │
│  │ SNS Topic│ "order-created"                            │
│  └────┬─────┘                                            │
│       │                                                  │
│   ┌───┼────────────────────────────────┐                 │
│   ▼   ▼                                ▼                 │
│  SQS  Lambda          Email       SMS      HTTP           │
│  Queue Notification   (admin)    (alerts)  (webhook)      │
│  (worker)                                                │
└──────────────────────────────────────────────────────────┘
```

```bash
# Create topic
TOPIC_ARN=$(aws sns create-topic \
  --name order-events \
  --query TopicArn --output text)

# Subscribe SQS queue to topic
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:123456:order-processing

# Subscribe Lambda
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456:function:send-notification

# Subscribe email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint admin@myapp.com

# Publish message
aws sns publish \
  --topic-arn $TOPIC_ARN \
  --subject "Order Created" \
  --message '{"orderId": "123", "userId": "456"}' \
  --message-attributes '{
    "eventType": {"DataType": "String", "StringValue": "OrderCreated"}
  }'
```

### SNS Message Filtering

```bash
# Subscribe SQS with filter — only receive OrderCreated events
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:...:order-processor \
  --attributes '{
    "FilterPolicy": "{\"eventType\": [\"OrderCreated\", \"OrderUpdated\"]}"
  }'

# Another subscription — only payment events
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:...:function:payment-processor \
  --attributes '{
    "FilterPolicy": "{\"eventType\": [\"PaymentReceived\", \"PaymentFailed\"]}"
  }'
```

---

## 9.4 Kinesis — Real-Time Streaming

Kinesis is for high-throughput, ordered, replayable data streams (like Apache Kafka but managed).

```
Use Kinesis when:
• Data arrives continuously (clickstreams, IoT, logs)
• You need ordering within a shard
• You need to replay data (retention up to 365 days)
• Multiple consumers need the same data stream
• Analytics in real-time

Use SQS when:
• Job queue — each message processed by one worker
• Ordering not critical (standard queue)
• Set-and-forget processing
```

### Kinesis Data Streams

```bash
# Create stream (1 shard = 1MB/s in, 2MB/s out, 1000 records/s)
aws kinesis create-stream \
  --stream-name clickstream \
  --shard-count 4

# Put record
aws kinesis put-record \
  --stream-name clickstream \
  --partition-key "user-123" \
  --data '{"userId": "123", "event": "page_view", "page": "/home"}' \
  --cli-binary-format raw-in-base64-out

# Put multiple records (batch)
aws kinesis put-records \
  --stream-name clickstream \
  --records '[
    {"Data": "{\"userId\":\"123\",\"event\":\"click\"}", "PartitionKey": "user-123"},
    {"Data": "{\"userId\":\"456\",\"event\":\"purchase\"}", "PartitionKey": "user-456"}
  ]' \
  --cli-binary-format raw-in-base64-out
```

```python
# Lambda triggered by Kinesis
import base64, json


def handler(event, context):
    for record in event["Records"]:
        # Decode base64 data
        payload = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
        data = json.loads(payload)
        
        shard_id = record["eventID"].split(":")[0]
        sequence_number = record["kinesis"]["sequenceNumber"]
        
        print(f"Shard: {shard_id}, Seq: {sequence_number}")
        print(f"Data: {data}")
        
        # Process event
        process_event(data)
```

### Kinesis Data Firehose

Firehose automatically batches and delivers streaming data to S3, Redshift, OpenSearch, or HTTP endpoints.

```bash
# Create Firehose delivery stream → S3
aws firehose create-delivery-stream \
  --delivery-stream-name clickstream-to-s3 \
  --s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123456:role/firehose-role",
    "BucketARN": "arn:aws:s3:::my-analytics-bucket",
    "Prefix": "clickstream/year=!{timestamp:yyyy}/month=!{timestamp:MM}/",
    "ErrorOutputPrefix": "errors/",
    "BufferingHints": {"SizeInMBs": 128, "IntervalInSeconds": 300},
    "CompressionFormat": "GZIP"
  }'
```

---

## 9.5 SES — Simple Email Service

SES sends transactional and marketing emails.

```bash
# Verify email address (sandbox mode)
aws ses verify-email-identity --email-address your@email.com

# Send email
aws ses send-email \
  --from "noreply@myapp.com" \
  --to "user@example.com" \
  --subject "Order Confirmation" \
  --text "Your order #123 has been confirmed." \
  --html "<h1>Order Confirmed</h1><p>Order #123 is confirmed.</p>"
```

```python
# Python SDK
import boto3

ses = boto3.client("ses", region_name="us-east-1")

ses.send_email(
    Source="noreply@myapp.com",
    Destination={"ToAddresses": ["user@example.com"]},
    Message={
        "Subject": {"Data": "Order Confirmation"},
        "Body": {
            "Html": {"Data": "<h1>Order #123 Confirmed!</h1>"}
        }
    }
)
```

---

## 9.6 Messaging Patterns

### Pattern 1: Fan-out (SNS → SQS × N)

```
Order Created → SNS Topic → SQS: email-queue → Lambda: send email
                          → SQS: analytics-queue → Lambda: update analytics
                          → SQS: inventory-queue → Lambda: reserve stock
```

### Pattern 2: Work Queue (SQS → Lambda)

```
Video uploaded → S3 event → SQS queue → Lambda (transcode video)
                                         (one Lambda per video, in parallel)
```

### Pattern 3: Event-Driven Saga

```
OrderService.createOrder()
    │
    ├──► SQS: PaymentRequested
    │         │
    │         └── PaymentService processes → SNS: PaymentResult
    │                                              │
    │         ┌──── PaymentSucceeded ─────────────┘
    │         │
    └──► SQS: ReserveInventory
              │
              └── InventoryService → SNS: OrderFulfilled
```

---

## 9.7 Interview Questions

**Q: What is the difference between SQS and SNS?**
> SQS is a queue — messages wait to be pulled by a consumer, and each message is processed by exactly one consumer. SNS is a pub/sub topic — when a message is published, it's pushed to all subscribers simultaneously (fan-out). They're often used together: SNS publishes to multiple SQS queues, which different services independently consume.

**Q: What is a Dead Letter Queue and why is it important?**
> A DLQ is where messages go after failing to process N times. Without a DLQ, failed messages would retry forever, blocking the queue. With a DLQ, failures are isolated for inspection and reprocessing. Best practice: set a CloudWatch alarm on DLQ depth to alert on processing failures, and build a redrive capability to replay DLQ messages after fixing the bug.

**Q: When would you use Kinesis vs SQS?**
> Kinesis for real-time streaming with ordered, replayable data — multiple consumers can read the same stream independently, useful for analytics pipelines, clickstream processing, IoT data. SQS for work queues where each message should be processed by exactly one worker. If you need to process a stream of events AND multiple services need the same data, Kinesis is better. For background job queues, SQS is simpler and cheaper.
