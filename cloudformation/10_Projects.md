# Chapter 10: Projects
## Three Complete CloudFormation Projects

---

## Project 1: Serverless REST API
### Lambda + API Gateway + DynamoDB + Cognito

```
Architecture:
Client → Cognito (auth) → API Gateway → Lambda → DynamoDB
                 ↓
         JWT token validated
         by Lambda Authorizer
```

```yaml
# project1-serverless-api.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: |
  Project 1 — Serverless REST API
  Cognito User Pool + HTTP API + Lambda + DynamoDB

Parameters:
  AppName:
    Type: String
    Default: taskmanager
  Environment:
    Type: String
    Default: prod
    AllowedValues: [dev, staging, prod]

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:

  # ── COGNITO ──────────────────────────────────────────────────
  UserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: !Sub "${AppName}-${Environment}-users"
      UsernameAttributes: [email]
      AutoVerifiedAttributes: [email]
      PasswordPolicy:
        MinimumLength: 8
        RequireUppercase: true
        RequireLowercase: true
        RequireNumbers: true
        RequireSymbols: false
      Schema:
        - Name: email
          Required: true
          Mutable: false
        - Name: name
          Required: true
          Mutable: true
      MfaConfiguration: !If [IsProd, OPTIONAL, "OFF"]
      AccountRecoverySetting:
        RecoveryMechanisms:
          - Name: verified_email
            Priority: 1

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties:
      ClientName: !Sub "${AppName}-api-client"
      UserPoolId: !Ref UserPool
      GenerateSecret: false    # Public client (SPA/mobile)
      ExplicitAuthFlows:
        - ALLOW_USER_SRP_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH
      AccessTokenValidity: 1    # hours
      IdTokenValidity: 1
      RefreshTokenValidity: 30  # days
      TokenValidityUnits:
        AccessToken: hours
        IdToken: hours
        RefreshToken: days
      PreventUserExistenceErrors: ENABLED

  # ── DYNAMODB ─────────────────────────────────────────────────
  TasksTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: !If [IsProd, Retain, Delete]
    Properties:
      TableName: !Sub "${AppName}-${Environment}-tasks"
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK        # USER#<userId>
          AttributeType: S
        - AttributeName: SK        # TASK#<taskId>
          AttributeType: S
        - AttributeName: status
          AttributeType: S
        - AttributeName: dueDate
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: status-dueDate-index
          KeySchema:
            - AttributeName: status
              KeyType: HASH
            - AttributeName: dueDate
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: !If [IsProd, true, false]
      SSESpecification:
        SSEEnabled: true

  # ── IAM ROLE ─────────────────────────────────────────────────
  LambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: DynamoDBAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:DeleteItem
                  - dynamodb:Query
                Resource:
                  - !GetAtt TasksTable.Arn
                  - !Sub "${TasksTable.Arn}/index/*"

  # ── LAMBDA FUNCTIONS ─────────────────────────────────────────
  TasksFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "${AppName}-${Environment}-tasks"
      Runtime: python3.12
      Handler: index.handler
      Role: !GetAtt LambdaRole.Arn
      Timeout: 30
      MemorySize: 256
      Environment:
        Variables:
          TABLE_NAME: !Ref TasksTable
      Code:
        ZipFile: |
          import boto3, json, os, uuid
          from datetime import datetime
          
          table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
          
          def handler(event, context):
              method = event["requestContext"]["http"]["method"]
              path = event["requestContext"]["http"]["path"]
              user_id = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
              
              if method == "GET" and path == "/tasks":
                  return list_tasks(user_id)
              elif method == "POST" and path == "/tasks":
                  return create_task(user_id, json.loads(event["body"]))
              elif method == "GET" and "/tasks/" in path:
                  task_id = event["pathParameters"]["taskId"]
                  return get_task(user_id, task_id)
              elif method == "PUT" and "/tasks/" in path:
                  task_id = event["pathParameters"]["taskId"]
                  return update_task(user_id, task_id, json.loads(event["body"]))
              elif method == "DELETE" and "/tasks/" in path:
                  task_id = event["pathParameters"]["taskId"]
                  return delete_task(user_id, task_id)
              return {"statusCode": 404, "body": "Not found"}
          
          def list_tasks(user_id):
              resp = table.query(
                  KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
                  ExpressionAttributeValues={":pk": f"USER#{user_id}", ":sk": "TASK#"}
              )
              return ok(resp["Items"])
          
          def create_task(user_id, body):
              task_id = str(uuid.uuid4())
              item = {
                  "PK": f"USER#{user_id}", "SK": f"TASK#{task_id}",
                  "taskId": task_id, "userId": user_id,
                  "title": body["title"], "status": "todo",
                  "dueDate": body.get("dueDate", ""),
                  "createdAt": datetime.utcnow().isoformat() + "Z"
              }
              table.put_item(Item=item)
              return {"statusCode": 201, "body": json.dumps(item)}
          
          def get_task(user_id, task_id):
              resp = table.get_item(Key={"PK": f"USER#{user_id}", "SK": f"TASK#{task_id}"})
              if "Item" not in resp:
                  return {"statusCode": 404, "body": "Not found"}
              return ok(resp["Item"])
          
          def update_task(user_id, task_id, body):
              table.update_item(
                  Key={"PK": f"USER#{user_id}", "SK": f"TASK#{task_id}"},
                  UpdateExpression="SET #s = :s, updatedAt = :ua",
                  ExpressionAttributeNames={"#s": "status"},
                  ExpressionAttributeValues={":s": body["status"], ":ua": datetime.utcnow().isoformat() + "Z"}
              )
              return {"statusCode": 200, "body": json.dumps({"taskId": task_id, "updated": True})}
          
          def delete_task(user_id, task_id):
              table.delete_item(Key={"PK": f"USER#{user_id}", "SK": f"TASK#{task_id}"})
              return {"statusCode": 204, "body": ""}
          
          def ok(data):
              return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(data)}

  TasksLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${TasksFunction}"
      RetentionInDays: 14

  # ── API GATEWAY ───────────────────────────────────────────────
  HttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: !Sub "${AppName}-${Environment}-api"
      ProtocolType: HTTP
      CorsConfiguration:
        AllowOrigins: ["*"]
        AllowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        AllowHeaders: ["Authorization", "Content-Type"]

  # JWT Authorizer — validates Cognito tokens
  CognitoAuthorizer:
    Type: AWS::ApiGatewayV2::Authorizer
    Properties:
      ApiId: !Ref HttpApi
      AuthorizerType: JWT
      Name: cognito-authorizer
      IdentitySource: ["$request.header.Authorization"]
      JwtConfiguration:
        Audience:
          - !Ref UserPoolClient
        Issuer: !Sub "https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}"

  ApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref HttpApi
      StageName: !Ref Environment
      AutoDeploy: true

  TasksIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !GetAtt TasksFunction.Arn
      PayloadFormatVersion: "2.0"

  # Routes — all require Cognito JWT authorizer
  ListTasksRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: GET /tasks
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub "integrations/${TasksIntegration}"

  CreateTaskRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: POST /tasks
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub "integrations/${TasksIntegration}"

  GetTaskRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: GET /tasks/{taskId}
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub "integrations/${TasksIntegration}"

  UpdateTaskRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: PUT /tasks/{taskId}
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub "integrations/${TasksIntegration}"

  DeleteTaskRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: DELETE /tasks/{taskId}
      AuthorizationType: JWT
      AuthorizerId: !Ref CognitoAuthorizer
      Target: !Sub "integrations/${TasksIntegration}"

  TasksFunctionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref TasksFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*"

Outputs:
  ApiUrl:
    Value: !Sub "https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
  UserPoolId:
    Value: !Ref UserPool
  UserPoolClientId:
    Value: !Ref UserPoolClient
```

