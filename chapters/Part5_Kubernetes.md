# Part V: Kubernetes and Amazon EKS
## Complete Beginner's Guide

---

# Chapter 26: Kubernetes Fundamentals

## 26.1 What is Kubernetes?

### The Problem Kubernetes Solves

```
Without Kubernetes (Manual Management):
┌─────────────────────────────────────────────────────────┐
│  You manage:                                            │
│  ✗ Which server runs which container?                   │
│  ✗ What if a server crashes?                            │
│  ✗ How to scale up during traffic spikes?               │
│  ✗ How to update without downtime?                      │
│  ✗ How to handle service discovery?                     │
└─────────────────────────────────────────────────────────┘

With Kubernetes (Automated):
┌─────────────────────────────────────────────────────────┐
│  You declare: "I want 3 instances of my app"            │
│                                                         │
│  Kubernetes handles:                                    │
│  ✓ Placing containers on available nodes                │
│  ✓ Restarting crashed containers                        │
│  ✓ Scaling up/down automatically                        │
│  ✓ Rolling updates with zero downtime                   │
│  ✓ Service discovery and load balancing                 │
└─────────────────────────────────────────────────────────┘
```

### Kubernetes in Simple Terms

**Analogy: Orchestra Conductor**

```
Orchestra (Your Application):
├── Violin section (Web servers)
├── Brass section (Database)
├── Percussion (Cache)
└── Woodwinds (Background workers)

Conductor (Kubernetes):
- Ensures each section has the right number of musicians
- Replaces musicians who leave mid-performance
- Coordinates timing between sections
- Manages the overall performance
```

---

## 26.2 Kubernetes Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KUBERNETES CLUSTER                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    CONTROL PLANE                         │    │
│  │  (The "Brain" - Manages the cluster)                     │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│  │  │  API Server  │  │  Scheduler   │  │  Controller  │   │    │
│  │  │              │  │              │  │   Manager    │   │    │
│  │  │  kubectl ────┼──│ Where to run │  │  Maintains   │   │    │
│  │  │  commands go │  │    pods?     │  │  desired     │   │    │
│  │  │  here        │  │              │  │  state       │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │                     etcd                          │   │    │
│  │  │   (Database storing all cluster state/config)    │   │    │
│  │  └──────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                               │                                  │
│                               ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     WORKER NODES                         │    │
│  │  (The "Muscles" - Run your applications)                 │    │
│  │                                                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐               │    │
│  │  │    Node 1       │  │    Node 2       │               │    │
│  │  │  ┌───────────┐  │  │  ┌───────────┐  │               │    │
│  │  │  │  kubelet  │  │  │  │  kubelet  │  │               │    │
│  │  │  │  (agent)  │  │  │  │  (agent)  │  │               │    │
│  │  │  └───────────┘  │  │  └───────────┘  │               │    │
│  │  │  ┌───────────┐  │  │  ┌───────────┐  │               │    │
│  │  │  │  Pod A    │  │  │  │  Pod C    │  │               │    │
│  │  │  │  Pod B    │  │  │  │  Pod D    │  │               │    │
│  │  │  └───────────┘  │  │  └───────────┘  │               │    │
│  │  └─────────────────┘  └─────────────────┘               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 26.3 Core Concepts

### Pod - The Smallest Unit

```
A Pod is one or more containers that:
- Share the same network (localhost)
- Share the same storage
- Are scheduled together

Simple Pod:
┌─────────────────────────┐
│          Pod            │
│  ┌───────────────────┐  │
│  │  Container        │  │
│  │  (your-app)       │  │
│  └───────────────────┘  │
│         IP: 10.0.0.5    │
└─────────────────────────┘

Multi-container Pod:
┌─────────────────────────┐
│          Pod            │
│  ┌─────────┐ ┌───────┐  │
│  │   App   │ │ Sidecar│  │
│  │Container│ │(logging)│ │
│  └─────────┘ └───────┘  │
│     Share localhost     │
│      IP: 10.0.0.6       │
└─────────────────────────┘
```

