# CloudFormation Chapter 2: Template Anatomy — Deep Dive
## Parameters, Mappings, Conditions, Intrinsic Functions & Metadata

---

## 2.1 Template Structure Overview

```yaml
# Complete template structure — ALL sections
AWSTemplateFormatVersion: '2010-09-09'   # Required, only valid value
Description: "String describing this template (max 1024 chars)"

Metadata:                  # Arbitrary data, used by console/tools
  ...

Parameters:                # Input values (up to 200)
  ...

Rules:                     # Validate parameter combinations
  ...

Mappings:                  # Static lookup tables
  ...

Conditions:                # Boolean flags controlling resource creation
  ...

Transform:                 # Macros (SAM, Serverless transforms)
  ...

Resources:                 # REQUIRED — AWS resources to create (up to 500)
  ...

Outputs:                   # Values to export (up to 200)
  ...
```

---

## 2.2 Parameters — Input Values

```yaml
Parameters:
  # String parameter
  AppName:
    Type: String
    Default: my-app
    MinLength: 3
    MaxLength: 50
    AllowedPattern: '[a-zA-Z][a-zA-Z0-9-]*'
    ConstraintDescription: Must start with a letter and contain only alphanumeric chars and hyphens

  # Constrained choice
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Default: dev

  # Number with range
  MinInstances:
    Type: Number
    Default: 1
    MinValue: 1
    MaxValue: 100

  # Sensitive value (hidden in console/CLI)
  DBPassword:
    Type: String
    NoEcho: true        # Value masked in console and describe-stacks output
    MinLength: 8

  # Comma-separated list
  AllowedCIDRs:
    Type: CommaDelimitedList
    Default: "10.0.0.0/8,172.16.0.0/12"

  # AWS-specific types (auto-validated against account resources)
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: Select a VPC from your account

  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Select subnets (multi-select)

  KeyPairName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: EC2 key pair for SSH access

  AMIId:
    Type: AWS::EC2::Image::Id
    Default: ami-0abcdef1234567890

  # AWS SSM Parameter — fetches value from SSM at deploy time
  LatestAMI:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2

  # Resolve SSM SecureString
  DBPasswordSSM:
    Type: AWS::SSM::Parameter::Value<String>
    Default: /prod/database/password
```

---

## 2.3 Mappings — Static Lookup Tables

```yaml
Mappings:
  # Region-specific AMI mapping
  RegionAMI:
    us-east-1:
      Amazon: ami-0abcdef1234567890
      Ubuntu: ami-0fedcba0987654321
    us-west-2:
      Amazon: ami-0111222333444555a
      Ubuntu: ami-0aabbccddeeff0011
    eu-west-1:
      Amazon: ami-0a1b2c3d4e5f67890
      Ubuntu: ami-0fedcba9876543210

  # Environment-specific instance sizing
  EnvironmentConfig:
    dev:
      InstanceType: t3.micro
      MinCapacity: 1
      MaxCapacity: 2
      MultiAZ: false
    staging:
      InstanceType: t3.medium
      MinCapacity: 1
      MaxCapacity: 4
      MultiAZ: false
    prod:
      InstanceType: m5.xlarge
      MinCapacity: 2
      MaxCapacity: 20
      MultiAZ: true

# Usage with FindInMap
Resources:
  WebServer:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !FindInMap [RegionAMI, !Ref AWS::Region, Amazon]
      InstanceType: !FindInMap [EnvironmentConfig, !Ref Environment, InstanceType]

  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      MultiAZ: !FindInMap [EnvironmentConfig, !Ref Environment, MultiAZ]
```

---

## 2.4 Conditions — Conditional Resource Creation

```yaml
Conditions:
  # Simple conditions
  IsProd: !Equals [!Ref Environment, prod]
  IsNotProd: !Not [!Equals [!Ref Environment, prod]]
  IsDevOrStaging: !Or
    - !Equals [!Ref Environment, dev]
    - !Equals [!Ref Environment, staging]
  
  # Combined conditions
  IsProdAndMultiAZ: !And
    - !Condition IsProd
    - !Equals [!Ref EnableMultiAZ, true]
  
  HasCustomDomain: !Not [!Equals [!Ref DomainName, ""]]

# Use conditions on resources, properties, and outputs
Resources:
  # Create resource only in prod
  ElasticacheCluster:
    Type: AWS::ElastiCache::ReplicationGroup
    Condition: IsProd    # This entire resource only created in prod
    Properties:
      ...

  WebServerGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      MinSize: !If [IsProd, "2", "1"]      # Property value based on condition
      MaxSize: !If [IsProd, "20", "4"]
      MultiAZWithShortLeadTime: !If [IsProd, true, !Ref AWS::NoValue]  # Omit in non-prod

  # Optional resource
  CustomDomainCertificate:
    Type: AWS::CertificateManager::Certificate
    Condition: HasCustomDomain
    Properties:
      DomainName: !Ref DomainName
      ValidationMethod: DNS
```

