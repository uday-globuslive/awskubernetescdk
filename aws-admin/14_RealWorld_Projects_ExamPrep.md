# Chapter 14: Real-World Projects & Exam Preparation

## AWS SysOps Administrator (SOA-C02) — Final Review

---

## 14.1 Exam Overview

### Exam Details
| Item | Details |
|------|---------|
| Exam Code | SOA-C02 |
| Duration | 180 minutes |
| Questions | 65 questions (scored) + 15 unscored |
| Passing Score | 720/1000 |
| Price | $150 USD |
| Delivery | Pearson VUE or PSI (online/testing center) |
| Format | Multiple choice, multiple response, exam labs |

### Domain Weights (SOA-C02)
| Domain | Topic | Weight |
|--------|-------|--------|
| 1 | Monitoring, Logging, and Remediation | **20%** |
| 2 | Reliability and Business Continuity | **16%** |
| 3 | Deployment, Provisioning, and Automation | **18%** |
| 4 | Security and Compliance | **16%** |
| 5 | Networking and Content Delivery | **18%** |
| 6 | Cost and Performance Optimization | **12%** |

---

## 14.2 Project 1: Highly Available 3-Tier Web Application

### Architecture
```
Internet
    │
    ▼
Route 53 (Latency-based routing + health checks)
    │
    ▼
CloudFront (CDN + WAF + DDoS protection)
    │
    ▼
ALB (Multi-AZ, HTTPS-only)
    │
    ▼
┌───────────────────────────────────────────────┐
│              AUTO SCALING GROUP                │
│    AZ-1              AZ-2              AZ-3    │
│  EC2 Web          EC2 Web          EC2 Web    │
│  (Private Subnet) (Private Subnet) (Private)  │
└───────────────────────────────────────────────┘
    │
    ▼
ElastiCache Redis (Session + Caching, Multi-AZ)
    │
    ▼
Aurora PostgreSQL (Multi-AZ, read replicas)
    │
    ▼
S3 (Static assets, backups, logs)
```

### CloudFormation Template (Abbreviated)
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Highly Available 3-Tier Web Application

Parameters:
  Environment:
    Type: String
    Default: production
  DBPassword:
    Type: String
    NoEcho: true

Resources:
  # ─── VPC + Networking ───────────────────────────
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true

  # Public subnets (ALB, NAT GW)
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']

  # ─── Application Load Balancer ──────────────────
  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Subnets: [!Ref PublicSubnet1, !Ref PublicSubnet2]
      SecurityGroups: [!Ref ALBSecurityGroup]
      LoadBalancerAttributes:
        - Key: access_logs.s3.enabled
          Value: true
        - Key: access_logs.s3.bucket
          Value: !Ref AccessLogBucket

  ALBListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Port: 443
      Protocol: HTTPS
      Certificates:
        - CertificateArn: !Ref ACMCertificate
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref WebTargetGroup

  HTTPRedirect:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Port: 80
      Protocol: HTTP
      DefaultActions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: '443'
            StatusCode: HTTP_301

  # ─── Auto Scaling Group ─────────────────────────
  WebASG:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      VPCZoneIdentifier:
        - !Ref PrivateAppSubnet1
        - !Ref PrivateAppSubnet2
      LaunchTemplate:
        LaunchTemplateId: !Ref WebLaunchTemplate
        Version: !GetAtt WebLaunchTemplate.LatestVersionNumber
      MinSize: 2
      MaxSize: 20
      DesiredCapacity: 4
      TargetGroupARNs: [!Ref WebTargetGroup]
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      MetricsCollection:
        - Granularity: 1Minute

  ScalingPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref WebASG
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ASGAverageCPUUtilization
        TargetValue: 60.0

  # ─── Aurora Database ────────────────────────────
  AuroraCluster:
    Type: AWS::RDS::DBCluster
    Properties:
      Engine: aurora-postgresql
      EngineVersion: '15.4'
      DBSubnetGroupName: !Ref DBSubnetGroup
      VpcSecurityGroupIds: [!Ref DBSecurityGroup]
      DatabaseName: production
      MasterUsername: admin
      ManageMasterUserPassword: true  # Auto-creates in Secrets Manager
      BackupRetentionPeriod: 7
      StorageEncrypted: true
      EnableCloudwatchLogsExports: [postgresql]
      DeletionProtection: true

  # ─── ElastiCache Redis ──────────────────────────
  RedisCluster:
    Type: AWS::ElastiCache::ReplicationGroup
    Properties:
      ReplicationGroupDescription: Session cache
      NumCacheClusters: 2
      CacheNodeType: cache.r6g.medium
      Engine: redis
      EngineVersion: '7.0'
      AtRestEncryptionEnabled: true
      TransitEncryptionEnabled: true
      AutomaticFailoverEnabled: true
      CacheSubnetGroupName: !Ref CacheSubnetGroup

  # ─── CloudWatch Monitoring ──────────────────────
  HighCPUAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: web-high-cpu
      Namespace: AWS/EC2
      MetricName: CPUUtilization
      Dimensions:
        - Name: AutoScalingGroupName
          Value: !Ref WebASG
      Statistic: Average
      Period: 60
      EvaluationPeriods: 5
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      AlarmActions: [!Ref OpsAlertsTopic]

  # ─── Outputs ────────────────────────────────────
