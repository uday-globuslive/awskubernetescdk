# Chapter 6: Container Stack
## ECR + ECS Fargate + ALB Full Template

---

## 6.1 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              ECS FARGATE ARCHITECTURE                        │
│                                                              │
│  Internet                                                    │
│      │                                                       │
│      ▼                                                       │
│  ALB (public subnets)                                        │
│  ├── HTTPS Listener (port 443)                               │
│  │   └── Target Group (port 8000)                            │
│  └── HTTP Listener (port 80 → redirect 443)                  │
│             │                                                │
│    ┌────────┼────────────────┐                               │
│    ▼        ▼                ▼                               │
│  ECS Fargate Tasks (private subnets, 3 AZs)                  │
│  ┌──────────────────────────────┐                            │
│  │ FastAPI container            │                            │
│  │ CPU: 512, Mem: 1024          │                            │
│  └──────────────────────────────┘                            │
│             │                                                │
│    ┌────────┼─────────────────────┐                          │
│    ▼        ▼                     ▼                          │
│  RDS     ElastiCache         Secrets Manager                 │
│  Aurora   Redis               (credentials)                  │
│                                                              │
│  ECS Service Auto Scaling:                                   │
│  min=2, max=10, scale on CPU > 70%                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 6.2 Container Stack Template

