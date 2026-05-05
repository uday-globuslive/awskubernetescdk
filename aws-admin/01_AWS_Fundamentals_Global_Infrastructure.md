# Chapter 1: AWS Fundamentals & Global Infrastructure

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 1**: Monitoring, Logging, and Remediation (partial)
- **Domain 5**: Networking and Content Delivery (partial)
- **Foundation**: All domains build on these fundamentals

---

## 1.1 What is AWS?

Amazon Web Services (AWS) is the world's most comprehensive and broadly adopted cloud platform, offering over 200 fully featured services from data centers globally. It follows a **pay-as-you-go** model — you pay only for what you use, with no upfront costs or long-term contracts (unless you choose Reserved Instances or Savings Plans).

### Why Cloud Computing?
| Traditional On-Premises | AWS Cloud |
|------------------------|-----------|
| High capital expenditure (CapEx) | Operational expenditure (OpEx) |
| Long procurement cycles (weeks/months) | Provision resources in minutes |
| Capacity guessing | Scale up or down on demand |
| Own and maintain hardware | AWS manages physical infrastructure |
| Single data center = single point of failure | Multi-AZ and Multi-Region built-in |
| Hard to go global | Deploy in 30+ regions worldwide |

### 6 Advantages of Cloud Computing (AWS Pillars)
1. **Trade capital expense for variable expense** — pay only for what you consume
2. **Benefit from massive economies of scale** — lower variable cost than on-premises
3. **Stop guessing capacity** — scale up/down within minutes
4. **Increase speed and agility** — new IT resources a click away
5. **Stop spending money running and maintaining data centers** — focus on projects
6. **Go global in minutes** — deploy in multiple regions instantly

---

## 1.2 AWS Global Infrastructure

AWS's global infrastructure is built around three core concepts: **Regions**, **Availability Zones (AZs)**, and **Edge Locations**.

```
AWS Global Infrastructure (as of 2025):
┌─────────────────────────────────────────────────────────────┐
│                    GLOBAL (Route 53, IAM, CloudFront CDN)   │
├─────────────────────────────────────────────────────────────┤
│  REGION (e.g., us-east-1)                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  AZ: us-east-1a    AZ: us-east-1b    AZ: us-east-1c  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │  Data Center│  │  Data Center│  │  Data Center│  │  │
│  │  │  (1-6 DCs)  │  │  (1-6 DCs)  │  │  (1-6 DCs)  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  EDGE LOCATIONS (400+ globally) — CloudFront, Route 53      │
└─────────────────────────────────────────────────────────────┘
```

### AWS Regions
- A **Region** is a physical location in the world with multiple, isolated, and physically separate AZs
- Currently **33+ regions** worldwide (us-east-1, eu-west-1, ap-southeast-1, etc.)
- **Each region is completely independent** — data does not leave a region unless explicitly configured
- You choose a region based on: **latency**, **data sovereignty/compliance**, **service availability**, **cost**

**Key Exam Regions:**
| Region Code | Location |
|-------------|----------|
| us-east-1 | N. Virginia (oldest, most services) |
| us-west-2 | Oregon |
| eu-west-1 | Ireland |
| ap-southeast-1 | Singapore |
| ap-northeast-1 | Tokyo |

### Availability Zones (AZs)
- Each region has **2–6 Availability Zones** (minimum 3 for most regions)
- Each AZ = one or more discrete data centers with redundant power, networking, and connectivity
- AZs within a region are **connected with high-bandwidth, low-latency networking** (under 1ms RTT)
- **Physically separated** by a meaningful distance (miles apart) — isolated from disasters
- AZs are the foundation for building **highly available** applications

> **SysOps Tip:** Always deploy across **at least 2 AZs** to achieve fault tolerance. The exam will test this constantly.

### Edge Locations & Points of Presence (PoPs)
- **400+ edge locations** and **13 regional edge caches** globally
- Used by **Amazon CloudFront** (CDN) and **Route 53** (DNS)
- Bring content closer to users, reducing latency
- **Not the same as AZs or Regions** — they only run edge services

