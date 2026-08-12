# Chapter 180: Minimax and Alpha-Beta Pruning

## Prerequisites

- Recursion and memoization (Chapter 8)
- Trees and tree traversal (Chapter 13)
- Dynamic programming fundamentals (Chapter 30)
- Game theory basics (Chapter 61)

## Interview Frequency: ★★★

Minimax and alpha-beta pruning appear at **Google**, **Meta**, **Amazon**, and gaming companies. While not as frequent as DP or graph problems, they demonstrate understanding of adversarial search, recursion, and optimization. **Google** has asked variations on tic-tac-toe and connect-four AI. Game AI questions test the ability to model problems as game trees and optimize search — skills directly applicable to decision-making systems.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Minimax algorithm | ★★★ | Google, Meta, Amazon | Medium |
| Alpha-beta pruning | ★★★ | Google, Meta | Medium |
| Evaluation functions | ★★ | Google, gaming companies | Medium-Hard |
| Game tree search | ★★ | Google, Amazon | Medium |
| Iterative deepening | ★★ | Google, competitive programming | Medium |
| Transposition tables | ★★ | Google, advanced interviews | Hard |

---

## 180.1 Minimax Algorithm

### Definition

The **minimax algorithm** is a recursive decision-making strategy for two-player, zero-sum, perfect-information games. It assumes both players play optimally: the maximizing player (MAX) tries to maximize the score, while the minimizing player (MIN) tries to minimize it.

### Motivation

In games like chess, tic-tac-toe, and connect-four:
- Two players alternate turns
- Each game state has a well-defined set of legal moves
- One player's gain is the other's loss (zero-sum)
- Both players have complete information about the game state

We need an algorithm that computes the optimal move for a player, assuming the opponent also plays optimally.

### Intuition

Think of the game as a tree where:
- Each node is a game state
- Each edge is a move
- Leaves are terminal states (win/lose/draw)
- MAX nodes choose the move with the highest value
- MIN nodes choose the move with the lowest value

Minimax evaluates this tree bottom-up, propagating scores from leaves to the root.

### Formal Definition

```
minimax(state, is_maximizing):
    if state is terminal:
        return score(state)
    
    if is_maximizing:
        best = -∞
        for each move in legal_moves(state):
            value = minimax(apply(state, move), false)
            best = max(best, value)
        return best
    else:
        best = +∞
        for each move in legal_moves(state):
            value = minimax(apply(state, move), true)
            best = min(best, value)
        return best
```

### Step-by-Step Walkthrough

Consider a simplified game tree:

```
         MAX
        / | \
       /  |  \
     MIN  MIN  MIN
     /\   /\   /\
    3  5  2  9  0  7
```

**Bottom-up evaluation**:
1. Left MIN node: min(3, 5) = 3
2. Middle MIN node: min(2, 9) = 2
3. Right MIN node: min(0, 7) = 0
4. MAX root: max(3, 2, 0) = 3

**Result**: MAX should choose the left branch, expecting a score of 3.

### Game Tree with Depth 2

```
MAX chooses:     A
               / | \
MIN chooses:  B   C   D
             /\   /\   /\
            3  5 2  9 0  7

Evaluation:
  B = min(3, 5) = 3
  C = min(2, 9) = 2
  D = min(0, 7) = 0
  A = max(3, 2, 0) = 3

Optimal move: A → B (score = 3)
```

### Implementation: Tic-Tac-Toe

#### C++

