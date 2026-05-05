# Chapter 9: Messaging — SQS, SNS, Kinesis, EventBridge & SES
## Asynchronous Communication, Event Streaming, and Notifications

---

## 9.1 Messaging Services Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                  AWS MESSAGING SERVICES                           │
├────────────────────┬──────────────────────────────────────────────┤
│ SQS                │ Message queuing, decoupling services,        │
│                    │ async processing, worker pools               │
├────────────────────┼──────────────────────────────────────────────┤
│ SNS                │ Pub/Sub notifications, fanout to multiple    │
│                    │ subscribers (SQS, Lambda, email, HTTP, SMS)  │
├────────────────────┼──────────────────────────────────────────────┤
│ Kinesis Data       │ Real-time streaming, ordered records, replay │
│ Streams            │ up to 1 year retention                       │
├────────────────────┼──────────────────────────────────────────────┤
│ Kinesis Firehose   │ Load streaming data to S3/Redshift/ES/Splunk │
│                    │ Managed ETL pipeline, no consumer needed     │
├────────────────────┼──────────────────────────────────────────────┤
│ EventBridge        │ Serverless event bus, AWS service events,    │
│                    │ SaaS integration, scheduled rules            │
├────────────────────┼──────────────────────────────────────────────┤
│ SES                │ Email sending (transactional + marketing)    │
├────────────────────┼──────────────────────────────────────────────┤
│ MQ                 │ Managed Apache ActiveMQ / RabbitMQ           │
│                    │ Lift-and-shift messaging workloads           │
└────────────────────┴──────────────────────────────────────────────┘

Choose by use case:
  Job queue / worker pattern:   SQS
  Fan-out (1→many):             SNS → SQS/Lambda
  Real-time stream analytics:   Kinesis Data Streams
  Load data to data lake:       Kinesis Firehose
  React to AWS events:          EventBridge
  Email delivery:               SES
```

---

## 9.2 SQS — Simple Queue Service

### SQS Core Concepts

```
SQS Queue Model:
  Producer ──→ Queue ──→ Consumer (polling)

Key properties:
  Standard Queue: At-least-once delivery, best-effort ordering, unlimited TPS
  FIFO Queue: Exactly-once processing, strict ordering, 3,000 TPS (or 300 TPS w/ msg groups)
  
  Visibility Timeout: Time a message is "invisible" after consumer receives it
    Default: 30 seconds. Consumer must delete before timeout or message becomes visible again
    Set to max expected processing time + buffer
  
  Message Retention: 1 minute to 14 days (default 4 days)
  Max Message Size: 256KB (use Extended Client Library for S3 payloads)
  Long Polling: Wait up to 20 seconds for messages (reduces empty responses)
  Short Polling: Returns immediately even if empty (wasteful, more API calls)
  
  Dead-Letter Queue (DLQ): Messages that fail processing N times go here
    Separately monitored, prevents endless retry loops
```

```bash
# Create Standard Queue with DLQ
DLQ_URL=$(aws sqs create-queue \
  --queue-name orders-dlq \
  --attributes '{
    "MessageRetentionPeriod": "1209600",
    "Tags": {"Environment": "prod", "Service": "orders"}
  }' \
  --query "QueueUrl" --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names QueueArn \
  --query "Attributes.QueueArn" --output text)

# Create main queue with DLQ configured
QUEUE_URL=$(aws sqs create-queue \
  --queue-name orders \
  --attributes '{
    "VisibilityTimeout": "300",
    "MessageRetentionPeriod": "86400",
    "ReceiveMessageWaitTimeSeconds": "20",
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":\"3\"}",
    "Tags": {"Environment": "prod"}
  }' \
  --query "QueueUrl" --output text)

# Create FIFO Queue (name MUST end with .fifo)
FIFO_URL=$(aws sqs create-queue \
  --queue-name payments.fifo \
  --attributes '{
    "FifoQueue": "true",
    "ContentBasedDeduplication": "true",
    "VisibilityTimeout": "60",
    "ReceiveMessageWaitTimeSeconds": "20",
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$FIFO_DLQ_ARN'\",\"maxReceiveCount\":\"5\"}"
  }' \
  --query "QueueUrl" --output text)
