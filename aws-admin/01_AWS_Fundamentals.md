# Chapter 1: AWS Fundamentals
## Global Infrastructure, Service Model & Getting Started

---

## 1.1 What is AWS?

Amazon Web Services is a cloud platform offering 200+ services — compute, storage, databases, networking, AI/ML, security, and more — hosted in data centres worldwide. Instead of buying and managing physical servers, you rent what you need and pay per use.

```
Traditional IT                    AWS Cloud
──────────────                    ─────────
Buy servers upfront          →    Pay per second/hour/request
Provision takes weeks        →    Ready in minutes
Fixed capacity               →    Scale up or down instantly
You manage hardware          →    AWS manages hardware
Single location              →    Global in minutes
High capital expense         →    Operational expense
```

---

## 1.2 Global Infrastructure

### Regions

A **Region** is a geographic area containing multiple, isolated data centres.

```
Major AWS Regions:
┌────────────────────────────────────────────────────────────┐
│  US East (N. Virginia)    us-east-1    ← Most services     │
│  US East (Ohio)           us-east-2                        │
│  US West (Oregon)         us-west-2                        │
│  Europe (Ireland)         eu-west-1                        │
│  Europe (Frankfurt)       eu-central-1                     │
│  Asia Pacific (Singapore) ap-southeast-1                   │
│  Asia Pacific (Mumbai)    ap-south-1                       │
│  Asia Pacific (Tokyo)     ap-northeast-1                   │
│  South America (São Paulo) sa-east-1                       │
└────────────────────────────────────────────────────────────┘
```

**How to choose a region:**
- **Latency** — pick closest to your users
- **Compliance** — data residency laws (GDPR → eu-west-1)
- **Service availability** — not all services in all regions
- **Price** — varies by region (us-east-1 usually cheapest)

### Availability Zones (AZs)

Each region has 2–6 **Availability Zones** — physically separate data centres with independent power, cooling, and networking.

```
Region: us-east-1
┌─────────────────────────────────────────────┐
│  AZ-1a          AZ-1b          AZ-1c        │
│  ┌──────┐       ┌──────┐       ┌──────┐     │
│  │Data  │       │Data  │       │Data  │     │
│  │Centre│       │Centre│       │Centre│     │
│  └──────┘       └──────┘       └──────┘     │
│     │               │               │       │
│     └───────────────┴───────────────┘       │
│              High-speed private link        │
└─────────────────────────────────────────────┘
```

**Best practice:** Deploy across at least 2 AZs for high availability.

### Edge Locations

100+ locations worldwide used by **CloudFront** (CDN) and **Route53** (DNS) for low-latency content delivery — separate from Regions/AZs.

### Local Zones

AWS infrastructure extensions placed closer to large cities for ultra-low latency (e.g., Los Angeles, Chicago).

---

## 1.3 AWS Service Categories

```
┌────────────────────────────────────────────────────────────────┐
│                    AWS SERVICE LANDSCAPE                       │
├─────────────────────┬──────────────────────────────────────────┤
│ CATEGORY            │ KEY SERVICES                             │
├─────────────────────┼──────────────────────────────────────────┤
│ Compute             │ EC2, Lambda, ECS, EKS, Fargate, Batch    │
│ Storage             │ S3, EBS, EFS, Glacier, Storage Gateway   │
│ Database            │ RDS, DynamoDB, Aurora, ElastiCache       │
│ Networking          │ VPC, Route53, CloudFront, API Gateway    │
│ Security            │ IAM, KMS, Secrets Manager, WAF, Shield  │
│ Messaging           │ SQS, SNS, Kinesis, EventBridge, SES     │
│ Monitoring          │ CloudWatch, CloudTrail, X-Ray, Config   │
│ Developer Tools     │ CodePipeline, CodeBuild, CodeDeploy     │
│ AI / ML             │ SageMaker, Rekognition, Comprehend      │
│ Analytics           │ Redshift, Athena, Glue, EMR             │
│ Management          │ CloudFormation, Systems Manager, OpsWorks│
│ Cost                │ Cost Explorer, Budgets, Trusted Advisor  │
└─────────────────────┴──────────────────────────────────────────┘
```

---

## 1.4 AWS Shared Responsibility Model

One of the most tested concepts in AWS exams.

```
┌────────────────────────────────────────────────────────────┐
│              SHARED RESPONSIBILITY MODEL                   │
├──────────────────────────┬─────────────────────────────────┤
│     YOUR responsibility  │     AWS responsibility           │
│     "Security IN cloud"  │     "Security OF cloud"          │
├──────────────────────────┼─────────────────────────────────┤
│ Your data                │ Physical data centres            │
│ Access management (IAM)  │ Hardware / networking            │
│ OS patching (on EC2)     │ Hypervisor / virtualisation      │
│ Application security     │ Managed service OS patches       │
│ Encryption of data       │ Global infrastructure            │
│ Firewall config (SGs)    │ Compliance certifications        │
│ Network config           │ (SOC 2, ISO 27001, etc.)         │
└──────────────────────────┴─────────────────────────────────┘

EC2 = more YOUR responsibility (you patch the OS)
S3  = more AWS responsibility (AWS manages the storage infra)
RDS = mixed (AWS patches DB engine, you manage access & data)
```

