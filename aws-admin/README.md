# AWS Administration — From Basics to Advanced
## A Complete Book-Style Guide Covering Most AWS Services

---

## Who This Guide Is For

- Developers preparing for AWS Solutions Architect / Developer / SysOps exams
- Backend engineers who need to understand AWS deeply for production systems
- Anyone moving from "I've used AWS" to "I can architect and operate AWS"

---

## Book Structure

| File | Chapter | Topics |
|------|---------|--------|
| [01_AWS_Fundamentals.md](01_AWS_Fundamentals.md) | 1 | Global infrastructure, regions, AZs, service categories, AWS CLI, IAM basics |
| [02_IAM.md](02_IAM.md) | 2 | Users, Groups, Roles, Policies, STS, MFA, best practices, trust policies |
| [03_Compute_EC2.md](03_Compute_EC2.md) | 3 | EC2 types, AMI, EBS volumes, User Data, Auto Scaling Groups, Load Balancers |
| [04_Storage.md](04_Storage.md) | 4 | S3 (all features), EBS, EFS, FSx, Glacier, Storage Gateway, Transfer Family |
| [05_Networking_VPC.md](05_Networking_VPC.md) | 5 | VPC, subnets, route tables, IGW, NAT, SGs, NACLs, peering, PrivateLink, VPN |
| [06_Databases.md](06_Databases.md) | 6 | RDS, Aurora, DynamoDB, ElastiCache, Redshift, Neptune, DocumentDB |
| [07_Serverless.md](07_Serverless.md) | 7 | Lambda, API Gateway, Step Functions, EventBridge, SAM |
| [08_Containers.md](08_Containers.md) | 8 | ECS, Fargate, EKS, ECR, App Mesh, service discovery |
| [09_Messaging.md](09_Messaging.md) | 9 | SQS, SNS, SES, Kinesis, MSK (Kafka), EventBridge patterns |
| [10_Monitoring.md](10_Monitoring.md) | 10 | CloudWatch (Metrics, Logs, Alarms, Dashboards), CloudTrail, X-Ray, AWS Config |
| [11_Security_Services.md](11_Security_Services.md) | 11 | KMS, Secrets Manager, WAF, Shield, GuardDuty, Security Hub, Macie, Inspector |
| [12_Cost_Governance.md](12_Cost_Governance.md) | 12 | Cost Explorer, Budgets, Savings Plans, Trusted Advisor, Organizations, Control Tower |
| [13_Developer_Tools.md](13_Developer_Tools.md) | 13 | CodeCommit, CodeBuild, CodeDeploy, CodePipeline, Cloud9, CloudShell |
| [14_Advanced_Architecture.md](14_Advanced_Architecture.md) | 14 | Well-Architected Framework, disaster recovery, multi-region, high availability |

---

## Core Mental Model

```
┌──────────────────────────────────────────────────────────────────┐
│                     AWS GLOBAL INFRASTRUCTURE                    │
│                                                                  │
│  ┌──────────────── REGION (e.g., us-east-1) ───────────────────┐ │
│  │                                                              │ │
│  │  ┌─── AZ-1 (us-east-1a) ───┐  ┌─── AZ-2 (us-east-1b) ───┐ │ │
│  │  │                         │  │                         │ │ │
│  │  │  ┌──────────────────┐   │  │  ┌──────────────────┐  │ │ │
│  │  │  │  Your Resources  │   │  │  │  Your Resources  │  │ │ │
│  │  │  │  EC2, RDS, etc.  │   │  │  │  EC2, RDS, etc.  │  │ │ │
│  │  │  └──────────────────┘   │  │  └──────────────────┘  │ │ │
│  │  └─────────────────────────┘  └────────────────────────┘ │ │
│  │                                                            │ │
│  │  Global services (same everywhere): IAM, Route53, CloudFront│ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Reference: AWS Service Categories

```
COMPUTE          STORAGE          DATABASE         NETWORKING
────────         ───────          ────────         ──────────
EC2              S3               RDS              VPC
Lambda           EBS              DynamoDB         Route 53
ECS / Fargate    EFS              Aurora           CloudFront
EKS              Glacier          ElastiCache      API Gateway
Elastic Beanstalk FSx             Redshift         Direct Connect

SECURITY         MESSAGING        MONITORING       DEVELOPER
────────         ─────────        ──────────       ─────────
IAM              SQS              CloudWatch       CodeCommit
KMS              SNS              CloudTrail       CodeBuild
Secrets Manager  Kinesis          X-Ray            CodeDeploy
WAF / Shield     EventBridge      AWS Config       CodePipeline
GuardDuty        SES              Trusted Advisor  Cloud9
```

## Prerequisites

```bash
# Install AWS CLI v2
# Windows:
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Mac/Linux:
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region: us-east-1
# Default output format: json

# Verify
aws sts get-caller-identity
```
