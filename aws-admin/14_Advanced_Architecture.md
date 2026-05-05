# Chapter 14: Advanced Architecture
## Well-Architected Framework, DR, High Availability & Production Patterns

---

## 14.1 The AWS Well-Architected Framework

The Well-Architected Framework provides a set of guiding principles to build cloud systems that are secure, reliable, performant, cost-effective, and operationally excellent.

```
┌──────────────────────────────────────────────────────────────┐
│            SIX PILLARS OF WELL-ARCHITECTED                   │
├─────────────────────────┬────────────────────────────────────┤
│ 1. Operational          │ Run & monitor systems, improve     │
│    Excellence           │ processes, automate operations     │
│                         │ Key: IaC, runbooks, CI/CD          │
├─────────────────────────┼────────────────────────────────────┤
│ 2. Security             │ Protect data & systems             │
│                         │ Key: least privilege, encryption,  │
│                         │ traceability, defence in depth     │
├─────────────────────────┼────────────────────────────────────┤
│ 3. Reliability          │ Recover from failures, scale       │
│                         │ Key: multi-AZ, backups, retries,   │
│                         │ circuit breakers, chaos testing    │
├─────────────────────────┼────────────────────────────────────┤
│ 4. Performance          │ Use resources efficiently          │
│    Efficiency           │ Key: right instance types, caching,│
│                         │ CDN, async processing              │
├─────────────────────────┼────────────────────────────────────┤
│ 5. Cost                 │ Avoid unnecessary costs            │
│    Optimisation         │ Key: right-sizing, Savings Plans,  │
│                         │ Spot Instances, S3 lifecycle       │
├─────────────────────────┼────────────────────────────────────┤
│ 6. Sustainability       │ Reduce environmental impact        │
│                         │ Key: Graviton, efficient scaling,  │
│                         │ eliminating idle resources         │
└─────────────────────────┴────────────────────────────────────┘
```

---

## 14.2 Disaster Recovery Strategies

```
┌──────────────────────────────────────────────────────────────┐
│                  DR SPECTRUM                                 │
│                                                              │
│  ←── MORE DOWNTIME ──────────────── LESS DOWNTIME ──►        │
│  ←── LOWER COST ─────────────────── HIGHER COST ──►         │
│                                                              │
│  Backup &     Pilot        Warm          Multi-Site          │
│  Restore      Light        Standby       Active/Active        │
│                                                              │
│  RTO: hours   RTO: tens    RTO: minutes  RTO: seconds        │
│  RPO: hours   of minutes   RPO: minutes  RPO: near-zero      │
└──────────────────────────────────────────────────────────────┘
```

### RTO and RPO Defined

```
RPO (Recovery Point Objective)
= How much data loss is acceptable?
= Time between last backup and the failure
= "We can lose at most 1 hour of data"

RTO (Recovery Time Objective)
= How long can the system be down?
= Time to restore service after failure
= "We must be back up within 30 minutes"
```

### Strategy 1: Backup & Restore

```
• Regular backups to S3 (RDS snapshots, EBS snapshots)
• AMIs of EC2 instances
• On disaster: restore from backup in same or different region
• Cheapest — just storage cost
• Highest downtime (hours to restore)
• Use for: dev/test, non-critical systems
```

```bash
# Automate RDS snapshot copy to DR region
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:123456:snapshot:mydb-2024-01-01 \
  --target-db-snapshot-identifier mydb-2024-01-01-dr \
  --region eu-west-1

# S3 Cross-Region Replication
aws s3api put-bucket-replication \
  --bucket my-data-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456:role/s3-replication-role",
    "Rules": [{
      "Status": "Enabled",
      "Destination": {
        "Bucket": "arn:aws:s3:::my-data-bucket-eu-west-1",
        "StorageClass": "STANDARD_IA"
      }
    }]
  }'
```

### Strategy 2: Pilot Light

