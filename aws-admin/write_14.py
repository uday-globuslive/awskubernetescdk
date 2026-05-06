
content = r"""# Chapter 14: Real-World Projects & Exam Preparation
## (Put It All Together)

---

## 14.1 Project 1: Highly Available Three-Tier Web Application

### Architecture Overview

This project builds a production-grade web application with full high availability, auto-scaling, security, and monitoring.

```
                        ┌─────────────────┐
                        │   Route 53      │
                        │  (DNS + Health) │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   CloudFront    │
                        │  (CDN + WAF +   │
                        │   SSL Term.)    │
                        └────────┬────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │          Production VPC (10.0.0.0/16)        │
          │                       │                       │
    AZ-1 (us-east-1a)            │              AZ-2 (us-east-1b)
          │                       │                       │
    ┌─────┴────┐         ┌────────▼────────┐        ┌────┴─────┐
    │ Public   │         │ Application     │         │ Public   │
    │ Subnet   │         │ Load Balancer   │         │ Subnet   │
    │ 10.0.1/24│         │ (ALB)           │         │ 10.0.2/24│
    └─────┬────┘         └────────┬────────┘         └────┬─────┘
          │                       │                       │
    ┌─────▼────┐    ┌─────────────┼──────────────┐   ┌───▼──────┐
    │ Private  │    │    Auto Scaling Group       │   │ Private  │
    │ App Sub. │    │  ┌──────────┐ ┌──────────┐  │   │ App Sub. │
    │ 10.0.3/24│    │  │ EC2 App  │ │ EC2 App  │  │   │ 10.0.4/24│
    └─────┬────┘    │  │ t3.medium│ │ t3.medium│  │   └────┬─────┘
          │         │  └──────────┘ └──────────┘  │        │
          │         └────────────────────────── ───┘        │
          │                       │                         │
    ┌─────▼─────────────┬─────────▼──────────────┬──────────▼──┐
    │  Private DB Subnet │                        │ Private DB  │
    │  10.0.5.0/24       │                        │ 10.0.6.0/24 │
    │  ┌─────────────┐   │    ┌──────────────┐    │             │
    │  │ RDS Primary │───┼────│ ElastiCache  │    │ RDS Standby │
    │  │ (Multi-AZ)  │   │    │ Redis Cluster│    │ (Standby)   │
    │  └─────────────┘   │    └──────────────┘    └─────────────┘
    └────────────────────┴────────────────────────────────────────┘
                                    │
                              ┌─────▼──────┐
                              │ S3 Bucket  │
                              │ (Static    │
                              │  Assets +  │
                              │  Backups)  │
                              └────────────┘
```

### Step-by-Step Build

```bash
# ── STEP 1: Network Foundation ─────────────────────────────────────

# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' --output text)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# Create 6 subnets (2 public, 2 private app, 2 private db)
PUB1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
PUB2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
APP1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
APP2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
DB1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.5.0/24 \
  --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
DB2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.6.0/24 \
  --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)

# NAT Gateways (for private subnets to reach internet for updates)
EIP1=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
NAT1=$(aws ec2 create-nat-gateway --subnet-id $PUB1 --allocation-id $EIP1 \
  --query 'NatGateway.NatGatewayId' --output text)

# ── STEP 2: Security Groups ────────────────────────────────────────

# ALB Security Group
ALB_SG=$(aws ec2 create-security-group \
  --group-name alb-sg --vpc-id $VPC_ID \
  --description "ALB Security Group" --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $ALB_SG \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# App Server Security Group
APP_SG=$(aws ec2 create-security-group \
  --group-name app-sg --vpc-id $VPC_ID \
  --description "App Server Security Group" --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $APP_SG \
  --protocol tcp --port 8080 --source-group $ALB_SG

# Database Security Group
DB_SG=$(aws ec2 create-security-group \
  --group-name db-sg --vpc-id $VPC_ID \
  --description "Database Security Group" --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $DB_SG \
  --protocol tcp --port 3306 --source-group $APP_SG

# ── STEP 3: RDS Aurora MySQL (Multi-AZ) ───────────────────────────

aws rds create-db-cluster \
  --db-cluster-identifier prod-aurora-cluster \
  --engine aurora-mysql \
  --engine-version 8.0 \
  --master-username admin \
  --master-user-password 'YourSecureP@ssw0rd' \
  --vpc-security-group-ids $DB_SG \
  --db-subnet-group-name prod-db-subnet-group \
  --backup-retention-period 7 \
  --deletion-protection \
  --storage-encrypted \
  --enable-cloudwatch-logs-exports '["error","slowquery","audit"]'

# ── STEP 4: Application Load Balancer ────────────────────────────

ALB_ARN=$(aws elbv2 create-load-balancer \
  --name prod-alb \
  --subnets $PUB1 $PUB2 \
  --security-groups $ALB_SG \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
  --name prod-app-tg \
  --protocol HTTP --port 8080 --vpc-id $VPC_ID \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# ── STEP 5: Auto Scaling Group ────────────────────────────────────

# Create Launch Template first
LT_ID=$(aws ec2 create-launch-template \
  --launch-template-name prod-app-lt \
  --launch-template-data '{
    "ImageId": "ami-0c02fb55956c7d316",
    "InstanceType": "t3.medium",
    "IamInstanceProfile": {"Name": "AppInstanceProfile"},
    "SecurityGroupIds": ["'$APP_SG'"],
    "UserData": "'$(base64 -w0 << 'USERDATA'
#!/bin/bash
yum update -y
cd /opt/app
python3 -m gunicorn --workers 4 --bind 0.0.0.0:8080 app:application &
USERDATA
)'",
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [{"Key": "Name", "Value": "prod-web-server"}]
    }]
  }' --query 'LaunchTemplate.LaunchTemplateId' --output text)

aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name prod-asg \
  --launch-template LaunchTemplateId=$LT_ID,Version='$Latest' \
  --min-size 2 \
  --desired-capacity 3 \
  --max-size 10 \
  --vpc-zone-identifier "$APP1,$APP2" \
  --target-group-arns $TARGET_GROUP_ARN \
  --health-check-type ELB \
  --health-check-grace-period 300

# Target tracking scaling policy (keep CPU at 60%)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name prod-asg \
  --policy-name cpu-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "TargetValue": 60,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    }
  }'
```

---

## 14.2 Project 2: Serverless REST API

```
Architecture:
  Client → CloudFront → API Gateway → Lambda → DynamoDB
                                              → S3 (file storage)
                            ↑
                            SQS → Lambda (async processing)
```

```python
# Lambda function for REST API
import json
import boto3
import os
from decimal import Decimal
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
table = dynamodb.Table(os.environ['TABLE_NAME'])
queue_url = os.environ['QUEUE_URL']

def handler(event, context):
    method = event['httpMethod']
    path = event['path']
    path_params = event.get('pathParameters') or {}
    
    routes = {
        ('GET', '/items'): list_items,
        ('POST', '/items'): create_item,
        ('GET', '/items/{id}'): get_item,
        ('PUT', '/items/{id}'): update_item,
        ('DELETE', '/items/{id}'): delete_item,
    }
    
    handler_fn = routes.get((method, path.replace(path_params.get('id', ''), '{id}')))
    if handler_fn:
        return handler_fn(event, path_params)
    return response(404, {'error': 'Not found'})

def list_items(event, params):
    result = table.scan(Limit=50)
    return response(200, result['Items'])

def create_item(event, params):
    body = json.loads(event['body'])
    item = {
        'id': str(uuid.uuid4()),
        'created_at': datetime.utcnow().isoformat(),
        **body
    }
    table.put_item(Item=item)
    
    # Async processing via SQS
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({'action': 'item_created', 'item_id': item['id']})
    )
    return response(201, item)

def get_item(event, params):
    result = table.get_item(Key={'id': params['id']})
    if 'Item' not in result:
        return response(404, {'error': 'Item not found'})
    return response(200, result['Item'])

def update_item(event, params):
    body = json.loads(event['body'])
    body['updated_at'] = datetime.utcnow().isoformat()
    update_expr = 'SET ' + ', '.join(f'#{k} = :{k}' for k in body)
    expr_names = {f'#{k}': k for k in body}
    expr_values = {f':{k}': v for k, v in body.items()}
    
    result = table.update_item(
        Key={'id': params['id']},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues='ALL_NEW'
    )
    return response(200, result['Attributes'])

def delete_item(event, params):
    table.delete_item(Key={'id': params['id']})
    return response(204, {})

def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, default=str)
    }
```

---

## 14.3 Exam Strategy & Tips

### AWS SysOps Administrator Associate — Exam Overview

```
Format:     65 questions (multiple choice and multiple response)
Duration:   130 minutes
Score:      100-1000, passing score: 720
Domains:
  - Domain 1: Monitoring, Logging, Remediation (20%)
  - Domain 2: Reliability and Business Continuity (16%)
  - Domain 3: Deployment, Provisioning, Automation (18%)
  - Domain 4: Security and Compliance (16%)
  - Domain 5: Networking and Content Delivery (18%)
  - Domain 6: Cost and Performance Optimization (12%)
```

### How to Approach Exam Questions

**Step 1: Read the ENTIRE question before looking at options**
- Identify the key constraint: "minimal cost", "minimal downtime", "without code changes", "fully managed"
- One word can completely change the correct answer

**Step 2: Eliminate obviously wrong answers (usually 2 of 4)**
- Remove options that are technically incorrect
- Remove options that violate the constraint

**Step 3: Compare remaining options against the constraint**
- If "minimal cost" → choose the most cost-effective option
- If "minimal downtime" → choose the option with fastest failover
- If "no code changes" → eliminate options requiring code changes

**Step 4: When in doubt, choose AWS managed services**
- AWS exams favor managed services over DIY solutions
- "Use RDS" is usually better than "install MySQL on EC2"
- "Use Lambda" is usually better than "long-polling on EC2"

### Common Exam Traps

```
TRAP 1: Multi-AZ vs Read Replicas
  Multi-AZ: High availability (automatic failover, same region)
  Read Replicas: Read scalability (NOT automatic failover!)
  Exam often asks about failover → Multi-AZ is the answer
  Exam often asks about read performance → Read Replica is the answer

TRAP 2: Security Groups vs NACLs
  Security Groups: Stateful; only ALLOW rules; attached to ENI/instance
  NACLs: Stateless; ALLOW and DENY rules; attached to subnet
  If question asks about DENYING specific IPs → NACL
  If question asks about allowing specific ports → Security Group

TRAP 3: S3 storage classes
  Question says "accessed once a quarter with millisecond retrieval"
  → Glacier INSTANT Retrieval (NOT regular Glacier which takes hours)

TRAP 4: CloudWatch Logs vs CloudTrail
  CloudWatch Logs: Application logs, system metrics, custom metrics
  CloudTrail: AWS API calls ("who did what to which resource when")
  "Who deleted the S3 bucket?" → CloudTrail
  "Why is my application returning errors?" → CloudWatch Logs

TRAP 5: RTO vs RPO
  RTO: How quickly can you recover? (Recovery Time Objective)
  RPO: How much data can you lose? (Recovery Point Objective)
  Question about "maximum acceptable downtime" → RTO
  Question about "maximum data loss acceptable" → RPO

TRAP 6: Encryption keys
  SSE-S3: AWS manages keys; you have least control; free
  SSE-KMS: KMS manages CMK; you control rotation, access; audit trail
  SSE-C: YOU provide keys with every request; AWS doesn't store key
  "Compliance requires you to manage keys" → SSE-KMS or SSE-C

TRAP 7: NAT Gateway vs NAT Instance
  NAT Gateway: Managed by AWS; highly available within AZ; more expensive
  NAT Instance: EC2 instance you manage; single point of failure; cheaper
  "Highly available NAT" → NAT Gateway
  "Most cost-effective NAT" → NAT Instance (but note: single AZ failure!)
```

---

## 14.4 Quick Reference: 20 Practice Exam Questions

**Q1:** An EC2 instance in a private subnet needs to download software updates from the internet. What is required?

A) Attach an Elastic IP to the instance
B) Add an internet gateway route to the private route table
C) A NAT Gateway in a public subnet with a route from the private subnet
D) A VPN connection to the internet

**Answer: C** — Private subnets need a NAT Gateway (in a public subnet) to initiate outbound internet connections. NAT Gateway provides internet access without making the instance directly reachable from the internet.

---

**Q2:** Your application logs are in CloudWatch Logs. You need to count the number of "ERROR" entries per minute for monitoring. What feature do you use?

A) CloudWatch Alarms
B) CloudWatch Metric Filters
C) CloudTrail
D) CloudWatch Dashboards

**Answer: B** — Metric Filters extract metrics from log data (count of error patterns, extract numeric values). Then you create a CloudWatch Alarm based on that metric.

---

**Q3:** You have an S3 bucket that should only be accessed by specific EC2 instances in your VPC. You do NOT want traffic going over the internet. What should you create?

A) NAT Gateway
B) Internet Gateway
C) VPC Gateway Endpoint for S3
D) Direct Connect

**Answer: C** — VPC Gateway Endpoints provide private connectivity from your VPC to S3 and DynamoDB without routing traffic through the internet. Free and easy to configure.

---

**Q4:** An RDS database is experiencing high CPU due to many read-heavy queries. What is the BEST solution?

A) Upgrade to a larger RDS instance class
B) Enable Multi-AZ deployment
C) Create a Read Replica and direct read traffic to it
D) Increase storage IOPS

**Answer: C** — Read Replicas offload read traffic from the primary instance. Multiple read replicas can be created for massive read scaling. Multi-AZ (B) is for high availability/failover, not read scaling.

---

**Q5:** Your Lambda function processes SQS messages, but some messages are failing consistently and going to a dead-letter queue. What is the most likely cause?

A) Lambda function is hitting memory limit
B) SQS visibility timeout is less than Lambda function execution time
C) Lambda function does not have permission to read SQS
D) SQS is in a different region than Lambda

**Answer: B** — If Lambda takes longer to process than the visibility timeout, SQS makes the message visible again while Lambda is still processing. Lambda picks it up again (duplicate), and eventually after N failures it goes to the DLQ. Fix: Set visibility timeout to 6× the Lambda function timeout.

---

**Q6:** You need to prevent engineers from accidentally deleting production CloudFormation stacks. What should you configure?

A) IAM permission boundaries
B) S3 bucket policies
C) CloudFormation stack policies with Deny on Delete
D) AWS Config rules

**Answer: C** — CloudFormation Stack Policies define what update actions are allowed on stack resources. A Deny on Delete for the stack prevents engineers from deleting critical stacks while still allowing updates.

---

**Q7:** Which AWS service provides continuous monitoring of your AWS account and notifies you when API calls match suspicious patterns (like root login, API calls from unknown IPs, or crypto-mining)?

A) AWS Config
B) Amazon Inspector
C) Amazon GuardDuty
D) AWS Security Hub

**Answer: C** — GuardDuty continuously analyzes CloudTrail logs, VPC Flow Logs, and DNS logs using ML to detect threats and suspicious patterns.

---

**Q8:** You have an application deployed on EC2. When you add new instances, you need to automatically configure them with the latest configuration from SSM Parameter Store. What is the best way to implement this?

A) Create an AMI with the configuration baked in, update AMI for each config change
B) Use EC2 User Data script to fetch parameters from SSM at launch
C) SSH into each new instance and manually copy configuration
D) Store configuration on EBS and attach to each instance

**Answer: B** — User Data runs at first launch. The script calls SSM Parameter Store to fetch the latest configuration values. This ensures each new instance always gets the current configuration without rebuilding the AMI.

---

**Q9:** You want to deploy code to 100 EC2 instances with zero downtime, automatic rollback on failure, and detailed deployment logs. Which service provides all of these?

A) CloudFormation
B) SSM Run Command
C) AWS CodeDeploy
D) Elastic Beanstalk

**Answer: C** — CodeDeploy supports rolling and blue/green deployments, has deployment lifecycle hooks (including health check validation), automatically rolls back on failure, and provides detailed deployment logs per instance.

---

**Q10:** A company must retain S3 objects for exactly 7 years for compliance and the objects must not be deletable by anyone, including administrators. Which S3 feature achieves this?

A) S3 Versioning
B) S3 Object Lock in Compliance Mode
C) S3 Object Lock in Governance Mode
D) MFA Delete

**Answer: B** — Object Lock Compliance Mode prevents ANY user, including root, from deleting or overwriting the object until the retention period expires. Governance Mode (C) can be overridden by users with special IAM permissions. Compliance Mode truly enforces the retention period.

---

**Q11:** Your web application behind CloudFront is experiencing a spike in SQL injection attempts. You want to block them immediately without changing application code. What should you do?

A) Update EC2 security group rules to block malicious IPs
B) Create a WAF Web ACL with the AWS Managed SQLi Rule Group and associate it with CloudFront
C) Enable GuardDuty on the EC2 instances
D) Apply an S3 bucket policy to deny suspicious requests

**Answer: B** — WAF with the AWSManagedRulesSQLiRuleSet inspects HTTP request content for SQL injection patterns and blocks them at the CloudFront edge, before requests reach your application.

---

**Q12:** Which pricing model provides the HIGHEST discount for EC2 instances but requires accepting interruption risk?

A) Reserved Instances (1-year, all upfront)
B) Reserved Instances (3-year, all upfront)
C) Spot Instances
D) Savings Plans (Compute)

**Answer: C** — Spot Instances offer up to 90% discount compared to On-Demand, but AWS can interrupt them with 2-minute notice when capacity is needed.

---

**Q13:** You are migrating an Oracle database to Amazon Aurora PostgreSQL. The application uses many Oracle-specific stored procedures. What AWS tool helps convert the stored procedures?

A) AWS DMS alone
B) AWS Schema Conversion Tool (SCT)
C) AWS DataSync
D) AWS Database Migration Service + Schema auto-conversion

**Answer: B** — SCT converts Oracle schema objects (tables, indexes, views, stored procedures, triggers) to PostgreSQL equivalents. DMS handles the data migration (row copying), while SCT handles the schema conversion.

---

**Q14:** An application sends messages to an SQS queue. Sometimes duplicate messages are being sent due to retry logic. The consumer must process each message exactly once and in order. Which SQS configuration achieves this?

A) Standard Queue with consumer deduplication logic
B) FIFO Queue with content-based deduplication enabled
C) Standard Queue with message delay
D) Standard Queue with long polling enabled

**Answer: B** — SQS FIFO queues guarantee ordering and exactly-once processing. Content-based deduplication automatically deduplicates messages with the same body within a 5-minute window, preventing duplicate processing from retry logic.

---

**Q15:** Your EC2 instances need to assume an IAM role to access S3. How should you configure this?

A) Create IAM users and embed access keys in the application code
B) Create an IAM role with S3 permissions and attach it as an instance profile
C) Create IAM users and store access keys in SSM Parameter Store
D) Enable IAM on the S3 bucket to allow all EC2 instances

**Answer: B** — Instance Profiles attach IAM roles to EC2 instances. The application uses the instance's role credentials automatically via the metadata service (no access keys in code). This is the correct, secure method. Never embed access keys in code (A).

---

**Q16:** You need to migrate 500 TB of video files from an on-premises NAS to S3. Your internet bandwidth is 100 Mbps. What is the MOST EFFICIENT migration method?

A) Upload directly using aws s3 sync over the internet
B) Order multiple AWS Snowball Edge devices to physically transfer the data
C) Use AWS DataSync over the internet
D) Set up AWS Direct Connect first

**Answer: B** — 500 TB over 100 Mbps = 40,000 seconds ÷ 8 bits = 500,000 MB ÷ 12.5 MB/s = ~11 days of continuous maximum throughput (likely 4-8 weeks in reality). Multiple Snowball Edge devices (each 80 TB usable) can complete the copy in days and be shipped back to AWS.

---

**Q17:** You want to automatically quarantine EC2 instances that GuardDuty identifies as compromised. What is the MOST automated approach?

A) Check GuardDuty daily and manually update security groups
B) Create an EventBridge rule triggered by GuardDuty findings that invokes a Lambda function to modify the security group
C) Set up email alerts from GuardDuty and have on-call engineers respond
D) Enable AWS Shield to automatically block compromised instances

**Answer: B** — EventBridge captures GuardDuty findings as events. A rule pattern matching high-severity findings triggers a Lambda function that: (1) Updates the instance's security group to block all traffic (quarantine). (2) Optionally creates a snapshot for forensics. (3) Sends an SNS notification to the security team. This is fully automated and responds in seconds.

---

**Q18:** Your application needs sub-millisecond latency database reads for a caching layer. The data is simple key-value pairs. Which service should you use?

A) Amazon RDS with read replicas
B) Amazon DynamoDB
C) Amazon ElastiCache for Redis
D) Amazon Aurora Serverless

**Answer: C** — ElastiCache Redis stores data in RAM and responds to GET operations in microseconds. RDS and DynamoDB store data on disk (DynamoDB's single-digit millisecond is slower than in-memory Redis for caching). Redis is specifically designed as an in-memory caching layer.

---

**Q19:** You are creating a highly available setup for your VPC. You have one NAT Gateway in us-east-1a. An engineer in us-east-1b tries to reach the internet but fails when us-east-1a goes down. How do you fix this?

A) Move the NAT Gateway to us-east-1b instead
B) Create a second NAT Gateway in us-east-1b and update the us-east-1b route table to use the local NAT Gateway
C) Use a NAT Instance instead of NAT Gateway
D) Create an Internet Gateway in both availability zones

**Answer: B** — For high availability, create one NAT Gateway per AZ. Each AZ's private subnet route table should route to its own NAT Gateway. If one AZ fails, the other AZ continues working independently. Internet Gateways (D) are already regional — there is only one per VPC.

---

**Q20:** An audit requirement states that all AWS API calls in your account must be logged and logs must be stored for 5 years, tamper-proof. What should you configure?

A) Enable VPC Flow Logs and store in S3
B) Enable CloudTrail for all regions with log file validation, deliver to S3 with Object Lock (Compliance Mode, 5-year retention)
C) Enable CloudWatch detailed monitoring
D) Configure S3 access logs for all buckets

**Answer: B** — CloudTrail records all AWS API calls. "For all regions" ensures no region is missed. "Log file validation" uses SHA-256 hashing to detect if log files are tampered with. Delivering to S3 with Object Lock in Compliance Mode with 5-year retention ensures logs cannot be deleted for 5 years, even by admins.

---

## 14.5 Last-Minute Review Tables

### Critical Service Comparison Tables

**Storage Services:**

| Service | Type | Use Case | Shared Access | Max Size |
|---------|------|----------|---------------|---------|
| EBS | Block | EC2 boot disk, databases | No (1 EC2 unless io2 multi-attach) | 64 TB |
| EFS | File (NFS) | Shared storage, Lambda /mnt | Yes (1000s of instances) | Unlimited |
| S3 | Object | Files, backups, data lake | Yes (HTTP API) | Unlimited |
| FSx for Windows | File (SMB) | Windows file shares | Yes | Unlimited |
| FSx for Lustre | File (HPC) | ML training, HPC | Yes | Petabytes |

**Database Services:**

| Service | Type | Use Case | Scaling | Managed |
|---------|------|----------|---------|---------|
| RDS MySQL/PostgreSQL | Relational | Standard OLTP | Read replicas | Partial |
| Aurora | Relational | High-performance OLTP | Auto, read replicas | Full |
| DynamoDB | NoSQL | Key-value, gaming, IoT | Auto (on-demand) | Full |
| ElastiCache Redis | In-memory | Caching, sessions, leaderboards | Cluster | Full |
| Redshift | Data warehouse | Analytics, OLAP | Node-based | Full |
| DocumentDB | Document | MongoDB compatible | Read replicas | Full |
| Neptune | Graph | Social networks, fraud detection | Read replicas | Full |

**Compute Services:**

| Service | Management | Scaling | Cost Model | Best For |
|---------|-----------|---------|------------|---------|
| EC2 | You manage OS | ASG (manual config) | Per hour | Full control, databases |
| ECS Fargate | AWS manages | Auto | Per vCPU/GB-hr | Containers without servers |
| Lambda | AWS manages all | Auto | Per invocation | Event-driven, short tasks |
| Elastic Beanstalk | AWS manages platform | Auto | EC2 cost + free PaaS | Quick deploy, PaaS |
| EKS | You manage cluster | K8s HPA | EC2/Fargate cost | K8s workloads |

**Security Services Quick Reference:**

| Service | What It Does | Key Fact |
|---------|-------------|---------|
| KMS | Encrypt/decrypt | CMK = $1/month; AWS Managed = free |
| Secrets Manager | Rotating secrets | $0.40/secret; auto-rotation |
| Parameter Store | Config + secrets | Free standard; SecureString = KMS |
| WAF | App firewall | SQLi, XSS, rate limiting |
| Shield Standard | Free DDoS | Automatic; all customers |
| Shield Advanced | Enhanced DDoS | $3,000/month; 24/7 DRT |
| GuardDuty | Threat detection | ML-based; CloudTrail + VPC Flow Logs |
| Inspector | CVE scanning | EC2 + ECR + Lambda |
| Macie | S3 data discovery | PII, credit cards, credentials |
| Security Hub | Central findings | Aggregates all security services |

---

## 14.6 Final Exam Checklist

Before taking the exam, make sure you can answer these questions:

**Networking:**
- [ ] What is the difference between a public and private subnet?
- [ ] When do you use Security Groups vs NACLs?
- [ ] How does a NAT Gateway work and where should it live?
- [ ] What is the difference between VPC Peering and Transit Gateway?
- [ ] When should you use Gateway Endpoints vs Interface Endpoints?

**Compute & Auto Scaling:**
- [ ] What are the three ASG scaling policy types?
- [ ] What is the difference between a Launch Template and Launch Configuration?
- [ ] When should you use Spot, On-Demand, and Reserved instances?
- [ ] What causes Lambda cold starts and how do you mitigate them?

**Storage:**
- [ ] What are the 6 S3 storage classes and when should you use each?
- [ ] What is S3 Object Lock Compliance vs Governance mode?
- [ ] When should you use EBS vs EFS?
- [ ] What is S3 Transfer Acceleration and when does it help?

**Databases:**
- [ ] What is the difference between Multi-AZ and Read Replicas?
- [ ] When should you use DynamoDB vs RDS?
- [ ] What is Aurora Global Database and when do you need it?
- [ ] When should you use Redis vs Memcached?

**Security:**
- [ ] What is the Shared Responsibility Model?
- [ ] How does envelope encryption work?
- [ ] What is the difference between Secrets Manager and Parameter Store?
- [ ] How does GuardDuty work (what data does it analyze)?
- [ ] When should you use WAF?

**Monitoring:**
- [ ] What metrics does CloudWatch collect by default for EC2?
- [ ] How do you monitor memory utilization on EC2?
- [ ] What is the difference between CloudWatch and CloudTrail?
- [ ] How do you create a custom metric?

**Good luck on the exam! Remember: AWS exams reward you for knowing WHEN to use each service, not just WHAT each service does.**
"""

with open(r"e:\fastapi\aws-admin\14_RealWorld_Projects_ExamPrep.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
