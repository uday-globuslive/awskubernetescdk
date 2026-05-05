# Part 1 (Continued): FastAPI — Authentication, Middleware & Advanced Patterns

---

## 2.1 JWT Authentication System

```python
# app/services/auth.py
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.dependencies import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: Any, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": str(subject), "iat": now, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: Any) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user
```

```python
# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.user import User
from app.schemas.auth import Token, TokenRefresh
from app.services.auth import (
    verify_password, create_access_token, create_refresh_token,
    get_current_user
)
from jose import JWTError, jwt
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and return access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
    
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(body: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Issue new access token using refresh token."""
    try:
        payload = jwt.decode(body.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )
```

---

## 2.2 Middleware

```python
# app/middleware/logging.py
import time
import uuid
import structlog
from fastapi import Request, Response

logger = structlog.get_logger()


async def logging_middleware(request: Request, call_next) -> Response:
    """Log all requests with timing and correlation ID."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start = time.perf_counter()
    
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
        client_ip=request.client.host if request.client else "unknown",
    )
    
    response = await call_next(request)
    
    duration_ms = (time.perf_counter() - start) * 1000
    
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
    )
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
    return response


# app/middleware/rate_limit.py
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._cache: dict[str, list[float]] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.period
        
        # Clean old entries
        self._cache[client_ip] = [t for t in self._cache[client_ip] if t > window_start]
        
        if len(self._cache[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(self.period)},
            )
        
        self._cache[client_ip].append(now)
        return await call_next(request)
```

---

## 2.3 Exception Handlers

```python
# app/exceptions.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import structlog

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Return structured validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation failed", "errors": errors},
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """Handle database constraint violations."""
        logger.warning("db_integrity_error", error=str(exc.orig))
        return JSONResponse(
            status_code=409,
            content={"detail": "Resource conflict — a record with these values already exists"},
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "unhandled_exception",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
```

---

## 2.4 Background Tasks and Task Queue

```python
# app/routers/emails.py
from fastapi import APIRouter, BackgroundTasks, Depends
from app.services.email import send_welcome_email
from app.schemas.user import UserResponse

router = APIRouter()


@router.post("/register")
async def register_user(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await create_user(user_in, db)
    
    # Run email sending in the background (non-blocking)
    background_tasks.add_task(
        send_welcome_email,
        email=user.email,
        username=user.username,
    )
    
    return user


# For heavy tasks, use Celery or AWS SQS instead
# app/workers/tasks.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_bulk_email(self, user_ids: list[int], template: str):
    try:
        # Process bulk email
        pass
    except Exception as exc:
        self.retry(exc=exc)
```

---

## 2.5 File Uploads to S3

```python
# app/routers/uploads.py
import boto3
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.config import settings
from app.services.auth import get_current_user

router = APIRouter(prefix="/uploads", tags=["Uploads"])

s3 = boto3.client("s3", region_name=settings.aws_region)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
):
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type {file.content_type} not allowed")
    
    # Read and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")
    
    # Generate safe key
    import uuid
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    key = f"avatars/{current_user.id}/{uuid.uuid4()}.{ext}"
    
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=contents,
        ContentType=file.content_type,
        ServerSideEncryption="aws:kms",
        Metadata={"user_id": str(current_user.id)},
    )
    
    url = f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
    return {"url": url, "key": key}
```

---

## 2.6 Testing FastAPI Applications

```python
# tests/conftest.py
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.dependencies import get_db
from app.models import Base
from app.services.auth import get_password_hash

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSession() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db: AsyncSession):
    from app.models.user import User
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPass123!"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# tests/test_auth.py
import pytest

@pytest.mark.asyncio
async def test_login_success(client, test_user):
    response = await client.post("/api/v1/auth/token", data={
        "username": "test@example.com",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    response = await client.post("/api/v1/auth/token", data={
        "username": "test@example.com",
        "password": "WrongPassword!",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_authenticated(client, test_user):
    # Login first
    login_resp = await client.post("/api/v1/auth/token", data={
        "username": "test@example.com",
        "password": "TestPass123!",
    })
    token = login_resp.json()["access_token"]
    
    response = await client.get(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```

---

## 2.7 Interview Q&A

**Q: How does FastAPI's dependency injection work and what are its benefits?**
A: FastAPI's DI uses Python type annotations. You declare a parameter with `Depends(some_function)` and FastAPI calls that function, passing its return value. Dependencies can themselves have dependencies (nested DI graph). Benefits: (1) Reusable logic (auth, DB session, pagination params) defined once; (2) Automatically closed/cleaned up after request (db session rollback on error); (3) Easily overridden in tests via `app.dependency_overrides`; (4) FastAPI builds and caches the dependency graph per request. For class-based dependencies, FastAPI supports `Depends(MyClass())` — the class instance is created once and reused.

**Q: What is the difference between `async def` and `def` in FastAPI path functions?**
A: `async def` functions run in the event loop and should only call async I/O (`await db.query()`, `await httpx.get()`). Regular `def` functions are automatically run in a thread pool executor, so blocking calls (synchronous `requests.get()`, `time.sleep()`) won't block the event loop. The worst pattern is mixing: calling `time.sleep()` inside `async def` blocks the entire event loop for all concurrent requests. Use `await asyncio.sleep()` in async functions. For CPU-intensive work, use `run_in_executor` with a process pool.

**Q: How do you implement API rate limiting in FastAPI?**
A: Several approaches: (1) **In-memory middleware** (simple, single-process only — resets on restart, doesn't work across multiple workers); (2) **Redis-backed rate limiting** using `slowapi` library (distributed, survives restarts, works across workers); (3) **AWS API Gateway throttling** (before requests even reach FastAPI — preferred for AWS deployments). For production, Redis-backed rate limiting with `slowapi` is common: `@limiter.limit("100/minute")` decorator on routes. The key should include user ID (authenticated) or IP address (unauthenticated).
