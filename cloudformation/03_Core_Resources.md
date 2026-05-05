# CloudFormation Chapter 3: Core Resources — EC2, IAM, S3 & Auto Scaling
## Complete Resource Definitions with All Key Properties

---

## 3.1 EC2 Instances — Full Configuration

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: EC2 with full configuration — security group, IAM role, user data

Parameters:
  InstanceType:
    Type: String
    Default: t3.micro
    AllowedValues: [t3.micro, t3.small, t3.medium, t3.large, m5.large, m5.xlarge]
  
  AmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64

  VpcId:
    Type: AWS::EC2::VPC::Id

  SubnetId:
    Type: AWS::EC2::Subnet::Id

  KeyPairName:
    Type: AWS::EC2::KeyPair::KeyName

Resources:
  # ── IAM Role for EC2 ─────────────────────────────────
  EC2InstanceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${AWS::StackName}-ec2-role'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore  # SSM Session Manager
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy   # CW Agent
      Policies:
        - PolicyName: AppPermissions
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub 'arn:aws:s3:::${AppBucket}/*'
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource: !Sub 'arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/*'
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-ec2-role'

  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      InstanceProfileName: !Sub '${AWS::StackName}-instance-profile'
      Roles:
        - !Ref EC2InstanceRole

  # ── Security Group ────────────────────────────────────
  AppSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: !Sub '${AWS::StackName}-app-sg'
      GroupDescription: Security group for application servers
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
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          CidrIp: 10.0.0.0/8
          Description: App port from internal networks
      SecurityGroupEgress:
        - IpProtocol: -1      # All traffic
          CidrIp: 0.0.0.0/0
          Description: Allow all outbound
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-app-sg'

  # ── EC2 Instance ──────────────────────────────────────
  AppInstance:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !Ref AmiId
      InstanceType: !Ref InstanceType
      KeyName: !Ref KeyPairName
      SubnetId: !Ref SubnetId
      SecurityGroupIds:
        - !Ref AppSecurityGroup
      IamInstanceProfile: !Ref EC2InstanceProfile
      DisableApiTermination: false    # Set true in prod
      EbsOptimized: true
      Monitoring: true                # Detailed CloudWatch monitoring (1-minute)
      BlockDeviceMappings:
        - DeviceName: /dev/xvda       # Root volume
          Ebs:
            VolumeSize: 30
            VolumeType: gp3
            Iops: 3000
            Throughput: 125           # MB/s
            Encrypted: true
            DeleteOnTermination: true
        - DeviceName: /dev/xvdb       # Data volume
          Ebs:
            VolumeSize: 100
            VolumeType: gp3
            Encrypted: true
            DeleteOnTermination: false  # Persist data volume
      MetadataOptions:
        HttpTokens: required          # Require IMDSv2 (security best practice)
        HttpPutResponseHopLimit: 1    # Limit hops (prevent SSRF)
        InstanceMetadataTags: enabled
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          set -e
          yum update -y
          
          # Install CloudWatch agent
          yum install -y amazon-cloudwatch-agent
          
          # Install app dependencies
          yum install -y python3 python3-pip nginx
          
          # Download and configure app
          aws s3 cp s3://${AppBucket}/app.tar.gz /tmp/
          tar -xzf /tmp/app.tar.gz -C /opt/
          
          # Signal CloudFormation success
          /opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} \
            --resource AppInstance --region ${AWS::Region}
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-app-server'
        - Key: Environment
          Value: !Ref Environment
    CreationPolicy:
      ResourceSignal:
        Timeout: PT10M    # Wait up to 10 minutes for cfn-signal

  # ── Elastic IP (optional) ─────────────────────────────
  AppEIP:
    Type: AWS::EC2::EIP
    Properties:
      Domain: vpc
      InstanceId: !Ref AppInstance
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-app-eip'
```

---

## 3.2 Auto Scaling Groups

```yaml
  # ── Launch Template (replaces Launch Configuration) ──
  AppLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub '${AWS::StackName}-lt'
      LaunchTemplateData:
        ImageId: !Ref AmiId
        InstanceType: !Ref InstanceType
        IamInstanceProfile:
          Arn: !GetAtt EC2InstanceProfile.Arn
        SecurityGroupIds:
          - !Ref AppSecurityGroup
        BlockDeviceMappings:
          - DeviceName: /dev/xvda
            Ebs:
              VolumeSize: 30
              VolumeType: gp3
              Encrypted: true
              DeleteOnTermination: true
        MetadataOptions:
          HttpTokens: required
          HttpPutResponseHopLimit: 1
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum update -y
            yum install -y python3 nginx
        TagSpecifications:
          - ResourceType: instance
            Tags:
              - Key: Name
                Value: !Sub '${AWS::StackName}-asg-instance'
              - Key: Environment
                Value: !Ref Environment

  # ── Auto Scaling Group ────────────────────────────────
  AppASG:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: !Sub '${AWS::StackName}-asg'
      LaunchTemplate:
        LaunchTemplateId: !Ref AppLaunchTemplate
        Version: !GetAtt AppLaunchTemplate.LatestVersionNumber
      MinSize: !If [IsProd, "2", "1"]
      MaxSize: !If [IsProd, "20", "4"]
      DesiredCapacity: !If [IsProd, "2", "1"]
      VPCZoneIdentifier:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      TargetGroupARNs:
        - !Ref AppTargetGroup
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      TerminationPolicies:
        - OldestLaunchTemplate   # Remove instances with old config first
        - OldestInstance
      MetricsCollection:
        - Granularity: 1Minute
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-asg'
          PropagateAtLaunch: true
    UpdatePolicy:
      AutoScalingRollingUpdate:
        MinInstancesInService: !If [IsProd, 1, 0]
        MaxBatchSize: 2
        PauseTime: PT5M
        WaitOnResourceSignals: true

  # ── Scaling Policies ──────────────────────────────────
  CPUScaleOutPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref AppASG
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ASGAverageCPUUtilization
        TargetValue: 70.0
        ScaleInCooldown: 300
        ScaleOutCooldown: 60

  # Custom metric scaling (SQS queue depth)
  SQSScalingPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref AppASG
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        CustomizedMetricSpecification:
          MetricName: ApproximateNumberOfMessagesVisible
          Namespace: AWS/SQS
          Dimensions:
            - Name: QueueName
              Value: !GetAtt AppQueue.QueueName
          Statistic: Average
          Unit: Count
        TargetValue: 10.0     # Target 10 messages per instance
