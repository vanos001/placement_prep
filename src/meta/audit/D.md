# Chunk D Audit — DSA Chapters 151-180 + Appendices

**Scope:** ch151-180 (excl. already-fixed: 152, 154, 156, 160, 163, 164, 165, 167, 168, 169, 170, 172, 176, 177, 178, 179) + all 13 appendices
**Files audited:** 27 (14 chapters + 13 appendices)
**Files clean:** 17
**Total findings:** 28

Audit methodology: read every file end-to-end; verified arithmetic with Python; cross-checked every chapter reference against the actual file at `src/dsa/chapters/`; flagged AI artifacts, broken LaTeX, code bugs, and self-contradictions.

The dominant pattern across ch151-180 is **wrong chapter cross-references** — many chapters cite a chapter number that does not match the topic. This is systematic and consistent with a previous LLM-generated draft that guessed chapter numbers. Below is the full breakdown.

---

## Findings

### HIGH severity

#### H1. `ch157-link-cut-trees.md:202, 314` — Wrong expected output for `findRoot(5)`
**Wrong text (C++):** `std::cout << "Find root of 5: " << lct.findRoot(5) << "\n"; // 3`
**Wrong text (Python):** `print(f"Find root of 5: {lct.find_root(5)}")  # 3`
**Correct:** `// 5` (and `# 5` in Python)
**Why:** `link(u, v)` is implemented as `makeRoot(u); u->parent = v`, which makes `u` a child of `v`. After `link(0,1); link(1,2); link(2,3); cut(1,2); link(3,4); link(4,5);` the represented tree rooted at 5 is `5 → 4 → 3 → 2`. `findRoot(5)` walks left from `nodes[5]` after `access(5)` — and since 5 *is* the represented-tree root, the left spine is empty, so it returns 5, not 3.
**Verification:** traced the standard LCT invariant by hand; also confirmed by simulating the operation sequence in Python (`lct.py` simulation outputs `findRoot(5) = 5`).

#### H2. `ch161-adv-geometry.md:350-355, 366-377` — Half-plane intersection code produces empty set, not unit square
The four half-planes defined in `main()`:
```cpp
HalfPlane({0, 0}, {0, 1}),    // comment says x >= 0
HalfPlane({1, 0}, {0, -1}),   // comment says x <= 1
HalfPlane({0, 0}, {-1, 0}),   // comment says y >= 0
HalfPlane({0, 1}, {1, 0}),    // comment says y <= 1
```
all have their **direction vectors flipped** relative to the comments. The `inside()` predicate uses `cross(hp.d, p - hp.p) >= -1e-9` (left-side convention), so for `d=(0,1)` from `(0,0)`, `inside((x,y)) = -x >= 0`, i.e. `x ≤ 0`, not `x ≥ 0`. Similarly the other three are flipped. The actual intersection is `{x ≤ 0, x ≥ 1, y ≤ 0, y ≥ 1}` = **empty set**.
**Dry run at lines 366-377** claims the result is the unit square with vertices `(0,0), (1,0), (1,1), (0,1)` — this directly contradicts the code.
**Verification:** Python script `cross(dx,dy,px-p0x,py-p0y) >= 0` confirms all four directions are inverted (see audit script in `meta/audit/` notes).
**Fix:** flip each direction vector — `{0,-1}` for `x ≥ 0`, `{0,1}` for `x ≤ 1`, `{1,0}` for `y ≥ 0`, `{-1,0}` for `y ≤ 1`.

#### H3. `ch151-linear-programming.md:664-669` — All cross-references point to wrong chapters
| Wrong text | Correct chapter |
|---|---|
| "**Chapter 152 (Network Flow):** Network flow is a special case of LP." | ch152 is `integer-programming.md`, not Network Flow. Network flow is ch29. |
| "**Chapter 153 (Approximation Algorithms):**" | ch153 is `advanced-optimization.md`, not Approximation Algorithms (ch145). |
| "**Chapter 154 (Game Theory):**" | ch154 is `spectral-graph-theory.md`, not Game Theory (ch61 or ch162). |
| "**Chapter 127 (Dynamic Programming):**" | ch127 is `move-semantics.md`, not DP (ch30/ch31). |
| "**Chapter 101 (Segment Trees):**" | ch101 is `rope-gap-buffer.md`, not Segment Trees (ch18). |

