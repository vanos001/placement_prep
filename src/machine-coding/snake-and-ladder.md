# Snake and Ladder — Machine Coding Problem

## Problem Statement

Design a Snake and Ladder game engine that supports multiple players, configurable board sizes, snake and ladder placements, dice rolling mechanics, and proper turn management including extra turns on sixes.

## Requirements Gathering

### Functional Requirements
1. A 10 x 10 board (100 cells, numbered 1–100)
2. Configurable snakes (head → tail) and ladders (start → end)
3. Two or more players, each with a token
4. Dice rolling (1–6)
5. Player moves forward by dice value; lands on snake/ladder triggers teleport
6. Exact landing required to win (overshoot bounces back)
7. Extra turn on rolling a 6 (max three consecutive 6s → forfeit turn)
8. Game continues until one player reaches the last cell

### Non-Functional Requirements
- Extensible board size and number of snakes/ladders
- Clean separation of board configuration from game logic
- Support for different dice strategies (loaded dice, average)

### Clarifying Questions
- "How many snakes and ladders should the default board have?"
- "Should the board layout be randomly generated or predefined?"
- "What happens on three consecutive sixes — is the turn forfeited entirely?"
- "Does landing on an opponent's token have any effect?"

## Class Design

### Entity Identification
```
Nouns: Board, Cell, Snake, Ladder, Player, Dice, Game, GameConfiguration
```

### Class Diagram

```
┌───────────────────────┐
│         Game           │
├───────────────────────┤
│ - board: Board         │
│ - players: List<Player>│
│ - currentPlayerIdx: int│
│ - gameState: GameState │
├───────────────────────┤
│ + start()              │
│ + playTurn()           │
│ + getWinner(): Player? │
│ + isOver(): bool       │
└───────────┬───────────┘
            │ uses        ┌──────────────────┐
            └────────────►│      Board        │
                          ├──────────────────┤
                          │ - size: int       │
                          │ - snakes: Map     │
                          │ - ladders: Map    │
                          │ - cells: Cell[]  │
                          ├──────────────────┤
                          │ + getPosition(pos)│
                          │ + resolve(pos): int│
                          │ + isSnake(pos)    │
                          │ + isLadder(pos)   │
                          └──────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Snake          │    │    Ladder         │    │      Player       │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ - head: int      │    │ - start: int      │    │ - name: String    │
│ - tail: int      │    │ - end: int        │    │ - position: int   │
├──────────────────┤    ├──────────────────┤    │ - skipTurn: bool  │
│ + getTail(): int │    │ + getEnd(): int   │    ├──────────────────┤
└──────────────────┘    └──────────────────┘    │ + move(steps)     │
                                                 │ + setPosition(pos)│
┌──────────────────┐                             │ + getPosition()   │
│   Dice           │                             └──────────────────┘
├──────────────────┤
│ - strategy: RollStrategy│
├──────────────────┤
│ + roll(): int    │
└──────────────────┘
```

### Board Concept

```
Cell numbering (1–100):
  100  99  98  97  96  95  94  93  92  91
   81  82  83  84  85  86  87  88  89  90
   80  79  78  77  76  75  74  73  72  71
   61  62  63  64  65  66  67  68  69  70
   60  59  58  57  56  55  54  53  52  51
   41  42  43  44  45  46  47  48  49  50
   40  39  38  37  36  35  34  33  32  31
   21  22  23  24  25  26  27  28  29  30
   20  19  18  17  16  15  14  13  12  11
    1   2   3   4   5   6   7   8   9  10

Snakes go DOWN (head > tail):
  16 → 6,   47 → 26,   49 → 11,   56 → 53,   62 → 19,
  64 → 60,  87 → 24,   93 → 73,   95 → 75,   98 → 78

Ladders go UP (start < end):
   1 → 38,   4 → 14,   9 → 31,   21 → 42,   28 → 84,
  36 → 44,   51 → 67,  71 → 91,   80 → 100
```

## Implementation

### Python Implementation

