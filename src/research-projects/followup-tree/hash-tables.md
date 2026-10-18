# Follow-up Tree: Hash Tables

## Overview

"What is a hash table?" is the most common data-structures opener, and also the one with the deepest escalation ladder, because it runs through probability, amortized analysis, adversarial inputs, and distributed systems. This page walks the ladder rung by rung: for each follow-up, what it tests, how to reason through it, and the answer with its edge cases. The companion misconception — that lookup is unconditionally O(1) — is documented in [Hash Lookup Is Always O(1)](../misconceptions/hash-lookup-o1.md); here we show how an interviewer climbs *to* that realization.

## The Opening Question

**"What is a hash table?"**

The expected core answer: a data structure mapping keys to values in expected O(1) time, by computing an index from the key with a hash function and storing the entry in a bucket indexed by that hash. Two components carry the whole structure: a *hash function* that scatters keys uniformly across buckets, and a *collision strategy* that handles two keys landing in the same bucket. Say both, because each one is a rung of the ladder and the interviewer is choosing which rung to climb first.

Why this answer is correct: the O(1) claim is *statistical*, not structural. Nothing about the array makes lookup constant time; it is the assumption that the hash function distributes keys so that the average bucket holds O(1) entries. Stating the assumption on rung one is what earns the follow-up instead of being ambushed by it on rung four.

## Follow-up 1: How Do You Handle Collisions?

**What it tests:** whether you know that "hash table" is a family of designs, not one design, and that the designs have different cache, memory, and deletion behavior.

**How to reason:** compare the two families on the axes that matter: memory locality, worst-case behavior, deletion, and load-factor tolerance.

**Answer.** Chaining stores colliding entries in a linked list (or tree) per bucket; open addressing stores all entries in the array itself and probes for the next free slot (linear probing, quadratic probing, double hashing). Chaining tolerates load factors above 1 and deletes trivially; open addressing has better cache locality — probe sequences touch contiguous memory instead of chasing pointers — but requires tombstones for deletion (you cannot mark a slot empty, or you break the probe chains of later insertions) and degrades sharply as the load factor approaches 1.

Edge cases worth naming: linear probing suffers *primary clustering* — long runs of occupied slots that lengthen future probe sequences (expected unsuccessful search is about (1 + 1/(1−α)²)/2 probes at load α, versus roughly 1 + α for chaining); Robin Hood hashing evicts rich entries (far from home slot) for poor ones to flatten probe-length variance; cuckoo hashing gives O(1) *worst-case* lookups at the cost of eviction loops on insert. Java's HashMap switches a chain to a red-black tree once a bin grows past 8 entries, capping the worst case at O(log n) per lookup. For depth on these variants, the repo's [Hashing](../../dsa/chapters/ch07-hashing.md) chapter and [Cuckoo and Robin Hood Hashing](../../dsa/chapters/ch105-cuckoo-robin-hood-hashing.md) cover the mechanics; here the interview signal is *knowing the trade exists and when each wins*.

## Follow-up 2: What Is the Load Factor, and When Do You Resize?

**What it tests:** whether you understand that performance is a function of *load*, and that a table must react to its own fullness.

**How to reason:** the load factor α = entries / buckets is the single knob that couples hash-table performance to memory usage. Ask: what does each collision strategy pay as α grows, and therefore where must the growth trigger sit?

**Answer.** For chaining, expected lookup cost grows linearly with α, so 0.75–1.0 is tolerable. For linear probing, cost grows superlinearly — at α = 0.9 an unsuccessful lookup costs about 50 probes on average — so implementations grow earlier, typically around 0.5–0.7. On trigger, allocate a new bucket array (usually double) and rehash every entry, because each key's bucket index depends on the array size. Doubling keeps the amortized cost constant (next follow-up); growing by a constant amount would make inserts O(n) amortized. Two senior details: growth by powers of two pairs with *multiplicative* hashing (masking low bits), while prime table sizes pair with division-based hashing — modern implementations mostly use power-of-two sizes with a well-mixed hash rather than primes with a weak one. And some tables (Redis's dict) rehash *incrementally*, migrating a few buckets per operation to avoid a single 100 ms pause — the same reasoning that turns one big rehash into amortized work, applied to latency instead of complexity.

## Follow-up 3: Prove the Amortized Cost of Insertion

**What it tests:** whether you can do the analysis, not just recite it — and whether you know the difference between average, worst, and amortized cases.

**How to reason:** charge the expensive rehash to the cheap inserts that precede it. Sum the geometric series.