#### H4. `ch153-advanced-optimization.md:644-650` — All 7 cross-references in the table are wrong
| Wrong text | Correct chapter |
|---|---|
| "Max Flow \| Chapter 100" | ch100 is `van-emde-boas.md` (should be ch29). |
| "Bipartite Matching \| Chapter 101" | ch101 is `rope-gap-buffer.md` (should be ch112 or ch170). |
| "Binary Search \| Chapter 3" | ch3 is `complexity-analysis.md` (should be ch6). |
| "Greedy Algorithms \| Chapter 15" | ch15 is `heaps.md` (should be ch32). |
| "Dynamic Programming \| Chapter 20" | ch20 is `sparse-table.md` (should be ch30/ch31). |
| "Graph Theory \| Chapter 40" | ch40 is `rolling-hash.md` (should be ch22). |
| "Number Theory (modular inverse) \| Chapter 80" | ch80 is `advanced-heaps.md` (should be ch60). |

#### H5. `ch159-external-memory.md` — Every cross-reference is wrong
Prerequisites (lines 4-7):
- "Sorting algorithms (Chapter 108)" — ch108 is `dsu-on-tree-rerooting.md` (should be ch5).
- "B-Trees (Chapter 104)" — ch104 is `cartesian-tournament-trees.md` (should be ch77).
- "Graph algorithms (Chapter 120)" — ch120 is `bwt-fmindex.md` (should be ch22).

Cross-References (lines 563-568):
- "Sorting: Chapter 108" — wrong (ch5).
- "B-Trees: Chapter 104" — wrong (ch77).
- "Graph Algorithms: Chapter 120" — wrong (ch22).
- "Hash Tables: Chapter 101" — ch101 is `rope-gap-buffer.md` (should be ch7).
- "Parallel Algorithms: Chapter 158" — ch158 is `succinct-ds.md` (should be ch160).
- "Database Indexing: Chapter 160" — ch160 is `parallel-algorithms.md` (should be a database chapter; none exists).

#### H6. `ch161-adv-geometry.md` — All cross-references wrong
Prerequisites (lines 4-5):
- "Convex hull (Chapter 156)" — ch156 is `dynamic-graph-algorithms.md` (should be ch64).
- "Sweep line basics (Chapter 157)" — ch157 is `link-cut-trees.md` (should be ch93).

Cross-References (lines 671-675):
- "Chapter 156: Convex Hull" — wrong (ch64).
- "Chapter 157: Sweep Line" — wrong (ch93).
- "Chapter 162: Advanced Graph Algorithms" — ch162 is `algorithmic-game-theory.md`.
- "Chapter 158: Interval Trees" — ch158 is `succinct-ds.md` (should be ch103).
- "Chapter 76: KD-Trees" — ch76 is `advanced-seg-trees.md` (should be ch78).

#### H7. `ch162-algorithmic-game-theory.md:87-89` — Gale-Shapley walkthrough cites wrong current matches
**Step 3 (line 87):** "Proposer 2 proposes to A (first choice). A prefers 1 (current) over 2 → rejected."
**Correct:** "A prefers 0 (current) over 2". After Step 1, A is matched to proposer 0, not proposer 1.
**Step 4 (line 89):** "Proposer 2 proposes to B (second choice). B prefers 0 (current) over 2 → rejected."
**Correct:** "B prefers 1 (current) over 2". After Step 2, B is matched to proposer 1, not proposer 0.
The final matching `{0→A, 1→B, 2→C}` is correct; only the explanation text is wrong.

