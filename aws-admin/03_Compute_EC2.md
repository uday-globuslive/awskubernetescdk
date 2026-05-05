# Chapter 3: Compute — EC2, Auto Scaling & Load Balancers
## Virtual Machines, Scaling, and Traffic Distribution

---

## 3.1 EC2 Overview

**EC2 (Elastic Compute Cloud)** gives you virtual machines (called instances) in the cloud.

```
┌──────────────────────────────────────────────────────────┐
│                   EC2 COMPONENTS                         │
│                                                          │
│  Instance       → Running virtual machine                │
│  AMI            → Template (OS + software) for instance  │
│  Instance Type  → Hardware spec (CPU, RAM, network)      │
│  EBS Volume     → Persistent disk attached to instance   │
│  Security Group → Virtual firewall (inbound/outbound)    │
│  Key Pair       → SSH credentials                        │
│  Elastic IP     → Static public IP address               │
│  User Data      → Script that runs on first boot         │
└──────────────────────────────────────────────────────────┘
```

---

## 3.2 Instance Types

AWS has 400+ instance types. Learn the families:

```
┌────────────┬────────────────────────────────────────────┐
│ Family     │ Purpose & Examples                         │
├────────────┼────────────────────────────────────────────┤
│ t3, t4g    │ General purpose, burstable (dev/test)       │
│            │ t3.micro (free tier), t3.medium             │
├────────────┼────────────────────────────────────────────┤
│ m5, m6i    │ General purpose, balanced (web servers)     │
│            │ m5.large, m5.xlarge, m5.4xlarge             │
├────────────┼────────────────────────────────────────────┤
│ c5, c6i    │ Compute optimised (CPU-heavy: ML, gaming)   │
│            │ c5.xlarge, c5.9xlarge                       │
├────────────┼────────────────────────────────────────────┤
│ r5, r6i    │ Memory optimised (in-memory DB, caches)     │
│            │ r5.xlarge (32GB RAM), r5.8xlarge (256GB)    │
├────────────┼────────────────────────────────────────────┤
│ p3, p4     │ GPU instances (deep learning, rendering)    │
│            │ p3.2xlarge (1 NVIDIA V100)                  │
├────────────┼────────────────────────────────────────────┤
│ i3, i4i    │ Storage optimised (high IOPS databases)     │
│            │ i3.xlarge (NVMe SSD)                        │
└────────────┴────────────────────────────────────────────┘

Naming: m5.xlarge
        │ │  └─ Size: nano < micro < small < medium < large
        │ └── Generation: higher = newer, cheaper, better
        └─── Family: m = general, c = compute, r = memory
```

---

## 3.3 AMI — Amazon Machine Image

An AMI is a snapshot (template) used to launch EC2 instances. Contains: OS, pre-installed packages, configuration.

```bash
# Find Amazon Linux 2023 AMI
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId"

# Create your own AMI from a running instance
aws ec2 create-image \
  --instance-id i-0abc123 \
  --name "my-app-v1.0" \
  --description "App server with all deps installed"

# Copy AMI to another region
aws ec2 copy-image \
  --source-region us-east-1 \
  --source-image-id ami-0abc123 \
  --name "my-app-v1.0-copy" \
  --region eu-west-1
```

---

## 3.4 Launching an EC2 Instance

```bash
# Minimal launch
aws ec2 run-instances \
  --image-id ami-0abc123456789 \
  --instance-type t3.micro \
  --key-name my-key-pair \
  --security-group-ids sg-0abc123 \
  --subnet-id subnet-0abc123 \
  --count 1

# With User Data (bootstrap script)
aws ec2 run-instances \
  --image-id ami-0abc123456789 \
  --instance-type t3.small \
  --key-name my-key-pair \
  --security-group-ids sg-0abc123 \
  --subnet-id subnet-0abc123 \
  --iam-instance-profile Name=my-ec2-role \
  --user-data file://bootstrap.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server},{Key=Environment,Value=prod}]'
```