---

## 1.5 AWS Account Structure

```
┌──────────────────────────────────────────────────────┐
│                 AWS ORGANIZATION                     │
│  ┌───────────────────────────────────────────────┐   │
│  │          Management (Root) Account            │   │
│  │  • Pays all bills                             │   │
│  │  • Applies Service Control Policies (SCPs)   │   │
│  └───────────────┬───────────────────────────────┘   │
│                  │                                    │
│        ┌─────────┴──────────┐                        │
│        ▼                    ▼                        │
│  ┌───────────┐        ┌───────────┐                  │
│  │ Dev       │        │ Prod      │                  │
│  │ Account   │        │ Account   │                  │
│  │           │        │           │                  │
│  │ dev-*     │        │ prod-*    │                  │
│  │ resources │        │ resources │                  │
│  └───────────┘        └───────────┘                  │
└──────────────────────────────────────────────────────┘
```

**Best practice:** Separate AWS accounts for dev / staging / prod.

---

## 1.6 AWS CLI Essentials

```bash
# ── CONFIGURE ─────────────────────────────────────────────────
aws configure                          # Interactive setup
aws configure list                     # Show current config
aws configure list-profiles            # Show all profiles

# Multiple profiles
aws configure --profile prod
aws s3 ls --profile prod               # Use specific profile

# ── IDENTITY ──────────────────────────────────────────────────
aws sts get-caller-identity            # Who am I?
aws iam get-user                       # Current IAM user info

# ── REGIONS ───────────────────────────────────────────────────
aws ec2 describe-regions               # List all regions
aws --region eu-west-1 s3 ls          # Override region per command

# ── OUTPUT FORMATS ────────────────────────────────────────────
aws ec2 describe-instances --output table    # Human-readable
aws ec2 describe-instances --output json     # Default
aws ec2 describe-instances --output text     # TSV

# ── FILTERING OUTPUT (JMESPath) ────────────────────────────────
aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType]" \
  --output table

# Filter by tag
aws ec2 describe-instances \
  --filters "Name=tag:Environment,Values=prod" \
  --query "Reservations[*].Instances[*].InstanceId"

# ── PAGINATION ────────────────────────────────────────────────
aws s3api list-objects-v2 \
  --bucket my-bucket \
  --max-items 100 \
  --page-size 50

# Automatic pagination (CLI handles it)
aws ec2 describe-instances --no-paginate
```

---

## 1.7 AWS Pricing Model

```
┌─────────────────────────────────────────────────────────┐
│               AWS PRICING PRINCIPLES                    │
├────────────────────┬────────────────────────────────────┤
│ Pay-as-you-go      │ No upfront, pay per second/GB/req  │
│ Save on commit     │ Reserved Instances: up to 72% off  │
│ Volume discounts   │ More you use, less per unit         │
│ Free tier          │ 12 months free + always free       │
└────────────────────┴────────────────────────────────────┘

EC2 Pricing Models:
┌──────────────────┬──────────────────────────────────────┐
│ On-Demand        │ Pay per second. Most expensive.       │
│                  │ Use for: unpredictable workloads      │
├──────────────────┼──────────────────────────────────────┤
│ Reserved (1-3yr) │ Up to 72% cheaper than On-Demand     │
│                  │ Use for: steady-state production      │
├──────────────────┼──────────────────────────────────────┤
│ Savings Plans    │ Commit to $/hour for 1-3yr, flexible  │
│                  │ Use for: mix of EC2/Lambda/Fargate    │
├──────────────────┼──────────────────────────────────────┤
│ Spot             │ Up to 90% off. Can be terminated.    │
│                  │ Use for: batch jobs, stateless work  │
├──────────────────┼──────────────────────────────────────┤
│ Dedicated Host   │ Physical server for compliance       │
└──────────────────┴──────────────────────────────────────┘
```

---

## 1.8 Key Exam / Interview Concepts

| Concept | Answer |
|---------|--------|
| How many AZs minimum for HA? | 2 |
| Which service is global (not regional)? | IAM, Route53, CloudFront |
| Where does CloudFront cache? | Edge locations |
| Who patches the OS on EC2? | You (customer) |
| Who patches the OS on RDS? | AWS |
| What is an ARN? | Amazon Resource Name — unique ID for every resource |
| Format of ARN | `arn:aws:service:region:account-id:resource` |

---

## 1.9 ARN Format

Every AWS resource has a unique ARN:

```
arn:partition:service:region:account-id:resource

Examples:
arn:aws:iam::123456789012:user/john
arn:aws:s3:::my-bucket                     (S3 is global — no region/account)
arn:aws:lambda:us-east-1:123456789012:function:my-function
arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123
arn:aws:rds:us-east-1:123456789012:db:my-database
arn:aws:dynamodb:us-east-1:123456789012:table/users
```

**ARN wildcards in policies:**
```json
"Resource": "arn:aws:s3:::my-bucket/*"      // All objects in bucket
"Resource": "arn:aws:dynamodb:*:*:table/*"  // All DynamoDB tables in any region
```
