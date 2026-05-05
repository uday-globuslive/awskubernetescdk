# Chapter 9: Deployment, Automation & Systems Manager

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 4**: Deployment, Provisioning, and Automation (18% of exam)
- CloudFormation, Systems Manager, Elastic Beanstalk, CodeDeploy heavily tested

---

## 9.1 AWS CloudFormation

CloudFormation enables **Infrastructure as Code (IaC)** — define all your AWS infrastructure in YAML/JSON templates.

### Why CloudFormation?
```
Without CloudFormation:
  Click Console → Create VPC → Create Subnets → Create IGW → 
  Create Security Groups → Launch EC2 → Configure... (manual, error-prone)

With CloudFormation:
  aws cloudformation deploy --template-file template.yaml → DONE
  (Reproducible, version-controlled, auditable)
```

### Template Structure
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Complete web application stack

# ─────────────────── PARAMETERS ───────────────────────────────
Parameters:
  Environment:
    Type: String
    AllowedValues: [development, staging, production]
    Default: development
    Description: Deployment environment
  
  InstanceType:
    Type: String
    Default: t3.micro
    AllowedValues: [t3.micro, t3.small, t3.medium, m5.large]
  
  DBPassword:
    Type: String
    NoEcho: true    # Masks the value in console
    MinLength: 8
    Description: Database password

# ─────────────────── MAPPINGS ─────────────────────────────────
Mappings:
  EnvironmentConfig:
    production:
      InstanceType: m5.large
      MultiAZ: true
      DeletionPolicy: Retain
    staging:
      InstanceType: t3.small
      MultiAZ: false
      DeletionPolicy: Delete

# ─────────────────── CONDITIONS ───────────────────────────────
Conditions:
  IsProduction: !Equals [!Ref Environment, production]
  CreateReadReplica: !Equals [!Ref Environment, production]

# ─────────────────── RESOURCES ────────────────────────────────
Resources:
  WebServerASG:
    Type: AWS::AutoScaling::AutoScalingGroup
    CreationPolicy:             # Wait for signal before marking stack success
      ResourceSignal:
        Count: 2
        Timeout: PT15M
    UpdatePolicy:               # Control how ASG updates
      AutoScalingRollingUpdate:
        MinInstancesInService: 1
        MaxBatchSize: 1
        WaitOnResourceSignals: true
        PauseTime: PT10M
    Properties:
      AutoScalingGroupName: !Sub '${Environment}-web-asg'
      MinSize: !If [IsProduction, 2, 1]
      MaxSize: !If [IsProduction, 20, 5]
      DesiredCapacity: !If [IsProduction, 4, 1]
      LaunchTemplate:
        LaunchTemplateId: !Ref WebLaunchTemplate
        Version: !GetAtt WebLaunchTemplate.LatestVersionNumber

  WebLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateData:
        InstanceType: !FindInMap [EnvironmentConfig, !Ref Environment, InstanceType]
        ImageId: !Ref LatestAmiId
        IamInstanceProfile:
          Name: !Ref InstanceProfile
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            /opt/aws/bin/cfn-init -v \
              --stack ${AWS::StackName} \
              --resource WebLaunchTemplate \
              --region ${AWS::Region}
            /opt/aws/bin/cfn-signal -e $? \
              --stack ${AWS::StackName} \
              --resource WebServerASG \
              --region ${AWS::Region}

  # RDS only in production (conditional resource)
  Database:
    Type: AWS::RDS::DBInstance
    Condition: IsProduction
    DeletionPolicy: Snapshot    # Take snapshot before deleting
    UpdateReplacePolicy: Snapshot
    Properties:
      DBInstanceClass: db.m5.large
      Engine: postgres
      EngineVersion: '15.4'
      MultiAZ: true
      StorageEncrypted: true
      MasterUsername: admin
      MasterUserPassword: !Ref DBPassword

# ─────────────────── OUTPUTS ──────────────────────────────────
Outputs:
  LoadBalancerDNS:
    Value: !GetAtt ApplicationLoadBalancer.DNSName
    Export:
      Name: !Sub '${AWS::StackName}-alb-dns'
  
  DatabaseEndpoint:
    Value: !GetAtt Database.Endpoint.Address
    Condition: IsProduction
    Export:
      Name: !Sub '${AWS::StackName}-db-endpoint'
