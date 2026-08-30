# Cuckoo Hashing: Worst-Case O(1) Lookups via Kick-and-Evict

Most hash tables promise O(1) *average* lookups and quietly reserve the right
to degrade into a probe sequence that touches the whole table. Cuckoo hashing
— named for the bird that shoves eggs out of nests — is the rare design that
keeps the worst case bounded: every key lives in one of exactly two slots, so
a lookup touches two buckets and stops, full stop. The price is paid at
insertion, which may evict a chain of keys, each relocating to its alternate
home until someone finds a free slot. Pagh and Rodler introduced the scheme
in 2001 [1], and the bucketized refinement that made it practical — four-slot
buckets, load thresholds near 0.96, and a small stash for the stubborn tail —
came from the same group and their collaborators over the following years
[2][3]. This page walks the kick mechanism, runs a deterministic
bucketized table to *watch* the threshold behave like a cliff, and sets the
boundaries of when cuckoo beats the alternatives. [Chapter 105]
(../chapters/ch105-cuckoo-robin-hood-hashing.md) introduces the scheme at
interview depth; here we go underneath it, and
[membership filters](../../dbms/advanced/membership-filters.md) cover the
cuckoo *filter* that repurposed the kick mechanics for approximate sets.

## The two-choice contract

The structure is minimal. Two independent hash functions `h1`, `h2` map each
key to one bucket in each of two tables; with 1-slot buckets, a key's entire
storage decision is "which of my two slots":

```text
          key x                        key y
    h1(x)=T1[3]  h2(x)=T2[7]      h1(y)=T1[3]  h2(y)=T2[3]
         |                               |
         v                               v
   T1: [ . . x . ]                 T1: [ . . x y ]     <- x gets kicked
   T2: [ . . . . . . . x ]         T2: [ . . y . . x . ]  <- x relocates to its
                                        ^                  ONLY other home T2[7]
                                  y landed in T1[3], the
                                  bucket cuckoo borrowed its
                                  name from: the egg is shoved
                                  out, and the loser re-nests.
```

Three consequences fall out of the contract. **Lookup** is two memory probes,
independent of load, history, or adversarial keys — the property that makes
cuckoo attractive for systems where a slow lookup is a correctness-adjacent
problem (packet processing, hard real-time). **Deletion** is one array slot
clear, no tombstones, no backward-shift repair — compare linear probing,
where honest deletion is fiddly. **Insertion** carries all the risk: when
both homes are occupied, the new key evicts one occupant, that occupant moves
to its alternate, possibly evicting another, and the cascade either finds a
free slot or runs forever on a cycle.

## The kick cascade and its failure modes

The cascade is a random walk on configurations, and it fails in exactly two
ways. A **cycle**: keys A and B each claim the other's alternate slot, and
the eviction sequence loops between them forever; the walk made no forward
progress, so the only escape is to abandon the attempt. An **exhausted
chain**: after `MAX_KICKS` evictions no free slot has appeared; practical
implementations treat this identically to a cycle and rebuild. Pagh and
Rodler's core theorem makes the first `n` insertions safe at load factor
below 1/2 for the two-table, one-slot-per-bucket scheme, with expected
amortized O(1) insertion cost; the failure probability below that threshold
is so small that "cycle found" is a signal that something else is wrong —
usually the hash functions, not the load [1].

The 1/2 limit is for two *slots* per key. Bucketizing changes the math
decisively: give each bucket `b` slots and the achievable load per slot
climbs steeply with `b` — the standard figures are 0.5 at `b = 1`, about
0.84 at `b = 2`, roughly 0.96 at `b = 4`, and effectively 1.0 near `b = 8`
[2]. Four-slot buckets are the sweet spot that made cuckoo practical: they
match cache lines, keep the two-probe lookup (a bucket is one probe), and
make simultaneous fullness of both homes — the only trigger for a kick —
rare until the table is nearly full. The kick chain below exists to be
*seen* near that threshold, which is exactly what the demo does.

