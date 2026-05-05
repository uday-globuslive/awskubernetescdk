# Chapter 8: Containers — ECS, EKS, ECR & Fargate
## Container Orchestration, Kubernetes, and Container Registry on AWS

---

## 8.1 Container Services Overview

```
AWS Container Services:
┌──────────────────────────────────────────────────────────────────┐
│ ECR  — Elastic Container Registry                               │
│        Private Docker registry (like Docker Hub, but AWS)       │
├──────────────────────────────────────────────────────────────────┤
│ ECS  — Elastic Container Service                                │
│        AWS-native orchestration (simpler, tighter AWS integration)│
│        Launch types: EC2 or Fargate                             │
├──────────────────────────────────────────────────────────────────┤
│ EKS  — Elastic Kubernetes Service                               │
│        Managed Kubernetes (portable, more complex, industry std) │
│        Node types: Managed Node Groups, Self-managed, Fargate   │
├──────────────────────────────────────────────────────────────────┤
│ Fargate — Serverless compute for containers                     │
│           No EC2 instances to manage                             │
│           Used with both ECS and EKS                             │
└──────────────────────────────────────────────────────────────────┘

Decision Guide:
  Simple workloads, AWS-native → ECS (Fargate)
  Kubernetes expertise, portability → EKS
  Don't want to manage servers → Fargate (with ECS or EKS)
  Cost-optimized, control → EC2 launch type
```

---

## 8.2 ECR — Elastic Container Registry

```bash
# Create private repository
aws ecr create-repository \
  --repository-name my-app \
  --image-tag-mutability IMMUTABLE \  # Prevent tag overwrites (best practice)
  --image-scanning-configuration scanOnPush=true \  # Auto-scan for CVEs
  --encryption-configuration encryptionType=KMS,kmsKey=alias/ecr-key \
  --tags Key=Service,Value=my-app

# Create lifecycle policy (keep only 10 latest images)
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 10 tagged images",
        "selection": {
          "tagStatus": "tagged",
          "tagPrefixList": ["v"],
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": {"type": "expire"}
      },
      {
        "rulePriority": 2,
        "description": "Delete untagged images after 1 day",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 1
        },
        "action": {"type": "expire"}
      }
    ]
  }'

# Set repository policy (cross-account pull)
aws ecr set-repository-policy \
  --repository-name my-app \
  --policy-text '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::987654321098:root"},
      "Action": ["ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:BatchCheckLayerAvailability"]
    }]
  }'

# ── BUILD AND PUSH ─────────────────────────────────────────────
ECR_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app

# Login (token expires in 12 hours)
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin $ECR_URI

# Build, tag, push
docker build -t $ECR_URI:v1.2.3 .
docker push $ECR_URI:v1.2.3

# For CI/CD: tag with git SHA
GIT_SHA=$(git rev-parse --short HEAD)
docker build -t $ECR_URI:$GIT_SHA .
docker push $ECR_URI:$GIT_SHA

# Scan results
aws ecr describe-image-scan-findings \
  --repository-name my-app \
  --image-id imageTag=v1.2.3 \
  --query "imageScanFindings.findings[?severity=='CRITICAL']"
```

---

## 8.3 ECS — Elastic Container Service

### ECS Core Concepts

```
ECS Hierarchy:
  Cluster → multiple services → multiple tasks
  
  Cluster: Logical grouping of tasks/services
  Task Definition: Blueprint (like docker-compose.yml) — CPU, memory, containers, volumes
  Task: Running instance of a task definition (= one or more containers)
  Service: Maintains N running copies of a task, integrates with ALB

  Launch Types:
    EC2:     You manage EC2 instances (Container Instances); more control
    Fargate: AWS manages underlying infra; you just specify CPU/memory
```

### Task Definition

```json
// task-definition.json — full production example
{
  "family": "my-app",
  "taskRoleArn": "arn:aws:iam::123:role/MyAppTaskRole",
  "executionRoleArn": "arn:aws:iam::123:role/ECSTaskExecutionRole",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.2.3",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp",
          "name": "app-port",
          "appProtocol": "http"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "PORT", "value": "8080"}
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123:secret:prod-db-password:password::"
        },
        {
          "name": "API_KEY",
          "valueFrom": "arn:aws:ssm:us-east-1:123:parameter/prod/api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/my-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "resourceRequirements": [],
      "mountPoints": [
        {
          "sourceVolume": "app-data",
          "containerPath": "/data",
          "readOnly": false
        }
      ]
    },
    {
      "name": "fluent-bit",
      "image": "amazon/aws-for-fluent-bit:latest",
      "essential": false,
      "firelensConfiguration": {
        "type": "fluentbit"
      }
    }
  ],
  "volumes": [
    {
      "name": "app-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-0abc123",
        "transitEncryption": "ENABLED",
        "authorizationConfig": {
          "accessPointId": "fsap-0abc123"
        }
      }
    }
  ]
}
```

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS cluster
aws ecs create-cluster \
  --cluster-name prod-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    "capacityProvider=FARGATE,weight=1,base=1" \
    "capacityProvider=FARGATE_SPOT,weight=3"

