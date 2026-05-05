# Chapter 10: Monitoring & Observability
## CloudWatch, CloudTrail, X-Ray & AWS Config

---

## 10.1 Observability Overview

```
┌──────────────────────────────────────────────────────────┐
│              THREE PILLARS OF OBSERVABILITY              │
│                                                          │
│  METRICS           LOGS             TRACES               │
│  ───────           ────             ──────               │
│  What happened     Why it happened  How it happened      │
│  (numbers)         (text events)    (request path)       │
│                                                          │
│  CloudWatch        CloudWatch       X-Ray                 │
│  Metrics           Logs             (distributed tracing) │
│                                                          │
│  e.g., CPU=80%,    e.g., "ERROR:   e.g., API call took  │
│  500 errors/min    connection       300ms — 200ms in DB  │
│                    refused"         + 100ms in Lambda    │
└──────────────────────────────────────────────────────────┘
```

---

## 10.2 CloudWatch Metrics

Every AWS service automatically publishes metrics to CloudWatch. You can also publish custom metrics.

### Built-In Metrics

```bash
# List metrics for EC2
aws cloudwatch list-metrics \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=i-0abc123

# Get CPU utilisation last 1 hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc123 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average,Maximum
```

### Custom Metrics

```python
import boto3

cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

# Publish custom metric
cloudwatch.put_metric_data(
    Namespace="MyApp/API",
    MetricData=[
        {
            "MetricName": "OrdersProcessed",
            "Value": 42,
            "Unit": "Count",
            "Dimensions": [
                {"Name": "Environment", "Value": "prod"},
                {"Name": "Service", "Value": "orders"},
            ]
        },
        {
            "MetricName": "OrderProcessingTime",
            "Value": 350.5,
            "Unit": "Milliseconds",
            "Dimensions": [
                {"Name": "Environment", "Value": "prod"},
            ]
        }
    ]
)
```

---

## 10.3 CloudWatch Alarms

Alarms watch metrics and trigger actions when thresholds are breached.

```bash
# Alarm: CPU > 80% for 2 consecutive 5-minute periods
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-ec2 \
  --alarm-description "EC2 CPU exceeds 80%" \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc123 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456:ops-alerts \
  --ok-actions arn:aws:sns:us-east-1:123456:ops-alerts \
  --treat-missing-data breaching

# Alarm: 5xx errors > 10 in 1 minute (ALB)
aws cloudwatch put-metric-alarm \
  --alarm-name high-5xx-errors \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_ELB_5XX_Count \
  --dimensions Name=LoadBalancer,Value=app/my-alb/abc123 \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456:ops-alerts

# Alarm: Lambda error rate > 1%
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-errors \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=my-function \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456:ops-alerts

# Composite alarm — alert only if BOTH CPU and memory are high
aws cloudwatch put-composite-alarm \
  --alarm-name high-resource-usage \
  --alarm-rule "ALARM(high-cpu-ec2) AND ALARM(high-memory-ec2)" \
  --alarm-actions arn:aws:sns:us-east-1:123456:ops-alerts
```

---

## 10.4 CloudWatch Logs

CloudWatch Logs stores and searches log data from all AWS services and your applications.

```bash
# Create log group with retention
aws logs create-log-group --log-group-name /app/fastapi-prod
aws logs put-retention-policy \
  --log-group-name /app/fastapi-prod \
  --retention-in-days 30

# View recent logs
aws logs tail /app/fastapi-prod --follow
aws logs tail /aws/lambda/my-function --follow --since 10m

# Filter logs (search)
aws logs filter-log-events \
  --log-group-name /app/fastapi-prod \
  --filter-pattern "ERROR" \
  --start-time $(($(date +%s) - 3600))000  # Last 1 hour

# CloudWatch Insights — SQL-like log analytics
aws logs start-query \
  --log-group-name /app/fastapi-prod \
  --start-time $(($(date +%s) - 3600)) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /ERROR/
    | stats count(*) as error_count by bin(5m)
    | sort @timestamp desc
    | limit 20
  '
```

### Structured Logging in Python

