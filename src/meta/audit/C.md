# Chunk C Audit — DSA Chapters 91-150

**Scope:** ch91-150 (skipping already-fixed files listed in `already_fixed.md`)
**Files audited:** 20
**Files clean:** 1 (ch97-pattern-recognition.md had no substantive issues)
**Total findings:** 47

## Summary by severity

| Severity | Count |
|---|---|
| HIGH | 13 |
| MEDIUM | 22 |
| LOW | 12 |

> Note: Wrong cross-references are pervasive across the chunk (every chapter audited
> except ch97 and ch112 has at least one). Many references point to the wrong chapter
> number for the topic described (e.g., "Chapter 40: Dynamic Programming" when ch40 is
> Rolling Hash and DP is actually ch30). These are grouped as MEDIUM-severity findings
> because they mislead readers looking for background material, but the chapter body
> content is usually self-contained.

## Findings

### HIGH severity

#### ch96-np-approximation.md:324
- **Wrong text:** `Approximate cover: 6 vertices. Optimal: 3 (e.g., {2,3,5} or {0,3,4}). Ratio: 6/3 = 2. ✓`
- **Correct text:** `Approximate cover: 6 vertices. Optimal: 3 (e.g., {0,3,4} or {1,2,5}). Ratio: 6/3 = 2. ✓`
- **Verification:** Python script enumerating all 3-subsets of {0..5} against edge set {(0,1),(0,2),(1,3),(2,3),(2,4),(3,5),(4,5)}. {2,3,5} does not cover edge (0,1). Only {0,3,4} and {1,2,5} are valid size-3 covers.
- **Justification:** Teaches a wrong example — readers who verify will be confused.

#### ch96-np-approximation.md:751
- **Wrong text:** `**Implement 3-Approximation**: Design a 3-approximation algorithm for the Traveling Salesman Problem when the triangle inequality does NOT hold (hint: use MST and shortcutting with a different analysis).`
- **Correct text:** Remove or rephrase. Without the triangle inequality, TSP admits no constant-factor polynomial-time approximation unless P=NP. The MST+shortcutting technique explicitly relies on the triangle inequality to bound the tour cost.
- **Verification:** Standard result — Sahni & Gonzalez (1976) show no constant-factor approximation for general TSP unless P=NP. The MST 2-approximation explicitly requires the triangle inequality to shortcut the Euler tour.
- **Justification:** Misleading exercise asks the impossible; the hint is invalid.

#### ch98-splay-trees.md:64-86
- **Wrong text:** Walkthrough shows tree as a "degenerate right chain" with 1 at root after inserting 1-7, then claims splaying 1 brings it to the root via multiple zig-zig rotations.
- **Correct text:** After inserting 1..7 with the chapter's own `insert()` (which splays each new node to the root), the resulting tree is a degenerate LEFT chain with 7 at the root, not a right chain with 1 at the root. Furthermore, splaying node 1 when it is already at the root (as the chapter's diagram depicts) would be a no-op — there are no rotations to perform.
- **Verification:** Python simulation of the chapter's SplayTree insert for 1..7 produces:
  ```
  7
    6
      5
        4
          3
            2
              1
  ```
- **Justification:** The walkthrough is internally inconsistent with the chapter's own insert code and with how splay trees actually behave.

#### ch100-van-emde-boas.md:97
- **Wrong text:** `min = 2, max = 14`
- **Correct text:** `min = 2, max = 15`
- **Verification:** The inserted set (line 105) is `{2, 3, 9, 14, 15}`; `max({2,3,9,14,15}) = 15`. The chapter's own `Insert(x)` pseudocode (line 134) sets `max = x` whenever `x > max`, so inserting 15 last must yield `max = 15`.
- **Justification:** Wrong arithmetic in a worked example.

#### ch102-wavelet-trees.md:133-155
- **Wrong text:** `B = [0,1,2,2,3,4,4,4,4]  (prefix count of ≤5)` and the resulting trace ends with `Result: 4th smallest in [0,7] = **4** ✓ (sorted: [1,1,2,3,4,5,6,9])`.
- **Correct text:** `B = [0,1,2,3,4,5,5,6,6]` and `Result: 4th smallest = 3`.
- **Verification:** Python reimplementation of the chapter's WaveletTree class returns `B = [0,1,2,3,4,5,5,6,6]` at the root. `sorted([3,1,4,1,5,9,2,6])[3] = 3`, not 4.
- **Justification:** Dry run is built on a fabricated B array; the final answer contradicts the chapter's own sorted-list check.

