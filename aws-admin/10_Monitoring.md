# Chapter 10: Monitoring — CloudWatch, CloudTrail, X-Ray & AWS Config
## Observability, Logging, Tracing, Auditing, and Compliance

---

## 10.1 Observability Overview

The three pillars of observability:

```
┌──────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY PILLARS                           │
├────────────────────┬─────────────────────────────────────────────┤
│ Metrics            │ Numerical measurements over time            │
│                    │ AWS: CloudWatch Metrics                      │
│                    │ e.g., CPUUtilization, RequestCount          │
├────────────────────┼─────────────────────────────────────────────┤
│ Logs               │ Timestamped text records of events          │
│                    │ AWS: CloudWatch Logs                         │
│                    │ e.g., application logs, access logs         │
├────────────────────┼─────────────────────────────────────────────┤
│ Traces             │ Request lifecycle across distributed systems │
│                    │ AWS: X-Ray                                   │
│                    │ e.g., API call → Lambda → DB duration       │
└────────────────────┴─────────────────────────────────────────────┘

AWS Monitoring Tools:
  CloudWatch:    Metrics, alarms, dashboards, logs, anomaly detection
  CloudTrail:    API call audit trail (who did what, when)
  X-Ray:         Distributed tracing for applications
  AWS Config:    Resource configuration history and compliance rules
  GuardDuty:     Threat detection (see Chapter 11)
  Security Hub:  Security posture aggregation (see Chapter 11)
```

---

## 10.2 CloudWatch Metrics

### Key Concepts

```
Namespace:   Container for related metrics (e.g., AWS/EC2, AWS/Lambda)
Metric:      Named measurement (e.g., CPUUtilization)
Dimension:   Name-value pair to filter metrics (e.g., InstanceId=i-0abc)
Datapoint:   A single value at a specific time
Statistics:  Average, Sum, Min, Max, SampleCount, p99, p95
Period:      Granularity of data aggregation (60s, 300s, etc.)
```

```bash
# List metrics for EC2
aws cloudwatch list-metrics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc123

# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc123 \
  --start-time 2025-01-15T00:00:00Z \
  --end-time 2025-01-15T23:59:59Z \
  --period 3600 \
  --statistics Average Maximum

# Get metric data (more flexible, handles multiple metrics)
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {
      "Id": "cpu",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/EC2",
          "MetricName": "CPUUtilization",
          "Dimensions": [{"Name": "InstanceId", "Value": "i-0abc123"}]
        },
        "Period": 300,
        "Stat": "Average"
      }
    }
  ]' \
  --start-time 2025-01-15T00:00:00Z \
  --end-time 2025-01-15T23:59:59Z
```

### Custom Metrics

```bash
# Publish custom metric from CLI
aws cloudwatch put-metric-data \
  --namespace "MyApp/Business" \
  --metric-data '[
    {
      "MetricName": "OrdersPerMinute",
      "Dimensions": [
        {"Name": "Environment", "Value": "prod"},
        {"Name": "Region", "Value": "us-east-1"}
      ],
      "Value": 42.0,
      "Unit": "Count"
    }
  ]'
```

```python
# Publish custom metrics from application
import boto3
import time
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

class MetricsPublisher:
    def __init__(self, namespace: str, dimensions: list):
        self.namespace = namespace
        self.dimensions = dimensions
        self.buffer = []
    
    def record(self, name: str, value: float, unit: str = 'Count'):
        self.buffer.append({
            'MetricName': name,
            'Dimensions': self.dimensions,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        })
        
        # Flush every 20 metrics (API limit per call)
        if len(self.buffer) >= 20:
            self.flush()
    
    def flush(self):
        if not self.buffer:
            return
        cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=self.buffer
        )
        self.buffer = []

# Usage
metrics = MetricsPublisher(
    namespace="MyApp/Orders",
    dimensions=[{"Name": "Environment", "Value": "prod"}]
)

def process_order(order):
    start = time.time()
    success = execute_order(order)
    duration = (time.time() - start) * 1000  # ms
    
    metrics.record('OrderProcessingTime', duration, 'Milliseconds')
    metrics.record('OrdersProcessed', 1, 'Count')
    if not success:
        metrics.record('OrderFailures', 1, 'Count')
```

---

## 10.3 CloudWatch Alarms

### Simple Alarms

