# Chapter 7: Monitoring, Logging & Remediation

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 1**: Monitoring, Logging, and Remediation (20% of exam — highest weight!)
- Expect 10-14 questions on CloudWatch, CloudTrail, Config, EventBridge

---

## 7.1 Monitoring Strategy Overview

```
┌─────────────────────────────────────────────────────────────┐
│               AWS OBSERVABILITY STACK                        │
│                                                             │
│  METRICS (What happened)          LOGS (Why it happened)   │
│  ├── CloudWatch Metrics           ├── CloudWatch Logs       │
│  ├── Container Insights           ├── CloudTrail           │
│  └── Lambda Insights              └── VPC Flow Logs         │
│                                                             │
│  TRACES (Where it happened)       EVENTS (When it happened)│
│  └── AWS X-Ray                    ├── CloudWatch Events     │
│                                   └── EventBridge           │
│                                                             │
│  COMPLIANCE (Was it allowed?)     HEALTH (Is it healthy?)  │
│  └── AWS Config                   └── AWS Health Dashboard  │
│                                                             │
│  SECURITY (Was it safe?)          COST (Was it efficient?) │
│  └── GuardDuty, Security Hub      └── Cost Explorer        │
└─────────────────────────────────────────────────────────────┘
```

---

## 7.2 Amazon CloudWatch — Metrics

CloudWatch collects metrics from AWS services and your applications.

### Key Concepts

| Concept | Definition |
|---------|-----------|
| **Namespace** | Container for metrics (e.g., `AWS/EC2`, `AWS/RDS`) |
| **Metric** | Time-ordered set of data points (e.g., CPUUtilization) |
| **Dimension** | Name-value pair that filters metrics (e.g., InstanceId=i-xxx) |
| **Period** | Length of time for a data point (default 60 seconds) |
| **Statistics** | Average, Sum, Min, Max, SampleCount, Percentile |
| **Alarm** | Watches metric and takes action when threshold crossed |
| **Dashboard** | Visual display of metrics |

### Default vs Detailed Monitoring
| Type | Cost | Frequency |
|------|------|-----------|
| Basic Monitoring | Free | 5-minute data points |
| Detailed Monitoring | $0.01/metric/month | 1-minute data points |

```bash
# Enable detailed monitoring on EC2 instance
aws ec2 monitor-instances --instance-ids i-1234567890abcdef0

# Get CPU metric for last hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average Maximum \
  --output table
```

### Custom Metrics
```python
import boto3
import psutil  # pip install psutil
from datetime import datetime, timezone

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def publish_custom_metrics():
    """Publish custom application metrics to CloudWatch."""
    
    # System metrics not included in standard CloudWatch
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    cloudwatch.put_metric_data(
        Namespace='MyApp/System',
        MetricData=[
            {
                'MetricName': 'MemoryUtilization',
                'Dimensions': [
                    {'Name': 'InstanceId', 'Value': get_instance_id()},
                    {'Name': 'Environment', 'Value': 'production'}
                ],
                'Value': memory.percent,
                'Unit': 'Percent',
                'Timestamp': datetime.now(timezone.utc)
            },
            {
                'MetricName': 'DiskUtilization',
                'Dimensions': [
                    {'Name': 'InstanceId', 'Value': get_instance_id()},
                    {'Name': 'MountPath', 'Value': '/'}
                ],
                'Value': disk.percent,
                'Unit': 'Percent',
                'Timestamp': datetime.now(timezone.utc)
            },
            {
                'MetricName': 'ActiveConnections',
                'Dimensions': [
                    {'Name': 'ServiceName', 'Value': 'api-server'}
                ],
                'Value': get_active_connections(),
                'Unit': 'Count',
                'Timestamp': datetime.now(timezone.utc)
            }
        ]
    )

# Publish using high-resolution metric (1-second granularity)
cloudwatch.put_metric_data(
    Namespace='MyApp/Performance',
    MetricData=[{
        'MetricName': 'RequestLatencyP99',
        'Value': 145.3,
        'Unit': 'Milliseconds',
        'StorageResolution': 1  # 1 second (vs default 60 seconds)
    }]
)
```

