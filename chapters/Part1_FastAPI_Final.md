# Part I: FastAPI Fundamentals (Final)
## Chapters 6-9: Database, Advanced Features, Testing & Best Practices

---

# Chapter 6: Database Integration

## 6.1 SQLAlchemy Setup

### What is SQLAlchemy?

SQLAlchemy is Python's most popular database toolkit. It lets you interact with databases using Python code instead of writing SQL.

```
Without SQLAlchemy:
"SELECT * FROM users WHERE id = 1"

With SQLAlchemy:
User.query.filter_by(id=1).first()
```

### Installation

```bash
pip install sqlalchemy
pip install psycopg2-binary  # For PostgreSQL
# OR
pip install pymysql          # For MySQL
```

### Basic Setup

```python
# database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL format:
# postgresql://username:password@host:port/database_name
# sqlite:///./database.db (for local SQLite)

DATABASE_URL = "sqlite:///./app.db"

# Create engine (the connection to the database)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Only for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()
```

### Creating Models

```python
# models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"  # Table name in database
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to other table
    posts = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship back to User
    author = relationship("User", back_populates="posts")
```

### Database Dependency

```python
# main.py

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get database session
def get_db():
    """
    Creates a new database session for each request.
    Closes it when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Using the database
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users

@app.post("/users")
def create_user(email: str, username: str, db: Session = Depends(get_db)):
    user = models.User(email=email, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)  # Refresh to get the ID
    return user
```

### Visual Flow

```
Request: POST /users
           ↓
get_db() creates database session
           ↓
Session passed to create_user()
           ↓
db.add(user) - Prepares to insert
           ↓
db.commit() - Actually inserts into database
           ↓
db.refresh(user) - Gets generated ID
           ↓
Response sent
           ↓
get_db() finally block closes session
```

---

## 6.2 Async Database with databases Library

### Why Async?

Synchronous database calls block your application while waiting for the database. Async allows handling other requests during that wait time.

```
Synchronous:
Request 1 → [Wait for DB] → Response
            Request 2 waits...

Asynchronous:
Request 1 → [Start DB query] → 
Request 2 → [Start DB query] →
Request 1 ← [DB responds] → Response
Request 2 ← [DB responds] → Response
```

### Setup

```bash
pip install databases
pip install aiosqlite  # For SQLite
# OR
pip install asyncpg    # For PostgreSQL
```

### Implementation

```python
# database.py

from databases import Database
import sqlalchemy

DATABASE_URL = "sqlite:///./app.db"

# Async database connection
database = Database(DATABASE_URL)

# SQLAlchemy metadata for table definitions
metadata = sqlalchemy.MetaData()

# Define tables
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True),
    sqlalchemy.Column("username", sqlalchemy.String),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True),
)

# Create tables
engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)
```

### Using Async Database

```python
# main.py

from fastapi import FastAPI
from database import database, users

app = FastAPI()

# Connect to database on startup
@app.on_event("startup")
async def startup():
    await database.connect()

# Disconnect on shutdown
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Async endpoint
@app.get("/users")
async def get_users():
    query = users.select()
    return await database.fetch_all(query)

@app.post("/users")
async def create_user(email: str, username: str):
    query = users.insert().values(email=email, username=username)
    last_record_id = await database.execute(query)
    return {"id": last_record_id, "email": email, "username": username}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    query = users.select().where(users.c.id == user_id)
    return await database.fetch_one(query)
```

---

## 6.3 MongoDB with Motor

### What is MongoDB?

MongoDB is a NoSQL database that stores data as JSON-like documents instead of tables.

```
SQL (Tables):
┌────┬─────────┬──────────────────┐
│ id │ name    │ email            │
├────┼─────────┼──────────────────┤
│ 1  │ Alice   │ alice@example.com│
│ 2  │ Bob     │ bob@example.com  │
└────┴─────────┴──────────────────┘

MongoDB (Documents):
{
  "_id": "1",
  "name": "Alice",
  "email": "alice@example.com",
  "preferences": {"theme": "dark"}
}
```

### Setup

```bash
pip install motor   # Async MongoDB driver
pip install pymongo
```

### Implementation

