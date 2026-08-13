# Object-Oriented Programming Patterns

Object-oriented programming (OOP) patterns provide proven solutions to recurring design problems. This section covers the SOLID principles in depth and the Gang of Four (GoF) design patterns, with practical code examples in Java and Python. These patterns are essential for writing maintainable, extensible, and testable code—skills that are heavily tested in technical interviews and critical for real-world software development.

## Why Patterns Matter

Design patterns emerged from decades of software engineering experience. They provide a shared vocabulary for developers, enable more flexible architectures, and help avoid common pitfalls. Understanding patterns is not about memorizing implementations—it is about recognizing problems and knowing which tools to apply.

Patterns serve three purposes:
1. **Communication**: Saying "use a Strategy pattern here" conveys a design decision instantly
2. **Proven solutions**: Patterns have been tested across thousands of real-world systems
3. **Design principles**: Patterns embody deeper principles like loose coupling, high cohesion, and the Open-Closed Principle

## SOLID Principles

The SOLID principles are five design principles that guide object-oriented design toward more maintainable and flexible code:

- **S** - Single Responsibility Principle (SRP)
- **O** - Open-Closed Principle (OCP)
- **L** - Liskov Substitution Principle (LSP)
- **I** - Interface Segregation Principle (ISP)
- **D** - Dependency Inversion Principle (DIP)

See [SOLID Deep Dive](solid-deep-dive.md) for detailed explanations with code examples, violations, and refactoring techniques.

## Design Patterns

Design patterns are categorized into three groups:

### Creational Patterns
Deal with object creation mechanisms, trying to create objects in a manner suitable to the situation.

| Pattern | Intent | When to Use |
|---------|--------|-------------|
| [Singleton](design-patterns-creational.md#singleton) | Ensure a class has only one instance | Configuration, connection pools, logging |
| [Factory Method](design-patterns-creational.md#factory-method) | Create objects without specifying exact class | When the type of object is determined at runtime |
| [Abstract Factory](design-patterns-creational.md#abstract-factory) | Create families of related objects | Cross-platform UI toolkits, database drivers |
| [Builder](design-patterns-creational.md#builder) | Construct complex objects step by step | Objects with many optional parameters |
| [Prototype](design-patterns-creational.md#prototype) | Clone existing objects | When object creation is expensive |

### Structural Patterns
Deal with object composition, forming larger structures from individual objects.

| Pattern | Intent | When to Use |
|---------|--------|-------------|
| [Adapter](design-patterns-structural-behavioral.md#adapter) | Convert one interface to another | Integrating legacy code or third-party libraries |
| [Decorator](design-patterns-structural-behavioral.md#decorator) | Add behavior dynamically | Adding features without modifying original class |
| [Facade](design-patterns-structural-behavioral.md#facade) | Simplify a complex subsystem | Providing a simple API over complex internals |
| [Proxy](design-patterns-structural-behavioral.md#proxy) | Control access to an object | Lazy loading, access control, caching |

### Behavioral Patterns
Deal with communication between objects and the assignment of responsibilities.

| Pattern | Intent | When to Use |
|---------|--------|-------------|
| [Observer](design-patterns-structural-behavioral.md#observer) | Notify dependents of state changes | Event systems, UI updates, pub/sub |
| [Strategy](design-patterns-structural-behavioral.md#strategy) | Encapsulate interchangeable algorithms | Sorting, payment processing, validation |
| [Command](design-patterns-structural-behavioral.md#command) | Encapsulate a request as an object | Undo/redo, task queues, macro recording |
| [Iterator](design-patterns-structural-behavioral.md#iterator) | Sequential access without exposing internals | Custom collections, lazy evaluation |

## Topics in This Section

| Topic | Description |
|-------|-------------|
| [SOLID Deep Dive](solid-deep-dive.md) | Each principle with Java/Python code, violations, and refactoring |
| [Creational Patterns](design-patterns-creational.md) | Singleton, Factory, Abstract Factory, Builder, Prototype |
| [Structural & Behavioral Patterns](design-patterns-structural-behavioral.md) | Adapter, Decorator, Facade, Proxy, Observer, Strategy, Command, Iterator |

## How to Approach Pattern Questions in Interviews

1. **Identify the problem**: What design challenge are you facing? Tight coupling? Rigid object creation? Extensibility?
2. **Match to a pattern**: Which pattern addresses this specific problem?
3. **Explain the trade-off**: Every pattern adds complexity. Explain why the benefit outweighs the cost.
4. **Code it out**: Be ready to implement the pattern from scratch, not just describe it.
5. **Give real examples**: Connect the pattern to real-world systems you have worked with.

## Recommended Reading

- *Design Patterns: Elements of Reusable Object-Oriented Software* by Gamma, Helm, Johnson, Vlissides (Gang of Four)
- *Head First Design Patterns* by Freeman & Robson
- *Clean Architecture* by Robert C. Martin
- *Refactoring* by Martin Fowler