| Variant | Choices | Slot threshold | Lookup | Kick risk at load 0.9 |
|---|---|---|---|---|
| 2 tables, 1-slot buckets | 2 | 0.50 | 2 probes | impossible (table full) |
| 2 tables, 2-slot buckets | 2 | ~0.84 | 2 bucket probes | common |
| 2 tables, 4-slot buckets | 2 | ~0.96 | 2 bucket probes | rare below 0.95 |
| d-ary cuckoo, 1-slot | d | →1 as d grows | d probes | moderate |
| + stash (s slots) | 2 | threshold unchanged | 2 + 1 probes | converts tail failures to stash hits |

The **stash** extension (Kirsch, Mitzenmacher, Wieder) adds a tiny
fixed-size overflow area — often just 2 to 4 slots — checked on every lookup
[3]. Its effect is wildly outsized: with 4-slot buckets and a stash of 4,
failure probabilities that would require rehashing drop by orders of
magnitude, because the failure event at high load is usually just a *handful*
of keys caught in mutual kicks, not a systemic condition. D-ary cuckoo takes
the other direction: `d` hash functions instead of 2 push the threshold
toward 1 while keeping lookups at `d` probes, trading a bigger constant for
density [4].

## A runnable table: comfort, then the cliff

The script below runs one deterministic bucketized table — two tables of 256
four-slot buckets — in two regimes. Pass 1 inserts 900 keys (load 0.439):
insertion is quiet, lookups cost at most two bucket probes. Pass 2 pushes
2,000 keys (load 0.977), past the ~0.96 threshold, where kick chains hit
their limit and rehashing with fresh salts cannot save the table — the
correct response is growth, and the demo says so explicitly.

```python
import collections

# Bucketized cuckoo hashing: 2 tables x 256 buckets x 4 slots, two hash
# functions h1, h2. Insert: place in an empty slot of either home bucket;
# if both are full, kick an occupant to its alternate bucket and repeat
# (max 100 kicks, else failure). Pass 1 runs at a comfortable load; pass 2
# pushes past the practical ~0.96 threshold to show the cliff.

B, CAP, MAX_KICKS = 256, 4, 100

def h(key, table, salt):
    x = (key * 0x9E3779B1 + salt * 0x85EBCA77 + table * 0xC2B2AE3D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x2C1B3C6D) & 0xFFFFFFFF
    x ^= x >> 12
    return (x >> 8) % B

def attempt(n_keys, salt):
    tables = [collections.defaultdict(list), collections.defaultdict(list)]

    def locate(key):
        return [(0, h(key, 0, salt)), (1, h(key, 1, salt))]

    def insert(key):
        for t, b in locate(key):
            if len(tables[t][b]) < CAP:
                tables[t][b].append(key)
                return 0
        t, b = locate(key)[0]
        for kick in range(1, MAX_KICKS + 1):
            victim = tables[t][b].pop(0)
            tables[t][b].append(key)
            alt = [tb for tb in locate(victim) if tb != (t, b)][0]
            t, b = alt
            if len(tables[t][b]) < CAP:
                tables[t][b].append(victim)
                return kick
            key = victim
        return None

    kicked = max_kick = fails = 0
    for k in range(1, n_keys + 1):
        r = insert(k)
        if r is None:
            fails += 1
        else:
            kicked += (r > 0)
            max_kick = max(max_kick, r)

    found = probes = 0
    if fails == 0:
        for k in range(1, n_keys + 1):
            for t, b in locate(k):
                probes += 1
                if k in tables[t][b]:
                    found += 1
                    break
    return fails, kicked, max_kick, found, probes

# pass 1: comfortable load
n1 = 900
print("pass 1: %d keys, load factor %.3f" % (n1, n1 / (2 * B * CAP)))
for salt in (1, 2, 3, 4, 5):
    fails, kicked, max_kick, found, probes = attempt(n1, salt)
    print("  salt %d: %d failures; longest kick chain %d"
          % (salt, fails, max_kick))
    if fails == 0:
        print("  salt %d adopted: lookups %d/%d found with %d table probes"
              % (salt, found, n1, probes))
        print("  (<= 2 table probes per lookup, O(1) worst case)")
        break

# pass 2: push past the ~0.96 bucketized threshold; rehashing cannot save it
n2 = 2000
print("pass 2: %d keys, load factor %.3f -- rehashing with fresh salts:"
      % (n2, n2 / (2 * B * CAP)))
for salt in (1, 3):
    fails, kicked, max_kick, _, _ = attempt(n2, salt)
    print("  salt %d: %d keys hit the %d-kick limit" % (salt, fails, MAX_KICKS))
print("  verdict: no salt fits -> grow the table, do not keep rehashing")
```

