# AWS CloudFormation — From Basics to Advanced
## A Complete Book-Style Guide with Real-World Templates

---

## What This Guide Covers

This guide teaches AWS CloudFormation end-to-end — from your first YAML template to
production-grade multi-stack architectures. Every chapter builds on the previous one
and includes working, copy-paste-ready templates.

---

## Book Structure

| File | Chapter | Topics |
|------|---------|--------|
| [01_Introduction.md](01_Introduction.md) | 1 | What is CloudFormation, how it works, key concepts, CLI setup |
| [02_Template_Anatomy.md](02_Template_Anatomy.md) | 2 | All template sections, every intrinsic function, pseudo-parameters |
| [03_Core_Resources.md](03_Core_Resources.md) | 3 | S3, IAM roles & policies, EC2 instances, Security Groups |
| [04_Networking.md](04_Networking.md) | 4 | VPC, public/private subnets, NAT Gateway, Route Tables, Bastion host |
| [05_Serverless_Stack.md](05_Serverless_Stack.md) | 5 | Lambda, API Gateway (HTTP & REST), DynamoDB, complete serverless app |
| [06_Container_Stack.md](06_Container_Stack.md) | 6 | ECR, ECS Cluster, Fargate tasks, ALB, Service Auto Scaling |
| [07_Databases.md](07_Databases.md) | 7 | RDS (PostgreSQL/MySQL), DynamoDB advanced, ElastiCache Redis |
| [08_Advanced_Features.md](08_Advanced_Features.md) | 8 | Nested stacks, cross-stack refs, Custom Resources, Macros, StackSets |
| [09_CICD_Deployment.md](09_CICD_Deployment.md) | 9 | Change sets, drift detection, GitHub Actions, rollback strategies |
| [10_Projects.md](10_Projects.md) | 10 | 3 complete projects: REST API, ECS microservices, multi-env platform |

---

## How to Use This Guide

### Beginner Path
Read chapters 1 → 2 → 3 → 4 → 5 in order.

### Intermediate Path
If you know YAML and basic AWS, start at chapter 2, skim 3–4, focus on 5–7.

### Advanced / Interview Prep
Jump to chapters 8–10 for nested stacks, custom resources, and full project templates.

---

## Prerequisites

```bash
# Install AWS CLI
pip install awscli
aws configure   # Set access key, secret, region

# Verify
aws cloudformation list-stacks

# Optional: install cfn-lint for template validation
pip install cfn-lint
cfn-lint template.yaml
```

---

## Core Mental Model

```
┌─────────────────────────────────────────────────────────────┐
│                  CLOUDFORMATION FLOW                        │
│                                                             │
│  You write          AWS reads           AWS creates         │
│  ──────────         ─────────           ────────────        │
│  template.yaml  →   CloudFormation  →   Real Resources      │
│  (YAML / JSON)      Service             (S3, Lambda,        │
│                                          RDS, etc.)         │
│                                                             │
│  Stack = one deployed instance of a template                │
│  Change Set = preview of what will change before applying   │
│  Stack Set = deploy same stack to multiple accounts/regions │
└─────────────────────────────────────────────────────────────┘
```