```bash
# CPU alarm → SNS
aws cloudwatch put-metric-alarm \
  --alarm-name prod-ec2-high-cpu \
  --alarm-description "EC2 CPU > 80% for 5 minutes" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=prod-asg \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \            # 2 consecutive periods
  --datapoints-to-alarm 2 \           # Both periods must breach
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123:ops-alerts \
  --ok-actions arn:aws:sns:us-east-1:123:ops-alerts \
  --insufficient-data-actions arn:aws:sns:us-east-1:123:ops-alerts

# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-errors-high \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=order-processor \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123:ops-alerts

# ALB 5xx error rate alarm (using metric math)
aws cloudwatch put-metric-alarm \
  --alarm-name alb-5xx-rate-high \
  --metrics '[
    {
      "Id": "errors",
      "MetricStat": {
        "Metric": {"Namespace": "AWS/ApplicationELB", "MetricName": "HTTPCode_Target_5XX_Count",
          "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc"}]},
        "Period": 60, "Stat": "Sum"
      }
    },
    {
      "Id": "total",
      "MetricStat": {
        "Metric": {"Namespace": "AWS/ApplicationELB", "MetricName": "RequestCount",
          "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc"}]},
        "Period": 60, "Stat": "Sum"
      }
    },
    {
      "Id": "error_rate",
      "Expression": "errors/total*100",
      "Label": "5xx Error Rate %"
    }
  ]' \
  --comparison-operator GreaterThanThreshold \
  --threshold 5 \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123:ops-critical

# Anomaly detection alarm (ML-based)
aws cloudwatch put-metric-alarm \
  --alarm-name request-count-anomaly \
  --metrics '[
    {
      "Id": "requests",
      "MetricStat": {
        "Metric": {"Namespace": "AWS/ApplicationELB", "MetricName": "RequestCount",
          "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc"}]},
        "Period": 300, "Stat": "Sum"
      }
    },
    {
      "Id": "anomaly_band",
      "Expression": "ANOMALY_DETECTION_BAND(requests, 3)",
      "Label": "Request Count (expected)"
    }
  ]' \
  --comparison-operator GreaterThanUpperThreshold \
  --threshold-metric-id anomaly_band \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123:ops-alerts

# Composite alarm (page only if BOTH CPU and memory are high)
aws cloudwatch put-composite-alarm \
  --alarm-name prod-resource-critical \
  --alarm-rule "ALARM(prod-ec2-high-cpu) AND ALARM(prod-ec2-high-memory)" \
  --alarm-actions arn:aws:sns:us-east-1:123:pagerduty-critical
```

---

## 10.4 CloudWatch Logs

```bash
# Create log group with retention
aws logs create-log-group \
  --log-group-name /app/prod/my-service \
  --kms-key-id arn:aws:kms:us-east-1:123:key/abc \
  --tags Environment=prod,Service=my-service

aws logs put-retention-policy \
  --log-group-name /app/prod/my-service \
  --retention-in-days 90

# Subscribe to CloudWatch Logs (stream logs to Lambda/Kinesis/Firehose)
aws logs put-subscription-filter \
  --log-group-name /app/prod/my-service \
  --filter-name error-stream \
  --filter-pattern "ERROR" \
  --destination-arn arn:aws:lambda:us-east-1:123:function:log-processor

# Create metric filter (count errors from logs)
aws logs put-metric-filter \
  --log-group-name /app/prod/my-service \
  --filter-name error-count \
  --filter-pattern "[timestamp, level=ERROR, ...]" \
  --metric-transformations '[{
    "metricName": "ApplicationErrors",
    "metricNamespace": "MyApp/Logs",
    "metricValue": "1",
    "unit": "Count"
  }]'

# Search logs with tail
aws logs tail /app/prod/my-service \
  --follow \              # Stream live
  --filter-pattern "ERROR"

# Query logs with CloudWatch Logs Insights
aws logs start-query \
  --log-group-names /app/prod/my-service \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message
    | filter @message like /ERROR/
    | stats count() as error_count by bin(5m)
    | sort @timestamp desc
    | limit 100'

# Get query results
aws logs get-query-results --query-id <id-from-above>
```

### CloudWatch Logs Insights Query Examples

