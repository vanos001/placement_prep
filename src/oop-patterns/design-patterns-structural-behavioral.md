# Structural and Behavioral Design Patterns

Structural patterns deal with how classes and objects are composed to form larger structures. Behavioral patterns deal with communication between objects and the assignment of responsibilities. Together, they provide solutions for organizing code, managing dependencies, and defining how objects interact.

## Structural Patterns

---

## Adapter

### Intent
Convert the interface of a class into another interface that clients expect. Adapter lets classes work together that otherwise could not because of incompatible interfaces.

### When to Use
- Integrating a third-party library with an incompatible interface
- Making legacy code work with new systems
- Reusing existing classes that don't have the interface you need

### Java Implementation (Object Adapter)
```java
// Target interface expected by the client
public interface PaymentProcessor {
    PaymentResult processPayment(double amount, String currency);
    boolean refund(String transactionId, double amount);
}

// Adaptee: third-party payment library with incompatible interface
public class StripeGateway {
    public StripeResponse charge(StripeChargeRequest request) {
        // Stripe-specific implementation
        return new StripeResponse(true, "ch_abc123");
    }
    
    public StripeResponse createRefund(StripeRefundRequest request) {
        return new StripeResponse(true, "re_xyz789");
    }
}

// Adapter: makes StripeGateway compatible with PaymentProcessor
public class StripeAdapter implements PaymentProcessor {
    private final StripeGateway stripe;
    
    public StripeAdapter(StripeGateway stripe) {
        this.stripe = stripe;
    }
    
    @Override
    public PaymentResult processPayment(double amount, String currency) {
        StripeChargeRequest request = new StripeChargeRequest();
        request.setAmount((int) (amount * 100));  // Stripe uses cents
        request.setCurrency(currency.toLowerCase());
        
        StripeResponse response = stripe.charge(request);
        
        return new PaymentResult(
            response.isSuccess(),
            response.getTransactionId(),
            amount,
            currency
        );
    }
    
    @Override
    public boolean refund(String transactionId, double amount) {
        StripeRefundRequest request = new StripeRefundRequest();
        request.setChargeId(transactionId);
        request.setAmount((int) (amount * 100));
        
        return stripe.createRefund(request).isSuccess();
    }
}

// Client code works with any payment processor
public class CheckoutService {
    private final PaymentProcessor processor;
    
    public CheckoutService(PaymentProcessor processor) {
        this.processor = processor;
    }
    
    public PaymentResult charge(Order order) {
        return processor.processPayment(order.getTotal(), order.getCurrency());
    }
}

// Usage
PaymentProcessor stripe = new StripeAdapter(new StripeGateway());
PaymentProcessor paypal = new PayPalAdapter(new PayPalClient());
CheckoutService checkout = new CheckoutService(stripe);
```

### Python Implementation
```python
from abc import ABC, abstractmethod

# Target interface
class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: float, currency: str) -> dict: pass

# Adaptee (third-party library)
class StripeGateway:
    def charge(self, amount_cents: int, currency: str, token: str) -> dict:
        # Stripe-specific logic
        return {"success": True, "id": "ch_abc123"}

# Adapter
class StripeAdapter(PaymentProcessor):
    def __init__(self, stripe: StripeGateway):
        self.stripe = stripe
    
    def process_payment(self, amount: float, currency: str) -> dict:
        amount_cents = int(amount * 100)
        response = self.stripe.charge(amount_cents, currency.lower(), "tok_default")
        return {"success": response["success"], "transaction_id": response["id"]}

# Client
processor = StripeAdapter(StripeGateway())
result = processor.process_payment(99.99, "USD")
```

---

## Decorator

### Intent
Attach additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality.

### When to Use
- Adding features to objects without modifying their class
- Features can be combined in various ways
- Subclassing would create an explosion of classes