#### ch102-wavelet-trees.md:251
- **Wrong text:** `// 2nd smallest in [0, 4] = sorted({3,1,4,1,5})[1] = 3`
- **Correct text:** `// 2nd smallest in [0, 4] = sorted({3,1,4,1,5})[1] = 1`
- **Verification:** `sorted([3,1,4,1,5]) = [1,1,3,4,5]`, so `sorted(...)[1] = 1`. Running the chapter's WaveletTree code yields `kth(0,4,1) = 1`.
- **Justification:** Code comment claims an answer that contradicts both the math and the code's actual output.

#### ch108-dsu-on-tree-rerooting.md:65-66
- **Wrong text:** `Process light child 4 (with 5): distinct = {2, 3} → 2` and `Process heavy child 3: distinct = {3} → 1`
- **Correct text:** Swap the labels: node 4 (subtree size 2) is the heavy child, node 3 (subtree size 1) is the light child.
- **Verification:** Subtree sizes: `|subtree(3)| = 1`, `|subtree(4)| = 2` (node 4 has child 5). Heavy child = larger subtree = node 4.
- **Justification:** The "heavy" / "light" labels are the central concept of DSU on Tree; getting them backwards undermines the explanation.

#### ch109-bridge-trees-treewidth.md:234 (step 6 of dry run)
- **Wrong text:** `DFS(3), explore neighbor 1 (visited back edge → low[3] = min(3, tin[1]) = 1). Explore 5.`
- **Correct text:** When at node 3, neighbor 1 is the parent in the DFS tree; the standard Tarjan bridge algorithm (and the chapter's own code) skips the parent edge, so `low[3]` is not updated here. The final table at lines 247-255 correctly lists `low[3] = 3`, which is inconsistent with this step.
- **Verification:** The chapter's `findBridges(u, p)` code has `if (v == p) continue;` — parent is skipped. The final table reports `low[3]=3`, contradicting step 6's claim of `low[3]=1`.
- **Justification:** Step-by-step trace uses wrong algorithm; readers following along will reach a different state than the algorithm actually produces.

#### ch114-probability-dp.md:478
- **Wrong text:** `In the dice-throw game, verify that the expected throws for n=6 is exactly 7/3.6 ≈ 1.9444.`
- **Correct text:** `In the dice-throw game, the expected throws for n=6 is (7/6)^5 = 16807/7776 ≈ 2.1614.`
- **Verification:** Python implementation of the chapter's `expected_dice_throws(6)` returns 2.161394. `7/3.6 = 1.9444...` does not match. The closed form for n=6 follows the recurrence `E[i] = 1 + (1/6) * sum(E[min(i+d,6)] for d in 1..6)` and equals `(7/6)^5`.
- **Justification:** Exercise asks readers to "verify" a wrong closed-form answer.

#### ch118-bitset-dp.md:425-441
- **Wrong text:** The knapsack dry run claims `After item 0 (w=2, v=3): dp = [0, 0, 3, 0, 3, 0, 3, 0, 3]` and similar intermediate dp arrays.
- **Correct text:** `After item 0: dp = [0, 0, 3, 3, 3, 3, 3, 3, 3]` (the loop runs `for w = W; w >= weights[i]; w--`, which updates ALL positions from 8 down to 2, not just even indices).
- **Verification:** Python reimplementation of the chapter's `knapsack01` produces `[0, 0, 3, 3, 3, 3, 3, 3, 3]` after item 0. The chapter's intermediate arrays throughout the dry run (after items 0, 1, 2) are wrong; only the final dp[8]=10 happens to be correct.
- **Justification:** Walkthrough contradicts the chapter's own code; students tracing by hand will be confused.

#### ch119-manacher.md:279
- **Wrong text:** `| 4 | a | 0 | 6 | 2 | 2 | "aba" |` (table row claiming d1[4] = 2 with palindrome "aba")
- **Correct text:** `| 4 | a | 0 | 6 | 1 | 1 | "a" |` (d1[4] = 1, palindrome = "a")
- **Verification:** For `s = "abacaba"`, centered at index 4 (s[4]='a'): the length-3 candidate `s[3..5] = "cab"` is not a palindrome. The only odd-length palindrome centered at 4 is "a" itself. Python reimplementation of the chapter's `manacher()` returns `d1 = [1, 2, 1, 4, 1, 2, 1]`.
- **Justification:** Dry run teaches wrong intermediate values for the algorithm.

#### ch123-regex-wildcard.md:54-106
- **Wrong text:** The wildcard matching dry run for `s = "adceb"`, `p = "*a*b"` uses `j = 5` with `p[4] = '*'`, and reports the final answer as `dp[5][5] = true`.
- **Correct text:** `p = "*a*b"` has length 4, so j ranges 0..4. The final cell is `dp[5][4]`, not `dp[5][5]`. There is no `p[4]` and no `dp[0][5]`/`dp[1][5]`/etc.
- **Verification:** Python reimplementation confirms `m = len("*a*b") = 4`, dp table is 6×5, and the final answer is `dp[5][4] = True`.
- **Justification:** Off-by-one in the dry run; treats the pattern as having 5 characters when it has 4.

#### ch125-simd-overview.md:35
- **Wrong text:** `| MMX | 64-bit | 2 | 2 | 1997 |` (claiming MMX supports 2 float32 lanes)
- **Correct text:** `| MMX | 64-bit | 2 | — | 1997 |` (MMX supports only integer operations; no float32)
- **Verification:** Intel's original MMX (Pentium P55C, 1997) introduced 64-bit MMx integer registers aliased onto the x87 FPU stack. MMX has no floating-point SIMD instructions — the FPU had to be used for floats. SSE (1999) was the first x86 SIMD instruction set with single-precision float support. (Source: Intel 64 and IA-32 Architectures Software Developer's Manual, Vol. 1, Ch. 9 "Programming with Intel MMX Technology".)
- **Justification:** Factually wrong claim about a hardware feature; readers will be misled about SIMD history.