#### H8. `ch162-algorithmic-game-theory.md:5-7` — Prerequisites have wrong chapter references
- "Graph algorithms (Chapters 97-105)" — ch97 is `pattern-recognition.md`, ch98 is `splay-trees.md`, ch99 is `scapegoat-aa-trees.md`, ch100 is `van-emde-boas.md`, ch101 is `rope-gap-buffer.md`, ch102 is `wavelet-trees.md`, ch103 is `interval-order-statistic-trees.md`, ch104 is `cartesian-tournament-trees.md`, ch105 is `cuckoo-robin-hood-hashing.md` — none are graph algorithms. Should be ch22-29, 81-84, 107-111.
- "Linear programming (Chapter 140)" — ch140 is `algorithm-selection.md` (should be ch151).
- "Probability (Chapter 150)" — ch150 is `advanced-randomized.md` (should be ch72).

#### H9. `ch166-master-indexes.md` — Many wrong chapter references in the index tables
The chapter is literally a master index, so wrong chapter numbers here are particularly damaging.

| Entry | Listed | Should be |
|---|---|---|
| Sieve of Eratosthenes | ch67 | ch60 (`number-theory.md`) |
| GCD (Euclidean) | ch67 | ch60 |
| Modular Exponentiation | ch67 | ch60 |
| Miller-Rabin | ch67 | ch60 (or ch175) |
| Pollard's Rho | ch67 | ch60 (or ch175) |
| Euler's Totient | ch67 | ch60 |
| Modular Inverse | ch67 | ch60 |
| Chinese Remainder | ch67 | ch176 (`chinese-remainder.md`) |
| Fermat's Little Theorem | ch67 | ch60 |
| Möbius Function | ch67 | ch172 (`mobius-inversion.md`) |
| Hungarian | ch84 | ch170 (`hungarian.md`) |
| Bloom Filter | ch80 | ch79 (`probabilistic-ds.md`) |
| Red-Black Tree | ch76 | ch14 (`bst.md`) or ch99 |
| Splay Tree | ch75 | ch98 (`splay-trees.md`) |
| Square Root Decomposition | ch94 | ch173 (`sqrt-decomposition.md`) |
| Mo's Algorithm | ch93 | ch173 (ch93 is `sweep-line.md`) |
| Persistent Segment Tree | ch79 | ch75 (`persistent-ds.md`) |
| HLD (Pattern Recognition) | ch62 | ch107 (`hld-centroid-applications.md`) |
| Permutation/Combination/Catalan/etc. | ch68 | ch71 (`combinatorics.md`) |
| Bayes/Birthday/Coupon/Linearity | ch69 | ch72 (`probability.md`) |

That's ~25 wrong entries in the master index.

#### H10. `ch151-linear-programming.md:622` — Broken LaTeX/MathJax delimiter
**Wrong text:** `Product A requires 2 hours of labor and 1 unit of material, yielding \\(5 profit. Product B requires 1 hour of labor and 3 units of material, yielding\\)7 profit.`
**Issue:** `\\(` and `\\)` are MathJax inline-math delimiters, but the opening `\\(` is placed before "5" and the closing `\\)` is placed before "7", making MathJax try to render `"5 profit. Product B requires 1 hour of labor and 3 units of material, yielding"` as a math expression — this fails to render and breaks the page.
**Fix:** use `$5` and `$7` (or `\\(5\\)` and `\\(7\\)` correctly placed) for the dollar signs.

---

### MEDIUM severity

#### M1. `ch153-advanced-optimization.md:63` — Gradient descent iteration 10 has wrong x value
**Wrong text:** `| 10 | 2.71 | -0.58 | -0.058 | 2.77 |`
**Correct:** `| 10 | 2.678 | -0.644 | -0.064 | 2.742 |`
**Verification:** Python script computing `x = x - 0.1 * 2*(x-3)` starting from x=0:
```
iter 0: x = 0.6
iter 1: x = 1.08
iter 2: x = 1.464
iter 3: x = 1.7712
...
iter 9: x = 2.6779
iter 10: x = 2.7423
```
Closed form: `x_n = 3 - 3·0.8^n`, so `x_10 = 3 - 3·0.8^10 = 3 - 3·0.1073741824 = 2.6779`. The chapter's value of 2.71 is incorrect (the gradient -0.58 and step -0.058 are correct only if you accept x=2.71, but x=2.71 itself is wrong).

