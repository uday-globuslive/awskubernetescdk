# Chapter 2: Template Anatomy
## All Sections, Intrinsic Functions & Pseudo-Parameters

---

## 2.1 Template Structure

A CloudFormation template has up to 9 top-level sections. Only `Resources` is mandatory.

```yaml
AWSTemplateFormatVersion: "2010-09-09"   # Always this value
Description: "Human-readable description"  # Optional

Metadata:          # Extra info for console/tools — optional
Parameters:        # Input values at deploy time — optional
Mappings:          # Static lookup tables — optional
Conditions:        # Conditionally create resources — optional
Transform:         # SAM / macros — optional
Resources:         # REQUIRED — AWS resources to create
Outputs:           # Values to export or display — optional
```

---

## 2.2 Parameters — User Inputs

```yaml
Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
    Description: Deployment environment

  InstanceType:
    Type: String
    Default: t3.micro
    AllowedValues: [t3.micro, t3.small, t3.medium, m5.large]
    Description: EC2 instance type

  DBPassword:
    Type: String
    NoEcho: true    # Never show in console or CLI output
    MinLength: 8
    MaxLength: 128
    Description: Database master password

  CertificateArn:
    Type: String
    Default: ""
    Description: Optional ACM certificate ARN for HTTPS

  Subnets:
    Type: List<AWS::EC2::Subnet::Id>
    Description: List of subnet IDs for ALB

  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC for the application

  AmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64
    Description: Latest Amazon Linux 2023 AMI (auto-resolved from SSM)
```

```bash
# Pass parameters at deploy time
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name myapp-prod \
  --parameter-overrides \
    Environment=prod \
    InstanceType=t3.medium \
    DBPassword=SecurePass123!
```

---

## 2.3 Mappings — Static Lookup Tables

```yaml
Mappings:
  RegionToAMI:
    us-east-1:
      AMI: ami-0abcdef1234567890
    us-west-2:
      AMI: ami-0fedcba9876543210
    eu-west-1:
      AMI: ami-0123456789abcdef0

  EnvironmentConfig:
    dev:
      InstanceType: t3.micro
      DesiredCapacity: 1
      MinSize: 1
      MaxSize: 2
    prod:
      InstanceType: t3.medium
      DesiredCapacity: 3
      MinSize: 2
      MaxSize: 10

# Usage:
# !FindInMap [MapName, Key1, Key2]
# !FindInMap [RegionToAMI, !Ref AWS::Region, AMI]
# !FindInMap [EnvironmentConfig, !Ref Environment, InstanceType]
```

---

## 2.4 Conditions — Conditional Resource Creation

```yaml
Conditions:
  IsProd: !Equals [!Ref Environment, prod]
  IsNotProd: !Not [!Equals [!Ref Environment, prod]]
  HasCertificate: !Not [!Equals [!Ref CertificateArn, ""]]
  IsProdOrStaging: !Or
    - !Equals [!Ref Environment, prod]
    - !Equals [!Ref Environment, staging]

Resources:
  # Create this resource only in prod
  ReadReplica:
    Type: AWS::RDS::DBInstance
    Condition: IsProd
    Properties:
      SourceDBInstanceIdentifier: !Ref PrimaryDB
      DBInstanceClass: db.t3.medium

  # Conditionally use a value in a property
  MyALBListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      Protocol: !If [HasCertificate, HTTPS, HTTP]
      Port: !If [HasCertificate, 443, 80]
      Certificates:
        !If
          - HasCertificate
          - - CertificateArn: !Ref CertificateArn
          - !Ref AWS::NoValue   # Omit this property entirely
```

---

## 2.5 Resources — The Heart of the Template

```yaml
Resources:
  # Logical ID: your name for the resource (PascalCase)
  # Type: AWS service type
  # Properties: resource configuration

  MyBucket:
    Type: AWS::S3::Bucket
    DependsOn: MyRole          # Force creation order
    DeletionPolicy: Retain     # Don't delete when stack is deleted
    UpdateReplacePolicy: Retain  # Keep old resource when replaced
    Properties:
      BucketName: !Sub "my-bucket-${AWS::AccountId}-${AWS::Region}"
      Tags:
        - Key: Environment
          Value: !Ref Environment
```

---

## 2.6 Outputs — Export Values

