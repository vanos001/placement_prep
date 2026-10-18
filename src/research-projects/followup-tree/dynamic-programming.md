# Follow-up Tree: Dynamic Programming

## Overview

"What is dynamic programming?" is the classic second-round algorithms question, and it escalates faster than almost any other because the follow-ups are not about the *technique* — they are about the *judgment* the technique demands: how to choose a state, when to add a dimension, when to throw memory at the problem and when to take it back. Candidates who memorized "memoization means a cache" stall at rung three; candidates who can articulate *what a state is* keep climbing. This page walks the ladder: each follow-up's purpose, the reasoning, and the answer with its edge cases. The worked mechanics live in [DP Fundamentals](../../dsa/chapters/ch30-dp-fundamentals.md) and [DP Patterns](../../dsa/chapters/ch31-dp-patterns.md); this chain is about how to think when the pattern is not on the shelf.

## The Opening Question

**"What is dynamic programming?"**

The expected core answer: dynamic programming is a technique for problems that have **overlapping subproblems** — the same subproblem is reached many times — and **optimal substructure** — an optimal solution is composed of optimal solutions to subproblems. Solve each distinct subproblem once, store its result, and reuse it. The naive recursion for Fibonacci makes ~2.7 million calls at n = 30 (2·F(31)−1, exactly 2,692,537) because fib(28) is recomputed inside fib(30) and fib(29) and again at every ancestor; memoization collapses the recursion tree to the n distinct states, and the cost drops from exponential to O(n).

Why this answer is correct: it names *both* preconditions, and the two rungs of the ladder hang off them separately. Optimal substructure is what makes "solve the smaller problem first" valid at all; overlapping subproblems is what makes storing the results *pay*. Merge sort has optimal substructure but no overlap — its subproblems are disjoint — so there is nothing to memoize and no DP. Reciting that contrast unprompted is the sentence that tells the interviewer which kind of candidate is sitting there. (The name itself is history, not meaning: Bellman picked "dynamic programming" in the 1950s partly to make it unattractive to funding reviewers who feared the word "research"; do not try to derive technique from the name.)

## Follow-up 1: Memoization or Tabulation — Does It Matter Which?

**What it tests:** whether you understand the two implementations as trade-offs rather than synonyms, and can pick one for a stated constraint.

**How to reason:** both compute the same table; the differences are *when* states are computed, *where* the stack lives, and *what* you can optimize afterward.

**Answer.** **Memoization** (top-down) keeps the natural recursion and adds a lookup — usually a hash table — before computing. **Tabulation** (bottom-up) iterates over states in dependency order and fills an array. Four practical differences: memoization computes *only reachable states*, which matters when the state space is huge but few states are actually hit; tabulation pays for the full enumeration but avoids recursion entirely, so there is no stack-overflow risk at depth 10⁵ and better constant factors from array access; tabulation makes the *evaluation order explicit*, which is the prerequisite for the space-optimization tricks of Follow-up 3; and memoization's cache is exactly a hash table, with the amortized-O(1)-with-latency-spikes behavior documented in [Hash Tables](./hash-tables.md) — a memo table that grows mid-run is a hash table resizing mid-run. The senior sentence: tabulate when the state space is small and dense, memoize when it is large and sparse, and know that the choice is about *reachable states*, not style.

Edge cases worth volunteering: memoized recursion on a deep chain (a DP over a 10⁶-long sequence) can blow the call stack even though the state count is small — the fix is an explicit stack or switching to tabulation; and a tabulation with a wrong iteration order silently computes garbage, because the order *is* the correctness argument (it is a topological order of the dependency DAG — the same structure as [Dependency Resolution](../connection-atlas/dependency-resolution.md) maps for build systems).

## Follow-up 2: "Now Add a Constraint" — How Do You Extend the State?

**What it tests:** the actual DP skill. Anyone can fill a template; extending a state when the problem changes is what interviews are probing.

**How to reason:** a state is the *minimal summary of the past that the future depends on*. When a new constraint arrives, ask what the current state can no longer tell you, and add exactly that.

**Answer.** The escalation pattern is always the same move. 0/1 knapsack: state is (items seen, capacity left) — the future depends only on remaining capacity, not which items were taken. Now add "at most k transactions" to a stock-profit problem: the state must also remember how many transactions remain, so the dimension count goes up by one — the general form is "if a new constraint can change what is legal next, it becomes a dimension." Now add "each item can be used once *and order matters*": order is information the state does not carry, and you either add it or prove it is irrelevant. The expensive escalation is the **bitmask**: when the future depends on *which subset* of n items has been used (traveling salesman: which cities visited), the state is (last node, visited-set) and the complexity is O(n²·2ⁿ) — the interview tell is a constraint like "n ≤ 20," which is the fingerprint of an intended 2ⁿ state space. Between "add a dimension" and "bitmask" sits **profile DP** (states describe a boundary strip across a grid) and **digit DP** (states carry "am I still pinned to the upper bound's prefix?"); the repo's [DP Optimization](../../dsa/chapters/ch86-dp-optimization.md) and [Profile DP](../../dsa/chapters/ch113-profile-dp.md) chapters own those mechanics.