```

### CloudFormation Operations
```bash
# Deploy/create or update a stack
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name production-app \
  --parameter-overrides Environment=production DBPassword=SecurePass123 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --tags Environment=production CostCenter=Engineering

# Create change set (preview changes before applying)
aws cloudformation create-change-set \
  --stack-name production-app \
  --change-set-name update-instance-type \
  --template-body file://template.yaml \
  --parameters ParameterKey=InstanceType,ParameterValue=m5.large \
  --capabilities CAPABILITY_IAM

# Review the change set
aws cloudformation describe-change-set \
  --stack-name production-app \
  --change-set-name update-instance-type

# Execute change set
aws cloudformation execute-change-set \
  --stack-name production-app \
  --change-set-name update-instance-type

# Check for stack drift (resources modified outside CloudFormation)
aws cloudformation detect-stack-drift --stack-name production-app

aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $(aws cloudformation detect-stack-drift \
    --stack-name production-app --query StackDriftDetectionId --output text)

# Describe drifted resources
aws cloudformation describe-stack-resource-drifts \
  --stack-name production-app \
  --stack-resource-drift-status-filters MODIFIED DELETED

# Delete stack (with confirmation)
aws cloudformation delete-stack --stack-name dev-app
```

### StackSets — Deploy Across Multiple Accounts/Regions
```bash
# Create StackSet (deploy same template to multiple accounts)
aws cloudformation create-stack-set \
  --stack-set-name baseline-security \
  --template-body file://baseline-security.yaml \
  --administration-role-arn arn:aws:iam::123456789012:role/AWSCloudFormationStackSetAdministrationRole \
  --execution-role-name AWSCloudFormationStackSetExecutionRole \
  --capabilities CAPABILITY_IAM

# Deploy to multiple accounts/regions
aws cloudformation create-stack-instances \
  --stack-set-name baseline-security \
  --accounts 111111111111 222222222222 333333333333 \
  --regions us-east-1 us-west-2 eu-west-1 \
  --operation-preferences MaxConcurrentPercentage=50,FailureTolerancePercentage=20
```

---

## 9.2 AWS Systems Manager (SSM)

SSM is the **operational hub** for managing EC2 instances and on-premises servers at scale.

### SSM Architecture
```
┌────────────────────────────────────────────────────────────────┐
│                 SYSTEMS MANAGER                                 │
│                                                                │
│  Fleet        ┌─────────────────────────────────────────────┐ │
│  Management   │  SSM Agent (installed on each managed node)  │ │
│  ├─ Inventory │  Communicates via HTTPS to SSM endpoints     │ │
│  ├─ State     │  NO inbound ports needed (port 443 outbound) │ │
│  │  Manager   └─────────────────────────────────────────────┘ │
│  └─ Patch                                                      │
│     Manager   Node must have:                                   │
│               ├─ SSM Agent installed                           │
│  Operations   ├─ IAM role with AmazonSSMManagedInstanceCore    │
│  ├─ Run Command ├─ Network access to SSM endpoints              │
│  ├─ Session   └─ (or VPC endpoint for private subnets)         │
│  │  Manager                                                    │
│  ├─ Automation                                                 │
│  └─ OpsCenter                                                  │
│                                                                │
│  Application  Parameter Store, Secrets Manager integration     │
│               AppConfig, Distributor                           │
└────────────────────────────────────────────────────────────────┘
```

### Session Manager — Secure Shell Without SSH
```bash
# Start interactive session (no SSH key or port 22 needed!)
aws ssm start-session --target i-1234567890abcdef0

# Run a command and get output
aws ssm start-session \
  --target i-1234567890abcdef0 \
  --document-name AWS-StartInteractiveCommand \
  --parameters '{"command": ["sudo systemctl status nginx"]}'

# Enable Session Manager logging (required for compliance)
aws ssm update-document \
  --name SSM-SessionManagerRunShell \
  --content '{
    "schemaVersion": "1.0",
    "description": "Document to hold regional settings",
    "sessionType": "Standard_Stream",
    "inputs": {
      "s3BucketName": "session-logs-bucket",
      "s3KeyPrefix": "sessions/",
      "s3EncryptionEnabled": true,
      "cloudWatchLogGroupName": "/aws/ssm/sessions",
      "cloudWatchEncryptionEnabled": true,
      "kmsKeyId": "arn:aws:kms:...",
      "runAsEnabled": false
    }
  }' \
  --document-version '$LATEST'
