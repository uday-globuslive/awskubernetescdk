# Part 6: Interview Preparation — FastAPI + AWS

---

## Section 1: FastAPI Deep-Dive Questions

**Q1: How does FastAPI handle request validation, and what happens when validation fails?**

FastAPI uses Pydantic models for request body validation and Python type hints for path/query parameters. When a request arrives: (1) FastAPI extracts data from the request (body, path params, query params, headers); (2) Pydantic validates using field types and validators; (3) If valid, the data is passed to the handler as typed Python objects; (4) If invalid, FastAPI automatically returns a `422 Unprocessable Entity` response with a detailed JSON error body listing all validation errors with their locations and messages.

You can customize the 422 response by registering a `RequestValidationError` exception handler:

```python
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"errors": exc.errors()})
```

---

**Q2: What is dependency injection in FastAPI and how is cleanup handled?**

FastAPI's DI system resolves dependencies in the correct order before calling the path function. Dependencies that use `yield` support cleanup:

```python
async def get_db():
    db = AsyncSession()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
```

FastAPI ensures the finally block runs even if the endpoint raises an exception. This is similar to a context manager. Dependencies can be scoped to: request (default, new instance per request), app startup (use `@asynccontextmanager` lifespan), or overridden in tests via `app.dependency_overrides`.

---

**Q3: Explain FastAPI's response model and how to exclude/include fields.**

```python
class UserResponse(BaseModel):
    id: int
    email: str
    # password NOT included — security

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user   # FastAPI filters to only UserResponse fields

# Exclude None fields from response
@router.get("/me", response_model=UserResponse, response_model_exclude_none=True)
async def get_me(...)

# Dynamic exclusion
@router.get("/admin/users/{id}")
async def get_user_admin(id: int, include_private: bool = False):
    user = await fetch_user(id)
    exclude = set() if include_private else {"internal_id", "admin_notes"}
    return user.model_dump(exclude=exclude)
```

---

**Q4: How do you implement pagination in FastAPI?**

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int
    next_page: int | None
    prev_page: int | None

def paginate(items, total, page, size):
    pages = (total + size - 1) // size
    return PaginatedResponse(
        items=items, total=total, page=page, size=size, pages=pages,
        next_page=page + 1 if page < pages else None,
        prev_page=page - 1 if page > 1 else None,
    )
```

For cursor-based pagination (better for large datasets): use a unique sort key (created_at + id) as cursor, encode as base64, and use `WHERE created_at < cursor_time OR (created_at = cursor_time AND id < cursor_id)`.

---

## Section 2: AWS Lambda Questions

**Q5: What triggers a Lambda cold start, and what are SnapStart and Provisioned Concurrency?**

Cold start occurs when: (1) first invocation ever; (2) traffic spike requiring new execution environments; (3) after ~15 minutes of idle; (4) after a code deployment.

**Provisioned Concurrency**: Pre-initializes N execution environments. They're always ready — zero cold start. Charged per GB-hour even when idle. Best for latency-sensitive APIs.

**SnapStart** (Java only): Takes a snapshot of the initialized JVM state. On cold start, restores from snapshot instead of reinitializing. Reduces Java cold starts from 1-5s to ~100ms. Enabled per Lambda version, not function.

For Python: keep init code minimal, use lazy imports for optional modules, use Lambda Layers to prevent re-downloading dependencies on each cold start.

---

**Q6: How does Lambda scale, and what are concurrency limits?**

Lambda scales by adding execution environments (one per concurrent invocation). **Account-level burst limit**: 3000 in us-east-1/us-west-2 (500-1000 in other regions), with +500/min linear scaling. **Throttling**: If burst limit exceeded, Lambda returns 429 — SQS automatically retries, API GW returns 502.

**Reserved Concurrency**: Hard cap per function (e.g., `max: 100`). Protects other functions from a runaway function consuming the pool. Also guarantees capacity.

**Concurrency math**: If a function processes one SQS message and takes 5 seconds, and 100 messages arrive simultaneously → 100 concurrent executions needed. Size your reserved concurrency accordingly.

---

**Q7: How do you handle Lambda timeouts and implement proper timeout handling?**

```python
import signal
from aws_lambda_powertools import Logger

logger = Logger()

def handler(event, context):
    # Check remaining time before starting expensive operation
    if context.get_remaining_time_in_millis() < 5000:
        logger.error("Insufficient time remaining, aborting")
        raise TimeoutError("Lambda timeout imminent")
    
    # For external calls, set timeouts less than Lambda timeout
    import httpx
    timeout = httpx.Timeout(
        connect=2.0,
        read=min(10.0, context.get_remaining_time_in_millis() / 1000 - 2),
        write=5.0,
    )
    response = httpx.get("https://api.external.com/data", timeout=timeout)
