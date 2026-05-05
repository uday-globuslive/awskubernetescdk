# Part 8: Templates & Reference

---

## FastAPI Templates

### Minimal FastAPI App

```python
# main.py — minimal production-ready FastAPI
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app):
    # startup
    yield
    # shutdown

app = FastAPI(title="My API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"ok": True}
```

### Pydantic Model Templates

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime

class CreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    value: float = Field(gt=0, le=1_000_000)

class UpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[float] = Field(None, gt=0)

class Response(BaseModel):
    id: int
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}

class PaginatedResponse(BaseModel):
    items: list[Response]
    total: int
    page: int
    pages: int
```

### Authentication Template

```python
# OAuth2 + JWT pattern
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

pwd_context = CryptContext(schemes=["bcrypt"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/token")
SECRET = "your-secret-key"
ALGORITHM = "HS256"

def hash_password(p): return pwd_context.hash(p)
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)

def create_token(subject: str, expire_minutes: int = 30) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, SECRET, ALGORITHM)

async def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET, [ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid token", headers={"WWW-Authenticate": "Bearer"})
    return user_id
```

---

## AWS CDK Templates

### VPC Template

```python
vpc = ec2.Vpc(self, "VPC",
    ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
    max_azs=3,
    nat_gateways=1,
    subnet_configuration=[
        ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
        ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24),
        ec2.SubnetConfiguration(name="DB", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
    ],
)
vpc.add_gateway_endpoint("S3", service=ec2.GatewayVpcEndpointAwsService.S3)
```

### Lambda Template

```python
fn = lambda_.Function(self, "Function",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="app.handler",
    code=lambda_.Code.from_asset("src"),
    architecture=lambda_.Architecture.ARM_64,
    memory_size=512,
    timeout=cdk.Duration.seconds(30),
    tracing=lambda_.Tracing.ACTIVE,
    environment={"TABLE": table.table_name},
)
table.grant_read_write_data(fn)
```

### ECS Fargate Template

```python
service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "Service",
    cluster=cluster,
    cpu=512,
    memory_limit_mib=1024,
    desired_count=2,
    task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
        image=ecs.ContainerImage.from_registry(image_uri),
        container_port=8000,
        task_role=task_role,
        environment=env_vars,
        secrets=secrets,
    ),
    circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
)
service.service.auto_scale_task_count(min_capacity=2, max_capacity=20).scale_on_cpu_utilization(
    "CpuScaling", target_utilization_percent=70
)
```

---

## CloudFormation Quick Reference

### Common Resource Types

| Resource | CloudFormation Type |
|----------|---------------------|
| S3 Bucket | `AWS::S3::Bucket` |
| Lambda Function | `AWS::Lambda::Function` |
| DynamoDB Table | `AWS::DynamoDB::Table` |
| ECS Service | `AWS::ECS::Service` |
| Aurora Cluster | `AWS::RDS::DBCluster` |
| VPC | `AWS::EC2::VPC` |
| ALB | `AWS::ElasticLoadBalancingV2::LoadBalancer` |
| API Gateway | `AWS::ApiGatewayV2::Api` |
| IAM Role | `AWS::IAM::Role` |
| CloudFront | `AWS::CloudFront::Distribution` |

### Intrinsic Functions Quick Reference

```yaml
!Ref LogicalName                         # Reference resource or parameter
!GetAtt Resource.Attribute               # Get attribute of resource
!Sub 'string-with-${Variable}'           # String substitution
!Join ['-', [!Ref Env, 'app']]          # Join list with delimiter
!Select [0, !GetAZs '']                 # Select item from list
!If [ConditionName, TrueValue, False]   # Conditional value
!ImportValue ExportName                  # Cross-stack import
!FindInMap [MapName, Key1, Key2]        # Look up in Mappings
```

### Deletion/Update Policies

```yaml
Resources:
  MyDB:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: Retain      # Keep on stack delete
    UpdateReplacePolicy: Retain # Keep on resource replace
    Properties:
      DeletionProtection: true   # Prevent CLI delete
```

---

## Kubernetes Quick Reference

### Common kubectl Commands

```bash
# Pods
kubectl get pods -n myapp
kubectl describe pod <name> -n myapp
kubectl logs <pod> -n myapp --follow
kubectl exec -it <pod> -n myapp -- /bin/sh

# Deployments
kubectl rollout status deployment/orders-api -n myapp
kubectl rollout history deployment/orders-api -n myapp
kubectl rollout undo deployment/orders-api -n myapp

# Scaling
kubectl scale deployment orders-api --replicas=5 -n myapp

# Secrets & ConfigMaps
kubectl create secret generic app-secrets --from-literal=KEY=value -n myapp
kubectl get secret app-secrets -o jsonpath='{.data.KEY}' | base64 -d

# Resources
kubectl top pods -n myapp
kubectl top nodes

# Port forwarding for debugging
kubectl port-forward svc/orders-api 8080:80 -n myapp
```

### Useful Annotations

```yaml
# ALB Ingress
alb.ingress.kubernetes.io/scheme: internet-facing
alb.ingress.kubernetes.io/target-type: ip
alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...

# IRSA
eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/ROLE_NAME

# Prometheus scraping
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

---

## Docker Cheat Sheet

```bash
# Build
docker build -t myapi:latest .
docker build -t myapi:v1.0 --platform linux/arm64 .    # For Graviton

# Run
docker run -p 8000:8000 --env-file .env myapi:latest

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker tag myapi:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/myapi:latest
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/myapi:latest

# Inspect
docker inspect myapi:latest
docker history myapi:latest --no-trunc
docker stats

# Cleanup
docker system prune -af
```

---

## AWS CLI Quick Reference

```bash
# ECS
aws ecs list-clusters
aws ecs describe-services --cluster myapp --services orders-api
aws ecs update-service --cluster myapp --service orders-api --force-new-deployment

# Lambda
aws lambda list-functions --query "Functions[*].[FunctionName,Runtime]"
aws lambda invoke --function-name myfunction --payload '{}' response.json
aws lambda update-function-configuration --function-name myfunction --memory-size 1024

# DynamoDB
aws dynamodb scan --table-name orders-prod --select COUNT
aws dynamodb get-item --table-name orders-prod --key '{"PK":{"S":"ORDER#123"},"SK":{"S":"METADATA"}}'

# CloudFormation
aws cloudformation describe-stacks --query "Stacks[*].[StackName,StackStatus]" --output table
aws cloudformation get-template --stack-name mystack
aws cloudformation list-stack-resources --stack-name mystack

# Logs
aws logs tail /ecs/myapp/prod/app --follow
aws logs filter-log-events --log-group-name /ecs/myapp --filter-pattern "ERROR"
```
