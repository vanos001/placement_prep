# Chess — Machine Coding Problem

## Problem Statement

Design a chess game engine that enforces all standard movement rules for each piece, detects check, checkmate, and stalemate, manages turn-based play, and supports castling, en passant, and pawn promotion. The design must be extensible for new piece types or game variants.

## Requirements Gathering

### Functional Requirements
1. Standard 8x8 board with 32 pieces in starting position
2. Turn-based movement (white moves first)
3. Movement validation for all six piece types
4. Check detection — king under attack
5. Checkmate detection — no legal moves to escape check
6. Stalemate detection — no legal moves but not in check
7. Special moves: castling (kingside/queenside), en passant, pawn promotion
8. Move history with undo capability
9. Board display with algebraic notation

### Non-Functional Requirements
- Extensible piece behavior (Strategy pattern for movement rules)
- Clean separation between board state, move validation, and display
- Efficient move generation for future AI integration

### Clarifying Questions
- "Should the engine support AI, or is it purely a validation engine?"
- "Are we implementing all FIDE rules (50-move rule, threefold repetition, insufficient material)?"
- "Should pawn promotion default to queen, or should the player choose?"
- "Is en passant required?"

## Class Design

### Entity Identification
```
Nouns: Board, Piece, King, Queen, Rook, Bishop, Knight, Pawn,
       Color, Position, Move, MoveValidator, GameState, MoveHistory
```

### Class Diagram

```
┌──────────────────────┐
│        Game           │
├──────────────────────┤
│ - board: Board        │
│ - currentTurn: Color  │
│ - moveHistory: List   │
│ - state: GameState    │
├──────────────────────┤
│ + makeMove(from, to)  │
│ + isValidMove(f, t)   │
│ + isCheck(color):bool│
│ + isCheckmate(): bool│
│ + isStalemate(): bool│
│ + undoLastMove()     │
│ + getBoard()          │
└───────────┬───────────┘
            │
            ▼
┌──────────────────────┐
│       Board           │
├──────────────────────┤
│ - grid: Piece[][]   │
│ - enPassantTarget    │
│ - castlingRights     │
├──────────────────────┤
│ + getPiece(pos)      │
│ + setPiece(pos, piece)│
│ + removePiece(pos)   │
│ + findKing(color)    │
│ + isInBounds(pos)    │
│ + isAttackedBy(pos, color)│
└──────────────────────┘

         ▲
         │ has many
         │
┌──────────────────────┐
│  Piece (Abstract)     │
├──────────────────────┤
│ - color: Color        │
│ - hasMoved: bool     │
├──────────────────────┤
│ + getValidMoves(pos, board): List<Position>
│ + canAttack(pos, target, board): bool
└───────────┬──────────┘
     ┌──────┼──────┬──────────┬────────┬──────────┐
     ▼      ▼      ▼          ▼        ▼          ▼
┌─────┐┌─────┐┌─────┐┌─────┐┌──────┐┌──────┐
│King ││Queen││Rook ││Bishop││Knight││Pawn │
└─────┘└─────┘└─────┘└─────┘└──────┘└──────┘

┌──────────────────────┐
│   Color (Enum)        │
├──────────────────────┤
│ WHITE, BLACK          │
└──────────────────────┘

┌──────────────────────┐
│    Position           │
├──────────────────────┤
│ - row: int (0-7)      │
│ - col: int (0-7)      │
├──────────────────────┤
│ + toAlgebraic(): str │
│ + fromAlgebraic(s)   │
└──────────────────────┘
```

## Move Validation Strategy

Each piece subclass implements `getValidMoves()`, returning a list of candidate squares. The Game class then **filters** this list to remove moves that would leave the player's own king in check.

```
Raw moves from piece → Filter: own king in check? → Legal moves
```

This two-layer approach keeps piece logic simple and centralizes check validation.

## Implementation

### Python Implementation

