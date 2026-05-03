# Part I: FastAPI Fundamentals
## Complete Detailed Guide for Beginners

---

# Chapter 1: Introduction to FastAPI

## 1.1 What is FastAPI?

Imagine you want to build a website or mobile app. The app needs to communicate with a server to get data (like user information, product lists, etc.). **FastAPI** is a tool that helps you build that server-side communication system, called an **API** (Application Programming Interface).

### Simple Analogy
Think of a restaurant:
- **You (the customer)** = The mobile app or website
- **The waiter** = The API
- **The kitchen** = The database/server

When you order food, you don't go directly to the kitchen. You tell the waiter what you want, and the waiter brings it back. Similarly, an API takes requests from apps and returns the right data.

**FastAPI** is a modern, fast framework for building these "waiters" (APIs) using Python.

### Key Characteristics
```
FastAPI = Fast + API
         ↓      ↓
    High Speed  Application Programming Interface
```

**Created by:** Sebastián Ramírez in 2018
**Language:** Python 3.7+
**Type:** Web framework for building APIs

### What Can You Build with FastAPI?
1. **REST APIs** - Most common web APIs
2. **Real-time applications** - Chat apps, live notifications
3. **Microservices** - Small, independent services
4. **Machine Learning APIs** - Serve ML models
5. **Backend for mobile apps** - Handle user data, authentication

---

## 1.2 Why FastAPI? (Performance, Type Hints, Auto Documentation)

### Three Main Superpowers of FastAPI

#### 1. SPEED (Performance)
FastAPI is one of the fastest Python frameworks available.

**Speed Comparison:**
```
Framework         Requests per Second
─────────────────────────────────────
FastAPI           ~15,000+ requests/sec
Flask             ~5,000 requests/sec
Django            ~3,000 requests/sec
```

**Why is it so fast?**
- Built on **Starlette** (for web handling)
- Built on **Pydantic** (for data validation)
- Supports **async/await** (handles multiple requests simultaneously)

**Real-world analogy:** 
Imagine a cashier at a store. A regular cashier (Flask) helps one customer at a time. FastAPI is like having a super-efficient cashier who can start processing the next customer while waiting for payment from the current one.

#### 2. TYPE HINTS (Automatic Validation)
Type hints tell Python what type of data to expect.

**Without Type Hints (Old Way):**
```python
def greet(name):
    return f"Hello, {name}"

# Problem: What if someone passes a number?
greet(123)  # Works but might cause issues later
```

**With Type Hints (FastAPI Way):**
```python
def greet(name: str) -> str:
    return f"Hello, {name}"

# Now Python knows 'name' should be a string
# FastAPI will automatically validate this!
```

**What FastAPI does with type hints:**
```
User sends: {"age": "twenty"}
              ↓
FastAPI checks: Is "twenty" an integer? NO!
              ↓
Returns error: "age must be an integer"
```

You don't write validation code - FastAPI does it automatically!

#### 3. AUTOMATIC DOCUMENTATION
FastAPI automatically creates interactive documentation for your API.

**What you get for FREE:**
- **Swagger UI** - Beautiful, interactive documentation at `/docs`
- **ReDoc** - Alternative documentation at `/redoc`

**Example:**
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}
```

Just by writing this code, you get:
- A webpage showing all your API endpoints
- The ability to test your API directly from the browser
- Automatic request/response examples

---

## 1.3 FastAPI vs Flask vs Django

Let's compare the three most popular Python web frameworks:

### Quick Comparison Table

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| **Speed** | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐⭐ Medium | ⭐⭐ Slower |
| **Learning Curve** | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Easiest | ⭐⭐ Steepest |
| **Built-in Features** | ⭐⭐⭐ Moderate | ⭐⭐ Minimal | ⭐⭐⭐⭐⭐ Most |
| **Async Support** | ⭐⭐⭐⭐⭐ Native | ⭐⭐ Limited | ⭐⭐⭐ Added later |
| **Auto Documentation** | ⭐⭐⭐⭐⭐ Yes | ❌ No | ❌ No |
| **Data Validation** | ⭐⭐⭐⭐⭐ Automatic | ❌ Manual | ⭐⭐⭐ With forms |

### When to Use Each

**Choose FastAPI when:**
- Building APIs (not full websites with HTML)
- Performance is critical
- You want automatic documentation
- You're building microservices
- You're serving machine learning models

**Choose Flask when:**
- Building simple applications
- You want maximum flexibility
- Learning web development
- You need lots of third-party extensions

**Choose Django when:**
- Building full websites with admin panels
- You need user authentication, database ORM built-in
- Building content management systems
- You want "batteries included"

### Code Comparison

**The same API in all three frameworks:**

**FastAPI:**
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello/{name}")
def hello(name: str):
    return {"message": f"Hello, {name}"}
```

