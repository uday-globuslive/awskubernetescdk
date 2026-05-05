# Chapter 5: Serverless Stack
## Lambda + API Gateway + DynamoDB Full Template

---

## 5.1 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│             SERVERLESS API ARCHITECTURE                      │
│                                                              │
│  Client                                                      │
│    │                                                         │
│    ▼                                                         │
│  API Gateway (HTTP API)                                      │
│    │                                                         │
│    ├── GET  /items        → Lambda: listItems                │
│    ├── POST /items        → Lambda: createItem               │
│    ├── GET  /items/{id}   → Lambda: getItem                  │
│    ├── PUT  /items/{id}   → Lambda: updateItem               │
│    └── DELETE /items/{id} → Lambda: deleteItem               │
│                │                                             │
│                ▼                                             │
│           DynamoDB Table                                     │
│           (items table with GSI)                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 5.2 Serverless Stack Template

```yaml
# serverless-stack.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: Serverless REST API — Lambda + HTTP API Gateway + DynamoDB

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

  LogRetentionDays:
    Type: Number
    Default: 14
    AllowedValues: [7, 14, 30, 90]

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:

  # ============================================================
  # DYNAMODB TABLE
  # ============================================================
  ItemsTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: !If [IsProd, Retain, Delete]
    UpdateReplacePolicy: Retain
    Properties:
      TableName: !Sub "${AWS::StackName}-items"
      
      BillingMode: PAY_PER_REQUEST    # On-demand — scales automatically
      
      # Primary key
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: userId
          AttributeType: S
        - AttributeName: createdAt
          AttributeType: S
      
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      
      # Global Secondary Index — query by userId
      GlobalSecondaryIndexes:
        - IndexName: userId-createdAt-index
          KeySchema:
            - AttributeName: userId
              KeyType: HASH
            - AttributeName: createdAt
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      
      # Point-in-time recovery
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      
      # Encryption at rest (managed by AWS)
      SSESpecification:
        SSEEnabled: true
      
      # TTL attribute
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true
      
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # ============================================================
  # IAM ROLE FOR LAMBDA
  # ============================================================
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${AWS::StackName}-lambda-role"
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
                  - dynamodb:Scan
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:DeleteItem
                  - dynamodb:Query
                  - dynamodb:Scan
                Resource:
                  - !GetAtt ItemsTable.Arn
                  - !Sub "${ItemsTable.Arn}/index/*"
        - PolicyName: SecretsAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource:
                  - !Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${AWS::StackName}/*"

  # ============================================================
  # LAMBDA FUNCTIONS
  # ============================================================
  
  # Shared environment variables for all Lambda functions
  # (use a Lambda Layer or SSM instead for production)
  
  ListItemsFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "${AWS::StackName}-list-items"
      Runtime: python3.12
      Handler: list_items.handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Timeout: 30
      MemorySize: 256
      Environment:
        Variables:
          TABLE_NAME: !Ref ItemsTable
          ENVIRONMENT: !Ref Environment
      Code:
        ZipFile: |
          import boto3, json, os
          
          table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
          
          def handler(event, context):
              user_id = event["queryStringParameters"].get("userId") if event.get("queryStringParameters") else None
              
              if user_id:
                  response = table.query(
                      IndexName="userId-createdAt-index",
                      KeyConditionExpression="userId = :uid",
                      ExpressionAttributeValues={":uid": user_id}
                  )
              else:
                  response = table.scan()
              
              return {
                  "statusCode": 200,
                  "headers": {"Content-Type": "application/json"},
                  "body": json.dumps(response["Items"])
              }
      Tags:
        - Key: Environment
          Value: !Ref Environment

  CreateItemFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "${AWS::StackName}-create-item"
      Runtime: python3.12
      Handler: create_item.handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Timeout: 30
      MemorySize: 256
      Environment:
        Variables:
          TABLE_NAME: !Ref ItemsTable
          ENVIRONMENT: !Ref Environment
      Code:
        ZipFile: |
          import boto3, json, os, uuid
          from datetime import datetime
          
          table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
          
          def handler(event, context):
              body = json.loads(event.get("body", "{}"))
              item_id = str(uuid.uuid4())
              
              item = {
                  "PK": f"ITEM#{item_id}",
                  "SK": "METADATA",
                  "id": item_id,
                  "userId": body.get("userId", "anonymous"),
                  "name": body["name"],
                  "createdAt": datetime.utcnow().isoformat() + "Z",
              }
              
              table.put_item(Item=item)
              
              return {
                  "statusCode": 201,
                  "headers": {"Content-Type": "application/json"},
                  "body": json.dumps(item)
              }

  GetItemFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "${AWS::StackName}-get-item"
      Runtime: python3.12
      Handler: get_item.handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Timeout: 10
      MemorySize: 128
      Environment:
        Variables:
          TABLE_NAME: !Ref ItemsTable
      Code:
        ZipFile: |
          import boto3, json, os
          
          table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
          
          def handler(event, context):
              item_id = event["pathParameters"]["id"]
              response = table.get_item(Key={"PK": f"ITEM#{item_id}", "SK": "METADATA"})
              
              if "Item" not in response:
                  return {"statusCode": 404, "body": json.dumps({"error": "Not found"})}
              
              return {
                  "statusCode": 200,
                  "headers": {"Content-Type": "application/json"},
                  "body": json.dumps(response["Item"])
              }

  # ============================================================
  # CLOUDWATCH LOG GROUPS (explicit — controls retention)
  # ============================================================
  ListItemsLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${ListItemsFunction}"
      RetentionInDays: !Ref LogRetentionDays

  CreateItemLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${CreateItemFunction}"
      RetentionInDays: !Ref LogRetentionDays

  # ============================================================
  # API GATEWAY — HTTP API
  # ============================================================
  HttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: !Sub "${AWS::StackName}-api"
      ProtocolType: HTTP
      Description: Items REST API
      CorsConfiguration:
        AllowOrigins:
          - "*"
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
          - OPTIONS
        AllowHeaders:
          - Content-Type
          - Authorization

  HttpApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref HttpApi
      StageName: !Ref Environment
      AutoDeploy: true
      DefaultRouteSettings:
        ThrottlingBurstLimit: 100
        ThrottlingRateLimit: 50

  # ============================================================
  # API GATEWAY INTEGRATIONS
  # ============================================================
  ListItemsIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !GetAtt ListItemsFunction.Arn
      PayloadFormatVersion: "2.0"

  CreateItemIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !GetAtt CreateItemFunction.Arn
      PayloadFormatVersion: "2.0"

  GetItemIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !GetAtt GetItemFunction.Arn
      PayloadFormatVersion: "2.0"

  # ============================================================
  # API GATEWAY ROUTES
  # ============================================================
  ListItemsRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: GET /items
      Target: !Sub "integrations/${ListItemsIntegration}"

  CreateItemRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: POST /items
      Target: !Sub "integrations/${CreateItemIntegration}"

  GetItemRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: GET /items/{id}
      Target: !Sub "integrations/${GetItemIntegration}"

  # ============================================================
  # LAMBDA PERMISSIONS (allow API GW to invoke each function)
  # ============================================================
  ListItemsPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref ListItemsFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*"

  CreateItemPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref CreateItemFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*"

  GetItemPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref GetItemFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*"

# ============================================================
# OUTPUTS
# ============================================================
Outputs:
  ApiUrl:
    Description: HTTP API endpoint URL
    Value: !Sub "https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
    Export:
      Name: !Sub "${AWS::StackName}-ApiUrl"

  TableName:
    Description: DynamoDB table name
    Value: !Ref ItemsTable
    Export:
      Name: !Sub "${AWS::StackName}-TableName"

  TableArn:
    Description: DynamoDB table ARN
    Value: !GetAtt ItemsTable.Arn
```