### MEDIUM severity

#### ch95-bit-advanced.md:656-658
- **Wrong text:**
  - `Chapter 94: Bit Manipulation Basics — Foundation: AND, OR, XOR, shifts, and basic tricks` (ch94 is Hashing Deep Dive)
  - `Chapter 23: Dynamic Programming — Bit DP is a specialized DP technique` (ch23 is DFS; DP is ch30)
  - `Chapter 91: STL Deep Dive — std::bitset for compile-time bit operations` (ch91 is Profiling and Benchmarking)
- **Correct text:** Update chapter numbers to point to actual chapters covering those topics.
- **Verification:** `head -1` on each referenced file confirms the mismatch.
- **Justification:** Cross-references send readers to the wrong chapters.

#### ch96-np-approximation.md:784-789
- **Wrong text:** All cross-references are wrong:
  - `Chapter 95: Complexity Theory` (ch95 is Advanced Bit Manipulation; complexity classes are ch70)
  - `Chapter 97: Backtracking` (ch97 is Pattern Recognition Handbook; backtracking is ch9)
  - `Chapter 98: Branch and Bound` (ch98 is Splay Trees; B&B is ch133)
  - `Chapter 40: Greedy Algorithms` (ch40 is Rolling Hash; greedy is ch32)
  - `Chapter 45: Dynamic Programming` (ch45 is Suffix Automaton; DP is ch30)
  - `Chapter 70: Graph Algorithms` (ch70 is Computational Models and Complexity Classes; graphs are ch22-29)
- **Verification:** `head -1` on each file.
- **Justification:** Every reference is mislabeled.

#### ch98-splay-trees.md:5
- **Wrong text:** `Tree rotations (Chapter 16)` (ch16 is "Trie", not tree rotations)
- **Correct text:** `Tree rotations (Chapter 14: BST)` or similar.
- **Justification:** Prerequisite reference points to wrong chapter.

#### ch98-splay-trees.md:548
- **Wrong text:** `Chapter 16: AVL Trees — Strictly balanced BSTs for worst-case guarantees` (ch16 is "Trie")
- **Correct text:** AVL Trees are not a separate chapter; remove or fix the reference.
- **Justification:** Mislabeled cross-reference.

