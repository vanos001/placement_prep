# Clean Architecture

Clean Architecture is a software design philosophy introduced by Robert C. Martin ("Uncle Bob") in 2012, formalized in his 2017 book "Clean Architecture: A Craftsman's Guide to Software Structure and Design". It builds on Hexagonal Architecture, Onion Architecture, and the SOLID principles, organizing software into concentric layers with strict dependency rules. This page covers the layers, the dependency rule, the SOLID principles' application, and the production patterns.

## The Layers

```text
┌─────────────────────────────────────────────────────┐
│  Frameworks & Drivers (outermost)                   │
│  - Web framework (Spring, FastAPI)                  │
│  - Database (PostgreSQL, MongoDB)                   │
│  - External APIs                                   │
└─────────────────────────────────────────────────────┘
                       ↑
┌─────────────────────────────────────────────────────┐
│  Interface Adapters                                 │
│  - Controllers                                      │
│  - Presenters                                       │
│  - Gateways                                         │
└─────────────────────────────────────────────────────┘
                       ↑
┌─────────────────────────────────────────────────────┐
│  Use Cases (Application Business Rules)             │
│  - Interactors                                      │
│  - Application services                             │
│  - Input/output boundaries                          │
└─────────────────────────────────────────────────────┘
                       ↑
┌─────────────────────────────────────────────────────┐
│  Entities (Enterprise Business Rules) (innermost)  │
│  - Domain models                                    │
│  - Business invariants                              │
└─────────────────────────────────────────────────────┘

Dependency rule: source code dependencies must point inward.
```

The four layers, from outermost to innermost:
1. **Frameworks & Drivers**: the outermost layer — the web framework, database, message queue, etc.
2. **Interface Adapters**: translates data between the outer and inner layers.
3. **Use Cases**: the application's business rules (what the app does).
4. **Entities**: the enterprise business rules (the domain).

The **dependency rule**: source code dependencies must point inward. The outer layer knows about the inner, never vice versa.

## The Dependency Rule

```python
# Innermost: Entity (no dependencies on outer layers)
class Order:
    def __init__(self, id, customer_id, items, status):
        self.id = id
        self.customer_id = customer_id
        self.items = items
        self.status = status
    
    def submit(self):
        if not self.items:
            raise ValueError("Cannot submit empty order")
        if self.status != "draft":
            raise ValueError("Order already submitted")
        self.status = "submitted"

# Use case layer: depends on entities, not on interface adapters
class SubmitOrderUseCase:
    def __init__(self, order_gateway: OrderGateway, presenter: SubmitOrderPresenter):
        self.order_gateway = order_gateway
        self.presenter = presenter
    
    def execute(self, input_data: SubmitOrderInput):
        order = self.order_gateway.find_by_id(input_data.order_id)
        order.submit()
        self.order_gateway.save(order)
        self.presenter.present(OrderSubmittedOutput(order.id))

# Interface adapter: implements the gateway interface
class SQLOrderGateway(OrderGateway):
    def find_by_id(self, id: int) -> Order:
        row = self.db.execute("SELECT * FROM orders WHERE id = ?", id)
        return Order.from_row(row)

# Framework layer: implements the HTTP entry point
@app.post("/orders/{id}/submit")
def submit_order(id: int):
    use_case = SubmitOrderUseCase(order_gateway, presenter)
    use_case.execute(SubmitOrderInput(id))
    return presenter.response
```

Notice:
- The entity doesn't know about the use case.
- The use case doesn't know about SQL or HTTP.
- The HTTP framework is the outermost; everything else depends on it (indirectly).

## The SOLID Principles

Clean Architecture is built on the SOLID principles:

- **Single Responsibility**: each class has one reason to change. The `Order` entity changes when business rules change; the `SQLOrderGateway` changes when the database schema changes.
- **Open/Closed**: classes are open for extension, closed for modification. The use case can be extended with new gateways without modification.
- **Liskov Substitution**: subclasses can replace their parents. A `MockOrderGateway` can replace `SQLOrderGateway` in tests.
- **Interface Segregation**: clients depend only on the methods they use. The use case depends only on `OrderGateway`'s methods, not on the gateway's full interface.
- **Dependency Inversion**: high-level modules (use cases) depend on abstractions (interfaces), not on concrete modules (SQL gateways). The SQL gateway implements the interface.

## The Use Case Pattern

A use case (a.k.a. interactor) is a class that implements a single application use case:

```python
class CreateOrderUseCase:
    def __init__(self, order_gateway, customer_gateway, event_publisher):
        self.order_gateway = order_gateway
        self.customer_gateway = customer_gateway
        self.event_publisher = event_publisher
    
    def execute(self, input_data: CreateOrderInput) -> CreateOrderOutput:
        # 1. Validate inputs
        customer = self.customer_gateway.find_by_id(input_data.customer_id)
        if not customer:
            return CreateOrderOutput(error="Customer not found")
        
        # 2. Apply business rules
        order = Order.create(customer.id, input_data.items)
        
        # 3. Persist
        self.order_gateway.save(order)
        
        # 4. Publish events
        self.event_publisher.publish(OrderCreated(order.id))
        
        # 5. Return output
        return CreateOrderOutput(order_id=order.id)
```

