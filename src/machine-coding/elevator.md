# Elevator System — Machine Coding Problem

## Problem Statement

Design an elevator control system for a building with multiple elevators serving multiple floors.

## Requirements

### Functional Requirements
1. Multiple elevators serving multiple floors
2. Users request elevator from any floor (up/down buttons)
3. Users inside elevator select destination floor
4. Elevator moves between floors with configurable speed
5. Display elevator position and direction
6. Handle multiple requests efficiently

### Non-Functional Requirements
- Fair scheduling (no starvation)
- Efficient movement (minimize total travel time)
- Thread-safe for concurrent requests

## Class Design

```
┌─────────────────────────────────────────────────────────┐
│                   ElevatorSystem                         │
│  (Singleton — manages all elevators and dispatching)     │
├─────────────────────────────────────────────────────────┤
│ - elevators: List<Elevator>                              │
│ - schedulingStrategy: SchedulingStrategy                 │
│ - floors: int                                            │
├─────────────────────────────────────────────────────────┤
│ + requestElevator(floor, direction): Elevator            │
│ + selectDestination(elevatorId, floor)                   │
│ + step()                                                 │
│ + display()                                              │
└─────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ Elevator │  │ Elevator │  │ Elevator │
     │    #1    │  │    #2    │  │    #3    │
     ├──────────┤  ├──────────┤  ├──────────┤
     │ - id     │  │          │  │          │
     │ - currentFloor      │  │          │
     │ - direction: Direction│  │         │
     │ - state: ElevatorState│  │         │
     │ - requests: TreeSet   │  │          │
     │ - door: Door          │  │          │
     ├──────────┤            │          │
     │ + move() │            │          │
     │ + stop() │            │          │
     │ + addRequest(floor)   │          │
     │ + step() │            │          │
     └──────────┘            │          │
            │                │          │
            ▼                │          │
     ┌──────────┐           │          │
     │   Door   │           │          │
     ├──────────┤           │          │
     │ - isOpen │           │          │
     │ + open() │           │          │
     │ + close()│           │          │
     └──────────┘           │          │
                            │          │
     ┌──────────────────────┘          │
     ▼                                 │
     ┌─────────────────────┐          │
     │ SchedulingStrategy   │──────────┘
     ├─────────────────────┤
     │ + selectElevator()  │
     └─────────────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐
│Nearest ││  SCAN  ││  LOOK  │
│  Elev  ││(SSTF)  ││        │
└────────┘└────────┘└────────┘
```

### Enums

```
Direction: UP, DOWN, IDLE
ElevatorState: MOVING, STOPPED, DOOR_OPEN, MAINTENANCE
```

## Implementation (Python)

