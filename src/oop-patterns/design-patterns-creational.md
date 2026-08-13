# Creational Design Patterns

Creational design patterns deal with object creation mechanisms. They abstract the instantiation process, making a system independent of how its objects are created, composed, and represented. Instead of creating objects directly with `new`, these patterns provide mechanisms that increase flexibility and reuse of existing code.

## Singleton

### Intent
Ensure a class has only one instance and provide a global point of access to it.

### When to Use
- Configuration managers that maintain application-wide settings
- Database connection pools that should be shared
- Logging services
- Thread pools and caches

### Thread-Safe Implementation (Java)
```java
public class ConfigurationManager {
    // volatile ensures visibility across threads
    private static volatile ConfigurationManager instance;
    private Map<String, String> config;
    
    // Private constructor prevents external instantiation
    private ConfigurationManager() {
        config = new HashMap<>();
        loadConfiguration();
    }
    
    // Double-checked locking for thread safety
    public static ConfigurationManager getInstance() {
        if (instance == null) {                    // First check (no lock)
            synchronized (ConfigurationManager.class) {
                if (instance == null) {            // Second check (with lock)
                    instance = new ConfigurationManager();
                }
            }
        }
        return instance;
    }
    
    private void loadConfiguration() {
        // Load from file, environment, etc.
        config.put("db.host", "localhost");
        config.put("db.port", "5432");
    }
    
    public String get(String key) {
        return config.get(key);
    }
    
    public void set(String key, String value) {
        config.put(key, value);
    }
}
```

### Bill Pugh Singleton (Java - Recommended)
```java
// Thread-safe without synchronization overhead
// Uses the Java class loading mechanism
public class ConfigurationManager {
    
    private ConfigurationManager() {
        // Load configuration
    }
    
    // Inner static class is not loaded until getInstance() is called
    private static class Holder {
        private static final ConfigurationManager INSTANCE = new ConfigurationManager();
    }
    
    public static ConfigurationManager getInstance() {
        return Holder.INSTANCE;
    }
}
```

### Enum Singleton (Java - Most Robust)
```java
// Thread-safe, serialization-safe, reflection-safe
public enum ConfigurationManager {
    INSTANCE;
    
    private Map<String, String> config = new HashMap<>();
    
    public String get(String key) { return config.get(key); }
    public void set(String key, String value) { config.put(key, value); }
}

// Usage: ConfigurationManager.INSTANCE.get("db.host");
```

### Python Implementation
```python
class ConfigurationManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ConfigurationManager._initialized:
            self.config = {}
            self._load_config()
            ConfigurationManager._initialized = True
    
    def _load_config(self):
        self.config = {
            'db.host': 'localhost',
            'db.port': '5432',
        }
    
    def get(self, key):
        return self.config.get(key)

# Alternative: Module-level singleton (Pythonic)
# Just create the instance at module level
# config.py:
#   class _Config: ...
#   instance = _Config()
```

### Singleton Pitfalls
- **Hidden dependencies**: Classes that use Singleton.getInstance() have a hidden global dependency
- **Testing difficulty**: Hard to mock or replace in tests
- **Thread safety**: Non-thread-safe implementations cause subtle bugs under concurrency
- **Lifetime management**: Singleton lives for the application lifetime; no way to reset or dispose

### Better Alternative: Dependency Injection
```java
// Instead of Singleton.getInstance(), inject the dependency
public class OrderService {
    private final ConfigurationManager config;
    
    public OrderService(ConfigurationManager config) {
        this.config = config;  // Injected, mockable in tests
    }
}

// In your composition root (e.g., Spring configuration)
@Configuration
public class AppConfig {
    @Bean
    public ConfigurationManager configurationManager() {
        return new ConfigurationManager();  // Spring manages the lifecycle
    }
    
    @Bean
    public OrderService orderService(ConfigurationManager config) {
        return new OrderService(config);
    }
}
```

---

## Factory Method

### Intent
Define an interface for creating objects, but let subclasses decide which class to instantiate. Factory Method lets a class defer instantiation to subclasses.

### When to Use
- The exact type of object to create is determined at runtime
- You want to provide a library of products that exposes only their interfaces, not implementations
- You want to localize the knowledge of which class gets created

