# Chapter 2: IAM, Security & Identity Management

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 4**: Security and Compliance (16% of exam)
- Heavily tested — expect 8-12 questions on IAM topics

---

## 2.1 IAM Fundamentals

AWS Identity and Access Management (IAM) is a **global service** (not region-specific) that controls authentication and authorization to AWS resources.

### Core Concepts
```
┌─────────────────────────────────────────────────────────────┐
│                      IAM COMPONENTS                         │
│                                                             │
│  PRINCIPAL           AUTHENTICATION         AUTHORIZATION   │
│  (Who am I?)         (Prove identity)       (What can I do?)│
│                                                             │
│  • IAM User    ──►  • Password         ──►  • IAM Policies  │
│  • IAM Role         • MFA                  • SCPs           │
│  • IAM Group        • Access Keys          • RBPs           │
│  • AWS Service      • SAML/OIDC            • Perm Boundary  │
│  • Federated                                                │
│    Identity                                                 │
└─────────────────────────────────────────────────────────────┘
```

### IAM Users
- Represents a **person or application** with long-term credentials
- Has a username + password (console) and/or access key + secret key (programmatic)
- **Best Practice:** Never use root user for day-to-day work; create individual IAM users

```bash
# Create IAM user
aws iam create-user --user-name alice

# Create login profile (console password)
aws iam create-login-profile \
  --user-name alice \
  --password "TempPass123!" \
  --password-reset-required

# Create access keys (programmatic)
aws iam create-access-key --user-name alice

# Attach policy to user
aws iam attach-user-policy \
  --user-name alice \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```

### IAM Groups
- Collection of IAM users
- Attach policies to groups rather than individual users
- A user can belong to multiple groups
- **Groups cannot contain other groups**

```bash
# Create group
aws iam create-group --group-name Developers

# Add user to group
aws iam add-user-to-group --group-name Developers --user-name alice

# Attach policy to group
aws iam attach-group-policy \
  --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

### IAM Roles
Roles are the **preferred** way to grant permissions to:
- AWS services (EC2, Lambda, ECS tasks)
- Applications (temporary credentials via STS)
- Cross-account access
- Federated identities (SAML, OIDC)

**Role vs User:**
| Feature | IAM User | IAM Role |
|---------|---------|---------|
| Credentials | Long-term (static keys) | Short-term (STS tokens, 15min-12hr) |
| Assigned to | Person/app | Service, user, or account |
| Best for | Human users | AWS services, cross-account, federation |
| Access key rotation | Required | Automatic |

```bash
# Create role for EC2 to access S3
aws iam create-role \
  --role-name EC2-S3-ReadRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach policy to role
aws iam attach-role-policy \
  --role-name EC2-S3-ReadRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create instance profile (required to attach role to EC2)
aws iam create-instance-profile --instance-profile-name EC2-S3-Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-S3-Profile \
  --role-name EC2-S3-ReadRole
