# Chapter 3: Compute — EC2, Auto Scaling & Load Balancing
## Virtual Machines, Instance Types, Storage, Networking & High Availability

---

## 3.1 EC2 Overview

Amazon Elastic Compute Cloud (EC2) provides resizable virtual machines (instances) in the cloud. You have full OS-level control, choose the hardware profile, and pay by the second.

```
EC2 Instance = virtual machine running on AWS hardware

┌─────────────────────────────────────────────────────────────────┐
│                    Physical AWS Host                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Instance A │  │  Instance B │  │  Instance C │            │
│  │  (your VM)  │  │  (someone   │  │  (dedicated  │            │
│  │             │  │   else's)   │  │   host)     │            │
│  │  OS: Linux  │  │  OS: Win    │  │  OS: any    │            │
│  │  vCPU: 2    │  │  vCPU: 4   │  │  vCPU: 16   │            │
│  │  RAM: 8GB   │  │  RAM: 16GB  │  │  RAM: 64GB  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│            Xen / Nitro Hypervisor                               │
│                                                                 │
│  CPU: Intel Xeon / AMD EPYC / AWS Graviton                     │
│  Network: 100Gbps Enhanced Networking (ENA)                    │
└─────────────────────────────────────────────────────────────────┘
```

### AWS Nitro System

Modern EC2 instances run on the **AWS Nitro System** — a combination of dedicated hardware and lightweight hypervisor that offloads virtualization functions to hardware:
- Near bare-metal performance
- Better security (hardware-enforced isolation)
- Higher network and storage performance
- Enables bare-metal instances (no hypervisor overhead)

---

## 3.2 EC2 Instance Types

Instance types follow the pattern: **family** + **generation** + **size** (e.g., `m7g.xlarge`)

```
Naming Convention:
  m   7   g  .  x  large
  │   │   │     │
  │   │   │     └─ Size: nano/micro/small/medium/large/xlarge/2xlarge...
  │   │   └─────── Attribute: g=Graviton, a=AMD, n=networking, d=NVMe, z=high freq
  │   └─────────── Generation: higher = newer/better price-performance
  └─────────────── Family: general purpose, compute, memory, storage...
```

### Instance Families

```
GENERAL PURPOSE (balanced CPU/RAM/network):
  t3, t4g     — Burstable (for variable workloads, web servers, dev)
                t3.micro FREE TIER (2 vCPU, 1GB RAM)
  m6i, m7g    — Fixed performance (web servers, app servers)
  m5, m6a     — AMD-based (cost savings ~10%)

COMPUTE OPTIMIZED (high CPU-to-RAM ratio):
  c6i, c7g    — Batch processing, HPC, gaming, ML inference
  c5n         — High networking (100Gbps)

MEMORY OPTIMIZED (high RAM-to-CPU ratio):
  r6i, r7g    — In-memory databases, Redis, SAP HANA
  x1e, x2gd  — Terabytes of RAM for massive in-memory workloads
  z1d         — High clock speed + local NVMe

STORAGE OPTIMIZED (high I/O):
  i3, i4i     — NVMe SSD storage, databases, Elasticsearch
  d2, d3      — Dense HDD storage, Hadoop, data warehousing
  h1          — HDD storage optimized

ACCELERATED COMPUTING (GPUs / FPGAs):
  p3, p4, p5  — ML training (NVIDIA Tesla/A100)
  g4dn, g5    — ML inference, gaming, video transcoding
  inf1, inf2  — AWS Inferentia chips (cheapest inference)
  f1          — FPGA instances (custom hardware)

HPCOPTIMIZED:
  hpc6a       — AMD EPYC, 100Gbps EFA, HPC workloads
```

### Instance Sizes

```
nano < micro < small < medium < large < xlarge < 2xlarge < 4xlarge < 8xlarge < 16xlarge < 32xlarge

Example: m6i family
  m6i.large      2 vCPU,  8 GB RAM
  m6i.xlarge     4 vCPU, 16 GB RAM
  m6i.2xlarge    8 vCPU, 32 GB RAM
  m6i.4xlarge   16 vCPU, 64 GB RAM
  m6i.8xlarge   32 vCPU,128 GB RAM
  m6i.16xlarge  64 vCPU,256 GB RAM
  m6i.32xlarge 128 vCPU,512 GB RAM
  m6i.metal    128 vCPU,512 GB RAM  (bare metal — no hypervisor)
```

