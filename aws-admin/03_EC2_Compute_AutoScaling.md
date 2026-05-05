# Chapter 3: EC2, Compute & Auto Scaling

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 3**: Deployment, Provisioning, and Automation (18%)
- **Domain 2**: Reliability and Business Continuity (partial)
- **Domain 6**: Cost and Performance Optimization (partial)

---

## 3.1 EC2 Fundamentals

Amazon Elastic Compute Cloud (EC2) provides **resizable virtual servers** (instances) in the cloud. It's the most fundamental and heavily-tested service for SysOps.

### EC2 Instance Components
```
┌─────────────────────────────────────────────────────────────┐
│                     EC2 INSTANCE                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AMI (Operating System + pre-installed software)    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Instance Type: c5.4xlarge                                  │
│  ├── vCPUs: 16                                              │
│  ├── Memory: 32 GiB                                         │
│  ├── Storage: EBS-only                                      │
│  └── Network: Up to 10 Gbps                                 │
│                                                             │
│  Storage: EBS Volume (Root) + Optional Data Volumes         │
│  Networking: ENI (Elastic Network Interface)                │
│  Security: Security Groups (stateful firewall)              │
│  IAM: Instance Profile (role for AWS API access)            │
│  User Data: Bootstrap script (runs once at launch)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3.2 EC2 Instance Types

AWS has **hundreds of instance types** organized into families:

| Family | Purpose | Examples | Use Cases |
|--------|---------|---------|----------|
| **General Purpose** | Balanced CPU/Memory | t3, t4g, m5, m6i | Web servers, dev environments |
| **Compute Optimized** | High CPU | c5, c6g, c6i | Batch processing, HPC, gaming |
| **Memory Optimized** | High RAM | r5, r6g, x1e | In-memory DBs, Redis, SAP HANA |
| **Storage Optimized** | High I/O | i3, d2, h1 | Data warehousing, Hadoop |
| **Accelerated Computing** | GPU/FPGA | p3, g4dn, inf1 | ML training, video encoding |
| **Burstable (T-class)** | Baseline + burst | t3, t3a, t4g | Dev/test, low-traffic sites |

### Instance Naming Convention
```
Example: m5.2xlarge

m  = Family (m = General Purpose)
5  = Generation (higher = newer, better price/performance)
.  = separator
2  = Size multiplier
xlarge = Base size

Common suffixes:
a = AMD processor
g = Graviton (ARM, best price/performance)
d = NVMe local storage
n = higher network bandwidth
z = high frequency
```

### T-Class Burstable Instances
T-class instances earn **CPU credits** when running below baseline. Credits are spent during bursts above baseline.

```
CPU Credit System:
┌────────────────────────────────────────────────────┐
│  Baseline CPU: 20% (t3.small example)              │
│                                                    │
│  Running at 10% → earns credits                   │
│  Running at 30% → spends credits                  │
│  Running at 20% → neutral                         │
│                                                    │
│  Max credit balance: 576 credits (t3.small)        │
│  Credit earn rate: 12 credits/hour                 │
│                                                    │
│  Unlimited mode: burst without credit limit        │
│  (charged for surplus CPU use)                     │
└────────────────────────────────────────────────────┘
```

```bash
# Check CPU credit balance
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUCreditBalance \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

---

## 3.3 AMI — Amazon Machine Image

An AMI is a **template** for launching EC2 instances. It contains:
- Root volume snapshot (OS, configuration)
- Launch permissions
- Block device mapping (which EBS volumes to attach)

### AMI Types
| Source | Description | Use Case |
|--------|-------------|---------|
| AWS-provided | Amazon Linux 2, Ubuntu, Windows Server | General purpose |
| AWS Marketplace | Third-party (CIS hardened, appliances) | Security-hardened, licensed software |
| Community AMIs | Public AMIs shared by community | Testing (verify source before using!) |
| Custom AMIs | Your own AMIs (golden images) | Standardized baseline |

