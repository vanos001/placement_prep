# Chunk B Audit — DSA Chapters 31-90

**Scope:** ch31-90 (skipping already-fixed: ch31-47, ch53-60, ch70, ch72, ch73, ch75, ch81-83, ch85, ch88)
**Files audited:** 26
**Files clean:** 14
**Total findings:** 11

## Audited files

ch48, ch49, ch50, ch51, ch52, ch61, ch62, ch63, ch64, ch65, ch66, ch67, ch68, ch69, ch71, ch74, ch76, ch77, ch78, ch79, ch80, ch84, ch86, ch87, ch89, ch90

## Findings

### HIGH severity

#### ch87-suffix-tree.md:36
- **Wrong text:** `A suffix tree is a compressed trie (radix tree) of all suffixes of a string S\(, where\) is a unique terminator not appearing in S.`
- **Correct text:** `A suffix tree is a compressed trie (radix tree) of all suffixes of a string S$, where $ is a unique terminator not appearing in S.`
- **Verification:** File inspection — the `$` characters were mangled into `\(` and `\)` (LaTeX inline-math delimiters) by some prior processing step. The surrounding text says "For S = \"banana$\"" (line 38) using the literal `$`, confirming the intended character.
- **Justification:** Text is unreadable in rendered output — MathJax consumes the text between `\(` and `\)` as math content.

#### ch87-suffix-tree.md:82
- **Wrong text:** `...we work with an **implicit suffix tree** — the suffix tree of S[0..i] without the \(terminator. Internal nodes may have only one child. We convert to the explicit suffix tree at the end by adding\).`
- **Correct text:** `...we work with an **implicit suffix tree** — the suffix tree of S[0..i] without the $ terminator. Internal nodes may have only one child. We convert to the explicit suffix tree at the end by adding $.`
- **Verification:** Same processing-mangle pattern as line 36. The original `$` characters surrounding the word "terminator" were converted to `\(` / `\)`.
- **Justification:** Text is unreadable; the entire sentence between `\(` and `\)` is consumed as inline math.

#### ch87-suffix-tree.md:152
- **Wrong text:** `Suffixes: banana\(, anana\), nana\(, ana\), na\(, a\), $`
- **Correct text:** `Suffixes: banana$, anana$, nana$, ana$, na$, a$, $`
- **Verification:** Compare with the code-block listing on lines 42–48 which shows the correct suffixes (`banana$`, `anana$`, …). The dollar signs at end-of-word were mangled.
- **Justification:** The text lists suffixes of "banana$" but every `$` (except the trailing one) was replaced by LaTeX delimiters, so the line is garbled.

#### ch49-behavioral.md:284
- **Wrong text:** `**Result**: "The system was back up within 45 minutes of my involvement. The hot-patch prevented the issue from recurring during the rest of the flash sale, which went on to generate \(2M in revenue. The runbook and monitoring I added caught a similar leak two months later before it caused an outage, saving an estimated\)100K in potential lost revenue."`
- **Correct text:** `**Result**: "The system was back up within 45 minutes of my involvement. The hot-patch prevented the issue from recurring during the rest of the flash sale, which went on to generate $2M in revenue. The runbook and monitoring I added caught a similar leak two months later before it caused an outage, saving an estimated $100K in potential lost revenue."`
- **Verification:** Same `$` → `\(` / `\)` mangle as ch87. Line 278 of the same STAR example uses `$50,000` correctly inside an opening quote, so MathJax opens inline math at `$2M` and closes it at `$100K`, swallowing the intervening prose.
- **Justification:** A large span of the STAR-example Result text is consumed as inline math and disappears in the rendered output.

