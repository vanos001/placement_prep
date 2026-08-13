# Splitwise — Expense Splitting Application

## Problem Statement

Design an expense-splitting application like Splitwise that supports multiple split types, balance tracking, and optimal settlement.

## Requirements

### Functional Requirements
1. Create groups with multiple members
2. Add expenses with different split types:
   - Equal split
   - Exact amounts
   - Percentage split
   - Shares (weighted)
3. Track balances between all pairs of members
4. Show who owes whom and how much
5. Settle debts between members
6. Simplify debts (minimize number of transactions)
7. Show expense history per group and per user

### Non-Functional Requirements
- Handle floating-point precision (use cents or BigDecimal)
- Efficient balance calculation
- Clear audit trail

## Class Design

```
┌────────────────────────────────────────────────────────┐
│                     SplitwiseApp                        │
├────────────────────────────────────────────────────────┤
│ - groups: Map<groupId, Group>                          │
│ - users: Map<userId, User>                             │
├────────────────────────────────────────────────────────┤
│ + createUser(name)                                     │
│ + createGroup(name, members)                           │
│ + addExpense(groupId, desc, amount, paidBy, splits)    │
│ + getBalances(groupId)                                 │
│ + settleUp(groupId): List<Settlement>                  │
└────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Group     │  │    User      │  │   Expense    │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ - groupId    │  │ - userId     │  │ - expenseId  │
│ - name       │  │ - name       │  │ - description│
│ - members    │  │ - email      │  │ - amount     │
│ - expenses   │  └──────────────┘  │ - paidBy     │
│ - balances   │                    │ - splitType  │
├──────────────┤                    │ - splits[]   │
│ + addExpense │                    ├──────────────┤
│ + getBalances│                    │ + validate() │
│ + settleUp   │                    └──────────────┘
└──────────────┘                           │
                              ┌────────────┴────────────┐
                              ▼                         ▼
                     ┌──────────────┐          ┌──────────────┐
                     │   Split      │          │  SplitType   │
                     ├──────────────┤          ├──────────────┤
                     │ - userId     │          │ EQUAL        │
                     │ - amount     │          │ EXACT        │
                     │ - percentage │          │ PERCENTAGE   │
                     │ - shares     │          │ SHARES       │
                     └──────────────┘          └──────────────┘

         Balance Graph (who owes whom):
         
         Alice ──$30──► Bob
         Bob   ──$20──► Charlie
         Charlie──$10──► Alice
         
         Simplified (net balances):
         Alice: +$20, Bob: +$10, Charlie: -$30
         Settlement: Charlie pays Alice $20, Charlie pays Bob $10
```

## Implementation (Python)