```python
from abc import ABC, abstractmethod
from random import randint
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ==================== Dice ====================

class RollStrategy(ABC):
    @abstractmethod
    def roll(self) -> int:
        pass


class FairDice(RollStrategy):
    def roll(self) -> int:
        return randint(1, 6)


class CrookedDice(RollStrategy):
    """A loaded dice that favors higher values."""
    def roll(self) -> int:
        return randint(2, 6)


class Dice:
    def __init__(self, strategy: RollStrategy = None):
        self.strategy = strategy or FairDice()

    def roll(self) -> int:
        return self.strategy.roll()


# ==================== Board ====================

class Snake:
    def __init__(self, head: int, tail: int):
        if head <= tail:
            raise ValueError(f"Snake head ({head}) must be above tail ({tail})")
        self.head = head
        self.tail = tail


class Ladder:
    def __init__(self, start: int, end: int):
        if start >= end:
            raise ValueError(f"Ladder start ({start}) must be below end ({end})")
        self.start = start
        self.end = end


class Board:
    DEFAULT_SNAKES = {
        16: 6, 47: 26, 49: 11, 56: 53, 62: 19,
        64: 60, 87: 24, 93: 73, 95: 75, 98: 78
    }
    DEFAULT_LADDERS = {
        1: 38, 4: 14, 9: 31, 21: 42, 28: 84,
        36: 44, 51: 67, 71: 91, 80: 100
    }

    def __init__(self, size: int = 10,
                 snakes: Dict[int, int] = None,
                 ladders: Dict[int, int] = None):
        self.size = size
        self.total_cells = size * size
        self.snakes: Dict[int, int] = snakes or dict(self.DEFAULT_SNAKES)
        self.ladders: Dict[int, int] = ladders or dict(self.DEFAULT_LADDERS)
        self._validate()

    def _validate(self):
        for pos in list(self.snakes.keys()) + list(self.ladders.keys()):
            if pos < 1 or pos > self.total_cells:
                raise ValueError(f"Position {pos} out of bounds")
        overlap = set(self.snakes.keys()) & set(self.ladders.keys())
        if overlap:
            raise ValueError(f"Snake and ladder overlap at: {overlap}")

    def resolve(self, position: int) -> Tuple[int, Optional[str]]:
        """Resolve snakes and ladders. Returns (final_position, description)."""
        if position in self.snakes:
            return self.snakes[position], f"Snake! {position} → {self.snakes[position]}"
        if position in self.ladders:
            return self.ladders[position], f"Ladder! {position} → {self.ladders[position]}"
        return position, None

    def final_position(self, start: int, steps: int) -> Tuple[int, Optional[str]]:
        """Compute new position with overshoot bounce-back."""
        target = start + steps
        if target > self.total_cells:
            # Bounce back: overshoot by (target - total), go back
            overshoot = target - self.total_cells
            new_pos = self.total_cells - overshoot
            event = None
        elif target == self.total_cells:
            return target, None
        else:
            new_pos, event = self.resolve(target)
        return new_pos, event

    def is_snake(self, pos: int) -> bool:
        return pos in self.snakes

    def is_ladder(self, pos: int) -> bool:
        return pos in self.ladders


# ==================== Player ====================

class Player:
    def __init__(self, name: str):
        self.name = name
        self.position = 0  # off-board
        self.consecutive_sixes = 0
        self.skip_next = False

    def set_position(self, pos: int):
        self.position = pos

    def move(self, steps: int) -> int:
        self.position += steps
        return self.position

    def record_six(self) -> bool:
        """Record a six. Returns True if turn should be forfeited (3 in a row)."""
        self.consecutive_sixes += 1
        if self.consecutive_sixes >= 3:
            self.consecutive_sixes = 0
            return True  # forfeit
        return False

    def reset_sixes(self):
        self.consecutive_sixes = 0

    def __repr__(self):
        return f"Player({self.name}, pos={self.position})"


# ==================== Game ====================

class Game:
    def __init__(self, board: Board = None):
        self.board = board or Board()
        self.players: List[Player] = []
        self.current_idx = 0
        self.winner: Optional[Player] = None
        self.dice = Dice()
        self.turn_count = 0

    def add_player(self, player: Player):
        if len(self.players) >= 4:
            raise ValueError("Maximum 4 players supported")
        self.players.append(player)

    def current_player(self) -> Player:
        return self.players[self.current_idx]

    def next_player(self):
        self.current_idx = (self.current_idx + 1) % len(self.players)

    def play_turn(self) -> str:
        """Execute one turn for the current player. Returns turn summary."""
        player = self.current_player()
        if player.skip_next:
            player.skip_next = False
            self.next_player()
            return f"{player.name} skips this turn."

        roll = self.dice.roll()
        self.turn_count += 1
        summary_parts = [f"{player.name} rolled a {roll}"]

        if roll == 6:
            forfeit = player.record_six()
            if forfeit:
                summary_parts.append("Three 6s in a row! Turn forfeited.")
                self.next_player()
                return " ".join(summary_parts)
        else:
            player.reset_sixes()

        new_pos, event = self.board.final_position(player.position, roll)
        old_pos = player.position
        player.set_position(new_pos)

        if event:
            summary_parts.append(event)

        summary_parts.append(f"Moved to {new_pos}")

        # Check win
        if new_pos == self.board.total_cells:
            self.winner = player
            summary_parts.append(f"🎉 {player.name} WINS!")
            return " ".join(summary_parts)

        # Extra turn on 6
        if roll == 6:
            summary_parts.append("Extra turn!")
        else:
            self.next_player()

        return " ".join(summary_parts)

    def is_over(self) -> bool:
        return self.winner is not None

    def get_status(self) -> str:
        lines = [f"Turn: {self.turn_count}"]
        for p in self.players:
            marker = " ◄" if p == self.current_player() else ""
            lines.append(f"  {p.name}: position {p.position}{marker}")
        return "\n".join(lines)


def main():
    game = Game()
    game.add_player(Player("Alice"))
    game.add_player(Player("Bob"))
    game.add_player(Player("Charlie"))

    print("=== Snake and Ladder ===")
    print(f"Snakes: {game.board.snakes}")
    print(f"Ladders: {game.board.ladders}")
    print()

    while not game.is_over():
        print(game.get_status())
        result = game.play_turn()
        print(result)
        print()

    print(f"\nFinal winner: {game.winner.name} after {game.turn_count} turns!")


if __name__ == "__main__":
    main()
```

