# Vending Machine — Machine Coding Problem

## Problem Statement

Design a vending machine that dispenses products, handles payments (coins and notes), returns change, and manages inventory. The machine should support multiple product slots with different prices and quantities.

## Requirements Gathering

### Functional Requirements
1. Display available products with name, price, and stock
2. Accept coins (1, 5, 10, 25 cents) and notes (1, 5, 10, 20 dollars)
3. Allow product selection by slot code
4. Dispense product if sufficient payment is provided
5. Return exact change when overpaid
6. Cancel transaction and refund inserted money
7. Reload inventory and collect cash by the operator
8. Display current balance and change to be returned

### Non-Functional Requirements
- Thread-safe for concurrent interactions
- Extensible for new payment methods (cards, UPI)
- Maintain accurate inventory and cash state

### Clarifying Questions
- "Should the machine support multiple currencies?"
- "What happens when change is unavailable? Cancel or suggest a cheaper product?"
- "Should inventory restocking be automatic or manual?"
- "Are there temperature-controlled slots (cold drinks)?"

## Class Design

### Entity Identification
```
Nouns: VendingMachine, Product, Slot, Coin, Note, Payment, Inventory, CashStore
```

### State Diagram

```
              ┌──────────┐
              │  IDLE    │◄───────────────────────┐
              │          │                         │
              └────┬─────┘                         │
                   │ insert money                  │ cancel / change
                   ▼                               │ returned
              ┌──────────┐                         │
              │ HAS_MONEY│─────────────────────────┘
              │          │
              └────┬─────┘
                   │ select product (sufficient funds)
                   ▼
              ┌──────────┐
              │ DISPENSING│
              └────┬─────┘
                   │ product dispensed, change returned
                   ▼
              ┌──────────┐
              │ DISPENSED │────► IDLE (auto-reset after timeout)
              └──────────┘
```

### Class Diagram

```
┌────────────────────────┐
│     VendingMachine      │
├────────────────────────┤
│ - state: MachineState   │
│ - slots: Map<id, Slot> │
│ - cashStore: CashStore │
│ - currentPayment: Money│
├────────────────────────┤
│ + insertCoin(amount)   │
│ + insertNote(amount)   │
│ + selectProduct(id)    │
│ + cancelTransaction() │
│ + getDisplay()         │
│ + reloadInventory()    │
│ + collectCash()        │
└───────────┬────────────┘
            │ has many          ┌──────────────────┐
            ▼                   │     CashStore     │
┌──────────────────────┐       ├──────────────────┤
│       Slot            │       │ - coins: Map<int,int> │
├──────────────────────┤       │ - notes: Map<int,int> │
│ - slotId: String     │       ├──────────────────┤
│ - product: Product   │       │ + addCash(denom) │
│ - quantity: int      │       │ + canReturn(amount)│
├──────────────────────┤       │ + dispenseChange()│
│ + hasProduct(): bool │       │ + getSummary()   │
│ + dispense()         │       └──────────────────┘
│ + reduceStock()      │
└───────────┬──────────┘
            │ has one
            ▼
┌──────────────────────┐
│      Product          │
├──────────────────────┤
│ - name: String        │
│ - price: Money        │
└──────────────────────┘
```

### Enums

```
MachineState: IDLE, HAS_MONEY, DISPENSING, DISPENSED, OUT_OF_ORDER
Coin:         PENNY(1), NICKEL(5), DIME(10), QUARTER(25)
Note:         ONE(100), FIVE(500), TEN(1000), TWENTY(2000)
              (values stored in cents for uniformity)
```

## Implementation

### Python Implementation

