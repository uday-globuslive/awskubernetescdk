# Chapter 1: Introduction to CloudFormation
## Infrastructure as Code on AWS

---

## 1.1 What is CloudFormation?

CloudFormation is AWS's native Infrastructure as Code (IaC) service. You describe your desired infrastructure in a template (YAML or JSON), and CloudFormation creates, updates, and deletes the actual AWS resources to match.

```
┌──────────────────────────────────────────────────────────────┐
│                HOW CLOUDFORMATION WORKS                      │
│                                                              │
│  You write:          CloudFormation does:                    │
│  ──────────          ──────────────────                      │
│  template.yaml  ──►  1. Parse template                       │
│  (desired state)     2. Calculate dependency order           │
│                      3. Call AWS APIs to create resources    │
│                      4. Wait for each resource               │
│                      5. Roll back if anything fails          │
│                      6. Track state in a "stack"             │
└──────────────────────────────────────────────────────────────┘
```

---

## 1.2 Why CloudFormation?

```
Without IaC:
• Click around the console — no record of what was done
• Can't reproduce in another environment
• Drift: production differs from staging
• Can't review infrastructure changes in PRs
• Manual disaster recovery takes hours

With CloudFormation:
• Template in Git = full history of infrastructure changes
• Same template deploys to dev, staging, prod
• Code review for infrastructure changes
• Stack rollback on failure
• Drift detection
• Can re-create entire environment in minutes
```

---

## 1.3 CloudFormation vs Other IaC Tools

```
┌─────────────────────────────────────────────────────────────┐
│              IaC TOOLS COMPARISON                           │
├──────────────────┬────────────────────────────────────────── │
│ CloudFormation   │ AWS-native, free, deep integration,      │
│                  │ YAML/JSON, declarative                    │
├──────────────────┼──────────────────────────────────────────┤
│ AWS CDK          │ CloudFormation generated from Python/TS  │
│                  │ Code, not templates; higher abstraction   │
├──────────────────┼──────────────────────────────────────────┤
│ Terraform        │ Multi-cloud, HCL, large community,       │
│                  │ state file management required            │
├──────────────────┼──────────────────────────────────────────┤
│ Pulumi           │ Real code (Python/TypeScript), multi-    │
│                  │ cloud, like CDK but not AWS-specific      │
└──────────────────┴──────────────────────────────────────────┘

Choose CloudFormation when:
• AWS-only workload
• Team prefers YAML/JSON over code
• Want zero-cost IaC with full AWS feature coverage
• Need stack-level rollback and change sets
```

---

## 1.4 Core Concepts

```
Stack
  A collection of AWS resources managed as a unit.
  All resources in one template = one stack.
  Create/update/delete the stack → all resources managed together.

Template
  The YAML or JSON file describing the resources.
  Uploaded to S3 or passed directly to CloudFormation.
  Up to 51,200 bytes inline; up to 1MB via S3.

Change Set
  Preview of what will change before you apply it.
  Like "git diff" for infrastructure.
  Create → review → execute (or discard).

Drift Detection
  Detect when actual AWS resource configuration differs
  from what CloudFormation last deployed.
  e.g., someone manually changed a security group.

Stack Set
  Deploy one template to multiple accounts and regions.
  Useful for organisation-wide baseline resources.
```

---

## 1.5 Setting Up: Install Tools

```bash
# Install AWS CLI
# Windows (PowerShell):
winget install Amazon.AWSCLI
# macOS:
brew install awscli
# Linux:
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip && sudo ./aws/install

# Configure CLI
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (e.g., us-east-1), output format (json)

# Install cfn-lint (CloudFormation template linter)
pip install cfn-lint

# Install cfn_nag (security scanner for templates)
gem install cfn-nag
```

---

## 1.6 Your First CloudFormation Stack

Let's deploy an S3 bucket — the simplest possible template.

```yaml
# first-stack.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: My first CloudFormation stack — an S3 bucket

Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "my-first-bucket-${AWS::AccountId}"
      VersioningConfiguration:
        Status: Enabled

Outputs:
  BucketName:
    Description: The name of the S3 bucket
    Value: !Ref MyBucket
  BucketArn:
    Description: The ARN of the S3 bucket
    Value: !GetAtt MyBucket.Arn
```