```python
# database.py

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "myapp"

# MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

# Collections (like tables)
users_collection = database["users"]
posts_collection = database["posts"]

# Helper to convert MongoDB ObjectId
def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "is_active": user.get("is_active", True)
    }
```

### Using MongoDB

```python
# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from bson import ObjectId
from database import users_collection, user_helper

app = FastAPI()

# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool

# CRUD Operations
@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    user_dict = user.dict()
    user_dict["is_active"] = True
    
    result = await users_collection.insert_one(user_dict)
    
    new_user = await users_collection.find_one({"_id": result.inserted_id})
    return user_helper(new_user)

@app.get("/users", response_model=List[UserResponse])
async def get_users():
    users = []
    async for user in users_collection.find():
        users.append(user_helper(user))
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_helper(user)

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}
```

---

## 6.4 Database Migrations with Alembic

### What are Migrations?

When you change your database models (add columns, change types), migrations update the actual database.

```
Before: User table has (id, name, email)
Change: Add "phone" column
Migration: ALTER TABLE users ADD COLUMN phone VARCHAR
After: User table has (id, name, email, phone)
```

### Setup

```bash
pip install alembic
alembic init alembic  # Creates alembic folder
```

### Configuration

```python
# alembic/env.py (edit these lines)

from database import Base, DATABASE_URL

config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata
```

### Creating and Running Migrations

```bash
# Create a migration after changing models
alembic revision --autogenerate -m "Add phone to users"

# Run migrations (update database)
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See migration history
alembic history
```

### Example Migration File

```python
# alembic/versions/xxxx_add_phone_to_users.py

def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))

def downgrade():
    op.drop_column('users', 'phone')
```

---

## 6.5 Repository Pattern

### What is the Repository Pattern?

A pattern that separates data access logic from business logic. Think of it as a middleman between your code and the database.

```
Without Repository:
Endpoint → Database (mixed logic)

With Repository:
Endpoint → Repository → Database (clean separation)
```

### Implementation

```python
# repositories/user_repository.py

from sqlalchemy.orm import Session
from models import User
from typing import List, Optional

class UserRepository:
    """
    Handles all database operations for Users.
    Business logic doesn't know about the database.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self) -> List[User]:
        return self.db.query(User).all()
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def create(self, email: str, username: str) -> User:
        user = User(email=email, username=username)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
```

### Using the Repository

```python
# main.py

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from repositories.user_repository import UserRepository

app = FastAPI()

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

@app.get("/users")
def get_users(repo: UserRepository = Depends(get_user_repository)):
    return repo.get_all()

@app.get("/users/{user_id}")
def get_user(user_id: int, repo: UserRepository = Depends(get_user_repository)):
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users")
def create_user(
    email: str,
    username: str,
    repo: UserRepository = Depends(get_user_repository)
):
    existing = repo.get_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return repo.create(email, username)
```

---

## 6.6 Unit of Work Pattern

### What is Unit of Work?

A pattern that groups database operations into a single transaction. Either all succeed or all fail.

```
Without Unit of Work:
1. Create order ✅
2. Reduce inventory ❌ (error!)
3. Create payment ❌ (never happens)
Result: Order exists but inventory not reduced - DATA INCONSISTENCY!

With Unit of Work:
1. Create order
2. Reduce inventory (error!)
3. ROLLBACK everything
Result: Nothing changed - DATA CONSISTENT!
```

### Implementation

```python
# unit_of_work.py

from sqlalchemy.orm import Session
from database import SessionLocal
from repositories.user_repository import UserRepository
from repositories.order_repository import OrderRepository

class UnitOfWork:
    """
    Manages database transactions.
    Ensures all operations succeed or all fail.
    """
    
    def __init__(self):
        self.session: Session = None
        self.users: UserRepository = None
        self.orders: OrderRepository = None
    
    def __enter__(self):
        self.session = SessionLocal()
        self.users = UserRepository(self.session)
        self.orders = OrderRepository(self.session)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Error occurred - rollback
            self.session.rollback()
        self.session.close()
    
    def commit(self):
        """Commit the transaction."""
        self.session.commit()
    
    def rollback(self):
        """Rollback the transaction."""
        self.session.rollback()
```

### Using Unit of Work

