# Movie Ticket Booking System — Machine Coding Problem

## Problem Statement

Design a movie ticket booking system that manages a multiplex with multiple screens, allows users to browse shows, select seats, hold seats during the payment window, and handle concurrent booking attempts with proper locking to prevent double-booking.

## Requirements Gathering

### Functional Requirements
1. Multiple theatres/cinemas, each with multiple screens (auditoriums)
2. Movies scheduled in time slots across screens
3. Seat layout per screen (rows A–H, numbered seats, with categories: Platinum, Gold, Silver)
4. Users can browse movies, view showtimes, and check seat availability
5. Seat selection and reservation (hold for a payment timeout window)
6. Booking confirmation with payment
7. Seat release on payment timeout or cancellation
8. Concurrent booking handling — no double-booking

### Non-Functional Requirements
- Thread-safe seat reservation under concurrent access
- Timeout-based seat release without manual intervention
- Scalable to thousands of concurrent users

### Clarifying Questions
- "What's the seat hold timeout — 5 minutes, 10 minutes?"
- "Should the system handle waitlists when a show is full?"
- "Are there VIP/premium seats with different pricing?"
- "Should we implement an actual payment gateway or mock it?"

## Class Design

### Entity Identification
```
Nouns: Cinema, Screen, Movie, Show, Seat, Booking, User,
       SeatLock, SeatCategory, PaymentService
```

### Class Diagram

```
┌────────────────────┐
│     Cinema          │
├────────────────────┤
│ - name: String      │
│ - screens: List     │
├────────────────────┤
│ + addScreen()       │
│ + getShows()        │
└────────────────────┘
           │
           ▼
┌────────────────────┐         ┌────────────────────┐
│     Screen          │         │     Movie           │
├────────────────────┤         ├────────────────────┤
│ - screenId: String  │◄────────│ - title: String     │
│ - rows: int         │         │ - duration: int     │
│ - cols: int         │         │ - genre: String      │
├────────────────────┤         └────────────────────┘
│ + createSeatLayout()│
│ + getSeats()        │
└────────┬───────────┘
         │ has many
         ▼
┌────────────────────┐
│      Show           │
├────────────────────┤
│ - showId: String    │
│ - movie: Movie      │
│ - screen: Screen    │
│ - startTime: DateTime│
│ - seats: Map<id,Seat>│
│ - seatLocks: Map    │
├────────────────────┤
│ + getAvailableSeats()│
│ + lockSeats(seatIds, user)│
│ + confirmBooking(lockedSeats)│
│ + releaseLock(seatIds)│
│ + getSeatMap()      │
└────────────────────┘

┌────────────────────┐
│      Seat           │
├────────────────────┤
│ - seatId: String    │
│ - row: String       │
│ - number: int       │
│ - category: SeatCat │
│ - status: SeatStatus│
└────────────────────┘

┌────────────────────┐
│    SeatLock          │
├────────────────────┤
│ - seatId: String     │
│ - lockedBy: User    │
│ - lockTime: DateTime│
│ - expiry: DateTime  │
│ - isExpired(): bool │
├────────────────────┤
│ + refresh()         │
└────────────────────┘

┌────────────────────┐
│    Booking           │
├────────────────────┤
│ - bookingId: String │
│ - user: User        │
│ - show: Show        │
│ - seats: List<Seat> │
│ - totalAmount: float│
│ - status: BookingStatus│
│ - createdAt: DateTime│
└────────────────────┘
```

### Enums

```
SeatCategory:  PLATINUM(250), GOLD(180), SILVER(120)
SeatStatus:    AVAILABLE, LOCKED, BOOKED
BookingStatus: PENDING, CONFIRMED, CANCELLED, EXPIRED
```

## Implementation

### Python Implementation

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from threading import Lock, Timer
import uuid
import string


class SeatCategory(Enum):
    PLATINUM = 250.0
    GOLD = 180.0
    SILVER = 120.0


class SeatStatus(Enum):
    AVAILABLE = "available"
    LOCKED = "locked"
    BOOKED = "booked"


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Movie:
    def __init__(self, title: str, duration_minutes: int, genre: str = ""):
        self.title = title
        self.duration = duration_minutes
        self.genre = genre

    def __repr__(self):
        return f"Movie({self.title}, {self.duration}m)"


class Seat:
    def __init__(self, seat_id: str, row: str, number: int,
                 category: SeatCategory):
        self.seat_id = seat_id
        self.row = row
        self.number = number
        self.category = category
        self.status = SeatStatus.AVAILABLE

    @property
    def price(self) -> float:
        return self.category.value

    def __repr__(self):
        return f"{self.row}{self.number}({self.category.name})"


