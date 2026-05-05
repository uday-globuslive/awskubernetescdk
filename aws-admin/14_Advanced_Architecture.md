# Chapter 14: Advanced Architecture — Well-Architected, DR, High Availability & Resilience
## Enterprise Patterns, Disaster Recovery, Chaos Engineering & Architecture Best Practices

---

## 14.1 AWS Well-Architected Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│              6 PILLARS OF WELL-ARCHITECTED                          │
├──────────────────────┬──────────────────────────────────────────────┤
│ Operational          │ Run and monitor systems to deliver business  │
│ Excellence           │ value and continually improve processes      │
│                      │ Key: IaC, observability, small changes,      │
│                      │ runbooks, post-mortems                       │
├──────────────────────┼──────────────────────────────────────────────┤
│ Security             │ Protect information, systems, and assets     │
│                      │ Key: Defense in depth, least privilege,      │
│                      │ encryption everywhere, traceability          │
├──────────────────────┼──────────────────────────────────────────────┤
│ Reliability          │ Recover from failures, meet demand           │
│                      │ Key: Multi-AZ, auto-scaling, retries,        │
│                      │ circuit breakers, chaos testing              │
├──────────────────────┼──────────────────────────────────────────────┤
│ Performance          │ Use resources efficiently at current and     │
│ Efficiency           │ future demand levels                         │
│                      │ Key: Serverless, CDN, caching, right-sizing  │
├──────────────────────┼──────────────────────────────────────────────┤
│ Cost                 │ Avoid unnecessary costs and optimize spend   │
│ Optimization         │ Key: Savings Plans, spot, auto-scaling,      │
│                      │ eliminate unused resources                   │
├──────────────────────┼──────────────────────────────────────────────┤
│ Sustainability       │ Minimize environmental impacts               │
│                      │ Key: Efficient utilization, managed services,│
│                      │ right-sizing, scheduled capacity             │
└──────────────────────┴──────────────────────────────────────────────┘
```

```bash
# Use the Well-Architected Tool
aws wellarchitected create-workload \
  --workload-name "e-commerce-platform" \
  --description "Production e-commerce platform" \
  --review-owner "platform-team@company.com" \
  --environment PRODUCTION \
  --aws-regions us-east-1 us-west-2 \
  --lenses wellarchitected serverless

# Start review
WORKLOAD_ID=$(aws wellarchitected list-workloads --query "WorkloadSummaries[0].WorkloadId" --output text)

aws wellarchitected list-lens-review-improvements \
  --workload-id $WORKLOAD_ID \
  --lens-alias wellarchitected \
  --pillar-id reliability
```

---

## 14.2 Disaster Recovery Strategies

### RPO and RTO

```
RPO (Recovery Point Objective): Maximum acceptable data loss
RTO (Recovery Time Objective): Maximum acceptable downtime

