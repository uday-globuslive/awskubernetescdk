# Part 1 (Final): FastAPI — WebSockets, Performance & Production Deployment

---

## 3.1 WebSockets

```python
# app/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Any
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for real-time features."""
    
    def __init__(self):
        # room_id -> list of active WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def broadcast(self, room_id: str, message: Any) -> None:
        """Send message to all connections in a room."""
        connections = self.active_connections.get(room_id, [])
        disconnected = []
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            connections.remove(conn)
    
    async def send_personal(self, websocket: WebSocket, message: Any) -> None:
        await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str,    # Query parameter for auth
):
    # Validate token before accepting
    from app.services.auth import validate_token
    user = await validate_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, room_id)
    
    # Notify others in room
    await manager.broadcast(room_id, {
        "type": "user_joined",
        "user": user.username,
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                await manager.broadcast(room_id, {
                    "type": "message",
                    "user": user.username,
                    "content": data["content"],
                })
            elif data.get("type") == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(room_id, {
            "type": "user_left",
            "user": user.username,
        })
```

---

## 3.2 Server-Sent Events (SSE)

```python
# app/routers/events.py
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


async def event_generator(topic: str):
    """Generate SSE events from a message queue."""
    import asyncio
    
    # Subscribe to real-time updates (e.g., from Redis pub/sub)
    while True:
        # Simulate fetching updates
        event_data = {"status": "processing", "progress": 50}
        
        yield f"data: {json.dumps(event_data)}\n\n"
        
        await asyncio.sleep(1)
        
        # Send keep-alive comment every 30 seconds
        yield ": keep-alive\n\n"


@router.get("/stream/{job_id}")
async def stream_job_progress(job_id: str):
    """Stream job progress as Server-Sent Events."""
    return StreamingResponse(
        event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering
        },
    )
```

---

## 3.3 Caching with Redis

```python
# app/cache.py
import json
from functools import wraps
from typing import Any
import redis.asyncio as redis
from app.config import settings

redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


async def get_cache(key: str) -> Any | None:
    value = await redis_client.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cache(key: str, value: Any, ttl: int = 300) -> None:
    await redis_client.setex(key, ttl, json.dumps(value))


async def delete_cache(pattern: str) -> int:
    """Delete all keys matching pattern."""
    keys = await redis_client.keys(pattern)
    if keys:
        return await redis_client.delete(*keys)
    return 0


def cached(key_prefix: str, ttl: int = 300):
    """Decorator to cache endpoint responses."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from prefix + relevant kwargs
            cache_key = f"{key_prefix}:{':'.join(str(v) for v in kwargs.values())}"
            
            cached_value = await get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            await set_cache(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# Usage in router
@router.get("/products/{product_id}")
@cached(key_prefix="product", ttl=600)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Not found")
    return ProductResponse.model_validate(product).model_dump()
```

---

## 3.4 Production Dockerfile

```dockerfile
# Dockerfile — Multi-stage build
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ──────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Install runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

---

## 3.5 Alembic Database Migrations

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.models import Base
from app.config import settings

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,          # Detect column type changes
                compare_server_default=True, # Detect default value changes
            )
        )
        async with context.begin_transaction():
            await conn.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```bash
# Migration commands
alembic revision --autogenerate -m "add users table"
alembic upgrade head          # Apply all pending migrations
alembic downgrade -1          # Roll back one migration
alembic history               # Show migration history
alembic current               # Show current version
```

---

## 3.6 OpenAPI Customization

```python
# app/main.py — customize OpenAPI schema
from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    schema = get_openapi(
        title="My API",
        version="1.0.0",
        description="Production-ready FastAPI service",
        routes=app.routes,
    )
    
    # Add security scheme
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Apply security to all routes except auth and health
    for path, path_item in schema["paths"].items():
        if path in ["/api/v1/auth/token", "/health"]:
            continue
        for operation in path_item.values():
            operation["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
```

---

## 3.7 Interview Q&A

**Q: How do you handle database connection pooling in production FastAPI?**
A: Use SQLAlchemy's async engine with tuned pool settings: `pool_size` (persistent connections, default 5 — set to ~20 for production), `max_overflow` (extra connections beyond pool_size, default 10), `pool_pre_ping=True` (test connections before use — catches stale connections), `pool_recycle=3600` (recycle connections hourly — prevents idle-in-transaction issues). For PostgreSQL on AWS RDS, consider RDS Proxy which handles connection pooling at the infrastructure level, allowing thousands of Lambda functions to connect without exhausting DB connections. For asyncpg driver, use separate `min_size`/`max_size` settings.

**Q: How do you secure a FastAPI application for production?**
A: (1) Disable `/docs` and `/redoc` in production (`docs_url=None`); (2) Use HTTPS only — terminate TLS at ALB/CloudFront; (3) Set strict CORS origins (not `*` in production); (4) Rate limit with Redis-backed slowapi; (5) Validate all inputs with Pydantic (use strict types, constrain lengths); (6) Hash passwords with bcrypt; (7) Use JWT with short expiry + refresh tokens; (8) Never log sensitive data (passwords, tokens, PII); (9) Set security headers via middleware (`X-Content-Type-Options`, `X-Frame-Options`); (10) Use Secrets Manager for credentials, not environment variables with plain text.

**Q: What is the best way to handle long-running tasks in FastAPI?**
A: For tasks < 5 seconds, `BackgroundTasks` works well (runs after response is sent). For longer tasks, use a proper task queue: **Celery + Redis** (mature, feature-rich, works well with FastAPI), or **AWS SQS + Lambda** (serverless, scales to zero). Pattern: POST to `/tasks/process` → immediately return `{"task_id": "abc123", "status": "queued"}` → enqueue to SQS/Celery → worker processes asynchronously → GET `/tasks/abc123/status` returns progress. Use DynamoDB or Redis to store task state. Never use `asyncio.sleep()` loops for polling in the web process.
