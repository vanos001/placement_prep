# Low Level Design (LLD) - Overview

## What is Low Level Design?

Low Level Design (LLD) is the process of designing the **internal structure of a system's components** at the class and object level. It focuses on how individual modules are implemented using OOP principles, design patterns, and clean code practices.

In an LLD interview, you're asked to design the class structure for a specific component — think "Design a Parking Lot system" or "Design an Elevator system" — by creating classes, defining relationships, and applying design patterns.

## What Interviewers Expect

### 1. Requirements Gathering (2-3 minutes)
- Clarify functional requirements
- Identify actors and use cases
- Define scope boundaries

### 2. Class Identification (5-7 minutes)
- Identify core classes (nouns in requirements)
- Define attributes and methods
- Establish relationships between classes

### 3. Design Patterns (3-5 minutes)
- Apply appropriate design patterns
- Justify why each pattern fits
- Show awareness of trade-offs

### 4. Code Implementation (10-15 minutes)
- Write key classes and interfaces
- Implement core logic
- Handle edge cases

### 5. Discussion (5 minutes)
- SOLID principles applied
- Extensibility considerations
- Error handling strategy

## OOP Principles Quick Reference

### The Four Pillars

```
┌─────────────────────────────────────────────┐
│              OOP Principles                  │
├──────────┬──────────┬──────────┬────────────┤
│Encapsula │ Inherita │ Polymorp │ Abstraction│
│tion      │ nce      │ hism     │            │
├──────────┼──────────┼──────────┼────────────┤
│Hide      │ "is-a"   │ One      │ Hide       │
│internal  │ relation │ interface│ complex    │
│state     │ ship     │ many     │ details    │
│          │          │ forms    │            │
└──────────┴──────────┴──────────┴────────────┘
```

| Principle | What | Why | Example |
|-----------|------|-----|---------|
| **Encapsulation** | Hide internal state, expose methods | Control access, reduce coupling | Private fields + getters/setters |
| **Inheritance** | Child class inherits from parent | Code reuse, hierarchy | Car extends Vehicle |
| **Polymorphism** | Same interface, different implementations | Flexibility, extensibility | Payment.process() → CardPayment, UPIPayment |
| **Abstraction** | Hide complexity, show essentials | Reduce complexity | Database interface hides SQL details |

## Design Patterns in LLD

### Pattern Categories

```
┌─────────────────────────────────────────────┐
│           Design Patterns                    │
├──────────┬──────────────┬───────────────────┤
│Creational│ Structural   │ Behavioral        │
├──────────┼──────────────┼───────────────────┤
│Singleton │ Adapter      │ Observer          │
│Factory   │ Decorator    │ Strategy          │
│Builder   │ Proxy        │ Command           │
│Prototype │ Facade       │ Iterator          │
│          │ Composite    │ State             │
│          │              │ Template Method   │
└──────────┴──────────────┴───────────────────┘
```

### When to Use Which Pattern

| Problem | Pattern | Example |
|---------|---------|---------|
| Need exactly one instance | Singleton | Database connection pool |
| Create objects based on type | Factory | Payment processor creation |
| Complex object construction | Builder | Building a House object |
| Add behavior dynamically | Decorator | Adding toppings to pizza |
| Convert incompatible interfaces | Adapter | Old API to new interface |
| Control access to object | Proxy | Lazy loading, caching proxy |
| Notify dependents of changes | Observer | UI event handling |
| Algorithm varies at runtime | Strategy | Sorting algorithms |
| Encapsulate a request | Command | Undo/redo operations |
| Object changes behavior by state | State | Vending machine states |

## UML Class Diagrams

### Relationships

```
Association:    A ──────── B  (A uses B)
Aggregation:    A ◇─────── B  (A has B, B can exist independently)
Composition:    A ◆─────── B  (A owns B, B cannot exist without A)
Inheritance:    A ───────▷ B  (A extends B)
Dependency:     A - - - - → B  (A depends on B temporarily)
```

### Multiplicity

```
1     Exactly one
0..1  Zero or one
*     Many (zero or more)
1..1  One or more
```

## Common LLD Interview Problems

| Problem | Key Concepts | Patterns |
|---------|-------------|----------|
| Parking Lot | Multiple vehicle types, floors | Strategy, Factory |
| Elevator | State machine, scheduling | State, Strategy, Observer |
| Library Management | Book checkout, reservations | Observer, Strategy |
| ATM | State machine, transactions | State, Command, Strategy |
| Chess | Board, pieces, moves | Strategy, Factory |
| LinkedIn/Twitter | Users, posts, feeds | Observer, Strategy |
| Uber | Matching, pricing | Strategy, Observer |
| Food Delivery | Orders, restaurants | State, Observer |
| Movie Ticket | Booking, seats | Strategy, Observer |
| File System | Files, directories | Composite, Iterator |
| Notification Service | Multiple channels | Strategy, Observer, Decorator |
| LRU Cache | Cache eviction | Strategy (eviction) |
| Key-Value Store | Storage, retrieval | Strategy, Composite |

## LLD Interview Tips

1. **Clarify requirements first** — "What are the main actors? What operations are needed?"
2. **Start with core classes** — Identify nouns, then verbs
3. **Draw class diagrams** — Always sketch relationships
4. **Apply patterns naturally** — Don't force patterns; use them where they fit
5. **Code the critical parts** — Implement key methods, not boilerplate
6. **Discuss trade-offs** — "I chose composition over inheritance because..."
7. **Handle edge cases** — "What if the parking lot is full?"
8. **Think about extensibility** — "How would we add a new vehicle type?"

## How to Approach LLD Problems

### Step-by-Step Process

```
1. Requirements (2 min)
   - Who are the actors?
   - What are the use cases?
   - What are the constraints?

2. Identify Classes (3 min)
   - Nouns → Classes
   - Verbs → Methods
   - Adjectives → Attributes

3. Define Relationships (3 min)
   - "has-a" → Composition/Aggregation
   - "is-a" → Inheritance
   - "uses" → Association/Dependency

4. Apply Design Patterns (3 min)
   - What pattern fits each requirement?
   - Justify your choice

5. Implement Code (15 min)
   - Write interfaces first
   - Implement core classes
   - Add key methods

6. Discuss (5 min)
   - SOLID principles
   - Extensibility
   - Edge cases
```

## Cross-References

- [SOLID Principles](./solid.md) — Foundation of good LLD
- [Design Patterns](./design-patterns.md) — Pattern catalog
- [OOP Concepts](./oop-concepts.md) — OOP deep dive
- [UML Class Diagrams](./uml-class-diagrams.md) — Diagramming skills

---

*Each LLD problem page in this section follows a consistent structure: requirements, class diagrams (Mermaid), code examples, patterns used, SOLID principles, edge cases, and interview tips.*
- [System Design Framework](../framework.md)
- [HLD Overview](../hld/README.md)

