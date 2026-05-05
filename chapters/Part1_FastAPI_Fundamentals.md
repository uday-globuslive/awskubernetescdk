# Part 1: FastAPI Fundamentals
## Building Production-Grade APIs with FastAPI

---

## 1.1 Introduction to FastAPI

FastAPI is a modern, high-performance Python web framework for building APIs. It is built on top of Starlette (ASGI framework) and Pydantic (data validation), offering automatic OpenAPI docs, type-safety, and async support out of the box.

**Key Advantages**:
- **Performance**: Comparable to Node.js and Go — one of the fastest Python frameworks
- **Type Safety**: Uses Python type hints for request/response validation
- **Auto Documentation**: Swagger UI at `/docs`, ReDoc at `/redoc` — auto-generated
- **Async Native**: First-class `async/await` support
- **Dependency Injection**: Built-in DI system for reusability and testability

---

## 1.2 Installation and Project Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
.venv\Scripts\activate        # Windows

# Install FastAPI with all extras
pip install "fastapi[all]"
# Or minimal:
pip install fastapi uvicorn[standard]

# Production dependencies
pip install fastapi uvicorn[standard] pydantic[email] python-multipart
pip install sqlalchemy asyncpg alembic
pip install python-jose[cryptography] passlib[bcrypt]
pip install boto3 aiobotocore

# Save requirements
pip freeze > requirements.txt
```

### Project Structure

```
myapi/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance + routers
│   ├── config.py            # Settings with Pydantic BaseSettings
│   ├── dependencies.py      # Shared dependencies (db, auth)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # SQLAlchemy ORM models
│   │   └── order.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py          # Pydantic request/response models
│   │   └── order.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py         # /users endpoints
│   │   └── orders.py        # /orders endpoints
│   ├── services/
│   │   ├── user_service.py  # Business logic
│   │   └── order_service.py
│   └── db/
│       ├── session.py       # Database session
│       └── init_db.py
├── tests/
│   ├── conftest.py
│   └── test_users.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 1.3 Your First FastAPI Application

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.routers import users, orders
from app.db.session import engine
from app.models import Base
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created")
    yield
    # Shutdown
    await engine.dispose()
    print("✓ Database connections closed")


app = FastAPI(
    title=settings.app_name,
    description="Production-grade FastAPI application",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,    # Disable in prod
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ────────────────────────────────────────────
app.include_router(users.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": app.version}
```

---

## 1.4 Pydantic Models — Request/Response Validation

```python
# app/schemas/user.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain an uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain a digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain a special character')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}   # Allow ORM model → Pydantic


class UserList(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int
```

---

## 1.5 SQLAlchemy Async ORM Models

```python
# app/models/user.py
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

---

## 1.6 Database Session Management

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,          # Test connections before use
    pool_recycle=3600,           # Recycle connections every hour
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,      # Don't expire objects after commit (safer for async)
    autocommit=False,
    autoflush=False,
)


# app/dependencies.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## 1.7 CRUD Routes with Full Error Handling

```python
# app/routers/users.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserList
from app.services.auth import get_password_hash, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: DbDep):
    """Create a new user account."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {user_in.email} is already registered"
        )
    
    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    await db.flush()   # Get the ID without committing
    await db.refresh(user)
    return user


@router.get("", response_model=UserList)
async def list_users(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
):
    """List users with pagination and optional search."""
    offset = (page - 1) * size
    
    query = select(User).where(User.is_active == True)
    count_query = select(func.count()).select_from(User).where(User.is_active == True)
    
    if search:
        search_filter = User.username.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    total = (await db.execute(count_query)).scalar_one()
    users = (await db.execute(query.offset(offset).limit(size))).scalars().all()
    
    return UserList(
        items=users,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: DbDep, current_user: CurrentUser):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot update other users")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: DbDep, current_user: CurrentUser):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot delete other users")
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete
    user.is_active = False
    await db.flush()
```

---

## 1.8 Configuration with Pydantic BaseSettings

```python
# app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "My FastAPI App"
    debug: bool = False
    secret_key: str
    
    # Database
    database_url: str   # postgresql+asyncpg://user:pass@host/db
    
    # Auth
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]
    
    # AWS
    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

## 1.9 Running the Application

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Gunicorn (better process management)
gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keepalive 5 \
  --access-logfile -

# Docker
docker build -t myapi .
docker run -p 8000:8000 --env-file .env myapi
```

---

## 1.10 Interview Q&A

**Q: What is FastAPI's relationship with ASGI and how does async work?**
A: FastAPI is built on Starlette (an ASGI framework). ASGI (Asynchronous Server Gateway Interface) allows the server to handle many concurrent connections without blocking. When you mark a path function with `async def`, FastAPI runs it in the event loop — awaiting I/O operations (DB queries, HTTP calls) releases the event loop to serve other requests. Regular `def` functions are automatically run in a thread pool to avoid blocking the event loop. Never use blocking I/O (requests, synchronous psycopg2) in async functions.

**Q: What is Pydantic V2 and what changed from V1?**
A: Pydantic V2 (2023) rewrote the core in Rust, making validation 5-50x faster. Key changes: `BaseModel.dict()` → `model_dump()`, `BaseModel.json()` → `model_dump_json()`, `@validator` → `@field_validator`, `orm_mode = True` → `model_config = {"from_attributes": True}`, `__fields__` → `model_fields`. FastAPI 0.100+ fully supports Pydantic V2. Migration from V1 requires updating these patterns but the performance gain is significant in high-throughput APIs.

**Q: How do you handle database migrations in production?**
A: Use Alembic with SQLAlchemy. Run `alembic init alembic` to set up, then `alembic revision --autogenerate -m "add users table"` to generate migrations from model changes. In production: (1) Never run `create_all` in production lifespan — use Alembic migrations; (2) Apply migrations in deployment pipeline before new code goes live; (3) Keep migrations backward-compatible (additive changes only during blue-green deployments); (4) Test rollbacks with `alembic downgrade -1`.