```bash
# bootstrap.sh — runs on first boot as root
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git

# Install app
pip3 install fastapi uvicorn

# Create systemd service
cat > /etc/systemd/system/fastapi.service << 'EOF'
[Unit]
Description=FastAPI App
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/app
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable fastapi
systemctl start fastapi
```

---

## 3.5 Security Groups

Security Groups are **stateful** virtual firewalls. If you allow inbound traffic, the response is automatically allowed outbound.

```bash
# Create security group
aws ec2 create-security-group \
  --group-name web-server-sg \
  --description "Web server security group" \
  --vpc-id vpc-0abc123

# Allow inbound HTTP
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abc123 \
  --protocol tcp --port 80 \
  --cidr 0.0.0.0/0

# Allow inbound HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abc123 \
  --protocol tcp --port 443 \
  --cidr 0.0.0.0/0

# Allow SSH from office IP only
aws ec2 authorize-security-group-ingress \
  --group-id sg-0abc123 \
  --protocol tcp --port 22 \
  --cidr 203.0.113.0/32

# Reference another security group (e.g., allow ALB to reach EC2)
aws ec2 authorize-security-group-ingress \
  --group-id sg-ec2-id \
  --protocol tcp --port 8000 \
  --source-group sg-alb-id
```

```
Common Security Group Patterns:
┌─────────────────────────────────────────────────────────┐
│  ALB Security Group                                     │
│  Inbound:  80, 443 from 0.0.0.0/0                      │
│  Outbound: 8000 to EC2 SG                               │
│                                                         │
│  EC2 App Security Group                                 │
│  Inbound:  8000 from ALB SG only                        │
│  Inbound:  22 from Bastion SG only                      │
│  Outbound: 5432 to RDS SG (database port)               │
│                                                         │
│  RDS Security Group                                     │
│  Inbound:  5432 from EC2 App SG only                    │
│  Outbound: (none needed — stateful)                     │
└─────────────────────────────────────────────────────────┘
```

---

## 3.6 EBS Volumes

**Elastic Block Store** — persistent block storage for EC2. Tied to one AZ.

```
EBS Volume Types:
┌──────────────┬────────────┬──────────────────────────────┐
│ Type         │ Use Case   │ Performance                  │
├──────────────┼────────────┼──────────────────────────────┤
│ gp3          │ General    │ 3000-16000 IOPS, baseline    │
│ (default)    │ purpose    │ 125-1000 MB/s throughput     │
├──────────────┼────────────┼──────────────────────────────┤
│ io2 Block    │ High-perf  │ Up to 256,000 IOPS           │
│ Express      │ databases  │ Sub-millisecond latency      │
├──────────────┼────────────┼──────────────────────────────┤
│ st1          │ Big data,  │ 500 MB/s throughput          │
│              │ log proc.  │ Sequential reads             │
├──────────────┼────────────┼──────────────────────────────┤
│ sc1          │ Cold data  │ 250 MB/s, lowest cost        │
└──────────────┴────────────┴──────────────────────────────┘
```

```bash
# Create EBS volume
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --size 100 \
  --volume-type gp3 \
  --iops 3000 \
  --throughput 125 \
  --encrypted

# Attach to instance
aws ec2 attach-volume \
  --volume-id vol-0abc123 \
  --instance-id i-0abc123 \
  --device /dev/sdf

# Take snapshot (backup)
aws ec2 create-snapshot \
  --volume-id vol-0abc123 \
  --description "Daily backup $(date +%Y-%m-%d)"

# Restore from snapshot to new volume
aws ec2 create-volume \
  --snapshot-id snap-0abc123 \
  --availability-zone us-east-1a \
  --volume-type gp3
```

---

## 3.7 Auto Scaling Groups (ASG)

ASG automatically adds or removes EC2 instances based on demand.