### Creating a Golden AMI
```bash
# 1. Launch base instance, install/configure everything
# 2. Create AMI from running instance
aws ec2 create-image \
  --instance-id i-1234567890abcdef0 \
  --name "GoldenAMI-WebServer-v1.0-$(date +%Y%m%d)" \
  --description "Hardened web server with app v1.0" \
  --no-reboot

# 3. Tag the AMI
aws ec2 create-tags \
  --resources ami-0123456789abcdef0 \
  --tags \
    Key=Environment,Value=Production \
    Key=Version,Value=1.0 \
    Key=BaseOS,Value=AmazonLinux2023

# 4. Copy to another region for DR
aws ec2 copy-image \
  --source-image-id ami-0123456789abcdef0 \
  --source-region us-east-1 \
  --region us-west-2 \
  --name "GoldenAMI-WebServer-v1.0-copy"

# 5. Share with other accounts
aws ec2 modify-image-attribute \
  --image-id ami-0123456789abcdef0 \
  --launch-permission '{"Add":[{"UserId":"999999999999"}]}'
```

### AMI Lifecycle — EC2 Image Builder
Automates building, testing, and distributing hardened AMIs:

```yaml
# EC2 Image Builder pipeline example (CloudFormation)
ImageBuilderPipeline:
  Type: AWS::ImageBuilder::ImagePipeline
  Properties:
    Name: web-server-pipeline
    ImageRecipeArn: !Ref WebServerRecipe
    InfrastructureConfigurationArn: !Ref BuildInfra
    DistributionConfigurationArn: !Ref MultiRegionDist
    Schedule:
      ScheduleExpression: "cron(0 2 ? * 1 *)"  # Weekly at 2 AM Sunday
      PipelineExecutionStartCondition: EXPRESSION_MATCH_ONLY

WebServerRecipe:
  Type: AWS::ImageBuilder::ImageRecipe
  Properties:
    Name: web-server-recipe
    Version: 1.0.0
    ParentImage: arn:aws:imagebuilder:us-east-1:aws:image/amazon-linux-2023-x86/x.x.x
    Components:
      - ComponentArn: !Sub arn:aws:imagebuilder:${AWS::Region}:aws:component/update-linux/x.x.x
      - ComponentArn: !Ref HardeningComponent
      - ComponentArn: !Ref InstallNginxComponent
```

---

## 3.4 EC2 Launch — User Data & Metadata

### User Data
Script that runs **once** at instance launch (as root):

```bash
#!/bin/bash
# This runs once when the instance first starts

# Update system
yum update -y

# Install web server
amazon-linux-extras enable nginx1
yum install -y nginx

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Configure application
cat > /etc/nginx/conf.d/app.conf << 'EOF'
server {
    listen 80;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

# Fetch application from S3
aws s3 cp s3://my-app-bucket/latest/app.tar.gz /opt/app.tar.gz
cd /opt && tar xzf app.tar.gz

# Start services
systemctl enable --now nginx
systemctl enable --now app

# Signal CloudFormation that setup is complete
/opt/aws/bin/cfn-signal -e $? \
  --stack ${AWS::StackName} \
  --resource AutoScalingGroup \
  --region ${AWS::Region}
```

### Instance Metadata Service (IMDS)
Available inside any EC2 instance at `169.254.169.254`:

```bash
# Get instance ID (IMDSv1 - legacy, less secure)
curl http://169.254.169.254/latest/meta-data/instance-id

# IMDSv2 (recommended - requires session token)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Use token for all metadata requests
INSTANCE_ID=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id)

REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region)

# Get IAM temporary credentials
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/MyRole

# Get user data
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/user-data
```

### Enforce IMDSv2 (SysOps Security Best Practice)
```bash
# Require IMDSv2 when launching new instance
aws ec2 run-instances \
  --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1

# Enforce on existing instance
aws ec2 modify-instance-metadata-options \
  --instance-id i-1234567890abcdef0 \
  --http-tokens required \
  --http-put-response-hop-limit 1

# Enforce via AWS Config rule (auto-remediation)
aws configservice put-config-rule \
  --config-rule file://require-imdsv2-rule.json
```

---

## 3.5 EC2 Networking