DR Strategy Comparison:
┌────────────────────────────────────────────────────────────────────────────────┐
│ Strategy          │ RPO      │ RTO       │ Cost  │ Description                 │
├───────────────────┼──────────┼───────────┼───────┼─────────────────────────────┤
│ Backup & Restore  │ Hours    │ Hours     │ $     │ Backups to S3, restore when │
│                   │          │           │       │ disaster occurs             │
├───────────────────┼──────────┼───────────┼───────┼─────────────────────────────┤
│ Pilot Light       │ Minutes  │ 10-60min  │ $$    │ Core systems running (DB    │
│                   │          │           │       │ replica), others off until  │
│                   │          │           │       │ disaster (scale up)         │
├───────────────────┼──────────┼───────────┼───────┼─────────────────────────────┤
│ Warm Standby      │ Seconds  │ Minutes   │ $$$   │ Scaled-down but fully       │
│                   │          │           │       │ functional copy running     │
├───────────────────┼──────────┼───────────┼───────┼─────────────────────────────┤
│ Multi-Site Active │ Near 0   │ Seconds   │ $$$$  │ Two identical prod          │
│ Active            │          │           │       │ environments, both serving  │
│                   │          │           │       │ traffic simultaneously      │
└───────────────────┴──────────┴───────────┴───────┴─────────────────────────────┘
```

### Multi-Region Active-Active Architecture

```
                        ┌─────────────────────────────────────┐
                        │           Route 53                   │
                        │      Latency-based routing           │
                        │    + Health checks + Failover        │
                        └───────────┬──────────────────────────┘
                                    │
              ┌─────────────────────┴──────────────────────┐
              │                                             │
    ┌─────────▼──────────┐                      ┌──────────▼─────────┐
    │    us-east-1       │                      │    eu-west-1       │
    │                    │                      │                    │
    │  ┌──────────────┐  │                      │  ┌──────────────┐  │
    │  │  CloudFront  │  │                      │  │  CloudFront  │  │
    │  └──────┬───────┘  │                      │  └──────┬───────┘  │
    │         │          │                      │         │          │
    │  ┌──────▼───────┐  │                      │  ┌──────▼───────┐  │
    │  │    ALB       │  │                      │  │    ALB       │  │
    │  └──────┬───────┘  │                      │  └──────┬───────┘  │
    │         │          │                      │         │          │
    │  ┌──────▼───────┐  │                      │  ┌──────▼───────┐  │
    │  │ ECS Service  │  │                      │  │ ECS Service  │  │
    │  └──────┬───────┘  │                      │  └──────┬───────┘  │
    │         │          │                      │         │          │
    │  ┌──────▼───────┐  │    ←  Replication →  │  ┌──────▼───────┐  │
    │  │Aurora Global │◄─┼──────────────────────┼─►│Aurora Global │  │
    │  │  (Primary)   │  │                      │  │ (Secondary)  │  │
    │  └──────────────┘  │                      │  └──────────────┘  │
    │                    │                      │                    │
    │  ┌──────────────┐  │    ←  Replication →  │  ┌──────────────┐  │
    │  │  DynamoDB    │◄─┼──────────────────────┼─►│  DynamoDB    │  │
    │  │ Global Table │  │                      │  │ Global Table │  │
    │  └──────────────┘  │                      │  └──────────────┘  │
    └────────────────────┘                      └────────────────────┘
```

### DR Implementation

```bash
# Aurora Global Database — cross-region replication
aws rds create-global-cluster \
  --global-cluster-identifier my-global-db \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:123:cluster:prod-aurora \
  --deletion-protection

# Add secondary region
aws rds create-db-cluster \
  --db-cluster-identifier prod-aurora-eu \
  --global-cluster-identifier my-global-db \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --db-subnet-group-name eu-db-subnet-group \
  --vpc-security-group-ids sg-eu-db \
  --region eu-west-1

# Failover Aurora Global Database (planned — low impact)
aws rds failover-global-cluster \
  --global-cluster-identifier my-global-db \
  --target-db-cluster-identifier arn:aws:rds:eu-west-1:123:cluster:prod-aurora-eu

# DynamoDB Global Tables (multi-region active-active)
aws dynamodb create-table \
  --table-name orders \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

aws dynamodb create-global-table \
  --global-table-name orders \
  --replication-group '[
    {"RegionName": "us-east-1"},
    {"RegionName": "eu-west-1"},
    {"RegionName": "ap-southeast-1"}
  ]'