```cpp
#include <iostream>
#include <vector>
#include <limits>
#include <algorithm>

class TicTacToe {
    std::vector<char> board;  // 'X', 'O', or ' '
    char aiPlayer;
    char humanPlayer;

public:
    TicTacToe(char ai = 'X', char human = 'O')
        : board(9, ' '), aiPlayer(ai), humanPlayer(human) {}

    void setBoard(const std::vector<char>& b) { board = b; }
    void makeMove(int pos, char player) { board[pos] = player; }

    // Check if a player has won
    char checkWinner() const {
        const int lines[8][3] = {
            {0,1,2}, {3,4,5}, {6,7,8},  // rows
            {0,3,6}, {1,4,7}, {2,5,8},  // cols
            {0,4,8}, {2,4,6}             // diagonals
        };
        for (const auto& line : lines) {
            if (board[line[0]] != ' ' &&
                board[line[0]] == board[line[1]] &&
                board[line[1]] == board[line[2]]) {
                return board[line[0]];
            }
        }
        return ' ';  // no winner yet
    }

    bool isBoardFull() const {
        return std::all_of(board.begin(), board.end(),
                           [](char c) { return c != ' '; });
    }

    bool isTerminal() const {
        return checkWinner() != ' ' || isBoardFull();
    }

    // Score from AI's perspective
    int evaluate() const {
        char winner = checkWinner();
        if (winner == aiPlayer) return +10;
        if (winner == humanPlayer) return -10;
        return 0;  // draw or game ongoing
    }

    std::vector<int> getLegalMoves() const {
        std::vector<int> moves;
        for (int i = 0; i < 9; i++) {
            if (board[i] == ' ') moves.push_back(i);
        }
        return moves;
    }

    // === MINIMAX ===
    int minimax(bool isMaximizing, int depth = 0) {
        if (isTerminal()) {
            int score = evaluate();
            // Prefer faster wins, slower losses
            if (score > 0) return score - depth;
            if (score < 0) return score + depth;
            return 0;
        }

        if (isMaximizing) {
            int best = std::numeric_limits<int>::min();
            for (int move : getLegalMoves()) {
                board[move] = aiPlayer;
                best = std::max(best, minimax(false, depth + 1));
                board[move] = ' ';  // undo
            }
            return best;
        } else {
            int best = std::numeric_limits<int>::max();
            for (int move : getLegalMoves()) {
                board[move] = humanPlayer;
                best = std::min(best, minimax(true, depth + 1));
                board[move] = ' ';  // undo
            }
            return best;
        }
    }

    // Find the best move for AI
    int findBestMove() {
        int bestScore = std::numeric_limits<int>::min();
        int bestMove = -1;

        for (int move : getLegalMoves()) {
            board[move] = aiPlayer;
            int score = minimax(false, 0);
            board[move] = ' ';

            if (score > bestScore) {
                bestScore = score;
                bestMove = move;
            }
        }
        return bestMove;
    }

    void printBoard() const {
        for (int i = 0; i < 9; i++) {
            std::cout << (board[i] == ' ? '.' : board[i]);
            if (i % 3 == 2) std::cout << '\n';
            else std::cout << '|';
        }
        std::cout << '\n';
    }
};
```

#### Python

```python
from typing import List, Optional
import math

class TicTacToe:
    """Tic-Tac-Toe with minimax AI."""

    def __init__(self, ai_player: str = 'X', human_player: str = 'O'):
        self.board: List[str] = [' '] * 9
        self.ai_player = ai_player
        self.human_player = human_player

    def check_winner(self) -> Optional[str]:
        """Return the winning player, or None."""
        lines = [
            (0,1,2), (3,4,5), (6,7,8),  # rows
            (0,3,6), (1,4,7), (2,5,8),  # cols
            (0,4,8), (2,4,6)             # diagonals
        ]
        for a, b, c in lines:
            if self.board[a] != ' ' and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    def is_terminal(self) -> bool:
        return self.check_winner() is not None or ' ' not in self.board

    def evaluate(self, depth: int = 0) -> int:
        """Score from AI's perspective. Prefer faster wins."""
        winner = self.check_winner()
        if winner == self.ai_player:
            return 10 - depth
        if winner == self.human_player:
            return depth - 10
        return 0

    def get_legal_moves(self) -> List[int]:
        return [i for i in range(9) if self.board[i] == ' ']

    # --- MINIMAX ---

    def minimax(self, is_maximizing: bool, depth: int = 0) -> int:
        """Pure minimax — explores the entire game tree."""
        if self.is_terminal():
            return self.evaluate(depth)

        if is_maximizing:
            best = -math.inf
            for move in self.get_legal_moves():
                self.board[move] = self.ai_player
                best = max(best, self.minimax(False, depth + 1))
                self.board[move] = ' '
            return best
        else:
            best = math.inf
            for move in self.get_legal_moves():
                self.board[move] = self.human_player
                best = min(best, self.minimax(True, depth + 1))
                self.board[move] = ' '
            return best

    def find_best_move(self) -> int:
        """Find the optimal move for the AI."""
        best_score = -math.inf
        best_move = -1

        for move in self.get_legal_moves():
            self.board[move] = self.ai_player
            score = self.minimax(False, 0)
            self.board[move] = ' '

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def print_board(self):
        for i in range(9):
            ch = self.board[i] if self.board[i] != ' ' else '.'
            print(ch, end='|\n' if i % 3 == 2 else '|')


# --- Demo ---
if __name__ == "__main__":
    game = TicTacToe(ai_player='X', human_player='O')
    # AI goes first — always wins or draws from any position
    move = game.find_best_move()
    print(f"AI chooses position: {move}")
```

#### Java

