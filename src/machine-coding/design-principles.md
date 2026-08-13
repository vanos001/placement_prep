# Design Principles for Machine Coding

## SOLID Principles in Practice

### S — Single Responsibility Principle (SRP)

**"A class should have one, and only one, reason to change."**

#### Bad Example:
```java
// This class does TOO MUCH
public class Employee {
    private String name;
    private double salary;
    
    public void calculatePay() { /* pay logic */ }
    public void saveToDatabase() { /* DB logic */ }
    public String generateReport() { /* report logic */ }
    public void sendEmail() { /* email logic */ }
}
```

#### Good Example:
```java
public class Employee {
    private String name;
    private double salary;
    // getters, setters — data only
}

public class PayCalculator {
    public double calculatePay(Employee emp) { ... }
}

public class EmployeeRepository {
    public void save(Employee emp) { ... }
}

public class ReportGenerator {
    public String generate(Employee emp) { ... }
}

public class EmailService {
    public void sendNotification(Employee emp) { ... }
}
```

#### In Machine Coding:
```
ParkingLot → manages parking operations
PricingStrategy → calculates fees
ParkingSpotRepository → stores/retrieves spots
NotificationService → sends alerts
```

### O — Open/Closed Principle (OCP)

**"Classes should be open for extension, closed for modification."**

#### Bad Example:
```java
public class PricingCalculator {
    public double calculate(Ticket ticket) {
        if (ticket.getVehicleType() == VehicleType.CAR) {
            return ticket.getHours() * 20;
        } else if (ticket.getVehicleType() == VehicleType.BIKE) {
            return ticket.getHours() * 10;
        } else if (ticket.getVehicleType() == VehicleType.TRUCK) {
            return ticket.getHours() * 40;
        }
        // Adding a new type requires modifying this class!
        return 0;
    }
}
```

#### Good Example:
```java
// Interface
public interface PricingStrategy {
    double calculate(Ticket ticket);
}

// Implementations — add new ones without modifying existing
public class CarPricingStrategy implements PricingStrategy {
    @Override
    public double calculate(Ticket ticket) {
        return ticket.getHours() * 20;
    }
}

public class BikePricingStrategy implements PricingStrategy {
    @Override
    public double calculate(Ticket ticket) {
        return ticket.getHours() * 10;
    }
}

// Registry — extensible
public class PricingStrategyFactory {
    private Map<VehicleType, PricingStrategy> strategies = new HashMap<>();
    
    public void register(VehicleType type, PricingStrategy strategy) {
        strategies.put(type, strategy);
    }
    
    public PricingStrategy getStrategy(VehicleType type) {
        return strategies.get(type);
    }
}
```

### L — Liskov Substitution Principle (LSP)

**"Subtypes must be substitutable for their base types."**

#### Bad Example:
```java
public class Bird {
    public void fly() { System.out.println("Flying"); }
}

public class Penguin extends Bird {
    @Override
    public void fly() {
        throw new UnsupportedOperationException("Penguins can't fly!");
    }
}
```

#### Good Example:
```java
public abstract class Bird {
    public abstract void move();
}

public class Sparrow extends Bird {
    @Override
    public void move() { System.out.println("Flying"); }
}

public class Penguin extends Bird {
    @Override
    public void move() { System.out.println("Swimming"); }
}
```

#### In Machine Coding:
```java
// All spot types can be occupied/freed
public abstract class ParkingSpot {
    protected boolean occupied;
    protected Vehicle vehicle;
    
    public abstract boolean canFit(Vehicle vehicle);
    
    public void occupy(Vehicle v) {
        if (!canFit(v)) throw new IllegalArgumentException("Vehicle too large");
        this.vehicle = v;
        this.occupied = true;
    }
    
    public void free() {
        this.vehicle = null;
        this.occupied = false;
    }
}

// Subtypes — all maintain the contract
public class CompactSpot extends ParkingSpot {
    @Override
    public boolean canFit(Vehicle vehicle) {
        return vehicle.getType() == VehicleType.MOTORCYCLE 
            || vehicle.getType() == VehicleType.CAR;
    }
}

public class LargeSpot extends ParkingSpot {
    @Override
    public boolean canFit(Vehicle vehicle) {
        return true; // Fits everything
    }
}
```