#### ch74-skip-lists.md:170
- **Wrong text:** `E[h] = Σ_{k=1}^{∞} P(level ≥ k) = Σ_{k=1}^{∞} (1/2)^k = 1 + 1 = O(log n)`
- **Correct text:** `The expected height of a skip list with n nodes is log_{1/p}(n) + O(1) = log₂(n) + O(1) for p = 1/2. (Derivation: P(no node reaches level k) = (1 − 1/2^k)^n ≈ e^{−n/2^k}; this transitions from ~1 to ~0 around k = log₂ n, so E[h] ≈ log₂ n.)`
- **Verification:** Python — `sum((1/2)**k for k in range(1, 100))` returns `1.0`, not 2. The geometric series Σ_{k=1}^∞ (1/2)^k = 1. The formula as written computes the expected level count of a *single* node (=1), not the expected maximum level (height) of n nodes. Line 102 of the same chapter already gives the correct `E[h] ≈ log₂(n) + 1`, so lines 102 and 170 contradict each other. Line 176 also says "1 + 1/2 + 1/4 + ... = 2" (the standard expected-pointer count), directly contradicting the "1 + 1 = O(log n)" step on line 170.
- **Justification:** Mathematical derivation is wrong (sum value, formula meaning, and conclusion), and it contradicts other formulas in the same chapter.

#### ch52-memory-hardware.md:386–413
- **Wrong text:** The false-sharing benchmark defines `struct Bad { std::atomic<long long> counter_a{0}; std::atomic<long long> counter_b{0}; };` but the templated `benchmark()` accesses `counters.counter_a.value.fetch_add(...)` (line 391, 395) — `.value` does not exist on `std::atomic<long long>`.
- **Correct text:** Either (a) make `Bad` mirror `Good`'s shape — `struct Bad { PaddedCounterUnpadded counter_a; ... };` — or (b) template-specialise the accessor so the template can call `counters.counter_a.fetch_add(...)` for `Bad` and `counters.counter_a.value.fetch_add(...)` for `Good`. Simplest fix: change `Bad` to `struct Bad { struct { std::atomic<long long> value{0}; } counter_a, counter_b; };` so the `.value` access works for both.
- **Verification:** C++ standard — `std::atomic<long long>` has no `.value` member; the only member fetch_add is invoked on directly. `g++` would emit "no member named 'value' in 'std::atomic<long long>'".
- **Justification:** The chapter's flagship code example for false-sharing does not compile as written.

### MEDIUM severity

#### ch62-offline-algorithms.md:192
- **Wrong text:** `| N^(2/3) | O(N^(2/3) × Q^(1/2)) | For Mo's with updates |` (in the "Block Size Optimization" table)
- **Correct text:** `| N^(2/3) | O((N+Q) · N^(2/3)) ≈ O(N^(5/3)) when N=Q | For Mo's with updates (3D Mo's) |`
- **Verification:** Web search — Codeforces blog entry 83630 ("Mo's algorithm and 3D Mo") and the standard reference both state the complexity of 3D Mo's with block size N^(2/3) is O((N+Q)·N^(2/3)). When N = Q this is O(N^(5/3)). The formula `O(N^(2/3) × Q^(1/2))` does not match any standard reference.
- **Justification:** Wrong asymptotic complexity taught for Mo's-with-updates.

#### ch79-probabilistic-ds.md:171,224,225,226
- **Wrong text:** `std::cout << "Estimated distinct: " << hll.estimate() << " (actual: 10000)\\n";` (line 171); similarly `<< "\\n"` on lines 224, 225, 226.
- **Correct text:** `<< "\n"` (single backslash) — produces a newline.
- **Verification:** C++ standard — `"\\n"` is a 2-character string literal (backslash + 'n'), not a newline. The double backslash appears in the source markdown and is preserved verbatim by mdbook into the code block, so the printed output is the literal text `\n`, not a newline.
- **Justification:** Sample program output is incorrect / confusing; beginners may copy the code expecting newlines.

#### ch86-dp-optimization.md:289,296
- **Wrong text:** `std::cout << "Distance matrix is Monge: " << isMonge(A) << "\\n";` (line 289); `<< "\\n"` on line 296.
- **Correct text:** `<< "\n"` (single backslash).
- **Verification:** Same as ch79 — `"\\n"` is a 2-character literal, not a newline.
- **Justification:** Sample program output is incorrect / confusing.

#### ch80-advanced-heaps.md:412
- **Wrong text:** `| Pairing | O(1) | O(log n) amort | O(log log n)* | O(1) |` (decrease-key column for Pairing Heap in the summary table)
- **Correct text:** `| Pairing | O(1) amort | O(log n) amort | O(log n) amort (best known bound O(2^(2√log log n)) by Pettie 2005) | O(1) amort |`
- **Verification:** Web search — Wikipedia "Pairing heap" and Pettie's FOCS 2005 paper "Towards a Final Analysis of Pairing Heaps" give the best known amortized bound for decrease-key as O(2^(2√log log n)) — sublogarithmic but **not** O(log log n). The asterisk in the table has no corresponding footnote. The conjectured optimal is O(1), not O(log log n). Fredman et al.'s original 1986 paper gives the O(log n) amortized bound that most textbooks cite.
- **Justification:** Wrong complexity claim with an undefined footnote marker; readers may believe a tighter bound than is actually proven.

