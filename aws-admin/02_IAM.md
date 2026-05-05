# Chapter 2: IAM — Identity and Access Management
## Users, Groups, Roles, Policies, and Security Best Practices

---

## 2.1 What is IAM?

IAM controls **who** can do **what** on **which** AWS resources.

```
┌──────────────────────────────────────────────────────────┐
│                    IAM COMPONENTS                        │
│                                                          │
│  WHO (Identity)          WHAT (Action)    WHICH (Resource)│
│  ─────────────           ─────────────    ───────────────│
│  User (person)           s3:GetObject     arn:aws:s3:::  │
│  Group (collection)      ec2:StartInstance  my-bucket/*  │
│  Role (assumed identity) lambda:Invoke    arn:aws:lambda:│
│  Service (AWS service)   dynamodb:PutItem   ...          │
│                                                          │
│  All controlled by → POLICIES (JSON documents)           │
└──────────────────────────────────────────────────────────┘
```

**IAM is global** — not region-specific. Users and roles work across all regions.

---

## 2.2 IAM Users

A **User** represents a person or application. Users have long-term credentials.

```bash
# Create a user
aws iam create-user --user-name john-doe

# Create access keys (for CLI/SDK use)
aws iam create-access-key --user-name john-doe

# Create login profile (for AWS Console)
aws iam create-login-profile \
  --user-name john-doe \
  --password "Temp@1234!" \
  --password-reset-required

# List users
aws iam list-users

# Delete user
aws iam delete-user --user-name john-doe
```

**Best practices for users:**
- Never use root account for day-to-day work
- One user per person (no shared accounts)
- Use IAM Identity Center (SSO) for human users in organisations
- Prefer roles over long-term access keys wherever possible

---

## 2.3 IAM Groups

A **Group** is a collection of users. Attach policies to groups, not individual users.

```bash
# Create group
aws iam create-group --group-name developers

# Add user to group
aws iam add-user-to-group \
  --user-name john-doe \
  --group-name developers

# Attach policy to group
aws iam attach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# List group members
aws iam get-group --group-name developers
```

```
Good group structure example:
┌─────────────────────────────────────────────────┐
│  Group: admins        → AdministratorAccess      │
│  Group: developers    → PowerUserAccess + custom │
│  Group: readonly      → ReadOnlyAccess            │
│  Group: billing       → Billing + Cost Explorer  │
└─────────────────────────────────────────────────┘
```

---

## 2.4 IAM Policies — The Core of IAM

A **Policy** is a JSON document defining permissions. Everything is **deny by default** — you must explicitly allow.

### Policy Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadOnMyBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket",
        "arn:aws:s3:::my-app-bucket/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Sid": "DenyDeleteEverywhere",
      "Effect": "Deny",
      "Action": "s3:DeleteObject",
      "Resource": "*"
    }
  ]
}
```

**Fields explained:**
- `Sid` — Statement ID, human-readable label (optional)
- `Effect` — `Allow` or `Deny`. Explicit Deny ALWAYS wins
- `Action` — AWS API action(s). Use `*` for all actions on a service
- `Resource` — ARN(s) the action applies to. `*` = all resources
- `Condition` — Optional extra constraints

### Policy Evaluation Logic

```
Request comes in
      │
      ▼
Is there an explicit DENY?  ──Yes──► DENY (always wins)
      │ No
      ▼
Is there an explicit ALLOW? ──Yes──► ALLOW
      │ No
      ▼
     DENY (implicit default)