### Java Implementation
```java
// Product interface
public interface Transport {
    void deliver();
    double getCost();
}

// Concrete products
public class Truck implements Transport {
    @Override
    public void deliver() {
        System.out.println("Delivering by land in a truck");
    }
    
    @Override
    public double getCost() { return 100.0; }
}

public class Ship implements Transport {
    @Override
    public void deliver() {
        System.out.println("Delivering by sea in a ship");
    }
    
    @Override
    public double getCost() { return 50.0; }
}

public class Airplane implements Transport {
    @Override
    public void deliver() {
        System.out.println("Delivering by air in an airplane");
    }
    
    @Override
    public double getCost() { return 500.0; }
}

// Creator with factory method
public abstract class Logistics {
    // Factory method - subclasses decide which transport to create
    protected abstract Transport createTransport();
    
    public void planDelivery() {
        Transport transport = createTransport();
        System.out.println("Planning delivery...");
        transport.deliver();
        System.out.println("Cost: $" + transport.getCost());
    }
}

// Concrete creators
public class RoadLogistics extends Logistics {
    @Override
    protected Transport createTransport() {
        return new Truck();
    }
}

public class SeaLogistics extends Logistics {
    @Override
    protected Transport createTransport() {
        return new Ship();
    }
}

public class AirLogistics extends Logistics {
    @Override
    protected Transport createTransport() {
        return new Airplane();
    }
}
```

### Python Implementation
```python
from abc import ABC, abstractmethod

class Transport(ABC):
    @abstractmethod
    def deliver(self): pass
    
    @abstractmethod
    def get_cost(self) -> float: pass

class Truck(Transport):
    def deliver(self):
        print("Delivering by land in a truck")
    def get_cost(self):
        return 100.0

class Ship(Transport):
    def deliver(self):
        print("Delivering by sea in a ship")
    def get_cost(self):
        return 50.0

class Logistics(ABC):
    @abstractmethod
    def create_transport(self) -> Transport: pass
    
    def plan_delivery(self):
        transport = self.create_transport()
        print("Planning delivery...")
        transport.deliver()
        print(f"Cost: ${transport.get_cost()}")

class RoadLogistics(Logistics):
    def create_transport(self) -> Transport:
        return Truck()

class SeaLogistics(Logistics):
    def create_transport(self) -> Transport:
        return Ship()

# Simple factory function (Pythonic alternative)
def create_transport(mode: str) -> Transport:
    transports = {
        'truck': Truck,
        'ship': Ship,
    }
    if mode not in transports:
        raise ValueError(f"Unknown transport mode: {mode}")
    return transports[mode]()
```

---

## Abstract Factory

### Intent
Provide an interface for creating families of related or dependent objects without specifying their concrete classes.

### When to Use
- A system must be independent of how its products are created
- A system must work with multiple families of products
- Related product objects are designed to be used together
- You want to enforce constraints about which products can be used together

### Java Implementation
```java
// Abstract products
public interface Button {
    void render();
    void onClick(Runnable action);
}

public interface Checkbox {
    void render();
    void toggle();
}

public interface TextInput {
    void render();
    String getValue();
}

// Abstract factory
public interface UIFactory {
    Button createButton();
    Checkbox createCheckbox();
    TextInput createTextInput();
}

// Light theme products
public class LightButton implements Button {
    @Override
    public void render() { System.out.println("Rendering light button"); }
    @Override
    public void onClick(Runnable action) { action.run(); }
}

public class LightCheckbox implements Checkbox {
    private boolean checked = false;
    @Override
    public void render() { System.out.println("Rendering light checkbox"); }
    @Override
    public void toggle() { checked = !checked; }
}

// Dark theme products
public class DarkButton implements Button {
    @Override
    public void render() { System.out.println("Rendering dark button"); }
    @Override
    public void onClick(Runnable action) { action.run(); }
}

public class DarkCheckbox implements Checkbox {
    private boolean checked = false;
    @Override
    public void render() { System.out.println("Rendering dark checkbox"); }
    @Override
    public void toggle() { checked = !checked; }
}

// Concrete factories
public class LightThemeFactory implements UIFactory {
    @Override
    public Button createButton() { return new LightButton(); }
    @Override
    public Checkbox createCheckbox() { return new LightCheckbox(); }
    @Override
    public TextInput createTextInput() { return new LightTextInput(); }
}

public class DarkThemeFactory implements UIFactory {
    @Override
    public Button createButton() { return new DarkButton(); }
    @Override
    public Checkbox createCheckbox() { return new DarkCheckbox(); }
    @Override
    public TextInput createTextInput() { return new DarkTextInput(); }
}

// Client code - works with any theme
public class Application {
    private UIFactory factory;
    
    public Application(UIFactory factory) {
        this.factory = factory;
    }
    
    public void createUI() {
        Button button = factory.createButton();
        Checkbox checkbox = factory.createCheckbox();
        button.render();
        checkbox.render();
    }
}

// Usage
Application lightApp = new Application(new LightThemeFactory());
Application darkApp = new Application(new DarkThemeFactory());
```