### I — Interface Segregation Principle (ISP)

**"No client should be forced to depend on methods it doesn't use."**

#### Bad Example:
```java
public interface ParkingSystem {
    void parkVehicle(Vehicle v);
    void removeVehicle(String ticketId);
    void processPayment(String ticketId);
    void generateReport();
    void sendNotification(String userId);
    void updateInventory();
}
```

#### Good Example:
```java
public interface ParkingOperations {
    Ticket parkVehicle(Vehicle v);
    void removeVehicle(String ticketId);
}

public interface PaymentProcessor {
    void processPayment(String ticketId, double amount);
}

public interface ReportGenerator {
    Report generateReport(DateRange range);
}

public interface NotificationSender {
    void sendNotification(String userId, String message);
}
```

### D — Dependency Inversion Principle (DIP)

**"Depend on abstractions, not concretions."**

#### Bad Example:
```java
public class ParkingLot {
    private MySQLDatabase database; // Concrete dependency!
    private EmailService emailService; // Concrete dependency!
    
    public Ticket park(Vehicle vehicle) {
        // ...
        database.save(ticket);
        emailService.send(ticket);
    }
}
```

#### Good Example:
```java
public class ParkingLot {
    private final ParkingRepository repository; // Abstraction!
    private final NotificationService notifier; // Abstraction!
    
    public ParkingLot(ParkingRepository repository, NotificationService notifier) {
        this.repository = repository;
        this.notifier = notifier;
    }
    
    public Ticket park(Vehicle vehicle) {
        // ...
        repository.save(ticket);
        notifier.notify(ticket);
    }
}

// Can swap implementations
ParkingLot lot = new ParkingLot(
    new InMemoryParkingRepository(),  // or MySQLParkingRepository
    new ConsoleNotificationService()  // or EmailNotificationService
);
```

---

## Design Patterns for Machine Coding

### 1. Strategy Pattern

**When:** You have multiple algorithms for the same task.

**Example:** Different pricing strategies for parking.

```java
// Strategy Interface
public interface PricingStrategy {
    double calculate(Ticket ticket);
}

// Concrete Strategies
public class HourlyPricing implements PricingStrategy {
    @Override
    public double calculate(Ticket ticket) {
        long hours = ChronoUnit.HOURS.between(
            ticket.getEntryTime(), LocalDateTime.now());
        return hours * 20.0;
    }
}

public class FlatRatePricing implements PricingStrategy {
    private final double flatRate;
    
    public FlatRatePricing(double flatRate) {
        this.flatRate = flatRate;
    }
    
    @Override
    public double calculate(Ticket ticket) {
        return flatRate;
    }
}

public class ProgressivePricing implements PricingStrategy {
    @Override
    public double calculate(Ticket ticket) {
        long hours = ChronoUnit.HOURS.between(
            ticket.getEntryTime(), LocalDateTime.now());
        if (hours <= 2) return hours * 10;
        if (hours <= 8) return 20 + (hours - 2) * 15;
        return 110 + (hours - 8) * 10;
    }
}

// Context
public class ParkingLot {
    private PricingStrategy pricingStrategy;
    
    public void setPricingStrategy(PricingStrategy strategy) {
        this.pricingStrategy = strategy;
    }
    
    public double calculateFee(Ticket ticket) {
        return pricingStrategy.calculate(ticket);
    }
}

// Usage
ParkingLot lot = new ParkingLot();
lot.setPricingStrategy(new ProgressivePricing());
double fee = lot.calculateFee(ticket);
```

### 2. Observer Pattern

**When:** One object's state change should notify multiple dependents.

**Example:** Notify when a parking spot becomes available.

