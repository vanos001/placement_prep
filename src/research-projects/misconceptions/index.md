# Misconception Elimination Project

## Overview

This collection targets forty-four widely repeated claims that survive
interviews, code reviews, and design documents because each one contains a
kernel of truth.
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
| 11 | [big-o-is-speed](./big-o-is-speed.md) | "O(n log n) always beats O(n²)" | False | Big-O is an asymptotic statement; at real sizes constants and input shape decide the race |
| 12 | [https-means-secure](./https-means-secure.md) | "The padlock means this site is safe" | False | TLS authenticates a domain and protects a transport; it says nothing about operator, content, or application safety |
| 13 | [ssd-ignores-io-patterns](./ssd-ignores-io-patterns.md) | "SSDs make I/O patterns irrelevant" | Incomplete | Random-write amplification and fsync behavior still dominate sustained writes and durability on flash |
| 14 | [gc-means-no-leaks](./gc-means-no-leaks.md) | "GC languages can't leak" | False | Leaks are unbounded reachable-but-unused memory; collectors manage reachability, not intent |
| 15 | [containers-are-vms](./containers-are-vms.md) | "Containers are lightweight virtual machines" | False | Namespaces and cgroups share the host kernel; the isolation boundary differs in kind, not degree |
| 16 | [relational-dbs-dont-scale](./relational-dbs-dont-scale.md) | "You must leave SQL to scale" | False | SQL systems run at planetary scale; scaling limits are per-system engineering choices, not the relational model |
| 17 | [more-replicas-more-consistency](./more-replicas-more-consistency.md) | "More replicas = more reliable and more consistent" | False | Async replicas widen staleness; quorum math decides consistency, not copy count |
| 18 | [bandwidth-fixes-latency](./bandwidth-fixes-latency.md) | "More bandwidth will make it faster" | Context-dependent | Bandwidth fixes throughput-bound work; RTT-bound work needs fewer round trips |
| 19 | [async-await-parallelism](./async-await-parallelism.md) | "async/await makes my code run in parallel" | False | async/await provides I/O concurrency on one thread; parallelism needs workers, processes, or a multithreaded runtime pool |
| 20 | [encryption-means-authenticated](./encryption-means-authenticated.md) | "It's encrypted, so it can't be tampered with" | False | Ciphers provide confidentiality only; malleability and padding oracles make integrity an AEAD/MAC job |
| 21 | [udp-cannot-be-reliable](./udp-cannot-be-reliable.md) | "UDP is unreliable, so serious applications can't use it" | False | Reliability is a layer you choose to build (QUIC/HTTP-3, netcode, DNS retries); TCP's ordering has costs |
| 22 | [crc-equality-means-file-equality](./crc-equality-means-file-equality.md) | "The checksums match, so the file is intact/identical" | Incomplete | CRC equality detects accidental damage; adversarial collisions are algebra, and only keyed digests authenticate |
| 23 | [single-threaded-languages-cant-parallelize](./single-threaded-languages-cant-parallelize.md) | "Node.js/Python can't use multiple cores" | False | Workers, processes, GIL-releasing native code, and free-threaded builds move work to other cores |
| 24 | [immutability-means-thread-safe](./immutability-means-thread-safe.md) | "final/const/immutable fields make this thread-safe" | Incomplete | Deep immutability plus safe publication is the real theorem; the keywords deliver only half |
| 25 | [averages-summarize-latency](./averages-summarize-latency.md) | "Average latency is a good performance metric" | Incomplete | Means hide tails and multimodality; percentiles from merged histograms represent user experience |
| 26 | [green-tests-mean-correct](./green-tests-mean-correct.md) | "All tests pass, so the code is correct" | False | A suite samples the behavior space; green proves only that sampled, asserted behavior matched expectations — sampling, oracle, and assertion-strength gaps remain |
| 27 | [backups-mean-recovery](./backups-mean-recovery.md) | "We have backups, so we can recover" | Incomplete | Recovery is a capability, not an artifact: tested restore path, RTO/RPO arithmetic, consistency under a running engine, and independence from the failure |
| 28 | [corruption-would-be-loud](./corruption-would-be-loud.md) | "If data gets corrupted, something would crash or error" | False | Bit rot, lost writes, and torn writes yield valid-looking wrong data; loudness is purchased per layer, and only end-to-end checks cover meaning |
| 29 | [high-throughput-means-low-latency](./high-throughput-means-low-latency.md) | "The system does 50k req/s, so responses are fast" | False | Latency follows queueing (Little's Law), not the rate record; saturation pins throughput flat while waiting grows unbounded |
| 30 | [dashboards-mean-observability](./dashboards-mean-observability.md) | "We have dashboards, so we are observable" | Incomplete | Observability is the ability to ask new questions of production; dashboards are frozen answers over pre-aggregated, cardinality-capped series |
| 31 | [coverage-means-tested](./coverage-means-tested.md) | "90% code coverage means the code is well tested" | False | Coverage measures execution, not assertion strength; mutation scoring measures the gap, and the uncovered residue maps the expensive paths |
| 32 | [jwt-is-encrypted](./jwt-is-encrypted.md) | "JWTs are secure because they're encrypted" | False | A JWT is base64url-encoded and typically signed (JWS), not encrypted (JWE); payloads are readable by anyone holding the token, and alg confusion invites forgery |
| 33 | [encryption-at-rest-means-access-control](./encryption-at-rest-means-access-control.md) | "The data is encrypted at rest, so access is controlled" | Incomplete | At-rest encryption protects the medium, not the credential path; authorization and key policy are separate access-control surfaces |
| 34 | [rollback-means-undo](./rollback-means-undo.md) | "We can always roll back the deploy, so the change is reversible" | Incomplete | Rollback reverts the artifact, not the world: migrations, side effects, caches, and contracts survive; expand-contract manufactures the reversibility the button promises |
| 35 | [stateless-means-no-state](./stateless-means-no-state.md) | "Our microservices are stateless, so scaling is trivial" | Incomplete | State moved, not vanished: backing stores concentrate it, saturate first, and affinity returns through cache locality |
| 36 | [load-test-proves-production](./load-test-proves-production.md) | "We load-tested at 2x peak, so production is safe" | False | A load test bounds collapse points for a synthetic workload on a named environment; parity gaps, traffic shape, and coordinated omission void the certificate |
| 37 | [the-network-is-reliable](./the-network-is-reliable.md) | "The network is reliable" | False | The first fallacy of distributed computing: loss, delay, duplication, and partition are ordinary events; reliability is engineered at the endpoints (timeouts, retries, idempotency, quorums) |
| 38 | [transactions-span-services-safely](./transactions-span-services-safely.md) | "A transaction spans the services, so it all commits or rolls back together" | False | A transaction ends at the resource manager that logs it; HTTP calls and broker publishes commit outside any rollback — outbox and sagas manufacture cross-service atomicity |
| 39 | [base64-is-encryption](./base64-is-encryption.md) | "It's base64-encoded, so it's encrypted" | False | Base64 is a keyless, reversible encoding (RFC 4648); secrecy needs a keyed transform, and one command decodes the "protected" value |
| 40 | [uuids-are-unguessable](./uuids-are-unguessable.md) | "UUIDs are unguessable, so exposing them in URLs is safe" | Incomplete | Unguessability belongs to the entropy source, not the format: v4 from a CSPRNG holds, v1 leaks time and node, v3/v5 are computed, and no identifier is an authorization system |
| 41 | [orm-prevents-injection](./orm-prevents-injection.md) | "We use an ORM, so SQL injection is handled" | Incomplete | The ORM parameterizes the queries it generates; raw fragments, identifier positions like ORDER BY, and second-order reuse of stored strings bypass it |
| 42 | [localhost-means-loopback](./localhost-means-loopback.md) | "localhost means the loopback interface, so it stays on this machine" | Incomplete | The reservation is real (127/8, ::1, RFC 6761), but address family, network namespaces, hosts files, and the bind-versus-dial privacy inversion each carry preconditions |
| 43 | [queues-guarantee-ordering](./queues-guarantee-ordering.md) | "The queue guarantees ordering" | Incomplete | Brokers preserve order within a scope (partition, message group) up to first delivery; producer retries, worker concurrency, redelivery, and replay reorder application |
| 44 | [regex-can-parse-html](./regex-can-parse-html.md) | "A regex can parse HTML" | False | Regular languages cannot match unbounded nesting; real HTML parsing needs the WHATWG error-recovery algorithm, and regexes match tokens, not trees |

## Coverage Ledger

| File | Topic area | Verdict | Status | Word count |
|---|---|---|---|---|
| index.md | Taxonomy and audit method | — | Written | ~2,120 |
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
| big-o-is-speed.md | Algorithms | False | Written | ~1,630 |
| https-means-secure.md | Security, networking | False | Written | ~1,820 |
| ssd-ignores-io-patterns.md | Storage, systems | Incomplete | Written | ~1,860 |
| gc-means-no-leaks.md | Languages, memory | False | Written | ~1,810 |
| containers-are-vms.md | Operating systems, cloud | False | Written | ~1,760 |
| relational-dbs-dont-scale.md | Databases, distributed | False | Written | ~1,700 |
| more-replicas-more-consistency.md | Distributed systems, replication | False | Written | ~1,600 |
| bandwidth-fixes-latency.md | Networking, performance | Context-dependent | Written | ~1,930 |
| async-await-parallelism.md | Languages, concurrency | False | Written | ~2,330 |
| encryption-means-authenticated.md | Security | False | Written | ~2,360 |
| udp-cannot-be-reliable.md | Networking | False | Written | ~2,330 |
| crc-equality-means-file-equality.md | Storage, security | Incomplete | Written | ~2,420 |
| single-threaded-languages-cant-parallelize.md | Languages, concurrency | False | Written | ~2,310 |
| immutability-means-thread-safe.md | Concurrency, languages | Incomplete | Written | ~2,510 |
| averages-summarize-latency.md | Performance, observability | Incomplete | Written | ~2,440 |
| green-tests-mean-correct.md | Testing, correctness | False | Written | ~2,360 |
| backups-mean-recovery.md | Storage, operations, recovery | Incomplete | Written | ~2,380 |
| corruption-would-be-loud.md | Storage, integrity | False | Written | ~2,330 |
| high-throughput-means-low-latency.md | Performance, queueing | False | Written | ~2,320 |
| dashboards-mean-observability.md | Observability, operations | Incomplete | Written | ~2,350 |
| coverage-means-tested.md | Testing, metrics | False | Written | ~2,400 |
| jwt-is-encrypted.md | Security, tokens | False | Written | ~2,320 |
| encryption-at-rest-means-access-control.md | Security, storage, access control | Incomplete | Written | ~2,350 |
| rollback-means-undo.md | Deployments, databases, operations | Incomplete | Written | ~2,310 |
| stateless-means-no-state.md | Architecture, scaling, state | Incomplete | Written | ~2,300 |
| load-test-proves-production.md | Testing, performance, reliability | False | Written | ~2,310 |
| the-network-is-reliable.md | Networking, distributed systems | False | Written | ~2,370 |
| transactions-span-services-safely.md | Distributed systems, transactions | False | Written | ~2,500 |
| base64-is-encryption.md | Security, encoding | False | Written | ~2,340 |
| uuids-are-unguessable.md | Security, identifiers | Incomplete | Written | ~2,430 |
| orm-prevents-injection.md | Security, databases | Incomplete | Written | ~2,350 |
| localhost-means-loopback.md | Networking, containers | Incomplete | Written | ~2,390 |
| queues-guarantee-ordering.md | Messaging, distributed systems | Incomplete | Written | ~2,320 |
| regex-can-parse-html.md | Parsing, languages, theory | False | Written | ~2,320 |

The collection stands at forty-four claims after six expansion rounds.
The Round 15 candidates tracked in the hub backlog ("HTTPS means safe",
"GC eliminates leaks", "container == VM") have since been incorporated as
full audits in Round 16, Round 17 added seven more whose thread runs
through runtime execution models (async/await, the GIL, immutability),
transport and cipher guarantees (UDP, encryption, checksums), and
measurement discipline (latency averages), and Round 18 added seven whose
thread runs through evidence and verification (green suites, coverage,
dashboards, backups), measured versus experienced performance (throughput
versus latency), and the boundary between encoding and protection (silent
corruption, JWT structure). Round 19 added five whose thread runs
through the boundary between a control and the property it is sold as —
encryption versus access control, rollback versus reversibility,
statelessness versus scale, a load test versus safety, and the network
versus reliability. Round 20 added seven whose thread runs through the
gap between a mechanism and the guarantee borrowed from it — transaction
boundaries versus service atomicity, encoding versus encryption,
identifier format versus entropy, ORM parameterization versus injection
coverage, a name versus the address it resolves to, broker scope order
versus end-to-end order, and regular expressions versus nested
structure. The remaining backlog candidate
(advisory locks prevent all race conditions) stays tracked at the hub, to
keep every entry fully argued rather than enumerated.

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
