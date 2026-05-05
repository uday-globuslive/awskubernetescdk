# Chapter 2: IAM — Identity and Access Management
## Users, Groups, Roles, Policies, STS, Federation & Best Practices

---

## 2.1 IAM Overview

AWS Identity and Access Management (IAM) is the foundation of AWS security. It controls **who** (authentication) can do **what** (authorization) to **which resources** in your AWS account.

```
IAM Core Concepts:
┌─────────────────────────────────────────────────────────────────┐
│                        AWS ACCOUNT                              │
│                                                                 │
│  IDENTITIES (Who)          RESOURCES (What)                     │
│  ┌──────────────────┐      ┌──────────────────────────────────┐ │
│  │ Users            │      │ S3 buckets, EC2 instances,       │ │
│  │ Groups           │      │ Lambda functions, RDS databases, │ │
│  │ Roles            │  →   │ DynamoDB tables, SQS queues...   │ │
│  │ Service Accounts │      │                                  │ │
│  └──────────────────┘      └──────────────────────────────────┘ │
│           │                                                      │
│           │ evaluated against                                    │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     POLICIES                             │   │
│  │  {"Effect": "Allow/Deny", "Action": [...], "Resource":[]}│   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Key IAM Facts:**
- IAM is **global** — not region-specific; an IAM user in us-east-1 can access us-west-2
- **Root account** — has full access to everything; should be locked away and never used daily
- **New users have zero permissions** by default (explicit allow required)
- **Deny overrides Allow** — an explicit Deny anywhere in the chain always wins
- IAM is **eventually consistent** — changes may take a few seconds to propagate

---

## 2.2 IAM Users

An IAM user represents a **person or application** that needs long-term credentials to access AWS.

### Creating Users

```bash
# Create a user
aws iam create-user --user-name alice

# Create login profile (console access with password)
aws iam create-login-profile \
  --user-name alice \
  --password "Temp@Password123" \
  --password-reset-required

# Create access keys (programmatic access)
aws iam create-access-key --user-name alice
# Returns: AccessKeyId + SecretAccessKey (save SecretAccessKey — shown once!)

# List users
aws iam list-users \
  --query "Users[*].[UserName,UserId,CreateDate]" \
  --output table

# Get user details
aws iam get-user --user-name alice

# Add tags to user
aws iam tag-user \
  --user-name alice \
  --tags Key=Department,Value=Engineering Key=Team,Value=Backend

# Deactivate access key (instead of deleting when rotating)
aws iam update-access-key \
  --user-name alice \
  --access-key-id AKIAIOSFODNN7EXAMPLE \
  --status Inactive

# Delete access key
aws iam delete-access-key \
  --user-name alice \
  --access-key-id AKIAIOSFODNN7EXAMPLE

# Delete user (must remove all attached items first)
aws iam remove-user-from-group --user-name alice --group-name Developers
aws iam delete-login-profile --user-name alice
aws iam delete-user --user-name alice
```

### Access Key Best Practices

```
┌───────────────────────────────────────────────────────────────┐
│                ACCESS KEY BEST PRACTICES                      │
├───────────────────────────────────────────────────────────────┤
│ 1. Never use root account access keys                        │
│ 2. Rotate access keys every 90 days                         │
│ 3. Use IAM roles instead of access keys for EC2/Lambda      │
│ 4. Use AWS Secrets Manager or SSM Parameter Store for apps  │
│ 5. Enable CloudTrail to audit key usage                     │
│ 6. Delete unused keys (check last-used date)                │
│ 7. Never commit keys to source code or Git                  │
└───────────────────────────────────────────────────────────────┘

# Check when a key was last used
aws iam get-access-key-last-used \
  --access-key-id AKIAIOSFODNN7EXAMPLE

# Find users with old access keys (keys older than 90 days)
aws iam generate-credential-report
aws iam get-credential-report --query "Content" --output text | base64 -d | \
  awk -F, 'NR>1 && $9!="N/A" && $9<"2024-10-01" {print $1, $9}'