```java
import java.util.*;

public class TicTacToe {
    private char[] board;
    private char aiPlayer;
    private char humanPlayer;

    public TicTacToe(char ai, char human) {
        this.board = new char[9];
        Arrays.fill(board, ' ');
        this.aiPlayer = ai;
        this.humanPlayer = human;
    }

    public char checkWinner() {
        int[][] lines = {
            {0,1,2}, {3,4,5}, {6,7,8},
            {0,3,6}, {1,4,7}, {2,5,8},
            {0,4,8}, {2,4,6}
        };
        for (int[] line : lines) {
            if (board[line[0]] != ' ' &&
                board[line[0]] == board[line[1]] &&
                board[line[1]] == board[line[2]]) {
                return board[line[0]];
            }
        }
        return ' ';
    }

    public boolean isTerminal() {
        if (checkWinner() != ' ') return true;
        for (char c : board) if (c == ' ') return false;
        return true;
    }

    public int evaluate(int depth) {
        char winner = checkWinner();
        if (winner == aiPlayer) return 10 - depth;
        if (winner == humanPlayer) return depth - 10;
        return 0;
    }

    public List<Integer> getLegalMoves() {
        List<Integer> moves = new ArrayList<>();
        for (int i = 0; i < 9; i++)
            if (board[i] == ' ') moves.add(i);
        return moves;
    }

    // --- MINIMAX ---

    public int minimax(boolean isMaximizing, int depth) {
        if (isTerminal()) return evaluate(depth);

        if (isMaximizing) {
            int best = Integer.MIN_VALUE;
            for (int move : getLegalMoves()) {
                board[move] = aiPlayer;
                best = Math.max(best, minimax(false, depth + 1));
                board[move] = ' ';
            }
            return best;
        } else {
            int best = Integer.MAX_VALUE;
            for (int move : getLegalMoves()) {
                board[move] = humanPlayer;
                best = Math.min(best, minimax(true, depth + 1));
                board[move] = ' ';
            }
            return best;
        }
    }

    public int findBestMove() {
        int bestScore = Integer.MIN_VALUE;
        int bestMove = -1;
        for (int move : getLegalMoves()) {
            board[move] = aiPlayer;
            int score = minimax(false, 0);
            board[move] = ' ';
            if (score > bestScore) {
                bestScore = score;
                bestMove = move;
            }
        }
        return bestMove;
    }
}
```

### Complexity

| Game | Branching Factor b | Depth d | Nodes (minimax) |
|---|---|---|---|
| Tic-Tac-Toe | ~5 (avg) | 9 | ~55,000 |
| Connect Four | ~7 | 42 | ~10^36 (intractable) |
| Chess | ~35 | ~80 | ~10^120 (intractable) |
| Go | ~250 | ~150 | ~10^360 (intractable) |

Pure minimax explores O(b^d) nodes. For any non-trivial game, this is completely infeasible without pruning or depth limits.

---

## 180.2 Alpha-Beta Pruning

### Definition

**Alpha-beta pruning** is an optimization of minimax that eliminates branches that cannot possibly affect the final decision. It maintains two bounds:
- **Alpha (α)**: the best score the maximizer can guarantee (lower bound)
- **Beta (β)**: the best score the minimizer can guarantee (upper bound)

When α ≥ β, the current branch is pruned — it cannot produce a better result than what's already available.

### Motivation

In the minimax tree:

```
         MAX
        / | \
       /  |  \
     MIN  MIN  MIN
     /\   /\   /\
    3  5 2  9  0  7
```

After evaluating the left MIN node (score = 3), the MAX player knows they can guarantee at least 3. When evaluating the middle MIN node, the first child returns 2. Since MIN will choose min(2, ...) ≤ 2, and MAX already has 3, the middle branch is irrelevant — it can never produce a value > 3 for MAX. We can skip the rest of the middle branch.

### Intuition

Alpha-beta pruning is like a race: once you find a path that's clearly better than an alternative, you stop exploring the alternative. The key insight is that you don't need to know the exact value of a branch — you only need to know if it can beat what you already have.

### Algorithm

```
ALPHA-BETA(state, depth, α, β, is_maximizing):
    if state is terminal or depth == 0:
        return evaluate(state)
    
    if is_maximizing:
        value = -∞
        for each move in legal_moves(state):
            value = max(value, ALPHA-BETA(child, depth-1, α, β, false))
            α = max(α, value)
            if α >= β:
                break  // β cutoff
        return value
    else:
        value = +∞
        for each move in legal_moves(state):
            value = min(value, ALPHA-BETA(child, depth-1, α, β, true))
            β = min(β, value)
            if α >= β:
                break  // α cutoff
        return value
```

