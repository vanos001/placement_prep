# FastAPI

## Overview

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints. It's built on Starlette (ASGI) and Pydantic (data validation).

## Why FastAPI for Interviews

- **Performance**: One of the fastest Python frameworks (Starlette-level throughput)
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
from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=0, le=150)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
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

### Pydantic V2 Deep Dive

```python
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Annotated

# V2 style: Annotated types for metadata
class Product(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    price: Annotated[float, Field(gt=0, description="Price in USD")]
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def name_must_be_title_case(cls, v: str) -> str:
        return v.strip().title()

    @model_validator(mode='after')
    def validate_business_rules(self):
        if self.price > 10000 and 'premium' not in self.tags:
            self.tags.append('premium')
        return self

# Nested models
class Address(BaseModel):
    street: str
    city: str
    country: str = "US"

class Customer(BaseModel):
    name: str
    addresses: list[Address] = []
    primary_address: Optional[Address] = None

# Serialization options
customer = Customer(name="Alice", addresses=[Address(street="123 Main", city="NYC")])
print(customer.model_dump())                    # dict
print(customer.model_dump(exclude_unset=True))   # only set fields
print(customer.model_dump_json(indent=2))        # JSON string
```

### Dependency Injection

```python
from fastapi import Depends, HTTPException, Header
from typing import Annotated

# Simple dependency
async def get_db():
    async with AsyncSession() as session:
        yield session

# Dependency with logic
async def get_current_user(
    authorization: Annotated[str, Header()],
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

### Advanced Dependency Patterns

```python
from functools import lru_cache
from fastapi import Request

# Class-based dependencies (for stateful deps)
class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(100, max(1, limit))

@app.get("/items/")
async def list_items(pagination: Annotated[PaginationParams, Depends()]):
    return {"skip": pagination.skip, "limit": pagination.limit}

# Cached dependencies (singleton per app)
@lru_cache
def get_settings():
    return Settings()

# Dependency override for testing
def get_test_db():
    return TestDatabase()

app.dependency_overrides[get_db] = get_test_db
```

### Async Context Managers as Dependencies

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_transaction():
    async with async_session() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

@app.post("/orders/")
async def create_order(
    order: OrderCreate,
    db: Annotated[AsyncSession, Depends(get_transaction)]
):
    db_order = Order(**order.model_dump())
    db.add(db_order)
    return db_order
```

### OpenAPI Customization

```python
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    description="A production-ready API",
    version="1.0.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc
    openapi_url="/openapi.json",
    contact={"name": "Team", "email": "team@example.com"},
    license_info={"name": "MIT"},
)

# Tags for grouping endpoints
@app.post("/users/", tags=["users"], summary="Create a user",
          description="Create a new user with the given data.",
          response_description="The created user")
async def create_user(user: UserCreate):
    """Create a user with these properties:

    - **name**: User's full name
    - **email**: Must be unique
    - **age**: Optional, 0-150
    """
    return user

# Response models with status codes
@app.get("/users/{id}", response_model=UserResponse,
         responses={
             404: {"description": "User not found", "model": ErrorResponse},
             422: {"description": "Validation error"},
         })
async def get_user(id: int):
    ...
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

### Middleware

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        return response

app.add_middleware(TimingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(GZipMiddleware, minimum_size=500)
```

## FastAPI vs Flask vs Django

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| **Async** | Native | Extensions | Django 3.1+ |
| **Validation** | Automatic (Pydantic) | Manual | DRF serializers |
| **Docs** | Auto-generated | Extensions | DRF |
| **Performance** | Very fast | Moderate | Moderate |
| **ORM** | Any (SQLAlchemy) | Any | Built-in |
| **Learning curve** | Low | Low | Medium |

## Testing

```python
from httpx import AsyncClient
import pytest

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post("/users/", json={
        "name": "Alice", "email": "alice@example.com", "age": 30
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"

@pytest.mark.asyncio
async def test_validation_error(client):
    response = await client.post("/users/", json={"name": ""})
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(e["loc"] == ["body", "email"] for e in errors)

# Dependency override in tests
app.dependency_overrides[get_current_user] = lambda: mock_user
```

## Interview Questions

1. **How does FastAPI validation work?** — Pydantic models validate request data automatically; errors return 422 with details
2. **What is ASGI?** — Asynchronous Server Gateway Interface; successor to WSGI; supports async, WebSockets, HTTP/2
3. **Dependency injection?** — FastAPI's DI system resolves dependencies per-request; supports nesting, caching
4. **How to handle authentication?** — OAuth2 with JWT tokens; `Depends` for token verification
5. **Background tasks vs Celery?** — Background tasks are simple, in-process; Celery for distributed, reliable task queues
6. **What is Starlette?** — ASGI toolkit that FastAPI is built on; handles routing, middleware, WebSockets
7. **How to optimize FastAPI?** — Async database drivers, connection pooling, response caching, pagination
8. **Testing FastAPI?** — `TestClient` (sync) or `httpx.AsyncClient` (async); dependency overrides
9. **Pydantic V1 vs V2?** — V2 uses Rust core (5-50x faster), `model_validator` instead of `validator`, `model_dump()` instead of `dict()`
10. **How does OpenAPI generation work?** — FastAPI inspects function signatures, type hints, Pydantic models, and docstrings to generate the schema automatically

## References

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/)
- [Starlette Documentation](https://www.starlette.io/)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [ASGI Specification](https://asgi.readthedocs.io/)

## Related Topics

- [Python](../../languages/python/) — Python language fundamentals
- [AsyncIO](../../languages/python/asyncio.md) — Async patterns in Python
- [REST API Design](../../backend/api/rest.md) — REST principles
- [Docker](../../backend/containers/docker.md) — Containerization