```

### Run Command — Execute Commands at Scale
```bash
# Run command on all production EC2 instances (by tag)
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --parameters '{"commands": [
    "systemctl status nginx",
    "df -h",
    "free -m",
    "uptime"
  ]}' \
  --targets '[{"Key":"tag:Environment","Values":["production"]}]' \
  --timeout-seconds 60 \
  --output-s3-bucket-name ssm-command-output \
  --output-s3-key-prefix run-command/

# Check command status
aws ssm list-command-invocations \
  --command-id $(aws ssm send-command --document-name ... --query Command.CommandId --output text) \
  --details

# Install software on all tagged instances
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --parameters '{"commands": [
    "yum install -y amazon-cloudwatch-agent",
    "systemctl enable --now amazon-cloudwatch-agent"
  ]}' \
  --targets '[{"Key":"tag:Role","Values":["web","app"]}]'
```

### Patch Manager — Automated Patching
```bash
# Create a patch baseline (what to patch)
aws ssm create-patch-baseline \
  --name production-linux-baseline \
  --operating-system AMAZON_LINUX_2 \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["AmazonLinux2"]},
          {"Key":"CLASSIFICATION","Values":["Security","Bugfix"]},
          {"Key":"SEVERITY","Values":["Critical","Important"]}
        ]
      },
      "ApproveAfterDays": 7,
      "ComplianceLevel": "CRITICAL",
      "EnableNonSecurity": false
    }]
  }'

# Create maintenance window for patching
aws ssm create-maintenance-window \
  --name weekly-patching \
  --schedule "cron(0 2 ? * SUN *)" \  # Every Sunday 2 AM
  --duration 4 \                       # 4-hour window
  --cutoff 1 \                         # Stop 1 hour before end
  --allow-unassociated-targets

# Register targets (by tag)
aws ssm register-target-with-maintenance-window \
  --window-id mw-xxx \
  --resource-type INSTANCE \
  --targets '[{"Key":"tag:PatchGroup","Values":["production"]}]'

# Register patching task
aws ssm register-task-with-maintenance-window \
  --window-id mw-xxx \
  --targets '[{"Key":"WindowTargetIds","Values":["target-xxx"]}]' \
  --task-arn AWS-RunPatchBaseline \
  --task-type RUN_COMMAND \
  --service-role-arn arn:aws:iam::123456789012:role/MaintenanceWindowRole \
  --task-invocation-parameters '{
    "RunCommand": {
      "Parameters": {"Operation": ["Install"]},
      "TimeoutSeconds": 3600
    }
  }' \
  --max-concurrency 10% \
  --max-errors 5%

# Scan for compliance (before patching)
aws ssm send-command \
  --document-name AWS-RunPatchBaseline \
  --parameters '{"Operation":["Scan"]}' \
  --targets '[{"Key":"tag:Environment","Values":["production"]}]'

# Check patch compliance
aws ssm describe-instance-patch-states-for-patch-group \
  --patch-group production
```

### Parameter Store — Configuration Management
```bash
# Store configuration parameters
aws ssm put-parameter \
  --name /production/app/database/host \
  --value "prod-postgres.cluster.us-east-1.rds.amazonaws.com" \
  --type String \
  --tier Standard

# Store sensitive values (encrypted)
aws ssm put-parameter \
  --name /production/app/database/password \
  --value "SuperSecretPassword123!" \
  --type SecureString \
  --key-id alias/production-parameter-key \
  --tier Standard

# Get parameter (with decryption)
aws ssm get-parameter \
  --name /production/app/database/password \
  --with-decryption \
  --query Parameter.Value \
  --output text

# Get multiple parameters at once
aws ssm get-parameters-by-path \
  --path /production/app/database/ \
  --with-decryption \
  --recursive

# Parameter Store in Python
import boto3

def get_config():
    ssm = boto3.client('ssm')
    
    params = ssm.get_parameters_by_path(
        Path='/production/app/',
        WithDecryption=True,
        Recursive=True
    )
    
    # Convert to dict with clean names
    config = {}
    for param in params['Parameters']:
        # /production/app/database/host → database_host
        key = param['Name'].split('/')[-2] + '_' + param['Name'].split('/')[-1]
        config[key] = param['Value']
    
    return config