The edge case that separates candidates: after extending the state, *re-derive the complexity* — states × transitions. Adding one dimension of size k multiplies the table by k, and interviewers watch whether you say "O(n·W·k)" out loud or keep claiming the old bound. And sometimes the right response to "add a constraint" is the reverse move: prove the new constraint is *implied* by the current state and refuse to add anything — that refusal, argued correctly, scores higher than a bigger table.

## Follow-up 3: Memory Is Tight — What Can You Throw Away?

**What it tests:** whether you know the dependency structure well enough to exploit it — the reward for making evaluation order explicit in Follow-up 1.

**How to reason:** look at each state's dependencies. If they span a bounded window of the previous dimension, only the window must live in memory.

**Answer.** If row i depends only on row i−1 (LCS, edit distance), keep two rows: O(n·m) time, O(m) space. If it depends on i−1 and i−2 (Fibonacci-style), keep two scalars. The subtlety interviewers probe: 0/1 knapsack's 2D table `dp[i][w]` collapses to a single 1D array only if you iterate `w` **downward** — upward iteration reuses the current row and lets one item be counted twice (that is the *unbounded* knapsack instead). Getting the loop direction right, and being able to say why, is the difference between reciting the trick and understanding it. The catch is **reconstruction**: two rows cannot hold parent pointers, so either store the choice per state while computing (giving memory back) or recompute — Hirschberg's algorithm recovers an optimal LCS in O(min(n,m)) memory by divide-and-conquering the split point, at the cost of a constant-factor time increase. Volunteering that "answer-only is cheap, path-reconstruction is the cost" is the seniority marker. Note the time complexity *never improves* here — space optimization is a memory play, with a cache-locality side benefit when the working set shrinks.

## Follow-up 4: When Does Greedy Beat DP — and How Do You Prove It?

**What it tests:** whether you can distinguish the two techniques by their structural requirements, rather than reaching for DP by default or greedy by optimism.

**How to reason:** greedy makes one irrevocable local choice and never revisits; that is only sound if a local choice can be *exchanged* into some optimal solution without loss. Ask for that proof; if you cannot produce it, fall back to DP.

**Answer.** **Interval scheduling** (maximize non-overlapping meetings) admits greedy by earliest finish time: the exchange argument holds — the interval that ends first can replace the first interval of any optimal solution. **Fractional knapsack** is greedy by value density. **0/1 knapsack is not**: taking the densest item can evict two items whose combined value is higher, and the state (capacity remaining, items available) genuinely matters — hence DP at O(n·W), which is *pseudo-polynomial*: W is a numeric value, not an input length, a distinction [Complexity Claims](../assumptions-hunt/complexity-claims.md) treats in detail. The cost comparison is the payoff line: greedy is O(n log n), DP is O(n·W) or O(n²) — greedy wins by an order of magnitude *when its proof exists*, and the proof is the whole game. The classic interview trap: coin change with arbitrary denominations (greedy fails on {1, 3, 4} for target 6: 4+1+1 = 3 coins vs 3+3 = 2) — which is why "just use greedy, it's obvious" on an unknown coin system is the wrong answer, and a one-line counterexample is the right one. For the full greedy toolkit and its exchange-argument proofs, see [Greedy](../../dsa/chapters/ch32-greedy.md).

## Follow-up 5: You Have Never Seen This Problem — How Do You Recognize DP?

**What it tests:** the transfer skill. The interviewer picks an unfamiliar problem precisely to see whether you have a *procedure* for state discovery, not a memory of LeetCode indices.

**How to reason:** DP recognition is pattern-of-question plus state-discovery procedure. Run the procedure aloud; the interviewer is grading the method.

**Answer.** The question shapes that signal DP: "count the number of ways," "minimum/maximum cost over a sequence of decisions," "is it possible to…", "longest/shortest X," strings or grids with n up to a few thousand (a hint of O(n²) states), or answers requested modulo 10⁹+7 (counting without big integers). Given a candidate problem, the discovery procedure is: (1) **weaken the question** — define the answer for a *prefix* of the input ("best value using the first i items"); (2) ask what the last decision was and what information suffices to keep deciding — that information set *is* the state; (3) write the transition as "take the last decision back out"; (4) check optimal substructure with a cut-and-paste argument (if the sub-solution were not optimal, swap in a better one and improve the whole — contradiction); (5) order the states so every dependency is ready — a topological order of the dependency DAG, the same notion as [Dependency Resolution](../connection-atlas/dependency-resolution.md). Complexity falls out as states × transitions, and the escalations of Follow-up 2 apply when a constraint breaks step 2.

The honest boundary: some problems look like DP but have *no* usable state because the future depends on unbounded history — that failure mode is itself diagnostic, and the response ("my state explodes; I would look for greedy structure, a different formulation, or an approximation") is a senior answer. What you should never do is force a table onto a problem whose transitions do not close.

## How to Approach Unfamiliar Variations

The transferable template for DP follow-ups:

1. **Say what the state means in one sentence before writing any code.** "dp[i][w] = the maximum value using the first i items with capacity w" — if that sentence has an "and" with two clauses, you have two dimensions; if it cannot be said at all, the formulation is not ready. Most wrong DP answers are wrong state definitions wearing correct code.
2. **When a constraint appears, ask what the state can no longer tell you.** Add exactly that as a dimension — or prove it derivable from what the state already holds and refuse. Complexity is states × transitions; re-derive it after every change.
3. **Read the dependency window off the transition, then size the memory to the window.** Two rows when the window is 1; Hirschberg-style recompute when the path must be reconstructed. Loop direction is part of the correctness argument for collapsed dimensions (downward for 0/1 knapsack).
4. **Demand a proof before believing a greedy shortcut.** One clean exchange argument, or back to DP. A counterexample hunt ({1,3,4} → 6) takes thirty seconds and settles the question.
5. **Check reachability before choosing memoization vs tabulation.** Sparse reachable states in a huge space → memoize; dense space with depth risk → tabulate; and remember the memo table is a hash table with hash-table failure modes.

## Interview Questions

**Q: Why is the Fibonacci recursion exponential if there are only n distinct states?**
A: Because the *recursion tree* has O(2ⁿ) nodes but only O(n) distinct labels — every subtree of fib(n−2) duplicates work already done inside fib(n−1). Memoization deduplicates by label, so cost drops to the number of distinct states times O(1) work. That "tree size vs distinct states" gap is the entire economic case for DP.

**Q: Your memoized solution passes small tests and stack-overflows on the real input. Diagnose.**
A: The state *graph* is small but its longest chain is deep — memoization still recurses to the bottom of the first dependency chain before anything is cached. Fix: tabulate in dependency order (or convert to an explicit stack). The memory profile changes too: tabulation's peak is the table, not the call stack plus the table.

**Q: A teammate insists greedy by ratio solves their 0/1 knapsack packaging problem. Response?**
A: A counterexample, not an argument: capacity 10, items (value 6, size 6), (value 5, size 5), (value 5, size 5) — greedy takes the first and stops at 6; optimal is 10. Greedy is fine for the fractional version; the 0/1 constraint is exactly what breaks the exchange argument. If they need 0/1 and n·W is tractable, it is a DP afternoon.

**Q: When is a bitmask state the *wrong* answer to a "n ≤ 20" problem?**
A: When the subset information is reconstructible from a cheaper summary — e.g., if items are processed in a fixed order, a small counter or boundary index may carry the same information. The bitmask is right when membership itself matters for future decisions (TSP, set-cover style); checking for that reconstructibility before committing to 2ⁿ states is the move.

## Key Takeaways

- Dynamic programming = overlapping subproblems + optimal substructure, and the whole cost model is "distinct states × cost per transition" — the naive recursion's exponential tree is a duplication artifact, not intrinsic difficulty.
- Memoization computes reachable states lazily; tabulation enumerates in dependency order, and that explicit order is what later enables space compression and prevents silent garbage.
- Extending a state = adding exactly the information a new constraint makes necessary; refusing to add a derivable dimension, argued correctly, is the stronger answer.
- Space optimization reads the dependency window off the transition — with loop direction as part of correctness — and answer-only computation is cheap while path reconstruction costs memory or time.
- Greedy beats DP only where an exchange argument exists; elsewhere it is a faster wrong answer. Recognition of unfamiliar DP problems is a *procedure*: weaken the question, extract the state, close the transitions, order the DAG.

## Cross-References

- [DP Fundamentals](../../dsa/chapters/ch30-dp-fundamentals.md) — the canonical problems and the state/transition notation this chain uses.
- [DP Patterns](../../dsa/chapters/ch31-dp-patterns.md) — knapsack, LCS, edit distance, and the family tree of standard states.
- [DP Expanded](../../dsa/chapters/ch59-dp-expanded.md) — the deeper catalog of DP formulations and their variations.
- [DP Optimization](../../dsa/chapters/ch86-dp-optimization.md) — monotonicity, convex hull trick, and divide-and-conquer optimization for slow transitions.
- [Profile DP](../../dsa/chapters/ch113-profile-dp.md) — bitmask/profile states for grids and tilings.
- [Greedy](../../dsa/chapters/ch32-greedy.md) — exchange arguments and where greedy's proof obligations live.
- [Divide and Conquer](../../dsa/chapters/ch39-divide-conquer.md) — the no-overlap sibling: why merge sort is not a DP.
- [Recursion Is Always Slower](../misconceptions/recursion-always-slower.md) — the misconception this chain's memoization rung refines.
- [Complexity Claims](../assumptions-hunt/complexity-claims.md) — pseudo-polynomial vs polynomial, and what O(nW) really promises.
- [Dependency Resolution](../connection-atlas/dependency-resolution.md) — topological order as the shared structure of DP evaluation and build systems.
- [Incremental Computation](../connection-atlas/incremental-computation.md) — memoization as a special case of reuse-under-change; the sibling deep-dive.
- [Hash Tables](./hash-tables.md) — the memo table's own data structure, with all its amortized behavior.