```

---

## 2.3 IAM Groups

Groups are collections of IAM users. Assign permissions to a group rather than individual users.

```
Organization structure → IAM Groups:
┌────────────────────────────────────────────────────────────────┐
│  Engineering Group          Operations Group                   │
│  ┌──────────────────┐       ┌──────────────────┐              │
│  │ Policies:        │       │ Policies:         │              │
│  │ - EC2 read/write │       │ - CloudWatch full │              │
│  │ - Lambda full    │       │ - Systems Manager │              │
│  │ - S3 full        │       │ - EC2 stop/start  │              │
│  └──────────────────┘       └──────────────────┘              │
│       ▲         ▲                   ▲                          │
│     Alice     Bob                 Carol                        │
│  (inherits Engineering)        (inherits Ops)                  │
│                                                                │
│  Alice also in: DBA-Group      (multiple groups allowed)       │
└────────────────────────────────────────────────────────────────┘
```

```bash
# Create group
aws iam create-group --group-name Developers

# Add policy to group (managed policy)
aws iam attach-group-policy \
  --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess

# Attach multiple policies
aws iam attach-group-policy --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess
aws iam attach-group-policy --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Add user to group
aws iam add-user-to-group --user-name alice --group-name Developers

# List users in group
aws iam get-group --group-name Developers \
  --query "Users[*].UserName" --output table

# List groups for user
aws iam list-groups-for-user --user-name alice \
  --query "Groups[*].GroupName" --output table

# List all policies attached to group
aws iam list-attached-group-policies --group-name Developers

# Remove user from group
aws iam remove-user-from-group --user-name alice --group-name Developers

# Delete group (remove users + policies first)
aws iam detach-group-policy --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess
aws iam delete-group --group-name Developers
```

---

## 2.4 IAM Policies — Deep Dive

A **policy** is a JSON document that defines permissions. It lists what actions are allowed or denied on what resources under what conditions.

### Policy Structure

```json
{
  "Version": "2012-10-17",          // Always use this version
  "Statement": [                    // Array of permission statements
    {
      "Sid": "AllowS3ReadAccess",   // Optional statement ID
      "Effect": "Allow",            // "Allow" or "Deny"
      "Action": [                   // What actions
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [                 // On what resources (ARNs)
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {                // Optional: when this applies
        "StringEquals": {
          "s3:prefix": ["logs/", "data/"]
        }
      }
    }
  ]
}
```

### Types of IAM Policies

```
┌──────────────────────────────────────────────────────────────────┐
│                    IAM POLICY TYPES                              │
├────────────────────┬─────────────────────────────────────────────┤
│ Type               │ Description                                 │
├────────────────────┼─────────────────────────────────────────────┤
│ AWS Managed        │ Created by AWS. Read-only. Common policies  │
│                    │ like AdministratorAccess, ReadOnlyAccess    │
├────────────────────┼─────────────────────────────────────────────┤
│ Customer Managed   │ You create and manage. Reusable across      │
│                    │ users/groups/roles in your account          │
├────────────────────┼─────────────────────────────────────────────┤
│ Inline             │ Embedded in a single user/group/role.       │
│                    │ Not reusable. Deleted with the identity     │
├────────────────────┼─────────────────────────────────────────────┤
│ Resource-based     │ Attached to a resource (S3 bucket policy,   │
│                    │ Lambda resource policy, KMS key policy)     │
├────────────────────┼─────────────────────────────────────────────┤
│ Permission         │ Set maximum permissions for IAM entities    │
│ Boundaries         │ (even if policy allows more, boundary caps) │
├────────────────────┼─────────────────────────────────────────────┤
│ SCP                │ Organization-level restriction on accounts  │
│ (Org level)        │ (see Chapter 1)                            │
├────────────────────┼─────────────────────────────────────────────┤
│ Session Policies   │ Passed during STS AssumeRole to restrict    │
│                    │ permissions further for that session only   │
└────────────────────┴─────────────────────────────────────────────┘
```

### Policy Evaluation Logic

```
Request comes in → AWS evaluates all applicable policies:

1. Explicit DENY anywhere → DENY (always wins)
   ↓
2. SCP (organization) allows? → If NO → DENY
   ↓
3. Resource-based policy → If ALLOW and cross-account → ALLOW
   ↓
4. Permission boundary set? → If YES, must also allow
   ↓
5. Identity-based policy → If ALLOW → ALLOW
   ↓
6. Default: IMPLICIT DENY

Summary:
  Explicit DENY > SCP > Resource policy > Permission boundary > Identity policy
  When in doubt: default is DENY
```

### Common Policies — Examples

```json
// Policy 1: S3 full access to specific bucket
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::my-team-bucket",
        "arn:aws:s3:::my-team-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListAllMyBuckets",
      "Resource": "*"
    }
  ]
}
```

```json
// Policy 2: EC2 start/stop/reboot (not terminate) in specific region
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

