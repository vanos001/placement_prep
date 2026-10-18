# Concept Connection Atlas

## Overview

Most technical curricula teach systems as silos: one chapter for virtual memory, one for database indexes, one for TCP. The exam then asks about each in isolation. Production systems and senior interviews do neither — they ask what a page cache, a DB buffer pool, and a CDN edge have in *mechanism* in common, and where that commonality stops. This atlas exists to answer that kind of question.

The unit of analysis here is the **cross-domain connection**, and every connection is held to the same five-part standard:

1. **Concepts stated independently.** Each side of the connection is explained on its own, with just enough mechanism for the link to make sense. If you cannot state both concepts crisply, the connection is decoration, not understanding.
2. **The shared principle, named precisely.** Not "these are similar" but something testable, e.g., "both are demand-filled caches with locality-driven eviction over a cost gradient" or "both compute a linear extension of a partial order induced by dependencies." A well-named principle is a transferable tool: next time you meet an unfamiliar system, you can ask "which known principle does this instantiate?"
3. **Where the analogy HOLDS and where it BREAKS.** Specific and technically honest. An analogy that never breaks is a definition, not an analogy. The breaking points are usually where the interview follow-up question lives ("but what about fan-out?"), and where real design mistakes happen (applying the cache-miss mental model to a page fault that costs 10,000× more).
4. **A concrete worked example, with numbers where possible.** Mechanisms earn belief through arithmetic: a B+tree that fits a billion keys in 3 levels, an M/M/1 queue whose latency doubles per 10% of utilization near saturation.
5. **When the connection is useful.** Problem-solving heuristics, interview answers, and real engineering decisions it unlocks — plus the decision it should *not* be stretched to.

**Why this matters for engineering judgment.** Mechanism transfer is how senior engineers reason about systems they have never operated. If you know that Git, Nix, Docker layers, IPFS, and content-hashed CDN assets all instantiate "hash the content, not the location," then a new system described as "content-addressed" immediately implies immutability, cheap integrity checks, dedup, and cache-friendliness — and its costs (GC of unreferenced data, no in-place mutation) are implied too. Without the abstraction, each system looks like isolated trivia.

**Why this matters for interviews.** Interviewers escalate along the axis of *abstraction*, not trivia: "What is a B+tree?" (junior) → "Why a B+tree and not a skip list on disk?" (mid) → "What property of the storage medium makes fan-out the dominant term?" (senior). The third question is answered by the principle this atlas names in [db-indexes-data-structures.md](./db-indexes-data-structures.md): data structures are shaped by the physics of the storage medium. The atlas pages are written so each can supply the top of that escalation chain.

## Map of the Atlas

Thirty connection pages, grouped by the *kind* of shared principle rather than by textbook silo:

```text
                         CONCEPT CONNECTION ATLAS
                         =======================
  ORDERING              dependency-resolution ........ topo sort ~ make ~ npm ~ schedulers
  HIERARCHY / CACHING   virtual-memory-caching ....... demand paging ~ page cache ~ buffer pool ~ CDN
  STORAGE PHYSICS       db-indexes-data-structures ... B+tree ~ LSM ~ skiplist ~ columnar
  QUEUES / DELAY        scheduling-queueing .......... CPU schedulers ~ Kendall notation ~ CoDel
                        backpressure ................. bounded queues ~ TCP windows ~ Kafka pull ~ load shedding
  FAILURE / PROTOCOL    tcp-distributed-failure ...... RTO ~ retries ~ idempotency ~ failure detectors
  CONTENT ADDRESSING    git-cas ...................... Git ~ Nix ~ Docker ~ IPFS ~ restic
  ORDERING CONTRACTS    transactions-concurrency ..... 2PL ~ RW locks ~ MVCC ~ isolation ~ memory models
  LIFETIMES             gc-memory-management ......... reachability ~ refcounts ~ generations ~ leases
  EVENT LOGS            event-sourcing-wal ........... git log ~ WAL ~ event sourcing ~ CDC ~ audit trails
  REPLICATED COPIES     cache-coherence-consistency .. MESI ~ invalidation ~ CDN purge ~ replicated consistency
  OPTIMIZER DAGS        query-planner-dataflow ....... compiler passes ~ query planner ~ Flink DAGs ~ build graphs
  REDUNDANCY            checksums-erasure-coding ..... checksums ~ RAID parity ~ Reed-Solomon ~ hashes ~ ECC
  COORDINATION          consensus-leases ............. Raft ~ distributed locks ~ leases ~ fencing tokens
  EVENT DISPATCH        interrupts-async ............. IRQs ~ signals ~ epoll ~ event loops ~ futures
  INVALIDATION          incremental-computation ...... make ~ spreadsheets ~ incr. compilers ~ matviews ~ React
  ADDRESSING / ROUTING  dns-cdn-routing .............. DNS hierarchy ~ anycast ~ GeoDNS ~ CDN edge ~ purge
  ISOLATION / RESOURCES containers-cgroups-namespaces   namespaces ~ cgroups ~ overlayfs layers ~ OCI runtime
  IDENTITY / STATE      auth-identity-session ........ OAuth2 ~ JWT ~ sessions ~ cookies ~ revocation ~ SSO
  PLACEMENT             load-balancing-partitioning ... L4/L7 ~ affinity ~ consistent hashing ~ discovery
  EXECUTION / SILICON   jit-interpretation-hardware .. interpreter ~ tiered JIT ~ inline caches ~ deopt
  RETRIEVAL             search-inverted-index ........ analyzer ~ postings ~ BM25 ~ segments ~ NRT refresh
  TELEMETRY             observability-pipeline ....... metrics/logs/traces ~ agents ~ sampling ~ cardinality
  RELEASE ENGINEERING   feature-flags-deploy-coupling  flags ~ deploy ~ rollout ~ kill switches ~ cleanup debt
  SHIPPING / SCHEMA     migrations-deploy-coupling ... expand-contract ~ dual-write ~ backfill ~ lock budgets
  ML SERVING            ml-inference-pipeline ........ artifacts ~ feature stores ~ batching ~ drift
  CONFIG DISTRIBUTION   config-management-pipeline ... layering ~ hot reload ~ secrets ~ blast radius
  MONEY AS A LOG        payments-ledger-double-entry . double-entry ~ idempotency ~ reconciliation ~ sagas
  BUILD HONESTY         build-caches-reproducibility . lockfiles ~ content-addressed caches ~ hermetic builds
  CALLBACK DELIVERY     webhook-delivery ............. retries ~ signing ~ dedup ~ DLQ ~ pull fallback
```