### Elastic Network Interfaces (ENI)
- Virtual NIC attached to an EC2 instance
- Has primary private IPv4, optional secondary private IPs, public IPv4, IPv6
- Security groups are attached to ENIs, not instances
- Can be moved between instances (useful for high availability failover)

```bash
# Create an ENI
aws ec2 create-network-interface \
  --subnet-id subnet-0123456789abcdef0 \
  --groups sg-0123456789abcdef0 \
  --description "Failover ENI for web server"

# Attach to instance
aws ec2 attach-network-interface \
  --network-interface-id eni-0123456789abcdef0 \
  --instance-id i-1234567890abcdef0 \
  --device-index 1

# Detach and move to another instance (failover)
aws ec2 detach-network-interface \
  --attachment-id eni-attach-0123456789abcdef0

aws ec2 attach-network-interface \
  --network-interface-id eni-0123456789abcdef0 \
  --instance-id i-0987654321fedcba0 \  # New instance
  --device-index 1
```

### Elastic IP (EIP)
- Static public IPv4 address
- Persists across instance stop/start (unlike regular public IPs)
- Free when associated with running instance; charged when unassociated

```bash
# Allocate EIP
EIP=$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)

# Associate with instance
aws ec2 associate-address \
  --instance-id i-1234567890abcdef0 \
  --allocation-id $EIP

# Move EIP to another instance (failover)
ASSOC_ID=$(aws ec2 describe-addresses \
  --allocation-ids $EIP \
  --query 'Addresses[0].AssociationId' \
  --output text)

aws ec2 disassociate-address --association-id $ASSOC_ID

aws ec2 associate-address \
  --instance-id i-0987654321fedcba0 \
  --allocation-id $EIP
```

---

## 3.6 EC2 Storage — EBS Deep Dive

### EBS Volume Types

| Volume Type | Use Case | Max IOPS | Max Throughput | Notes |
|-------------|---------|---------- |---------------|-------|
| **gp3** | General purpose (recommended) | 16,000 | 1,000 MB/s | IOPS independent of size |
| **gp2** | General purpose (legacy) | 16,000 | 250 MB/s | 3 IOPS/GB, bursts to 3,000 |
| **io2 Block Express** | Critical DBs, sub-ms latency | 256,000 | 4,000 MB/s | Most expensive, most IOPS |
| **io1** | I/O-intensive databases | 64,000 | 1,000 MB/s | Legacy io2 predecessor |
| **st1** | Throughput-intensive sequential | 500 | 500 MB/s | Big data, log processing |
| **sc1** | Cold storage, infrequent access | 250 | 250 MB/s | Lowest cost HDD |

```bash
# Create optimized gp3 volume
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --volume-type gp3 \
  --size 100 \
  --iops 4000 \
  --throughput 250 \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id

# Attach to instance
aws ec2 attach-volume \
  --volume-id vol-0123456789abcdef0 \
  --instance-id i-1234567890abcdef0 \
  --device /dev/xvdf

# Modify volume (online, no restart needed)
aws ec2 modify-volume \
  --volume-id vol-0123456789abcdef0 \
  --volume-type gp3 \
  --size 200 \
  --iops 6000

# Monitor modification progress
aws ec2 describe-volumes-modifications \
  --volume-ids vol-0123456789abcdef0

# After modification, extend the filesystem (Linux)
sudo growpart /dev/xvdf 1
sudo xfs_growfs /  # for XFS
# OR
sudo resize2fs /dev/xvdf1  # for ext4
```

### EBS Snapshots
```bash
# Create snapshot
aws ec2 create-snapshot \
  --volume-id vol-0123456789abcdef0 \
  --description "Pre-deployment snapshot $(date +%Y%m%d)" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=pre-deploy}]'

# Copy snapshot to another region (DR)
aws ec2 copy-snapshot \
  --source-region us-east-1 \
  --source-snapshot-id snap-0123456789abcdef0 \
  --destination-region us-west-2 \
  --encrypted

# Create volume from snapshot
aws ec2 create-volume \
  --snapshot-id snap-0123456789abcdef0 \
  --availability-zone us-east-1b \
  --volume-type gp3

# Automate snapshots with Data Lifecycle Manager
aws dlm create-lifecycle-policy \
  --description "Daily snapshots, 14-day retention" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::123456789012:role/AWSDataLifecycleManagerDefaultRole \
  --policy-details '{
    "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
    "ResourceTypes": ["VOLUME"],
    "TargetTags": [{"Key":"Backup","Value":"true"}],
    "Schedules": [{
      "Name": "DailySnapshots",
      "CreateRule": {"Interval":24,"IntervalUnit":"HOURS","Times":["02:00"]},
      "RetainRule": {"Count":14},
      "CopyTags": true
    }]
  }'
```