```python
# logging_config.py
import logging
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


# FastAPI middleware for request logging
import time
from fastapi import Request

async def logging_middleware(request: Request, call_next):
    start = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger = logging.getLogger("api")
    logger.info("Request started", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path
    })
    
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    
    logger.info("Request completed", extra={
        "request_id": request_id,
        "status_code": response.status_code,
        "duration_ms": round(duration, 2)
    })
    return response
```

### Log Metric Filter — Alert on Errors in Logs

```bash
# Create metric filter (count ERROR lines as a metric)
aws logs put-metric-filter \
  --log-group-name /app/fastapi-prod \
  --filter-name error-count \
  --filter-pattern "[timestamp, level=ERROR, ...]" \
  --metric-transformations \
    metricName=ApplicationErrors,\
    metricNamespace=MyApp/API,\
    metricValue=1,\
    defaultValue=0

# Then create CloudWatch alarm on that metric
aws cloudwatch put-metric-alarm \
  --alarm-name application-error-rate \
  --namespace MyApp/API \
  --metric-name ApplicationErrors \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:...:ops-alerts
```

---

## 10.5 CloudWatch Dashboards

```bash
# Create dashboard (JSON body)
aws cloudwatch put-dashboard \
  --dashboard-name "MyApp-Production" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "title": "API Request Count",
          "metrics": [["AWS/Lambda", "Invocations", "FunctionName", "my-function"]],
          "period": 300,
          "stat": "Sum",
          "view": "timeSeries"
        }
      },
      {
        "type": "metric",
        "properties": {
          "title": "Lambda Errors",
          "metrics": [["AWS/Lambda", "Errors", "FunctionName", "my-function"]],
          "period": 300,
          "stat": "Sum",
          "view": "timeSeries"
        }
      },
      {
        "type": "alarm",
        "properties": {
          "title": "Alarms",
          "alarms": [
            "arn:aws:cloudwatch:us-east-1:123456:alarm:high-cpu-ec2",
            "arn:aws:cloudwatch:us-east-1:123456:alarm:high-5xx-errors"
          ]
        }
      }
    ]
  }'
```

---

## 10.6 CloudTrail — Audit Logging

CloudTrail records every API call made in your AWS account — who did what, when, from where.

```
CloudTrail captures:
• Console actions (user clicked "Delete" on EC2)
• CLI commands (aws s3 rm ...)
• SDK/API calls (boto3.client("s3").delete_object(...))
• AWS service-to-service calls

NOT captured:
• Traffic within your EC2 instances
• Application logs
• Data events (S3 object reads) — optional, extra cost
```

```bash
# Create trail (enables multi-region logging)
aws cloudtrail create-trail \
  --name my-audit-trail \
  --s3-bucket-name my-cloudtrail-logs \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456:log-group:cloudtrail \
  --cloud-watch-logs-role-arn arn:aws:iam::123456:role/cloudtrail-cloudwatch-role

aws cloudtrail start-logging --name my-audit-trail

# Look up events (last 90 days kept in Event History for free)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time 2024-01-01T00:00:00Z

# Who deleted my EC2 instance?
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=i-0abc123 \
  --query "Events[?EventName=='TerminateInstances'].[EventTime,Username,SourceIPAddress]"
```

---

## 10.7 AWS X-Ray — Distributed Tracing

X-Ray traces requests as they travel through your microservices, showing where time is spent.

```
Request trace:
API Gateway (5ms)
  └── Lambda cold start (250ms)
       └── Lambda handler (95ms)
            ├── DynamoDB GetItem (15ms) ✅
            ├── External API call (60ms) ⚠ SLOW
            └── DynamoDB PutItem (20ms) ✅
Total: 350ms → root cause found: external API call
```

```python
# Install: pip install aws-xray-sdk
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware
from fastapi import FastAPI

# Auto-patch AWS SDK calls (boto3) to trace them
patch_all()

app = FastAPI()
app.add_middleware(XRayMiddleware, recorder=xray_recorder)

xray_recorder.configure(service="my-fastapi-app")


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    # Create a sub-segment for custom tracing
    with xray_recorder.in_subsegment("fetch-order"):
        order = await get_from_db(order_id)
    
    with xray_recorder.in_subsegment("enrich-order"):
        xray_recorder.current_subsegment().put_annotation("order_id", order_id)
        enriched = await enrich_with_user_data(order)
    
    return enriched
```