```python
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import uuid


# ==================== Enums ====================

class SplitType(Enum):
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"
    SHARES = "shares"


# ==================== Models ====================

@dataclass
class User:
    user_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    email: str = ""

    def __str__(self):
        return f"{self.name} ({self.user_id})"


@dataclass
class Split:
    user_id: str
    amount: float = 0.0
    percentage: float = 0.0
    shares: int = 1


@dataclass
class Expense:
    expense_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    amount: float = 0.0
    paid_by: str = ""           # user_id
    split_type: SplitType = SplitType.EQUAL
    splits: List[Split] = field(default_factory=list)

    def validate(self):
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if not self.paid_by:
            raise ValueError("Must specify who paid")
        if not self.splits:
            raise ValueError("Must specify splits")

        if self.split_type == SplitType.EXACT:
            total = sum(s.amount for s in self.splits)
            if abs(total - self.amount) > 0.01:
                raise ValueError(
                    f"Split amounts ({total}) != expense ({self.amount})")

        if self.split_type == SplitType.PERCENTAGE:
            total_pct = sum(s.percentage for s in self.splits)
            if abs(total_pct - 100) > 0.01:
                raise ValueError(
                    f"Percentages ({total_pct}%) != 100%")


@dataclass
class Group:
    group_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    members: List[str] = field(default_factory=list)  # user_ids
    expenses: List[Expense] = field(default_factory=list)
    # balances[i][j] = how much user i owes user j
    balances: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float)))


class DebtSimplifier:
    """Minimize number of transactions using greedy algorithm."""

    @staticmethod
    def simplify(balances: Dict[str, float]) -> List[Tuple[str, str, float]]:
        """
        Given net balances (positive = owed money, negative = owes money),
        return minimal list of (debtor, creditor, amount).
        """
        # Separate creditors and debtors
        creditors = []  # (user_id, amount_owed_to_them)
        debtors = []    # (user_id, amount_they_owe)

        for user_id, balance in balances.items():
            if balance > 0.01:
                creditors.append([user_id, balance])
            elif balance < -0.01:
                debtors.append([user_id, -balance])

        # Sort for greedy matching
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)

        settlements = []
        i, j = 0, 0

        while i < len(debtors) and j < len(creditors):
            debtor_id, debt_amount = debtors[i]
            creditor_id, credit_amount = creditors[j]

            settle_amount = min(debt_amount, credit_amount)
            if settle_amount > 0.01:
                settlements.append(
                    (debtor_id, creditor_id, round(settle_amount, 2)))

            debtors[i][1] -= settle_amount
            creditors[j][1] -= settle_amount

            if debtors[i][1] < 0.01:
                i += 1
            if creditors[j][1] < 0.01:
                j += 1

        return settlements


class GroupService:
    def __init__(self, group: Group, users: Dict[str, User]):
        self.group = group
        self.users = users

    def add_expense(self, expense: Expense):
        expense.validate()

        # Resolve splits if needed
        if expense.split_type == SplitType.EQUAL:
            self._resolve_equal_splits(expense)
        elif expense.split_type == SplitType.PERCENTAGE:
            self._resolve_percentage_splits(expense)
        elif expense.split_type == SplitType.SHARES:
            self._resolve_share_splits(expense)

        # Update balances
        self._update_balances(expense)
        self.group.expenses.append(expense)

    def _resolve_equal_splits(self, expense: Expense):
        if not expense.splits:
            # Default: split among all members
            share = expense.amount / len(self.group.members)
            expense.splits = [
                Split(user_id=uid, amount=round(share, 2))
                for uid in self.group.members
            ]
        else:
            # Split among specified users
            share = expense.amount / len(expense.splits)
            for split in expense.splits:
                split.amount = round(share, 2)

    def _resolve_percentage_splits(self, expense: Expense):
        for split in expense.splits:
            split.amount = round(
                expense.amount * split.percentage / 100, 2)

    def _resolve_share_splits(self, expense: Expense):
        total_shares = sum(s.shares for s in expense.splits)
        for split in expense.splits:
            split.amount = round(
                expense.amount * split.shares / total_shares, 2)

    def _update_balances(self, expense: Expense):
        paid_by = expense.paid_by
        for split in expense.splits:
            if split.user_id == paid_by:
                continue  # Don't owe yourself
            # split.user_id owes paid_by this amount
            self.group.balances[split.user_id][paid_by] += split.amount

    def get_net_balances(self) -> Dict[str, float]:
        """Calculate net balance for each member.
        Positive = others owe them. Negative = they owe others."""
        net = defaultdict(float)
        for debtor, creditors in self.group.balances.items():
            for creditor, amount in creditors.items():
                net[debtor] -= amount
                net[creditor] += amount
        return dict(net)

    def get_pairwise_balances(self) -> List[Tuple[str, str, float]]:
        """Get simplified pairwise balances."""
        # Net out bilateral debts
        simplified = defaultdict(lambda: defaultdict(float))
        for debtor, creditors in self.group.balances.items():
            for creditor, amount in creditors.items():
                simplified[debtor][creditor] += amount
                simplified[creditor][debtor] -= amount

        result = []
        seen = set()
        for user_a in simplified:
            for user_b in simplified[user_a]:
                pair = tuple(sorted([user_a, user_b]))
                if pair in seen:
                    continue
                seen.add(pair)
                net = simplified[user_a][user_b]
                if net > 0.01:
                    result.append((user_a, user_b, round(net, 2)))
                elif net < -0.01:
                    result.append((user_b, user_a, round(-net, 2)))
        return result

    def settle_up(self) -> List[Tuple[str, str, float]]:
        """Get optimal settlement plan."""
        net_balances = self.get_net_balances()
        return DebtSimplifier.simplify(net_balances)


class SplitwiseApp:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}

    def create_user(self, name: str, email: str = "") -> User:
        user = User(name=name, email=email)
        self.users[user.user_id] = user
        return user

    def create_group(self, name: str, 
                     member_ids: List[str]) -> Group:
        for mid in member_ids:
            if mid not in self.users:
                raise ValueError(f"User {mid} not found")
        group = Group(name=name, members=member_ids)
        self.groups[group.group_id] = group
        return group

    def add_expense(self, group_id: str, description: str,
                    amount: float, paid_by: str,
                    split_type: SplitType = SplitType.EQUAL,
                    splits: List[Split] = None) -> Expense:
        group = self.groups.get(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")

        expense = Expense(
            description=description,
            amount=amount,
            paid_by=paid_by,
            split_type=split_type,
            splits=splits or []
        )

        service = GroupService(group, self.users)
        service.add_expense(expense)
        return expense

    def get_group_balances(self, group_id: str) -> List[Tuple[str, str, float]]:
        group = self.groups.get(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")
        return GroupService(group, self.users).get_pairwise_balances()

    def settle_up(self, group_id: str) -> List[Dict]:
        group = self.groups.get(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")

        settlements = GroupService(group, self.users).settle_up()
        result = []
        for debtor_id, creditor_id, amount in settlements:
            debtor = self.users[debtor_id]
            creditor = self.users[creditor_id]
            result.append({
                "from": debtor.name,
                "to": creditor.name,
                "amount": amount
            })
        return result

    def display_balances(self, group_id: str):
        group = self.groups.get(group_id)
        if not group:
            return

        print(f"\n{'='*50}")
        print(f"  {group.name} — Balances")
        print(f"{'='*50}")

        balances = self.get_group_balances(group_id)
        if not balances:
            print("  All settled up! 🎉")
        else:
            for debtor_id, creditor_id, amount in balances:
                debtor = self.users[debtor_id].name
                creditor = self.users[creditor_id].name
                print(f"  {debtor} owes {creditor}: ${amount:.2f}")

        print(f"{'='*50}")

    def display_settlement(self, group_id: str):
        settlements = self.settle_up(group_id)
        print(f"\n{'='*50}")
        print(f"  Optimal Settlement")
        print(f"{'='*50}")
        if not settlements:
            print("  No payments needed! 🎉")
        for s in settlements:
            print(f"  {s['from']} pays {s['to']}: ${s['amount']:.2f}")
        print(f"{'='*50}")


# ==================== Demo ====================

def main():
    app = SplitwiseApp()

    # Create users
    alice = app.create_user("Alice", "alice@email.com")
    bob = app.create_user("Bob", "bob@email.com")
    charlie = app.create_user("Charlie", "charlie@email.com")
    diana = app.create_user("Diana", "diana@email.com")

    print(f"Created users: {alice.name}, {bob.name}, {charlie.name}, {diana.name}")

    # Create group
    trip = app.create_group("Goa Trip", 
                            [alice.user_id, bob.user_id, 
                             charlie.user_id, diana.user_id])

    # Equal split
    print("\n--- Adding expenses ---")
    app.add_expense(trip.group_id, "Hotel", 10000, alice.user_id,
                    SplitType.EQUAL)

    # Exact split
    app.add_expense(trip.group_id, "Dinner", 3000, bob.user_id,
                    SplitType.EXACT, [
                        Split(alice.user_id, amount=800),
                        Split(bob.user_id, amount=1000),
                        Split(charlie.user_id, amount=700),
                        Split(diana.user_id, amount=500),
                    ])

    # Percentage split
    app.add_expense(trip.group_id, "Car Rental", 4000, charlie.user_id,
                    SplitType.PERCENTAGE, [
                        Split(alice.user_id, percentage=30),
                        Split(bob.user_id, percentage=30),
                        Split(charlie.user_id, percentage=20),
                        Split(diana.user_id, percentage=20),
                    ])

    # Shares split
    app.add_expense(trip.group_id, "Activities", 6000, alice.user_id,
                    SplitType.SHARES, [
                        Split(alice.user_id, shares=3),
                        Split(bob.user_id, shares=2),
                        Split(charlie.user_id, shares=2),
                        Split(diana.user_id, shares=1),
                    ])

    # Show balances
    app.display_balances(trip.group_id)

    # Show optimal settlement
    app.display_settlement(trip.group_id)


if __name__ == "__main__":
    main()
```

