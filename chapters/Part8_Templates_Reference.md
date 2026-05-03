# Part VIII: Code Templates & Quick Reference
## Ready-to-Use Production Templates

---

# Template 1: FastAPI Starter Template

```python
# app/main.py
"""
Production-ready FastAPI template
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment
ENV = os.getenv("ENVIRONMENT", "development")

# App initialization
app = FastAPI(
    title="My API",
    description="Production API",
    version="1.0.0",
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: str

    class Config:
        from_attributes = True

class ItemList(BaseModel):
    items: List[Item]
    total: int

# Dependencies
def get_db():
    """Database dependency - replace with real implementation."""
    db = {}  # Replace with actual DB
    try:
        yield db
    finally:
        pass  # Close connection

# Middleware
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": ENV}

# Routes
@app.get("/items", response_model=ItemList)
def list_items(
    skip: int = 0,
    limit: int = 10,
    db: dict = Depends(get_db)
):
    items = list(db.values())[skip:skip+limit]
    return ItemList(items=items, total=len(db))

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str, db: dict = Depends(get_db)):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    return db[item_id]

@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: dict = Depends(get_db)):
    import uuid
    item_id = str(uuid.uuid4())
    new_item = Item(id=item_id, **item.dict())
    db[item_id] = new_item
    logger.info(f"Created item: {item_id}")
    return new_item

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, db: dict = Depends(get_db)):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    del db[item_id]
    logger.info(f"Deleted item: {item_id}")

# For Lambda deployment
from mangum import Mangum
handler = Mangum(app, lifespan="off")
```

---

# Template 2: CDK Stack Template

```python
# cdk/stacks/api_stack.py
"""
Production CDK stack template
"""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    Tags,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
)
from constructs import Construct
from dataclasses import dataclass
from typing import Optional

@dataclass
class StackConfig:
    """Configuration for the stack."""
    env_name: str
    memory_size: int = 512
    timeout_seconds: int = 30
    log_retention_days: int = 14
    provisioned_concurrency: Optional[int] = None

class APIStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: StackConfig,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
        
        # Tags
        Tags.of(self).add("Environment", config.env_name)
        Tags.of(self).add("Project", "my-api")
        
        # DynamoDB
        self.table = dynamodb.Table(
            self, "Table",
            table_name=f"items-{config.env_name}",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=(
                RemovalPolicy.RETAIN 
                if config.env_name == "prod" 
                else RemovalPolicy.DESTROY
            ),
            point_in_time_recovery=config.env_name == "prod",
        )
        
        # Lambda
        self.handler = _lambda.Function(
            self, "Handler",
            function_name=f"api-handler-{config.env_name}",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset(
                "../app",
                exclude=["*.pyc", "__pycache__", "tests"]
            ),
            memory_size=config.memory_size,
            timeout=Duration.seconds(config.timeout_seconds),
            environment={
                "TABLE_NAME": self.table.table_name,
                "ENVIRONMENT": config.env_name,
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays(config.log_retention_days),
            tracing=_lambda.Tracing.ACTIVE,
        )
        
        # Permissions
        self.table.grant_read_write_data(self.handler)
        
        # Provisioned concurrency for production
        if config.provisioned_concurrency:
            version = self.handler.current_version
            version.add_alias(
                "live",
                provisioned_concurrent_executions=config.provisioned_concurrency
            )
        
        # API Gateway
        self.api = apigw.RestApi(
            self, "API",
            rest_api_name=f"api-{config.env_name}",
            deploy_options=apigw.StageOptions(
                stage_name=config.env_name,
                logging_level=apigw.MethodLoggingLevel.INFO,
                throttling_rate_limit=1000,
                throttling_burst_limit=500,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            )
        )
        
        # Proxy integration
        self.api.root.add_proxy(
            default_integration=apigw.LambdaIntegration(self.handler),
            any_method=True
        )
        
        # Monitoring
        self._setup_monitoring(config)
        
        # Outputs
        CfnOutput(self, "ApiUrl", value=self.api.url)
        CfnOutput(self, "TableName", value=self.table.table_name)
    
    def _setup_monitoring(self, config: StackConfig):
        """Setup CloudWatch alarms and dashboards."""
        
        # Alarm topic
        alarm_topic = sns.Topic(self, "AlarmTopic")
        
        # Lambda errors alarm
        error_alarm = cloudwatch.Alarm(
            self, "ErrorAlarm",
            metric=self.handler.metric_errors(),
            threshold=5,
            evaluation_periods=1,
            alarm_description="Lambda errors exceeded threshold",
        )
        error_alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))
        
        # Dashboard
        dashboard = cloudwatch.Dashboard(
            self, "Dashboard",
            dashboard_name=f"api-{config.env_name}"
        )
        
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda Metrics",
                left=[
                    self.handler.metric_invocations(),
                    self.handler.metric_errors(),
                ]
            ),
            cloudwatch.GraphWidget(
                title="Duration",
                left=[self.handler.metric_duration()]
            )
        )
```

