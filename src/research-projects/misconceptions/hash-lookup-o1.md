# "Hash-table lookup is always O(1)"

## Overview

This page examines the most quoted sentence in data-structure education. The
claim is that a hash table gives constant-time lookup, full stop. The reality
is more conditional: O(1) is an *expected* cost under assumptions about hash
quality and load factor, the *worst* case is O(n), and two real, documented
engineering responses to that worst case exist — hash randomization in Python
and bucket treeification in Java 8. This page states the claim fairly, gives
the correct asymptotic statement, and walks through scenarios where the
constant-time promise collapses, with numbers that check out.

## The Claim, Stated Fairly

The strongest common form of the claim is: "A hash map gives O(1) `get` and
`put`. Therefore replacing a balanced tree with a hash map can never make
lookups asymptotically slower, and no input can make a hash lookup cost more
than a tree lookup." Stated this way, the claim is not a caricature; it is
exactly what many candidates conclude from the textbook sentence, and exactly
what gets tested when an interviewer asks "when would you *not* use a hash
table?"

The claim deserves its fairness because the kernel is solid: under simple
uniform hashing with a load factor bounded by a constant, the expected number
of keys examined per lookup is constant. That is a theorem, not folklore. The
question is whether "expected under assumptions" honestly compresses to
"always".

## Verdict

**False.** O(1) is the expected cost under simple uniform hashing and a bounded
load factor; the worst case is O(n) when all keys collide, and real runtimes
carry documented defenses precisely because that worst case is reachable.

## Why People Believe It

The kernel of truth is threefold. First, the mathematics really does work:
with n keys in m buckets under uniform hashing, expected chain length is the
load factor α = n/m, which is constant when the table grows proportionally.
Second, the empirical experience agrees: over millions of lookups in ordinary
programs, no single lookup is observably worse than another, so "constant time"
matches every measurement an ordinary developer ever makes. Third, the
standard libraries themselves advertise speed: the Python wiki's complexity
page lists dictionary operations at average O(1), and that page is the closest
thing Python has to an official complexity contract.

What disappears in compression is the phrase *average*, and what it is
averaged *over* — a good hash function distributing keys independently of
bucket index. Hash tables are a bet on the hash function. Believers in the
claim are quoting a bet whose house edge is tiny but whose tail is unbounded.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Lookup is O(1)" | Expected O(1 + α) under simple uniform hashing; worst case O(n) |
| "Any input behaves the same" | Adversarial inputs can force every key into one bucket |
| "The table absorbs growth invisibly" | Resizing rehashes all n entries — O(n) in one step, amortized O(1) over insertions |
| "Hashing is free" | Computing the hash of a key costs O(k) in the key length k; strings are not O(1) keys |
| "Hash maps beat trees" | Trees give O(log n) *worst* case; hash maps give O(1) *expected* — different guarantees |