```bash
# Deploy Project 1
aws cloudformation deploy \
  --template-file project1-serverless-api.yaml \
  --stack-name taskmanager-prod \
  --parameter-overrides AppName=taskmanager Environment=prod \
  --capabilities CAPABILITY_NAMED_IAM

# Test: register a user, get token, call API
API_URL=$(aws cloudformation describe-stacks --stack-name taskmanager-prod \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)

# Create user (via SDK or Cognito Hosted UI)
# Then call:
curl -H "Authorization: Bearer $JWT_TOKEN" $API_URL/tasks
```

---

## Project 2: Multi-Environment Platform
### Dev / Staging / Prod with Nested Stacks + StackSets

```
parent-stack.yaml
├── networking.yaml    (VPC, subnets, NAT)
├── databases.yaml     (RDS + ElastiCache)
└── app.yaml           (ECS + ALB)

One template, three environments:
  myapp-networking-dev     myapp-networking-prod
  myapp-databases-dev      myapp-databases-prod
  myapp-app-dev            myapp-app-prod
```

```yaml
# environment-parent.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Multi-environment parent stack

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  
  TemplatesBucket:
    Type: String
    Description: S3 bucket containing child templates

Mappings:
  EnvironmentConfig:
    dev:
      EnableNatGateway: "false"
      DBInstanceClass: db.t3.micro
      DesiredCount: 1
    staging:
      EnableNatGateway: "true"
      DBInstanceClass: db.t3.medium
      DesiredCount: 1
    prod:
      EnableNatGateway: "true"
      DBInstanceClass: db.r6g.large
      DesiredCount: 3

Resources:
  NetworkingStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub "https://s3.amazonaws.com/${TemplatesBucket}/networking.yaml"
      Parameters:
        Environment: !Ref Environment
        EnableNatGateway: !FindInMap [EnvironmentConfig, !Ref Environment, EnableNatGateway]
      TimeoutInMinutes: 30

  DatabaseStack:
    Type: AWS::CloudFormation::Stack
    DependsOn: NetworkingStack
    Properties:
      TemplateURL: !Sub "https://s3.amazonaws.com/${TemplatesBucket}/databases.yaml"
      Parameters:
        Environment: !Ref Environment
        NetworkingStack: !GetAtt NetworkingStack.Outputs.StackName
        DBInstanceClass: !FindInMap [EnvironmentConfig, !Ref Environment, DBInstanceClass]
        DBPassword: !Sub "{{resolve:secretsmanager:${Environment}/db-password}}"
      TimeoutInMinutes: 60

  AppStack:
    Type: AWS::CloudFormation::Stack
    DependsOn: [NetworkingStack, DatabaseStack]
    Properties:
      TemplateURL: !Sub "https://s3.amazonaws.com/${TemplatesBucket}/app.yaml"
      Parameters:
        Environment: !Ref Environment
        NetworkingStack: !GetAtt NetworkingStack.Outputs.StackName
        DesiredCount: !FindInMap [EnvironmentConfig, !Ref Environment, DesiredCount]
      TimeoutInMinutes: 20

Outputs:
  AppUrl:
    Value: !GetAtt AppStack.Outputs.ServiceUrl
  
  EnvironmentSummary:
    Value: !Sub |
      Environment: ${Environment}
      App URL: ${AppStack.Outputs.ServiceUrl}
      DB Endpoint: ${DatabaseStack.Outputs.DBEndpoint}
```

