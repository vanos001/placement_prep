# Tic-Tac-Toe — Machine Coding Problem

## Problem Statement

Design a Tic-Tac-Toe game engine that supports two players (human vs human or human vs AI), validates moves, detects winners, and can be extended to N x N boards with customizable winning condition lengths.

## Requirements Gathering

### Functional Requirements
1. N x N game board (default 3 x 3)
2. Two players taking turns (X and O)
3. Validate moves (within bounds, cell not occupied)
4. Detect win condition (row, column, diagonal)
5. Detect draw (board full, no winner)
6. Reset game for a new round
7. Keep track of score across rounds
8. AI opponent using minimax algorithm

### Non-Functional Requirements
- Clean separation of game logic from display
- Extensible to different board sizes
- Efficient win-check (avoid scanning entire board each move)

### Clarifying Questions
- "Should the game support more than 2 players?"
- "Is the winning condition always N-in-a-row, or configurable (e.g., 3-in-a-row on 5x5)?"
- "Should the AI use minimax, or is random play acceptable?"
- "Is this console-based or should it support a GUI?"

## Class Design

### Entity Identification
```
Nouns: Board, Player, Symbol, Move, Game, AIPlayer, GameResult, ScoreBoard
```

### Class Diagram

```
┌──────────────────────┐
│       Game            │
├──────────────────────┤
│ - board: Board        │
│ - players: List<Player>│
│ - currentPlayer: int │
│ - result: GameResult  │
│ - scoreboard: Scores  │
├──────────────────────┤
│ + makeMove(row, col) │
│ + getBoard()          │
│ + getCurrentPlayer() │
│ + reset()             │
│ + isOver(): bool      │
│ + getWinner()         │
└───────────┬───────────┘
            │ uses
            ▼
┌──────────────────────┐      ┌────────────────────┐
│       Board           │      │     Player          │
├──────────────────────┤      ├────────────────────┤
│ - size: int           │◄─────│ - name: String      │
│ - grid: Symbol[][]   │      │ - symbol: Symbol    │
│ - winLength: int     │      ├────────────────────┤
├──────────────────────┤      │ + getName()         │
│ + getCell(r, c)      │      │ + getSymbol()       │
│ + setCell(r, c, sym) │      └─────────┬──────────┘
│ + isEmpty(r, c): bool│                │
│ + isFull(): bool     │        ┌───────┴────────┐
│ + checkWin(sym): bool│        │ extends        │
└──────────────────────┘        ▼                ▼
                        ┌──────────────┐ ┌──────────────┐
                        │  HumanPlayer │ │  AIPlayer    │
                        ├──────────────┤ ├──────────────┤
                        │              │ │- depth: int  │
                        └──────────────┘ │+ getMove(bd)│
                                         └──────────────┘

┌──────────────────────┐
│     GameResult        │
├──────────────────────┤
│ - winner: Player?    │
│ - isDraw: bool       │
│ - winningCells: List │
└──────────────────────┘

┌──────────────────────┐
│     Symbol (Enum)     │
├──────────────────────┤
│ X, O, EMPTY          │
└──────────────────────┘
```

## Implementation

### Python Implementation