```

### SQS Message Operations

```bash
# Send a message
aws sqs send-message \
  --queue-url $QUEUE_URL \
  --message-body '{"orderId": "ord-123", "customerId": "cust-456", "total": 99.95}' \
  --message-attributes '{
    "OrderType": {"DataType": "String", "StringValue": "EXPRESS"},
    "Priority": {"DataType": "Number", "StringValue": "1"}
  }' \
  --delay-seconds 0       # Delay before visible (0-900 seconds)

# Send batch (up to 10 messages per call)
aws sqs send-message-batch \
  --queue-url $QUEUE_URL \
  --entries '[
    {"Id": "1", "MessageBody": "{\"orderId\": \"ord-1\"}"},
    {"Id": "2", "MessageBody": "{\"orderId\": \"ord-2\"}"},
    {"Id": "3", "MessageBody": "{\"orderId\": \"ord-3\"}"}
  ]'

# Receive messages (long polling, up to 10)
aws sqs receive-message \
  --queue-url $QUEUE_URL \
  --max-number-of-messages 10 \
  --wait-time-seconds 20 \         # Long polling
  --message-attribute-names All \
  --attribute-names All

# Delete message after successful processing
aws sqs delete-message \
  --queue-url $QUEUE_URL \
  --receipt-handle "receipt-handle-from-receive"

# Delete batch (save API calls)
aws sqs delete-message-batch \
  --queue-url $QUEUE_URL \
  --entries '[
    {"Id": "1", "ReceiptHandle": "receipt-1"},
    {"Id": "2", "ReceiptHandle": "receipt-2"}
  ]'

# Change visibility timeout (extend if processing takes longer)
aws sqs change-message-visibility \
  --queue-url $QUEUE_URL \
  --receipt-handle "receipt-handle" \
  --visibility-timeout 120    # Extend by 120 more seconds

# Purge queue (delete all messages)
aws sqs purge-queue --queue-url $QUEUE_URL
```

### Python SQS Worker

```python
import boto3
import json
import logging
import time
from typing import Optional

logger = logging.getLogger()
sqs = boto3.client('sqs')
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123/orders'
MAX_MESSAGES = 10
WAIT_TIME = 20
VISIBILITY_TIMEOUT = 300

def process_order(order_data: dict) -> bool:
    """Process an order. Return True on success, False on failure."""
    logger.info(f"Processing order {order_data.get('orderId')}")
    # ... business logic ...
    return True

def run_worker():
    """Continuous SQS polling worker."""
    logger.info("Starting SQS worker...")
    
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=MAX_MESSAGES,
                WaitTimeSeconds=WAIT_TIME,
                MessageAttributeNames=['All'],
                AttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            if not messages:
                continue
            
            for message in messages:
                message_id = message['MessageId']
                receipt_handle = message['ReceiptHandle']
                
                try:
                    body = json.loads(message['Body'])
                    
                    if process_order(body):
                        # Delete on success
                        sqs.delete_message(
                            QueueUrl=QUEUE_URL,
                            ReceiptHandle=receipt_handle
                        )
                        logger.info(f"Processed and deleted: {message_id}")
                    else:
                        # Leave in queue for retry (visibility timeout expires)
                        logger.warning(f"Processing failed, will retry: {message_id}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in message {message_id}: {e}")
                    # Delete malformed messages to prevent infinite loop
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
                
                except Exception as e:
                    logger.error(f"Error processing {message_id}: {e}", exc_info=True)
                    # Visibility timeout will expire and message will be retried
        
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(5)

if __name__ == '__main__':
    run_worker()
```

---

## 9.3 SNS — Simple Notification Service

### SNS Concepts

```
SNS Pub/Sub Model:
  Publisher ──→ Topic ──→ [Subscriber 1: SQS Queue]
                       ──→ [Subscriber 2: Lambda]
                       ──→ [Subscriber 3: HTTPS endpoint]
                       ──→ [Subscriber 4: Email]
                       ──→ [Subscriber 5: SMS]
                       ──→ [Subscriber 6: Mobile Push]

