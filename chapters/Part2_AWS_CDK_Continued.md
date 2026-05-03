# Part II: AWS CDK (Continued)
## Chapters 12-16: Core Services, Compute, Networking, Security & Patterns

---

# Chapter 12: Core AWS Services with CDK

## 12.1 S3 Buckets

### What is S3?

S3 (Simple Storage Service) is AWS's object storage. Think of it as a giant, unlimited hard drive in the cloud.

```
S3 Structure:
┌────────────────────────────┐
│         BUCKET             │  ← Like a folder
│  ┌─────────────────────┐   │
│  │    /images/         │   │
│  │    ├── photo1.jpg   │   │  ← Objects (files)
│  │    ├── photo2.png   │   │
│  │                     │   │
│  │    /documents/      │   │
│  │    ├── report.pdf   │   │
│  │    └── data.csv     │   │
│  └─────────────────────┘   │
└────────────────────────────┘
```

### Creating S3 Buckets with CDK

```python
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
)
from constructs import Construct

class S3Stack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Basic bucket
        basic_bucket = s3.Bucket(
            self, "BasicBucket"
            # AWS generates a unique name
        )
        
        # Bucket with all options
        advanced_bucket = s3.Bucket(
            self, "AdvancedBucket",
            
            # Naming (optional - AWS generates if not specified)
            bucket_name="my-unique-bucket-name-12345",
            
            # Versioning - keep all versions of objects
            versioned=True,
            
            # Encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Options: UNENCRYPTED, S3_MANAGED, KMS_MANAGED, KMS
            
            # Public access
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            
            # Lifecycle rules
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldFiles",
                    expiration=Duration.days(365),  # Delete after 1 year
                ),
                s3.LifecycleRule(
                    id="MoveToGlacier",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)  # After 90 days
                        )
                    ]
                )
            ],
            
            # What happens when stack is deleted
            removal_policy=RemovalPolicy.DESTROY,  # Delete bucket
            auto_delete_objects=True,  # Delete contents first
        )
        
        # Website hosting
        website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            )
        )
```

### Common S3 Operations

```python
# Grant permissions
bucket.grant_read(lambda_function)       # Lambda can read
bucket.grant_write(lambda_function)      # Lambda can write
bucket.grant_read_write(lambda_function) # Both

# Add event notifications
from aws_cdk import aws_s3_notifications as s3n

bucket.add_event_notification(
    s3.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(lambda_function),
    s3.NotificationKeyFilter(prefix="uploads/", suffix=".jpg")
)

# Deploy files to bucket
from aws_cdk import aws_s3_deployment as s3deploy

s3deploy.BucketDeployment(
    self, "DeployFiles",
    sources=[s3deploy.Source.asset("./local-folder")],
    destination_bucket=bucket,
    destination_key_prefix="path/in/bucket"
)
```

---

## 12.2 DynamoDB Tables

### What is DynamoDB?

DynamoDB is a fast, serverless NoSQL database. Perfect for high-scale applications.

```
DynamoDB Structure:
┌─────────────────────────────────────────────────────────┐
│                        TABLE                             │
├──────────────────┬──────────────────┬──────────────────┤
│ Partition Key    │ Sort Key         │ Attributes       │
│ (Required)       │ (Optional)       │ (Flexible)       │
├──────────────────┼──────────────────┼──────────────────┤
│ user_123         │ order_001        │ {status, total}  │
│ user_123         │ order_002        │ {status, total}  │
│ user_456         │ order_003        │ {status, items}  │
└──────────────────┴──────────────────┴──────────────────┘
```

### Creating DynamoDB Tables

```python
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
)

class DynamoDBStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Simple table with just partition key
        simple_table = dynamodb.Table(
            self, "SimpleTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Table with partition key and sort key
        orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="orders",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="order_id",
                type=dynamodb.AttributeType.STRING
            ),
            
            # Billing mode
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            # Or: PROVISIONED with read/write capacity
            
            # Stream for change data capture
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Add Global Secondary Index (GSI)
        orders_table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Grant permissions
        orders_table.grant_read_write_data(lambda_function)
```

---

## 12.3 SQS Queues

### What is SQS?

SQS (Simple Queue Service) is a message queue. Services send messages to the queue, and other services process them.

```
Producer → [SQS Queue] → Consumer

Use case: Order processing
1. Web app receives order
2. Sends message to queue
3. Worker service processes order asynchronously
```