```

### Policy Types

```
┌──────────────────────────────────────────────────────────┐
│                  POLICY TYPES                            │
├────────────────────┬─────────────────────────────────────┤
│ AWS Managed        │ Pre-built by AWS. Read-only.         │
│                    │ e.g., AmazonS3FullAccess,            │
│                    │ AmazonEC2ReadOnlyAccess              │
├────────────────────┼─────────────────────────────────────┤
│ Customer Managed   │ You create and own them.             │
│                    │ More flexible, reusable              │
├────────────────────┼─────────────────────────────────────┤
│ Inline             │ Embedded in a single user/role.      │
│                    │ Not reusable. Avoid in practice.     │
├────────────────────┼─────────────────────────────────────┤
│ Service Control    │ Org-level guardrails. Apply to       │
│ Policies (SCPs)    │ entire accounts. Even overrides      │
│                    │ admin. Used in AWS Organizations.    │
├────────────────────┼─────────────────────────────────────┤
│ Resource-based     │ Attached TO the resource (S3 bucket │
│                    │ policy, SQS queue policy, etc.)      │
└────────────────────┴─────────────────────────────────────┘
```

### Common AWS Managed Policies

| Policy Name | Grants |
|------------|--------|
| `AdministratorAccess` | Full access to everything |
| `PowerUserAccess` | Full access except IAM management |
| `ReadOnlyAccess` | Read-only to all services |
| `AmazonS3FullAccess` | Full S3 access |
| `AmazonEC2ReadOnlyAccess` | Read EC2 resources |
| `AmazonDynamoDBFullAccess` | Full DynamoDB |
| `AWSLambdaBasicExecutionRole` | Write CloudWatch Logs (for Lambda) |
| `AmazonECSTaskExecutionRolePolicy` | For ECS task execution |

---

## 2.5 IAM Roles

A **Role** is an identity that can be **assumed** — no long-term credentials. Think of it as a temporary costume.

```
┌──────────────────────────────────────────────────────────┐
│                   ROLE USE CASES                         │
│                                                          │
│  1. AWS Service assumes role:                            │
│     EC2 instance → assumes role → can read S3            │
│     Lambda → assumes role → can write DynamoDB           │
│                                                          │
│  2. Cross-account access:                                │
│     Account A user → assumes role in Account B           │
│     → accesses Account B resources                       │
│                                                          │
│  3. Federated / SSO users:                               │
│     Google/Microsoft users → assume role via SAML        │
│     → access AWS Console                                 │
│                                                          │
│  4. Applications (EC2 instance profiles, ECS task roles) │
└──────────────────────────────────────────────────────────┘
```

### Role Anatomy: Two Policies

Every role has **two** policies:

```json
// 1. TRUST POLICY — WHO can assume this role
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "lambda.amazonaws.com"   // Lambda can assume this role
    },
    "Action": "sts:AssumeRole"
  }]
}

// 2. PERMISSIONS POLICY — WHAT the role can do
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["dynamodb:PutItem", "dynamodb:GetItem"],
    "Resource": "arn:aws:dynamodb:us-east-1:123456:table/users"
  }]
}
```

### Creating and Using Roles

```bash
# Create role with trust policy
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document file://trust-policy.json

# Attach permissions
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Assume a role manually (get temporary credentials)
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/my-role \
  --role-session-name my-session

# Output: AccessKeyId, SecretAccessKey, SessionToken (expire in ~1hr)
```

### Cross-Account Role

```json
// Trust policy — Account A user (111111) can assume this role in Account B (222222)
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::111111111111:user/john"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:ExternalId": "unique-external-id-12345"  // Extra security
      }
    }
  }]
}
```

---

## 2.6 IAM Policy Conditions

Conditions add context-based restrictions.

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*",
      "Condition": {
        // Only allow from specific IP range
        "IpAddress": {
          "aws:SourceIp": ["203.0.113.0/24", "198.51.100.0/24"]
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        // Deny everything if MFA is not present
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*",
      "Condition": {
        // Only allow in specific region
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    }
  ]
}
```

### Common Condition Keys

| Key | Example Use |
|-----|-------------|
| `aws:RequestedRegion` | Restrict to specific regions |
| `aws:SourceIp` | Allow only from office IP |
| `aws:MultiFactorAuthPresent` | Require MFA |
| `aws:PrincipalTag` | Match tag on user/role |
| `s3:prefix` | Restrict S3 paths |
| `ec2:Region` | Restrict EC2 region |
| `sts:ExternalId` | Secure cross-account role assumption |

---

## 2.7 IAM Resource-Based Policies

Some resources can have policies attached directly to them (unlike identity policies attached to users/roles).

```json
// S3 Bucket Policy — allow public read
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",               // Anyone
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-public-website/*"
  }]
}

// S3 Bucket Policy — allow only from specific VPC endpoint
{
  "Statement": [{
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
    "Condition": {
      "StringNotEquals": {
        "aws:sourceVpce": "vpce-0abc123456789"  // Only from this VPC endpoint
      }
    }
  }]
}
```

**Services supporting resource-based policies:**
S3 buckets, SQS queues, SNS topics, Lambda functions, KMS keys, ECR repositories, Secrets Manager secrets

---

## 2.8 IAM Security Best Practices

