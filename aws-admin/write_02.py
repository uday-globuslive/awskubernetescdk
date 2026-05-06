
content = r"""# Chapter 2: IAM — Identity and Access Management
## (Who Can Do What in AWS — Explained Simply)

---

## 2.1 What is IAM and Why Does It Matter?

### The Simple Analogy: A Company Building

Imagine a large company office building with 500 employees. The building has:
- A **reception desk** — only people with ID badges get in (Authentication)
- **Different floors** — Finance floor, Engineering floor, HR floor
- **Locked rooms** — only specific people can enter the server room, accounting room, etc.
- **Security cameras** — record who goes where and when
- **Visitor badges** — temporary access for guests that expires

Now imagine the building has NO security:
- Anyone can walk in off the street
- Anyone can look at payroll records
- A disgruntled employee can delete everything
- No record of who did what when something goes wrong

**IAM is the security system for your entire AWS "building."** It controls:
- **Who** can access your AWS account (users, groups, roles, services)
- **What** they are allowed to do (read S3? launch EC2? delete databases?)
- **Under what conditions** (only from the office IP? only with MFA?)

### Why Getting IAM Wrong is Catastrophic

Real-world AWS security incidents:

1. **Capital One (2019):** A misconfigured WAF + overly permissive EC2 IAM role → attacker stole 100 million credit card applications. $80 million fine.

2. **Code Spaces (2014):** Attacker gained root access to AWS account → deleted ALL data, backups, and EC2 instances → company went out of business in 12 hours.

3. **Countless crypto miners:** Developer accidentally pushes AWS access keys to GitHub → bots find the keys in seconds → launch thousands of EC2 instances for Bitcoin mining → $50,000 AWS bill.

IAM done right prevents all of these.

---

## 2.2 IAM Core Components — The Building Blocks

IAM has 5 main components. You need to understand each one deeply.

### Component 1: IAM Users — Individual Identities

An **IAM User** represents a single person or application that needs long-term access to AWS.

- Has a **username** and **password** for console login
- Can have **access keys** (Access Key ID + Secret Access Key) for programmatic/CLI access
- By default has **no permissions** — you must explicitly grant permissions
- Belongs to an AWS account

**When to use IAM Users:**
- Human users who need to log in to the AWS Console
- Applications running OUTSIDE of AWS that need to call AWS APIs (legacy — modern apps use roles)
- CI/CD systems that need static credentials (legacy — prefer OIDC federation now)

**What IAM Users should NOT do:**
- The root account user should NEVER be used for daily work
- Access keys should not be embedded in application code
- A single "admin" user should not be shared by multiple people

```bash
# Create an IAM user
aws iam create-user --user-name john-developer

# Create a login profile (enables console access with password)
aws iam create-login-profile \
  --user-name john-developer \
  --password "TempPass123!" \
  --password-reset-required  # force password change on first login

# Create access keys (for CLI/SDK access)
aws iam create-access-key --user-name john-developer
# IMPORTANT: Save the SecretAccessKey now — it is shown ONCE only!

# List all users
aws iam list-users --output table

# Get details about a specific user
aws iam get-user --user-name john-developer
```

### Component 2: IAM Groups — Collections of Users

An **IAM Group** is a collection of users. You attach permissions to the group, and all users in the group inherit those permissions.

**Why groups matter:**
- Managing permissions per user = nightmare with 50 users
- Managing permissions per group = attach policy to group once, add users to group
- "John is a developer" → add John to the Developers group → he gets all developer permissions
- "Jane is promoted to admin" → remove from Developers group, add to Admins group

**Example group structure:**

```
IAM Groups:
  Admins
    → Full administrator access (use sparingly!)
    → Members: alice (CTO), bob (lead engineer)
    
  Developers
    → EC2 read/write, S3 read/write, CloudWatch read, CloudFormation read
    → Members: john, jane, carlos, priya, ...
    
  ReadOnly
    → ViewOnlyAccess policy (read everything, change nothing)
    → Members: new-engineer (for first 2 weeks), contractor-audit
    
  DataScientists
    → S3 read, Athena full access, SageMaker access, Glue read
    → Members: alice-data, bob-ml, ...
    
  NetworkAdmins
    → VPC full access, Route53 full access, ELB full access
    → Members: network-ops-team
```

**Key facts about groups:**
- Groups cannot contain other groups (no nesting)
- A user can be in multiple groups
- Groups are just permission containers — they cannot be used in resource-based policies

```bash
# Create a group
aws iam create-group --group-name Developers

# Add a user to the group
aws iam add-user-to-group --group-name Developers --user-name john-developer

# Attach a managed policy to the group
aws iam attach-group-policy \
  --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# List members of a group
aws iam get-group --group-name Developers

# List all groups a user belongs to
aws iam list-groups-for-user --user-name john-developer
```

### Component 3: IAM Roles — Temporary, Assumable Identities

An **IAM Role** is like a temporary badge you can assume. Unlike users (who have permanent credentials), roles:
- Have **no permanent credentials**
- Are **assumed** temporarily (credentials expire after 1-12 hours)
- Can be assumed by: users, AWS services, applications, users from other accounts, external IdPs

**The key insight:** IAM Roles are the PREFERRED way to grant permissions in AWS. If anything (a service, an app, a Lambda function) needs AWS permissions, give it a role — not access keys.

**Why roles over access keys:**
```
Access Keys (BAD for most cases):
  - Static, long-lived credentials
  - If leaked (git commit, logs, screenshot), attacker has access forever
  - Hard to rotate when compromised
  - Often over-privileged because "just in case"

IAM Roles (GOOD):
  - Temporary credentials (expire after 1-12 hours)
  - Auto-rotated by AWS (you never manage them)
  - Cannot be leaked to Git (no static keys)
  - Clear audit trail: "EC2 instance i-12345 assumed role ReadS3Role at 14:32"
```

**Common role use cases:**

1. **EC2 Instance Role:** EC2 server needs to read from S3 → give the EC2 a role with S3 read permission → EC2 can read S3 without any static keys stored on the server

2. **Lambda Execution Role:** Lambda function needs to write to DynamoDB → give the Lambda a role with DynamoDB write permission

3. **Cross-Account Role:** Company B wants to read your CloudWatch metrics → create a role that trusts Company B's account → Company B assumes the role → no credentials shared

4. **Federated Identity:** Users login via your company's Active Directory (SAML) → they assume an IAM role → get temporary AWS access → no IAM users needed

```bash
# Create a role for EC2 instances to read S3
cat > /tmp/ec2-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name EC2-ReadS3 \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json \
  --description "Allows EC2 instances to read from S3"

# Attach S3 read permission to the role
aws iam attach-role-policy \
  --role-name EC2-ReadS3 \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create an instance profile (wrapper for EC2)
aws iam create-instance-profile --instance-profile-name EC2-ReadS3-Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-ReadS3-Profile \
  --role-name EC2-ReadS3

# Attach the instance profile to an EC2 instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-0123456789abcdef0 \
  --iam-instance-profile Name=EC2-ReadS3-Profile

# Now the EC2 instance can run: aws s3 ls — no keys needed!
```

### Component 4: IAM Policies — The Permission Documents

An **IAM Policy** is a JSON document that says: "Allow or Deny these Actions on these Resources under these Conditions."

**Policies define WHAT is allowed (or denied). Everything else is implicit deny.**

The basic structure of a policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OptionalStatementID",
      "Effect": "Allow",    ← or "Deny"
      "Action": [           ← what API calls are allowed/denied
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [         ← which specific resources
        "arn:aws:s3:::my-company-bucket",
        "arn:aws:s3:::my-company-bucket/*"
      ],
      "Condition": {        ← optional: only if these conditions are true
        "StringEquals": {
          "s3:prefix": "finance/"
        }
      }
    }
  ]
}
```

**Understanding ARNs (Amazon Resource Names):**

Every AWS resource has a unique ARN. It is the resource's "address":
```
arn:aws:service:region:account-id:resource-type/resource-id

Examples:
  arn:aws:s3:::my-bucket              (S3 bucket — no region, no account)
  arn:aws:s3:::my-bucket/*            (all objects in my-bucket)
  arn:aws:ec2:us-east-1:123456789:instance/i-0123456789abcdef0
  arn:aws:iam::123456789:user/john    (IAM — no region because global)
  arn:aws:iam::123456789:role/MyRole
  arn:aws:lambda:us-east-1:123456789:function:my-function
  arn:aws:rds:us-east-1:123456789:db:my-database

The wildcard * means "all":
  "Resource": "*"           → applies to ALL resources
  "Action": "s3:*"          → allows ALL S3 actions
  "Resource": "arn:aws:s3:::my-bucket/*"  → all objects in my-bucket
```

### The 3 Types of Policies

**1. AWS Managed Policies — Pre-built by AWS**

AWS creates and maintains these. They are updated when new services/features launch.

Common ones to know:
```
AdministratorAccess   — Allow all actions on all resources (*)
PowerUserAccess       — Full access except IAM user/group management
ReadOnlyAccess        — Read access to all services
AmazonS3FullAccess    — Full S3 access
AmazonS3ReadOnlyAccess — Read-only S3
AmazonEC2FullAccess   — Full EC2 access
AmazonRDSFullAccess   — Full RDS access
CloudWatchFullAccess  — Full CloudWatch access
```

Pros: Easy to use, AWS maintains them
Cons: Often broader than needed (over-permissive)

**2. Customer Managed Policies — You Create, You Maintain**

You write your own policies tailored to your exact needs.

Example: "Our developers can read and write to any S3 bucket in our account, but cannot delete buckets or objects":
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:ListBucket",
        "s3:GetBucketLocation", "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDelete",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteObject",
        "s3:DeleteBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

**3. Inline Policies — Embedded in User/Group/Role**

Written directly into the user, group, or role. Not reusable.

Use case: A permission so unique that no other identity should ever have it.
Drawback: Hard to manage, cannot reuse, easy to miss in audits.

**Recommendation: Use Customer Managed Policies for everything. Avoid inline policies. Use AWS Managed Policies only when they exactly match your needs.**

### How Policy Evaluation Works — The Decision Logic

This is very important for the exam. When AWS receives a request, it goes through this logic:

```
Step 1: Is there an EXPLICIT DENY anywhere?
  → SCPs (Organization level)
  → Resource-based policies
  → Identity-based policies (IAM policies)
  → Permission boundaries
  → Session policies
  
  If YES → DENY (denied immediately, no further evaluation)

Step 2: Is there an EXPLICIT ALLOW?
  → Any of the above policy types explicitly allows this action
  
  If YES → ALLOW

Step 3: Neither explicit deny nor explicit allow?
  → IMPLICIT DENY (default, deny everything not explicitly allowed)
```

**The priority order:**
```
1. Explicit Deny in ANY policy → Always DENY (trumps everything)
2. SCPs → Filter what is possible in the account
3. Resource-based policies → Can allow cross-account
4. Identity-based policies (IAM) → The usual permissions
5. Permission boundaries → Maximum limit for identity
6. Session policies → Limit for assumed roles
7. Implicit Deny → If nothing allows, DENY
```

**Example exam scenario:**

A user has an IAM policy with `"Effect": "Allow", "Action": "s3:*", "Resource": "*"`.
But there is also an SCP at the OU level with `"Effect": "Deny", "Action": "s3:DeleteBucket"`.

Question: Can the user delete an S3 bucket?
Answer: **NO** — the explicit DENY in the SCP trumps the Allow in the IAM policy.

### The "Deny Overrides Allow" Principle

**Remember this:** ANY explicit Deny, from ANYWHERE, wins over any Allow.

```
Allow from IAM policy + Deny from SCP = DENY
Allow from IAM policy + Deny from resource policy = DENY
Allow from group + Deny from user's own policy = DENY
```

The ONLY exception: The root user of an account is not restricted by certain AWS-managed policies (but IS restricted by SCPs from the parent organization).

---

## 2.3 The Principle of Least Privilege

### What It Means

**Least Privilege** means: give every identity (user, role, service) **only the exact permissions they need** to do their specific job — **nothing more**.

**Why this matters:**
- If a developer's credentials are stolen, the attacker can only do what that developer can do
- If a Lambda function is compromised, it cannot pivot to delete your databases
- Limits the "blast radius" of any security incident

### Analogy: A Hospital

A nurse needs access to:
- Patient records (read + update)
- Medicine cabinet in their ward

A nurse does NOT need:
- Financial records
- Other wards' medicine cabinets
- Surgery scheduling system
- Building security codes

If you give every nurse keys to everything, one bad actor (or a stolen badge) can cause massive harm. If you restrict each nurse to only what they need, a stolen badge only compromises that nurse's scope.

### How to Apply Least Privilege in Practice

**Step 1: Start with NO permissions (the default)**
New IAM entities have zero permissions. This is the correct starting point.

**Step 2: Identify what the entity ACTUALLY needs to do**
- "This Lambda function processes S3 uploads and stores results in DynamoDB"
- Needs: `s3:GetObject` on one bucket, `dynamodb:PutItem` on one table
- Does NOT need: EC2, RDS, IAM, networking, any other S3 bucket, DynamoDB full access

**Step 3: Write the most specific policy possible**

Bad (too broad):
```json
{
  "Effect": "Allow",
  "Action": "*",
  "Resource": "*"
}
```

Also bad (still too broad):
```json
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}
```

Good (specific):
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject"],
  "Resource": "arn:aws:s3:::my-upload-bucket/incoming/*"
}
```

**Step 4: Use IAM Access Analyzer to find unused permissions**

```bash
# Create an Access Analyzer to find over-permissive policies
aws accessanalyzer create-analyzer \
  --analyzer-name my-account-analyzer \
  --type ACCOUNT

# Get findings (things accessible from outside your account)
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/my-account-analyzer

# Check what permissions an IAM entity actually used (last 90 days)
aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:user/john-developer

# Get the result (use the job-id from above)
aws iam get-service-last-accessed-details \
  --job-id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# → Shows which services were actually accessed
# → Services NOT accessed in 90 days = permissions you can remove!
```

---

## 2.4 Multi-Factor Authentication (MFA) — The Second Lock

### What is MFA?

**MFA (Multi-Factor Authentication)** means requiring TWO forms of proof to log in:
1. **Something you know** — your password
2. **Something you have** — a 6-digit code from your phone

**Analogy:** An ATM card.
- The card (something you have) + PIN (something you know) = access
- Steal just the card? Useless without the PIN.
- Know just the PIN? Useless without the card.

With MFA on your AWS account:
- Attacker steals your password → still cannot log in without your phone
- Attacker clones your phone → still cannot log in without your password
- Both must be compromised simultaneously → much harder

### MFA Device Types

| Type | How It Works | Example |
|------|------------|---------|
| **Virtual MFA** | App on your phone generates 6-digit codes | Google Authenticator, Authy, Microsoft Authenticator |
| **Hardware TOTP** | Physical key fob with display | Gemalto token |
| **FIDO Security Key** | Physical USB/NFC key | YubiKey, Apple Touch ID |
| **AWS MFA Hardware** | AWS-provided hardware token | For high-security environments |

### Enforcing MFA via IAM Policy

You can write an IAM policy that says: "If you do not have MFA, you can only do these things":

```json
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
        "iam:ListMFADevices"
      ],
      "Resource": [
        "arn:aws:iam::*:mfa/${aws:username}",
        "arn:aws:iam::*:user/${aws:username}"
      ]
    },
    {
      "Sid": "DenyAllExceptMFASetupIfNoMFA",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ListVirtualMFADevices",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}
      }
    }
  ]
}
```

This policy: allows users to set up their MFA device, but blocks ALL other actions until they have MFA enabled. Effectively forces MFA enrollment.

### Enable MFA via CLI

```bash
# Enable MFA for root account (must do from console — CLI cannot set root MFA)
# But for IAM users:

# Step 1: Create a virtual MFA device
aws iam create-virtual-mfa-device \
  --virtual-mfa-device-name john-developer-mfa \
  --outfile /tmp/qrcode.png \
  --bootstrap-method QRCodePNG

# Step 2: User scans QR code with Authenticator app and provides two consecutive codes
aws iam enable-mfa-device \
  --user-name john-developer \
  --serial-number arn:aws:iam::123456789012:mfa/john-developer-mfa \
  --authentication-code1 123456 \
  --authentication-code2 789012

# Step 3: Verify MFA is active
aws iam list-mfa-devices --user-name john-developer
```

### Requiring MFA for Sensitive Actions

Best practice: require MFA before allowing destructive actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDangerousActionsWithoutMFA",
      "Effect": "Deny",
      "Action": [
        "ec2:TerminateInstances",
        "rds:DeleteDBInstance",
        "s3:DeleteBucket",
        "iam:DeleteUser",
        "iam:CreateAccessKey"
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

---

## 2.5 IAM Roles in Depth — The Most Important IAM Concept

### How Role Assumption Works (Step by Step)

```
Step 1: Entity (user, service, app) calls sts:AssumeRole
  → "I want to assume the role 'S3ReadRole'"

Step 2: AWS checks the Role's Trust Policy
  → Does the Trust Policy allow this entity to assume this role?
  → If NO → Deny
  → If YES → Continue

Step 3: AWS STS issues temporary credentials
  → AccessKeyId (temporary, like a regular access key but expires)
  → SecretAccessKey (temporary)
  → SessionToken (proves the credentials are temporary)
  → Expiration time (default 1 hour, max 12 hours)

Step 4: Entity uses temporary credentials for API calls
  → All API calls authenticated with these temp credentials

Step 5: Credentials expire
  → Entity must call AssumeRole again for new credentials
  → Or they just stop having access
```

### Trust Policy vs Permissions Policy

Every IAM Role has TWO policies:

**1. Trust Policy (Who can assume this role?)**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "lambda.amazonaws.com"  ← Only Lambda can assume this role
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**2. Permissions Policy (What can this role do?)**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem"
    ],
    "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/orders"
  }]
}
```

Both policies must align: the Trust Policy must allow the entity to assume the role, AND the Permissions Policy must allow the action being attempted.

### Cross-Account Role Assumption

Scenario: Your security team's account (Account A) needs to audit resources in Account B (production).

```
Account A (Security): 123456789012
Account B (Production): 987654321098
```

**Setup in Account B (where resources are):**

```bash
# In Account B, create a role that Account A can assume
cat > /tmp/cross-account-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::123456789012:root"  ← Trust the entire Account A
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "Bool": {"aws:MultiFactorAuthPresent": "true"}  ← Only with MFA
    }
  }]
}
EOF

aws iam create-role \
  --role-name SecurityAuditRole \
  --assume-role-policy-document file:///tmp/cross-account-trust.json

aws iam attach-role-policy \
  --role-name SecurityAuditRole \
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit  # AWS Managed: read-only audit
```

**Assuming the role from Account A:**

```bash
# In Account A (security account), assume the role in Account B
aws sts assume-role \
  --role-arn arn:aws:iam::987654321098:role/SecurityAuditRole \
  --role-session-name security-audit-$(date +%Y%m%d) \
  --duration-seconds 3600

# Output includes:
# AccessKeyId: ASIA...
# SecretAccessKey: xxxx...
# SessionToken: xxxx...
# Expiration: 2025-01-01T13:00:00+00:00

# Use the credentials
export AWS_ACCESS_KEY_ID=ASIA...
export AWS_SECRET_ACCESS_KEY=xxxx...
export AWS_SESSION_TOKEN=xxxx...

# Now you are operating as the SecurityAuditRole in Account B
aws ec2 describe-instances --region us-east-1
```

### IAM Identity Center (SSO) — The Modern Way

For larger organizations, instead of creating IAM users in every account, use **IAM Identity Center** (formerly AWS SSO):

```
Traditional approach (painful):
  50 accounts × 100 engineers = 5,000 IAM users to manage
  Each engineer has different credentials for each account
  Engineer leaves → must disable 50 accounts separately
  
IAM Identity Center approach:
  Connect to your existing identity source (Active Directory, Google Workspace, Okta)
  Assign permission sets to users/groups
  Users login ONCE at the IAM Identity Center portal
  They can switch between any account they have access to
  Engineer leaves → disable once in Active Directory → access removed from all 50 accounts
```

```bash
# Enable IAM Identity Center (do this in the management account)
# This is mostly done via the console — CLI support is limited

# List permission sets
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxx

# Assign a permission set to a user for a specific account
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxx \
  --target-id 123456789012 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xxxx/ps-xxxx \
  --principal-type USER \
  --principal-id user-id-from-identity-store
```

---

## 2.6 Permission Boundaries — Guardrails for Delegated Administration

### The Problem They Solve

Imagine you want to let your development team create their own IAM roles for their Lambda functions. But you are worried they might accidentally (or intentionally) create a role with admin access.

**Permission Boundaries** solve this: you grant the developer the ability to create roles, but you set a maximum limit on what permissions those roles can have.

**Analogy:** You hire an employee and give them a company credit card. But you set a spending limit — they can buy whatever they need for work, but cannot spend more than $500/day. The $500 limit is the permission boundary.

### How Permission Boundaries Work

```
Developer's IAM policy ALLOWS: iam:CreateRole, iam:AttachRolePolicy, ...
BUT their permission boundary says max allowed: S3FullAccess, DynamoDBFullAccess

Result:
  Developer tries to create role with AdministratorAccess → DENIED
  (The boundary limits them to S3 + DynamoDB, even though their IAM policy allows iam:CreateRole)
  
  Developer creates role with S3ReadOnlyAccess → ALLOWED
  (S3ReadOnlyAccess is within the boundary)
```

### Permission Boundary Example

```bash
# Create a permission boundary policy
# "Anyone with this boundary can only use S3 and DynamoDB"
cat > /tmp/dev-boundary.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "dynamodb:*",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "logs:*",
        "lambda:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name DeveloperPermissionBoundary \
  --policy-document file:///tmp/dev-boundary.json

# Apply the boundary to a developer user
aws iam put-user-permissions-boundary \
  --user-name john-developer \
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperPermissionBoundary

# Now john-developer cannot access EC2, RDS, IAM, or any other service
# even if someone accidentally gives him a broad policy
```

---

## 2.7 IAM Best Practices — The Security Checklist

### 1. Protect the Root Account

The **root account** is created when you first open an AWS account. It has **complete, unrestricted access to everything** and cannot be limited by any IAM policy.

**Root account security:**
```bash
# What you MUST do with root account (do this first day):
# 1. Enable MFA on root (do in console — cannot do via CLI)
# 2. Do NOT create access keys for root
# 3. Never use root for daily work
# 4. Store root credentials in a password manager + separate location
# 5. Set up billing alerts (only root can see all billing)

# Check if root has access keys (should be empty):
aws iam get-account-summary --query 'SummaryMap.AccountAccessKeysPresent'
# Should return: 0 (no root access keys)

# Check root MFA status (should return data, not empty):
aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled'
# Should return: 1 (MFA enabled)
```

### 2. Create Individual IAM Users

Never share credentials. Each person = their own IAM user with their own password and (if needed) access keys.

```bash
# Good: Individual users
aws iam create-user --user-name alice-developer
aws iam create-user --user-name bob-devops
aws iam create-user --user-name carol-manager

# Bad: Shared user (never do this)
# aws iam create-user --user-name dev-team-shared  ← WRONG
```

### 3. Use Groups, Not Direct Policies

```bash
# Good: Manage via groups
aws iam create-group --group-name SysAdmins
aws iam attach-group-policy --group-name SysAdmins \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam add-user-to-group --group-name SysAdmins --user-name alice

# Bad: Attach policies directly to users (hard to manage)
# aws iam attach-user-policy --user-name alice \  ← Avoid this
#   --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

### 4. Strong Password Policy

```bash
aws iam update-account-password-policy \
  --minimum-password-length 12 \
  --require-symbols \
  --require-numbers \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --allow-users-to-change-password \
  --max-password-age 90 \
  --password-reuse-prevention 12 \
  --hard-expiry false
```

### 5. Rotate Access Keys Regularly

```bash
# List all access key ages
aws iam list-users --query 'Users[*].UserName' --output text | \
  tr '\t' '\n' | \
  while read user; do
    keys=$(aws iam list-access-keys --user-name $user \
      --query 'AccessKeyMetadata[*].[AccessKeyId,CreateDate,Status]' \
      --output text)
    if [ ! -z "$keys" ]; then
      echo "User: $user"
      echo "$keys"
    fi
  done
# Keys older than 90 days should be rotated

# Rotate a key:
# Step 1: Create new key
aws iam create-access-key --user-name john-developer
# Step 2: Update application to use new key and verify it works
# Step 3: Deactivate old key
aws iam update-access-key --user-name john-developer \
  --access-key-id AKIAIOSFODNN7EXAMPLE --status Inactive
# Step 4: Wait 24h, confirm nothing using old key, then delete
aws iam delete-access-key --user-name john-developer \
  --access-key-id AKIAIOSFODNN7EXAMPLE
```

### 6. Use IAM Access Analyzer

```bash
# Create analyzer to detect overly-permissive resources
aws accessanalyzer create-analyzer \
  --analyzer-name account-access-analyzer \
  --type ACCOUNT

# Review findings
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-access-analyzer \
  --filter '{"status": {"eq": ["ACTIVE"]}}' \
  --output table

# Archive a finding (mark as intentional/OK)
aws accessanalyzer update-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-access-analyzer \
  --ids finding-id-1234 \
  --status ARCHIVED
```

### 7. Generate Credential Reports

```bash
# Generate a report of all users and their credential status
aws iam generate-credential-report
aws iam get-credential-report \
  --query 'Content' --output text | base64 --decode > /tmp/credential-report.csv

# The CSV shows:
# - user: username
# - password_enabled: has console access?
# - password_last_used: when did they last log in?
# - mfa_active: is MFA enabled?
# - access_key_1_active: do they have active access keys?
# - access_key_1_last_used_date: when were they last used?
```

---

## 2.8 IAM Policy Examples — Real-World Scenarios

### Developer Access (Read/Write, No Delete)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2ReadWrite",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "ec2:RunInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NoEC2Delete",
      "Effect": "Deny",
      "Action": [
        "ec2:TerminateInstances",
        "ec2:DeleteVolume",
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3FullExceptDelete",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:ListBucket",
        "s3:GetBucketLocation", "s3:ListAllMyBuckets",
        "s3:GetObjectVersion"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchReadMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricStatistics",
        "logs:GetLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
```

### S3 Bucket — Only Access Own Folder

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::company-files",
      "arn:aws:s3:::company-files/${aws:username}/*"
    ],
    "Condition": {
      "StringLike": {
        "s3:prefix": ["${aws:username}/*", ""]
      }
    }
  }]
}
```

### Resource-Based Policy (S3 Bucket Policy)

Unlike IAM policies (attached to identities), resource-based policies are attached to the RESOURCE itself.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSpecificAccountsOnly",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::111111111111:root",
          "arn:aws:iam::222222222222:root"
        ]
      },
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::shared-reports-bucket",
        "arn:aws:s3:::shared-reports-bucket/*"
      ]
    },
    {
      "Sid": "DenyHTTP",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::shared-reports-bucket",
        "arn:aws:s3:::shared-reports-bucket/*"
      ],
      "Condition": {
        "Bool": {"aws:SecureTransport": "false"}
      }
    }
  ]
}
```

---

## 2.9 Real-World Project: Secure IAM Foundation

### Scenario

Your company has 30 engineers of different types: 10 backend developers, 5 frontend developers, 3 DevOps engineers, 5 data scientists, 5 read-only stakeholders, 2 security auditors.

### Implementation

```python
import boto3
import json

iam = boto3.client('iam', region_name='us-east-1')

# ── 1. Password Policy ──────────────────────────────────────────────
iam.update_account_password_policy(
    MinimumPasswordLength=14,
    RequireSymbols=True,
    RequireNumbers=True,
    RequireUppercaseCharacters=True,
    RequireLowercaseCharacters=True,
    AllowUsersToChangePassword=True,
    MaxPasswordAge=90,
    PasswordReusePrevention=12,
    HardExpiry=False
)
print("Password policy set")

# ── 2. Create Groups ─────────────────────────────────────────────────
groups = {
    'BackendDevelopers': [
        'arn:aws:iam::aws:policy/AmazonEC2FullAccess',
        'arn:aws:iam::aws:policy/AmazonRDSFullAccess',
        'arn:aws:iam::aws:policy/AmazonS3FullAccess',
        'arn:aws:iam::aws:policy/CloudWatchFullAccess',
    ],
    'FrontendDevelopers': [
        'arn:aws:iam::aws:policy/AmazonS3FullAccess',
        'arn:aws:iam::aws:policy/CloudFrontFullAccess',
        'arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess',
    ],
    'DevOps': [
        'arn:aws:iam::aws:policy/AdministratorAccess',
    ],
    'DataScientists': [
        'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess',
        'arn:aws:iam::aws:policy/AmazonAthenaFullAccess',
        'arn:aws:iam::aws:policy/AmazonSageMakerFullAccess',
    ],
    'ReadOnly': [
        'arn:aws:iam::aws:policy/ReadOnlyAccess',
    ],
    'SecurityAuditors': [
        'arn:aws:iam::aws:policy/SecurityAudit',
        'arn:aws:iam::aws:policy/AWSCloudTrailReadOnlyAccess',
    ]
}

for group_name, policies in groups.items():
    try:
        iam.create_group(GroupName=group_name)
        print(f"Created group: {group_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"Group already exists: {group_name}")
    
    for policy_arn in policies:
        iam.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)
    print(f"  Attached {len(policies)} policies to {group_name}")

# ── 3. Create Users and Add to Groups ───────────────────────────────
engineers = [
    ('alice-backend', 'BackendDevelopers'),
    ('bob-backend', 'BackendDevelopers'),
    ('carol-frontend', 'FrontendDevelopers'),
    ('dave-devops', 'DevOps'),
    ('eve-data', 'DataScientists'),
    ('frank-readonly', 'ReadOnly'),
    ('grace-security', 'SecurityAuditors'),
]

for username, group in engineers:
    try:
        iam.create_user(
            UserName=username,
            Tags=[
                {'Key': 'Department', 'Value': group},
                {'Key': 'CreatedBy', 'Value': 'IAM-Bootstrap'},
                {'Key': 'CreatedDate', 'Value': '2025-01-01'}
            ]
        )
        iam.create_login_profile(
            UserName=username,
            Password='TempPass@123!',
            PasswordResetRequired=True
        )
        iam.add_user_to_group(GroupName=group, UserName=username)
        print(f"Created user {username} in group {group}")
    except Exception as e:
        print(f"Error creating {username}: {e}")

# ── 4. Create MFA Enforcement Policy ────────────────────────────────
mfa_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowMFASetup",
            "Effect": "Allow",
            "Action": [
                "iam:CreateVirtualMFADevice", "iam:EnableMFADevice",
                "iam:GetUser", "iam:ListMFADevices",
                "iam:ListVirtualMFADevices", "sts:GetSessionToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyWithoutMFA",
            "Effect": "Deny",
            "NotAction": [
                "iam:CreateVirtualMFADevice", "iam:EnableMFADevice",
                "iam:GetUser", "iam:ListMFADevices",
                "iam:ListVirtualMFADevices", "sts:GetSessionToken"
            ],
            "Resource": "*",
            "Condition": {
                "BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}
            }
        }
    ]
}

policy_arn = iam.create_policy(
    PolicyName='RequireMFA',
    PolicyDocument=json.dumps(mfa_policy),
    Description='Blocks all actions unless MFA is present'
)['Policy']['Arn']

# Attach MFA requirement to ALL groups
for group_name in groups.keys():
    iam.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)

print("MFA policy attached to all groups")
print("IAM foundation setup complete!")
```

---

## 2.10 Practice Questions

**Q1:** A Lambda function needs to read objects from an S3 bucket and write results to DynamoDB. What is the MOST secure way to grant the Lambda function these permissions?

- A) Create an IAM user, generate access keys, store them in Lambda environment variables
- B) Create an IAM role with S3 read and DynamoDB write permissions, assign it as the Lambda execution role
- C) Store AWS access keys in the Lambda source code
- D) Grant the Lambda function AdministratorAccess for simplicity

**Answer: B**

Explanation: IAM Roles are always the correct choice for AWS services (Lambda, EC2, ECS, etc.) needing AWS permissions. Roles provide temporary, automatically rotated credentials. Storing access keys in code or environment variables is a security risk — they can be extracted from deployment packages or logs. AdministratorAccess violates least privilege.

---

**Q2:** An IAM user has the AWS-managed `AmazonS3FullAccess` policy attached. However, a bucket policy on bucket "finance-reports" has an explicit `"Effect": "Deny"` on `s3:GetObject` for all principals. The user tries to get an object from that bucket. What happens?

- A) Access is allowed because the IAM policy explicitly allows S3 full access
- B) Access is denied because an explicit Deny anywhere overrides any Allow
- C) Access depends on whether the user is listed in the bucket policy
- D) Access is allowed if the user is in the same account as the bucket

**Answer: B**

Explanation: The policy evaluation logic: if there is an explicit Deny anywhere (SCP, IAM policy, resource policy, permission boundary), the request is DENIED regardless of any Allow. The explicit Deny in the resource-based bucket policy overrides the Allow in the identity-based IAM policy. Deny > Allow, always.

---

**Q3:** Your company has 5 AWS accounts. You want engineers to be able to log in once and switch between accounts without separate passwords for each. What solution should you implement?

- A) Create identical IAM users in all 5 accounts with the same password
- B) Configure AWS IAM Identity Center (SSO) integrated with your existing Active Directory
- C) Share the root account credentials across all 5 accounts
- D) Create cross-account IAM roles that users manually assume in each account

**Answer: B**

Explanation: IAM Identity Center provides Single Sign-On for multiple AWS accounts. Users authenticate once (using existing Active Directory, Google, Okta, or built-in directory), then can switch between any accounts they have access to from a single portal. When someone leaves the company, you disable them in Active Directory and they immediately lose access to all accounts. This is far superior to managing separate IAM users in each account.

---

**Q4:** A developer accidentally commits AWS access keys to a public GitHub repository. You discover this 30 minutes later. What should you do FIRST?

- A) Rotate the access keys immediately (generate new keys, delete old ones)
- B) Delete the GitHub repository to remove the credentials
- C) Immediately deactivate/delete the compromised access keys and check CloudTrail for unauthorized API calls
- D) Change the IAM user's console password

**Answer: C**

Explanation: Bots scan GitHub for AWS access keys continuously — within minutes of a commit, automated scanners will find and use the keys. The FIRST action is to immediately deactivate and delete the compromised keys (not just rotate, but delete). Then check CloudTrail for any API calls made with those keys in the last 30 minutes. Deleting the GitHub repo (B) does not help because the keys are already exposed and likely already used. Changing the console password (D) is irrelevant to access keys.

---

**Q5:** Which of the following is TRUE about IAM permission boundaries?

- A) They grant additional permissions on top of the IAM policy
- B) They define the maximum permissions an IAM entity can have — they do not grant permissions on their own
- C) They are only applicable to IAM roles, not users
- D) Permission boundaries override Service Control Policies

**Answer: B**

Explanation: Permission boundaries define the MAXIMUM set of permissions that an identity-based policy can grant to an IAM entity. They are a ceiling, not a grant. An action is only allowed if BOTH the IAM policy allows it AND it is within the permission boundary. If the IAM policy allows S3 full access but the permission boundary only allows S3 read, the effective permission is S3 read. Boundaries apply to both users and roles. SCPs take precedence over permission boundaries in the evaluation order.

---

## Chapter 2 Summary

| Concept | Key Fact |
|---------|----------|
| IAM User | Individual long-term identity; each person gets their own; no shared accounts |
| IAM Group | Container for users; manage permissions at group level; users inherit group permissions |
| IAM Role | Temporary assumable identity; always use roles for AWS services (never static keys) |
| IAM Policy | JSON document defining Allow/Deny on Actions/Resources; Deny always wins |
| Least Privilege | Give only the minimum permissions needed; never use AdministratorAccess for services |
| MFA | Second factor authentication; MUST be enabled on root and all human accounts |
| Permission Boundary | Maximum permissions ceiling; delegation of admin without full admin rights |
| Cross-Account Roles | One account assumes role in another; no shared credentials |
| IAM Identity Center | Single Sign-On for multiple accounts; integrates with AD/Google/Okta |
| Evaluation Logic | Explicit Deny > SCP > Resource Policy > IAM Policy > Permission Boundary > Implicit Deny |
| Access Keys | Long-lived; rotate every 90 days; NEVER commit to git; prefer roles instead |
| Root Account | Ultimate power; protect with MFA; NEVER use for daily tasks; no access keys |
"""

with open(r"e:\fastapi\aws-admin\02_IAM_Security_Identity.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
