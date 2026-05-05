# Chapter 8: Advanced Features
## Nested Stacks, Cross-Stack References, Custom Resources & StackSets

---

## 8.1 Cross-Stack References

Cross-stack references let stacks share values without being nested. One stack exports a value; another imports it.

```yaml
# networking-stack.yaml — EXPORTS values
Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: !Sub "${AWS::StackName}-VpcId"   # Export name must be unique per region/account

  PrivateSubnets:
    Value: !Join [",", [!Ref PrivateSubnet1, !Ref PrivateSubnet2]]
    Export:
      Name: !Sub "${AWS::StackName}-PrivateSubnets"
```

```yaml
# app-stack.yaml — IMPORTS values
Parameters:
  NetworkingStack:
    Type: String
    Default: myapp-networking

Resources:
  MySecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      VpcId: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcId"   # Import by export name
```

```bash
# View all exports in a region
aws cloudformation list-exports \
  --query "Exports[*].[Name,Value]"

# IMPORTANT: Cannot delete a stack that has values imported by another stack
# You must delete the importing stack first
```

---

## 8.2 Nested Stacks

Nested stacks allow you to decompose a large template into reusable modules. A parent stack creates child stacks as resources.

```
parent-stack.yaml
├── networking-stack.yaml   (reusable VPC module)
├── databases-stack.yaml    (reusable DB module)
└── app-stack.yaml          (application, depends on above)
```

```yaml
# parent-stack.yaml — creates child stacks
AWSTemplateFormatVersion: "2010-09-09"
Description: Parent stack — orchestrates child stacks

Parameters:
  Environment:
    Type: String
    Default: prod

Resources:

  # Upload child templates to S3 first, then reference them
  NetworkingStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub "https://s3.amazonaws.com/my-templates/networking.yaml"
      Parameters:
        Environment: !Ref Environment
        VpcCidr: 10.0.0.0/16
        EnableNatGateway: "true"
      TimeoutInMinutes: 30
      Tags:
        - Key: ParentStack
          Value: !Ref AWS::StackName

  DatabaseStack:
    Type: AWS::CloudFormation::Stack
    DependsOn: NetworkingStack
    Properties:
      TemplateURL: !Sub "https://s3.amazonaws.com/my-templates/databases.yaml"
      Parameters:
        Environment: !Ref Environment
        NetworkingStack: !GetAtt NetworkingStack.Outputs.StackName
        DBPassword: !Sub "{{resolve:secretsmanager:${AWS::StackName}/db-password}}"
      TimeoutInMinutes: 45

  AppStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - NetworkingStack
      - DatabaseStack
    Properties:
      TemplateURL: !Sub "https://s3.amazonaws.com/my-templates/app.yaml"
      Parameters:
        Environment: !Ref Environment
        NetworkingStack: !GetAtt NetworkingStack.Outputs.StackName
        DatabaseStack: !GetAtt DatabaseStack.Outputs.StackName
      TimeoutInMinutes: 20

Outputs:
  AppUrl:
    Value: !GetAtt AppStack.Outputs.ServiceUrl
```

```bash
# Upload templates to S3
aws s3 sync ./templates s3://my-templates/ --exclude "*" --include "*.yaml"

# Package templates (resolves local file references to S3 URLs automatically)
aws cloudformation package \
  --template-file parent-stack.yaml \
  --s3-bucket my-templates \
  --output-template-file packaged.yaml

# Deploy packaged template
aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name myapp-prod \
  --parameter-overrides Environment=prod \
  --capabilities CAPABILITY_NAMED_IAM
```

---

## 8.3 Custom Resources — Lambda-Backed

Custom Resources let you execute arbitrary code during stack operations using a Lambda function. Useful for:
- Provisioning resources CloudFormation doesn't support natively
- Sending notifications
- Copying S3 data during stack creation
- Looking up values from external systems

```yaml
# custom-resource-example.yaml
Resources:

  # Lambda function that handles custom resource lifecycle
  DatabaseInitFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "${AWS::StackName}-db-init"
      Runtime: python3.12
      Handler: index.handler
      Role: !GetAtt LambdaRole.Arn
      Timeout: 300
      Code:
        ZipFile: |
          import json, urllib.request, urllib.error
          
          def send_response(event, context, status, data=None, reason=""):
              """Send response back to CloudFormation."""
              body = json.dumps({
                  "Status": status,
                  "Reason": reason,
                  "PhysicalResourceId": event.get("PhysicalResourceId", context.log_stream_name),
                  "StackId": event["StackId"],
                  "RequestId": event["RequestId"],
                  "LogicalResourceId": event["LogicalResourceId"],
                  "Data": data or {}
              })
              
              req = urllib.request.Request(
                  event["ResponseURL"],
                  data=body.encode(),
                  method="PUT",
                  headers={"Content-Type": "application/json"}
              )
              urllib.request.urlopen(req)
          
          def handler(event, context):
              request_type = event["RequestType"]
              props = event["ResourceProperties"]
              
              try:
                  if request_type == "Create":
                      # Run DB migrations, seed data, etc.
                      result = run_migrations(props["DBEndpoint"])
                      send_response(event, context, "SUCCESS", {"Result": result})
                  
                  elif request_type == "Update":
                      # Handle updates
                      send_response(event, context, "SUCCESS")
                  
                  elif request_type == "Delete":
                      # Cleanup if needed
                      send_response(event, context, "SUCCESS")
              
              except Exception as e:
                  send_response(event, context, "FAILED", reason=str(e))
          
          def run_migrations(db_endpoint):
              # Actually run your migrations here
              return "Migrations completed"

  # The custom resource — CloudFormation calls the Lambda on Create/Update/Delete
  DatabaseInit:
    Type: AWS::CloudFormation::CustomResource
    Properties:
      ServiceToken: !GetAtt DatabaseInitFunction.Arn
      DBEndpoint: !ImportValue "databases-stack-DBEndpoint"
      Environment: !Ref Environment
      # Changes to these properties trigger a resource Update
      MigrationVersion: "v1.2.3"
```