### Python Implementation
```python
from abc import ABC, abstractmethod

class Button(ABC):
    @abstractmethod
    def render(self): pass

class Checkbox(ABC):
    @abstractmethod
    def render(self): pass

class UIFactory(ABC):
    @abstractmethod
    def create_button(self) -> Button: pass
    
    @abstractmethod
    def create_checkbox(self) -> Checkbox: pass

class LightButton(Button):
    def render(self):
        print("Light button")

class DarkButton(Button):
    def render(self):
        print("Dark button")

class LightThemeFactory(UIFactory):
    def create_button(self): return LightButton()
    def create_checkbox(self): return LightCheckbox()

class DarkThemeFactory(UIFactory):
    def create_button(self): return DarkButton()
    def create_checkbox(self): return DarkCheckbox()

class Application:
    def __init__(self, factory: UIFactory):
        self.factory = factory
    
    def create_ui(self):
        button = self.factory.create_button()
        button.render()
```

---

## Builder

### Intent
Separate the construction of a complex object from its representation. The same construction process can create different representations.

### When to Use
- Objects with many optional parameters (telescoping constructor anti-pattern)
- Construction involves multiple steps that must follow a specific order
- You want to create different representations of the same construction process
- Immutable objects that need complex construction

### Java Implementation
```java
public class HttpRequest {
    private final String url;
    private final String method;
    private final Map<String, String> headers;
    private final Map<String, String> queryParams;
    private final String body;
    private final int timeout;
    private final boolean followRedirects;
    private final int retryCount;
    
    private HttpRequest(Builder builder) {
        this.url = builder.url;
        this.method = builder.method;
        this.headers = Collections.unmodifiableMap(builder.headers);
        this.queryParams = Collections.unmodifiableMap(builder.queryParams);
        this.body = builder.body;
        this.timeout = builder.timeout;
        this.followRedirects = builder.followRedirects;
        this.retryCount = builder.retryCount;
    }
    
    // Getters...
    public String getUrl() { return url; }
    public String getMethod() { return method; }
    public Map<String, String> getHeaders() { return headers; }
    
    public static class Builder {
        // Required parameters
        private final String url;
        private String method = "GET";
        
        // Optional parameters with defaults
        private Map<String, String> headers = new HashMap<>();
        private Map<String, String> queryParams = new HashMap<>();
        private String body = null;
        private int timeout = 30000;
        private boolean followRedirects = true;
        private int retryCount = 3;
        
        public Builder(String url) {
            this.url = url;
        }
        
        public Builder method(String method) {
            this.method = method;
            return this;
        }
        
        public Builder header(String key, String value) {
            this.headers.put(key, value);
            return this;
        }
        
        public Builder queryParam(String key, String value) {
            this.queryParams.put(key, value);
            return this;
        }
        
        public Builder body(String body) {
            this.body = body;
            return this;
        }
        
        public Builder timeout(int timeout) {
            this.timeout = timeout;
            return this;
        }
        
        public Builder followRedirects(boolean follow) {
            this.followRedirects = follow;
            return this;
        }
        
        public Builder retryCount(int count) {
            this.retryCount = count;
            return this;
        }
        
        public HttpRequest build() {
            // Validation
            if (url == null || url.isEmpty()) {
                throw new IllegalStateException("URL is required");
            }
            if (body != null && "GET".equals(method)) {
                throw new IllegalStateException("GET requests cannot have a body");
            }
            return new HttpRequest(this);
        }
    }
}

// Usage - fluent and readable
HttpRequest request = new HttpRequest.Builder("https://api.example.com/users")
    .method("POST")
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer token123")
    .body("{\"name\": \"John\"}")
    .timeout(5000)
    .retryCount(2)
    .build();
```

### Python Implementation
```python
class HttpRequest:
    def __init__(self, builder):
        self.url = builder.url
        self.method = builder._method
        self.headers = dict(builder._headers)
        self.body = builder._body
        self.timeout = builder._timeout
    
    class Builder:
        def __init__(self, url):
            self.url = url
            self._method = "GET"
            self._headers = {}
            self._body = None
            self._timeout = 30
        
        def method(self, method):
            self._method = method
            return self
        
        def header(self, key, value):
            self._headers[key] = value
            return self
        
        def body(self, body):
            self._body = body
            return self
        
        def timeout(self, timeout):
            self._timeout = timeout
            return self
        
        def build(self):
            if not self.url:
                raise ValueError("URL is required")
            return HttpRequest(self)

# Usage
request = (HttpRequest.Builder("https://api.example.com/users")
    .method("POST")
    .header("Content-Type", "application/json")
    .body('{"name": "John"}')
    .timeout(5)
    .build())
```