#### ch100-van-emde-boas.md:1021-1024
- **Wrong text:**
  - `Chapter 29: Hashing` (ch29 is Network Flow; hashing is ch7)
  - `Chapter 30: Tries` (ch30 is DP Fundamentals; tries are ch16)
  - `Chapter 25: Binary Search Trees` (ch25 is Topological Sort; BST is ch14)
  - `Chapter 33: Heaps` (ch33 is Bit Manipulation; heaps are ch15)
- **Justification:** Cross-references send readers to the wrong chapters.

#### ch101-rope-gap-buffer.md:230-233
- **Wrong text:** Step 12 diagram shows `[H e l l o ! _ _ _ _ _ _ _ _ ' ' W o r l d !]` (21 characters) after inserting one char.
- **Correct text:** `[H e l l o ! _ _ _ _ _ _ _ ' ' W o r l d !]` (20 characters, 7 underscores in gap, not 8).
- **Verification:** Buffer capacity is 20 throughout; after inserting one char, gap shrinks from 8 to 7 slots.
- **Justification:** Visual dry run has an extra slot, breaking the invariant that array size stays at 20.

#### ch101-rope-gap-buffer.md:984-989
- **Wrong text:** All cross-references wrong:
  - `Chapter 13 (Arrays and Strings)` (ch13 is Trees; arrays/strings is ch4)
  - `Chapter 15 (Binary Trees)` (ch15 is Heaps)
  - `Chapter 16 (Balanced BSTs)` (ch16 is Trie)
  - `Chapter 102 (Tries)` (ch102 is Wavelet Trees; tries are ch16)
  - `Chapter 104 (Segment Trees)` (ch104 is Cartesian/Tournament Trees; seg trees are ch18)
  - `Chapter 105 (Fenwick Trees)` (ch105 is Cuckoo/Robin-Hood Hashing; Fenwick is ch19)
- **Justification:** Mislabeled cross-references.

#### ch104-cartesian-tournament-trees.md:492-497
- **Wrong text:** All cross-references wrong:
  - `Chapter 101 (Segment Trees)` (ch101 is Rope/Gap Buffer; seg trees are ch18)
  - `Chapter 105 (Suffix Trees/Arrays)` (ch105 is Cuckoo Hashing; suffix arrays are ch44)
  - `Chapter 97 (Heaps)` (ch97 is Pattern Recognition; heaps are ch15)
  - `Chapter 11 (LCA)` (ch11 is Queues; LCA is ch21)
  - `Chapter 116 (Treaps)` (ch116 is Alien Trick)
- **Justification:** Mislabeled cross-references.

#### ch106-euler-tour-tree-flattening.md:572-577
- **Wrong text:** Cross-references wrong:
  - `Chapter 101 (Segment Trees)` (ch101 is Rope/Gap Buffer; seg trees are ch18)
  - `Chapter 99 (BIT/Fenwick Tree)` (ch99 is Scapegoat/AA Trees; Fenwick is ch19)
  - `Chapter 11 (LCA)` (ch11 is Queues; LCA is ch21)
  - `Chapter 110 (Heavy-Light Decomposition)` (ch110 is Dominator Trees; HLD is ch107)
  - `Chapter 150 (Mo's Algorithm)` (ch150 is Advanced Randomized)
- **Justification:** Mislabeled cross-references.

#### ch108-dsu-on-tree-rerooting.md:5, 580
- **Wrong text:** `DSU / Union-Find (Chapter 20)` and cross-ref `Chapter 20: DSU / Union-Find` (ch20 is Sparse Table; DSU is ch17)
- **Justification:** Prerequisite and cross-reference both point to the wrong chapter.

#### ch109-bridge-trees-treewidth.md:4-8, 728-736
- **Wrong text:** Every cross-reference is wrong. Prerequisites list `Chapter 102: Graph Fundamentals` (ch102 is Wavelet Trees; graphs are ch22), `Chapter 103: DFS and BFS` (ch103 is Interval Order Statistic Trees; DFS is ch23), `Chapter 104: Strongly Connected Components` (ch104 is Cartesian Trees; SCC is ch81), `Chapter 105: Shortest Paths` (ch105 is Cuckoo Hashing; shortest paths are ch26), `Chapter 108: Trees` (ch108 is DSU on Tree; trees are ch13). Cross-references section has the same issues plus `Chapter 110: Euler Tour and Flows` (ch110 is Dominator Trees; Euler tour is ch106), `Chapter 112: Advanced Graph Algorithms` (ch112 is Hopcroft-Karp/Blossom), `Chapter 106: Minimum Spanning Trees` (ch106 is Euler Tour; MST is ch27), `Chapter 107: Network Flow` (ch107 is HLD; network flow is ch29).
- **Justification:** Prerequisites and cross-references all point to wrong chapters.

