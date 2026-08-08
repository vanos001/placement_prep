# FastAPI

## Overview

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It's built on Starlette (ASGI) and Pydantic (data validation).

## Why FastAPI for Interviews

- **Performance**: One of the fastest Python frameworks (on par with Node.js/Go)
- **Type safety**: Automatic validation via Pydantic
- **Auto-docs**: OpenAPI/Swagger generated automatically
- **Async native**: First-class async/await support
- **Growing adoption**: Replacing Flask/Django for API services

## Architecture

```mermaid
flowchart TD
    CLIENT[Client] --> ASGI[ASGI Server<br/>Uvicorn/Hypercorn]
    ASGI --> APP[FastAPI Application]
    
    APP --> ROUTES[Route Matching]
    ROUTES --> DEPS[Dependency Injection]
    DEPS --> VALIDATE[Request Validation<br/>Pydantic]
    VALIDATE --> HANDLER[Route Handler]
    HANDLER --> SERIALIZE[Response Serialization<br/>Pydantic]
    SERIALIZE --> RESPONSE[JSON Response]
    
    subgraph "Middleware"
        CORS[CORS]
        GZIP[GZip]
        CUSTOM[Custom Middleware]
    end
    
    APP --> CORS
    APP --> GZIP
```

## Core Concepts

### Path Operations

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

# Path parameters
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

# Query parameters
@app.get("/users/")
async def list_users(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}

# Request body
class UserCreate(BaseModel):
    name: str
    email: str
    age: int | None = None

@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    return user
```

### Pydantic Models

```python
from pydantic import BaseModel, Field, validator, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=0, le=150)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('must contain uppercase')
        return v

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # ORM mode

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
```

### Dependency Injection

```python
from fastapi import Depends, HTTPException, Header

# Simple dependency
async def get_db():
    async with AsyncSession() as session:
        yield session

# Dependency with logic
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    token = authorization.removeprefix("Bearer ")
    user = await verify_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# Using dependencies
@app.get("/me")
async def get_me(user = Depends(get_current_user)):
    return user

# Dependency chains
async def get_admin(user = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403)
    return user
```

### Database Integration (SQLAlchemy)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)

# Repository pattern
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, id: int) -> User | None:
        return await self.db.get(User, id)
    
    async def create(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.db.add(user)
        await self.db.commit()
        return user
```

### Background Tasks

```python
from fastapi import BackgroundTasks

async def send_email(email: str, message: str):
    # Long-running task
    await email_client.send(email, message)

@app.post("/users/")
async def create_user(user: UserCreate, bg: BackgroundTasks):
    db_user = await save_user(user)
    bg.add_task(send_email, user.email, "Welcome!")
    return db_user
```

### WebSocket Support

```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

## FastAPI vs Flask vs Django

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| **Async** | Native | Extensions | Django 4.1+ |
| **Validation** | Automatic (Pydantic) | Manual | DRF serializers |
| **Docs** | Auto-generated | Extensions | DRF |
| **Performance** | Very fast | Moderate | Moderate |
| **ORM** | Any (SQLAlchemy) | Any | Built-in |
| **Learning curve** | Low | Low | Medium |

## Interview Questions

1. **How does FastAPI validation work?** — Pydantic models validate request data automatically; errors return 422 with details
2. **What is ASGI?** — Asynchronous Server Gateway Interface; successor to WSGI; supports async, WebSockets, HTTP/2
3. **Dependency injection?** — FastAPI's DI system resolves dependencies per-request; supports nesting, caching
4. **How to handle authentication?** — OAuth2 with JWT tokens; `Depends` for token verification
5. **Background tasks vs Celery?** — Background tasks are simple, in-process; Celery for distributed, reliable task queues
6. **What is Starlette?** — ASGI toolkit that FastAPI is built on; handles routing, middleware, WebSockets
7. **How to optimize FastAPI?** — Async database drivers, connection pooling, response caching, pagination
8. **Testing FastAPI?** — `TestClient` (sync) or `httpx.AsyncClient` (async); dependency overrides

## Related Topics

- [Python](../../languages/python/) — Python language fundamentals
- [AsyncIO](../../languages/python/asyncio.md) — Async patterns in Python
- [REST API Design](../../backend/api/rest.md) — REST principles
- [Docker](../../backend/containers/docker.md) — Containerization