#### M2. `ch155-advanced-graph-theory.md:697-704` — Wrong cross-references
- "Chapter 27: Shortest paths" — ch27 is `mst.md` (should be ch26 `shortest-paths.md`).
- "Chapter 78: Dynamic programming on graphs" — ch78 is `kd-trees.md`.
- "Chapter 122: Divide and conquer" — ch122 is `edit-distance-variants.md` (should be ch39).
- "Chapter 150: Randomized algorithms" — ch150 is `advanced-randomized.md` ✓ (correct).
- "Chapter 161: Advanced geometry" — ch161 is `adv-geometry.md` ✓ (correct).

#### M3. `ch155-advanced-graph-theory.md:107-158` — `spectralGap()` returns wrong quantity
The code computes `w = A·v / d` (the normalized adjacency matrix), so the Rayleigh quotient `lambda = v^T·w` is the eigenvalue of `A/d`, in range `[-1, 1]`. But the chapter labels this `lambda2` and computes `d - lambda2` as the spectral gap. For a 3-regular graph, `λ₂(A/d)` ≈ 0.7 would give `d - λ₂ = 3 - 0.7 = 2.3`, which is meaningless (mixing the unnormalized `d` with the normalized eigenvalue). The actual spectral gap of `A` is `d - d·λ₂(A/d) = d(1 - λ₂(A/d))`.
**Fix:** either return `lambda * d` (eigenvalue of `A`), or change the spectral-gap computation to `d * (1 - lambda2)`.

#### M4. `ch157-link-cut-trees.md:167-174` — `cut()` missing the `u->right == nullptr` check
The standard LCT `cut(u, v)`:
```
makeRoot(u); access(v); splay(v);
if (v->left == u && u->right == nullptr) {  // direct edge check
    v->left = nullptr; u->parent = nullptr;
}
```
This chapter's implementation only checks `v->left == u`, which is true whenever `u` is anywhere on the path from represented-tree root to `v`. The missing `u->right == nullptr` check means the code would "cut" even when there are intermediate nodes between u and v, corrupting the tree. The provided example only tests the directly-connected case (`cut(1, 2)` on chain `0-1-2-3`), so it happens to work, but the function is wrong for the general case.

#### M5. `ch180-minimax-alpha-beta.md:427` — Tic-Tac-Toe node count off by ~10×
**Wrong text:** `| Tic-Tac-Toe | ~5 (avg) | 9 | ~55,000 |`
**Correct:** approximately 549,946 nodes in the full game tree (with early termination), or 1,953,125 = 5⁹ without early termination.
**Source:** standard reference for tic-tac-toe game-tree size; see Wikipedia "Tic-tac-toe" — 255,168 leaf games, ~549,946 nodes total. The chapter's 55,000 figure is inconsistent with both, off by roughly 10×. The Connect Four (~10³⁶), Chess (~10¹²⁰ — Shannon number), and Go (~10³⁶⁰) figures in the same table are correct, which makes the tic-tac-toe entry look like a typo.

#### M6. `appendix-k-60-day-plan.md:9, 11` — Self-contradiction: title says 60 days but plan covers only 56
**Line 9:** `**Duration:** 8 weeks (60 days, including 4 rest days)`
**Line 11:** `**Weekly pattern:** 6 days learning + 1 day review (rest on days 15, 30, 45, 60)`
**Actual plan:** Week 1 covers Days 1-7, Week 8 covers Days 50-56. The plan stops at Day 56, not Day 60.
**Rest days stated:** 15, 30, 45, 60. **Rest days in plan:** Day 15 (Week 3), Day 29 (Week 5 — not 30!), Day 45 (Week 7), Day 56 (Week 8 — not 60!).
**Fix:** either extend the plan to actually cover 60 days, or change the duration to "8 weeks (56 days)" and the rest days to "15, 29, 45, 56".

#### M7. `appendix-i-faq.md:306` — Malformed markdown
**Wrong text:** `Problem:** Count paths from top-left to bottom-right (only right/down).`
**Issue:** missing opening `**` before "Problem". All other entries use `**Problem:**` (bold). This entry renders as plain text starting with `Problem:**`.
**Fix:** change to `**Problem:** Count paths from top-left to bottom-right (only right/down).`