### Java Implementation (I/O Streams)
```java
// Component interface
public interface DataSource {
    void writeData(String data);
    String readData();
}

// Concrete component
public class FileDataSource implements DataSource {
    private String filename;
    
    public FileDataSource(String filename) {
        this.filename = filename;
    }
    
    @Override
    public void writeData(String data) {
        // Write to file
    }
    
    @Override
    public String readData() {
        // Read from file
        return "file data";
    }
}

// Base decorator
public abstract class DataSourceDecorator implements DataSource {
    protected DataSource wrappee;
    
    public DataSourceDecorator(DataSource wrappee) {
        this.wrappee = wrappee;
    }
    
    @Override
    public void writeData(String data) {
        wrappee.writeData(data);
    }
    
    @Override
    public String readData() {
        return wrappee.readData();
    }
}

// Concrete decorator: Encryption
public class EncryptionDecorator extends DataSourceDecorator {
    public EncryptionDecorator(DataSource wrappee) {
        super(wrappee);
    }
    
    @Override
    public void writeData(String data) {
        String encrypted = encrypt(data);
        super.writeData(encrypted);
    }
    
    @Override
    public String readData() {
        String data = super.readData();
        return decrypt(data);
    }
    
    private String encrypt(String data) {
        // Base64 encode as simple example
        return Base64.getEncoder().encodeToString(data.getBytes());
    }
    
    private String decrypt(String data) {
        return new String(Base64.getDecoder().decode(data));
    }
}

// Concrete decorator: Compression
public class CompressionDecorator extends DataSourceDecorator {
    public CompressionDecorator(DataSource wrappee) {
        super(wrappee);
    }
    
    @Override
    public void writeData(String data) {
        super.writeData(compress(data));
    }
    
    @Override
    public String readData() {
        return decompress(super.readData());
    }
    
    private String compress(String data) {
        // Simple compression logic
        return data;  // Placeholder
    }
    
    private String decompress(String data) {
        return data;  // Placeholder
    }
}

// Usage: Stack decorators for combined behavior
DataSource source = new EncryptionDecorator(
    new CompressionDecorator(
        new FileDataSource("data.txt")
    )
);
source.writeData("secret data");
// Writes: compressed, then encrypted data to file
```

### Python Implementation
```python
from abc import ABC, abstractmethod

class DataSource(ABC):
    @abstractmethod
    def write(self, data: str): pass
    
    @abstractmethod
    def read(self) -> str: pass

class FileDataSource(DataSource):
    def __init__(self, filename):
        self.filename = filename
    
    def write(self, data: str):
        with open(self.filename, 'w') as f:
            f.write(data)
    
    def read(self) -> str:
        with open(self.filename, 'r') as f:
            return f.read()

class DataSourceDecorator(DataSource):
    def __init__(self, wrappee: DataSource):
        self._wrappee = wrappee
    
    def write(self, data: str):
        self._wrappee.write(data)
    
    def read(self) -> str:
        return self._wrappee.read()

class EncryptionDecorator(DataSourceDecorator):
    def write(self, data: str):
        import base64
        encrypted = base64.b64encode(data.encode()).decode()
        super().write(encrypted)
    
    def read(self) -> str:
        import base64
        data = super().read()
        return base64.b64decode(data.encode()).decode()

class CompressionDecorator(DataSourceDecorator):
    def write(self, data: str):
        compressed = data.replace("  ", " ")  # Simplified
        super().write(compressed)
    
    def read(self) -> str:
        return super().read()

# Stack decorators
source = EncryptionDecorator(CompressionDecorator(FileDataSource("data.txt")))
source.write("secret data")
```

---

## Facade

### Intent
Provide a unified interface to a set of interfaces in a subsystem. Facade defines a higher-level interface that makes the subsystem easier to use.

### When to Use
- A subsystem is complex and clients only need a simplified interface
- You want to decouple clients from subsystem components
- You want to layer your subsystems

