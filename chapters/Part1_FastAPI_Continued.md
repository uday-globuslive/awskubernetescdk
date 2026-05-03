# Part I: FastAPI Fundamentals (Continued)
## Chapters 4-9: Advanced FastAPI Concepts

---

# Chapter 4: Dependency Injection

## 4.1 Understanding Dependencies

### What is Dependency Injection?

Imagine you're making a sandwich. You need bread, lettuce, tomato, and cheese. Instead of growing wheat, farming vegetables, and milking a cow yourself, you **depend** on a grocery store to provide these ingredients.

**Dependency Injection** is the same concept in programming. Instead of a function creating everything it needs, you "inject" (provide) what it needs from outside.

### Why Use Dependency Injection?

```
WITHOUT Dependency Injection:
┌─────────────────────────────────┐
│ def get_user():                 │
│     db = create_database()      │  ← Creates its own database
│     user = db.query("SELECT...") │
│     db.close()                  │  ← Has to manage connection
│     return user                 │
└─────────────────────────────────┘
Problem: Every function creates its own database connection!

WITH Dependency Injection:
┌─────────────────────────────────┐
│ def get_user(db: Database):     │  ← Receives database
│     return db.query("SELECT...") │  ← Just uses it
└─────────────────────────────────┘
Benefit: One database connection is shared!
```

### Benefits

1. **Reusability** - Write once, use everywhere
2. **Testability** - Easy to swap fake dependencies for testing
3. **Cleaner Code** - Functions do one thing
4. **Centralized Logic** - Change in one place affects everywhere

---

## 4.2 Creating Dependencies

### Basic Dependency

```python
from fastapi import FastAPI, Depends

app = FastAPI()

# This is a dependency function
def get_common_parameters(skip: int = 0, limit: int = 10):
    """
    Common parameters used by many endpoints.
    Returns a dictionary of parameters.
    """
    return {"skip": skip, "limit": limit}

# Use the dependency with Depends()
@app.get("/items")
def get_items(commons: dict = Depends(get_common_parameters)):
    return {
        "message": "Getting items",
        "skip": commons["skip"],
        "limit": commons["limit"]
    }

@app.get("/users")
def get_users(commons: dict = Depends(get_common_parameters)):
    return {
        "message": "Getting users",
        "skip": commons["skip"],
        "limit": commons["limit"]
    }
```

### How It Works

```
Request: GET /items?skip=5&limit=20
               ↓
FastAPI sees: Depends(get_common_parameters)
               ↓
Calls: get_common_parameters(skip=5, limit=20)
               ↓
Returns: {"skip": 5, "limit": 20}
               ↓
Passes to: get_items(commons={"skip": 5, "limit": 20})
               ↓
Your function runs with the dependency data
```

### Class-Based Dependencies

```python
from fastapi import FastAPI, Depends

app = FastAPI()

class CommonQueryParams:
    def __init__(self, skip: int = 0, limit: int = 10, search: str = None):
        self.skip = skip
        self.limit = limit
        self.search = search

@app.get("/items")
def get_items(commons: CommonQueryParams = Depends(CommonQueryParams)):
    return {
        "skip": commons.skip,
        "limit": commons.limit,
        "search": commons.search
    }

# Shorter syntax (same result)
@app.get("/users")
def get_users(commons: CommonQueryParams = Depends()):
    return {
        "skip": commons.skip,
        "limit": commons.limit,
        "search": commons.search
    }
```

---

## 4.3 Sub-dependencies

### Dependencies That Depend on Other Dependencies

```python
from fastapi import FastAPI, Depends

app = FastAPI()

# Level 1: Basic dependency
def get_database_connection():
    """Simulates getting a database connection"""
    print("Getting database connection...")
    return {"connection": "db_connection_object"}

# Level 2: Depends on Level 1
def get_user_repository(db = Depends(get_database_connection)):
    """Creates a user repository using the database"""
    print("Creating user repository...")
    return {"repository": "user_repo", "db": db}

# Level 3: Uses the user repository
@app.get("/users/{user_id}")
def get_user(user_id: int, repo = Depends(get_user_repository)):
    """Gets a user using the repository"""
    return {
        "user_id": user_id,
        "from_repo": repo
    }
```

