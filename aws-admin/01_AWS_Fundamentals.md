# Chapter 1: AWS Fundamentals
## Global Infrastructure, Service Model, CLI, Pricing & Getting Started

---

## 1.1 What is AWS?

Amazon Web Services (AWS) is the world's most comprehensive and broadly adopted cloud platform, offering over 200 fully featured services from data centers globally. Millions of customers — including the fastest-growing startups, largest enterprises, and leading government agencies — trust AWS to power their infrastructure, become more agile, and lower costs.

```
Traditional On-Premises IT                  AWS Cloud
──────────────────────────                  ─────────────────────────
Buy servers upfront (CapEx)         →       Pay per second/hour/request (OpEx)
Provisioning takes weeks/months     →       Resources ready in minutes
Fixed capacity — over or under       →       Elastic: scale up/down instantly
You manage: hardware + OS + racks   →       AWS manages hardware layer
Single location (DR = duplicate DC) →       Global reach in minutes
Physical security, HVAC, cabling    →       AWS handles physical security
Refresh cycle every 3-5 years       →       Always latest hardware
```

### Cloud Benefits (The 6 Advantages of Cloud)

AWS documents these as the six core advantages:

1. **Trade capital expense for variable expense** — Pay only when you consume resources
2. **Benefit from massive economies of scale** — AWS aggregates usage from hundreds of thousands of customers → lower prices
3. **Stop guessing capacity** — Scale up or down as needed; no idle servers
4. **Increase speed and agility** — New IT resources weeks → minutes
5. **Stop spending money on data center operations** — Focus on customers, not infrastructure
6. **Go global in minutes** — Deploy in multiple regions with a few clicks

### Cloud Deployment Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Public Cloud** | Resources on AWS shared infrastructure, logically isolated | Most workloads |
| **Private Cloud** | Resources on your own infrastructure (VMware, OpenStack) | Regulated industries |
| **Hybrid Cloud** | Mix of on-premises and public cloud (AWS Outposts, Direct Connect) | Gradual migration, data sovereignty |
| **Multi-Cloud** | AWS + Azure + GCP | Avoiding vendor lock-in, best-of-breed |

### Cloud Service Models

```
┌────────────────────────────────────────────────────────────────┐
│                  CLOUD SERVICE MODELS                          │
├──────────────────┬─────────────────────┬───────────────────────┤
│     IaaS         │       PaaS           │       SaaS            │
│  (You manage     │   (Platform provided)│  (Fully managed app)  │
│   more)          │                      │                       │
├──────────────────┼─────────────────────┼───────────────────────┤
│ EC2, VPC, EBS    │ Elastic Beanstalk   │ WorkMail, Chime       │
│ Raw compute      │ Lambda (runtime)    │ Salesforce, Gmail     │
│ You manage OS    │ RDS (DB engine)     │ No infrastructure     │
│ networking, apps │ ECS (container mgmt)│ just use the app      │
└──────────────────┴─────────────────────┴───────────────────────┘
```

---

## 1.2 Global Infrastructure — Deep Dive

### Regions

A **Region** is an independent geographic area containing multiple, isolated, physically separate data centers called Availability Zones. Each region is completely independent — data does not replicate across regions unless you explicitly configure it.

```
AWS Regions (33+ launched regions):

Americas:
  us-east-1      US East (N. Virginia)      ← Oldest, most services
  us-east-2      US East (Ohio)
  us-west-1      US West (N. California)
  us-west-2      US West (Oregon)
  ca-central-1   Canada (Central)
  ca-west-1      Canada (Calgary)
  sa-east-1      South America (São Paulo)
  mx-central-1   Mexico (Central)

Europe:
  eu-west-1      Europe (Ireland)
  eu-west-2      Europe (London)
  eu-west-3      Europe (Paris)
  eu-central-1   Europe (Frankfurt)
  eu-central-2   Europe (Zurich)
  eu-north-1     Europe (Stockholm)
  eu-south-1     Europe (Milan)
  eu-south-2     Europe (Spain)

Asia Pacific:
  ap-southeast-1 Asia Pacific (Singapore)
  ap-southeast-2 Asia Pacific (Sydney)
  ap-southeast-3 Asia Pacific (Jakarta)
  ap-southeast-4 Asia Pacific (Melbourne)
  ap-northeast-1 Asia Pacific (Tokyo)
  ap-northeast-2 Asia Pacific (Seoul)
  ap-northeast-3 Asia Pacific (Osaka)
  ap-south-1     Asia Pacific (Mumbai)
  ap-south-2     Asia Pacific (Hyderabad)
  ap-east-1      Asia Pacific (Hong Kong)

Middle East & Africa:
  me-south-1     Middle East (Bahrain)
  me-central-1   Middle East (UAE)
  af-south-1     Africa (Cape Town)
  il-central-1   Israel (Tel Aviv)

GovCloud (US only — isolated):
  us-gov-east-1  AWS GovCloud (US-East)
  us-gov-west-1  AWS GovCloud (US-West)

China (separate entities):
  cn-north-1     China (Beijing)   — operated by Sinnet
  cn-northwest-1 China (Ningxia)   — operated by NWCD
```

**How to choose a Region — Decision Framework:**