### Python Implementation
```python
# Complex subsystem classes
class CPU:
    def freeze(self): print("CPU: Freezing processor")
    def jump(self, address): print(f"CPU: Jumping to {address}")
    def execute(self): print("CPU: Executing instructions")

class Memory:
    def load(self, address, data): print(f"Memory: Loading data at {address}")
    def free(self, address): print(f"Memory: Freeing {address}")

class SSD:
    def read(self, sector):
        print(f"SSD: Reading sector {sector}")
        return "boot_data"
    def write(self, sector, data):
        print(f"SSD: Writing to sector {sector}")

class Bootloader:
    def load_kernel(self): print("Bootloader: Loading kernel")
    def init_drivers(self): print("Bootloader: Initializing drivers")

# Facade: simple interface to complex boot process
class ComputerFacade:
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()
        self.ssd = SSD()
        self.bootloader = Bootloader()
    
    def start(self):
        print("=== Starting Computer ===")
        self.cpu.freeze()
        boot_data = self.ssd.read(0)
        self.memory.load(0, boot_data)
        self.cpu.jump(0)
        self.cpu.execute()
        self.bootloader.load_kernel()
        self.bootloader.init_drivers()
        print("=== Computer Ready ===")
    
    def shutdown(self):
        print("=== Shutting Down ===")
        self.memory.free(0)
        print("=== Computer Off ===")

# Client uses simple interface
computer = ComputerFacade()
computer.start()  # One method call handles everything
computer.shutdown()
```

### Java Implementation
```java
public class OrderFacade {
    private InventoryService inventory;
    private PaymentService payment;
    private ShippingService shipping;
    private NotificationService notification;
    
    public OrderFacade() {
        this.inventory = new InventoryService();
        this.payment = new PaymentService();
        this.shipping = new ShippingService();
        this.notification = new NotificationService();
    }
    
    public OrderResult placeOrder(Order order) {
        // 1. Check inventory
        if (!inventory.checkAvailability(order.getItems())) {
            return OrderResult.failure("Items out of stock");
        }
        
        // 2. Reserve items
        inventory.reserve(order.getItems());
        
        // 3. Process payment
        PaymentResult paymentResult = payment.charge(order.getTotal(), order.getPaymentMethod());
        if (!paymentResult.isSuccess()) {
            inventory.release(order.getItems());
            return OrderResult.failure("Payment failed: " + paymentResult.getError());
        }
        
        // 4. Create shipment
        Shipment shipment = shipping.createShipment(order);
        
        // 5. Send confirmation
        notification.sendOrderConfirmation(order, shipment);
        
        return OrderResult.success(shipment.getTrackingNumber());
    }
}
```

---

## Proxy

### Intent
Provide a surrogate or placeholder for another object to control access to it.

### Types of Proxies
- **Virtual Proxy**: Lazy initialization of expensive objects
- **Protection Proxy**: Access control checks
- **Caching Proxy**: Cache results of expensive operations
- **Remote Proxy**: Represent an object in a different address space

### Python Implementation
```python
from abc import ABC, abstractmethod
import time

# Subject interface
class Image(ABC):
    @abstractmethod
    def display(self): pass

# Real subject (expensive to create)
class HighResImage(Image):
    def __init__(self, filename):
        self.filename = filename
        self._load_from_disk()
    
    def _load_from_disk(self):
        print(f"Loading {self.filename} from disk... (expensive)")
        time.sleep(1)  # Simulate slow loading
        self.data = f"Image data for {self.filename}"
    
    def display(self):
        print(f"Displaying {self.filename}")

# Virtual Proxy (lazy loading)
class ImageProxy(Image):
    def __init__(self, filename):
        self.filename = filename
        self._real_image = None
    
    def display(self):
        if self._real_image is None:
            self._real_image = HighResImage(self.filename)  # Load only when needed
        self._real_image.display()

# Caching Proxy
class CachedImageProxy(Image):
    _cache = {}
    
    def __init__(self, filename):
        self.filename = filename
    
    def display(self):
        if self.filename not in self._cache:
            self._cache[self.filename] = HighResImage(self.filename)
        self._cache[self.filename].display()

# Protection Proxy
class ProtectedImageProxy(Image):
    def __init__(self, filename, user_role):
        self.filename = filename
        self.user_role = user_role
        self._real_image = None
    
    def display(self):
        if self.user_role not in ('admin', 'viewer'):
            raise PermissionError(f"Role '{self.user_role}' cannot view images")
        if self._real_image is None:
            self._real_image = HighResImage(self.filename)
        self._real_image.display()

# Usage
images = [ImageProxy(f"photo_{i}.jpg") for i in range(100)]
# No loading happens yet
images[0].display()  # Loads only photo_0.jpg
images[0].display()  # Already loaded, no disk access
```

