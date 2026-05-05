# CloudFormation Chapter 10: Complete Projects
## Three Production-Grade Architecture Templates

---

## Project 1: Three-Tier Web Application

**Architecture**: CloudFront → ALB → ECS Fargate → Aurora Serverless v2

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CloudFront                                   │
│  (CDN, WAF, HTTPS termination, Origin Shield)                        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                    Application Load Balancer                         │
│  (HTTPS, /api/* → ECS, /* → S3 static site)                         │
└──────────┬──────────────────────────────┬───────────────────────────┘
           │                              │
┌──────────▼──────────┐        ┌──────────▼──────────┐
│   ECS Fargate       │        │   S3 Static Website │
│   (API service)     │        │   (React/Vue SPA)   │
│   2-10 tasks        │        └─────────────────────┘
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Aurora Serverless  │
│  (PostgreSQL 15)    │
│  0.5-8 ACUs         │
└─────────────────────┘
```

```yaml
# project1-three-tier.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Three-tier web application with CloudFront, ECS, and Aurora

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  
  ProjectName:
    Type: String
    Default: webapp
  
  ImageUri:
    Type: String
    Description: ECS container image URI
  
  DomainName:
    Type: String
    Description: Domain name (e.g., example.com)
  
  CertificateArn:
    Type: String
    Description: ACM certificate ARN for HTTPS

Mappings:
  EnvironmentConfig:
    dev:
      AuroraMinCapacity: 0.5
      AuroraMaxCapacity: 2
      EcsDesiredCount: 1
      EcsCpu: 256
      EcsMemory: 512
    staging:
      AuroraMinCapacity: 0.5
      AuroraMaxCapacity: 4
      EcsDesiredCount: 2
      EcsCpu: 512
      EcsMemory: 1024
    prod:
      AuroraMinCapacity: 1
      AuroraMaxCapacity: 16
      EcsDesiredCount: 3
      EcsCpu: 1024
      EcsMemory: 2048

Resources:
  # ── KMS Key ───────────────────────────────────────────
  EncryptionKey:
    Type: AWS::KMS::Key
    DeletionPolicy: Retain
    Properties:
      Description: !Sub '${ProjectName}-${Environment} encryption key'
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: Enable IAM User Permissions
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: 'kms:*'
            Resource: '*'

  KeyAlias:
    Type: AWS::KMS::Alias
    Properties:
      AliasName: !Sub 'alias/${ProjectName}-${Environment}'
      TargetKeyId: !Ref EncryptionKey

  # ── VPC ───────────────────────────────────────────────
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-${Environment}-vpc'

  InternetGateway:
    Type: AWS::EC2::InternetGateway
  
  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: false

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: false

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [0, !GetAZs '']

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.12.0/24
      AvailabilityZone: !Select [1, !GetAZs '']

  DbSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.21.0/24
      AvailabilityZone: !Select [0, !GetAZs '']

  DbSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.22.0/24
      AvailabilityZone: !Select [1, !GetAZs '']

  # ── Static Website S3 ─────────────────────────────────
  StaticWebsiteBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !Ref EncryptionKey
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  CloudFrontOAC:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: !Sub '${ProjectName}-${Environment}-oac'
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4

  StaticWebsiteBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref StaticWebsiteBucket
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: cloudfront.amazonaws.com
            Action: s3:GetObject
            Resource: !Sub '${StaticWebsiteBucket.Arn}/*'
            Condition:
              StringEquals:
                AWS:SourceArn: !Sub 'arn:aws:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}'

  # ── ALB Security Group ────────────────────────────────
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      VpcId: !Ref VPC
      GroupDescription: ALB security group
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0

  ECSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      VpcId: !Ref VPC
      GroupDescription: ECS tasks security group
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          SourceSecurityGroupId: !Ref ALBSecurityGroup

  AuroraSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      VpcId: !Ref VPC
      GroupDescription: Aurora security group
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref ECSSecurityGroup

  # ── ALB ───────────────────────────────────────────────
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Scheme: internet-facing
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup
      LoadBalancerAttributes:
        - Key: deletion_protection.enabled
          Value: !If [IsProd, 'true', 'false']
        - Key: access_logs.s3.enabled
          Value: 'true'
        - Key: access_logs.s3.bucket
          Value: !Ref LogsBucket

  ALBTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      VpcId: !Ref VPC
      Protocol: HTTP
      Port: 8000
      TargetType: ip
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3

  ALBListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ApplicationLoadBalancer
      Protocol: HTTPS
      Port: 443
      Certificates:
        - CertificateArn: !Ref CertificateArn
      SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref ALBTargetGroup

  # ── CloudFront ────────────────────────────────────────
  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        HttpVersion: http2and3
        PriceClass: PriceClass_100
        Aliases:
          - !Ref DomainName
        ViewerCertificate:
          AcmCertificateArn: !Ref CertificateArn
          SslSupportMethod: sni-only
          MinimumProtocolVersion: TLSv1.2_2021
        Origins:
          - Id: S3Origin
            DomainName: !GetAtt StaticWebsiteBucket.RegionalDomainName
            OriginAccessControlId: !Ref CloudFrontOAC
            S3OriginConfig: {}
          - Id: ALBOrigin
            DomainName: !GetAtt ApplicationLoadBalancer.DNSName
            CustomOriginConfig:
              HTTPSPort: 443
              OriginProtocolPolicy: https-only
              OriginSSLProtocols: [TLSv1.2]
        DefaultCacheBehavior:
          TargetOriginId: S3Origin
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods: [GET, HEAD]
          CachedMethods: [GET, HEAD]
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CachingOptimized
          Compress: true
        CacheBehaviors:
          - PathPattern: /api/*
            TargetOriginId: ALBOrigin
            ViewerProtocolPolicy: https-only
            AllowedMethods: [GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE]
            CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad  # CachingDisabled
            OriginRequestPolicyId: 216adef6-5c7f-47e4-b989-5492eafa07d3  # AllViewer
        WebACLId: !GetAtt WAFWebACL.Arn

  # ── Aurora Serverless v2 ──────────────────────────────
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Aurora subnet group
      SubnetIds:
        - !Ref DbSubnet1
        - !Ref DbSubnet2

  DBSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub '${ProjectName}/${Environment}/db-password'
      GenerateSecretString:
        SecretStringTemplate: '{"username": "dbadmin"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludeCharacters: '"@/\'

  AuroraCluster:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: !If [IsProd, Retain, Delete]
    UpdateReplacePolicy: !If [IsProd, Retain, Delete]
    Properties:
      Engine: aurora-postgresql
      EngineVersion: '15.4'
      DatabaseName: appdb
      MasterUsername: !Sub '{{resolve:secretsmanager:${DBSecret}:SecretString:username}}'
      ManageMasterUserPassword: false
      MasterUserPassword: !Sub '{{resolve:secretsmanager:${DBSecret}:SecretString:password}}'
      DBSubnetGroupName: !Ref DBSubnetGroup
      VpcSecurityGroupIds:
        - !Ref AuroraSecurityGroup
      StorageEncrypted: true
      KmsKeyId: !Ref EncryptionKey
      BackupRetentionPeriod: !If [IsProd, 30, 7]
      DeletionProtection: !If [IsProd, true, false]
      ServerlessV2ScalingConfiguration:
        MinCapacity: !FindInMap [EnvironmentConfig, !Ref Environment, AuroraMinCapacity]
        MaxCapacity: !FindInMap [EnvironmentConfig, !Ref Environment, AuroraMaxCapacity]

  AuroraInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBClusterIdentifier: !Ref AuroraCluster
      DBInstanceClass: db.serverless
      Engine: aurora-postgresql

  # ── ECS Fargate ───────────────────────────────────────
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterSettings:
        - Name: containerInsights
          Value: enabled

  TaskExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
      Policies:
        - PolicyName: read-secrets
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                  - kms:Decrypt
                Resource:
                  - !Ref DBSecret
                  - !GetAtt EncryptionKey.Arn

  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: !Sub '${ProjectName}-${Environment}'
      RequiresCompatibilities: [FARGATE]
      NetworkMode: awsvpc
      Cpu: !FindInMap [EnvironmentConfig, !Ref Environment, EcsCpu]
      Memory: !FindInMap [EnvironmentConfig, !Ref Environment, EcsMemory]
      ExecutionRoleArn: !GetAtt TaskExecutionRole.Arn
      ContainerDefinitions:
        - Name: app
          Image: !Ref ImageUri
          PortMappings:
            - ContainerPort: 8000
          Secrets:
            - Name: DATABASE_URL
              ValueFrom: !Sub '${DBSecret}:database_url::'
          Environment:
            - Name: ENVIRONMENT
              Value: !Ref Environment
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref AppLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: app
          HealthCheck:
            Command: [CMD-SHELL, 'curl -f http://localhost:8000/health || exit 1']
            Interval: 30
            Timeout: 5
            Retries: 3

  AppLogGroup:
    Type: AWS::Logs::LogGroup
    DeletionPolicy: Retain
    Properties:
      LogGroupName: !Sub '/ecs/${ProjectName}/${Environment}/app'
      RetentionInDays: !If [IsProd, 90, 14]

  ECSService:
    Type: AWS::ECS::Service
    DependsOn: ALBListener
    Properties:
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref TaskDefinition
      DesiredCount: !FindInMap [EnvironmentConfig, !Ref Environment, EcsDesiredCount]
      LaunchType: FARGATE
      NetworkConfiguration:
        AwsvpcConfiguration:
          Subnets:
            - !Ref PrivateSubnet1
            - !Ref PrivateSubnet2
          SecurityGroups:
            - !Ref ECSSecurityGroup
          AssignPublicIp: DISABLED
      LoadBalancers:
        - ContainerName: app
          ContainerPort: 8000
          TargetGroupArn: !Ref ALBTargetGroup
      DeploymentConfiguration:
        MinimumHealthyPercent: 100
        MaximumPercent: 200
        DeploymentCircuitBreaker:
          Enable: true
          Rollback: true

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Outputs:
  CloudFrontDomain:
    Value: !GetAtt CloudFrontDistribution.DomainName
    Export:
      Name: !Sub '${AWS::StackName}:CloudFrontDomain'
  
  AuroraEndpoint:
    Value: !GetAtt AuroraCluster.Endpoint.Address
    Export:
      Name: !Sub '${AWS::StackName}:AuroraEndpoint'
```

---

## Project 2: Serverless Microservices

**Architecture**: API Gateway → Lambda → DynamoDB + SQS queue

```yaml
# project2-serverless.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Serverless order processing microservice

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  
  ApiLambdaUri:
    Type: String
  
  WorkerLambdaUri:
    Type: String

Resources:
  # ── DynamoDB Single-Table ──────────────────────────────
  OrdersTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: Retain
    Properties:
      TableName: !Sub 'orders-${Environment}'
      BillingMode: PAY_PER_REQUEST
      TableClass: STANDARD
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL

  # ── SQS Queue ─────────────────────────────────────────
  OrdersDLQ:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub 'orders-dlq-${Environment}'
      KmsMasterKeyId: alias/aws/sqs
      MessageRetentionPeriod: 1209600   # 14 days

  OrdersQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub 'orders-${Environment}'
      KmsMasterKeyId: alias/aws/sqs
      VisibilityTimeout: 300
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt OrdersDLQ.Arn
        maxReceiveCount: 3

  # ── Lambda Execution Roles ────────────────────────────
  ApiLambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: api-permissions
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:Query
                Resource:
                  - !GetAtt OrdersTable.Arn
                  - !Sub '${OrdersTable.Arn}/index/*'
              - Effect: Allow
                Action:
                  - sqs:SendMessage
                Resource: !GetAtt OrdersQueue.Arn

  WorkerLambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: worker-permissions
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action:
                  - sqs:ReceiveMessage
                  - sqs:DeleteMessage
                  - sqs:GetQueueAttributes
                  - sqs:ChangeMessageVisibility
                Resource: !GetAtt OrdersQueue.Arn
              - Effect: Allow
                Action:
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                Resource: !GetAtt OrdersTable.Arn

  # ── Lambda Functions ──────────────────────────────────
  ApiFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub 'orders-api-${Environment}'
      Runtime: python3.11
      Handler: app.handler
      Role: !GetAtt ApiLambdaRole.Arn
      Code:
        ImageUri: !Ref ApiLambdaUri
      PackageType: Image
      Architectures: [arm64]
      MemorySize: 512
      Timeout: 29
      Environment:
        Variables:
          ORDERS_TABLE: !Ref OrdersTable
          ORDERS_QUEUE_URL: !Ref OrdersQueue
          ENVIRONMENT: !Ref Environment
      TracingConfig:
        Mode: Active
      LoggingConfig:
        LogFormat: JSON
        ApplicationLogLevel: INFO
        SystemLogLevel: WARN
        LogGroup: !Ref ApiLogGroup

  WorkerFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub 'orders-worker-${Environment}'
      Runtime: python3.11
      Handler: worker.handler
      Role: !GetAtt WorkerLambdaRole.Arn
      Code:
        ImageUri: !Ref WorkerLambdaUri
      PackageType: Image
      Architectures: [arm64]
      MemorySize: 1024
      Timeout: 300
      Environment:
        Variables:
          ORDERS_TABLE: !Ref OrdersTable
          ENVIRONMENT: !Ref Environment
      TracingConfig:
        Mode: Active

  WorkerEventSourceMapping:
    Type: AWS::Lambda::EventSourceMapping
    Properties:
      FunctionName: !Ref WorkerFunction
      EventSourceArn: !GetAtt OrdersQueue.Arn
      BatchSize: 10
      MaximumBatchingWindowInSeconds: 5
      FunctionResponseTypes:
        - ReportBatchItemFailures

  # ── API Gateway HTTP API ──────────────────────────────
  HttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: !Sub 'orders-api-${Environment}'
      ProtocolType: HTTP
      CorsConfiguration:
        AllowMethods: [GET, POST, PUT, DELETE, OPTIONS]
        AllowHeaders: ['*']
        AllowOrigins: !If
          - IsProd
          - ['https://myapp.com']
          - ['*']
        MaxAge: 300

  ApiIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${ApiFunction.Arn}/invocations'
      PayloadFormatVersion: '2.0'

  LambdaPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref ApiFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub '${HttpApi.Arn}/*/*'

  HttpApiRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: 'ANY /{proxy+}'
      Target: !Sub 'integrations/${ApiIntegration}'

  HttpApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref HttpApi
      StageName: '$default'
      AutoDeploy: true
      DefaultRouteSettings:
        ThrottlingBurstLimit: 1000
        ThrottlingRateLimit: 500

  ApiLogGroup:
    Type: AWS::Logs::LogGroup
    DeletionPolicy: Retain
    Properties:
      RetentionInDays: 30

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Outputs:
  ApiEndpoint:
    Value: !GetAtt HttpApi.ApiEndpoint
    Export:
      Name: !Sub '${AWS::StackName}:ApiEndpoint'
```

---

## Deployment Instructions

```bash
# ── Project 1: Three-Tier App ──────────────────────────

# 1. Create artifacts bucket
aws s3 mb s3://my-cfn-artifacts-$ACCOUNT_ID --region us-east-1

# 2. Package (uploads referenced templates/code to S3)
aws cloudformation package \
  --template-file project1-three-tier.yaml \
  --s3-bucket my-cfn-artifacts-$ACCOUNT_ID \
  --output-template-file packaged.yaml

# 3. Deploy dev first
aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name webapp-dev \
  --parameter-overrides \
    Environment=dev \
    ProjectName=webapp \
    ImageUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/webapp:latest \
    DomainName=dev.myapp.com \
    CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM

# 4. Promote to prod
aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name webapp-prod \
  --parameter-overrides \
    Environment=prod \
    ProjectName=webapp \
    ImageUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/webapp:v1.2.3 \
    DomainName=myapp.com \
    CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/xyz789 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --rollback-configuration 'RollbackTriggers=[{Arn=arn:aws:cloudwatch:us-east-1:123456789012:alarm/prod-5xx-rate,Type=AWS::CloudWatch::Alarm}],MonitoringTimeInMinutes=10'

# ── Project 2: Serverless Microservices ───────────────

# Deploy
aws cloudformation deploy \
  --template-file project2-serverless.yaml \
  --stack-name orders-dev \
  --parameter-overrides \
    Environment=dev \
    ApiLambdaUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/orders-api:latest \
    WorkerLambdaUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/orders-worker:latest \
  --capabilities CAPABILITY_IAM

# Get API endpoint
aws cloudformation describe-stacks \
  --stack-name orders-dev \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text
```

---

## Interview Q&A

**Q: How do you manage CloudFormation template parameters between environments?**
A: Use separate parameter files per environment (`parameters/dev.json`, `parameters/prod.json`) and pass them with `--parameter-overrides`. For sensitive values, store in SSM Parameter Store and use `{{resolve:ssm:/path/to/param}}` or in Secrets Manager with `{{resolve:secretsmanager:name:SecretString:key}}`. Avoid hardcoding account IDs — use `AWS::AccountId` pseudo-parameter. Use Mappings for config that varies by environment (sizing, retention periods) — this keeps it in the template and avoids parameter sprawl.

**Q: How do you handle the DeletionPolicy for production databases in CloudFormation?**
A: Set `DeletionPolicy: Retain` on production databases (`AWS::RDS::DBCluster`, `AWS::DynamoDB::Table`). Also set `UpdateReplacePolicy: Retain` to prevent replacement on update. Use `DeletionProtection: true` on RDS clusters. For DynamoDB, enable PITR. Combine with stack policies that deny `Update:Delete` and `Update:Replace` on database resources. In dev/staging, `DeletionPolicy: Delete` is fine (faster teardown). Consider `DeletionPolicy: Snapshot` for RDS to automatically take a final snapshot before deletion.

**Q: What is the `CAPABILITY_AUTO_EXPAND` capability and when is it needed?**
A: `CAPABILITY_AUTO_EXPAND` is required when deploying templates that contain macros (`Transform:` key). Without it, CloudFormation will refuse to deploy the template. SAM templates use `Transform: AWS::Serverless-2016-10-31`, so `CAPABILITY_AUTO_EXPAND` is always needed for SAM. For nested stacks (`AWS::CloudFormation::Stack`), you need `CAPABILITY_AUTO_EXPAND` only if the nested template itself contains a Transform. The three capabilities: `CAPABILITY_IAM` (creates IAM resources with auto-generated names), `CAPABILITY_NAMED_IAM` (creates IAM resources with explicit names), `CAPABILITY_AUTO_EXPAND` (expands macros/transforms). AWS CLI requires explicit acknowledgment because these operations have elevated privilege implications.