### CloudWatch Agent
Runs on EC2/on-premises to collect detailed metrics and logs:

```json
// cloudwatch-agent-config.json
{
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["disk_used_percent"],
        "resources": ["/", "/var"],
        "metrics_collection_interval": 60
      },
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60,
        "totalcpu": true
      },
      "diskio": {
        "measurement": ["reads", "writes", "read_bytes", "write_bytes"],
        "resources": ["*"],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": ["tcp_established", "tcp_time_wait"],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/production/nginx/access",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/app/*.log",
            "log_group_name": "/production/app/logs",
            "log_stream_name": "{hostname}-{instance_id}",
            "multi_line_start_pattern": "\\d{4}-\\d{2}-\\d{2}"
          }
        ]
      }
    }
  }
}
```

```bash
# Install and configure CloudWatch agent via SSM
aws ssm put-parameter \
  --name /cloudwatch-agent/config \
  --type String \
  --value file://cloudwatch-agent-config.json

# Start agent via SSM Run Command (on all EC2 instances with tag)
aws ssm send-command \
  --document-name AWS-ConfigureAWSPackage \
  --parameters '{"action":["Install"],"name":["AmazonCloudWatchAgent"]}' \
  --targets '[{"Key":"tag:Monitoring","Values":["enabled"]}]'

aws ssm send-command \
  --document-name AmazonCloudWatch-ManageAgent \
  --parameters '{"action":["configure","start"],"mode":["ec2"],"optionalConfigurationSource":["ssm"],"optionalConfigurationLocation":["/cloudwatch-agent/config"]}' \
  --targets '[{"Key":"tag:Monitoring","Values":["enabled"]}]'
```

---

## 7.3 CloudWatch Alarms

Alarms watch a metric and trigger actions when the metric crosses a threshold.

### Alarm States
```
┌──────────────────────────────────────────────────────────────┐
│                   ALARM STATES                               │
│                                                              │
│  OK          — metric within acceptable range               │
│  ALARM       — metric outside threshold                     │
│  INSUFFICIENT_DATA — not enough data to evaluate           │
└──────────────────────────────────────────────────────────────┘
```

### Creating Effective Alarms
```bash
# High CPU alarm with SNS notification
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-web-high-cpu" \
  --alarm-description "CPU > 80% for 5 consecutive minutes" \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=prod-web-asg \
  --statistic Average \
  --period 60 \
  --evaluation-periods 5 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
  --ok-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
  --insufficient-data-actions arn:aws:sns:us-east-1:123456789012:ops-alerts

# RDS storage alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-low-storage" \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=prod-postgres \
  --statistic Average \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 10000000000 \  # 10 GB in bytes
  --comparison-operator LessThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts

# Composite alarm (alarm when BOTH conditions true)
aws cloudwatch put-composite-alarm \
  --alarm-name "prod-critical-alert" \
  --alarm-rule "ALARM(prod-web-high-cpu) AND ALARM(prod-web-high-error-rate)" \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:pagerduty-critical

# Anomaly detection alarm (ML-based threshold)
aws cloudwatch put-metric-alarm \
  --alarm-name "requests-anomaly" \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/xxx \
  --extended-statistic p99 \
  --period 300 \
  --evaluation-periods 3 \
  --comparison-operator GreaterThanUpperThreshold \
  --threshold-metric-id e1 \
  --metrics '[{
    "Id": "m1",
    "MetricStat": {
      "Metric": {"Namespace":"AWS/ApplicationELB","MetricName":"RequestCount","Dimensions":[{"Name":"LoadBalancer","Value":"app/prod-alb/xxx"}]},
      "Period": 300,
      "Stat": "Sum"
    }
  },{
    "Id": "e1",
    "Expression": "ANOMALY_DETECTION_BAND(m1, 2)"
  }]'
```