### Creating SQS Queues

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_sqs as sqs,
)

class SQSStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Dead letter queue (for failed messages)
        dlq = sqs.Queue(
            self, "DeadLetterQueue",
            queue_name="my-dlq",
            retention_period=Duration.days(14)
        )
        
        # Main queue
        main_queue = sqs.Queue(
            self, "MainQueue",
            queue_name="my-queue",
            
            # Message settings
            visibility_timeout=Duration.seconds(300),  # 5 minutes
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            retention_period=Duration.days(4),
            
            # Dead letter queue
            dead_letter_queue=sqs.DeadLetterQueue(
                queue=dlq,
                max_receive_count=3  # After 3 failures, move to DLQ
            )
        )
        
        # FIFO Queue (First-In-First-Out)
        fifo_queue = sqs.Queue(
            self, "FifoQueue",
            queue_name="my-queue.fifo",  # Must end with .fifo
            fifo=True,
            content_based_deduplication=True
        )
        
        # Grant permissions
        main_queue.grant_send_messages(producer_lambda)
        main_queue.grant_consume_messages(consumer_lambda)
```

---

## 12.4 SNS Topics

### What is SNS?

SNS (Simple Notification Service) is a pub/sub messaging service. One message can go to many subscribers.

```
Publisher → [SNS Topic] → Subscriber 1 (Email)
                       → Subscriber 2 (Lambda)
                       → Subscriber 3 (SQS Queue)
```

### Creating SNS Topics

```python
from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
)

class SNSStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create topic
        topic = sns.Topic(
            self, "MyTopic",
            topic_name="notifications",
            display_name="My Notifications"
        )
        
        # Add subscriptions
        
        # Email subscription
        topic.add_subscription(
            subs.EmailSubscription("admin@example.com")
        )
        
        # Lambda subscription
        topic.add_subscription(
            subs.LambdaSubscription(my_lambda)
        )
        
        # SQS subscription
        topic.add_subscription(
            subs.SqsSubscription(my_queue)
        )
        
        # Grant publish permission
        topic.grant_publish(publisher_lambda)
```

---

## 12.5 API Gateway

### What is API Gateway?

API Gateway creates HTTP endpoints that trigger Lambda functions or other services.

```
Client → API Gateway → Lambda → Database
           ↓
    Handles: Auth, Rate limiting, Caching
```

### Creating API Gateway

```python
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
)

class APIStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Lambda function
        handler = _lambda.Function(
            self, "Handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="main.handler",
            code=_lambda.Code.from_asset("lambda")
        )
        
        # Option 1: Lambda REST API (simplest)
        api = apigw.LambdaRestApi(
            self, "SimpleApi",
            handler=handler
        )
        
        # Option 2: REST API with more control
        api = apigw.RestApi(
            self, "MyApi",
            rest_api_name="My Service",
            description="My API Gateway",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=1000,
                throttling_burst_limit=500
            )
        )
        
        # Add resources and methods
        # /items
        items = api.root.add_resource("items")
        items.add_method(
            "GET",
            apigw.LambdaIntegration(list_handler),
            api_key_required=True
        )
        items.add_method(
            "POST",
            apigw.LambdaIntegration(create_handler)
        )
        
        # /items/{id}
        item = items.add_resource("{id}")
        item.add_method(
            "GET",
            apigw.LambdaIntegration(get_handler)
        )
        item.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_handler)
        )
        
        # Add CORS
        items.add_cors_preflight(
            allow_origins=["https://mywebsite.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization"]
        )
```

### HTTP API (Simpler, Cheaper)

```python
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration

# HTTP API - simpler and cheaper than REST API
http_api = apigwv2.HttpApi(
    self, "HttpApi",
    api_name="my-http-api",
    cors_preflight=apigwv2.CorsPreflightOptions(
        allow_headers=["Authorization"],
        allow_methods=[
            apigwv2.CorsHttpMethod.GET,
            apigwv2.CorsHttpMethod.POST
        ],
        allow_origins=["*"]
    )
)

# Add Lambda integration
http_api.add_routes(
    path="/items",
    methods=[apigwv2.HttpMethod.GET],
    integration=HttpLambdaIntegration("GetItems", handler)
)
```

---

## 12.6 CloudWatch Logs and Alarms

### CloudWatch Overview

CloudWatch monitors your AWS resources and applications.

```
Your App → Logs → CloudWatch Logs
                        ↓
              Metrics → Alarms → SNS → Email