```python
# main.py

from fastapi import FastAPI, HTTPException
from unit_of_work import UnitOfWork

app = FastAPI()

@app.post("/orders")
def create_order_with_user(user_email: str, product_id: int):
    """
    Creates a user and order in a single transaction.
    If anything fails, everything is rolled back.
    """
    with UnitOfWork() as uow:
        try:
            # Create user
            user = uow.users.create(email=user_email, username="new_user")
            
            # Create order
            order = uow.orders.create(user_id=user.id, product_id=product_id)
            
            # Commit both operations
            uow.commit()
            
            return {"user_id": user.id, "order_id": order.id}
        
        except Exception as e:
            # Rollback on any error
            uow.rollback()
            raise HTTPException(status_code=500, detail=str(e))
```

---

# Chapter 7: Advanced Features

## 7.1 Background Tasks

### What are Background Tasks?

Tasks that run after the response is sent to the user. Useful for things that take time but don't need to delay the response.

```
Normal Request:
User → Send Email (5 seconds) → Response
Total: 5+ seconds

With Background Task:
User → Response (instant)
       ↓
       Send Email (happens in background)
Total: Instant response!
```

### Implementation

```python
from fastapi import FastAPI, BackgroundTasks
from time import sleep

app = FastAPI()

def send_email(email: str, message: str):
    """
    Simulate sending an email.
    This runs AFTER the response is sent.
    """
    print(f"Sending email to {email}...")
    sleep(5)  # Simulate email sending
    print(f"Email sent to {email}")

@app.post("/register")
def register_user(
    email: str,
    background_tasks: BackgroundTasks
):
    """
    Register user and send welcome email.
    User gets response immediately!
    """
    # Add email task to background
    background_tasks.add_task(send_email, email, "Welcome to our app!")
    
    # Return immediately
    return {"message": f"User registered. Welcome email being sent to {email}"}

# Multiple background tasks
@app.post("/order")
def create_order(
    user_email: str,
    product: str,
    background_tasks: BackgroundTasks
):
    # Multiple tasks
    background_tasks.add_task(send_email, user_email, f"Order confirmed: {product}")
    background_tasks.add_task(update_inventory, product)
    background_tasks.add_task(notify_warehouse, product)
    
    return {"message": "Order created"}
```

---

## 7.2 WebSockets

### What are WebSockets?

WebSockets enable real-time, two-way communication between client and server. Unlike HTTP (request → response), WebSockets keep a connection open.

```
HTTP:
Client → Request → Server → Response → Connection closed

WebSocket:
Client ←→ Persistent Connection ←→ Server
Messages can go both ways, anytime!
```

### Use Cases
- Chat applications
- Live notifications
- Real-time games
- Stock tickers
- Collaborative editing

### Implementation

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    await manager.broadcast(f"Client {client_id} joined the chat")
    
    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            # Broadcast to all connected clients
            await manager.broadcast(f"{client_id}: {data}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client {client_id} left the chat")
```

### Client-Side JavaScript

```html
<!DOCTYPE html>
<html>
<body>
    <input id="messageInput" type="text">
    <button onclick="sendMessage()">Send</button>
    <ul id="messages"></ul>

    <script>
        const ws = new WebSocket("ws://localhost:8000/ws/user123");
        
        ws.onmessage = function(event) {
            const messages = document.getElementById('messages');
            const li = document.createElement('li');
            li.textContent = event.data;
            messages.appendChild(li);
        };
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            ws.send(input.value);
            input.value = '';
        }
    </script>
</body>
</html>
```

---

## 7.3 File Uploads and Downloads

### File Uploads

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List
import shutil
import os

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Single file upload
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a single file.
    UploadFile provides async methods and file info.
    """
    # Check file type
    if not file.filename.endswith(('.jpg', '.png', '.pdf')):
        raise HTTPException(400, "Invalid file type")
    
    # Save the file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": os.path.getsize(file_path)
    }

# Multiple file upload
@app.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """Upload multiple files at once."""
    uploaded = []
    
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded.append(file.filename)
    
    return {"uploaded": uploaded, "count": len(uploaded)}

# File with additional data
from pydantic import BaseModel

class FileMetadata(BaseModel):
    description: str
    category: str

@app.post("/upload-with-data")
async def upload_with_metadata(
    file: UploadFile = File(...),
    description: str = None,
    category: str = None
):
    # Process file and metadata
    return {
        "filename": file.filename,
        "description": description,
        "category": category
    }
```