```

---

## 2.2 IAM Policies Deep Dive

A **policy** is a JSON document that defines permissions. Policies are attached to identities (users, groups, roles) or resources.

### Policy Structure

```json
{
  "Version": "2012-10-17",       // Always use this version
  "Statement": [
    {
      "Sid": "AllowS3ReadInProd",   // Optional: Statement ID (label)
      "Effect": "Allow",             // Allow or Deny
      "Principal": {                 // WHO (only in resource-based policies)
        "AWS": "arn:aws:iam::123456789012:user/alice"
      },
      "Action": [                    // WHAT actions
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [                  // ON WHAT resources
        "arn:aws:s3:::my-prod-bucket",
        "arn:aws:s3:::my-prod-bucket/*"
      ],
      "Condition": {                 // WHEN (optional constraints)
        "StringEquals": {
          "s3:prefix": ["prod/"]
        },
        "Bool": {
          "aws:SecureTransport": "true"
        }
      }
    }
  ]
}
```

### Policy Types

```
┌──────────────────────────────────────────────────────────────┐
│                     IAM POLICY TYPES                         │
│                                                              │
│  IDENTITY-BASED POLICIES (attached to users/groups/roles)   │
│  ├── AWS Managed — created/maintained by AWS                 │
│  ├── Customer Managed — you create and manage               │
│  └── Inline — embedded directly in an identity              │
│                                                              │
│  RESOURCE-BASED POLICIES (attached to resources)            │
│  └── S3 bucket policies, SQS queue policies, KMS key policy │
│      Trust policies on IAM roles (who can assume the role)  │
│                                                              │
│  PERMISSION BOUNDARIES (max permissions ceiling)            │
│  └── Identity-based policy that limits maximum permissions  │
│                                                              │
│  SERVICE CONTROL POLICIES (SCPs) — AWS Organizations        │
│  └── Applied to OUs/accounts; limit maximum permissions     │
│                                                              │
│  SESSION POLICIES — passed via STS AssumeRole               │
│  └── Limit permissions of a temporary session               │
└──────────────────────────────────────────────────────────────┘
```

### Policy Evaluation Logic

```
                    Is there an explicit DENY?
                           │
                    ┌──────┴──────┐
                   YES            NO
                    │              │
                  DENY       Is there an SCP DENY?
                                   │
                            ┌──────┴──────┐
                           YES            NO
                            │              │
                          DENY       Is there a Permissions Boundary?
                                           │
                                    ┌──────┴──────┐
                                   YES            NO
                                    │              │
                             (Boundary limits  Is there an Allow?
                              effective perms)  │
                                           ┌────┴────┐
                                          YES        NO
                                           │          │
                                         ALLOW      DENY (implicit)
```

**Key Rule: Explicit DENY always wins, regardless of any ALLOW.**

### Common Policy Examples

**1. S3 Bucket Policy — Enforce HTTPS only:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyHTTP",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

**2. IAM Policy — Allow EC2 actions only in specific region:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:*",
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

**3. Require MFA for sensitive operations:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyWithoutMFA",
      "Effect": "Deny",
      "Action": ["iam:*", "ec2:TerminateInstances"],
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

## 2.3 Multi-Factor Authentication (MFA)

MFA adds a second factor beyond username/password.

### MFA Types
| Type | Description | Example |
|------|-------------|---------|
| Virtual MFA | Software TOTP authenticator | Google Authenticator, Authy |
| Hardware MFA | Physical TOTP device | Gemalto token |
| U2F/FIDO | USB security key | YubiKey |
| SMS (legacy) | Text message (not recommended) | — |

```bash
# Enable MFA for a user (virtual device)
# First, create virtual MFA device
aws iam create-virtual-mfa-device \
  --virtual-mfa-device-name alice-mfa \
  --outfile /tmp/alice-qr.png \
  --bootstrap-method QRCodePNG

# Enable MFA using two consecutive codes from authenticator
aws iam enable-mfa-device \
  --user-name alice \
  --serial-number arn:aws:iam::123456789012:mfa/alice-mfa \
  --authentication-code1 123456 \
  --authentication-code2 789012
```

### Enforcing MFA via Policy
```bash
# Apply MFA enforcement policy to all developers
aws iam put-group-policy \
  --group-name Developers \
  --policy-name ForceMFA \
  --policy-document file://force-mfa-policy.json
```

---

## 2.4 IAM Best Practices (SysOps Checklist)

```
IAM Security Checklist:
□ Lock away root account credentials
□ Enable MFA on root account
□ Create individual IAM users (no shared accounts)
□ Assign permissions to groups, not users
□ Grant least privilege access
□ Use IAM roles for EC2/Lambda/ECS — never embed access keys
□ Use AWS managed policies as starting point
□ Rotate access keys regularly (90 days max)
□ Remove unused credentials (IAM Access Analyzer)
□ Monitor with CloudTrail and IAM Access Advisor
□ Use password policy (minimum length, complexity, rotation)
□ Enable AWS Organizations with SCPs
□ Use Permission Boundaries for developer self-service
```

```bash
# Set account password policy
aws iam update-account-password-policy \
  --minimum-password-length 14 \
  --require-symbols \
  --require-numbers \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --allow-users-to-change-password \
  --max-password-age 90 \
  --password-reuse-prevention 24 \
  --hard-expiry

# Find users with old access keys (credential report)
aws iam generate-credential-report
aws iam get-credential-report \
  --output text --query Content | base64 -d > credentials.csv
```

---

## 2.5 Permission Boundaries

A permission boundary is an **advanced feature** that limits the maximum permissions an identity can have, even if the identity-based policy allows more.

### Use Case: Allowing Developers to Create Roles (Self-Service)
Without boundaries, developers with `iam:CreateRole` could create admin roles and escalate privileges. Boundaries prevent this.

```json
// Permission Boundary — Developer can only do S3 and EC2
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "ec2:*",
        "cloudwatch:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

```bash
# Create the permission boundary policy
aws iam create-policy \
  --policy-name DeveloperBoundary \
  --policy-document file://dev-boundary.json

# Create IAM role WITH a permission boundary
aws iam create-role \
  --role-name dev-role \
  --assume-role-policy-document file://trust-policy.json \
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary

# Attach permissions boundary to existing user
aws iam put-user-permissions-boundary \
  --user-name alice \
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary
```

---

## 2.6 AWS STS — Security Token Service

STS issues **temporary, limited-privilege credentials** (Access Key + Secret Key + Session Token).

### AssumeRole — Cross-Account Access

```
Account A (Trusting)         Account B (Trusted)
┌──────────────────┐         ┌──────────────────┐
│  IAM User Alice  │─────►   │  IAM Role        │
│  sts:AssumeRole  │  STS    │  (Trust Policy   │
│                  │◄────────│  allows Account A│
│  Temp Credentials│         │  to assume it)   │
└──────────────────┘         └──────────────────┘
```

**Step 1: Create role in Account B with trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

**Step 2: Assume role from Account A:**
```bash
# Assume the cross-account role
aws sts assume-role \
  --role-arn arn:aws:iam::222222222222:role/CrossAccountRole \
  --role-session-name alice-session \
  --duration-seconds 3600

# Use returned credentials
export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
```

```python
import boto3

# Assume cross-account role programmatically
sts = boto3.client('sts')
response = sts.assume_role(
    RoleArn='arn:aws:iam::222222222222:role/CrossAccountRole',
    RoleSessionName='automation-session',
    DurationSeconds=3600
)

creds = response['Credentials']
s3 = boto3.client(
    's3',
    aws_access_key_id=creds['AccessKeyId'],
    aws_secret_access_key=creds['SecretAccessKey'],
    aws_session_token=creds['SessionToken']
)
```

---

## 2.7 AWS IAM Identity Center (formerly SSO)

IAM Identity Center provides **centralized access management** for multiple AWS accounts and applications using a single sign-on experience.

```
                    ┌─────────────────────┐
                    │  Identity Provider   │
                    │  (Azure AD, Okta,   │
                    │   Active Directory)  │
                    └──────────┬──────────┘
                               │ SAML 2.0
                    ┌──────────▼──────────┐
                    │  AWS IAM Identity   │
                    │      Center         │
                    └──────────┬──────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Account │     │ Account │     │ Account │
        │   Dev   │     │  Prod   │     │ Audit   │
        │         │     │         │     │         │
        │ DevRole │     │ ReadOnly│     │ Admin   │
        └─────────┘     └─────────┘     └─────────┘
```

**Benefits over individual IAM users:**
- One set of credentials for all accounts
- Integrates with enterprise IdPs (Azure AD, Okta)
- Permission Sets reusable across accounts
- Automatic provisioning via SCIM
- Access portal for users to switch accounts

```bash
# List permission sets
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxxxxxxx

# Assign permission set to account
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxxxxxxx \
  --target-id 123456789012 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xx/ps-xx \
  --principal-type GROUP \
  --principal-id group-id-from-idp
```

---

## 2.8 AWS Organizations & Service Control Policies (SCPs)

### SCPs — The Key Points for SysOps Exam
1. SCPs apply to the **root, OUs, or individual accounts** in an organization
2. SCPs **DO NOT** apply to the management account
3. SCPs affect all IAM users, roles, and the root user of member accounts
4. SCPs are **not grants** — they are guardrails that filter what IAM can allow
5. The effective permissions = **intersection** of SCP Allow + IAM Allow

### Critical SCP Examples

**Deny all actions outside approved regions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnapprovedRegions",
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
        "trustedadvisor:*",
        "health:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    }
  ]
}
```

**Protect security baselines:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ProtectSecurityServices",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:DeleteTrail",
        "cloudtrail:StopLogging",
        "config:DeleteConfigRule",
        "config:DeleteConfigurationRecorder",
        "config:StopConfigurationRecorder",
        "guardduty:DeleteDetector",
        "guardduty:DisassociateFromMasterAccount",
        "securityhub:DisableSecurityHub"
      ],
      "Resource": "*"
    }
  ]
}
```