### Graviton (ARM) Instances

AWS Graviton3 (g-suffix) instances offer **up to 40% better price-performance** than equivalent x86 instances:

```
t4g  vs  t3   — same price, better performance
m7g  vs  m6i  — ~20% cheaper for same performance
c7g  vs  c6i  — up to 40% better price-performance for compute
```

```bash
# Check if your app supports ARM
# Python, Node.js, Java, Go: fully supported
# Most Docker images now have multi-arch (amd64 + arm64)

# Build multi-arch Docker image
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest --push .
```

---

## 3.3 Launching EC2 Instances

### Quick Launch (CLI)

```bash
# Find latest Amazon Linux 2 AMI
AMI=$(aws ec2 describe-images \
  --owners amazon \
  --filters \
    "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text)

echo "Latest AMI: $AMI"

# Launch instance
aws ec2 run-instances \
  --image-id $AMI \
  --instance-type t3.micro \
  --key-name my-keypair \
  --security-group-ids sg-0abc123 \
  --subnet-id subnet-0abc123 \
  --associate-public-ip-address \
  --iam-instance-profile Name=EC2SSMRole \
  --user-data file://userdata.sh \
  --tag-specifications \
    "ResourceType=instance,Tags=[{Key=Name,Value=web-01},{Key=Environment,Value=dev}]" \
  --count 1

# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=web-01" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)
```

### User Data Script

User data runs as root when the instance first starts:

```bash
#!/bin/bash
# userdata.sh — Amazon Linux 2

set -e

# Update system
yum update -y

# Install packages
yum install -y \
  python3 python3-pip \
  docker \
  git \
  jq \
  htop \
  aws-cli

# Start and enable Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Python app dependencies
pip3 install fastapi uvicorn gunicorn boto3

# Configure CloudWatch agent
yum install -y amazon-cloudwatch-agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWCONFIG'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {"file_path": "/var/log/app/*.log", "log_group_name": "/ec2/web-servers", "log_stream_name": "{instance_id}"}
        ]
      }
    }
  },
  "metrics": {
    "append_dimensions": {"InstanceId": "${aws:InstanceId}"},
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "disk": {"measurement": ["disk_used_percent"], "resources": ["/"]}
    }
  }
}
CWCONFIG
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

# Signal CloudFormation (if launched via CFn)
/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource AutoScalingGroup --region ${AWS::Region} || true

echo "User data script complete"
```

### Key Pairs

```bash
# Create key pair (saves .pem file locally)
aws ec2 create-key-pair \
  --key-name my-keypair \
  --query "KeyMaterial" \
  --output text > my-keypair.pem
chmod 400 my-keypair.pem

# Import existing public key
aws ec2 import-key-pair \
  --key-name my-existing-key \
  --public-key-material fileb://~/.ssh/id_rsa.pub

# List key pairs
aws ec2 describe-key-pairs \
  --query "KeyPairs[*].[KeyName,KeyFingerprint]" \
  --output table

# SSH to instance
ssh -i my-keypair.pem ec2-user@<public-ip>   # Amazon Linux
ssh -i my-keypair.pem ubuntu@<public-ip>     # Ubuntu

# SSM Session Manager (no key pair or open SSH port needed!)
aws ssm start-session --target i-0abc123
```

---

## 3.4 EC2 Storage — EBS, Instance Store, EFS

### EBS (Elastic Block Store)

EBS volumes are persistent block storage attached to EC2 instances. They persist independently of instance lifecycle (survive stop/terminate if configured).