### Step-by-Step Walkthrough

```
Game tree:
              MAX
           /   |   \
         /     |     \
       MIN    MIN    MIN
       /\     /\     /\
      3  5   2  9   0  7

Alpha-Beta execution (α=-∞, β=+∞ at root):

1. Process left MIN node:
   - Evaluate 3: value = 3
   - Evaluate 5: value = min(3, 5) = 3
   - Return 3 to MAX
   - MAX: α = max(-∞, 3) = 3

2. Process middle MIN node (α=3, β=+∞):
   - Evaluate 2: value = 2
   - β = min(+∞, 2) = 2
   - α (3) >= β (2) → PRUNE! Skip evaluating 9.
   - Return 2 to MAX
   - MAX: α = max(3, 2) = 3

3. Process right MIN node (α=3, β=+∞):
   - Evaluate 0: value = 0
   - β = min(+∞, 0) = 0
   - α (3) >= β (0) → PRUNE! Skip evaluating 7.
   - Return 0 to MAX
   - MAX: α = max(3, 0) = 3

Final result: 3
Nodes evaluated: 4 out of 6 (33% pruned)
```

### Deeper Example with Pruning

```
                    MAX (α=-∞, β=+∞)
                 /         |         \
              /            |            \
        MIN(α=-∞,β=+∞)  MIN(α=3,β=+∞)  MIN(α=3,β=+∞)
         /    \            /    \            /    \
        3      5          2      9          0      7

Step-by-step:

1. Left MIN → evaluates both children (3, 5) → returns 3
   MAX updates α = 3

2. Middle MIN → first child = 2
   MIN: β = min(+∞, 2) = 2
   Check: α(3) ≥ β(2)? YES → PRUNE second child (9)
   Returns 2 to MAX (MAX ignores it since 2 < α=3)

3. Right MIN → first child = 0
   MIN: β = min(+∞, 0) = 0
   Check: α(3) ≥ β(0)? YES → PRUNE second child (7)
   Returns 0 to MAX (MAX ignores it since 0 < α=3)

Result: 3, with 4 nodes evaluated instead of 6.
```

### Implementation

#### C++: Tic-Tac-Toe with Alpha-Beta Pruning

```cpp
#include <iostream>
#include <vector>
#include <limits>
#include <algorithm>

class TicTacToeAlphaBeta {
    std::vector<char> board;
    char aiPlayer, humanPlayer;
    int nodesEvaluated;

public:
    TicTacToeAlphaBeta(char ai = 'X', char human = 'O')
        : board(9, ' '), aiPlayer(ai), humanPlayer(human),
          nodesEvaluated(0) {}

    void setBoard(const std::vector<char>& b) { board = b; }
    void makeMove(int pos, char player) { board[pos] = player; }

    char checkWinner() const {
        const int lines[8][3] = {
            {0,1,2}, {3,4,5}, {6,7,8},
            {0,3,6}, {1,4,7}, {2,5,8},
            {0,4,8}, {2,4,6}
        };
        for (const auto& line : lines) {
            if (board[line[0]] != ' ' &&
                board[line[0]] == board[line[1]] &&
                board[line[1]] == board[line[2]])
                return board[line[0]];
        }
        return ' ';
    }

    bool isBoardFull() const {
        return std::all_of(board.begin(), board.end(),
                           [](char c) { return c != ' '; });
    }
    bool isTerminal() const {
        return checkWinner() != ' ' || isBoardFull();
    }

    int evaluate(int depth) const {
        char w = checkWinner();
        if (w == aiPlayer) return 10 - depth;
        if (w == humanPlayer) return depth - 10;
        return 0;
    }

    std::vector<int> getLegalMoves() const {
        std::vector<int> m;
        for (int i = 0; i < 9; i++)
            if (board[i] == ' ') m.push_back(i);
        return m;
    }

    // --- ALPHA-BETA PRUNING ---
    int alphaBeta(bool isMax, int depth, int alpha, int beta) {
        nodesEvaluated++;

        if (isTerminal()) return evaluate(depth);

        if (isMax) {
            int value = std::numeric_limits<int>::min();
            for (int move : getLegalMoves()) {
                board[move] = aiPlayer;
                value = std::max(value,
                    alphaBeta(false, depth + 1, alpha, beta));
                board[move] = ' ';
                alpha = std::max(alpha, value);
                if (alpha >= beta) break;  // β cutoff
            }
            return value;
        } else {
            int value = std::numeric_limits<int>::max();
            for (int move : getLegalMoves()) {
                board[move] = humanPlayer;
                value = std::min(value,
                    alphaBeta(true, depth + 1, alpha, beta));
                board[move] = ' ';
                beta = std::min(beta, value);
                if (alpha >= beta) break;  // α cutoff
            }
            return value;
        }
    }

    int findBestMove() {
        int bestScore = std::numeric_limits<int>::min();
        int bestMove = -1;
        nodesEvaluated = 0;

        for (int move : getLegalMoves()) {
            board[move] = aiPlayer;
            int score = alphaBeta(false, 0,
                std::numeric_limits<int>::min(),
                std::numeric_limits<int>::max());
            board[move] = ' ';

            if (score > bestScore) {
                bestScore = score;
                bestMove = move;
            }
        }
        return bestMove;
    }

    int getNodesEvaluated() const { return nodesEvaluated; }

    void printBoard() const {
        for (int i = 0; i < 9; i++) {
            std::cout << (board[i] == ' ? '.' : board[i]);
            if (i % 3 == 2) std::cout << '\n';
            else std::cout << '|';
        }
    }
};
```

