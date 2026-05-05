# CloudFormation Chapter 6: Container Stack — ECS Fargate & ECR
## Complete ECS Service, Task Definitions, and Container Registry Templates

---

## 6.1 ECS Fargate — Complete Stack

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: ECS Fargate service with ALB, Service Connect, and auto-scaling

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Default: dev

  ImageUri:
    Type: String
    Description: Full ECR image URI (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.2.3)

  DesiredCount:
    Type: Number
    Default: 2

  CpuUnits:
    Type: Number
    Default: 512
    AllowedValues: [256, 512, 1024, 2048, 4096]

  MemoryMiB:
    Type: Number
    Default: 1024

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:
  # ── ECS Cluster ────────────────────────────────────────
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub '${AWS::StackName}-cluster'
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE
          Base: 2              # At least 2 tasks on FARGATE (not Spot)
          Weight: 1
        - CapacityProvider: FARGATE_SPOT
          Base: 0
          Weight: 4            # Remaining tasks on Spot (80% cheaper)
      ClusterSettings:
        - Name: containerInsights
          Value: enabled
      ServiceConnectDefaults:
        Namespace: !Sub '${AWS::StackName}-namespace'

  # ── CloudWatch Log Group ───────────────────────────────
  AppLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/ecs/${AWS::StackName}/app'
      RetentionInDays: !If [IsProd, 90, 14]

  # ── Task Execution Role ────────────────────────────────
  TaskExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${AWS::StackName}-task-execution-role'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
      Policies:
        - PolicyName: SecretAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                  - kms:Decrypt
                Resource:
                  - !Sub 'arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/*'
                  - !GetAtt AppKMSKey.Arn

  # ── Task Role (app runtime permissions) ───────────────
  TaskRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${AWS::StackName}-task-role'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: AppPermissions
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:Query
                Resource: !GetAtt AppTable.Arn
              - Effect: Allow
                Action:
                  - sqs:SendMessage
                  - sqs:ReceiveMessage
                  - sqs:DeleteMessage
                  - sqs:GetQueueAttributes
                Resource: !GetAtt AppQueue.Arn
              # Allow ECS Exec (for debugging)
              - Effect: Allow
                Action:
                  - ssmmessages:CreateControlChannel
                  - ssmmessages:CreateDataChannel
                  - ssmmessages:OpenControlChannel
                  - ssmmessages:OpenDataChannel
                Resource: '*'

  # ── Task Definition ────────────────────────────────────
  AppTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: !Sub '${AWS::StackName}-app'
      RequiresCompatibilities:
        - FARGATE
      NetworkMode: awsvpc
      Cpu: !Ref CpuUnits
      Memory: !Ref MemoryMiB
      ExecutionRoleArn: !GetAtt TaskExecutionRole.Arn
      TaskRoleArn: !GetAtt TaskRole.Arn
      ContainerDefinitions:
        - Name: app
          Image: !Ref ImageUri
          Essential: true
          PortMappings:
            - ContainerPort: 8000
              Protocol: tcp
              Name: app-port     # Named port for Service Connect
              AppProtocol: http
          Environment:
            - Name: ENVIRONMENT
              Value: !Ref Environment
            - Name: APP_TABLE_NAME
              Value: !Ref AppTable
            - Name: LOG_LEVEL
              Value: !If [IsProd, INFO, DEBUG]
          Secrets:
            - Name: DATABASE_URL
              ValueFrom: !Sub 'arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/db-url'
            - Name: API_KEY
              ValueFrom: !Sub '/ssm/${AWS::StackName}/api-key'
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref AppLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: app
          HealthCheck:
            Command:
              - CMD-SHELL
              - "curl -f http://localhost:8000/health || exit 1"
            Interval: 30
            Timeout: 5
            Retries: 3
            StartPeriod: 60    # Grace period for startup
          ReadonlyRootFilesystem: true    # Security best practice
          User: "1001"                    # Non-root user
          ResourceRequirements: []
          StopTimeout: 30                 # Grace period for graceful shutdown
          LinuxParameters:
            InitProcessEnabled: true      # Enable init process (reap zombies)

        # Sidecar: FireLens log router
        - Name: log-router
          Image: amazon/aws-for-fluent-bit:stable
          Essential: false
          FirelensConfiguration:
            Type: fluentbit
            Options:
              enable-ecs-log-metadata: "true"
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref AppLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: firelens

  # ── ECS Service ────────────────────────────────────────
  AppService:
    Type: AWS::ECS::Service
    DependsOn:
      - AppListenerRule
    Properties:
      ServiceName: !Sub '${AWS::StackName}-app'
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref AppTaskDefinition
      DesiredCount: !Ref DesiredCount
      LaunchType: FARGATE
      PlatformVersion: LATEST
      NetworkConfiguration:
        AwsvpcConfiguration:
          AssignPublicIp: DISABLED
          Subnets: !Split [',', !ImportValue 'network-stack-PrivateSubnets']
          SecurityGroups:
            - !Ref AppSecurityGroup
      LoadBalancers:
        - ContainerName: app
          ContainerPort: 8000
          TargetGroupArn: !Ref AppTargetGroup
      ServiceConnectConfiguration:
        Enabled: true
        Namespace: !Sub '${AWS::StackName}-namespace'
        Services:
          - PortName: app-port
            DiscoveryName: app
            ClientAliases:
              - Port: 8000
                DnsName: app
        LogConfiguration:
          LogDriver: awslogs
          Options:
            awslogs-group: !Ref AppLogGroup
            awslogs-region: !Ref AWS::Region
            awslogs-stream-prefix: service-connect
      DeploymentConfiguration:
        MaximumPercent: 200
        MinimumHealthyPercent: 100
        DeploymentCircuitBreaker:
          Enable: true
          Rollback: true    # Auto-rollback on failed deployment
      EnableExecuteCommand: true    # ECS Exec for debugging
      PropagateTags: TASK_DEFINITION
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # ── Auto Scaling ───────────────────────────────────────
  ScalableTarget:
    Type: AWS::ApplicationAutoScaling::ScalableTarget
    Properties:
      ServiceNamespace: ecs
      ResourceId: !Sub 'service/${ECSCluster}/${AppService.Name}'
      ScalableDimension: ecs:service:DesiredCount
      MinCapacity: !If [IsProd, 2, 1]
      MaxCapacity: !If [IsProd, 50, 10]
      RoleARN: !Sub 'arn:aws:iam::${AWS::AccountId}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService'

  CPUScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: cpu-target-tracking
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref ScalableTarget
      TargetTrackingScalingPolicyConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ECSServiceAverageCPUUtilization
        TargetValue: 70.0
        ScaleOutCooldown: 60
        ScaleInCooldown: 300

  RequestScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: alb-request-tracking
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref ScalableTarget
      TargetTrackingScalingPolicyConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ALBRequestCountPerTarget
          ResourceLabel: !Sub
            - '${ALBSuffix}/${TargetGroupSuffix}'
            - ALBSuffix: !GetAtt AppALB.LoadBalancerFullName
              TargetGroupSuffix: !GetAtt AppTargetGroup.TargetGroupFullName
        TargetValue: 1000.0    # 1000 requests per task