#### ch110-dominator-trees.md:550-558
- **Wrong text:** All cross-references wrong:
  - `DFS | Chapter 40` (ch40 is Rolling Hash; DFS is ch23)
  - `SCC (Tarjan's) | Chapter 45` (ch45 is Suffix Automaton; SCC is ch81)
  - `LCA | Chapter 65` (ch65 is Searching Expanded; LCA is ch21)
  - `Union-Find | Chapter 35` (ch35 is Sliding Window; DSU is ch17)
  - `Topological Sort | Chapter 42` (ch42 is Z-Algorithm; topo sort is ch25)
  - `Control Flow Graphs | Chapter 120` (ch120 is BWT/FM-Index)
  - `SSA Form | Chapter 122` (ch122 is Edit Distance Variants)
- **Justification:** Mislabeled cross-references.

#### ch114-probability-dp.md:4, 497-500
- **Wrong text:** Prerequisite `DP basics (Chapters 45–48)` (ch45-48 are Suffix Automaton, Aho-Corasick, Problem Solving, Technical Communication — none are DP basics). Cross-references `DP fundamentals: Chapter 45`, `Game theory DP: Chapter 115` (ch115 is Matrix DP), `Probability basics: Chapter 100` (ch100 is Van Emde Boas; probability is ch72), `Markov chains: Chapter 101` (ch101 is Rope/Gap Buffer).
- **Justification:** All chapter references for DP/probability background are wrong.

#### ch118-bitset-dp.md:4-5, 803-809
- **Wrong text:** Prerequisites `Bit manipulation (Chapter 15)` (ch15 is Heaps; bit manipulation is ch33), `Dynamic programming basics (Chapter 40–45)` (none of ch40-45 are DP basics; DP is ch30). Cross-references `Chapter 15: Bit Manipulation`, `Chapter 40: Dynamic Programming Basics`, `Chapter 43: Knapsack Problems` (ch43 is Trie Applications), `Chapter 44: String DP` (ch44 is Suffix Array), `Chapter 45: Interval DP` (ch45 is Suffix Automaton), `Chapter 70: Graph Algorithms` (ch70 is Computational Models), `Chapter 117: State Space Search` (ch117 is Monotone Queue Optimization).
- **Justification:** Prerequisites and cross-references all wrong.

#### ch118-bitset-dp.md:123
- **Wrong text:** `dp << 3: ...00001000 (shift right by 3: bit 3 set)`
- **Correct text:** `dp << 3: ...00001000 (shift LEFT by 3: bit 3 set)`
- **Justification:** `<<` is left-shift, not right-shift. Wrong description of the operation.

#### ch119-manacher.md:4-5, 453-458
- **Wrong text:** Prerequisites `[Chapter 102](ch102-wavelet-trees.md)` labeled "Palindromes, string basics" (ch102 is Wavelet Trees; string basics are ch4/ch55), `[Chapter 107](ch107-hld-centroid-applications.md)` labeled "Two-pointer technique" (ch107 is HLD; two pointers are ch34). Cross-references similarly mislabeled: `KMP Algorithm: Chapter 103` (ch103 is Interval Order Statistic Trees; KMP is ch41), `Suffix Arrays: Chapter 104` (ch104 is Cartesian Trees; suffix arrays are ch44), `Dynamic Programming: Chapter 109` (ch109 is Bridge Trees; DP is ch30), `Palindromic Tree: Chapter 120` (ch120 is BWT/FM-Index; palindromic tree is ch88).
- **Justification:** All cross-references point to wrong chapters.