## Key Mechanics

### Snake and Ladder Resolution
When a player lands on a cell that is the head of a snake, they immediately slide down to the tail. When they land at the base of a ladder, they climb to the top. Chains are not allowed — if the landing point of a snake/ladder is itself the start of another, the game should either prevent it during configuration or only resolve once.

### Overshoot Bounce-Back
If a player is at position 97 and rolls a 5 (target = 102), they bounce back: 102 - 100 = 2, so final position is 100 - 2 = 98.

### Three Consecutive Sixes Rule
A common house rule: if a player rolls three sixes in a row, their entire turn (all accumulated moves) is forfeited and the turn passes to the next player.

## Extensions and Discussion Points

### 1. Random Board Generation
Generate random snake and ladder placements ensuring:
- No snake/ladder starts or ends on the same cell
- No circular loops (snake tail is ladder start, etc.)
- Minimum distance for snakes and ladders

### 2. GUI Board Rendering
Implement a `BoardRenderer` that draws the 10x10 grid with snake/ladder indicators and player tokens. The boustrophedon (alternating direction) numbering is visually important.

### 3. Undo/Replay
Store each turn as `(player, roll, old_pos, new_pos, event)` for replay capability.

### 4. Strategy for AI Players
Implement simple heuristics: an AI player could choose to delay (skip a turn) or use a special dice. More interesting would be a "strategic ladder" variant where players pick their next roll from a limited hand.

## Interview Tips

1. **Model the board carefully** — snakes/ladders are special cells, the board itself resolves movement
2. **Edge cases**: player at 99 rolls 1, player lands on snake head that goes below their current position, simultaneous winning
3. **Dice strategy as a Strategy pattern** — easy to swap fair/crooked dice
4. **Overshoot rule is important** — discuss whether bounce-back applies or the move is simply invalid
5. **Time complexity per turn**: O(1) since board lookups are hash-map operations
