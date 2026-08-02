# Design Patterns

## What are Design Patterns?

Design patterns are reusable solutions to common software design problems. They provide a shared vocabulary and proven approaches to recurring design challenges.

## Creational Patterns

### 1. Singleton

**Problem**: Need exactly one instance of a class (e.g., database connection, config manager).

```python
class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.connection = "Connected to DB"

# Usage
db1 = DatabaseConnection()
db2 = DatabaseConnection()
print(db1 is db2)  # True
```

**Thread-safe version**:
```python
import threading

class DatabaseConnection:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
```

**When to use**: Configuration, connection pools, logging
**When NOT to use**: When you need multiple instances, makes testing hard

### 2. Factory Method

**Problem**: Create objects without specifying exact class.

```python
from abc import ABC, abstractmethod

class Notification(ABC):
    @abstractmethod
    def send(self, message: str):
        pass

class EmailNotification(Notification):
    def send(self, message: str):
        print(f"Email: {message}")

class SMSNotification(Notification):
    def send(self, message: str):
        print(f"SMS: {message}")

class PushNotification(Notification):
    def send(self, message: str):
        print(f"Push: {message}")

class NotificationFactory:
    @staticmethod
    def create(notification_type: str) -> Notification:
        if notification_type == "email":
            return EmailNotification()
        elif notification_type == "sms":
            return SMSNotification()
        elif notification_type == "push":
            return PushNotification()
        else:
            raise ValueError(f"Unknown type: {notification_type}")

# Usage
notification = NotificationFactory.create("email")
notification.send("Hello!")
```

**When to use**: Object creation logic is complex, need to decouple creation from usage
**Real-world**: Java `Calendar.getInstance()`, Python `datetime.strptime()`

### 3. Builder

**Problem**: Construct complex objects step by step.

```python
class House:
    def __init__(self):
        self.walls = None
        self.roof = None
        self garage = None
        self.pool = None
    
    def __str__(self):
        parts = []
        if self.walls: parts.append(f"{self.walls} walls")
        if self.roof: parts.append(f"{self.roof} roof")
        if self.garage: parts.append("garage")
        if self.pool: parts.append("pool")
        return f"House with {', '.join(parts)}"

class HouseBuilder:
    def __init__(self):
        self.house = House()
    
    def set_walls(self, material: str) -> 'HouseBuilder':
        self.house.walls = material
        return self
    
    def set_roof(self, material: str) -> 'HouseBuilder':
        self.house.roof = material
        return self
    
    def add_garage(self) -> 'HouseBuilder':
        self.house.garage = True
        return self
    
    def add_pool(self) -> 'HouseBuilder':
        self.house.pool = True
        return self
    
    def build(self) -> House:
        return self.house

# Usage (fluent interface)
house = (HouseBuilder()
    .set_walls("brick")
    .set_roof("tile")
    .add_garage()
    .add_pool()
    .build())
print(house)  # House with brick walls, tile roof, garage, pool
```

**When to use**: Many optional parameters, complex construction, immutable objects
**Real-world**: `StringBuilder`, `SQLQueryBuilder`, `HttpClient.Builder`

## Structural Patterns

### 4. Adapter

**Problem**: Make incompatible interfaces work together.

```python
# Old payment system
class OldPaymentSystem:
    def make_payment(self, amount: float):
        print(f"Old system: paying ${amount}")

# New interface expected by our app
class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: float, currency: str):
        pass

# Adapter: wraps old system to match new interface
class OldPaymentAdapter(PaymentProcessor):
    def __init__(self, old_system: OldPaymentSystem):
        self.old_system = old_system
    
    def process_payment(self, amount: float, currency: str):
        # Convert currency if needed, then delegate
        converted = self._convert_to_usd(amount, currency)
        self.old_system.make_payment(converted)
    
    def _convert_to_usd(self, amount: float, currency: str) -> float:
        rates = {"EUR": 1.1, "GBP": 1.3}
        return amount * rates.get(currency, 1.0)

# Usage
processor = OldPaymentAdapter(OldPaymentSystem())
processor.process_payment(100, "EUR")  # Works with new interface
```

