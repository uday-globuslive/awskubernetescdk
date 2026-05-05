# Part 9: Additional Topics

---

## 9.1 Observability — Metrics, Logs, Traces

### FastAPI Prometheus Metrics

```python
# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
import time

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ACTIVE_REQUESTS = Gauge("http_requests_active", "Active HTTP requests")


async def prometheus_middleware(request: Request, call_next) -> Response:
    if request.url.path == "/metrics":
        return await call_next(request)
    
    ACTIVE_REQUESTS.inc()
    start = time.perf_counter()
    
    response = await call_next(request)
    
    duration = time.perf_counter() - start
    endpoint = request.url.path
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
    ACTIVE_REQUESTS.dec()
    
    return response


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Structured Logging with structlog

```python
# app/logging_config.py
import structlog
import logging
import sys


def configure_logging(environment: str) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if environment == "prod":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
    )


# Usage
logger = structlog.get_logger()

async def process_order(order_id: str) -> None:
    log = logger.bind(order_id=order_id, service="order-processor")
    log.info("Processing started")
    
    try:
        result = await do_processing(order_id)
        log.info("Processing completed", duration_ms=result.duration)
    except Exception as e:
        log.error("Processing failed", error=str(e), exc_info=True)
        raise
```

---

## 9.2 Security Hardening

### Security Headers Middleware

```python
# app/middleware/security.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        
        # Remove server info
        response.headers.pop("Server", None)
        
        return response
```

### Input Sanitization

```python
import bleach
from pydantic import BaseModel, field_validator


