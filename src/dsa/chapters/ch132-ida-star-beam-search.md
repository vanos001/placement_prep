# Chapter 132: IDA* and Beam Search

## Prerequisites
- DFS, BFS, A*

## Interview Frequency: ★

Advanced search strategies for large state spaces.

---

## 132.1 IDA* (Iterative Deepening A*)

Combines iterative deepening with heuristic pruning. Memory-efficient alternative to A*.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

// 8-puzzle heuristic (Manhattan distance)
int manhattan(const std::vector<int>& state) {
    int dist = 0;
    for (int i = 0; i < 9; i++) {
        if (state[i] == 0) continue;
        int targetRow = (state[i] - 1) / 3;
        int targetCol = (state[i] - 1) % 3;
        int currRow = i / 3;
        int currCol = i % 3;
        dist += abs(targetRow - currRow) + abs(targetCol - currCol);
    }
    return dist;
}

int idaStar(std::vector<int> state, int bound, int& nextBound) {
    int h = manhattan(state);
    if (h == 0) return 0;
    int f = h;
    if (f > bound) { nextBound = std::min(nextBound, f); return -1; }
    
    int zeroPos = 0;
    for (int i = 0; i < 9; i++) if (state[i] == 0) { zeroPos = i; break; }
    
    int dx[] = {0, 0, 1, -1};
    int dy[] = {1, -1, 0, 0};
    
    for (int d = 0; d < 4; d++) {
        int nx = zeroPos / 3 + dx[d];
        int ny = zeroPos % 3 + dy[d];
        if (nx < 0 || nx >= 3 || ny < 0 || ny >= 3) continue;
        
        int newPos = nx * 3 + ny;
        std::swap(state[zeroPos], state[newPos]);
        
        int newBound = INT_MAX;
        int result = idaStar(state, bound, newBound);
        if (result >= 0) { std::swap(state[zeroPos], state[newPos]); return result + 1; }
        nextBound = std::min(nextBound, newBound);
        
        std::swap(state[zeroPos], state[newPos]);
    }
    
    return -1;
}

int main() {
    std::vector<int> state = {1, 2, 3, 4, 0, 5, 6, 7, 8};
    int bound = manhattan(state);
    
    while (true) {
        int nextBound = INT_MAX;
        int result = idaStar(state, bound, nextBound);
        if (result >= 0) {
            std::cout << "Solution found in " << result << " moves\n";
            break;
        }
        if (nextBound == INT_MAX) break;
        bound = nextBound;
    }
    
    return 0;
}
```

---

## 132.2 Beam Search

Beam search keeps only the top-k states at each level of a search tree. It's a memory-bounded best-first search.

**Key parameter**: beam width k. Larger k = better solutions but more memory and time.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>

struct State {
    std::vector<int> choices;
    double score;
    bool operator<(const State& other) const { return score < other.score; }
};

// Beam search for TSP (approximate)
std::vector<int> beamSearchTSP(const std::vector<std::vector<int>>& dist, int beamWidth = 3) {
    int n = dist.size();
    std::vector<State> beam;
    beam.push_back({std::vector<int>{0}, 0.0});
    
    for (int step = 1; step < n; step++) {
        std::vector<State> candidates;
        for (auto& state : beam) {
            for (int next = 0; next < n; next++) {
                if (std::find(state.choices.begin(), state.choices.end(), next) != state.choices.end()) continue;
                State newState = state;
                newState.choices.push_back(next);
                newState.score += dist[state.choices.back()][next];
                candidates.push_back(newState);
            }
        }
        std::sort(candidates.begin(), candidates.end());
        beam.clear();
        for (int i = 0; i < std::min(beamWidth, (int)candidates.size()); i++)
            beam.push_back(candidates[i]);
    }
    
    State best = beam[0];
    best.score += dist[best.choices.back()][0];
    best.choices.push_back(0);
    return best.choices;
}

int main() {
    std::vector<std::vector<int>> dist = {{0,10,15,20},{10,0,35,25},{15,35,0,30},{20,25,30,0}};
    auto tour = beamSearchTSP(dist, 2);
    std::cout << "Beam search tour: ";
    for (int v : tour) std::cout << v << " ";
    std::cout << "\n";
    return 0;
}
```
## Summary

