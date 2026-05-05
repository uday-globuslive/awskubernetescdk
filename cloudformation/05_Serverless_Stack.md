# CloudFormation Chapter 5: Serverless Stack — Lambda, API Gateway & EventBridge
## Complete Serverless Application Templates with SAM

---

## 5.1 Lambda Function — Complete CloudFormation Resource

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Serverless application with Lambda, API Gateway, and DynamoDB

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Default: dev

  DeploymentPackage:
    Type: String
    Description: S3 key for Lambda deployment package

  ArtifactBucket:
    Type: String
    Description: S3 bucket containing Lambda artifacts

Resources:
  # ── Lambda Execution Role ─────────────────────────────
  LambdaRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${AWS::StackName}-lambda-role'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
        - arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess
      Policies:
        - PolicyName: LambdaAppPermissions
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:DeleteItem
                  - dynamodb:Query
                  - dynamodb:Scan
                  - dynamodb:BatchGetItem
                  - dynamodb:BatchWriteItem
                Resource:
                  - !GetAtt OrdersTable.Arn
                  - !Sub '${OrdersTable.Arn}/index/*'
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource:
                  - !Sub 'arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/*'
              - Effect: Allow
                Action:
                  - sqs:SendMessage
                  - sqs:ReceiveMessage
                  - sqs:DeleteMessage
                  - sqs:GetQueueAttributes
                Resource: !GetAtt ProcessingQueue.Arn
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: !Sub 'arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}*:*'

  # ── Lambda Function ───────────────────────────────────
  OrdersFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub '${AWS::StackName}-orders'
      Runtime: python3.11
      Handler: handlers.orders.handler
      Role: !GetAtt LambdaRole.Arn
      Code:
        S3Bucket: !Ref ArtifactBucket
        S3Key: !Ref DeploymentPackage
      MemorySize: 512
      Timeout: 29          # API GW max is 29s
      ReservedConcurrentExecutions: 100   # Hard limit, protect DB
      Environment:
        Variables:
          ORDERS_TABLE: !Ref OrdersTable
          PROCESSING_QUEUE_URL: !Ref ProcessingQueue
          ENVIRONMENT: !Ref Environment
          POWERTOOLS_SERVICE_NAME: !Sub '${AWS::StackName}-orders'
          LOG_LEVEL: !If [IsProd, INFO, DEBUG]
      VpcConfig:
        SubnetIds: !Split [',', !ImportValue 'network-stack-PrivateSubnets']
        SecurityGroupIds:
          - !Ref LambdaSecurityGroup
      Layers:
        - !Ref CommonLayer
        - !Sub 'arn:aws:lambda:${AWS::Region}:017000801446:layer:AWSLambdaPowertoolsPythonV2-Arm64:x'
      Architectures:
        - arm64      # Graviton2 — 20% faster, 20% cheaper than x86
      EphemeralStorage:
        Size: 1024   # /tmp size in MB
      TracingConfig:
        Mode: Active    # X-Ray tracing
      SnapStart:        # Only for Java, preview for others
        ApplyOn: None
      Tags:
        Environment: !Ref Environment
        Service: orders

  # ── Lambda Version and Alias ──────────────────────────
  OrdersFunctionVersion:
    Type: AWS::Lambda::Version
    Properties:
      FunctionName: !GetAtt OrdersFunction.Arn
      Description: !Sub 'Version for ${Environment}'

  OrdersFunctionAlias:
    Type: AWS::Lambda::Alias
    Properties:
      FunctionName: !Ref OrdersFunction
      FunctionVersion: !GetAtt OrdersFunctionVersion.Version
      Name: !Ref Environment    # live / prod / dev alias
      # Canary routing (10% to new, 90% to old)
      # RoutingConfig:
      #   AdditionalVersionWeights:
      #     - FunctionVersion: !GetAtt OrdersFunctionVersionV2.Version
      #       FunctionWeight: 0.1

  # ── Provisioned Concurrency ───────────────────────────
  OrdersFunctionPC:
    Type: AWS::Lambda::ProvisionedConcurrencyConfig
    Condition: IsProd
    Properties:
      FunctionName: !Ref OrdersFunction
      Qualifier: !GetAtt OrdersFunctionAlias.AliasArn
      ProvisionedConcurrentExecutions: 5

  # ── Log Group ─────────────────────────────────────────
  OrdersFunctionLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/lambda/${OrdersFunction}'
      RetentionInDays: !If [IsProd, 90, 14]

  # ── Lambda Layer ──────────────────────────────────────
  CommonLayer:
    Type: AWS::Lambda::LayerVersion
    Properties:
      LayerName: !Sub '${AWS::StackName}-common'
      Description: Common dependencies (boto3, pydantic, etc.)
      Content:
        S3Bucket: !Ref ArtifactBucket
        S3Key: layers/common-layer.zip
      CompatibleRuntimes:
        - python3.11
      CompatibleArchitectures:
        - arm64

  LayerPermission:
    Type: AWS::Lambda::LayerVersionPermission
    Properties:
      Action: lambda:GetLayerVersion
      LayerVersionArn: !Ref CommonLayer
      Principal: !Ref AWS::AccountId

  # ── Event Source Mapping (SQS → Lambda) ──────────────
  SQSTrigger:
    Type: AWS::Lambda::EventSourceMapping
    Properties:
      EventSourceArn: !GetAtt ProcessingQueue.Arn
      FunctionName: !GetAtt ProcessorFunction.Arn
      BatchSize: 10
      MaximumBatchingWindowInSeconds: 30    # Wait up to 30s to fill batch
      FunctionResponseTypes:
        - ReportBatchItemFailures     # Partial batch failure
      ScalingConfig:
        MaximumConcurrency: 50       # Max concurrent Lambda for this trigger