#### Python: Tic-Tac-Toe with Alpha-Beta Pruning

```python
from typing import List, Optional
import math

class TicTacToeAlphaBeta:
    """Tic-Tac-Toe AI with alpha-beta pruning."""

    def __init__(self, ai_player: str = 'X', human_player: str = 'O'):
        self.board: List[str] = [' '] * 9
        self.ai_player = ai_player
        self.human_player = human_player
        self.nodes_evaluated = 0

    def check_winner(self) -> Optional[str]:
        lines = [
            (0,1,2), (3,4,5), (6,7,8),
            (0,3,6), (1,4,7), (2,5,8),
            (0,4,8), (2,4,6)
        ]
        for a, b, c in lines:
            if self.board[a] != ' ' and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    def is_terminal(self) -> bool:
        return self.check_winner() is not None or ' ' not in self.board

    def evaluate(self, depth: int) -> int:
        winner = self.check_winner()
        if winner == self.ai_player: return 10 - depth
        if winner == self.human_player: return depth - 10
        return 0

    def get_legal_moves(self) -> List[int]:
        return [i for i in range(9) if self.board[i] == ' ']

    # --- ALPHA-BETA ---

    def alpha_beta(
        self, is_maximizing: bool, depth: int,
        alpha: float, beta: float
    ) -> int:
        self.nodes_evaluated += 1

        if self.is_terminal():
            return self.evaluate(depth)

        if is_maximizing:
            value = -math.inf
            for move in self.get_legal_moves():
                self.board[move] = self.ai_player
                value = max(value,
                    self.alpha_beta(False, depth + 1, alpha, beta))
                self.board[move] = ' '
                alpha = max(alpha, value)
                if alpha >= beta:
                    break  # β cutoff
            return value
        else:
            value = math.inf
            for move in self.get_legal_moves():
                self.board[move] = self.human_player
                value = min(value,
                    self.alpha_beta(True, depth + 1, alpha, beta))
                self.board[move] = ' '
                beta = min(beta, value)
                if alpha >= beta:
                    break  # α cutoff
            return value

    def find_best_move(self) -> int:
        best_score = -math.inf
        best_move = -1
        self.nodes_evaluated = 0

        for move in self.get_legal_moves():
            self.board[move] = self.ai_player
            score = self.alpha_beta(
                False, 0, -math.inf, math.inf)
            self.board[move] = ' '

            if score > best_score:
                best_score = score
                best_move = move

        return best_move


# --- Comparison demo ---
def compare_minimax_vs_alphabeta():
    """Show the node count reduction from alpha-beta pruning."""
    import time

    game = TicTacToeAlphaBeta('X', 'O')
    # Empty board — AI picks first move
    start = time.perf_counter()
    move = game.find_best_move()
    elapsed = time.perf_counter() - start
    print(f"Alpha-beta: move={move}, nodes={game.nodes_evaluated}, "
          f"time={elapsed:.4f}s")

    # Compare with a nearly-full board (more constrained)
    game.board = ['X','O','X', 'O','X',' ', ' ','O',' ']
    start = time.perf_counter()
    move = game.find_best_move()
    elapsed = time.perf_counter() - start
    print(f"Late game:  move={move}, nodes={game.nodes_evaluated}, "
          f"time={elapsed:.4f}s")


if __name__ == "__main__":
    compare_minimax_vs_alphabeta()
```

#### Java: Tic-Tac-Toe with Alpha-Beta Pruning