Outputs:
  LoadBalancerURL:
    Value: !Sub 'https://${ALB.DNSName}'
  DatabaseEndpoint:
    Value: !GetAtt AuroraCluster.Endpoint.Address
  RedisEndpoint:
    Value: !GetAtt RedisCluster.PrimaryEndPoint.Address
```

---

## 14.3 Project 2: Event-Driven Data Pipeline

### Architecture
```
Data Sources:
  IoT Devices ──────────────────────────────────┐
  Application Events ────────────────────────┐  │
  Database CDC ───────────────────────────┐  │  │
                                          │  │  │
                                          ▼  ▼  ▼
                                    Kinesis Data Streams
                                          │
                              ┌───────────┼───────────┐
                              │           │           │
                           Lambda      Firehose    Analytics
                        (real-time)  (→S3 archive) (real-time SQL)
                              │
                           DynamoDB
                        (processed data)
                              │
                              ▼
                          EventBridge
                              │
                    ┌─────────┼─────────┐
                    │         │         │
                  Lambda    Lambda    SNS
                (transform) (alert)  (notify)
```

### Kinesis + Lambda Processing
```python
import boto3
import json
import base64
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('sensor-readings')

def lambda_handler(event, context):
    """Process Kinesis records — batch processing."""
    
    processed = 0
    failed = []
    
    for record in event['Records']:
        try:
            # Kinesis data is base64 encoded
            data = json.loads(base64.b64decode(record['kinesis']['data']))
            
            # Enrich and validate
            reading = {
                'deviceId': data['deviceId'],
                'timestamp': record['kinesis']['approximateArrivalTimestamp'],
                'temperature': Decimal(str(data['temperature'])),
                'humidity': Decimal(str(data['humidity'])),
                'shardId': record['eventID'],
                'processed': True
            }
            
            # Check thresholds
            if data['temperature'] > 85:
                trigger_alert(data['deviceId'], 'HIGH_TEMPERATURE', data['temperature'])
            
            # Store to DynamoDB
            table.put_item(Item=reading)
            processed += 1
            
        except Exception as e:
            print(f"Failed record {record['eventID']}: {e}")
            failed.append(record['eventID'])
    
    print(f"Processed: {processed}, Failed: {len(failed)}")
    
    # Report failures for Kinesis to retry
    return {
        'batchItemFailures': [
            {'itemIdentifier': seq_num} for seq_num in failed
        ]
    }

def trigger_alert(device_id: str, alert_type: str, value: float):
    events = boto3.client('events')
    events.put_events(Entries=[{
        'Source': 'com.iot.sensor',
        'DetailType': f'Sensor Alert',
        'Detail': json.dumps({
            'deviceId': device_id,
            'alertType': alert_type,
            'value': value
        })
    }])