# Create service with rolling deployment
aws ecs create-service \
  --cluster prod-cluster \
  --service-name my-app \
  --task-definition my-app:5 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIV_SUB_1,$PRIV_SUB_2],
    securityGroups=[$APP_SG],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=app,containerPort=8080" \
  --deployment-configuration "deploymentCircuitBreaker={enable=true,rollback=true},maximumPercent=200,minimumHealthyPercent=50" \
  --deployment-controller type=ECS \
  --enable-execute-command \      # Allow ECS Exec (like SSH into containers)
  --health-check-grace-period-seconds 120 \
  --service-connect-configuration '{
    "enabled": true,
    "namespace": "prod",
    "services": [{"portName": "app-port", "clientAliases": [{"port": 8080}]}]
  }'

# Update service (rolling deploy new task definition)
aws ecs update-service \
  --cluster prod-cluster \
  --service my-app \
  --task-definition my-app:6 \
  --force-new-deployment

# ECS Exec (exec into running container)
aws ecs execute-command \
  --cluster prod-cluster \
  --task arn:aws:ecs:us-east-1:123:task/prod-cluster/abc123 \
  --container app \
  --interactive \
  --command "/bin/bash"
```

### ECS Auto Scaling

```bash
# Register service as scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/prod-cluster/my-app \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 50

# Scale on CPU utilization
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/prod-cluster/my-app \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    "TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization},ScaleInCooldown=300,ScaleOutCooldown=60"

# Scale on ALB request count per target
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/prod-cluster/my-app \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name request-count-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 1000.0,
    "CustomizedMetricSpecification": {
      "MetricName": "RequestCountPerTarget",
      "Namespace": "AWS/ApplicationELB",
      "Dimensions": [{"Name": "TargetGroup", "Value": "targetgroup/my-tg/abc"}],
      "Statistic": "Sum",
      "Unit": "Count"
    }
  }'
```

### Blue/Green Deployment with CodeDeploy

```bash
# Create CodeDeploy application
aws deploy create-application \
  --application-name MyECSApp \
  --compute-platform ECS

# Create deployment group
aws deploy create-deployment-group \
  --application-name MyECSApp \
  --deployment-group-name MyECSDeployGroup \
  --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
  --ecs-services "serviceName=my-app,clusterName=prod-cluster" \
  --load-balancer-info "targetGroupPairInfoList=[{
    targetGroups:[
      {name=blue-tg},
      {name=green-tg}
    ],
    prodTrafficRoute:{listenerArns:[arn:aws:...alb-listener]},
    testTrafficRoute:{listenerArns:[arn:aws:...test-listener]}
  }]" \
  --service-role-arn arn:aws:iam::123:role/CodeDeployECSRole

# AppSpec file for ECS Blue/Green
cat > appspec.yaml << 'EOF'
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: app
          ContainerPort: 8080
        PlatformVersion: LATEST
Hooks:
  - BeforeInstall: ValidateBeforeInstall
  - AfterInstall: ValidateAfterInstall  
  - AfterAllowTestTraffic: RunTests
  - BeforeAllowTraffic: ValidateBeforeAllowTraffic
  - AfterAllowTraffic: ValidateAfterAllowTraffic
EOF
```

---

## 8.4 EKS — Elastic Kubernetes Service

### EKS Architecture

```
EKS Cluster:
┌───────────────────────────────────────────────────────────────┐
│                    EKS Control Plane (AWS managed)            │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  API Server   │  │  etcd        │  │  Scheduler/      │  │
│  │  (kube-api)   │  │  (state)     │  │  Controller Mgr  │  │
│  └───────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Manages
                              ▼
┌──────────────────────────────────────────────────────────────┐
│              Worker Nodes (Data Plane — you manage)          │
│  ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │  Node Group 1 (EC2)  │    │  Node Group 2 (Fargate)  │   │
│  │  ┌───────┐ ┌───────┐ │    │  ┌───────┐ ┌───────┐    │   │
│  │  │ Pod   │ │ Pod   │ │    │  │ Pod   │ │ Pod   │    │   │
│  │  │(App)  │ │(App)  │ │    │  │       │ │       │    │   │
│  │  └───────┘ └───────┘ │    │  └───────┘ └───────┘    │   │
│  └──────────────────────┘    └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Create EKS Cluster