```
• Minimal active environment in DR region
• Database replicated live (RDS read replica cross-region)
• Application servers off (AMIs ready to launch)
• On disaster: scale up infrastructure from AMIs
• Medium cost — only DB running in DR
• RTO: tens of minutes (launch EC2 fleet, redirect DNS)
• Use for: critical applications with budget constraints
```

### Strategy 3: Warm Standby

```
• Scaled-down copy of production running in DR region
• RDS read replica cross-region (promoted on failover)
• Small EC2 / ECS fleet running (scale up on failover)
• On disaster: scale up, promote replica, flip Route53
• Higher cost — scaled-down infra always running
• RTO: minutes
• Use for: important business applications
```

### Strategy 4: Multi-Site Active/Active

```
• Full production running in 2+ regions simultaneously
• Route53 latency-based or geolocation routing splits traffic
• Global DynamoDB tables / Aurora Global Database
• Zero data loss, zero downtime
• Most expensive — double infra
• Use for: mission-critical (banking, e-commerce)
```

```bash
# Aurora Global Database (primary + replica in second region)
aws rds create-global-cluster \
  --global-cluster-identifier myapp-global \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:123456:cluster:myapp-prod

aws rds create-db-cluster \
  --db-cluster-identifier myapp-eu-replica \
  --global-cluster-identifier myapp-global \
  --engine aurora-postgresql \
  --engine-version 15.2 \
  --region eu-west-1 \
  --db-subnet-group-name myapp-db-subnet-eu \
  --vpc-security-group-ids sg-xxxx

# Failover to secondary region (promotes EU replica to primary)
aws rds failover-global-cluster \
  --global-cluster-identifier myapp-global \
  --target-db-cluster-identifier arn:aws:rds:eu-west-1:123456:cluster:myapp-eu-replica
```

---

## 14.3 High Availability Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              MULTI-AZ PRODUCTION ARCHITECTURE                │
│                                                              │
│  Route 53 (with health checks + failover)                   │
│       │                                                      │
│       ▼                                                      │
│  CloudFront                                                  │
│       │                                                      │
│       ▼                                                      │
│  Application Load Balancer (us-east-1)                       │
│       │                                                      │
│  ┌────┼────────────────────────────────┐                     │
│  ▼    ▼                                ▼                     │
│  AZ-a (ECS/EC2)  AZ-b (ECS/EC2)  AZ-c (ECS/EC2)            │
│       │               │                │                     │
│  ┌────┴───────────────┴────────────────┴────┐                │
│  │              ElastiCache (Redis)         │                │
│  │              Multi-AZ replication        │                │
│  └──────────────────────────────────────────┘                │
│  ┌──────────────────────────────────────────┐                │
│  │          RDS Aurora Multi-AZ             │                │
│  │  Primary AZ-a  ←→ Replica AZ-b + AZ-c  │                │
│  └──────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
```

### Route53 Health Checks & Failover

```bash
# Create health check (checks /health endpoint every 30s)
aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "api.myapp.com",
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "EnableSNI": true
  }'

