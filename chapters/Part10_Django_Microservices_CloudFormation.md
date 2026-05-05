# Part X: Django, Microservices Architecture & CloudFormation Templates
## JD Gap Coverage: Django Framework, Microservices Patterns, Raw CloudFormation

---

# Chapter 45: Django for Python Backend Developers

## 45.1 Why Django Matters (Even If You Love FastAPI)

The JD says **"Django or FastAPI"** — you may be asked Django questions in interviews or inherit a Django codebase.

```
┌────────────────────────────────────────────────────────────┐
│              PYTHON WEB FRAMEWORK LANDSCAPE                │
│                                                            │
│   Django          FastAPI         Flask                    │
│   ──────          ───────         ─────                    │
│   "Batteries      "Fast &         "Micro &                 │
│   Included"       Modern"         Flexible"                │
│                                                            │
│   Built-in ORM    Pydantic        No built-ins             │
│   Built-in Admin  Auto-docs       Roll your own            │
│   Built-in Auth   Async native    Manual setup             │
│   Full-stack      API-first       Anything                 │
│                                                            │
│   Best for:       Best for:       Best for:                │
│   CMS, Admin,     APIs, ML,       Simple apps,             │
│   Monoliths       Microservices   Learning                 │
└────────────────────────────────────────────────────────────┘
```

---

## 45.2 Django Project Structure

```bash
# Create Django project
pip install django djangorestframework
django-admin startproject myproject
cd myproject
python manage.py startapp users
python manage.py startapp products
```

```
myproject/
├── manage.py                    ← CLI tool (like uvicorn for FastAPI)
├── myproject/
│   ├── __init__.py
│   ├── settings.py              ← All config (like .env + config.py)
│   ├── urls.py                  ← Root URL routing
│   ├── wsgi.py                  ← WSGI entry point
│   └── asgi.py                  ← ASGI entry point (async)
├── users/                       ← App (like a FastAPI router module)
│   ├── models.py                ← Database models (like SQLAlchemy models)
│   ├── views.py                 ← Request handlers (like FastAPI path functions)
│   ├── serializers.py           ← DRF: like Pydantic schemas
│   ├── urls.py                  ← App-level URL routing
│   ├── admin.py                 ← Admin panel registration
│   └── tests.py                 ← Tests
└── products/
    └── ...
```

**FastAPI → Django mental mapping:**

| FastAPI | Django | Purpose |
|---------|--------|---------|
| `app = FastAPI()` | `django-admin startproject` | App creation |
| `@app.get("/users")` | `path('users/', view)` in urls.py | Routing |
| Pydantic model | `serializers.py` (DRF) | Data validation/serialization |
| SQLAlchemy model | `models.py` (Django ORM) | Database schema |
| `Depends(get_db)` | Django ORM (always available) | DB access |
| `uvicorn main:app` | `python manage.py runserver` | Dev server |

---

## 45.3 Django ORM — Models

Django's built-in ORM replaces SQLAlchemy.

```python
# users/models.py
from django.db import models


class User(models.Model):
    # Fields (like SQLAlchemy columns)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)   # auto set on create
    updated_at = models.DateTimeField(auto_now=True)       # auto update

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.username


class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    # Foreign Key (like SQLAlchemy relationship)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="products"
    )

    class Meta:
        db_table = "products"
```

### Migrations (like Alembic)

```bash
# Generate migration file from model changes
python manage.py makemigrations

# Apply migrations to database
python manage.py migrate

# Show migration history
python manage.py showmigrations
```

### ORM Queries (vs SQLAlchemy)

```python
# FastAPI + SQLAlchemy style:
db.query(User).filter(User.id == user_id).first()

# Django ORM style:
User.objects.get(id=user_id)           # Raises DoesNotExist if not found
User.objects.filter(is_active=True)    # Returns QuerySet (lazy)
User.objects.all()                     # All records

# Create
user = User.objects.create(username="john", email="john@example.com")

# Update
User.objects.filter(id=1).update(is_active=False)

# Delete
User.objects.filter(id=1).delete()

# Filtering
User.objects.filter(username__icontains="john")  # ILIKE %john%
User.objects.filter(created_at__gte=some_date)   # >= date

# Joins (select_related = INNER JOIN, prefetch_related = separate query)
products = Product.objects.select_related("owner").filter(price__lt=100)

# Aggregates
from django.db.models import Count, Avg
User.objects.aggregate(total=Count("id"))
Product.objects.values("owner").annotate(count=Count("id"))
```

---

## 45.4 Django REST Framework (DRF)