```java
// Observer Interface
public interface ParkingObserver {
    void onSpotAvailable(ParkingSpot spot);
    void onLotFull();
}

// Subject
public class ParkingLot {
    private List<ParkingObserver> observers = new ArrayList<>();
    
    public void addObserver(ParkingObserver observer) {
        observers.add(observer);
    }
    
    public void removeObserver(ParkingObserver observer) {
        observers.remove(observer);
    }
    
    private void notifySpotAvailable(ParkingSpot spot) {
        for (ParkingObserver obs : observers) {
            obs.onSpotAvailable(spot);
        }
    }
    
    private void notifyLotFull() {
        for (ParkingObserver obs : observers) {
            obs.onLotFull();
        }
    }
    
    public void remove(Ticket ticket) {
        // ... remove vehicle
        notifySpotAvailable(freedSpot);
    }
}

// Concrete Observers
public class DisplayBoard implements ParkingObserver {
    @Override
    public void onSpotAvailable(ParkingSpot spot) {
        System.out.println("Spot " + spot.getId() + " is now available");
    }
    
    @Override
    public void onLotFull() {
        System.out.println("PARKING FULL — Please wait");
    }
}

public class MobileAppNotifier implements ParkingObserver {
    @Override
    public void onSpotAvailable(ParkingSpot spot) {
        // Send push notification to users waiting
        sendPushNotification("Spot available on floor " + spot.getFloor());
    }
    
    @Override
    public void onLotFull() {
        sendPushNotification("Parking lot is full");
    }
}
```

### 3. Factory Pattern

**When:** Object creation logic is complex or varies by type.

```java
// Simple Factory
public class VehicleFactory {
    public static Vehicle create(String licensePlate, VehicleType type) {
        switch (type) {
            case MOTORCYCLE:
                return new Motorcycle(licensePlate);
            case CAR:
                return new Car(licensePlate);
            case TRUCK:
                return new Truck(licensePlate);
            default:
                throw new IllegalArgumentException("Unknown type: " + type);
        }
    }
}

// Factory Method
public abstract class ParkingSpotFactory {
    public abstract ParkingSpot createSpot(String id);
    
    // Factory method in base class
    public static ParkingSpotFactory getFactory(SpotSize size) {
        switch (size) {
            case COMPACT: return new CompactSpotFactory();
            case LARGE:   return new LargeSpotFactory();
            case HANDICAPPED: return new HandicappedSpotFactory();
            default: throw new IllegalArgumentException();
        }
    }
}

public class CompactSpotFactory extends ParkingSpotFactory {
    @Override
    public ParkingSpot createSpot(String id) {
        return new CompactSpot(id, SpotSize.COMPACT);
    }
}
```

### 4. Builder Pattern

**When:** Object has many optional parameters or complex construction.

```java
public class ParkingLot {
    private final String name;
    private final int floors;
    private final int spotsPerFloor;
    private final PricingStrategy pricing;
    private final ParkingStrategy allocation;
    private final boolean hasEVCharging;
    private final int maxReservationHours;
    
    private ParkingLot(Builder builder) {
        this.name = builder.name;
        this.floors = builder.floors;
        this.spotsPerFloor = builder.spotsPerFloor;
        this.pricing = builder.pricing;
        this.allocation = builder.allocation;
        this.hasEVCharging = builder.hasEVCharging;
        this.maxReservationHours = builder.maxReservationHours;
    }
    
    public static class Builder {
        // Required
        private final String name;
        private final int floors;
        
        // Optional — defaults
        private int spotsPerFloor = 50;
        private PricingStrategy pricing = new HourlyPricing();
        private ParkingStrategy allocation = new NearestSpotStrategy();
        private boolean hasEVCharging = false;
        private int maxReservationHours = 24;
        
        public Builder(String name, int floors) {
            this.name = name;
            this.floors = floors;
        }
        
        public Builder spotsPerFloor(int val) {
            this.spotsPerFloor = val; return this;
        }
        
        public Builder pricing(PricingStrategy val) {
            this.pricing = val; return this;
        }
        
        public Builder allocation(ParkingStrategy val) {
            this.allocation = val; return this;
        }
        
        public Builder evCharging(boolean val) {
            this.hasEVCharging = val; return this;
        }
        
        public Builder maxReservationHours(int val) {
            this.maxReservationHours = val; return this;
        }
        
        public ParkingLot build() {
            return new ParkingLot(this);
        }
    }
}

// Usage — clean, readable
ParkingLot lot = new ParkingLot.Builder("Central Park", 3)
    .spotsPerFloor(100)
    .pricing(new ProgressivePricing())
    .allocation(new NearestSpotStrategy())
    .evCharging(true)
    .maxReservationHours(48)
    .build();
```