```
┌──────────────────────────────────────────────────────────┐
│                 AUTO SCALING GROUP                       │
│                                                          │
│  Min: 2  ──── always running at least 2 instances       │
│  Max: 10 ──── never exceed 10 instances                  │
│  Desired: 4 ─ target when no scaling happening           │
│                                                          │
│  Scale Out trigger: CPU > 70% for 2 minutes              │
│  Scale In trigger:  CPU < 30% for 10 minutes             │
│                                                          │
│  AZ-1a: 2 instances                                      │
│  AZ-1b: 2 instances                                      │
│  (ASG spreads across AZs automatically)                  │
└──────────────────────────────────────────────────────────┘
```

### Launch Template

```bash
# Create launch template (modern way — replaces Launch Configuration)
aws ec2 create-launch-template \
  --launch-template-name web-server-lt \
  --version-description "v1" \
  --launch-template-data '{
    "ImageId": "ami-0abc123456789",
    "InstanceType": "t3.medium",
    "KeyName": "my-key-pair",
    "SecurityGroupIds": ["sg-0abc123"],
    "IamInstanceProfile": {"Name": "web-server-role"},
    "UserData": "'"$(base64 -w0 bootstrap.sh)"'",
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [{"Key": "Environment", "Value": "prod"}]
    }]
  }'
```

### Create and Configure ASG

```bash
# Create ASG
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name web-servers-asg \
  --launch-template LaunchTemplateName=web-server-lt,Version='$Latest' \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 4 \
  --vpc-zone-identifier "subnet-0abc,subnet-0def" \
  --target-group-arns arn:aws:elasticloadbalancing:...:targetgroup/... \
  --health-check-type ELB \
  --health-check-grace-period 300

# Target tracking policy — keep CPU at 50%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-servers-asg \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 50.0
  }'

# Manual scale
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name web-servers-asg \
  --desired-capacity 6
```

### Scaling Policies

```
┌─────────────────────────────────────────────────────────┐
│              ASG SCALING POLICY TYPES                   │
├────────────────────────┬────────────────────────────────┤
│ Target Tracking        │ "Keep CPU at 50%"               │
│                        │ AWS adds/removes automatically  │
│                        │ Recommended for most cases      │
├────────────────────────┼────────────────────────────────┤
│ Step Scaling           │ "If CPU > 70% add 2, if > 90%  │
│                        │ add 5 more"                     │
│                        │ More control                    │
├────────────────────────┼────────────────────────────────┤
│ Scheduled              │ "Every weekday at 9am → min 10" │
│                        │ For predictable patterns        │
├────────────────────────┼────────────────────────────────┤
│ Predictive             │ ML-based, forecasts future load │
│                        │ Pre-scales before traffic hits  │
└────────────────────────┴────────────────────────────────┘
```

---

## 3.8 Elastic Load Balancing (ELB)

Load balancers distribute traffic across multiple targets (EC2, ECS, Lambda, IPs).

```
┌──────────────────────────────────────────────────────────┐
│              THREE TYPES OF LOAD BALANCERS               │
├────────────────┬─────────────────────────────────────────┤
│ ALB            │ Application Load Balancer                │
│ (Recommended)  │ Layer 7 (HTTP/HTTPS/WebSocket)           │
│                │ Route by path, host header, query string │
│                │ Supports Lambda targets                  │
│                │ Best for web apps and microservices      │
├────────────────┼─────────────────────────────────────────┤
│ NLB            │ Network Load Balancer                    │
│                │ Layer 4 (TCP/UDP/TLS)                    │
│                │ Ultra-low latency, millions req/sec      │
│                │ Static IP per AZ                         │
│                │ Best for gaming, IoT, financial apps     │
├────────────────┼─────────────────────────────────────────┤
│ Gateway LB     │ Layer 3 — for network appliances         │
│                │ Firewalls, intrusion detection           │
│                │ Rarely used in typical apps              │
└────────────────┴─────────────────────────────────────────┘
```

