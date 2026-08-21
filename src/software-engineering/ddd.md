# Domain-Driven Design (DDD)

Domain-Driven Design (DDD) is a software design approach introduced by Eric Evans in 2003 in his book "Domain-Driven Design: Tackling Complexity in the Heart of Software". DDD focuses on modeling software around the business domain — the real-world problem the software is meant to solve — rather than around technical concerns. This page covers the strategic design (bounded contexts, ubiquitous language), tactical design (entities, value objects, aggregates, repositories), and the production deployment patterns.

## The Premise

Most enterprise software projects fail not because of technical issues but because the developers don't understand the business domain. A developer building an order management system without understanding what "order fulfillment" means to the business will produce software that doesn't fit the actual workflow.

DDD's response: spend significant time modeling the domain with domain experts (the people who run the business). The software model should mirror the business model.

## Strategic Design

### Ubiquitous Language

The team (developers + domain experts) develops a shared vocabulary called the **ubiquitous language**. Every term has a precise meaning; code uses these terms verbatim.

```text
Domain expert: "An order is submitted, then fulfilled, then shipped."
Developer (without DDD): "A row is inserted in 'orders', status set to 'NEW'..."
Developer (with DDD): "Order.submit(); ... ; Order.fulfill(); ... ; Order.ship();"
```

The ubiquitous language is shared across:
- Conversations (developers and domain experts use the same words).
- Code (class and method names match the language).
- Documentation (uses the same terms).

### Bounded Contexts

A large business has multiple sub-domains, each with its own model. A "product" in the marketing context (a brochure item with images and descriptions) is different from a "product" in the inventory context (a stockable item with SKU and weight).

A **bounded context** is a logical boundary within which a model is consistent. Outside the boundary, the same word may mean different things.

```text
Bounded Context: Marketing
  Product: { name, description, image_url, marketing_category }

Bounded Context: Inventory
  Product: { sku, weight, dimensions, warehouse_location }

Bounded Context: Sales
  Product: { sku, price, discount_eligible, tax_rate }
```

Each bounded context has its own codebase (or module), its own ubiquitous language, and its own team. The boundary prevents model pollution.

### Context Mapping

Bounded contexts must communicate. The relationship between them is captured in a **context map**:

- **Partnership**: two contexts cooperate, evolve together.
- **Shared Kernel**: two contexts share a small kernel of code.
- **Customer-Supplier**: one context (supplier) provides services to another (customer).
- **Conformist**: customer conforms to supplier's model without negotiation.
- **Anticorruption Layer (ACL)**: customer translates supplier's model to its own.
- **Open Host Service**: supplier exposes a public API.
- **Published Language**: a well-documented interchange format (e.g., a JSON schema).

```text
Sales Context ← ACL → Inventory Context (sales translates inventory's model)
Sales Context → Open Host Service → external partners
```

The ACL is the most common pattern: a translation layer that prevents the supplier's model from polluting the customer's.

## Tactical Design

### Entities

An entity is an object defined by its identity, not its attributes. Two `Order` entities with the same ID are the same order, even if their attributes differ.

```python
class Order:
    def __init__(self, id, customer_id, items):
        self.id = id  # the identity
        self.customer_id = customer_id
        self.items = items
    
    def __eq__(self, other):
        return isinstance(other, Order) and self.id == other.id
```

Entities are mutable (their attributes can change); their identity stays constant.

### Value Objects

A value object is defined by its attributes, not its identity. Two `Money` objects with the same amount and currency are equal.

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str
    
    def add(self, other):
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
```

Value objects are immutable; their attributes are set at construction. This makes them easy to reason about and safe to share.

### Aggregates

An aggregate is a cluster of related entities and value objects, treated as a single unit for data changes. One entity is the **aggregate root**; all access to the aggregate's contents goes through the root.

```python
class Order:  # aggregate root
    def __init__(self, id, customer_id):
        self.id = id
        self.customer_id = customer_id
        self.items = []  # list of OrderItem entities
        self.status = "draft"
    
    def add_item(self, sku, quantity, price):
        # All modifications go through the root
        if self.status != "draft":
            raise ValueError("Cannot modify submitted order")
        item = OrderItem(sku, quantity, price)
        self.items.append(item)
    
    def submit(self):
        if not self.items:
            raise ValueError("Cannot submit empty order")
        self.status = "submitted"
        # publish OrderSubmitted event
