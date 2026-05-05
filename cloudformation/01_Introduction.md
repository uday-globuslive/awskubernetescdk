# CloudFormation Chapter 1: Introduction to Infrastructure as Code
## Why IaC, CloudFormation Concepts, and Getting Started

---

## 1.1 Infrastructure as Code (IaC) Fundamentals

```
Traditional Infrastructure Management:
  - Manual clicks in console → Not reproducible, error-prone, not auditable
  - Shell scripts → Imperative (HOW), not idempotent, hard to maintain
  
Infrastructure as Code:
  - Declarative (WHAT you want) → CloudFormation, CDK
  - Idempotent (same result every run)
  - Version-controlled (Git history = audit trail)
  - Reviewable (code review for infrastructure changes)
  - Tested (unit tests, linting, compliance checks)

┌──────────────────────────────────────────────────────────────────┐
│              IaC TOOL COMPARISON                                  │
├─────────────────┬──────────────────┬────────────────────────────┤
│ Tool            │ Language         │ Scope                      │
├─────────────────┼──────────────────┼────────────────────────────┤
│ CloudFormation  │ YAML/JSON        │ AWS only, native, free     │
│ CDK             │ Python/TS/Java/Go│ AWS, generates CFN        │
│ Terraform       │ HCL              │ Multi-cloud, community     │
│ Pulumi          │ Python/TS/Go     │ Multi-cloud, code-based   │
│ Ansible         │ YAML             │ Config management + IaC   │
└─────────────────┴──────────────────┴────────────────────────────┘
```

---

## 1.2 CloudFormation Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                CLOUDFORMATION WORKFLOW                               │
│                                                                      │
│  Template (YAML/JSON)                                                │
│       │                                                              │
│       ▼                                                              │
│  CloudFormation Service                                              │
│       │                                                              │
│       ├── Validate template syntax                                   │
│       ├── Parse parameters and mappings                              │
│       ├── Resolve dependencies (DependsOn, Ref, GetAtt)             │
│       ├── Call AWS APIs to provision resources                       │
│       └── Track state in Stack                                       │
│                                                                      │
│  Stack States:                                                       │
│    CREATE_IN_PROGRESS → CREATE_COMPLETE                             │
│    UPDATE_IN_PROGRESS → UPDATE_COMPLETE                             │
│    DELETE_IN_PROGRESS → DELETE_COMPLETE                             │
│    *_FAILED (with rollback)                                          │
└─────────────────────────────────────────────────────────────────────┘

Key Benefits:
  Drift Detection:    CloudFormation notices if someone manually changed a resource
  Stack Rollback:     If any resource fails, entire stack rolls back automatically
  Change Sets:        Preview changes BEFORE applying (like git diff for infrastructure)
  Outputs:           Export values for cross-stack references
  Nested Stacks:     Decompose large templates into manageable modules
  StackSets:         Deploy the same stack across multiple accounts/regions
```

---

## 1.3 Your First CloudFormation Template

```yaml
# hello-s3.yaml — Create an S3 bucket with basic settings
AWSTemplateFormatVersion: '2010-09-09'
Description: My first CloudFormation template — creates an S3 bucket

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Default: dev
    Description: Deployment environment

  BucketSuffix:
    Type: String
    MaxLength: 20
    AllowedPattern: '[a-z0-9-]+'
    Description: Unique suffix for bucket name (lowercase, numbers, hyphens only)

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'my-app-${Environment}-${BucketSuffix}'
      VersioningConfiguration:
        Status: !If [IsProd, Enabled, Suspended]
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: delete-old-versions
            Status: Enabled
            NoncurrentVersionExpiration:
              NoncurrentDays: 30
      Tags:
        - Key: Environment
          Value: !Ref Environment

Outputs:
  BucketName:
    Description: Name of the created S3 bucket
    Value: !Ref MyBucket
    Export:
      Name: !Sub '${AWS::StackName}-BucketName'

  BucketArn:
    Description: ARN of the S3 bucket
    Value: !GetAtt MyBucket.Arn
    Export:
      Name: !Sub '${AWS::StackName}-BucketArn'
```

---

## 1.4 CloudFormation CLI Operations

```bash
# ── VALIDATE ─────────────────────────────────────────────
aws cloudformation validate-template \
  --template-body file://hello-s3.yaml

