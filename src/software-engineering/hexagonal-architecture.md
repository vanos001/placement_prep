# Hexagonal Architecture (Ports and Adapters)

Hexagonal Architecture, also known as Ports and Adapters, is a software architecture pattern introduced by Alistair Cockburn in 2005. It isolates the application's core business logic from external concerns (UI, database, message queues) by defining "ports" (interfaces) that adapters plug into. This page covers the architecture, the difference from Clean Architecture, and the production patterns.

## The Architecture

```text
                    ┌─────────────────────────────────┐
                    │                                  │
                    │   Application Core (Domain)      │
                    │   - Business logic                │
                    │   - Domain models                 │
                    │   - Use cases (interactors)      │
                    │                                  │
                    │  ┌────────┐         ┌────────┐  │
                    │  │ Port   │         │ Port   │  │
                    │  │ (in)   │         │ (out)  │  │
                    │  └────────┘         └────────┘  │
                    └─────────────────────────────────┘
                            ↑                 ↑
                            │                 │
                ┌───────────┘                 └───────────┐
                │                                          │
        ┌───────────────┐                       ┌───────────────┐
        │  HTTP Adapter │                       │  Database      │
        │  (driving)    │                       │  Adapter       │
        └───────────────┘                       └───────────────┘
                ↑                                          ↑
                │                                          │
        HTTP request                              SQL queries
```

The hexagon has two sides:
- **Driving side (left)**: adapters that call into the application (HTTP controllers, CLI commands, message consumers).
- **Driven side (right)**: adapters that the application calls (databases, external APIs, message publishers).

The application core doesn't know about specific adapters — it only knows about the **ports** (interfaces) that adapters implement.

## Ports and Adapters

A **port** is an interface defined by the application core:

```python
# Port: an interface the application needs
class OrderRepositoryPort(Protocol):
    def find_by_id(self, id: int) -> Order: ...
    def save(self, order: Order) -> None: ...

class NotificationPort(Protocol):
    def send_order_submitted(self, order: Order) -> None: ...

# Use case (in the application core)
class SubmitOrderUseCase:
    def __init__(self, order_repo: OrderRepositoryPort, notification: NotificationPort):
        self.order_repo = order_repo
        self.notification = notification
    
    def execute(self, order_id: int):
        order = self.order_repo.find_by_id(order_id)
        order.submit()
        self.order_repo.save(order)
        self.notification.send_order_submitted(order)
```

An **adapter** implements a port:

```python
# Adapter: PostgreSQL implementation of the port
class PostgresOrderRepository:
    def __init__(self, db):
        self.db = db
    
    def find_by_id(self, id: int) -> Order:
        row = self.db.execute("SELECT * FROM orders WHERE id = ?", id)
        return Order.from_row(row)
    
    def save(self, order: Order) -> None:
        self.db.execute("UPDATE orders SET status = ? WHERE id = ?", 
                        order.status, order.id)

# Adapter: SMTP implementation of the notification port
class SmtpNotification:
    def send_order_submitted(self, order: Order) -> None:
        send_email(f"order+{order.id}@example.com", "Order submitted", ...)

# Adapter: HTTP controller (driving side)
@app.post("/orders/{id}/submit")
def submit_order(id: int):
    use_case = SubmitOrderUseCase(order_repo, notification)
    use_case.execute(id)
    return {"status": "submitted"}
```

The application core doesn't import `PostgresOrderRepository` or `SmtpNotification` — it only knows the port interfaces. The composition root (the application's `main()`) wires up the concrete adapters.

## The Composition Root

The composition root is the one place where adapters are wired to ports:

```python
# main.py (the composition root)
from app.use_cases import SubmitOrderUseCase
from app.adapters import PostgresOrderRepository, SmtpNotification

def create_app():
    db = create_db_connection()
    order_repo = PostgresOrderRepository(db)
    notification = SmtpNotification(smtp_config)
    use_case = SubmitOrderUseCase(order_repo, notification)
    
    app = FastAPI()
    app.state.use_case = use_case
    return app

app = create_app()
```

This is the only place that knows the concrete adapter implementations. The rest of the code uses ports.

## Comparison to Clean Architecture