```
EBS Volume Types:
┌─────────────────────────────────────────────────────────────────────┐
│ Type    │ Full Name       │ IOPS (max) │ Throughput │ Use Case       │
├─────────┼─────────────────┼────────────┼────────────┼────────────────┤
│ gp3     │ General SSD     │ 16,000     │ 1,000 MB/s │ Most workloads │
│ gp2     │ General SSD v2  │ 16,000     │ 250 MB/s   │ Old default    │
│ io2     │ Provisioned SSD │ 256,000    │ 4,000 MB/s │ Databases      │
│ io1     │ Provisioned SSD │ 64,000     │ 1,000 MB/s │ Databases      │
│ st1     │ Throughput HDD  │ 500        │ 500 MB/s   │ Hadoop, logs   │
│ sc1     │ Cold HDD        │ 250        │ 250 MB/s   │ Archives       │
│ standard│ Magnetic HDD    │ 40-200     │ N/A        │ Infrequent use │
└─────────┴─────────────────┴────────────┴────────────┴────────────────┘

gp3 vs gp2:
  gp3: Can independently set IOPS (3,000–16,000) and throughput (125–1,000 MB/s)
  gp2: IOPS tied to size (3 IOPS/GB), max 16,000 at 5,333 GB
  gp3 is 20% cheaper than gp2 and always recommended for new deployments
```

```bash
# Create EBS volume
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --volume-type gp3 \
  --size 100 \
  --iops 3000 \
  --throughput 125 \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123:key/... \
  --tag-specifications "ResourceType=volume,Tags=[{Key=Name,Value=app-data}]"

# Attach volume to instance
aws ec2 attach-volume \
  --volume-id vol-0abc123 \
  --instance-id i-0abc123 \
  --device /dev/xvdf

# On Linux — format and mount new volume
sudo mkfs -t xfs /dev/xvdf
sudo mkdir /data
sudo mount /dev/xvdf /data

# Make mount persistent (add to /etc/fstab)
echo "UUID=$(sudo blkid -s UUID -o value /dev/xvdf) /data xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab

# Modify volume (online — no downtime for gp3)
aws ec2 modify-volume \
  --volume-id vol-0abc123 \
  --size 200 \
  --iops 6000

# Create snapshot
aws ec2 create-snapshot \
  --volume-id vol-0abc123 \
  --description "Backup before upgrade" \
  --tag-specifications "ResourceType=snapshot,Tags=[{Key=Name,Value=app-data-backup}]"

# Copy snapshot to another region
aws ec2 copy-snapshot \
  --source-region us-east-1 \
  --source-snapshot-id snap-0abc123 \
  --region us-west-2 \
  --description "Cross-region backup"

# List snapshots
aws ec2 describe-snapshots \
  --owner-ids self \
  --query "Snapshots[*].[SnapshotId,VolumeSize,StartTime,State]" \
  --output table

# Restore volume from snapshot (create in different AZ)
aws ec2 create-volume \
  --snapshot-id snap-0abc123 \
  --availability-zone us-east-1b \
  --volume-type gp3
```

### EBS Encryption

```bash
# Enable default EBS encryption for account/region
aws ec2 enable-ebs-encryption-by-default --region us-east-1

# Check if enabled
aws ec2 get-ebs-encryption-by-default

# Create encrypted volume with specific KMS key
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --volume-type gp3 \
  --size 100 \
  --encrypted \
  --kms-key-id alias/my-key
```

### Instance Store

Temporary storage **physically attached** to the host. Very fast (NVMe SSDs), but:
- Data lost on: stop, terminate, hardware failure
- Not all instance types have it (i3, d2, r5d, m5d families do)

Use for: temporary files, caches, scratch data, replica data

### EFS (Elastic File System)

Fully managed **NFS** file system — mountable on multiple EC2 instances simultaneously.

```bash
# Create EFS file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=shared-files

# Create mount targets (one per AZ)
aws efs create-mount-target \
  --file-system-id fs-0abc123 \
  --subnet-id subnet-0abc123 \
  --security-groups sg-0abc123

# Mount on EC2 (Amazon Linux 2)
sudo yum install -y amazon-efs-utils
sudo mkdir /mnt/efs
sudo mount -t efs fs-0abc123:/ /mnt/efs

# Or via NFS
sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 \
  fs-0abc123.efs.us-east-1.amazonaws.com:/ /mnt/efs

# Make persistent in /etc/fstab
echo "fs-0abc123.efs.us-east-1.amazonaws.com:/ /mnt/efs nfs4 defaults,_netdev 0 0" >> /etc/fstab
```

---

## 3.5 EC2 Networking

### Security Groups

Security groups are **virtual stateful firewalls** for EC2 instances. They control inbound and outbound traffic.