---

## 2.5 Intrinsic Functions — Reference, Transform, Select

```yaml
# ── REF ──────────────────────────────────────────────────
# Returns resource's physical ID or parameter value
VPC:
  Type: AWS::EC2::VPC
  Properties:
    CidrBlock: !Ref VpcCidr    # Returns parameter value

Subnet:
  Type: AWS::EC2::Subnet
  Properties:
    VpcId: !Ref VPC            # Returns VPC's physical ID (vpc-0abc...)

# ── GETATT ───────────────────────────────────────────────
# Returns attribute of a resource (not just the ID)
BucketPolicy:
  Type: AWS::S3::BucketPolicy
  Properties:
    Bucket: !Ref MyBucket
    PolicyDocument:
      Statement:
        - Principal:
            AWS: !GetAtt LambdaRole.Arn   # Gets ARN of IAM role
        - Resource: !GetAtt MyBucket.Arn  # Gets ARN of bucket

# ── SUB ──────────────────────────────────────────────────
# String substitution with ${Variable}
Resources:
  Instance:
    Properties:
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-web-server'   # Built-in pseudo params
        - Key: Region
          Value: !Sub '${AWS::Region}'
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          yum update -y
          aws s3 cp s3://${ConfigBucket}/app.tar.gz /tmp/
          echo "Stack: ${AWS::StackName}" > /etc/stack-info

# ── JOIN ─────────────────────────────────────────────────
# Joins array of values with delimiter
SG:
  Properties:
    GroupDescription: !Join [' ', ['Security group for', !Ref AppName, 'in', !Ref Environment]]

FQDN:
  Value: !Join ['.', [!Ref AppName, !Ref Environment, 'example.com']]

# ── SELECT ───────────────────────────────────────────────
# Select item from list by index
SubnetA:
  Properties:
    CidrBlock: !Select [0, !Ref SubnetCIDRs]  # First item in list
SubnetB:
  Properties:
    CidrBlock: !Select [1, !Ref SubnetCIDRs]  # Second item

# ── SPLIT ────────────────────────────────────────────────
# Split string into list
ARNParts:
  Value: !Select [4, !Split [':', !GetAtt MyLambda.Arn]]  # Get account from ARN

# ── CIDR ─────────────────────────────────────────────────
# Generate subnet CIDRs from a VPC CIDR
VPC:
  Properties:
    CidrBlock: 10.0.0.0/16

PublicSubnet1:
  Properties:
    CidrBlock: !Select [0, !Cidr [!GetAtt VPC.CidrBlock, 6, 8]]  # 10.0.0.0/24
PublicSubnet2:
  Properties:
    CidrBlock: !Select [1, !Cidr [!GetAtt VPC.CidrBlock, 6, 8]]  # 10.0.1.0/24
PrivateSubnet1:
  Properties:
    CidrBlock: !Select [2, !Cidr [!GetAtt VPC.CidrBlock, 6, 8]]  # 10.0.2.0/24

# ── IF ───────────────────────────────────────────────────
DBStorage:
  Properties:
    AllocatedStorage: !If [IsProd, 500, 20]
    StorageType: !If [IsProd, io1, gp3]
    Iops: !If [IsProd, 3000, !Ref AWS::NoValue]  # AWS::NoValue removes the property

# ── TRANSFORM (inline macro) ─────────────────────────────
SomeList:
  Value:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: s3://my-bucket/templates/common-tags.yaml
```

---

## 2.6 Pseudo Parameters

```yaml
# Built-in parameters always available
AWS::AccountId        # 123456789012
AWS::Region           # us-east-1
AWS::StackId          # arn:aws:cloudformation:us-east-1:123:stack/my-stack/uuid
AWS::StackName        # my-stack
AWS::Partition        # aws (or aws-cn, aws-us-gov)
AWS::URLSuffix        # amazonaws.com (or amazonaws.com.cn)
AWS::NoValue          # Removes property when used in Fn::If

# Example usage
BucketPolicy:
  Properties:
    PolicyDocument:
      Statement:
        - Principal:
            AWS: !Sub 'arn:${AWS::Partition}:iam::${AWS::AccountId}:root'
          Resource: !Sub 'arn:${AWS::Partition}:s3:::${BucketName}/*'
```