```

### Creating Logs and Alarms

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_logs as logs,
)

class MonitoringStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Log group
        log_group = logs.LogGroup(
            self, "MyLogGroup",
            log_group_name="/my-app/logs",
            retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Metric filter - count errors in logs
        error_metric = log_group.add_metric_filter(
            "ErrorMetric",
            filter_pattern=logs.FilterPattern.literal("ERROR"),
            metric_name="ErrorCount",
            metric_namespace="MyApp"
        )
        
        # Alarm based on metric
        error_alarm = cloudwatch.Alarm(
            self, "ErrorAlarm",
            metric=cloudwatch.Metric(
                namespace="MyApp",
                metric_name="ErrorCount"
            ),
            threshold=10,
            evaluation_periods=1,
            alarm_description="Too many errors!",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        
        # Add alarm action
        error_alarm.add_alarm_action(
            cw_actions.SnsAction(alert_topic)
        )
        
        # Lambda error alarm
        lambda_errors = cloudwatch.Alarm(
            self, "LambdaErrors",
            metric=lambda_function.metric_errors(),
            threshold=1,
            evaluation_periods=1
        )
        
        # Dashboard
        dashboard = cloudwatch.Dashboard(
            self, "MyDashboard",
            dashboard_name="my-app-dashboard"
        )
        
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda Invocations",
                left=[lambda_function.metric_invocations()]
            ),
            cloudwatch.GraphWidget(
                title="Errors",
                left=[lambda_function.metric_errors()]
            )
        )
```

---

# Chapter 13: Compute Services

## 13.1 Lambda Functions

### Complete Lambda Example

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
)

class LambdaStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Lambda from local code
        api_handler = _lambda.Function(
            self, "ApiHandler",
            function_name="my-api-handler",
            
            # Runtime
            runtime=_lambda.Runtime.PYTHON_3_11,
            
            # Code location
            code=_lambda.Code.from_asset("./lambda/api"),
            handler="main.handler",  # file.function
            
            # Configuration
            memory_size=256,  # MB
            timeout=Duration.seconds(30),
            
            # Environment variables
            environment={
                "TABLE_NAME": table.table_name,
                "ENVIRONMENT": "production"
            },
            
            # Logging
            log_retention=logs.RetentionDays.ONE_WEEK,
            
            # Tracing
            tracing=_lambda.Tracing.ACTIVE
        )
        
        # Grant permissions
        table.grant_read_write_data(api_handler)
        bucket.grant_read(api_handler)
```

### Lambda Layers

```python
# Create layer from local files
layer = _lambda.LayerVersion(
    self, "DependenciesLayer",
    code=_lambda.Code.from_asset("./layers/dependencies"),
    compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
    description="Python dependencies"
)

# Use the layer
function = _lambda.Function(
    self, "MyFunction",
    runtime=_lambda.Runtime.PYTHON_3_11,
    code=_lambda.Code.from_asset("./lambda"),
    handler="main.handler",
    layers=[layer]  # Add layer
)
```

---

## 13.2 ECS and Fargate

### What is ECS/Fargate?

ECS runs Docker containers. Fargate is serverless - no servers to manage.

```python
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
)

class FargateStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # VPC
        vpc = ec2.Vpc(self, "MyVpc", max_azs=2)
        
        # ECS Cluster
        cluster = ecs.Cluster(
            self, "MyCluster",
            vpc=vpc,
            cluster_name="my-cluster"
        )
        
        # Fargate Service with Load Balancer (L3 Pattern)
        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "MyService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("./docker"),
                container_port=8000,
                environment={
                    "ENVIRONMENT": "production"
                }
            ),
            public_load_balancer=True
        )
        
        # Auto Scaling
        scaling = service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=10
        )
        
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70
        )