---

## 7.4 CloudWatch Logs

### Log Groups & Retention
```bash
# Create log group with retention
aws logs create-log-group --log-group-name /production/app/api

aws logs put-retention-policy \
  --log-group-name /production/app/api \
  --retention-in-days 90

# Encrypt log group with KMS
aws logs associate-kms-key \
  --log-group-name /production/app/api \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id

# Set retention on ALL log groups that don't have it (automation)
aws logs describe-log-groups \
  --query 'logGroups[?!retentionInDays].[logGroupName]' \
  --output text | \
  xargs -I{} aws logs put-retention-policy \
    --log-group-name {} \
    --retention-in-days 90
```

### CloudWatch Logs Insights
Powerful query language for analyzing log data:

```bash
# Query: Find top error messages in last hour
aws logs start-query \
  --log-group-name /production/app/api \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message, level, errorMessage
    | filter level = "ERROR"
    | stats count(*) as errorCount by errorMessage
    | sort errorCount desc
    | limit 20
  '

# Query: Average response time by endpoint
aws logs start-query \
  --log-group-name /production/nginx/access \
  --start-time $(date -d '1 day ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, method, path, status, responseTime
    | filter status >= 400
    | stats avg(responseTime) as avgResponseTime, count(*) as requests, count(status >= 500) as serverErrors by path
    | sort requests desc
    | limit 50
  '

# Query: IP addresses making most requests
aws logs start-query \
  --log-group-name /aws/vpc/flowlogs \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields srcAddr, dstAddr, dstPort, action, bytes
    | filter action = "REJECT"
    | stats count(*) as rejectedRequests, sum(bytes) as totalBytes by srcAddr
    | sort rejectedRequests desc
    | limit 25
  '
```

### Metric Filters (Logs → Metrics)
```bash
# Create metric filter: count HTTP 5xx errors from logs
aws logs put-metric-filter \
  --log-group-name /production/nginx/access \
  --filter-name http-5xx-errors \
  --filter-pattern '[ip, id, user, timestamp, request, status_code=5*, bytes]' \
  --metric-transformations '[{
    "metricName": "HTTP5xxErrors",
    "metricNamespace": "Production/Application",
    "metricValue": "1",
    "defaultValue": 0,
    "unit": "Count"
  }]'

# Create alarm on the custom metric
aws cloudwatch put-metric-alarm \
  --alarm-name "http-5xx-errors-high" \
  --namespace Production/Application \
  --metric-name HTTP5xxErrors \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

### Logs Subscriptions (Real-time processing)
```bash
# Stream logs to Lambda for real-time processing
aws logs put-subscription-filter \
  --log-group-name /production/app/api \
  --filter-name stream-to-lambda \
  --filter-pattern 'ERROR' \
  --destination-arn arn:aws:lambda:us-east-1:123456789012:function:LogProcessor

# Stream logs to OpenSearch for full-text search
aws logs put-subscription-filter \
  --log-group-name /production/app/api \
  --filter-name stream-to-opensearch \
  --filter-pattern '' \
  --destination-arn arn:aws:logs:us-east-1:123456789012:destination:opensearch-destination
```

---

## 7.5 AWS CloudTrail

CloudTrail records **API calls** made to AWS — who did what, when, and from where.

### Key Concepts

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDTRAIL                                │
│                                                             │
│  EVENT TYPES:                                               │
│  • Management Events  — control plane (default logged)      │
│    CreateBucket, RunInstances, DeleteUser, etc.             │
│  • Data Events        — data plane (not default, extra cost)│
│    S3:GetObject, Lambda:Invoke, DynamoDB:PutItem, etc.      │
│  • Insights Events    — unusual API activity (ML-based)     │
│                                                             │
│  TRAILS:                                                    │
│  • Single Region — logs only current region                 │
│  • Multi-Region  — logs all regions (recommended)           │
│  • Organization Trail — covers all accounts in org          │
│                                                             │
│  STORAGE: S3 (encrypted, validated, lifecycle)              │
│  ANALYSIS: CloudWatch Logs, Athena, CloudTrail Insights     │
└─────────────────────────────────────────────────────────────┘
```

