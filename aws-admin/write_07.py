
content = r"""# Chapter 7: Monitoring — CloudWatch, CloudTrail & AWS Config
## (Eyes and Ears of Your AWS Environment)

---

## 7.1 Why Monitoring Matters

### The Problem Without Monitoring

Imagine running a restaurant without any feedback systems:
- No thermometer in the kitchen — don't know if the oven is too hot
- No register tracking orders — don't know how busy you are
- No security camera — don't know if someone is stealing
- No customer complaints system — don't know if food is bad

Your AWS infrastructure is the same. Without monitoring:
- Your web server is using 100% CPU — you don't know until users complain
- Someone is deleting IAM users — you don't notice until things break
- Your S3 bucket was made public last week — still don't know
- Your database is nearly full — you find out when it crashes

**Monitoring is not optional. It is how you operate AWS professionally.**

AWS provides three primary monitoring services:
- **CloudWatch** — metrics, logs, dashboards, alarms (the dashboard and alarm system)
- **CloudTrail** — who did what, when (the security camera footage)
- **AWS Config** — what does my infrastructure look like, is it compliant? (the auditor)

---

## 7.2 CloudWatch — Metrics, Alarms & Dashboards

### What is CloudWatch?

**CloudWatch** is AWS's comprehensive monitoring service. Think of it as the control room of your infrastructure:
- **Metrics** = numbers measured over time (CPU%, requests/sec, error count)
- **Logs** = text records of events (application logs, access logs, VPC flow logs)
- **Alarms** = rules that trigger when metrics cross thresholds
- **Dashboards** = visual displays of multiple metrics together
- **Events/EventBridge** = react to AWS service events in real time

### CloudWatch Metrics — Numbers Over Time

**Built-in AWS metrics (free for most services):**

```
EC2 metrics (reported every 5 minutes by default):
  CPUUtilization          (percentage, 0-100)
  NetworkIn               (bytes received)
  NetworkOut              (bytes sent)
  DiskReadBytes           (for instance store only)
  DiskWriteBytes          (for instance store only)
  StatusCheckFailed       (0=OK, 1=FAILED)
  StatusCheckFailed_System   (hardware/AWS issue)
  StatusCheckFailed_Instance (OS/software issue)

NOTE: EC2 does NOT report these without CloudWatch Agent:
  Memory usage (RAM)          ← must install CW agent for this!
  Disk usage percentage       ← must install CW agent!
  Custom application metrics  ← send via PutMetricData API

RDS metrics:
  CPUUtilization
  DatabaseConnections         (number of active connections)
  FreeStorageSpace            (bytes of free storage)
  ReadLatency, WriteLatency   (seconds)
  ReadIOPS, WriteIOPS
  ReplicaLag                  (for read replicas)

ALB metrics:
  RequestCount                (total requests)
  TargetResponseTime          (latency)
  HTTP_5XX_Count              (errors)
  HTTP_4XX_Count              (client errors)
  HealthyHostCount            (how many targets are healthy)
  UnHealthyHostCount          (how many are unhealthy)

S3 metrics (bucket-level, must enable in bucket settings):
  NumberOfObjects
  BucketSizeBytes
  AllRequests
```

**CloudWatch Detailed Monitoring:**
- Default: metrics every **5 minutes** (free)
- Detailed Monitoring: metrics every **1 minute** (small cost, ~$3.50/instance/month)
- Enable when you need faster alarm response

```bash
# Enable detailed monitoring on EC2
aws ec2 monitor-instances --instance-ids i-0123456789abcdef0

# Enable detailed monitoring when launching
aws ec2 run-instances \
  --image-id ami-xxx \
  --instance-type t3.medium \
  --monitoring Enabled=true

# Check a specific metric (last 1 hour, 5-minute intervals)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average,Maximum \
  --query 'Datapoints[*].[Timestamp,Average,Maximum]' \
  --output table
```

### CloudWatch Agent — For Custom and System Metrics

The CloudWatch Agent is software you install on EC2 instances to collect metrics and logs that AWS cannot see:

```bash
# Install CloudWatch Agent (Amazon Linux 2023)
sudo yum install -y amazon-cloudwatch-agent

# Create configuration file
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent", "mem_available"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["disk_used_percent", "disk_free"],
        "resources": ["/", "/data"],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": ["tcp_established", "tcp_time_wait"],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}",
      "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/aws/ec2/nginx/access",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "/aws/ec2/nginx/error",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          },
          {
            "file_path": "/var/log/app/application.log",
            "log_group_name": "/aws/ec2/app/application",
            "log_stream_name": "{instance_id}",
            "multi_line_start_pattern": "^\\d{4}-\\d{2}-\\d{2}"
          }
        ]
      }
    }
  }
}
EOF

# Start the agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Verify it is running
sudo systemctl status amazon-cloudwatch-agent
```

### CloudWatch Alarms — Automated Responses

**Alarms watch a metric and trigger actions when it crosses a threshold.**

**Three alarm states:**
```
OK      — metric is within the acceptable range
ALARM   — metric has crossed the threshold
INSUFFICIENT_DATA — not enough data to evaluate
```

**Alarm actions you can take:**
- Send SNS notification (email, SMS, HTTP webhook)
- Scale an Auto Scaling Group (add/remove instances)
- Stop, terminate, reboot, or recover an EC2 instance
- Create OpsCenter OpsItem (ticketing integration)

```bash
# Alarm: High CPU → scale out and alert
aws cloudwatch put-metric-alarm \
  --alarm-name web-server-high-cpu \
  --alarm-description "CPU > 80% for 5 minutes" \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=web-app-asg \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions \
    arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:xxx:autoScalingGroupName/web-app-asg:policyName/scale-out \
    arn:aws:sns:us-east-1:123456789012:ops-alerts

# Alarm: Database connection count too high
aws cloudwatch put-metric-alarm \
  --alarm-name rds-too-many-connections \
  --alarm-description "RDS connections > 100 for 10 minutes" \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=production-mysql \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts

# Alarm: EC2 instance status check failure → auto-recover
aws cloudwatch put-metric-alarm \
  --alarm-name ec2-auto-recover \
  --alarm-description "Recover instance on status check failure" \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed_System \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:automate:us-east-1:ec2:recover

# Billing alarm (on the total AWS bill)
aws cloudwatch put-metric-alarm \
  --alarm-name monthly-billing-alert \
  --alarm-description "Alert when monthly bill exceeds $500" \
  --namespace AWS/Billing \
  --metric-name EstimatedCharges \
  --dimensions Name=Currency,Value=USD \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:billing-alerts \
  --treat-missing-data notBreaching \
  --region us-east-1
  # Billing metrics are ONLY in us-east-1!
```

### Composite Alarms — Reducing Noise

A **Composite Alarm** combines multiple individual alarms using AND/OR logic. This reduces alert fatigue by only paging you when multiple things are wrong simultaneously.

```bash
# Example: Only alert if BOTH CPU is high AND error rate is high
# (not just CPU spike from a legitimate traffic burst)
aws cloudwatch put-composite-alarm \
  --alarm-name web-app-critical \
  --alarm-description "Alert only when both CPU and errors are high" \
  --alarm-rule "ALARM(\"web-server-high-cpu\") AND ALARM(\"high-error-rate\")" \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:pagerduty-critical
```

### CloudWatch Logs — Centralized Log Management

**CloudWatch Logs** stores log files from any source:
- EC2 application and system logs (via CW Agent)
- Lambda function logs (automatic)
- API Gateway access logs
- RDS logs (error, general, slow query)
- VPC Flow Logs
- Route 53 query logs

**Key concepts:**
```
Log Group: Container for log streams (like a folder)
           e.g., /aws/ec2/nginx/access

Log Stream: Individual source within a group
            e.g., i-0123456789abcdef0 (each instance has its own stream)

Log Event: A single log record with timestamp and message

Retention: 1 day to 10 years (default: never expire)
           Set retention to reduce costs!
```

```bash
# Set retention on a log group
aws logs put-retention-policy \
  --log-group-name /aws/ec2/nginx/access \
  --retention-in-days 30

# Search logs with CloudWatch Insights
aws logs start-query \
  --log-group-name /aws/ec2/nginx/access \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /ERROR/
    | stats count(*) as error_count by bin(5m) as time_bucket
    | sort time_bucket desc
    | limit 20
  '

# Get query results
QUERY_ID="query-id-from-start-query"
aws logs get-query-results --query-id $QUERY_ID

# Create a metric filter (extract metrics from log text)
# Example: Count HTTP 5xx errors from nginx access logs
aws logs put-metric-filter \
  --log-group-name /aws/ec2/nginx/access \
  --filter-name 5xx-errors \
  --filter-pattern '[ip, identity, user, timestamp, request, status_code=5*, size]' \
  --metric-transformations '{
    "metricName": "HTTP5xxErrors",
    "metricNamespace": "WebApp/Nginx",
    "metricValue": "1",
    "unit": "Count"
  }'
  
# Now create an alarm on this custom metric
aws cloudwatch put-metric-alarm \
  --alarm-name high-5xx-error-rate \
  --namespace WebApp/Nginx \
  --metric-name HTTP5xxErrors \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

### CloudWatch Dashboards — Visibility at a Glance

```bash
# Create a dashboard with multiple widgets
cat > /tmp/dashboard.json << 'EOF'
{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "metrics": [
          ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "web-app-asg",
           {"stat": "Average", "period": 300, "color": "#2ca02c"}],
          ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "web-app-asg",
           {"stat": "Maximum", "period": 300, "color": "#d62728", "label": "CPU Max"}]
        ],
        "view": "timeSeries",
        "stacked": false,
        "title": "EC2 CPU Utilization",
        "period": 300,
        "yAxis": {"left": {"min": 0, "max": 100}},
        "annotations": {
          "horizontal": [{"label": "Scale-out threshold", "value": 80}]
        }
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 0, "width": 12, "height": 6,
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/web-app-alb/xxx",
           {"stat": "Sum", "period": 300}],
          ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/web-app-alb/xxx",
           {"stat": "p99", "period": 300, "yAxis": "right"}]
        ],
        "title": "ALB Requests and Latency (p99)",
        "period": 300
      }
    },
    {
      "type": "alarm",
      "x": 0, "y": 6, "width": 24, "height": 3,
      "properties": {
        "title": "All Active Alarms",
        "alarms": [
          "arn:aws:cloudwatch:us-east-1:123456789012:alarm:web-server-high-cpu",
          "arn:aws:cloudwatch:us-east-1:123456789012:alarm:rds-too-many-connections",
          "arn:aws:cloudwatch:us-east-1:123456789012:alarm:high-5xx-error-rate"
        ]
      }
    }
  ]
}
EOF

aws cloudwatch put-dashboard \
  --dashboard-name production-ops-dashboard \
  --dashboard-body file:///tmp/dashboard.json
```

---

## 7.3 CloudTrail — Who Did What, When

### What is CloudTrail?

**CloudTrail** records every API call made to your AWS account. Every action taken:
- Via AWS Console (clicking buttons makes API calls)
- Via AWS CLI commands
- Via SDKs (Python boto3, Java SDK, etc.)
- By AWS services acting on your behalf
- By IAM users, IAM roles, root account

**Analogy:** CloudTrail is the CCTV camera system for your AWS account. Every action is recorded. Who opened the front door? Who moved the servers? Who deleted the database? CloudTrail has the footage.

**Why it matters:**
- Security investigations: "Who deleted the production S3 bucket?"
- Compliance: "Prove to our auditor that only authorized people access PHI data"
- Operational troubleshooting: "What changed right before the system broke?"
- Alert on suspicious activity: "Alert me if root account is used"

### CloudTrail Event Types

**Management Events (enabled by default):**
- Actions on AWS resources: Create/Delete/Modify EC2 instances, Create S3 buckets, IAM changes
- Both write activities (CreateBucket, DeleteObject) and read activities (DescribeInstances, GetObject)
- Read events can be disabled to reduce volume

**Data Events (not enabled by default — cost extra):**
- Actions on data INSIDE resources:
  - S3: GetObject, PutObject, DeleteObject (every file access)
  - Lambda: function invocations
  - DynamoDB: GetItem, PutItem, DeleteItem
- Very high volume — enable only for sensitive resources

**Insights Events:**
- CloudTrail Insights detects unusual API activity
- "This account normally makes 10 CreateUser calls/hour; today it made 500 in 5 minutes — suspicious!"

### CloudTrail Setup

```bash
# Create a CloudTrail (trail) that logs all management events
aws cloudtrail create-trail \
  --name organization-audit-trail \
  --s3-bucket-name company-cloudtrail-logs \
  --include-global-service-events \  # IAM, STS, CloudFront events
  --is-multi-region-trail \         # Logs ALL regions (not just current)
  --enable-log-file-validation      # Detect if logs are tampered with

# Start logging
aws cloudtrail start-logging --name organization-audit-trail

# Enable CloudWatch Logs integration (so you can create alarms on CloudTrail events)
aws cloudtrail update-trail \
  --name organization-audit-trail \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail/management-events:* \
  --cloud-watch-logs-role-arn arn:aws:iam::123456789012:role/CloudTrailCloudWatchRole

# Enable data events for a sensitive S3 bucket
aws cloudtrail put-event-selectors \
  --trail-name organization-audit-trail \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": [
            "arn:aws:s3:::sensitive-customer-data-bucket/"
          ]
        }
      ]
    }
  ]'
```

### Querying CloudTrail — Finding Who Did What

```bash
# Search for events from the last hour
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DeleteBucket \
  --start-time $(date -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Events[*].[EventTime,Username,CloudTrailEvent]' \
  --output table

# Find all actions by a specific user
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=alice \
  --start-time $(date -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Events[*].[EventTime,EventName,CloudTrailEvent]' \
  --output table

# Find root account usage (security concern!)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=root \
  --start-time $(date -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)

# Create CloudWatch alarm for root account usage
aws logs put-metric-filter \
  --log-group-name CloudTrail/management-events \
  --filter-name root-account-usage \
  --filter-pattern '{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }' \
  --metric-transformations \
    metricName=RootAccountUsage,metricNamespace=CloudTrailAlerts,metricValue=1

aws cloudwatch put-metric-alarm \
  --alarm-name root-account-used \
  --namespace CloudTrailAlerts \
  --metric-name RootAccountUsage \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:security-alerts
```

---

## 7.4 AWS Config — Infrastructure Compliance Auditor

### What is AWS Config?

**AWS Config** continuously monitors your AWS resource configurations and evaluates them against your desired rules. It answers:
- "What does my infrastructure look like right now?"
- "What did it look like 6 months ago?" (Configuration history)
- "Is it compliant with my security rules?"
- "What changed, and when?" (Change tracking)

**Analogy:** AWS Config is like a building inspector who:
1. Takes a complete photo of your entire building every few minutes
2. Compares each photo to the building code
3. Flags any violations immediately
4. Can go back through the photo history and show you exactly when and what changed

### How Config Works

```
1. Resource Change Detected
   (Someone modifies a security group)
   
2. Config records the new configuration
   (Stores a "configuration item" snapshot in S3)
   
3. Config rules evaluate the change
   (Is this security group compliant with our rules?)
   
4. If non-compliant: Mark as NON_COMPLIANT
   Optionally: SNS notification, auto-remediation
```

### Managed Rules — Pre-Built Compliance Checks

AWS provides 100+ pre-built rules:

```
Security rules:
  s3-bucket-public-read-prohibited       — no S3 bucket should allow public read
  s3-bucket-ssl-requests-only            — S3 must require HTTPS
  encrypted-volumes                      — all EBS volumes must be encrypted
  rds-storage-encrypted                  — all RDS instances must be encrypted
  ec2-instances-in-vpc                   — all EC2 instances must be in a VPC
  iam-root-access-key-check             — root account must not have access keys
  iam-user-mfa-enabled                   — all IAM users must have MFA
  cloudtrail-enabled                     — CloudTrail must be enabled
  vpc-flow-logs-enabled                  — VPC flow logs must be enabled
  
Best practice rules:
  ec2-instance-no-public-ip              — EC2 should not have public IPs
  rds-instance-public-access-check       — RDS should not be publicly accessible
  s3-bucket-versioning-enabled           — S3 buckets should have versioning
  restricted-ssh                         — SSH (port 22) not open to 0.0.0.0/0
  restricted-common-ports                — no dangerous ports open to internet
  
Tagging rules:
  required-tags                          — resources must have required tags
```

```bash
# Enable AWS Config recording
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123456789012:role/config-role",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

# Set delivery channel (where Config stores data)
aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "company-config-bucket",
    "snsTopicARN": "arn:aws:sns:us-east-1:123456789012:config-notifications",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

# Start recording
aws configservice start-configuration-recorder \
  --configuration-recorder-name default

# Add a managed rule: all EBS volumes must be encrypted
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "encrypted-volumes",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "ENCRYPTED_VOLUMES"
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::EC2::Volume"]
    }
  }'

# Add a managed rule: S3 buckets must not allow public read
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    }
  }'

# Check compliance status
aws configservice describe-compliance-by-config-rule \
  --query 'ComplianceByConfigRules[*].[ConfigRuleName,Compliance.ComplianceType]' \
  --output table

# Get all NON_COMPLIANT resources
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name encrypted-volumes \
  --compliance-types NON_COMPLIANT \
  --query 'EvaluationResults[*].[EvaluationResultIdentifier.EvaluationResultQualifier.ResourceType,EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId]' \
  --output table
```

### Config Auto-Remediation

**Auto-Remediation** automatically fixes non-compliant resources using SSM Automation documents.

```bash
# Auto-remediate S3 buckets that become publicly accessible
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-DisableS3BucketPublicReadWrite",
    "Parameters": {
      "AutomationAssumeRole": {
        "StaticValue": {
          "Values": ["arn:aws:iam::123456789012:role/config-remediation-role"]
        }
      },
      "S3BucketName": {
        "ResourceValue": {"Value": "RESOURCE_ID"}
      }
    },
    "Automatic": true,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 60,
    "ExecutionControls": {
      "SsmControls": {
        "ConcurrentExecutionRatePercentage": 10,
        "ErrorPercentage": 10
      }
    }
  }]'
```

---

## 7.5 Amazon EventBridge — Reacting to AWS Events

### What is EventBridge?

**Amazon EventBridge** (formerly CloudWatch Events) is an event bus that routes events from AWS services to Lambda functions, SQS, SNS, and other targets.

Think of it as: "When X happens, do Y automatically."

**Common patterns:**

```
Pattern 1: Security response
  CloudTrail → EventBridge rule (when root account is used) → Lambda → revoke credentials + alert

Pattern 2: Cost control
  EC2 Spot interruption notice → EventBridge → Lambda → graceful shutdown logic

Pattern 3: Operations automation
  EC2 Auto Scaling: new instance launched → EventBridge → Lambda → configure monitoring
  EC2 state change: instance terminated → EventBridge → Lambda → update CMDB

Pattern 4: Cross-account events
  Account A: Dev environment → EventBridge → Account B: Production monitoring

Pattern 5: Scheduled tasks (cron)
  Every day at 2am → EventBridge → Lambda → database cleanup job
  Every Monday 7am → EventBridge → Lambda → generate weekly report
```

```bash
# Create a rule that triggers when any EC2 instance state changes
aws events put-rule \
  --name ec2-state-change-monitor \
  --event-pattern '{
    "source": ["aws.ec2"],
    "detail-type": ["EC2 Instance State-change Notification"]
  }' \
  --state ENABLED

# Add a Lambda function as the target
aws events put-targets \
  --rule ec2-state-change-monitor \
  --targets '[{
    "Id": "ec2-monitor-lambda",
    "Arn": "arn:aws:lambda:us-east-1:123456789012:function:ec2-state-monitor"
  }]'

# Create a scheduled rule (cron): Run every day at 3am UTC
aws events put-rule \
  --name daily-cleanup \
  --schedule-expression "cron(0 3 * * ? *)" \
  --state ENABLED

# Create a rate-based rule (run every 5 minutes)
aws events put-rule \
  --name health-check \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED
```

---

## 7.6 Practice Questions

**Q1:** A SysOps administrator needs to monitor memory utilization on their EC2 instances and create alarms when it exceeds 85%. They check CloudWatch but cannot find the MemoryUtilization metric. Why?

- A) Memory monitoring is not supported by CloudWatch
- B) Memory metrics are only available for t3 instance types
- C) The CloudWatch Agent must be installed and configured to collect memory metrics
- D) Memory metrics are only available in CloudWatch detailed mode

**Answer: C**

Explanation: AWS/EC2 namespace in CloudWatch does NOT include memory or disk utilization by default — these metrics are not visible to the hypervisor (they are inside the OS). The CloudWatch Agent must be installed on the instance to collect and push these metrics to a custom namespace (CWAgent). Once the agent is configured with "mem_used_percent" collection, the metric appears and alarms can be created.

---

**Q2:** Your company needs to prove to an auditor that no S3 bucket has been publicly accessible in the last 12 months. Which service provides this evidence?

- A) CloudWatch Logs — check access logs
- B) AWS Config — shows configuration history and compliance evaluation results
- C) CloudTrail — shows who accessed S3
- D) VPC Flow Logs — shows S3 traffic

**Answer: B**

Explanation: AWS Config continuously records the configuration of every S3 bucket (including public access settings). The Config rule s3-bucket-public-read-prohibited evaluates each bucket. Config maintains a configuration history, allowing you to prove what the configuration was at any point in the past. This is exactly what auditors need: a compliance timeline showing the resource was always compliant.

---

**Q3:** A security incident is being investigated. The IR team needs to know exactly what API calls were made by a specific IAM role in the last 90 days. Which service provides this information?

- A) CloudWatch Logs
- B) CloudTrail
- C) AWS Config
- D) VPC Flow Logs

**Answer: B**

Explanation: CloudTrail records every API call with who made it, what they did, when, from where (source IP), and what the request/response was. Querying CloudTrail for a specific IAM role gives a complete audit trail of all actions taken. CloudTrail logs can be queried directly (lookup-events) or via Athena for more complex analysis. By default, CloudTrail retains events for 90 days in the event history.

---

**Q4:** You set up a CloudWatch alarm to trigger when CPU > 80% for 2 evaluation periods (5 minutes each). The CPU spikes to 95% for 3 minutes then drops back to 30%. Does the alarm trigger?

- A) Yes, because CPU exceeded 80% at any point
- B) No, because CPU was only above 80% for 3 minutes, not the full 2 evaluation periods (10 minutes)
- C) Yes, because the average CPU across the evaluation period was above 80%
- D) It depends on the alarm action type

**Answer: B**

Explanation: The alarm requires CPU > 80% for 2 consecutive evaluation periods. Each period is 5 minutes. The alarm evaluates at the end of each 5-minute period. If CPU was 95% for 3 minutes then dropped to 30%, the 5-minute AVERAGE for that period would be below 80% (e.g., 95*3/5 + 30*2/5 = 57% + 12% = 69%). Two consecutive periods both need to exceed 80% for the alarm to trigger. This is how evaluation periods prevent false alarms from brief spikes.

---

**Q5:** AWS Config shows an EBS volume as NON_COMPLIANT for the encrypted-volumes rule. Auto-remediation is configured. What happens?

- A) Config automatically encrypts the existing volume
- B) Config triggers an SSM Automation document that can take the configured remediation action (e.g., create encrypted snapshot and replace the volume)
- C) Config deletes the non-compliant volume
- D) Config creates a new encrypted volume but cannot migrate data from the old one

**Answer: B**

Explanation: Config auto-remediation triggers the configured SSM Automation document when a resource is marked non-compliant. For EBS encryption, the automation typically: creates a snapshot → creates new encrypted volume from snapshot → detaches old volume → attaches new encrypted volume → optionally deletes old volume. Config cannot directly modify resource configurations — it delegates to SSM Automation for the actual remediation. The specific behavior depends on the SSM document configured.

---

## Chapter 7 Summary

| Service | Purpose | Key Feature |
|---------|---------|-------------|
| CloudWatch Metrics | Collect numbers over time | EC2 default metrics free; memory/disk need CW Agent |
| CloudWatch Alarms | Trigger actions on thresholds | 3 states: OK/ALARM/INSUFFICIENT_DATA |
| CloudWatch Logs | Centralized log storage | Log groups, streams; Insights for queries |
| CloudWatch Dashboards | Visual monitoring | Custom widgets; share with team |
| Composite Alarms | Reduce alert fatigue | AND/OR logic across multiple alarms |
| CloudTrail | API call audit log | Who did what when; 90-day history default |
| CloudTrail Insights | Anomaly detection | Unusual API activity patterns |
| AWS Config | Configuration compliance | Current + historical resource configurations |
| Config Rules | Compliance checks | 100+ managed rules + custom Lambda rules |
| Config Remediation | Auto-fix | SSM Automation on non-compliant resources |
| EventBridge | Event routing | When X happens, do Y; cron scheduling |
"""

with open(r"e:\fastapi\aws-admin\07_Monitoring_CloudWatch_Config.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