### 5. Singleton Pattern

**When:** Exactly one instance should exist (parking lot, configuration).

```java
// Thread-safe Singleton
public class ParkingLotManager {
    private static ParkingLotManager instance;
    private final Map<String, ParkingLot> lots;
    
    private ParkingLotManager() {
        this.lots = new HashMap<>();
    }
    
    public static synchronized ParkingLotManager getInstance() {
        if (instance == null) {
            instance = new ParkingLotManager();
        }
        return instance;
    }
    
    public void registerLot(ParkingLot lot) {
        lots.put(lot.getName(), lot);
    }
    
    public ParkingLot getLot(String name) {
        return lots.get(name);
    }
}

// Or use Enum Singleton (preferred in Java)
public enum ParkingLotManager {
    INSTANCE;
    
    private final Map<String, ParkingLot> lots = new HashMap<>();
    
    public void registerLot(ParkingLot lot) {
        lots.put(lot.getName(), lot);
    }
    
    public ParkingLot getLot(String name) {
        return lots.get(name);
    }
}
```

### 6. State Pattern

**When:** Object behavior changes based on its state.

```java
// State Interface
public interface SpotState {
    void park(ParkingSpot spot, Vehicle vehicle);
    void free(ParkingSpot spot);
    void reserve(ParkingSpot spot, String userId);
    boolean isAvailable();
}

// Concrete States
public class AvailableState implements SpotState {
    @Override
    public void park(ParkingSpot spot, Vehicle vehicle) {
        spot.setVehicle(vehicle);
        spot.setState(new OccupiedState());
    }
    
    @Override
    public void free(ParkingSpot spot) {
        throw new IllegalStateException("Spot is already free");
    }
    
    @Override
    public void reserve(ParkingSpot spot, String userId) {
        spot.setReservedBy(userId);
        spot.setState(new ReservedState());
    }
    
    @Override
    public boolean isAvailable() { return true; }
}

public class OccupiedState implements SpotState {
    @Override
    public void park(ParkingSpot spot, Vehicle vehicle) {
        throw new IllegalStateException("Spot is already occupied");
    }
    
    @Override
    public void free(ParkingSpot spot) {
        spot.setVehicle(null);
        spot.setState(new AvailableState());
    }
    
    @Override
    public void reserve(ParkingSpot spot, String userId) {
        throw new IllegalStateException("Can't reserve occupied spot");
    }
    
    @Override
    public boolean isAvailable() { return false; }
}

public class ReservedState implements SpotState {
    @Override
    public void park(ParkingSpot spot, Vehicle vehicle) {
        spot.setVehicle(vehicle);
        spot.setState(new OccupiedState());
    }
    
    @Override
    public void free(ParkingSpot spot) {
        spot.setReservedBy(null);
        spot.setState(new AvailableState());
    }
    
    @Override
    public void reserve(ParkingSpot spot, String userId) {
        throw new IllegalStateException("Spot already reserved");
    }
    
    @Override
    public boolean isAvailable() { return false; }
}

// Context
public class ParkingSpot {
    private SpotState state = new AvailableState();
    
    public void park(Vehicle vehicle) {
        state.park(this, vehicle);
    }
    
    public void free() {
        state.free(this);
    }
    
    public void setState(SpotState state) {
        this.state = state;
    }
}
```

## Pattern Selection Guide

```
Need multiple algorithms?           → Strategy
Need event notifications?           → Observer
Complex object creation?            → Factory / Builder
Single instance needed?             → Singleton
Object behavior changes by state?   → State
Want to traverse a collection?      → Iterator
Need undo/redo?                     → Command
Want to add behavior dynamically?   → Decorator
Need to reduce coupling?            → Mediator
```

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| God Class | One class does everything | Split with SRP |
| Spaghetti Code | No structure | Use proper patterns |
| Copy-Paste | Duplicated logic | Extract methods/classes |
| Magic Numbers | Hardcoded values | Use constants/enums |
| Premature Optimization | Over-engineering | Start simple, optimize later |