### Creating a Comprehensive Trail
```bash
# Create S3 bucket for CloudTrail with required policy
aws s3api create-bucket --bucket my-cloudtrail-logs --region us-east-1

# Apply bucket policy (required for CloudTrail)
aws s3api put-bucket-policy --bucket my-cloudtrail-logs --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::my-cloudtrail-logs"
    },
    {
      "Sid": "AWSCloudTrailWrite",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-cloudtrail-logs/AWSLogs/123456789012/*",
      "Condition": {
        "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
      }
    }
  ]
}'

# Create comprehensive trail
aws cloudtrail create-trail \
  --name production-trail \
  --s3-bucket-name my-cloudtrail-logs \
  --is-multi-region-trail \
  --include-global-service-events \
  --enable-log-file-validation \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail:* \
  --cloud-watch-logs-role-arn arn:aws:iam::123456789012:role/CloudTrailToCloudWatchLogs \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id

aws cloudtrail start-logging --name production-trail

# Add data events (extra cost — only add for critical resources)
aws cloudtrail put-event-selectors \
  --trail-name production-trail \
  --event-selectors '[
    {
      "ReadWriteType": "WriteOnly",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": ["arn:aws:s3:::sensitive-data-bucket/"]
        },
        {
          "Type": "AWS::Lambda::Function",
          "Values": ["arn:aws:lambda"]
        }
      ]
    }
  ]'
```

### Querying CloudTrail with Athena
```sql
-- Create Athena table for CloudTrail logs (one-time setup)
CREATE EXTERNAL TABLE cloudtrail_logs (
    eventVersion STRING,
    userIdentity STRUCT<type:STRING, principalId:STRING, arn:STRING, accountId:STRING, 
      sessionContext:STRUCT<sessionIssuer:STRUCT<type:STRING,principalId:STRING,arn:STRING,accountId:STRING,userName:STRING>, 
      attributes:STRUCT<mfaAuthenticated:STRING,creationDate:STRING>>>,
    eventTime STRING,
    eventSource STRING,
    eventName STRING,
    awsRegion STRING,
    sourceIPAddress STRING,
    userAgent STRING,
    errorCode STRING,
    errorMessage STRING,
    requestParameters STRING,
    responseElements STRING,
    requestId STRING,
    eventId STRING,
    resources ARRAY<STRUCT<ARN:STRING,accountId:STRING,type:STRING>>,
    eventType STRING,
    recipientAccountId STRING
)
PARTITIONED BY (region STRING, year STRING, month STRING, day STRING)
ROW FORMAT SERDE 'com.amazon.emr.hive.serde.CloudTrailSerde'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://my-cloudtrail-logs/AWSLogs/123456789012/CloudTrail/'

-- Find who deleted a resource
SELECT eventTime, userIdentity.arn, sourceIPAddress, requestParameters
FROM cloudtrail_logs
WHERE eventName = 'DeleteBucket'
  AND year='2025' AND month='05'
ORDER BY eventTime DESC;

-- Find all console logins from unfamiliar IPs
SELECT eventTime, userIdentity.userName, sourceIPAddress, awsRegion
FROM cloudtrail_logs
WHERE eventName = 'ConsoleLogin'
  AND sourceIPAddress NOT LIKE '10.%'
  AND year='2025'
ORDER BY eventTime DESC;

-- Find IAM changes
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM cloudtrail_logs
WHERE eventSource = 'iam.amazonaws.com'
  AND eventName IN ('CreateUser', 'AttachRolePolicy', 'PutRolePolicy', 'CreateAccessKey')
  AND year='2025' AND month='05'
ORDER BY eventTime DESC;
```