```

---

## 3.3 IAM Resources — Roles, Policies, Users

```yaml
  # ── Cross-Account Role ────────────────────────────────
  CrossAccountRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: cross-account-deploy-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${TrustedAccountId}:root'
            Action: sts:AssumeRole
            Condition:
              Bool:
                aws:MultiFactorAuthPresent: true
              StringEquals:
                sts:ExternalId: !Ref ExternalId  # Confused deputy prevention
      MaxSessionDuration: 3600
      Path: /cross-account/

  # ── Customer Managed Policy ───────────────────────────
  S3ReadPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub '${AWS::StackName}-s3-read-policy'
      Description: Read access to application S3 bucket
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - s3:GetObject
              - s3:GetObjectVersion
              - s3:ListBucket
              - s3:GetBucketLocation
            Resource:
              - !GetAtt AppBucket.Arn
              - !Sub '${AppBucket.Arn}/*'

  # ── Service-Linked Role (example: ECS) ───────────────
  # Usually created automatically, but can be explicit:
  ECSServiceRole:
    Type: AWS::IAM::ServiceLinkedRole
    Properties:
      AWSServiceName: ecs.amazonaws.com

  # ── OIDC Provider for GitHub Actions ─────────────────
  GitHubOIDCProvider:
    Type: AWS::IAM::OIDCProvider
    Properties:
      Url: https://token.actions.githubusercontent.com
      ClientIdList:
        - sts.amazonaws.com
      ThumbprintList:
        - 6938fd4d98bab03faadb97b34396831e3780aea1

  GitHubActionsRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: github-actions-deploy-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Federated: !GetAtt GitHubOIDCProvider.Arn
            Action: sts:AssumeRoleWithWebIdentity
            Condition:
              StringEquals:
                token.actions.githubusercontent.com:aud: sts.amazonaws.com
              StringLike:
                token.actions.githubusercontent.com:sub: !Sub 'repo:${GitHubOrg}/${GitHubRepo}:*'
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonECR_FullAccess
```

---

## 3.4 S3 Buckets — Comprehensive Configuration

```yaml
  # ── Secure Application Bucket ─────────────────────────
  AppBucket:
    Type: AWS::S3::Bucket
    DeletionPolicy: Retain    # Don't delete bucket on stack deletion
    UpdateReplacePolicy: Retain
    Properties:
      BucketName: !Sub '${AWS::StackName}-app-${AWS::AccountId}'
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - BucketKeyEnabled: true   # Reduce KMS API calls/costs
            ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !Ref KMSKey
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      IntelligentTieringConfigurations:
        - Id: auto-tier
          Status: Enabled
          Tierings:
            - AccessTier: ARCHIVE_ACCESS
              Days: 90
            - AccessTier: DEEP_ARCHIVE_ACCESS
              Days: 180
      LifecycleConfiguration:
        Rules:
          - Id: transition-and-expire
            Status: Enabled
            Transitions:
              - StorageClass: STANDARD_IA
                TransitionInDays: 30
              - StorageClass: GLACIER
                TransitionInDays: 90
            NoncurrentVersionExpiration:
              NoncurrentDays: 30
            AbortIncompleteMultipartUpload:
              DaysAfterInitiation: 7
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: s3:ObjectCreated:*
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: uploads/
                  - Name: suffix
                    Value: .csv
            Function: !GetAtt ProcessUploadFunction.Arn
      ReplicationConfiguration:
        Role: !GetAtt S3ReplicationRole.Arn
        Rules:
          - Id: replicate-to-backup-region
            Status: Enabled
            Filter:
              Prefix: critical-data/
            Destination:
              Bucket: !Sub 'arn:aws:s3:::${AWS::StackName}-backup-${AWS::AccountId}'
              StorageClass: STANDARD_IA
              ReplicationTime:
                Status: Enabled
                Time:
                  Minutes: 15
              Metrics:
                Status: Enabled
      Tags:
        - Key: DataClassification
          Value: confidential

  # ── Bucket Policy ─────────────────────────────────────
  AppBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref AppBucket
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Sid: DenyUnencryptedObjectUploads
            Effect: Deny
            Principal: '*'
            Action: s3:PutObject
            Resource: !Sub '${AppBucket.Arn}/*'
            Condition:
              StringNotEquals:
                s3:x-amz-server-side-encryption: aws:kms
          - Sid: DenyNonSSLRequests
            Effect: Deny
            Principal: '*'
            Action: s3:*
            Resource:
              - !GetAtt AppBucket.Arn
              - !Sub '${AppBucket.Arn}/*'
            Condition:
              Bool:
                aws:SecureTransport: false
          - Sid: AllowAppRole
            Effect: Allow
            Principal:
              AWS: !GetAtt EC2InstanceRole.Arn
            Action:
              - s3:GetObject
              - s3:PutObject
              - s3:DeleteObject
            Resource: !Sub '${AppBucket.Arn}/*'
