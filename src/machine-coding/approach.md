# How to Approach Machine Coding Problems

## The Four-Phase Approach

### Phase 1: Requirements Analysis (5–10 minutes)

Before writing a single line of code, **understand what you're building**.

#### Read the Problem Statement Carefully
- Identify the core entities (nouns in the problem)
- Identify the core operations (verbs in the problem)
- Note constraints and assumptions

#### Ask Clarifying Questions
Good questions show maturity:
- "Should the system handle concurrent access?"
- "What happens when capacity is reached?"
- "Are there any performance requirements?"
- "Should I support undo/redo?"
- "What's the expected scale — 100 users or 1 million?"

#### Define Scope
List features as **Must Have**, **Should Have**, **Nice to Have**:

```
Must Have:    Core functionality that makes the system useful
Should Have:  Important features if time permits
Nice to Have: Enhancements to discuss at the end
```

#### Example — Parking Lot:
```
Must Have:
  - Park a vehicle (find nearest available spot)
  - Remove a vehicle (free the spot)
  - Display available spots

Should Have:
  - Different vehicle types (car, bike, truck)
  - Different spot sizes
  - Fee calculation

Nice to Have:
  - Multiple floors
  - EV charging spots
  - Reservation system
```

### Phase 2: Design (10–15 minutes)

#### Step 1: Identify Entities
Extract nouns from requirements:
```
Problem: "A parking lot has multiple floors. Each floor has spots 
of different sizes. Vehicles can park in appropriate spots."

Entities: ParkingLot, Floor, ParkingSpot, Vehicle, Ticket
```

#### Step 2: Define Relationships
```
ParkingLot  --has many-->  Floor
Floor       --has many-->  ParkingSpot
ParkingSpot --holds-->     Vehicle (0..1)
Ticket      --references-> ParkingSpot, Vehicle
```

#### Step 3: Draw Class Diagram (Text-Based)
```
┌─────────────┐       ┌──────────────┐
│ ParkingLot   │──────>│    Floor      │
├─────────────┤       ├──────────────┤
│ - floors     │       │ - spots      │
│ - name       │       │ - floorNum   │
├─────────────┤       ├──────────────┤
│ + park()     │       │ + findSpot() │
│ + remove()   │       │ + addSpot()  │
└─────────────┘       └──────────────┘
                              │
                              │ has many
                              ▼
┌─────────────┐       ┌──────────────┐
│   Vehicle    │<──────│ ParkingSpot   │
├─────────────┤       ├──────────────┤
│ - licenseNo  │       │ - spotId     │
│ - type       │       │ - size       │
└─────────────┘       │ - vehicle    │
                      ├──────────────┤
                      │ + park()     │
                      │ + remove()   │
                      └──────────────┘
```

#### Step 4: Choose Design Patterns
Think about which patterns fit:
- **Strategy** — different algorithms (pricing, allocation)
- **Observer** — event notifications (spot available)
- **Factory** — creating different vehicle/spot types
- **Singleton** — single parking lot instance
- **State** — spot states (available, occupied, reserved)

#### Step 5: Define Interfaces
```java
// Core interfaces before implementation
public interface ParkingStrategy {
    ParkingSpot findSpot(Floor floor, VehicleType type);
}

public interface PricingStrategy {
    double calculateFee(Ticket ticket);
}
```

### Phase 3: Implementation (30–40 minutes)

#### Golden Rules:
1. **Compile early, compile often** — don't write 200 lines then compile
2. **Core first** — implement the happy path before edge cases
3. **Incremental builds** — get one feature working, then add the next
4. **Use meaningful names** — `findNearestAvailableSpot()` beats `find()`

#### Implementation Order:
```
1. Define enums and constants
2. Create core entity classes (with constructors, getters)
3. Implement primary operations (park, remove, search)
4. Add supporting classes (Ticket, Strategy, etc.)
5. Create the main class / entry point
6. Wire everything together
7. Add error handling and validation
```

#### Code Structure:
```
src/
├── models/
│   ├── Vehicle.java
│   ├── ParkingSpot.java
│   ├── Floor.java
│   ├── ParkingLot.java
│   └── Ticket.java
├── enums/
│   ├── VehicleType.java
│   └── SpotSize.java
├── strategies/
│   ├── ParkingStrategy.java
│   └── PricingStrategy.java
└── Main.java
```