```
1. Compliance / Data Residency (FIRST priority)
   ├── GDPR (EU users) → eu-west-1, eu-central-1
   ├── Australia data laws → ap-southeast-2
   └── US federal data → us-gov-east-1

2. Latency (user proximity)
   ├── Use AWS latency tester: cloudping.info
   └── Target: <100ms for interactive apps

3. Service Availability
   ├── Check: https://aws.amazon.com/about-aws/global-infrastructure/
   └── Not all services in all regions (some AI services us-east-1 only)

4. Price
   ├── us-east-1 generally cheapest
   ├── ap-southeast-2 (Sydney) typically 10-20% more expensive
   └── Use AWS Pricing Calculator to compare
```

### Availability Zones (AZs) — Deep Dive

Each region contains **2–6 Availability Zones** (most have 3). Each AZ:
- Is one or more **discrete data centers** with redundant power, networking, and connectivity
- Is physically separated by meaningful distance (typically tens of miles apart)
- Is connected to other AZs in the region via low-latency, high-bandwidth, fully redundant fiber
- Has its own independent power grids from multiple utilities

```
Region: us-east-1 — 6 AZs
┌────────────────────────────────────────────────────────────┐
│                     us-east-1                              │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ us-east- │  │ us-east- │  │ us-east- │                 │
│  │  1a      │  │  1b      │  │  1c      │                 │
│  │          │  │          │  │          │                 │
│  │ Data     │  │ Data     │  │ Data     │                 │
│  │ Center 1 │  │ Center 3 │  │ Center 5 │                 │
│  │ +2       │  │ +4       │  │ +6       │                 │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                 │
│       │              │              │                      │
│       └──────────────┴──────────────┘                      │
│            High-speed private fiber (<1ms latency)         │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ us-east- │  │ us-east- │  │ us-east- │                 │
│  │  1d      │  │  1e      │  │  1f      │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└────────────────────────────────────────────────────────────┘

NOTE: The letter (1a, 1b...) is account-specific! AWS maps the
physical AZ randomly per account. Your "us-east-1a" != my "us-east-1a"
(use AZ IDs like use1-az1 for sharing across accounts)
```

**HA Pattern — Minimum 2 AZs:**
```
                        Internet
                           │
                        Route53
                           │
                    ┌──────┴──────┐
                    │    ALB      │
                    └──────┬──────┘
              ┌────────────┴────────────┐
              │                         │
         AZ-1a (primary)           AZ-1b (standby)
         ┌──────────┐              ┌──────────┐
         │  EC2 #1  │              │  EC2 #2  │
         └────┬─────┘              └────┬─────┘
              │                         │
         ┌────┴─────┐             ┌─────┴────┐
         │ RDS      │  replicate  │ RDS      │
         │ Primary  │ ──────────► │ Standby  │
         └──────────┘             └──────────┘

If AZ-1a goes down → ALB routes to AZ-1b, RDS auto-failovers
```

### Edge Locations and Points of Presence

AWS has **600+ Points of Presence** (PoPs) across 90+ cities in 40+ countries:
- **Edge Locations** (400+): Cache CloudFront content closest to users; used by Route53
- **Regional Edge Caches** (13): Larger caches between origin and edge locations

```
Request flow with CloudFront:
User (Tokyo) → Edge Location Tokyo → Regional Cache Singapore → Origin us-east-1

Without CloudFront:
User (Tokyo) → Origin us-east-1  [~150ms latency]

With CloudFront (cached):
User (Tokyo) → Edge Location Tokyo  [<10ms latency]
```

### Local Zones

AWS Local Zones are extensions of an AWS Region that place compute, storage, database, and other select services closer to large population centers. Examples: Los Angeles, Dallas, Denver, Atlanta, Chicago.

```bash
# List available Local Zones
aws ec2 describe-availability-zones \
  --filters Name=zone-type,Values=local-zone \
  --query "AvailabilityZones[*].[ZoneName,ZoneType,State]" \
  --output table
```

### Wavelength Zones

AWS Wavelength embeds AWS compute and storage at telecom providers' 5G networks. Enables single-digit millisecond latency for mobile/edge applications (gaming, AR/VR, live video).

### AWS Outposts

Run AWS services on-premises. Same hardware, same APIs, same tools as AWS cloud — but physically in your data center.

```
┌─────────────────────────────────────────┐
│           Your Data Center              │
│  ┌──────────────────────────────────┐   │
│  │    AWS Outpost Rack              │   │
│  │  ┌──────────┐  ┌──────────┐     │   │
│  │  │  EC2     │  │   RDS    │     │   │
│  │  │ instances│  │ on-prem  │     │   │
│  │  └──────────┘  └──────────┘     │   │
│  │    Same APIs as AWS cloud        │   │
│  └──────────────────────────────────┘   │
│          ↕ AWS Direct Connect           │
└─────────────────────────────────────────┘
                    ↕
           AWS Region (control plane)
```

---

## 1.3 AWS Service Categories — Comprehensive Overview

### Compute

| Service | Description | Key Use Cases |
|---------|-------------|---------------|
| **EC2** | Virtual machines (IaaS) | Web servers, databases, any workload needing full OS control |
| **Lambda** | Serverless functions, run code without servers | APIs, event processing, scheduled tasks |
| **ECS** | Container orchestration with Docker | Microservices, containerized apps |
| **EKS** | Managed Kubernetes | Complex container orchestration |
| **Fargate** | Serverless containers (no EC2 to manage) | Containers without capacity management |
| **Elastic Beanstalk** | PaaS — deploy apps without managing infrastructure | Simple deployments, developer-focused |
| **Lightsail** | Simplified VPS (fixed pricing) | Simple web apps, WordPress |
| **Batch** | Batch computing at scale | HPC, scientific computing |
| **App Runner** | Fully managed container/source deployment | Simple containerized web services |