```java
import java.util.*;

public class TicTacToeAlphaBeta {
    private char[] board;
    private char aiPlayer, humanPlayer;
    private int nodesEvaluated;

    public TicTacToeAlphaBeta(char ai, char human) {
        this.board = new char[9];
        Arrays.fill(board, ' ');
        this.aiPlayer = ai;
        this.humanPlayer = human;
    }

    public char checkWinner() {
        int[][] lines = {
            {0,1,2}, {3,4,5}, {6,7,8},
            {0,3,6}, {1,4,7}, {2,5,8},
            {0,4,8}, {2,4,6}
        };
        for (int[] l : lines) {
            if (board[l[0]] != ' ' &&
                board[l[0]] == board[l[1]] &&
                board[l[1]] == board[l[2]])
                return board[l[0]];
        }
        return ' ';
    }

    public boolean isTerminal() {
        if (checkWinner() != ' ') return true;
        for (char c : board) if (c == ' ') return false;
        return true;
    }

    public int evaluate(int depth) {
        char w = checkWinner();
        if (w == aiPlayer) return 10 - depth;
        if (w == humanPlayer) return depth - 10;
        return 0;
    }

    public List<Integer> getLegalMoves() {
        List<Integer> moves = new ArrayList<>();
        for (int i = 0; i < 9; i++)
            if (board[i] == ' ') moves.add(i);
        return moves;
    }

    // --- ALPHA-BETA PRUNING ---

    public int alphaBeta(boolean isMax, int depth, int alpha, int beta) {
        nodesEvaluated++;
        if (isTerminal()) return evaluate(depth);

        if (isMax) {
            int value = Integer.MIN_VALUE;
            for (int move : getLegalMoves()) {
                board[move] = aiPlayer;
                value = Math.max(value,
                    alphaBeta(false, depth + 1, alpha, beta));
                board[move] = ' ';
                alpha = Math.max(alpha, value);
                if (alpha >= beta) break;
            }
            return value;
        } else {
            int value = Integer.MAX_VALUE;
            for (int move : getLegalMoves()) {
                board[move] = humanPlayer;
                value = Math.min(value,
                    alphaBeta(true, depth + 1, alpha, beta));
                board[move] = ' ';
                beta = Math.min(beta, value);
                if (alpha >= beta) break;
            }
            return value;
        }
    }

    public int findBestMove() {
        int bestScore = Integer.MIN_VALUE, bestMove = -1;
        nodesEvaluated = 0;
        for (int move : getLegalMoves()) {
            board[move] = aiPlayer;
            int score = alphaBeta(false, 0,
                Integer.MIN_VALUE, Integer.MAX_VALUE);
            board[move] = ' ';
            if (score > bestScore) {
                bestScore = score;
                bestMove = move;
            }
        }
        return bestMove;
    }
}
```

### Alpha-Beta Pruning Effectiveness

The effectiveness of alpha-beta pruning depends heavily on **move ordering**:

| Move Ordering | Nodes Explored | Speedup |
|---|---|---|
| Worst case (random) | O(b^d) | 1× (no improvement) |
| Best case (optimal) | O(b^(d/2)) | Equivalent to doubling search depth |
| Typical (good heuristic) | O(b^(3d/4)) | Significant improvement |

**Optimal ordering**: If the best move is always examined first, alpha-beta prunes maximally and explores only O(b^(d/2)) nodes — effectively doubling the searchable depth compared to plain minimax.

---

## 180.3 Evaluation Functions

### Definition

An **evaluation function** assigns a numeric score to a non-terminal game state, estimating how favorable it is for one player. It is essential when the game tree is too deep to search completely.

### Design Principles

1. **Fast to compute**: Called millions of times during search
2. **Accurate**: Correlated with actual winning probability
3. **Bounded**: Return values in a known range for proper alpha-beta behavior
4. **Differentiated**: Distinguish between good and bad positions

### Example: Chess Evaluation

```cpp
int evaluateChess(const Board& board) {
    int score = 0;

    // Material (piece values)
    score += 100 * (board.pawns(WHITE) - board.pawns(BLACK));
    score += 300 * (board.knights(WHITE) - board.knights(BLACK));
    score += 300 * (board.bishops(WHITE) - board.bishops(BLACK));
    score += 500 * (board.rooks(WHITE) - board.rooks(BLACK));
    score += 900 * (board.queens(WHITE) - board.queens(BLACK));

    // Positional bonuses
    score += centerControl(board);
    score += kingSafety(board);
    score += pawnStructure(board);

    return score;  // positive = WHITE advantage, negative = BLACK
}
```