```yaml
# container-stack.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: ECS Fargate service with ALB, auto scaling, and ECR

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

  NetworkingStack:
    Type: String
    Description: Name of the networking stack (for cross-stack imports)

  ImageUri:
    Type: String
    Description: ECR image URI (e.g., 123456.dkr.ecr.us-east-1.amazonaws.com/myapp:latest)
    Default: "public.ecr.aws/amazonlinux/amazonlinux:latest"

  ContainerPort:
    Type: Number
    Default: 8000

  CertificateArn:
    Type: String
    Default: ""
    Description: ACM certificate ARN for HTTPS (leave empty for HTTP only)

  DesiredCount:
    Type: Number
    Default: 2

  TaskCpu:
    Type: String
    Default: "512"
    AllowedValues: ["256", "512", "1024", "2048", "4096"]

  TaskMemory:
    Type: String
    Default: "1024"
    AllowedValues: ["512", "1024", "2048", "4096", "8192"]

Conditions:
  IsProd: !Equals [!Ref Environment, prod]
  HasCertificate: !Not [!Equals [!Ref CertificateArn, ""]]

Resources:

  # ============================================================
  # ECR REPOSITORY
  # ============================================================
  ECRRepository:
    Type: AWS::ECR::Repository
    DeletionPolicy: Retain
    Properties:
      RepositoryName: !Sub "${AWS::StackName}/app"
      ImageTagMutability: MUTABLE
      ImageScanningConfiguration:
        ScanOnPush: true
      EncryptionConfiguration:
        EncryptionType: AES256
      LifecyclePolicy:
        LifecyclePolicyText: |
          {
            "rules": [
              {
                "rulePriority": 1,
                "description": "Keep last 10 production images",
                "selection": {
                  "tagStatus": "tagged",
                  "tagPrefixList": ["prod"],
                  "countType": "imageCountMoreThan",
                  "countNumber": 10
                },
                "action": {"type": "expire"}
              },
              {
                "rulePriority": 2,
                "description": "Delete untagged images older than 7 days",
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

  # ============================================================
  # SECURITY GROUPS
  # ============================================================
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ALB security group
      VpcId: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcId"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-alb-sg"

  TaskSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ECS task security group
      VpcId: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcId"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: !Ref ContainerPort
          ToPort: !Ref ContainerPort
          SourceSecurityGroupId: !Ref ALBSecurityGroup
          Description: Traffic from ALB only
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-task-sg"

  # ============================================================
  # APPLICATION LOAD BALANCER
  # ============================================================
  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub "${AWS::StackName}-alb"
      Type: application
      Scheme: internet-facing
      Subnets:
        - !ImportValue
          Fn::Sub: "${NetworkingStack}-PublicSubnet1"
        - !ImportValue
          Fn::Sub: "${NetworkingStack}-PublicSubnet2"
      SecurityGroups:
        - !Ref ALBSecurityGroup
      LoadBalancerAttributes:
        - Key: access_logs.s3.enabled
          Value: !If [IsProd, "true", "false"]
        - Key: idle_timeout.timeout_seconds
          Value: "60"
      Tags:
        - Key: Environment
          Value: !Ref Environment

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub "${AWS::StackName}-tg"
      Port: !Ref ContainerPort
      Protocol: HTTP
      TargetType: ip    # Required for Fargate
      VpcId: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcId"
      HealthCheckPath: /health
      HealthCheckProtocol: HTTP
      HealthCheckIntervalSeconds: 30
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      HealthCheckTimeoutSeconds: 10
      DeregistrationDelay: 30    # Seconds to wait before deregistering
      TargetGroupAttributes:
        - Key: stickiness.enabled
          Value: "false"

  HTTPSListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Condition: HasCertificate
    Properties:
      LoadBalancerArn: !Ref ALB
      Port: 443
      Protocol: HTTPS
      Certificates:
        - CertificateArn: !Ref CertificateArn
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup

  HTTPListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Port: 80
      Protocol: HTTP
      DefaultActions:
        - !If
          - HasCertificate
          - Type: redirect
            RedirectConfig:
              Protocol: HTTPS
              Port: "443"
              StatusCode: HTTP_301
          - Type: forward
            TargetGroupArn: !Ref TargetGroup

  # ============================================================
  # ECS CLUSTER
  # ============================================================
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub "${AWS::StackName}-cluster"
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE
          Weight: 1
      ClusterSettings:
        - Name: containerInsights
          Value: enabled

  # ============================================================
  # IAM ROLES FOR ECS
  # ============================================================
  TaskExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${AWS::StackName}-task-execution-role"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
      Policies:
        - PolicyName: SecretsAndLogs
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource:
                  - !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/*"

  TaskRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${AWS::StackName}-task-role"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: AppPermissions
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub "arn:aws:s3:::${AWS::StackName}-*/*"
              - Effect: Allow
                Action:
                  - sqs:SendMessage
                  - sqs:ReceiveMessage
                  - sqs:DeleteMessage
                Resource: !Sub "arn:aws:sqs:${AWS::Region}:${AWS::AccountId}:${AWS::StackName}-*"

  # ============================================================
  # CLOUDWATCH LOG GROUP
  # ============================================================
  AppLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/ecs/${AWS::StackName}"
      RetentionInDays: !If [IsProd, 30, 7]

  # ============================================================
  # ECS TASK DEFINITION
  # ============================================================
  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: !Sub "${AWS::StackName}-app"
      RequiresCompatibilities:
        - FARGATE
      NetworkMode: awsvpc    # Required for Fargate
      Cpu: !Ref TaskCpu
      Memory: !Ref TaskMemory
      ExecutionRoleArn: !GetAtt TaskExecutionRole.Arn
      TaskRoleArn: !GetAtt TaskRole.Arn
      ContainerDefinitions:
        - Name: app
          Image: !Ref ImageUri
          Essential: true
          PortMappings:
            - ContainerPort: !Ref ContainerPort
              Protocol: tcp
          Environment:
            - Name: ENVIRONMENT
              Value: !Ref Environment
            - Name: PORT
              Value: !Sub "${ContainerPort}"
          # Pull secrets from Secrets Manager at task start
          Secrets:
            - Name: DB_PASSWORD
              ValueFrom: !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/db:password::"
            - Name: JWT_SECRET
              ValueFrom: !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/jwt:secret::"
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref AppLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: app
          HealthCheck:
            Command:
              - CMD-SHELL
              - !Sub "curl -f http://localhost:${ContainerPort}/health || exit 1"
            Interval: 30
            Timeout: 5
            Retries: 3
            StartPeriod: 60
          ReadonlyRootFilesystem: false
          User: "1000"    # Non-root user

  # ============================================================
  # ECS SERVICE
  # ============================================================
  ECSService:
    Type: AWS::ECS::Service
    DependsOn:
      - HTTPListener
    Properties:
      ServiceName: !Sub "${AWS::StackName}-service"
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref TaskDefinition
      LaunchType: FARGATE
      DesiredCount: !Ref DesiredCount
      DeploymentConfiguration:
        MinimumHealthyPercent: 100
        MaximumPercent: 200
        DeploymentCircuitBreaker:
          Enable: true
          Rollback: true
      NetworkConfiguration:
        AwsvpcConfiguration:
          AssignPublicIp: DISABLED
          SecurityGroups:
            - !Ref TaskSecurityGroup
          Subnets:
            - !ImportValue
              Fn::Sub: "${NetworkingStack}-PrivateSubnet1"
            - !ImportValue
              Fn::Sub: "${NetworkingStack}-PrivateSubnet2"
      LoadBalancers:
        - ContainerName: app
          ContainerPort: !Ref ContainerPort
          TargetGroupArn: !Ref TargetGroup
      EnableExecuteCommand: !If [IsProd, false, true]  # ECS Exec for dev
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # ============================================================
  # AUTO SCALING
  # ============================================================
  ScalableTarget:
    Type: AWS::ApplicationAutoScaling::ScalableTarget
    Properties:
      MaxCapacity: !If [IsProd, 10, 4]
      MinCapacity: !If [IsProd, 2, 1]
      ResourceId: !Sub "service/${ECSCluster}/${ECSService.Name}"
      RoleARN: !Sub "arn:aws:iam::${AWS::AccountId}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService"
      ScalableDimension: ecs:service:DesiredCount
      ServiceNamespace: ecs

  CPUScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: !Sub "${AWS::StackName}-cpu-scaling"
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref ScalableTarget
      TargetTrackingScalingPolicyConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ECSServiceAverageCPUUtilization
        TargetValue: 70.0
        ScaleInCooldown: 300
        ScaleOutCooldown: 60

# ============================================================
# OUTPUTS
# ============================================================
Outputs:
  ServiceUrl:
    Description: Application URL
    Value: !Sub
      - "http${Https}://${DNS}"
      - Https: !If [HasCertificate, "s", ""]
        DNS: !GetAtt ALB.DNSName

  ClusterName:
    Value: !Ref ECSCluster
    Export:
      Name: !Sub "${AWS::StackName}-ClusterName"

  ServiceName:
    Value: !GetAtt ECSService.Name
    Export:
      Name: !Sub "${AWS::StackName}-ServiceName"

  ECRRepositoryUri:
    Value: !GetAtt ECRRepository.RepositoryUri
    Export:
      Name: !Sub "${AWS::StackName}-ECRUri"
```