### Deployment - Manages Pods

```
Deployment: "Keep 3 replicas of my app running"

┌──────────────────────────────────────┐
│             Deployment               │
│  replicas: 3                         │
│                                      │
│    ┌─────┐  ┌─────┐  ┌─────┐        │
│    │ Pod │  │ Pod │  │ Pod │        │
│    │  1  │  │  2  │  │  3  │        │
│    └─────┘  └─────┘  └─────┘        │
│                                      │
│  If Pod 2 crashes:                   │
│    ┌─────┐  ┌─────┐  ┌─────┐        │
│    │ Pod │  │ NEW │  │ Pod │        │
│    │  1  │  │ Pod │  │  3  │        │
│    └─────┘  └─────┘  └─────┘        │
│                                      │
│  Kubernetes automatically replaces   │
└──────────────────────────────────────┘
```

### Service - Networking

```
Problem: Pod IPs change when pods restart
Solution: Service provides stable endpoint

┌──────────────────────────────────────┐
│              Service                  │
│        (my-service:80)               │
│         Stable IP/DNS                │
└──────────────────┬───────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    ┌─────┐    ┌─────┐    ┌─────┐
    │Pod 1│    │Pod 2│    │Pod 3│
    │10.0.│    │10.0.│    │10.0.│
    │0.5  │    │0.6  │    │0.7  │
    └─────┘    └─────┘    └─────┘

Access: http://my-service:80
Service load balances to healthy pods
```

---

## 26.4 YAML Files - Kubernetes Language

### Basic Pod YAML

```yaml
# my-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  containers:
    - name: my-app
      image: my-app:1.0
      ports:
        - containerPort: 8000
```

### Deployment YAML

```yaml
# deployment.yaml
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
      containers:
        - name: my-app
          image: my-app:1.0
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "64Mi"
              cpu: "250m"
            limits:
              memory: "128Mi"
              cpu: "500m"
```

### Service YAML

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
spec:
  selector:
    app: my-app
  ports:
    - port: 80           # Service port
      targetPort: 8000   # Container port
  type: LoadBalancer     # External access
```

---

## 26.5 kubectl - Kubernetes CLI

### Essential Commands

```bash
# Cluster info
kubectl cluster-info
kubectl get nodes

# Pods
kubectl get pods                    # List pods
kubectl get pods -o wide           # With more details
kubectl describe pod <pod-name>    # Full details
kubectl logs <pod-name>            # View logs
kubectl logs -f <pod-name>         # Stream logs
kubectl exec -it <pod-name> -- bash # Shell into pod

# Deployments
kubectl get deployments
kubectl describe deployment <name>
kubectl scale deployment <name> --replicas=5
kubectl rollout status deployment <name>
kubectl rollout history deployment <name>
kubectl rollout undo deployment <name>

# Services
kubectl get services
kubectl describe service <name>

# Apply YAML files
kubectl apply -f deployment.yaml
kubectl apply -f ./k8s/            # Apply entire directory

# Delete resources
kubectl delete pod <pod-name>
kubectl delete -f deployment.yaml

# Get all resources
kubectl get all
kubectl get all -n <namespace>     # Specific namespace
```

---

# Chapter 27: Kubernetes Workloads

## 27.1 Deployment vs StatefulSet vs DaemonSet

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKLOAD TYPES                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  DEPLOYMENT (Most common)                                    │
│  ├── Stateless applications                                  │
│  ├── Pods are interchangeable                                │
│  └── Use for: Web servers, APIs                              │
│                                                              │
│  STATEFULSET                                                 │
│  ├── Stateful applications                                   │
│  ├── Pods have stable identity (pod-0, pod-1, pod-2)        │
│  ├── Persistent storage per pod                              │
│  └── Use for: Databases, Kafka, Redis                        │
│                                                              │
│  DAEMONSET                                                   │
│  ├── One pod per node                                        │
│  ├── For cluster-wide services                               │
│  └── Use for: Log collectors, monitoring agents              │
│                                                              │
│  JOB / CRONJOB                                               │
│  ├── Run-to-completion tasks                                 │
│  └── Use for: Batch processing, scheduled tasks              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 27.2 StatefulSet Example

```yaml
# For databases with persistent storage
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