**Flask:**
```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/hello/<name>")
def hello(name):
    return jsonify({"message": f"Hello, {name}"})
```

**Django:** (Requires more setup - urls.py, views.py, settings.py)
```python
# views.py
from django.http import JsonResponse

def hello(request, name):
    return JsonResponse({"message": f"Hello, {name}"})

# urls.py
urlpatterns = [
    path('hello/<str:name>/', views.hello),
]
```

---

## 1.4 Installation and Setup

### Step 1: Prerequisites

**What you need:**
1. **Python 3.7 or higher** - Check with: `python --version`
2. **pip** (Python package manager) - Usually comes with Python
3. **A code editor** - VS Code recommended

### Step 2: Create a Project Folder

```bash
# Windows
mkdir my-fastapi-project
cd my-fastapi-project

# Create a virtual environment (keeps your project isolated)
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

**What's a Virtual Environment?**
Think of it as a separate room for each project. Each room has its own tools (libraries). This prevents conflicts between different projects.

### Step 3: Install FastAPI and Uvicorn

```bash
pip install fastapi uvicorn
```

**What are these?**
- **FastAPI** - The framework itself
- **Uvicorn** - The server that runs your FastAPI app (like an engine that powers your car)

### Step 4: Verify Installation

```bash
pip list | grep -i fastapi
pip list | grep -i uvicorn
```

You should see:
```
fastapi    0.100.0 (or higher)
uvicorn    0.23.0 (or higher)
```

### Optional: Install All Features

```bash
pip install "fastapi[all]"
```

This includes:
- `uvicorn` - Server
- `python-multipart` - For file uploads
- `jinja2` - For templates
- `python-jose` - For JWT tokens
- And more useful tools

---

## 1.5 Your First FastAPI Application

Let's build your first API step by step!

### Step 1: Create the File

Create a file called `main.py`:

```python
# main.py

# Step 1: Import FastAPI
from fastapi import FastAPI

# Step 2: Create an instance of FastAPI
app = FastAPI()

# Step 3: Define your first endpoint
@app.get("/")
def home():
    return {"message": "Welcome to my first API!"}

# Step 4: Add another endpoint
@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello, {name}!"}
```

### Understanding Each Line

```python
from fastapi import FastAPI
```
↑ This imports the FastAPI class from the fastapi library

```python
app = FastAPI()
```
↑ This creates your API application. Think of it as starting your restaurant.

```python
@app.get("/")
```
↑ This is a **decorator**. It tells FastAPI:
- `get` = This handles GET requests (reading data)
- `"/"` = The URL path (root of your website)

```python
def home():
    return {"message": "Welcome to my first API!"}
```
↑ This is the function that runs when someone visits the URL.
- Returns a dictionary, which FastAPI automatically converts to JSON

### Step 2: Run the Server

In your terminal:

```bash
uvicorn main:app --reload
```

**What does this mean?**
- `main` = Your file name (main.py)
- `app` = The FastAPI instance you created
- `--reload` = Automatically restart when you change code (for development)

### Step 3: Test Your API

Open your browser and visit:
- `http://127.0.0.1:8000` - See your welcome message
- `http://127.0.0.1:8000/hello/John` - See personalized greeting
- `http://127.0.0.1:8000/docs` - Interactive documentation!

### What You'll See

**At `/`:**
```json
{
    "message": "Welcome to my first API!"
}
```

**At `/hello/John`:**
```json
{
    "message": "Hello, John!"
}
```

**At `/docs`:**
A beautiful interactive page where you can:
- See all your endpoints
- Test them with real requests
- See example responses

### Complete Beginner Example with Comments