### Builder with Director (Java)
```java
// Director defines the construction process
public class HttpRequestDirector {
    public HttpRequest createGetRequest(String url) {
        return new HttpRequest.Builder(url)
            .method("GET")
            .header("Accept", "application/json")
            .build();
    }
    
    public HttpRequest createPostRequest(String url, String body) {
        return new HttpRequest.Builder(url)
            .method("POST")
            .header("Content-Type", "application/json")
            .body(body)
            .retryCount(1)
            .build();
    }
}
```

---

## Prototype

### Intent
Specify the kinds of objects to create using a prototypical instance, and create new objects by copying (cloning) this prototype.

### When to Use
- Object creation is expensive (complex initialization, network calls, database queries)
- You need many similar objects with slight variations
- You want to avoid subclasses of an object creator (the Factory hierarchy)

### Java Implementation
```java
public abstract class Shape implements Cloneable {
    protected String color;
    protected int x, y;
    
    public Shape(String color, int x, int y) {
        this.color = color;
        this.x = x;
        this.y = y;
    }
    
    // Clone method
    @Override
    public Shape clone() {
        try {
            return (Shape) super.clone();  // Shallow copy
        } catch (CloneNotSupportedException e) {
            throw new RuntimeException(e);
        }
    }
    
    public abstract Shape deepCopy();
    
    public void setPosition(int x, int y) {
        this.x = x;
        this.y = y;
    }
    
    @Override
    public String toString() {
        return String.format("%s[color=%s, x=%d, y=%d]", getClass().getSimpleName(), color, x, y);
    }
}

public class Circle extends Shape {
    private double radius;
    
    public Circle(String color, int x, int y, double radius) {
        super(color, x, y);
        this.radius = radius;
    }
    
    @Override
    public Shape deepCopy() {
        return new Circle(this.color, this.x, this.y, this.radius);
    }
}

public class Rectangle extends Shape {
    private double width, height;
    
    public Rectangle(String color, int x, int y, double width, double height) {
        super(color, x, y);
        this.width = width;
        this.height = height;
    }
    
    @Override
    public Shape deepCopy() {
        return new Rectangle(this.color, this.x, this.y, this.width, this.height);
    }
}

// Prototype registry
public class ShapeRegistry {
    private Map<String, Shape> prototypes = new HashMap<>();
    
    public void register(String key, Shape prototype) {
        prototypes.put(key, prototype);
    }
    
    public Shape create(String key) {
        Shape prototype = prototypes.get(key);
        if (prototype == null) {
            throw new IllegalArgumentException("Unknown prototype: " + key);
        }
        return prototype.deepCopy();
    }
}

// Usage
ShapeRegistry registry = new ShapeRegistry();
registry.register("red-circle", new Circle("red", 0, 0, 10));
registry.register("blue-rect", new Rectangle("blue", 0, 0, 20, 30));

// Clone and customize
Shape circle1 = registry.create("red-circle");
circle1.setPosition(50, 50);

Shape circle2 = registry.create("red-circle");
circle2.setPosition(100, 100);
```

### Python Implementation
```python
import copy

class Shape:
    def __init__(self, color, x=0, y=0):
        self.color = color
        self.x = x
        self.y = y
    
    def clone(self):
        return copy.deepcopy(self)
    
    def __repr__(self):
        return f"{self.__class__.__name__}(color={self.color}, x={self.x}, y={self.y})"

class Circle(Shape):
    def __init__(self, color, x=0, y=0, radius=1):
        super().__init__(color, x, y)
        self.radius = radius

class ShapeRegistry:
    def __init__(self):
        self._prototypes = {}
    
    def register(self, key, prototype):
        self._prototypes[key] = prototype
    
    def create(self, key):
        prototype = self._prototypes.get(key)
        if not prototype:
            raise ValueError(f"Unknown prototype: {key}")
        return prototype.clone()

# Usage
registry = ShapeRegistry()
registry.register("red-circle", Circle("red", 0, 0, 10))

circle1 = registry.create("red-circle")
circle1.x = 50
circle1.y = 50

circle2 = registry.create("red-circle")  # Independent copy
```

---

## Summary

| Pattern | Key Idea | Trade-off |
|---------|----------|-----------|
| **Singleton** | One instance, global access | Hard to test, hidden dependency |
| **Factory Method** | Subclass decides which class to create | More classes to maintain |
| **Abstract Factory** | Create families of related objects | Adding new product types requires changing all factories |
| **Builder** | Step-by-step construction of complex objects | More code, builder class needed |
| **Prototype** | Clone existing objects instead of creating new ones | Deep vs shallow copy complexity |