```bash
# Install eksctl (recommended tool)
choco install eksctl  # Windows
brew install eksctl   # Mac

# Create cluster with eksctl (simplest approach)
eksctl create cluster \
  --name prod-cluster \
  --region us-east-1 \
  --version 1.28 \
  --nodegroup-name standard-workers \
  --node-type m6i.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \      # Managed node group (AWS patches nodes)
  --asg-access \   # Add IAM for cluster autoscaler
  --external-dns-access \
  --full-ecr-access \
  --alb-ingress-access \
  --with-oidc     # Enable IRSA (IAM Roles for Service Accounts)

# OR with full config file:
cat > cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: prod-cluster
  region: us-east-1
  version: "1.28"

iam:
  withOIDC: true

managedNodeGroups:
  - name: general-workers
    instanceType: m6i.xlarge
    minSize: 2
    maxSize: 20
    desiredCapacity: 3
    privateNetworking: true
    labels:
      role: general
    taints:
      - key: dedicated
        value: general
        effect: NoSchedule
    iam:
      attachPolicyARNs:
        - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
        - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
        - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

  - name: spot-workers
    instanceTypes: ["m6i.xlarge", "m5.xlarge", "m5a.xlarge"]
    spot: true
    minSize: 0
    maxSize: 50
    desiredCapacity: 5
    labels:
      role: spot

fargateProfiles:
  - name: system-profile
    selectors:
      - namespace: kube-system
        labels:
          compute-type: fargate
      - namespace: monitoring

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    wellKnownPolicies:
      ebsCSIController: true
EOF

eksctl create cluster -f cluster.yaml
```

### IRSA — IAM Roles for Service Accounts

IRSA allows Kubernetes pods to assume AWS IAM roles without node-level credentials:

```bash
# Create IAM role for pod
eksctl create iamserviceaccount \
  --cluster prod-cluster \
  --namespace default \
  --name my-app-sa \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --attach-policy-arn arn:aws:iam::123:policy/custom-policy \
  --approve

# The above creates:
# 1. IAM role with trust policy allowing the service account
# 2. Kubernetes service account annotated with IAM role ARN
```

```yaml
# Kubernetes deployment using IRSA
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app-sa  # Uses IRSA
      containers:
        - name: app
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.2.3
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          env:
            - name: AWS_REGION
              value: us-east-1
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 30
```

### Cluster Autoscaler

```bash
# Deploy Cluster Autoscaler
cat > cluster-autoscaler.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
        - name: cluster-autoscaler
          image: registry.k8s.io/autoscaling/cluster-autoscaler:v1.28.0
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/prod-cluster
            - --balance-similar-node-groups
            - --scale-down-enabled=true
            - --scale-down-delay-after-add=10m
            - --scale-down-unneeded-time=10m
EOF

kubectl apply -f cluster-autoscaler.yaml
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 50
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
    - type: External
      external:
        metric:
          name: sqs_queue_depth
          selector:
            matchLabels:
              queue: orders-queue
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scale down
    scaleUp:
      stabilizationWindowSeconds: 30
```

### AWS Load Balancer Controller

```bash
# Install AWS Load Balancer Controller
eksctl create iamserviceaccount \
  --cluster prod-cluster \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --attach-policy-arn arn:aws:iam::123:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=prod-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

```yaml
# Ingress resource (creates ALB)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123:certificate/abc
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/group.name: prod-alb-group  # Share ALB across services
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app-service
                port:
                  number: 8080
    - host: admin.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: admin-service
                port:
                  number: 3000
```

---

## 8.5 EKS — Useful Day-2 Operations

```bash
# Update kubeconfig
aws eks update-kubeconfig --name prod-cluster --region us-east-1

# Check cluster
kubectl get nodes -o wide
kubectl get pods -A   # All namespaces

# Check pod logs
kubectl logs -f pod-name -c container-name
kubectl logs --previous pod-name  # Previous container logs (crashed)

# Exec into pod
kubectl exec -it pod-name -- /bin/bash

# Port forward (test services locally)
kubectl port-forward svc/my-app-service 8080:8080

# Apply with kustomize
kubectl apply -k overlays/production/

# Rolling restart
kubectl rollout restart deployment/my-app

# Check rollout status
kubectl rollout status deployment/my-app

# Rollback
kubectl rollout undo deployment/my-app
kubectl rollout undo deployment/my-app --to-revision=3