---

# Template 3: Kubernetes Deployment Template

```yaml
# k8s/production-deployment.yaml
---
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: ${APP_NAME}
  labels:
    app: ${APP_NAME}

---
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${APP_NAME}-config
  namespace: ${APP_NAME}
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  WORKERS: "4"

---
# Secret (use external secrets in production!)
apiVersion: v1
kind: Secret
metadata:
  name: ${APP_NAME}-secrets
  namespace: ${APP_NAME}
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@host:5432/db"
  JWT_SECRET: "your-secret-key"

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}
  namespace: ${APP_NAME}
  labels:
    app: ${APP_NAME}
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: ${APP_NAME}
  template:
    metadata:
      labels:
        app: ${APP_NAME}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: ${APP_NAME}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: ${APP_NAME}
          image: ${IMAGE}
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8000
              protocol: TCP
          envFrom:
            - configMapRef:
                name: ${APP_NAME}-config
            - secretRef:
                name: ${APP_NAME}-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1000m"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 5
            successThreshold: 1
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
            timeoutSeconds: 5
            successThreshold: 1
            failureThreshold: 3
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ${APP_NAME}

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: ${APP_NAME}
  namespace: ${APP_NAME}
spec:
  type: ClusterIP
  selector:
    app: ${APP_NAME}
  ports:
    - name: http
      port: 80
      targetPort: 8000
      protocol: TCP

---
# Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${APP_NAME}
  namespace: ${APP_NAME}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
    - hosts:
        - ${DOMAIN}
      secretName: ${APP_NAME}-tls
  rules:
    - host: ${DOMAIN}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ${APP_NAME}
                port:
                  number: 80

---
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ${APP_NAME}-hpa
  namespace: ${APP_NAME}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${APP_NAME}
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

---
# PodDisruptionBudget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ${APP_NAME}-pdb
  namespace: ${APP_NAME}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: ${APP_NAME}

---
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${APP_NAME}
  namespace: ${APP_NAME}
```

---

# Part IX: Quick Reference Cheat Sheets

## FastAPI Cheat Sheet

```python
# Quick Reference

# Basic app
from fastapi import FastAPI
app = FastAPI()

# Route methods
@app.get("/items")
@app.post("/items")
@app.put("/items/{id}")
@app.delete("/items/{id}")
@app.patch("/items/{id}")

# Path parameters
@app.get("/items/{item_id}")
def get(item_id: int):
    pass

# Query parameters
@app.get("/items")
def list(skip: int = 0, limit: int = 10):
    pass

# Request body
from pydantic import BaseModel
class Item(BaseModel):
    name: str

@app.post("/items")
def create(item: Item):
    pass

# Dependency injection
from fastapi import Depends

def get_db():
    yield db

@app.get("/")
def read(db = Depends(get_db)):
    pass

# Authentication
from fastapi.security import OAuth2PasswordBearer
oauth2 = OAuth2PasswordBearer(tokenUrl="token")

# File upload
from fastapi import File, UploadFile
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    pass

# Background tasks
from fastapi import BackgroundTasks
@app.post("/")
def create(bg: BackgroundTasks):
    bg.add_task(func, arg)

# Response types
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
```