### Storage

| Service | Type | Description | Use Cases |
|---------|------|-------------|-----------|
| **S3** | Object | Unlimited files (objects) in buckets | Backups, static websites, data lake |
| **EBS** | Block | SSD/HDD volumes attached to EC2 | OS disks, databases on EC2 |
| **EFS** | File | NFS shared filesystem | Shared content, CMS |
| **FSx** | File | Windows (NTFS), Lustre, ONTAP | Windows workloads, HPC |
| **S3 Glacier** | Archive | Low-cost long-term archival | Compliance archives, old data |
| **Storage Gateway** | Hybrid | Connect on-prem to S3/EBS/FSx | Hybrid storage, backup to cloud |
| **Snow Family** | Physical | Physical devices to move data to AWS | Large data migrations |

### Databases

| Service | Type | Engine | Use Cases |
|---------|------|--------|-----------|
| **RDS** | Relational (managed) | MySQL, PostgreSQL, MariaDB, Oracle, SQL Server | Traditional apps |
| **Aurora** | Relational (cloud-native) | MySQL/PostgreSQL compatible | High-performance, enterprise |
| **DynamoDB** | NoSQL (key-value/document) | Proprietary | High-scale, single-digit ms latency |
| **ElastiCache** | In-memory | Redis, Memcached | Caching, sessions, leaderboards |
| **DocumentDB** | Document | MongoDB compatible | MongoDB workloads (managed) |
| **Keyspaces** | Wide-column | Cassandra compatible | Cassandra workloads (managed) |
| **Neptune** | Graph | Gremlin/SPARQL | Social networks, fraud detection |
| **Timestream** | Time-series | Proprietary | IoT metrics, telemetry |
| **Redshift** | Data warehouse | PostgreSQL-based | Analytics, BI, large-scale queries |

### Networking & Content Delivery

| Service | Description |
|---------|-------------|
| **VPC** | Private network in AWS — subnets, route tables, security groups |
| **Route53** | DNS service + domain registration + health checks |
| **CloudFront** | CDN — cache content at 400+ edge locations globally |
| **API Gateway** | Managed API endpoint for REST/HTTP/WebSocket APIs |
| **Elastic Load Balancing** | ALB (HTTP/HTTPS), NLB (TCP/UDP), GWLB (appliances) |
| **Direct Connect** | Dedicated private connection from on-prem to AWS |
| **Site-to-Site VPN** | Encrypted tunnel over internet from on-prem to VPC |
| **Transit Gateway** | Hub-and-spoke to connect multiple VPCs + on-prem |
| **Global Accelerator** | Route traffic to nearest healthy endpoint using AWS backbone |
| **PrivateLink** | Private connectivity to AWS services / VPC endpoints |

### Security, Identity & Compliance

| Service | Description |
|---------|-------------|
| **IAM** | Users, groups, roles, policies — who can do what |
| **Organizations** | Manage multiple accounts centrally with SCPs |
| **Cognito** | User authentication for apps (OAuth2/OIDC) |
| **KMS** | Key Management Service — create/manage encryption keys |
| **Secrets Manager** | Store/rotate secrets (passwords, API keys) |
| **Systems Manager Parameter Store** | Lightweight config/secret storage |
| **WAF** | Web Application Firewall — block common web attacks |
| **Shield** | DDoS protection (Standard free, Advanced paid) |
| **GuardDuty** | Threat detection using ML (analyzes CloudTrail, VPC Flow Logs, DNS) |
| **Security Hub** | Aggregated security findings across AWS accounts |
| **Inspector** | Automated vulnerability scanning for EC2/containers |
| **Macie** | ML-powered sensitive data discovery in S3 |
| **Certificate Manager** | Provision/manage TLS/SSL certificates |

---

## 1.4 AWS Shared Responsibility Model — Complete Guide

The Shared Responsibility Model defines what AWS secures vs what you secure.

```
┌────────────────────────────────────────────────────────────────┐
│                SHARED RESPONSIBILITY MODEL                     │
├────────────────────────────┬───────────────────────────────────┤
│   CUSTOMER RESPONSIBILITY  │   AWS RESPONSIBILITY              │
│   "Security IN the Cloud"  │   "Security OF the Cloud"         │
├────────────────────────────┼───────────────────────────────────┤
│ Customer data              │ Physical security of data centers  │
│ Platform, apps, IAM        │ Hardware (servers, storage, net)  │
│ OS configuration (EC2)     │ Hypervisor / virtualization layer │
│ Network config (SG, NACL)  │ Software for managed services     │
│ Firewall rules             │ Availability zones infrastructure │
│ Client-side encryption     │ Global infrastructure             │
│ Server-side encryption     │ Edge locations                    │
│ Network traffic protection │ Compliance certifications         │
└────────────────────────────┴───────────────────────────────────┘
```

**Service-specific breakdown:**