Fanout Pattern (best practice):
  Use SNS → multiple SQS queues instead of SNS → Lambda directly
  Reason: SQS provides buffering, retry, DLQ for each consumer
```

```bash
# Create SNS topic
TOPIC_ARN=$(aws sns create-topic \
  --name order-events \
  --attributes '{
    "DisplayName": "Order Events",
    "KmsMasterKeyId": "alias/sns-key"
  }' \
  --tags Key=Service,Value=orders \
  --query "TopicArn" --output text)

# Create FIFO topic (preserves order)
FIFO_TOPIC=$(aws sns create-topic \
  --name payment-events.fifo \
  --attributes '{
    "FifoTopic": "true",
    "ContentBasedDeduplication": "true"
  }' \
  --query "TopicArn" --output text)

# Subscribe SQS to SNS (fanout)
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol sqs \
  --notification-endpoint $ORDER_PROCESSOR_QUEUE_ARN \
  --attributes '{
    "RawMessageDelivery": "true",
    "FilterPolicy": "{\"event_type\": [\"ORDER_CREATED\", \"ORDER_UPDATED\"]}"
  }'

# Subscribe Lambda
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123:function:order-analytics

# Subscribe email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint ops-team@company.com

# Subscribe HTTPS endpoint
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol https \
  --notification-endpoint https://webhook.example.com/sns \
  --attributes '{"DeliveryPolicy": "{\"healthyRetryPolicy\": {\"numRetries\": 20}}"}'

# Add SQS queue policy to allow SNS publish
aws sqs set-queue-attributes \
  --queue-url $QUEUE_URL \
  --attributes '{
    "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$QUEUE_ARN'\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"'$TOPIC_ARN'\"}}}]}"
  }'

# Publish message
aws sns publish \
  --topic-arn $TOPIC_ARN \
  --message '{"event_type": "ORDER_CREATED", "order_id": "ord-123", "total": 99.95}' \
  --subject "New Order Created" \
  --message-attributes '{
    "event_type": {"DataType": "String", "StringValue": "ORDER_CREATED"}
  }'
```

### Message Filtering

```bash
# SNS message filtering — subscriber only receives matching messages
# Subscription filter policy (applied at SNS, not subscriber)
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:...:sub-id \
  --attribute-name FilterPolicy \
  --attribute-value '{
    "event_type": ["ORDER_CREATED"],
    "region": ["us-east-1", "eu-west-1"],
    "amount": [{"numeric": [">=", 100]}]
  }'
```

---

## 9.4 Kinesis Data Streams

Kinesis is for real-time data streaming at scale — ingest and process millions of records per second.

```
Kinesis Concepts:
  Stream: Named collection of shards
  Shard:  Unit of capacity — 1MB/s write, 2MB/s read, 1000 records/s write
  Record: Data unit — partition key + data blob (up to 1MB)
  Partition Key: Routes record to a specific shard (hash-based)
  Sequence Number: Unique ordered ID per record per shard
  Retention: Default 24 hours, up to 365 days

Consumers:
  Standard: 2MB/s per shard TOTAL across all consumers (shared)
  Enhanced Fan-Out: 2MB/s per shard PER consumer (dedicated, push-based)
```

### Kinesis Management

```bash
# Create stream
aws kinesis create-stream \
  --stream-name user-events \
  --shard-count 10 \
  --stream-mode-details StreamMode=PROVISIONED

# OR On-Demand (auto-scales shards)
aws kinesis create-stream \
  --stream-name user-events \
  --stream-mode-details StreamMode=ON_DEMAND

# Get stream status
aws kinesis describe-stream-summary --stream-name user-events

# Increase shards (split, doubling capacity)
aws kinesis update-shard-count \
  --stream-name user-events \
  --target-shard-count 20 \
  --scaling-type UNIFORM_SCALING

# Put record
aws kinesis put-record \
  --stream-name user-events \
  --partition-key "user-123" \
  --data '{"user_id": "user-123", "event": "page_view", "page": "/home"}' \
  | base64    # --data accepts base64 encoded

