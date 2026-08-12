# Chapter 61: Game Theory for Interviews

## Prerequisites

- XOR properties
- Recursion and memoization
- Basic graph theory (for game on graphs)
- Dynamic programming fundamentals

## Interview Frequency: ★★

Game theory appears in interviews at **Google**, **Meta**, **Two Sigma**, and **Jane Street**. While not as frequent as standard DP, it's a differentiating skill. **Google** has asked Nim variants and game DP. **Two Sigma** and **Jane Street** love probabilistic game theory. Understanding Grundy numbers helps solve many seemingly unrelated problems.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Nim Game | ★★★ | Google, Meta | Easy-Medium |
| Grundy Numbers | ★★ | Google, competitive programming | Medium |
| Sprague-Grundy Theorem | ★★ | Google, advanced interviews | Hard |
| Game on Graphs | ★★★ | Google, Meta | Medium |
| Combinatorial Games | ★★ | Two Sigma, Jane Street | Medium-Hard |

---

## 61.1 Impartial Games

An **impartial game** is a two-player game where:
- Both players have the same moves available from any position
- The only difference between players is who moves first
- The game ends in finite time
- The last player to move wins (**normal play convention**)

Examples: Nim, subtraction games, turning turtles, many puzzle games.

Non-examples: Chess (different pieces for each player), checkers (same pieces but different roles).

### Normal Play vs Misère Play

| Convention | Winning Condition | Analysis |
|---|---|---|
| Normal play | Last player to move wins | Standard Sprague-Grundy |
| Misère play | Last player to move loses | Modified analysis needed |

---

## 61.2 Nim Game

### The Game

There are several piles of stones. Players alternate turns. On each turn, a player removes one or more stones from a single pile. The player who takes the last stone wins.

### The XOR Strategy

**Theorem**: The first player has a winning strategy if and only if the XOR of all pile sizes is non-zero.

```
Position is losing (P-position) iff a₁ ⊕ a₂ ⊕ ... ⊕ aₙ = 0
Position is winning (N-position) iff a₁ ⊕ a₂ ⊕ ... ⊕ aₙ ≠ 0
```

### Proof by Induction

**Base case**: All piles empty → XOR = 0 → losing position ✓

**Inductive step**: 
1. If XOR = 0: Any move changes one pile, making XOR ≠ 0 (opponent gets N-position)
2. If XOR ≠ 0: Can always make a move to make XOR = 0 (give opponent P-position)

For case 2: Let `s = a₁ ⊕ ... ⊕ aₙ`. Find the highest bit of `s`. There exists a pile `aᵢ` with that bit set. Reducing `aᵢ` to `aᵢ ⊕ s` makes the new XOR zero.

```cpp
#include <iostream>
#include <vector>
#include <numeric>

class NimGame {
    std::vector<int> piles;
    
public:
    NimGame(std::vector<int> p) : piles(p) {}
    
    bool isFirstPlayerWin() {
        int xorSum = 0;
        for (int p : piles) xorSum ^= p;
        return xorSum != 0;
    }
    
    // Find the winning move (pile index, stones to remove)
    // Returns {-1, -1} if no winning move
    std::pair<int, int> winningMove() {
        int xorSum = 0;
        for (int p : piles) xorSum ^= p;
        
        if (xorSum == 0) return {-1, -1}; // Losing position
        
        for (int i = 0; i < (int)piles.size(); i++) {
            int target = piles[i] ^ xorSum;
            if (target < piles[i]) {
                return {i, piles[i] - target};
            }
        }
        
        return {-1, -1}; // Should not reach here
    }
    
    void printState() {
        std::cout << "Piles: ";
        int xorSum = 0;
        for (int p : piles) {
            std::cout << p << " ";
            xorSum ^= p;
        }
        std::cout << "(XOR = " << xorSum << ")\n";
    }
};

int main() {
    NimGame game({3, 5, 7});
    game.printState();
    
    if (game.isFirstPlayerWin()) {
        auto [pile, remove] = game.winningMove();
        std::cout << "First player wins! Remove " << remove 
                  << " from pile " << pile << "\n";
    } else {
        std::cout << "Second player wins!\n";
    }
    
    // Simulate a game
    std::cout << "\nSimulating game:\n";
    NimGame sim({3, 5, 7});
    sim.printState();
    
    for (int turn = 0; turn < 10 && sim.isFirstPlayerWin(); turn++) {
        auto [pile, remove] = sim.winningMove();
        if (pile == -1) break;
        std::cout << "Player " << (turn % 2 + 1) << " removes " << remove 
                  << " from pile " << pile << "\n";
        // Actually make the move (simplified)
        break; // Just show the first move
    }
    
    return 0;
}
```