The use case:
- Takes input data (a DTO, not framework objects).
- Returns output data (also a DTO).
- Uses gateways (interfaces) for I/O.
- Encapsulates the application's business rules.

## The Gateway Pattern

A gateway is an interface for external systems:

```python
class OrderGateway(ABC):
    @abstractmethod
    def find_by_id(self, id: int) -> Order: ...
    
    @abstractmethod
    def save(self, order: Order) -> None: ...
    
    @abstractmethod
    def find_by_customer(self, customer_id: int) -> List[Order]: ...
```

The use case depends on the abstract gateway. The concrete implementation (SQL, NoSQL, in-memory) is in the outer layers.

## The Presenter Pattern

The presenter translates the use case's output to the framework's expected format:

```python
class CreateOrderPresenter:
    def __init__(self):
        self.response = None
    
    def present(self, output: CreateOrderOutput):
        if output.error:
            self.response = {"error": output.error}
        else:
            self.response = {"order_id": output.order_id, "status": "created"}

# Use in HTTP controller
@app.post("/orders")
def create_order(request):
    use_case = CreateOrderUseCase(...)
    presenter = CreateOrderPresenter()
    use_case.execute(CreateOrderInput(...))
    return presenter.response
```

The presenter lets the use case return framework-agnostic output; the presenter translates to JSON, HTML, or whatever the framework needs.

## Production Patterns

### Pattern 1: Clean Architecture Microservice

```text
src/
├── domain/            # Entity layer
│   ├── order.py
│   ├── customer.py
│   └── exceptions.py
├── use_cases/         # Use case layer
│   ├── create_order.py
│   ├── submit_order.py
│   └── cancel_order.py
├── gateways/          # Interface adapter layer (interfaces)
│   ├── order_gateway.py
│   └── customer_gateway.py
├── adapters/          # Interface adapter layer (implementations)
│   ├── sql_order_gateway.py
│   ├── sql_customer_gateway.py
│   └── http_presenters.py
├── frameworks/        # Framework layer
│   ├── app.py
│   └── routes.py
└── main.py            # composition root
```

Each layer is in its own package; the dependencies point inward.

### Pattern 2: Multi-Frontend Support

The same use cases can serve HTTP, gRPC, and CLI:

```python
# HTTP frontend
@app.post("/orders")
def http_create_order(request):
    use_case = CreateOrderUseCase(...)
    presenter = HTTPCreateOrderPresenter()
    use_case.execute(...)
    return presenter.response

# gRPC frontend
def grpc_create_order(request):
    use_case = CreateOrderUseCase(...)
    presenter = GRPCCreateOrderPresenter()
    use_case.execute(...)
    return presenter.response

# CLI frontend
def cli_create_order(args):
    use_case = CreateOrderUseCase(...)
    presenter = CLICreateOrderPresenter()
    use_case.execute(...)
    print(presenter.message)
```

The use case and entities are shared; the presenters and frontends are per-frontend.

## Comparison to Hexagonal Architecture

| Aspect | Clean Architecture | Hexagonal |
|--------|---------------------|-----------|
| Layer count | 4 | 2 (core + adapters) |
| Naming | Use cases, gateways, presenters | Ports, adapters |
| Origin | Robert Martin 2012 | Alistair Cockburn 2005 |
| Practical difference | Minimal | Minimal |

Both patterns isolate the business logic. Clean Architecture's 4 layers are more granular; Hexagonal's 2 are simpler. Most modern implementations pick one and use terminology loosely.

## Common Pitfalls

1. **Putting business logic in controllers.** The controller is a framework adapter; it should call the use case and return the response. Business rules go in the use case or entity.

2. **Forgetting to use DTOs across boundaries.** Passing entity objects to the controller couples the controller to the entity. Use DTOs (data transfer objects) for input/output.

3. **Over-engineering simple apps.** Clean Architecture's full layering is overkill for a CRUD app. Use a simpler structure.

4. **Leaking framework types into the core.** If the use case imports `from fastapi import ...`, the dependency is wrong. Use gateways/presenters.

5. **Forgetting the composition root.** Without it, the layers don't know which adapters to use. The `main()` function is critical.

6. **Confusing "interface adapter" with "controller".** The interface adapter layer includes controllers, presenters, and gateways. All three are needed.

## References

- Robert C. Martin, "[Clean Architecture: A Craftsman's Guide to Software Structure and Design](https://www.oreilly.com/library/view/clean-architecture-a/9780134494272/)" (Prentice Hall 2017)
- [The Clean Architecture blog post](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) (Uncle Bob, 2012)
- [Clean Architecture with Python (Pydantic)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Clean Architecture in Go](https://github.com/bxcodec/go-clean-arch) (popular reference impl)
- [Hexagonal vs Clean Architecture (Jason Taylor)](https://jasonpearce.github.io/2017/03/02/hexagonal-clean-architecture.html)
- [LWN: Clean Architecture overview (2022)](https://lwn.net/Articles/856675/)