```python
from enum import Enum
from typing import List, Optional, Tuple
from copy import deepcopy
import math


class Symbol(Enum):
    EMPTY = " "
    X = "X"
    O = "O"


class GameResult:
    def __init__(self):
        self.winner: Optional[str] = None  # player name or None
        self.is_draw = False
        self.winning_cells: List[Tuple[int, int]] = []

    @property
    def is_over(self) -> bool:
        return self.winner is not None or self.is_draw


class Board:
    def __init__(self, size: int = 3, win_length: int = 3):
        if win_length > size:
            raise ValueError("Win length cannot exceed board size")
        self.size = size
        self.win_length = win_length
        self.grid = [[Symbol.EMPTY] * size for _ in range(size)]

    def get_cell(self, row: int, col: int) -> Symbol:
        return self.grid[row][col]

    def set_cell(self, row: int, col: int, symbol: Symbol):
        self.grid[row][col] = symbol

    def is_empty(self, row: int, col: int) -> bool:
        return self.grid[row][col] == Symbol.EMPTY

    def is_full(self) -> bool:
        return all(
            self.grid[r][c] != Symbol.EMPTY
            for r in range(self.size)
            for c in range(self.size)
        )

    def is_valid_move(self, row: int, col: int) -> bool:
        return (
            0 <= row < self.size
            and 0 <= col < self.size
            and self.is_empty(row, col)
        )

    def check_win(self, symbol: Symbol) -> List[Tuple[int, int]]:
        """Check if the given symbol has a winning line. Returns winning cells
        or empty list."""
        # Directions: horizontal, vertical, two diagonals
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] != symbol:
                    continue
                for dr, dc in directions:
                    cells = [(r, c)]
                    for i in range(1, self.win_length):
                        nr, nc = r + dr * i, c + dc * i
                        if (
                            0 <= nr < self.size
                            and 0 <= nc < self.size
                            and self.grid[nr][nc] == symbol
                        ):
                            cells.append((nr, nc))
                        else:
                            break
                    if len(cells) == self.win_length:
                        return cells
        return []

    def get_empty_cells(self) -> List[Tuple[int, int]]:
        return [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self.is_empty(r, c)
        ]

    def display(self):
        separator = "|" + "---|" * self.size
        print(separator)
        for row in self.grid:
            line = "| " + " | ".join(cell.value for cell in row) + " |"
            print(line)
            print(separator)

    def clone(self) -> "Board":
        new_board = Board(self.size, self.win_length)
        new_board.grid = deepcopy(self.grid)
        return new_board


class Player:
    def __init__(self, name: str, symbol: Symbol):
        self.name = name
        self.symbol = symbol


class HumanPlayer(Player):
    def get_move(self, board: Board) -> Tuple[int, int]:
        while True:
            try:
                move = input(f"{self.name}'s turn ({self.symbol.value}). "
                             "Enter row,col: ")
                r, c = map(int, move.strip().split(","))
                if board.is_valid_move(r, c):
                    return r, c
                print("Invalid move. Try again.")
            except (ValueError, IndexError):
                print("Invalid input. Use format: row,col")


class AIPlayer(Player):
    """AI using minimax with alpha-beta pruning."""

    def __init__(self, name: str, symbol: Symbol, max_depth: int = 10):
        super().__init__(name, symbol)
        self.max_depth = max_depth
        self.opponent_symbol = (
            Symbol.O if symbol == Symbol.X else Symbol.X
        )

    def get_move(self, board: Board) -> Tuple[int, int]:
        best_score = -math.inf
        best_move = board.get_empty_cells()[0]

        for r, c in board.get_empty_cells():
            board.set_cell(r, c, self.symbol)
            score = self._minimax(board, 0, False, -math.inf, math.inf)
            board.set_cell(r, c, Symbol.EMPTY)
            if score > best_score:
                best_score = score
                best_move = (r, c)

        print(f"{self.name} plays at ({best_move[0]},{best_move[1]})")
        return best_move

    def _minimax(self, board: Board, depth: int, is_maximizing: bool,
                 alpha: float, beta: float) -> float:
        # Terminal checks
        if board.check_win(self.symbol):
            return 100 - depth  # prefer faster wins
        if board.check_win(self.opponent_symbol):
            return -100 + depth
        if board.is_full() or depth >= self.max_depth:
            return 0

        if is_maximizing:
            best = -math.inf
            for r, c in board.get_empty_cells():
                board.set_cell(r, c, self.symbol)
                best = max(best, self._minimax(board, depth + 1, False, alpha, beta))
                board.set_cell(r, c, Symbol.EMPTY)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best
        else:
            best = math.inf
            for r, c in board.get_empty_cells():
                board.set_cell(r, c, self.opponent_symbol)
                best = min(best, self._minimax(board, depth + 1, True, alpha, beta))
                board.set_cell(r, c, Symbol.EMPTY)
                beta = min(beta, best)
                if beta <= alpha:
                    break
            return best


class Game:
    def __init__(self, size: int = 3, win_length: int = 3):
        self.board = Board(size, win_length)
        self.players: List[Player] = []
        self.current_player_idx = 0
        self.result = GameResult()
        self.scores = {"X": 0, "O": 0}

    def add_player(self, player: Player):
        self.players.append(player)

    def make_move(self, row: int, col: int):
        current = self.players[self.current_player_idx]
        if not self.board.is_valid_move(row, col):
            raise ValueError(f"Invalid move: ({row}, {col})")

        self.board.set_cell(row, col, current.symbol)
        winning_cells = self.board.check_win(current.symbol)

        if winning_cells:
            self.result.winner = current.name
            self.result.winning_cells = winning_cells
            self.scores[current.symbol.name] += 1
        elif self.board.is_full():
            self.result.is_draw = True
        else:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def is_over(self) -> bool:
        return self.result.is_over

    def get_winner(self) -> Optional[str]:
        return self.result.winner

    def reset(self):
        self.board = Board(self.board.size, self.board.win_length)
        self.current_player_idx = 0
        self.result = GameResult()


def main():
    game = Game(size=3, win_length=3)
    game.add_player(HumanPlayer("Alice", Symbol.X))
    game.add_player(AIPlayer("Computer", Symbol.O))

    while not game.is_over():
        game.board.display()
        current = game.players[game.current_player_idx]
        if isinstance(current, HumanPlayer):
            r, c = current.get_move(game.board)
        else:
            r, c = current.get_move(game.board)
        game.make_move(r, c)

    game.board.display()
    if game.result.winner:
        print(f"Winner: {game.result.winner}!")
    else:
        print("It's a draw!")
    print(f"Scores — X: {game.scores['X']}, O: {game.scores['O']}")


if __name__ == "__main__":
    main()
```