```
EC2 (IaaS — you manage most):
┌────────────────────────────────────────┐
│ YOU: OS, patches, apps, firewall       │
│ YOU: IAM instance profile              │
│ YOU: Data encryption                   │
│ AWS: Hypervisor, physical hardware     │
└────────────────────────────────────────┘

RDS (Managed — AWS manages more):
┌────────────────────────────────────────┐
│ YOU: Data, access (users/passwords)    │
│ YOU: Security groups, TLS config       │
│ AWS: OS patches, DB engine patches     │
│ AWS: Backups (automated), replication │
│ AWS: Hardware, failover                │
└────────────────────────────────────────┘

Lambda (Serverless — AWS manages most):
┌────────────────────────────────────────┐
│ YOU: Function code, IAM role           │
│ YOU: Environment variables security    │
│ AWS: Runtime patches                   │
│ AWS: OS, hardware, execution env       │
│ AWS: Scaling, availability             │
└────────────────────────────────────────┘

S3 (Managed Object Storage):
┌────────────────────────────────────────┐
│ YOU: Bucket policies, ACLs, encryption│
│ YOU: Block public access settings     │
│ YOU: Who has IAM access               │
│ AWS: Storage infrastructure, 11 9s    │
│ AWS: Disk replication within region   │
└────────────────────────────────────────┘
```

**Key Rule — "Inherited" vs "Shared" controls:**

| Control Type | Description | Examples |
|-------------|-------------|---------|
| **Inherited** | AWS fully responsible | Physical controls, environmental |
| **Shared** | Both responsible in different layers | Patch management, config management |
| **Customer** | Customer fully responsible | Customer data, IAM |

---

## 1.5 AWS Account Structure & Organizations

### Single Account (Not Recommended for Production)

```
AWS Account (123456789012)
├── All dev resources
├── All prod resources
├── All billing mixed
└── Single blast radius
```

### Multi-Account Strategy (Best Practice)

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Organization                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Management Account                     │   │
│  │  • Consolidated billing                             │   │
│  │  • Service Control Policies (SCPs)                 │   │
│  │  • AWS Organizations management                    │   │
│  │  • NO workloads (keep clean)                       │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│         ┌───────────┼───────────┐                           │
│         ▼           ▼           ▼                           │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐                   │
│  │ Security   │ │  Dev     │ │  Prod    │ Organizational    │
│  │    OU      │ │   OU     │ │   OU     │ Units (OUs)       │
│  └─────┬──────┘ └────┬─────┘ └────┬─────┘                   │
│        │             │             │                         │
│  ┌─────┴────┐  ┌─────┴────┐  ┌────┴─────┐                   │
│  │ Log      │  │ Dev      │  │ Prod     │ Member            │
│  │ Archive  │  │ Account  │  │ Account  │ Accounts          │
│  │ Account  │  │          │  │          │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
│  ┌──────────┐                                                │
│  │ Security │                                                │
│  │ Tooling  │                                                │
│  │ Account  │ (GuardDuty, Security Hub aggregation)         │
│  └──────────┘                                                │
└─────────────────────────────────────────────────────────────┘
```

**AWS Landing Zone / Control Tower** provides a pre-built multi-account setup with:
- Centralized logging (CloudTrail, Config to Log Archive account)
- Security notifications (Security Tooling account)
- Identity management (AWS SSO / IAM Identity Center)
- Guardrails (SCPs + Config rules)

### Service Control Policies (SCPs)

SCPs are organization-level policies that restrict what AWS accounts can do — even if the IAM policy allows it.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyOutsideApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "organizations:*",
        "route53:*",
        "budgets:*",
        "waf:*",
        "cloudfront:*",
        "globalaccelerator:*",
        "importexport:*",
        "support:*",
        "sts:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2",
            "eu-west-1"
          ]
        }
      }
    }
  ]
}
```

```bash
# Create an organization
aws organizations create-organization --feature-set ALL

# List existing OUs
aws organizations list-organizational-units-for-parent \
  --parent-id r-xxxx

# Create an OU
aws organizations create-organizational-unit \
  --parent-id r-xxxx \
  --name "Production"

# Create SCP
aws organizations create-policy \
  --name "DenyNonApprovedRegions" \
  --description "Restrict regions" \
  --type SERVICE_CONTROL_POLICY \
  --content file://scp-deny-regions.json

# Attach SCP to OU
aws organizations attach-policy \
  --policy-id p-xxxxxxxxxxxx \
  --target-id ou-xxxx-yyyyyyyy

# List accounts in OU
aws organizations list-accounts-for-parent \
  --parent-id ou-xxxx-yyyyyyyy
```

---

## 1.6 AWS CLI — Comprehensive Reference

### Installation & Configuration

```bash
# Install on Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Install on macOS
brew install awscli

# Verify
aws --version    # aws-cli/2.x.x

# Configure default profile
aws configure
# AWS Access Key ID: AKIA...
# AWS Secret Access Key: ...
# Default region: us-east-1
# Default output format: json

# Multiple named profiles
aws configure --profile dev
aws configure --profile prod

# Use specific profile
aws s3 ls --profile prod
export AWS_PROFILE=prod  # Set for entire shell session

# Configure using environment variables (best for CI/CD)
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

### Configuration Files

```ini
# ~/.aws/credentials
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[prod]
aws_access_key_id = AKIAI44QH8DHBEXAMPLE
aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY

# ~/.aws/config
[default]
region = us-east-1
output = json

[profile prod]
region = us-west-2
output = table
role_arn = arn:aws:iam::123456789012:role/AdminRole
source_profile = default     # Assume role from default profile
mfa_serial = arn:aws:iam::123456789012:mfa/myuser
```

### Identity & Authentication

```bash
# Who am I?
aws sts get-caller-identity
# Returns: UserId, Account, Arn

# Assume a role (get temporary credentials)
aws sts assume-role \
  --role-arn "arn:aws:iam::123456789012:role/AdminRole" \
  --role-session-name "MySession" \
  --duration-seconds 3600