```
# Top 10 slowest API endpoints
fields @timestamp, method, path, duration
| filter duration > 1000
| stats avg(duration) as avg_duration, count() as requests by path
| sort avg_duration desc
| limit 10

# Error rate by Lambda function
fields @timestamp, @logStream, @message
| filter @message like "ERROR"
| stats count() as errors by @logStream
| sort errors desc

# 4xx/5xx rate per hour
fields @timestamp, status
| filter status >= 400
| stats count(*) as error_count by bin(1h), status
| sort @timestamp desc

# Lambda cold starts
fields @requestId, @initDuration
| filter @initDuration > 0
| stats count() as cold_starts, avg(@initDuration) as avg_init by bin(1h)

# P99 latency by endpoint  
fields @timestamp, path, duration
| filter ispresent(duration)
| stats pct(duration, 99) as p99, pct(duration, 95) as p95, avg(duration) as avg by path
| sort p99 desc
```

---

## 10.5 CloudWatch Dashboards

```python
# Create dashboard via API
import json

dashboard_body = {
    "widgets": [
        {
            "type": "metric",
            "x": 0, "y": 0,
            "width": 12, "height": 6,
            "properties": {
                "title": "API Request Count & Latency",
                "view": "timeSeries",
                "metrics": [
                    ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/prod-alb/abc"],
                    ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/prod-alb/abc", {"stat": "p99"}]
                ],
                "period": 60,
                "yAxis": {"left": {"label": "Requests", "min": 0}},
                "annotations": {
                    "horizontal": [{"value": 1000, "label": "Capacity limit", "color": "#ff0000"}]
                }
            }
        },
        {
            "type": "metric",
            "x": 12, "y": 0,
            "width": 12, "height": 6,
            "properties": {
                "title": "Error Rates",
                "view": "timeSeries",
                "metrics": [
                    ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", "app/prod-alb/abc", {"stat": "Sum"}],
                    ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "app/prod-alb/abc", {"stat": "Sum", "color": "#ff0000"}]
                ]
            }
        },
        {
            "type": "alarm",
            "x": 0, "y": 6,
            "width": 24, "height": 4,
            "properties": {
                "title": "Production Alarms",
                "alarms": [
                    "arn:aws:cloudwatch:us-east-1:123:alarm:prod-ec2-high-cpu",
                    "arn:aws:cloudwatch:us-east-1:123:alarm:lambda-errors-high",
                    "arn:aws:cloudwatch:us-east-1:123:alarm:alb-5xx-rate-high"
                ]
            }
        }
    ]
}

cloudwatch = boto3.client('cloudwatch')
cloudwatch.put_dashboard(
    DashboardName='prod-overview',
    DashboardBody=json.dumps(dashboard_body)
)
```

---

## 10.6 CloudTrail — API Audit Logging

CloudTrail records every API call made in your AWS account (who, what, when, from where).

```bash
# Create trail (multi-region, with log file validation)
aws cloudtrail create-trail \
  --name prod-trail \
  --s3-bucket-name my-cloudtrail-logs \
  --is-multi-region-trail \
  --enable-log-file-validation \  # Detect log tampering
  --kms-key-id arn:aws:kms:us-east-1:123:key/abc \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123:log-group:CloudTrail \
  --cloud-watch-logs-role-arn arn:aws:iam::123:role/CloudTrailCWLogsRole \
  --include-global-service-events \  # Include IAM, STS, etc.
  --tags Key=Purpose,Value=security-audit

# Enable trail
aws cloudtrail start-logging --name prod-trail

# Enable data events (S3 object-level, Lambda invocations — adds cost!)
aws cloudtrail put-event-selectors \
  --trail-name prod-trail \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": ["arn:aws:s3:::sensitive-bucket/"]
        },
        {
          "Type": "AWS::Lambda::Function",
          "Values": ["arn:aws:lambda:us-east-1:123:function:critical-function"]
        }
      ]
    }
  ]'

# Validate log file integrity
aws cloudtrail validate-logs \
  --trail-arn arn:aws:cloudtrail:us-east-1:123:trail/prod-trail \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-15T23:59:59Z \
  --verbose

# Lookup events (last 90 days searchable without S3)
aws cloudtrail lookup-events \
  --lookup-attributes \
    AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time 2025-01-01T00:00:00Z \
  --query "Events[*].[EventTime,Username,EventName,Resources]" \
  --output table

# Find who deleted something
aws cloudtrail lookup-events \
  --lookup-attributes \
    AttributeKey=ResourceName,AttributeValue=my-critical-bucket \
  --max-results 50

# CloudTrail Lake — SQL queries on audit events (long retention, fast queries)
# Create event data store
aws cloudtrail create-event-data-store \
  --name prod-audit-lake \
  --advanced-event-selectors '[{
    "Name": "All events",
    "FieldSelectors": [{"Field": "eventCategory", "Equals": ["Management"]}]
  }]' \
  --multi-region-enabled \
  --organization-enabled \
  --retention-period 2555   # 7 years

# Query Lake
aws cloudtrail start-query \
  --query-statement "SELECT eventName, userIdentity.arn, eventTime FROM prod-audit-lake
    WHERE eventName = 'DeleteBucket'
    AND eventTime > '2025-01-01 00:00:00'
    ORDER BY eventTime DESC"
```