DRF is Django's de-facto API library — like FastAPI but bolt-on.

```python
# settings.py — enable DRF
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",          # ← Add DRF
    "rest_framework.authtoken", # ← Token auth
    "users",
    "products",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
```

### DRF Serializers — Pydantic Equivalent

```python
# users/serializers.py
from rest_framework import serializers
from .models import User, Product


# READ serializer (output)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "created_at"]
        read_only_fields = ["id", "created_at"]


# WRITE serializer (input with validation)
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "full_name", "password", "password_confirm"]

    # Custom validation (like @validator in Pydantic)
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)   # Hashes password
        user.save()
        return user


class ProductSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price", "stock", "owner", "owner_username"]
        read_only_fields = ["id", "owner"]
```

**FastAPI Pydantic ↔ DRF Serializer comparison:**

```python
# FastAPI (Pydantic)               # Django (DRF Serializer)
class UserCreate(BaseModel):       class UserCreateSerializer(ModelSerializer):
    username: str                      class Meta:
    email: EmailStr                        model = User
    password: str                          fields = ["username", "email", "password"]

    @validator("email")                def validate_email(self, value):
    def validate_email(cls, v):            ...
        ...
```

---

## 45.5 DRF Views — Class-Based Views (CBV)

```python
# users/views.py
from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import User, Product
from .serializers import UserSerializer, UserCreateSerializer, ProductSerializer


# ── FUNCTION-BASED VIEW (like FastAPI path function) ──────────────────────
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ── GENERIC CLASS-BASED VIEWS (less code, more convention) ────────────────

# List + Create  →  GET /users/  and  POST /users/
class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]  # Registration is public
        return [IsAuthenticated()]


# Retrieve + Update + Delete  →  GET/PUT/PATCH/DELETE /users/{id}/
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False   # Soft delete
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── VIEWSET (combines all CRUD into one class) ────────────────────────────

class ProductViewSet(viewsets.ModelViewSet):
    """
    Automatically provides: list, create, retrieve, update, partial_update, destroy
    GET    /products/        → list
    POST   /products/        → create
    GET    /products/{id}/   → retrieve
    PUT    /products/{id}/   → update
    PATCH  /products/{id}/   → partial_update
    DELETE /products/{id}/   → destroy
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Each user only sees their own products
        return Product.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
```

### URL Routing

```python
# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")

urlpatterns = [
    path("me/", views.get_current_user),
    path("", views.UserListCreateView.as_view()),
    path("<int:pk>/", views.UserDetailView.as_view()),
    path("", include(router.urls)),   # Auto-generates all CRUD URLs
]

# myproject/urls.py
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/users/", include("users.urls")),
]
```

---

## 45.6 Django Authentication

```python
# Token-based auth (similar to JWT but server-stored)
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.authtoken.models import Token

# URL: POST /api/auth/token/  → returns {"token": "abc123..."}
path("api/auth/token/", obtain_auth_token),

# In requests:
# Authorization: Token abc123...

# JWT with djangorestframework-simplejwt (preferred for stateless)
# pip install djangorestframework-simplejwt
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns += [
    path("api/token/", TokenObtainPairView.as_view()),         # POST → access + refresh
    path("api/token/refresh/", TokenRefreshView.as_view()),    # POST → new access token
]

# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}
```

---

## 45.7 Django Admin Panel

Django's killer feature — a fully automatic admin UI for your data.

```python
# users/admin.py
from django.contrib import admin
from .models import User, Product


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "username", "email", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["username", "email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "stock", "owner"]
    list_filter = ["price"]
    search_fields = ["name", "owner__username"]
    raw_id_fields = ["owner"]   # Avoid loading all users in dropdown
```

```bash
# Create superuser to access /admin/
python manage.py createsuperuser
python manage.py runserver
# Visit http://localhost:8000/admin/
```

---

## 45.8 Django vs FastAPI — Interview Decision Matrix

| Criteria | Use Django | Use FastAPI |
|---------|-----------|------------|
| Building a full website | ✅ Yes | ❌ Overkill |
| Need admin panel for content | ✅ Built-in | ❌ Build manually |
| Pure REST/GraphQL API | ❌ Heavy | ✅ Purpose-built |
| High-throughput microservice | ❌ Slower | ✅ 3–5x faster |
| ML model serving | ❌ | ✅ Async support |
| Team knows Django already | ✅ | Consider |
| Auto OpenAPI docs needed | ❌ Manual (drf-spectacular) | ✅ Built-in |
| WebSockets | ❌ Channels required | ✅ Native |