```yaml
Outputs:
  VpcId:
    Description: VPC ID
    Value: !Ref MyVPC
    Export:
      Name: !Sub "${AWS::StackName}-VpcId"   # Export for cross-stack reference

  DBEndpoint:
    Description: RDS endpoint address
    Value: !GetAtt MyDatabase.Endpoint.Address

  APIUrl:
    Description: API Gateway URL
    Value: !Sub "https://${MyApi}.execute-api.${AWS::Region}.amazonaws.com/prod"
```

```bash
# View outputs
aws cloudformation describe-stacks \
  --stack-name myapp \
  --query "Stacks[0].Outputs"
```

---

## 2.7 Intrinsic Functions — Complete Reference

### !Ref

Returns a resource's default value (usually ID or name) or a parameter value.

```yaml
# On a resource → returns resource ID or name
SecurityGroupId: !Ref MySecurityGroup     # Returns sg-abc123
BucketName: !Ref MyBucket                 # Returns bucket name

# On a parameter → returns parameter value
InstanceType: !Ref InstanceTypeParam
```

### !GetAtt

Gets an attribute from a resource.

```yaml
# Syntax: !GetAtt LogicalResourceId.AttributeName
DBEndpoint: !GetAtt MyDatabase.Endpoint.Address
DBPort: !GetAtt MyDatabase.Endpoint.Port
BucketArn: !GetAtt MyBucket.Arn
LoadBalancerDNS: !GetAtt MyALB.DNSName
LambdaArn: !GetAtt MyFunction.Arn
RoleArn: !GetAtt MyRole.Arn
```

### !Sub

String substitution — replaces ${Variable} in a string.

```yaml
# Simple substitution with pseudo-parameters
BucketName: !Sub "my-app-${AWS::AccountId}-${AWS::Region}"
FunctionName: !Sub "${AWS::StackName}-processor"

# Substitute logical resource IDs
PolicyArn: !Sub "arn:aws:s3:::${MyBucket}/*"

# With explicit variable map (useful for complex substitutions)
PolicyDocument: !Sub
  - |
    {
      "Effect": "Allow",
      "Resource": "${BucketArn}/*"
    }
  - BucketArn: !GetAtt MyBucket.Arn
```

### !FindInMap

Look up a value in a Mappings table.

```yaml
# !FindInMap [MapName, TopLevelKey, SecondLevelKey]
ImageId: !FindInMap [RegionToAMI, !Ref AWS::Region, AMI]
InstanceType: !FindInMap [EnvironmentConfig, !Ref Environment, InstanceType]
```

### !If

Conditional value selection.

```yaml
# !If [ConditionName, ValueIfTrue, ValueIfFalse]
InstanceType: !If [IsProd, m5.large, t3.micro]
MultiAZ: !If [IsProd, true, false]

# Use AWS::NoValue to omit a property
Encrypted: !If [IsProd, true, !Ref AWS::NoValue]
```

### !Select

Pick one item from a list.

```yaml
# !Select [index, listOfValues]
FirstSubnet: !Select [0, !Ref Subnets]
SecondSubnet: !Select [1, !Ref Subnets]
```

### !Split

Split a string into a list.

```yaml
# !Split [delimiter, string]
SubnetList: !Split [",", !Ref SubnetIdsString]
# "subnet-a,subnet-b,subnet-c" → [subnet-a, subnet-b, subnet-c]
```

### !Join

Join a list into a string.

```yaml
# !Join [delimiter, [list, of, values]]
DBEndpointUrl: !Join
  - ""
  - - "jdbc:postgresql://"
    - !GetAtt MyDB.Endpoint.Address
    - ":"
    - !GetAtt MyDB.Endpoint.Port
    - "/mydb"

# Simpler: use !Sub instead
DBEndpointUrl: !Sub "jdbc:postgresql://${MyDB.Endpoint.Address}:${MyDB.Endpoint.Port}/mydb"
```

### !ImportValue

Import an exported output from another stack.

```yaml
# !ImportValue ExportName
VpcId: !ImportValue "networking-stack-VpcId"
PublicSubnet1: !ImportValue "networking-stack-PublicSubnet1"
```

### !Base64

Encode a string as Base64 (used for EC2 UserData).

```yaml
UserData:
  !Base64 |
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
```

### !Cidr

Generate a list of CIDR blocks.

```yaml
# !Cidr [ipBlock, count, sizeMask]
# Generate 4 /24 subnets from a /16 VPC CIDR
Subnets: !Cidr [!GetAtt VPC.CidrBlock, 4, 8]
```

---

## 2.8 Pseudo-Parameters

Pseudo-parameters are AWS-provided variables you can use anywhere in a template.

