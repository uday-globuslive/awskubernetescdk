# Chapter 8: Containers — ECS, Fargate, EKS & ECR
## Running Containerised Applications on AWS

---

## 8.1 Container Services Overview

```
┌──────────────────────────────────────────────────────────┐
│              AWS CONTAINER SERVICES                      │
├────────────────────┬─────────────────────────────────────┤
│ ECR                │ Elastic Container Registry           │
│                    │ Private Docker image registry        │
├────────────────────┼─────────────────────────────────────┤
│ ECS                │ Elastic Container Service            │
│                    │ AWS-native container orchestration   │
│                    │ Simpler than Kubernetes              │
├────────────────────┼─────────────────────────────────────┤
│ Fargate            │ Serverless compute for containers    │
│                    │ No EC2 instances to manage           │
│                    │ Works with ECS and EKS               │
├────────────────────┼─────────────────────────────────────┤
│ EKS                │ Elastic Kubernetes Service           │
│                    │ Managed Kubernetes control plane     │
│                    │ More power, more complexity          │
└────────────────────┴─────────────────────────────────────┘

ECS + Fargate = AWS-native, easiest to operate
EKS = Kubernetes, portable across clouds
```

---

## 8.2 ECR — Elastic Container Registry

ECR is a private Docker image registry.

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository \
  --repository-name my-app \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# Build and push image
docker build -t my-app:v1.0 .
docker tag my-app:v1.0 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0

# List images
aws ecr list-images --repository-name my-app

# Set lifecycle policy (auto-delete old images)
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {"type": "expire"}
    }]
  }'
```

### ECR in GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Build and Push to ECR

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # For OIDC auth — no stored secrets!
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials (OIDC — no keys needed)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
          aws-region: us-east-1

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and Push
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/my-app:$IMAGE_TAG .
          docker push $ECR_REGISTRY/my-app:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/my-app:$IMAGE_TAG" >> $GITHUB_OUTPUT
```

---

## 8.3 ECS — Elastic Container Service

ECS manages where and how containers run. Two launch types: EC2 (you manage instances) or Fargate (AWS manages instances).

### ECS Concepts

```
┌──────────────────────────────────────────────────────────┐
│                   ECS HIERARCHY                          │
│                                                          │
│  Cluster                                                 │
│  └── Service (keeps N tasks running, handles rolling     │
│      │        deploys, connects to ALB)                 │
│      └── Task (one running unit = one or more            │
│               containers)                               │
│                                                          │
│  Task Definition (blueprint for a task):                 │
│  └── Container definitions (image, CPU, memory,         │
│      ports, env vars, logging, health check)            │
└──────────────────────────────────────────────────────────┘
```

### Task Definition

```json
// task-definition.json
{
  "family": "fastapi-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456:role/ecs-task-execution-role",
  "taskRoleArn": "arn:aws:iam::123456:role/fastapi-task-role",
  "containerDefinitions": [
    {
      "name": "fastapi",
      "image": "123456.dkr.ecr.us-east-1.amazonaws.com/my-app:latest",
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "prod"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456:secret:myapp/db-password-abc123"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/fastapi-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "fastapi"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "essential": true
    }
  ]
}
```

```bash
# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# Create cluster
aws ecs create-cluster \
  --cluster-name prod-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=4

# Create service
aws ecs create-service \
  --cluster prod-cluster \
  --service-name fastapi-service \
  --task-definition fastapi-app:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-0abc", "subnet-0def"],
      "securityGroups": ["sg-0abc123"],
      "assignPublicIp": "DISABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "arn:aws:elasticloadbalancing:...:targetgroup/...",
    "containerName": "fastapi",
    "containerPort": 8000
  }]' \
  --deployment-configuration '{
    "minimumHealthyPercent": 50,
    "maximumPercent": 200,
    "deploymentCircuitBreaker": {"enable": true, "rollback": true}
  }' \
  --health-check-grace-period-seconds 60

# Deploy new version (update service with new task definition)
aws ecs update-service \
  --cluster prod-cluster \
  --service fastapi-service \
  --task-definition fastapi-app:2 \
  --force-new-deployment

# View service events (deployment progress)
aws ecs describe-services \
  --cluster prod-cluster \
  --services fastapi-service \
  --query "services[0].events[:5]"

# Execute into running container (like SSH)
aws ecs execute-command \
  --cluster prod-cluster \
  --task <task-id> \
  --container fastapi \
  --interactive \
  --command "/bin/sh"
```

### ECS Service Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id "service/prod-cluster/fastapi-service" \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 20

# Target tracking — keep CPU at 60%
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id "service/prod-cluster/fastapi-service" \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

---

## 8.4 ECS Fargate vs EC2 Launch Type