**Interview answer:** *"Both are excellent Python frameworks. I prefer FastAPI for greenfield APIs and microservices due to its performance, native async, and automatic OpenAPI docs. Django is my choice when the project needs an admin panel, rapid full-stack development, or when the team already has a Django codebase. I'm comfortable working with both."*

---

# Chapter 46: Microservices Architecture

## 46.1 Monolith vs Microservices

```
MONOLITH                          MICROSERVICES
────────                          ─────────────
┌──────────────────────┐          ┌──────────┐ ┌──────────┐
│    Single App        │          │  Users   │ │ Products │
│  ┌────────────────┐  │          │ Service  │ │ Service  │
│  │  User Logic    │  │          └────┬─────┘ └────┬─────┘
│  │  Product Logic │  │    →          │              │
│  │  Order Logic   │  │          ┌────┴─────┐ ┌────┴─────┐
│  │  Auth Logic    │  │          │  Orders  │ │  Auth    │
│  └────────────────┘  │          │ Service  │ │ Service  │
│                      │          └──────────┘ └──────────┘
│  Single Database     │          Each has its OWN database
└──────────────────────┘
```

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| Deployment | Deploy all at once | Deploy each independently |
| Scaling | Scale entire app | Scale only the bottleneck |
| Team size | Small teams | Large teams, multiple squads |
| Failure | One failure = all down | Isolated failures |
| Complexity | Simple to start | Complex operations |
| DB | Shared database | Database per service |
| Communication | In-process function call | Network call (HTTP/gRPC/queue) |
| Testing | Easier | Harder (integration tests) |

**When to use microservices:**
- Team is large (>20 engineers)
- Different services need different tech stacks
- Services have very different scaling needs
- You need independent deployments

---

## 46.2 Microservices Design Patterns

### Pattern 1: API Gateway

The single entry point for all client requests.

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENTS                             │
│   Mobile App    Web App    Third-party APIs             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                  API GATEWAY                            │
│   • Authentication & Authorization                      │
│   • Rate limiting                                       │
│   • Request routing                                     │
│   • SSL termination                                     │
│   • Request/Response transformation                     │
│   • Load balancing                                      │
└─────┬──────────────┬──────────────┬────────────────────┘
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Users   │  │ Products │  │  Orders  │
│ Service  │  │ Service  │  │ Service  │
│:8001     │  │:8002     │  │:8003     │
└──────────┘  └──────────┘  └──────────┘
```

**AWS implementation:** API Gateway → Lambda functions or ECS services

```python
# FastAPI as API Gateway (simple version)
# gateway/main.py
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="API Gateway")

SERVICES = {
    "users":    "http://users-service:8001",
    "products": "http://products-service:8002",
    "orders":   "http://orders-service:8003",
}


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    target_url = f"{SERVICES[service]}/{path}"
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=dict(request.headers),
            content=await request.body(),
            params=dict(request.query_params),
            timeout=30.0,
        )
    
    return JSONResponse(
        content=response.json(),
        status_code=response.status_code,
    )
```

---

### Pattern 2: Inter-Service Communication

#### Synchronous (REST/HTTP)

```python
# orders/main.py — Orders service calls Users service
import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()

USERS_SERVICE_URL = "http://users-service:8001"