---

## 7.6 AWS Config

AWS Config continuously evaluates the **configuration of your resources** against desired rules.

### Core Concepts
```
┌─────────────────────────────────────────────────────────────┐
│                      AWS CONFIG                              │
│                                                             │
│  CONFIGURATION ITEM — snapshot of resource at a point      │
│  in time (all attributes + relationships + metadata)        │
│                                                             │
│  CONFIGURATION HISTORY — timeline of changes to a resource  │
│                                                             │
│  CONFIGURATION SNAPSHOT — full account config at a point   │
│                                                             │
│  CONFIG RULES — desired configuration checks               │
│  ├── AWS Managed Rules (150+ built-in)                     │
│  └── Custom Rules (Lambda-backed)                          │
│                                                             │
│  CONFORMANCE PACKS — collection of Config rules + actions  │
│  (e.g., CIS AWS Foundations Benchmark)                     │
│                                                             │
│  AGGREGATORS — view config data from multiple accounts/regions│
└─────────────────────────────────────────────────────────────┘
```

### Enable AWS Config
```bash
# Create Config delivery channel
aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "my-config-bucket",
    "snsTopicARN": "arn:aws:sns:us-east-1:123456789012:config-notifications",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

# Create configuration recorder
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123456789012:role/AWSConfigRole",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

aws configservice start-configuration-recorder --configuration-recorder-name default
```

### Common AWS Config Rules
```bash
# S3 bucket should have server-side encryption
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-server-side-encryption-enabled",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
    }
  }'

# All EBS volumes should be encrypted
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "encrypted-volumes",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "ENCRYPTED_VOLUMES"
    }
  }'

# Multi-AZ enabled for RDS
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "rds-multi-az-support",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "RDS_MULTI_AZ_SUPPORT"
    }
  }'

# Required tags on EC2 instances
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "REQUIRED_TAGS"
    },
    "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"CostCenter\"}"
  }'

# Check IMDSv2 required
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-imdsv2-check",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "EC2_IMDSV2_CHECK"
    }
  }'
```

### Automatic Remediation with Config
```bash
# Auto-remediate: disable public access on non-compliant S3 buckets
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "s3-bucket-public-access-prohibited",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-DisableS3BucketPublicReadWrite",
    "Parameters": {
      "AutomationAssumeRole": {
        "StaticValue": {"Values": ["arn:aws:iam::123456789012:role/ConfigRemediationRole"]}
      },
      "BucketName": {
        "ResourceValue": {"Value": "RESOURCE_ID"}
      }
    },
    "Automatic": true,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 60
  }]'

# Check compliance status
aws configservice describe-compliance-by-config-rule \
  --config-rule-names s3-bucket-server-side-encryption-enabled \
  --compliance-types NON_COMPLIANT

# Get non-compliant resources
aws configservice describe-compliance-by-resource \
  --resource-type AWS::EC2::Instance \
  --compliance-types NON_COMPLIANT
```

---

## 7.7 Amazon EventBridge

EventBridge is the **event bus** that connects AWS services, SaaS, and custom applications.

### Event-Driven Architecture
```
Event Source                   EventBridge             Target
                              ┌───────────────┐
EC2 State Change         ──►  │               │ ──►  Lambda (tag instance)
S3 Object Created        ──►  │  Event Bus    │ ──►  SNS (notify team)
CloudTrail API Call      ──►  │               │ ──►  SQS (queue for processing)
CodePipeline State       ──►  │  Rules        │ ──►  Step Functions (workflow)
GuardDuty Finding        ──►  │  (filter +    │ ──►  Systems Manager (remediate)
Custom Application       ──►  │   route)      │ ──►  Kinesis (stream)
Schedule (cron/rate)     ──►  │               │ ──►  ECS Task (batch job)
SaaS (Zendesk, PagerDuty)──►  └───────────────┘
```