### Nim Variants

| Variant | Rule Change | Winning Condition |
|---|---|---|
| Standard Nim | Remove any from one pile | XOR ≠ 0 |
| Misère Nim | Last to move loses | XOR ≠ 0 (except all ≤ 1) |
| Subtraction Nim | Can only remove 1..k stones | XOR of Grundy numbers |
| Wythoff's Game | Two piles, remove from both equally | Golden ratio positions |

---

## 61.3 Grundy Numbers (Sprague-Grundy Numbers)

### The mex Function

The **minimum excludant** (mex) of a set S is the smallest non-negative integer not in S.

```
mex({0, 1, 3}) = 2
mex({1, 2, 3}) = 0
mex({}) = 0
mex({0, 1, 2}) = 3
```

### Grundy Number Definition

For any position p in an impartial game:

```
G(p) = mex({ G(q) : q is reachable from p })
```

Base case: Terminal positions have G = 0 (no moves available).

### Key Properties

1. G(p) = 0 if and only if p is a losing position (P-position)
2. G(p) ≠ 0 if and only if p is a winning position (N-position)
3. For a game composed of independent subgames, the Grundy number is the XOR of individual Grundy numbers

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <cstring>

// Compute Grundy number for subtraction game
// Players can remove 1, 2, or 3 stones
int grundySubtraction(int n) {
    std::vector<int> g(n + 1, 0);
    std::vector<int> moves = {1, 2, 3};
    
    for (int i = 1; i <= n; i++) {
        std::set<int> reachable;
        for (int m : moves) {
            if (m <= i) reachable.insert(g[i - m]);
        }
        
        int mex = 0;
        while (reachable.count(mex)) mex++;
        g[i] = mex;
    }
    
    return g[n];
}

// Grundy number for general subtraction game with custom moves
std::vector<int> grundyGeneral(const std::vector<int>& moves, int maxN) {
    std::vector<int> g(maxN + 1, 0);
    
    for (int i = 1; i <= maxN; i++) {
        std::set<int> reachable;
        for (int m : moves) {
            if (m <= i) reachable.insert(g[i - m]);
        }
        
        int mex = 0;
        while (reachable.count(mex)) mex++;
        g[i] = mex;
    }
    
    return g;
}

int main() {
    // Subtraction game: remove 1, 2, or 3
    std::cout << "Grundy numbers (subtraction {1,2,3}):\n";
    for (int i = 0; i <= 15; i++) {
        std::cout << "G(" << i << ") = " << grundySubtraction(i) << "\n";
    }
    
    // Custom moves: remove 1 or 4
    auto g = grundyGeneral({1, 4}, 15);
    std::cout << "\nGrundy numbers (subtraction {1,4}):\n";
    for (int i = 0; i <= 15; i++) {
        std::cout << "G(" << i << ") = " << g[i] << "\n";
    }
    
    // Multi-pile game: XOR of Grundy numbers
    std::vector<int> piles = {5, 3, 8};
    int xorSum = 0;
    std::cout << "\nMulti-pile subtraction {1,2,3}:\n";
    for (int p : piles) {
        int gp = grundySubtraction(p);
        std::cout << "  G(" << p << ") = " << gp << "\n";
        xorSum ^= gp;
    }
    std::cout << "XOR of Grundy numbers: " << xorSum << "\n";
    std::cout << (xorSum ? "First" : "Second") << " player wins.\n";
    
    return 0;
}
```

---

## 61.4 Sprague-Grundy Theorem

### Statement

**Every impartial game under normal play is equivalent to a Nim pile.**

More precisely: If G₁, G₂, ..., Gₖ are impartial games, then the composite game (playing all simultaneously) has Grundy number:

```
G(G₁ + G₂ + ... + Gₖ) = G(G₁) ⊕ G(G₂) ⊕ ... ⊕ G(Gₖ)
```

### Significance

This theorem means we can analyze ANY impartial game by:
1. Computing Grundy numbers for individual positions
2. XORing them together for composite games

### Applications

| Game | Grundy Number | Pattern |
|---|---|---|
| Nim pile of n | G(n) = n | Direct |
| Subtraction {1,2,3} | G(n) = n mod 4 | Periodic |
| Subtraction {1,4} | Periodic after some point | Eventually periodic |
| Wythoff's Game | Floor(n * φ) related | Beatty sequence |
| Turning Turtles | Depends on position | State-dependent |

### Example: Green Hackenbush (on trees)

Each edge is a "stalk" that can be cut. Cutting an edge removes it and everything above it.

```cpp
#include <iostream>
#include <vector>