```python
from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass


class MachineState(Enum):
    IDLE = "idle"
    HAS_MONEY = "has_money"
    DISPENSING = "dispensing"
    DISPENSED = "dispensed"


@dataclass
class Product:
    name: str
    price: int  # in cents

    def __str__(self):
        return f"{self.name} (${self.price / 100:.2f})"


class Slot:
    def __init__(self, slot_id: str, product: Product, quantity: int):
        self.slot_id = slot_id
        self.product = product
        self.quantity = quantity

    def has_product(self) -> bool:
        return self.quantity > 0

    def dispense(self):
        if self.quantity <= 0:
            raise RuntimeError(f"Slot {self.slot_id} is empty")
        self.quantity -= 1

    def reload(self, count: int):
        self.quantity += count

    def __str__(self):
        return f"[{self.slot_id}] {self.product} — Stock: {self.quantity}"


class CashStore:
    """Manages the coins and notes inside the machine for making change."""

    def __init__(self):
        self.coins: Dict[int, int] = {1: 10, 5: 10, 10: 10, 25: 10}
        self.notes: Dict[int, int] = {100: 5, 500: 5, 1000: 5, 2000: 5}

    def add_denomination(self, amount: int, count: int):
        if amount in self.coins:
            self.coins[amount] += count
        elif amount in self.notes:
            self.notes[amount] += count
        else:
            raise ValueError(f"Unknown denomination: {amount}")

    def can_return_change(self, amount: int) -> bool:
        """Check if exact change can be given using greedy approach."""
        available = dict(self.coins)
        available.update(self.notes)
        denominations = sorted(available.keys(), reverse=True)

        remaining = amount
        temp = dict(available)
        for denom in denominations:
            if remaining >= denom and temp[denom] > 0:
                count = min(remaining // denom, temp[denom])
                remaining -= denom * count
                temp[denom] -= count
            if remaining == 0:
                return True
        return remaining == 0

    def dispense_change(self, amount: int) -> List[int]:
        """Return list of denominations that make up the change."""
        if amount == 0:
            return []
        if not self.can_return_change(amount):
            raise RuntimeError(f"Cannot make exact change for {amount} cents")

        denominations = sorted({**self.coins, **self.notes}.keys(), reverse=True)
        change: List[int] = []
        remaining = amount
        for denom in denominations:
            if remaining >= denom:
                store = self.coins if denom in self.coins else self.notes
                count = min(remaining // denom, store[denom])
                change.extend([denom] * count)
                store[denom] -= count
                remaining -= denom * count
        return change

    def total(self) -> int:
        coin_total = sum(denom * count for denom, count in self.coins.items())
        note_total = sum(denom * count for denom, count in self.notes.items())
        return coin_total + note_total


class VendingMachine:
    def __init__(self):
        self.state = MachineState.IDLE
        self.slots: Dict[str, Slot] = {}
        self.cash_store = CashStore()
        self.current_payment = 0
        self.selected_slot: Optional[str] = None

    def add_slot(self, slot_id: str, product: Product, quantity: int):
        self.slots[slot_id] = Slot(slot_id, product, quantity)

    def insert_coin(self, amount: int):
        valid_coins = {1, 5, 10, 25}
        if amount not in valid_coins:
            raise ValueError(f"Invalid coin: {amount}. Accepts: {valid_coins}")
        self.current_payment += amount
        self.state = MachineState.HAS_MONEY

    def insert_note(self, amount: int):
        valid_notes = {100, 500, 1000, 2000}
        if amount not in valid_notes:
            raise ValueError(f"Invalid note: {amount}. Accepts: {valid_notes}")
        self.current_payment += amount
        self.state = MachineState.HAS_MONEY

    def select_product(self, slot_id: str) -> str:
        slot = self.slots.get(slot_id)
        if not slot:
            raise ValueError(f"Invalid slot: {slot_id}")

        if not slot.has_product():
            raise RuntimeError(f"{slot.product.name} is out of stock")

        if self.current_payment < slot.product.price:
            raise RuntimeError(
                f"Insufficient funds. Need ${slot.product.price / 100:.2f}, "
                f"have ${self.current_payment / 100:.2f}"
            )

        self.state = MachineState.DISPENSING
        slot.dispense()
        change_amount = self.current_payment - slot.product.price
        self.state = MachineState.DISPENSED

        # Move inserted money to cash store
        self.cash_store.add_denomination(
            slot.product.price, 1  # simplified
        )

        change = []
        if change_amount > 0:
            change = self.cash_store.dispense_change(change_amount)

        self.current_payment = 0
        return f"Dispensed: {slot.product.name}. Change: {change}"

    def cancel_transaction(self) -> List[int]:
        """Refund all inserted money."""
        if self.state == MachineState.IDLE:
            raise RuntimeError("No active transaction to cancel")
        refund = []
        # In a real system, we'd track individual denominations inserted
        # For simplicity, return as the current amount
        amount = self.current_payment
        if amount > 0:
            refund = self.cash_store.dispense_change(amount)
        self.current_payment = 0
        self.state = MachineState.IDLE
        return refund

    def get_display(self) -> str:
        lines = ["=== Vending Machine ==="]
        for slot_id, slot in sorted(self.slots.items()):
            status = "OUT OF STOCK" if not slot.has_product() else f"Stock: {slot.quantity}"
            lines.append(f"  {slot.slot_id}: {slot.product.name} "
                         f"${slot.product.price / 100:.2f} [{status}]")
        if self.current_payment > 0:
            lines.append(f"\n  Current Balance: ${self.current_payment / 100:.2f}")
        return "\n".join(lines)

    def reload(self, slot_id: str, count: int):
        slot = self.slots.get(slot_id)
        if not slot:
            raise ValueError(f"Invalid slot: {slot_id}")
        slot.reload(count)

    def collect_cash(self) -> int:
        total = self.cash_store.total()
        self.cash_store = CashStore()  # reset
        return total


def main():
    machine = VendingMachine()
    machine.add_slot("A1", Product("Coca-Cola", 150), 5)
    machine.add_slot("A2", Product("Pepsi", 150), 3)
    machine.add_slot("B1", Product("Chips", 100), 8)
    machine.add_slot("B2", Product("Candy Bar", 75), 10)
    machine.add_slot("C1", Product("Water", 100), 6)

    print(machine.get_display())

    # Customer buys a candy bar
    machine.insert_coin(25)
    machine.insert_coin(25)
    machine.insert_coin(25)
    machine.insert_coin(25)
    print(f"\nInserted ${machine.current_payment / 100:.2f}")

    result = machine.select_product("B2")
    print(result)
    print(machine.get_display())


if __name__ == "__main__":
    main()
```