### Example: Connect Four Evaluation

```python
def evaluate_connect_four(board, player) -> int:
    score = 0
    opponent = 'O' if player == 'X' else 'X'

    # Center column preference
    center_col = len(board[0]) // 2
    center_count = sum(1 for row in board if row[center_col] == player)
    score += center_count * 3

    # Count windows of 4
    for window in get_all_windows(board):
        score += evaluate_window(window, player, opponent)

    return score

def evaluate_window(window, player, opponent) -> int:
    score = 0
    p_count = window.count(player)
    o_count = window.count(opponent)
    empty = window.count(' ')

    if p_count == 4: score += 100
    elif p_count == 3 and empty == 1: score += 5
    elif p_count == 2 and empty == 2: score += 2

    if o_count == 3 and empty == 1: score -= 4  # block opponent

    return score
```

---

## 180.4 Advanced Techniques

### Iterative Deepening

Search to depth 1, then depth 2, etc. This ensures you always have a best move ready (useful with time limits) and dramatically improves alpha-beta pruning when combined with move ordering from shallower searches.

```cpp
int iterativeDeepening(Board& board, int maxDepth, int timeLimit) {
    int bestMove = -1;
    auto start = std::chrono::steady_clock::now();

    for (int depth = 1; depth <= maxDepth; depth++) {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - start).count();
        if (elapsed > timeLimit * 0.8) break;  // stop if ~80% time used

        // Use previous iteration's best move for ordering
        int score = alphaBeta(board, depth, INT_MIN, INT_MAX, true, &bestMove);
    }
    return bestMove;
}
```

### Transposition Table

Store evaluated positions in a hash table to avoid re-evaluating the same state reached via different move sequences.

```cpp
struct TTEntry {
    uint64_t hash;
    int depth;
    int score;
    enum { EXACT, LOWER, UPPER } flag;
};

std::unordered_map<uint64_t, TTEntry> transpositionTable;

int alphaBetaWithTT(Board& board, int depth, int alpha, int beta, bool isMax) {
    uint64_t hash = board.zobristHash();

    // Check transposition table
    auto it = transpositionTable.find(hash);
    if (it != transpositionTable.end() && it->second.depth >= depth) {
        const auto& entry = it->second;
        if (entry.flag == TTEntry::EXACT) return entry.score;
        if (entry.flag == TTEntry::LOWER) alpha = std::max(alpha, entry.score);
        if (entry.flag == TTEntry::UPPER) beta = std::min(beta, entry.score);
        if (alpha >= beta) return entry.score;
    }

    // ... normal alpha-beta search ...

    // Store in transposition table
    TTEntry entry;
    entry.hash = hash;
    entry.depth = depth;
    entry.score = value;
    if (value <= origAlpha) entry.flag = TTEntry::UPPER;
    else if (value >= origBeta) entry.flag = TTEntry::LOWER;
    else entry.flag = TTEntry::EXACT;
    transpositionTable[hash] = entry;

    return value;
}
```

### Move Ordering Heuristics

Better move ordering = more pruning. Common heuristics:

1. **Capture moves first**: Often lead to high-value positions
2. **Killer moves**: Moves that caused cutoffs at the same depth in sibling nodes
3. **History heuristic**: Track which moves have been good historically
4. **MVV-LVA** (Most Valuable Victim – Least Valuable Attacker): For captures in chess

```cpp
std::vector<int> orderedMoves(const Board& board) {
    auto moves = board.getLegalMoves();

    std::sort(moves.begin(), moves.end(), [&](int a, int b) {
        int scoreA = moveScore(board, a);
        int scoreB = moveScore(board, b);
        return scoreA > scoreB;
    });

    return moves;
}

int moveScore(const Board& board, int move) {
    int score = 0;
    if (board.isCapture(move)) {
        score += 10000 + MVVLVA(board, move);  // captures first
    }
    if (isKillerMove(move, board.ply())) {
        score += 9000;
    }
    score += historyScore(move);
    return score;
}
```

---

## 180.5 Dry Run: Complete Alpha-Beta Example

### Game Tree

```
Consider this game tree (MAX at root):

              MAX
           /       \
        MIN          MIN
       /    \       /    \
      MAX    MAX   MAX    MAX
     / \    / \   / \    / \
    5   3  6   2  7   1  4   8
```

### Alpha-Beta Execution

