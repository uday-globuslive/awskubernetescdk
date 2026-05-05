# CloudFormation Chapter 8: Advanced Features
## Nested Stacks, StackSets, Custom Resources, Macros & Drift Detection

---

## 8.1 Nested Stacks — Modular Infrastructure

```yaml
# root-stack.yaml — Master stack that composes nested stacks
AWSTemplateFormatVersion: '2010-09-09'
Description: Root stack composing network, security, app, and data stacks

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  
  ProjectName:
    Type: String
    Default: myapp
  
  TemplatesBucket:
    Type: String
    Description: S3 bucket containing nested stack templates

Resources:
  # ── Network Stack (VPC, Subnets, NAT) ─────────────────
  NetworkStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub 'https://${TemplatesBucket}.s3.${AWS::Region}.amazonaws.com/templates/vpc.yaml'
      Parameters:
        Environment: !Ref Environment
        ProjectName: !Ref ProjectName
        VpcCidr: 10.0.0.0/16
        EnableNatGateway: !If [IsProd, true, true]
        NatGatewayCount: !If [IsProd, 3, 1]
      TimeoutInMinutes: 30
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Layer
          Value: network

  # ── Security Stack (KMS, Security Groups, WAF) ────────
  SecurityStack:
    Type: AWS::CloudFormation::Stack
    DependsOn: NetworkStack
    Properties:
      TemplateURL: !Sub 'https://${TemplatesBucket}.s3.${AWS::Region}.amazonaws.com/templates/security.yaml'
      Parameters:
        Environment: !Ref Environment
        NetworkStackName: !GetAtt NetworkStack.Outputs.StackName
        VpcId: !GetAtt NetworkStack.Outputs.VpcId

  # ── Data Stack (Aurora, DynamoDB, ElastiCache) ────────
  DataStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - NetworkStack
      - SecurityStack
    Properties:
      TemplateURL: !Sub 'https://${TemplatesBucket}.s3.${AWS::Region}.amazonaws.com/templates/databases.yaml'
      Parameters:
        Environment: !Ref Environment
        NetworkStackName: !GetAtt NetworkStack.Outputs.StackName
        SecurityStackName: !GetAtt SecurityStack.Outputs.StackName

  # ── Application Stack (ECS, Lambda, API GW) ──────────
  AppStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - DataStack
    Properties:
      TemplateURL: !Sub 'https://${TemplatesBucket}.s3.${AWS::Region}.amazonaws.com/templates/app.yaml'
      Parameters:
        Environment: !Ref Environment
        NetworkStackName: !GetAtt NetworkStack.Outputs.StackName
        DataStackName: !GetAtt DataStack.Outputs.StackName
        ImageUri: !Sub '${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/myapp:latest'

Outputs:
  ApiEndpoint:
    Description: API endpoint URL
    Value: !GetAtt AppStack.Outputs.ApiEndpoint

  NetworkStackId:
    Value: !Ref NetworkStack
```

---

## 8.2 StackSets — Multi-Account/Region Deployment

```yaml
# stackset.yaml — Deploy security baseline across organization
AWSTemplateFormatVersion: '2010-09-09'
Description: Deploy CloudTrail and Config to all organization accounts

Resources:
  SecurityBaselineStackSet:
    Type: AWS::CloudFormation::StackSet
    Properties:
      StackSetName: security-baseline
      Description: Security baseline — CloudTrail, Config, GuardDuty
      PermissionModel: SERVICE_MANAGED    # Uses Organizations service role
      OrganizationalUnitIds:
        - !Ref ProductionOUId
        - !Ref StagingOUId
      AutoDeployment:
        Enabled: true    # Auto-deploy to new accounts in these OUs
        RetainStacksOnAccountRemoval: false
      ManagedExecution:
        Active: true     # Concurrent deployments (faster)
      DeploymentTargets:
        OrganizationalUnitIds:
          - ou-abc-12345678
      StackInstancesGroup:
        - DeploymentTargets:
            OrganizationalUnitIds:
              - ou-abc-12345678
          Regions:
            - us-east-1
            - eu-west-1
            - ap-southeast-1
      OperationPreferences:
        MaxConcurrentPercentage: 50      # Deploy to 50% of accounts at once
        FailureTolerancePercentage: 20   # Allow 20% failures before stopping
        RegionConcurrencyType: PARALLEL  # Deploy to all regions concurrently
      TemplateBody: |
        AWSTemplateFormatVersion: '2010-09-09'
        Resources:
          CloudTrail:
            Type: AWS::CloudTrail::Trail
            Properties:
              IsLogging: true
              IsMultiRegionTrail: true
              EnableLogFileValidation: true
              S3BucketName: central-cloudtrail-logs
          
          GuardDutyDetector:
            Type: AWS::GuardDuty::Detector
            Properties:
              Enable: true
              FindingPublishingFrequency: FIFTEEN_MINUTES
```