```

### Automation — Self-Service Operations
```yaml
# Custom Automation document for EC2 AMI creation
description: Create AMI from instance, tag it, and notify
schemaVersion: '0.3'
assumeRole: '{{AutomationAssumeRole}}'
parameters:
  InstanceId:
    type: String
    description: EC2 instance to create AMI from
  AutomationAssumeRole:
    type: String

mainSteps:
  - name: StopInstance
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: StopInstances
      InstanceIds:
        - '{{InstanceId}}'
  
  - name: WaitForStopped
    action: aws:waitForAwsResourceProperty
    inputs:
      Service: ec2
      Api: DescribeInstances
      InstanceIds:
        - '{{InstanceId}}'
      PropertySelector: '$.Reservations[0].Instances[0].State.Name'
      DesiredValues: [stopped]
  
  - name: CreateAMI
    action: aws:executeAwsApi
    outputs:
      - Name: AmiId
        Selector: $.ImageId
        Type: String
    inputs:
      Service: ec2
      Api: CreateImage
      InstanceId: '{{InstanceId}}'
      Name: 'Golden-AMI-{{global:DATE}}'
      NoReboot: false
  
  - name: StartInstance
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: StartInstances
      InstanceIds:
        - '{{InstanceId}}'
  
  - name: SendNotification
    action: aws:executeAwsApi
    inputs:
      Service: sns
      Api: Publish
      TopicArn: arn:aws:sns:us-east-1:123456789012:ops-alerts
      Message: 'AMI created: {{CreateAMI.AmiId}} from {{InstanceId}}'
```

```bash
# Execute automation document
aws ssm start-automation-execution \
  --document-name CreateGoldenAMI \
  --parameters InstanceId=i-xxx,AutomationAssumeRole=arn:aws:iam::123456789012:role/AutomationRole
```

---

## 9.3 Elastic Beanstalk

Elastic Beanstalk is a **PaaS** — upload your code, AWS manages the infrastructure.

### Deployment Strategies

| Strategy | Downtime | Time | Cost |
|----------|---------|------|------|
| **All at Once** | Yes (brief) | Fastest | Same |
| **Rolling** | No (partial available) | Moderate | Same |
| **Rolling with additional batch** | No | Slower | Small extra |
| **Immutable** | No | Slow | 2x during deploy |
| **Traffic Splitting (Canary)** | No | Gradual | Small extra |

```
All at Once:
  OLD → OLD → NEW → NEW (all down briefly)

Rolling (batch=1):
  OLD → NEW, OLD → NEW, OLD → NEW (some instances always running)

Immutable:
  NEW NEW    ← Launch new instances in new ASG
  OLD OLD    ← Keep old running
  └─ swap    ← Route traffic to new, terminate old

Traffic Splitting:
  90% → OLD, 10% → NEW  ← Test with small % of traffic
  Wait for metrics, then gradually shift
```

```bash
# Create application and environment
aws elasticbeanstalk create-application --application-name my-api

aws elasticbeanstalk create-environment \
  --application-name my-api \
  --environment-name my-api-production \
  --solution-stack-name "64bit Amazon Linux 2 v3.5.3 running Python 3.9" \
  --option-settings \
    Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=LoadBalanced \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=10 \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=RollingWithAdditionalBatch \
    Namespace=aws:elasticbeanstalk:command,OptionName=BatchSize,Value=25 \
    Namespace=aws:elasticbeanstalk:command,OptionName=BatchSizeType,Value=Percentage

# Deploy new version
aws elasticbeanstalk create-application-version \
  --application-name my-api \
  --version-label v1.2.3 \
  --source-bundle S3Bucket=my-deploy-bucket,S3Key=builds/v1.2.3.zip

aws elasticbeanstalk update-environment \
  --environment-name my-api-production \
  --version-label v1.2.3
```

### .ebextensions — Customize Beanstalk Environment
```yaml
# .ebextensions/01-packages.config
packages:
  yum:
    nginx: []
    git: []

files:
  "/etc/nginx/conf.d/custom.conf":
    mode: "000644"
    owner: root
    group: root
    content: |
      client_max_body_size 50M;

commands:
  01-setup:
    command: "mkdir -p /var/app/current/logs"

container_commands:
  01-migrate:
    command: "python manage.py db upgrade"
    leader_only: true   # Only run on one instance

option_settings:
  aws:elasticbeanstalk:application:environment:
    DJANGO_SETTINGS_MODULE: myapp.settings.production