### Creating EventBridge Rules
```bash
# Rule: Send SNS alert when EC2 instance is terminated
aws events put-rule \
  --name ec2-termination-alert \
  --event-pattern '{
    "source": ["aws.ec2"],
    "detail-type": ["EC2 Instance State-change Notification"],
    "detail": {
      "state": ["terminated"]
    }
  }' \
  --state ENABLED

aws events put-targets \
  --rule ec2-termination-alert \
  --targets '[{
    "Id": "sns-target",
    "Arn": "arn:aws:sns:us-east-1:123456789012:ops-alerts",
    "InputTransformer": {
      "InputPathsMap": {
        "instance": "$.detail.instance-id",
        "region": "$.region",
        "time": "$.time"
      },
      "InputTemplate": "EC2 instance <instance> was terminated in <region> at <time>"
    }
  }]'

# Rule: Scheduled task (every day at 2 AM UTC)
aws events put-rule \
  --name daily-cleanup-job \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

aws events put-targets \
  --rule daily-cleanup-job \
  --targets '[{
    "Id": "lambda-target",
    "Arn": "arn:aws:lambda:us-east-1:123456789012:function:DailyCleanup"
  }]'

# Rule: React to GuardDuty finding
aws events put-rule \
  --name guardduty-high-severity \
  --event-pattern '{
    "source": ["aws.guardduty"],
    "detail-type": ["GuardDuty Finding"],
    "detail": {
      "severity": [{"numeric": [">=", 7]}]
    }
  }' \
  --state ENABLED
```

### Custom Event Bus (for microservices)
```python
import boto3
import json
from datetime import datetime, timezone

events = boto3.client('events')

def publish_order_event(order_id: str, event_type: str, details: dict):
    """Publish custom business event to EventBridge."""
    events.put_events(
        Entries=[
            {
                'Time': datetime.now(timezone.utc),
                'Source': 'com.myapp.orders',
                'DetailType': f'Order {event_type}',
                'Detail': json.dumps({
                    'orderId': order_id,
                    'eventType': event_type,
                    **details
                }),
                'EventBusName': 'production-event-bus'
            }
        ]
    )

# Usage
publish_order_event(
    order_id='ORD-001',
    event_type='Created',
    details={'customerId': 'CUST001', 'total': 99.99}
)
```

---

## 7.8 AWS X-Ray

X-Ray provides **distributed tracing** to debug and analyze distributed applications.

```python
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

# Auto-instrument all AWS SDK calls and HTTP requests
patch_all()

app = Flask(__name__)
xray_recorder.configure(service='order-service')
XRayMiddleware(app, xray_recorder)

@app.route('/orders/<order_id>')
@xray_recorder.capture('get_order')
def get_order(order_id):
    # This creates a subsegment in the trace
    with xray_recorder.in_subsegment('db_query') as subsegment:
        subsegment.put_annotation('orderId', order_id)
        order = db.get_order(order_id)
    
    with xray_recorder.in_subsegment('cache_lookup') as subsegment:
        cached = redis.get(f'order:{order_id}')
    
    return jsonify(order)
```

---

## 7.9 AWS Systems Manager — OpsCenter & Explorer

### OpsCenter
Centralized place to view and resolve **operational issues** (OpsItems):

```python
import boto3

ssm = boto3.client('ssm')

# Create OpsItem programmatically (e.g., from Lambda triggered by alarm)
def create_ops_item(title: str, description: str, severity: str, source: str):
    response = ssm.create_ops_item(
        Title=title,
        Description=description,
        Source=source,
        Severity=severity,  # '1' (Critical) to '4' (Low)
        Priority=1,
        Category='Availability',
        Tags=[
            {'Key': 'Environment', 'Value': 'production'},
            {'Key': 'AutoCreated', 'Value': 'true'}
        ]
    )
    return response['OpsItemId']

# Triggered by CloudWatch alarm → SNS → Lambda
def lambda_handler(event, context):
    alarm_name = event['Records'][0]['Sns']['Subject']
    message = json.loads(event['Records'][0]['Sns']['Message'])
    
    ops_item_id = create_ops_item(
        title=f"CloudWatch Alarm: {alarm_name}",
        description=f"Alarm state: {message.get('NewStateValue')}. {message.get('NewStateReason')}",
        severity='1' if 'critical' in alarm_name.lower() else '2',
        source='cloudwatch'
    )
    print(f"Created OpsItem: {ops_item_id}")
```