```
Stateful = return traffic automatically allowed
           (opposite of NACLs which are stateless)

Security Group Rules:
  Inbound: control traffic ENTERING the instance
  Outbound: control traffic LEAVING the instance (default: all allowed)
```

```bash
# Create security group
aws ec2 create-security-group \
  --group-name web-server-sg \
  --description "Security group for web servers" \
  --vpc-id vpc-0abc123

SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=web-server-sg" \
  --query "SecurityGroups[0].GroupId" --output text)

# Add inbound rules
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow SSH from specific IP only
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 203.0.113.0/24

# Allow traffic FROM another security group (chaining)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8080 \
  --source-group sg-alb-id  # Allow from ALB security group only

# Remove rule
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0   # Close the world SSH if accidentally opened

# Tag security group
aws ec2 create-tags \
  --resources $SG_ID \
  --tags Key=Name,Value=web-server-sg
```

### Elastic IP Addresses

```bash
# Allocate Elastic IP
EIP=$(aws ec2 allocate-address \
  --domain vpc \
  --query "AllocationId" --output text)

# Associate with instance
aws ec2 associate-address \
  --instance-id i-0abc123 \
  --allocation-id $EIP

# Disassociate
aws ec2 disassociate-address \
  --association-id eipassoc-0abc123

# Release (stops billing)
aws ec2 release-address --allocation-id $EIP

# Note: Unused EIPs cost ~$0.005/hour — always release when done
```

### Enhanced Networking & Placement Groups

```bash
# Placement Groups
# Cluster: instances physically close together (low latency, high bandwidth)
#          Single AZ. For HPC, distributed databases
aws ec2 create-placement-group \
  --group-name my-hpc-cluster \
  --strategy cluster

# Spread: instances on different hardware racks
#         Max 7 instances per AZ. For critical instances needing isolation
aws ec2 create-placement-group \
  --group-name critical-instances \
  --strategy spread

# Partition: groups of instances on separate partitions (racks)
#            For HDFS, Cassandra, Kafka (rack-aware)
aws ec2 create-placement-group \
  --group-name kafka-cluster \
  --strategy partition \
  --partition-count 3

# Launch instances into placement group
aws ec2 run-instances \
  --placement "GroupName=my-hpc-cluster,Tenancy=default" \
  --image-id $AMI \
  --instance-type c5n.18xlarge \
  ...
```

---

## 3.6 AMIs (Amazon Machine Images)

An AMI is a template for launching EC2 instances. It includes:
- Root volume snapshot (OS + installed software)
- Launch permissions
- Block device mapping

```bash
# List available AMIs
# Amazon Linux 2
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].[Name,ImageId,CreationDate]" \
  --output table

# Amazon Linux 2023
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].[Name,ImageId]" \
  --output table

# Ubuntu 22.04
aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --query "sort_by(Images, &CreationDate)[-1].[Name,ImageId]" \
  --output table

# Create custom AMI from running instance
aws ec2 create-image \
  --instance-id i-0abc123 \
  --name "MyApp-v1.0-$(date +%Y%m%d)" \
  --description "Application server with all dependencies installed" \
  --no-reboot   # Don't reboot instance (may have filesystem inconsistencies)

# Wait for AMI to be available
aws ec2 wait image-available --image-ids ami-0abc123

# Copy AMI to another region
aws ec2 copy-image \
  --source-region us-east-1 \
  --source-image-id ami-0abc123 \
  --region us-west-2 \
  --name "MyApp-v1.0-copy"

# Share AMI with another account
aws ec2 modify-image-attribute \
  --image-id ami-0abc123 \
  --launch-permission "Add=[{UserId=987654321098}]"

# Deregister (delete) AMI
aws ec2 deregister-image --image-id ami-0abc123
# Then delete associated snapshots
aws ec2 delete-snapshot --snapshot-id snap-0abc123
```

---

## 3.7 Auto Scaling Groups (ASG)

Auto Scaling Groups automatically adjust the number of EC2 instances based on demand.