class SeatLock:
    def __init__(self, seat_id: str, locked_by: str,
                 timeout_seconds: int = 300):
        self.seat_id = seat_id
        self.locked_by = locked_by
        self.lock_time = datetime.now()
        self.expiry = self.lock_time + timedelta(seconds=timeout_seconds)
        self.timer = Timer(timeout_seconds, self._auto_release)
        self.timer.daemon = True

    def _auto_release(self):
        """Called by timer when lock expires."""
        self.is_expired_flag = True

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expiry

    def refresh(self, timeout_seconds: int = 300):
        self.expiry = datetime.now() + timedelta(seconds=timeout_seconds)

    def cancel_timer(self):
        self.timer.cancel()

    def start_timer(self):
        self.timer.start()


class Booking:
    def __init__(self, user: str, show: "Show", seats: List[Seat]):
        self.booking_id = str(uuid.uuid4())[:8].upper()
        self.user = user
        self.show = show
        self.seats = seats
        self.total_amount = sum(s.price for s in seats)
        self.status = BookingStatus.PENDING
        self.created_at = datetime.now()

    def __repr__(self):
        return (f"Booking[{self.booking_id}] {self.user} — "
                f"{len(self.seats)} seats, ${self.total_amount:.2f}")


class Show:
    def __init__(self, show_id: str, movie: Movie, screen_name: str,
                 start_time: datetime):
        self.show_id = show_id
        self.movie = movie
        self.screen_name = screen_name
        self.start_time = start_time
        self.seats: Dict[str, Seat] = {}
        self.locks: Dict[str, SeatLock] = {}
        self.bookings: List[Booking] = []
        self.lock_timeout = 300  # 5 minutes
        self._lock = Lock()

    def add_seat(self, seat: Seat):
        self.seats[seat.seat_id] = seat

    def get_available_seats(self, category: SeatCategory = None
                            ) -> List[Seat]:
        """Get all available seats, optionally filtered by category."""
        available = []
        for seat in self.seats.values():
            if seat.status != SeatStatus.AVAILABLE:
                continue
            if category and seat.category != category:
                continue
            available.append(seat)
        return available

    def lock_seats(self, seat_ids: List[str], user: str) -> List[Seat]:
        """Lock seats for a user. Returns locked seats or raises on failure."""
        with self._lock:
            failed = []
            locked_seats = []

            for sid in seat_ids:
                seat = self.seats.get(sid)
                if not seat or seat.status != SeatStatus.AVAILABLE:
                    failed.append(sid)
                    continue
                # Check if expired lock exists
                existing = self.locks.get(sid)
                if existing and not existing.is_expired:
                    failed.append(sid)
                    continue

            if failed:
                raise ValueError(
                    f"Cannot lock seats: {failed} "
                    f"(unavailable or locked by others)")

            for sid in seat_ids:
                seat = self.seats[sid]
                seat.status = SeatStatus.LOCKED
                lock = SeatLock(sid, user, self.lock_timeout)
                lock.start_timer()
                self.locks[sid] = lock
                locked_seats.append(seat)

            return locked_seats

    def confirm_booking(self, user: str, seat_ids: List[str]) -> Booking:
        """Confirm booking for locked seats."""
        with self._lock:
            seats = []
            for sid in seat_ids:
                seat = self.seats.get(sid)
                lock = self.locks.get(sid)

                if not seat or seat.status != SeatStatus.LOCKED:
                    raise ValueError(f"Seat {sid} is not locked")

                if not lock or lock.locked_by != user:
                    raise ValueError(f"Seat {sid} not locked by {user}")

                if lock.is_expired:
                    seat.status = SeatStatus.AVAILABLE
                    del self.locks[sid]
                    raise ValueError(f"Lock on {sid} has expired")

                lock.cancel_timer()
                del self.locks[sid]
                seat.status = SeatStatus.BOOKED
                seats.append(seat)

            booking = Booking(user, self, seats)
            booking.status = BookingStatus.CONFIRMED
            self.bookings.append(booking)
            return booking

    def release_locks(self, seat_ids: List[str]):
        """Release locks (on cancellation or expiry)."""
        with self._lock:
            for sid in seat_ids:
                seat = self.seats.get(sid)
                lock = self.locks.get(sid)
                if lock:
                    lock.cancel_timer()
                    del self.locks[sid]
                if seat and seat.status == SeatStatus.LOCKED:
                    seat.status = SeatStatus.AVAILABLE

    def get_seat_map(self) -> str:
        """Display a visual seat map."""
        rows = {}
        for seat in self.seats.values():
            if seat.row not in rows:
                rows[seat.row] = {}
            rows[seat.row][seat.number] = seat

        lines = [f"Screen: {self.screen_name} | {self.movie.title}"]
        lines.append(f"{'':>3} " + " ".join(
            str(n).rjust(3) for n in sorted(rows.values())[0].keys()
            if rows.values()))

        for row_name in sorted(rows.keys()):
            seats = rows[row_name]
            seat_str = f"{row_name}  "
            for num in sorted(seats.keys()):
                s = seats[num]
                if s.status == SeatStatus.AVAILABLE:
                    seat_str += " ○  "
                elif s.status == SeatStatus.LOCKED:
                    seat_str += " ◐  "
                else:
                    seat_str += " ●  "
            lines.append(seat_str)

        lines.append("  ○ Available  ◐ Locked  ● Booked")
        return "\n".join(lines)