**Require EC2 instances to use approved AMIs:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireApprovedAMI",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotLike": {
          "ec2:ImageID": "ami-company-approved-*"
        }
      }
    }
  ]
}
```

---

## 2.9 IAM Access Analyzer

IAM Access Analyzer helps you identify resources that are shared with **external entities** (outside your AWS account or organization).

```bash
# Create an analyzer for your account
aws accessanalyzer create-analyzer \
  --analyzer-name account-analyzer \
  --type ACCOUNT

# Or organization-wide analyzer (from management account)
aws accessanalyzer create-analyzer \
  --analyzer-name org-analyzer \
  --type ORGANIZATION

# List findings (externally accessible resources)
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-analyzer

# Validate an IAM policy before deploying
aws accessanalyzer validate-policy \
  --policy-document file://my-policy.json \
  --policy-type IDENTITY_POLICY
```

**Access Analyzer Findings:**
- S3 buckets with public access or cross-account access
- IAM roles with external trust relationships
- KMS keys with external key access
- Lambda functions with resource-based policies allowing external access
- SQS queues accessible from outside the account

---

## 2.10 IAM Credential Management

### Credential Report
Lists all IAM users and the status of their credentials:
```bash
# Generate and download
aws iam generate-credential-report
aws iam get-credential-report --output text --query Content | base64 -d