---

## Behavioral Patterns

---

## Observer

### Intent
Define a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.

### When to Use
- Event handling systems
- UI frameworks (model changes trigger view updates)
- Pub/sub messaging systems
- Reactive programming

### Java Implementation
```java
// Observer interface
public interface EventListener {
    void update(String eventType, String data);
}

// Subject (Observable)
public class EventManager {
    private Map<String, List<EventListener>> listeners = new HashMap<>();
    
    public void subscribe(String eventType, EventListener listener) {
        listeners.computeIfAbsent(eventType, k -> new ArrayList<>()).add(listener);
    }
    
    public void unsubscribe(String eventType, EventListener listener) {
        List<EventListener> list = listeners.get(eventType);
        if (list != null) list.remove(listener);
    }
    
    public void notify(String eventType, String data) {
        List<EventListener> list = listeners.get(eventType);
        if (list != null) {
            for (EventListener listener : list) {
                listener.update(eventType, data);
            }
        }
    }
}

// Concrete subject
public class Document {
    private EventManager events = new EventManager();
    private String content;
    
    public Document() {
        events.subscribe("open", new LoggingListener());
        events.subscribe("save", new LoggingListener());
        events.subscribe("save", new EmailNotificationListener());
    }
    
    public void open(String filename) {
        this.content = readFile(filename);
        events.notify("open", filename);
    }
    
    public void save() {
        writeToFile(content);
        events.notify("save", content);
    }
}

// Concrete observers
public class LoggingListener implements EventListener {
    @Override
    public void update(String eventType, String data) {
        System.out.println("[LOG] Event: " + eventType + ", Data: " + data);
    }
}

public class EmailNotificationListener implements EventListener {
    @Override
    public void update(String eventType, String data) {
        System.out.println("[EMAIL] Sending notification about: " + eventType);
    }
}
```

### Python Implementation
```python
from typing import Callable, Dict, List

class EventEmitter:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
    
    def on(self, event: str, callback: Callable):
        self._listeners.setdefault(event, []).append(callback)
    
    def off(self, event: str, callback: Callable):
        if event in self._listeners:
            self._listeners[event].remove(callback)
    
    def emit(self, event: str, *args, **kwargs):
        for callback in self._listeners.get(event, []):
            callback(*args, **kwargs)

class Document:
    def __init__(self):
        self.events = EventEmitter()
        self.content = ""
    
    def save(self):
        self._write_to_file()
        self.events.emit("save", content=self.content)
    
    def open(self, filename):
        self.content = self._read_file(filename)
        self.events.emit("open", filename=filename)

# Usage
doc = Document()
doc.events.on("save", lambda content: print(f"Saved: {len(content)} chars"))
doc.events.on("save", lambda content: send_notification("Document saved"))
doc.events.on("open", lambda filename: print(f"Opened: {filename}"))

doc.open("report.txt")
doc.save()
```

---

## Strategy

### Intent
Define a family of algorithms, encapsulate each one, and make them interchangeable. Strategy lets the algorithm vary independently from clients that use it.

### When to Use
- Multiple ways to perform a task (sorting, compression, payment)
- You want to select an algorithm at runtime
- You want to eliminate conditional statements for algorithm selection