### Local Zones
- Extensions of a Region placed closer to large population centers or industries
- Enable single-digit millisecond latency for specific geographic areas
- Use case: video streaming, gaming, real-time applications in cities not served by a full region
- Example: `us-east-1-bos-1` (Boston Local Zone)

### Wavelength Zones
- Deploy AWS compute and storage at the edge of 5G networks
- Use case: ultra-low latency mobile applications, AR/VR, IoT
- Partner with telecom providers (Verizon, Vodafone, etc.)

### AWS Outposts
- Fully managed service that extends AWS infrastructure to **your own data center**
- Run AWS services on-premises using the same AWS APIs, tools, hardware
- Rack (full or partial) delivered and installed by AWS
- Use case: regulatory requirements for on-premises, low-latency hybrid workloads

---

## 1.3 AWS Shared Responsibility Model

This is **critical for SysOps certification**. Understanding who is responsible for what is foundational.

```
┌─────────────────────────────────────────────────────────────────┐
│              CUSTOMER RESPONSIBILITY ("IN the cloud")           │
│                                                                 │
│  • Customer Data                                                │
│  • Platform, Applications, Identity & Access Management        │
│  • Operating System, Network & Firewall Configuration          │
│  • Client-side Data Encryption & Data Integrity Authentication  │
│  • Server-side Encryption (File System and/or Data)            │
│  • Network Traffic Protection (Encryption, Integrity, Identity) │
├─────────────────────────────────────────────────────────────────┤
│              AWS RESPONSIBILITY ("OF the cloud")                │
│                                                                 │
│  • Compute  • Storage  • Database  • Networking                 │
│  • Regions  • Availability Zones  • Edge Locations             │
│  (Hardware / AWS Global Infrastructure)                         │
└─────────────────────────────────────────────────────────────────┘
```

### Shared Responsibility by Service Type

| Service Type | AWS Manages | Customer Manages |
|--------------|-------------|-----------------|
| **EC2 (IaaS)** | Hypervisor, hardware, physical security | OS patches, network config, app, data, firewall rules |
| **RDS (PaaS)** | OS, DB engine patches, hardware, backups | DB settings, user access, data, network access |
| **Lambda (Serverless)** | Runtime, OS, infrastructure, scaling | Code, function config, IAM, dependencies |
| **S3 (Object Storage)** | Durability, hardware, infrastructure | Bucket policies, encryption, access control |
| **DynamoDB (Managed DB)** | Everything infrastructure | Data, access control, app-level encryption |

> **Exam Tip:** For EC2, you own the OS and everything above. For managed services (RDS, Lambda, S3), AWS takes more responsibility for the underlying platform.

---

## 1.4 AWS Service Categories Overview