# Fields: user, arn, user_creation_time, password_enabled, 
#         password_last_used, password_last_changed,
#         access_key_1_active, access_key_1_last_used_date,
#         access_key_2_active, access_key_2_last_used_date,
#         mfa_active
```

### Access Advisor
Shows service permissions granted to an identity and when each service was last accessed:
```bash
# Get last accessed services for a role
JOB_ID=$(aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:role/MyRole \
  --query JobId --output text)

aws iam get-service-last-accessed-details --job-id $JOB_ID
```

### Automated Credential Rotation
```python
import boto3
from datetime import datetime, timezone, timedelta

iam = boto3.client('iam')

def find_old_access_keys(max_age_days=90):
    """Find access keys older than max_age_days."""
    users = iam.list_users()['Users']
    old_keys = []
    
    for user in users:
        keys = iam.list_access_keys(UserName=user['UserName'])['AccessKeyMetadata']
        for key in keys:
            age = (datetime.now(timezone.utc) - key['CreateDate']).days
            if age > max_age_days and key['Status'] == 'Active':
                old_keys.append({
                    'user': user['UserName'],
                    'key_id': key['AccessKeyId'],
                    'age_days': age
                })
    return old_keys

old_keys = find_old_access_keys()
for k in old_keys:
    print(f"⚠️  User: {k['user']}, Key: {k['key_id']}, Age: {k['age_days']} days")
```

---

## 2.11 AWS IAM Roles for AWS Services

### EC2 Instance Profiles

**Always use IAM roles for EC2 — never hardcode credentials!**

```bash
# Attach role to running EC2 instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-1234567890abcdef0 \
  --iam-instance-profile Name=EC2-S3-Profile

# Verify role on instance (from EC2 metadata)
# curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
# Returns: role name

# Get temporary credentials (from inside EC2)
# curl http://169.254.169.254/latest/meta-data/iam/security-credentials/EC2-S3-ReadRole
# Returns: AccessKeyId, SecretAccessKey, Token, Expiration
```

### Lambda Execution Role
```json
// Lambda basic execution role trust policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

```bash
# Create Lambda execution role
aws iam create-role \
  --role-name LambdaBasicRole \
  --assume-role-policy-document file://lambda-trust-policy.json

aws iam attach-role-policy \
  --role-name LambdaBasicRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

---

## 2.12 Real-World Project: Secure IAM Setup for a DevOps Team

### Scenario
A startup has 10 developers, 3 DevOps engineers, and 2 security admins. Need to implement least-privilege access with self-service for developers.

### Solution Architecture

```
                    AWS Organization
                           │
                    ┌──────┴──────┐
              Dev Account    Prod Account
                    │
         ┌──────────┼──────────┐
         │          │          │
    Developers   DevOps    Security
      Group       Group      Group
         │          │          │
    Dev Perms   DevOps    Security
    + Boundary  Perms     Full Access
```

**Step 1: Create groups with policies**
```bash
# Developer Group — can only manage their own resources
aws iam create-group --group-name Developers
aws iam attach-group-policy \
  --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# DevOps Group — can manage infrastructure
aws iam create-group --group-name DevOps
aws iam attach-group-policy \
  --group-name DevOps \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Security Group — read-only + security services
aws iam create-group --group-name SecurityAdmins
aws iam attach-group-policy \
  --group-name SecurityAdmins \
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit
```

**Step 2: Developer Permission Boundary (prevents privilege escalation)**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*", "dynamodb:*", "lambda:*",
        "apigateway:*", "cloudwatch:*", "logs:*",
        "ec2:Describe*", "ecs:*", "ecr:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:PutRolePolicy"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PermissionsBoundary": "arn:aws:iam::123456789012:policy/DeveloperBoundary"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": [
        "organizations:*",
        "account:*",
        "iam:CreateUser",
        "iam:DeleteUser",
        "iam:CreateGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

**Step 3: Automate user onboarding**
```python
import boto3

iam = boto3.client('iam')

