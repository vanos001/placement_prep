# Parking Lot System — Machine Coding Problem

## Problem Statement

Design a parking lot system that can handle multiple floors, different vehicle types, and various parking strategies.

## Requirements Gathering

### Functional Requirements
1. Park a vehicle and issue a ticket
2. Remove a vehicle and calculate fee
3. Support different vehicle types: Motorcycle, Car, Truck
4. Support different spot sizes: Compact, Large, Handicapped
5. Multiple floors with multiple spots each
6. Find available spots (nearest, random, etc.)
7. Display parking lot status

### Non-Functional Requirements
- Thread-safe operations
- Efficient spot lookup (O(1) for availability check)
- Extensible for new vehicle types and pricing strategies

### Clarifying Questions (Ask These!)
- "Should I handle reservations or just first-come-first-served?"
- "What pricing model — hourly, flat rate, or progressive?"
- "Should the system handle concurrent access?"
- "Are there EV charging spots?"

## Class Design

### Entity Identification
```
Nouns in requirements:
- ParkingLot, Floor, ParkingSpot, Vehicle, Ticket, 
- VehicleType, SpotSize, PricingStrategy
```

### Class Diagram

```
┌─────────────────────┐
│     ParkingLot       │
├─────────────────────┤
│ - name: String       │
│ - floors: List<Floor>│
│ - pricingStrategy    │
│ - spotAllocationStrat│
├─────────────────────┤
│ + park(vehicle): Tkt │
│ + remove(ticket)     │
│ + getAvailableSpots()│
│ + displayStatus()    │
└─────────┬───────────┘
          │ has many
          ▼
┌─────────────────────┐
│       Floor          │
├─────────────────────┤
│ - floorNumber: int   │
│ - spots: Map<id,Spot>│
├─────────────────────┤
│ + findSpot(type): Spot│
│ + addSpot(spot)      │
│ + getAvailableCount()│
└─────────┬───────────┘
          │ has many
          ▼
┌─────────────────────┐      ┌─────────────────────┐
│    ParkingSpot       │      │      Vehicle         │
├─────────────────────┤      ├─────────────────────┤
│ - spotId: String     │      │ - licensePlate: Str  │
│ - size: SpotSize     │ ◄────│ - type: VehicleType  │
│ - vehicle: Vehicle   │      │ - color: String      │
│ - state: SpotState   │      ├─────────────────────┤
├─────────────────────┤      │ + getType()          │
│ + park(vehicle)      │      │ + getLicensePlate()  │
│ + remove()           │      └─────────────────────┘
│ + isAvailable()      │
│ + canFit(vehicle)    │
└─────────────────────┘

┌─────────────────────┐
│       Ticket         │
├─────────────────────┤
│ - ticketId: String   │
│ - vehicle: Vehicle   │
│ - spot: ParkingSpot  │
│ - entryTime: DateTime│
│ - exitTime: DateTime │
├─────────────────────┤
│ + getDuration()      │
│ + getFee()           │
└─────────────────────┘
```

### Enums

```
VehicleType: MOTORCYCLE(size=1), CAR(size=2), TRUCK(size=3)
SpotSize:    COMPACT(max=2), LARGE(max=3), HANDICAPPED(max=2)
SpotState:   AVAILABLE, OCCUPIED, RESERVED, OUT_OF_SERVICE
```

## Implementation

### Python Implementation