# Put records (batch, up to 500)
aws kinesis put-records \
  --stream-name user-events \
  --records '[
    {"PartitionKey": "user-1", "Data": "eyJldmVudCI6InBhZ2VfdmlldyJ9"},
    {"PartitionKey": "user-2", "Data": "eyJldmVudCI6ImNsaWNrIn0="}
  ]'

# Enable enhanced fan-out consumer
aws kinesis register-stream-consumer \
  --stream-arn arn:aws:kinesis:us-east-1:123:stream/user-events \
  --consumer-name analytics-service
```

### Python Kinesis Producer

```python
import boto3
import json
import base64
from typing import List, Dict

kinesis = boto3.client('kinesis')
STREAM_NAME = 'user-events'

def send_events(events: List[Dict]) -> dict:
    """Batch send events to Kinesis."""
    records = [
        {
            'Data': json.dumps(event).encode('utf-8'),
            'PartitionKey': str(event.get('user_id', 'default'))
        }
        for event in events
    ]
    
    response = kinesis.put_records(
        StreamName=STREAM_NAME,
        Records=records
    )
    
    failed = response.get('FailedRecordCount', 0)
    if failed > 0:
        # Retry failed records
        failed_records = [
            records[i] for i, r in enumerate(response['Records'])
            if 'ErrorCode' in r
        ]
        retry_response = kinesis.put_records(
            StreamName=STREAM_NAME,
            Records=failed_records
        )
    
    return response
```

### Python Kinesis Consumer

```python
import boto3
import json
import time
import base64

kinesis = boto3.client('kinesis')
STREAM_NAME = 'user-events'

def get_shard_iterator(shard_id: str, iterator_type: str = 'LATEST') -> str:
    response = kinesis.get_shard_iterator(
        StreamName=STREAM_NAME,
        ShardId=shard_id,
        ShardIteratorType=iterator_type,
        # For AFTER_SEQUENCE_NUMBER or AT_SEQUENCE_NUMBER:
        # StartingSequenceNumber='sequence-number'
        # For AT_TIMESTAMP:
        # Timestamp=datetime(2025, 1, 1)
    )
    return response['ShardIterator']

def consume_stream():
    # Get all shards
    response = kinesis.describe_stream(StreamName=STREAM_NAME)
    shards = response['StreamDescription']['Shards']
    
    for shard in shards:
        shard_id = shard['ShardId']
        iterator = get_shard_iterator(shard_id, 'TRIM_HORIZON')  # From beginning
        
        while True:
            response = kinesis.get_records(
                ShardIterator=iterator,
                Limit=100
            )
            
            for record in response['Records']:
                data = json.loads(record['Data'].decode('utf-8'))
                seq = record['SequenceNumber']
                partition_key = record['PartitionKey']
                
                process_event(data, seq, partition_key)
            
            iterator = response['NextShardIterator']
            if not iterator:
                break  # Shard is closed
            
            # Respect rate limits (5 GetRecords/shard/sec for standard consumers)
            time.sleep(1)
```

---

## 9.5 Kinesis Data Firehose

Firehose automatically delivers streaming data to destinations without managing consumers:

```bash
# Create Firehose delivery stream (S3 destination)
aws firehose create-delivery-stream \
  --delivery-stream-name user-events-firehose \
  --delivery-stream-type DirectPut \
  --extended-s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123:role/FirehoseRole",
    "BucketARN": "arn:aws:s3:::my-data-lake",
    "Prefix": "user-events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "ErrorOutputPrefix": "errors/",
    "BufferingHints": {
      "SizeInMBs": 128,
      "IntervalInSeconds": 300
    },
    "CompressionFormat": "GZIP",
    "DataFormatConversionConfiguration": {
      "Enabled": true,
      "InputFormatConfiguration": {
        "Deserializer": {
          "OpenXJsonSerDe": {}
        }
      },
      "OutputFormatConfiguration": {
        "Serializer": {
          "ParquetSerDe": {}
        }
      },
      "SchemaConfiguration": {
        "DatabaseName": "analytics",
        "TableName": "user_events",
        "RoleARN": "arn:aws:iam::123:role/FirehoseRole"
      }
    },
    "ProcessingConfiguration": {
      "Enabled": true,
      "Processors": [{
        "Type": "Lambda",
        "Parameters": [{
          "ParameterName": "LambdaArn",
          "ParameterValue": "arn:aws:lambda:us-east-1:123:function:transform-events"
        }]
      }]
    }
  }'