```
Root: α=-∞, β=+∞

1. Left MIN → α=-∞, β=+∞
   1a. Left MAX → α=-∞, β=+∞
       - Evaluate 5: value=5, α=5
       - Evaluate 3: value=max(5,3)=5
       - Return 5 to MIN
   1b. Right MAX → α=-∞, β=5
       - Evaluate 6: value=6, α=6
       - α(6) ≥ β(5)? YES → PRUNE 2!
       - Return 6 to MIN
   MIN returns min(5, 6) = 5
   Root: α = max(-∞, 5) = 5

2. Right MIN → α=5, β=+∞
   2a. Left MAX → α=5, β=+∞
       - Evaluate 7: value=7, α=7
       - α(7) ≥ β(+∞)? NO
       - Evaluate 1: value=max(7,1)=7
       - Return 7 to MIN
   2b. Right MAX → α=5, β=7
       - Evaluate 4: value=4, α=4
       - α(4) ≥ β(7)? NO
       - Evaluate 8: value=max(4,8)=8, α=8
       - α(8) ≥ β(7)? YES → cutoff (but all children explored)
       - Return 8 to MIN
   MIN returns min(7, 8) = 7
   Root: α = max(5, 7) = 7

Final answer: 7
Pruned: 1 node (value 2)
```

---

## 180.6 Interview Questions

### Classic Problems

1. **Tic-Tac-Toe AI**: Implement a perfect tic-tac-toe player using minimax with alpha-beta pruning. Discuss complexity reduction.

2. **Connect Four**: Given a Connect Four board and a depth limit, find the best move using minimax with an evaluation function.

3. **Nim Game (LeetCode 292)**: Determine if the first player can win given n stones (take 1-3 per turn). This is minimax with a simple evaluation.

4. **Can I Win (LeetCode 464)**: Two players pick numbers from 1 to maxChoosableInteger. The player who causes the running total to reach or exceed desiredTotal wins. Use minimax with memoization.

5. **Predict the Winner (LeetCode 486)**: Given an array of scores, two players alternately pick from either end. Determine if the first player can win. Minimax or DP.

6. **Stone Game (LeetCode 877)**: Similar to Predict the Winner but with specific constraints. Can be solved with minimax or mathematically proven.

### Follow-Up Questions

- **"When would you use minimax vs. DP?"**: Minimax for adversarial games with alternating players. DP for optimization problems without an opponent.
- **"How does alpha-beta pruning affect correctness?"**: It doesn't — the result is identical to minimax. Only the search path changes.
- **"What if you can't search to the end?"**: Use an evaluation function + depth limit. The evaluation estimates the position's value.
- **"How do you handle games with randomness (dice)?"**: Use expectimax instead of minimax — average over random outcomes instead of min/max.
- **"What is iterative deepening and why use it?"**: Search depth 1, 2, 3, ... in sequence. Guarantees a best move at any time cutoff and improves move ordering for alpha-beta.

---

## 180.7 Exercises

1. **Implement Connect Four AI**: Build a Connect Four game with minimax + alpha-beta. Use an evaluation function that considers:
   - Number of 2-in-a-row and 3-in-a-row patterns
   - Center column preference
   - Blocking opponent's winning threats

2. **Compare pruning effectiveness**: Modify the tic-tac-toe implementation to count nodes with and without alpha-beta pruning. Report the speedup ratio for various board states.

3. **Expectimax for stochastic games**: Extend the minimax implementation to handle games with chance nodes (e.g., a coin flip determines which player moves next). Replace `min`/`max` with `average` for chance nodes.

4. **Evaluation function tuning**: For Connect Four, create three different evaluation functions of increasing sophistication. Test each against the others in a round-robin tournament.

5. **Transposition table**: Add a transposition table (Zobrist hashing) to the alpha-beta implementation. Measure the reduction in nodes evaluated for repeated positions.

6. **Monte Carlo Tree Search (MCTS)**: Research and implement MCTS for tic-tac-toe. Compare its play strength and node count against minimax + alpha-beta.

---

## 180.8 Cross-References

- **Chapter 8 (Recursion)**: Minimax is inherently recursive — understanding recursion is essential.
- **Chapter 13 (Trees)**: Game trees are a direct application of tree data structures.
- **Chapter 30 (DP Fundamentals)**: Many game problems can be solved with either minimax or DP with memoization.
- **Chapter 61 (Game Theory)**: Broader context for combinatorial games and optimal strategies.
- **Chapter 132 (IDA* and Beam Search)**: Related search strategies for game trees.
- **Chapter 133 (Branch and Bound)**: Another pruning technique for search trees.
- **Chapter 162 (Algorithmic Game Theory)**: Advanced topics including Nash equilibria and mechanism design.