---

## 3.7 EC2 Placement Groups

Placement groups affect how instances are placed across underlying hardware:

| Type | Spread Logic | Latency | Availability | Use Case |
|------|-------------|---------|--------------|---------|
| **Cluster** | Same rack | Lowest (25 Gbps) | Single AZ only | HPC, big data, ML training |
| **Spread** | Different hardware | Higher | Up to 7/AZ | Critical single instances needing HA |
| **Partition** | Different partitions (racks) | Medium | Multi-AZ | Cassandra, HDFS, Kafka |

```bash
# Create cluster placement group
aws ec2 create-placement-group \
  --group-name hpc-cluster \
  --strategy cluster

# Create partition placement group
aws ec2 create-placement-group \
  --group-name kafka-partition-group \
  --strategy partition \
  --partition-count 3

# Launch instance into placement group
aws ec2 run-instances \
  --image-id ami-0123456789abcdef0 \
  --instance-type c5n.9xlarge \
  --placement 'GroupName=hpc-cluster'
```

---

## 3.8 EC2 Auto Scaling

Auto Scaling automatically adjusts the number of EC2 instances based on demand.

### Auto Scaling Components
```
┌─────────────────────────────────────────────────────────────┐
│                   AUTO SCALING GROUP (ASG)                   │
│                                                             │
│  Launch Template/Config (WHAT to launch)                    │
│  ├── AMI, Instance Type, Security Groups                    │
│  ├── User Data, IAM Role, Key Pair                          │
│  └── EBS volumes, Network config                            │
│                                                             │
│  Capacity Settings (HOW MANY instances)                     │
│  ├── Minimum: 2 (never go below)                            │
│  ├── Desired: 4 (current target)                            │
│  └── Maximum: 10 (never exceed)                             │
│                                                             │
│  Health Checks (WHICH instances are healthy)                │
│  ├── EC2 health check (instance state)                      │
│  └── ELB health check (target group health)                 │
│                                                             │
│  Scaling Policies (WHEN to scale)                           │
│  ├── Target Tracking (CPU at 50%)                           │
│  ├── Step Scaling (tiered response)                         │
│  ├── Scheduled (known traffic patterns)                     │
│  └── Predictive (ML-based forecasting)                      │
└─────────────────────────────────────────────────────────────┘
```

### Launch Templates (Modern Approach)
```bash
# Create launch template
aws ec2 create-launch-template \
  --launch-template-name WebServerTemplate \
  --version-description "v1.0 - Initial" \
  --launch-template-data '{
    "ImageId": "ami-0123456789abcdef0",
    "InstanceType": "t3.medium",
    "KeyName": "my-key-pair",
    "SecurityGroupIds": ["sg-0123456789abcdef0"],
    "IamInstanceProfile": {"Name": "WebServerProfile"},
    "MetadataOptions": {
      "HttpTokens": "required",
      "HttpPutResponseHopLimit": 1
    },
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [{"Key":"Name","Value":"web-server"}]
    }],
    "UserData": "'$(base64 -w 0 userdata.sh)'"
  }'

# Create version for instance type change
aws ec2 create-launch-template-version \
  --launch-template-name WebServerTemplate \
  --source-version 1 \
  --version-description "v1.1 - Updated to t3.large" \
  --launch-template-data '{"InstanceType":"t3.large"}'
```