### Execution Order

```
Request: GET /users/1
          ↓
Step 1: get_database_connection() runs
          → Returns {"connection": "db_connection_object"}
          ↓
Step 2: get_user_repository(db=...) runs
          → Returns {"repository": "user_repo", "db": ...}
          ↓
Step 3: get_user(user_id=1, repo=...) runs
          → Returns final response
```

### Practical Example: Authentication Chain

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

# Step 1: Extract token from request
def get_token(authorization: str = None):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    return authorization.replace("Bearer ", "")

# Step 2: Validate token and get user ID
def get_current_user_id(token: str = Depends(get_token)):
    # In reality, you'd verify the JWT here
    if token == "valid-token":
        return 123  # User ID
    raise HTTPException(status_code=401, detail="Invalid token")

# Step 3: Get full user data
def get_current_user(user_id: int = Depends(get_current_user_id)):
    # In reality, you'd query the database
    return {"id": user_id, "name": "Alice", "email": "alice@example.com"}

# Use the full chain
@app.get("/me")
def get_my_profile(user = Depends(get_current_user)):
    return user

@app.get("/my-settings")
def get_my_settings(user = Depends(get_current_user)):
    return {"user": user["name"], "settings": {"theme": "dark"}}
```

---

## 4.4 Dependencies with Yield (Context Managers)

### What's the Problem?

Sometimes you need to:
1. Set something up before the request
2. Clean it up after the request

Example: Open a database connection → Use it → Close it

### Using Yield

```python
from fastapi import FastAPI, Depends

app = FastAPI()

def get_database():
    """
    This dependency:
    1. Opens a connection before the request
    2. Provides it to the function
    3. Closes it after the request (even if there's an error)
    """
    print("Opening database connection...")
    db = {"connection": "active"}  # Simulated connection
    
    try:
        yield db  # Provide the connection
    finally:
        print("Closing database connection...")
        db["connection"] = "closed"

@app.get("/items")
def get_items(db = Depends(get_database)):
    print(f"Using database: {db}")
    return {"items": ["apple", "banana"]}
```

### Execution Flow

```
Request arrives
      ↓
"Opening database connection..."
      ↓
yield db (connection is given to the function)
      ↓
"Using database: {'connection': 'active'}"
      ↓
Response is sent
      ↓
