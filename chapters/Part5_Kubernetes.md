# Part 5: Kubernetes on AWS (EKS)

---

## 8.1 EKS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     EKS Architecture                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AWS Managed Control Plane (API Server, etcd, scheduler)  │   │
│  └─────────────────────────────┬────────────────────────────┘   │
│                                 │                                  │
│  ┌──────────────────────────────▼────────────────────────────┐   │
│  │              Worker Nodes (EC2 / Fargate)                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │ Node Group 1 │  │ Node Group 2 │  │Fargate Profile│   │   │
│  │  │ (on-demand)  │  │ (spot)       │  │(serverless)   │   │   │
│  │  │ m5.xlarge    │  │ m5.xlarge    │  │               │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8.2 EKS Cluster Setup with eksctl

```bash
# Install eksctl
curl --silent --location "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster with managed node groups
eksctl create cluster -f cluster.yaml

# cluster.yaml
cat > cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: myapp-prod
  region: us-east-1
  version: "1.28"
  tags:
    Environment: prod
    ManagedBy: eksctl

iam:
  withOIDC: true    # Enable IRSA (IAM Roles for Service Accounts)

addons:
  - name: vpc-cni
    version: latest
    attachPolicyARNs:
      - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    wellKnownPolicies:
      ebsCSIController: true

managedNodeGroups:
  - name: system
    instanceType: m5.large
    minSize: 2
    maxSize: 4
    desiredCapacity: 2
    privateNetworking: true
    labels:
      workload: system
    taints:
      - key: CriticalAddonsOnly
        value: "true"
        effect: NoSchedule
  
  - name: app-ondemand
    instanceTypes: [m5.xlarge, m5.2xlarge]
    minSize: 2
    maxSize: 20
    desiredCapacity: 3
    privateNetworking: true
    spot: false
    labels:
      workload: application
  
  - name: app-spot
    instanceTypes: [m5.xlarge, m5.2xlarge, m4.xlarge]
    minSize: 0
    maxSize: 30
    desiredCapacity: 0
    privateNetworking: true
    spot: true
    labels:
      workload: batch
    taints:
      - key: spot
        value: "true"
        effect: NoSchedule

fargateProfiles:
  - name: default
    selectors:
      - namespace: fargate-workloads
EOF
```

---

## 8.3 Deploying FastAPI on EKS

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp
  labels:
    name: myapp

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-api
  namespace: myapp
  labels:
    app: orders-api
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orders-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0    # Zero downtime
      maxSurge: 1
  template:
    metadata:
      labels:
        app: orders-api
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: orders-api    # For IRSA
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: orders-api
      
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: orders-api
                topologyKey: kubernetes.io/hostname
      
      containers:
        - name: app
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/orders-api:v1.2.3
          ports:
            - containerPort: 8000
              name: http
          
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi
          
          env:
            - name: ENVIRONMENT
              value: prod
            - name: AWS_REGION
              value: us-east-1
          
          envFrom:
            - secretRef:
                name: orders-api-secrets
            - configMapRef:
                name: orders-api-config
          
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 3
          
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3
          
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            failureThreshold: 30
            periodSeconds: 2
          
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      
      volumes:
        - name: tmp
          emptyDir: {}
      
      terminationGracePeriodSeconds: 60

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: orders-api
  namespace: myapp
spec:
  selector:
    app: orders-api
  ports:
    - name: http
      port: 80
      targetPort: 8000
  type: ClusterIP

---
# k8s/hpa.yaml — Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orders-api
  namespace: myapp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orders-api
  minReplicas: 3
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 5
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
```

---

## 8.4 IAM Roles for Service Accounts (IRSA)

```bash
# Create IAM policy for DynamoDB access
aws iam create-policy \
  --policy-name orders-api-dynamodb \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem","dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/orders-prod"
    }]
  }'