```python
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List
from abc import ABC, abstractmethod
import uuid


# ==================== Enums ====================

class VehicleType(Enum):
    MOTORCYCLE = 1
    CAR = 2
    TRUCK = 3


class SpotSize(Enum):
    COMPACT = 1
    LARGE = 2
    HANDICAPPED = 3


class SpotState(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    OUT_OF_SERVICE = "out_of_service"


# ==================== Models ====================

class Vehicle:
    def __init__(self, license_plate: str, vehicle_type: VehicleType, color: str = ""):
        if not license_plate:
            raise ValueError("License plate cannot be empty")
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type
        self.color = color

    def __str__(self):
        return f"{self.vehicle_type.name}({self.license_plate})"


class ParkingSpot:
    def __init__(self, spot_id: str, size: SpotSize, floor_number: int):
        self.spot_id = spot_id
        self.size = size
        self.floor_number = floor_number
        self.vehicle: Optional[Vehicle] = None
        self.state = SpotState.AVAILABLE

    def can_fit(self, vehicle: Vehicle) -> bool:
        if self.state != SpotState.AVAILABLE:
            return False
        return vehicle.vehicle_type.value <= self.size.value

    def park(self, vehicle: Vehicle) -> bool:
        if not self.can_fit(vehicle):
            return False
        self.vehicle = vehicle
        self.state = SpotState.OCCUPIED
        return True

    def remove(self) -> Optional[Vehicle]:
        if self.state != SpotState.OCCUPIED:
            return None
        vehicle = self.vehicle
        self.vehicle = None
        self.state = SpotState.AVAILABLE
        return vehicle

    def is_available(self) -> bool:
        return self.state == SpotState.AVAILABLE

    def __str__(self):
        status = f"Occupied by {self.vehicle}" if self.vehicle else self.state.value
        return f"Spot {self.spot_id} [{self.size.name}] - {status}"


class Ticket:
    def __init__(self, vehicle: Vehicle, spot: ParkingSpot):
        self.ticket_id = str(uuid.uuid4())[:8].upper()
        self.vehicle = vehicle
        self.spot = spot
        self.entry_time = datetime.now()
        self.exit_time: Optional[datetime] = None

    def close(self):
        self.exit_time = datetime.now()

    def get_duration_hours(self) -> float:
        end = self.exit_time or datetime.now()
        delta = end - self.entry_time
        return max(delta.total_seconds() / 3600, 0)

    def __str__(self):
        return (f"Ticket[{self.ticket_id}] - {self.vehicle} "
                f"at Spot {self.spot.spot_id}")


class Floor:
    def __init__(self, floor_number: int):
        self.floor_number = floor_number
        self.spots: Dict[str, ParkingSpot] = {}

    def add_spot(self, spot: ParkingSpot):
        self.spots[spot.spot_id] = spot

    def find_available_spot(self, vehicle: Vehicle) -> Optional[ParkingSpot]:
        for spot in self.spots.values():
            if spot.can_fit(vehicle):
                return spot
        return None

    def get_spot(self, spot_id: str) -> Optional[ParkingSpot]:
        return self.spots.get(spot_id)

    def get_available_count(self) -> int:
        return sum(1 for s in self.spots.values() if s.is_available())

    def get_occupancy(self) -> Dict:
        total = len(self.spots)
        occupied = sum(1 for s in self.spots.values() 
                      if s.state == SpotState.OCCUPIED)
        return {
            "floor": self.floor_number,
            "total": total,
            "occupied": occupied,
            "available": total - occupied,
            "occupancy_pct": round(occupied / total * 100, 1) if total else 0
        }


# ==================== Strategies ====================

class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, ticket: Ticket) -> float:
        pass


class HourlyPricing(PricingStrategy):
    def __init__(self, rate_per_hour: float = 20.0):
        self.rate = rate_per_hour

    def calculate(self, ticket: Ticket) -> float:
        hours = ticket.get_duration_hours()
        return round(hours * self.rate, 2)


class ProgressivePricing(PricingStrategy):
    def calculate(self, ticket: Ticket) -> float:
        hours = ticket.get_duration_hours()
        if hours <= 1:
            return 10.0
        elif hours <= 5:
            return 10 + (hours - 1) * 15
        elif hours <= 24:
            return 70 + (hours - 5) * 10
        else:
            return 260 + (hours - 24) * 5


class VehicleTypePricing(PricingStrategy):
    """Different rates for different vehicle types."""
    RATES = {
        VehicleType.MOTORCYCLE: 10,
        VehicleType.CAR: 20,
        VehicleType.TRUCK: 40,
    }

    def calculate(self, ticket: Ticket) -> float:
        hours = ticket.get_duration_hours()
        rate = self.RATES.get(ticket.vehicle.vehicle_type, 20)
        return round(hours * rate, 2)


class SpotAllocationStrategy(ABC):
    @abstractmethod
    def find_spot(self, floors: List[Floor], vehicle: Vehicle) -> Optional[ParkingSpot]:
        pass


class NearestSpotStrategy(SpotAllocationStrategy):
    """Find the first available spot from floor 0 upward."""
    def find_spot(self, floors: List[Floor], vehicle: Vehicle) -> Optional[ParkingSpot]:
        for floor in floors:
            spot = floor.find_available_spot(vehicle)
            if spot:
                return spot
        return None


class BestFitStrategy(SpotAllocationStrategy):
    """Find the smallest spot that fits the vehicle."""
    def find_spot(self, floors: List[Floor], vehicle: Vehicle) -> Optional[ParkingSpot]:
        best: Optional[ParkingSpot] = None
        for floor in floors:
            for spot in floor.spots.values():
                if spot.can_fit(vehicle):
                    if best is None or spot.size.value < best.size.value:
                        best = spot
        return best


# ==================== Main System ====================

class ParkingLot:
    def __init__(self, name: str, pricing: PricingStrategy = None,
                 allocation: SpotAllocationStrategy = None):
        self.name = name
        self.floors: List[Floor] = []
        self.active_tickets: Dict[str, Ticket] = {}  # ticket_id -> Ticket
        self.vehicle_tickets: Dict[str, Ticket] = {}  # license -> Ticket
        self.completed_tickets: List[Ticket] = []
        self.pricing = pricing or HourlyPricing()
        self.allocation = allocation or NearestSpotStrategy()

    def add_floor(self, floor: Floor):
        self.floors.append(floor)
        self.floors.sort(key=lambda f: f.floor_number)

    def park(self, vehicle: Vehicle) -> Ticket:
        if vehicle.license_plate in self.vehicle_tickets:
            raise ValueError(f"Vehicle {vehicle.license_plate} already parked")

        spot = self.allocation.find_spot(self.floors, vehicle)
        if not spot:
            raise ValueError("No available spot for " + str(vehicle))

        spot.park(vehicle)
        ticket = Ticket(vehicle, spot)
        self.active_tickets[ticket.ticket_id] = ticket
        self.vehicle_tickets[vehicle.license_plate] = ticket
        return ticket

    def remove(self, ticket_id: str) -> float:
        ticket = self.active_tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Invalid ticket: {ticket_id}")

        ticket.close()
        fee = self.pricing.calculate(ticket)
        ticket.spot.remove()

        del self.active_tickets[ticket_id]
        del self.vehicle_tickets[ticket.vehicle.license_plate]
        self.completed_tickets.append(ticket)
        return fee

    def get_status(self) -> Dict:
        total = sum(len(f.spots) for f in self.floors)
        occupied = total - sum(f.get_available_count() for f in self.floors)
        return {
            "name": self.name,
            "total_spots": total,
            "occupied": occupied,
            "available": total - occupied,
            "floors": [f.get_occupancy() for f in self.floors]
        }

    def display(self):
        print(f"\n{'='*50}")
        print(f"  {self.name} — Parking Status")
        print(f"{'='*50}")
        for floor in self.floors:
            info = floor.get_occupancy()
            bar = "█" * int(info["occupancy_pct"] / 5) + "░" * (20 - int(info["occupancy_pct"] / 5))
            print(f"  Floor {info['floor']}: [{bar}] "
                  f"{info['occupied']}/{info['total']} "
                  f"({info['occupancy_pct']}%)")
        status = self.get_status()
        print(f"\n  Total: {status['available']} spots available "
              f"out of {status['total_spots']}")
        print(f"{'='*50}\n")


# ==================== Demo ====================

def create_demo_lot() -> ParkingLot:
    lot = ParkingLot("City Center Parking", pricing=ProgressivePricing())

    # Floor 0: 5 compact + 3 large
    floor0 = Floor(0)
    for i in range(5):
        floor0.add_spot(ParkingSpot(f"0-C{i+1}", SpotSize.COMPACT, 0))
    for i in range(3):
        floor0.add_spot(ParkingSpot(f"0-L{i+1}", SpotSize.LARGE, 0))
    lot.add_floor(floor0)

    # Floor 1: 8 compact + 4 large
    floor1 = Floor(1)
    for i in range(8):
        floor1.add_spot(ParkingSpot(f"1-C{i+1}", SpotSize.COMPACT, 1))
    for i in range(4):
        floor1.add_spot(ParkingSpot(f"1-L{i+1}", SpotSize.LARGE, 1))
    lot.add_floor(floor1)

    return lot


def main():
    lot = create_demo_lot()

    # Park some vehicles
    car1 = Vehicle("KA-01-HH-1234", VehicleType.CAR, "White")
    car2 = Vehicle("KA-01-HH-5678", VehicleType.CAR, "Black")
    bike1 = Vehicle("KA-01-HH-9999", VehicleType.MOTORCYCLE, "Red")
    truck1 = Vehicle("KA-01-HH-0001", VehicleType.TRUCK, "Blue")

    t1 = lot.park(car1)
    print(f"Parked: {t1}")

    t2 = lot.park(car2)
    print(f"Parked: {t2}")

    t3 = lot.park(bike1)
    print(f"Parked: {t3}")

    t4 = lot.park(truck1)
    print(f"Parked: {t4}")

    lot.display()

    # Remove a vehicle
    fee = lot.remove(t2.ticket_id)
    print(f"Removed {t2.vehicle} — Fee: ${fee}")

    lot.display()


if __name__ == "__main__":
    main()
```