# Create failover record — primary region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.myapp.com",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "HealthCheckId": "<health-check-id>",
        "AliasTarget": {
          "HostedZoneId": "Z...",
          "DNSName": "my-alb-us-east.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

---

## 14.4 Production Application Architecture

### Serverless API (High Scale, Low Management)

```
┌──────────────────────────────────────────────────────────────┐
│            SERVERLESS PRODUCTION ARCHITECTURE                │
│                                                              │
│  Client                                                      │
│    │                                                         │
│    ▼                                                         │
│  CloudFront  ──── WAF rules                                  │
│    │                                                         │
│    ▼                                                         │
│  API Gateway (HTTP API)                                      │
│    │         └── Lambda Authorizer (JWT validation)          │
│    │                                                         │
│  ┌─┴───────────────────────────────────────┐                 │
│  │    Lambda Functions (auto-scaling)      │                 │
│  │   ┌──────────┐  ┌──────────┐            │                 │
│  │   │ GET /api │  │POST /api │  ...        │                 │
│  │   └──────────┘  └──────────┘            │                 │
│  └─────────────────────────────────────────┘                 │
│           │              │              │                    │
│           ▼              ▼              ▼                    │
│       DynamoDB     ElastiCache      SQS Queue                │
│       (data)       (cache)          (async jobs)             │
│                                         │                    │
│                                    Lambda Worker              │
└──────────────────────────────────────────────────────────────┘
```

### Containerised API (ECS Fargate)

```
┌──────────────────────────────────────────────────────────────┐
│            FARGATE PRODUCTION ARCHITECTURE                   │
│                                                              │
│  Route53 → CloudFront → WAF                                  │
│                │                                             │
│                ▼                                             │
│           ALB (HTTPS:443)                                    │
│                │                                             │
│   ┌────────────┼────────────────────┐                        │
│   ▼            ▼                    ▼                        │
│  ECS Fargate Tasks (3 AZs)                                   │
│  ┌──────────────────────────────┐                            │
│  │ FastAPI container            │                            │
│  │ Port 8000                    │                            │
│  └──────────────────────────────┘                            │
│           │                                                  │
│    ┌──────┼──────────────────────┐                           │
│    ▼      ▼                      ▼                           │
│  RDS    ElastiCache          Secrets Manager                 │
│  Aurora  Redis                (DB creds)                     │
│    │                                                          │
│  ECS Service Auto Scaling (min 2, max 20 tasks)              │
│  Scale on CPU > 70% or SQS queue depth                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 14.5 Chaos Engineering

Chaos engineering validates resilience by intentionally injecting failures.

```bash
# AWS Fault Injection Simulator (FIS)
aws fis create-experiment-template \
  --description "Terminate 30% of ECS tasks" \
  --targets '{
    "ECSTaskTargets": {
      "resourceType": "aws:ecs:task",
      "resourceTags": {"Environment": "staging"},
      "selectionMode": "PERCENT(30)"
    }
  }' \
  --actions '{
    "TerminateTasks": {
      "actionId": "aws:ecs:stop-task",
      "targets": {"Tasks": "ECSTaskTargets"}
    }
  }' \
  --stop-conditions '[{
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:...:alarm:critical-error-rate"
  }]' \
  --role-arn arn:aws:iam::123456:role/fis-role

# Run experiment
aws fis start-experiment \
  --experiment-template-id <template-id>
```

```
Chaos testing scenarios:
• Terminate EC2/ECS instances — does Auto Scaling replace them?
• Throttle DynamoDB writes — do you get graceful errors?
• Block outbound internet from Lambda — does circuit breaker trigger?
• Kill primary RDS — does Multi-AZ failover work within 60s?
• Inject latency into service calls — does timeout fire, not hang forever?
```

---

## 14.6 Circuit Breaker Pattern

```python
# Simple circuit breaker for external service calls
import time
from enum import Enum
from functools import wraps


class CircuitState(Enum):
    CLOSED = "closed"        # Normal — requests pass through
    OPEN = "open"            # Failing — requests blocked
    HALF_OPEN = "half_open"  # Testing — one request allowed


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker OPEN — downstream service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


# Usage
payment_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

def charge_payment(order_id: str, amount: float):
    return payment_circuit.call(
        external_payment_api_call,
        order_id=order_id,
        amount=amount
    )