---

## 7.10 Real-World Project: Comprehensive Monitoring Stack

### Architecture: Monitoring Everything
```
Application Layer:
  EC2/ECS → CloudWatch Agent → CW Logs + CW Metrics
  Lambda → CloudWatch Logs (automatic) + X-Ray traces

Infrastructure Layer:
  All resources → CloudTrail (API calls) → S3 + CW Logs
  All resources → AWS Config (compliance) → Config dashboard
  VPC → VPC Flow Logs → S3 (Athena analysis)

Alerting Layer:
  CW Alarms → SNS → Email/PagerDuty/Slack
  EventBridge → Lambda → Auto-remediation
  GuardDuty → EventBridge → Security Hub → SNS

Dashboards:
  CloudWatch Dashboard: 
    - Application health (requests, errors, latency)
    - Infrastructure (CPU, memory, disk)
    - Business KPIs (orders/min, revenue)
```

### Lambda for Auto-Remediation
```python
import boto3
import json

ec2 = boto3.client('ec2')
sns = boto3.client('sns')

def lambda_handler(event, context):
    """Auto-remediate Config non-compliance or CloudWatch alarm events."""
    
    detail = event.get('detail', {})
    event_type = event.get('detail-type', '')
    
    if 'Config Rules Compliance Change' in event_type:
        rule_name = detail.get('configRuleName', '')
        resource_id = detail.get('resourceId', '')
        compliance = detail.get('newEvaluationResult', {}).get('complianceType', '')
        
        if compliance == 'NON_COMPLIANT':
            handle_non_compliance(rule_name, resource_id)
    
    elif 'EC2 Instance State-change Notification' in event_type:
        instance_id = detail.get('instance-id')
        state = detail.get('state')
        
        if state == 'running':
            # Auto-tag new instances
            auto_tag_instance(instance_id)

def handle_non_compliance(rule_name: str, resource_id: str):
    """Handle specific non-compliance scenarios."""
    
    if rule_name == 'ec2-imdsv2-check':
        # Enforce IMDSv2 on non-compliant instance
        try:
            ec2.modify_instance_metadata_options(
                InstanceId=resource_id,
                HttpTokens='required',
                HttpPutResponseHopLimit=1
            )
            print(f"✅ Enforced IMDSv2 on {resource_id}")
        except Exception as e:
            notify_ops(f"Failed to remediate {resource_id}: {str(e)}")
    
    elif rule_name == 'required-tags':
        notify_ops(f"Instance {resource_id} missing required tags. Manual action needed.")

def auto_tag_instance(instance_id: str):
    """Auto-tag instances launched without required tags."""
    instance = ec2.describe_instances(InstanceIds=[instance_id])
    # ... check existing tags, add missing ones

def notify_ops(message: str):
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:123456789012:ops-alerts',
        Subject='AWS Auto-Remediation Alert',
        Message=message
    )
```

---

## 7.11 Practice Questions (SysOps Exam Level)

**Q1:** An RDS instance failed over to the standby due to Multi-AZ. You receive a CloudWatch alarm notification 10 minutes after the failover. What should you check to improve the alert timing?

**A:** The alarm delay indicates:
1. CloudWatch metric period was too long (5 minutes) — reduce to 1 minute with detailed monitoring
2. Evaluation periods too high (e.g., 2 consecutive) — reduce to 1
3. Subscribe to **RDS Event Notifications** via SNS for immediate notification on failover events

