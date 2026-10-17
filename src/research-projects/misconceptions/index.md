# Misconception Elimination Project

## Overview

This collection targets ten widely repeated claims that survive interviews,
code reviews, and design documents because each one contains a kernel of truth.
The format is deliberately adversarial but fair: each page states the claim in
its strongest common form, renders a verdict (false, incomplete, or
context-dependent), explains why the claim is believable, gives the correct
formulation, and then breaks the claim with a concrete scenario whose numbers
actually work out.

The goal is not to mock the claims. Most of them are true in a specific,
well-defined regime, and engineers who repeat them are usually quoting a real
experience. The failure is in the missing quantifiers: "always", "guarantees",
"completely", "average case" — words that quietly delete the preconditions
under which the statement holds. Removing those deletions is what this project
does. Read the inventory below, pick the claim you have caught yourself
repeating, and audit it against the counterexample.

## A Taxonomy of Misconception Types

Not all wrong claims are wrong in the same way, and the verdict category
changes what you should do about it.

| Type | Definition | What to do about it | Example in this collection |
|---|---|---|---|
| False | The claim is contradicted outright: a valid counterexample exists where the outcome is the opposite of the claim | Replace the claim; memorize the counterexample | "TCP guarantees the application receives the data" |
| Incomplete | The claim is true in a common regime but omits preconditions whose violation flips or voids the result | Attach the preconditions explicitly; treat the claim as conditional | "Good average-case complexity guarantees good real-world performance" |
| Context-dependent | The claim is true on one side of a tradeoff and false on the other; neither polarity is universally valid | Learn the regime boundary, not a verdict | "Recursion is always slower than iteration" |

The distinction matters in interviews. Saying "that is false" when the honest
answer is "that is incomplete — here are the three missing preconditions"
signals precision, and interviewers probe exactly this. A false claim has a
counterexample that inverts the outcome; an incomplete claim usually has a
counterexample that only fails to deliver the promised benefit. When you are
unsure which verdict applies, try to construct a scenario where the claim's
outcome is worse than the baseline. If you can, the claim is false; if the
outcome merely fails to improve, the claim is incomplete; if the outcome
depends on workload shape, it is context-dependent.

## Why These Claims Persist

Every claim in this collection survives because it encodes a kernel of truth
so reliable that most encounters with the claim never expose the boundary.

- **The common regime dominates experience.** Hash lookups are O(1) almost
  every time you measure them; most tables are indexed usefully; most caches
  improve latency. A rule that holds in 99% of observed cases is indistinguishable
  from an unconditional rule unless you go looking for the 1%.
- **Teaching simplifications harden into axioms.** Courses say "hash tables are
  constant time" to defer the fine print about expected versus worst-case cost.
  Students remember the slogan and lose the quantifier "expected, under simple
  uniform hashing".
- **Guarantees get smuggled across abstraction layers.** TCP really does
  guarantee reliable, ordered byte delivery — to the kernel socket buffer, not
  to the receiving application. The guarantee is real at one layer and fictional
  one layer up.
- **Survivorship bias.** The projects where "more threads fixed it" ship; the
  projects where more threads caused a contention collapse get rewritten before
  anyone writes the postmortem.
- **The fine print is documented but unread.** Java's `HashMap` javadoc and
  PostgreSQL's planner documentation both state their limits plainly. The
  misconception persists because nobody reads the documentation of things they
  believe they already understand.

## How to Audit Your Own Beliefs

Use this checklist on any performance or correctness claim you are about to
repeat in a design review or an interview.

1. **State the claim with quantifiers.** Rewrite it as "for all X, doing Y
   yields Z". Vague claims cannot be audited.
2. **Name the regime where it holds.** Every surviving claim has one. If you
   cannot name it, you do not understand the claim yet.
3. **Hunt for one valid counterexample.** Not a plausible story — a concrete
   scenario with numbers you have actually computed. If your counterexample
   does not survive arithmetic, the claim survives.
4. **Identify the missing precondition.** Classify the verdict: false,
   incomplete, or context-dependent, using the table above.
5. **Check what the primary source actually promises.** Read the RFC, the
   javadoc, the database planner documentation, or the language specification.
   Most misconceptions are directly contradicted by the official documentation
   of the very technology involved.
6. **Separate transport from delivery, average from worst case, isolation from
   autonomy.** Many claims fail because two adjacent concepts were merged into
   one word.

Repeat the audit periodically. Beliefs decay as tools change: a claim that was
true for Python 2 dictionaries (pre-hash-randomization) becomes false for an
adversarial workload on Python 3 unless the sentence names the version and the
protections.