```python
"""
My First FastAPI Application
Created for learning purposes
"""

# Import the FastAPI framework
from fastapi import FastAPI

# Create the application
# title and description appear in the documentation
app = FastAPI(
    title="My First API",
    description="Learning FastAPI step by step",
    version="1.0.0"
)

# Home page endpoint
# GET request to the root URL "/"
@app.get("/")
def read_root():
    """
    This is the home page.
    Returns a simple welcome message.
    """
    return {
        "message": "Welcome to my API!",
        "documentation": "Visit /docs for interactive docs"
    }

# Greeting endpoint with a path parameter
# The {name} in the URL becomes a function parameter
@app.get("/greet/{name}")
def greet_user(name: str):
    """
    Greet a user by name.
    
    - **name**: The name of the person to greet
    """
    return {
        "greeting": f"Hello, {name}!",
        "tip": "Try changing the name in the URL"
    }

# Addition calculator endpoint
# Shows how to use multiple parameters
@app.get("/add/{num1}/{num2}")
def add_numbers(num1: int, num2: int):
    """
    Add two numbers together.
    
    - **num1**: First number
    - **num2**: Second number
    """
    result = num1 + num2
    return {
        "num1": num1,
        "num2": num2,
        "result": result,
        "operation": f"{num1} + {num2} = {result}"
    }

# Health check endpoint
# Common in production APIs to verify the server is running
@app.get("/health")
def health_check():
    """
    Check if the API is running.
    Used by monitoring systems.
    """
    return {"status": "healthy"}
```

### Running and Testing

```bash
# Start the server
uvicorn main:app --reload

# Server will start at http://127.0.0.1:8000
```

**Test URLs:**
- `http://127.0.0.1:8000/` - Welcome message
- `http://127.0.0.1:8000/greet/Alice` - Greet Alice
- `http://127.0.0.1:8000/add/5/3` - Add 5 + 3
- `http://127.0.0.1:8000/health` - Health check
- `http://127.0.0.1:8000/docs` - Documentation

### Summary Diagram

```
Your Code (main.py)
        ↓
    FastAPI App
        ↓
    Uvicorn Server
        ↓
Available at http://127.0.0.1:8000
        ↓
┌───────────────────────────────────┐
│  /          → Welcome message     │
│  /greet/X   → Hello, X!           │
│  /add/X/Y   → X + Y result        │
│  /docs      → Documentation       │
└───────────────────────────────────┘
```

**Congratulations!** You've built your first FastAPI application! 🎉

---

# Chapter 2: Core Concepts

## 2.1 Path Operations (GET, POST, PUT, DELETE, PATCH)

### What are HTTP Methods?

When your phone talks to a server, it uses **HTTP methods** to say what it wants to do. Think of them as different types of requests:

```
HTTP Methods = Verbs that tell the server what action to perform
```

### The Main HTTP Methods

| Method | Purpose | Real-world Analogy |
|--------|---------|-------------------|
| **GET** | Read/retrieve data | Reading a book |
| **POST** | Create new data | Writing a new book |
| **PUT** | Update/replace data completely | Replacing an entire book |
| **PATCH** | Update data partially | Fixing a typo in a book |
| **DELETE** | Remove data | Throwing away a book |

### Visual Representation

```
┌─────────────────────────────────────────────────────────┐
│                     USER DATABASE                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   GET /users     → List all users (READ)                │
│   GET /users/1   → Get user #1 (READ)                   │
│                                                          │
│   POST /users    → Create new user (CREATE)             │
│                                                          │
│   PUT /users/1   → Replace user #1 completely (UPDATE)  │
│                                                          │
│   PATCH /users/1 → Update part of user #1 (PARTIAL)     │
│                                                          │
│   DELETE /users/1 → Remove user #1 (DELETE)             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### FastAPI Implementation

```python
from fastapi import FastAPI

app = FastAPI()

# Simulated database (a simple list)
users_db = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
]

# GET - Read all users
@app.get("/users")
def get_all_users():
    """Retrieve all users from the database"""
    return {"users": users_db}