# Assume role and export environment variables
eval $(aws sts assume-role \
  --role-arn "arn:aws:iam::123456789012:role/AdminRole" \
  --role-session-name "admin" \
  --query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
  --output text | awk '{
    print "export AWS_ACCESS_KEY_ID="$1
    print "export AWS_SECRET_ACCESS_KEY="$2
    print "export AWS_SESSION_TOKEN="$3
  }')

# MFA — get session token
aws sts get-session-token \
  --serial-number arn:aws:iam::123456789012:mfa/myuser \
  --token-code 123456
```

### Output Formatting & JMESPath Filtering

```bash
# Output formats
aws ec2 describe-instances --output json   # Default, machine-readable
aws ec2 describe-instances --output table  # Human-readable table
aws ec2 describe-instances --output text   # Tab-separated, scriptable
aws ec2 describe-instances --output yaml   # YAML format

# JMESPath queries (--query)
# Get specific fields
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,PublicIpAddress]" \
  --output table

# Filter running instances only
aws ec2 describe-instances \
  --query "Reservations[*].Instances[?State.Name=='running'].[InstanceId,InstanceType]" \
  --output table

# Get single value
aws ec2 describe-instances \
  --instance-ids i-0abc123 \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text

# Filter using --filters (server-side — faster for large sets)
aws ec2 describe-instances \
  --filters \
    "Name=tag:Environment,Values=prod" \
    "Name=instance-state-name,Values=running" \
  --query "Reservations[*].Instances[*].[InstanceId,PrivateIpAddress]" \
  --output table

# Count resources
aws ec2 describe-instances \
  --query "length(Reservations[*].Instances[])" \
  --output text

# Get tag value by key
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].{ID:InstanceId,Name:Tags[?Key=='Name']|[0].Value}" \
  --output table
```

### Pagination

```bash
# CLI auto-paginates most list/describe commands
# But for large datasets, control it:

# Disable auto-pagination (get first page only — much faster)
aws ec2 describe-instances --no-paginate --max-items 50

# Page-size (controls API call size, but returns all results)
aws ec2 describe-snapshots \
  --owner-ids self \
  --page-size 50

# Manual pagination with --starting-token
RESULT=$(aws s3api list-objects-v2 --bucket my-bucket --max-items 100)
TOKEN=$(echo $RESULT | jq -r '.NextToken')
aws s3api list-objects-v2 --bucket my-bucket --max-items 100 --starting-token $TOKEN
```

### Common CLI Patterns for All Services

```bash
# ── EC2 ───────────────────────────────────────────────────────
# List instances with names
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,Tags[?Key=='Name'].Value|[0]]" \
  --output table

# Start / stop / terminate
aws ec2 start-instances --instance-ids i-0abc123
aws ec2 stop-instances --instance-ids i-0abc123
aws ec2 reboot-instances --instance-ids i-0abc123
aws ec2 terminate-instances --instance-ids i-0abc123

# Get instance public IP
aws ec2 describe-instances \
  --instance-ids i-0abc123 \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text

# Describe security groups
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=vpc-0abc123" \
  --output table

# ── S3 ────────────────────────────────────────────────────────
aws s3 ls                                         # List all buckets
aws s3 ls s3://my-bucket/ --recursive             # List all objects
aws s3 cp file.txt s3://my-bucket/path/           # Upload single file
aws s3 cp s3://my-bucket/file.txt .               # Download
aws s3 sync ./local/ s3://my-bucket/prefix/       # Sync directory
aws s3 sync s3://source/ s3://dest/ --delete      # Mirror buckets
aws s3 rm s3://my-bucket/file.txt                 # Delete object
aws s3 rb s3://my-bucket --force                  # Delete bucket + all objects
aws s3 mb s3://new-bucket --region us-east-1      # Create bucket
aws s3 presign s3://my-bucket/file.txt \          # Pre-signed URL
  --expires-in 3600

# ── IAM ───────────────────────────────────────────────────────
aws iam list-users --output table
aws iam list-roles --output table
aws iam list-groups --output table
aws iam get-user --user-name john
aws iam list-attached-user-policies --user-name john
aws iam list-attached-role-policies --role-name MyRole
aws iam simulate-principal-policy \               # Test permissions
  --policy-source-arn arn:aws:iam::123:user/john \
  --action-names s3:GetObject ec2:DescribeInstances \
  --resource-arns "*"

# ── LAMBDA ────────────────────────────────────────────────────
aws lambda list-functions --output table
aws lambda invoke \                               # Invoke synchronously
  --function-name my-function \
  --payload '{"key":"value"}' \
  --cli-binary-format raw-in-base64-out \
  output.json ; cat output.json

# ── CLOUDFORMATION ────────────────────────────────────────────
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
aws cloudformation describe-stack-resources --stack-name my-stack
aws cloudformation validate-template --template-body file://template.yaml

# ── CLOUDWATCH ────────────────────────────────────────────────
# Get metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc123 \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average \
  --output table

# Tail logs
aws logs tail /aws/lambda/my-function --follow
aws logs filter-log-events \
  --log-group-name /aws/lambda/my-function \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

---

## 1.7 AWS Pricing Model — Complete Guide

### Core Pricing Principles

AWS follows three fundamental pricing rules:
1. **Pay for what you use** — No minimum fees (usually)
2. **Pay less when you reserve** — Commit to 1 or 3 years → up to 72% savings
3. **Pay less with volume** — Tiered pricing as usage grows

### EC2 Pricing Options — Detailed Comparison