```

---

## 13.3 Step Functions

### What is Step Functions?

Step Functions orchestrate multiple Lambda functions into workflows.

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)

class StepFunctionsStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Step 1: Process Order
        process_order = tasks.LambdaInvoke(
            self, "ProcessOrder",
            lambda_function=process_lambda,
            result_path="$.orderResult"
        )
        
        # Step 2: Send Notification
        send_notification = tasks.LambdaInvoke(
            self, "SendNotification",
            lambda_function=notify_lambda
        )
        
        # Error handler
        handle_error = tasks.LambdaInvoke(
            self, "HandleError",
            lambda_function=error_lambda
        )
        
        # Build workflow
        definition = process_order.add_catch(
            handle_error,
            errors=["States.ALL"]
        ).next(send_notification)
        
        # Create state machine
        state_machine = sfn.StateMachine(
            self, "OrderWorkflow",
            state_machine_name="order-workflow",
            definition=definition,
            timeout=Duration.minutes(5)
        )
```

---

# Chapter 14: Networking with CDK

## 14.1 VPC Configuration

```python
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)

class NetworkStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # VPC with all options
        vpc = ec2.Vpc(
            self, "MyVpc",
            vpc_name="my-vpc",
            
            # IP range
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            
            # Availability zones
            max_azs=3,
            
            # Subnet configuration
            subnet_configuration=[
                # Public subnets (internet access)
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                # Private subnets (with NAT Gateway)
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                # Isolated subnets (no internet)
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ],
            
            # NAT Gateways
            nat_gateways=1  # One NAT per AZ can be expensive
        )
        
        # Security Group
        security_group = ec2.SecurityGroup(
            self, "MySecurityGroup",
            vpc=vpc,
            description="Allow web traffic",
            allow_all_outbound=True
        )
        
        # Allow inbound HTTP
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP"
        )
        
        # Allow inbound HTTPS
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS"
        )
```

---

# Chapter 15: Security and IAM

## 15.1 IAM Roles and Policies

```python
from aws_cdk import (
    Stack,
    aws_iam as iam,
)

class SecurityStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create IAM Role
        role = iam.Role(
            self, "MyRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for my Lambda function"
        )
        
        # Add managed policies
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        
        # Add custom policy
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                resources=[f"{bucket.bucket_arn}/*"]
            )
        )
        
        # Create custom policy
        custom_policy = iam.Policy(
            self, "CustomPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=["dynamodb:*"],
                    resources=[table.table_arn]
                )
            ]
        )
        
        role.attach_inline_policy(custom_policy)
```

## 15.2 Secrets Manager

```python
from aws_cdk import (
    Stack,
    aws_secretsmanager as secretsmanager,
)

class SecretsStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create secret
        secret = secretsmanager.Secret(
            self, "MySecret",
            secret_name="my-app/database-credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
                exclude_punctuation=True
            )
        )
        
        # Grant read access to Lambda
        secret.grant_read(lambda_function)
        
        # Use in Lambda environment
        lambda_function = _lambda.Function(
            self, "MyFunction",
            environment={
                "SECRET_ARN": secret.secret_arn
            }
        )
```

---

# Chapter 16: CDK Patterns and Best Practices

## 16.1 Construct Libraries

Create reusable constructs for your organization:

```python
# my_constructs/api_lambda.py

from constructs import Construct
from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_logs as logs,
    Duration,
)

class ApiLambda(Construct):
    """
    Reusable construct for API + Lambda setup.
    Use across multiple projects.
    """
    
    def __init__(
        self,
        scope: Construct,
        id: str,
        code_path: str,
        handler: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
        
        # Lambda
        self.function = _lambda.Function(
            self, "Function",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(code_path),
            handler=handler,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # API Gateway
        self.api = apigw.LambdaRestApi(
            self, "Api",
            handler=self.function
        )
    
    @property
    def url(self):
        return self.api.url

# Usage
class MyStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        api = ApiLambda(
            self, "UserApi",
            code_path="./lambda/users",
            handler="main.handler"
        )
        
        CfnOutput(self, "ApiUrl", value=api.url)
```

## 16.2 CDK Testing

```python
# tests/test_my_stack.py

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from my_stack import MyStack

def test_lambda_created():
    app = cdk.App()
    stack = MyStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Check Lambda exists
    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.11",
        "MemorySize": 256
    })

def test_s3_bucket_encrypted():
    app = cdk.App()
    stack = MyStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Check S3 encryption
    template.has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": Match.object_like({
            "ServerSideEncryptionConfiguration": Match.any_value()
        })
    })

def test_resource_count():
    app = cdk.App()
    stack = MyStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Count resources
    template.resource_count_is("AWS::Lambda::Function", 2)
    template.resource_count_is("AWS::DynamoDB::Table", 1)
```

---

*Continue to Part 3 for AWS Lambda Chapters...*