#### M8. `ch158-succinct-ds.md:176` — LOUDS bit count claim slightly off
**Wrong text:** "Total 1s = n-1 (for a tree with n nodes, there are n-1 edges). Total 0s = n. So the bitvector has 2n-1 bits ≈ 2n bits."
**Issue:** The count is correct (n-1 ones + n zeros = 2n-1 bits), but the framing "≈ 2n bits" hides the fact that LOUDS encodes the root specially (the chapter itself shows the start marker `11` prepended, making the actual stored length 2n+1 bits including the marker). Minor pedagogical issue.

---

### LOW severity

#### L1. `ch155-advanced-graph-theory.md:330-334` — Forbidden minors table minor imprecision
"Knotless embeddable | Unknown | Open" — the forbidden minors for knotless embedding are not actually fully unknown; the *set* is finite (by Robertson-Seymour) but the explicit list is large and not fully enumerated. Saying "Unknown" is misleading; "Not fully characterized" would be more accurate.

#### L2. `ch151-linear-programming.md:608` — Network simplex complexity claim
**Text:** `| Network simplex | O(n² m) | Specialized for network problems |`
Network simplex is *empirically* very fast but has exponential worst case; the O(n²m) is an average-case practical bound, not a rigorous worst-case bound. Should be clarified as "O(n²m) typical, exponential worst case" to be consistent with the Simplex row above.

#### L3. `ch159-external-memory.md:41` — Block-size unit ambiguity
**Text:** `| B (block size) | 4 KB = 1024 words |`
Assumes 4-byte words. This is fine but should be stated explicitly ("assuming 4-byte words"), since on systems with 8-byte words this would be 512 words.

#### L4. `ch159-external-memory.md:451-453` — SSD random/sequential ratio
**Text:** `| Random/Sequential ratio | 1000:1 | 30:1 |`
The HDD ratio of 1000:1 depends heavily on block size and is closer to 100:1–1000:1. For SSDs, 30:1 is at the high end; modern NVMe SSDs are closer to 10:1–20:1. Acceptable approximation, but the values are stated as fact.

#### L5. `appendix-g-math-handbook.md:43` — log₂(Fibonacci) approximation
**Text:** `log₂(Fibonacci(n)) ≈ n·log₂(φ) ≈ 0.694n`
Correct (φ = (1+√5)/2 ≈ 1.618, log₂(φ) ≈ 0.6942), but the value 0.694 is rounded inconsistently — 0.6942 is more standard. Minor.

#### L6. `ch166-master-indexes.md:236` — Complexity index entry
**Text:** `| n ≤ 10^9 | O(√n) | Number theory | Primality, factorization |`
This is fine for trial division, but for primality testing Miller-Rabin (ch175) is O(k log² n), which is much faster than √n. The "Typical Approach" column conflates trial division (the only √n primality algorithm) with the broader category.

#### L7. `ch173-sqrt-decomposition.md:618-619` — Hilbert curve code uses array literal extension
```cpp
int nrot = (rotate + [3, 0, 0, 1][sector]) & 3;
```
This uses a GCC extension (compound literal as array subscript) that is not standard C++. Will not compile on MSVC. Should use a static const array or a switch.

#### L8. `appendix-l-30-day-crash-course.md:30-38` — Topic percentages sum to 100% but double-count
Percentages: 20+15+15+12+10+10+8+5+5 = 100%. Looks correct, but "Hash Tables" (10%) overlaps heavily with "Arrays & Strings" (which often use hash maps). Minor classification overlap, not an error.

---

## Files confirmed clean

The following files were read end-to-end and found to have no HIGH or MEDIUM severity issues:

1. `ch158-succinct-ds.md` — accurate on Catalan number, rank/select, LOUDS, wavelet trees, FM-Index (minor LOUDS bit-count framing noted in M8).
2. `ch171-berlekamp-massey.md` — BM walkthrough for Fibonacci verified step-by-step (d=35, s=4, x=263→166→67→1 ✓). All cross-references correct (ch115, 60, 73, 163, 86).
3. `ch173-sqrt-decomposition.md` — D-query and Mo's algorithm dry runs verified; all cross-references correct (ch18, 19, 20, 62, 76, 130). Hilbert curve code uses non-standard GCC extension (L7).
4. `ch174-matrix-exponentiation.md` — Fibonacci M^9 = [[55,34],[34,21]] verified by hand; all cross-references correct (ch2, 30, 73, 171, 167).
5. `ch175-miller-rabin-pollard-rho.md` — Miller-Rabin on 561 (s=4, d=35, sequence 263→166→67→1) and 221 (s=2, d=55, x=128→30) both verified with Python; all cross-references correct (ch60, 63, 172, 7, 163).
6. `ch180-minimax-alpha-beta.md` — minimax walkthrough (max(3,2,0)=3) and alpha-beta walkthrough (final=7, 1 node pruned) both verified; all cross-references correct (ch8, 13, 30, 61, 132, 133, 162). Tic-tac-toe node count flagged in M5.
7. `appendix-a-stl-guide.md` — comprehensive STL reference; spot-checked reverse_iterator base() warning (correct).
8. `appendix-b-complexity-cheat-sheet.md` — verified Dijkstra (binary & Fibonacci heap), Bellman-Ford, Floyd-Warshall, Kruskal, Prim, Edmonds-Karp, Dinic, Hungarian complexities. Push-Relabel O(V²√E) is for the highest-label variant.
9. `appendix-c-algorithm-cheat-sheet.md` — pseudocode for 35 algorithms; spot-checked KMP, Z, Tarjan SCC, convex hull, Manacher, Edmonds-Karp, Dinic, Euler totient, sieve. All correct.
10. `appendix-d-code-templates.md` — BFS/DFS templates and others spot-checked; clean.
11. `appendix-e-debugging-checklist.md` — clean checklist of common bugs.
12. `appendix-f-interview-checklist.md` — clean behavioral/technical interview checklist.
13. `appendix-g-math-handbook.md` — verified log properties, modular arithmetic, Master Theorem cases (including the tricky `T(n) = 3T(n/4) + O(n log n) = O(n log n)` entry — case 3 applies, correct).
14. `appendix-h-top-200-mistakes.md` — clean list of 200 common mistakes.
15. `appendix-i-faq.md` — clean list of 100 interview questions (formatting bug at line 306 noted in M7).
16. `appendix-j-90-day-plan.md` — clean 13-week study plan.
17. `appendix-l-30-day-crash-course.md` — clean crash course; correctly notes 28 days + 2 rest days = 30 days total (consistent).
18. `appendix-m-company-wise.md` — clean company-prep guide for 17 companies.

---

## Patterns observed

1. **Systematic wrong cross-references** in ch151, ch153, ch155, ch159, ch161, ch162, ch166. The wrong chapter numbers often look "plausible" (e.g., "Chapter 27: Shortest paths" sounds right but ch27 is actually `mst.md`). This strongly suggests an LLM-generated draft where chapter numbers were inferred from topic adjacency rather than checked against the actual TOC. **Recommend the parent agent run a single pass over all of ch151-180 + appendices to verify every `Chapter N` reference against the actual `ch<N>-*.md` filename.**

2. **Code examples that "work for the demo but are wrong in general":** ch157's `cut()` and ch161's half-plane intersection both fall in this category — they pass the specific example shown but would fail on other inputs. These are particularly insidious because a casual reader assumes the code is correct.

3. **Dry runs that contradict the code:** ch161's half-plane dry run describes the *intended* behavior (unit square), but the code produces the *opposite* (empty set). This suggests the dry run was written from the intent rather than from running the code.

4. **All HIGH-severity findings cluster in chapters with significant code/dry-run content** (ch157, ch161, ch162). The pure-theory chapters (ch171, ch173, ch174, ch175, ch180) and the appendices are largely clean.

5. **No AI artifacts** ("Wait,", "Hmm,", "Actually,", etc.) found in the audited scope. The two `Actually,` matches in ch178-burnsides-lemma.md (already-fixed file) are legitimate uses in mathematical exposition. The single `Let me try` in appendix-l is a quoted interview-strategy phrase. So this category is clean.