```
┌──────────────────────────────────────────────────────────┐
│          FARGATE vs EC2 LAUNCH TYPE                      │
├────────────────────────┬─────────────────────────────────┤
│ Fargate                │ EC2                              │
├────────────────────────┼─────────────────────────────────┤
│ No EC2 management      │ You manage EC2 fleet            │
│ Pay per task (CPU+RAM) │ Pay per EC2 instance            │
│ Each task isolated VM  │ Tasks share EC2 instance        │
│ Higher cost/unit       │ Better cost at scale            │
│ No SSH needed          │ Can SSH to EC2 instances        │
│ Scales to zero         │ Min 1 EC2 instance always       │
│ Best for most workloads│ Best for cost optimisation      │
│                        │ at very large scale             │
└────────────────────────┴─────────────────────────────────┘

Use Fargate unless:
- You need GPU instances (not supported on Fargate)
- You need specific EC2 instance types
- Cost is critical at large scale
```

---

## 8.5 EKS — Elastic Kubernetes Service

EKS is managed Kubernetes. AWS manages the control plane (master nodes), you manage worker nodes (or use Fargate).

```
┌──────────────────────────────────────────────────────────┐
│                   EKS ARCHITECTURE                       │
│                                                          │
│  AWS Manages:              You Manage:                   │
│  ─────────────             ───────────                   │
│  Control Plane             Worker Nodes (EC2 or Fargate) │
│  ┌────────────────┐        ┌────────────────────────┐    │
│  │ API Server     │        │ Node Group 1 (m5.large) │   │
│  │ etcd           │  →     │ Node Group 2 (c5.xlarge)│   │
│  │ Scheduler      │        │ Fargate Profile         │   │
│  │ Controller Mgr │        └────────────────────────┘    │
│  └────────────────┘                                      │
│                                                          │
│  Cost: $0.10/hr for control plane + worker node costs   │
└──────────────────────────────────────────────────────────┘
```

```bash
# Install eksctl (recommended EKS CLI)
# https://eksctl.io/

# Create cluster with managed node group
eksctl create cluster \
  --name my-cluster \
  --region us-east-1 \
  --nodegroup-name standard-nodes \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --with-oidc \
  --ssh-access \
  --ssh-public-key my-key-pair

# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name my-cluster

# Verify
kubectl get nodes
kubectl get pods -A
```

### Deploy FastAPI to EKS

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      serviceAccountName: fastapi-sa    # IAM role for service account (IRSA)
      containers:
        - name: fastapi
          image: 123456.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          env:
            - name: ENVIRONMENT
              value: "production"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: password
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
  namespace: production
spec:
  selector:
    app: fastapi-app
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
spec:
  rules:
    - host: api.myapp.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi-service
                port:
                  number: 80
```

```bash
kubectl apply -f k8s/
kubectl get pods -n production
kubectl rollout status deployment/fastapi-app -n production
kubectl rollout undo deployment/fastapi-app -n production  # Rollback
```

---

## 8.6 ECS vs EKS — When to Use Which

```
┌──────────────────────────────────────────────────────────┐
│                  ECS vs EKS                              │
├────────────────────────┬─────────────────────────────────┤
│ ECS + Fargate          │ EKS                              │
├────────────────────────┼─────────────────────────────────┤
│ Simpler to learn       │ More complex                     │
│ AWS-native             │ Cloud-portable (runs anywhere)  │
│ Less YAML              │ More YAML / tooling              │
│ Cheaper small scale    │ Better ecosystem (Helm, etc.)   │
│ Good for most teams    │ Need K8s-specific features       │
│ Faster to get running  │ Already know Kubernetes          │
│                        │ Need Istio, KEDA, etc.          │
└────────────────────────┴─────────────────────────────────┘

If team is new to containers → ECS + Fargate
If team knows Kubernetes → EKS
If portability matters → EKS
```

---

## 8.7 Interview Questions

**Q: What is the difference between ECS and EKS?**
> ECS is AWS's proprietary container orchestration service — simpler to operate, deeply integrated with other AWS services, less operational overhead. EKS is managed Kubernetes — more powerful, portable across clouds, with a huge ecosystem of tools (Helm, Istio, KEDA), but more complex to operate. For teams not already invested in Kubernetes, ECS is usually the better choice.

**Q: What is Fargate and why would you use it?**
> Fargate is serverless compute for containers — you define the task (CPU/RAM requirements) and AWS handles the underlying EC2 instances, patching, and capacity. You pay per task-second rather than per instance-hour. Benefits: no EC2 fleet to manage, each task is isolated, scales to zero, and there are no idle instance costs. Downsides: slightly higher per-unit cost vs EC2, no GPU support, cold start latency.

**Q: How do you deploy a new Docker image to ECS with zero downtime?**
> Update the ECS service with the new task definition revision. ECS performs a rolling deployment by default: it starts new tasks with the new image while the old tasks serve traffic, waits for new tasks to pass health checks, then drains and terminates old tasks. Set `minimumHealthyPercent: 50` and `maximumPercent: 200` to ensure some capacity is always available. Enable deployment circuit breaker to auto-rollback if new tasks fail health checks.