| Aspect | Hexagonal | Clean Architecture |
|--------|----------|---------------------|
| Author | Cockburn 2005 | Robert "Uncle Bob" Martin 2012 |
| Center | Application core | Entities (pure domain) |
| Layers | Ports + Adapters | Entities → Use Cases → Interface Adapters → Frameworks |
| Direction of dependency | Inward (adapters depend on ports) | Inward (outer depends on inner) |
| Practical difference | Minimal | Minimal |

Hexagonal and Clean Architecture are very similar — both isolate the business logic from external concerns via interfaces. The differences are largely terminology:
- Hexagonal's "ports" = Clean's "boundaries".
- Hexagonal's "driving/driven" = Clean's "input/output".
- Hexagonal's "adapters" = Clean's "gateways" / "presenters".

Most modern implementations mix terminology from both.

## Production Patterns

### Pattern 1: Hexagonal Microservices

A microservice with a hexagonal structure:

```text
src/
├── domain/         # business logic, no I/O
├── use_cases/      # use case interactors, depend on ports
├── ports/          # port interfaces
├── adapters/
│   ├── http/       # FastAPI/Flask controllers (driving)
│   ├── db/         # SQLAlchemy repositories (driven)
│   ├── messaging/  # RabbitMQ/Kafka publishers (driven)
│   └── external/   # third-party API clients (driven)
└── main.py        # composition root
```

Each layer has clear dependencies inward. Testing is easy: mock the ports.

### Pattern 2: Test-Driven Design

Hexagonal's isolation makes the use cases testable without external dependencies:

```python
class TestSubmitOrderUseCase:
    def setup_method(self):
        self.order_repo = MockOrderRepository()
        self.notification = MockNotification()
        self.use_case = SubmitOrderUseCase(self.order_repo, self.notification)
    
    def test_submit_order_updates_status(self):
        # Given an order exists
        self.order_repo.add(Order(id=1, status="draft"))
        
        # When the use case executes
        self.use_case.execute(1)
        
        # Then the order is submitted
        order = self.order_repo.find_by_id(1)
        assert order.status == "submitted"
        assert self.notification.order_submitted_called
    
    def test_submit_empty_order_raises(self):
        self.order_repo.add(Order(id=1, status="draft", items=[]))
        with pytest.raises(ValueError):
            self.use_case.execute(1)
```

Tests run in milliseconds, no database or SMTP server needed.

### Pattern 3: Multiple Adapters per Port

A port can have multiple adapters (e.g., for different environments):

```python
# Production adapter
class PostgresOrderRepository: ...

# Test adapter (in-memory)
class InMemoryOrderRepository: ...

# Development adapter (file-based)
class FileOrderRepository: ...
```

The composition root picks the adapter based on the environment.

## When Hexagonal Helps

- **Complex business logic** that should be isolated from framework concerns.
- **Multiple integrations** (multiple DBs, multiple UIs) for the same logic.
- **Testability** is a high priority.
- **Long-lived software** that may outlive its framework.

Hexagonal is overkill for:
- **Simple CRUD apps** where the logic is just database access.
- **Scripts** without persistent state.
- **Performance-critical code** where the indirection adds overhead.

## Common Pitfalls

1. **Putting business logic in adapters.** If your HTTP controller has business rules, you've broken the architecture. Move logic to use cases.

2. **Leaking adapter types into the core.** If the use case imports `SQLAlchemy` or `FastAPI`, the dependency is wrong. Use ports.

3. **Over-using ports.** A port for every micro-feature adds boilerplate. Use ports for external dependencies, not for internal helpers.

4. **Forgetting the composition root.** Without it, the architecture is incomplete; the use cases don't know which adapters to use.

5. **Confusing "driving" and "driven".** A driving adapter calls the use case (input); a driven adapter is called by the use case (output). The arrow points the same direction (inward), but the call direction is opposite.

6. **Treating ports as DTOs.** A port is an interface, not a data structure. If you're passing data across a port, use a separate DTO.

## References

- Alistair Cockburn, "[Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)" (2005)
- [Hexagonal Architecture (Wikipedia)](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))
- Juan Manuel Garrido de Mena, "[Hexagonal Architecture in Python](https://jmgarridodev.medium.com/hexagonal-architecture-in-python-7a35979e1c7e)" (2020)
- [Clean Architecture book (Robert Martin)](https://www.oreilly.com/library/view/clean-architecture-a/9780134494272/)
- [Hexagonal vs Clean Architecture comparison](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [LWN: Hexagonal Architecture overview (2021)](https://lwn.net/Articles/856675/)