# Put records to Firehose
aws firehose put-record \
  --delivery-stream-name user-events-firehose \
  --record '{"Data": "eyJ1c2VyX2lkIjoidXNlci0xMjMiLCJldmVudCI6ImNsaWNrIn0K"}'
  # Note: each record should end with newline for S3 file readability
```

---

## 9.6 Amazon EventBridge

EventBridge is a serverless event bus connecting AWS services, SaaS, and your applications.

```
EventBridge Architecture:
  Event Sources          Event Bus          Rules → Targets
  ─────────────          ─────────          ──────────────
  AWS Services     →                    → Lambda
  Custom apps      →    default bus     → SQS
  SaaS (Salesforce →    custom bus      → SNS
  Zendesk, etc.)   →    partner bus     → EventBridge API Destinations
                                        → Step Functions
                                        → ECS Task
                                        → Another Event Bus (cross-account)
```

```bash
# Create custom event bus
aws events create-event-bus \
  --name orders-bus \
  --tags Key=Service,Value=orders

# Create a rule (match specific events)
aws events put-rule \
  --name process-high-value-orders \
  --event-bus-name orders-bus \
  --event-pattern '{
    "source": ["com.mycompany.orders"],
    "detail-type": ["OrderCreated"],
    "detail": {
      "status": ["CONFIRMED"],
      "total": [{"numeric": [">=", 500]}]
    }
  }' \
  --state ENABLED

# Create scheduled rule (cron)
aws events put-rule \
  --name daily-report \
  --schedule-expression "cron(0 8 * * ? *)" \   # 8 AM UTC daily
  --state ENABLED

# Add Lambda target
aws events put-targets \
  --rule process-high-value-orders \
  --event-bus-name orders-bus \
  --targets '[{
    "Id": "vip-order-processor",
    "Arn": "arn:aws:lambda:us-east-1:123:function:vip-processor",
    "InputTransformer": {
      "InputPathsMap": {
        "orderId": "$.detail.order_id",
        "amount": "$.detail.total"
      },
      "InputTemplate": "{\"order\": \"<orderId>\", \"amount\": <amount>, \"vip\": true}"
    }
  }]'

# Add SQS target with dead-letter
aws events put-targets \
  --rule process-high-value-orders \
  --event-bus-name orders-bus \
  --targets '[{
    "Id": "order-queue",
    "Arn": "arn:aws:sqs:us-east-1:123:orders-queue",
    "DeadLetterConfig": {"Arn": "arn:aws:sqs:us-east-1:123:eventbridge-dlq"}
  }]'

# Send custom event
aws events put-events \
  --entries '[{
    "EventBusName": "orders-bus",
    "Source": "com.mycompany.orders",
    "DetailType": "OrderCreated",
    "Detail": "{\"order_id\": \"ord-123\", \"status\": \"CONFIRMED\", \"total\": 750.00, \"customer_id\": \"cust-456\"}"
  }]'

# Create API destination (webhook to external service)
aws events create-connection \
  --name stripe-webhook \
  --authorization-type API_KEY \
  --auth-parameters '{
    "ApiKeyAuthParameters": {
      "ApiKeyName": "Authorization",
      "ApiKeyValue": "Bearer sk_live_..."
    }
  }'

aws events create-api-destination \
  --name send-to-stripe \
  --connection-arn arn:aws:events:...:connection/stripe-webhook \
  --invocation-endpoint https://api.stripe.com/v1/events \
  --http-method POST \
  --invocation-rate-limit-per-second 100
```

### Python EventBridge Publisher

```python
import boto3
import json
from datetime import datetime

events = boto3.client('events')