```

---

## 14.4 Project 3: Security Automation Platform

### Architecture
```
AWS Config ──────────────────────────────────────┐
GuardDuty ───────────────────────────────────┐   │
Security Hub ─────────────────────────────┐  │   │
IAM Access Analyzer ──────────────────┐   │  │   │
                                      │   │  │   │
                                      ▼   ▼  ▼   ▼
                                   EventBridge
                                       │
                          ┌────────────┼────────────┐
                          │            │            │
                       Lambda       Lambda        SQS
                    (auto-         (notify     (queue for
                    remediate)      security)   review)
                          │
                    SSM Automation
                    (isolate/fix)
```

### Security Automation Lambda
```python
import boto3
import json

ec2 = boto3.client('ec2')
iam = boto3.client('iam')
ssm = boto3.client('ssm')
sns = boto3.client('sns')

SECURITY_TOPIC = 'arn:aws:sns:us-east-1:123456789012:security-alerts'

def lambda_handler(event, context):
    source = event.get('source', '')
    detail = event.get('detail', {})
    detail_type = event.get('detail-type', '')
    
    if source == 'aws.guardduty':
        handle_guardduty_finding(detail)
    
    elif source == 'aws.config':
        if 'Config Rules Compliance Change' in detail_type:
            handle_config_violation(detail)
    
    elif source == 'aws.iam':
        if detail.get('eventName') == 'CreateAccessKey':
            handle_new_access_key(detail)

def handle_guardduty_finding(detail: dict):
    severity = detail.get('severity', 0)
    finding_type = detail.get('type', '')
    resource = detail.get('resource', {})
    
    if 'CryptoCurrency' in finding_type or 'Backdoor' in finding_type:
        instance_id = resource.get('instanceDetails', {}).get('instanceId')
        if instance_id and severity >= 7:
            isolate_instance(instance_id)
            notify_security(f"CRITICAL: Isolated instance {instance_id} - {finding_type}")

def handle_config_violation(detail: dict):
    rule = detail.get('configRuleName', '')
    resource_id = detail.get('resourceId', '')
    compliance = detail.get('newEvaluationResult', {}).get('complianceType', '')
    
    if compliance != 'NON_COMPLIANT':
        return
    
    if rule == 'restricted-ssh':
        remediate_ssh_sg(resource_id)
    
    elif rule == 's3-bucket-public-access-prohibited':
        remediate_s3_public_access(resource_id)

def handle_new_access_key(detail: dict):
    """Alert when any IAM access key is created."""
    user = detail.get('requestParameters', {}).get('userName')
    creator = detail.get('userIdentity', {}).get('arn')
    
    notify_security(
        f"IAM Access Key Created\n"
        f"User: {user}\n"
        f"Created by: {creator}\n"
        f"Source IP: {detail.get('sourceIPAddress')}\n"
        "Action required: Verify this is authorized."
    )

def isolate_instance(instance_id: str):
    # Get VPC to create isolation SG
    vpc_id = ec2.describe_instances(
        InstanceIds=[instance_id]
    )['Reservations'][0]['Instances'][0]['VpcId']
    
    sg = ec2.create_security_group(
        GroupName=f'ISOLATED-{instance_id[:8]}',
        Description=f'Isolation - GuardDuty incident',
        VpcId=vpc_id
    )['GroupId']
    
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[sg]
    )

def remediate_s3_public_access(bucket_name: str):
    s3control = boto3.client('s3control')
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    boto3.client('s3').put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )

def notify_security(message: str):
    sns.publish(
        TopicArn=SECURITY_TOPIC,
        Subject='AWS Security Alert',
        Message=message
    )