---

## 5.3 Deploying the Stack

```bash
# Lint first
cfn-lint serverless-stack.yaml

# Deploy (dev)
aws cloudformation deploy \
  --template-file serverless-stack.yaml \
  --stack-name items-api-dev \
  --parameter-overrides Environment=dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Get the API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name items-api-dev \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

# Test endpoints
curl $API_URL/items
curl -X POST $API_URL/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Test item", "userId": "user-123"}'
```

---

## 5.4 Interview Questions

**Q: Why do you need `AWS::Lambda::Permission` when using API Gateway?**
> API Gateway needs explicit permission to invoke Lambda functions. Without a `Lambda::Permission` resource, the invocation will fail with a 403 AccessDeniedException even though the Lambda execution role doesn't grant this permission to itself — it's a resource-based policy on the Lambda function. The `SourceArn` condition is important for security: it restricts the permission to only the specific API Gateway, not any API Gateway in the account. This prevents confused deputy attacks.

**Q: What is the difference between HTTP API and REST API in API Gateway?**
> HTTP API is newer, simpler, and cheaper (~70% less cost). It supports Lambda proxy integrations, JWT authorisers, CORS, and is ideal for CRUD APIs. REST API supports more features: request/response transformations, usage plans, API keys, WAF integration, resource policies, more detailed access logging, and mock integrations. For most modern serverless applications, HTTP API is the right choice. Use REST API when you need usage plans, API keys for third-party access, or request/response transformation.

**Q: Why define CloudWatch Log Groups explicitly in CloudFormation?**
> If you don't define a `LogGroup` resource, Lambda auto-creates one without a retention policy — logs accumulate forever and cost grows indefinitely. Defining the log group explicitly lets you set `RetentionInDays` and also means the log group is cleaned up when the stack is deleted. Name it exactly `/aws/lambda/{FunctionName}` so Lambda uses it automatically. This is a simple best practice that prevents unexpected costs.