The precise statement for chained hashing: expected lookup cost is
O(1 + α), so keeping α bounded by resizing gives expected O(1). Open
addressing behaves similarly while the load factor stays well below 1
(Python's dict resizes at two-thirds full). None of this bounds the worst
case: a single lookup in a degenerate table is O(n) no matter how the
amortization averages out.

## Where It Breaks

**All keys collide.** Put 1,000,000 keys into a table where every key hashes
to the same bucket. Each lookup examines up to 1,000,000 entries — versus 20
comparisons in a balanced tree over the same data. The gap is not a constant
factor; it is the difference between the claim and its contradiction.

**The worst case is reachable, and vendors responded — that is the proof it
is real.** Java's `HashMap` documentation describes buckets with many
colliding keys being converted to balanced trees (from JDK 8): a bucket
treeifies when it reaches `TREEIFY_THRESHOLD` (8 entries) and the table is at
least `MIN_TREEIFY_CAPACITY` (64), turning a degenerate bucket from O(k) into
O(log k). If colliding buckets were impossible, that machinery would not
exist. Python's defense is hash randomization: since Python 3.3, str and
bytes hashing is randomized per process by default (`PYTHONHASHSEED`), using
a keyed SipHash variant, so an attacker cannot precompute colliding keys for
a fresh process. Both mechanisms exist because someone actually sent hostile
keys (the "HashDoS" class of attacks, disclosed in 2011 against multiple
runtimes).

**Resize pauses.** Inserting keys one at a time is amortized O(1), but the
insertion that triggers growth rehashes every existing entry: growing a
10,000,000-entry table rehashes 10,000,000 entries in one call. Amortized
analysis is about total work, not latency; latency-sensitive services see a
single slow request. Redis deliberately rehashes incrementally across
operations for exactly this reason.

**Key length.** Hashing a string of length k costs O(k). A "constant-time"
dictionary lookup of a 1 MB key is at least a million-byte scan. Python
memoizes the hash on the str object, which helps only if you reuse the same
object — a fresh equal string pays full price.

## Practical Implications

- Know the hash function and the input source. Untrusted keys demand
  randomization (Python default) or a treeified fallback (Java), or your own
  choice of a keyed hash.
- Pre-size large tables (`reserve`, `dict` capacity hints, initial capacity in
  Java) to avoid rehash storms during startup and load spikes.
- For worst-case-sensitive code (real-time, request-budget systems), a balanced
  tree's O(log n) worst case is the guarantee you are buying; 20 comparisons
  bounded beats 1 comparison expected when the tail is priced.
- Long string keys: hash once, reuse the object, or intern — the hash is O(k)
  the first time regardless of the table.

## Interview Questions

### Is hash-table lookup O(1)?

Expected O(1) under simple uniform hashing with a bounded load factor; worst
case O(n) when all keys collide. A strong answer names the assumptions
(good hash, uniform distribution, resize policy) and one real defense (Java 8
bucket treeification, Python hash randomization).

### Why did Java 8 start converting long collision chains in `HashMap` buckets to trees?

Because adversarial or unlucky keys can pile many entries into one bucket,
degrading lookups to O(k). Treeifying a bucket at `TREEIFY_THRESHOLD` (8,
with table size at least 64) bounds it at O(log k). This is a documented
admission that the O(1) claim has a reachable worst case.

### Your service shows occasional 200 ms p99 spikes on a pure in-memory cache layer using a hash map. What hash-table-specific causes do you investigate?

Resize rehashing (one request pays for rehashing all entries), collision
chains from a skewed key distribution, and hash computation cost for large
string keys. Fixes: pre-size or use incremental rehashing, check key
distribution, and reuse/intern keys.

## Key Takeaways

- "O(1)" for hash tables means *expected*, under uniform hashing and bounded
  load factor — three conditions, not zero.
- The worst case is O(n), it is reachable in practice, and mainstream runtimes
  ship documented defenses against it (Java treeification, Python hash
  randomization) — strong evidence the boundary is real.
- Amortized O(1) insertion hides O(n) resize pauses; latency budgets care.
- Hashing a key costs O(key length); constant-time claims ignore key size.
- A balanced tree is the structure whose worst case you buy; a hash table is
  the structure whose average case you rent.

## Cross-References

- [Follow-up Tree: Hash Tables](../followup-tree/hash-tables.md) — the
  interview escalation chain that starts from this exact claim
- [Why-Not Handbook: Binary Search vs Hashing](../why-not-handbook/binary-search-vs-hashing.md)
  — the worst-case-vs-expected tradeoff as a decision
- [Assumptions Hunt: Complexity Claims](../assumptions-hunt/complexity-claims.md)
  — the hidden assumptions inside big-O statements
- [Average-Case Complexity](./average-case-complexity.md) — why "average" is
  a distribution claim, not a promise
- [Hashing](../../dsa/chapters/ch07-hashing.md) — collision resolution and
  load factor mechanics
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- Python Wiki. *TimeComplexity*.
  <https://wiki.python.org/moin/TimeComplexity>
- Python documentation. *PYTHONHASHSEED environment variable* (hash
  randomization on by default since Python 3.3).
  <https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED>
- Oracle. *Class HashMap* API documentation — treeification of large
  collision buckets, `TREEIFY_THRESHOLD`, `MIN_TREEIFY_CAPACITY`.
  <https://docs.oracle.com/javase/8/docs/api/java/util/HashMap.html>
- A. Klink and J. Wälde. *Efficient Denial of Service Attacks on Web
  Application Platforms* — 28C3 talk (December 2011) whose adversarial-hash
  demonstration ("HashDoS") motivated the randomization and treeification
  defenses above.