// Grundy number for Green Hackenbush on a tree
// G(tree) = XOR of (G(subtree) + 1) for each child
int hackenbushGrundy(int u, int p, const std::vector<std::vector<int>>& adj) {
    int g = 0;
    for (int v : adj[u]) {
        if (v != p) {
            g ^= (hackenbushGrundy(v, u, adj) + 1);
        }
    }
    return g;
}

int main() {
    //       0
    //      / \
    //     1   2
    //    /|
    //   3  4
    
    int n = 5;
    std::vector<std::vector<int>> adj(n);
    adj[0] = {1, 2}; adj[1] = {0, 3, 4}; adj[2] = {0};
    adj[3] = {1}; adj[4] = {1};
    
    int g = hackenbushGrundy(0, -1, adj);
    std::cout << "Green Hackenbush Grundy number: " << g << "\n";
    std::cout << (g ? "First" : "Second") << " player wins.\n";
    
    return 0;
}
```

---

## 61.5 Game on Graphs

### Winning and Losing Positions

On a directed graph where players alternate moving a token:
- **Terminal position** (no outgoing edges): Losing (P-position)
- **P-position**: All moves lead to N-positions
- **N-position**: At least one move leads to a P-position

### Algorithm

```
1. Mark all terminal positions as P (losing)
2. BFS/DFS from terminals:
   - If all neighbors of u are N → u is P
   - If any neighbor of u is P → u is N
```

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

class GameOnGraph {
    int n;
    std::vector<std::vector<int>> adj;     // Forward edges
    std::vector<std::vector<int>> revAdj;  // Reverse edges
    std::vector<int> outDegree;
    std::vector<int> status; // 0 = unknown, 1 = N (win), -1 = P (lose)
    
public:
    GameOnGraph(int n) : n(n), adj(n), revAdj(n), outDegree(n, 0), status(n, 0) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        revAdj[v].push_back(u);
        outDegree[u]++;
    }
    
    // Returns status for each position: 1 = winning, -1 = losing
    std::vector<int> solve() {
        std::queue<int> q;
        
        // Find terminal positions (no outgoing edges)
        for (int i = 0; i < n; i++) {
            if (outDegree[i] == 0) {
                status[i] = -1; // Losing
                q.push(i);
            }
        }
        
        while (!q.empty()) {
            int u = q.front(); q.pop();
            
            for (int v : revAdj[u]) {
                if (status[v] != 0) continue;
                
                if (status[u] == -1) {
                    // v can move to a losing position → v is winning
                    status[v] = 1;
                    q.push(v);
                } else {
                    // v's neighbor is winning
                    outDegree[v]--;
                    if (outDegree[v] == 0) {
                        // All moves from v lead to winning positions → v is losing
                        status[v] = -1;
                        q.push(v);
                    }
                }
            }
        }
        
        return status;
    }
};

int main() {
    // Game graph:
    // 0 → 1 → 3 (terminal)
    // 0 → 2 → 4 (terminal)
    // 2 → 3
    
    GameOnGraph game(5);
    game.addEdge(0, 1);
    game.addEdge(0, 2);
    game.addEdge(1, 3);
    game.addEdge(2, 3);
    game.addEdge(2, 4);
    
    auto status = game.solve();
    
    std::cout << "Game positions:\n";
    for (int i = 0; i < 5; i++) {
        std::cout << "Position " << i << ": " 
                  << (status[i] == 1 ? "WINNING" : "LOSING") << "\n";
    }
    
    return 0;
}
```

### Game on Graphs with Cycles

When the graph has cycles, the analysis is more complex:
- Positions that can reach a cycle may be draws
- Modified algorithm: classify as Win/Lose/Draw