```

---

## 14.5 Quick Reference: Critical Numbers for Exam

### Service Limits & Key Numbers
| Service | Key Numbers |
|---------|-------------|
| **S3** | Max object size 5TB; Multipart required >5GB; Free Tier 5GB |
| **EC2** | T3 unlimited CPU credit: $0.05/vCPU-hr; Max EBS vols per instance: 40 |
| **EBS** | gp3 default: 3000 IOPS, 125MB/s; io2 max: 256,000 IOPS |
| **Lambda** | Max memory: 10GB; Max timeout: 15 min; Package: 50MB zip, 250MB unzipped |
| **SQS** | Max message size: 256KB; Max retention: 14 days; Max visibility: 12 hours |
| **SNS** | Max message size: 256KB; 12.5M subscriptions per topic |
| **DynamoDB** | Item max: 400KB; On-demand mode; 40K RCU/WCU default limit |
| **RDS** | Max storage: 64TB; Multi-AZ failover: 60-120 seconds |
| **Aurora** | 6 copies across 3 AZs; Read replicas: up to 15; Failover: ~30 sec |
| **CloudFront** | 450 edge locations; Free Tier: 1TB transfer, 10M requests |
| **CloudTrail** | 90-day event history free; S3 storage for long-term |
| **CloudWatch** | 1-year metric storage (15 months for detailed); 5 min basic, 1 min detailed |
| **IAM** | Max users/account: 5000; Max groups/account: 300; Max policies/user: 10 |
| **VPC** | 5 VPCs per region; 200 subnets per VPC; 5 IPs reserved per subnet |
| **Route 53** | 50 domains per account; 300 hosted zones |

---

## 14.6 Exam Strategy & Tips

### Time Management
- 180 minutes / 65 questions = **2.7 minutes per question**
- Spend max 2 minutes on each question first pass
- Flag uncertain questions, return at end
- Never leave questions blank (no penalty for wrong answers)

### Question Patterns to Know

**"MOST operationally efficient"** = AWS managed service (not EC2+custom)

**"MINIMUM changes"** = simplest solution, often just enable existing feature

**"MOST cost-effective"** = Reserved Instances, Spot, Savings Plans, right-sizing

**"AUTOMATICALLY"** = Lambda trigger, EventBridge rule, ASG, Auto Scaling

**"CENTRALLY manage across accounts"** = AWS Organizations, StackSets, Control Tower

**"Near real-time"** = Kinesis, not S3 batch, not daily runs

**"Encryption at rest"** = KMS CMK or AWS managed key (not SSL/TLS which is in-transit)

**"Compliance/audit"** = CloudTrail, AWS Config, Audit Manager

### Common Traps

❌ **S3 Block Public Access vs S3 bucket policy** — Block Public Access overrides bucket policy for public access

❌ **Security Group stateful vs NACL stateless** — SGs: no explicit deny, stateful; NACLs: explicit deny, stateful no (must allow ephemeral ports)

❌ **CloudTrail vs CloudWatch** — CloudTrail = WHO/WHAT API calls; CloudWatch = METRICS/LOGS/ALARMS

❌ **RDS Multi-AZ vs Read Replica** — Multi-AZ = HA/failover (sync); Read Replica = performance/scale (async)

❌ **Reserved Instances vs Savings Plans** — RIs: specific instance type; Savings Plans: flexible $/hour

❌ **S3 Transfer Acceleration vs CloudFront** — Transfer Acceleration = UPLOAD to S3; CloudFront = DOWNLOAD/CDN

❌ **Global Accelerator vs CloudFront** — GA = TCP/UDP apps, static IPs, non-HTTP; CloudFront = HTTP/HTTPS with caching

---

## 14.7 Practice Questions — Final 20 (Mixed Topics)

**Q1:** An EC2 instance running in a private subnet needs to access S3 without going through the internet. What should you use?
- A) NAT Gateway
- B) VPC Gateway Endpoint
- C) Internet Gateway
- D) VPC Interface Endpoint

**Answer: B** — Gateway Endpoints for S3 and DynamoDB are free and keep traffic within AWS.

---

**Q2:** You need to ensure no developer can accidentally delete production EC2 instances. What is the MOST effective control?
- A) IAM deny policy on each developer user
- B) Service Control Policy (SCP) denying ec2:TerminateInstances with condition on tag
- C) CloudWatch alarm on EC2 termination events
- D) AWS Config rule for EC2 termination

**Answer: B** — SCPs are preventive controls enforced at the organization level; they cannot be overridden by any identity within the account.

```json
{
  "Effect": "Deny",
  "Action": "ec2:TerminateInstances",
  "Resource": "*",
  "Condition": {
    "StringEquals": {"aws:ResourceTag/Environment": "production"}
  }
}
```

---

**Q3:** CloudWatch shows a spike in HTTP 5xx errors on an ALB. You need to investigate which backend instance is causing errors. Where do you look?
- A) VPC Flow Logs
- B) ALB Access Logs in S3
- C) CloudTrail
- D) EC2 instance metrics

**Answer: B** — ALB Access Logs record each request with target IP, response code, and response time, allowing you to identify which specific backend instance is returning 5xx.

---

**Q4:** Your RDS PostgreSQL instance has performance issues. CPU is at 20% but queries are slow. What should you check?
- A) Enable Multi-AZ
- B) Enable Performance Insights and check Top SQL
- C) Increase instance size
- D) Create read replicas

**Answer: B** — Performance Insights shows the "DB load" broken down by top SQL queries, waits, and hosts. Low CPU but slow queries usually indicates I/O waits or lock contention, visible in Performance Insights.

---

**Q5:** You want to deploy a CloudFormation stack to 50 accounts across 3 regions. What service do you use?
- A) CloudFormation nested stacks
- B) CloudFormation StackSets
- C) CloudFormation change sets
- D) AWS CDK

**Answer: B** — StackSets deploy and manage stacks across multiple accounts and regions with a single operation.

---

**Q6:** A Lambda function processing Kinesis records is failing. Some records succeed and some fail. How do you ensure only failed records are retried?
- A) Set ReservedConcurrentExecutions to 0
- B) Use partial batch response (batchItemFailures)
- C) Set MaximumRetryAttempts to 0
- D) Create a DLQ for the Lambda

**Answer: B** — Partial batch response allows Lambda to report specific failed message IDs, so only those are retried (not the whole batch).

---

**Q7:** How do you enable memory utilization monitoring on EC2 instances in CloudWatch?
- A) Enable detailed monitoring
- B) Install and configure CloudWatch Agent
- C) Enable Performance Insights
- D) Enable VPC Flow Logs

**Answer: B** — Memory is an OS-level metric not available from the hypervisor. CloudWatch Agent collects it and sends to CloudWatch in the CWAgent namespace.

---

**Q8:** A company wants to prevent their AWS accounts from disabling CloudTrail. What should they do?
- A) Enable CloudTrail in all regions
- B) Create an SCP that denies cloudtrail:StopLogging and cloudtrail:DeleteTrail
- C) Set CloudTrail log file validation
- D) Create a CloudWatch alarm on CloudTrail events

**Answer: B** — An SCP applied to all accounts in the organization prevents anyone, including account administrators, from disabling CloudTrail.

---

**Q9:** An Auto Scaling Group has 6 instances across 3 AZs. One AZ goes down. The ASG min is 4 instances. What happens?
- A) The entire application goes down
- B) ASG terminates instances in healthy AZs to match min
- C) ASG launches new instances in remaining 2 AZs to meet desired count
- D) Nothing — ASG doesn't react to AZ failures

**Answer: C** — ASG health checks detect the instances in the failed AZ as unhealthy, terminates them, and launches replacements in the remaining healthy AZs to maintain desired capacity.

---

**Q10:** Which of the following is NOT a valid use case for S3 Object Lock?
- A) Prevent deletion of financial records for 7 years
- B) Meet regulatory requirements for immutable backups
- C) Protect against ransomware that has compromised an AWS account
- D) Improve S3 read performance

**Answer: D** — Object Lock provides immutability (WORM), not performance enhancement.

---

**Q11:** A company wants to migrate from an on-premises Oracle database to Amazon Aurora MySQL with minimal downtime. Which migration approach is correct?
- A) Take a mysqldump, restore to Aurora
- B) Use AWS SCT to convert the schema, then DMS for data migration with CDC
- C) Use AWS Snowball to transfer the database files
- D) Use DataSync to copy the database

**Answer: B** — SCT handles the schema conversion between different DB engines; DMS performs the data migration with CDC for minimal downtime.

---

**Q12:** You're designing a system where multiple services consume the same events. What is the BEST architecture?
- A) SQS FIFO queue with multiple consumers
- B) SNS topic with SQS subscriptions (fan-out)
- C) Multiple SQS queues with a single producer writing to all
- D) Kinesis Data Stream with DynamoDB

**Answer: B** — SNS fan-out pattern: publish once to SNS, delivered to multiple SQS queues for independent parallel processing by different services.

---

**Q13:** A CloudFormation stack deployment fails and rolls back. You want to preserve the failed resources for debugging. What flag do you use?
- A) --no-rollback
- B) --disable-rollback
- C) --on-failure DO_NOTHING
- D) Both B and C

**Answer: D** — `--disable-rollback` flag or `--on-failure DO_NOTHING` both prevent rollback on failure.

---

**Q14:** Your ECS tasks need to access Secrets Manager secrets. What is the MOST secure approach?
- A) Store secrets in environment variables in the task definition
- B) Use the `secrets` parameter in task definition with SecretManager ARN
- C) Store secrets in S3 and download at startup
- D) Use IAM user credentials in the task

**Answer: B** — ECS natively integrates with Secrets Manager via the `secrets` block in task definitions. The ECS task execution role fetches the secret and injects it as an environment variable, encrypted in transit.

---

**Q15:** AWS Config shows 10 S3 buckets are non-compliant with the `s3-bucket-ssl-requests-only` rule. How do you fix all 10 automatically?
- A) Manually add HTTPS-only bucket policies
- B) Create a Lambda function triggered by Config
- C) Use AWS Config automatic remediation with SSM Automation
- D) Enable S3 default encryption

**Answer: C** — Config automatic remediation with an SSM Automation document is the most efficient way. Set `Automatic: true` to remediate without manual intervention.

---

**Q16:** You want to ensure EC2 instances are automatically replaced within 5 minutes of a system check failure. What do you configure?
- A) CloudWatch alarm with ec2:reboot action
- B) CloudWatch alarm with ec2:recover action targeting StatusCheckFailed_System
- C) Auto Scaling health check grace period of 300 seconds
- D) Launch a second identical instance

**Answer: B** — EC2 Auto Recovery (`ec2:recover`) automatically recovers an instance when `StatusCheckFailed_System` metric crosses threshold.

---

**Q17:** A company is charged for data transfer between two EC2 instances. How should they reduce this cost?
- A) Move instances to the same AZ
- B) Use a VPC Endpoint
- C) Use S3 Transfer Acceleration
- D) Enable Enhanced Networking

**Answer: A** — Data transfer between EC2 instances in the SAME AZ is free. Cross-AZ transfer incurs costs ($0.01/GB each direction). However, note that placing in same AZ reduces fault tolerance.

---

**Q18:** Which Route 53 routing policy would you use for a blue/green deployment where you want to gradually shift traffic from old version to new?
- A) Failover routing
- B) Weighted routing
- C) Latency-based routing
- D) Multivalue answer

**Answer: B** — Weighted routing lets you assign weights (e.g., Blue=90, Green=10) and gradually change them. Start with 10% on green, monitor, increase to 50%, then 100%.

---

**Q19:** What happens to unprocessed SQS messages when the retention period expires?
- A) They are moved to the DLQ
- B) They are permanently deleted
- C) They are archived to S3
- D) They remain in the queue indefinitely

**Answer: B** — Messages are permanently deleted after the retention period (1 minute to 14 days). They do NOT go to DLQ automatically on retention expiry.

---

**Q20:** Your organization needs to reduce AWS costs. Compute Optimizer recommends downsizing from m5.2xlarge to m5.large for 50 instances. What is the MOST efficient way to make this change?
- A) Terminate and relaunch instances
- B) Manually change instance types one by one
- C) Update the Launch Template and perform a rolling update via ASG
- D) Create a new AMI and deploy

**Answer: C** — Update the Launch Template with the new instance type, then do an instance refresh on the ASG (rolling replacement). This changes all 50 instances with minimal downtime.

```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name web-asg \
  --launch-template LaunchTemplateId=lt-xxx,Version='$Latest'

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name web-asg \
  --preferences MinHealthyPercentage=80,InstanceWarmup=300