**Answer.** Start with 1 bucket and double whenever full. Inserting n keys incurs rehash costs of 1 + 2 + 4 + … + n/2 + n ≈ 2n element copies, plus the n insertions themselves: O(n) total, so **O(1) amortized per insert**. Contrast the three cases explicitly, because this is the rung where candidates conflate them: *worst case* insert is O(n) (the insert that triggers a rehash of the whole table); *average case* is O(1) if keys are well distributed; *amortized* is O(1) for *any* input sequence, because the doubling structure — not luck — guarantees it. The distinction matters operationally: amortized O(1) still means a periodic latency spike, which is why latency-sensitive systems incrementalize the rehash (Follow-up 2). The [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md) chapter derives this in general; the [Average vs Worst Case](../misconceptions/average-case-complexity.md) page covers the misconception directly.

## Follow-up 4: What Is the Worst Case, and Who Can Force It?

**What it tests:** the adversariality axis — whether you have asked who controls the keys, which is the move that separates book knowledge from threat modeling.

**How to reason:** the average-case bound assumed uniform hash distribution. Ask what happens when the assumption is false, then ask what makes it false in practice.

**Answer.** If every key lands in one bucket, every operation is O(n) over that bucket's chain: insert, lookup, everything. This is not hypothetical. Crosby and Wallach's USENIX 2003 paper ("Denial of Service via Algorithmic Complexity Attacks") demonstrated the attack against real systems; Klink and Wälde's 28C3 talk in 2011 showed it against PHP, Java, Python, and Ruby web frameworks by POSTing thousands of colliding form parameters — a few kilobytes of request body forcing hours of CPU work. The defenses, in order of prevalence: (1) **keyed hashing** — randomize the hash function per process with a secret seed, so an attacker cannot precompute collisions; Python has randomized hashes since 3.4, Rust's std HashMap uses SipHash-1-3 with a per-map random key (see the [Rust HashMap docs](https://doc.rust-lang.org/std/collections/struct.HashMap.html)), and SipHash ([Aumasson & Bernstein](https://131002.net/siphash/)) was designed exactly for this: a fast *short-input* PRF; (2) **treeified buckets** — Java 8's HashMap turns long chains into red-black trees, capping the damage at O(log n) ([OpenJDK JEP 180](https://openjdk.org/jeps/180)); (3) **input limits** — reject oversized parameter maps before they reach the table. The senior observation: whether you need any of this depends on whether the attacker can choose your keys. A server hashing attacker-controlled request parameters needs keyed hashing; a job hashing its own internally generated IDs mostly does not. For the full treatment, see [Adversarial Input and Hash Flooding](../assumptions-hunt/input-constraints.md).

## Follow-up 5: What Changes in a Distributed Setting?

**What it tests:** whether the O(1) abstraction survives the move from memory to a fleet — the consequence axis of escalation.

**How to reason:** the in-memory table maps key → slot via modulo. Replacing buckets with servers keeps the same math but changes the cost of *resize*: now "rehashing" means moving data over the network.

**Answer.** With n keys modulo m servers, adding one server remaps nearly every key — a full data migration. *Consistent hashing* hashes both keys and servers onto a ring and assigns each key to the next server clockwise, so adding a server relocates only ~1/m of the keys (Karger et al., 1997, "Consistent Hashing and Random Trees"). Real deployments add *virtual nodes* — each physical server appears at many ring positions — to smooth load imbalance and handle heterogeneous capacity; this is the design in Amazon's Dynamo paper ("Dynamo: Amazon's Highly Available Key-value Store", DeCandia et al., SOSP 2007, [allthingsdistributed.com](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)) and in client-side memcached routing. Edge cases: hot keys still overload a single node (consistent hashing balances *quantity*, not *popularity* — see [Consistent Hashing](../../dsa/chapters/ch134-consistent-hashing.md) for the mechanics); and removing a node doubles the load on its ring successor, which can cascade. The ladder now closed: the same "resize" analysis from Follow-up 2 reappeared as re-sharding, and the same adversarial-input analysis from Follow-up 4 reappears as hot keys.

## Follow-up 6: "Now Design a Hash Table"

**What it tests:** design judgment — the rung-5 question. The interviewer wants decisions and their justifications, not a transcription of `unordered_map`.

**How to reason:** enumerate the decision points in dependency order and *say the trade-off at each one out loud*: hash function, bucket strategy, load factor and growth policy, deletion strategy, iteration order, concurrency.

**Answer sketch.** For an in-memory, single-threaded, general-purpose table: a well-mixed non-cryptographic hash with a random seed (Murmur/wyhash-style mixing is enough; SipHash if inputs are attacker-controlled); open addressing with linear probing for cache locality; load factor 0.7 with doubling; tombstones with a rehash-to-clean policy when tombstone density rises; unordered iteration unless callers pay for order. Each choice should be defended by *what workload it optimizes* — and the strongest answer volunteers the alternatives that were rejected and why. If the interviewer then twists ("make it thread-safe," "make it persistent," "make it sharded"), the twist resolves via the ladders already climbed: thread safety → per-bucket locks or concurrent tables like Java's ConcurrentHashMap ([Concurrent Hash Maps](../../concurrency/concurrent-hashmap.md)); persistence → this is now a storage-engine question, see [LSM vs B+tree](./database-indexes.md); sharding → Follow-up 5.

## How to Approach Unfamiliar Variations

The transferable template for this chain:

1. **Locate the assumption behind any complexity claim.** O(1) = uniform hashing + O(1) hash computation + bounded load. Any variation ("strings up to 10 GB," "keys chosen by the client," "load factor 5") invalidates one of the three clauses — find which.
2. **Distinguish who controls the input.** Internally generated keys → average case is real; attacker-controlled keys → design for the worst case (seeded hashing, treeified buckets, input limits).
3. **Distinguish the three complexity cases explicitly.** Worst, average, and amortized answer three different questions: what can happen, what usually happens, what you promise over any sequence. Interviewers escalate precisely where you blur them.
4. **When the table crosses a boundary — disk, network, process — re-derive, do not recall.** A distributed hash table is the same structure with resize cost measured in network transfers; a persistent hash table is the same structure with locality cost measured in I/Os. Name the old cost, name the new cost, and the design falls out.

## Interview Questions

**Q: Why does Java's HashMap treeify buckets instead of just reseeding its hash function?**
A: Different threat models for different layers: reseeding helps when the application cannot limit attacker-chosen keys, but Java is a library that cannot assume its callers use it safely — so it caps the *damage* (O(log n) per bin) rather than only the *likelihood*. The two defenses compose: SipHash-style seeds make collisions rare, treeification makes them cheap.

**Q: Your service's p99 latency spikes every few minutes in lockstep with memory growth. Hypothesis?**
A: A hash table (or map) somewhere is rehashing on resize: the spike is the O(n) worst-case insert that the amortized analysis hides. Check table sizes at spike time; fixes are pre-sizing the map at known capacity, or moving to incremental rehashing (Redis-style) if pre-sizing is impossible.

**Q: Why is linear probing's load factor usually capped below 0.7 while chaining tolerates 1.0?**
A: Cost models differ: chaining pays 1 + α expected probes (mild, linear), linear probing pays ~(1 + 1/(1−α)²)/2 for unsuccessful search (superlinear, catastrophic near 1). The cap is not style — it is where each curve crosses an acceptable-probe-count threshold.

**Q: A teammate proposes using a cryptographic hash (SHA-256) for all hash tables to prevent hash flooding. Right call?**
A: It fixes security by overspending: SHA-256 is ~10× slower than needed and solves only the adversarial case. Keyed *short-input* PRFs like SipHash give the same flood resistance at general-purpose speed. Reserve full cryptographic hashes for where collision resistance itself is required (signatures, content addressing).

## Key Takeaways

- A hash table is a hash function plus a collision strategy; every performance claim is conditional on the function distributing keys uniformly, and every escalation starts by testing that condition.
- Worst, average, and amortized are three different promises: O(n) worst-case insert, O(1) average lookup, O(1) amortized insert — and latency spikes are the visible shadow of the amortized bound.
- Hash flooding is the canonical "average case is a lie" attack; the defenses (seeded hashing, treeified buckets, input limits) each map to a different threat model.
- Consistent hashing is the resize analysis over the network: same math, different migration cost, new failure modes (hot keys, successor overload).
- When asked to design one, the grading is on spoken trade-offs at each decision point, not on matching a reference implementation.

## Cross-References

- [Hashing](../../dsa/chapters/ch07-hashing.md) — the mechanics: hash functions, collision strategies, table implementation.
- [Hashing Deep Dive](../../dsa/chapters/ch94-hashing-deep-dive.md) — universal hashing, perfect hashing, the math behind the average-case bound.
- [Cuckoo and Robin Hood Hashing](../../dsa/chapters/ch105-cuckoo-robin-hood-hashing.md) — the O(1)-worst-case-lookup variants and their insert costs.
- [Consistent Hashing](../../dsa/chapters/ch134-consistent-hashing.md) — ring layout, virtual nodes, and rebalancing mechanics.
- [Hash Lookup Is Always O(1)](../misconceptions/hash-lookup-o1.md) — the misconception this ladder is built to expose.
- [Adversarial Input and Hash Flooding](../assumptions-hunt/input-constraints.md) — sibling deep-dive on input-controlled complexity claims.
- [Binary Search vs Hashing](../why-not-handbook/binary-search-vs-hashing.md) — the structured comparison when sorted order is also needed.
- [Concurrent Hash Maps](../../concurrency/concurrent-hashmap.md) — thread-safety designs from per-bucket locks to lock-free read paths.
- [DB Indexes: B+tree vs Hash](./database-indexes.md) — where a hash index wins and why databases still default to B+trees.
- [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md) — amortized analysis toolkit used in Follow-up 3.