```bash
# Lint the template first
cfn-lint first-stack.yaml

# Deploy (create stack)
aws cloudformation deploy \
  --template-file first-stack.yaml \
  --stack-name my-first-stack \
  --region us-east-1

# Check stack status
aws cloudformation describe-stacks \
  --stack-name my-first-stack \
  --query "Stacks[0].StackStatus"

# View outputs
aws cloudformation describe-stacks \
  --stack-name my-first-stack \
  --query "Stacks[0].Outputs"

# View all resources created
aws cloudformation list-stack-resources \
  --stack-name my-first-stack

# Delete stack (deletes the bucket too)
aws cloudformation delete-stack --stack-name my-first-stack
```

---

## 1.7 Deployment Commands Reference

```bash
# Deploy (create or update — most common command)
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name my-stack \
  --parameter-overrides Env=prod AppName=myapp \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --no-fail-on-empty-changeset

# CAPABILITY_IAM is required when template creates IAM resources
# CAPABILITY_NAMED_IAM is required when template creates named IAM resources

# Create change set (review before applying)
aws cloudformation create-change-set \
  --stack-name my-stack \
  --template-body file://template.yaml \
  --change-set-name my-changes \
  --capabilities CAPABILITY_IAM

# View change set (what will change?)
aws cloudformation describe-change-set \
  --stack-name my-stack \
  --change-set-name my-changes \
  --query "Changes[*].[Type,ResourceChange.Action,ResourceChange.LogicalResourceId,ResourceChange.Replacement]"

# Execute change set
aws cloudformation execute-change-set \
  --stack-name my-stack \
  --change-set-name my-changes

# Watch deployment events in real time
aws cloudformation describe-stack-events \
  --stack-name my-stack \
  --query "StackEvents[*].[Timestamp,ResourceStatus,LogicalResourceId,ResourceStatusReason]" \
  --max-items 20
```

---

## 1.8 Stack States

```
CREATE_IN_PROGRESS  → Being created
CREATE_COMPLETE     → Created successfully
CREATE_FAILED       → Failed, auto-rollback started
ROLLBACK_COMPLETE   → Failed + rolled back (all resources deleted)

UPDATE_IN_PROGRESS  → Being updated
UPDATE_COMPLETE     → Updated successfully
UPDATE_ROLLBACK_COMPLETE → Failed update, rolled back to previous state

DELETE_IN_PROGRESS  → Being deleted
DELETE_COMPLETE     → Deleted
DELETE_FAILED       → Deletion failed (e.g., non-empty S3 bucket)
```

---

## 1.9 cfn-lint — Template Linting

```bash
# Lint a template
cfn-lint template.yaml

# Lint with specific region (validates region-specific features)
cfn-lint template.yaml --region us-east-1

# Lint and output as JSON (for CI pipelines)
cfn-lint template.yaml --format json

# Common errors cfn-lint catches:
# E3001: Invalid resource type
# E3002: Invalid property
# E3003: Invalid property type
# W2001: Unused parameter
# W3002: Should use !Sub instead of string concatenation
```

---

## 1.10 Interview Questions

**Q: What is the difference between a CloudFormation stack and a template?**
> A template is the YAML/JSON file that describes the desired infrastructure — it's the blueprint. A stack is what CloudFormation creates from a template — the live collection of AWS resources managed as a unit. One template can be used to create many stacks (e.g., dev, staging, prod stacks from the same template). The stack tracks all resources and their current state; if you delete a stack, all its resources are deleted too (unless DeletionPolicy is set to Retain).

**Q: What happens when a CloudFormation deployment fails?**
> By default, CloudFormation rolls back the entire stack to the previous known-good state. On a new stack creation failure, it deletes all resources created so far. On an update failure, it reverts all resources to their pre-update configuration. You can disable rollback (--disable-rollback) to keep failed resources for debugging. The stack goes into ROLLBACK_COMPLETE (new create) or UPDATE_ROLLBACK_COMPLETE (failed update). You can see exactly which resource failed and why in the stack events.

**Q: What is a change set and when would you use it?**
> A change set is a preview of what changes CloudFormation will make before you execute them — similar to terraform plan. It shows which resources will be created, modified, or deleted, and critically, whether any modification requires replacing a resource (which means downtime for that resource). Always use change sets in production before applying an update: it prevents surprises, enables review in a PR, and lets you verify that no critical resources will be replaced unexpectedly.