### Java Implementation (Core Classes)

```java
// VehicleType.java
public enum VehicleType {
    MOTORCYCLE(1), CAR(2), TRUCK(3);
    
    private final int size;
    VehicleType(int size) { this.size = size; }
    public int getSize() { return size; }
}

// SpotSize.java
public enum SpotSize {
    COMPACT(2), LARGE(3), HANDICAPPED(2);
    
    private final int maxSize;
    SpotSize(int maxSize) { this.maxSize = maxSize; }
    public int getMaxSize() { return maxSize; }
}

// Vehicle.java
public class Vehicle {
    private final String licensePlate;
    private final VehicleType type;
    private final String color;
    
    public Vehicle(String licensePlate, VehicleType type, String color) {
        if (licensePlate == null || licensePlate.isEmpty())
            throw new IllegalArgumentException("License plate required");
        this.licensePlate = licensePlate;
        this.type = type;
        this.color = color;
    }
    
    // getters, equals, hashCode, toString
}

// ParkingSpot.java
public class ParkingSpot {
    private final String id;
    private final SpotSize size;
    private final int floorNumber;
    private Vehicle vehicle;
    private SpotState state;
    
    public ParkingSpot(String id, SpotSize size, int floorNumber) {
        this.id = id;
        this.size = size;
        this.floorNumber = floorNumber;
        this.state = SpotState.AVAILABLE;
    }
    
    public boolean canFit(Vehicle v) {
        return state == SpotState.AVAILABLE 
            && v.getType().getSize() <= size.getMaxSize();
    }
    
    public synchronized boolean park(Vehicle v) {
        if (!canFit(v)) return false;
        this.vehicle = v;
        this.state = SpotState.OCCUPIED;
        return true;
    }
    
    public synchronized Vehicle remove() {
        if (state != SpotState.OCCUPIED) return null;
        Vehicle v = this.vehicle;
        this.vehicle = null;
        this.state = SpotState.AVAILABLE;
        return v;
    }
    
    // getters
}

// ParkingLot.java
public class ParkingLot {
    private final String name;
    private final List<Floor> floors;
    private final Map<String, Ticket> activeTickets;
    private final PricingStrategy pricingStrategy;
    
    public Ticket park(Vehicle vehicle) {
        // Find spot using allocation strategy
        // Create ticket
        // Return ticket
    }
    
    public double remove(String ticketId) {
        // Validate ticket
        // Calculate fee
        // Free spot
        // Return fee
    }
}
```