---

## 10.7 AWS X-Ray — Distributed Tracing

X-Ray helps you analyze and debug distributed applications by tracing requests through services.

```
X-Ray Concepts:
  Trace:    Complete journey of a request (segments stitched together)
  Segment:  Record for one service (e.g., your Lambda function)
  Subsegment: Record for work within a segment (DB query, HTTP call)
  Annotation: Key-value pairs indexed for filtering (e.g., user_id, order_id)
  Metadata:   Key-value pairs NOT indexed (any size data)
  Sampling:   Rate at which traces are captured (reduce cost/overhead)
  Group:      Filter expression for segmenting traces (e.g., errors only)
```

```bash
# Enable X-Ray for Lambda
aws lambda update-function-configuration \
  --function-name my-function \
  --tracing-config Mode=Active  # Active = always trace; PassThrough = only if upstream requests it

# Enable X-Ray for API Gateway
aws apigateway update-stage \
  --rest-api-id $REST_API_ID \
  --stage-name prod \
  --patch-operations op=replace,path=/tracingEnabled,value=true

# Configure sampling rules (reduce cost)
aws xray create-sampling-rule \
  --sampling-rule '{
    "RuleName": "high-priority-traces",
    "Priority": 1,
    "FixedRate": 0.05,
    "ReservoirSize": 10,
    "ServiceName": "order-service",
    "ServiceType": "AWS::Lambda::Function",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1,
    "Attributes": {"env": "prod"}
  }'

# Create trace group (filter for dashboard/alerting)
aws xray create-group \
  --group-name errors-only \
  --filter-expression "fault = true OR error = true" \
  --insights-configuration InsightsEnabled=true
```

### X-Ray with Python Lambda

```python
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core import patch

# Patch all supported libraries (boto3, requests, psycopg2, etc.)
patch_all()

@xray_recorder.capture('process_order')
def process_order(order_id: str) -> dict:
    # This creates a subsegment named 'process_order'
    
    # Add annotations (searchable/filterable)
    xray_recorder.current_subsegment().put_annotation('order_id', order_id)
    xray_recorder.current_subsegment().put_annotation('environment', 'prod')
    
    # Add metadata (not indexed, any data)
    xray_recorder.current_subsegment().put_metadata('order_details', {
        'order_id': order_id,
        'processing_start': time.time()
    })
    
    with xray_recorder.in_subsegment('database_query') as sub:
        sub.put_annotation('db_name', 'orders_db')
        result = db.get_order(order_id)
    
    with xray_recorder.in_subsegment('external_api_call') as sub:
        sub.put_annotation('service', 'payment-gateway')
        payment_result = call_payment_api(result)
    
    return payment_result

def handler(event, context):
    order_id = event['pathParameters']['orderId']
    
    # Add trace annotation at root level
    xray_recorder.current_segment().put_annotation('user_id', 
        event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub'))
    
    result = process_order(order_id)
    return {'statusCode': 200, 'body': json.dumps(result)}
```

---

## 10.8 AWS Config — Resource Configuration Compliance

AWS Config continuously monitors and records AWS resource configurations, enabling compliance rules and change history.