```
┌──────────────────── AWS Service Universe ────────────────────┐
│                                                              │
│  COMPUTE         STORAGE            DATABASE                 │
│  • EC2           • S3               • RDS                   │
│  • Lambda        • EBS              • DynamoDB               │
│  • ECS/EKS       • EFS              • Aurora                 │
│  • Elastic       • Glacier          • ElastiCache            │
│    Beanstalk     • FSx              • Redshift               │
│  • Lightsail     • Storage Gateway  • DocumentDB             │
│                                                              │
│  NETWORKING      SECURITY           MONITORING               │
│  • VPC           • IAM              • CloudWatch             │
│  • Route 53      • KMS              • CloudTrail             │
│  • CloudFront    • WAF              • AWS Config             │
│  • Direct        • Shield           • X-Ray                  │
│    Connect       • GuardDuty        • EventBridge            │
│  • Global        • Macie            • Systems Manager        │
│    Accelerator   • Security Hub     • Trusted Advisor        │
│                                                              │
│  DEPLOYMENT      MESSAGING          MIGRATION                │
│  • CloudFormation• SQS              • Migration Hub          │
│  • CDK           • SNS              • DMS                    │
│  • Systems       • EventBridge      • DataSync               │
│    Manager       • SES              • Snowball               │
│  • Elastic       • Kinesis          • Transfer Family        │
│    Beanstalk                                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 1.5 AWS Account Structure & Organizations

### Single Account vs. Multi-Account
Most organizations use **multiple AWS accounts** for:
- Separation of environments (dev/staging/prod)
- Billing isolation
- Security blast radius reduction
- Compliance requirements

### AWS Organizations
AWS Organizations lets you **centrally manage and govern multiple AWS accounts**.

```
                    ┌────────────────┐
                    │ Management     │
                    │ Account (Root) │
                    └────────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │   OU:   │   │   OU:   │   │   OU:   │
        │Security │   │  Dev    │   │  Prod   │
        └────┬────┘   └────┬────┘   └────┬────┘
             │             │             │
        ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
        │ Account │   │ Account │   │ Account │
        │  Audit  │   │  Dev    │   │  Prod   │
        └─────────┘   └─────────┘   └─────────┘
```

**Key Concepts:**
- **Management Account** — the master account, owns the organization
- **Member Accounts** — accounts within the organization
- **Organizational Units (OUs)** — logical grouping of accounts
- **Service Control Policies (SCPs)** — guardrails applied to OUs or accounts (covered in IAM chapter)
- **Consolidated Billing** — single payment method for all accounts, volume discounts

```bash
# Create an organization
aws organizations create-organization --feature-set ALL

# Create an OU under root
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name "Production"

# Create a new member account
aws organizations create-account \
  --email prod@company.com \
  --account-name "Production-Account"

# Move account to OU
aws organizations move-account \
  --account-id 123456789012 \
  --source-parent-id $ROOT_ID \
  --destination-parent-id ou-xxxx-xxxxxxxx
```

---

## 1.6 AWS Support Plans

| Feature | Basic | Developer | Business | Enterprise On-Ramp | Enterprise |
|---------|-------|-----------|----------|-------------------|------------|
| Cost | Free | $29/mo | $100/mo | $5,500/mo | $15,000/mo |
| Tech Support | None | Business hours | 24/7 | 24/7 | 24/7 |
| Response (Critical) | N/A | N/A | 1 hour | 30 min | 15 min |
| TAM | No | No | No | Pool TAM | Dedicated TAM |
| Trusted Advisor | 7 checks | 7 checks | All checks | All checks | All checks |
| AWS Health API | No | No | Yes | Yes | Yes |

> **SysOps Exam Tip:** The exam tests which support plan provides specific features. Business plan = 24/7 support + all Trusted Advisor checks. Enterprise = TAM + Concierge.

---

## 1.7 AWS Pricing Fundamentals

### Pricing Principles
1. **Pay for what you use** — per-second/per-hour billing for most compute
2. **Pay less when you reserve** — Reserved Instances, Savings Plans (up to 72% savings)
3. **Pay less for more** — tiered pricing for S3 storage, data transfer
4. **No cost for data transfer INTO AWS** — egress charges apply

### Common Pricing Models
```
EC2 Pricing Options:
┌────────────────────────────────────────────────────────────────┐
│ ON-DEMAND    │ Standard rate, no commitment                    │
│              │ Best for: unpredictable workloads, short-term   │
├────────────────────────────────────────────────────────────────┤
│ RESERVED     │ 1 or 3-year commitment, up to 72% discount      │
│ INSTANCES    │ Best for: steady-state, predictable workloads   │
├────────────────────────────────────────────────────────────────┤
│ SAVINGS PLANS│ Flexible, hourly spend commitment, up to 66%    │
│              │ Best for: flexible workloads across services    │
├────────────────────────────────────────────────────────────────┤
│ SPOT         │ Unused capacity, up to 90% discount             │
│ INSTANCES    │ Best for: fault-tolerant, flexible workloads    │
├────────────────────────────────────────────────────────────────┤
│ DEDICATED    │ Physical server dedicated to you                │
│ HOSTS        │ Best for: compliance, licensing (BYOL)          │
└────────────────────────────────────────────────────────────────┘
```

### Free Tier
AWS offers a **12-month Free Tier** for new accounts:
- **EC2**: 750 hours/month of t2.micro or t3.micro
- **S3**: 5 GB standard storage, 20,000 GET requests, 2,000 PUT requests
- **RDS**: 750 hours/month of db.t2.micro, 20 GB storage
- **Lambda**: 1 million requests/month, 400,000 GB-seconds compute
- **CloudWatch**: 10 custom metrics, 10 alarms, 1 million API requests

**Always Free (no expiry):**
- DynamoDB: 25 GB storage, 25 WCU, 25 RCU
- Lambda: 1M requests/month
- CloudWatch: Basic monitoring (5-minute intervals)

---

## 1.8 AWS Management Interfaces

### AWS Management Console
- Web-based GUI at `console.aws.amazon.com`
- Each service has its own console page
- Supports multi-account access via AWS Organizations or IAM Identity Center

### AWS CLI
```bash
# Install AWS CLI v2 (Linux/Mac)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure with credentials
aws configure
# AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
# AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name: us-east-1
# Default output format: json