def publish_order_event(event_type: str, order_data: dict) -> dict:
    """Publish order event to EventBridge."""
    return events.put_events(
        Entries=[{
            'EventBusName': 'orders-bus',
            'Source': 'com.mycompany.orders',
            'DetailType': event_type,
            'Detail': json.dumps({
                **order_data,
                'timestamp': datetime.utcnow().isoformat()
            }),
            'Resources': [
                f"arn:aws:orders::123:order/{order_data['order_id']}"
            ]
        }]
    )

# Usage
publish_order_event('OrderCreated', {
    'order_id': 'ord-123',
    'customer_id': 'cust-456',
    'total': 99.95,
    'status': 'CONFIRMED',
    'items': [{'sku': 'ITEM-1', 'qty': 2}]
})
```

---

## 9.7 Fanout Pattern with SNS + SQS

```
The Fanout Pattern — one event → multiple independent processors:

         ┌──────────────────────────────────────────────┐
         │              SNS Topic                        │
         │         "order-events"                        │
         └──────────┬──────────────┬───────────────┬────┘
                    │              │               │
                    ▼              ▼               ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │SQS Queue │  │SQS Queue │  │SQS Queue │
              │order-proc│  │inventory │  │analytics │
              └──────────┘  └──────────┘  └──────────┘
                    │              │               │
                    ▼              ▼               ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ Lambda   │  │ Lambda   │  │ Lambda   │
              │OrderSvc  │  │ InvSvc   │  │Analytics │
              └──────────┘  └──────────┘  └──────────┘

Benefits:
  - Services are decoupled (order service doesn't know about downstream)
  - Each queue has independent DLQ, retry, scaling
  - Add new consumers without changing publishers
  - Message filtering per subscription
```

```python
import boto3
import json

sns = boto3.client('sns')
TOPIC_ARN = 'arn:aws:sns:us-east-1:123:order-events'

def publish_order_created(order: dict):
    """Publish to SNS with attributes for filtering."""
    response = sns.publish(
        TopicArn=TOPIC_ARN,
        Message=json.dumps(order),
        MessageAttributes={
            'event_type': {
                'DataType': 'String',
                'StringValue': 'ORDER_CREATED'
            },
            'customer_tier': {
                'DataType': 'String', 
                'StringValue': order.get('customer_tier', 'standard')
            },
            'order_amount': {
                'DataType': 'Number',
                'StringValue': str(order.get('total', 0))
            }
        }
    )
    return response['MessageId']
```

---

## 9.8 SES — Simple Email Service

```bash
# Verify email identity (for sandbox mode)
aws ses verify-email-identity --email-address sender@example.com

# Verify domain identity
aws ses verify-domain-identity --domain example.com

# Create configuration set (for tracking + suppression)
aws sesv2 create-configuration-set \
  --configuration-set-name prod-config \
  --tracking-options HttpRedirectDomain=tracking.example.com \
  --suppression-options SuppressedReasons=BOUNCE,COMPLAINT

# Add event destination (CloudWatch metrics)
aws sesv2 create-configuration-set-event-destination \
  --configuration-set-name prod-config \
  --event-destination-name cloudwatch-metrics \
  --event-destination '{
    "Enabled": true,
    "MatchingEventTypes": ["SEND", "BOUNCE", "COMPLAINT", "DELIVERY", "OPEN", "CLICK"],
    "CloudWatchDestination": {
      "DimensionConfigurations": [{
        "DimensionName": "EmailType",
        "DimensionValueSource": "MESSAGE_TAG",
        "DefaultDimensionValue": "generic"
      }]
    }
  }'

# Send transactional email
aws sesv2 send-email \
  --from-email-address noreply@example.com \
  --destination '{"ToAddresses": ["customer@example.com"]}' \
  --content '{
    "Simple": {
      "Subject": {"Data": "Your order has shipped!", "Charset": "UTF-8"},
      "Body": {
        "Html": {
          "Data": "<h1>Your order ord-123 has shipped!</h1><p>Track it <a href='"'"'https://track.example.com/ord-123'"'"'>here</a>.</p>",
          "Charset": "UTF-8"
        },
        "Text": {
          "Data": "Your order ord-123 has shipped! Track it at https://track.example.com/ord-123",
          "Charset": "UTF-8"
        }
      }
    }
  }' \
  --configuration-set-name prod-config \
  --email-tags '[{"Name": "EmailType", "Value": "shipping-confirmation"}]'