```bash
# Subscribe to RDS events (near-instant notification)
aws rds create-event-subscription \
  --subscription-name rds-failover-alerts \
  --sns-topic-arn arn:aws:sns:us-east-1:123456789012:ops-alerts \
  --source-type db-instance \
  --event-categories availability failover
```

---

**Q2:** A developer deleted an S3 bucket containing critical data. How do you investigate and what should you have had in place?

**A:**
**Investigation:**
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time 2025-05-01 \
  --query 'Events[*].{Time:EventTime,User:Username,IP:CloudTrailEvent}' \
  --output table
```

**Prevention (should have had in place):**
1. **S3 Versioning** + **MFA Delete** — would have prevented permanent deletion
2. **S3 Object Lock** (Governance/Compliance mode) — immutable objects
3. **AWS Config rule** `s3-versioning-enabled` — detect unprotected buckets
4. **SCP** or bucket policy denying `s3:DeleteBucket`
5. **Backup** with AWS Backup

---

**Q3:** How do you monitor memory utilization on EC2 instances? CloudWatch doesn't show memory by default.

**A:** Install and configure the **CloudWatch Agent** on the EC2 instances. The agent collects OS-level metrics not available from hypervisor: memory, disk usage, processes, network.

```bash
# Install and configure CloudWatch Agent
sudo yum install amazon-cloudwatch-agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard

# After configuration, start agent
sudo systemctl enable --now amazon-cloudwatch-agent
```

The metric will appear in namespace `CWAgent` with dimension `InstanceId`.

---

**Q4:** You need to detect when someone makes an IAM change and automatically notify security. What is the architecture?

**A:**
1. **CloudTrail** → sends events to **CloudWatch Logs**
2. **CloudWatch Logs Metric Filter** → creates metric on IAM API calls
3. **CloudWatch Alarm** → triggers when metric > 0
4. **SNS** → notifies Security team

OR more elegantly:
1. **EventBridge rule** matching `source=aws.iam` events
2. **SNS target** → immediate notification
3. **Lambda target** → automated investigation (create OpsItem, check user, etc.)

---

**Q5:** AWS Config shows 47 EC2 instances are non-compliant with the `ec2-imdsv2-check` rule. You need to fix all 47 at once. What is the most efficient approach?

**A:** Use **AWS Config Automatic Remediation** with Systems Manager Automation:

```bash
# Set up automatic remediation
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "ec2-imdsv2-check",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-ModifyInstanceMetadataOptions",
    "Parameters": {
      "InstanceId": {"ResourceValue": {"Value": "RESOURCE_ID"}},
      "HttpTokens": {"StaticValue": {"Values": ["required"]}},
      "HttpPutResponseHopLimit": {"StaticValue": {"Values": ["1"]}}
    },
    "Automatic": true
  }]'

# Remediate all non-compliant resources immediately
aws configservice start-remediation-execution \
  --config-rule-name ec2-imdsv2-check \
  --resource-keys file://non-compliant-instances.json
```

---

## Key Monitoring Terms for Exam

| Term | Definition |
|------|-----------|
| CloudWatch Metric | Time-series data point from AWS service |
| CloudWatch Alarm | Watches metric, takes action on threshold |
| CloudWatch Logs | Centralized log storage and analysis |
| Logs Insights | Query language for CloudWatch Logs |
| Metric Filter | Extract metrics from log patterns |
| CloudWatch Agent | Collects OS-level metrics and logs from EC2 |
| CloudTrail | Records all AWS API calls |
| Management Events | Control plane API calls (default in CloudTrail) |
| Data Events | Data plane calls (S3 GetObject, Lambda invoke) |
| AWS Config | Evaluates resource configs against rules |
| Config Rule | Desired configuration check |
| Conformance Pack | Bundle of Config rules |
| EventBridge | Event bus connecting AWS services and custom apps |
| Event Pattern | Filter criteria for EventBridge rules |
| X-Ray | Distributed tracing for debugging |
| OpsCenter | Centralized operational issue management |