```python
from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass
from copy import deepcopy


class Color(Enum):
    WHITE = "W"
    BLACK = "B"

    def opponent(self):
        return Color.BLACK if self == Color.WHITE else Color.WHITE


@dataclass(frozen=True)
class Position:
    row: int  # 0 = rank 8, 7 = rank 1
    col: int  # 0 = file a, 7 = file h

    def to_algebraic(self) -> str:
        return chr(ord('a') + self.col) + str(8 - self.row)

    @staticmethod
    def from_algebraic(s: str) -> "Position":
        col = ord(s[0]) - ord('a')
        row = 8 - int(s[1])
        return Position(row, col)

    def offset(self, dr: int, dc: int) -> "Position":
        return Position(self.row + dr, self.col + dc)

    def in_bounds(self) -> bool:
        return 0 <= self.row < 8 and 0 <= self.col < 8


class Piece:
    def __init__(self, color: Color):
        self.color = color
        self.has_moved = False

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        raise NotImplementedError

    def can_attack(self, pos: Position, target: Position,
                    board: "Board") -> bool:
        """Can this piece attack the target square? Used for check detection."""
        return target in self.get_valid_moves(pos, board)

    def __repr__(self):
        return f"{self.color.value}{self.symbol}"


class King(Piece):
    symbol = "K"

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                target = pos.offset(dr, dc)
                if not target.in_bounds():
                    continue
                piece = board.get_piece(target)
                if piece is None or piece.color != self.color:
                    moves.append(target)
        return moves

    def get_castling_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        if self.has_moved:
            return moves
        if board.is_in_check(self.color):
            return moves
        row = 0 if self.color == Color.WHITE else 7
        # Kingside: e1→g1 (col 4→6)
        rook_pos = Position(row, 7)
        rook = board.get_piece(rook_pos)
        if isinstance(rook, Rook) and not rook.has_moved:
            if (board.get_piece(Position(row, 5)) is None
                    and board.get_piece(Position(row, 6)) is None):
                if (not board.is_square_attacked(Position(row, 4), self.color.opponent())
                        and not board.is_square_attacked(Position(row, 5), self.color.opponent())
                        and not board.is_square_attacked(Position(row, 6), self.color.opponent())):
                    moves.append(Position(row, 6))
        # Queenside: e1→c1 (col 4→2)
        rook_pos = Position(row, 0)
        rook = board.get_piece(rook_pos)
        if isinstance(rook, Rook) and not rook.has_moved:
            if (board.get_piece(Position(row, 1)) is None
                    and board.get_piece(Position(row, 2)) is None
                    and board.get_piece(Position(row, 3)) is None):
                if (not board.is_square_attacked(Position(row, 2), self.color.opponent())
                        and not board.is_square_attacked(Position(row, 3), self.color.opponent())
                        and not board.is_square_attacked(Position(row, 4), self.color.opponent())):
                    moves.append(Position(row, 2))
        return moves


class Queen(Piece):
    symbol = "Q"

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1),
                        (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            for dist in range(1, 8):
                target = pos.offset(dr * dist, dc * dist)
                if not target.in_bounds():
                    break
                piece = board.get_piece(target)
                if piece is None:
                    moves.append(target)
                elif piece.color != self.color:
                    moves.append(target)
                    break
                else:
                    break
        return moves


class Rook(Piece):
    symbol = "R"

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            for dist in range(1, 8):
                target = pos.offset(dr * dist, dc * dist)
                if not target.in_bounds():
                    break
                piece = board.get_piece(target)
                if piece is None:
                    moves.append(target)
                elif piece.color != self.color:
                    moves.append(target)
                    break
                else:
                    break
        return moves


class Bishop(Piece):
    symbol = "B"

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            for dist in range(1, 8):
                target = pos.offset(dr * dist, dc * dist)
                if not target.in_bounds():
                    break
                piece = board.get_piece(target)
                if piece is None:
                    moves.append(target)
                elif piece.color != self.color:
                    moves.append(target)
                    break
                else:
                    break
        return moves


class Knight(Piece):
    symbol = "N"

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                        (1, -2), (1, 2), (2, -1), (2, 1)]:
            target = pos.offset(dr, dc)
            if not target.in_bounds():
                continue
            piece = board.get_piece(target)
            if piece is None or piece.color != self.color:
                moves.append(target)
        return moves


class Pawn(Piece):
    symbol = "P"

    def get_valid_moves(self, pos: Position, board: "Board") -> List[Position]:
        moves = []
        direction = -1 if self.color == Color.WHITE else 1
        start_row = 6 if self.color == Color.WHITE else 1
        # Forward one
        fwd = pos.offset(direction, 0)
        if fwd.in_bounds() and board.get_piece(fwd) is None:
            moves.append(fwd)
            # Forward two from start
            if pos.row == start_row:
                fwd2 = pos.offset(direction * 2, 0)
                if board.get_piece(fwd2) is None:
                    moves.append(fwd2)
        # Captures (diagonal)
        for dc in [-1, 1]:
            target = pos.offset(direction, dc)
            if not target.in_bounds():
                continue
            piece = board.get_piece(target)
            if piece and piece.color != self.color:
                moves.append(target)
            # En passant
            if board.en_passant_target == target:
                moves.append(target)
        return moves


class Board:
    def __init__(self):
        self.grid = [[None] * 8 for _ in range(8)]
        self.en_passant_target: Optional[Position] = None
        self._setup_initial()

    def _setup_initial(self):
        order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col in range(8):
            self.grid[0][col] = order[col](Color.BLACK)
            self.grid[1][col] = Pawn(Color.BLACK)
            self.grid[6][col] = Pawn(Color.WHITE)
            self.grid[7][col] = order[col](Color.WHITE)

    def get_piece(self, pos: Position) -> Optional[Piece]:
        return self.grid[pos.row][pos.col]

    def set_piece(self, pos: Position, piece: Optional[Piece]):
        self.grid[pos.row][pos.col] = piece

    def find_king(self, color: Color) -> Position:
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if isinstance(piece, King) and piece.color == color:
                    return Position(r, c)
        raise RuntimeError(f"{color} king not found")

    def is_square_attacked(self, pos: Position, by_color: Color) -> bool:
        """Check if a square is under attack by the given color."""
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece and piece.color == by_color:
                    if not isinstance(piece, Pawn):
                        if pos in piece.get_valid_moves(Position(r, c), self):
                            return True
                    else:
                        # Pawn attacks diagonally only
                        direction = -1 if piece.color == Color.WHITE else 1
                        attacker_pos = Position(r, c)
                        for dc in [-1, 1]:
                            if attacker_pos.offset(direction, dc) == pos:
                                return True
        return False

    def is_in_check(self, color: Color) -> bool:
        king_pos = self.find_king(color)
        return self.is_square_attacked(king_pos, color.opponent())

    def clone(self) -> "Board":
        new = Board.__new__(Board)
        new.grid = [[p if not isinstance(p, Piece) else
                      type(p)(p.color) for p in row] for row in self.grid]
        new.en_passant_target = self.en_passant_target
        return new

    def display(self):
        print("   a  b  c  d  e  f  g  h")
        for r in range(8):
            rank = str(8 - r)
            line = f"{rank} "
            for c in range(8):
                piece = self.grid[r][c]
                token = str(piece) if piece else " . "
                line += token + " "
            print(line)
        print()


class Move:
    def __init__(self, piece: Piece, from_pos: Position, to_pos: Position,
                 captured: Optional[Piece] = None, is_castle: bool = False,
                 is_en_passant: bool = False, promotion: Optional[Piece] = None,
                 old_en_passant: Optional[Position] = None):
        self.piece = piece
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.captured = captured
        self.is_castle = is_castle
        self.is_en_passant = is_en_passant
        self.promotion = promotion
        self.old_en_passant = old_en_passant


class Game:
    def __init__(self):
        self.board = Board()
        self.current_turn = Color.WHITE
        self.move_history: List[Move] = []
        self.game_over = False
        self.result: Optional[str] = None

    def get_legal_moves(self, pos: Position) -> List[Position]:
        piece = self.board.get_piece(pos)
        if not piece or piece.color != self.current_turn:
            return []

        raw_moves = piece.get_valid_moves(pos, self.board)

        # Add castling moves for king
        if isinstance(piece, King):
            raw_moves.extend(piece.get_castling_moves(pos, self.board))

        # Filter moves that leave own king in check
        legal = []
        for target in raw_moves:
            if not self._would_be_in_check(pos, target, piece.color):
                legal.append(target)
        return legal

    def _would_be_in_check(self, from_pos: Position, to_pos: Position,
                           color: Color) -> bool:
        """Simulate the move and check if own king is in check."""
        saved_board = self.board.clone()
        # Execute move on clone
        piece = saved_board.get_piece(from_pos)
        saved_board.set_piece(from_pos, None)
        saved_board.set_piece(to_pos, piece)
        return saved_board.is_in_check(color)

    def make_move(self, from_algebraic: str, to_algebraic: str,
                  promotion_char: str = None) -> bool:
        from_pos = Position.from_algebraic(from_algebraic)
        to_pos = Position.from_algebraic(to_algebraic)
        legal = self.get_legal_moves(from_pos)
        if to_pos not in legal:
            return False

        piece = self.board.get_piece(from_pos)
        captured = self.board.get_piece(to_pos)
        is_ep = False

        # En passant detection
        if isinstance(piece, Pawn) and to_pos == self.board.en_passant_target:
            is_ep = True
            captured_pos = Position(from_pos.row, to_pos.col)
            captured = self.board.get_piece(captured_pos)
            self.board.set_piece(captured_pos, None)

        old_ep = self.board.en_passant_target
        self.board.en_passant_target = None

        # Set en passant target for opponent
        if isinstance(piece, Pawn) and abs(to_pos.row - from_pos.row) == 2:
            ep_row = (from_pos.row + to_pos.row) // 2
            self.board.en_passant_target = Position(ep_row, from_pos.col)

        move = Move(piece, from_pos, to_pos, captured, is_en_passant=is_ep,
                    old_en_passant=old_ep)
        self.board.set_piece(from_pos, None)
        self.board.set_piece(to_pos, piece)
        piece.has_moved = True

        # Pawn promotion
        if isinstance(piece, Pawn) and to_pos.row in (0, 7):
            promo_map = {'Q': Queen, 'R': Rook, 'B': Bishop, 'N': Knight}
            promo_class = promo_map.get(promotion_char or 'Q', Queen)
            promoted = promo_class(piece.color)
            move.promotion = promoted
            self.board.set_piece(to_pos, promoted)

        self.move_history.append(move)
        self.current_turn = self.current_turn.opponent()
        self._check_game_state()
        return True

    def _check_game_state(self):
        # Check if the new current player has any legal moves
        has_legal = False
        for r in range(8):
            for c in range(8):
                p = self.board.get_piece(Position(r, c))
                if p and p.color == self.current_turn:
                    if self.get_legal_moves(Position(r, c)):
                        has_legal = True
                        break
            if has_legal:
                break

        if not has_legal:
            self.game_over = True
            if self.board.is_in_check(self.current_turn):
                self.result = f"Checkmate! {self.current_turn.opponent().value} wins!"
            else:
                self.result = "Stalemate — Draw!"

    def display(self):
        self.board.display()
        if self.board.is_in_check(self.current_turn):
            print(f"{self.current_turn.value} is in CHECK!")
        print(f"Turn: {self.current_turn.value}")


def main():
    game = Game()
    print("Chess Engine — Enter moves in algebraic notation (e.g., e2 e4)")
    print("For promotion, add piece: e7 e8 Q")
    game.display()

    while not game.game_over:
        try:
            parts = input(f"{game.current_turn.value} move: ").strip().split()
            if len(parts) < 2:
                continue
            promo = parts[2] if len(parts) > 2 else None
            success = game.make_move(parts[0], parts[1], promo)
            if not success:
                print("Illegal move. Try again.")
            game.display()
        except (ValueError, IndexError):
            print("Invalid input.")

    print(game.result)


if __name__ == "__main__":
    main()
```