```

```python
# Python SES v2 email
import boto3
from botocore.exceptions import ClientError

ses = boto3.client('sesv2')

def send_welcome_email(to_email: str, user_name: str) -> bool:
    try:
        response = ses.send_email(
            FromEmailAddress='welcome@example.com',
            Destination={'ToAddresses': [to_email]},
            Content={
                'Template': {
                    'TemplateName': 'WelcomeEmail',
                    'TemplateData': json.dumps({
                        'UserName': user_name,
                        'LoginUrl': 'https://app.example.com/login'
                    })
                }
            },
            ConfigurationSetName='prod-config',
            EmailTags=[{'Name': 'EmailType', 'Value': 'welcome'}]
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccountSuspendedException':
            logger.error("SES account suspended!")
        elif e.response['Error']['Code'] == 'SendingPausedException':
            logger.error("Sending paused for configuration set")
        return False
```

---

## 9.9 Interview Q&A

**Q: What is the difference between SQS Standard and FIFO queues?**
A: Standard queues: at-least-once delivery (occasional duplicates), best-effort ordering, nearly unlimited TPS. FIFO queues: exactly-once processing (deduplication), strict ordering within message groups, 3,000 TPS (with batching) or 300 TPS. Use FIFO when order matters and duplicates are harmful (payment processing, bank transactions). Use Standard for most other use cases where higher throughput is needed.

**Q: What is an SQS dead-letter queue and why is it important?**
A: A DLQ is a separate queue that receives messages that couldn't be processed successfully after N attempts. It prevents infinite retry loops that waste compute and block the queue. After investigation, you can re-drive messages from the DLQ back to the source queue. Always configure DLQ with CloudWatch alarm for monitoring — messages in DLQ indicate application problems.

**Q: What is the difference between SNS and SQS?**
A: SNS is push-based pub/sub: publishes to multiple subscribers simultaneously (fanout). SQS is pull-based queue: messages wait for consumers to poll and process. They complement each other — use SNS→SQS fanout pattern: SNS broadcasts to multiple SQS queues, each with independent consumers, retry, and DLQ. Never have many Lambda functions subscribe to SNS directly — use SQS for buffering.

**Q: What is the difference between Kinesis and SQS?**
A: Kinesis is for ordered, real-time streaming with replay capability and multiple independent consumers reading simultaneously. Records are retained up to 365 days. SQS is for job queuing where each message is processed exactly once and deleted. Key differences: Kinesis maintains order per shard, supports replay; SQS guarantees at-least-once delivery, auto-deletes on consume. Use Kinesis for analytics pipelines, event sourcing; use SQS for task queues.

**Q: What is EventBridge and when would you use it over SQS/SNS?**
A: EventBridge is a serverless event bus for event-driven architectures. Use over SQS/SNS when: reacting to AWS service events (EC2 state changes, S3 events, etc.); integrating with 200+ SaaS partners; routing events with complex content-based rules; scheduling (cron); connecting microservices on an event bus pattern. EventBridge handles discovery and routing; SQS handles queuing; they work together.

**Q: How do you handle Kinesis consumer hot partitions?**
A: Hot partitions occur when many records have the same partition key, overloading one shard. Solutions: (1) use high-cardinality partition keys (random UUID, timestamp + random suffix); (2) append random salt to partition key for write distribution; (3) use Kinesis Enhanced Fan-Out for 2MB/s per consumer instead of shared throughput; (4) increase shard count via UpdateShardCount.

**Q: What is the Lambda + SQS `ReportBatchItemFailures` feature?**
A: When Lambda processes SQS messages in batches, if one message fails, the default behavior retries the entire batch. With `ReportBatchItemFailures`, your Lambda can return the IDs of specific failed messages. Lambda then only puts those failed messages back in the queue, not the entire batch. This prevents successfully-processed messages from being reprocessed. Essential for production SQS+Lambda integrations.