```
┌──────────────────────────────────────────────────────────────────┐
│                    EC2 PRICING OPTIONS                           │
├─────────────────┬────────────┬──────────────────────────────────┤
│ Option          │ Savings vs │ Best For                         │
│                 │ On-Demand  │                                  │
├─────────────────┼────────────┼──────────────────────────────────┤
│ On-Demand       │ baseline   │ Short-term, unpredictable        │
│                 │            │ Dev/test, spiky workloads        │
├─────────────────┼────────────┼──────────────────────────────────┤
│ Savings Plans   │ up to 66%  │ Flexible — applies to EC2,       │
│ (Compute)       │            │ Lambda, Fargate; any family/     │
│                 │            │ region/OS; 1 or 3 year commit    │
├─────────────────┼────────────┼──────────────────────────────────┤
│ Savings Plans   │ up to 72%  │ EC2 only; specific instance      │
│ (EC2 Instance)  │            │ family + region; any size/OS     │
├─────────────────┼────────────┼──────────────────────────────────┤
│ Reserved        │ up to 72%  │ Steady-state, predictable load   │
│ Instances (RI)  │            │ 1-year or 3-year; can resell on  │
│                 │            │ RI Marketplace                   │
├─────────────────┼────────────┼──────────────────────────────────┤
│ Spot Instances  │ up to 90%  │ Fault-tolerant batch jobs,       │
│                 │            │ stateless apps, CI/CD workers    │
│                 │            │ Can be interrupted with 2-min    │
│                 │            │ warning                          │
├─────────────────┼────────────┼──────────────────────────────────┤
│ Dedicated Host  │ N/A        │ BYOL (Bring Your Own License)    │
│                 │            │ Compliance (single-tenant)       │
│                 │            │ Most expensive option            │
└─────────────────┴────────────┴──────────────────────────────────┘
```

**Reserved Instance types:**

| RI Type | Payment | Approximate Discount |
|---------|---------|---------------------|
| All Upfront 3-year | Full payment now | Highest (~72%) |
| Partial Upfront 3-year | Half now, half monthly | ~60% |
| No Upfront 3-year | Monthly only | ~50% |
| All Upfront 1-year | Full payment now | ~40% |
| No Upfront 1-year | Monthly only | ~25% |

### Other Service Pricing Models

```
S3 Pricing Components:
├── Storage: per GB/month (tiered: first 50TB → next 450TB → over 500TB)
├── Requests: per 1,000 requests (PUT/COPY/POST: $0.005, GET: $0.0004)
├── Data Transfer OUT: per GB (first 100GB/month free, then tiered)
├── Replication: additional storage + request charges
└── Features: S3 Select, Replication, Lifecycle transitions

Lambda Pricing:
├── Requests: $0.20 per million requests
├── Duration: $0.0000166667 per GB-second
├── Free tier: 1M requests + 400,000 GB-seconds per month FOREVER
└── Example: 1M requests x 1GB x 0.5s = 500K GB-s = $8.33/month

RDS Pricing:
├── Instance hours (similar to EC2 On-Demand/Reserved)
├── Storage: per GB/month (gp2: $0.115/GB, io1: $0.125/GB + $0.10/IOPS)
├── I/O requests (for Magnetic storage)
├── Backup storage beyond DB size
└── Data transfer (between AZs for Multi-AZ: charged)

Data Transfer Pricing (often overlooked):
├── IN to AWS: FREE
├── OUT to Internet: first 100GB/month free, then $0.09/GB
├── Between AZs same region: $0.01/GB each way
├── Between regions: $0.02/GB (varies by region pair)
└── To CloudFront: FREE
```

### AWS Free Tier

```
AWS Free Tier (12 months from account creation):
┌───────────────────────────────────────────────────────────────┐
│ EC2:       750 hrs/month  t2.micro or t3.micro                │
│ RDS:       750 hrs/month  db.t2.micro/db.t3.micro             │
│ S3:        5GB storage, 20K GET, 2K PUT                        │
│ Lambda:    1M requests + 400K GB-sec (ALWAYS FREE)            │
│ DynamoDB:  25GB storage + 25 WCU + 25 RCU (ALWAYS FREE)       │
│ CloudFront:1TB out + 10M requests (ALWAYS FREE)               │
│ SQS:       1M requests (ALWAYS FREE)                          │
│ SNS:       1M publishes (ALWAYS FREE)                         │
│ CloudWatch:10 custom metrics + 5GB log ingestion (ALWAYS FREE)│
└───────────────────────────────────────────────────────────────┘
```

### AWS Pricing Tools

```bash
# AWS Pricing Calculator (browser): calculator.aws
# Estimate costs before deploying

# Cost Explorer (CLI)
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity"

# Current month spend by service
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "ResultsByTime[0].Groups[?Metrics.BlendedCost.Amount>'10'].[Keys[0],Metrics.BlendedCost.Amount]" \
  --output table

# Current month forecast
aws ce get-cost-forecast \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --metric BLENDED_COST \
  --granularity MONTHLY
```

---

## 1.8 AWS Support Plans