```
┌────────────────────────────────────────────────────────────┐
│              IAM SECURITY CHECKLIST                        │
├────────────────────────────────────────────────────────────┤
│ ✅ Lock away the root account — enable MFA on root         │
│ ✅ Never use root for daily operations                     │
│ ✅ Delete / never create root access keys                  │
│ ✅ Enable MFA for all IAM users with console access        │
│ ✅ Use IAM roles for applications — not access keys        │
│ ✅ Follow least privilege — grant minimum needed           │
│ ✅ Use groups for permissions — not individual users       │
│ ✅ Rotate access keys every 90 days                        │
│ ✅ Review IAM Access Advisor for unused permissions        │
│ ✅ Use IAM Access Analyzer to find external access         │
│ ✅ Set password policy (length, complexity, rotation)      │
│ ✅ Use AWS Organizations SCPs as guardrails                │
└────────────────────────────────────────────────────────────┘
```

```bash
# Check IAM credential report (last login, key age, MFA status)
aws iam generate-credential-report
aws iam get-credential-report --output text \
  --query Content | base64 --decode

# Check Access Advisor (services used by a user/role)
aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:user/john

# Set account password policy
aws iam update-account-password-policy \
  --minimum-password-length 14 \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --require-numbers \
  --require-symbols \
  --allow-users-to-change-password \
  --max-password-age 90 \
  --password-reuse-prevention 5
```

---

## 2.9 AWS STS — Security Token Service

STS issues **temporary** security credentials (access key + secret + session token). Credentials expire (default 1 hour, max 12 hours).

```bash
# Assume a role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME \
  --role-session-name my-session \
  --duration-seconds 3600

# Get Federation Token (for web identity)
aws sts get-federation-token \
  --name my-federation-user \
  --policy file://policy.json

# Decode authorization message on AccessDenied errors
aws sts decode-authorization-message \
  --encoded-message <encoded-message-from-error>
```

---

## 2.10 IAM Identity Center (SSO)

For organisations with many accounts, IAM Identity Center (formerly SSO) centralises access.

```
┌──────────────────────────────────────────────────────────┐
│             IAM IDENTITY CENTER FLOW                     │
│                                                          │
│  External Identity Provider (e.g., Microsoft AD)        │
│               │                                          │
│               ▼                                          │
│      IAM Identity Center                                 │
│      ┌─────────────────────────────┐                     │
│      │ Permission Sets (like roles)│                     │
│      │ - AdminAccess               │                     │
│      │ - DeveloperAccess           │                     │
│      │ - ReadOnly                  │                     │
│      └──────────────┬──────────────┘                     │
│                     │                                    │
│     ┌───────────────┼───────────────┐                   │
│     ▼               ▼               ▼                   │
│  Dev Account   Staging Account  Prod Account            │
│  (123456)      (234567)         (345678)                │
└──────────────────────────────────────────────────────────┘

User logs in once → picks account → assumes permission set
No long-term credentials anywhere
```

---

## 2.11 IAM Policies: Real Examples

### Lambda execution policy (least privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/my-function:*"
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/users",
        "arn:aws:dynamodb:us-east-1:123456789012:table/users/index/*"
      ]
    },
    {
      "Sid": "SecretsManagerRead",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-app/db-password-*"
    }
  ]
}
```

### Developer policy (all dev resources, no prod)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "s3:*",
        "lambda:*",
        "dynamodb:*",
        "logs:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Environment": "prod"
        }
      }
    }
  ]
}
```

---

## 2.12 Interview Questions

**Q: What's the difference between an IAM User and an IAM Role?**
> A user has permanent credentials (password + access keys) and represents a person or application. A role has no permanent credentials — it's assumed temporarily by a service, user, or application and provides short-lived credentials via STS. Best practice is to use roles for everything, including applications on EC2 or Lambda.

**Q: What happens if an identity has both an Allow and a Deny for the same action?**
> Explicit Deny always wins. Even if you have AdministratorAccess on your user, an explicit Deny on the same resource will block it. This is the core of IAM evaluation logic.

**Q: How do you give an EC2 instance permission to read S3?**
> Create an IAM role with a trust policy allowing EC2 to assume it, attach an S3 read policy to the role, then attach the role to the EC2 instance as an instance profile. The EC2 instance automatically gets temporary credentials via the instance metadata service — no access keys needed in code.

**Q: What is the principle of least privilege?**
> Grant only the minimum permissions needed to perform the task — nothing more. Start with no permissions and add only what's required. Use IAM Access Advisor to see what permissions are actually being used and remove unused ones.