class CommentCreate(BaseModel):
    content: str
    
    @field_validator("content")
    @classmethod
    def sanitize_html(cls, v: str) -> str:
        # Allow only safe HTML tags
        allowed_tags = ["b", "i", "em", "strong", "p", "br"]
        allowed_attrs: dict = {}
        return bleach.clean(v, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    
    @field_validator("content")
    @classmethod
    def max_length(cls, v: str) -> str:
        if len(v) > 10000:
            raise ValueError("Content too long")
        return v
```

---

## 9.3 API Versioning Strategies

```python
# Strategy 1: URL versioning (most common)
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")

# Strategy 2: Header versioning
from fastapi import Header, HTTPException

async def get_api_version(x_api_version: str = Header(default="1")):
    if x_api_version not in ["1", "2"]:
        raise HTTPException(400, "Unsupported API version")
    return x_api_version

@router.get("/orders")
async def list_orders(version = Depends(get_api_version)):
    if version == "2":
        return list_orders_v2()
    return list_orders_v1()

# Strategy 3: Query parameter
@router.get("/orders")
async def list_orders(api_version: str = Query("1", alias="version")):
    pass
```

---

## 9.4 Testing Strategies

### Contract Testing with Pact

```python
# Consumer-driven contract testing
# tests/contract/test_consumer.py
import pytest
from pact import Consumer, Provider

pact = Consumer("orders-api").has_pact_with(Provider("payment-service"))

def test_payment_request(pact):
    expected = {
        "orderId": "123",
        "amount": 99.99,
        "currency": "USD",
    }
    
    (pact
        .given("payment service is available")
        .upon_receiving("a payment request")
        .with_request("POST", "/payments", body=expected)
        .will_respond_with(201, body={"paymentId": "pay_abc123", "status": "completed"})
    )
    
    with pact:
        result = payment_client.charge(order_id="123", amount=99.99)
        assert result["status"] == "completed"
```

### Load Testing with Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class OrdersUser(HttpUser):
    wait_time = between(0.5, 2)
    token = None
    
    def on_start(self):
        response = self.client.post("/api/v1/auth/token", data={
            "username": "test@example.com",
            "password": "TestPass123!",
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def list_orders(self):
        self.client.get("/api/v1/orders",
            headers={"Authorization": f"Bearer {self.token}"},
            name="/api/v1/orders",
        )
    
    @task(1)
    def create_order(self):
        self.client.post("/api/v1/orders",
            json={"items": [{"productId": "prod_1", "quantity": 2}]},
            headers={"Authorization": f"Bearer {self.token}"},
            name="/api/v1/orders [POST]",
        )
```

```bash
# Run load test
locust -f locustfile.py --headless \
  --users 100 --spawn-rate 10 \
  --run-time 5m \
  --host http://localhost:8000
```

---

## 9.5 Event-Driven Architecture Patterns

### Saga Pattern with Step Functions

```json
{
  "Comment": "Order processing saga",
  "StartAt": "ReserveInventory",
  "States": {
    "ReserveInventory": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:reserve-inventory",
      "Next": "ProcessPayment",
      "Catch": [{
        "ErrorEquals": ["InsufficientInventoryError"],
        "Next": "OrderFailed"
      }]
    },
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:process-payment",
      "Next": "FulfillOrder",
      "Catch": [{
        "ErrorEquals": ["PaymentFailedError"],
        "Next": "CompensateInventory"
      }]
    },
    "FulfillOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:fulfill-order",
      "Next": "OrderComplete"
    },
    "CompensateInventory": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123:function:release-inventory",
      "Next": "OrderFailed"
    },
    "OrderComplete": {"Type": "Succeed"},
    "OrderFailed": {"Type": "Fail", "Cause": "Order processing failed"}
  }
}
```

---

## 9.6 Cost Optimization Tips

| Area | Tip | Savings |
|------|-----|---------|
| Lambda | Use ARM64 (Graviton2) | ~20% cheaper |
| Lambda | Right-size memory (use Power Tuning) | 20-40% |
| ECS | Mix on-demand + Spot (70/30) | ~40% |
| RDS | Aurora Serverless v2 (dev/staging) | 50-80% dev env |
| EC2 | Savings Plans 1-year compute | ~30% |
| S3 | Intelligent Tiering for > 128KB objects | 40-68% |
| CloudFront | Cache aggressively (reduce origin hits) | Varies |
| NAT Gateway | VPC Endpoints for AWS services | Significant |
| Data Transfer | Use same-region resources | Avoid transfer fees |

### Lambda Power Tuning

```bash
# Deploy AWS Lambda Power Tuning SAR app
# Then run:
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123:stateMachine:powerTuningStateMachine \
  --input '{
    "lambdaARN": "arn:aws:lambda:us-east-1:123:function:my-function",
    "powerValues": [128, 256, 512, 1024, 2048, 3008],
    "num": 50,
    "payload": {},
    "parallelInvocation": true,
    "strategy": "cost"
  }'
```

---

## 9.7 GitOps with Argo CD on EKS

```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: orders-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/k8s-manifests.git
    targetRevision: main
    path: apps/orders-api/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
  syncPolicy:
    automated:
      prune: true        # Remove resources deleted from Git
      selfHeal: true     # Revert manual changes
    syncOptions:
      - CreateNamespace=true
```

```bash
# Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Sync app
argocd app sync orders-api

# Check status
argocd app get orders-api
```

---

## 9.8 Final Interview Tips

1. **Always explain the "why"** — interviewers want to see you understand trade-offs, not just syntax.

2. **Use the STAR format** for behavioral questions (Situation, Task, Action, Result).

3. **Think aloud** during system design — interviewers evaluate your thought process.

4. **Key numbers to remember**:
   - Lambda max timeout: 15 min | max memory: 10GB | max package: 250MB unzipped
   - DynamoDB item size: 400KB | max partition throughput: 3000 RCU / 1000 WCU
   - SQS message size: 256KB | max visibility timeout: 12 hours | retention: 14 days
   - API GW HTTP timeout: 29 seconds
   - ALB target response timeout: configurable, default 60s

5. **Common mistakes to avoid**:
   - Blocking I/O in `async def` functions
   - Missing `await` on coroutines
   - Not handling rollback in database operations
   - Storing secrets in environment variables (use Secrets Manager)
   - Not setting resource limits in Kubernetes
   - Missing DLQ on SQS event sources