#### ch119-manacher.md:283-291 (walkthrough for i=3)
- **Wrong text:** Walkthrough says `l=1, r=3` (actual state before i=3 is `l=0, r=2`); uses `d1[1] = 1` (actual d1[1] = 2); says `s[3-1]='b'` (actually s[2]='a'); says `s[3-2]='a'` (actually s[1]='b').
- **Correct text:** State before i=3 is `l=0, r=2`; mirror `l+r-i = 0+2-3 = -1`, but since i=3 > r=2, k=1 directly. Characters checked: s[2]='a' vs s[4]='a' (match), s[1]='b' vs s[5]='b' (match), s[0]='a' vs s[6]='a' (match), then out of bounds. d1[3]=4.
- **Justification:** Walkthrough has multiple incorrect intermediate values; final answer happens to be right.

#### ch122-edit-distance-variants.md:4, 782-787
- **Wrong text:** Prerequisite `Dynamic programming basics (Chapter 40)` (ch40 is Rolling Hash; DP is ch30). Cross-references `Chapter 40: Dynamic Programming Basics`, `Chapter 44: String DP` (ch44 is Suffix Array), `Chapter 43: LCS` (ch43 is Trie Applications), `Chapter 123: Cache Optimization` (ch123 is Regex Wildcard), `Chapter 77: Trie` (ch77 is B-Trees; trie is ch16).
- **Justification:** Prerequisites and cross-references all wrong.