# Route53 failover routing
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123 \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "primary-us-east-1",
          "Failover": "PRIMARY",
          "HealthCheckId": "health-check-us-east-1",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "us-east-1-alb.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "secondary-eu-west-1",
          "Failover": "SECONDARY",
          "AliasTarget": {
            "HostedZoneId": "Z2IFOLAFXWLO4F",
            "DNSName": "eu-west-1-alb.eu-west-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

---

## 14.3 High Availability Design Patterns

### Circuit Breaker Pattern

```python
import time
import functools
from enum import Enum
from threading import Lock

class CircuitState(Enum):
    CLOSED = "CLOSED"     # Normal — requests pass through
    OPEN = "OPEN"         # Failing — requests blocked
    HALF_OPEN = "HALF_OPEN"  # Testing — limited requests allowed

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, half_open_requests=3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.half_open_count = 0
        self._lock = Lock()
    
    def call(self, func, *args, **kwargs):
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_count = 0
                else:
                    raise Exception(f"Circuit OPEN — service unavailable")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_count >= self.half_open_requests:
                    raise Exception("Circuit HALF_OPEN — max probe requests reached")
        
        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.half_open_count += 1
                    if self.half_open_count >= self.half_open_requests:
                        self._reset()   # Close circuit — service recovered
                else:
                    self._reset()
            return result
        
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
            raise
    
    def _reset(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

# Usage
payment_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

def charge_customer(order_id: str, amount: float):
    return payment_breaker.call(_call_payment_api, order_id, amount)
```

### Retry with Exponential Backoff

```python
import random
import time
from functools import wraps
from botocore.exceptions import ClientError

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=32.0, 
                       retryable_errors=None):
    """Decorator for retry with exponential backoff and jitter."""
    if retryable_errors is None:
        retryable_errors = ['ThrottlingException', 'ProvisionedThroughputExceededException',
                           'RequestLimitExceeded', 'ServiceUnavailable', 'InternalError']
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if attempt == max_retries or error_code not in retryable_errors:
                        raise
                    
                    # Exponential backoff with full jitter
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    jitter = random.uniform(0, delay)
                    print(f"Attempt {attempt+1} failed ({error_code}), retrying in {jitter:.2f}s")
                    time.sleep(jitter)
                except Exception:
                    raise
            return None
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def put_item_with_retry(table, item):
    return table.put_item(Item=item)
```

---

## 14.4 Event-Driven Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│              EVENT-DRIVEN ARCHITECTURE ON AWS                        │
│                                                                      │
│  Producers:                     Consumers:                           │
│    Web API        ──► SQS ──►  Order Processor                      │
│    Mobile App     ──► SNS ──►  Notification Service                  │
│    IoT Devices    ──► Kinesis ► Analytics Pipeline                   │
│    Scheduled Task ──► EventBridge ► Multiple handlers               │
│                                                                      │
│  Benefits:                                                           │
│    - Decoupled services (change consumers without touching producers)│
│    - Resilient (events buffered in SQS during consumer downtime)    │
│    - Scalable (consumers scale independently)                        │
│    - Auditable (events are the source of truth)                     │
└──────────────────────────────────────────────────────────────────────┘
```

### Saga Pattern for Distributed Transactions

```python
# Implement Saga with Step Functions
# Order placement spanning multiple services

import json

# State machine definition (AWS Step Functions)
saga_definition = {
    "Comment": "Order Placement Saga",
    "StartAt": "ReserveInventory",
    "States": {
        "ReserveInventory": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:reserve-inventory",
            "Next": "ChargePayment",
            "Catch": [{
                "ErrorEquals": ["States.ALL"],
                "Next": "RollbackInventory"
            }]
        },
        "ChargePayment": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:charge-payment",
            "Next": "CreateShipment",
            "Catch": [{
                "ErrorEquals": ["States.ALL"],
                "Next": "RollbackPayment"
            }]
        },
        "CreateShipment": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:create-shipment",
            "Next": "OrderConfirmed",
            "Catch": [{
                "ErrorEquals": ["States.ALL"],
                "Next": "RollbackShipment"
            }]
        },
        "OrderConfirmed": {
            "Type": "Succeed"
        },
        # Compensating transactions
        "RollbackShipment": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:rollback-shipment",
            "Next": "RollbackPayment"
        },
        "RollbackPayment": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:rollback-payment",
            "Next": "RollbackInventory"
        },
        "RollbackInventory": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:rollback-inventory",
            "Next": "OrderFailed"
        },
        "OrderFailed": {
            "Type": "Fail",
            "Error": "OrderFailed",
            "Cause": "Saga rollback completed"
        }
    }
}

# Deploy state machine
aws stepfunctions create-state-machine \
  --name order-saga \
  --definition "$(echo $saga_definition | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))')" \
  --role-arn arn:aws:iam::123:role/StepFunctionsRole \
  --type STANDARD \
  --logging-configuration '{
    "level": "ALL",
    "includeExecutionData": true,
    "destinations": [{"cloudWatchLogsLogGroup": {"logGroupArn": "arn:aws:logs:us-east-1:123:log-group:/stepfunctions/order-saga:*"}}]
  }'