---

## 27.3 DaemonSet Example

```yaml
# Log collector on every node
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      containers:
        - name: fluentd
          image: fluentd:latest
          volumeMounts:
            - name: varlog
              mountPath: /var/log
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
```

---

## 27.4 Job and CronJob

```yaml
# One-time job
apiVersion: batch/v1
kind: Job
metadata:
  name: data-migration
spec:
  template:
    spec:
      containers:
        - name: migration
          image: my-app:latest
          command: ["python", "migrate.py"]
      restartPolicy: Never
  backoffLimit: 3  # Retry 3 times on failure

---
# Scheduled job (CronJob)
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: backup-tool:latest
          restartPolicy: OnFailure
```

---

# Chapter 28: Networking in Kubernetes

## 28.1 Service Types

```
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE TYPES                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ClusterIP (Default)                                         │
│  ├── Internal cluster access only                            │
│  └── Use for: Internal services                              │
│                                                              │
│  NodePort                                                    │
│  ├── Exposes on each node's IP at a static port             │
│  ├── Range: 30000-32767                                      │
│  └── Use for: Development, direct node access                │
│                                                              │
│  LoadBalancer                                                │
│  ├── External load balancer (cloud provider)                 │
│  └── Use for: Production external access                     │
│                                                              │
│  ExternalName                                                │
│  ├── Maps to external DNS name                               │
│  └── Use for: External database access                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Service Examples

```yaml
# ClusterIP - Internal only
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
    - port: 80
      targetPort: 8000