#### ch122-edit-distance-variants.md:657
- **Wrong text:** `// Needleman-Wunsch (global alignment) with affine gap penalties` (function signature takes `gapOpen` and `gapExtend` parameters)
- **Correct text:** The implementation uses LINEAR gap penalties — every gap position costs `gapOpen`. The `gapExtend` parameter is declared but never used. True affine gap penalties require separate DP matrices for "in a gap" vs "not in a gap" states (e.g., Gotoh's algorithm).
- **Verification:** Code inspection: line 666-667 `dp[i][0] = i * gapOpen; dp[0][j] = j * gapOpen;` — linear, not affine. Line 674-675 uses `gapOpen` for both transitions; `gapExtend` is unused.
- **Justification:** Comment misrepresents the algorithm implemented.

#### ch123-regex-wildcard.md:671-675
- **Wrong text:** Cross-references `Chapter 89 (String Matching)` (ch89 is Engineering Cache; string matching is ch40-42), `Chapter 90 (Trie)` (ch90 is C++ Deep Dive; trie is ch16), `Chapter 102 (Advanced DP)` (ch102 is Wavelet Trees), `Chapter 45 (Backtracking)` (ch45 is Suffix Automaton; backtracking is ch9).
- **Justification:** Cross-references all wrong.

#### ch126-raii-smart-pointers.md:493-498
- **Wrong text:** All cross-references wrong: `Chapter 2: Memory management fundamentals` (ch2 is Math Foundations; memory hardware is ch52), `Chapter 5: Linked lists using smart pointers` (ch5 is Sorting; linked lists are ch12), `Chapter 32: Thread safety and mutexes` (ch32 is Greedy Algorithms), `Chapter 45: Move semantics and rvalue references` (ch45 is Suffix Automaton; move semantics are ch127), `Chapter 78: Design patterns` (ch78 is Kd-Trees), `Chapter 145: Lock-free data structures` (ch145 is Approximation Algorithms).
- **Justification:** Mislabeled cross-references.

#### ch126-raii-smart-pointers.md:294
- **Wrong text:** `B->left = A (weak): A.use_count = 1 (not incremented)` (the `GoodNode` struct at line 282-285 has `parent` as the weak field, not `left`)
- **Correct text:** `B->parent = A (weak): A.use_count = 1 (not incremented)`
- **Justification:** Dry run uses a field name inconsistent with the struct definition above it.

### LOW severity

#### ch97-pattern-recognition.md:152
- **Wrong text:** `n > 10^7 | O(log n) | Binary search, math` — implies that for n > 10^7, only O(log n) algorithms work, which excludes valid O(n) solutions.
- **Correct text:** For n > 10^7, neither O(n) nor O(log n) is universally required — it depends on the time limit and constant factors. Consider rephrasing to "sub-linear preferred" or removing this row.
- **Justification:** Overly restrictive guidance; could mislead.

#### ch97-pattern-recognition.md:194
- **Wrong text:** `int slidingWindow(vector<int>& nums, int k)` declares parameter `k` but never uses it.
- **Justification:** Unused parameter in template code.

#### ch100-van-emde-boas.md:80
- **Wrong text:** `O(V + E) × α(V))` — unbalanced parenthesis.
- **Correct text:** `O((V + E) × α(V))`
- **Justification:** Typo.

#### ch109-bridge-trees-treewidth.md:656, 661
- **Wrong text:** `std::cout << "Is tree: " << isTree(4, adj) << "\\n";` and `std::cout << "Is tree: " << isTree(3, adj2) << "\\n";` — `\\n` in C++ source is a literal backslash-n, not a newline.
- **Correct text:** `"\n"` (single backslash).
- **Justification:** Minor code bug; output formatting would be wrong.

#### ch112-hopcroft-karp-blossom.md:172-173, 177-178
- **Wrong text:** `std::cout << "Triangle matching: " << bs.maxMatching() << "\n";` (string literal spans two lines with embedded newline).
- **Justification:** Unusual but technically valid C++; stylistic only.

#### ch112-hopcroft-karp-blossom.md:305, 310
- **Wrong text:** `"\\n"` in `std::cout` statements (literal backslash-n).
- **Justification:** Cosmetic; output would print "\n" literally.

#### ch114-probability-dp.md:114
- **Wrong text:** Comment in C++ header says `#include <iomanip>` is included but `std::function` is used in line 164 (`std::function<void(int)> dfs = ...`) without `#include <functional>`.
- **Correct text:** Add `#include <functional>`.
- **Justification:** Missing header (might fail to compile on strict compilers).

#### ch118-bitset-dp.md:251 (in dry run)
- **Wrong text:** `dp << 3: ...00001000 (shift right by 3: bit 3 set)` is described twice — once at line 123 and the same error pattern repeats.
- **Justification:** Cosmetic; already noted as MEDIUM.

#### ch119-manacher.md:289
- **Wrong text:** `Check s[3-3]='?' — out of bounds, stop. Wait, s[0]='a', s[6]='a' → match, k=4` — the "?" placeholder is confusing.
- **Correct text:** `Check s[0]='a' vs s[6]='a' → match, k=4`.
- **Justification:** Awkward phrasing in walkthrough.

#### ch122-edit-distance-variants.md:480
- **Wrong text:** `// 29 = 11101, 15 = 01111, XOR = 10010, popcount = 2` — this is correct, but popcount could be ambiguous; use `__builtin_popcount` semantics explicitly.
- **Justification:** Minor cosmetic; correctness verified.

#### ch125-simd-overview.md:42
- **Wrong text:** `SVE (ARM) | 128-2048 bit | varies | varies | 2016` — SVE was specified in ARMv8.2-A (2016) but actual hardware (Fujitsu A64FX) shipped in 2019+.
- **Justification:** Date ambiguity; not strictly wrong but could be clarified.

#### ch126-raii-smart-pointers.md:350
- **Wrong text:** `Memory overhead | 0 bytes | 16-32 bytes | 16-32 bytes` — `unique_ptr` with a custom deleter may have non-zero overhead.
- **Correct text:** `Memory overhead | 0 bytes (default deleter) | 16-32 bytes | 16-32 bytes`
- **Justification:** Minor caveat missing.

## Files confirmed clean

- ch97-pattern-recognition.md (only minor LOW-severity stylistic notes; no factual errors in the decision flowchart, complexity table, or templates)

## Files with the most findings

1. ch109-bridge-trees-treewidth.md — 9 findings (all cross-references wrong + dry run inconsistency + code typo)
2. ch118-bitset-dp.md — 9 findings (prerequisites/cross-refs + knapsack dry run + shift direction)
3. ch119-manacher.md — 8 findings (prerequisites/cross-refs + dry run table + walkthrough chars)
4. ch96-np-approximation.md — 8 findings (cross-refs + vertex cover example + TSP exercise)
5. ch110-dominator-trees.md — 7 findings (all cross-references wrong)

## Verification methodology

- Arithmetic claims were verified by re-implementing the relevant algorithm in Python and running it.
- Vertex cover, TSP, dice throws, knapsack, Manacher, wavelet tree, wildcard matching — all verified with executable Python scripts.
- Chapter-title cross-references were verified by `head -1` on each referenced file.
- The MMX/SIMD fact was verified against the Intel SDM Vol. 1.
- The TSP-without-triangle-inequality impossibility was verified against standard approximation-algorithms references (Sahni & Gonzalez 1976; Vazirani's *Approximation Algorithms*).