```
Auto Scaling Group Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    Auto Scaling Group                           │
│  Min: 2 instances    Max: 10 instances    Desired: 4            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ALB Target Group                      │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                             │                                   │
│  AZ us-east-1a              │     AZ us-east-1b                 │
│  ┌──────────┐  ┌──────────┐ │  ┌──────────┐  ┌──────────┐     │
│  │ EC2 #1   │  │ EC2 #2   │ │  │ EC2 #3   │  │ EC2 #4   │     │
│  └──────────┘  └──────────┘ │  └──────────┘  └──────────┘     │
│                              │                                  │
│  Scale-out trigger: CPU > 70% for 5 minutes → add 2 instances   │
│  Scale-in trigger:  CPU < 30% for 15 minutes → remove 1 instance│
└─────────────────────────────────────────────────────────────────┘
```

### Launch Template

```bash
# Create launch template
aws ec2 create-launch-template \
  --launch-template-name MyAppTemplate \
  --version-description "v1 - base configuration" \
  --launch-template-data '{
    "ImageId": "ami-0abc123",
    "InstanceType": "t3.medium",
    "KeyName": "my-keypair",
    "SecurityGroupIds": ["sg-0abc123"],
    "IamInstanceProfile": {"Name": "EC2AppRole"},
    "UserData": "'$(base64 -w 0 userdata.sh)'",
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 30,
        "VolumeType": "gp3",
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    }],
    "MetadataOptions": {
      "HttpTokens": "required",
      "HttpEndpoint": "enabled"
    },
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [
        {"Key": "Name", "Value": "app-server"},
        {"Key": "Environment", "Value": "prod"}
      ]
    }]
  }'

# Create new version of launch template
aws ec2 create-launch-template-version \
  --launch-template-id lt-0abc123 \
  --version-description "v2 - updated AMI" \
  --source-version 1 \
  --launch-template-data '{"ImageId": "ami-0def456"}'

# Set default version
aws ec2 modify-launch-template \
  --launch-template-id lt-0abc123 \
  --default-version 2
```

### Create Auto Scaling Group

```bash
# Create ASG
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name my-app-asg \
  --launch-template "LaunchTemplateId=lt-0abc123,Version=\$Latest" \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 4 \
  --vpc-zone-identifier "subnet-0abc123,subnet-0def456" \
  --target-group-arns "arn:aws:elasticloadbalancing:us-east-1:123:targetgroup/my-targets/abc123" \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --default-cooldown 300 \
  --tags \
    "Key=Name,Value=app-server,PropagateAtLaunch=true" \
    "Key=Environment,Value=prod,PropagateAtLaunch=true"

# Describe ASG
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names my-app-asg \
  --query "AutoScalingGroups[0].[MinSize,MaxSize,DesiredCapacity,Instances[*].InstanceId]"

# Manually set desired capacity
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name my-app-asg \
  --desired-capacity 6

# Update ASG parameters
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name my-app-asg \
  --min-size 3 \
  --max-size 15

# Instance refresh (rolling update with new launch template version)
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name my-app-asg \
  --preferences '{
    "MinHealthyPercentage": 50,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [25, 50, 100],
    "CheckpointDelay": 60
  }'
```

### Scaling Policies

```bash
# ── TARGET TRACKING (simplest, recommended) ───────────────────
# Maintain average CPU at 50%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-app-asg \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 50.0,
    "DisableScaleIn": false
  }'

# ALB request count per target
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-app-asg \
  --policy-name alb-requests-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/my-alb/abc123/targetgroup/my-targets/def456"
    },
    "TargetValue": 1000.0
  }'

# ── STEP SCALING ──────────────────────────────────────────────
# Create CloudWatch alarm first
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-alarm \
  --alarm-description "High CPU alarm" \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions "Name=AutoScalingGroupName,Value=my-app-asg" \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold

# Create step scaling policy
POLICY_ARN=$(aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-app-asg \
  --policy-name scale-out-steps \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments \
    "MetricIntervalLowerBound=0,MetricIntervalUpperBound=20,ScalingAdjustment=1" \
    "MetricIntervalLowerBound=20,MetricIntervalUpperBound=40,ScalingAdjustment=2" \
    "MetricIntervalLowerBound=40,ScalingAdjustment=4" \
  --query "PolicyARN" --output text)

# Link alarm to policy
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-alarm \
  --alarm-actions $POLICY_ARN

# ── SCHEDULED SCALING ─────────────────────────────────────────
# Scale up Mon-Fri 8am ET, scale down 7pm ET
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name my-app-asg \
  --scheduled-action-name morning-scale-up \
  --cron "0 13 * * 1-5" \     # 8am ET = 13:00 UTC
  --desired-capacity 10 \
  --min-size 6

aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name my-app-asg \
  --scheduled-action-name evening-scale-down \
  --cron "0 0 * * *" \        # Midnight UTC
  --desired-capacity 3 \
  --min-size 2
```