```

---

## 14.7 Architecture Anti-Patterns

```
┌──────────────────────────────────────────────────────────────┐
│              COMMON ARCHITECTURE MISTAKES                    │
├──────────────────────────────────────────────────────────────┤
│ ❌ Single point of failure                                   │
│    One instance, no Multi-AZ, no Auto Scaling                │
│    → Fix: Multi-AZ deployments, Auto Scaling, health checks  │
├──────────────────────────────────────────────────────────────┤
│ ❌ Secrets in code or environment variables                  │
│    → Fix: Secrets Manager or Parameter Store                 │
├──────────────────────────────────────────────────────────────┤
│ ❌ No retry logic for transient failures                     │
│    → Fix: exponential backoff with jitter                    │
├──────────────────────────────────────────────────────────────┤
│ ❌ Synchronous calls to slow external services               │
│    → Fix: async with SQS + Lambda consumer                  │
├──────────────────────────────────────────────────────────────┤
│ ❌ No DLQ on SQS queues                                      │
│    → Failures loop forever, block the queue                  │
│    → Fix: DLQ + CloudWatch alarm on DLQ depth               │
├──────────────────────────────────────────────────────────────┤
│ ❌ Lambda timeout too short                                  │
│    → Requests fail mid-processing                            │
│    → Fix: set timeout to 2x expected max duration            │
├──────────────────────────────────────────────────────────────┤
│ ❌ No caching in front of expensive DB queries               │
│    → DB overwhelmed at scale                                 │
│    → Fix: ElastiCache for read-heavy, idempotent queries     │
├──────────────────────────────────────────────────────────────┤
│ ❌ VPC resources querying S3/DynamoDB through NAT Gateway    │
│    → Unnecessary data transfer costs                         │
│    → Fix: Gateway VPC Endpoints (free for S3/DynamoDB)       │
└──────────────────────────────────────────────────────────────┘
```

---

## 14.8 System Design Interview Framework

When asked to design a system, use this structure:

```
1. Clarify requirements (5 min)
   • Scale: how many users / requests per second?
   • Consistency needs: eventual vs strong?
   • SLA: 99.9% (8h downtime/year) vs 99.99% (52min/year)?
   • Budget constraints?

2. Estimate scale (2 min)
   • 1M DAU × 10 requests/day = ~115 req/sec avg, ~1150 peak
   • 1KB/request × 115 req/sec = ~100MB/s write throughput

3. High-level design (10 min)
   • Draw the main components: client → API → service → DB
   • Identify bottlenecks

4. Deep dive on key components (15 min)
   • Database choice (SQL vs DynamoDB, schema)
   • Caching strategy
   • How does it handle failure?
   • How does it scale?

5. Address non-functionals (5 min)
   • Security: auth, encryption, WAF
   • Monitoring: metrics, logs, traces
   • DR: backup strategy, RTO/RPO
```

---

## 14.9 Interview Questions

**Q: Walk me through how you would design a URL shortener on AWS.**
> Users call POST /shorten → API Gateway → Lambda → generates 6-char hash, stores long URL in DynamoDB (short code as key) → returns short URL. GET /{code} → API Gateway → Lambda → DynamoDB GetItem → 301 redirect to original URL. Scale: DynamoDB auto-scales, Lambda scales to thousands concurrent. CloudFront caches redirects. For analytics: on each GET, push to Kinesis Data Firehose → S3 for click analytics. Security: WAF rate limiting to prevent abuse. Cost: nearly zero at low traffic, scales linearly.

**Q: How do you design for 99.99% availability?**
> (1) Eliminate single points of failure: Multi-AZ deployments for every component, minimum 2 tasks/instances. (2) Auto Scaling: replace unhealthy instances automatically. (3) Health checks at every layer: Route53 → ALB → ECS tasks. (4) Graceful degradation: if one service fails, return cached data or a fallback response rather than an error. (5) Circuit breakers: prevent cascade failures. (6) Multi-region active/active for global or very high SLA requirements. (7) Chaos testing to validate all of the above actually works.

**Q: What is the difference between RPO and RTO?**
> RPO (Recovery Point Objective) is how much data loss is acceptable — it determines backup frequency. If RPO is 1 hour, you need hourly backups; if near-zero, you need synchronous replication. RTO (Recovery Time Objective) is how long the system can be down after a disaster — it determines DR strategy. If RTO is 4 hours, backup & restore may suffice. If RTO is minutes, you need a warm standby or active/active setup. Both are business decisions: lower RPO and RTO cost more.