### Phase 4: Testing & Refinement (10–15 minutes)

#### Test the Happy Path:
```java
// Create parking lot
ParkingLot lot = new ParkingLot("Central Park", 3, 10);

// Park a vehicle
Vehicle car = new Vehicle("KA-01-HH-1234", VehicleType.CAR);
Ticket ticket = lot.park(car);
System.out.println("Parked at: " + ticket.getSpot().getId());

// Remove vehicle
lot.remove(ticket);
System.out.println("Vehicle removed");
```

#### Test Edge Cases:
- What if the lot is full?
- What if you try to remove a vehicle that's not parked?
- What if you park the same vehicle twice?
- What about null inputs?

#### Discuss Improvements:
- "I'd add a notification system using Observer pattern"
- "For production, I'd use a database instead of in-memory storage"
- "I'd add logging for debugging"
- "The pricing strategy could be made configurable"

## Common Mistakes to Avoid

### ❌ Mistake 1: Jumping to Code
**Problem:** Starting to code without understanding requirements.
**Solution:** Spend 5-10 minutes on requirements and design.

### ❌ Mistake 2: Over-Engineering
**Problem:** Using 10 design patterns for a simple problem.
**Solution:** Use patterns only when they add clear value.

### ❌ Mistake 3: God Class
**Problem:** One class doing everything.
**Solution:** Single Responsibility — one class, one job.

### ❌ Mistake 4: No Error Handling
**Problem:** Code crashes on invalid input.
**Solution:** Validate inputs, handle exceptions gracefully.

### ❌ Mistake 5: Hardcoding
**Problem:** Magic numbers and strings everywhere.
**Solution:** Use constants, enums, and configuration.

### ❌ Mistake 6: Ignoring the Interviewer
**Problem:** Coding silently for 60 minutes.
**Solution:** Explain your thought process, ask for feedback.

### ❌ Mistake 7: Poor Time Management
**Problem:** Spending 40 minutes on design, 10 on code.
**Solution:** Follow the time allocation guidelines.

### ❌ Mistake 8: Not Compiling
**Problem:** Writing a full solution that doesn't compile.
**Solution:** Compile and test incrementally.

## Template: Starting a Machine Coding Problem

```java
// Step 1: Enums
public enum VehicleType {
    MOTORCYCLE(1), CAR(2), TRUCK(3);
    
    private final int size;
    VehicleType(int size) { this.size = size; }
    public int getSize() { return size; }
}

// Step 2: Core Entity
public class Vehicle {
    private final String licensePlate;
    private final VehicleType type;
    
    public Vehicle(String licensePlate, VehicleType type) {
        if (licensePlate == null || licensePlate.isEmpty()) {
            throw new IllegalArgumentException("License plate required");
        }
        this.licensePlate = licensePlate;
        this.type = type;
    }
    // getters, equals, hashCode
}

// Step 3: Primary Operations
public class ParkingLot {
    private final List<Floor> floors;
    
    public Ticket park(Vehicle vehicle) {
        // Find available spot using strategy
        // Create ticket
        // Return ticket
    }
    
    public void remove(Ticket ticket) {
        // Validate ticket
        // Free the spot
        // Calculate fee
    }
}

// Step 4: Entry Point
public class Main {
    public static void main(String[] args) {
        // Create system
        // Run demo
        // Show results
    }
}
```

## Practice Schedule

| Week | Problems | Focus |
|------|----------|-------|
| 1 | Parking Lot, LRU Cache | Basic OOP, data structures |
| 2 | Elevator, Task Scheduler | State machines, scheduling |
| 3 | Library, Splitwise | Relationships, algorithms |
| 4 | Rate Limiter, Custom | Concurrency, design patterns |

## Key Takeaways

1. **Design before code** — 20% design saves 50% refactoring
2. **Start simple** — working code > perfect design
3. **Communicate** — explain your decisions
4. **Manage time** — don't get stuck on one feature
5. **Practice** — build 5-10 systems before the interview