### Java Implementation
```java
// Strategy interface
public interface SortStrategy<T extends Comparable<T>> {
    void sort(List<T> list);
    String getName();
}

// Concrete strategies
public class BubbleSort<T extends Comparable<T>> implements SortStrategy<T> {
    @Override
    public void sort(List<T> list) {
        int n = list.size();
        for (int i = 0; i < n - 1; i++) {
            for (int j = 0; j < n - i - 1; j++) {
                if (list.get(j).compareTo(list.get(j + 1)) > 0) {
                    Collections.swap(list, j, j + 1);
                }
            }
        }
    }
    
    @Override
    public String getName() { return "BubbleSort"; }
}

public class QuickSort<T extends Comparable<T>> implements SortStrategy<T> {
    @Override
    public void sort(List<T> list) {
        // QuickSort implementation
    }
    
    @Override
    public String getName() { return "QuickSort"; }
}

// Context
public class Sorter<T extends Comparable<T>> {
    private SortStrategy<T> strategy;
    
    public Sorter(SortStrategy<T> strategy) {
        this.strategy = strategy;
    }
    
    public void setStrategy(SortStrategy<T> strategy) {
        this.strategy = strategy;
    }
    
    public void sort(List<T> list) {
        System.out.println("Sorting with: " + strategy.getName());
        strategy.sort(list);
    }
}

// Usage
Sorter<Integer> sorter = new Sorter<>(new BubbleSort<>());
sorter.sort(smallList);

sorter.setStrategy(new QuickSort<>());
sorter.sort(largeList);
```

### Python Implementation
```python
from abc import ABC, abstractmethod

class CompressionStrategy(ABC):
    @abstractmethod
    def compress(self, data: bytes) -> bytes: pass
    
    @abstractmethod
    def decompress(self, data: bytes) -> bytes: pass

class NoCompression(CompressionStrategy):
    def compress(self, data): return data
    def decompress(self, data): return data

class GzipCompression(CompressionStrategy):
    def compress(self, data):
        import gzip
        return gzip.compress(data)
    
    def decompress(self, data):
        import gzip
        return gzip.decompress(data)

class LZ4Compression(CompressionStrategy):
    def compress(self, data):
        import lz4.frame
        return lz4.frame.compress(data)
    
    def decompress(self, data):
        import lz4.frame
        return lz4.frame.decompress(data)

class FileCompressor:
    def __init__(self, strategy: CompressionStrategy):
        self._strategy = strategy
    
    def compress_file(self, filename: str):
        with open(filename, 'rb') as f:
            data = f.read()
        compressed = self._strategy.compress(data)
        with open(filename + '.compressed', 'wb') as f:
            f.write(compressed)

# Usage
compressor = FileCompressor(GzipCompression())
compressor.compress_file("data.txt")

# Switch strategy at runtime
compressor._strategy = LZ4Compression()
compressor.compress_file("data.txt")
```

---

## Command

### Intent
Encapsulate a request as an object, thereby letting you parameterize clients with different requests, queue or log requests, and support undoable operations.

### When to Use
- Undo/redo functionality
- Task queues and job scheduling
- Macro recording (record and replay sequences of operations)
- Transactional behavior

### Python Implementation
```python
from abc import ABC, abstractmethod
from typing import List

class Command(ABC):
    @abstractmethod
    def execute(self): pass
    
    @abstractmethod
    def undo(self): pass

class TextEditor:
    def __init__(self):
        self.content = ""
    
    def insert(self, text, position):
        self.content = self.content[:position] + text + self.content[position:]
    
    def delete(self, position, length):
        deleted = self.content[position:position + length]
        self.content = self.content[:position] + self.content[position + length:]
        return deleted

class InsertCommand(Command):
    def __init__(self, editor: TextEditor, text: str, position: int):
        self.editor = editor
        self.text = text
        self.position = position
    
    def execute(self):
        self.editor.insert(self.text, self.position)
    
    def undo(self):
        self.editor.delete(self.position, len(self.text))

class DeleteCommand(Command):
    def __init__(self, editor: TextEditor, position: int, length: int):
        self.editor = editor
        self.position = position
        self.length = length
        self.deleted_text = ""
    
    def execute(self):
        self.deleted_text = self.editor.delete(self.position, self.length)
    
    def undo(self):
        self.editor.insert(self.deleted_text, self.position)

class CommandHistory:
    def __init__(self):
        self._history: List[Command] = []
        self._redo_stack: List[Command] = []
    
    def execute(self, command: Command):
        command.execute()
        self._history.append(command)
        self._redo_stack.clear()
    
    def undo(self):
        if self._history:
            command = self._history.pop()
            command.undo()
            self._redo_stack.append(command)
    
    def redo(self):
        if self._redo_stack:
            command = self._redo_stack.pop()
            command.execute()
            self._history.append(command)

# Usage
editor = TextEditor()
history = CommandHistory()

history.execute(InsertCommand(editor, "Hello", 0))
print(editor.content)  # "Hello"

history.execute(InsertCommand(editor, " World", 5))
print(editor.content)  # "Hello World"

history.execute(DeleteCommand(editor, 5, 6))
print(editor.content)  # "Hello"

history.undo()
print(editor.content)  # "Hello World"

history.undo()
print(editor.content)  # "Hello"
```