# ── CREATE STACK ─────────────────────────────────────────
aws cloudformation create-stack \
  --stack-name my-first-stack \
  --template-body file://hello-s3.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=dev \
    ParameterKey=BucketSuffix,ParameterValue=myapp123 \
  --tags Key=Project,Value=demo Key=Owner,Value=myteam \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --on-failure ROLLBACK    # ROLLBACK (default) | DO_NOTHING | DELETE

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name my-first-stack

# ── DESCRIBE STACK ───────────────────────────────────────
aws cloudformation describe-stacks \
  --stack-name my-first-stack \
  --query "Stacks[0].{Status:StackStatus,Outputs:Outputs,Parameters:Parameters}"

# ── CREATE CHANGE SET (preview changes) ──────────────────
aws cloudformation create-change-set \
  --stack-name my-first-stack \
  --change-set-name update-versioning \
  --template-body file://hello-s3-v2.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=prod \
    ParameterKey=BucketSuffix,UsePreviousValue=true \
  --capabilities CAPABILITY_IAM

# Review the change set before applying
aws cloudformation describe-change-set \
  --stack-name my-first-stack \
  --change-set-name update-versioning \
  --query "Changes[*].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Replace:ResourceChange.Replacement}"

# Apply the change set
aws cloudformation execute-change-set \
  --stack-name my-first-stack \
  --change-set-name update-versioning

# ── UPDATE STACK ─────────────────────────────────────────
aws cloudformation update-stack \
  --stack-name my-first-stack \
  --template-body file://hello-s3-v2.yaml \
  --parameters ParameterKey=Environment,UsePreviousValue=true \
               ParameterKey=BucketSuffix,UsePreviousValue=true

# ── DETECT DRIFT ─────────────────────────────────────────
aws cloudformation detect-stack-drift --stack-name my-first-stack
aws cloudformation describe-stack-resource-drifts \
  --stack-name my-first-stack \
  --stack-resource-drift-status-filters MODIFIED DELETED

# ── GET STACK EVENTS (debug failures) ────────────────────
aws cloudformation describe-stack-events \
  --stack-name my-first-stack \
  --query "StackEvents[?ResourceStatus=='CREATE_FAILED'].[ResourceType,ResourceStatusReason]"

# ── DELETE STACK ─────────────────────────────────────────
# First empty S3 bucket (required before deletion)
aws s3 rm s3://my-app-dev-myapp123 --recursive
aws cloudformation delete-stack --stack-name my-first-stack
aws cloudformation wait stack-delete-complete --stack-name my-first-stack
```

---

## 1.5 CloudFormation Service Limits and Quotas

```
Template:
  Max size (S3):           1 MB
  Max size (direct):       51,200 bytes
  
Stack:
  Max resources per stack:  500
  Max stacks per account:   10,000 (soft limit)
  Max outputs per stack:    200
  Max parameters:           200

StackSets:
  Max stack sets:           100 per administrator account
  Max stack instances:      2,000 per stack set
```

---

## 1.6 Interview Q&A

**Q: What is the difference between CloudFormation and Terraform?**
A: CloudFormation is AWS-native, free, deeply integrated with AWS services (no separate state management needed — AWS stores state), and supports all AWS services on day one. Terraform is multi-cloud, open-source, uses HCL language, requires state management (remote state in S3+DynamoDB), and has a large community module ecosystem. CloudFormation has Change Sets (native preview), StackSets (multi-account deploy), and CDK integration. Terraform has better multi-cloud support and Terraform Cloud for collaboration. Most AWS-only shops use CloudFormation or CDK; multi-cloud shops use Terraform.

**Q: What happens when a CloudFormation stack update fails?**
A: By default, CloudFormation rolls back all changes to the previous state. This includes: stopping any in-progress resource creates/updates, deleting resources that were created during the failed update, reverting resources that were modified. You can disable rollback with `--disable-rollback` for debugging (examine the failed state). Stack ends in `UPDATE_ROLLBACK_COMPLETE` (successful rollback) or `UPDATE_ROLLBACK_FAILED` (couldn't even rollback — requires manual intervention or deleting/retaining problematic resources).

**Q: What is a CloudFormation Change Set and why should you use it?**
A: A Change Set shows exactly what changes CloudFormation will make BEFORE applying them, similar to `terraform plan`. It shows: which resources will be Added, Modified, or Removed, and whether a modification requires Replacement (i.e., the resource will be deleted and recreated — potential data loss for stateful resources like RDS). Always use Change Sets in production to review: (1) accidental deletions, (2) resource replacements, (3) unexpected side effects of parameter changes. Mandatory for compliance in many organizations.
