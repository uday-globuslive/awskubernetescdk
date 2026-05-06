
content = r"""# Chapter 3: EC2 — Elastic Compute Cloud & Auto Scaling
## (Virtual Servers in the Cloud — From Zero to Production Ready)

---

## 3.1 What is EC2? — The Virtual Computer in the Cloud

### The Simple Explanation

Imagine you need a computer to run your application. You have two options:

**Option 1: Buy a physical computer**
- Order it online → wait 2 weeks → it arrives → set it up → install OS → install software → finally start working
- Cost: $3,000–$20,000 upfront
- If you need a bigger computer next year? Buy another one.
- If you only need it for 3 months? Too bad, you own it now.

**Option 2: Use EC2 (Elastic Compute Cloud)**
- Open AWS console → click a few buttons → computer ready in 60 seconds
- Cost: $0.01–$20/hour depending on size, paid by the second
- Need a bigger computer? Stop the instance, change the type, start again — takes 5 minutes
- Done using it? Just stop or terminate it — pay only for what you used

**EC2 = Virtual computers you rent from AWS by the second.**

"Virtual" means it is software-defined. Your EC2 instance runs on AWS's physical hardware, but it appears to you as its own dedicated computer. AWS can run hundreds of virtual machines on one physical server.

### What Can You Run on EC2?

Anything a computer can run:
- Web applications (Python Django, Node.js, Java Spring, PHP)
- Databases (if you want to manage them yourself instead of using RDS)
- Application servers (Tomcat, nginx, Apache)
- Machine learning workloads (on GPU instances)
- Windows desktop applications (via remote desktop)
- SAP, Oracle, or any enterprise software
- Game servers
- Continuous integration build agents (Jenkins workers)

---

## 3.2 EC2 Instance Types — Choosing the Right Computer

### The Instance Family Naming Convention

EC2 instance names follow a pattern:
```
[Family][Generation][Attribute].[Size]

Examples:
  m6i.large
  │ │ │   └── Size: nano, micro, small, medium, large, xlarge, 2xlarge, etc.
  │ │ └────── Attribute: i=Intel, g=Graviton (ARM), n=Network optimized, etc.
  │ └──────── Generation: 6 (higher = newer, better price/performance)
  └────────── Family: m=General Purpose, c=Compute, r=Memory, etc.
```

### The Instance Families — Choosing the Right Tool

**General Purpose (M and T families) — Balanced CPU, Memory, Network**

Think of these like a general contractor: they can do a bit of everything reasonably well.

```
T family (t3, t4g) — Burstable Performance:
  - Normally low CPU usage, but CAN burst when needed
  - Earns CPU credits when idle, spends them during bursts
  - Best for: Web servers, dev/test environments, small databases
  - Example: t3.micro (2 vCPU, 1 GB RAM, 2 EBS volumes) — cheapest general option
  - T instances in "unlimited" mode can burst indefinitely (extra charge applies)

M family (m6i, m7g) — Standard General Purpose:
  - Balanced compute, memory, and network resources
  - Best for: Web servers, app servers, enterprise apps, gaming servers
  - Example: m6i.large (2 vCPU, 8 GB RAM)
  - Example: m6i.4xlarge (16 vCPU, 64 GB RAM)
```

**Compute Optimized (C family) — High CPU, Less Memory**

Think of these like a sprinter: extremely fast but built for speed, not endurance.

```
C family (c6i, c7g) — Compute Optimized:
  - High ratio of CPU to RAM
  - Best for: Video encoding, batch processing, high-performance web servers,
             machine learning inference, scientific computing
  - Example: c6i.large (2 vCPU, 4 GB RAM) — same CPU as m6i.large, half the RAM = cheaper
  - Example: c6i.32xlarge (128 vCPU, 256 GB RAM) — massive parallel compute
```

**Memory Optimized (R, X, U families) — Lots of RAM**

Think of these like a library with millions of books: designed to keep huge amounts of data in memory.

```
R family (r6i, r7g) — Memory Optimized:
  - High RAM to CPU ratio
  - Best for: In-memory databases (Redis), SAP HANA, real-time big data processing
  - Example: r6i.large (2 vCPU, 16 GB RAM) — vs m6i.large (2 vCPU, 8 GB RAM)
  - 2x the RAM for similar CPU

X family (x2idn, x2iedn) — Extra Large Memory:
  - Terabytes of RAM
  - Best for: SAP HANA, large in-memory databases
  - Example: x2idn.32xlarge (128 vCPU, 2,048 GB RAM = 2 TB!)

U family (u-6tb1.metal) — Ultra High Memory:
  - Up to 24 TB of RAM
  - For the largest SAP HANA deployments in the world
```

**Storage Optimized (I, D, H families) — Fast Local NVMe Storage**

Think of these like a warehouse: optimized for storing and retrieving large amounts of data very quickly.

```
I family (i4i) — NVMe SSD Storage:
  - Local NVMe SSDs with millions of IOPS
  - Best for: High I/O NoSQL databases (Cassandra, MongoDB), data warehouses
  - Example: i4i.4xlarge (16 vCPU, 128 GB RAM, 3.75 TB NVMe)
  - NOTE: Local storage is temporary — data lost if instance is stopped!

D family (d3en) — Dense HDD Storage:
  - Massive amounts of HDD storage
  - Best for: Distributed filesystems (HDFS), data warehousing
  - Example: d3en.8xlarge (32 vCPU, 128 GB RAM, 96 TB HDD)

H family (h1) — HDD Storage with High Throughput:
  - Best for: MapReduce, distributed filesystems
```

**Accelerated Computing (P, G, Inf, Trn families) — GPU/Special Hardware**

```
P family (p4d, p4de) — ML Training:
  - NVIDIA A100 GPUs
  - Best for: Machine learning training, high-performance computing
  - Example: p4d.24xlarge — 8x NVIDIA A100 GPUs, 1.1 TB RAM, $32/hour!

G family (g5, g4dn) — ML Inference + Graphics:
  - NVIDIA GPUs but less expensive than P family
  - Best for: ML inference, video transcoding, game streaming, virtual desktops
  - Example: g5.xlarge — 1 NVIDIA A10G GPU, $1.006/hour

Inf family (inf2) — ML Inference:
  - AWS-designed Inferentia chips, optimized for inference at low cost
  - Best for: Running trained ML models at scale, very cost-effective

Trn family (trn1) — ML Training:
  - AWS-designed Trainium chips, competitive with NVIDIA for training cost
```

### Choosing the Right Instance — Decision Guide

```
Your application uses lots of CPU (video encoding, batch processing)?
→ C family (c6i, c7g)

Your application needs lots of RAM (in-memory database, SAP)?
→ R family (r6i, r7g) or X family

Your application needs fast local disk I/O (NoSQL, data warehouse)?
→ I family (i4i)

Your application is ML training?
→ P family (NVIDIA) or Trn family (AWS Trainium)

Your application is ML inference (running predictions)?
→ G family or Inf family

Your application is a general web server or app server?
→ M family (m6i, m7g) for stable workloads
→ T family (t3, t4g) for dev/test or low-traffic sites

Your application is Windows with enterprise software?
→ M family usually works well
```

---

## 3.3 Amazon Machine Images (AMIs) — What Gets Pre-installed

### What is an AMI?

An **AMI (Amazon Machine Image)** is a template containing everything needed to launch an instance:
- The **operating system** (Amazon Linux 2, Ubuntu, Windows Server 2022, etc.)
- The **pre-installed software** (could be blank, or could have Apache, MySQL, etc.)
- The **configuration** (which ports are open, what services start on boot)
- Optional: **data volumes** (EBS snapshots to attach)

**Analogy:** An AMI is like a computer's **disk image** (similar to a .iso file). When you launch an EC2 instance, you are creating a fresh computer from that image. Like buying a laptop that comes pre-installed with Windows and Microsoft Office.

### Types of AMIs

**1. AWS-Provided AMIs:**
- Maintained by AWS
- Include: Amazon Linux 2023, Amazon Linux 2, Ubuntu, Windows Server, Red Hat, SUSE
- Always up-to-date security patches (but you must still patch after launch)
- Amazon Linux 2 is free and optimized for EC2 (good default choice)

```bash
# Find the latest Amazon Linux 2023 AMI in us-east-1
aws ssm get-parameter \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query 'Parameter.Value' --output text

# Find all Ubuntu 22.04 LTS AMIs
aws ec2 describe-images \
  --owners 099720109477 \
  --filters \
    "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
    "Name=state,Values=available" \
  --query 'sort_by(Images,&CreationDate)[-1].[ImageId,Name,CreationDate]' \
  --output table
```

**2. Marketplace AMIs:**
- Sold by third-party vendors in the AWS Marketplace
- Examples: Ubuntu Pro with 10-year support, WordPress pre-installed, pfSense firewall
- Some are free, some have additional hourly charges
- Good for getting complex software set up quickly

**3. Community AMIs:**
- Shared publicly by other AWS users
- **Use with caution** — not vetted by AWS, could contain malware
- Only use from trusted, well-known sources

**4. Custom AMIs — Your Own Golden Images:**
This is the most important type for SysOps!

```
What is a Golden Image?
  A custom AMI you create from a running instance that has:
  - All required software pre-installed (nginx, Java runtime, monitoring agent)
  - All required configurations applied
  - Security hardening done (CIS benchmarks)
  - CloudWatch agent installed and configured
  - Company SSL certificates installed

Why use Golden Images?
  Instead of:
    Launch new instance → SSH in → apt install nginx → configure → restart → test
    (20 minutes, error-prone, different every time)
  
  You do:
    Launch new instance from Golden Image → everything already configured → running in 2 minutes
    (Consistent, fast, auditable)

How to create a Golden Image:
  1. Launch base EC2 instance (from AWS-provided AMI)
  2. Install and configure everything you need
  3. Harden the OS (disable unneeded services, update all packages)
  4. Create AMI from the running instance
  5. Tag it: Name=my-app-golden-image, Version=1.2, Date=2025-01-15
  6. Use this AMI for all future launches
  7. Update quarterly or when new patches are needed
```

```bash
# Create an AMI from a running instance
aws ec2 create-image \
  --instance-id i-0123456789abcdef0 \
  --name "my-app-golden-image-$(date +%Y%m%d)" \
  --description "Golden image with nginx 1.24, OpenJDK 21, CW Agent" \
  --no-reboot \
  --tag-specifications 'ResourceType=image,Tags=[
    {Key=Name,Value=my-app-golden-image},
    {Key=Version,Value=1.3},
    {Key=Environment,Value=golden},
    {Key=CreatedBy,Value=sysops-team}
  ]'

# Check AMI creation status (it takes a few minutes)
aws ec2 describe-images \
  --owners self \
  --filters "Name=name,Values=my-app-golden-image-*" \
  --query 'Images[*].[ImageId,Name,State,CreationDate]' \
  --output table
```

---

## 3.4 Launching EC2 Instances — The Complete Guide

### All the Options When Launching

When you launch an EC2 instance, you configure:
1. **AMI** — what OS and software
2. **Instance Type** — how much CPU, RAM, network
3. **Network** — which VPC, which subnet, public IP yes/no
4. **IAM Role** — what AWS permissions does this instance have
5. **Storage** — what disk drives to attach
6. **Security Group** — what network traffic is allowed in/out
7. **Key Pair** — SSH keys for remote access (Linux) or password decrypt (Windows)
8. **User Data** — script to run on first boot

### User Data — Run a Script on First Boot

**User Data** is a script that runs ONE TIME when the instance first launches. It is how you automate the initial configuration.

```bash
#!/bin/bash
# This User Data script runs ONCE on first boot, as root

# Update all packages
yum update -y

# Install nginx web server
amazon-linux-extras install nginx1 -y

# Create a simple web page
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head><title>My Web Server</title></head>
<body>
  <h1>Hello from EC2!</h1>
  <p>Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>
  <p>Region: $(curl -s http://169.254.169.254/latest/meta-data/placement/region)</p>
  <p>AZ: $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</p>
</body>
</html>
EOF

# Start nginx and enable it to start on reboot
systemctl start nginx
systemctl enable nginx

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

echo "User Data script completed successfully" >> /var/log/user-data.log
```

```bash
# Launch an EC2 instance with user data
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name my-key-pair \
  --security-group-ids sg-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --iam-instance-profile Name=EC2-ReadS3-Profile \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[
    {Key=Name,Value=web-server-01},
    {Key=Environment,Value=production},
    {Key=Project,Value=my-app}
  ]'
```

### EC2 Metadata Service — What Instances Know About Themselves

Every EC2 instance can access information about itself via a special IP address: **169.254.169.254**

This is called the **Instance Metadata Service (IMDS)**.

```bash
# From inside an EC2 instance, you can query your own information:
curl http://169.254.169.254/latest/meta-data/instance-id     # i-0abc123def456789
curl http://169.254.169.254/latest/meta-data/instance-type   # t3.micro
curl http://169.254.169.254/latest/meta-data/local-ipv4      # 10.0.1.45
curl http://169.254.169.254/latest/meta-data/public-ipv4     # 54.123.45.67
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/MyRoleName
# ↑ Gets the temporary credentials for the attached IAM role!

curl http://169.254.169.254/latest/meta-data/placement/availability-zone  # us-east-1a
curl http://169.254.169.254/latest/meta-data/placement/region             # us-east-1
```

### IMDSv2 — The Secure Version (Required for Exam)

The original IMDS (v1) was vulnerable to SSRF (Server-Side Request Forgery) attacks. An attacker could trick your application into fetching the instance credentials.

**IMDSv2** (version 2) requires a token-based workflow — harder to exploit via SSRF:

```bash
# IMDSv2 workflow (more secure — must use PUT to get token first)
# Step 1: Get a token (valid for up to 6 hours)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 3600")

# Step 2: Use the token in all subsequent metadata requests
curl -s http://169.254.169.254/latest/meta-data/instance-id \
  -H "X-aws-ec2-metadata-token: $TOKEN"

# Force IMDSv2 only on an instance (disable v1):
aws ec2 modify-instance-metadata-options \
  --instance-id i-0123456789abcdef0 \
  --http-tokens required \
  --http-endpoint enabled

# Force IMDSv2 when launching new instances:
aws ec2 run-instances \
  --image-id ami-xxx \
  --instance-type t3.micro \
  --metadata-options HttpTokens=required,HttpEndpoint=enabled
```

**SysOps exam tip:** Always require IMDSv2. An exam question about preventing SSRF attacks against the metadata service → answer is IMDSv2.

---

## 3.5 EBS — Elastic Block Store (EC2 Storage)

### What is EBS?

**EBS (Elastic Block Store)** is the virtual hard drive for your EC2 instances. It is:
- **Persistent** — data survives instance stop/start (unlike instance store)
- **Network-attached** — connected to your instance via the AWS network (not physically inside)
- **Flexible** — you can detach from one instance and attach to another
- **Independent** — EBS volumes outlive EC2 instances

**Analogy:** EBS is like an external USB drive, but connected via a very fast private network.

### EBS Volume Types — Choosing the Right Drive

```
gp3 — General Purpose SSD (the new default, best value)
  Performance: 3,000 IOPS baseline (can increase to 16,000 IOPS independently)
              125 MB/s baseline (can increase to 1,000 MB/s)
  Use for: Most workloads — root volumes, development, general databases
  Cost: $0.08/GB/month (cheaper than gp2!)
  Key fact: Performance is INDEPENDENT of size (unlike gp2)

gp2 — General Purpose SSD (older, still common)
  Performance: 3 IOPS per GB (100 GB = 300 IOPS minimum, max 16,000 IOPS)
  Use for: Same as gp3, but performance is tied to size
  Cost: $0.10/GB/month
  Exam tip: Migrate gp2 → gp3 for better performance at lower cost

io2/io2 Block Express — Provisioned IOPS SSD (highest performance)
  Performance: Up to 256,000 IOPS, up to 4,000 MB/s throughput
              Consistent sub-millisecond latency
  Use for: I/O-intensive databases (Oracle, SQL Server, high-performance MySQL)
  Cost: Much more expensive — $0.125/GB + $0.065/provisioned IOPS
  Key fact: 99.999% durability (better than 99.8% for other volume types)

st1 — Throughput Optimized HDD
  Performance: 500 IOPS, 500 MB/s throughput
  Use for: Big data, data warehouses, log processing — SEQUENTIAL access
  Cannot be used as root (boot) volume
  Cost: $0.045/GB/month (cheap for large volumes)

sc1 — Cold HDD (cheapest)
  Performance: 250 IOPS, 250 MB/s
  Use for: Infrequently accessed data, archives
  Cannot be used as root (boot) volume
  Cost: $0.015/GB/month (cheapest EBS option)
```

### EBS Snapshots — Backups

**Snapshots** are point-in-time backups of your EBS volumes, stored in S3.

Key facts:
- First snapshot = full copy of volume
- Subsequent snapshots = only changed blocks (incremental) — faster and cheaper
- Snapshots can be used to create new volumes (in any AZ, any size)
- Snapshots can be copied to another region for disaster recovery

```bash
# Create a snapshot
aws ec2 create-snapshot \
  --volume-id vol-0123456789abcdef0 \
  --description "Production DB backup $(date +%Y%m%d)" \
  --tag-specifications 'ResourceType=snapshot,Tags=[
    {Key=Name,Value=prod-db-backup},
    {Key=Date,Value='$(date +%Y-%m-%d)'}
  ]'

# Create a volume from a snapshot (in a different AZ)
aws ec2 create-volume \
  --availability-zone us-east-1b \
  --snapshot-id snap-0123456789abcdef0 \
  --volume-type gp3 \
  --size 100

# Copy snapshot to another region (for DR)
aws ec2 copy-snapshot \
  --source-region us-east-1 \
  --source-snapshot-id snap-0123456789abcdef0 \
  --destination-region us-west-2 \
  --description "DR copy"
```

### Data Lifecycle Manager (DLM) — Automated Snapshot Policies

Instead of manually creating snapshots, use DLM to automate:

```json
{
  "ExecutionRoleArn": "arn:aws:iam::123456789012:role/AWSDataLifecycleManagerDefaultRole",
  "Description": "Daily snapshots, keep 7 days",
  "State": "ENABLED",
  "Details": {
    "ResourceTypes": ["VOLUME"],
    "TargetTags": [{"Key": "Backup", "Value": "true"}],
    "Schedules": [{
      "Name": "Daily Backup",
      "CreateRule": {
        "Interval": 24,
        "IntervalUnit": "HOURS",
        "Times": ["03:00"]
      },
      "RetainRule": {"Count": 7},
      "CopyTags": true,
      "TagsToAdd": [
        {"Key": "SnapshotType", "Value": "DLM-Daily"}
      ]
    }]
  }
}
```

```bash
aws dlm create-lifecycle-policy \
  --execution-role-arn arn:aws:iam::123456789012:role/AWSDataLifecycleManagerDefaultRole \
  --description "Daily EBS backups" \
  --state ENABLED \
  --policy-details file://dlm-policy.json
```

---

## 3.6 EC2 Placement Groups — Controlling Where Instances Go

### What Problem Do Placement Groups Solve?

By default, AWS places instances wherever it wants to balance load across its infrastructure. But sometimes you want MORE control:
- "I want these 10 ML training instances as close together as possible — low latency between them is critical"
- "I want these 10 database replicas spread as far apart as possible — never put two in the same hardware"
- "I want these instances spread across racks but in the same AZ"

### The 3 Types

**1. Cluster Placement Group — Ultra Low Latency (Put Close Together)**

```
+------------------------------------------------+
|  Single AZ, Same Physical Rack Cluster         |
|  [Instance 1][Instance 2][Instance 3][Instance 4]|
|  Network: 10 Gbps to 100 Gbps between instances |
|  Latency: microseconds                          |
+------------------------------------------------+
```

- All instances in ONE AZ, on hardware near each other
- Network: 10 Gbps to 100 Gbps between instances
- Latency: sub-millisecond between instances
- Use for: HPC (High Performance Computing), ML distributed training, video processing
- Risk: If that hardware fails, ALL instances affected together

**2. Spread Placement Group — Maximum Isolation**

```
AZ-1:          AZ-2:          AZ-3:
[Instance 1]   [Instance 2]   [Instance 3]
(Rack A)       (Rack B)       (Rack C)

Each instance is on different hardware
```

- Each instance on a different physical rack/host
- Maximum 7 instances per AZ
- Use for: Critical application components where you cannot afford simultaneous failure
- Best for: Small numbers of critical instances (databases, payment services)

**3. Partition Placement Group — Balance of Performance and Isolation**

```
AZ-1:
  Partition 1: [Instance 1][Instance 2][Instance 3]
  Partition 2: [Instance 4][Instance 5][Instance 6]
  Partition 3: [Instance 7][Instance 8][Instance 9]

Instances within a partition may share hardware.
Instances across partitions are on isolated hardware.
```

- Divide instances into partitions (groups); each partition on different racks
- Up to 7 partitions per AZ
- Hundreds of instances total
- Use for: Distributed big data systems (Hadoop, Cassandra, Kafka)
- You can get the partition number via Instance Metadata (for rack-aware data placement)

---

## 3.7 Auto Scaling Groups (ASG) — Automatic Scaling

### What is Auto Scaling and Why It Matters

**Auto Scaling** automatically adjusts the number of EC2 instances based on demand.

**Without Auto Scaling:**
- Monday 9am: 1,000 users → your 3 servers handle it fine
- Monday 12pm: 10,000 users (lunch rush) → servers overloaded → website slow/down
- Monday 3am: 50 users → 3 servers sitting idle → wasting money all night

**With Auto Scaling:**
- 9am: 3 instances running (normal load)
- 12pm: Load spike → ASG automatically launches 8 more instances → handles 10,000 users fine
- 3am: Load drops → ASG terminates 8 instances → back to 3 → save money

```
Auto Scaling Group:
  Min Size: 2    ← Never go below 2 (minimum for availability)
  Desired:  4    ← Default target
  Max Size: 20   ← Never exceed 20
  
  Normal: [EC2-1][EC2-2][EC2-3][EC2-4]
  
  High load: 
  [EC2-1][EC2-2][EC2-3][EC2-4][EC2-5][EC2-6][EC2-7][EC2-8]
  
  Low load at 3am:
  [EC2-1][EC2-2]  ← cannot go below Min (2)
```

### ASG Configuration

```bash
# Step 1: Create a Launch Template (defines WHAT to launch)
aws ec2 create-launch-template \
  --launch-template-name web-server-template \
  --version-description "v1.0 — nginx web server" \
  --launch-template-data '{
    "ImageId": "ami-0c02fb55956c7d316",
    "InstanceType": "t3.medium",
    "KeyName": "my-key-pair",
    "SecurityGroupIds": ["sg-0123456789abcdef0"],
    "IamInstanceProfile": {"Name": "EC2-WebServer-Profile"},
    "UserData": "IyEvYmluL2Jhc2gKeXVtIHVwZGF0ZSAteQo=",
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [
        {"Key": "Name", "Value": "web-server-asg"},
        {"Key": "Environment", "Value": "production"}
      ]
    }],
    "MetadataOptions": {
      "HttpTokens": "required",
      "HttpEndpoint": "enabled"
    }
  }'

# Step 2: Create the ASG (defines WHERE and HOW MANY to launch)
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name web-app-asg \
  --launch-template LaunchTemplateId=lt-0123456789abcdef0,Version='$Latest' \
  --min-size 2 \
  --max-size 20 \
  --desired-capacity 4 \
  --vpc-zone-identifier "subnet-111111111,subnet-222222222,subnet-333333333" \
  --target-group-arns "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/web-tg/abcdef123456" \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --tags 'ResourceId=web-app-asg,ResourceType=auto-scaling-group,Key=Environment,Value=production,PropagateAtLaunch=true'
```

### Scaling Policies — How ASG Decides When to Scale

**Policy 1: Target Tracking (Recommended — simplest)**

Tell ASG: "Keep average CPU at 60%". ASG figures out how many instances to add/remove.

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-app-asg \
  --policy-name cpu-target-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# Other pre-defined metrics you can target:
# ALBRequestCountPerTarget — keep requests per instance at X
# ASGAverageNetworkIn — keep network bytes in at X
# ASGAverageNetworkOut — keep network bytes out at X
```

**Policy 2: Step Scaling (Granular control)**

Define what to do at different CPU levels:
```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-app-asg \
  --policy-name step-scale-out \
  --policy-type StepScaling \
  --adjustment-type PercentChangeInCapacity \
  --step-adjustments '[
    {
      "MetricIntervalLowerBound": 0,
      "MetricIntervalUpperBound": 10,
      "ScalingAdjustment": 25
    },
    {
      "MetricIntervalLowerBound": 10,
      "MetricIntervalUpperBound": 30,
      "ScalingAdjustment": 50
    },
    {
      "MetricIntervalLowerBound": 30,
      "ScalingAdjustment": 100
    }
  ]'
# CPU 60-70% = add 25% more instances
# CPU 70-90% = add 50% more instances
# CPU 90%+ = double the instances (100% increase)
```

**Policy 3: Scheduled Scaling (For predictable patterns)**

Your website always gets busy 9am-6pm weekdays:
```bash
# Scale out Monday-Friday at 8:55am (before rush starts)
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name web-app-asg \
  --scheduled-action-name weekday-scale-out \
  --recurrence "55 8 * * MON-FRI" \
  --min-size 6 \
  --desired-capacity 10 \
  --max-size 20

# Scale in at 7pm weekdays
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name web-app-asg \
  --scheduled-action-name weekday-scale-in \
  --recurrence "0 19 * * MON-FRI" \
  --min-size 2 \
  --desired-capacity 4 \
  --max-size 20
```

### ASG Lifecycle Hooks — Custom Actions During Launch and Termination

Lifecycle hooks let you run custom code BEFORE an instance fully enters service or before it terminates.

```
Normal launch:          Pending → InService
With lifecycle hook:    Pending → Pending:Wait → [your code runs] → Pending:Proceed → InService

Normal terminate:       Terminating → Terminated
With lifecycle hook:    Terminating → Terminating:Wait → [your code runs] → Terminating:Proceed → Terminated
```

**Use case for Launch hook:**
- Instance launches → run configuration management (Ansible/Chef)
- Run tests to verify the instance is ready
- Register with service discovery
- Download configuration from S3

**Use case for Termination hook:**
- Drain connections gracefully
- Archive logs before the instance disappears
- Deregister from service discovery
- Upload final metrics

```bash
# Add a lifecycle hook for launch
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name web-app-asg \
  --lifecycle-hook-name configure-on-launch \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --default-result ABANDON \
  --heartbeat-timeout 300 \
  --notification-target-arn arn:aws:sns:us-east-1:123456789012:asg-lifecycle-topic

# Complete the hook from your Lambda (after configuration is done)
aws autoscaling complete-lifecycle-action \
  --lifecycle-action-result CONTINUE \
  --auto-scaling-group-name web-app-asg \
  --lifecycle-hook-name configure-on-launch \
  --instance-id i-0123456789abcdef0
```

### ASG Health Checks — How ASG Detects Unhealthy Instances

ASG can use two types of health checks:

**EC2 Health Check (default):**
- Checks hardware and hypervisor health
- Marks instance unhealthy if: underlying hardware fails, instance is stopped, system check fails
- Does NOT check if your application is actually running correctly

**ELB Health Check (recommended for web applications):**
- The load balancer checks your application's HTTP endpoint every 30 seconds
- If `/health` returns non-200 response for X consecutive checks → marked unhealthy
- ASG terminates and replaces the unhealthy instance
- This catches application-level failures, not just hardware failures

```bash
# Configure ELB health checks for your target group
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/web-tg/... \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --health-check-timeout-seconds 10

# Make sure your ASG uses ELB health checks
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name web-app-asg \
  --health-check-type ELB \
  --health-check-grace-period 300
  # Grace period: don't check health for first 300 seconds after launch
  # (gives app time to start up and become ready)
```

---

## 3.8 Elastic Load Balancing (ELB) — Distributing Traffic

### What is a Load Balancer?

A load balancer sits in front of your servers and distributes incoming traffic across them. Like a traffic cop at an intersection directing cars to different roads.

**Without a load balancer:**
```
User 1 → Your Server 1 (might be overloaded)
User 2 → Your Server 1 (same overloaded server!)
User 3 → Your Server 1 (users 2 and 3 never reach Server 2 and 3)
```

**With a load balancer:**
```
User 1 → Load Balancer → Server 1
User 2 → Load Balancer → Server 2
User 3 → Load Balancer → Server 3
User 4 → Load Balancer → Server 1
```

Benefits:
- **Even distribution** of traffic across all servers
- **Health checks** — stops sending traffic to failed servers
- **SSL termination** — handles HTTPS encryption/decryption (saves CPU on servers)
- **Sticky sessions** — routes same user to same server (when app requires it)
- **Single DNS name** — your users use one address, you can add/remove servers behind it

### The Three Types of AWS Load Balancers

**1. Application Load Balancer (ALB) — Layer 7 HTTP/HTTPS**

```
What it does: Understands HTTP/HTTPS — can route based on:
  - URL path (/api/* → API servers, /images/* → image servers)
  - Hostname (api.example.com → API servers, www.example.com → web servers)
  - HTTP headers (Mobile-User-Agent → mobile servers)
  - Query strings (?version=2 → v2 servers)

Use for: Web applications, microservices, REST APIs, WebSocket
Protocol: HTTP, HTTPS, gRPC
```

**2. Network Load Balancer (NLB) — Layer 4 TCP/UDP**

```
What it does: Ultra-high-performance TCP/UDP routing
  - Handles millions of requests per second
  - Sub-millisecond latency
  - Preserves client IP address
  - Static IP addresses per AZ (important for firewall rules!)
  - Can handle non-HTTP protocols

Use for: Gaming servers, IoT, financial trading, anything needing extreme performance
Protocol: TCP, UDP, TLS, TCP_UDP
```

**3. Gateway Load Balancer (GWLB) — Layer 3 for Security Appliances**

```
What it does: Route traffic through third-party network appliances
  (firewalls, IDS/IPS, deep packet inspection)
  
Use for: Network security architectures with virtual firewalls
Protocol: IP protocol (Layer 3)
```

### Setting Up an Application Load Balancer

```bash
# Step 1: Create the ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name web-app-alb \
  --subnets subnet-public-1 subnet-public-2 subnet-public-3 \
  --security-groups sg-alb-security-group \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Step 2: Create a target group (where traffic will go)
TG_ARN=$(aws elbv2 create-target-group \
  --name web-app-targets \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-0123456789abcdef0 \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Step 3: Create HTTPS listener (with redirect from HTTP)
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# Step 4: Create HTTP redirect to HTTPS
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
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

# Step 5: Add routing rules (path-based)
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --query 'Listeners[?Port==`443`].ListenerArn' --output text)

# Route /api/* to API target group
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions Type=forward,TargetGroupArn=$API_TG_ARN
```

---

## 3.9 EC2 Purchasing Options — Optimizing Costs

```
ON-DEMAND:
  Pay: $0.192/hour for m5.xlarge
  Use when: Unpredictable needs, short-term, testing
  Flexibility: Stop/start anytime, no commitment
  
RESERVED INSTANCES:
  Pay: $0.076/hour (1-yr All Upfront) = 60% savings!
  Use when: Always-on servers (web servers, databases)
  Commitment: 1 or 3 years
  
SAVINGS PLANS (Compute):
  Commit: $X/hour on any compute
  Savings: Up to 66%
  Flexibility: Can change instance type/family/region
  
SPOT INSTANCES:
  Pay: $0.02-0.05/hour = up to 90% savings!
  Catch: Can be interrupted with 2-min notice
  Use when: Batch jobs, ML training, data processing
  
DEDICATED HOSTS:
  Pay: Hourly for the entire physical server
  Use when: Per-socket/per-core software licensing (Oracle, SQL Server)
  Compliance: Some regulations require dedicated hardware
  
DEDICATED INSTANCES:
  Pay: Per-instance premium (~10%)
  Use when: Compliance requiring no shared hardware (but you don't need full server)
```

---

## 3.10 Real-World Project: Auto-Healing, Auto-Scaling Web Application

### Architecture

```
Internet → Route 53 → ALB (Multi-AZ) → Auto Scaling Group
                                              │
                       ┌──────────────────────┼──────────────────────┐
                       │                      │                      │
                    AZ-1a                   AZ-1b                  AZ-1c
               Web Server (t3.medium)   Web Server (t3.medium)  Web Server
                       │                      │                      │
                       └──────────────────────┼──────────────────────┘
                                              │
                                      Aurora MySQL (Multi-AZ)
                                      ElastiCache Redis (Multi-AZ)
```

### CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Auto-healing, auto-scaling web application

Parameters:
  EnvironmentName:
    Type: String
    Default: production
  InstanceType:
    Type: String
    Default: t3.medium
    AllowedValues: [t3.small, t3.medium, t3.large, m6i.large, m6i.xlarge]
  MinInstances:
    Type: Number
    Default: 2
  MaxInstances:
    Type: Number
    Default: 20
  DesiredInstances:
    Type: Number
    Default: 4

Resources:
  # ── IAM Role for EC2 instances ──────────────────────────────────
  EC2InstanceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${EnvironmentName}-ec2-role'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
      Policies:
        - PolicyName: AppS3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: ['s3:GetObject', 's3:PutObject', 's3:ListBucket']
                Resource: ['arn:aws:s3:::app-assets-bucket/*', 'arn:aws:s3:::app-assets-bucket']

  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles: [!Ref EC2InstanceRole]

  # ── Security Groups ──────────────────────────────────────────────
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Allow HTTP/HTTPS from internet
      VpcId: !ImportValue VPC-Id
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

  WebServerSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Allow traffic from ALB only
      VpcId: !ImportValue VPC-Id
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          SourceSecurityGroupId: !Ref ALBSecurityGroup

  # ── Application Load Balancer ────────────────────────────────────
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub '${EnvironmentName}-alb'
      Type: application
      Scheme: internet-facing
      Subnets:
        - !ImportValue PublicSubnet1
        - !ImportValue PublicSubnet2
        - !ImportValue PublicSubnet3
      SecurityGroups: [!Ref ALBSecurityGroup]
      LoadBalancerAttributes:
        - Key: deletion_protection.enabled
          Value: 'true'
        - Key: access_logs.s3.enabled
          Value: 'true'
        - Key: access_logs.s3.bucket
          Value: !Sub 'access-logs-${AWS::AccountId}'

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub '${EnvironmentName}-tg'
      Protocol: HTTP
      Port: 80
      VpcId: !ImportValue VPC-Id
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      TargetGroupAttributes:
        - Key: deregistration_delay.timeout_seconds
          Value: '30'  # Only 30 sec drain instead of default 300

  HTTPSListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ApplicationLoadBalancer
      Port: 443
      Protocol: HTTPS
      Certificates:
        - CertificateArn: !Sub 'arn:aws:acm:${AWS::Region}:${AWS::AccountId}:certificate/YOUR-CERT-ID'
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup

  # ── Launch Template ──────────────────────────────────────────────
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub '${EnvironmentName}-lt'
      LaunchTemplateData:
        ImageId: !Sub '{{resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64}}'
        InstanceType: !Ref InstanceType
        IamInstanceProfile:
          Arn: !GetAtt EC2InstanceProfile.Arn
        SecurityGroupIds: [!Ref WebServerSecurityGroup]
        MetadataOptions:
          HttpTokens: required        # Force IMDSv2
          HttpEndpoint: enabled
          InstanceMetadataTags: enabled
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            set -e
            yum update -y
            yum install -y amazon-cloudwatch-agent
            amazon-linux-extras install nginx1 -y
            
            # Get app config from Parameter Store
            aws ssm get-parameter --name /app/config --with-decryption \
              --query 'Parameter.Value' --output text > /app/config.json
            
            # Start services
            systemctl start nginx
            systemctl enable nginx
            systemctl start amazon-cloudwatch-agent
            
            # Signal CloudFormation that setup is complete
            /opt/aws/bin/cfn-signal -e 0 --stack ${AWS::StackName} \
              --resource AutoScalingGroup --region ${AWS::Region}

  # ── Auto Scaling Group ───────────────────────────────────────────
  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    CreationPolicy:
      ResourceSignal:
        Count: !Ref MinInstances
        Timeout: PT10M  # Wait up to 10 min for instances to signal ready
    UpdatePolicy:
      AutoScalingRollingUpdate:
        MinInstancesInService: 1
        MaxBatchSize: 2
        PauseTime: PT5M
        WaitOnResourceSignals: true
    Properties:
      AutoScalingGroupName: !Sub '${EnvironmentName}-asg'
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      MinSize: !Ref MinInstances
      MaxSize: !Ref MaxInstances
      DesiredCapacity: !Ref DesiredInstances
      VPCZoneIdentifier:
        - !ImportValue PrivateSubnet1
        - !ImportValue PrivateSubnet2
        - !ImportValue PrivateSubnet3
      TargetGroupARNs: [!Ref TargetGroup]
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      MetricsCollection:
        - Granularity: '1Minute'
      Tags:
        - Key: Name
          Value: !Sub '${EnvironmentName}-web-server'
          PropagateAtLaunch: true
        - Key: Environment
          Value: !Ref EnvironmentName
          PropagateAtLaunch: true

  # ── Scaling Policies ─────────────────────────────────────────────
  ScaleOnCPU:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref AutoScalingGroup
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ASGAverageCPUUtilization
        TargetValue: 60.0

  ScaleOnRequests:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref AutoScalingGroup
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ALBRequestCountPerTarget
          ResourceLabel: !Sub 
            - '${AlbFullName}/${TgFullName}'
            - AlbFullName: !GetAtt ApplicationLoadBalancer.LoadBalancerFullName
              TgFullName: !GetAtt TargetGroup.TargetGroupFullName
        TargetValue: 1000  # 1000 requests per instance before scaling out

Outputs:
  LoadBalancerURL:
    Value: !Sub 'https://${ApplicationLoadBalancer.DNSName}'
    Export:
      Name: !Sub '${EnvironmentName}-LoadBalancerURL'
  AutoScalingGroupName:
    Value: !Ref AutoScalingGroup
```

---

## 3.11 Practice Questions

**Q1:** Your EC2 instances are running a financial trading application that requires extremely low latency communication between instances. They are also network-intensive. Which placement group type and instance configuration should you use?

- A) Spread placement group with any instance type
- B) Cluster placement group with Enhanced Networking enabled instances
- C) Partition placement group with t3 instances
- D) No placement group needed — use multiple AZs

**Answer: B**

Explanation: Cluster placement groups put instances on the same physical hardware in the same AZ, enabling 10-100 Gbps network throughput between instances with microsecond latency. Enhanced Networking (using ENA or SR-IOV) provides low-latency, high-throughput networking. For latency-sensitive applications like financial trading, this combination is optimal. Spread placement (A) maximizes fault isolation but increases network latency. Multiple AZs (D) adds latency.

---

**Q2:** Your web application's ASG currently has 4 instances. A deployment goes wrong and all 4 instances are failing health checks. The ASG's minimum is 2, desired is 4, max is 10. What does the ASG do?

- A) Nothing — ASG only scales out, not replace unhealthy instances
- B) Terminates all 4 and launches 4 new ones from the Launch Template
- C) Terminates unhealthy instances one by one and replaces them, maintaining at least 1 running
- D) Terminates all 4 instances and reduces desired to 0

**Answer: B**

Explanation: ASG continuously monitors instance health. When it detects unhealthy instances, it terminates them and launches new ones to maintain the desired capacity. With all 4 failing, ASG will terminate all 4 and launch 4 new ones from the Launch Template. The minimum of 2 prevents going below 2 instances, but since desired is 4 and instances are actively failing (not slowly scaling in), ASG will attempt to replace all. This is the "auto-healing" behavior of ASG.

---

**Q3:** Your company needs to run Oracle Database on EC2 with a per-socket license. The license requires you to count each physical CPU socket. Which EC2 purchasing option gives you visibility and control over physical socket placement?

- A) On-Demand instances in a placement group
- B) Dedicated Hosts
- C) Reserved Instances
- D) Spot Instances

**Answer: B**

Explanation: Dedicated Hosts provide a physical server entirely dedicated to your use. You have visibility into the physical server's socket and core configuration, which is required for per-socket software licensing (Oracle, SQL Server, etc.). On-Demand and Reserved Instances may share physical hardware with other customers. Spot Instances are not appropriate for databases due to interruption risk.

---

**Q4:** A developer reports that their application running on EC2 cannot read its IAM role credentials. The application is getting 401 errors when calling AWS APIs. What should you check first?

- A) Verify the EC2 instance has internet access to reach AWS APIs
- B) Verify an IAM instance profile is attached to the EC2 instance
- C) Verify the IAM user's access keys are configured in ~/.aws/credentials
- D) Verify CloudTrail is enabled

**Answer: B**

Explanation: EC2 instances get IAM credentials through an attached Instance Profile. If no instance profile is attached, there are no credentials available and all AWS API calls will fail with 401/403. The instance metadata service at 169.254.169.254 provides these credentials when an instance profile is attached. Note: configuring access keys in ~/.aws/credentials (C) is the old/wrong way — you should use IAM roles/instance profiles instead.

---

**Q5:** You have an ASG with target tracking set to maintain 60% average CPU. Currently 4 instances are running at 40% CPU each. You notice the ASG is not scaling in (reducing instances) even though CPU is below 60%. What is the MOST likely reason?

- A) Target tracking only scales out, not in
- B) The instances are within the scale-in cooldown period, or the minimum instance count is already reached
- C) CloudWatch metrics are delayed by 5 minutes
- D) The ASG needs manual intervention to scale in

**Answer: B**

Explanation: Target tracking scaling DOES support scale-in, but there are two reasons it might not happen: (1) The ASG has a scale-in cooldown period (default 300 seconds) — if instances were recently launched or an action was recently taken, scale-in waits. (2) The ASG's minimum instance count acts as a floor — if you are already at minimum (say, 2), it cannot scale in further. Target tracking scaling also typically waits for 3 evaluation periods before scaling in (more conservative than scale-out) to avoid rapid fluctuations.

---

## Chapter 3 Summary

| Concept | Key Facts |
|---------|----------|
| EC2 | Virtual computers rented by the second; instance type determines CPU/RAM/network |
| Instance Families | M/T=General, C=Compute, R=Memory, I=Storage, P/G=GPU |
| AMI | Template for launching instances; create Golden AMIs for consistent deployments |
| User Data | Script runs ONCE on first boot; use for software installation and configuration |
| IMDSv2 | Secure metadata access requiring token; always enable; prevents SSRF attacks |
| EBS Types | gp3=default SSD, io2=high IOPS, st1=throughput HDD, sc1=cold HDD |
| EBS Snapshots | Point-in-time backups stored in S3; incremental after first snapshot |
| Placement Groups | Cluster=low latency same rack; Spread=max isolation different racks; Partition=big distributed |
| ASG | Automatically scale EC2 instances; min/desired/max; ELB health checks recommended |
| Scaling Policies | Target Tracking=simplest; Step=granular; Scheduled=predictable patterns |
| Lifecycle Hooks | Run custom code during launch or termination; default timeout 1 hour |
| ALB | Layer 7 HTTP/HTTPS; path/host-based routing; use for web apps and APIs |
| NLB | Layer 4 TCP/UDP; extreme performance; static IPs; use for non-HTTP or high-performance |
| Purchasing | On-Demand=flexible; RI=commit 1-3yr save 72%; Spot=90% off interruptible; Dedicated=licensing |
"""

with open(r"e:\fastapi\aws-admin\03_EC2_Compute_AutoScaling.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