| Algorithm | Memory | Optimal? | Best For |
|---|---|---|---|
| IDA* | O(d) depth | Yes | Memory-constrained A* |
| Beam Search | O(k) per level | No | Large state spaces |

---

---

## Interview Questions

### Q1: What is IDA* and when would you use it over A*?
**Answer**: IDA* (Iterative Deepening A*) performs iterative deepening where the threshold is the f-cost bound. Unlike A*, it uses O(d) memory (d = solution depth) instead of O(b^d). Use IDA* when memory is constrained (e.g., embedded systems, very large state spaces) and a good heuristic exists.

### Q2: How does beam search differ from BFS?
**Answer**: BFS keeps all nodes at each level (exponential memory). Beam search keeps only the top-k nodes (beam width k) at each level, using a heuristic to rank them. This limits memory to O(k) per level but sacrifices optimality — it may miss the optimal solution.

### Q3: When is beam search preferred over A* or IDA*?
**Answer**: Beam search is preferred when: (1) the state space is enormous (e.g., NLP parsing, protein folding), (2) approximate solutions are acceptable, and (3) real-time constraints require fast decisions. It's common in machine learning and combinatorial optimization.

### Q4: What is the weakness of beam search?
**Answer**: Beam search can miss optimal solutions because it discards states at each level. A promising path may be pruned early if its immediate score is poor but would lead to a great solution later. Increasing beam width mitigates this but increases runtime linearly.

### Q5: How does IDA* choose its threshold sequence?
**Answer**: IDA* starts with the heuristic value h(start) as the first threshold. If no solution is found, it sets the next threshold to the minimum f-cost that exceeded the previous threshold. This ensures no solution is missed and the threshold sequence is monotonically increasing.

---

## Exercises

1. **IDA* for 15-Puzzle**: Extend the 8-puzzle IDA* solver to handle the 15-puzzle (4×4 grid). Compare the number of nodes explored with and without the Manhattan distance heuristic.

2. **Beam Width Tradeoff**: Run the beam search TSP solver with beam widths 1, 2, 5, 10, and 20 on a 10-city instance. Plot solution quality vs. runtime. What width gives the best tradeoff?

3. **IDA* vs. A***: Implement A* for the 8-puzzle and compare the number of states explored vs. IDA* on the same inputs. When does IDA* explore more states?

4. **Beam Search with Restart**: Modify beam search to restart with a random initial state when it gets stuck. Test on TSP instances and compare to single-run beam search.

5. **Heuristic Design**: Implement the linear conflict heuristic for the 8-puzzle (in addition to Manhattan distance). Compare node counts for IDA* with each heuristic on 20 random puzzles.

---

## See Also

- [Chapter 6: Searching](ch06-searching.md) — Foundational search algorithms (BFS, DFS, binary search) that IDA* and beam search extend.
- [Chapter 8: Recursion](ch08-recursion.md) — IDA* is inherently recursive, using iterative deepening with recursive DFS at each level.
- [Chapter 133: Branch and Bound and Dancing Links](ch133-branch-bound-dancing-links.md) — Branch and Bound is another bounded search strategy; DLX handles exact cover problems.
- [Chapter 9: Backtracking](ch09-backtracking.md) — Both IDA* and beam search are forms of guided backtracking.
- [Chapter 86: DP Optimization](ch86-dp-optimization.md) — Some DP problems can be solved with search-based approaches when the state space is too large.
- [Chapter 3: Complexity Analysis](ch03-complexity-analysis.md) — Understanding time/space tradeoffs helps choose between A*, IDA*, and beam search.