# Create IRSA role
eksctl create iamserviceaccount \
  --cluster myapp-prod \
  --namespace myapp \
  --name orders-api \
  --attach-policy-arn arn:aws:iam::123456789012:policy/orders-api-dynamodb \
  --approve
```

```yaml
# The ServiceAccount with IRSA annotation (created by eksctl)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  namespace: myapp
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/myapp-prod-orders-api
```

---

## 8.5 Ingress with AWS Load Balancer Controller

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: orders-api
  namespace: myapp
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc123
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/load-balancer-attributes: |
      deletion_protection.enabled=true,
      access_logs.s3.enabled=true,
      access_logs.s3.bucket=my-alb-logs
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:123456789012:regional/webacl/myacl/abc
spec:
  rules:
    - host: api.myapp.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: orders-api
                port:
                  number: 80
```

---

## 8.6 Helm Charts for FastAPI

```yaml
# charts/orders-api/values.yaml
replicaCount: 3

image:
  repository: 123456789012.dkr.ecr.us-east-1.amazonaws.com/orders-api
  tag: "v1.2.3"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  hostname: api.myapp.com
  certificateArn: ""

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 50
  targetCPUUtilizationPercentage: 70

env:
  ENVIRONMENT: prod
  AWS_REGION: us-east-1

secrets:
  DATABASE_URL: ""
  SECRET_KEY: ""

serviceAccount:
  create: false
  name: orders-api
  iamRoleArn: ""
```

```bash
# Deploy with Helm
helm install orders-api ./charts/orders-api \
  --namespace myapp \
  --create-namespace \
  --values values-prod.yaml \
  --set image.tag=v1.2.3

# Upgrade
helm upgrade orders-api ./charts/orders-api \
  --namespace myapp \
  --set image.tag=v1.3.0 \
  --atomic \     # Rollback on failure
  --timeout 5m

# Rollback
helm rollback orders-api 1 --namespace myapp
```

---

## 8.7 Interview Q&A

**Q: What is IRSA and why is it preferred over instance profiles for EKS?**
A: IRSA (IAM Roles for Service Accounts) allows individual Kubernetes pods to assume specific IAM roles via projected service account tokens. Each pod gets its own credentials rather than sharing the EC2 instance role. Benefits: (1) Least privilege — each pod has only the permissions it needs; (2) Credential isolation — compromising one pod doesn't expose other pods' credentials; (3) Auditable — CloudTrail shows which service account made API calls; (4) Automatic rotation — credentials are short-lived (1 hour), automatically refreshed. Instance profile gives all pods on a node the same IAM permissions, violating least privilege. Always use IRSA.

**Q: What is the difference between Readiness, Liveness, and Startup probes?**
A: **Readiness probe**: Is the pod ready to receive traffic? Failing readiness removes the pod from Service endpoints (stops routing traffic) but doesn't restart it. Use for: app still initializing, temporarily overloaded, dependencies unavailable. **Liveness probe**: Is the pod alive? Failing liveness restarts the container. Use for: detecting deadlocks, hung processes that won't self-recover. **Startup probe**: Used during container startup. Disables liveness/readiness until the startup probe succeeds. Use for: slow-starting applications (JVM, loading large models). Set `failureThreshold * periodSeconds` to the maximum acceptable startup time. All three use the same httpGet/tcpSocket/exec mechanism.

**Q: How do you achieve zero-downtime deployments on Kubernetes?**
A: (1) `maxUnavailable: 0, maxSurge: 1` in RollingUpdate strategy — always add before removing; (2) `readinessProbe` — ensures traffic only routes to pods that are fully ready; (3) `preStop` hook + `terminationGracePeriodSeconds` — allow in-flight requests to complete before shutdown (FastAPI should handle SIGTERM); (4) `minReadySeconds` — wait before marking pod available; (5) **PodDisruptionBudget** — ensures minimum replicas are available during node drains; (6) **Topology spread constraints** — distribute across AZs so AZ failure doesn't take down all replicas. All six must work together — missing any one can cause downtime.