---

## 10.8 AWS Config — Resource Configuration Compliance

Config continuously records the configuration of AWS resources and evaluates against rules.

```bash
# Enable Config
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123456:role/config-role",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "my-config-logs",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

aws configservice start-configuration-recorder --configuration-recorder-name default

# Add a managed rule — check all S3 buckets are not publicly accessible
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    }
  }'

# Check compliance
aws configservice describe-compliance-by-config-rule \
  --config-rule-names s3-bucket-public-read-prohibited

# View resource history (what did this S3 bucket look like 3 days ago?)
aws configservice get-resource-config-history \
  --resource-type AWS::S3::Bucket \
  --resource-id my-bucket \
  --later-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --limit 5
```

---

## 10.9 Key Monitoring Metrics to Track

```
┌──────────────────────────────────────────────────────────────┐
│              ESSENTIAL METRICS CHEATSHEET                    │
├─────────────────────┬────────────────────────────────────────┤
│ EC2                 │ CPUUtilization, NetworkIn/Out,         │
│                     │ StatusCheckFailed, DiskReadOps         │
├─────────────────────┼────────────────────────────────────────┤
│ RDS                 │ CPUUtilization, FreeStorageSpace,      │
│                     │ DatabaseConnections, ReadLatency,      │
│                     │ WriteLatency, FreeableMemory           │
├─────────────────────┼────────────────────────────────────────┤
│ Lambda              │ Invocations, Errors, Throttles,        │
│                     │ Duration, ConcurrentExecutions,        │
│                     │ IteratorAge (SQS/Kinesis trigger)      │
├─────────────────────┼────────────────────────────────────────┤
│ ALB                 │ RequestCount, HTTPCode_ELB_5XX_Count,  │
│                     │ TargetResponseTime, HealthyHostCount   │
├─────────────────────┼────────────────────────────────────────┤
│ ECS/Fargate         │ CPUUtilization, MemoryUtilization,     │
│                     │ RunningTaskCount                       │
├─────────────────────┼────────────────────────────────────────┤
│ SQS                 │ ApproximateNumberOfMessagesVisible,    │
│                     │ ApproximateAgeOfOldestMessage          │
│                     │ (DLQ depth!)                           │
├─────────────────────┼────────────────────────────────────────┤
│ DynamoDB            │ ConsumedReadCapacityUnits,             │
│                     │ ConsumedWriteCapacityUnits,            │
│                     │ SystemErrors, ThrottledRequests        │
└─────────────────────┴────────────────────────────────────────┘
```

---

## 10.10 Interview Questions

**Q: What is the difference between CloudWatch and CloudTrail?**
> CloudWatch monitors the **performance and health** of AWS resources and applications — CPU, memory, error counts, latency — and triggers alarms. CloudTrail records **API activity** — who made what API call, when, from which IP. CloudWatch answers "is my system healthy?"; CloudTrail answers "who did this and when?". Both are essential for production systems.

**Q: How would you debug a slow Lambda function?**
> (1) Check CloudWatch Logs for ERROR messages or slow queries. (2) Enable X-Ray tracing to see exactly where time is spent (DB calls, external APIs, cold start overhead). (3) Look at CloudWatch Metrics: Duration P95/P99 tells you worst-case latency, IteratorAge tells you queue backlog for SQS triggers. (4) Check if it's a cold start — provisioned concurrency eliminates this. (5) Use CloudWatch Insights to query logs for patterns over time.

**Q: How would you set up alerting for a production outage?**
> Multi-layer approach: (1) ALB 5xx alarm → SNS → PagerDuty/Slack within 1 minute. (2) Lambda error rate alarm. (3) RDS connection errors and latency alarms. (4) SQS DLQ depth alarm (messages failing to process). (5) Custom application health metric. (6) CloudWatch Synthetics (canary) — scheduled test that hits the API every minute and alarms if it fails. This ensures you're alerted within 1-2 minutes of any customer-facing issue.