---

## 6.3 Deploying

```bash
# Lint
cfn-lint container-stack.yaml

# Deploy (requires networking stack deployed first)
aws cloudformation deploy \
  --template-file container-stack.yaml \
  --stack-name myapp-containers-dev \
  --parameter-overrides \
    Environment=dev \
    NetworkingStack=myapp-networking \
    ImageUri=nginx:latest \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Get the service URL
aws cloudformation describe-stacks \
  --stack-name myapp-containers-dev \
  --query "Stacks[0].Outputs[?OutputKey=='ServiceUrl'].OutputValue" \
  --output text

# Push a new image (GitHub Actions or manually)
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name myapp-containers-dev \
  --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" \
  --output text)

aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker build -t $ECR_URI:latest .
docker push $ECR_URI:latest

# Force new deployment (pull latest image)
aws ecs update-service \
  --cluster myapp-containers-dev-cluster \
  --service myapp-containers-dev-service \
  --force-new-deployment
```

---

## 6.4 Interview Questions

**Q: What is the difference between TaskExecutionRole and TaskRole in ECS?**
> The `TaskExecutionRole` is used by the ECS agent to set up the task — pulling the Docker image from ECR, retrieving secrets from Secrets Manager to inject as environment variables, and writing logs to CloudWatch. The `TaskRole` is used by your application code running inside the container — it defines what AWS APIs your app can call (S3, SQS, DynamoDB, etc.). Both are required, both are IAM roles, but they're assumed by different actors: ECS infrastructure vs your application.

**Q: What does `DeploymentCircuitBreaker` do?**
> The circuit breaker monitors ECS service deployments. If new tasks keep failing to start (failing health checks, crashing), it stops the deployment and automatically rolls back to the previous working task definition — rather than letting a bad deploy drain all healthy tasks. Without it, a bad deployment could bring down the entire service before anyone notices. It's enabled with `Enable: true, Rollback: true` and is a simple best practice for every ECS service.

**Q: Why set `AssignPublicIp: DISABLED` for Fargate tasks?**
> Fargate tasks in private subnets should never have public IPs. They access the internet through NAT Gateways (for outbound), and incoming traffic only arrives from the ALB (which is in the public subnet and routes to tasks via private IPs). Assigning public IPs to tasks would expose them directly to the internet, bypassing the ALB, WAF, and security group protection. Private subnets + no public IP + ALB in front is the correct architecture.