```

---

## 9.4 AWS CodeDeploy

CodeDeploy automates application deployments to EC2, Lambda, or ECS.

### Deployment Types

**In-Place (EC2/On-Premises):**
```
Stop app → Deploy → Start app (one server at a time)
```

**Blue/Green (EC2):**
```
Green (running)  ──────────────────────► (eventually terminated)
Blue  (new)      ← launch → attach ALB → receive traffic
```

**Lambda Deployment (Serverless):**
```
Canary10Percent5Minutes: 10% traffic to new for 5 min, then all
Linear10PercentEvery1Minute: Gradually shift over 10 minutes
AllAtOnce: Instant cutover
```

### AppSpec Configuration
```yaml
# appspec.yml for EC2 deployment
version: 0.0
os: linux
files:
  - source: /app
    destination: /var/www/myapp
  - source: /config/nginx.conf
    destination: /etc/nginx/conf.d/myapp.conf

hooks:
  BeforeInstall:
    - location: scripts/install-dependencies.sh
      timeout: 300
      runas: root
  
  AfterInstall:
    - location: scripts/set-permissions.sh
      timeout: 60
      runas: root
  
  ApplicationStart:
    - location: scripts/start-server.sh
      timeout: 60
      runas: ec2-user
  
  ValidateService:
    - location: scripts/health-check.sh
      timeout: 120
      runas: ec2-user
```

```bash
# scripts/health-check.sh
#!/bin/bash
MAX_RETRIES=30
RETRY_INTERVAL=5

for i in $(seq 1 $MAX_RETRIES); do
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)
    
    if [ "$HTTP_STATUS" = "200" ]; then
        echo "Health check passed (attempt $i)"
        exit 0
    fi
    
    echo "Health check failed with status $HTTP_STATUS (attempt $i/$MAX_RETRIES)"
    sleep $RETRY_INTERVAL
done

echo "Health check failed after $MAX_RETRIES attempts"
exit 1
```

```bash
# Create CodeDeploy deployment
aws deploy create-deployment \
  --application-name myapp \
  --deployment-group-name production \
  --s3-location bucket=deploy-bucket,bundleType=zip,key=app-v1.2.3.zip \
  --deployment-config-name CodeDeployDefault.OneAtATime \
  --description "Release v1.2.3"

# Monitor deployment
aws deploy get-deployment --deployment-id d-xxx

# Rollback to previous version
aws deploy create-deployment \
  --application-name myapp \
  --deployment-group-name production \
  --s3-location bucket=deploy-bucket,bundleType=zip,key=app-v1.2.2.zip

# Enable automatic rollback on failure
aws deploy update-deployment-group \
  --application-name myapp \
  --deployment-group-name production \
  --auto-rollback-configuration '{"enabled": true, "events": ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]}'
```

---

## 9.5 EC2 Image Builder

Automates the creation, maintenance, testing, and distribution of EC2 AMIs.

```bash
# Create an Image Builder pipeline
aws imagebuilder create-image-pipeline \
  --name golden-ami-pipeline \
  --image-recipe-arn arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/my-recipe/1.0.0 \
  --infrastructure-configuration-arn arn:aws:imagebuilder:...:infrastructure-configuration/my-config \
  --distribution-configuration-arn arn:aws:imagebuilder:...:distribution-configuration/my-dist \
  --schedule '{"scheduleExpression":"cron(0 0 * * ? *)","pipelineExecutionStartCondition":"EXPRESSION_MATCH_ONLY"}'
```

```yaml
# Image recipe component — install software on AMI
name: install-security-tools
description: Install and configure security tools
schemaVersion: 1.0

phases:
  - name: build
    steps:
      - name: install-packages
        action: ExecuteBash
        inputs:
          commands:
            - sudo yum install -y amazon-cloudwatch-agent awscli
            - sudo yum update -y --security
      
      - name: configure-cloudwatch-agent
        action: ExecuteBash
        inputs:
          commands:
            - sudo amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c ssm:/cloudwatch-agent/config
      
      - name: harden-ssh
        action: ExecuteBash
        inputs:
          commands:
            - sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
            - sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
            - sudo systemctl restart sshd

  - name: validate
    steps:
      - name: verify-cloudwatch-agent
        action: ExecuteBash
        inputs:
          commands:
            - systemctl is-active --quiet amazon-cloudwatch-agent