### Lifecycle Hooks

Perform actions during instance launch or termination:

```bash
# Lifecycle hook for launch (e.g., configure monitoring agent)
aws autoscaling put-lifecycle-hook \
  --lifecycle-hook-name launch-config-hook \
  --auto-scaling-group-name my-app-asg \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --default-result CONTINUE \
  --heartbeat-timeout 300 \
  --notification-target-arn arn:aws:sqs:us-east-1:123:config-queue

# Lifecycle hook for termination (e.g., drain connections)
aws autoscaling put-lifecycle-hook \
  --lifecycle-hook-name termination-drain-hook \
  --auto-scaling-group-name my-app-asg \
  --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
  --default-result CONTINUE \
  --heartbeat-timeout 60  # 60 seconds to drain

# Complete lifecycle action (call from instance or Lambda)
aws autoscaling complete-lifecycle-action \
  --lifecycle-hook-name launch-config-hook \
  --auto-scaling-group-name my-app-asg \
  --instance-id i-0abc123 \
  --lifecycle-action-result CONTINUE
```

---

## 3.8 Elastic Load Balancing (ELB)

### Load Balancer Types

```
┌──────────────────────────────────────────────────────────────────┐
│                    ELB TYPES COMPARISON                          │
├────────────────┬─────────────┬─────────────────────────────────┤
│ Type           │ Protocol    │ Use Case                        │
├────────────────┼─────────────┼─────────────────────────────────┤
│ ALB            │ HTTP/HTTPS/ │ Web apps, microservices, gRPC   │
│ (Application)  │ WebSocket   │ Path/header/query routing       │
│                │ HTTP/2      │ Targets: EC2, Lambda, ECS, IPs  │
├────────────────┼─────────────┼─────────────────────────────────┤
│ NLB            │ TCP/UDP/TLS │ High performance (<100ms), games │
│ (Network)      │             │ Static IP per AZ, PrivateLink   │
│                │             │ Targets: EC2, IPs, ALB          │
├────────────────┼─────────────┼─────────────────────────────────┤
│ GWLB           │ GENEVE      │ 3rd-party network appliances    │
│ (Gateway)      │ (UDP 6081)  │ Firewalls, IDS/IPS, DPI         │
└────────────────┴─────────────┴─────────────────────────────────┘
```

### Application Load Balancer (ALB)

```bash
# Create target group
aws elbv2 create-target-group \
  --name my-app-targets \
  --protocol HTTP \
  --port 8080 \
  --vpc-id vpc-0abc123 \
  --target-type instance \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

TG_ARN=$(aws elbv2 describe-target-groups \
  --names my-app-targets \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# Register targets manually (ASG handles this automatically)
aws elbv2 register-targets \
  --target-group-arn $TG_ARN \
  --targets Id=i-0abc123,Port=8080 Id=i-0def456,Port=8080

# Create ALB
aws elbv2 create-load-balancer \
  --name my-app-alb \
  --subnets subnet-0abc123 subnet-0def456 \
  --security-groups sg-0abc123 \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4

ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names my-app-alb \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names my-app-alb \
  --query "LoadBalancers[0].DNSName" --output text)

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123:certificate/abc \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# HTTP → HTTPS redirect listener
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

# Add path-based routing rule
HTTPS_LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --query "Listeners[?Protocol=='HTTPS'].ListenerArn" --output text)

aws elbv2 create-rule \
  --listener-arn $HTTPS_LISTENER_ARN \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"'$API_TG_ARN'"}]'

# Header-based routing
aws elbv2 create-rule \
  --listener-arn $HTTPS_LISTENER_ARN \
  --priority 20 \
  --conditions '[{"Field":"http-header","HttpHeaderConfig":{"HttpHeaderName":"X-Version","Values":["v2"]}}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"'$V2_TG_ARN'"}]'
```