## Extensibility Discussion

### Adding New Vehicle Types
1. Add to `VehicleType` enum
2. Update `canFit()` logic if needed
3. Add pricing rate if using type-based pricing

### Adding Reservations
```
New class: Reservation
- userId, spot, startTime, endTime

New state: RESERVED (in SpotState)

New methods:
- ParkingLot.reserve(userId, spotId, timeRange)
- ParkingLot.cancelReservation(reservationId)
```

### Adding EV Charging
```
New class: EVChargingSpot extends ParkingSpot
- chargingRate: double (kWh)
- chargeVehicle(): double

Strategy: PreferEVSpotStrategy extends SpotAllocationStrategy
```

### Adding Valet Parking
```
New class: ValetService
- assignValet(ticketId): Valet
- Valet: id, name, currentTask

Observer: ValetNotificationObserver
- onSpotAvailable → assign next valet
```

## Complexity Analysis

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|-----------------|
| Park | O(F × S) worst case | O(1) |
| Remove | O(1) with HashMap | O(1) |
| Find Spot | O(F × S) | O(1) |
| Display | O(F × S) | O(1) |

Where F = floors, S = spots per floor.

## Common Interview Follow-ups

1. **"How would you handle concurrent access?"**
   → Use synchronized blocks on ParkingSpot, or use ConcurrentHashMap

2. **"How would you persist data?"**
   → Repository pattern with interface, swap between in-memory and DB

3. **"How would you handle 10,000 spots efficiently?"**
   → Maintain available spot queues per type, avoid scanning all spots

4. **"How would you add a mobile app?"**
   → Observer pattern for notifications, REST API layer on top