# Scale manually
kubectl scale deployment my-app --replicas=10

# Node drain (for maintenance)
kubectl drain node-name --ignore-daemonsets --delete-emptydir-data

# Resource usage
kubectl top nodes
kubectl top pods

# Upgrade cluster (via eksctl)
eksctl upgrade cluster --name prod-cluster --approve
eksctl upgrade nodegroup --cluster prod-cluster --name standard-workers
```

---

## 8.6 EKS — Storage with EBS CSI Driver

```yaml
# StorageClass — EBS gp3
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-east-1:123:key/abc

---
# PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 100Gi

---
# Use in deployment
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: app-data
volumeMounts:
  - name: data
    mountPath: /data
```

---

## 8.7 Container Security Best Practices

```dockerfile
# Secure Dockerfile best practices
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

# Don't run as root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy only installed packages
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser src/ .

USER appuser

# Expose non-privileged port
EXPOSE 8080

# Read-only filesystem (override with volumes for writable dirs)
# Set in ECS task definition: readonlyRootFilesystem=true

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# Scan image for vulnerabilities
aws ecr start-image-scan \
  --repository-name my-app \
  --image-id imageTag=v1.2.3

# Enhanced scanning (with Amazon Inspector)
aws ecr put-registry-scanning-configuration \
  --scan-type ENHANCED \
  --rules '[{
    "repositoryFilters": [{"filter": "*", "filterType": "WILDCARD"}],
    "scanFrequency": "CONTINUOUS_SCAN"
  }]'
```

---

## 8.8 Interview Q&A

**Q: What is the difference between ECS and EKS?**
A: ECS is AWS's native container orchestration with deep AWS integration (simpler to operate, lower overhead). EKS is managed Kubernetes — industry standard, portable across clouds/on-prem, larger ecosystem of tools, but more complex. Choose ECS when: AWS-only, team unfamiliar with Kubernetes, want simplicity. Choose EKS when: Kubernetes expertise, need portability, have complex orchestration needs, or migrating existing K8s workloads.

**Q: What is Fargate and when would you use it?**
A: Fargate is serverless compute for containers — you define CPU/memory; AWS manages the underlying EC2 infrastructure. Use Fargate when: you don't want to manage EC2 instances, you have variable workloads, you want per-container billing, you prefer simplicity. Use EC2 launch type when: you need specific instance types (GPU), you want to control OS/kernel settings, you're cost-optimizing predictable workloads (Savings Plans), or you need host networking mode.

**Q: What is IRSA and why is it important?**
A: IRSA (IAM Roles for Service Accounts) maps Kubernetes service accounts to IAM roles using OIDC federation. This allows individual pods to have minimal AWS permissions without giving all pods on a node the same IAM role. Security benefit: least-privilege per application instead of per-node. Replaces the older approach of attaching IAM policies to EC2 node instance profiles.

**Q: How do you do zero-downtime deployments with ECS?**
A: Configure the ECS service with `minimumHealthyPercent=50` (or 100%) and `maximumPercent=200`. ECS launches new tasks first (up to 200%), waits for them to pass load balancer health checks, then terminates old tasks. Add `deregistrationDelay` on the target group for graceful connection draining. Use deployment circuit breaker to auto-rollback failed deployments. For canary, use CodeDeploy blue/green with traffic shifting.

**Q: What is the Kubernetes Horizontal Pod Autoscaler?**
A: HPA automatically scales the number of pod replicas based on CPU utilization, memory, or custom metrics. It periodically queries the metrics API and compares against targets. HPA works with Cluster Autoscaler: HPA adds more pods → Cluster Autoscaler adds more nodes if capacity exhausted. Configure stabilization windows to prevent flapping (rapidly scaling up and down).

**Q: What is a DaemonSet in Kubernetes?**
A: A DaemonSet ensures that a pod runs on every node (or a subset of nodes matching labels/taints). Common uses: log collection agent (Fluent Bit), monitoring agent (CloudWatch agent), network plugin (VPC CNI), node problem detector. When a new node is added, the DaemonSet controller automatically adds the pod to the new node.

**Q: How do you manage secrets in Kubernetes on EKS?**
A: Several approaches: (1) AWS Secrets Manager + Secrets Store CSI Driver — mounts secrets as files or env vars, auto-rotates; (2) External Secrets Operator — syncs from Secrets Manager/SSM to Kubernetes Secrets; (3) IRSA + boto3 in application code — fetch secrets at startup from Secrets Manager directly. Never commit secrets to code or store in plain ConfigMaps.