**When to use**: Integrating legacy code, third-party libraries with different interfaces

### 5. Decorator

**Problem**: Add behavior to objects dynamically without modifying their class.

```python
from abc import ABC, abstractmethod

class Coffee(ABC):
    @abstractmethod
    def cost(self) -> float:
        pass
    
    @abstractmethod
    def description(self) -> str:
        pass

class SimpleCoffee(Coffee):
    def cost(self) -> float:
        return 2.0
    
    def description(self) -> str:
        return "Simple coffee"

class CoffeeDecorator(Coffee, ABC):
    def __init__(self, coffee: Coffee):
        self._coffee = coffee

class MilkDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 0.5
    
    def description(self) -> str:
        return self._coffee.description() + ", milk"

class SugarDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 0.25
    
    def description(self) -> str:
        return self._coffee.description() + ", sugar"

class WhipDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 0.75
    
    def description(self) -> str:
        return self._coffee.description() + ", whip"

# Usage - stack decorators
coffee = SimpleCoffee()
coffee = MilkDecorator(coffee)
coffee = SugarDecorator(coffee)
coffee = WhipDecorator(coffee)
print(f"{coffee.description()}: ${coffee.cost()}")
# Simple coffee, milk, sugar, whip: $3.5
```

**When to use**: Add responsibilities dynamically, avoid subclass explosion
**Real-world**: Java I/O streams (`BufferedInputStream(FileInputStream(...))`)

### 6. Proxy

**Problem**: Control access to an object.

```python
class Image(ABC):
    @abstractmethod
    def display(self):
        pass

class RealImage(Image):
    def __init__(self, filename: str):
        self.filename = filename
        self._load_from_disk()
    
    def _load_from_disk(self):
        print(f"Loading {self.filename} from disk...")
    
    def display(self):
        print(f"Displaying {self.filename}")

class ProxyImage(Image):
    def __init__(self, filename: str):
        self.filename = filename
        self._real_image = None
    
    def display(self):
        if self._real_image is None:
            self._real_image = RealImage(self.filename)  # Lazy loading
        self._real_image.display()

# Usage
image = ProxyImage("photo.jpg")  # Not loaded yet
image.display()  # Loads from disk, then displays
image.display()  # Already loaded, just displays
```

**When to use**: Lazy loading, access control, caching, logging
**Types**: Virtual proxy, protection proxy, caching proxy

### 7. Facade

**Problem**: Provide a simplified interface to a complex subsystem.

```python
class CPU:
    def freeze(self): print("CPU: Freezing")
    def execute(self): print("CPU: Executing")
    def unfreeze(self): print("CPU: Unfreezing")

class Memory:
    def load(self, address: int, data: str): print(f"Memory: Loading {data} at {address}")

class HardDrive:
    def read(self, sector: int) -> str: return f"Data from sector {sector}"

class ComputerFacade:
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()
        self.hard_drive = HardDrive()
    
    def start(self):
        print("Computer starting...")
        self.cpu.freeze()
        data = self.hard_drive.read(0)
        self.memory.load(0, data)
        self.cpu.execute()
        self.cpu.unfreeze()
        print("Computer started!")

# Usage - simple interface hides complexity
computer = ComputerFacade()
computer.start()
```

**When to use**: Simplify complex subsystems, reduce dependencies

## Behavioral Patterns

### 8. Observer

**Problem**: Notify multiple objects when state changes.

