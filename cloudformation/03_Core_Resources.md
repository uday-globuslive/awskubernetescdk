# Chapter 3: Core Resources
## S3, IAM, EC2 & Security Groups in CloudFormation

---

## 3.1 S3 Bucket

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: S3 bucket with versioning, encryption, and lifecycle

Parameters:
  BucketName:
    Type: String
    Description: S3 bucket name (must be globally unique)

Resources:

  # --------------------------------------------------
  # S3 Bucket — versioning, encryption, notifications
  # --------------------------------------------------
  AppDataBucket:
    Type: AWS::S3::Bucket
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Properties:
      BucketName: !Ref BucketName
      
      # Versioning
      VersioningConfiguration:
        Status: Enabled
      
      # Encryption at rest
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
            BucketKeyEnabled: true
      
      # Block all public access
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      
      # Lifecycle rules
      LifecycleConfiguration:
        Rules:
          - Id: MoveToIA
            Status: Enabled
            Transitions:
              - TransitionInDays: 90
                StorageClass: STANDARD_IA
              - TransitionInDays: 365
                StorageClass: GLACIER
            NoncurrentVersionTransitions:
              - TransitionInDays: 30
                StorageClass: STANDARD_IA
            NoncurrentVersionExpirationInDays: 90
      
      # Event notifications (notify Lambda on object creation)
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: "s3:ObjectCreated:*"
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: uploads/
                  - Name: suffix
                    Value: .csv
            Function: !GetAtt ProcessUploadFunction.Arn
      
      Tags:
        - Key: Environment
          Value: !Ref "AWS::StackName"

  # Bucket policy — allow read-only from a specific role
  AppDataBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref AppDataBucket
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: AllowSSLOnly
            Effect: Deny
            Principal: "*"
            Action: "s3:*"
            Resource:
              - !GetAtt AppDataBucket.Arn
              - !Sub "${AppDataBucket.Arn}/*"
            Condition:
              Bool:
                "aws:SecureTransport": false
          
          - Sid: AllowAppRole
            Effect: Allow
            Principal:
              AWS: !GetAtt AppRole.Arn
            Action:
              - s3:GetObject
              - s3:PutObject
              - s3:DeleteObject
            Resource: !Sub "${AppDataBucket.Arn}/*"

Outputs:
  BucketName:
    Value: !Ref AppDataBucket
    Export:
      Name: !Sub "${AWS::StackName}-BucketName"
  BucketArn:
    Value: !GetAtt AppDataBucket.Arn
    Export:
      Name: !Sub "${AWS::StackName}-BucketArn"