```json
// Policy 3: Deny delete actions (protect against accidental deletion)
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDeleteActions",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteBucket",
        "s3:DeleteObject",
        "dynamodb:DeleteTable",
        "rds:DeleteDBInstance",
        "ec2:TerminateInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

```json
// Policy 4: Allow Lambda to read from S3 and write to DynamoDB
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadFromS3",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-data-bucket",
        "arn:aws:s3:::my-data-bucket/*"
      ]
    },
    {
      "Sid": "WriteToDynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/Records"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

```json
// Policy 5: Force MFA before any action
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowViewAccountInfo",
      "Effect": "Allow",
      "Action": [
        "iam:GetAccountPasswordPolicy",
        "iam:ListVirtualMFADevices"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowManageOwnMFA",
      "Effect": "Allow",
      "Action": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ResyncMFADevice"
      ],
      "Resource": [
        "arn:aws:iam::*:mfa/${aws:username}",
        "arn:aws:iam::*:user/${aws:username}"
      ]
    },
    {
      "Sid": "DenyAllExceptListedIfNoMFA",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ResyncMFADevice",
        "iam:GetAccountPasswordPolicy",
        "iam:ListVirtualMFADevices",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

### Policy Conditions — Complete Reference

```json
// Condition Operators:
{
  "Condition": {
    // String comparison
    "StringEquals": {"aws:RequestedRegion": "us-east-1"},
    "StringNotEquals": {"aws:RequestedRegion": "cn-north-1"},
    "StringLike": {"s3:prefix": ["home/${aws:username}/*"]},
    "StringNotLike": {"aws:userid": "*:TemporaryUser*"},

    // Numeric comparison
    "NumericLessThan": {"s3:max-keys": "10"},
    "NumericGreaterThan": {"ec2:disk-iops": "1000"},

    // Date comparison
    "DateLessThan": {"aws:CurrentTime": "2025-12-31T23:59:59Z"},
    "DateGreaterThan": {"aws:CurrentTime": "2025-01-01T00:00:00Z"},

    // Boolean
    "Bool": {"aws:MultiFactorAuthPresent": "true"},
    "BoolIfExists": {"aws:SecureTransport": "true"},

    // IP address
    "IpAddress": {"aws:SourceIp": ["203.0.113.0/24", "198.51.100.0/24"]},
    "NotIpAddress": {"aws:SourceIp": "10.0.0.0/8"},

    // ARN comparison
    "ArnEquals": {"aws:SourceArn": "arn:aws:sns:us-east-1:123:my-topic"},
    "ArnLike": {"aws:SourceArn": "arn:aws:sns:us-east-1:123:*"},

    // Null check
    "Null": {"aws:TokenIssueTime": "false"},    // Key must NOT be null

    // Set operators (for multi-valued)
    "StringEqualsIfExists": {"ec2:Region": "us-east-1"}
  }
}
```

### Policy CLI Operations

```bash
# Create customer-managed policy
aws iam create-policy \
  --policy-name LambdaS3DynamoDB \
  --policy-document file://lambda-policy.json

# List all managed policies (AWS + customer)
aws iam list-policies --scope Local \  # Local = customer-managed
  --query "Policies[*].[PolicyName,PolicyId,AttachmentCount]" \
  --output table

# Get policy document
POLICY_ARN="arn:aws:iam::123456789012:policy/LambdaS3DynamoDB"
VERSION=$(aws iam get-policy --policy-arn $POLICY_ARN \
  --query "Policy.DefaultVersionId" --output text)
aws iam get-policy-version \
  --policy-arn $POLICY_ARN \
  --version-id $VERSION \
  --query "PolicyVersion.Document"

# Update policy (create new version)
aws iam create-policy-version \
  --policy-arn $POLICY_ARN \
  --policy-document file://updated-policy.json \
  --set-as-default

# Attach policy to user
aws iam attach-user-policy \
  --user-name alice \
  --policy-arn $POLICY_ARN

# Attach inline policy to user
aws iam put-user-policy \
  --user-name alice \
  --policy-name InlinePowerUser \
  --policy-document file://inline-policy.json

# Simulate policy (test without running)
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:user/alice \
  --action-names s3:GetObject ec2:TerminateInstances \
  --resource-arns "arn:aws:s3:::my-bucket/*" "arn:aws:ec2:us-east-1:123:instance/*" \
  --query "EvaluationResults[*].[ActionName,EvalDecision]" \
  --output table
```

---

## 2.5 IAM Roles — Complete Guide

A **role** is an IAM identity that can be assumed by:
- AWS services (EC2, Lambda, ECS tasks)
- IAM users in the same or different account (cross-account)
- External identities (SAML federation, OIDC/web identity federation)

Unlike users, roles have **no long-term credentials** — they issue temporary security credentials (STS tokens) valid for 15 minutes to 12 hours.

```
Role Assumption Flow:
┌──────────────┐     AssumeRole()    ┌──────────────────────────┐
│  EC2 Instance│ ────────────────────► │ AWS STS Service          │
│  (or user,   │                      │                          │
│  Lambda, etc)│ ◄──────────────────── │ Returns temporary:       │
└──────────────┘   Temp credentials   │  • AccessKeyId           │
                                      │  • SecretAccessKey       │
                                      │  • SessionToken          │
                                      │  • Expiration            │
                                      └──────────────────────────┘
```

### Role Components

```
Role = Trust Policy + Permission Policies

Trust Policy (who can assume this role):
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}