```yaml
# AWS::AccountId — current AWS account ID (e.g., 123456789012)
BucketName: !Sub "logs-${AWS::AccountId}"

# AWS::Region — current region (e.g., us-east-1)
Endpoint: !Sub "https://api.${AWS::Region}.amazonaws.com"

# AWS::StackName — name of the current stack (e.g., myapp-prod)
ResourceName: !Sub "${AWS::StackName}-function"

# AWS::StackId — full ARN of the stack
# arn:aws:cloudformation:us-east-1:123456789012:stack/myapp/abc-123

# AWS::Partition — aws, aws-cn, or aws-us-gov
PolicyArn: !Sub "arn:${AWS::Partition}:iam::aws:policy/ReadOnlyAccess"

# AWS::URLSuffix — amazonaws.com (or cn.amazonaws.com.cn in China)
Endpoint: !Sub "https://s3.${AWS::URLSuffix}"

# AWS::NoValue — removes a property entirely (used with !If)
OptionalProp: !If [HasOptional, SomeValue, !Ref AWS::NoValue]
```

---

## 2.9 Resource Attributes

### DependsOn

```yaml
# Force explicit creation order (usually CloudFormation handles this automatically)
MyInstance:
  Type: AWS::EC2::Instance
  DependsOn: MyInternetGatewayAttachment  # IGW must be attached first
  Properties: ...
```

### DeletionPolicy

```yaml
# What happens to the resource when the stack is deleted
MyBucket:
  Type: AWS::S3::Bucket
  DeletionPolicy: Retain   # Keep the bucket (default: Delete)

MyDatabase:
  Type: AWS::RDS::DBInstance
  DeletionPolicy: Snapshot  # Take final snapshot, then delete

# Values: Delete (default), Retain, Snapshot (for stateful resources)
```

### UpdateReplacePolicy

```yaml
# What happens to the OLD resource when it needs to be replaced
MyDatabase:
  Type: AWS::RDS::DBInstance
  UpdateReplacePolicy: Snapshot  # Snapshot old DB before replacing
  DeletionPolicy: Snapshot
```

### CreationPolicy

```yaml
# Wait for a signal before marking resource as CREATE_COMPLETE
# Used with EC2 AutoScaling — wait for instances to be "ready"
MyASG:
  Type: AWS::AutoScaling::AutoScalingGroup
  CreationPolicy:
    ResourceSignal:
      Count: 2        # Wait for 2 instances to signal success
      Timeout: PT15M  # Wait up to 15 minutes
```

### UpdatePolicy

```yaml
# Control how Auto Scaling groups are updated
MyASG:
  Type: AWS::AutoScaling::AutoScalingGroup
  UpdatePolicy:
    AutoScalingRollingUpdate:
      MinInstancesInService: 1
      MaxBatchSize: 2
      PauseTime: PT5M  # Wait 5 min between batches
      WaitOnResourceSignals: true
```

---

## 2.10 Interview Questions

**Q: What is the difference between !Ref and !GetAtt?**
> `!Ref` returns a resource's primary identifier — usually the resource ID (like `sg-abc123` for a security group, or the bucket name for S3). `!GetAtt` returns a specific attribute of a resource, like `!GetAtt MyBucket.Arn` for the full ARN, or `!GetAtt MyALB.DNSName` for the load balancer's DNS name. Use `!Ref` when you need the ID to link resources together; use `!GetAtt` when you need a specific property like ARN, endpoint, or DNS name.

**Q: How does !Sub work and when would you use it over !Join?**
> `!Sub` performs string interpolation — you embed `${VariableName}` in a string and CloudFormation substitutes the value. It's cleaner and more readable than `!Join`. Use `!Sub "arn:aws:s3:::${MyBucket}/*"` instead of `!Join ["", ["arn:aws:s3:::", !Ref MyBucket, "/*"]]`. `!Sub` can reference resource attributes directly with `${Resource.Attribute}` syntax. Only fall back to `!Join` when you need to join a list of values (e.g., join subnet IDs with commas).

**Q: What is DeletionPolicy and why is it important?**
> DeletionPolicy controls what happens to a resource when its stack is deleted (or when the resource is removed from the template). The default is `Delete` — which permanently removes the resource and its data. Set `Retain` on S3 buckets, DynamoDB tables, and other stateful resources to keep them even after stack deletion, preventing accidental data loss. Set `Snapshot` on RDS and ElastiCache resources to take a final snapshot before deletion. In production, always set DeletionPolicy on any resource that holds data you can't recreate.