```

---

## 3.5 Interview Q&A

**Q: What is the DeletionPolicy attribute and when should you use Retain?**
A: `DeletionPolicy` controls what happens to a resource when the CloudFormation stack is deleted. Options: `Delete` (default — resource deleted with stack), `Retain` (resource kept but removed from stack management), `Snapshot` (creates final snapshot before deleting — for EBS, RDS, ElastiCache). Use `Retain` for S3 buckets with data, RDS databases with production data, and any resource you can't afford to lose accidentally. Also use `UpdateReplacePolicy: Retain` to prevent data loss when a resource replacement is triggered by an update.

**Q: What is the difference between a Launch Template and a Launch Configuration?**
A: Launch Configurations are the legacy approach — immutable, must create new one for every change, no versioning, being deprecated. Launch Templates support versioning (keep history), can be modified to create new versions, support mixed instance types (On-Demand + Spot), support instance refresh, and are required for newer features like Attribute-based Instance Selection. Always use Launch Templates for new ASGs. LTs also support spot override per instance type for cost optimization.

**Q: How do you implement zero-downtime rolling updates in CloudFormation?**
A: Using the `UpdatePolicy` on an AutoScaling group with `AutoScalingRollingUpdate`: set `MinInstancesInService` to keep minimum healthy instances during update (e.g., 1 for a 2-instance group), `MaxBatchSize` to limit how many instances update at once, and `WaitOnResourceSignals: true` with `cfn-signal` in UserData to only proceed after new instances confirm healthy. Combined with ELB health checks (`HealthCheckType: ELB`) and `HealthCheckGracePeriod`, this enables zero-downtime updates.