---

## 8.3 Custom Resources — Extend CloudFormation

Custom Resources let you run any code during stack operations.

```yaml
# custom-resource-example.yaml
Resources:
  # ── Custom Resource Lambda ────────────────────────────
  CustomResourceFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-custom-resource'
      Runtime: python3.11
      Handler: index.handler
      Role: !GetAtt CustomResourceRole.Arn
      Timeout: 300
      Code:
        ZipFile: |
          import boto3
          import json
          import cfnresponse
          
          def handler(event, context):
              request_type = event['RequestType']
              resource_properties = event['ResourceProperties']
              
              try:
                  if request_type == 'Create':
                      result = create_resource(resource_properties)
                      cfnresponse.send(event, context, cfnresponse.SUCCESS, 
                                       result, physical_resource_id=result['Id'])
                  
                  elif request_type == 'Update':
                      result = update_resource(resource_properties, 
                                               event['OldResourceProperties'])
                      cfnresponse.send(event, context, cfnresponse.SUCCESS, 
                                       result, physical_resource_id=event['PhysicalResourceId'])
                  
                  elif request_type == 'Delete':
                      delete_resource(event['PhysicalResourceId'])
                      cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
              
              except Exception as e:
                  print(f"Error: {e}")
                  cfnresponse.send(event, context, cfnresponse.FAILED,
                                   {'Error': str(e)})
          
          def create_resource(props):
              # Example: create Cognito user pool domain
              client = boto3.client('cognito-idp')
              client.create_user_pool_domain(
                  Domain=props['DomainPrefix'],
                  UserPoolId=props['UserPoolId']
              )
              return {'Id': props['DomainPrefix'], 'Domain': f"{props['DomainPrefix']}.auth.us-east-1.amazoncognito.com"}
          
          def delete_resource(physical_id):
              client = boto3.client('cognito-idp')
              # Delete the domain — need to look up UserPoolId
              pass

  # ── Custom Resource Usage ─────────────────────────────
  CognitoUserPoolDomain:
    Type: Custom::CognitoUserPoolDomain
    Properties:
      ServiceToken: !GetAtt CustomResourceFunction.Arn
      DomainPrefix: !Sub '${ProjectName}-${Environment}'
      UserPoolId: !Ref UserPool

  # ── Use Custom Resource Output ────────────────────────
  CognitoHostedUI:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Sub '/app/${Environment}/auth-domain'
      Type: String
      Value: !GetAtt CognitoUserPoolDomain.Domain
```

### AWS CDK Custom Resource (simpler approach)

```python
# In CDK, use AwsCustomResource for simple SDK calls
from aws_cdk import custom_resources as cr

# Example: enable a feature that CloudFormation doesn't support natively
custom_resource = cr.AwsCustomResource(
    self, "EnableAdvancedSecurity",
    on_create=cr.AwsSdkCall(
        service="wafv2",
        action="updateWebACL",
        parameters={
            "Name": "my-web-acl",
            "Scope": "REGIONAL",
            "Id": web_acl.attr_id,
            "LockToken": web_acl.attr_lock_token,
            "DefaultAction": {"Allow": {}},
            "VisibilityConfig": {"..."}
        },
        physical_resource_id=cr.PhysicalResourceId.of("waf-advanced-config")
    ),
    policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
        resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
    )
)
```

---

## 8.4 CloudFormation Macros — Transform Templates

```yaml
# macro-lambda.yaml — A CloudFormation macro
Resources:
  MacroFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: MyOrg-CommonTags
      Runtime: python3.11
      Handler: index.handler
      Code:
        ZipFile: |
          def handler(event, context):
              """Add standard tags to all resources that support tagging."""
              fragment = event['fragment']
              params = event['templateParameterValues']
              
              standard_tags = {
                  'ManagedBy': 'CloudFormation',
                  'StackName': params.get('AWS::StackName', 'unknown'),
                  'Environment': params.get('Environment', 'unknown'),
                  'LastUpdated': '2025-01-15'
              }
              
              # Add tags to all taggable resources
              for resource in fragment.get('Resources', {}).values():
                  props = resource.get('Properties', {})
                  existing_tags = props.get('Tags', [])
                  existing_tag_keys = {t.get('Key') for t in existing_tags}
                  
                  for key, value in standard_tags.items():
                      if key not in existing_tag_keys:
                          existing_tags.append({'Key': key, 'Value': value})
                  
                  props['Tags'] = existing_tags
              
              return {'requestId': event['requestId'], 'status': 'success', 'fragment': fragment}

  Macro:
    Type: AWS::CloudFormation::Macro
    Properties:
      Name: MyOrg-CommonTags
      FunctionName: !GetAtt MacroFunction.Arn

# Usage in templates:
# Transform: MyOrg-CommonTags  ← Applied to entire template
```