class Cinema:
    def __init__(self, name: str):
        self.name = name
        self.shows: Dict[str, Show] = {}

    def add_show(self, show: Show):
        self.shows[show.show_id] = show

    def create_standard_screen(self, show_id: str, movie: Movie,
                               screen_name: str, start_time: datetime):
        """Create a show with a standard seat layout."""
        show = Show(show_id, movie, screen_name, start_time)

        # Create seat layout: rows A-H, 10 seats per row
        categories = {
            'A': SeatCategory.PLATINUM, 'B': SeatCategory.PLATINUM,
            'C': SeatCategory.GOLD, 'D': SeatCategory.GOLD,
            'E': SeatCategory.GOLD, 'F': SeatCategory.SILVER,
            'G': SeatCategory.SILVER, 'H': SeatCategory.SILVER,
        }
        for row in sorted(categories.keys()):
            cat = categories[row]
            for num in range(1, 11):
                sid = f"{row}{num}"
                show.add_seat(Seat(sid, row, num, cat))

        self.add_show(show)
        return show


def main():
    cinema = Cinema("Star Cinema")
    show = cinema.create_standard_screen(
        "S001",
        Movie("Inception", 148, "Sci-Fi"),
        "Screen 1",
        datetime(2025, 1, 15, 18, 0)
    )

    print(show.get_seat_map())

    # User browses available seats
    available = show.get_available_seats()
    print(f"\nAvailable seats: {len(available)}")

    # User locks seats
    selected = ["C3", "C4", "C5"]
    locked = show.lock_seats(selected, "alice@example.com")
    print(f"\nAlice locked: {locked}")

    print(show.get_seat_map())

    # Alice confirms booking
    booking = show.confirm_booking("alice@example.com", selected)
    print(f"\n{booking}")
    print(f"Status: {booking.status.name}")

    print(show.get_seat_map())


if __name__ == "__main__":
    main()
```

## Concurrency Model

### Seat Locking with Timeout
When a user selects seats, they are **locked** for a configurable timeout (default 5 minutes). A background `Timer` thread marks the lock as expired. On confirmation, the timer is cancelled and seats become BOOKED.

### Thread Safety
A `threading.Lock` on the `Show` object ensures that lock/confirm/release operations are atomic. In a distributed setting, this would be replaced with:
- **Distributed lock** (Redis SETNX) for multi-instance deployments
- **Optimistic locking** (version column in database) for lower-contention paths

### Handling Failed Payments
When a lock expires:
1. The timer fires → marks lock as expired
2. On next access (or a cleanup sweep), expired locks are released
3. Seats return to AVAILABLE status

## Extensions and Discussion Points

### 1. Waitlist
When a show is sold out, users can join a waitlist. If a booking is cancelled or a lock expires, the waitlisted user gets first dibs with a short notification window.

### 2. Seat Recommendation Algorithm
Suggest the "best available" cluster — contiguous seats centered in the row, or the closest to the middle of the auditorium.

### 3. Dynamic Pricing
Surge pricing for opening weekends, premium showtimes. Introduce `PricingStrategy` with time-based and demand-based modifiers.

### 4. Distributed Architecture
Replace in-memory locks with Redis-based locks. Use a message queue (Kafka) for booking events. Store bookings in PostgreSQL with optimistic concurrency control.

## Complexity Analysis

| Operation | Time | Notes |
|-----------|------|-------|
| Get available seats | O(S) | S = seats per screen (~80) |
| Lock seats | O(K) | K = seats to lock, with mutex |
| Confirm booking | O(K) | With mutex |
| Seat map display | O(S) | Sorting and grouping |

## Interview Tips

1. **Concurrency is the main challenge** — discuss locks, race conditions, double-booking
2. **Lock timeout vs. polling** — timers are elegant but need careful lifecycle management
3. **Discuss optimistic vs. pessimistic locking** — pessimistic (mutex) for correctness, optimistic (version check) for scalability
4. **Discuss what happens at scale** — Redis distributed locks, database-level constraints
5. **Edge cases**: booking same seat twice, confirming after expiry, concurrent confirms for the same seat