# Use profiles for multiple accounts
aws configure --profile production
aws s3 ls --profile production

# CLI pagination example
aws ec2 describe-instances \
  --max-items 100 \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags[?Key==`Name`].Value]' \
  --output table
```

### AWS SDKs
Available for: Python (boto3), JavaScript/TypeScript, Java, Go, .NET, Ruby, PHP, C++

```python
import boto3

# Initialize clients (best practice: use IAM roles, not hardcoded keys)
ec2 = boto3.client('ec2', region_name='us-east-1')
s3 = boto3.resource('s3')

# List running instances
response = ec2.describe_instances(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
)
for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        print(f"ID: {instance['InstanceId']}, Type: {instance['InstanceType']}")
```

### AWS CloudShell
- Browser-based shell in the AWS Console
- Pre-authenticated with your current IAM credentials
- Persistent 1 GB storage per region
- Pre-installed: AWS CLI, Python, Node.js, jq, git
- No charges for CloudShell itself

### Infrastructure as Code (IaC) — The SysOps Way
For SysOps, you should always prefer IaC over manual console actions:

| Tool | Language | Best For |
|------|----------|---------- |
| CloudFormation | YAML/JSON | AWS-native, no extra install |
| AWS CDK | Python/TypeScript | Programmatic, reusable constructs |
| Terraform | HCL | Multi-cloud, widely adopted |
| AWS SAM | YAML | Serverless applications |

---

## 1.9 AWS Well-Architected Framework

The AWS Well-Architected Framework provides architectural best practices across **6 pillars**:

```
        ┌─────────────────────────────────────┐
        │     AWS WELL-ARCHITECTED FRAMEWORK  │
        │                                     │
        │  1. OPERATIONAL EXCELLENCE          │
        │     Run and monitor systems         │
        │     Continuously improve processes  │
        │                                     │
        │  2. SECURITY                        │
        │     Protect information & systems   │
        │     Identity, detection, protection │
        │                                     │
        │  3. RELIABILITY                     │
        │     Recover from failures           │
        │     Scale to meet demand            │
        │                                     │
        │  4. PERFORMANCE EFFICIENCY          │
        │     Efficiently use resources       │
        │     Maintain efficiency as demand   │
        │                                     │
        │  5. COST OPTIMIZATION               │
        │     Avoid unnecessary costs         │
        │     Understand spending patterns    │
        │                                     │
        │  6. SUSTAINABILITY                  │
        │     Minimize environmental impact   │
        │     Reduce energy consumption       │
        └─────────────────────────────────────┘