Permission Policy (what the role can do):
{
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::my-bucket/*"
  }]
}
```

### Common Role Patterns

```bash
# ── SERVICE ROLE (EC2 can do things) ──────────────────────────
# Create trust policy for EC2
cat > trust-ec2.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create the role
aws iam create-role \
  --role-name EC2S3ReadRole \
  --assume-role-policy-document file://trust-ec2.json \
  --description "Allows EC2 instances to read from S3"

# Attach policy to role
aws iam attach-role-policy \
  --role-name EC2S3ReadRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create instance profile (required to attach role to EC2)
aws iam create-instance-profile \
  --instance-profile-name EC2S3ReadProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2S3ReadProfile \
  --role-name EC2S3ReadRole

# Attach profile to running EC2 instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-0abc123 \
  --iam-instance-profile Name=EC2S3ReadProfile
```

```bash
# ── LAMBDA EXECUTION ROLE ─────────────────────────────────────
cat > trust-lambda.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name LambdaExecutionRole \
  --assume-role-policy-document file://trust-lambda.json

# Basic Lambda permissions (CloudWatch Logs)
aws iam attach-role-policy \
  --role-name LambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Lambda in VPC needs VPC access permissions too
aws iam attach-role-policy \
  --role-name LambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
```

```bash
# ── CROSS-ACCOUNT ROLE ────────────────────────────────────────
# Account A (123456789012) wants to allow Account B (987654321098) to access S3

# In Account A — create role with trust for Account B
cat > trust-cross-account.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::987654321098:root"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"sts:ExternalId": "unique-external-id-12345"}
    }
  }]
}
EOF

aws iam create-role \
  --role-name CrossAccountS3Role \
  --assume-role-policy-document file://trust-cross-account.json

aws iam attach-role-policy \
  --role-name CrossAccountS3Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# In Account B — assume the role in Account A
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/CrossAccountS3Role \
  --role-session-name "CrossAccountSession" \
  --external-id "unique-external-id-12345"
```

### ECS Task Role (Fargate)

```bash
# Trust policy for ECS tasks
cat > trust-ecs.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Task execution role (ECS agent needs this to pull images + get secrets)
aws iam create-role \
  --role-name ECSTaskExecutionRole \
  --assume-role-policy-document file://trust-ecs.json

aws iam attach-role-policy \
  --role-name ECSTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Task role (the actual container permissions)
aws iam create-role \
  --role-name ECSTaskRole \
  --assume-role-policy-document file://trust-ecs.json

aws iam attach-role-policy \
  --role-name ECSTaskRole \
  --policy-arn arn:aws:iam::123456789012:policy/AppPolicy
```

---

## 2.6 IAM Role Chaining & Permission Boundaries

### Permission Boundaries

A permission boundary is a **maximum permissions policy** attached to a user or role. The actual effective permissions are the intersection of the identity policy AND the boundary.

```
Effective permissions = Identity policy ∩ Permission boundary ∩ SCP

Example:
Identity Policy allows: s3:*, ec2:*, dynamodb:*
Permission Boundary: s3:*, ec2:*
Effective: s3:*, ec2:*       (dynamodb:* is outside boundary → denied)
```

```bash
# Create a permission boundary policy
aws iam create-policy \
  --policy-name DeveloperBoundary \
  --policy-document file://boundary.json

# Attach boundary to a user
aws iam put-user-permissions-boundary \
  --user-name alice \
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary

# Attach boundary to a role
aws iam put-role-permissions-boundary \
  --role-name DevRole \
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary

# Remove boundary
aws iam delete-user-permissions-boundary --user-name alice
```

**Use case:** Delegate IAM creation to developers but prevent privilege escalation.

```json
// Boundary: developers can only create roles that are also bounded
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PermissionsBoundary": "arn:aws:iam::123456789012:policy/DeveloperBoundary"
        }
      }
    }
  ]
}
```

---

## 2.7 AWS STS — Security Token Service

STS issues **temporary security credentials** for cross-account access, federation, and role assumption.

```bash
# AssumeRole — standard role assumption
aws sts assume-role \
  --role-arn "arn:aws:iam::123456789012:role/MyRole" \
  --role-session-name "SessionName" \
  --duration-seconds 3600         # 15 min to 12 hours
  --policy file://session-policy.json  # Optional: restrict further

# AssumeRoleWithWebIdentity — for OIDC (GitHub Actions, Cognito, etc.)
aws sts assume-role-with-web-identity \
  --role-arn "arn:aws:iam::123456789012:role/GitHubActionsRole" \
  --role-session-name "github-ci" \
  --web-identity-token "$GITHUB_TOKEN"

# AssumeRoleWithSAML — for enterprise SSO (Active Directory)
aws sts assume-role-with-saml \
  --role-arn "arn:aws:iam::123456789012:role/ADFSRole" \
  --principal-arn "arn:aws:iam::123456789012:saml-provider/ADFS" \
  --saml-assertion "$SAML_RESPONSE"

# GetSessionToken — for MFA-protected API calls
aws sts get-session-token \
  --serial-number arn:aws:iam::123456789012:mfa/alice \
  --token-code 123456 \
  --duration-seconds 43200       # up to 36 hours

# GetCallerIdentity — useful in scripts to verify identity
aws sts get-caller-identity
# Output: {Account, Arn, UserId}

# Decode authorization error messages
aws sts decode-authorization-message \
  --encoded-message "very-long-base64-encoded-error"
```

---

## 2.8 Identity Federation

### OIDC (OpenID Connect) Federation — GitHub Actions Example

```bash
# 1. Create OIDC Provider for GitHub
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"

# 2. Create IAM role that GitHub Actions can assume
cat > trust-github.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:*"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://trust-github.json

aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECRFullAccess
```

```yaml
# .github/workflows/deploy.yml — GitHub Actions using OIDC (no stored keys)
name: Deploy

on:
  push:
    branches: [main]

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC — no keys needed)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsDeployRole
          aws-region: us-east-1

      - name: Deploy to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
          docker build -t myapp .
          docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:latest
```

### SAML 2.0 Federation (Active Directory / Okta)

```
Flow:
┌──────────────┐     1. Login    ┌──────────────────┐
│   User       │────────────────►│  Identity Provider│
│ (AD/Okta)    │                 │  (ADFS / Okta)    │
└──────────────┘                 └────────┬─────────┘
                                          │ 2. SAML assertion
                                          ▼
                                 ┌──────────────────┐
                                 │  AWS STS         │
                                 │  AssumeRoleWith  │
                                 │  SAML            │
                                 └────────┬─────────┘
                                          │ 3. Temp credentials
                                          ▼
                                 ┌──────────────────┐
                                 │  AWS Console /   │
                                 │  API access      │
                                 └──────────────────┘
```

### AWS IAM Identity Center (SSO)

AWS IAM Identity Center (formerly AWS SSO) is the recommended way to manage human access to multiple AWS accounts:

```bash
# Create permission set (what users can do)
aws sso-admin create-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxx \
  --name "DeveloperAccess" \
  --description "Developer access to dev accounts" \
  --session-duration PT8H

# Attach managed policy to permission set
aws sso-admin attach-managed-policy-to-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxx \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xxxx/ps-xxxx \
  --managed-policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Assign users/groups to accounts
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxx \
  --target-id 123456789012 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xxxx/ps-xxxx \
  --principal-type GROUP \
  --principal-id group-id-from-identity-store
```

---

## 2.9 IAM Best Practices — Complete Checklist

```
ROOT ACCOUNT:
□ Enable MFA on root account immediately
□ Delete or don't create root access keys
□ Use root only for: account closure, billing, support plan changes
□ Monitor root usage with CloudTrail + CloudWatch alarm

USERS:
□ Create individual IAM users (never share credentials)
□ Enforce MFA for all users (especially console access)
□ Use groups to assign permissions (not individual policies)
□ Set IAM password policy (complexity + rotation)
□ Review and remove unused users regularly

ACCESS KEYS:
□ Rotate access keys every 90 days
□ Use IAM roles instead of keys for AWS services
□ Use Instance Profiles for EC2, not embedded keys
□ Never put access keys in code, Git, or environment variables in prod
□ Audit keys regularly: aws iam generate-credential-report

POLICIES:
□ Grant least privilege (start with nothing, add what's needed)
□ Use customer-managed policies over inline policies for reusability
□ Use conditions to restrict by IP, region, MFA status
□ Use permission boundaries to limit delegated admin scope
□ Audit: aws iam get-account-authorization-details > full-audit.json

ROLES:
□ Use roles for all AWS service communication (EC2, Lambda, ECS)
□ Use cross-account roles instead of embedding credentials
□ Use OIDC for CI/CD systems (GitHub Actions, GitLab, Jenkins)
□ Set appropriate role session duration (shorter = more secure)
□ Include ExternalId when creating cross-account roles

MONITORING:
□ Enable CloudTrail in all regions (track IAM API calls)
□ Set CloudWatch alarm for root account login
□ Use IAM Access Analyzer to find external access
□ Review Service Last Accessed to find unused permissions
□ Use IAM Access Advisor to see which permissions are actually used
```

---

## 2.10 IAM Access Analyzer

IAM Access Analyzer identifies resources shared with **external principals** (outside your AWS account or organization).

```bash
# Create analyzer for account
aws accessanalyzer create-analyzer \
  --analyzer-name MyAccountAnalyzer \
  --type ACCOUNT

# Create analyzer for organization
aws accessanalyzer create-analyzer \
  --analyzer-name MyOrgAnalyzer \
  --type ORGANIZATION

# List findings (resources accessible from outside)
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123:analyzer/MyAccountAnalyzer \
  --filter "status=eq:ACTIVE" \
  --query "findings[*].[id,resourceType,resource,status]" \
  --output table

# Get finding details
aws accessanalyzer get-finding \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123:analyzer/MyAccountAnalyzer \
  --id finding-id-here

# Archive a finding (expected public access — e.g., public S3 static website)
aws accessanalyzer update-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123:analyzer/MyAccountAnalyzer \
  --ids finding-id-here \
  --status ARCHIVED

# Policy validation (check policy before creating)
aws accessanalyzer validate-policy \
  --policy-document file://my-policy.json \
  --policy-type IDENTITY_POLICY \
  --query "findings[*].[findingType,issueCode,learnMoreLink]" \
  --output table

# Generate policy from CloudTrail (create least-privilege policy)
aws accessanalyzer start-policy-generation \
  --policy-generation-details '{"principalArn": "arn:aws:iam::123:role/MyRole"}' \
  --cloud-trail-details '{
    "accessRole": "arn:aws:iam::123:role/AccessAnalyzerRole",
    "trails": [{"cloudTrailArn": "arn:aws:cloudtrail:us-east-1:123:trail/MyTrail", "allRegions": true}],
    "startTime": "2025-01-01T00:00:00Z",
    "endTime": "2025-02-01T00:00:00Z"
  }'
```

---

## 2.11 Service Last Accessed & Credential Report

```bash
# Generate credential report (CSV) — all users: keys, MFA, last login
aws iam generate-credential-report
aws iam get-credential-report \
  --query "Content" --output text | base64 -d > credential-report.csv

# View with headers
aws iam get-credential-report \
  --query "Content" --output text | base64 -d | \
  awk -F, 'NR==1{print; next} {print}' | column -t -s,

# Check last time a service was accessed by a role
aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:role/MyRole

JOB_ID=$(aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:role/MyRole \
  --query "JobId" --output text)

aws iam get-service-last-accessed-details \
  --job-id $JOB_ID \
  --query "ServicesLastAccessed[?TotalAuthenticatedEntities>`0`].[ServiceName,LastAuthenticated]" \
  --output table
```

---

## 2.12 IAM Policy Troubleshooting

Common reasons why access is denied:

```
ERROR: "User: arn:aws:iam::123:user/alice is not authorized to perform: 
        ec2:TerminateInstances on resource: arn:aws:ec2:us-east-1:123:instance/i-0abc"

Diagnosis checklist:
1. Is there an explicit DENY somewhere?
   - Check user policies
   - Check group policies  
   - Check SCPs (organization level)
   - Check resource-based policies

2. Is there any ALLOW?
   - User may have no policy granting this action
   - Policy may allow different resource (ARN mismatch)
   - Condition may not be met

3. Debug tools:
```

```bash
# Simulate policy to find the issue
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:user/alice \
  --action-names ec2:TerminateInstances \
  --resource-arns arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123 \
  --query "EvaluationResults[*].[EvalActionName,EvalDecision,MatchedStatements[*].SourcePolicyId]" \
  --output json

# List all policies attached to user (direct + via groups)
aws iam list-attached-user-policies --user-name alice
aws iam list-user-policies --user-name alice  # inline
aws iam list-groups-for-user --user-name alice  # groups

# For each group, list policies
aws iam list-attached-group-policies --group-name Developers
aws iam list-group-policies --group-name Developers  # inline

# Decode authorization failure messages (from error response)
aws sts decode-authorization-message \
  --encoded-message "EncodedMessageFromErrorResponse"
```

---

## 2.13 Interview Q&A

**Q: What is the difference between an IAM user and an IAM role?**
A: An IAM user has permanent credentials (password + access keys) and represents a specific person or application. An IAM role has no permanent credentials — it issues temporary credentials via STS when assumed. Roles are assumed by AWS services (EC2, Lambda), other IAM users/roles, or federated identities.

**Q: What is the evaluation order for IAM policies?**
A: 1) Explicit DENY (always wins), 2) SCPs (organization level), 3) Resource-based policies (for cross-account), 4) Permission boundaries, 5) Identity-based policies. Default is DENY if no ALLOW found.

**Q: What is a permission boundary?**
A: A permission boundary is a managed policy that sets the maximum permissions an IAM user or role can have. Even if the identity policy grants broader permissions, the boundary caps them. Used to safely delegate IAM management to developers.

**Q: How do you allow GitHub Actions to deploy to AWS without storing access keys?**
A: Use OIDC federation. Create an OIDC provider in IAM pointing to GitHub's token service, then create an IAM role with a trust policy that allows GitHub to assume it. In the workflow, use `aws-actions/configure-aws-credentials` with `role-to-assume`. No AWS credentials stored as GitHub secrets.

**Q: What is the difference between a managed policy and an inline policy?**
A: Managed policies are standalone, reusable, versionable policies that can be attached to multiple identities. AWS managed policies are AWS-maintained; customer managed are yours. Inline policies are embedded directly in a single user/group/role, cannot be reused, and are deleted when the identity is deleted. Best practice: use customer-managed policies.

**Q: What is IAM Access Analyzer?**
A: A service that analyzes resource policies (S3 buckets, IAM roles, KMS keys, etc.) and identifies any access granted to entities outside your AWS account or organization. Helps prevent unintended external access. It can also generate least-privilege policies from CloudTrail activity.

**Q: What is the difference between an IAM role trust policy and a permission policy?**
A: The trust policy (also called the assume-role policy) defines WHO can assume the role (which principals — services, accounts, users). The permission policy defines WHAT the role can do once assumed (which actions on which resources). Both are required for a role to function.

**Q: How do you rotate access keys without downtime?**
A: 1) Create a new access key for the user, 2) Update all applications to use the new key, 3) Verify the new key works, 4) Set the old key to Inactive, 5) Monitor for any failures, 6) Delete the old key after a safe period.