```

---

## 5.2 API Gateway — HTTP API

```yaml
  # ── HTTP API (low cost, high performance) ─────────────
  HttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: !Sub '${AWS::StackName}-api'
      ProtocolType: HTTP
      Description: Orders service REST API
      CorsConfiguration:
        AllowOrigins:
          - 'https://app.example.com'
          - !If [IsNotProd, 'http://localhost:3000', !Ref AWS::NoValue]
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
          - OPTIONS
        AllowHeaders:
          - Content-Type
          - Authorization
          - X-Request-ID
        MaxAge: 3600
        AllowCredentials: true

  # ── JWT Authorizer ────────────────────────────────────
  CognitoAuthorizer:
    Type: AWS::ApiGatewayV2::Authorizer
    Properties:
      ApiId: !Ref HttpApi
      AuthorizerType: JWT
      Name: cognito-authorizer
      IdentitySource:
        - $request.header.Authorization
      JwtConfiguration:
        Audience:
          - !Ref UserPoolClient
        Issuer: !Sub 'https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}'

  # ── Lambda Integration ────────────────────────────────
  OrdersIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${OrdersFunction.Arn}/invocations'
      PayloadFormatVersion: "2.0"    # Newer, smaller payload format
      TimeoutInMillis: 29000

  # ── Routes ────────────────────────────────────────────
  ListOrdersRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: GET /orders
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub 'integrations/${OrdersIntegration}'
      AuthorizationScopes:
        - orders:read

  CreateOrderRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: POST /orders
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub 'integrations/${OrdersIntegration}'
      AuthorizationScopes:
        - orders:write

  HealthRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: GET /health
      AuthorizationType: NONE
      Target: !Sub 'integrations/${OrdersIntegration}'

  # ── Stage (auto-deploy) ───────────────────────────────
  DefaultStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref HttpApi
      StageName: $default
      AutoDeploy: true
      AccessLogSettings:
        DestinationArn: !GetAtt APIAccessLogGroup.Arn
        Format: '{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","integrationLatency":"$context.integrationLatency","responseLatency":"$context.responseLatency"}'
      DefaultRouteSettings:
        ThrottlingBurstLimit: 1000
        ThrottlingRateLimit: 500

  # ── Lambda Permission for API GW ──────────────────────
  ApiGatewayLambdaPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref OrdersFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*'

  APIAccessLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/apigateway/${AWS::StackName}'
      RetentionInDays: 30

  # ── Custom Domain ─────────────────────────────────────
  APICustomDomain:
    Type: AWS::ApiGatewayV2::DomainName
    Properties:
      DomainName: !Sub 'api.${DomainName}'
      DomainNameConfigurations:
        - CertificateArn: !Ref Certificate
          EndpointType: REGIONAL
          SecurityPolicy: TLS_1_2

  APIMapping:
    Type: AWS::ApiGatewayV2::ApiMapping
    DependsOn: DefaultStage
    Properties:
      DomainName: !Ref APICustomDomain
      ApiId: !Ref HttpApi
      Stage: $default