### File Downloads

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
import io

app = FastAPI()

# Download a file
@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")
    
    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

# Generate and download a file
@app.get("/generate-report")
def generate_report():
    """Generate a CSV report on the fly."""
    
    # Create CSV content
    csv_content = "Name,Email,Age\n"
    csv_content += "Alice,alice@example.com,25\n"
    csv_content += "Bob,bob@example.com,30\n"
    
    # Return as downloadable file
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"}
    )
```

---

## 7.4 Streaming Responses

### What is Streaming?

Instead of sending all data at once, streaming sends it piece by piece. Good for large files or real-time data.

```
Normal Response:
Server → [Entire 1GB file loads in memory] → Send all at once

Streaming Response:
Server → [Read chunk] → Send → [Read chunk] → Send → ...
Memory usage stays low!
```

### Implementation

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import time

app = FastAPI()

# Stream a large file
def generate_large_file():
    """Generator that yields file chunks."""
    for i in range(1000):
        yield f"Line {i}: This is some content\n"
        
@app.get("/stream-file")
def stream_large_file():
    return StreamingResponse(
        generate_large_file(),
        media_type="text/plain"
    )

# Server-Sent Events (SSE)
def event_stream():
    """Generate server-sent events."""
    for i in range(10):
        time.sleep(1)  # Wait 1 second
        yield f"data: Event {i}\n\n"

@app.get("/events")
def get_events():
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )

# Stream database query results
async def stream_users():
    """Stream users from database one by one."""
    async for user in users_collection.find():
        yield json.dumps(user_helper(user)) + "\n"

@app.get("/stream-users")
async def get_stream_users():
    return StreamingResponse(
        stream_users(),
        media_type="application/x-ndjson"
    )
```

---

## 7.5 Middleware

### What is Middleware?

Code that runs before and/or after every request. Like a checkpoint that every request passes through.

```
Request → Middleware (before) → Your Endpoint → Middleware (after) → Response
```

### Creating Middleware

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

# Basic middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Adds a header showing how long the request took.
    """
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    print(f"Incoming: {request.method} {request.url}")
    
    response = await call_next(request)
    
    print(f"Outgoing: Status {response.status_code}")
    return response

# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Check authentication for all requests."""
    
    # Skip auth for certain paths
    if request.url.path in ["/", "/docs", "/health"]:
        return await call_next(request)
    
    # Check for token
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"}
        )
    
    return await call_next(request)
```

---

## 7.6 Lifespan Events (startup/shutdown)

### What are Lifespan Events?

Code that runs when the app starts up or shuts down. Perfect for setting up connections and cleaning up resources.

### Modern Approach (lifespan context manager)

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before 'yield' runs on startup.
    Code after 'yield' runs on shutdown.
    """
    # STARTUP
    print("Starting up...")
    app.state.db = await connect_to_database()
    app.state.redis = await connect_to_redis()
    
    yield  # Application runs here
    
    # SHUTDOWN
    print("Shutting down...")
    await app.state.db.disconnect()
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"message": "App is running!"}
```