## Extensions and Discussion Points

### 1. Coin/Note Tracking per Transaction
Track individual denominations inserted so `cancel()` can return the exact coins/notes rather than computing change.

### 2. Suggestive Selling
When change is unavailable for the selected product, suggest cheaper alternatives the customer can afford.

### 3. Payment Method Abstraction
```python
class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: int) -> bool:
        pass
    @abstractmethod
    def refund(self) -> int:
        pass

class CashPayment(PaymentStrategy): ...
class CardPayment(PaymentStrategy): ...
class UPIPayment(PaymentStrategy): ...
```

### 4. Temperature Zones
Add `SlotType` enum (AMBIENT, COLD, HOT) and associate cooling/heating per zone.

### 5. State Pattern
Formalize states into the State design pattern — each state is a class implementing a common interface, transitions are handled by the state objects themselves.

## Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| Insert money | O(1) | O(1) |
| Select product | O(1) | O(1) |
| Make change | O(D) | O(C) |
| Display | O(S) | O(1) |

Where D = denominations, S = slots, C = number of coins/notes in change.

## Interview Tips

1. **State machine is the key pattern** — draw the state diagram before coding
2. **Change dispensing is the hardest part** — discuss greedy vs. dynamic programming for coin change
3. **Edge cases**: insufficient change, exact payment, out-of-stock during selection, multiple rapid interactions
4. **Real-world**: discuss IoT connectivity, telemetry for restocking alerts, cashless payment trends