```

---

## 5.3 EventBridge Rule Template

```yaml
  # ── EventBridge — Scheduled Rule ─────────────────────
  DailyReportRule:
    Type: AWS::Events::Rule
    Properties:
      Name: !Sub '${AWS::StackName}-daily-report'
      Description: Trigger daily report generation at 8 AM UTC
      ScheduleExpression: cron(0 8 * * ? *)    # 8 AM UTC every day
      State: ENABLED
      Targets:
        - Arn: !GetAtt ReportFunction.Arn
          Id: ReportTarget
          Input: !Sub '{"environment": "${Environment}", "type": "daily"}'

  DailyReportPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref ReportFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt DailyReportRule.Arn

  # ── EventBridge — Custom Event Bus ───────────────────
  OrdersEventBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: !Sub '${AWS::StackName}-orders'

  # ── EventBridge — Content-Based Rule ─────────────────
  OrderCreatedRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !Ref OrdersEventBus
      EventPattern:
        source:
          - orders-service
        detail-type:
          - Order Created
        detail:
          status:
            - CONFIRMED
          amount:
            numeric:
              - '>'
              - 100
      Targets:
        - Arn: !GetAtt NotificationFunction.Arn
          Id: NotifyTarget
          InputTransformer:
            InputPathsMap:
              orderId: $.detail.orderId
              amount: $.detail.amount
              customer: $.detail.customerId
            InputTemplate: |
              {
                "message": "New order <orderId> for $<amount> from customer <customer>",
                "priority": "high"
              }
        - Arn: !GetAtt ProcessingQueue.Arn
          Id: QueueTarget
          SqsParameters:
            MessageGroupId: orders

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !GetAtt HttpApi.ApiEndpoint
    Export:
      Name: !Sub '${AWS::StackName}-ApiEndpoint'

  FunctionArn:
    Description: Orders Lambda function ARN
    Value: !GetAtt OrdersFunction.Arn
    Export:
      Name: !Sub '${AWS::StackName}-OrdersFunctionArn'
```

---

## 5.4 Interview Q&A

**Q: How do you handle Lambda function updates in CloudFormation without downtime?**
A: Use versions and aliases: (1) Lambda version is an immutable snapshot of function code + config; (2) Alias points to a version and is used by consumers (API GW, SQS); (3) On update, create a new version and update the alias to point to it. For canary deployments, use `RoutingConfig` on the alias to split traffic (e.g., 10% to new version, 90% to old). Combine with CodeDeploy Lambda deployment groups for automated traffic shifting with pre/post hooks for smoke tests.

**Q: What is the difference between API Gateway V1 (REST API) and V2 (HTTP API)?**
A: HTTP API (V2): cheaper (~70% less), lower latency, JWT/Lambda authorizers, auto-deploy, native CORS, OIDC support. Lacks: WAF integration, usage plans/API keys, custom authorizer caching, request/response transformation, body validation. REST API (V1): full-featured, WAF support, usage plans with API keys, throttling per stage/method, request/response mapping, model validation, VPC Link. Use HTTP API for simple Lambda-backed APIs with JWT auth. Use REST API when you need WAF, usage plans, or advanced request/response handling.

**Q: How do you configure Lambda to only allow invocation from your API Gateway?**
A: Use `AWS::Lambda::Permission` with `SourceArn` pointing to your specific API Gateway ARN pattern. For HTTP API: `arn:aws:execute-api:region:account:api-id/*/*`. For REST API: `arn:aws:execute-api:region:account:api-id/stage/method/resource`. This prevents other API Gateways or direct Lambda invocations without API GW. Additionally, if Lambda is in a VPC, its security group can restrict network-level access. For inter-service calls, use resource-based policies limiting Principal to specific IAM roles.