### ALB — Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name web-alb \
  --subnets subnet-0abc subnet-0def \
  --security-groups sg-0abc123 \
  --scheme internet-facing \
  --type application

# Create Target Group
aws elbv2 create-target-group \
  --name web-servers-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-0abc123 \
  --target-type instance \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Register targets
aws elbv2 register-targets \
  --target-group-arn arn:...:targetgroup/web-servers-tg/... \
  --targets Id=i-0abc123 Id=i-0def456

# Create listener (HTTP)
aws elbv2 create-listener \
  --load-balancer-arn arn:...:loadbalancer/app/web-alb/... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:...:targetgroup/web-servers-tg/...

# Add HTTPS listener with SSL cert
aws elbv2 create-listener \
  --load-balancer-arn arn:...:loadbalancer/app/web-alb/... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:...:certificate/... \
  --default-actions Type=forward,TargetGroupArn=arn:...:targetgroup/web-servers-tg/...
```

### ALB Path-Based Routing (Microservices)

```bash
# Route /api/users/* to users-tg
aws elbv2 create-rule \
  --listener-arn arn:...:listener/... \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/users/*"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"arn:...:targetgroup/users-tg/..."}]'

# Route /api/products/* to products-tg
aws elbv2 create-rule \
  --listener-arn arn:...:listener/... \
  --priority 20 \
  --conditions '[{"Field":"path-pattern","Values":["/api/products/*"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"arn:...:targetgroup/products-tg/..."}]'

# Redirect HTTP → HTTPS
aws elbv2 create-rule \
  --listener-arn arn:...:listener/http-listener/... \
  --priority 1 \
  --conditions '[{"Field":"path-pattern","Values":["/*"]}]' \
  --actions '[{
    "Type": "redirect",
    "RedirectConfig": {
      "Protocol": "HTTPS",
      "Port": "443",
      "StatusCode": "HTTP_301"
    }
  }]'
```

---

## 3.9 EC2 Metadata Service

Every EC2 instance can query its own metadata — no credentials needed:

```bash
# From inside an EC2 instance:

# Get instance ID
curl http://169.254.169.254/latest/meta-data/instance-id

# Get IAM role temporary credentials
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/my-role-name

# Get public IP
curl http://169.254.169.254/latest/meta-data/public-ipv4

# Get AZ
curl http://169.254.169.254/latest/meta-data/placement/availability-zone

# IMDSv2 (more secure — requires session token)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id
```

---

## 3.10 Interview Questions

**Q: What is the difference between a Security Group and a NACL?**
> Security Groups are stateful (return traffic auto-allowed), operate at the instance level, and only have allow rules. NACLs (Network Access Control Lists) are stateless (must explicitly allow inbound AND outbound), operate at the subnet level, and support both allow and deny rules. For most applications, Security Groups are sufficient.

**Q: What's the difference between vertical and horizontal scaling?**
> Vertical scaling = making one instance bigger (t3.micro → t3.xlarge). Has an upper limit, causes downtime to resize. Horizontal scaling = adding more instances. No upper limit (within reason), zero downtime with ASG. AWS favors horizontal scaling.

**Q: What's the difference between ALB and NLB?**
> ALB operates at Layer 7 (HTTP) and can route based on URL path, headers, or query strings — ideal for web apps and microservices. NLB operates at Layer 4 (TCP/UDP) with much lower latency (microseconds vs milliseconds) and a static IP per AZ — ideal for gaming, financial trading, or anything needing raw throughput.

**Q: How does Auto Scaling know when to scale in/out?**
> Through CloudWatch alarms and scaling policies. Target tracking scaling policies are the simplest — you specify a metric (e.g., CPU = 50%) and ASG automatically adds/removes instances to maintain that target. You can also use custom metrics like SQS queue depth or request count per target.