### Create Auto Scaling Group
```bash
# Create ASG with multiple AZs
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name web-asg \
  --launch-template LaunchTemplateName=WebServerTemplate,Version='$Latest' \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 2 \
  --vpc-zone-identifier "subnet-aaa,subnet-bbb,subnet-ccc" \
  --target-group-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/xxx \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --tags Key=Environment,Value=production,PropagateAtLaunch=true

# Enable instance refresh (rolling replace with new launch template)
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name web-asg \
  --preferences '{
    "InstanceWarmup": 300,
    "MinHealthyPercentage": 90,
    "SkipMatching": true
  }'
```

### Scaling Policies

**Target Tracking (Recommended — simplest):**
```bash
# Keep average CPU at 50%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-asg \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 50.0,
    "DisableScaleIn": false
  }'

# Track ALB request count per target
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-asg \
  --policy-name alb-request-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/my-alb/xxxx/targetgroup/my-tg/yyyy"
    },
    "TargetValue": 1000.0
  }'
```

**Step Scaling (More control):**
```bash
# Create CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "high-cpu-alarm" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=web-asg \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:xxx:autoScalingGroupName/web-asg:policyName/scale-out

# Step scaling policy (scale based on threshold magnitude)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-asg \
  --policy-name step-scale-out \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[
    {"MetricIntervalLowerBound":0,"MetricIntervalUpperBound":10,"ScalingAdjustment":1},
    {"MetricIntervalLowerBound":10,"MetricIntervalUpperBound":20,"ScalingAdjustment":2},
    {"MetricIntervalLowerBound":20,"ScalingAdjustment":3}
  ]'
```

**Scheduled Scaling:**
```bash
# Scale up every weekday morning at 7 AM
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name web-asg \
  --scheduled-action-name scale-up-morning \
  --recurrence "0 12 * * 1-5" \   # 7 AM EST = 12 UTC
  --min-size 4 \
  --desired-capacity 6 \
  --max-size 20

# Scale down every weekday evening at 7 PM
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name web-asg \
  --scheduled-action-name scale-down-evening \
  --recurrence "0 0 * * 1-5" \    # 7 PM EST = 0 UTC
  --min-size 2 \
  --desired-capacity 2 \
  --max-size 10
```

### Lifecycle Hooks
Lifecycle hooks pause instance launches/terminations so you can run custom logic:

```
Instance Launch:
  Pending → [Lifecycle Hook: Pending:Wait] → InService
             (run: install agent, warm up cache, register in config)

Instance Termination:
  InService → [Lifecycle Hook: Terminating:Wait] → Terminated
               (run: deregister, flush logs, drain connections)
```

```bash
# Create lifecycle hook for launching
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name web-asg \
  --lifecycle-hook-name launch-hook \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --heartbeat-timeout 300 \
  --default-result CONTINUE \
  --notification-target-arn arn:aws:sqs:us-east-1:123456789012:lifecycle-queue

# Lambda processes the hook, then completes it
# (via aws autoscaling complete-lifecycle-action)
```

---

## 3.9 Elastic Load Balancing (ELB)

ELB distributes incoming traffic across multiple targets (EC2, Lambda, containers).

### ELB Types Comparison

| Feature | Application LB (ALB) | Network LB (NLB) | Gateway LB (GWLB) |
|---------|---------------------|-----------------|------------------|
| Layer | 7 (HTTP/HTTPS) | 4 (TCP/UDP/TLS) | 3 (IP) |
| Routing | Path, host, header | IP, Port | — |
| Performance | Flexible | Extreme (millions/sec) | — |
| Fixed IP | No (use NLB) | Yes (per AZ) | — |
| WebSockets | Yes | Yes | — |
| gRPC | Yes | — | — |
| Use Case | Web apps, microservices | Gaming, IoT, real-time | Security appliances |

### ALB Deep Dive
```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name my-alb \
  --subnets subnet-aaa subnet-bbb subnet-ccc \
  --security-groups sg-0123456789abcdef0 \
  --scheme internet-facing \
  --type application

# Create target group
aws elbv2 create-target-group \
  --name web-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-0123456789abcdef0 \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --target-type instance

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/xxx \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...

# Create HTTP → HTTPS redirect rule
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions '[{
    "Type": "redirect",
    "RedirectConfig": {
      "Protocol": "HTTPS",
      "Port": "443",
      "StatusCode": "HTTP_301"
    }
  }]'
```