Reading order is flexible; the two most load-bearing pages are `virtual-memory-caching.md` (the caching lens appears in half the other pages) and `scheduling-queueing.md` (Little's Law is the quantitative glue reused in `backpressure.md`).

## File Inventory

| File | Domains bridged | Core named principle |
|---|---|---|
| [dependency-resolution.md](./dependency-resolution.md) | Graph algorithms, build systems, package managers, schedulers | A build is a linear extension of a partial order; invalidation propagates on the reversed DAG |
| [virtual-memory-caching.md](./virtual-memory-caching.md) | OS virtual memory, CPU caches, DB buffer pools, CDNs | One demand-filled hierarchy; eviction theory is layer-independent, cost gradients are not |
| [db-indexes-data-structures.md](./db-indexes-data-structures.md) | DBMS internals, DSA, Redis | Structures are shaped by the physics of the storage medium; amplification is the exchange rate |
| [scheduling-queueing.md](./scheduling-queueing.md) | OS scheduling, queueing theory, AQM | A scheduler is a queue discipline; Little's Law connects staffing, load, and delay |
| [tcp-distributed-failure.md](./tcp-distributed-failure.md) | TCP/IP, distributed systems | Timeouts are statistical failure detectors; retries are only safe with deduplication |
| [git-cas.md](./git-cas.md) | Git, Nix, Docker, IPFS, backups, CDNs | Hash the content, not the location; a Merkle DAG authenticates its whole graph |
| [transactions-concurrency-control.md](./transactions-concurrency-control.md) | DB transactions, threading, memory models | Concurrency control is a chosen ordering contract plus the mechanism that enforces it |
| [gc-memory-management.md](./gc-memory-management.md) | GC, memory allocators, distributed leases | Reclamation needs a definition of "dead"; every definition approximates from incomplete information |
| [backpressure.md](./backpressure.md) | OS queues, TCP, Kafka, Reactive Streams, load management | Demand must propagate upstream as fast as work flows downstream; Little's Law caps throughput |
| [event-sourcing-wal.md](./event-sourcing-wal.md) | Git history, database WAL, event sourcing, CDC, audit logs | State is a fold over an immutable, ordered event log; present state is a cache of that fold |
| [cache-coherence-consistency.md](./cache-coherence-consistency.md) | CPU caches (MESI), distributed cache invalidation, CDN purge, replication | Replicas of one truth + a write-propagation protocol; invalidation traffic scales with reader fan-out |
| [query-planner-dataflow.md](./query-planner-dataflow.md) | Compilers, SQL planners, stream DAGs (Flink/Beam), build schedulers | Declarative intent → optimizer picks an execution DAG under a cost model; filter-early is one algebraic move everywhere |
| [checksums-erasure-coding.md](./checksums-erasure-coding.md) | TCP checksums, RAID parity, Reed-Solomon, Git hashes, ECC RAM | Redundancy converts detection into recovery; overhead vs repair cost vs failure independence is the whole trade |
| [consensus-leases.md](./consensus-leases.md) | Paxos/Raft, distributed locks, leases, fencing tokens | Linearizable registry + time-bounded grant + monotonic check at the resource; exclusion happens at the data |
| [interrupts-async.md](./interrupts-async.md) | Hardware IRQs, signals, epoll/kqueue, event loops, futures | Push beats poll: register interest, yield, be resumed; handler cost is paid by everyone sharing the dispatcher |
| [incremental-computation.md](./incremental-computation.md) | Build systems, spreadsheets, incremental compilers, matviews, React | Recompute only what a change invalidates: dependency graph + dirty propagation + memoized results |
| [dns-cdn-routing.md](./dns-cdn-routing.md) | DNS, BGP/anycast, GeoDNS, CDNs | Every addressing layer is a cached copy of truth with a bounded staleness budget: TTL lease, BGP convergence, purge propagation |
| [containers-cgroups-namespaces.md](./containers-cgroups-namespaces.md) | Linux namespaces, cgroups, union filesystems, OCI, Kubernetes | Isolation is two orthogonal axes (view and resources); every container property is a composition decision about which to share |
| [auth-identity-session.md](./auth-identity-session.md) | OAuth2, JWT, sessions, cookies, SSO | Auth mechanisms are leases on identity truth; revocation is shortening a lease after the fact, always by re-adding state, keys, or clocks |
| [load-balancing-partitioning.md](./load-balancing-partitioning.md) | L4/L7 balancing, hashing, data partitioning, discovery | Two placements per request (server and data owner) share one slider: spread vs locality vs stability in a changing pool |
| [jit-interpretation-hardware.md](./jit-interpretation-hardware.md) | Interpreters, tiered JITs, CPU front ends | Inline caches, tiering, and branch predictors are one mechanism: frequency-trained prediction with recovery cost, at three scales |
| [search-inverted-index.md](./search-inverted-index.md) | Text analysis, inverted indexes, BM25, segment stores | A B+tree idea transposed from values to terms; the contract diverges where relevance replaces exact, transactional truth |
| [observability-pipeline.md](./observability-pipeline.md) | Metrics/logs/traces, agents, TSDBs, alerting | A fan-in flow that sheds evidence instead of blocking producers; fidelity knobs couple layers invisibly until incident time |
| [feature-flags-deploy-coupling.md](./feature-flags-deploy-coupling.md) | Flag stores, deployment pipelines, experiment rollouts, config stores | A flag is a runtime branch point over cached, replicated rules; percentage rollout is deterministic, monotone bucketing; defaults fail toward the old world |
| [migrations-deploy-coupling.md](./migrations-deploy-coupling.md) | Schema migrations, deploy ordering, online DDL tooling | Expand-contract is two-phase commit without an abort branch; the invariant is that every intermediate state serves every live process version |
| [ml-inference-pipeline.md](./ml-inference-pipeline.md) | ML serving, feature stores, GPU queueing, drift monitoring | A deployed model is a demand-filled, versioned pipeline; feature skew is the consistency failure of a two-level store whose layers must agree semantically |
| [config-management-pipeline.md](./config-management-pipeline.md) | Config stores, env layering, secrets, hot reload | Config is a replicated, layered cache of intent; atomic snapshot swap and per-request capture are the transactional boundaries; secrets are leases |
| [payments-ledger-double-entry.md](./payments-ledger-double-entry.md) | Payments, ledgers, retries, sagas, reconciliation | Money state is a fold over an immutable, sum-zero log; idempotency keys tame at-least-once delivery; reconciliation is the cross-system checksum |
| [build-caches-reproducibility.md](./build-caches-reproducibility.md) | Build systems, package managers, CI, artifact pipelines | A build is a memoized function over an explicit input graph; reproducibility (the pure-function property) is what makes the memo table safely shareable |
| [webhook-delivery.md](./webhook-delivery.md) | Webhooks, queues, retries, consumer processing | At-least-once over HTTP: the producer's retry queue is a retransmission buffer; consumer idempotency keyed by event ID is the entry fee |

## Coverage Ledger

Status as of tasks 3-c (Round 15), 3-c2 (Round 16), r17-c2 (Round 17), and r18-c (Round 18); sibling `research-projects/` directories are owned by parallel tasks per the coordinator's plan — links to them resolve once those tasks land.

| Page | Domains covered | Status | Notes / gaps |
|---|---|---|---|
| index.md | — | Complete | This page |
| dependency-resolution.md | topo sort, make, npm/pip, Airflow, K8s init containers | Complete | SAT-based resolution only sketched; content-addressed rebuilds (Bazel/Nix) deferred to [git-cas.md](./git-cas.md) |
| virtual-memory-caching.md | demand paging, page cache, TLB, L1/L2, buffer pool, CDN | Complete | NUMA and huge pages left to [../../os/memory/numa.md](../../os/memory/numa.md) and [../../os/memory/huge-pages.md](../../os/memory/huge-pages.md) |
| db-indexes-data-structures.md | B+tree, LSM, hash index, skiplist, columnar | Complete | Deep LSM compaction math left to [../../dbms/internals/lsm-trees.md](../../dbms/internals/lsm-trees.md) |
| scheduling-queueing.md | CFS/MLFQ, M/M/1, Little's Law, HOL, CoDel | Complete | M/M/c and Erlang models left to [../../queueing-theory/applied-systems.md](../../queueing-theory/applied-systems.md) |
| tcp-distributed-failure.md | RTO, retransmission, backoff, idempotency, failure detectors | Complete | Byzantine fault tolerance out of scope ([../../distributed/fundamentals/byzantine-faults.md](../../distributed/fundamentals/byzantine-faults.md)) |
| git-cas.md | Git objects, Merkle DAGs, Nix, Docker, IPFS, restic/borg, CDN assets | Complete | Packfile delta heuristics treated qualitatively |
| transactions-concurrency-control.md | 2PL, RW locks, monitors, MVCC, serializability, memory models | Complete | Distributed commit deep-dive stays in [../../dbms/transactions/two-phase-commit.md](../../dbms/transactions/two-phase-commit.md) |
| gc-memory-management.md | tracing, refcounting, generational, STW/SLO, leases | Complete | JVM collector comparison left to [../../compilers/advanced/g1gc.md](../../compilers/advanced/g1gc.md) and neighbors |
| backpressure.md | bounded queues, TCP windows, Kafka pull, Reactive Streams, shedding | Complete | Rate-limit algorithms detailed in [../followup-tree/rate-limiter-design.md](../followup-tree/rate-limiter-design.md) |
| event-sourcing-wal.md | git history, WAL/ARIES, event sourcing + CQRS, Debezium CDC, audit logs | Complete | Stream-windowing semantics out of scope; log-compaction mechanics deferred to [../../distributed/messaging-internals/kafka-log-internals.md](../../distributed/messaging-internals/kafka-log-internals.md) |
| cache-coherence-consistency.md | MESI/MOESI, snooping vs directories, pub/sub invalidation, CDN purge, replicated consistency | Complete | Memory *consistency* models (TSO, relaxed) deferred to [../../arch/memory-hierarchy/coherence.md](../../arch/memory-hierarchy/coherence.md) |
| query-planner-dataflow.md | compiler passes, cost-based planning, cardinality misestimates, Flink/Beam DAGs, build scheduling | Complete | Cascades memo internals sketched; details left to [../../dbms/advanced/cascades-optimizer.md](../../dbms/advanced/cascades-optimizer.md) |
| checksums-erasure-coding.md | Internet checksum, CRC, RAID parity, RS(k,m) vs replication, SECDED ECC, end-to-end argument | Complete | Regenerating codes (LRC, repair amplification below k) not covered |
| consensus-leases.md | Raft/Paxos, lock services, lease timing, fencing tokens, frozen-client case | Complete | Byzantine agreement out of scope ([../../distributed/fundamentals/byzantine-faults.md](../../distributed/fundamentals/byzantine-faults.md)) |
| interrupts-async.md | IRQs/top-bottom halves, signals, epoll/kqueue, io_uring, event loops, futures | Complete | Per-language runtime internals deferred to [../../languages/rust/async-runtimes.md](../../languages/rust/async-runtimes.md) and siblings |
| incremental-computation.md | make/Bazel keys, spreadsheet recalc, rustc queries, IVM, React memoization | Complete | Demand-driven frameworks (Adapton/Salsa) treated qualitatively |
| dns-cdn-routing.md | DNS hierarchy/resolution, TTL leases, anycast, GeoDNS, CDN edge/shield/purge, failover budgets | Complete | DNSSEC and DoH left to [../../networks/dns/dnssec.md](../../networks/dns/dnssec.md) and [../../networks/dns/doh.md](../../networks/dns/doh.md) |
| containers-cgroups-namespaces.md | namespaces, cgroup v2 controllers, overlayfs layers, OCI/runc, Pod composition, OOM vs throttling | Complete | Sandbox hardening (seccomp/Landlock) left to [../../os/security-internals/seccomp.md](../../os/security-internals/seccomp.md) |
| auth-identity-session.md | OAuth2 grants, JWT claims/keys, sessions/cookies, refresh/revocation, SAML/OIDC/Kerberos, clock skew | Complete | WebAuthn/FIDO2 left to [../../security/advanced/fido2-webauthn.md](../../security/advanced/fido2-webauthn.md) |
| load-balancing-partitioning.md | L4/L7 policies, affinity, consistent/rendezvous hashing, range/hash partitioning, discovery, health checks | Complete | Live resharding protocols left to [../../dbms/advanced/online-resharding.md](../../dbms/advanced/online-resharding.md) |
| jit-interpretation-hardware.md | interpreters, tiered JIT, ICs/hidden classes, deopt/OSR, branch prediction, uop cache, warmup | Complete | Register allocation left to [../../compilers/advanced/register-allocation.md](../../compilers/advanced/register-allocation.md); GC coupling to [./gc-memory-management.md](./gc-memory-management.md) |
| search-inverted-index.md | analyzers, FST term dictionary, postings, BM25, segments/NRT, filter cache, GIN vs external engines | Complete | Vector/similarity search out of scope ([../../dbms/internals/vector-indexes-deep.md](../../dbms/internals/vector-indexes-deep.md)) |
| observability-pipeline.md | metrics/logs/traces, agents/buffers, head/tail sampling, cardinality, TSDB storage, burn-rate alerts | Complete | OpenTelemetry SDK internals treated qualitatively |
| feature-flags-deploy-coupling.md | flag species/lifecycles, SDK caching and defaults, deterministic rollout bucketing, targeting rules, kill switches, cleanup debt, flag interactions | Complete | Experiment statistics (CUPED, sequential testing) out of scope; rollout telemetry joins treated qualitatively |
| migrations-deploy-coupling.md | expand-contract, dual-write, backfill batching arithmetic, online DDL tools, lock budgets, deploy/migration serialization | Complete | Engine-specific DDL mechanics deferred to [../followup-tree/zero-downtime-migrations.md](../followup-tree/zero-downtime-migrations.md) |
| ml-inference-pipeline.md | artifacts/registries, online/offline feature stores, prediction caches, quantization, dynamic batching math, drift layers, shadow/canary | Complete | Distributed training infrastructure out of scope; feature-store product internals treated qualitatively |
| config-management-pipeline.md | five config stores and their propagation clocks, layering/shadowing, hot reload, atomic swap, secret rotation with overlap, blast radius | Complete | Consensus internals of config stores deferred to [./consensus-leases.md](./consensus-leases.md) |
| payments-ledger-double-entry.md | double-entry legs and sum-zero, chart of accounts, idempotency registries, reconciliation SLOs, compensation/sagas, books-close policy | Complete | Card-network auth/capture mechanics and regulatory specifics treated generically |
| build-caches-reproducibility.md | lockfiles plus integrity hashes, cache key completeness, hermetic toolchains, artifact promotion/attestation, shard stampedes, cache GC, poisoning | Complete | Bit-for-bit reproducibility tooling (diffoscope-class rebuild diffs) not covered |
| webhook-delivery.md | retry/backoff clocks, fast-ack pipelines, HMAC plus timestamp verification, dedup stores, DLQ/replay, pull fallback, storm arithmetic | Complete | Provider-specific retry policies (Stripe/GitHub-class) described generically, no URLs cited |

Deliberately **out of scope** for the atlas: generic pattern catalogs (owned by `failure-modes/`), mechanism-deep single-topic trade-offs (owned by the Why-Not Handbook), and incident timelines (owned by the Failure Casebook). Where those cover a topic, these pages link instead of duplicating.

## Interview Questions

1. A candidate explains that "a database buffer pool is basically a cache." What follow-up questions would you ask to distinguish rote analogy from mechanism understanding, and what answers would satisfy you?
2. Name two systems that share a partial-order dependency structure and one behavioral difference that emerges when a dependency graph contains a cycle.
3. Why is "the disk is just slow RAM" a dangerous simplification when tuning a system that mmaps a large file? Give one workload where mmap loses to explicit `read()` and say why in terms of fault cost.
4. Your p99 latency doubles as CPU utilization crosses 70%, though average latency barely moves. Construct an explanation using queueing theory alone, naming the law and the variance term.
5. Design-interview framing: "Build me a container registry." Which named principle from this atlas would structure your answer, and what are the two costs of that principle you would volunteer?

## Key Takeaways

- A connection is only worth writing down if it names a precise shared mechanism and states exactly where the mapping fails.
- The same small set of principles — partial order, demand-filled caching, cost-of-the-medium, queue discipline as policy, statistical failure detection, content addressing, ordering contracts, liveness approximation, upstream demand propagation, state as a fold over an immutable log, write-propagation across replicas, cost-based plan selection over DAGs, redundancy converting detection into recovery, grant/lease/fencing stacks, push-based event dispatch, and invalidate-only-what-changed — explains a disproportionate fraction of systems behavior across OS, DBMS, networking, and distributed systems.
- Analogies transfer *predictions*, not constants: a cache miss at L1 costs ~1 ns, a page fault ~ms; the theory of eviction transfers, the numbers do not.
- Use the Coverage Ledger above to see what is covered, where depth was deliberately deferred to canonical pages, and which sibling research projects own the adjacent angles.

## Cross-References

- [../../dsa/README.md](../../dsa/README.md) — Data Structures and Algorithms Track — where the primitive structures (hash tables, trees, graphs) are taught before the atlas reinterprets them.
- [../../os/overview.md](../../os/overview.md) — Operating Systems Overview — canonical treatment of memory, scheduling, and paging that the atlas connects outward.
- [../../dbms/overview.md](../../dbms/overview.md) — Database Management Systems Overview — canonical indexing and transaction content.
- [../../networks/overview.md](../../networks/overview.md) — Computer Networks — canonical TCP/IP content behind the failure-detection connections.
- [../../distributed/overview.md](../../distributed/overview.md) — Distributed Systems Overview — failure detectors, consistency models, and leases referenced across these pages.
- [../../queueing-theory/fundamentals.md](../../queueing-theory/fundamentals.md) — Queueing Theory Fundamentals — the formal backbone for the scheduling and backpressure pages.
- [../../git/internals.md](../../git/internals.md) — Git Internals — object model details behind the content-addressing connection.
- [../../compilers/README.md](../../compilers/README.md) — Compilers Track — optimization passes and SSA, the compiler side of the planner connection.
- [../../data-engineering/README.md](../../data-engineering/README.md) — Data Engineering — Flink/Beam/Debezium pages behind the event-log and dataflow connections.
- [../../arch/overview.md](../../arch/overview.md) — Computer Architecture — cache hierarchy and memory-hierarchy numbers used throughout.
- [../followup-tree/rate-limiter-design.md](../followup-tree/rate-limiter-design.md) — Rate Limiter Design — escalation chains for the rate-limiting half of the backpressure connection.
- [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md) — Caching vs Distributed Coordination — the decision-level companion to the caching analogy.
- [../failure-casebook/github-october-2018.md](../failure-casebook/github-october-2018.md) — GitHub October 2018 — the named incident illustrating retry-storm dynamics cited in two atlas pages.