```

---

## 9.6 CloudFormation Helper Scripts

```yaml
# cfn-init in Launch Template for bootstrap configuration
Resources:
  WebLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Metadata:
      AWS::CloudFormation::Init:
        config:
          packages:
            yum:
              nginx: []
              python3-pip: []
          
          files:
            /etc/nginx/conf.d/app.conf:
              content: |
                server {
                    listen 80;
                    location / {
                        proxy_pass http://127.0.0.1:8000;
                    }
                }
            
            /opt/app/app.py:
              source: !Sub 'https://s3.${AWS::Region}.amazonaws.com/my-bucket/app.py'
          
          services:
            sysvinit:
              nginx:
                enabled: true
                ensureRunning: true
                files: [/etc/nginx/conf.d/app.conf]
    
    Properties:
      LaunchTemplateData:
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum install -y aws-cfn-bootstrap
            
            # Initialize configuration from Metadata
            /opt/aws/bin/cfn-init -v \
              --stack ${AWS::StackName} \
              --resource WebLaunchTemplate \
              --region ${AWS::Region}
            
            # Signal CloudFormation success/failure
            /opt/aws/bin/cfn-signal -e $? \
              --stack ${AWS::StackName} \
              --resource WebServerASG \
              --region ${AWS::Region}
```

---

## 9.7 Real-World Project: Full CI/CD Pipeline with CloudFormation

### Architecture
```
Developer pushes code
       │
       ▼
  GitHub/CodeCommit
       │
       ▼
  CodePipeline ──────────────────────────────────────────┐
  │                                                       │
  ├─► CodeBuild (tests + build + push to S3/ECR)         │
  │                                                       │
  ├─► CloudFormation ChangeSet Preview                   │
  │   (requires manual approval for production)           │
  │                                                       │
  └─► CodeDeploy → EC2 (Blue/Green)                     │
       │                                                  │
       ▼                                                  │
  SNS notification ──────────────────────────────────────┘
```

### CloudFormation Pipeline Template
```yaml
# cicd-pipeline.yaml
Resources:
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: !Sub '${AppName}-pipeline'
      RoleArn: !GetAtt PipelineRole.Arn
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactBucket
      
      Stages:
        - Name: Source
          Actions:
            - Name: Source
              ActionTypeId:
                Category: Source
                Owner: ThirdParty
                Provider: GitHub
                Version: '1'
              OutputArtifacts: [{Name: SourceCode}]
              Configuration:
                Owner: !Ref GitHubOwner
                Repo: !Ref GitHubRepo
                Branch: main
        
        - Name: Build
          Actions:
            - Name: Build
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              InputArtifacts: [{Name: SourceCode}]
              OutputArtifacts: [{Name: BuildOutput}]
              Configuration:
                ProjectName: !Ref BuildProject
        
        - Name: Deploy-Staging
          Actions:
            - Name: Deploy-Staging
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CloudFormation
                Version: '1'
              InputArtifacts: [{Name: BuildOutput}]
              Configuration:
                ActionMode: CREATE_UPDATE
                StackName: staging-app
                TemplatePath: BuildOutput::template.yaml
                Capabilities: CAPABILITY_IAM
        
        - Name: Approval
          Actions:
            - Name: ManualApproval
              ActionTypeId:
                Category: Approval
                Owner: AWS
                Provider: Manual
                Version: '1'
              Configuration:
                NotificationArn: !Ref OpsTopic
                CustomData: "Please review staging deployment before approving production"
        
        - Name: Deploy-Production
          Actions:
            - Name: Deploy-Production
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CodeDeploy
                Version: '1'
              InputArtifacts: [{Name: BuildOutput}]
              Configuration:
                ApplicationName: !Ref CodeDeployApp
                DeploymentGroupName: production
```

---

## 9.8 Practice Questions (SysOps Exam Level)

**Q1:** A CloudFormation stack update has been running for 90 minutes and is still in `UPDATE_IN_PROGRESS`. The stack has a `CreationPolicy` with `ResourceSignal`. What is likely happening?

**A:** The EC2 instances (or ASG instances) are not sending the `cfn-signal`. Reasons:
1. **User Data script failed** before the `cfn-signal` command
2. **Network issue** — instances can't reach CloudFormation endpoint
3. **Timeout too short** — increase `Timeout: PT30M` in CreationPolicy

```bash
# Check the signal status
aws cloudformation describe-stack-resource \
  --stack-name my-stack \
  --logical-resource-id WebServerASG