---

## Iterator

### Intent
Provide a way to access the elements of an aggregate object sequentially without exposing its underlying representation.

### When to Use
- Custom collections with complex internal structures
- Traversing different data structures with a uniform interface
- Lazy evaluation of sequences
- Multiple simultaneous traversals of the same collection

### Python Implementation
```python
from typing import Any, Iterator, List

class TreeNode:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

class BinaryTree:
    def __init__(self, root: TreeNode = None):
        self.root = root
    
    def __iter__(self) -> Iterator:
        return InOrderIterator(self.root)
    
    def bfs(self) -> Iterator:
        return BFSIterator(self.root)
    
    def dfs(self) -> Iterator:
        return DFSIterator(self.root)

class InOrderIterator:
    def __init__(self, root):
        self.stack = []
        self._push_left(root)
    
    def _push_left(self, node):
        while node:
            self.stack.append(node)
            node = node.left
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if not self.stack:
            raise StopIteration
        node = self.stack.pop()
        self._push_left(node.right)
        return node.value

class BFSIterator:
    def __init__(self, root):
        from collections import deque
        self.queue = deque()
        if root:
            self.queue.append(root)
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if not self.queue:
            raise StopIteration
        node = self.queue.popleft()
        if node.left:
            self.queue.append(node.left)
        if node.right:
            self.queue.append(node.right)
        return node.value

# Usage
tree = BinaryTree(
    TreeNode(4,
        TreeNode(2, TreeNode(1), TreeNode(3)),
        TreeNode(6, TreeNode(5), TreeNode(7))
    )
)

# In-order: 1, 2, 3, 4, 5, 6, 7
for val in tree:
    print(val, end=" ")

# BFS: 4, 2, 6, 1, 3, 5, 7
for val in tree.bfs():
    print(val, end=" ")
```

### Java Implementation
```java
public interface Iterator<T> {
    boolean hasNext();
    T next();
}

public interface Iterable<T> {
    Iterator<T> iterator();
}

public class BinaryTree<T> implements Iterable<T> {
    private TreeNode<T> root;
    
    @Override
    public Iterator<T> iterator() {
        return new InOrderIterator<>(root);
    }
    
    private static class InOrderIterator<T> implements Iterator<T> {
        private Stack<TreeNode<T>> stack = new Stack<>();
        
        public InOrderIterator(TreeNode<T> root) {
            pushLeft(root);
        }
        
        private void pushLeft(TreeNode<T> node) {
            while (node != null) {
                stack.push(node);
                node = node.left;
            }
        }
        
        @Override
        public boolean hasNext() {
            return !stack.isEmpty();
        }
        
        @Override
        public T next() {
            if (!hasNext()) throw new NoSuchElementException();
            TreeNode<T> node = stack.pop();
            pushLeft(node.right);
            return node.value;
        }
    }
}
```

---

## Summary

| Pattern | Type | Key Idea | Common Use |
|---------|------|----------|------------|
| **Adapter** | Structural | Convert incompatible interfaces | Third-party integration |
| **Decorator** | Structural | Add behavior dynamically | I/O streams, middleware |
| **Facade** | Structural | Simplify complex subsystems | API wrappers, service layers |
| **Proxy** | Structural | Control access to objects | Lazy loading, caching, auth |
| **Observer** | Behavioral | One-to-many notification | Event systems, UI updates |
| **Strategy** | Behavioral | Interchangeable algorithms | Sorting, compression, payment |
| **Command** | Behavioral | Encapsulate requests as objects | Undo/redo, task queues |
| **Iterator** | Behavioral | Sequential access to collections | Custom data structures |