```python
from enum import Enum
from typing import List, Optional, Set
from collections import deque
import time


class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0


class ElevatorState(Enum):
    IDLE = "idle"
    MOVING = "moving"
    DOOR_OPEN = "door_open"
    MAINTENANCE = "maintenance"


class Door:
    def __init__(self):
        self.is_open = False

    def open(self):
        self.is_open = True
        print("  ↕ Door opened")

    def close(self):
        self.is_open = False
        print("  ↕ Door closed")


class Elevator:
    def __init__(self, elevator_id: int, total_floors: int):
        self.id = elevator_id
        self.total_floors = total_floors
        self.current_floor = 0
        self.direction = Direction.IDLE
        self.state = ElevatorState.IDLE
        self.door = Door()
        self.up_requests: Set[int] = set()      # floors to stop at going up
        self.down_requests: Set[int] = set()     # floors to stop at going down
        self.destination_floors: Set[int] = set() # all requested floors

    def add_request(self, floor: int):
        if floor < 0 or floor >= self.total_floors:
            raise ValueError(f"Invalid floor: {floor}")
        if floor == self.current_floor and self.state == ElevatorState.IDLE:
            self._open_door()
            return

        self.destination_floors.add(floor)
        if floor > self.current_floor:
            self.up_requests.add(floor)
        else:
            self.down_requests.add(floor)

        if self.state == ElevatorState.IDLE:
            self._decide_direction()

    def _decide_direction(self):
        if not self.destination_floors:
            self.direction = Direction.IDLE
            self.state = ElevatorState.IDLE
            return

        # SCAN algorithm: continue in current direction if requests exist
        if self.direction == Direction.UP or self.direction == Direction.IDLE:
            if self.up_requests:
                self.direction = Direction.UP
                self.state = ElevatorState.MOVING
                return
            if self.down_requests:
                self.direction = Direction.DOWN
                self.state = ElevatorState.MOVING
                return

        if self.direction == Direction.DOWN:
            if self.down_requests:
                self.direction = Direction.DOWN
                self.state = ElevatorState.MOVING
                return
            if self.up_requests:
                self.direction = Direction.UP
                self.state = ElevatorState.MOVING
                return

    def step(self):
        """Advance elevator by one step (simulate real-time movement)."""
        if self.state == ElevatorState.MAINTENANCE:
            return

        if self.state == ElevatorState.DOOR_OPEN:
            self._close_door()
            return

        if self.state == ElevatorState.IDLE:
            self._decide_direction()
            if self.state == ElevatorState.IDLE:
                return

        # Move one floor
        if self.direction == Direction.UP:
            self.current_floor += 1
        elif self.direction == Direction.DOWN:
            self.current_floor -= 1

        # Check if we need to stop
        if self._should_stop():
            self._stop_at_floor()

    def _should_stop(self) -> bool:
        if self.direction == Direction.UP:
            return self.current_floor in self.up_requests
        elif self.direction == Direction.DOWN:
            return self.current_floor in self.down_requests
        return False

    def _stop_at_floor(self):
        self.state = ElevatorState.STOPPED
        self.up_requests.discard(self.current_floor)
        self.down_requests.discard(self.current_floor)
        self.destination_floors.discard(self.current_floor)
        self._open_door()

    def _open_door(self):
        self.door.open()
        self.state = ElevatorState.DOOR_OPEN

    def _close_door(self):
        self.door.close()
        self._decide_direction()

    def get_status(self) -> dict:
        return {
            "id": self.id,
            "floor": self.current_floor,
            "direction": self.direction.name,
            "state": self.state.value,
            "requests": sorted(self.destination_floors),
        }

    def __str__(self):
        arrow = {"UP": "↑", "DOWN": "↓", "IDLE": "•"}
        return (f"Elevator {self.id}: Floor {self.current_floor} "
                f"{arrow[self.direction.name]} [{self.state.value}]")


class SchedulingStrategy:
    """Base class for elevator scheduling algorithms."""
    def select_elevator(self, elevators: List[Elevator], 
                        floor: int, direction: Direction) -> Optional[Elevator]:
        raise NotImplementedError


class NearestElevatorStrategy(SchedulingStrategy):
    """Select the nearest idle or same-direction elevator."""
    def select_elevator(self, elevators: List[Elevator], 
                        floor: int, direction: Direction) -> Optional[Elevator]:
        best = None
        best_distance = float('inf')

        for elev in elevators:
            if elev.state == ElevatorState.MAINTENANCE:
                continue

            distance = abs(elev.current_floor - floor)

            # Prefer idle elevators
            if elev.state == ElevatorState.IDLE:
                if distance < best_distance:
                    best_distance = distance
                    best = elev
            # Prefer elevators moving in same direction and past us
            elif elev.direction == direction:
                if direction == Direction.UP and elev.current_floor <= floor:
                    if distance < best_distance:
                        best_distance = distance
                        best = elev
                elif direction == Direction.DOWN and elev.current_floor >= floor:
                    if distance < best_distance:
                        best_distance = distance
                        best = elev

        return best


class SCANStrategy(SchedulingStrategy):
    """SCAN (elevator) algorithm — reduces starvation."""
    def select_elevator(self, elevators: List[Elevator], 
                        floor: int, direction: Direction) -> Optional[Elevator]:
        # First: try to find elevator moving toward us in same direction
        for elev in elevators:
            if elev.state == ElevatorState.MAINTENANCE:
                continue
            if elev.direction == direction:
                if direction == Direction.UP and elev.current_floor <= floor:
                    return elev
                if direction == Direction.DOWN and elev.current_floor >= floor:
                    return elev

        # Second: idle elevator
        idle_elevators = [e for e in elevators 
                         if e.state == ElevatorState.IDLE]
        if idle_elevators:
            return min(idle_elevators, 
                      key=lambda e: abs(e.current_floor - floor))

        # Third: any elevator (will change direction after current requests)
        return min(elevators, key=lambda e: abs(e.current_floor - floor))


class ElevatorSystem:
    def __init__(self, num_elevators: int, num_floors: int,
                 strategy: SchedulingStrategy = None):
        self.num_floors = num_floors
        self.elevators = [Elevator(i, num_floors) for i in range(num_elevators)]
        self.strategy = strategy or NearestElevatorStrategy()

    def request_elevator(self, floor: int, direction: Direction) -> Elevator:
        """External request: user at floor presses UP or DOWN."""
        if floor < 0 or floor >= self.num_floors:
            raise ValueError(f"Invalid floor: {floor}")

        elevator = self.strategy.select_elevator(
            self.elevators, floor, direction)

        if not elevator:
            raise RuntimeError("No available elevator")

        elevator.add_request(floor)
        print(f"→ Elevator {elevator.id} assigned to floor {floor} "
              f"(going {direction.name})")
        return elevator

    def select_destination(self, elevator_id: int, floor: int):
        """Internal request: user inside elevator selects floor."""
        elevator = self.elevators[elevator_id]
        elevator.add_request(floor)
        print(f"  → Elevator {elevator_id} destination: floor {floor}")

    def step(self):
        """Advance all elevators by one time step."""
        for elevator in self.elevators:
            elevator.step()

    def run_steps(self, n: int):
        """Run n simulation steps."""
        for i in range(n):
            print(f"\n--- Step {i+1} ---")
            self.step()
            self.display()

    def display(self):
        print("\n" + "=" * 50)
        for floor in range(self.num_floors - 1, -1, -1):
            line = f"Floor {floor:2d} |"
            for elev in self.elevators:
                if elev.current_floor == floor:
                    arrow = {"UP": "↑", "DOWN": "↓", "IDLE": "•"}
                    line += f" [{elev.id}{arrow[elev.direction.name]}] "
                else:
                    line += "  .  "
            print(line)
        print("=" * 50)
        for elev in self.elevators:
            print(f"  {elev}")


# ==================== Demo ====================

def main():
    system = ElevatorSystem(num_elevators=3, num_floors=10)

    print("=== Elevator System Demo ===\n")

    # User at floor 3 wants to go UP
    system.request_elevator(3, Direction.UP)

    # User at floor 7 wants to go DOWN
    system.request_elevator(7, Direction.DOWN)

    # User at floor 1 wants to go UP
    system.request_elevator(1, Direction.UP)

    # Simulate 15 steps
    system.run_steps(15)

    # Users inside elevators select destinations
    system.select_destination(0, 8)
    system.select_destination(1, 2)

    system.run_steps(10)


if __name__ == "__main__":
    main()
```

## Scheduling Algorithms Explained

### 1. FCFS (First Come First Served)
- Simplest: serve requests in order
- Problem: causes excessive travel ("elevator humping")

### 2. SSTF (Shortest Seek Time First)
- Always go to nearest requested floor
- Problem: can starve far-away requests

### 3. SCAN (Elevator Algorithm)
- Move in one direction, serving all requests
- Reverse at the end, serve in opposite direction
- **Best general-purpose algorithm**

### 4. LOOK (Improved SCAN)
- Like SCAN, but reverse direction when no more requests ahead
- More efficient than SCAN

### 5. C-SCAN (Circular SCAN)
- Go to top, jump back to bottom, continue
- Uniform wait time distribution

## Interview Follow-ups

1. **"How would you handle 100 elevators?"**
   → Zone-based dispatching, each elevator serves a range of floors

2. **"How would you optimize for energy efficiency?"**
   → Batch nearby requests, reduce unnecessary movement

3. **"How would you handle peak hours?"**
   → Adaptive scheduling, increase frequency during rush hours

4. **"How would you add priority floors (lobby, parking)?"**
   → Weighted scheduling, priority queues

5. **"How would you handle an elevator going out of service?"**
   → Redistribute requests, update scheduling strategy dynamically