```cpp
#include <iostream>
#include <vector>
#include <queue>

enum Status { UNKNOWN, WIN, LOSE, DRAW };

class GameOnGraphCyclic {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<std::vector<int>> revAdj;
    std::vector<int> outDegree;
    std::vector<Status> status;
    
public:
    GameOnGraphCyclic(int n) : n(n), adj(n), revAdj(n), 
                                outDegree(n, 0), status(n, UNKNOWN) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        revAdj[v].push_back(u);
        outDegree[u]++;
    }
    
    std::vector<Status> solve() {
        std::queue<int> q;
        
        // Terminal positions are losing
        for (int i = 0; i < n; i++) {
            if (outDegree[i] == 0) {
                status[i] = LOSE;
                q.push(i);
            }
        }
        
        while (!q.empty()) {
            int u = q.front(); q.pop();
            
            for (int v : revAdj[u]) {
                if (status[v] != UNKNOWN) continue;
                
                if (status[u] == LOSE) {
                    status[v] = WIN;
                    q.push(v);
                } else {
                    outDegree[v]--;
                    if (outDegree[v] == 0) {
                        status[v] = LOSE;
                        q.push(v);
                    }
                }
            }
        }
        
        // Remaining unknown positions can reach a cycle → DRAW
        for (int i = 0; i < n; i++) {
            if (status[i] == UNKNOWN) status[i] = DRAW;
        }
        
        return status;
    }
};

int main() {
    GameOnGraphCyclic game(4);
    game.addEdge(0, 1);
    game.addEdge(1, 2);
    game.addEdge(2, 1); // Cycle: 1 ↔ 2
    game.addEdge(2, 3); // Terminal
    
    auto status = game.solve();
    
    const char* names[] = {"UNKNOWN", "WIN", "LOSE", "DRAW"};
    for (int i = 0; i < 4; i++) {
        std::cout << "Position " << i << ": " << names[status[i]] << "\n";
    }
    
    return 0;
}
```

---

## 61.6 Combinatorial Game Theory Basics

### Game Classification

| Type | Example | Analysis |
|---|---|---|
| Impartial | Nim, subtraction | Sprague-Grundy |
| Partisan | Chess, Go | Much harder (no general theory) |
| Normal play | Last to move wins | Standard |
| Misère play | Last to move loses | Modified Sprague-Grundy |

### Sums of Games

When multiple games are played simultaneously (a player chooses one game to move in), the composite game's Grundy number is the XOR of individual Grundy numbers.

### The Theory of Hot and Cold Games

- **Hot games**: The current player has an advantage (value > 0)
- **Cold games**: The next player has an advantage (value < 0)
- **Temperate games**: Close to fair

For impartial games, this reduces to Grundy numbers (0 = cold/losing, >0 = hot/winning).

### Common Game Patterns

| Pattern | Grundy Number | Notes |
|---|---|---|
| Single pile, take 1..k | n mod (k+1) | Periodic with period k+1 |
| Two piles, take from both | Wythoff pairs | Related to golden ratio |
| Graph game (tree) | XOR of (child_G + 1) | Green Hackenbush |
| Grid game | Position-dependent | Complex analysis |

---

## 61.7 More Game Theory Examples

### Subtraction Game Analysis

In a subtraction game, players can remove 1, 2, or 3 stones from a pile. The Grundy numbers follow a periodic pattern: G(n) = n mod 4.

This means:
- G(0) = 0 (losing)
- G(1) = 1 (winning: take 1)
- G(2) = 2 (winning: take 2)
- G(3) = 3 (winning: take 3)
- G(4) = 0 (losing: any move leaves opponent in winning position)
- G(5) = 1 (winning: take 1, leave opponent at G(4) = 0)

The pattern repeats with period 4. This generalizes: for subtraction set S, the Grundy numbers are eventually periodic with period at most 2^max(S).

### Why Periodicity Occurs

For subtraction games, the Grundy number G(n) depends only on the previous max(S) Grundy numbers. Since each Grundy number is a non-negative integer bounded by max(S), the sequence of the last max(S) values can take at most (max(S)+1)^(max(S)) distinct values. By the pigeonhole principle, the sequence must eventually repeat, creating a cycle.

This is a powerful insight: instead of computing Grundy numbers up to n (which could be huge), we only need to find the period and compute the answer modulo the period.

### Sprague-Grundy for Multi-Pile Games

When a game consists of multiple independent piles, the overall Grundy number is the XOR of individual pile Grundy numbers. This is the key insight that makes Nim analysis work:

- Each pile is an independent subgame
- The composite game's Grundy number = XOR of all pile Grundy numbers
- If XOR = 0, the position is losing (P-position)
- If XOR ≠ 0, the position is winning (N-position)