"Closing database connection..."
(finally block runs even if there's an error)
```

### Real-World Example: Database Session

```python
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Database setup
engine = create_engine("sqlite:///./app.db")
SessionLocal = sessionmaker(bind=engine)

# Dependency with cleanup
def get_db():
    """
    Creates a database session for each request
    and ensures it's closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
```

### Multiple Cleanup Steps

```python
def get_resources():
    # Setup
    db = open_database()
    cache = connect_cache()
    
    try:
        yield {"db": db, "cache": cache}
    finally:
        # Cleanup - runs in reverse order
        cache.disconnect()
        db.close()
```

---

## 4.5 Global Dependencies

### What are Global Dependencies?

Sometimes you want a dependency to run for EVERY request, not just specific endpoints.

### Adding Global Dependencies

```python
from fastapi import FastAPI, Depends, HTTPException

# Dependency that checks API key
def verify_api_key(x_api_key: str = None):
    if x_api_key != "secret-api-key":
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

# Apply to entire application
app = FastAPI(dependencies=[Depends(verify_api_key)])

@app.get("/items")
def get_items():
    return {"items": ["apple", "banana"]}

@app.get("/users")
def get_users():
    return {"users": ["Alice", "Bob"]}

# Both endpoints now require the API key!
```

### Router-Level Dependencies

```python
from fastapi import FastAPI, APIRouter, Depends

app = FastAPI()

# Dependency for admin routes
def require_admin(role: str = "user"):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

# Create router with dependency
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin)]
)

@admin_router.get("/dashboard")
def admin_dashboard():
    return {"message": "Admin dashboard"}

@admin_router.get("/users")
def admin_users():
    return {"message": "Admin user management"}

# Include the router
app.include_router(admin_router)
```

### Combining Dependencies

```python
from fastapi import FastAPI, Depends

def log_request():
    print("Request logged")

def check_rate_limit():
    print("Rate limit checked")

def verify_auth():
    print("Auth verified")

# Multiple global dependencies
app = FastAPI(
    dependencies=[
        Depends(log_request),
        Depends(check_rate_limit),
        Depends(verify_auth)
    ]
)
```

---

## 4.6 Dependency Overrides for Testing

### The Problem with Testing

When testing, you don't want to:
- Connect to real databases
- Call real external APIs
- Send real emails

### Solution: Override Dependencies

```python
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

app = FastAPI()

# Real dependency (connects to database)
def get_database():
    return {"type": "real", "data": get_from_real_db()}

@app.get("/users")
def get_users(db = Depends(get_database)):
    return {"database": db["type"]}

# --- Testing ---

# Fake dependency for testing
def get_fake_database():
    return {"type": "fake", "data": [{"id": 1, "name": "Test User"}]}

# Override the dependency
app.dependency_overrides[get_database] = get_fake_database

# Now testing uses fake database
client = TestClient(app)
response = client.get("/users")
print(response.json())  # {"database": "fake"}

# Reset overrides when done
app.dependency_overrides = {}
```

### Complete Testing Example

```python
# app.py
from fastapi import FastAPI, Depends

app = FastAPI()

def get_email_service():
    return RealEmailService()  # Sends real emails

@app.post("/send-welcome-email")
def send_welcome(email: str, service = Depends(get_email_service)):
    service.send(email, "Welcome!")
    return {"status": "sent"}

# test_app.py
from fastapi.testclient import TestClient
from app import app, get_email_service

class FakeEmailService:
    def __init__(self):
        self.sent_emails = []
    
    def send(self, to, message):
        self.sent_emails.append({"to": to, "message": message})

fake_service = FakeEmailService()

def get_fake_email_service():
    return fake_service

# Override
app.dependency_overrides[get_email_service] = get_fake_email_service

def test_welcome_email():
    client = TestClient(app)
    response = client.post("/send-welcome-email?email=test@example.com")
    
    assert response.status_code == 200
    assert len(fake_service.sent_emails) == 1
    assert fake_service.sent_emails[0]["to"] == "test@example.com"
```

---

# Chapter 5: Authentication & Security

## 5.1 OAuth2 with Password Flow

### What is OAuth2?

OAuth2 is a standard way to handle authentication (proving who you are) and authorization (what you're allowed to do).

**Password Flow** means the user provides their username and password directly to your application.

```
User                    Your App                    Database
  │                        │                           │
  │── Username/Password ──→│                           │
  │                        │── Verify credentials ────→│
  │                        │←── User data ─────────────│
  │                        │                           │
  │←── Access Token ───────│                           │
  │                        │                           │
  │── Request + Token ────→│                           │
  │                        │── Verify token            │
  │←── Protected data ─────│                           │
```

### Basic Implementation

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()

# This tells FastAPI where the token comes from
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fake user database
fake_users_db = {
    "alice": {
        "username": "alice",
        "password": "secret123",  # In real apps, this would be hashed!
        "email": "alice@example.com"
    }
}

# Login endpoint
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    User sends username and password,
    receives an access token.
    """
    user = fake_users_db.get(form_data.username)
    
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # In reality, you'd create a proper JWT token here
    return {"access_token": user["username"], "token_type": "bearer"}

# Dependency to get current user from token
def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Extract user from the token.
    """
    user = fake_users_db.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user

# Protected endpoint
@app.get("/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Returns the current user's information.
    Only accessible with a valid token.
    """
    return current_user
```

### Testing the Flow

```
Step 1: Login
POST /token
Content-Type: application/x-www-form-urlencoded
Body: username=alice&password=secret123

Response: {"access_token": "alice", "token_type": "bearer"}

Step 2: Access protected endpoint
GET /users/me
Authorization: Bearer alice

Response: {"username": "alice", "email": "alice@example.com"}
```

---

## 5.2 JWT Tokens

### What is JWT?

JWT (JSON Web Token) is a secure way to transmit information between parties.

```
JWT = Header.Payload.Signature

Example:
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbGljZSJ9.signature_here
        ↓                    ↓                    ↓
      Header              Payload             Signature
   (algorithm)         (user data)         (verification)
```

### Why Use JWT?

1. **Stateless** - Server doesn't need to store session data
2. **Portable** - Can be used across different services
3. **Self-contained** - Contains all needed information
4. **Secure** - Signed to prevent tampering

### Implementation

```python
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = "your-secret-key-keep-it-secret"  # Change in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

# Fake database
fake_users_db = {
    "alice": {
        "username": "alice",
        "email": "alice@example.com",
        "hashed_password": pwd_context.hash("secret123"),
        "disabled": False
    }
}

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if password matches hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Create password hash."""
    return pwd_context.hash(password)

def get_user(db: dict, username: str) -> Optional[UserInDB]:
    """Get user from database."""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(db: dict, username: str, password: str):
    """Verify username and password."""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode token and return current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if user is active."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token."""
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile."""
    return current_user
```

### How JWT Works Visually

```
Login Request:
POST /token
username=alice&password=secret123
            ↓
Server verifies credentials
            ↓
Creates JWT:
{
  "sub": "alice",      ← Subject (username)
  "exp": 1699999999    ← Expiration time
}
            ↓
Signs with SECRET_KEY
            ↓
Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

─────────────────────────────────────────

Protected Request:
GET /users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            ↓
Server decodes JWT
            ↓
Verifies signature with SECRET_KEY
            ↓
Checks expiration
            ↓
Extracts username: "alice"
            ↓
Returns user data
```

---

## 5.3 API Key Authentication

### What is API Key Authentication?

A simpler alternative to OAuth2, where clients send a secret key with each request.

```
Client sends: X-API-Key: abc123secret
Server checks: Is this key valid?
If yes: Process request
If no: Reject with 403
```

### Implementation

```python
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

app = FastAPI()

# Define where to look for the API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# Valid API keys (in reality, store in database)
API_KEYS = {
    "abc123secret": {"user": "alice", "permissions": ["read", "write"]},
    "xyz789key": {"user": "bob", "permissions": ["read"]}
}

async def get_api_key(
    api_key_header: str = Security(api_key_header),
    api_key_query: str = Security(api_key_query)
):
    """
    Check for API key in header or query parameter.
    """
    # Check header first
    if api_key_header and api_key_header in API_KEYS:
        return API_KEYS[api_key_header]
    
    # Then check query parameter
    if api_key_query and api_key_query in API_KEYS:
        return API_KEYS[api_key_query]
    
    # No valid key found
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing API key"
    )

@app.get("/data")
async def get_protected_data(api_key_data: dict = Security(get_api_key)):
    """
    Protected endpoint requiring valid API key.
    """
    return {
        "message": "Here's your protected data!",
        "user": api_key_data["user"],
        "permissions": api_key_data["permissions"]
    }

# Test with:
# GET /data?api_key=abc123secret
# OR
# GET /data with header X-API-Key: abc123secret
```

---

## 5.4 OAuth2 Scopes

### What are Scopes?

Scopes let you give different levels of access to different users or applications.

```
User A: ["read"]          → Can only read data
User B: ["read", "write"] → Can read and write
Admin:  ["read", "write", "admin"] → Full access
```

### Implementation

```python
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Define available scopes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access"
    }
)

# User database with scopes
users_db = {
    "alice": {"password": "secret", "scopes": ["read", "write"]},
    "admin": {"password": "admin123", "scopes": ["read", "write", "admin"]}
}

def create_token_with_scopes(username: str, scopes: List[str]) -> str:
    """Create JWT with scopes."""
    payload = {
        "sub": username,
        "scopes": scopes
    }
    return jwt.encode(payload, "secret", algorithm="HS256")

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
):
    """Verify token and check scopes."""
    # Decode token
    payload = jwt.decode(token, "secret", algorithms=["HS256"])
    username = payload.get("sub")
    token_scopes = payload.get("scopes", [])
    
    # Check if user has required scopes
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {scope}"
            )
    
    return {"username": username, "scopes": token_scopes}

# Endpoints with different scope requirements
@app.get("/items")
async def read_items(user = Security(get_current_user, scopes=["read"])):
    """Requires 'read' scope."""
    return {"items": ["apple", "banana"], "user": user}

@app.post("/items")
async def create_item(user = Security(get_current_user, scopes=["write"])):
    """Requires 'write' scope."""
    return {"message": "Item created", "user": user}

@app.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    user = Security(get_current_user, scopes=["admin"])
):
    """Requires 'admin' scope."""
    return {"message": f"Item {item_id} deleted", "user": user}
```

---

## 5.5 CORS Configuration

### What is CORS?

CORS (Cross-Origin Resource Sharing) controls which websites can access your API.

```
Your API: https://api.example.com
Website A: https://mysite.com → Allowed ✅
Website B: https://hacker.com → Blocked ❌
```

### Why is CORS Needed?

Browsers block requests from one website to another by default (security feature). CORS tells the browser which cross-origin requests are allowed.

### Implementation

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Define allowed origins
origins = [
    "http://localhost:3000",      # React dev server
    "https://mywebsite.com",      # Production website
    "https://admin.mywebsite.com" # Admin panel
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Which origins can access
    allow_credentials=True,         # Allow cookies
    allow_methods=["*"],            # Allow all HTTP methods
    allow_headers=["*"],            # Allow all headers
)

@app.get("/api/data")
def get_data():
    return {"message": "This can be accessed from allowed origins"}
```

### CORS Options Explained

```python
app.add_middleware(
    CORSMiddleware,
    
    # Which websites can access your API
    allow_origins=["https://mysite.com"],
    # Or use ["*"] for any website (not recommended for production)
    
    # Allow cookies and authentication
    allow_credentials=True,
    
    # Which HTTP methods are allowed
    allow_methods=["GET", "POST"],  # Only GET and POST
    # Or ["*"] for all methods
    
    # Which headers clients can send
    allow_headers=["Authorization", "Content-Type"],
    # Or ["*"] for all headers
    
    # Cache preflight requests (in seconds)
    max_age=600  # 10 minutes
)
```

---

## 5.6 Security Best Practices

### 1. Never Store Plain Passwords

```python
# ❌ BAD - Never do this!
user = {"password": "secret123"}

# ✅ GOOD - Always hash passwords
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

hashed = pwd_context.hash("secret123")
# "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

# To verify
pwd_context.verify("secret123", hashed)  # True
```

### 2. Use Environment Variables for Secrets

```python
# ❌ BAD - Never hardcode secrets!
SECRET_KEY = "my-secret-key"

# ✅ GOOD - Use environment variables
import os
SECRET_KEY = os.environ.get("SECRET_KEY")

# Or use pydantic settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    database_url: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. Validate and Sanitize Input

```python
from pydantic import BaseModel, Field, validator
import re

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(min_length=8)
    
    @validator('email')
    def validate_email(cls, v):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError('Invalid email')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain uppercase')
        if not re.search(r"[0-9]", v):
            raise ValueError('Password must contain number')
        return v
```

### 4. Rate Limiting

```python
from fastapi import FastAPI, Request, HTTPException
from collections import defaultdict
import time

app = FastAPI()

# Simple rate limiter (use Redis in production)
request_counts = defaultdict(list)
RATE_LIMIT = 100  # requests per minute

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        t for t in request_counts[client_ip]
        if current_time - t < 60
    ]
    
    # Check rate limit
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    # Record this request
    request_counts[client_ip].append(current_time)
    
    return await call_next(request)
```

### 5. HTTPS Only

```python
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Redirect HTTP to HTTPS
app.add_middleware(HTTPSRedirectMiddleware)
```

### Security Checklist

```
□ Hash passwords with bcrypt
□ Use JWT with short expiration
□ Store secrets in environment variables
□ Validate all input with Pydantic
□ Use HTTPS in production
□ Configure CORS properly
□ Implement rate limiting
□ Log security events
□ Keep dependencies updated
□ Use security headers
```

---

*Continue to Part 2 for Chapters 6-9: Database Integration, Advanced Features, Testing, and Project Structure...*