## Win Detection Strategy

The win check iterates over every cell as a potential start of a winning line and checks four directions (horizontal, vertical, two diagonals). For a 3x3 board this is O(N^2) per move, which is fast. For an NxN board with configurable win_length K, the complexity is O(N^2 * K).

**Optimization**: Track the last move and only check lines passing through that cell, reducing to O(K * 4) per move.

## AI: Minimax with Alpha-Beta Pruning

The minimax algorithm evaluates every possible game state as a tree:
- **Maximizing player (AI)**: chooses the move with the highest score
- **Minimizing player (opponent)**: chooses the move with the lowest score
- **Alpha-beta pruning**: cuts branches that cannot affect the final decision, reducing the search tree dramatically

For a 3x3 board, the full game tree has at most 9! = 362,880 nodes — manageable. For 4x4 (16! ≈ 20 trillion), alpha-beta pruning and depth limiting are essential.

## Extensions and Discussion Points

### 1. N x N with Configurable Win Length
Already supported via `Board(size, win_length)`. A 5x5 board with `win_length=4` is a common variant.

### 2. Monte Carlo Tree Search (MCTS)
For larger boards, minimax becomes intractable. MCTS simulates random playouts from each possible move and picks the move with the highest win rate.

### 3. Game History and Undo
Add `MoveHistory` to store `(row, col, symbol)` tuples. Implement `undo_last_move()`.

### 4. Network Multiplayer
Add a `RemotePlayer` that communicates over WebSocket or TCP, serializing moves as JSON.

### 5. GUI Integration
Decouple display from logic — the `Board` is the source of truth. A `Display` interface can have console and GUI implementations.

## Interview Tips

1. **Start with the simplest working version** (3x3, human vs human) then add AI and extensibility
2. **Minimax is often asked as a follow-up** — be ready to explain the algorithm on a whiteboard
3. **Discuss the time complexity** of minimax on N x N boards and how alpha-beta pruning helps
4. **Strategy pattern** for player types (Human, AI, Remote) shows good OOP design
5. **Edge cases**: board full, repeated moves, undo behavior during a game