# GET - Read one user
@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Retrieve a specific user by ID"""
    for user in users_db:
        if user["id"] == user_id:
            return user
    return {"error": "User not found"}

# POST - Create a new user
@app.post("/users")
def create_user(name: str, email: str):
    """Create a new user"""
    new_id = len(users_db) + 1
    new_user = {"id": new_id, "name": name, "email": email}
    users_db.append(new_user)
    return {"message": "User created", "user": new_user}

# PUT - Replace a user completely
@app.put("/users/{user_id}")
def replace_user(user_id: int, name: str, email: str):
    """Replace all information for a user"""
    for user in users_db:
        if user["id"] == user_id:
            user["name"] = name
            user["email"] = email
            return {"message": "User replaced", "user": user}
    return {"error": "User not found"}

# PATCH - Update part of a user
@app.patch("/users/{user_id}")
def update_user(user_id: int, name: str = None, email: str = None):
    """Update specific fields of a user"""
    for user in users_db:
        if user["id"] == user_id:
            if name:
                user["name"] = name
            if email:
                user["email"] = email
            return {"message": "User updated", "user": user}
    return {"error": "User not found"}

# DELETE - Remove a user
@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    """Delete a user by ID"""
    for i, user in enumerate(users_db):
        if user["id"] == user_id:
            deleted_user = users_db.pop(i)
            return {"message": "User deleted", "user": deleted_user}
    return {"error": "User not found"}
```

### When to Use Each Method

```
Need to FETCH data?          → GET
Need to CREATE something?    → POST
Need to REPLACE entirely?    → PUT
Need to UPDATE partially?    → PATCH
Need to REMOVE something?    → DELETE
```

---

## 2.2 Path Parameters

### What are Path Parameters?

Path parameters are variables in the URL that you use to identify specific resources.

```
URL: /users/42
            ↓
      Path Parameter (user ID is 42)
```

### Simple Example

```python
from fastapi import FastAPI

app = FastAPI()

# Basic path parameter
@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id}

# Try: /items/5 → Returns {"item_id": 5}
# Try: /items/100 → Returns {"item_id": 100}
```

### How It Works

```
User requests: /items/42
                     ↓
FastAPI extracts: item_id = 42
                     ↓
Converts to: integer (because of : int)
                     ↓
Passes to function: get_item(item_id=42)
                     ↓
Returns: {"item_id": 42}
```

### Multiple Path Parameters

```python
@app.get("/users/{user_id}/posts/{post_id}")
def get_user_post(user_id: int, post_id: int):
    return {
        "user_id": user_id,
        "post_id": post_id
    }

# Try: /users/1/posts/5
# Returns: {"user_id": 1, "post_id": 5}
```

### Path Parameter Types

FastAPI automatically validates the type:

```python
# Integer parameter
@app.get("/items/{item_id}")
def get_item(item_id: int):  # Must be a number
    return {"item_id": item_id}

# String parameter
@app.get("/users/{username}")
def get_user(username: str):  # Any text
    return {"username": username}

# Float parameter
@app.get("/prices/{price}")
def get_price(price: float):  # Decimal number
    return {"price": price}
```

### Validation in Action

```
Request: /items/abc
Expected: integer
Result: Error 422 - Validation Error
        "value is not a valid integer"

Request: /items/42
Expected: integer
Result: Success! {"item_id": 42}
```

### Order Matters!

```python
# WRONG ORDER - "me" will never be reached
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}

@app.get("/users/me")  # This won't work!
def get_current_user():
    return {"user": "current user"}

# CORRECT ORDER - Put fixed paths first
@app.get("/users/me")  # This comes first
def get_current_user():
    return {"user": "current user"}

@app.get("/users/{user_id}")  # This comes second
def get_user(user_id: int):
    return {"user_id": user_id}
```

---

## 2.3 Query Parameters

### What are Query Parameters?

Query parameters come after the `?` in a URL and are used for filtering, sorting, or pagination.

```
URL: /items?skip=10&limit=20
            ↓
      Query Parameters
      skip = 10
      limit = 20
```

### Simple Example

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items")
def get_items(skip: int = 0, limit: int = 10):
    """
    Get items with pagination
    
    - skip: Number of items to skip (default: 0)
    - limit: Maximum items to return (default: 10)
    """
    # Simulated database
    all_items = ["apple", "banana", "cherry", "date", "elderberry"]
    return all_items[skip : skip + limit]

# /items → Returns first 10 items (default)
# /items?skip=2 → Skips first 2 items
# /items?limit=3 → Returns only 3 items
# /items?skip=1&limit=2 → Skips 1, returns 2
```

### Path vs Query Parameters

```
Path Parameters: /users/42
- Used for required identifiers
- Part of the resource path
- Example: Get user with ID 42

Query Parameters: /items?color=red&size=large
- Used for optional filtering
- Appear after the ?
- Example: Filter items by color and size
```

### Combining Both

```python
@app.get("/users/{user_id}/items")
def get_user_items(
    user_id: int,           # Path parameter (required)
    category: str = None,   # Query parameter (optional)
    skip: int = 0,          # Query parameter with default
    limit: int = 10         # Query parameter with default
):
    return {
        "user_id": user_id,
        "category": category,
        "skip": skip,
        "limit": limit
    }

# /users/5/items → user_id=5, category=None, skip=0, limit=10
# /users/5/items?category=books → user_id=5, category="books"
# /users/5/items?skip=10&limit=5 → user_id=5, skip=10, limit=5
```

### Required vs Optional Query Parameters

```python
# Optional: Has default value (= None or = some_value)
@app.get("/items")
def get_items(search: str = None):  # Optional
    if search:
        return {"searching_for": search}
    return {"message": "No search term provided"}

# Required: No default value
@app.get("/search")
def search_items(q: str):  # Required!
    return {"query": q}

# /search → Error! 'q' is required
# /search?q=hello → Works! Returns {"query": "hello"}
```

### Boolean Query Parameters

```python
@app.get("/items")
def get_items(show_hidden: bool = False):
    if show_hidden:
        return {"items": ["public", "secret"]}
    return {"items": ["public"]}

# /items → {"items": ["public"]}
# /items?show_hidden=true → {"items": ["public", "secret"]}
# /items?show_hidden=1 → Same as true
# /items?show_hidden=yes → Same as true
```

---

## 2.4 Request Body with Pydantic Models

### What is a Request Body?

When you send data to create or update something, you put that data in the **request body**. It's like filling out a form and submitting it.

```
POST /users
Body: {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 25
}
```

### What is Pydantic?

Pydantic is a library that:
1. Defines the structure of your data
2. Validates the data automatically
3. Converts data types if possible

### Basic Example

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Define the data structure
class User(BaseModel):
    name: str
    email: str
    age: int

# Use it in your endpoint
@app.post("/users")
def create_user(user: User):
    return {
        "message": "User created successfully",
        "user": user
    }
```

### How to Send the Request

Using the `/docs` page or a tool like curl:

```json
POST /users
Content-Type: application/json

{
    "name": "Alice",
    "email": "alice@example.com",
    "age": 25
}
```

### Automatic Validation

```python
class User(BaseModel):
    name: str      # Must be a string
    email: str     # Must be a string
    age: int       # Must be an integer

# Valid request:
{
    "name": "Alice",
    "email": "alice@example.com",
    "age": 25
}
# ✅ Works!

# Invalid request (age is a string):
{
    "name": "Alice",
    "email": "alice@example.com",
    "age": "twenty-five"
}
# ❌ Error: "age must be an integer"

# Missing field:
{
    "name": "Alice"
}
# ❌ Error: "email is required, age is required"
```

### Optional Fields

```python
from typing import Optional

class User(BaseModel):
    name: str
    email: str
    age: Optional[int] = None  # Optional with default None
    country: str = "USA"       # Optional with default value

# Minimum required:
{
    "name": "Alice",
    "email": "alice@example.com"
}
# ✅ Works! age=None, country="USA"
```

### Complete Example

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

# Simple model
class Item(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    is_available: bool = True
    tags: List[str] = []

# In-memory database
items_db = []

@app.post("/items")
def create_item(item: Item):
    """Create a new item"""
    items_db.append(item.dict())
    return {"message": "Item created", "item": item}

@app.get("/items")
def get_items():
    """Get all items"""
    return {"items": items_db}
```

### Testing with Different Data

```json
// Minimal data
{
    "name": "Apple",
    "price": 0.99
}
// Result: is_available=True, description=None, tags=[]

// Full data
{
    "name": "Laptop",
    "price": 999.99,
    "description": "High-performance laptop",
    "is_available": true,
    "tags": ["electronics", "computers"]
}
// Result: All fields populated
```

---

## 2.5 Response Models

### What are Response Models?

Response models define what data your API sends back. They help you:
1. Document what the response looks like
2. Filter out sensitive data (like passwords)
3. Ensure consistent responses

### Basic Example

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Input model (what we receive)
class UserCreate(BaseModel):
    name: str
    email: str
    password: str  # Sensitive!

# Output model (what we send back)
class UserResponse(BaseModel):
    name: str
    email: str
    # Notice: NO password field!

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    # Even though we have the password, it won't be returned
    return user
```

### Why This Matters

```
Input: {
    "name": "Alice",
    "email": "alice@example.com",
    "password": "secret123"
}

Output (with response_model): {
    "name": "Alice",
    "email": "alice@example.com"
}

Password is automatically filtered out! 🔒
```

### Multiple Response Models

```python
from typing import List

class Item(BaseModel):
    name: str
    price: float
    description: str

class ItemList(BaseModel):
    items: List[Item]
    total: int

@app.get("/items", response_model=ItemList)
def get_items():
    items = [
        {"name": "Apple", "price": 0.99, "description": "Fresh apple"},
        {"name": "Banana", "price": 0.59, "description": "Yellow banana"},
    ]
    return {"items": items, "total": len(items)}
```

---

## 2.6 Status Codes and HTTP Exceptions

### What are Status Codes?

Status codes are numbers that tell you if a request succeeded or failed.

```
2xx = Success ✅
3xx = Redirect ↪️
4xx = Client Error (your fault) ❌
5xx = Server Error (server's fault) 💥
```

### Common Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Success (default) |
| 201 | Created | Something was created |
| 204 | No Content | Success, but nothing to return |
| 400 | Bad Request | Invalid data sent |
| 401 | Unauthorized | Not logged in |
| 403 | Forbidden | Not allowed |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Data validation failed |
| 500 | Server Error | Something broke |

### Setting Status Codes in FastAPI

```python
from fastapi import FastAPI, status

app = FastAPI()

# Default is 200 OK
@app.get("/items")
def get_items():
    return {"items": []}

# Set custom status code
@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(name: str):
    return {"message": "Item created"}

# Or use the number directly
@app.post("/users", status_code=201)
def create_user(name: str):
    return {"message": "User created"}
```

### Raising HTTP Exceptions

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

items_db = {"apple": {"name": "Apple", "price": 0.99}}

@app.get("/items/{item_name}")
def get_item(item_name: str):
    if item_name not in items_db:
        # Raise a 404 error
        raise HTTPException(
            status_code=404,
            detail=f"Item '{item_name}' not found"
        )
    return items_db[item_name]

# GET /items/apple → {"name": "Apple", "price": 0.99}
# GET /items/banana → 404 Error: "Item 'banana' not found"
```

### Custom Error Responses

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id < 0:
        raise HTTPException(
            status_code=400,
            detail="User ID must be positive"
        )
    
    if user_id == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found",
            headers={"X-Error": "User does not exist"}  # Custom header
        )
    
    return {"user_id": user_id, "name": "Test User"}
```

### Complete CRUD Example with Proper Status Codes

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

# In-memory database
items_db: Dict[str, Item] = {}

@app.get("/items/{item_id}")
def get_item(item_id: str):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.post("/items/{item_id}", status_code=status.HTTP_201_CREATED)
def create_item(item_id: str, item: Item):
    if item_id in items_db:
        raise HTTPException(status_code=400, detail="Item already exists")
    items_db[item_id] = item
    return {"message": "Item created", "item": item}

@app.put("/items/{item_id}")
def update_item(item_id: str, item: Item):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item
    return {"message": "Item updated", "item": item}

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
    return None  # 204 returns no content
```

---

# Chapter 3: Data Validation with Pydantic

## 3.1 Pydantic Models Deep Dive

### What is Pydantic?

Pydantic is Python's most popular data validation library. It ensures your data is correct before your code uses it.

**Analogy:** Pydantic is like a security guard at a club. It checks your ID (validates data) before letting you in (processing data).

### Basic Model Structure

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    # Required fields
    id: int
    name: str
    email: str
    
    # Optional fields
    phone: Optional[str] = None
    
    # Fields with default values
    is_active: bool = True
    role: str = "user"
    
    # Complex types
    tags: List[str] = []
    created_at: datetime = datetime.now()
```

### Automatic Type Conversion

Pydantic tries to convert data to the correct type:

```python
class Item(BaseModel):
    id: int
    price: float
    name: str

# This works! Pydantic converts types
data = {
    "id": "123",      # String "123" → int 123
    "price": "9.99",  # String "9.99" → float 9.99
    "name": "Apple"
}
item = Item(**data)
print(item.id)     # 123 (integer)
print(item.price)  # 9.99 (float)
```

### Accessing Model Data

```python
user = User(id=1, name="Alice", email="alice@example.com")

# Access as attributes
print(user.name)        # "Alice"
print(user.email)       # "alice@example.com"

# Convert to dictionary
user_dict = user.dict()
# {"id": 1, "name": "Alice", "email": "alice@example.com", ...}

# Convert to JSON string
user_json = user.json()
# '{"id": 1, "name": "Alice", "email": "alice@example.com", ...}'
```

---

## 3.2 Field Validation and Constraints

### The Field Function

Use `Field` to add extra validation rules:

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(
        ...,                    # ... means required
        min_length=1,           # At least 1 character
        max_length=100,         # At most 100 characters
        description="Product name"
    )
    price: float = Field(
        ...,
        gt=0,                   # Greater than 0
        description="Price in dollars"
    )
    quantity: int = Field(
        default=0,
        ge=0,                   # Greater than or equal to 0
        le=1000,                # Less than or equal to 1000
        description="Items in stock"
    )
```

### Common Constraints

```python
from pydantic import BaseModel, Field

class ValidationExample(BaseModel):
    # String constraints
    name: str = Field(min_length=2, max_length=50)
    code: str = Field(regex=r'^[A-Z]{3}[0-9]{3}$')  # Like "ABC123"
    
    # Number constraints
    age: int = Field(ge=0, le=150)           # 0 <= age <= 150
    price: float = Field(gt=0)                # price > 0
    discount: float = Field(ge=0, lt=1)       # 0 <= discount < 1
    
    # List constraints
    tags: List[str] = Field(min_items=1, max_items=10)
```

### Constraint Reference

| Constraint | Meaning | Example |
|------------|---------|---------|
| `gt` | Greater than | `Field(gt=0)` → must be > 0 |
| `ge` | Greater or equal | `Field(ge=0)` → must be >= 0 |
| `lt` | Less than | `Field(lt=100)` → must be < 100 |
| `le` | Less or equal | `Field(le=100)` → must be <= 100 |
| `min_length` | Minimum string length | `Field(min_length=5)` |
| `max_length` | Maximum string length | `Field(max_length=50)` |
| `regex` | Pattern match | `Field(regex=r'^[a-z]+$')` |

---

## 3.3 Custom Validators

### Basic Validator

Create custom validation logic with the `@validator` decorator:

```python
from pydantic import BaseModel, validator

class User(BaseModel):
    name: str
    email: str
    age: int
    
    @validator('name')
    def name_must_not_be_empty(cls, value):
        if not value.strip():
            raise ValueError('Name cannot be empty')
        return value.strip()  # Return cleaned value
    
    @validator('email')
    def email_must_be_valid(cls, value):
        if '@' not in value:
            raise ValueError('Invalid email address')
        return value.lower()  # Return lowercase email
    
    @validator('age')
    def age_must_be_reasonable(cls, value):
        if value < 0 or value > 150:
            raise ValueError('Age must be between 0 and 150')
        return value
```

### Validator with Multiple Fields

```python
from pydantic import BaseModel, validator, root_validator

class DateRange(BaseModel):
    start_date: str
    end_date: str
    
    @root_validator
    def check_dates(cls, values):
        start = values.get('start_date')
        end = values.get('end_date')
        if start and end and start > end:
            raise ValueError('start_date must be before end_date')
        return values
```

### Pre and Post Validators

```python
class User(BaseModel):
    name: str
    
    # Runs BEFORE type conversion
    @validator('name', pre=True)
    def convert_name(cls, value):
        if isinstance(value, int):
            return str(value)
        return value
    
    # Runs for each item in a list
    @validator('tags', each_item=True)
    def lowercase_tags(cls, value):
        return value.lower()
```

---

## 3.4 Nested Models

### What are Nested Models?

Nested models let you structure complex data with models inside other models.

```python
from pydantic import BaseModel
from typing import List, Optional

# Address model
class Address(BaseModel):
    street: str
    city: str
    country: str
    zip_code: str

# User model contains Address
class User(BaseModel):
    name: str
    email: str
    address: Address  # Nested model!

# Usage
user_data = {
    "name": "Alice",
    "email": "alice@example.com",
    "address": {
        "street": "123 Main St",
        "city": "New York",
        "country": "USA",
        "zip_code": "10001"
    }
}

user = User(**user_data)
print(user.address.city)  # "New York"
```

### Lists of Nested Models

```python
class OrderItem(BaseModel):
    product_name: str
    quantity: int
    price: float

class Order(BaseModel):
    order_id: str
    customer_name: str
    items: List[OrderItem]  # List of nested models
    
    @property
    def total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

# Usage
order_data = {
    "order_id": "ORD-001",
    "customer_name": "Bob",
    "items": [
        {"product_name": "Apple", "quantity": 3, "price": 0.99},
        {"product_name": "Banana", "quantity": 2, "price": 0.59}
    ]
}

order = Order(**order_data)
print(order.total)  # 4.15
```

### Deep Nesting

```python
class Company(BaseModel):
    name: str
    address: Address

class Employee(BaseModel):
    name: str
    company: Company

class Department(BaseModel):
    name: str
    employees: List[Employee]
```

---

## 3.5 Optional and Default Values

### Understanding Optional

```python
from typing import Optional

class User(BaseModel):
    # Required - must be provided
    name: str
    email: str
    
    # Optional with None default
    phone: Optional[str] = None
    
    # Optional with value default
    country: str = "USA"
    is_active: bool = True
```

### Difference Between Optional and Default

```python
# Optional[str] = None
# - Can be None
# - Doesn't need to be provided

# str = "default"
# - Cannot be None
# - Doesn't need to be provided
# - If not provided, uses "default"

class Example(BaseModel):
    # Must be provided, cannot be None
    required_field: str
    
    # Optional, defaults to None
    optional_field: Optional[str] = None
    
    # Not required, has default value
    default_field: str = "default"
    
    # Can be string or None, defaults to specific value
    optional_with_default: Optional[str] = "default"
```

### Using None vs Unset

```python
from pydantic import BaseModel
from typing import Optional

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

# Partial update - only update provided fields
def update_user(user_id: int, update_data: UserUpdate):
    current_user = {"name": "Alice", "email": "alice@example.com", "age": 25}
    
    update_dict = update_data.dict(exclude_unset=True)
    # Only includes fields that were actually provided
    
    current_user.update(update_dict)
    return current_user

# If you send {"name": "Bob"}
# Only name is updated, email and age stay the same
```

---

## 3.6 Config Classes and Schema Customization

### Model Config

Configure model behavior with the `Config` class:

```python
from pydantic import BaseModel

class User(BaseModel):
    user_name: str
    email_address: str
    
    class Config:
        # Use different names in JSON
        fields = {
            'user_name': 'username',
            'email_address': 'email'
        }
        
        # Allow creating model from ORM objects
        from_attributes = True
        
        # Custom JSON schema example
        schema_extra = {
            "example": {
                "user_name": "johndoe",
                "email_address": "john@example.com"
            }
        }
```

### Common Config Options

```python
class MyModel(BaseModel):
    class Config:
        # Immutable model (can't change after creation)
        frozen = True
        
        # Allow extra fields
        extra = 'allow'  # or 'forbid' or 'ignore'
        
        # Validate data on assignment
        validate_assignment = True
        
        # Use enum values instead of enum objects
        use_enum_values = True
        
        # Custom JSON encoders
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Field Aliases

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # Internal name is 'user_id', but JSON uses 'id'
    user_id: int = Field(..., alias='id')
    user_name: str = Field(..., alias='name')
    
    class Config:
        populate_by_name = True  # Allow both names

# Both work:
User(id=1, name="Alice")       # Using aliases
User(user_id=1, user_name="Alice")  # Using field names
```

---

*Continue to Part 2 for Chapters 4-9...*