### ALB Listener Rules (Path-based & Host-based routing)
```bash
# Path-based routing rule
aws elbv2 create-rule \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --priority 10 \
  --conditions '[
    {"Field":"path-pattern","Values":["/api/*"]},
    {"Field":"http-header","HttpHeaderConfig":{"HttpHeaderName":"X-Version","Values":["v2"]}}
  ]' \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/api-v2-tg/xxx

# Host-based routing
aws elbv2 create-rule \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --priority 20 \
  --conditions '[{"Field":"host-header","Values":["api.example.com"]}]' \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/api-tg/xxx
```

### Connection Draining & Deregistration Delay
```bash
# Set deregistration delay (default 300 seconds)
# Allows in-flight requests to complete before deregistering
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --attributes Key=deregistration_delay.timeout_seconds,Value=60

# Slow-start mode (gradually increase traffic to new targets)
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --attributes Key=slow_start.duration_seconds,Value=120
```

---

## 3.10 EC2 Purchasing Options

### On-Demand vs Reserved vs Spot

```
Cost Comparison (rough):
┌──────────────────────────────────────────────────────────────┐
│ ON-DEMAND    $0.0832/hr  (100% baseline)                    │
│ RESERVED 1yr $0.0528/hr  (36% savings, no upfront)         │
│ RESERVED 1yr $0.0464/hr  (44% savings, all upfront)        │
│ RESERVED 3yr $0.0336/hr  (60% savings, no upfront)         │
│ RESERVED 3yr $0.0255/hr  (69% savings, all upfront)        │
│ SAVINGS PLANS            (up to 66% savings, flexible)     │
│ SPOT         $0.0100/hr  (up to 90% savings, interruptible)│
└──────────────────────────────────────────────────────────────┘
(Example prices for t3.medium in us-east-1)
```

### Spot Instances — Deep Dive

Spot instances use **spare AWS capacity**. They can be interrupted with 2-minute warning.

```bash
# Request spot instance
aws ec2 run-instances \
  --instance-type m5.large \
  --image-id ami-0123456789abcdef0 \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"MaxPrice":"0.05","SpotInstanceType":"persistent"}}'

# Check spot price history
aws ec2 describe-spot-price-history \
  --instance-types m5.large m5.xlarge c5.large \
  --start-time $(date -u +%Y-%m-%dT%H:%M:%SZ -d "1 day ago") \
  --product-descriptions "Linux/UNIX" \
  --query 'SpotPriceHistory[*].[InstanceType,SpotPrice,Timestamp]' \
  --output table
```

**Spot Fleet — Mixed instances for fault tolerance:**
```json
{
  "TargetCapacity": 20,
  "IamFleetRole": "arn:aws:iam::123456789012:role/AmazonEC2SpotFleetRole",
  "LaunchSpecifications": [
    {
      "InstanceType": "m5.large",
      "ImageId": "ami-xxx",
      "SubnetId": "subnet-aaa"
    },
    {
      "InstanceType": "m5.xlarge",
      "ImageId": "ami-xxx",
      "SubnetId": "subnet-bbb",
      "WeightedCapacity": 2
    }
  ],
  "AllocationStrategy": "diversified",
  "SpotPrice": "0.10",
  "TerminationPolicies": ["Default"]
}
```