async def get_user(user_id: int) -> dict:
    """Call Users microservice to verify user exists."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{USERS_SERVICE_URL}/api/v1/users/{user_id}",
            timeout=5.0,
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        response.raise_for_status()
        return response.json()


@app.post("/orders/")
async def create_order(user_id: int, product_id: int, quantity: int):
    # 1. Verify user exists (sync call to Users service)
    user = await get_user(user_id)
    
    # 2. Create order
    order = {"user_id": user_id, "product_id": product_id, "quantity": quantity}
    return {"order": order, "user": user["username"]}
```

#### Asynchronous (Message Queue — SQS/SNS)

```python
# orders/events.py — Publish events to SQS after order created
import boto3
import json
from datetime import datetime

sqs = boto3.client("sqs", region_name="us-east-1")
ORDER_CREATED_QUEUE = "https://sqs.us-east-1.amazonaws.com/123456/order-created"


def publish_order_created(order: dict):
    """
    Async communication: fire-and-forget.
    Notification service will consume this and send email.
    """
    message = {
        "event": "ORDER_CREATED",
        "order_id": order["id"],
        "user_id": order["user_id"],
        "timestamp": datetime.utcnow().isoformat(),
    }
    sqs.send_message(
        QueueUrl=ORDER_CREATED_QUEUE,
        MessageBody=json.dumps(message),
    )


# notifications/consumer.py — Notification service consumes from SQS
import boto3
import json

sqs = boto3.client("sqs", region_name="us-east-1")


def process_order_created(message_body: str):
    data = json.loads(message_body)
    user_id = data["user_id"]
    order_id = data["order_id"]
    # Send email/push notification
    print(f"Sending confirmation email for order {order_id} to user {user_id}")


def poll_queue():
    while True:
        response = sqs.receive_message(
            QueueUrl=ORDER_CREATED_QUEUE,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,   # Long polling
        )
        for message in response.get("Messages", []):
            process_order_created(message["Body"])
            sqs.delete_message(
                QueueUrl=ORDER_CREATED_QUEUE,
                ReceiptHandle=message["ReceiptHandle"],
            )
```

**Sync vs Async communication:**

```
Synchronous (REST):                Asynchronous (SQS/SNS):
┌──────────┐  HTTP req  ┌───────┐  ┌──────────┐  publish  ┌─────┐
│ Orders   │ ────────►  │ Users │  │ Orders   │ ────────►  │ SQS │
│ Service  │ ◄────────  │ Svc   │  │ Service  │            └──┬──┘
└──────────┘  response  └───────┘  └──────────┘               │ consume
                                                          ┌────▼────┐
Tight coupling, immediate          Loose coupling,        │ Notif.  │
response needed                    eventual consistency   │ Service │
                                                          └─────────┘
```

---

### Pattern 3: Circuit Breaker

Prevent cascading failures when a downstream service is down.

```python
# pip install pybreaker
import pybreaker
import httpx

# If 5 failures in 60s → open circuit for 30s
breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)


@breaker
async def call_users_service(user_id: int) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"http://users-service:8001/users/{user_id}")
        response.raise_for_status()
        return response.json()


async def get_user_safe(user_id: int) -> dict | None:
    try:
        return await call_users_service(user_id)
    except pybreaker.CircuitBreakerError:
        # Circuit is open — return cached/default data
        return {"id": user_id, "username": "unknown", "cached": True}
    except httpx.HTTPError:
        return None
```

---

### Pattern 4: Service Discovery

How microservices find each other on AWS.

```
┌─────────────────────────────────────────────────────────┐
│              SERVICE DISCOVERY ON AWS                   │
│                                                         │
│  Option 1: DNS-based (AWS Cloud Map / ECS Service       │
│            Discovery)                                   │
│                                                         │
│  users-service.local → 10.0.1.5:8001                   │
│  products-service.local → 10.0.2.3:8002                 │
│                                                         │
│  Option 2: Environment Variables (simple, works in ECS) │
│                                                         │
│  USERS_SERVICE_URL=http://users-service:8001            │
│  PRODUCTS_SERVICE_URL=http://products-service:8002      │
│                                                         │
│  Option 3: API Gateway (single DNS, routes internally)  │
│                                                         │
│  All traffic → api.example.com/users → users-service   │
│                api.example.com/products → products-svc  │
└─────────────────────────────────────────────────────────┘
```

```python
# config.py — environment-based service discovery
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Each service URL injected via env var (set in ECS task definition)
    users_service_url: str = "http://users-service:8001"
    products_service_url: str = "http://products-service:8002"
    orders_service_url: str = "http://orders-service:8003"

    class Config:
        env_file = ".env"


settings = Settings()
```

---

## 46.3 Microservices on AWS — Architecture

```
┌──────────────────────────────────────────────────────────┐
│              MICROSERVICES ON AWS                        │
│                                                          │
│  Internet                                                │
│      │                                                   │
│      ▼                                                   │
│  ┌──────────┐                                            │
│  │  Route53 │ ← DNS                                      │
│  └─────┬────┘                                            │
│        │                                                 │
│        ▼                                                 │
│  ┌──────────────┐                                        │
│  │     ALB      │ ← Load Balancer                        │
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌──────────────────────────────────────────────┐        │
│  │              ECS Cluster                     │        │
│  │                                              │        │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │        │
│  │  │  Users   │  │Products  │  │  Orders  │   │        │
│  │  │ Service  │  │ Service  │  │ Service  │   │        │
│  │  │ Fargate  │  │ Fargate  │  │ Fargate  │   │        │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘   │        │
│  └───────┼─────────────┼─────────────┼──────────┘        │
│          │             │             │                    │
│          ▼             ▼             ▼                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │  RDS     │  │  RDS     │  │  RDS     │                │
│  │ (Users)  │  │(Products)│  │ (Orders) │                │
│  └──────────┘  └──────────┘  └──────────┘                │
│                                                          │
│              SQS ← async events between services         │
└──────────────────────────────────────────────────────────┘
```

---

## 46.4 Microservices with AWS CDK

```python
# cdk/microservices_stack.py
from aws_cdk import (
    Stack, aws_ecs as ecs, aws_ecs_patterns as ecs_patterns,
    aws_ec2 as ec2, aws_sqs as sqs, aws_rds as rds,
)
from constructs import Construct


class MicroservicesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "MicroservicesVpc", max_azs=2)
        cluster = ecs.Cluster(self, "MicroservicesCluster", vpc=vpc)

        # Shared SQS queue for async events
        order_queue = sqs.Queue(self, "OrderCreatedQueue",
                                queue_name="order-created")

        # Users Service
        users_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "UsersService",
            cluster=cluster,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("services/users"),
                container_port=8001,
                environment={"SERVICE_NAME": "users"},
            ),
            desired_count=2,
            listener_port=8001,
        )

        # Orders Service (needs SQS access)
        orders_task = ecs.FargateTaskDefinition(self, "OrdersTask")
        orders_task.add_container(
            "OrdersContainer",
            image=ecs.ContainerImage.from_asset("services/orders"),
            environment={
                "ORDER_QUEUE_URL": order_queue.queue_url,
                "USERS_SERVICE_URL": f"http://{users_service.load_balancer.load_balancer_dns_name}:8001",
            },
            port_mappings=[ecs.PortMapping(container_port=8003)],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="orders"),
        )
        # Grant queue publish permission
        order_queue.grant_send_messages(orders_task.task_role)
```

---

## 46.5 Interview: Microservices Questions

**Q: How do you handle distributed transactions across microservices?**

> "I use the SAGA pattern. Instead of a single DB transaction, each service performs its own local transaction and publishes an event. If any step fails, compensating transactions roll back previous steps. For example: Order Created → Reserve Inventory → Charge Payment. If payment fails, a compensating event releases the inventory reservation."

**Q: How do you prevent data inconsistency between services?**

> "Each service owns its data (database per service pattern). For cross-service reads, I use event-driven synchronization — each service maintains a local read model updated by consuming events from other services. This is eventual consistency, which is acceptable for most use cases. For strict consistency requirements, I avoid distributing the transaction."

**Q: How do you debug issues across multiple microservices?**

> "Distributed tracing with AWS X-Ray or OpenTelemetry. Each request gets a unique trace ID that's passed in headers (`X-Trace-ID`) across all service calls. I can then see the full call chain in the X-Ray console, including which service added latency or returned an error."

---

# Chapter 47: CloudFormation Templates

## 47.1 What is CloudFormation?

AWS CloudFormation lets you define AWS infrastructure as YAML or JSON templates. AWS CDK compiles down to CloudFormation — understanding raw templates makes you a better CDK user and is explicitly tested in interviews.

```
You write:           AWS CDK reads:        AWS deploys:
┌──────────────┐     ┌──────────────┐      ┌──────────────┐
│ CDK Python   │ →   │CloudFormation│  →   │ Real AWS     │
│ (TypeScript) │     │ YAML/JSON    │      │ Resources    │
└──────────────┘     └──────────────┘      └──────────────┘
     OR                                    
┌──────────────┐                           ┌──────────────┐
│ Raw CF YAML  │         directly  →       │ Real AWS     │
└──────────────┘                           └──────────────┘
```

---

## 47.2 CloudFormation Template Structure

Every CloudFormation template has the same top-level sections:

```yaml
AWSTemplateFormatVersion: "2010-09-09"   # Always this value
Description: "My application stack"

# ── PARAMETERS ── (like function arguments, filled at deploy time) ─────────
Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Default: dev
    Description: "Deployment environment"
  
  InstanceType:
    Type: String
    Default: t3.micro

# ── MAPPINGS ── (like a lookup table / switch statement) ──────────────────
Mappings:
  EnvConfig:
    dev:
      DesiredCount: 1
      Cpu: 256
    prod:
      DesiredCount: 3
      Cpu: 1024

# ── CONDITIONS ── (like if/else for resources) ────────────────────────────
Conditions:
  IsProduction: !Equals [!Ref Environment, prod]

# ── RESOURCES ── (required — the actual AWS resources) ────────────────────
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "my-app-${Environment}-${AWS::AccountId}"

# ── OUTPUTS ── (values to expose after deploy, like return values) ─────────
Outputs:
  BucketName:
    Value: !Ref MyBucket
    Export:
      Name: !Sub "${AWS::StackName}-BucketName"
```

---

## 47.3 Intrinsic Functions (CloudFormation Built-ins)

```yaml
# !Ref — reference a parameter or resource
BucketName: !Ref MyBucketParameter

# !Sub — string substitution (like f-strings)
Name: !Sub "my-app-${Environment}-${AWS::Region}"
Name: !Sub
  - "arn:aws:s3:::${BucketName}/*"
  - BucketName: !Ref MyBucket

# !GetAtt — get an attribute of a resource
QueueArn: !GetAtt MyQueue.Arn
LambdaArn: !GetAtt MyFunction.Arn

# !ImportValue — import output from another stack
VpcId: !ImportValue "network-stack-VpcId"

# !If — conditional value
DesiredCount: !If [IsProduction, 3, 1]

# !Select — pick item from list
SubnetId: !Select [0, !Split [",", !Ref SubnetIds]]

# !Join — join list into string
PolicyArn: !Join [":", ["arn", "aws", "iam", "", "123456", "policy/MyPolicy"]]
```

---

## 47.4 Real Template: Lambda Function

```yaml
# lambda-stack.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: "FastAPI on Lambda with API Gateway"

Parameters:
  Environment:
    Type: String
    Default: dev
  LambdaS3Bucket:
    Type: String
    Description: "S3 bucket containing Lambda deployment package"
  LambdaS3Key:
    Type: String
    Description: "S3 key for Lambda ZIP"

Resources:

  # ── IAM Role for Lambda ────────────────────────────────────────────────
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "fastapi-lambda-role-${Environment}"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: DynamoDBAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:DeleteItem
                  - dynamodb:Query
                  - dynamodb:Scan
                Resource: !GetAtt UsersTable.Arn

  # ── Lambda Function ────────────────────────────────────────────────────
  FastAPIFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub "fastapi-app-${Environment}"
      Runtime: python3.11
      Handler: lambda_handler.handler    # file.function
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        S3Bucket: !Ref LambdaS3Bucket
        S3Key: !Ref LambdaS3Key
      Timeout: 30
      MemorySize: 512
      Environment:
        Variables:
          ENVIRONMENT: !Ref Environment
          TABLE_NAME: !Ref UsersTable
          LOG_LEVEL: !If [IsProduction, "WARNING", "DEBUG"]
      Layers:
        - !Ref DependenciesLayer

  # ── Lambda Layer (shared dependencies) ────────────────────────────────
  DependenciesLayer:
    Type: AWS::Lambda::LayerVersion
    Properties:
      LayerName: !Sub "fastapi-dependencies-${Environment}"
      Description: "FastAPI, Mangum, and other dependencies"
      Content:
        S3Bucket: !Ref LambdaS3Bucket
        S3Key: "layers/dependencies.zip"
      CompatibleRuntimes:
        - python3.11

  # ── API Gateway (HTTP API) ────────────────────────────────────────────
  HttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: !Sub "fastapi-api-${Environment}"
      ProtocolType: HTTP
      CorsConfiguration:
        AllowOrigins: ["*"]
        AllowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        AllowHeaders: ["Content-Type", "Authorization"]

  HttpApiIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref HttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !GetAtt FastAPIFunction.Arn
      PayloadFormatVersion: "2.0"

  HttpApiRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref HttpApi
      RouteKey: "$default"           # Catch all routes → Lambda
      Target: !Sub "integrations/${HttpApiIntegration}"

  HttpApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref HttpApi
      StageName: !Ref Environment
      AutoDeploy: true

  # ── Lambda Permission for API Gateway ────────────────────────────────
  LambdaApiGatewayPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref FastAPIFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${HttpApi}/*/*"

  # ── DynamoDB Table ────────────────────────────────────────────────────
  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub "users-${Environment}"
      BillingMode: PAY_PER_REQUEST   # On-demand, no capacity planning
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: email
          AttributeType: S
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: email-index
          KeySchema:
            - AttributeName: email
              KeyType: HASH
          Projection:
            ProjectionType: ALL

  # Conditions section (referenced above)
Conditions:
  IsProduction: !Equals [!Ref Environment, prod]

Outputs:
  ApiEndpoint:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
    Export:
      Name: !Sub "${AWS::StackName}-ApiEndpoint"

  LambdaFunctionName:
    Value: !Ref FastAPIFunction
    Export:
      Name: !Sub "${AWS::StackName}-LambdaFunction"
```

---

## 47.5 Real Template: ECS Fargate Service

```yaml
# ecs-fargate-stack.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: "FastAPI on ECS Fargate"

Parameters:
  Environment:
    Type: String
    Default: dev
  DockerImage:
    Type: String
    Description: "ECR image URI (e.g. 123456.dkr.ecr.us-east-1.amazonaws.com/myapp:latest)"
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>

Resources:

  # ── ECS Cluster ────────────────────────────────────────────────────────
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub "fastapi-cluster-${Environment}"
      CapacityProviders: [FARGATE, FARGATE_SPOT]
      ClusterSettings:
        - Name: containerInsights
          Value: enabled

  # ── CloudWatch Log Group ───────────────────────────────────────────────
  LogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/ecs/fastapi-${Environment}"
      RetentionInDays: 30

  # ── IAM Role for ECS Task ──────────────────────────────────────────────
  TaskExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

  TaskRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole

  # ── ECS Task Definition ────────────────────────────────────────────────
  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: !Sub "fastapi-task-${Environment}"
      Cpu: "512"
      Memory: "1024"
      NetworkMode: awsvpc
      RequiresCompatibilities: [FARGATE]
      ExecutionRoleArn: !GetAtt TaskExecutionRole.Arn
      TaskRoleArn: !GetAtt TaskRole.Arn
      ContainerDefinitions:
        - Name: fastapi-app
          Image: !Ref DockerImage
          PortMappings:
            - ContainerPort: 8000
              Protocol: tcp
          Environment:
            - Name: ENVIRONMENT
              Value: !Ref Environment
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref LogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: fastapi
          HealthCheck:
            Command: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
            Interval: 30
            Timeout: 5
            Retries: 3

  # ── Security Group ─────────────────────────────────────────────────────
  ServiceSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: "FastAPI ECS service security group"
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          CidrIp: "0.0.0.0/0"

  # ── Application Load Balancer ──────────────────────────────────────────
  LoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub "fastapi-alb-${Environment}"
      Subnets: !Ref SubnetIds
      SecurityGroups: [!Ref ServiceSecurityGroup]
      Scheme: internet-facing

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Port: 8000
      Protocol: HTTP
      VpcId: !Ref VpcId
      TargetType: ip
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30

  Listener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref LoadBalancer
      Port: 80
      Protocol: HTTP
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup

  # ── ECS Service ────────────────────────────────────────────────────────
  ECSService:
    Type: AWS::ECS::Service
    DependsOn: Listener      # Must wait for ALB listener
    Properties:
      ServiceName: !Sub "fastapi-service-${Environment}"
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref TaskDefinition
      DesiredCount: 2
      LaunchType: FARGATE
      NetworkConfiguration:
        AwsvpcConfiguration:
          Subnets: !Ref SubnetIds
          SecurityGroups: [!Ref ServiceSecurityGroup]
          AssignPublicIp: ENABLED
      LoadBalancers:
        - ContainerName: fastapi-app
          ContainerPort: 8000
          TargetGroupArn: !Ref TargetGroup
      DeploymentConfiguration:
        MinimumHealthyPercent: 50
        MaximumPercent: 200

  # ── Auto Scaling ───────────────────────────────────────────────────────
  ScalableTarget:
    Type: AWS::ApplicationAutoScaling::ScalableTarget
    Properties:
      MinCapacity: 2
      MaxCapacity: 10
      ResourceId: !Sub "service/${ECSCluster}/${ECSService.Name}"
      ScalableDimension: ecs:service:DesiredCount
      ServiceNamespace: ecs
      RoleARN: !Sub "arn:aws:iam::${AWS::AccountId}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService"

  CpuScalingPolicy:
    Type: AWS::ApplicationAutoScaling::ScalingPolicy
    Properties:
      PolicyName: CpuScaling
      PolicyType: TargetTrackingScaling
      ScalingTargetId: !Ref ScalableTarget
      TargetTrackingScalingPolicyConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ECSServiceAverageCPUUtilization
        TargetValue: 70.0    # Scale when CPU > 70%

Outputs:
  LoadBalancerDNS:
    Value: !GetAtt LoadBalancer.DNSName
    Export:
      Name: !Sub "${AWS::StackName}-ALB-DNS"
```

---

## 47.6 Deploying CloudFormation Templates

```bash
# Validate template syntax
aws cloudformation validate-template \
  --template-body file://lambda-stack.yaml

# Deploy (create or update)
aws cloudformation deploy \
  --template-file lambda-stack.yaml \
  --stack-name fastapi-lambda-dev \
  --parameter-overrides \
    Environment=dev \
    LambdaS3Bucket=my-deploy-bucket \
    LambdaS3Key=lambda/app.zip \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

# Describe stack outputs
aws cloudformation describe-stacks \
  --stack-name fastapi-lambda-dev \
  --query "Stacks[0].Outputs"

# Delete stack (tears down all resources)
aws cloudformation delete-stack --stack-name fastapi-lambda-dev

# View events (useful for debugging failures)
aws cloudformation describe-stack-events \
  --stack-name fastapi-lambda-dev \
  --query "StackEvents[?ResourceStatus=='CREATE_FAILED']"
```

---

## 47.7 CloudFormation vs AWS CDK — When to Use Which

| Scenario | Use CloudFormation | Use CDK |
|----------|-------------------|---------|
| Simple, static infrastructure | ✅ | ✅ |
| Complex logic (loops, conditions) | ❌ Verbose | ✅ Use Python loops |
| Reusable components (Constructs) | ❌ Nested stacks = complex | ✅ Constructs |
| Team knows Python/TypeScript | ❌ | ✅ |
| Existing CF templates to maintain | ✅ | ✅ CDK can import |
| New greenfield project | ❌ (harder) | ✅ Preferred |
| Strict compliance (raw template audit) | ✅ | ❌ (generated CF) |

**Key fact:** AWS CDK `cdk synth` generates a CloudFormation template. You can always inspect it:

```bash
cdk synth                          # Prints CloudFormation YAML to stdout
cdk synth > template.yaml          # Save to file for inspection/direct deploy
aws cloudformation deploy \
  --template-file cdk.out/MyStack.template.json \
  --stack-name my-stack \
  --capabilities CAPABILITY_IAM
```

---

## 47.8 Interview: IaC Questions

**Q: What's the difference between CloudFormation and AWS CDK?**

> "CloudFormation is AWS's native IaC service — you write YAML/JSON templates that describe resources, and AWS deploys them. AWS CDK is a higher-level framework where you write Python (or TypeScript) code that synthesizes to CloudFormation templates. CDK provides abstractions called Constructs that bundle multiple CF resources together, adds sensible defaults, and eliminates boilerplate. Under the hood, CDK always compiles to CloudFormation — so CDK stacks are just CloudFormation stacks. I prefer CDK for new projects because it removes repetition and allows loops, conditionals, and reuse. However, I'm comfortable reading and writing raw CloudFormation when needed, such as maintaining legacy stacks or debugging what CDK is generating."

**Q: How do you handle CloudFormation stack updates that could cause downtime?**

> "I use change sets — `aws cloudformation create-change-set` — to preview what will change before applying. For resources that would be replaced (like certain RDS changes), CloudFormation warns you. I always review change sets in CI/CD pipelines before auto-applying to production. For zero-downtime ECS deployments, I configure `MinimumHealthyPercent: 50` and `MaximumPercent: 200` in the ECS service so new tasks start before old ones are drained."

---

# Updated JD Coverage Summary

| JD Requirement | Coverage | Where |
|---------------|----------|-------|
| Python (strong expertise) | ✅ | All chapters |
| FastAPI framework | ✅ | Parts 1–4, Part 6 |
| **Django framework** | ✅ | **Chapter 45** (this file) |
| Docker & containerization | ✅ | Chapter 39 |
| Docker orchestration | ✅ | Part 5 (K8s), Chapter 39 |
| AWS Lambda | ✅ | Part 3, Part 4 |
| AWS ECS | ✅ | Ch. 13.2 (CDK), Ch. 47 (CF) |
| AWS Fargate | ✅ | Ch. 13.2 (CDK), Ch. 47 (CF) |
| CI/CD with GitHub Actions | ✅ | Chapter 40 |
| CloudFormation Templates | ✅ | **Chapter 47** (this file) |
| AWS CDK | ✅ | Parts 2, 4 |
| **Microservices architecture** | ✅ | **Chapter 46** (this file) |
| REST APIs | ✅ | All FastAPI chapters |
| Security best practices | ✅ | Chapter 5, Part 5 |
| Scalability & reliability | ✅ | Ch. 13.2, Ch. 44, Ch. 47 |
| Monitoring & troubleshooting | ✅ | Ch. 12.6, Ch. 42, Part 3 |
| Performance optimization | ✅ | Chapter 44, Part 3 |
| Debugging & problem-solving | ✅ | Part 6 (interview patterns) |

**All JD requirements are now covered.**