---

## 2.7 Outputs — Export Values for Cross-Stack References

```yaml
Outputs:
  # Simple output
  WebURL:
    Description: URL of the web application
    Value: !Sub 'https://${ALB.DNSName}'

  # Export for cross-stack import
  VpcId:
    Description: VPC ID for use by other stacks
    Value: !Ref VPC
    Export:
      Name: !Sub '${AWS::StackName}-VpcId'
      # Convention: StackName-ResourceDescription

  PublicSubnet1Id:
    Description: Public subnet 1
    Value: !Ref PublicSubnet1
    Export:
      Name: !Sub '${AWS::StackName}-PublicSubnet1'

# ── IMPORT IN ANOTHER STACK ──────────────────────────────
# In a separate stack file:
Resources:
  SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      VpcId: !ImportValue 'network-stack-VpcId'   # Imports from network-stack's export

  ECSService:
    Type: AWS::ECS::Service
    Properties:
      NetworkConfiguration:
        AwsvpcConfiguration:
          Subnets:
            - !ImportValue 'network-stack-PublicSubnet1'
            - !ImportValue 'network-stack-PublicSubnet2'
```

---

## 2.8 Metadata — Console Grouping & cfn-init

```yaml
Metadata:
  # Group parameters in CloudFormation console
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label:
          default: "Network Configuration"
        Parameters:
          - VpcId
          - SubnetIds
          - AllowedCIDR
      - Label:
          default: "Application Configuration"
        Parameters:
          - AppName
          - Environment
          - InstanceType
      - Label:
          default: "Database Configuration"
        Parameters:
          - DBPassword
          - DBInstanceClass
    ParameterLabels:
      VpcId:
        default: "VPC"
      DBPassword:
        default: "Database Password"

  # cfn-init configuration
  AWS::CloudFormation::Init:
    config:
      packages:
        yum:
          nginx: []
          python3: []
      files:
        /etc/nginx/nginx.conf:
          content: !Sub |
            server {
              listen 80;
              server_name ${AppName}.${AWS::Region}.amazonaws.com;
              location / {
                proxy_pass http://localhost:8000;
              }
            }
          mode: "000644"
          owner: root
          group: root
      commands:
        start-app:
          command: "systemctl start nginx"
      services:
        sysvinit:
          nginx:
            enabled: true
            ensureRunning: true
            files: [/etc/nginx/nginx.conf]
```

---

## 2.9 DependsOn and Resource Ordering

```yaml
Resources:
  InternetGateway:
    Type: AWS::EC2::InternetGateway

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # Must wait for IGW attachment before creating route
  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment  # Explicit dependency
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  # DependsOn with list
  Application:
    Type: AWS::ECS::Service
    DependsOn:
      - ALBListener       # Wait for listener before creating service
      - TargetGroup
      - LogGroup
    Properties:
      ...
```

---

## 2.10 Interview Q&A

**Q: What is the difference between Ref and GetAtt in CloudFormation?**
A: `!Ref` returns the "natural" identifier of a resource — usually the physical ID (e.g., VPC ID for EC2::VPC, bucket name for S3::Bucket, function name for Lambda::Function, role name for IAM::Role). `!GetAtt` returns a specific attribute of a resource that may differ from its ID — e.g., `!GetAtt MyBucket.Arn` returns the ARN, `!GetAtt LoadBalancer.DNSName` returns the DNS name, `!GetAtt LambdaFunction.Arn` returns the ARN. Check the CloudFormation resource documentation for available attributes.

**Q: What is Fn::Sub and how does it differ from Fn::Join?**
A: `!Sub` performs string substitution using `${Variable}` syntax — cleaner and more readable. Variables can be parameter names, resource logical IDs (returns the `Ref` value), or explicit key-value pairs `${VariableName}`. `!Join` concatenates an array of values with a delimiter — more verbose. `!Sub '${AWS::StackName}-${AppName}'` vs `!Join ['-', [!Ref AWS::StackName, !Ref AppName]]`. Use `!Sub` for template strings and `!Join` when building dynamic arrays.

**Q: How do CloudFormation exports and imports work? What are the limitations?**
A: Exports create a globally unique name (per region/account) mapping to a value. Other stacks import using `!ImportValue 'export-name'`. Limitations: (1) Export names must be unique per region; (2) You cannot delete a stack that has exports being imported by another stack (you must delete the importing stack first); (3) Changes to exports require updating all importing stacks. Best practice: name exports as `${StackName}-ResourceDescription` to avoid conflicts. For complex dependencies, consider SSM Parameter Store or DynamoDB to pass values between stacks instead.