#### ch78-kd-trees.md:92–94
- **Wrong text:** Dry-run step 1: `1. At root (5,4): dist=1.0, best=(5,4) / Split on x: target x=5, go left (x<5) first`
- **Correct text:** `1. At root (5,4): dist=1.0, best=(5,4) / Split on x: target x=5, diff = 0 → code's ternary "diff < 0 ? left : right" sends us right first` (or change the code on line 175 to `diff < 0 ? node->right : node->left` to match the dry-run, or change the dry-run to say "go right first").
- **Verification:** Code inspection of line 175 — `KDNode* first = diff < 0 ? node->left : node->right;`. With target.x = 5 and node.x = 5, diff = 0, so `first = node->right`, but the dry-run says "go left (x<5) first". The final answer (5,4 at distance 1.0) is still correct, but the traversal order described does not match the code.
- **Justification:** Dry-run narrative contradicts the listed code; readers tracing the code will be confused.

### LOW severity

#### ch76-advanced-seg-trees.md:362
- **Wrong text:** In `SlidingWindowMin::refill()`: `int val = in.top().first; int newMin = in.top().second; in.pop(); int minVal = out.empty() ? val : std::min(val, out.top().second);` — `newMin` is assigned but never used.
- **Correct text:** Remove the dead `int newMin = in.top().second;` line.
- **Verification:** Code inspection — `newMin` is read from `in.top().second` but never used; `minVal` is recomputed from `val` and `out.top().second`.
- **Justification:** Dead variable; harmless but suggests leftover refactoring.

#### ch76-advanced-seg-trees.md:380–384
- **Wrong text:** `SlidingWindowMin::getMin()` uses `INT_MAX` (line 382) and `std::min` (line 384), but the snippet's only includes are `<iostream>` and `<stack>` (line 350–351).
- **Correct text:** Add `#include <climits>` and `#include <algorithm>`.
- **Verification:** C++ standard — `INT_MAX` is defined in `<climits>`; `std::min` in `<algorithm>`.
- **Justification:** Snippet won't compile without the missing includes.

#### ch89-engineering-cache.md:311
- **Wrong text:** `In AoS, each Particle_AoS is 28 bytes (7 floats + int).`
- **Correct text:** `In AoS, each Particle_AoS is 32 bytes (7 floats × 4 bytes + 1 int × 4 bytes = 32 bytes).`
- **Verification:** Python — `7*4 + 4 = 32`. The struct definition (line 254–259) has 7 floats (x, y, z, vx, vy, vz, mass) plus 1 int (id) = 32 bytes. The text says "28 bytes" but the parenthetical "7 floats + int" implies 8 fields = 32 bytes; the "28" matches only the 7 floats and forgot the int.
- **Justification:** Wrong arithmetic in a worked example; the surrounding argument about cache lines depends on this size.

## Files confirmed clean

- ch48-technical-communication.md
- ch50-mock-interviews.md
- ch51-computational-thinking.md
- ch61-game-theory.md (verified Grundy numbers, Wythoff P-positions, subtraction-game periodicity with Python)
- ch63-randomized-algorithms.md
- ch64-geometry.md (cross-product orientation table is internally consistent, though it uses a non-standard sign convention compared to the C++ helper later in the same chapter — confusing but not wrong)
- ch65-searching-expanded.md (UCS example verified with Python: 0→1→3→4 = 5 ✓)
- ch66-interview-engineering.md
- ch67-algorithmic-thinking.md
- ch68-problem-modeling.md
- ch69-correctness-proofs.md
- ch71-combinatorics.md (verified nCr/nPr, stars-and-bars, Catalan, derangements, Stirling, Bell with Python — all correct)
- ch77-btrees.md
- ch84-tree-algorithms-advanced.md
- ch90-cpp-deep-dive.md