## Debt Simplification Algorithm

The key insight: convert the problem to **net balances**, then greedily match the largest debtor with the largest creditor.

```
Original debts (complex):
  Alice → Bob: $50
  Bob → Charlie: $30
  Charlie → Alice: $20
  Bob → Alice: $10

Net balances:
  Alice: +50 - 20 + 10 = +$40  (is owed $40)
  Bob:   -50 + 30 - 10 + ...  (complex)
  
Simplified approach:
  1. Calculate net for each person
  2. Sort creditors descending, debtors descending
  3. Greedily match: largest debtor pays largest creditor
  4. Repeat until all settled

Time: O(n log n) where n = number of people
```

## Handling Floating-Point Precision

```python
# Bad — floating point errors
0.1 + 0.2  # = 0.30000000000000004

# Good — use cents (integers)
amount_in_cents = 3000  # $30.00

# Or use Decimal
from decimal import Decimal
amount = Decimal("30.00")
```

## Interview Follow-ups

1. **"How would you handle currency conversion?"**
   → Add currency field to expense, store exchange rate at time of expense

2. **"How would you add recurring expenses?"**
   → Scheduler pattern, auto-generate expenses on schedule

3. **"How would you handle partial settlements?"**
   → Track settlement records, update balances incrementally

4. **"How would you scale to millions of users?"**
   → Shard by group, use graph database for balance queries