This decomposition works because of the Sprague-Grundy theorem: every impartial game under normal play is equivalent to a Nim heap of some size.

### Wythoff's Game

In Wythoff's Game, two players have two piles of stones. On each turn, a player can:
1. Remove any number of stones from one pile, OR
2. Remove the same number of stones from both piles

The losing positions (P-positions) are exactly the pairs:

```
(⌊kφ⌋, ⌊kφ²⌋) for k = 0, 1, 2, ...
```

where φ = (1 + √5) / 2 is the golden ratio.

The first few P-positions: (0,0), (1,2), (3,5), (4,7), (6,10), (8,13), ...

```cpp
#include <iostream>
#include <cmath>
#include <vector>
#include <algorithm>

bool isWythoffLosing(int a, int b) {
    if (a > b) std::swap(a, b);
    double phi = (1.0 + std::sqrt(5.0)) / 2.0;
    int k = b - a;
    // Check if a == floor(k * phi)
    return a == (int)(k * phi);
}

int main() {
    std::cout << "Wythoff's Game P-positions:\n";
    double phi = (1.0 + std::sqrt(5.0)) / 2.0;
    for (int k = 0; k <= 10; k++) {
        int a = (int)(k * phi);
        int b = (int)(k * phi * phi);
        std::cout << "(" << a << ", " << b << ")\n";
    }
    
    // Check specific positions
    std::cout << "\n(3, 5) is losing: " << isWythoffLosing(3, 5) << "\n";
    std::cout << "(3, 4) is losing: " << isWythoffLosing(3, 4) << "\n";
    
    return 0;
}
```

### Chomp Game

Chomp is a game played on a rectangular grid of cookies. Players alternate turns, each choosing a cookie and eating it along with all cookies below and to the right. The cookie at position (0,0) is poisoned; the player forced to eat it loses.

**Theorem**: The first player always has a winning strategy in Chomp (for any non-trivial board), but the proof is non-constructive (existence proof by strategy stealing).

### Game Theory Problem-Solving Strategy

When you encounter a game theory problem in an interview:

1. **Determine if it's impartial**: Same moves for both players? → Use Sprague-Grundy
2. **Check for known patterns**: Is it Nim? Subtraction? Wythoff?
3. **Compute Grundy numbers for small cases**: Look for patterns
4. **Check periodicity**: Many games have eventually periodic Grundy numbers
5. **For graph games**: Build the game graph, classify positions
6. **For composite games**: XOR of individual Grundy numbers

### Interview Tips for Game Theory

| Question Pattern | Approach |
|---|---|
| "Who wins?" | Compute XOR / Grundy number |
| "Find the winning move" | Try each move, check if result is P-position |
| "Count winning moves" | Enumerate moves, count those leaving P-position |
| "Is this position winning?" | Check Grundy number ≠ 0 |
| "Optimal play" | Both players play optimally → game theory |

## Summary

| Concept | Key Insight | Application |
|---|---|---|
| Nim | XOR of pile sizes | Classic impartial game |
| Grundy Numbers | mex of reachable Grundy values | Any impartial game |
| Sprague-Grundy | Every impartial game = Nim pile | Game decomposition |
| Game on Graphs | BFS from terminals | Win/Lose/Draw classification |
| Hot/Cold | Advantage analysis | Partisan games |
| Misère | Modify for last-to-move-loses | Variant analysis |
| Wythoff's Game | Golden ratio P-positions | Two-pile game |
| Periodicity | Grundy numbers often periodic | Pattern recognition |

### When NOT to Use Game Theory

| Situation | Why Not | Better Alternative |
|---|---|---|
| Not a two-player game | Game theory doesn't apply | Standard DP/optimization |
| Players have different moves | Not impartial (partisan) | Much harder analysis |
| No win/lose condition | Not a combinatorial game | Optimization problems |
| Game never ends | Infinite games need different analysis | Fixed-point theorems |
| Random elements in game | Not purely combinatorial | Stochastic game theory |

### Game Theory Trade-offs

| Approach | Pro | Con |
|---|---|---|
| Grundy numbers | Universal for impartial games | Can be hard to compute |
| XOR analysis | O(1) for Nim | Only works for Nim-heap equivalence |
| Graph-based | Exact win/lose classification | O(V+E) per analysis |
| Memoization | Handles complex states | Exponential state space |
| Pattern recognition | Fast for known games | Must know the pattern |
| Simulation | Intuitive | May not reveal optimal strategy |
