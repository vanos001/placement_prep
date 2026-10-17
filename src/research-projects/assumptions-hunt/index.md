# Hidden Assumptions Hunt

## Overview

Every algorithm you memorized and every system guarantee you quote comes with a list of preconditions that nobody states out loud. Binary search assumes sorted input, a total order, and an overflow-safe midpoint. Big-O assumes a machine where every memory access costs the same. A "cached" value assumes the world did not change underneath it. This collection takes common textbook rules, makes their hidden assumptions explicit, breaks each one with a concrete counterexample, and rebuilds a corrected statement that survives contact with production.

The framing matters because interviews and incidents rarely punish you for knowing a rule; they punish you for not knowing when the rule stops applying. A candidate who says "binary search is O(log n)" is fine. A candidate who says "binary search is O(log n) comparisons, provided the array is sorted under a strict weak order and the midpoint computation cannot overflow — which the JDK got wrong for nine years" is demonstrating a different level of understanding. That second sentence is the product of this collection's method.

## Why Textbook Rules Break at Boundaries

Textbooks optimize for clarity of the core idea, so they study the interior of the design space: sorted arrays, well-behaved hash functions, balanced workloads, infinite memory, single-threaded execution, reliable networks. Production lives at the boundaries: adversarial inputs, sizes that cross integer limits, concurrent access, data that does not fit in RAM, networks that partition, clocks that drift. The rule itself was never false — it was conditional, and the conditions were unstated.

Three forces consistently create the gap:

1. **Idealized cost models.** The RAM model charges one unit per memory access, so O(1) array access and O(1) hash lookup look equivalent. Real hardware has caches, TLBs, page faults, and NUMA, so the constants differ by orders of magnitude and sometimes the asymptotics themselves change (external-memory algorithms).
2. **Idealized semantics.** "The midpoint of `low` and `high`" is mathematically `(low + high) / 2`. In 32-bit arithmetic that expression overflows. The algorithm is correct; the translation into a bounded type is not. Textbooks reason in integers; languages hand you fixed-width types.
3. **Idealized environments.** "The cache returns the current value" assumes no concurrent writer. "The network delivers the request" assumes no partition. "REPEATABLE READ means the same thing everywhere" assumes the SQL standard was implemented identically — it was not, and the divergence between MySQL and PostgreSQL is documented in both vendors' manuals.

None of this makes the textbooks wrong. It makes them incomplete, and the missing parts are exactly what senior interviews probe.

## The Method Used in Every Chapter

Each chapter follows the same five-step pattern, applied to a specific family of assumptions. When you read or recall any chapter, you should be able to reconstruct it from this skeleton:

1. **The taught rule.** Stated fairly, the way a textbook or a lecture would state it. No strawmen — the rule is genuinely correct under its intended conditions.
2. **The hidden assumptions.** An explicit list of the preconditions the rule silently relies on, with a note on why each one is usually invisible (usually because it holds in the demo, the unit test, and the classroom example).
3. **Counterexample / boundary case.** A concrete input, timing, or environment where the rule fails. Every counterexample in this collection is real and checkable — no invented pathology. Where a claim is subtle (integer overflow points, isolation-level behavior, memory-model guarantees), the numbers and quotes were verified against primary sources: the C11 standard draft, the JLS, the Go memory model, PostgreSQL and MySQL manuals, and the original engineering posts.
4. **What changes when the assumption is removed.** The corrected statement — the same rule, restated with its preconditions explicit, plus the standard defenses (safer idiom, alternative algorithm, explicit contract).
5. **Practical consequences and interview implications.** Where this shows up in code review, incidents, and interview questions, including the follow-up questions that separate memorized answers from understood ones.

Worked micro-example, so the pattern is visible before you dive in:

- **Taught rule:** "Binary search runs in O(log n) time."
- **Hidden assumptions:** the array is sorted; the comparison is a total (strict weak) order; indices fit in the index type; the midpoint expression cannot overflow.
- **Counterexample:** Joshua Bloch's 2006 Google Research post documented that `int mid = (low + high) / 2` throws `ArrayIndexOutOfBoundsException` once the sum of `low` and `high` exceeds `2^31 - 1`, which is reachable for arrays of roughly 2^30 elements or more. The bug sat in the JDK for about nine years.
- **Corrected statement:** "Binary search performs O(log n) comparisons and O(log n) index computations, provided the input is sorted under the comparator's order and index arithmetic is overflow-safe, e.g. `mid = low + (high - low) / 2`."
- **Consequences:** in interviews, this is the canonical "your trivial code has a bug" probe; in practice, it is a template for auditing every arithmetic expression that aggregates sizes, counts, or timestamps.

## How This Differs From the Sibling Projects

The research projects share a subject pool but not an angle. Use this directory when the question is "what precondition was silently assumed?"; use the others when the question is different:

- [Misconceptions](../misconceptions/index.md) targets claims that are *false as stated* (for example, "hash lookup is always O(1)"). Here, the rules are true as stated — the failure is in the unstated conditions.
- [Why-Not Handbook](../why-not-handbook/index.md) explains why you would choose mechanism A over mechanism B. Here we are not choosing; we are auditing the chosen mechanism's fine print.
- [Follow-up Tree](../followup-tree/index.md) escalates a question into the depth an interviewer adds, layer by layer. The assumptions here are the material those follow-ups are made of.
- [Failure Casebook](../failure-casebook/index.md) documents named incidents with timelines and primary sources. When an assumption failure has a famous incident behind it, the chapter links to the casebook instead of retelling the story.
- [Connection Atlas](../connection-atlas/index.md) maps dependencies between topics. The assumptions collection is frequently the *reason* an edge exists in that graph (for example, isolation-level semantics depending on the concurrency-control mechanism).

If you find the same concept in two projects, the treatment is deliberately different rather than duplicated. Hash tables, for instance, appear in all five projects from five angles: escalation chain (followup), adversarial hashing (this project's [complexity claims](complexity-claims.md)), versus binary search (why-not), the O(1) claim (misconceptions), and as database index structure (atlas).

## File Inventory

| File | Domain | Assumptions audited |
|------|--------|---------------------|
| [input-constraints.md](input-constraints.md) | Algorithms | Sortedness, total order, overflow-safe midpoint, partition invariants, int-sized sums, in-memory input, ASCII text, non-empty inputs |
| [memory-model.md](memory-model.md) | Systems | Zeroed memory, valid pointers, contiguity, no padding, unbounded stack, deterministic uninitialized reads, signed overflow, data races and UB, `volatile` semantics |
| [concurrency-and-scheduling.md](concurrency-and-scheduling.md) | Concurrency | Atomicity of compound operations, check-then-act, single-core visibility intuitions, `volatile` as synchronization, sleep durations, priority scheduling, instant thread startup, timeouts as guarantees |
| [complexity-claims.md](complexity-claims.md) | Algorithms | O(1) memory access, uniform hashing, the comparison-sort lower bound, recursion depth, "better big-O wins" |
| [caching.md](caching.md) | Infrastructure | Locality, read-heavy workloads, free coherence, tolerated staleness, TTL as consistency, transferable hit rates, "no downsides" |
| [database-isolation.md](database-isolation.md) | Databases | "Transactions are isolated", SELECT never blocks, commit order equals transaction order, REPEATABLE READ portability, phantom reads, ORM-managed races |
| [network-distributed.md](network-distributed.md) | Networking & distributed | LAN reliability, localhost parity, in-order delivery, zero-latency calls, synchronized clocks, accurate failure detection, safe retries, the Eight Fallacies |

## Coverage Ledger

Status per file, the primary sources each relies on, and known gaps. Primary sources marked "verified" were fetched and checked (HTTP 200 plus content inspection) during writing; factual claims from them are quoted or closely paraphrased in the chapters.

| File | Status | Primary sources | Known gaps / future work |
|------|--------|-----------------|--------------------------|
| index.md | Complete | This collection's own method; sibling-project indexes | Sibling links assume the other research-project directories land per the coverage plan |
| input-constraints.md | Complete | [Bloch, Google Research blog, 2006](https://research.google/blog/extra-extra-read-all-about-it-nearly-all-binary-searches-and-mergesorts-are-broken/) (verified, quotes extracted); C11 overflow semantics via the [N1570 draft](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) (verified) | McIlroy's "killer adversary" paper cited by name only (no URL included); could add a worked UTF-8 byte-table |
| memory-model.md | Complete | [C11 N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) (verified), [JLS ch. 17](https://docs.oracle.com/javase/specs/jls/se8/html/jls-17.html) (verified), [Go memory model](https://go.dev/ref/mem) (verified, race-semantics quote extracted), [JSR-133 Cookbook](https://gee.cs.oswego.edu/dl/jmm/cookbook.html) (verified) | C++ standard wording cited by section name ([intro.races]) without URL by design; store-buffer litmus test described, not benchmarked |
| concurrency-and-scheduling.md | Complete | JLS §17.7 tearing via the [JLS](https://docs.oracle.com/javase/specs/jls/se8/html/jls-17.html) (verified); POSIX sleep semantics from the POSIX.1-2017 specification (text-level knowledge, no URL included); Pathfinder account cited as the JPL team's write-up (name only) | Priority-inheritance mechanics could use a diagram; sleep/signal counterexample could include a compilable reproducer |
| complexity-claims.md | Complete | [oCERT-2011-003](https://ocert.org/advisories/ocert-2011-003.html) (verified) for hash-flooding; SipHash adoption in Python (PEP 456) and Rust std referenced as documented facts; OpenJDK/TimSort thresholds stated as implementation facts (checkable in source) | Paper URLs (Vattani et al. stampede paper; McIlroy) deliberately omitted rather than risk unverified links; matrix-traversal numbers are hardware-dependent ranges, not single figures |
| caching.md | Complete | Probabilistic early expiration attributed to Vattani, Chierichetti, Lowenstein (VLDB 2015) by name; cache-aside race sequence standard in the repo's own cache-patterns page | No direct stampede reproducer with numbers; hit-rate distribution examples are illustrative, not measured datasets |
| database-isolation.md | Complete | [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (verified, default-level and RR-error quotes extracted), [MySQL InnoDB isolation levels](https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html) (verified), [MySQL consistent reads](https://dev.mysql.com/doc/refman/8.0/en/innodb-consistent-read.html) (verified, SELECT-vs-DML snapshot quote extracted) | Write-skew example reasoned from documented SI semantics, not executed; SQL Server/Oracle defaults stated from common documentation (no URLs) |
| network-distributed.md | Complete | [Cloudflare leap-second post](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns) (verified), [Eight Fallacies](https://nighthacks.com/jag/res/Fallacies.html) (verified), [RFC 5905](https://www.rfc-editor.org/rfc/rfc5905.html) and [RFC 768](https://www.rfc-editor.org/rfc/rfc768.txt) (verified via rfc-editor.org; datatracker blocks bots with 403) | Retry-storm and ECMP-reordering mechanics described from protocol knowledge without packet-trace evidence; no QUIC RFC cited yet (RFC 9000 would be the source) |

Ledger maintenance rule: when a gap is closed, update this table in the same change so status never outruns content.

## Interview Questions

1. **Why do hidden assumptions matter more in system design interviews than in coding interviews?** In coding interviews the constraints are printed in the problem statement (sizes, ranges, sortedness); the assumptions are handed to you. In system design they are not — the interviewer's follow-ups ("what if the cache goes stale?", "what if the network partitions?") are precisely asking you to name and handle assumptions you never wrote down. Candidates who volunteer assumptions preempt half the follow-ups.
2. **Give an example where the algorithm was correct but the implementation still failed.** Binary search: Bentley proved the algorithm correct, yet the JDK implementation overflowed the midpoint computation for arrays near 2^30 elements, throwing `ArrayIndexOutOfBoundsException` after roughly nine years in production. The gap was between the mathematical integers of the proof and the fixed-width integers of the machine.
3. **How do you systematically find hidden assumptions in your own code?** Ask for each quantity: what are its bounds, and what happens at them (empty, one element, maximum, zero, negative)? For each operation: what interleaving would break it? For each external dependency: what does it promise (delivery, ordering, consistency, timing), and what does it merely usually do? Then test the boundaries deliberately rather than incidentally.
4. **What is the difference between a misconception and a hidden assumption?** A misconception is false as stated ("SELECT never blocks"). A hidden assumption is a true rule plus unstated preconditions ("binary search is O(log n) — if the input is sorted and the midpoint is overflow-safe"). Misconceptions get corrected by denial; assumptions get corrected by completing the sentence.
5. **Which hidden assumption has caused the most expensive real-world failures in this collection?** Strong candidates: uninitialized memory reads (security-relevant data leaks), lost updates from ORM read-modify-write cycles (financial data corruption), and the "retrying is safe" assumption (duplicate charges and amplified outages). All three are cheap to prevent and expensive to discover in production.

## Key Takeaways

- A rule and its preconditions are inseparable; learning the rule without the preconditions is learning half of it.
- Boundary behavior — empty input, maximum input, concurrent access, degraded network — is where textbook rules and production behavior diverge, and it is exactly where interviewers and incidents probe.
- The five-step pattern (taught rule, hidden assumptions, counterexample, corrected statement, consequences) turns any memorized fact into an auditable claim.
- Every counterexample in this collection is real and source-backed; treat the primary sources cited in each chapter as part of the material, not decoration.
- Stating assumptions out loud is the cheapest performance improvement available in an interview: it converts unknown-unknowns into answered follow-ups.

## Cross-References

- [Misconceptions project](../misconceptions/index.md) — claims that are false as stated, the complement of hidden assumptions.
- [Why-Not Handbook](../why-not-handbook/index.md) — mechanism-level comparisons that rest on the assumptions audited here.
- [Follow-up Tree](../followup-tree/index.md) — interview escalation chains built from these boundary cases.
- [Failure Casebook](../failure-casebook/index.md) — named incidents where one of these assumptions failed in production.
- [Connection Atlas](../connection-atlas/index.md) — dependency graph between topics, with assumptions as the edges.
- [Complexity claims](complexity-claims.md) — the RAM-model assumptions behind big-O, audited in depth.
- [Memory model](memory-model.md) — the assumptions about memory and language semantics that underlie every systems claim.