### Legacy Approach (on_event decorators)

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Runs when the application starts."""
    print("Starting up...")
    # Connect to database
    # Load ML models
    # Initialize caches

@app.on_event("shutdown")
async def shutdown_event():
    """Runs when the application shuts down."""
    print("Shutting down...")
    # Close database connections
    # Save state
    # Clean up resources
```

---

## 7.7 Custom Exception Handlers

### What are Exception Handlers?

Functions that handle errors in a custom way instead of the default error response.

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Custom exception class
class ItemNotFoundException(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

# Handler for custom exception
@app.exception_handler(ItemNotFoundException)
async def item_not_found_handler(request: Request, exc: ItemNotFoundException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "ItemNotFound",
            "message": f"Item with ID {exc.item_id} was not found",
            "path": str(request.url)
        }
    )

# Use the custom exception
@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in items_db:
        raise ItemNotFoundException(item_id)
    return items_db[item_id]

# Override default HTTPException handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

# Handle ALL other exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc)  # Remove in production!
        }
    )
```

---

# Chapter 8: Testing FastAPI

## 8.1 TestClient Basics

### What is TestClient?

A tool that simulates HTTP requests to your API without actually starting a server.

### Setup

```bash
pip install pytest httpx
```

### Basic Testing

```python
# test_main.py

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_read_item():
    response = client.get("/items/1")
    assert response.status_code == 200
    assert "item_id" in response.json()

def test_create_item():
    response = client.post(
        "/items",
        json={"name": "Test Item", "price": 9.99}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"

def test_invalid_item():
    response = client.get("/items/999")
    assert response.status_code == 404
```

### Running Tests

```bash
pytest test_main.py -v
```

---

## 8.2 Testing with pytest

### Fixtures for Reusable Setup

```python
# conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db
from database import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides = {}

@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123"
    }
```

### Using Fixtures

```python
# test_users.py

def test_create_user(client, sample_user):
    response = client.post("/users", json=sample_user)
    assert response.status_code == 201
    assert response.json()["email"] == sample_user["email"]

def test_get_users(client, sample_user):
    # Create a user first
    client.post("/users", json=sample_user)
    
    # Get all users
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_duplicate_email(client, sample_user):
    # Create first user
    client.post("/users", json=sample_user)
    
    # Try to create duplicate
    response = client.post("/users", json=sample_user)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
```

---

## 8.3 Async Testing

### Testing Async Endpoints

```python
# test_async.py

import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/async-endpoint")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_multiple_async_requests():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make multiple requests concurrently
        responses = await asyncio.gather(
            client.get("/endpoint1"),
            client.get("/endpoint2"),
            client.get("/endpoint3")
        )
        
        for response in responses:
            assert response.status_code == 200
```

---

## 8.4-8.6 Mocking, Integration Testing, Coverage

### Mocking Dependencies

```python
from unittest.mock import Mock, patch

def test_with_mock():
    # Mock the email service
    mock_email = Mock()
    mock_email.send.return_value = True
    
    app.dependency_overrides[get_email_service] = lambda: mock_email
    
    response = client.post("/send-email?to=test@example.com")
    
    assert response.status_code == 200
    mock_email.send.assert_called_once()
```

### Running with Coverage

```bash
pip install pytest-cov

pytest --cov=app --cov-report=html
# Opens coverage report in browser
```

---

# Chapter 9: Project Structure & Best Practices

## 9.1 Recommended Project Layout

```
my-fastapi-project/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── config.py            # Settings and configuration
│   ├── dependencies.py      # Shared dependencies
│   │
│   ├── routers/             # Route handlers
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── items.py
│   │   └── auth.py
│   │
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   │
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── item_service.py
│   │
│   ├── repositories/        # Database operations
│   │   ├── __init__.py
│   │   └── user_repository.py
│   │
│   └── utils/               # Utility functions
│       ├── __init__.py
│       └── helpers.py
│
├── tests/                   # Test files
│   ├── __init__.py
│   ├── conftest.py
│   └── test_users.py
│
├── alembic/                 # Database migrations
│   └── versions/
│
├── requirements.txt         # Dependencies
├── .env                     # Environment variables
├── .gitignore
└── README.md
```

---

## 9.2-9.6 Router Organization, Settings, Logging, Error Handling, Versioning

### Router Organization

```python
# app/routers/users.py
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)

@router.get("/")
def get_users():
    return []

@router.get("/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}

# app/main.py
from fastapi import FastAPI
from routers import users, items, auth

app = FastAPI()

app.include_router(users.router)
app.include_router(items.router)
app.include_router(auth.router)
```

### Settings Management

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My API"
    debug: bool = False
    database_url: str
    secret_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### API Versioning

```python
from fastapi import FastAPI

app = FastAPI()

# Version 1
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/users")
def get_users_v1():
    return {"version": "1", "users": []}

# Version 2
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/users")
def get_users_v2():
    return {"version": "2", "users": [], "total": 0}

app.include_router(v1_router)
app.include_router(v2_router)
```

---

*Continue to Part 2 for AWS CDK Chapters...*