```

---

## 14.8 SysOps vs Solutions Architect Differences

| Topic | SysOps Focus | SA Focus |
|-------|-------------|---------|
| CloudWatch | Deep dive — alarms, agents, logs insights | Overview |
| SSM | Patch Manager, Run Command, Session Manager | Overview |
| CloudFormation | Change sets, drift, CreationPolicy, rollback | Design patterns |
| Cost | Budgets actions, RI/SP analysis | Architecture choices |
| Troubleshooting | How to diagnose/fix | When to choose |
| Operations | Day-2 operations, maintenance | Initial design |

**SysOps is an OPERATIONAL exam** — focus on:
- How to MONITOR systems
- How to TROUBLESHOOT problems  
- How to AUTOMATE operations
- How to MAINTAIN compliance
- How to OPTIMIZE costs

---

## 14.9 Pre-Exam Checklist

### 1 Week Before
- [ ] Complete all practice exams (aim for >80%)
- [ ] Review all AWS service FAQs for main services
- [ ] Review CloudWatch metrics for each service
- [ ] Practice writing CloudFormation templates from memory

### 1 Day Before
- [ ] Review your notes, not new material
- [ ] Get familiar with the exam interface (Pearson VUE tutorial)
- [ ] Confirm exam time, ID requirements
- [ ] Rest — don't cram

### Exam Day
- [ ] Arrive 15 minutes early (or log in 15 min early for online)
- [ ] Read all questions carefully (second option may be "more correct")
- [ ] Use elimination — narrow to 2 options, pick the best
- [ ] For "which TWO" questions — usually 2 that work together
- [ ] Don't overthink — first instinct is often correct

---

## 14.10 After Exam — What's Next?

### If You Pass
- **Developer Associate** — overlapping skills, easier to get now
- **Database Specialty** — deeper RDS/Aurora/DynamoDB
- **Security Specialty** — deeper on KMS, GuardDuty, Security Hub
- **Advanced Networking Specialty** — deeper VPC, Direct Connect, BGP

### Continuous Learning
- AWS re:Invent videos on YouTube (free, deep technical content)
- AWS Workshops (hands-on labs, free)
- AWS Whitepapers: Well-Architected, Security, Cost Optimization
- A Cloud Guru / Stephane Maarek courses
- Practice with real AWS account (Free Tier + 12-month)

---

## Final Summary: Service Matrix

| Category | Primary Services | SysOps Focus |
|----------|----------------|-------------|
| **Compute** | EC2, Lambda, ECS, Fargate | ASG, Launch Templates, Lifecycle Hooks |
| **Storage** | S3, EBS, EFS, Glacier | Lifecycle Policies, Encryption, Object Lock |
| **Database** | RDS, Aurora, DynamoDB, ElastiCache | Multi-AZ, Read Replicas, Backup/Restore |
| **Networking** | VPC, Route 53, CloudFront, Direct Connect | Routing, Security Groups, NACLs, Flow Logs |
| **Security** | IAM, KMS, WAF, GuardDuty, Security Hub | Policies, Encryption, Finding Remediation |
| **Monitoring** | CloudWatch, CloudTrail, Config | Alarms, Dashboards, Compliance Rules |
| **Deployment** | CloudFormation, SSM, CodeDeploy | Stacks, Patch Manager, Run Command |
| **Messaging** | SQS, SNS, EventBridge, Kinesis | Queues, Fan-out, Event-driven Automation |
| **Migration** | DMS, DataSync, Snowball, Transfer | Migration Strategies, CDC |
| **Cost** | Cost Explorer, Budgets, Trusted Advisor | Optimization, Rightsizing |

---

**Good luck on your AWS SysOps Administrator exam! You've got this! 🚀**