### Spot Interruption Handling
```python
import boto3
import requests

def handle_spot_interruption():
    """Check for spot interruption warning from IMDS and handle gracefully."""
    try:
        # Check for 2-minute interruption warning
        token = requests.put(
            'http://169.254.169.254/latest/api/token',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
            timeout=1
        ).text
        
        response = requests.get(
            'http://169.254.169.254/latest/meta-data/spot/interruption-action',
            headers={'X-aws-ec2-metadata-token': token},
            timeout=1
        )
        
        if response.status_code == 200:
            action = response.text  # "hibernate", "stop", or "terminate"
            print(f"⚠️  Spot interruption incoming! Action: {action}")
            
            # Graceful shutdown actions:
            # 1. Stop accepting new requests (remove from LB target group)
            # 2. Finish processing current jobs
            # 3. Save state to S3 or DynamoDB
            # 4. Drain connections
            graceful_shutdown()
    except requests.exceptions.ConnectionError:
        pass  # Not a spot instance or no interruption

def graceful_shutdown():
    """Perform graceful cleanup before spot interruption."""
    # Deregister from ALB target group
    elbv2 = boto3.client('elbv2')
    # ... deregister logic
    
    # Flush any pending work to SQS for reprocessing
    sqs = boto3.client('sqs')
    # ... enqueue pending work
```

---

## 3.11 EC2 Security Best Practices

### Security Groups
```bash
# Create security group with minimal access
aws ec2 create-security-group \
  --group-name web-sg \
  --description "Web server security group" \
  --vpc-id vpc-0123456789abcdef0

# Allow HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow SSH only from bastion host SG (not IP ranges)
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 22 \
  --source-group sg-bastion-sg-id

# Block all outbound to 0.0.0.0/0 except specific
aws ec2 revoke-security-group-egress \
  --group-id sg-0123456789abcdef0 \
  --protocol -1 \
  --cidr 0.0.0.0/0

# Only allow outbound to DB security group
aws ec2 authorize-security-group-egress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 5432 \
  --source-group sg-db-sg-id
```

### Systems Manager Session Manager (No SSH Required)
```bash
# Connect to instance without SSH key or open port 22
aws ssm start-session --target i-1234567890abcdef0

# Port forwarding to RDS through SSM
aws ssm start-session \
  --target i-1234567890abcdef0 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'
```

---

## 3.12 Real-World Project: Auto-Healing Web Tier

### Scenario
An e-commerce site needs to handle Black Friday traffic (10x normal) automatically and self-heal from instance failures.

### Architecture
```
Internet → Route 53 → ALB (Multi-AZ)
                      ├── AZ-1: ASG Instances (min 2)
                      ├── AZ-2: ASG Instances (min 2)
                      └── AZ-3: ASG Instances (min 1)
                              ↓
                           RDS Multi-AZ
                           ElastiCache
```

### CloudFormation Template
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Auto-healing web tier with Auto Scaling

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
  AmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64
  InstanceType:
    Type: String
    Default: t3.medium

Resources:
  WebSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Web server security group
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          SourceSecurityGroupId: !Ref ALBSecurityGroup
      Tags:
        - Key: Name
          Value: web-sg

  WebLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: web-server-lt
      LaunchTemplateData:
        ImageId: !Ref AmiId
        InstanceType: !Ref InstanceType
        SecurityGroupIds:
          - !Ref WebSecurityGroup
        IamInstanceProfile:
          Name: !Ref InstanceProfile
        MetadataOptions:
          HttpTokens: required
          HttpPutResponseHopLimit: 1
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum update -y
            yum install -y amazon-cloudwatch-agent nginx
            systemctl enable --now nginx
            # Install CloudWatch agent config
            /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
              -a fetch-config \
              -m ec2 \
              -s \
              -c ssm:/web-server/cloudwatch-config
            /opt/aws/bin/cfn-signal -e $? \
              --stack ${AWS::StackName} \
              --resource WebASG \
              --region ${AWS::Region}

  WebASG:
    Type: AWS::AutoScaling::AutoScalingGroup
    CreationPolicy:
      ResourceSignal:
        Count: 2
        Timeout: PT10M
    UpdatePolicy:
      AutoScalingRollingUpdate:
        MinInstancesInService: 2
        MaxBatchSize: 1
        PauseTime: PT5M
        WaitOnResourceSignals: true
        SuspendProcesses:
          - HealthCheck
          - ReplaceUnhealthy
    Properties:
      LaunchTemplate:
        LaunchTemplateId: !Ref WebLaunchTemplate
        Version: !GetAtt WebLaunchTemplate.LatestVersionNumber
      MinSize: '2'
      MaxSize: '20'
      DesiredCapacity: '2'
      VPCZoneIdentifier: !Ref SubnetIds
      TargetGroupARNs:
        - !Ref WebTargetGroup
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      MetricsCollection:
        - Granularity: 1Minute
      Tags:
        - Key: Name
          Value: web-asg-instance
          PropagateAtLaunch: true

  CPUScalingPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref WebASG
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ASGAverageCPUUtilization
        TargetValue: 60.0