## Inventory

| # | File | Claim | Verdict | Core correction |
|---|---|---|---|---|
| 1 | [hash-lookup-o1](./hash-lookup-o1.md) | "Hash-table lookup is always O(1)" | False | O(1) is the expected cost under uniform hashing; worst case is O(n), and resizing pauses are real |
| 2 | [more-threads-faster](./more-threads-faster.md) | "Adding more threads always improves performance" | False | Useful parallelism is bounded by the parallelizable fraction and by contention points |
| 3 | [indexes-always-faster](./indexes-always-faster.md) | "Indexes always make databases faster" | Context-dependent | Indexes trade write amplification and planner dependence for selective-read speed |
| 4 | [tcp-guarantees-delivery](./tcp-guarantees-delivery.md) | "TCP guarantees the application receives the data" | False | TCP guarantees ordered delivery to the socket buffer while the connection lives, not delivery to the application |
| 5 | [deadlock-requires-cpu](./deadlock-requires-cpu.md) | "A deadlock involves heavy CPU usage" | False | Deadlocked threads are blocked and consume near-zero CPU; liveness failures have distinct CPU signatures |
| 6 | [recursion-always-slower](./recursion-always-slower.md) | "Recursion is always slower than iteration" | Context-dependent | Without tail-call optimization deep recursion pays stack costs; with it, recursion compiles to a loop |
| 7 | [cache-always-improves](./cache-always-improves.md) | "A cache always improves performance" | Incomplete | Caching pays off only under locality, reuse, sufficient hit rate, and tolerance for staleness |
| 8 | [process-full-isolation](./process-full-isolation.md) | "A process is completely isolated from other processes" | False | Process isolation is strong address-space isolation, not total isolation: kernel, filesystem, IPC, and side channels remain shared |
| 9 | [consistency-availability-partition](./consistency-availability-partition.md) | "A distributed system can always provide consistency and availability during a partition" | False | Gilbert–Lynch 2002 proves C and A cannot both hold under partition; PACELC extends the tradeoff |
| 10 | [average-case-complexity](./average-case-complexity.md) | "Good average-case complexity guarantees good real-world performance" | Incomplete | Averages are over a distribution; adversarial inputs, tails, and constants decide real-world outcomes |

## Coverage Ledger

| File | Topic area | Verdict | Status | Word count |
|---|---|---|---|---|
| index.md | Taxonomy and audit method | — | Written | ~1,460 |
| hash-lookup-o1.md | Data structures | False | Written | ~1,420 |
| more-threads-faster.md | Concurrency | False | Written | ~1,420 |
| indexes-always-faster.md | Databases | Context-dependent | Written | ~1,360 |
| tcp-guarantees-delivery.md | Networking | False | Written | ~1,320 |
| deadlock-requires-cpu.md | Concurrency, OS | False | Written | ~1,290 |
| recursion-always-slower.md | Algorithms, languages | Context-dependent | Written | ~1,440 |
| cache-always-improves.md | Systems, caching | Incomplete | Written | ~1,460 |
| process-full-isolation.md | Operating systems, security | False | Written | ~1,420 |
| consistency-availability-partition.md | Distributed systems | False | Written | ~1,450 |
| average-case-complexity.md | Algorithms, performance | Incomplete | Written | ~1,420 |

The collection is complete at ten claims. Candidate future additions (advisory
locks prevent all race conditions, GC eliminates memory leaks, HTTPS means the
site is safe, container == VM) are tracked in the hub backlog rather than
grown here, to keep every entry fully argued rather than enumerated.

## Cross-References

- [Follow-up Tree: Hash Tables](../followup-tree/hash-tables.md) — interview
  escalation chains that start from the same O(1) belief and go deeper
- [Assumptions Hunt: Complexity Claims](../assumptions-hunt/complexity-claims.md)
  — the hidden assumptions behind big-O statements in interviews
- [Why-Not Handbook: Binary Search vs Hashing](../why-not-handbook/binary-search-vs-hashing.md)
  — the decision that the O(1) slogan hides
- [Failure Casebook: Therac-25](../failure-casebook/therac-25.md) — a race
  condition that no amount of average-case reasoning would have excused
- [DSA: Hashing](../../dsa/chapters/ch07-hashing.md) — the mechanics this
  collection assumes
- [OS Overview](../../os/overview.md) — where process isolation actually
  comes from
- [Distributed Systems Overview](../../distributed/overview.md) — the CAP
  material in its native habitat