```

The aggregate enforces invariants:
- "An order cannot have items added after submission."
- "An order must have at least one item to be submitted."
- "An order's total is the sum of item prices × quantities."

All these are enforced by the root's methods; external code can't bypass them.

### Repositories

A repository is an abstraction over persistence, providing collection-like access to aggregates:

```python
class OrderRepository:
    def find_by_id(self, id: int) -> Order: ...
    def save(self, order: Order) -> None: ...
    def find_by_customer(self, customer_id: int) -> List[Order]: ...
```

The application code doesn't know whether the repository uses SQL, NoSQL, or a file system. The repository's interface is domain-focused (find_by_customer, not raw SQL queries).

### Domain Events

A domain event represents something significant that happened in the domain. Other bounded contexts can subscribe to these events.

```python
@dataclass
class OrderSubmitted:
    order_id: int
    customer_id: int
    submitted_at: datetime
```

The sales context publishes `OrderSubmitted`; the shipping context subscribes and creates a shipment. This decouples the contexts.

## Production Patterns

### Pattern 1: Microservice per Bounded Context

Each bounded context is a microservice:

```text
Sales Service (Sales Context)
Inventory Service (Inventory Context)
Shipping Service (Shipping Context)
```

Services communicate via events (Kafka, RabbitMQ) or APIs. The bounded context boundary is the service boundary.

### Pattern 2: Anticorruption Layer for Legacy Integration

When integrating with a legacy system, an ACL translates the legacy's model to the new system's model:

```python
class LegacyOrderTranslator:
    def to_modern_order(self, legacy_row):
        return Order(
            id=int(legacy_row['order_id']),
            customer_id=int(legacy_row['cust_id']),
            items=[self._to_item(item) for item in legacy_row['items']]
        )
```

The ACL is in the new system; the legacy system is untouched.

### Pattern 3: Event Storming for Domain Discovery

Event Storming is a workshop format where developers and domain experts collaborate to discover the domain model:

1. Post-its on a wall represent domain events ("Order Submitted", "Payment Received").
2. The events are arranged in time order.
3. Commands (what triggers events) are added.
4. Aggregates are identified by grouping events.
5. Bounded contexts emerge from natural clusters.

Event Storming is a fast way to start a DDD project — a 1-day workshop produces a domain model that would take weeks to discover otherwise.

## When DDD Helps

DDD's overhead is significant (workshops, ubiquitous language, aggregates, repositories). It's worth it for:
- **Complex domains** (financial trading, healthcare, logistics) where the business logic is the heart of the software.
- **Long-lived software** that will evolve over years — the investment in a clear model pays off.
- **Multi-team software** where bounded contexts prevent model pollution.

DDD is overkill for:
- **CRUD apps** (admin panels, simple CRUD services).
- **Short-lived software** (prototypes, demos).
- **Single-team software** where model pollution isn't a concern.

## Common Pitfalls

1. **Treating entities as aggregates.** Not every entity should be an aggregate root. A `Money` value object doesn't need its own repository.

2. **Forgetting that aggregates enforce invariants.** If the invariant can be bypassed by direct attribute access, the aggregate isn't really protecting anything.

3. **Confusing bounded contexts with modules.** A bounded context is a model boundary, not necessarily a code boundary. Two contexts in the same codebase are still two contexts.

4. **Trying to model the whole enterprise in one bounded context.** This leads to a "universal model" that doesn't fit any specific use case.

5. **Forgetting that ubiquitous language evolves.** As the team learns more about the domain, terms should be renamed. Resist the urge to freeze the language.

6. **Using DDD for CRUD.** A simple CRUD app doesn't need aggregates, repositories, or domain events. Use DDD where it adds value.

## References

- Eric Evans, "[Domain-Driven Design: Tackling Complexity in the Heart of Software](https://www.domainlanguage.com/ddd/)" (Addison-Wesley 2003)
- Vaughn Vernon, "[Implementing Domain-Driven Design](https://www.dddcommunity.com/book/vernon_2011/)" (Addison-Wesley 2013)
- [DDD Community](https://www.dddcommunity.com/)
- Eric Evans, "[Domain-Driven Design Reference](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_1.0.pdf)" (2016)
- [Event Storming](https://www.eventstorming.com/) (Alberto Brandolini's site)
- Martin Fowler, "[Bounded Context](https://martinfowler.com/bliki/BoundedContext.html)"
- [LWN: DDD overview (2020)](https://lwn.net/Articles/815571/)