```

---

## 3.13 Practice Questions (SysOps Exam Level)

**Q1:** An ASG has MinSize=2, MaxSize=10, DesiredCapacity=4. The ALB health check fails for 2 instances. What happens?

**A:** The ASG detects unhealthy instances (via ELB health check), terminates the 2 unhealthy instances, and launches 2 new replacement instances to maintain DesiredCapacity=4. The 2 healthy instances continue serving traffic during this process.

---

**Q2:** You need to deploy new code to an ASG without downtime. What options do you have?

**A:**
1. **Instance Refresh** — rolling replacement using new launch template version (recommended)
2. **Rolling Update via UpdatePolicy** — CloudFormation manages rolling replacement
3. **Blue/Green** — spin up new ASG, shift traffic via ALB weighted target groups, then delete old ASG

```bash
# Instance refresh with minimum 90% healthy
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name web-asg \
  --preferences MinHealthyPercentage=90,InstanceWarmup=300
```

---

**Q3:** A t3.medium instance shows high CPU (100%) at 3 AM with no traffic. What could cause this?

**A:**
- **Cron job** running at that time (log rotation, backup, update)
- **Automated OS patching** (AWS Systems Manager Patch Manager)
- **CloudWatch agent** sending metrics
- **Security scan** scheduled at that time
- **T3 burstable**: spending accumulated CPU credits

Check CloudWatch metrics (CPUCreditUsage) and system logs:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUCreditUsage \
  --dimensions Name=InstanceId,Value=i-xxx \
  --start-time 2025-01-01T02:00:00Z \
  --end-time 2025-01-01T04:00:00Z \
  --period 300 --statistics Sum
```

---

**Q4:** You have a stateful application that cannot easily scale horizontally. The instance type needs an upgrade from c5.large to c5.2xlarge. What is the process?

**A:**
1. Stop the instance (not terminate)
2. Change instance type: `aws ec2 modify-instance-attribute --instance-id i-xxx --instance-type c5.2xlarge`
3. Start the instance
4. **Note**: EIP and EBS data are preserved. Public IPv4 changes on stop/start unless you use an EIP.

---

**Q5:** A Spot instance was terminated unexpectedly. Your batch job was halfway complete. How do you build resilience against this?

**A:**
1. Use **Spot + On-Demand mixed fleet** (ASG or Spot Fleet with `diversified` strategy)
2. Implement **checkpointing** — save progress to S3/DynamoDB every N iterations
3. Use **SQS for job queue** — job visibility timeout causes failed jobs to reappear automatically
4. Monitor `EC2 Spot Instance Interruption Warning` EventBridge event for graceful shutdown
5. Use **Spot placement scores** to pick most available instance type/size

---

## Key EC2 Terms for Exam

| Term | Definition |
|------|-----------|
| AMI | Amazon Machine Image — template for instances |
| Instance Profile | Container for IAM role assigned to EC2 |
| User Data | Bootstrap script runs once at launch |
| IMDS | Instance Metadata Service — 169.254.169.254 |
| EBS | Elastic Block Store — persistent block storage |
| EIP | Elastic IP — static public IPv4 |
| ENI | Elastic Network Interface — virtual NIC |
| ASG | Auto Scaling Group — automatic capacity management |
| Launch Template | Modern way to define instance configuration |
| Health Check Grace Period | Time before ASG health checks kick in after launch |
| Cooldown | Time ASG waits after scaling before scaling again |
| Lifecycle Hook | Pause launch/terminate for custom logic |
| gp3 | Latest SSD EBS type — best price/performance |
| Placement Group | Control physical placement of instances |
| Spot | Spare capacity up to 90% discount; interruptible |
| Reserved Instance | 1-3 year commitment for up to 72% discount |