### ALB Access Logs

```bash
# Enable access logs to S3
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn $ALB_ARN \
  --attributes \
    Key=access_logs.s3.enabled,Value=true \
    Key=access_logs.s3.bucket,Value=my-alb-logs \
    Key=access_logs.s3.prefix,Value=my-app-alb \
    Key=idle_timeout.timeout_seconds,Value=60

# Log format: timestamp, ELB name, client IP, backend IP, request time, etc.
```

### Network Load Balancer (NLB)

```bash
# Create NLB (TCP traffic, very high performance)
aws elbv2 create-load-balancer \
  --name my-tcp-nlb \
  --subnets subnet-0abc123 subnet-0def456 \
  --type network \
  --scheme internet-facing

# NLB with static Elastic IP per AZ
aws elbv2 create-load-balancer \
  --name my-nlb-static \
  --subnet-mappings \
    "SubnetId=subnet-0abc123,AllocationId=eipalloc-0abc123" \
    "SubnetId=subnet-0def456,AllocationId=eipalloc-0def456" \
  --type network

# TCP target group
aws elbv2 create-target-group \
  --name nlb-targets \
  --protocol TCP \
  --port 443 \
  --vpc-id vpc-0abc123 \
  --target-type ip

# TLS listener (NLB handles TLS termination)
aws elbv2 create-listener \
  --load-balancer-arn $NLB_ARN \
  --protocol TLS \
  --port 443 \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123:certificate/abc \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

---

## 3.9 EC2 Instance Metadata Service (IMDS)

```bash
# IMDSv2 (recommended — token-based, prevents SSRF attacks)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Get instance ID
curl -s http://169.254.169.254/latest/meta-data/instance-id \
  -H "X-aws-ec2-metadata-token: $TOKEN"

# Get IAM credentials (from instance role)
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/MyRole \
  -H "X-aws-ec2-metadata-token: $TOKEN"

# Get all metadata
curl -s http://169.254.169.254/latest/meta-data/ \
  -H "X-aws-ec2-metadata-token: $TOKEN"

# Useful metadata endpoints:
# instance-id, instance-type, public-ipv4, local-ipv4
# placement/availability-zone, placement/region
# iam/security-credentials/<role-name>
# hostname, public-hostname

# In Python
import boto3
from botocore.utils import IMDSFetcher

# boto3 automatically uses IMDSv2
session = boto3.Session()
ec2_metadata = session.client('ec2')
```

---

## 3.10 EC2 Systems Manager (SSM)

SSM allows you to manage EC2 instances **without SSH** or open port 22:

```bash
# Prerequisite: instance has SSM agent + AmazonSSMManagedInstanceCore role

# Start SSM Session (like SSH but over HTTPS)
aws ssm start-session --target i-0abc123

# Run command on one or more instances
aws ssm send-command \
  --instance-ids i-0abc123 i-0def456 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["df -h", "free -m", "uptime"]' \
  --output text

# Get command output
COMMAND_ID=$(aws ssm send-command \
  --instance-ids i-0abc123 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cat /etc/os-release"]' \
  --query "Command.CommandId" --output text)

aws ssm get-command-invocation \
  --command-id $COMMAND_ID \
  --instance-id i-0abc123 \
  --query "StandardOutputContent"

# Run command across all instances with tag
aws ssm send-command \
  --targets "Key=tag:Environment,Values=prod" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl restart my-service"]'

# Port forwarding through SSM (access private RDS via localhost)
aws ssm start-session \
  --target i-0abc123 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'
# Then: psql -h localhost -p 5432 -U myuser mydb
```

---

## 3.11 EC2 Spot Instances & Spot Fleet

```bash
# Spot instance request
aws ec2 request-spot-instances \
  --instance-count 5 \
  --type one-time \
  --launch-specification '{
    "ImageId": "ami-0abc123",
    "InstanceType": "c5.xlarge",
    "KeyName": "my-keypair",
    "SecurityGroupIds": ["sg-0abc123"],
    "SubnetId": "subnet-0abc123",
    "IamInstanceProfile": {"Name": "BatchWorkerRole"}
  }' \
  --spot-price "0.05"  # Max price (default: on-demand price)