```bash
# Set up Config recorder
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123:role/AWSConfigRole",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

# Set delivery channel (where Config stores data)
aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "my-config-bucket",
    "snsTopicARN": "arn:aws:sns:us-east-1:123:config-alerts",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

aws configservice start-configuration-recorder --configuration-recorder-name default

# ── MANAGED RULES ─────────────────────────────────────────────
# Check S3 bucket public access
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    }
  }'

# Require MFA for console access
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "root-mfa-enabled",
    "Source": {"Owner": "AWS", "SourceIdentifier": "ROOT_ACCOUNT_MFA_ENABLED"}
  }'

# Required tags on EC2 instances
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags-ec2",
    "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
    "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\"}",
    "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance"]}
  }'

# ── CONFORMANCE PACKS ─────────────────────────────────────────
# Deploy a set of rules (security baseline)
aws configservice put-conformance-pack \
  --conformance-pack-name security-baseline \
  --template-s3-uri s3://my-config-templates/security-baseline.yaml \
  # OR use AWS-managed templates:
  # --template-body "$(cat aws-security-best-practices.yaml)"

# Check compliance
aws configservice describe-compliance-by-config-rule \
  --config-rule-names s3-bucket-public-read-prohibited \
  --compliance-types NON_COMPLIANT

# Get non-compliant resources
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-bucket-public-read-prohibited \
  --compliance-types NON_COMPLIANT

# Config Aggregator (multi-account/region view)
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-aggregator \
  --organization-aggregation-source '{
    "RoleArn": "arn:aws:iam::123:role/ConfigAggregatorRole",
    "AllAwsRegions": true
  }'
```

---

## 10.9 CloudWatch Agent on EC2

```bash
# Install CloudWatch agent via SSM
aws ssm send-command \
  --instance-ids i-0abc123 \
  --document-name "AWS-ConfigureAWSPackage" \
  --parameters '{"action":["Install"],"name":["AmazonCloudWatchAgent"]}'

# Configure agent (collect memory, disk, custom logs)
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "namespace": "CWAgent",
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}",
      "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
    },
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": ["used_percent", "inodes_free"],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      },
      "statsd": {
        "service_address": ":8125",
        "metrics_collection_interval": 10
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/application.log",
            "log_group_name": "/app/prod/my-service",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S"
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/nginx/prod/access",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s
```

---

## 10.10 Interview Q&A

**Q: What is the difference between CloudWatch and CloudTrail?**
A: CloudWatch monitors AWS resource performance and application health — metrics, logs, and alarms for operational monitoring (CPU usage, error rates, latency). CloudTrail is a security and audit service that records every AWS API call — who did what, when, and from where (create/modify/delete resources). CloudWatch answers "is my system healthy?"; CloudTrail answers "who changed what?"

**Q: What are the three types of CloudWatch alarms?**
A: (1) Metric alarms: trigger based on a single CloudWatch metric crossing a threshold; (2) Composite alarms: combine multiple alarms with AND/OR logic to reduce alert noise; (3) Anomaly detection alarms: use ML to establish a baseline and alert when metrics deviate beyond expected bands.

**Q: How do you debug a Lambda function in production using CloudWatch?**
A: Multiple tools: (1) CloudWatch Logs — Lambda automatically writes stdout/stderr to log groups; use Logs Insights to query; (2) CloudWatch Metrics — monitor Duration, Errors, Throttles, ConcurrentExecutions; (3) X-Ray — enable active tracing to see request flows and identify slow operations; (4) Lambda Power Tuning — identify optimal memory/cost configuration; (5) Lambda Destinations — capture failed invocations with full event context.

**Q: What is an AWS Config conformance pack?**
A: A conformance pack is a collection of AWS Config rules and remediation actions packaged as a single deployable unit. It simplifies deploying a compliance standard (like CIS AWS Benchmarks, PCI-DSS, HIPAA) across your organization. AWS provides pre-built templates; you can customize or create your own. Conformance packs provide an aggregate compliance score.

**Q: What is CloudTrail log file validation and why is it important?**
A: Log file validation creates a cryptographic hash (SHA-256) of each log file delivered to S3 and stores it in a digest file. This allows you to verify that log files haven't been tampered with or deleted after delivery. Important for compliance and forensics — proves that audit logs are complete and unaltered. Enable with `--enable-log-file-validation` when creating a trail.

**Q: How does X-Ray sampling work?**
A: X-Ray samples a subset of requests to trace (tracing all requests would add latency and cost). The default sampling rule traces 1 request per second per reservoir plus 5% of additional requests. Custom sampling rules can match on service name, HTTP method, URL path, or custom attributes. For latency-sensitive paths, you can reduce sampling; for critical operations or debugging, you can increase to 100%.

**Q: What are CloudWatch Logs Insights and when would you use it?**
A: Logs Insights is an interactive query service for CloudWatch Logs using a purpose-built query language. Use it when: searching logs across many log streams simultaneously; analyzing patterns (error frequency, response times); creating dashboards from log data; debugging by correlating log events across services. Queries are charged per GB scanned, so use time filters and specific log groups to minimize cost.