```bash
# Upload templates
aws s3 sync cloudformation/ s3://my-cf-templates/

# Deploy dev
aws cloudformation deploy \
  --template-file environment-parent.yaml \
  --stack-name myapp-dev \
  --parameter-overrides Environment=dev TemplatesBucket=my-cf-templates \
  --capabilities CAPABILITY_NAMED_IAM

# Deploy prod
aws cloudformation deploy \
  --template-file environment-parent.yaml \
  --stack-name myapp-prod \
  --parameter-overrides Environment=prod TemplatesBucket=my-cf-templates \
  --capabilities CAPABILITY_NAMED_IAM
```

---

## Project 3: Organisation-Wide Security Baseline
### StackSets to All Accounts

```yaml
# security-baseline.yaml — deployed to all accounts via StackSet
AWSTemplateFormatVersion: "2010-09-09"
Description: Organisation security baseline — deployed via StackSets

Resources:

  # Enable GuardDuty in every account/region
  GuardDutyDetector:
    Type: AWS::GuardDuty::Detector
    Properties:
      Enable: true
      FindingPublishingFrequency: FIFTEEN_MINUTES

  # Enable CloudTrail in every account/region
  AuditTrail:
    Type: AWS::CloudTrail::Trail
    Properties:
      TrailName: org-audit-trail
      S3BucketName: !Sub "org-cloudtrail-logs-${AWS::AccountId}"
      IsLogging: true
      IsMultiRegionTrail: true
      EnableLogFileValidation: true
      IncludeGlobalServiceEvents: true

  # Mandatory CloudWatch alarm — root account usage
  RootAccountAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: root-account-usage
      AlarmDescription: Alert when root account is used
      Namespace: CloudTrailMetrics
      MetricName: RootAccountUsageCount
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanOrEqualToThreshold
      AlarmActions:
        - !Sub "arn:aws:sns:${AWS::Region}:${AWS::AccountId}:security-alerts"
      TreatMissingData: notBreaching

  # Password policy for all IAM users
  PasswordPolicy:
    Type: AWS::IAM::AccountPasswordPolicy
    Properties:
      MinimumPasswordLength: 14
      RequireUppercaseCharacters: true
      RequireLowercase: true
      RequireNumbers: true
      RequireSymbols: true
      MaxPasswordAge: 90
      PasswordReusePrevention: 12
      AllowUsersToChangePassword: true
```