# Get instance logs via SSM or CloudWatch Logs
# Check /var/log/cfn-init.log and /var/log/cloud-init-output.log
```

---

**Q2:** You need to run a security script on 500 EC2 instances without logging in. How?

**A:** Use **SSM Run Command**:
```bash
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --parameters '{"commands": ["./security-audit.sh"]}' \
  --targets '[{"Key":"tag:Env","Values":["production"]}]' \
  --output-s3-bucket-name audit-results \
  --max-concurrency 50 \
  --max-errors 5
```
Benefits: No SSH, auditable, results in S3, works across all instances simultaneously.

---

**Q3:** How do you apply OS patches to 200 production instances with minimal downtime?

**A:**
1. **Create Patch Baseline** with approved patches
2. **Create Maintenance Window** (e.g., Sunday 2 AM)
3. **Register instances by tag** (not individual IDs)
4. **Set MaxConcurrency=10%** (patches 20 at a time) and **MaxErrors=5%**
5. **For zero downtime**: Use pre-patch lifecycle hook to detach from load balancer, patch, re-attach

```bash
aws ssm register-task-with-maintenance-window \
  --window-id mw-xxx \
  --max-concurrency "10%" \
  --max-errors "5%" \
  --task-arn AWS-RunPatchBaseline \
  --task-type RUN_COMMAND \
  --task-invocation-parameters '{"RunCommand":{"Parameters":{"Operation":["Install"]}}}'
```

---

**Q4:** A CloudFormation stack fails and begins rolling back. You want to investigate without losing the failed resources. What do you do?

**A:** Use `--disable-rollback` flag:
```bash
aws cloudformation create-stack \
  --stack-name debug-stack \
  --template-body file://template.yaml \
  --disable-rollback  # Don't roll back on failure — investigate instead

# OR after a failure that already started rolling back:
aws cloudformation continue-update-rollback \
  --stack-name my-stack \
  --resources-to-skip LogicalResourceIdThatFailed
```

---

**Q5:** How do you ensure EC2 instances patched last month are still compliant with the current patch baseline (no new patches have been skipped)?

**A:** Use **SSM Patch Manager compliance scanning**:
```bash
# Run scan (doesn't install, just checks)
aws ssm send-command \
  --document-name AWS-RunPatchBaseline \
  --parameters '{"Operation":["Scan"]}' \
  --targets '[{"Key":"tag:PatchGroup","Values":["production"]}]'

# View compliance dashboard
aws ssm list-compliance-summaries \
  --filters Key=ComplianceType,Values=Patch,Type=EQUAL

# Get non-compliant instances
aws ssm describe-instance-patch-states \
  --instance-ids i-xxx i-yyy \
  --query 'InstancePatchStates[?NotApplicableCount>`0`]'
```
Set up **Config rule** `ec2-managedinstance-patch-compliance-status-check` to continuously monitor.

---

## Key Deployment Terms for Exam

| Term | Definition |
|------|-----------|
| CloudFormation | IaC service — define infrastructure as YAML/JSON |
| Stack | CloudFormation deployment unit |
| Change Set | Preview of changes before applying to a stack |
| Stack Drift | Resources modified outside CloudFormation |
| StackSets | Deploy CloudFormation across multiple accounts/regions |
| cfn-init | CloudFormation helper script for EC2 initialization |
| cfn-signal | Signal CloudFormation from EC2 (CreationPolicy) |
| CreationPolicy | Wait for signals before marking resource complete |
| UpdatePolicy | Control how ASG instances are updated |
| SSM | Systems Manager — operational management hub |
| SSM Agent | Software on EC2 enabling SSM features |
| Session Manager | SSH replacement (no ports, no keys) |
| Run Command | Execute commands across multiple instances |
| Patch Manager | Automate OS patching via maintenance windows |
| Parameter Store | Configuration and secret storage |
| Automation | Runbook automation for AWS operations |
| Elastic Beanstalk | PaaS — upload code, AWS manages infrastructure |
| Immutable Deployment | New instances → test → replace old instances |
| CodeDeploy | Automated code deployment to EC2/Lambda/ECS |
| AppSpec | CodeDeploy deployment configuration file |
| Image Builder | Automated AMI creation and distribution |