def onboard_developer(username: str, email: str, temp_password: str):
    """Onboard a new developer with proper security settings."""
    # Create user
    iam.create_user(
        UserName=username,
        Tags=[
            {'Key': 'Email', 'Value': email},
            {'Key': 'Team', 'Value': 'Engineering'}
        ]
    )
    
    # Set permission boundary
    iam.put_user_permissions_boundary(
        UserName=username,
        PermissionsBoundary='arn:aws:iam::123456789012:policy/DeveloperBoundary'
    )
    
    # Add to Developers group
    iam.add_user_to_group(GroupName='Developers', UserName=username)
    
    # Set temporary console password (must change on first login)
    iam.create_login_profile(
        UserName=username,
        Password=temp_password,
        PasswordResetRequired=True
    )
    
    # Tag for tracking
    print(f"✅ User {username} created with Developer permissions")
    print(f"   Console login: https://123456789012.signin.aws.amazon.com/console")
    print(f"   Temp password: {temp_password}")
    print(f"   ⚠️  Must enable MFA after first login")

onboard_developer('bob', 'bob@company.com', 'TempPass123!')
```

---

## 2.13 Practice Questions (SysOps Exam Level)

**Q1:** A developer accidentally deleted production data using their IAM user credentials. Which COMBINATION of changes would prevent this from happening again?

**A:**
1. Apply a **Permission Boundary** limiting developers' maximum permissions (exclude delete operations on prod)
2. Create an **SCP** that denies destructive actions on tagged production resources
3. Use **resource-based policies** (S3 bucket policies) to deny delete without MFA
4. Enable **S3 MFA Delete** on critical buckets

---

**Q2:** Your company's security audit found that an IAM role has `*:*` (admin) permissions but was created by a developer. How do you investigate and remediate?

**A:**
1. Check **CloudTrail** for who created the role and when
2. Use **IAM Access Analyzer** to see if the role is used externally
3. Use **Access Advisor** to see what services the role actually accesses
4. Apply **Permission Boundary** to limit the role immediately
5. Use **AWS IAM Policy Simulator** to test effects before replacing the policy
6. Replace with least-privilege policy based on Access Advisor data

```bash
# Check who created the role via CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateRole \
  --start-time 2025-01-01 \
  --end-time 2025-12-31 \
  --query 'Events[?contains(Resources[].ResourceName, `AdminRole`)].{User:Username,Time:EventTime}'
```

---

**Q3:** You need to allow an application in Account A to read from an S3 bucket in Account B. What is the MINIMUM required?

**A:**
- **Option 1 (Resource-based policy):** Add a bucket policy in Account B allowing Account A's role/user. The identity in Account A also needs IAM permission to access S3.
- **Option 2 (Cross-account role):** Create a role in Account B with S3 access. Update trust policy to allow Account A to assume it. Have Account A assume the role via STS.

For cross-account S3 access:
1. Account B bucket policy must allow Account A
2. Account A IAM identity must have `s3:GetObject` permission (or the role in Account B must be assumed)

---

**Q4:** An EC2 instance is running an application that needs to access DynamoDB and SSM Parameter Store. What is the BEST way to provide these credentials?

**A:** Create an **IAM Instance Profile** with a role that has exactly the permissions needed:
- `dynamodb:GetItem`, `dynamodb:PutItem`, etc. on specific table ARNs
- `ssm:GetParameter` on specific parameter paths

Never use access keys on EC2. The instance metadata service (IMDS) automatically provides rotating temporary credentials.

---

**Q5:** What happens when both an SCP and an IAM policy are applied to an IAM user? The SCP allows only S3 access, but the IAM policy allows S3 and EC2.

**A:** The **effective permissions are the intersection** — only S3 is allowed. SCPs set the maximum permissions ceiling. Even though the IAM policy allows EC2, the SCP restricts it. The effective permission = S3 only.

---

## Key IAM Terms for Exam

| Term | Definition |
|------|-----------|
| Principal | Entity making request (user, role, service) |
| Authentication | Verifying identity (password, access key, MFA) |
| Authorization | Determining allowed actions (policies) |
| Trust Policy | Who can assume a role (attached to role) |
| Permission Policy | What actions are allowed/denied |
| Permission Boundary | Maximum permissions ceiling for identity |
| SCP | Organization-wide guardrails (not grants) |
| ARN | Amazon Resource Name — unique resource identifier |
| STS | Security Token Service — issues temporary credentials |
| Instance Profile | Container for IAM role assigned to EC2 |
| OIDC | OpenID Connect — modern federation for web/mobile |
| SAML 2.0 | Enterprise federation (Active Directory, Okta) |
