
content = r"""# Chapter 9: Deployment, Automation & Systems Manager
## (How Professionals Deploy and Manage AWS at Scale)

---

## 9.1 Infrastructure as Code — Why Manual Clicking is Bad

### The Problem with Clicking in the Console

Imagine a team of 5 engineers each building an environment by clicking in the AWS Console:
- Engineer Alice sets up the VPC one way
- Engineer Bob sets up a similar VPC slightly differently
- Next month, nobody remembers exactly what settings were used
- When something goes wrong: "What did we set for the security group? I think it was port 8080... or was it 8000?"
- Building a new environment takes 3 days of clicking and documenting

**Infrastructure as Code (IaC)** solves this by defining infrastructure in code files:
- Version controlled in Git (full history of every change)
- Repeatable (run the same template, get the exact same result every time)
- Auditable ("Alice changed the security group port on January 15, 2025")
- Automated (no manual clicking — run a command)
- Testable (validate templates before deploying)

AWS provides two main IaC tools: **CloudFormation** (AWS-native) and you can also use Terraform (third-party, multi-cloud).

---

## 9.2 CloudFormation — AWS's Native IaC

### What is CloudFormation?

**CloudFormation** lets you define your entire AWS infrastructure in YAML or JSON files called **templates**. When you run the template, AWS creates all the resources in the right order, handling dependencies automatically.

**Analogy:** CloudFormation is like a detailed recipe for your infrastructure. The recipe lists every ingredient (resource) in the correct order (dependencies). Anyone with the recipe can make the exact same dish (environment) every time.

### CloudFormation Template Structure

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'What this template creates'

# ── Parameters ───────────────────────────────────────────────────────
# Variables you provide when deploying (makes template reusable)
Parameters:
  EnvironmentName:
    Type: String
    Default: production
    AllowedValues: [development, staging, production]
    Description: 'Deployment environment'
  
  InstanceType:
    Type: String
    Default: t3.micro
    AllowedValues: [t3.micro, t3.small, t3.medium, t3.large]
  
  DBPassword:
    Type: String
    NoEcho: true  # Hides the value in console and CloudTrail
    MinLength: 8
    MaxLength: 41
    Description: 'Database password (8-41 characters)'

# ── Mappings ─────────────────────────────────────────────────────────
# Lookup tables (like a dictionary)
Mappings:
  RegionAMI:
    us-east-1:
      AmazonLinux2023: ami-0c02fb55956c7d316
    us-west-2:
      AmazonLinux2023: ami-0ceecbb0f30a902a6
    eu-west-1:
      AmazonLinux2023: ami-0694d931cee176e7d

# ── Conditions ───────────────────────────────────────────────────────
# Conditionally create resources based on parameters
Conditions:
  IsProduction: !Equals [!Ref EnvironmentName, production]
  IsNotDevelopment: !Not [!Equals [!Ref EnvironmentName, development]]

# ── Resources ────────────────────────────────────────────────────────
# The actual AWS resources to create (required section)
Resources:
  
  # EC2 Instance
  WebServer:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !FindInMap [RegionAMI, !Ref AWS::Region, AmazonLinux2023]
      InstanceType: !Ref InstanceType
      Tags:
        - Key: Name
          Value: !Sub '${EnvironmentName}-web-server'
        - Key: Environment
          Value: !Ref EnvironmentName
  
  # Security Group (with conditional rule)
  WebSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: 'Web server security group'
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        # Only allow SSH in non-production environments
        - !If
          - IsNotDevelopment
          - !Ref AWS::NoValue  # Skip this rule in production
          - IpProtocol: tcp
            FromPort: 22
            ToPort: 22
            CidrIp: 10.0.0.0/8

  # RDS Instance (only in production)
  Database:
    Type: AWS::RDS::DBInstance
    Condition: IsProduction  # Only created when IsProduction = true
    DeletionPolicy: Snapshot  # Take snapshot before deleting
    Properties:
      DBInstanceIdentifier: !Sub '${EnvironmentName}-database'
      DBInstanceClass: db.t3.medium
      Engine: mysql
      EngineVersion: '8.0'
      MasterUsername: admin
      MasterUserPassword: !Ref DBPassword
      AllocatedStorage: 100
      MultiAZ: true
      StorageEncrypted: true
      DeletionProtection: true

# ── Outputs ───────────────────────────────────────────────────────────
# Values to export after stack creation (for use by other stacks)
Outputs:
  WebServerPublicIP:
    Value: !GetAtt WebServer.PublicIp
    Description: 'Public IP of the web server'
  
  DatabaseEndpoint:
    Condition: IsProduction
    Value: !GetAtt Database.Endpoint.Address
    Export:
      Name: !Sub '${EnvironmentName}-DatabaseEndpoint'
    Description: 'RDS endpoint for application configuration'
```

### Deploying CloudFormation Stacks

```bash
# Validate the template before deploying
aws cloudformation validate-template \
  --template-body file://web-infrastructure.yaml

# Create (deploy) a new stack
aws cloudformation create-stack \
  --stack-name production-web-infrastructure \
  --template-body file://web-infrastructure.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=production \
    ParameterKey=InstanceType,ParameterValue=t3.medium \
    ParameterKey=DBPassword,ParameterValue=MySecureP@ssword123 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --tags Key=Project,Value=my-app Key=ManagedBy,Value=CloudFormation \
  --on-failure ROLLBACK  # Automatically rollback on failure

# Wait for stack creation to complete
aws cloudformation wait stack-create-complete \
  --stack-name production-web-infrastructure

# Get stack status and outputs
aws cloudformation describe-stacks \
  --stack-name production-web-infrastructure \
  --query 'Stacks[0].[StackStatus,Outputs]'

# Update an existing stack
aws cloudformation update-stack \
  --stack-name production-web-infrastructure \
  --template-body file://web-infrastructure.yaml \
  --parameters \
    ParameterKey=EnvironmentName,UsePreviousValue=true \
    ParameterKey=InstanceType,ParameterValue=t3.large \  # Changed instance type
    ParameterKey=DBPassword,UsePreviousValue=true

# Delete a stack (and all its resources!)
aws cloudformation delete-stack \
  --stack-name development-web-infrastructure
  # Note: Resources with DeletionPolicy=Retain are NOT deleted
```

### Change Sets — Preview Changes Before Applying

**Change Sets** let you see exactly what changes will be made to a running stack BEFORE applying them.

```bash
# Create a change set (preview of changes)
aws cloudformation create-change-set \
  --stack-name production-web-infrastructure \
  --change-set-name upgrade-instance-type \
  --template-body file://web-infrastructure-v2.yaml \
  --parameters ParameterKey=EnvironmentName,UsePreviousValue=true

# Review what will change
aws cloudformation describe-change-set \
  --stack-name production-web-infrastructure \
  --change-set-name upgrade-instance-type \
  --query 'Changes[*].[Type,ResourceChange.Action,ResourceChange.LogicalResourceId,ResourceChange.Replacement]' \
  --output table

# Apply the change set (or delete it if changes are too risky)
aws cloudformation execute-change-set \
  --stack-name production-web-infrastructure \
  --change-set-name upgrade-instance-type
```

**Replacement warning:** Change Sets show if a resource will be REPLACED (deleted and recreated) vs just updated. Replacement can cause downtime — always review!

### Stack Policies — Protect Critical Resources

```bash
# Stack policy: prevent accidental deletion of database
aws cloudformation set-stack-policy \
  --stack-name production-web-infrastructure \
  --stack-policy-body '{
    "Statement": [{
      "Effect": "Deny",
      "Action": "Update:Delete",
      "Principal": "*",
      "Resource": "LogicalResourceId/Database"
    }, {
      "Effect": "Allow",
      "Action": "Update:*",
      "Principal": "*",
      "Resource": "*"
    }]
  }'
```

### Nested Stacks — Organizing Large Infrastructures

```yaml
# parent-stack.yaml — orchestrates child stacks
Resources:
  NetworkStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/network-stack.yaml
      Parameters:
        VpcCidr: 10.0.0.0/16

  DatabaseStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/database-stack.yaml
      Parameters:
        VpcId: !GetAtt NetworkStack.Outputs.VpcId
        SubnetIds: !GetAtt NetworkStack.Outputs.PrivateSubnetIds
```

---

## 9.3 AWS Systems Manager (SSM) — Managing Servers at Scale

### What is Systems Manager?

**AWS Systems Manager (SSM)** is a suite of tools for managing your EC2 instances and on-premises servers at scale. Without SSM, managing 100 servers would require:
- SSH into each server individually
- Run commands one by one
- No central record of what was done
- Patching each server manually

With SSM, you can:
- Run commands on all servers simultaneously
- Manage configuration at scale
- Patch all servers automatically
- Access servers securely without SSH keys or bastion hosts
- Store secrets and configurations centrally

### SSM Session Manager — SSH Without SSH

**Session Manager** provides secure browser-based or CLI access to EC2 instances without:
- Opening SSH port (22)
- Managing SSH key pairs
- Maintaining a bastion host
- Configuring inbound security group rules

**How it works:**
```
Your browser/CLI → SSM service (HTTPS port 443) → SSM Agent on EC2 instance
                                                  (agent polls SSM, no inbound port needed)
```

**Requirements:**
- SSM Agent installed (pre-installed on Amazon Linux 2, Amazon Linux 2023, Windows Server AMIs)
- IAM instance profile with AmazonSSMManagedInstanceCore policy
- VPC endpoint for SSM (if instances are in private subnets with no internet)

```bash
# Start a session with an EC2 instance (no SSH needed!)
aws ssm start-session --target i-0123456789abcdef0

# Run a command on the instance (interactive shell)
# OR run a specific command:
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartInteractiveCommand \
  --parameters 'command=["bash -l"]'

# Port forwarding via Session Manager (no VPN or bastion needed!)
# Forward local port 5432 to RDS port 5432 through EC2 instance
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["my-rds.abc123.us-east-1.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["5432"]}'
  
# Connect from your machine:
# psql -h localhost -p 5432 -U admin -d mydb
```

### SSM Run Command — Execute Commands Across All Instances

```bash
# Run a command on all production web servers simultaneously
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --targets Key=tag:Environment,Values=production \
            Key=tag:Role,Values=web-server \
  --parameters 'commands=["yum update -y --security", "systemctl restart nginx", "echo Update complete"]' \
  --timeout-seconds 300 \
  --output-s3-bucket-name command-output-bucket \
  --output-s3-key-prefix ssm-run-command-output

# Get the command ID
COMMAND_ID="command-id-from-above"

# Check command status on all targeted instances
aws ssm list-command-invocations \
  --command-id $COMMAND_ID \
  --query 'CommandInvocations[*].[InstanceId,Status,StatusDetails]' \
  --output table

# Get output from a specific instance
aws ssm get-command-invocation \
  --command-id $COMMAND_ID \
  --instance-id i-0123456789abcdef0 \
  --query '[StandardOutputContent,StandardErrorContent]' \
  --output text
```

### SSM Patch Manager — Automated Patching

**Patch Manager** automates the process of patching OS and applications on your fleet of servers.

**Key concepts:**
- **Patch Baseline:** Which patches to apply (approve all critical, auto-approve after 7 days, etc.)
- **Maintenance Window:** When patching runs (e.g., every Sunday 2am-4am)
- **Patch Group:** Which instances to patch (using tags)

```bash
# Create a custom patch baseline
aws ssm create-patch-baseline \
  --name production-linux-baseline \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "PatchFilters": [{
          "Key": "SEVERITY",
          "Values": ["Critical", "Important"]
        }]
      },
      "ApproveAfterDays": 7
    }]
  }' \
  --rejected-patches "kernel" \
  --rejected-patches-action BLOCK \
  --description "Production Linux patching baseline"

# Create a maintenance window
WINDOW_ID=$(aws ssm create-maintenance-window \
  --name sunday-patching \
  --schedule "cron(0 2 ? * SUN *)" \
  --duration 4 \
  --cutoff 1 \
  --allow-unassociated-targets false \
  --query 'WindowId' --output text)

# Register all production instances (by tag) in this window
aws ssm register-target-with-maintenance-window \
  --window-id $WINDOW_ID \
  --resource-type INSTANCE \
  --targets Key=tag:Environment,Values=production \
            Key=tag:PatchGroup,Values=linux-web-servers

# Register the patching task
aws ssm register-task-with-maintenance-window \
  --window-id $WINDOW_ID \
  --task-arn arn:aws:ssm:us-east-1::document/AWS-RunPatchBaseline \
  --task-type RUN_COMMAND \
  --targets Key=WindowTargetIds,Values=$TARGET_ID \
  --task-invocation-parameters '{
    "RunCommand": {
      "Parameters": {"Operation": ["Install"]},
      "OutputS3BucketName": "patching-output-bucket"
    }
  }'

# Check patch compliance
aws ssm describe-instance-patch-states-for-patch-group \
  --patch-group linux-web-servers \
  --query 'InstancePatchStates[*].[InstanceId,PatchGroup,MissingCount,FailedCount,InstalledCount]' \
  --output table
```

### SSM Parameter Store — Configuration Management

**Parameter Store** is a secure, centralized store for configuration values and secrets.

**Two tiers:**
- **Standard:** Free, up to 10,000 parameters, 4 KB value size
- **Advanced:** $0.05/parameter/month, up to 100,000 parameters, 8 KB value size, policies (expiration, notifications)

**Three parameter types:**
- **String:** Simple text (environment URLs, feature flags)
- **StringList:** Comma-separated list
- **SecureString:** Encrypted with KMS (passwords, API keys)

```bash
# Store application configuration
aws ssm put-parameter \
  --name /myapp/production/database/host \
  --value "production-mysql.abc123.us-east-1.rds.amazonaws.com" \
  --type String

# Store a secret (encrypted with KMS)
aws ssm put-parameter \
  --name /myapp/production/database/password \
  --value "MySecurePassword123!" \
  --type SecureString \
  --key-id arn:aws:kms:us-east-1:123456789012:key/abc123

# Store JSON config
aws ssm put-parameter \
  --name /myapp/production/config \
  --value '{"max_connections": 100, "timeout": 30, "log_level": "INFO"}' \
  --type String

# Read parameters in application code (Python)
```

```python
import boto3
import json

ssm = boto3.client('ssm')

def get_config():
    # Get multiple parameters at once (cost efficient — reduces API calls)
    response = ssm.get_parameters_by_path(
        Path='/myapp/production/',
        Recursive=True,
        WithDecryption=True  # Decrypt SecureString values
    )
    
    config = {}
    for param in response['Parameters']:
        # Convert /myapp/production/database/host → database_host
        key = param['Name'].replace('/myapp/production/', '').replace('/', '_')
        config[key] = param['Value']
    
    return config

def get_db_password():
    response = ssm.get_parameter(
        Name='/myapp/production/database/password',
        WithDecryption=True
    )
    return response['Parameter']['Value']
```

```bash
# Read a parameter
aws ssm get-parameter \
  --name /myapp/production/database/host \
  --query 'Parameter.Value' --output text

# Read a SecureString parameter (decrypted)
aws ssm get-parameter \
  --name /myapp/production/database/password \
  --with-decryption \
  --query 'Parameter.Value' --output text

# Get parameter with version history
aws ssm get-parameter-history \
  --name /myapp/production/database/host \
  --query 'Parameters[*].[Version,Value,LastModifiedDate]' \
  --output table
```

---

## 9.4 AWS CodeDeploy — Automated Application Deployments

### What is CodeDeploy?

**CodeDeploy** automates application deployments to EC2 instances, Lambda functions, and ECS services. It handles:
- Rolling deployments (avoid downtime)
- Automatic rollback on failure
- Deployment hooks (run pre/post scripts)
- Traffic shifting during deployments

### Deployment Configurations — How to Deploy

**In-Place Deployment (EC2 only):**
```
All at once (fastest, but causes downtime):
  Stop ALL instances → Deploy → Start ALL instances
  
Rolling with batch (balance of speed and availability):
  Stop 25% → Deploy 25% → Start 25% → Repeat until done
  Never more than 25% offline at a time

Rolling with minimum healthy hosts:
  Configured minimum healthy % (e.g., 75% must stay healthy)
```

**Blue/Green Deployment (Zero downtime):**
```
Blue = Current production environment (v1)
Green = New environment (v2)

1. Create Green environment (same size as Blue)
2. Deploy new version to Green
3. Run tests against Green
4. Shift traffic from Blue to Green
5. Keep Blue running for X minutes (fast rollback window)
6. Terminate Blue (or keep for quick rollback)
```

```yaml
# appspec.yml — CodeDeploy configuration (in your application repository)
version: 0.0
os: linux

files:
  - source: /application
    destination: /opt/myapp

hooks:
  BeforeInstall:
    - location: scripts/stop_server.sh
      timeout: 180
      runas: root
  
  AfterInstall:
    - location: scripts/install_dependencies.sh
      timeout: 300
      runas: root
    - location: scripts/configure_app.sh
      timeout: 60
      runas: app-user
  
  ApplicationStart:
    - location: scripts/start_server.sh
      timeout: 60
      runas: root
  
  ValidateService:
    - location: scripts/health_check.sh
      timeout: 120
      runas: root
    # If this script exits non-zero, deployment is marked failed
    # and CodeDeploy automatically rolls back!
```

```bash
#!/bin/bash
# scripts/health_check.sh
# Check application health after deployment

MAX_RETRIES=30
RETRY_INTERVAL=10
HEALTH_URL="http://localhost/health"

for i in $(seq 1 $MAX_RETRIES); do
  HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' $HEALTH_URL)
  if [ "$HTTP_CODE" = "200" ]; then
    echo "Health check passed on attempt $i"
    exit 0
  fi
  echo "Attempt $i: Got $HTTP_CODE, waiting ${RETRY_INTERVAL}s..."
  sleep $RETRY_INTERVAL
done

echo "Health check failed after $MAX_RETRIES attempts"
exit 1  # Non-zero exit triggers CodeDeploy rollback!
```

---

## 9.5 AWS Elastic Beanstalk — Platform as a Service (PaaS)

### What is Elastic Beanstalk?

**Elastic Beanstalk** is AWS's PaaS (Platform as a Service). You give it your application code, and Beanstalk:
- Creates the EC2 instances
- Configures the load balancer
- Sets up auto-scaling
- Manages deployment
- Handles patching and OS maintenance

**Analogy:** Elastic Beanstalk is like a fully-managed apartment. Elastic Beanstalk is the building super — you just move in (deploy your code). They handle plumbing, electricity, maintenance.

**Compared to raw EC2:** With EC2, you manage everything. With Beanstalk, you manage almost nothing.

**Supported platforms:**
- Python (Django, Flask)
- Node.js
- Java (Tomcat, Spring)
- .NET (IIS)
- PHP
- Ruby
- Go
- Docker (single or multi-container)

```bash
# Deploy a Python web application to Elastic Beanstalk
# Initialize
eb init my-python-app --platform python-3.11 --region us-east-1

# Create the environment
eb create production-env \
  --instance-type t3.small \
  --min-instances 2 \
  --max-instances 10 \
  --scale-based-on-size \
  --database.engine mysql \
  --database.instance db.t3.micro

# Deploy application
eb deploy

# Check status
eb status
eb health  # Shows instance health in detail

# Open the application URL
eb open

# Set environment variables
eb setenv \
  DATABASE_URL=mysql://user:pass@host:3306/db \
  SECRET_KEY=mysecretkey \
  ENVIRONMENT=production

# SSH into a running instance (Beanstalk handles the SSH)
eb ssh
```

---

## 9.6 Automation Document Library (SSM Automation)

### SSM Automation — Complex Multi-Step Automation

While Run Command executes simple scripts, **SSM Automation** handles complex multi-step operational procedures with:
- Branching logic (if-then-else)
- Waiting for conditions
- Cross-service actions (launch EC2, wait for it to be ready, configure it)
- Approvals (pause for human approval before continuing)

```bash
# Common AWS automation documents (pre-built):
# AWS-StartEC2Instance
# AWS-StopEC2Instance
# AWS-RestartEC2Instance
# AWS-CreateImage (create AMI)
# AWS-CreateSnapshot (EBS snapshot)
# AWS-DisableS3BucketPublicReadWrite
# AWS-EnableS3BucketLogging
# AWS-PatchInstanceWithRollback (patch with automatic rollback on failure)

# Execute an automation document
aws ssm start-automation-execution \
  --document-name AWS-CreateImage \
  --parameters '{
    "InstanceId": ["i-0123456789abcdef0"],
    "ImageName": ["MyAutoAMI_{{global:DATE}}"],
    "NoReboot": ["true"]
  }'

# Check automation execution status
aws ssm describe-automation-executions \
  --filters Key=Status,Values=InProgress \
  --query 'AutomationExecutionMetadataList[*].[AutomationExecutionId,DocumentName,Status,StartTime]' \
  --output table
```

---

## 9.7 Practice Questions

**Q1:** A CloudFormation template has `DeletionPolicy: Retain` on an S3 bucket resource. When the stack is deleted, what happens to the S3 bucket?

- A) The bucket is deleted along with all its contents
- B) The bucket is emptied but the bucket itself is kept
- C) The bucket is retained — it remains in AWS after the stack is deleted
- D) An error occurs and the stack deletion fails

**Answer: C**

Explanation: DeletionPolicy: Retain tells CloudFormation to keep the resource in AWS even when the stack is deleted. The resource becomes an "orphan" — no longer managed by CloudFormation but still exists in your account. This is commonly used for S3 buckets (which must be empty to delete anyway) and databases where you want to preserve data even if the infrastructure stack is deleted. You would need to manually delete the resource later.

---

**Q2:** What is the PRIMARY security benefit of using SSM Session Manager instead of traditional SSH?

- A) Session Manager uses stronger encryption than SSH
- B) No inbound port 22 needed on security groups; no SSH keys to manage; all sessions logged
- C) Session Manager is free; SSH requires paid certificates
- D) Session Manager is faster than SSH

**Answer: B**

Explanation: Session Manager's key security benefits are: (1) No need to open port 22 in security groups — the attack surface is reduced (common SSH brute force attacks cannot reach the instance). (2) No SSH key pairs to create, manage, rotate, or revoke. (3) All sessions are automatically logged to CloudWatch Logs and S3 — complete audit trail of who connected and what they typed. (4) Access controlled by IAM policies — granular, centrally managed.

---

**Q3:** You want to deploy a new version of your application to 100 EC2 instances with zero downtime. Which deployment strategy achieves this?

- A) In-Place All at Once
- B) In-Place Rolling (25% batch)
- C) Blue/Green deployment
- D) Deploy directly to all instances simultaneously

**Answer: C**

Explanation: Blue/Green deployment creates a completely new environment (Green) with the new version while the original (Blue) continues serving production traffic. After the new version is deployed and tested, traffic is shifted from Blue to Green. There is no downtime because traffic continues to flow to Blue until Green is ready. If Green has issues, traffic can be immediately shifted back to Blue. In-Place All at Once (A) causes downtime. In-Place Rolling (B) can cause partial downtime if some instances are offline during deployment.

---

**Q4:** Your application reads its database password from AWS SSM Parameter Store at startup. You rotate the password in Parameter Store, but the application still uses the old password. Why?

- A) Parameter Store caches values for 24 hours
- B) The application cached the parameter value at startup; it must be restarted to read the new value
- C) SSM Parameter Store does not support secret rotation
- D) The IAM role needs to be updated with new permissions

**Answer: B**

Explanation: If your application reads Parameter Store at startup and caches the value in memory, it will continue using the old password until it restarts. There are two solutions: (1) Restart the application after rotating the password (causes brief downtime). (2) Use AWS Secrets Manager instead, which supports automatic rotation AND has a caching library that applications can use to automatically get the latest secret version without restart. Secrets Manager is specifically designed for secret rotation scenarios.

---

**Q5:** A CloudFormation stack update is showing that the RDS database will be REPLACED (not updated) in a Change Set. What should you do?

- A) Proceed — CloudFormation will migrate data to the new database automatically
- B) Cancel, modify the template to use parameters that don't require replacement, or manually migrate data
- C) Proceed only if in a maintenance window
- D) Replace is faster than update — always proceed

**Answer: B**

Explanation: When CloudFormation "replaces" an RDS instance, it deletes the old one and creates a new one. This means: (1) Downtime while the new instance initializes. (2) Potential data loss — the new database starts empty (unless the old one has a final snapshot and you restore from it). Never blindly proceed with database replacement. Instead: check WHY replacement is needed (some properties like DBInstanceIdentifier cannot be changed in place), modify the approach, or plan a proper migration. Always review Change Sets carefully, especially for databases!

---

## Chapter 9 Summary

| Service/Concept | Purpose | Key Feature |
|----------------|---------|-------------|
| CloudFormation | IaC for AWS | YAML/JSON templates; repeatable; rollback on failure |
| Change Sets | Preview CF changes | See what will change before applying |
| Stack Policies | Protect resources | Prevent deletion/replacement of critical resources |
| Nested Stacks | Organize large infra | Reusable child stacks called by parent |
| SSM Session Manager | Secure instance access | No SSH/port 22; IAM-controlled; fully audited |
| SSM Run Command | Remote command execution | Run scripts on many instances simultaneously |
| SSM Patch Manager | Automated patching | Baselines + maintenance windows + compliance |
| SSM Parameter Store | Config/secrets | String and SecureString; versioning; free tier |
| SSM Automation | Complex operations | Multi-step workflows; approvals; cross-service |
| CodeDeploy | App deployments | Blue/Green, rolling; automatic rollback on failure |
| Elastic Beanstalk | PaaS | You deploy code; AWS manages infrastructure |
"""

with open(r"e:\fastapi\aws-admin\09_Deployment_Automation_SystemsManager.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