---

## 8.5 Drift Detection

```bash
# Detect drift across entire stack
aws cloudformation detect-stack-drift \
  --stack-name my-production-stack

# Check drift status
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id <detection-id>

# Get drifted resources
aws cloudformation describe-stack-resource-drifts \
  --stack-name my-production-stack \
  --stack-resource-drift-status-filters MODIFIED DELETED

# Result example:
# {
#   "LogicalResourceId": "AppSecurityGroup",
#   "ResourceType": "AWS::EC2::SecurityGroup",
#   "StackResourceDriftStatus": "MODIFIED",
#   "PropertyDifferences": [
#     {
#       "PropertyPath": "/SecurityGroupIngress/2",
#       "ExpectedValue": null,
#       "ActualValue": "{\"CidrIp\": \"0.0.0.0/0\", \"FromPort\": 22, ...}",
#       "DifferenceType": "ADD"
#     }
#   ]
# }

# Remediation: remove the manual change and update stack
# Or: update the template to match reality, then update stack
```

---

## 8.6 Stack Policies — Prevent Accidental Updates

```bash
# Create stack policy preventing deletion of production DB
aws cloudformation set-stack-policy \
  --stack-name prod-data-stack \
  --stack-policy-body '{
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "Update:*",
        "Resource": "*"
      },
      {
        "Effect": "Deny",
        "Principal": "*",
        "Action": ["Update:Replace", "Update:Delete"],
        "Resource": "LogicalResourceId/AuroraCluster"
      },
      {
        "Effect": "Deny",
        "Principal": "*",
        "Action": ["Update:Replace", "Update:Delete"],
        "Resource": "LogicalResourceId/OrdersTable"
      }
    ]
  }'

# Override policy temporarily for maintenance
aws cloudformation update-stack \
  --stack-name prod-data-stack \
  --template-body file://updated-template.yaml \
  --stack-policy-during-update-body '{
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "Update:*",
      "Resource": "*"
    }]
  }'
```

---

## 8.7 CloudFormation Guard — Policy-as-Code

```
# guard-rules.guard — Validate templates before deployment
# Run: cfn-guard validate -d template.yaml -r guard-rules.guard

rule s3_bucket_encrypted {
    AWS::S3::Bucket {
        Properties {
            BucketEncryption exists
            BucketEncryption.ServerSideEncryptionConfiguration[*].ServerSideEncryptionByDefault.SSEAlgorithm in ["AES256", "aws:kms"]
        }
    }
}

rule s3_block_public_access {
    AWS::S3::Bucket {
        Properties.PublicAccessBlockConfiguration {
            BlockPublicAcls == true
            BlockPublicPolicy == true
            IgnorePublicAcls == true
            RestrictPublicBuckets == true
        }
    }
}

rule rds_encrypted {
    AWS::RDS::DBInstance {
        Properties.StorageEncrypted == true
    }
    AWS::RDS::DBCluster {
        Properties.StorageEncrypted == true
    }
}

rule no_public_ec2 {
    AWS::EC2::Instance {
        Properties.NetworkInterfaces[*].AssociatePublicIpAddress != true
    }
}
```

---

## 8.8 Interview Q&A

**Q: What is the benefit of nested stacks over a single large template?**
A: Nested stacks solve CloudFormation's 500-resource-per-stack limit, enable reuse (deploy the same VPC template across projects), allow independent lifecycle management (update networking without touching app), enable parallel development by different teams, and improve maintainability. Drawbacks: more complex — root stack must be deployed before nested stacks, S3 hosting required for templates, debugging becomes harder. For small projects, a single stack is simpler. For large enterprise environments, nested stacks are essential.

**Q: When would you use a Custom Resource vs a native CloudFormation resource?**
A: Use Custom Resources when: (1) a resource type isn't supported by CloudFormation natively (some new AWS services, third-party APIs); (2) you need to perform side effects during deployment (populate data, call external APIs, trigger processes); (3) you need complex validation logic; (4) you need to look up dynamic values not available via SSM. The Lambda function MUST call `cfnresponse.send()` in all code paths (including errors) — failure to respond causes a timeout and stack gets stuck. Always add a `DependsOn` if your custom resource relies on other resources.

**Q: What is CloudFormation Guard (cfn-guard) and why use it?**
A: cfn-guard is an open-source policy-as-code tool that validates CloudFormation templates against rules before deployment. Rules are written in a DSL that matches template structure. Use in CI/CD pipelines to: enforce encryption standards (all S3 buckets must be encrypted), prevent public resources (no public EC2 IPs, no public S3 ACLs), ensure tagging requirements, validate parameter value ranges. Runs fast (seconds), catches misconfigurations before they reach AWS, works without AWS credentials. Part of a shift-left security strategy.