```

### For SysOps Admins — Key Design Principles

**Operational Excellence:**
- Perform operations as code (IaC)
- Make frequent, small, reversible changes
- Anticipate failure (Game Days, chaos engineering)
- Learn from all operational events

**Reliability:**
- Automatically recover from failure
- Test recovery procedures
- Scale horizontally to increase aggregate workload availability
- Stop guessing capacity — use Auto Scaling
- Manage change through automation

---

## 1.10 AWS Health Dashboard

### Service Health Dashboard (public)
- `status.aws.amazon.com`
- Shows the general status of AWS services globally
- Anyone can view it — no AWS account needed

### Personal Health Dashboard (Account-specific)
- `health.aws.amazon.com`
- Shows events specific to YOUR resources and account
- Alerts for: scheduled maintenance, service disruptions affecting your resources
- Programmatic access via AWS Health API (Business/Enterprise support plans)

```bash
# View upcoming scheduled events (requires Business/Enterprise support)
aws health describe-events \
  --filter '{"eventStatusCodes":["upcoming"],"services":["EC2"]}' \
  --region us-east-1

# Get affected resources for an event
aws health describe-affected-resources \
  --filter '{"eventArns":["arn:aws:health:us-east-1::event/EC2/EC2_..."]}'
```

---

## 1.11 AWS Compliance & Data Residency

### Compliance Programs
AWS is compliant with many global standards:
- **SOC 1/2/3** — Service Organization Controls
- **ISO 27001, 27017, 27018** — Information Security Management
- **PCI DSS Level 1** — Payment Card Industry
- **HIPAA** — Health Insurance Portability and Accountability Act
- **FedRAMP** — Federal Risk and Authorization Management Program
- **GDPR** — General Data Protection Regulation (EU)

### AWS Artifact
- **Free** self-service portal for on-demand access to AWS compliance reports
- Download AWS ISO certifications, PCI DSS, SOC reports
- Sign and manage compliance agreements (e.g., BAA for HIPAA)

```bash
# List available compliance reports
aws artifact list-reports
```

### Data Residency
- By default, data stays in the region you deploy to
- AWS **never** moves customer data out of a region without explicit consent
- For sovereignty: use **AWS GovCloud** (US government requirements) or dedicated local zones
- **Data residency controls** via AWS Organizations Service Control Policies

---

## 1.12 Real-World Project: Multi-Account AWS Foundation

### Scenario
A fintech startup needs to set up AWS with proper governance from day one to pass SOC 2 audit within 6 months.

### Architecture

```
┌──────────────── AWS Organization ────────────────────────┐
│                                                          │
│  Management Account (billing, org management only)       │
│                                                          │
│  OU: Security                                            │
│  ├── Log Archive Account (CloudTrail, Config, VPC logs)  │
│  └── Security Tooling Account (GuardDuty, Security Hub)  │
│                                                          │
│  OU: Shared Services                                     │
│  └── Shared Services Account (DNS, CI/CD, Directory)     │
│                                                          │
│  OU: Workloads                                           │
│  ├── OU: Dev                                             │
│  │   └── Dev Account                                     │
│  ├── OU: Staging                                         │
│  │   └── Staging Account                                 │
│  └── OU: Prod                                            │
│      └── Production Account                              │
└──────────────────────────────────────────────────────────┘
```

### Implementation Steps

**Step 1: Create AWS Organization and enable all features**
```bash
# Enable all features in the organization
aws organizations enable-all-features

# Enable consolidated billing and service integration
aws organizations enable-aws-service-access \
  --service-principal cloudtrail.amazonaws.com
aws organizations enable-aws-service-access \
  --service-principal config.amazonaws.com
aws organizations enable-aws-service-access \
  --service-principal guardduty.amazonaws.com
aws organizations enable-aws-service-access \
  --service-principal securityhub.amazonaws.com
