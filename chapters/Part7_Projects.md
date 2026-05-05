# Part 7: Projects — Full-Stack AWS Applications

---

## Project 1: E-Commerce Order Management System

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    E-Commerce Architecture                        │
│                                                                    │
│  CloudFront (CDN) → ALB → ECS Fargate (FastAPI)                  │
│       ↓                        ↓                                  │
│  S3 (static)           DynamoDB (orders)                         │
│                         Aurora (products/catalog)                 │
│                         ElastiCache Redis (sessions/cart)         │
│                                ↓                                  │
│                    SQS → Lambda (order processing)               │
│                         → SNS (notifications)                     │
│                              → SES (email)                        │
│                              → SMS (pinpoint)                     │
└──────────────────────────────────────────────────────────────────┘
```

### CDK Infrastructure

```python
# infra/stacks/ecommerce_stack.py
import aws_cdk as cdk
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_rds as rds,
    aws_elasticache as elasticache,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_lambda as lambda_,
    aws_lambda_event_sources as event_sources,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_kms as kms,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct


class ECommerceStack(cdk.Stack):
    
    def __init__(self, scope, id, *, environment: str, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # ── KMS Encryption Key ────────────────────────
        key = kms.Key(self, "Key", enable_key_rotation=True)
        
        # ── DynamoDB: Orders Table ────────────────────
        orders_table = dynamodb.TableV2(
            self, "OrdersTable",
            table_name=f"orders-{environment}",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(),
            encryption=dynamodb.TableEncryptionV2.aws_managed_key(),
            point_in_time_recovery=True,
            removal_policy=cdk.RemovalPolicy.RETAIN if environment == "prod" else cdk.RemovalPolicy.DESTROY,
        )
        
        # ── Aurora PostgreSQL: Product Catalog ────────
        db_secret = rds.DatabaseSecret(self, "DBSecret", username="dbadmin")
        
        aurora = rds.DatabaseCluster(
            self, "Aurora",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_4
            ),
            credentials=rds.Credentials.from_secret(db_secret),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=8,
            writer=rds.ClusterInstance.serverless_v2("Writer"),
            readers=[rds.ClusterInstance.serverless_v2("Reader")] if environment == "prod" else [],
            storage_encrypted=True,
            storage_encryption_key=key,
            backup=rds.BackupProps(retention=cdk.Duration.days(30 if environment == "prod" else 7)),
            deletion_protection=environment == "prod",
            removal_policy=cdk.RemovalPolicy.RETAIN if environment == "prod" else cdk.RemovalPolicy.DESTROY,
        )
        
        # ── SQS: Order Processing Queue ───────────────
        order_dlq = sqs.Queue(self, "OrderDLQ",
            retention_period=cdk.Duration.days(14),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=key,
        )
        
        order_queue = sqs.Queue(self, "OrderQueue",
            visibility_timeout=cdk.Duration.seconds(300),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=key,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=order_dlq),
        )
        
        # ── SNS: Notification Topic ───────────────────
        notification_topic = sns.Topic(self, "NotificationTopic",
            master_key=key,
            display_name=f"ecommerce-notifications-{environment}",
        )
        
        # ── S3: Assets Bucket ─────────────────────────
        assets_bucket = s3.Bucket(self, "AssetsBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        
        # ── ECS Fargate: FastAPI Service ──────────────
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)
        
        task_role = iam.Role(self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        orders_table.grant_read_write_data(task_role)
        order_queue.grant_send_messages(task_role)
        assets_bucket.grant_read_write(task_role)
        aurora.secret.grant_read(task_role)
        
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ApiService",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(
                    f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/ecommerce-api:latest"
                ),
                task_role=task_role,
                environment={
                    "ENVIRONMENT": environment,
                    "ORDERS_TABLE": orders_table.table_name,
                    "ORDER_QUEUE_URL": order_queue.queue_url,
                    "NOTIFICATION_TOPIC_ARN": notification_topic.topic_arn,
                    "ASSETS_BUCKET": assets_bucket.bucket_name,
                },
                secrets={
                    "DATABASE_URL": ecs.Secret.from_secrets_manager(aurora.secret, field="database_url"),
                },
            ),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )
        
        # ── Lambda: Order Processor ───────────────────
        order_processor = lambda_.Function(self, "OrderProcessor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="processor.handler",
            code=lambda_.Code.from_asset("src/order_processor"),
            architecture=lambda_.Architecture.ARM_64,
            timeout=cdk.Duration.minutes(5),
            memory_size=1024,
            environment={
                "ORDERS_TABLE": orders_table.table_name,
                "NOTIFICATION_TOPIC_ARN": notification_topic.topic_arn,
            },
            tracing=lambda_.Tracing.ACTIVE,
        )
        
        orders_table.grant_read_write_data(order_processor)
        notification_topic.grant_publish(order_processor)
        order_processor.add_event_source(
            event_sources.SqsEventSource(order_queue, batch_size=10, report_batch_item_failures=True)
        )
        
        # ── CloudFront Distribution ───────────────────
        distribution = cloudfront.Distribution(self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(
                    fargate_service.load_balancer,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                ),
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/static/*": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(assets_bucket),
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                )
            },
        )
        
        cdk.CfnOutput(self, "ApiUrl", value=f"https://{distribution.distribution_domain_name}")
```

---

## Project 2: Real-Time Analytics Dashboard

### Architecture

```
Data Ingestion:  Kinesis Data Streams → Lambda → DynamoDB
                 CloudWatch Logs → Kinesis Firehose → S3
Analytics:       S3 → Athena (SQL queries) → QuickSight
Real-Time:       DynamoDB Streams → Lambda → API GW WebSocket
Frontend:        CloudFront → S3 (React SPA)
```

```python
# FastAPI WebSocket endpoint for real-time dashboard
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import boto3
import json
import asyncio

router = APIRouter()
dynamodb = boto3.client("dynamodb")

class DashboardManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
    
    async def connect(self, ws: WebSocket, user_id: str):
        await ws.accept()
        self.connections[user_id] = ws
    
    def disconnect(self, user_id: str):
        self.connections.pop(user_id, None)
    
    async def broadcast_metric(self, metric: dict):
        disconnected = []
        for user_id, ws in self.connections.items():
            try:
                await ws.send_json(metric)
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.connections.pop(uid, None)

manager = DashboardManager()

@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        # Send initial snapshot
        metrics = await get_current_metrics()
        await websocket.send_json({"type": "snapshot", "data": metrics})
        
        # Keep alive while waiting for updates
        while True:
            try:
                # Wait for client ping
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)
```

---

## Project 3: ML Inference API

### Architecture

```
Client → API Gateway → Lambda (FastAPI/Mangum)
                         → S3 (model artifacts)
                         → SageMaker Endpoint (inference)
                         → DynamoDB (prediction cache)
```

```python
# FastAPI ML inference endpoint
import boto3
import json
import hashlib
from functools import lru_cache

sagemaker_runtime = boto3.client("sagemaker-runtime")
dynamodb = boto3.resource("dynamodb")
cache_table = dynamodb.Table("prediction-cache")


async def get_cached_prediction(input_hash: str) -> dict | None:
    response = cache_table.get_item(Key={"hash": input_hash})
    return response.get("Item")


async def cache_prediction(input_hash: str, prediction: dict, ttl: int = 3600):
    from time import time
    cache_table.put_item(Item={
        "hash": input_hash,
        "prediction": prediction,
        "ttl": int(time()) + ttl,
    })


@router.post("/predict")
async def predict(request: PredictionRequest, current_user=Depends(get_current_user)):
    # Hash input for cache key
    input_hash = hashlib.sha256(
        json.dumps(request.features, sort_keys=True).encode()
    ).hexdigest()
    
    # Check cache first
    cached = await get_cached_prediction(input_hash)
    if cached:
        return {**cached["prediction"], "cached": True}
    
    # Call SageMaker endpoint
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=os.environ["SAGEMAKER_ENDPOINT"],
        ContentType="application/json",
        Body=json.dumps({"features": request.features}),
    )
    
    prediction = json.loads(response["Body"].read())
    
    # Cache result
    await cache_prediction(input_hash, prediction)
    
    return {**prediction, "cached": False}
```

---

## Interview Q&A

**Q: How do you design a system that handles 1 million requests per day?**
A: 1M req/day ≈ 11.6 req/s average, with peaks potentially 10x = ~116 req/s peak. This is modest — a single FastAPI container handles 500-1000 req/s. Design: CloudFront (cache static, absorb spikes) → ALB → 2-5 ECS Fargate tasks (auto-scale on CPU/requests) → Aurora Serverless v2 (scales storage/compute automatically) + Redis cache (reduce DB load). Key decisions: (1) Cache aggressively at CDN and application layer; (2) Use async/await for DB calls; (3) Set up auto-scaling so you scale before you need it; (4) Monitor P95/P99 latency, not just average. This architecture comfortably handles 10M req/day with proper caching.

**Q: How do you implement a multi-tenant SaaS on AWS?**
A: Three models: (1) **Silo** (dedicated per-tenant): Separate AWS account/VPC per tenant. Max isolation, highest cost, hardest to manage. Best for enterprise compliance. (2) **Pool** (shared infrastructure): All tenants share the same ECS service, DynamoDB table (partition key = tenant_id), Aurora DB. Cheapest, most efficient. Tenant data mixing risk — must filter everything by tenant_id. (3) **Bridge**: Shared infra with dedicated resources for premium tenants. In DynamoDB, use `PK = TENANT#{tenant_id}#...` — isolates by key prefix. In PostgreSQL, use Row Level Security (RLS) policies. Always validate tenant access in middleware: extract tenant from JWT, inject into DB session context, never trust tenant IDs from request body.