```

---

## 6.2 ECR — Elastic Container Registry

```yaml
  # ── ECR Repository ─────────────────────────────────────
  AppECRRepository:
    Type: AWS::ECR::Repository
    DeletionPolicy: Retain
    Properties:
      RepositoryName: !Sub '${ProjectName}/app'
      ImageTagMutability: IMMUTABLE    # Cannot overwrite existing tags
      ImageScanningConfiguration:
        ScanOnPush: true              # Scan for vulnerabilities on push
      EncryptionConfiguration:
        EncryptionType: KMS
        KmsKey: !GetAtt AppKMSKey.Arn
      LifecyclePolicy:
        LifecyclePolicyText: |
          {
            "rules": [
              {
                "rulePriority": 1,
                "description": "Keep last 20 tagged images",
                "selection": {
                  "tagStatus": "tagged",
                  "tagPrefixList": ["v"],
                  "countType": "imageCountMoreThan",
                  "countNumber": 20
                },
                "action": {"type": "expire"}
              },
              {
                "rulePriority": 2,
                "description": "Expire untagged images older than 7 days",
                "selection": {
                  "tagStatus": "untagged",
                  "countType": "sinceImagePushed",
                  "countUnit": "days",
                  "countNumber": 7
                },
                "action": {"type": "expire"}
              }
            ]
          }

  # ── Cross-Account ECR Policy ───────────────────────────
  AppECRRepositoryPolicy:
    Type: AWS::ECR::RepositoryPolicy
    Properties:
      RepositoryName: !Ref AppECRRepository
      PolicyText:
        Version: '2012-10-17'
        Statement:
          - Sid: CrossAccountPull
            Effect: Allow
            Principal:
              AWS:
                - !Sub 'arn:aws:iam::${DevAccountId}:root'
                - !Sub 'arn:aws:iam::${StagingAccountId}:root'
            Action:
              - ecr:GetDownloadUrlForLayer
              - ecr:BatchGetImage
              - ecr:BatchCheckLayerAvailability

Outputs:
  ClusterName:
    Value: !Ref ECSCluster
    Export:
      Name: !Sub '${AWS::StackName}-ClusterName'

  ServiceName:
    Value: !GetAtt AppService.Name
    Export:
      Name: !Sub '${AWS::StackName}-ServiceName'

  ECRRepositoryUri:
    Value: !GetAtt AppECRRepository.RepositoryUri
    Export:
      Name: !Sub '${AWS::StackName}-ECRRepositoryUri'
```

---

## 6.3 Interview Q&A

**Q: What is the difference between TaskExecutionRole and TaskRole in ECS?**
A: TaskExecutionRole is used by the ECS agent on your behalf to pull Docker images from ECR, push logs to CloudWatch, and retrieve secrets from Secrets Manager/SSM for injection as environment variables at task startup. TaskRole is the IAM role your application container assumes at runtime — used for calls to DynamoDB, S3, SQS, etc. Principle of least privilege: TaskExecutionRole has ECR + CloudWatch + Secrets access; TaskRole has only your app's specific permissions. The container uses TaskRole's credentials via the container metadata endpoint (IMDSv1-equivalent for containers).

**Q: What does DeploymentCircuitBreaker do in ECS?**
A: It monitors new task deployments and automatically rolls back if tasks fail to reach a RUNNING state (e.g., container crashes on startup, health check failures). Without it, a bad deployment would leave old tasks running but eventually drain them and leave the service with 0 healthy tasks. With `Rollback: true`, ECS detects the failure and re-deploys the previous task definition version. This prevents bad deployments from causing service outages. Combined with the `MinimumHealthyPercent: 100` deployment configuration, it ensures zero-downtime rollbacks.

**Q: What is ECS Service Connect and how does it differ from Service Discovery?**
A: Service Discovery (Cloud Map) creates DNS records for services — other services resolve them via DNS. Latency: DNS TTL causes stale IPs, no load balancing at DNS level. Service Connect is a newer feature that injects an Envoy proxy sidecar into each task, providing service-to-service load balancing, retries, circuit breaking, and metrics without code changes. Service Connect proxies route traffic and report CloudWatch metrics per service. Use Service Connect for new deployments; it provides better observability and resilience than DNS-based discovery.