---
# LoadBalancer - External access
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 3000
```

---

## 28.2 Ingress

Ingress manages external HTTP/HTTPS access with routing rules.

```
                     ┌─────────────────┐
    Internet ──────▶ │    Ingress      │
                     │   Controller    │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        /api/*          /web/*          /admin/*
              │               │               │
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │   API   │     │   Web   │     │  Admin  │
        │ Service │     │ Service │     │ Service │
        └─────────┘     └─────────┘     └─────────┘
```

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
  tls:
    - hosts:
        - myapp.example.com
      secretName: tls-secret
```

---

# Chapter 29: Storage in Kubernetes

## 29.1 Volumes and Persistent Storage

```
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE CONCEPTS                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Volume                                                      │
│  └── Storage attached to a pod                               │
│      ├── emptyDir: Temporary, deleted with pod               │
│      ├── hostPath: Node's filesystem                         │
│      └── configMap/secret: Configuration data                │
│                                                              │
│  PersistentVolume (PV)                                       │
│  └── Cluster-wide storage resource                           │
│      ├── Created by admin or dynamically                     │
│      └── Independent of pod lifecycle                        │
│                                                              │
│  PersistentVolumeClaim (PVC)                                 │
│  └── Request for storage by a pod                            │
│      ├── "I need 10GB of storage"                            │
│      └── Kubernetes finds/creates a PV                       │
│                                                              │
│  StorageClass                                                │
│  └── Defines how to provision storage                        │
│      ├── gp2 (AWS EBS)                                       │
│      ├── standard (GCE PD)                                   │
│      └── Enables dynamic provisioning                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Storage Example

```yaml
# PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: gp2

---
# Use in Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-storage
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:latest
          volumeMounts:
            - name: data
              mountPath: /app/data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: data-pvc
```

---

# Chapter 30: Amazon EKS

## 30.1 What is EKS?

Amazon Elastic Kubernetes Service (EKS) is managed Kubernetes on AWS.

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS MANAGES                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                CONTROL PLANE                          │   │
│  │   API Server, etcd, Scheduler, Controller Manager    │   │
│  │   (Highly available, across 3 AZs)                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    YOU MANAGE                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                WORKER NODES                          │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐        │    │
│  │  │   EC2     │  │   EC2     │  │   EC2     │        │    │
│  │  │ instance  │  │ instance  │  │ instance  │        │    │
│  │  └───────────┘  └───────────┘  └───────────┘        │    │
│  │                                                      │    │
│  │  Or: AWS Fargate (serverless nodes)                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 30.2 Creating EKS with CDK

```python
from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct

class EKSStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # VPC
        vpc = ec2.Vpc(
            self, "EksVpc",
            max_azs=3,
            nat_gateways=1
        )
        
        # EKS Cluster
        cluster = eks.Cluster(
            self, "MyCluster",
            cluster_name="my-cluster",
            vpc=vpc,
            version=eks.KubernetesVersion.V1_28,
            default_capacity=0,  # We'll add node groups
        )
        
        # Managed Node Group
        cluster.add_nodegroup_capacity(
            "WorkerNodes",
            instance_types=[ec2.InstanceType("t3.medium")],
            min_size=2,
            max_size=10,
            desired_size=3,
            disk_size=50,
            ami_type=eks.NodegroupAmiType.AL2_X86_64,
        )
        
        # Fargate Profile (serverless nodes)
        cluster.add_fargate_profile(
            "FargateProfile",
            selectors=[
                eks.Selector(namespace="serverless")
            ]
        )
```

---

# Chapter 31: Deploying FastAPI on Kubernetes

## 31.1 Complete FastAPI K8s Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Run with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Manifests

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fastapi

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fastapi-config
  namespace: fastapi
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: fastapi-secrets
  namespace: fastapi
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXNxbDovL3VzZXI6cGFzc0Bob3N0L2Ri  # base64

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
  namespace: fastapi
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
        - name: fastapi
          image: 123456789.dkr.ecr.us-east-1.amazonaws.com/fastapi:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: fastapi-config
            - secretRef:
                name: fastapi-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi
  namespace: fastapi
spec:
  selector:
    app: fastapi
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi
  namespace: fastapi
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi
                port:
                  number: 80

---
# k8s/hpa.yaml (Horizontal Pod Autoscaler)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-hpa
  namespace: fastapi
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

# Chapter 32: Kubernetes Security

## 32.1 RBAC (Role-Based Access Control)

```yaml
# Role - defines permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: fastapi
  name: developer
rules:
  - apiGroups: [""]
    resources: ["pods", "services"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "update"]

---
# RoleBinding - assigns role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: fastapi
subjects:
  - kind: User
    name: john@example.com
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

## 32.2 Network Policies

```yaml
# Only allow traffic from specific pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
  namespace: fastapi
spec:
  podSelector:
    matchLabels:
      app: database
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: fastapi
      ports:
        - port: 5432
```

---

# Chapter 33: Helm and GitOps

## 33.1 Helm Charts

Helm is a package manager for Kubernetes.

```
my-fastapi-chart/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
```

```yaml
# Chart.yaml
apiVersion: v2
name: fastapi
version: 1.0.0
description: FastAPI application

# values.yaml
replicaCount: 3
image:
  repository: my-registry/fastapi
  tag: latest
service:
  type: ClusterIP
  port: 80
resources:
  limits:
    cpu: 500m
    memory: 512Mi

# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
        - name: fastapi
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

### Helm Commands

```bash
# Install chart
helm install my-api ./my-fastapi-chart

# Install with custom values
helm install my-api ./my-fastapi-chart -f production-values.yaml

# Upgrade
helm upgrade my-api ./my-fastapi-chart

# Rollback
helm rollback my-api 1

# List releases
helm list

# Uninstall
helm uninstall my-api
```

## 33.2 GitOps with ArgoCD

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fastapi
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/fastapi-k8s
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: fastapi
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

*Continue to Part 6 for Interview Preparation...*