## Check and Checkmate Detection

**Check**: After each move, check if the opponent's king is attacked by any piece of the current player.

**Checkmate**: The opponent is in check AND has zero legal moves (every possible move leaves the king in check).

**Stalemate**: The opponent is NOT in check but has zero legal moves.

The implementation simulates each candidate move on a board clone, then checks if the king is in check — this is the most straightforward approach and sufficient for interview purposes.

## Complexity Analysis

| Operation | Time Complexity |
|-----------|----------------|
| Generate raw moves for a piece | O(N) where N depends on piece (max 27 for queen) |
| Check detection | O(P) per move, where P = total pieces on board |
| Checkmate detection | O(P * M) per turn, where M = avg moves per piece |
| Full game state check | O(P * M) per turn |

## Extensions and Discussion Points

### 1. AI Integration
Add a `Player` interface with `getMove()` method. Implement `MinimaxPlayer` and `StockfishPlayer` (wrapping the Stockfish engine via UCI protocol).

### 2. Move Notation (PGN/Algebraic)
Implement standard algebraic notation: `Nf3`, `Bxe5`, `O-O` (castling), `e8=Q` (promotion).

### 3. FIDE Rules
50-move rule, threefold repetition, insufficient material (K vs K, K+B vs K, K+N vs K).

### 4. Board Evaluation
Material count, piece-square tables, mobility, king safety — building blocks for an AI.

### 5. Undo with Full State Restoration
Each `Move` stores enough information to fully reverse: captured piece, old en passant target, castling rights.

## Interview Tips

1. **Start with core movement for 2-3 pieces** (pawn, rook, king) and expand from there
2. **Check filtering is the trickiest part** — simulate moves on a clone and verify
3. **Castling has the most rules** — king/rook unmoved, no pieces between, not through/into check
4. **Discuss trade-offs**: simulating on clone is O(1) space per check but adds overhead; alternative is make/unmake with a single board
5. **Pawn has the most special rules**: two-square first move, en passant, diagonal capture, promotion — handle these carefully