```

**Step 2: Enable CloudTrail organization-wide**
```bash
# Create organization trail in management account
aws cloudtrail create-trail \
  --name org-trail \
  --s3-bucket-name my-org-cloudtrail-logs \
  --is-organization-trail \
  --is-multi-region-trail \
  --include-global-service-events \
  --enable-log-file-validation

aws cloudtrail start-logging --name org-trail
```

**Step 3: Apply baseline SCP to all accounts**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeavingOrg",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    },
    {
      "Sid": "DenyRootUserActions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:root"
        }
      }
    },
    {
      "Sid": "DenyDisablingCloudTrail",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:DeleteTrail",
        "cloudtrail:StopLogging",
        "cloudtrail:UpdateTrail"
      ],
      "Resource": "*"
    }
  ]
}
```

**Step 4: AWS Control Tower (recommended for SysOps)**
```bash
# AWS Control Tower sets up a landing zone automatically:
# - Creates Log Archive and Audit accounts
# - Enables CloudTrail organization-wide
# - Enables AWS Config organization-wide
# - Applies baseline guardrails (SCPs)
# - Sets up IAM Identity Center (SSO)

# Enable via Console: AWS Control Tower -> Set up landing zone
# CLI is limited for Control Tower; use console or CloudFormation
```

---

## 1.13 Practice Questions

**Q1:** Your company is deploying a new application in AWS and must ensure that data never leaves the European Union due to GDPR requirements. What is the BEST approach?

**A:** Deploy all resources in EU regions (eu-west-1, eu-central-1, etc.). Use AWS Organizations Service Control Policies (SCPs) to deny the creation of resources outside approved EU regions. Enable CloudTrail to audit any API calls.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonEURegions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "eu-central-1",
            "eu-north-1",
            "eu-south-1"
          ]
        }
      }
    }
  ]
}
```

---

**Q2:** A company has applications deployed across 3 AZs in us-east-1. One AZ experiences a power outage. What is the EXPECTED behavior?

**A:** Traffic automatically routes to the remaining 2 healthy AZs via the load balancer. Auto Scaling replaces failed instances in healthy AZs. Services like RDS Multi-AZ automatically failover to a standby in another AZ (~60-120 seconds). The application remains available throughout if properly architected.

---

**Q3:** What is the difference between an AWS Region, an Availability Zone, and an Edge Location?

**A:**
- **Region**: A physical location with 2-6 AZs; all data stays in region by default; ~33 regions
- **Availability Zone**: One or more data centers with separate power/networking; for HA within a region
- **Edge Location**: PoPs for CDN (CloudFront) and DNS (Route 53); not for running applications; 400+ globally

---

**Q4:** Your company receives an email from AWS saying a specific EC2 instance will be retired next week. Where would you have seen this notification proactively?

**A:** **AWS Personal Health Dashboard** (health.aws.amazon.com). It shows events specific to your resources. For programmatic access, use the AWS Health API (requires Business or Enterprise support plan). You can also set up EventBridge rules to trigger Lambda or SNS notifications when Health events occur.

---

**Q5:** An auditor asks for documentation proving your AWS environment is PCI DSS compliant. What AWS service provides this?

**A:** **AWS Artifact** — provides on-demand access to AWS compliance reports and agreements. Download the PCI DSS Attestation of Compliance (AoC) and Responsibility Summary from the Artifact console or via the API.

---

## Key Terms for Exam

| Term | Definition |
|------|-----------|
| Region | Geographic area with 2+ AZs; data isolation boundary |
| AZ | Isolated data center cluster; foundation for HA |
| Edge Location | CDN PoP for CloudFront and Route 53 |
| Local Zone | Region extension for low-latency in specific cities |
| Outposts | AWS infrastructure in your data center |
| SLA | Service Level Agreement — AWS commits to uptime % |
| ARN | Amazon Resource Name — unique identifier for AWS resources |
| Management Account | Root account of an AWS Organization |
| SCP | Service Control Policy — guardrails for org accounts |
| Artifact | AWS compliance documentation portal |