```
┌──────────────────────────────────────────────────────────────────┐
│                    AWS SUPPORT PLANS                             │
├───────────┬────────────┬─────────────┬────────────┬─────────────┤
│ Feature   │  Basic     │ Developer   │ Business   │ Enterprise  │
│           │  (Free)    │ ($29/mo)    │ ($100/mo+) │ ($15K/mo+)  │
├───────────┼────────────┼─────────────┼────────────┼─────────────┤
│ AWS docs  │ YES        │ YES         │ YES        │ YES         │
│ Forums    │ YES        │ YES         │ YES        │ YES         │
│ Trusted   │ Core only  │ Core only   │ All checks │ All checks  │
│ Advisor   │            │             │            │             │
│ Tech      │ None       │ Business    │ 24/7 phone │ 24/7 phone  │
│ Support   │            │ hours only  │ email chat │ email chat  │
│ Response  │ None       │ General:    │ General:   │ General:    │
│ SLA       │            │ <24 biz hr  │ <24hr      │ <24hr       │
│           │            │ Impaired:   │ Impaired:  │ Impaired:   │
│           │            │ <12 biz hr  │ <12hr      │ <4hr        │
│           │            │             │ Prod down: │ Critical:   │
│           │            │             │ <4hr       │ <15min      │
│ TAM       │ None       │ None        │ None       │ Dedicated   │
│ Well-Arch │ Self-svc   │ Self-svc    │ Self-svc   │ Included    │
│ Reviews   │            │             │            │             │
└───────────┴────────────┴─────────────┴────────────┴─────────────┘
```

---

## 1.9 AWS Well-Architected Framework — Overview

The six pillars of the Well-Architected Framework:

```
┌──────────────────────────────────────────────────────────────┐
│            WELL-ARCHITECTED FRAMEWORK — 6 PILLARS            │
├──────────────────────────┬───────────────────────────────────┤
│ Pillar                   │ Core Question                     │
├──────────────────────────┼───────────────────────────────────┤
│ 1. Operational Excellence│ How do you run and monitor?       │
│   • IaC (CloudFormation) │ Small, reversible changes        │
│   • Runbooks, automation │ Anticipate failure               │
├──────────────────────────┼───────────────────────────────────┤
│ 2. Security              │ How do you protect information?   │
│   • IAM least privilege  │ Enable traceability              │
│   • Encryption at rest   │ Security at all layers           │
│   • WAF, Shield          │ Automate security best practices │
├──────────────────────────┼───────────────────────────────────┤
│ 3. Reliability           │ How do you recover from failure?  │
│   • Multi-AZ             │ Test recovery procedures         │
│   • Auto Scaling         │ Scale horizontally               │
│   • Backups, DR          │ Stop guessing capacity           │
├──────────────────────────┼───────────────────────────────────┤
│ 4. Performance Efficiency│ How do you use resources wisely?  │
│   • Right instance type  │ Use serverless where possible    │
│   • CloudFront CDN       │ Go global in minutes             │
│   • Benchmark regularly  │ Experiment more often            │
├──────────────────────────┼───────────────────────────────────┤
│ 5. Cost Optimization     │ How do you deliver value?        │
│   • Reserved/Spot        │ Measure efficiency               │
│   • S3 lifecycle rules   │ Stop spending on undifferentiated│
│   • Tag resources        │ Analyze and attribute spend      │
├──────────────────────────┼───────────────────────────────────┤
│ 6. Sustainability        │ What is environmental impact?    │
│   • Rightsize instances  │ Maximize utilization             │
│   • Use managed services │ Adopt efficient hardware         │
└──────────────────────────┴───────────────────────────────────┘
```

---

## 1.10 ARN Format — Complete Reference

Every AWS resource has a globally unique Amazon Resource Name (ARN):

```
Format:
arn:partition:service:region:account-id:resource-type/resource-id

partition:
  aws          → Standard AWS regions
  aws-cn       → China regions
  aws-us-gov   → GovCloud

Examples by service:
─────────────────────────────────────────────────────────────────
IAM User:
  arn:aws:iam::123456789012:user/john

IAM Role:
  arn:aws:iam::123456789012:role/MyLambdaRole

S3 Bucket (no region/account — global):
  arn:aws:s3:::my-unique-bucket-name

S3 Object:
  arn:aws:s3:::my-bucket/path/to/file.txt

EC2 Instance:
  arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456

Lambda Function:
  arn:aws:lambda:us-east-1:123456789012:function:my-function

Lambda Function with Qualifier (version/alias):
  arn:aws:lambda:us-east-1:123456789012:function:my-function:prod

RDS Database:
  arn:aws:rds:us-east-1:123456789012:db:my-database

DynamoDB Table:
  arn:aws:dynamodb:us-east-1:123456789012:table/Users

DynamoDB GSI:
  arn:aws:dynamodb:us-east-1:123456789012:table/Users/index/email-index

SQS Queue:
  arn:aws:sqs:us-east-1:123456789012:my-queue

SNS Topic:
  arn:aws:sns:us-east-1:123456789012:my-topic

CloudWatch Log Group:
  arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/my-function

Secrets Manager Secret:
  arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/db-password-AbCdEf

KMS Key:
  arn:aws:kms:us-east-1:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab

API Gateway REST API execute:
  arn:aws:execute-api:us-east-1:123456789012:abc123def/*/GET/users
─────────────────────────────────────────────────────────────────
ARN Wildcards in IAM Policies:
  arn:aws:s3:::my-bucket/*              → All objects in bucket
  arn:aws:ec2:*:*:instance/*           → All EC2 instances everywhere
  arn:aws:dynamodb:us-east-1:*:table/* → All DynamoDB tables in us-east-1
  arn:aws:lambda:*:123456789012:function:* → All functions in account
```

---

## 1.11 AWS Compliance & Certifications

AWS maintains compliance certifications that customers inherit for the infrastructure layer:

```
┌────────────────────────────────────────────────────────────────┐
│              AWS COMPLIANCE PROGRAMS (SELECTED)                │
├─────────────────────────┬──────────────────────────────────────┤
│ Certification           │ Relevance                           │
├─────────────────────────┼──────────────────────────────────────┤
│ SOC 1 / SOC 2 / SOC 3   │ Financial + security controls       │
│ ISO 27001               │ Information security management     │
│ ISO 27017               │ Cloud security                      │
│ ISO 27018               │ Cloud privacy (PII)                 │
│ PCI DSS Level 1         │ Payment card data                   │
│ HIPAA                   │ US healthcare data (HIPAA-eligible  │
│                         │ services — you sign BAA with AWS)   │
│ FedRAMP                 │ US federal government               │
│ GDPR                    │ EU data protection                  │
│ CSA STAR                │ Cloud security assurance            │
└─────────────────────────┴──────────────────────────────────────┘

Shared compliance model:
→ AWS has the certifications for its infrastructure
→ YOU are responsible for configuring your workload correctly
→ AWS Artifact: download compliance reports (SOC, ISO, PCI)
  console.aws.amazon.com/artifact
```

---

## 1.12 Getting Started Checklist

```
Day 1 — Account Setup:
□ Create AWS account
□ Enable MFA on root account (CRITICAL — do this first)
□ Create admin IAM user (never use root for daily tasks)
□ Enable MFA on admin IAM user
□ Set up billing alarm ($10 threshold for learning accounts)
□ Enable Cost Explorer
□ Set IAM password policy (minimum 12 chars + MFA)

Week 1 — Foundation:
□ Install AWS CLI v2
□ Configure CLI with IAM user credentials
□ Explore IAM: create user, group, role, policy
□ Launch an EC2 instance (free tier t3.micro)
□ Create an S3 bucket, upload a file
□ Create a Lambda function (Hello World)
□ Deploy a CloudFormation stack

Month 1 — Core Services:
□ VPC: create custom VPC with public/private subnets
□ RDS: launch MySQL/PostgreSQL (free tier)
□ DynamoDB: create table, put/get items
□ ECS/Fargate: deploy a containerized app
□ API Gateway + Lambda: build a simple REST API
□ CloudWatch: create alarms and dashboards
□ IAM roles: understand least privilege

Security Hardening (Production):
□ Enable CloudTrail in all regions
□ Enable GuardDuty
□ Enable Security Hub
□ Enable Config with managed rules
□ Review and remediate Trusted Advisor findings
□ Block public access on all S3 buckets
□ Enable S3 bucket versioning on critical buckets
□ Rotate access keys older than 90 days
□ Enable VPC Flow Logs
□ Set up AWS Budget alert for cost threshold
```

---

## 1.13 Interview Q&A

**Q: What is the difference between a Region and an Availability Zone?**
A: A Region is a geographic area (e.g., us-east-1) containing multiple, physically separate data centers called Availability Zones. AZs in a region are connected by low-latency private fiber but are isolated from each other for fault tolerance. Deploy across multiple AZs for high availability.

**Q: What is the Shared Responsibility Model?**
A: AWS is responsible for security "of" the cloud (physical infrastructure, hardware, hypervisor, managed service OS patches). Customers are responsible for security "in" the cloud (their data, IAM permissions, OS configuration on EC2, application security, encryption choices).

**Q: What is an ARN?**
A: An Amazon Resource Name — a globally unique identifier for every AWS resource. Format: `arn:partition:service:region:account-id:resource`. Used in IAM policies to specify exactly what resource a permission applies to.

**Q: What is the difference between Spot, On-Demand, and Reserved Instances?**
A: On-Demand = pay per second, no commitment, most expensive. Reserved = 1 or 3 year commitment, up to 72% savings, best for steady workloads. Spot = up to 90% savings but AWS can reclaim with 2-minute notice, best for fault-tolerant batch/stateless workloads.

**Q: Which AWS services are global (not region-specific)?**
A: IAM (users, roles, policies), Route53 (DNS), CloudFront (CDN), WAF (when attached to CloudFront), AWS Organizations. Everything else is regional.

**Q: What is an SCP (Service Control Policy)?**
A: An organization-level policy that acts as a permission boundary for all accounts in an AWS Organization. SCPs restrict what actions are possible in member accounts — even if an IAM policy allows it. SCPs do not grant permissions; they only restrict.

**Q: What is the difference between Savings Plans and Reserved Instances?**
A: Savings Plans are more flexible — Compute Savings Plans apply to EC2, Lambda, and Fargate across any instance family, size, OS, or region. EC2 Instance Savings Plans apply to a specific instance family in a region. Reserved Instances are less flexible (locked to specific instance type, region) but offer similar savings.

**Q: How many AZs should you deploy across for production?**
A: Minimum 2 AZs for high availability. 3 AZs is better — if one fails with 2-AZ you are at 50% capacity; with 3 AZs you are at 67%. AWS recommends 3 AZs for production critical systems.

**Q: What happens to an EC2 Spot Instance when AWS needs the capacity back?**
A: AWS sends a 2-minute interruption notice (via instance metadata and EventBridge). The instance then gets stopped or terminated. Best practices: use Spot with Auto Scaling groups and Spot Fleet across multiple instance types and AZs for resilience.

**Q: What is the difference between CloudFront and Global Accelerator?**
A: CloudFront is a CDN — it caches content (HTTP/HTTPS) at edge locations close to users. Global Accelerator uses the AWS backbone network to route TCP/UDP traffic to the nearest healthy endpoint. CloudFront is for cacheable web content; Global Accelerator is for non-cacheable traffic needing low-latency routing (APIs, gaming, IoT).