```

---

## 14.5 Chaos Engineering with AWS FIS

AWS Fault Injection Service (FIS) helps test system resilience by injecting faults.

```bash
# Create experiment template — terminate random EC2 instance in ASG
aws fis create-experiment-template \
  --description "Terminate random EC2 instance in prod ASG" \
  --targets '{
    "prodInstances": {
      "resourceType": "aws:ec2:instance",
      "resourceTags": {"Environment": "prod"},
      "filters": [{"path": "State.Name", "values": ["running"]}],
      "selectionMode": "PERCENT(25)"    # Target 25% of instances
    }
  }' \
  --actions '{
    "terminateInstances": {
      "actionId": "aws:ec2:terminate-instances",
      "targets": {"Instances": "prodInstances"},
      "startAfter": []
    }
  }' \
  --stop-conditions '[{
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123:alarm:prod-error-rate-critical"
  }]' \
  --role-arn arn:aws:iam::123:role/FISExperimentRole \
  --log-configuration '{
    "cloudWatchLogsConfiguration": {
      "logGroupArn": "arn:aws:logs:us-east-1:123:log-group:/fis/experiments:*"
    },
    "logSchemaVersion": 2
  }'

# Run chaos experiment
aws fis start-experiment \
  --experiment-template-id EXT-abc123 \
  --tags Name=resilience-test-2025-01-15

# Monitor experiment
aws fis get-experiment --id EXP-xyz789
```

---

## 14.6 Microservices & Service Mesh

### App Mesh — Service Mesh for ECS/EKS

```bash
# Create mesh
aws appmesh create-mesh \
  --mesh-name prod-mesh \
  --spec '{"egressFilter": {"type": "DROP_ALL"}}'  # Block unregistered traffic

# Create virtual service
aws appmesh create-virtual-service \
  --mesh-name prod-mesh \
  --virtual-service-name orders.prod.local \
  --spec '{
    "provider": {
      "virtualRouter": {
        "virtualRouterName": "orders-router"
      }
    }
  }'

# Create virtual router with traffic shifting (canary)
aws appmesh create-virtual-router \
  --mesh-name prod-mesh \
  --virtual-router-name orders-router \
  --spec '{
    "listeners": [{"portMapping": {"port": 8080, "protocol": "http"}}]
  }'

aws appmesh create-route \
  --mesh-name prod-mesh \
  --virtual-router-name orders-router \
  --route-name orders-route \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "orders-v1", "weight": 90},
          {"virtualNode": "orders-v2", "weight": 10}
        ]
      },
      "retryPolicy": {
        "httpRetryEvents": ["server-error", "gateway-error"],
        "maxRetries": 3,
        "perRetryTimeout": {"unit": "ms", "value": 2000}
      },
      "timeout": {
        "idle": {"unit": "s", "value": 30},
        "perRequest": {"unit": "s", "value": 5}
      }
    }
  }'
```

---

## 14.7 Cost-Optimized Architecture Patterns

```
Pattern 1: Compute Savings
  ┌─────────────────────────────────────────────────────────────────┐
  │  Spot for batch/CI  +  Savings Plans for steady-state           │
  │                                                                  │
  │  ECS Service (Savings Plans capacity):                          │
  │    On-demand: 2 tasks (baseline production traffic)             │
  │  ECS Service (Spot capacity provider):                          │
  │    Spot: 10 tasks (burst capacity, 70% cheaper)                 │
  └─────────────────────────────────────────────────────────────────┘

Pattern 2: Tiered Storage
  ┌─────────────────────────────────────────────────────────────────┐
  │  Hot data  → DynamoDB (< 1ms latency)                           │
  │  Warm data → Aurora/RDS (< 10ms latency)                        │
  │  Cold data → S3 Standard (100ms-1s)                             │
  │  Archive   → S3 Glacier Instant (ms retrieval)                  │
  │  Deep arch → S3 Glacier Deep Archive (12h, ~$0.00099/GB/month)  │
  └─────────────────────────────────────────────────────────────────┘

Pattern 3: Serverless-First
  ┌─────────────────────────────────────────────────────────────────┐
  │  API Gateway HTTP API → Lambda → DynamoDB                       │
  │  EventBridge → Lambda → SQS → Lambda                           │
  │  Cost: Pay per request, zero idle cost                          │
  │  Scale: 0 to millions automatically                             │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 14.8 Security Architecture Patterns