```python
from abc import ABC, abstractmethod
from typing import List

class Observer(ABC):
    @abstractmethod
    def update(self, event: str, data: dict):
        pass

class EventEmitter:
    def __init__(self):
        self._observers: dict[str, List[Observer]] = {}
    
    def subscribe(self, event: str, observer: Observer):
        if event not in self._observers:
            self._observers[event] = []
        self._observers[event].append(observer)
    
    def unsubscribe(self, event: str, observer: Observer):
        self._observers[event].remove(observer)
    
    def emit(self, event: str, data: dict = None):
        for observer in self._observers.get(event, []):
            observer.update(event, data or {})

class OrderService(EventEmitter):
    def create_order(self, order_id: str, user_id: str):
        # Create order logic...
        self.emit("order_created", {"order_id": order_id, "user_id": user_id})

# Observers
class EmailNotifier(Observer):
    def update(self, event: str, data: dict):
        print(f"Email: Order {data['order_id']} created for user {data['user_id']}")

class InventoryService(Observer):
    def update(self, event: str, data: dict):
        print(f"Inventory: Reserving items for order {data['order_id']}")

class AnalyticsService(Observer):
    def update(self, event: str, data: dict):
        print(f"Analytics: Tracking order {data['order_id']}")

# Usage
order_service = OrderService()
order_service.subscribe("order_created", EmailNotifier())
order_service.subscribe("order_created", InventoryService())
order_service.subscribe("order_created", AnalyticsService())

order_service.create_order("ORD-123", "USER-456")
```

**When to use**: Event systems, UI updates, microservice communication

### 9. Strategy

**Problem**: Algorithm varies at runtime.

```python
from abc import ABC, abstractmethod

class SortingStrategy(ABC):
    @abstractmethod
    def sort(self, data: list) -> list:
        pass

class BubbleSort(SortingStrategy):
    def sort(self, data: list) -> list:
        arr = data.copy()
        n = len(arr)
        for i in range(n):
            for j in range(0, n-i-1):
                if arr[j] > arr[j+1]:
                    arr[j], arr[j+1] = arr[j+1], arr[j]
        return arr

class QuickSort(SortingStrategy):
    def sort(self, data: list) -> list:
        if len(data) <= 1:
            return data
        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]
        return self.sort(left) + middle + self.sort(right)

class MergeSort(SortingStrategy):
    def sort(self, data: list) -> list:
        if len(data) <= 1:
            return data
        mid = len(data) // 2
        left = self.sort(data[:mid])
        right = self.sort(data[mid:])
        return self._merge(left, right)
    
    def _merge(self, left, right):
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result

class Sorter:
    def __init__(self, strategy: SortingStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: SortingStrategy):
        self._strategy = strategy
    
    def sort(self, data: list) -> list:
        return self._strategy.sort(data)

# Usage
sorter = Sorter(BubbleSort())
print(sorter.sort([3, 1, 4, 1, 5]))

sorter.set_strategy(QuickSort())
print(sorter.sort([3, 1, 4, 1, 5]))
```

**When to use**: Multiple algorithms, runtime selection, A/B testing

### 10. Command

**Problem**: Encapsulate a request as an object.

```python
from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self):
        pass
    
    @abstractmethod
    def undo(self):
        pass

class TextEditor:
    def __init__(self):
        self.content = ""
    
    def insert(self, text: str, position: int):
        self.content = self.content[:position] + text + self.content[position:]
    
    def delete(self, position: int, length: int):
        self.content = self.content[:position] + self.content[position+length:]

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
        self.deleted_text = self.editor.content[self.position:self.position+self.length]
        self.editor.delete(self.position, self.length)
    
    def undo(self):
        self.editor.insert(self.deleted_text, self.position)

class CommandHistory:
    def __init__(self):
        self._history: list[Command] = []
    
    def execute(self, command: Command):
        command.execute()
        self._history.append(command)
    
    def undo(self):
        if self._history:
            command = self._history.pop()
            command.undo()

# Usage
editor = TextEditor()
history = CommandHistory()

history.execute(InsertCommand(editor, "Hello", 0))
print(editor.content)  # "Hello"

history.execute(InsertCommand(editor, " World", 5))
print(editor.content)  # "Hello World"

history.undo()
print(editor.content)  # "Hello"
```

**When to use**: Undo/redo, queuing operations, logging

### 11. State

**Problem**: Object behavior changes based on internal state.

