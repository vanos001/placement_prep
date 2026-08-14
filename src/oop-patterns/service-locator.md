# Service Locator Pattern

## Intent

Provide a global point of access to a service without the consumer having to know how to construct it. The service locator acts as a registry that maps interfaces to concrete implementations.

## How It Works

```python
class ServiceLocator:
    _services = {}

    @classmethod
    def register(cls, interface, implementation):
        cls._services[interface] = implementation

    @classmethod
    def get(cls, interface):
        if interface not in cls._services:
            raise ValueError(f'No service registered for {interface}')
        return cls._services[interface]()

# Registration (typically at app startup)
ServiceLocator.register(ILogger, FileLogger)
ServiceLocator.register(IDatabase, PostgresDB)

# Usage
logger = ServiceLocator.get(ILogger)
logger.log('Hello')
```

## Service Locator vs Dependency Injection

| Aspect | Service Locator | Dependency Injection |
--------|----------------|---------------------|
| Who resolves deps? | Consumer asks for them | Framework/container provides them |
| Coupling | Consumer depends on the locator | Consumer depends only on abstractions |
| Testability | Harder to swap in tests | Easy to inject mocks via constructor |
| Visibility | Dependencies hidden in method bodies | Dependencies explicit in constructors |
| Compile-time safety | Runtime errors for missing services | Compile-time errors (constructor params) |

## Why It's Considered an Anti-Pattern

1. **Hidden dependencies**: Reading a class doesn't reveal what services it needs — they're buried in method calls.
2. **Runtime failures**: A missing registration causes a runtime crash, not a compile error.
3. **Tight coupling to the locator itself**: Every consumer imports the ServiceLocator.
4. **Testability friction**: Tests must set up the global registry instead of passing mocks directly.

## When to Use Anyway

- Migrating a legacy codebase to DI incrementally (locator as an intermediate step).
- Frameworks where DI containers aren't available (e.g., constrained embedded environments).
- Plugin architectures where dynamic registration is a core requirement.

## Interview Questions

**Q: Why is service locator often called an anti-pattern?**
A: It hides dependencies (not visible at construction), introduces runtime coupling to the locator, and makes testing harder. DI makes dependencies explicit in constructors, enables compile-time checking, and simplifies unit testing with injected mocks.

**Q: Can service locator and DI coexist?**
A: Yes, in practice they often do during migrations. Use DI for new code and the service locator for legacy modules. Gradually refactor locators into constructor-injected dependencies.

## References

- [Martin Fowler — Inversion of Control Containers and the Dependency Injection Pattern](https://martinfowler.com/articles/injection.html)
- [Mark Seemann — Service Locator is an Anti-Pattern](https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/)
- See also: [SOLID Deep Dive](./solid-deep-dive.md), [Creational Patterns](./design-patterns-creational.md), [Structural & Behavioral Patterns](./design-patterns-structural-behavioral.md)