```

For SQS: set Lambda timeout < SQS visibility timeout. If Lambda times out while processing, the message becomes visible again and retries.

---

## Section 3: AWS CDK / CloudFormation Questions

**Q8: What is the difference between CDK App, Stage, and Stack?**

**App**: Root of the CDK application. Contains all stacks and stages. `cdk synth` processes the entire App. **Stack**: A CloudFormation stack — a unit of deployment. Maps to a single CFN stack. Has its own template, parameters, outputs. **Stage**: Groups stacks for pipeline deployment. A Stage gets deployed as a unit (all stacks together). Enables deploying the same infrastructure to multiple environments (dev, prod) with different configs.

```python
# Hierarchy
App
└── ProdStage (environment=prod, account=111...)
│   ├── NetworkStack
│   ├── DataStack
│   └── AppStack
└── DevStage (environment=dev, account=222...)
    ├── NetworkStack
    ├── DataStack
    └── AppStack
```

---

**Q9: How do you handle rollback in CloudFormation?**

By default, CloudFormation rolls back automatically on failure. Key mechanisms: (1) **Rollback triggers**: CloudWatch alarms that trigger auto-rollback if they fire during the monitoring window post-deployment; (2) **Stack policies**: Prevent certain update types (Replace/Delete) on protected resources; (3) **`--disable-rollback`**: Flag to disable auto-rollback for debugging; (4) **`UPDATE_ROLLBACK_FAILED` state**: When rollback itself fails (e.g., trying to restore a deleted resource). Recovery: `continue-update-rollback` with resources that failed rollback skipped.

For production: always add rollback triggers monitoring your key metrics (5xx rate, Lambda errors, DB connections).

---

## Section 4: EKS/Kubernetes Questions

**Q10: What is the difference between ConfigMap and Secret, and how do you manage secrets in Kubernetes?**

**ConfigMap**: Non-sensitive configuration (feature flags, URLs, app settings). Stored unencrypted in etcd. Available as environment variables or mounted files.

**Secret**: Sensitive data (passwords, tokens, API keys). Base64-encoded (NOT encrypted by default in etcd). To actually secure secrets: (1) **Envelope encryption**: Encrypt etcd with a KMS key (`--encryption-provider-config`); (2) **External Secrets Operator**: Sync from AWS Secrets Manager/SSM to Kubernetes Secrets automatically (recommended); (3) **AWS Secrets Store CSI Driver**: Mount secrets directly as volumes, no copy in etcd.

For EKS production: never put plaintext secrets in manifests. Use External Secrets Operator with AWS Secrets Manager. The operator creates/syncs Kubernetes Secrets automatically.

---

**Q11: How does Kubernetes networking work at a high level?**

Every Pod gets a unique IP. Pods can communicate with each other directly (flat network) without NAT. Services provide stable DNS names and IP (ClusterIP) that load-balance across pod endpoints. 

**Key components**: (1) **CNI plugin** (AWS VPC CNI on EKS): assigns real VPC IPs to pods — they're directly routable; (2) **kube-proxy**: Manages iptables/IPVS rules for Service IP → Pod IP routing; (3) **CoreDNS**: Resolves `service.namespace.svc.cluster.local` to ClusterIP; (4) **Network Policies**: Firewall rules between pods (requires CNI support).

In EKS with VPC CNI: each pod gets a secondary IP from the VPC subnet. Pod-to-pod traffic stays within VPC, no overlay network overhead. Direct integration with security groups via Security Groups for Pods.

---

## Section 5: System Design Questions

**Q12: Design a high-throughput order processing system on AWS.**

```
API Layer:      CloudFront → ALB → ECS Fargate (FastAPI)
Async Queue:    SQS FIFO (per customer) → Lambda workers
Database:       DynamoDB (order state) + Aurora (reporting)
Cache:          ElastiCache Redis (session, rate limiting, idempotency)
Notifications:  SNS → SQS fan-out (email, SMS, analytics)
Observability:  CloudWatch + X-Ray + OpenSearch
```

Key design decisions:
- **Idempotency**: Idempotency-Key header + Redis NX set prevents double-orders
- **Optimistic locking**: DynamoDB condition expressions prevent race conditions
- **FIFO queues**: Per-customer ordering guarantees (message group = customer ID)
- **Circuit breaker**: Resilience4j / Polly pattern for downstream service failures
- **Saga pattern**: Step Functions for multi-step orders (reserve → charge → fulfill)

---

**Q13: How do you handle database migrations with zero downtime?**

Multi-phase approach:
1. **Add nullable column** (backward compatible, old code ignores it)
2. **Deploy new code** that reads from old column, writes to both
3. **Backfill** old data into new column
4. **Deploy code** that reads from new column primarily
5. **Drop old column** (after verifying no reads)

For RDS with ECS/K8s: use Alembic in an init container that runs before app containers, or in a separate migration job. Never run migrations at app startup in production (multiple pods would race). Use advisory locks in PostgreSQL to prevent concurrent migration runs.

---

## Practice Interview Answers (STAR Format)

**"Tell me about a time you improved API performance."**

Situation: API latency at P99 was 800ms, causing timeout errors for mobile users.
Task: Reduce P99 to under 200ms without downtime.
Action: (1) Added APM tracing (X-Ray) — found N+1 DB queries; (2) Rewrote with bulk fetches; (3) Added Redis caching for user profile lookups (TTL 5min); (4) Moved non-critical work (notifications) to SQS background processing.
Result: P99 dropped to 120ms. Error rate from 2% to 0.01%.