```bash
# Create StackSet
aws cloudformation create-stack-set \
  --stack-set-name org-security-baseline \
  --template-body file://security-baseline.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --capabilities CAPABILITY_NAMED_IAM

# Deploy to all accounts in Production OU
aws cloudformation create-stack-instances \
  --stack-set-name org-security-baseline \
  --deployment-targets '{"OrganizationalUnitIds": ["ou-xxxx-prod"]}' \
  --regions us-east-1 us-west-2 eu-west-1 \
  --operation-preferences '{
    "RegionConcurrencyType": "PARALLEL",
    "MaxConcurrentPercentage": 50,
    "FailureTolerancePercentage": 10
  }'
```

---

## Final Checklist: CloudFormation Best Practices

```
┌──────────────────────────────────────────────────────────────┐
│           CLOUDFORMATION BEST PRACTICES CHECKLIST           │
├──────────────────────────────────────────────────────────────┤
│ Templates                                                    │
│ ✅ Always lint with cfn-lint before deploying               │
│ ✅ Validate with aws cloudformation validate-template        │
│ ✅ Use parameters for environment-specific values           │
│ ✅ Use conditions for optional resources                    │
│ ✅ Use Mappings for environment config lookup               │
├──────────────────────────────────────────────────────────────┤
│ Resources                                                    │
│ ✅ DeletionPolicy: Retain or Snapshot on stateful resources  │
│ ✅ DeletionProtection on Aurora and critical DBs            │
│ ✅ Explicit CloudWatch Log Groups with retention period     │
│ ✅ IAM roles with least-privilege policies                  │
│ ✅ NoEcho: true on all password parameters                  │
├──────────────────────────────────────────────────────────────┤
│ Deployment                                                   │
│ ✅ Use change sets in production (review before execute)    │
│ ✅ Set rollback triggers on CloudWatch alarms               │
│ ✅ Stack policies to protect critical resources             │
│ ✅ Store templates in S3, not inline                        │
│ ✅ Tag all resources with Environment, Team, Project        │
├──────────────────────────────────────────────────────────────┤
│ Secrets                                                      │
│ ✅ Use Secrets Manager, not parameters, for passwords       │
│ ✅ Use dynamic references {{resolve:secretsmanager:...}}    │
│ ✅ Never commit secrets to Git                              │
└──────────────────────────────────────────────────────────────┘
```