```

---

## 3.2 IAM Resources

```yaml
Resources:

  # --------------------------------------------------
  # IAM Role — for EC2 or Lambda
  # --------------------------------------------------
  AppRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${AWS::StackName}-app-role"
      
      # Trust policy — who can assume this role
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - ec2.amazonaws.com
                - lambda.amazonaws.com
            Action: sts:AssumeRole
      
      # Managed policies attached
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
      
      # Inline policies (defined inline)
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:DeleteObject
                Resource: !Sub "arn:aws:s3:::${BucketName}/*"
              - Effect: Allow
                Action:
                  - s3:ListBucket
                Resource: !Sub "arn:aws:s3:::${BucketName}"
      
      Tags:
        - Key: Environment
          Value: prod

  # --------------------------------------------------
  # Standalone managed policy (reusable across roles)
  # --------------------------------------------------
  ReadSecretsPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub "${AWS::StackName}-read-secrets"
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Action:
              - secretsmanager:GetSecretValue
            Resource:
              - !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/*"

  # --------------------------------------------------
  # Instance Profile — wraps Role for EC2 instances
  # --------------------------------------------------
  AppInstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      InstanceProfileName: !Sub "${AWS::StackName}-instance-profile"
      Roles:
        - !Ref AppRole
```

---

## 3.3 EC2 Security Group

```yaml
Resources:

  # --------------------------------------------------
  # VPC Security Groups
  # --------------------------------------------------
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: !Sub "${AWS::StackName}-alb-sg"
      GroupDescription: Security group for Application Load Balancer
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
          Description: HTTP from internet
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
          Description: HTTPS from internet
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-alb-sg"

  AppSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: !Sub "${AWS::StackName}-app-sg"
      GroupDescription: Security group for application servers
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        # Only accept traffic from ALB
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          SourceSecurityGroupId: !Ref ALBSecurityGroup
          Description: App port from ALB only
        # SSH from bastion only
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          SourceSecurityGroupId: !Ref BastionSecurityGroup
          Description: SSH from bastion
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-app-sg"

  DatabaseSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: !Sub "${AWS::StackName}-db-sg"
      GroupDescription: Security group for RDS
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        # Only accept connections from app tier
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref AppSecurityGroup
          Description: PostgreSQL from app servers only
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-db-sg"

  # Self-referencing rule (ElastiCache cluster members talk to each other)
  CacheSecurityGroupIngress:
    Type: AWS::EC2::SecurityGroupIngress
    Properties:
      GroupId: !Ref CacheSecurityGroup
      IpProtocol: tcp
      FromPort: 6379
      ToPort: 6379
      SourceSecurityGroupId: !Ref AppSecurityGroup
      Description: Redis from app servers
```

---

## 3.4 EC2 Instance

```yaml
Parameters:
  KeyPairName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: EC2 key pair for SSH access

  AmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64

Resources:

  # --------------------------------------------------
  # EC2 Instance
  # --------------------------------------------------
  AppInstance:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !Ref AmiId
      InstanceType: t3.medium
      KeyName: !Ref KeyPairName
      IamInstanceProfile: !Ref AppInstanceProfile
      SubnetId: !Select [0, !Ref PrivateSubnets]
      SecurityGroupIds:
        - !Ref AppSecurityGroup
      
      # Root volume
      BlockDeviceMappings:
        - DeviceName: /dev/xvda
          Ebs:
            VolumeSize: 30
            VolumeType: gp3
            Encrypted: true
            DeleteOnTermination: true
      
      # Bootstrap script
      UserData:
        !Base64
          Fn::Sub: |
            #!/bin/bash
            set -e
            yum update -y
            yum install -y python3-pip git
            
            # Install application
            pip3 install fastapi uvicorn boto3
            
            # Get secrets from Secrets Manager
            DB_CREDS=$(aws secretsmanager get-secret-value \
              --secret-id ${AWS::StackName}/db-credentials \
              --query SecretString --output text)
            
            # Signal CloudFormation success
            /opt/aws/bin/cfn-signal -e $? \
              --stack ${AWS::StackName} \
              --resource AppInstance \
              --region ${AWS::Region}
      
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-app"
    
    CreationPolicy:
      ResourceSignal:
        Timeout: PT10M

  # Elastic IP (optional — for fixed public IP)
  AppEIP:
    Type: AWS::EC2::EIP
    Condition: IsProd
    Properties:
      Domain: vpc
      InstanceId: !Ref AppInstance
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-eip"
```

---

## 3.5 Complete Working Template

```yaml
# core-resources.yaml — S3 + IAM + EC2 complete example
AWSTemplateFormatVersion: "2010-09-09"
Description: Core resources - S3, IAM Role, Security Group, EC2

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, prod]
    Default: dev
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetId:
    Type: AWS::EC2::Subnet::Id

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:
  AppBucket:
    Type: AWS::S3::Bucket
    DeletionPolicy: !If [IsProd, Retain, Delete]
    Properties:
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256

  AppRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: BucketAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: [s3:GetObject, s3:PutObject]
                Resource: !Sub "${AppBucket.Arn}/*"

  AppInstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles: [!Ref AppRole]

  AppSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: App server security group
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          CidrIp: 10.0.0.0/8

  AppInstance:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !Sub "{{resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64}}"
      InstanceType: !If [IsProd, t3.medium, t3.micro]
      SubnetId: !Ref SubnetId
      IamInstanceProfile: !Ref AppInstanceProfile
      SecurityGroupIds: [!Ref AppSG]
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-app"

Outputs:
  InstanceId:
    Value: !Ref AppInstance
  BucketName:
    Value: !Ref AppBucket
```

---

## 3.6 Interview Questions

**Q: Why do you need an InstanceProfile when attaching a Role to EC2?**
> An IAM Role is a standalone identity that can be assumed by various principals (EC2, Lambda, another service). An InstanceProfile is a container that holds a Role and is the mechanism through which EC2 instances can assume it. EC2 instances can only reference an InstanceProfile, not a Role directly. Lambda functions reference Roles directly. CloudFormation automatically creates an InstanceProfile with the same name as the Role when using `AWS::IAM::InstanceProfile`, but you must explicitly create it and reference it in the EC2 resource.

**Q: What is the recommended practice for security groups — reference by ID or CIDR?**
> Always reference by security group ID (`SourceSecurityGroupId`) rather than CIDR ranges where possible. This is more secure because: (1) IP ranges can change; (2) SG references automatically update when instances are added to the referenced group; (3) they convey intent clearly ("traffic from the ALB SG" vs "traffic from 10.0.0.0/8"). Use CIDR ranges only for external traffic (internet-facing ALB, VPN CIDR, office IP).

**Q: How does UserData work in CloudFormation and how do you ensure it ran successfully?**
> UserData is a Base64-encoded script that EC2 runs on first boot. In CloudFormation, use `!Base64` with `Fn::Sub` to inject stack variables into the script. To know if UserData ran successfully, install `cfn-init` and `cfn-signal` from the AWS CloudFormation helper scripts, and use `CreationPolicy` with `ResourceSignal` on the resource. The instance sends a success or failure signal at the end of the script, and CloudFormation waits for it before marking the resource complete — or rolls back if the signal indicates failure or the timeout is exceeded.