### Defense in Depth

```
Internet
    │
    ▼
CloudFront (WAF + Shield + GeoIP blocking)
    │
    ▼
ALB (HTTPS only, redirect HTTP → HTTPS)
    │
    ▼
Security Group (Allow only from ALB SG)
    │
    ▼
ECS Tasks (no public IP, private subnet)
    │
    ├── Secrets Manager (DB creds — no env vars with secrets)
    ├── KMS (envelope encryption for all data)
    └── VPC Endpoint (S3/DynamoDB — no internet path)
            │
            ▼
        Aurora PostgreSQL
        (private subnet, encrypted at rest, SSL in transit)
```

---

## 14.9 Interview Q&A

**Q: What are the four DR strategies and when would you choose each?**
A: (1) Backup & Restore: cheapest, hourly RPO/RTO, suitable for non-critical apps that can tolerate hours of downtime. Just regular backups to S3. (2) Pilot Light: keep a minimal DB replica running, scale up rest on disaster. 10-60min RTO. Good for medium-criticality apps. (3) Warm Standby: scaled-down but fully functional copy in another region. Minutes of RTO/seconds of RPO. For business-critical systems. (4) Multi-Site Active-Active: two full production environments, traffic split by Route53. Near-zero RPO/RTO. For mission-critical systems (banking, healthcare). Cost increases significantly: Backup < Pilot < Warm < Active-Active.

**Q: What is the Saga pattern and why is it needed in microservices?**
A: In microservices, you can't use ACID database transactions across services. The Saga pattern coordinates distributed transactions through a sequence of local transactions, each publishing events/messages. Two types: (1) Choreography — each service listens for events and triggers next step; (2) Orchestration — central orchestrator (Step Functions) coordinates steps. Each step has a compensating transaction for rollback. Needed when you have: order placement spanning inventory, payment, and shipping services. Step Functions makes orchestration-based Sagas easy to implement and visualize.

**Q: What is the difference between a circuit breaker and retry with backoff?**
A: Retry with backoff: re-attempts a failed operation with increasing delays (e.g., 1s, 2s, 4s, 8s). Useful for transient failures (network blips, throttling). Circuit breaker: after N consecutive failures, "opens" and immediately rejects requests for a timeout period without even attempting the call. Prevents cascading failures — if a downstream service is down, don't keep hammering it. After the timeout, allows a few probe requests (half-open state) to test recovery. Use both: retry handles transient errors; circuit breaker handles sustained outages.

**Q: How does Aurora Global Database achieve cross-region replication?**
A: Aurora Global Database uses storage-level replication (not logical replication). Changes are replicated across regions asynchronously with typically < 1 second latency using dedicated replication infrastructure. The secondary region has a read replica cluster. For planned failover (low impact), you demote the primary and promote the secondary — takes about 1 minute. For unplanned failover (detach), promotes secondary with latest available data. The secondary can serve read traffic, reducing latency for globally distributed users.

**Q: What is AWS FIS and how does it differ from traditional testing?**
A: AWS Fault Injection Service injects real faults into running AWS environments: EC2 terminations, AZ outages, CPU/memory stress, latency injection, I/O faults, network drops. Traditional testing validates expected behavior; chaos engineering validates system resilience to unexpected failures. FIS has safety mechanisms: stop conditions (CloudWatch alarms halt the experiment if something goes wrong), rollback actions, and experiment logs. Run in staging first, then gradually extend to production. Validates assumptions: "we assume our multi-AZ setup handles AZ failure" → test it to confirm.

**Q: What is defense in depth in AWS and how do you implement it?**
A: Defense in depth applies security at multiple layers so a breach of one doesn't compromise the entire system. AWS layers: (1) Edge — CloudFront WAF + Shield blocks attacks before reaching origin; (2) Network — VPC with public/private subnets, NACLs, security groups with least-privilege rules; (3) Application — authentication/authorization, input validation, secrets in Secrets Manager; (4) Data — encryption at rest (KMS) and in transit (TLS), S3 bucket policies, no public buckets; (5) Identity — IAM with least privilege, MFA, no root account usage, SCPs; (6) Detection — GuardDuty, Security Hub, CloudTrail, Config compliance rules.