# Check spot price history
aws ec2 describe-spot-price-history \
  --instance-types c5.xlarge c5a.xlarge c5d.xlarge \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --query "SpotPriceHistory[*].[InstanceType,SpotPrice,Timestamp,AvailabilityZone]" \
  --output table | sort -k2 -n

# Create Spot Fleet (mix of instance types for resilience)
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "TargetCapacity": 10,
    "AllocationStrategy": "capacityOptimized",
    "IamFleetRole": "arn:aws:iam::123:role/AmazonEC2SpotFleetRole",
    "LaunchSpecifications": [
      {"InstanceType": "c5.xlarge", "ImageId": "ami-0abc123"},
      {"InstanceType": "c5a.xlarge", "ImageId": "ami-0abc123"},
      {"InstanceType": "c5d.xlarge", "ImageId": "ami-0abc123"},
      {"InstanceType": "c4.xlarge", "ImageId": "ami-0abc123"}
    ]
  }'

# Spot interruption notice — handle in your app
# 2 minutes before interruption:
# curl http://169.254.169.254/latest/meta-data/spot/termination-time
# returns ISO8601 timestamp if being interrupted

# Best practices:
# - Use interruption handler to drain tasks gracefully
# - Store work in SQS, process in chunks
# - Use mixed instances policy in ASG (50% On-Demand, 50% Spot)
```

---

## 3.12 Interview Q&A

**Q: What is the difference between gp2 and gp3 EBS volumes?**
A: gp3 is the newer generation — 20% cheaper than gp2, and you can independently configure IOPS (3,000–16,000) and throughput (125–1,000 MB/s) regardless of volume size. gp2 ties IOPS to volume size (3 IOPS/GB). gp3 should be used for all new volumes.

**Q: What is the difference between an AMI and a snapshot?**
A: A snapshot is a point-in-time backup of an EBS volume. An AMI (Amazon Machine Image) includes one or more snapshots plus metadata (launch permissions, block device mappings) used to launch new EC2 instances. Creating an AMI automatically creates the associated EBS snapshots.

**Q: What is the difference between horizontal and vertical scaling?**
A: Vertical scaling (scale up) means increasing the size of existing instances (e.g., t3.micro → t3.large). Horizontal scaling (scale out) means adding more instances of the same size. AWS best practice is to prefer horizontal scaling — it's more resilient (no single point of failure) and works with Auto Scaling Groups.

**Q: What is the difference between ALB and NLB?**
A: ALB operates at Layer 7 (HTTP/HTTPS) and supports content-based routing (path, headers, query strings). NLB operates at Layer 4 (TCP/UDP), handles millions of requests per second with ultra-low latency, and supports static IPs. Use ALB for web applications; use NLB for high-performance, non-HTTP traffic.

**Q: What is an Instance Profile?**
A: An instance profile is a container for an IAM role that can be attached to an EC2 instance. It allows the EC2 instance to assume the role and get temporary credentials via IMDS. Applications running on the instance can then call AWS APIs without embedding access keys.

**Q: When would you use Spot Instances?**
A: For fault-tolerant, stateless, or checkpointable workloads: batch processing, scientific computing, CI/CD workers, video transcoding, machine learning training. Not suitable for persistent stateful workloads like databases where interruption would cause data loss.

**Q: What is IMDSv2 and why is it important?**
A: IMDSv2 is a session-oriented, token-based method to access EC2 instance metadata. Unlike IMDSv1 (simple GET requests), IMDSv2 requires a PUT request with a TTL to get a token first. This prevents SSRF (Server-Side Request Forgery) attacks where a compromised application could exfiltrate IAM credentials from the metadata endpoint.

**Q: What are EC2 placement groups and when would you use each type?**
A: Cluster placement groups pack instances together in a single AZ for low-latency, high-bandwidth networking (HPC, distributed databases). Spread placement groups place instances on different hardware racks for maximum isolation of critical instances. Partition placement groups distribute instances into partitions on separate racks — used by distributed systems like Hadoop, Cassandra, Kafka that need rack-awareness.