---

## 8.4 Dynamic References

Dynamic references let you pull values from SSM Parameter Store or Secrets Manager directly in templates, without passing them as parameters.

```yaml
Resources:
  MyInstance:
    Type: AWS::EC2::Instance
    Properties:
      # Pull from SSM Parameter Store
      ImageId: "{{resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64}}"
      InstanceType: "{{resolve:ssm:/myapp/prod/instance-type}}"
      
      # Pull encrypted SSM parameter
      # {{resolve:ssm-secure:/myapp/prod/db-password}}
      
      # Pull from Secrets Manager
      UserData:
        !Base64
          !Sub |
            #!/bin/bash
            export DB_PASS='{{resolve:secretsmanager:${AWS::StackName}/db:SecretString:password}}'
            export API_KEY='{{resolve:secretsmanager:${AWS::StackName}/api:SecretString:key}}'
```

---

## 8.5 CloudFormation StackSets

StackSets deploy a single template across multiple accounts and regions simultaneously.

```bash
# Create StackSet (from management account or delegated admin)
aws cloudformation create-stack-set \
  --stack-set-name security-baseline \
  --template-body file://security-baseline.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false

# Deploy to specific accounts and regions
aws cloudformation create-stack-instances \
  --stack-set-name security-baseline \
  --accounts 111122223333 444455556666 \
  --regions us-east-1 us-west-2 eu-west-1 \
  --operation-preferences '{
    "RegionConcurrencyType": "PARALLEL",
    "MaxConcurrentPercentage": 50,
    "FailureTolerancePercentage": 0
  }'

# Deploy to all accounts in an OU (Organizations integration)
aws cloudformation create-stack-instances \
  --stack-set-name security-baseline \
  --deployment-targets '{"OrganizationalUnitIds": ["ou-xxxx-yyyy"]}' \
  --regions us-east-1 eu-west-1 \
  --operation-preferences '{
    "RegionConcurrencyType": "PARALLEL",
    "MaxConcurrentCount": 10
  }'

# Update StackSet (updates all instances)
aws cloudformation update-stack-set \
  --stack-set-name security-baseline \
  --template-body file://security-baseline-v2.yaml \
  --capabilities CAPABILITY_NAMED_IAM

# View stack instances status
aws cloudformation list-stack-instances \
  --stack-set-name security-baseline \
  --query "Summaries[*].[Account,Region,Status,StatusReason]"
```

---

## 8.6 CloudFormation Macros

Macros are Lambda-backed transform functions that pre-process templates before CloudFormation processes them.

```yaml
# Using the built-in AWS::Include transform to include a template fragment
Resources:
  SecurityGroup:
    !Transform
      Name: AWS::Include
      Parameters:
        Location: s3://my-templates/security-group-fragment.yaml

# Custom macro example
Transform: MyCompanyMacro

Resources:
  MyDatabase:
    Type: Custom::SecureRDS    # Your macro expands this to full RDS + SG + subnet group
    Properties:
      Environment: prod
      InstanceClass: db.r6g.large
```

---

## 8.7 Drift Detection

```bash
# Detect drift on a stack (finds resources changed outside CloudFormation)
aws cloudformation detect-stack-drift --stack-name myapp-prod

# Wait for drift detection to complete (it's async)
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id <detection-id>

# View drifted resources
aws cloudformation describe-stack-resource-drifts \
  --stack-name myapp-prod \
  --stack-resource-drift-status-filters MODIFIED DELETED

# Example output for a modified security group:
# LogicalResourceId: AppSecurityGroup
# ExpectedProperties: {"GroupDescription": "...", "SecurityGroupIngress": [...]}
# ActualProperties: {"GroupDescription": "...", "SecurityGroupIngress": [..., {extra_rule}]}
# PropertyDifferences: [{"PropertyPath": "/SecurityGroupIngress/2", "ChangeType": "ADD"}]
```

---

## 8.8 Interview Questions

**Q: What is the difference between nested stacks and cross-stack references?**
> Nested stacks create a parent-child hierarchy — the parent stack creates child stacks as resources and can pass outputs between them. Cross-stack references use `Export`/`ImportValue` to share values between completely independent stacks. Nested stacks are tightly coupled (parent must exist for children to exist); cross-stack references are loosely coupled (stacks are independent but cannot be deleted if values are being imported). Use nested stacks for modular decomposition of one logical deployment; use cross-stack references for sharing infrastructure between separate teams or domains.

**Q: When would you use a Custom Resource?**
> When CloudFormation doesn't natively support what you need. Common cases: (1) running database migrations after RDS is created; (2) generating an RSA key pair and storing it in Secrets Manager; (3) copying S3 objects between buckets; (4) looking up the latest ECS task definition revision; (5) sending a Slack notification when a stack deploys. The Lambda function receives Create/Update/Delete events with your resource properties and must send a success or failure response to CloudFormation's pre-signed URL. If it times out without responding, the stack waits up to 1 hour then fails.

**Q: What is drift detection and how does it help?**
> Drift detection compares the current actual state of AWS resources against what CloudFormation last deployed. If someone manually added a security group rule, changed an instance type, or deleted a tag through the console, drift detection will show the difference. It helps you: (1) enforce "no manual changes" policies; (2) understand why a stack update failed (resource was modified outside CF); (3) audit infrastructure for compliance. It does NOT automatically fix drift — you either re-deploy the stack to restore the desired state or import the changed resource.