```python
from abc import ABC, abstractmethod

class VendingMachineState(ABC):
    @abstractmethod
    def insert_money(self, machine: 'VendingMachine', amount: float):
        pass
    
    @abstractmethod
    def select_item(self, machine: 'VendingMachine', item: str):
        pass
    
    @abstractmethod
    def dispense(self, machine: 'VendingMachine'):
        pass

class IdleState(VendingMachineState):
    def insert_money(self, machine: 'VendingMachine', amount: float):
        machine.balance += amount
        machine.set_state(HasMoneyState())
        print(f"Inserted ${amount}. Balance: ${machine.balance}")
    
    def select_item(self, machine: 'VendingMachine', item: str):
        print("Insert money first!")
    
    def dispense(self, machine: 'VendingMachine'):
        print("Insert money and select item first!")

class HasMoneyState(VendingMachineState):
    def insert_money(self, machine: 'VendingMachine', amount: float):
        machine.balance += amount
        print(f"Inserted ${amount}. Balance: ${machine.balance}")
    
    def select_item(self, machine: 'VendingMachine', item: str):
        if item in machine.items and machine.items[item] > 0:
            if machine.balance >= machine.prices[item]:
                machine.selected_item = item
                machine.set_state(DispensingState())
                machine.dispense()
            else:
                print(f"Insufficient funds. Need ${machine.prices[item]}")
        else:
            print(f"Item {item} not available")
    
    def dispense(self, machine: 'VendingMachine'):
        print("Select an item first!")

class DispensingState(VendingMachineState):
    def insert_money(self, machine: 'VendingMachine', amount: float):
        print("Please wait, dispensing...")
    
    def select_item(self, machine: 'VendingMachine', item: str):
        print("Please wait, dispensing...")
    
    def dispense(self, machine: 'VendingMachine'):
        item = machine.selected_item
        machine.items[item] -= 1
        change = machine.balance - machine.prices[item]
        print(f"Dispensing {item}. Change: ${change}")
        machine.balance = 0
        machine.selected_item = None
        machine.set_state(IdleState())

class VendingMachine:
    def __init__(self):
        self.items = {"coke": 5, "pepsi": 3, "water": 10}
        self.prices = {"coke": 1.5, "pepsi": 1.5, "water": 1.0}
        self.balance = 0.0
        self.selected_item = None
        self._state = IdleState()
    
    def set_state(self, state: VendingMachineState):
        self._state = state
    
    def insert_money(self, amount: float):
        self._state.insert_money(self, amount)
    
    def select_item(self, item: str):
        self._state.select_item(self, item)
    
    def dispense(self):
        self._state.dispense(self)

# Usage
vm = VendingMachine()
vm.insert_money(2.0)
vm.select_item("coke")  # Dispensing coke. Change: $0.5
```

**When to use**: State machines, objects with distinct behaviors per state

## Pattern Selection Guide

| Problem | Pattern | Key Benefit |
|---------|---------|------------|
| Need one instance | Singleton | Controlled access |
| Create objects by type | Factory | Decoupled creation |
| Complex object setup | Builder | Step-by-step construction |
| Incompatible interfaces | Adapter | Interface compatibility |
| Add behavior dynamically | Decorator | Flexible extension |
| Control object access | Proxy | Lazy loading, caching |
| Simplify complex system | Facade | Simple interface |
| Notify on changes | Observer | Loose coupling |
| Algorithm varies | Strategy | Runtime flexibility |
| Encapsulate request | Command | Undo/redo support |
| State-dependent behavior | State | Clean state transitions |

## Interview Tips

1. **Name the pattern** — "I'll use the Observer pattern here"
2. **Explain why** — "Because we need to notify multiple services"
3. **Show the structure** — Draw class diagrams
4. **Implement key parts** — Write the core classes
5. **Discuss trade-offs** — "Pattern X is simpler but less flexible than Y"
6. **Don't over-pattern** — Use patterns where they naturally fit

## Cross-References

- [SOLID Principles](./solid.md) — Patterns embody SOLID
- [OOP Concepts](./oop-concepts.md) — Foundation for patterns
- [UML Class Diagrams](./uml-class-diagrams.md) — Visualize patterns
- [LLD Problems](./parking-lot.md) — Patterns in practice