Real output:

```text
pass 1: 900 keys, load factor 0.439
  salt 1: 0 failures; longest kick chain 0
  salt 1 adopted: lookups 900/900 found with 1043 table probes
  (<= 2 table probes per lookup, O(1) worst case)
pass 2: 2000 keys, load factor 0.977 -- rehashing with fresh salts:
  salt 1: 8 keys hit the 100-kick limit
  salt 3: 2 keys hit the 100-kick limit
  verdict: no salt fits -> grow the table, do not keep rehashing
```

Two observations worth reading out of this. At load 0.439 the kick machinery
never fires at all — a fresh key's two homes are simultaneously full with
probability near zero, so insertion is a quiet two-bucket probe and every
lookup but 143 of the 900 hit on the first probe (1,043 probes total). At
0.977 the failure mode is exactly the theory's: a handful of keys, not a
collapsing table, each stuck in a kick cycle that no hash salt dissolves —
the load is simply past what two choices and four slots can certify, and the
production response is a resize, not a rehash.

## Interview drill

- **Why is lookup worst-case O(1) while insertion is only expected O(1)?**
  A key's home buckets are fixed by `h1` and `h2`, so finding it is two
  probes regardless of everything. Insertion may trigger a kick cascade of
  unbounded length (a cycle), so it carries expected O(1) amortized cost
  below the load threshold and a small failure probability requiring rehash.
- **Where do cycles come from, and what is the standard fix?** Two keys can
  claim each other's alternate slots, making the eviction walk cycle forever.
  Implementations cap kick chains (dozens to a few hundred) and treat
  exhaustion as a rebuild signal; the stash turns most such tails into
  successful placements [3].
- **Why bucketize, and why 4 slots specifically?** Buckets raise the load
  threshold (0.5 at 1 slot to ~0.96 at 4) while keeping a bucket probe down
  to one cache line, so lookups stay two probes. Four matches common cache
  geometry; 8 slots buy little (threshold already ~1.0) and waste memory.
- **When would you not use cuckoo?** Deletion-heavy workloads that also
  require high load favor chaining (no cascade on delete); workloads needing
  load > 0.9 with 1-slot semantics need d-ary cuckoo; and any workload with
  adversarial keys needs hash-function seeds, because fixed broken hashes
  create degenerate keys whose two homes coincide.

## References

1. R. Pagh, F. F. Rodler, "Cuckoo Hashing," *Journal of Algorithms* 51(2):122-144, 2004. DOI 10.1016/j.jalgor.2003.12.002 (Crossref-verified)
2. M. Dietzfelbinger, C. Weidling, "Balanced allocation and dictionaries with tightly packed constant size bins," *Theoretical Computer Science* 380(1-2):47-68, 2007 (bucketized thresholds; the b=1/2/4/8 figures). DOI 10.1016/j.tcs.2007.02.054 (Crossref-verified)
3. A. Kirsch, M. Mitzenmacher, U. Wieder, "More Robust Hashing: Cuckoo Hashing with a Stash," *SIAM Journal on Computing* 39(4):1543-1561, 2009. DOI 10.1137/080728743 (Crossref-verified)
4. N. Fotakis, R. Pagh, P. Sanders, P. G. Spirakis, "Space Efficient Hash Tables with Worst Case Constant Access Time," *Theory of Computing Systems* 38(2):229-248, 2004 (d-ary cuckoo). DOI 10.1007/s00224-004-1195-x (Crossref-verified)
5. B. Fan, D. G. Andersen, M. Kaminsky, M. Mitzenmacher, "A Cuckoo Filter: Practically Better Than Bloom," *CoNEXT 2014*. DOI 10.1145/2674005.2674994 (Crossref-verified)
6. [Chapter 105: Cuckoo and Robin Hood Hashing](../chapters/ch105-cuckoo-robin-hood-hashing.md) — interview-depth treatment in this book
7. [Membership Filters](../../dbms/advanced/membership-filters.md) — the cuckoo filter and its cousins
8. [Hashing Deep Dive](../chapters/ch94-hashing-deep-dive.md) — universal hashing foundations