## AWS CDK Cheat Sheet

```python
# Quick Reference

# Initialize project
cdk init app --language python

# Common commands
cdk bootstrap
cdk synth
cdk deploy
cdk diff
cdk destroy

# Common resources
from aws_cdk import (
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_apigateway as apigw,
    aws_sqs as sqs,
    aws_sns as sns,
)

# Lambda
_lambda.Function(self, "Fn",
    runtime=_lambda.Runtime.PYTHON_3_11,
    handler="main.handler",
    code=_lambda.Code.from_asset("./lambda")
)

# DynamoDB
dynamodb.Table(self, "Table",
    partition_key=dynamodb.Attribute(
        name="id", type=dynamodb.AttributeType.STRING
    )
)

# S3
s3.Bucket(self, "Bucket",
    versioned=True,
    encryption=s3.BucketEncryption.S3_MANAGED
)

# Grant permissions
table.grant_read_write_data(lambda_fn)
bucket.grant_read(lambda_fn)
```

## kubectl Cheat Sheet

```bash
# Cluster
kubectl cluster-info
kubectl get nodes

# Pods
kubectl get pods [-o wide] [-n namespace]
kubectl describe pod <name>
kubectl logs <pod> [-f]
kubectl exec -it <pod> -- bash

# Deployments
kubectl get deployments
kubectl scale deployment <name> --replicas=3
kubectl rollout status deployment <name>
kubectl rollout undo deployment <name>

# Services
kubectl get services
kubectl expose deployment <name> --port=80

# Apply/Delete
kubectl apply -f file.yaml
kubectl delete -f file.yaml

# Debug
kubectl get events
kubectl top pods
kubectl describe node <name>

# Context
kubectl config get-contexts
kubectl config use-context <name>
```

## Lambda Best Practices

```python
# 1. Initialize OUTSIDE handler
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('my-table')

def handler(event, context):
    # Just use pre-initialized resources
    return table.get_item(Key={'id': '1'})

# 2. Environment variables
import os
TABLE_NAME = os.environ['TABLE_NAME']

# 3. Error handling
def handler(event, context):
    try:
        # Your code
        pass
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

# 4. Structured logging
import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(json.dumps({
        "event": "processing",
        "request_id": context.aws_request_id
    }))
```

---

## AWS Architecture Patterns

```
# Pattern 1: Synchronous API
Client → API Gateway → Lambda → DynamoDB

# Pattern 2: Async Processing
Client → API Gateway → Lambda → SQS → Lambda → DynamoDB

# Pattern 3: Event-Driven
S3 (upload) → Lambda → DynamoDB
                    → SNS → Email

# Pattern 4: Microservices on EKS
ALB → Ingress → Service A
              → Service B
              → Service C

# Pattern 5: Hybrid
CloudFront → S3 (static)
          → API Gateway → Lambda → RDS
```

---

# Final Checklist

## Production Readiness

### Application
- [ ] Input validation
- [ ] Error handling
- [ ] Logging
- [ ] Health endpoints
- [ ] Rate limiting
- [ ] Authentication
- [ ] CORS configured

### Infrastructure
- [ ] VPC configuration
- [ ] Security groups
- [ ] IAM least privilege
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Backups configured

### Monitoring
- [ ] CloudWatch metrics
- [ ] Alarms configured
- [ ] Dashboard created
- [ ] Log retention set
- [ ] Tracing enabled

### CI/CD
- [ ] Automated testing
- [ ] Staging environment
- [ ] Blue/green deployment
- [ ] Rollback procedure

---

**END OF GUIDE**

This comprehensive guide covers everything you need to build, deploy, and manage FastAPI applications with AWS CDK, Lambda, and Kubernetes. Good luck with your projects and interviews!
