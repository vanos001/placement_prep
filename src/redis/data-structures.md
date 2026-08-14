# Redis Data Structure Internals

## Overview

Redis exposes five core data types (String, List, Hash, Set, Sorted Set) plus Stream, but the underlying C implementations use multiple specialized structures that adapt based on size and content. Understanding these internals is critical for reasoning about memory usage, time complexity, and when to optimize.

## String Internals: SDS (Simple Dynamic Strings)

Redis strings are not raw C strings (`char*`). They use **SDS** (Simple Dynamic Strings), a custom structure that adds metadata:

```c
struct sdshdr {
    int len;       // used bytes (excluding null terminator)
    int free;      // unused bytes (pre-allocated for amortized O(1) append)
    char buf[];    // the actual string data (null-terminated for C compat)
};
```

### Why SDS Instead of C Strings?

| Operation | C String (`char*`) | SDS |
|-----------|-------------------|-----|
| Get length | O(N) — must scan for `\0` | O(1) — read `len` field |
| Append (concat) | O(N) — reallocate + copy | O(1) amortized — use pre-allocated `free` space |
| Binary safety | No — stops at `\0` byte | Yes — length tracked, not null-terminated data |
| Buffer overflow | Manual prevention needed | Automatic — SDS checks before write |

### SDS Types (Redis 3.2+)

Redis uses **five SDS header types** based on string length to minimize memory overhead:

| Type | Header Size | Max Length | Used When |
|------|------------|------------|-----------|
| `sdshdr5` | 1 byte | 32 bytes | Short strings (rarely, due to flags sharing) |
| `sdshdr8` | 3 bytes | 256 bytes | Very short strings |
| `sdshdr16` | 5 bytes | 64 KB | Short strings |
| `sdshdr32` | 9 bytes | 4 GB | Medium strings |
| `sdshdr64` | 17 bytes | 2^64 | Large strings |

This saves ~8 bytes per string on average compared to always using a 17-byte header.

## List Internals: QuickList

Redis lists evolved through three implementations:

1. **Linked list** (pre-3.2): Per-node `malloc` overhead, poor cache locality
2. **ziplist** (3.2): Compact, but O(N) for most operations and risk of cascade reallocation
3. **quicklist** (3.2+): A **doubly-linked list of ziplists**

```
QuickList:

[ziplist_1] <-> [ziplist_2] <-> [ziplist_3]
   64KB          64KB          64KB
  (5 items)     (5 items)     (3 items)
```

### QuickList Design Decisions

- Each node is a ziplist limited to a configurable size (`list-max-ziplist-size`, default -2 = 8KB per node)
- **Compression**: Middle nodes can be LZF-compressed (`list-compress-depth` controls how many nodes near head/tail are uncompressed)
- This combines the cache locality of ziplists with the O(1) push/pop of linked lists
- `LPUSH`/`RPUSH`: O(1) — operate on head/tail ziplist
- `LINDEX`: O(N) — must traverse, but ziplist scanning is cache-friendly

## Hash Internals

### Small Hashes: Listpack (was Ziplist)

When a hash has few fields and small values, Redis uses a **listpack** (replaced ziplist in Redis 7.0):

```
Listpack layout:
[total_bytes] [entry1] [entry2] ... [entryN] [end_byte]

Each entry:
[encoding|length] [data] [backlen (varint, for reverse traversal)]
```

- Encoding uses variable-length integers for small values (e.g., `uint8`, `uint16`, `int32`)
- Strings are stored inline with length prefix
- Trigger: controlled by `hash-max-listpack-entries` (default 512) and `hash-max-listpack-value` (default 64 bytes)
- When thresholds are exceeded, converts to a hashtable

### Large Hashes: Hashtable

Two hashtables (dict) are used — one current, one for rehashing:

```
dict:
├── ht[0]: current hash table
│   ├── table[]: array of dictEntry* (bucket array)
│   ├── size: total buckets (power of 2)
│   ├── sizemask: size - 1 (for fast modulo)
│   └── used: number of entries
├── ht[1]: rehash target (0 capacity initially)
└── rehashidx: -1 (not rehashing) or 0..size-1 (bucket being rehashed)
```

**Progressive rehashing**: Redis doesn't rehash the entire table at once (that would block). Instead, it rehashes one bucket at a time — every `CR` command (1000 ops) rehashes one bucket, or every `RDB` operation rehashes 100 buckets. Both tables are queried during rehashing.

## Set Internals

### intset (Integer-Only Sets)

When all set members are integers within int64 range, Redis uses an **intset**:

```
intset layout:
[encoding] [length] [contents[]]

Encoding: INTSET_ENC_INT16 (2 bytes each)
           INTSET_ENC_INT32 (4 bytes each)
           INTSET_ENC_INT64 (8 bytes each)

Contents: Sorted array of integers
```

- O(log N) lookup via binary search
- O(N) insert (must shift elements to maintain sorted order)
- Automatically upgrades encoding (int16 → int32 → int64) as needed
- Trigger: `set-max-intset-entries` (default 512)

### Hashtable (Mixed Sets)

If any member is not an integer or the set exceeds the intset threshold, Redis uses the same `dict` (hashtable) as for large hashes. Uses SipHash for hash function.

## Sorted Set Internals

Sorted sets use a **dual structure**: a skiplist for range queries and a hashtable for O(1) member lookups.

### Skiplist

```
Level 4:  HEAD ──────────────────────────────── NIL
Level 3:  HEAD ──────── 30 ─────────────────── NIL
Level 2:  HEAD ──── 10 ── 30 ──────── 70 ────── NIL
Level 1:  HEAD ── 5 ─ 10 ─ 20 ─ 30 ─ 50 ─ 70 ─ NIL
```

Each node stores a member, a score (double), and a random level (generated by `ZSKIPLIST_MAXLEVEL=32` and `ZSKIPLIST_P=0.25`). Expected number of pointers per node = 1.33 (since P=0.25).

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `ZADD` | O(log N) | Insert into skiplist + O(1) hashtable update |
| `ZSCORE` | O(1) | Hashtable lookup |
| `ZRANGE` | O(log N + M) | Skiplist traversal, M = range size |
| `ZRANK` | O(log N) | Skiplist traversal with rank tracking |

### Memory Optimization

- Small sorted sets use **listpack** (same thresholds as hashes, controlled by `zset-max-listpack-entries` default 128, `zset-max-listpack-value` default 64 bytes)
- Within the skiplist, Redis uses a specialized encoding for scores that are close to each other

## Stream Internals

Streams (added in Redis 5.0) use a **radix tree of listpacks**:

```
Radix Tree (by timestamp prefix):
  "16094"  → [listpack: entries for 1609400000-1609499999]
  "16095"  → [listpack: entries for 1609500000-1609599999]
  "16096"  → [listpack: entries for 1609600000-1609699999]
```

- Each node in the radix tree holds a **listpack** of stream entries sharing a common timestamp prefix
- Entries within a listpack are ordered by ID
- Consumer groups are tracked as separate metadata structures
- Radix tree nodes can be compressed when they have only one child
- `XADD` is O(log N) for insertion into the radix tree; O(1) amortized for appending to the current listpack node
- `XRANGE` is O(log N + M) for range queries

## Memory Optimization Techniques

| Technique | Applies To | Savings |
|-----------|-----------|---------|
| **SDS type selection** | All strings | 4-16 bytes per string |
| **Listpack encoding** | Small hashes, sets, sorted sets | Up to 10x vs hashtable overhead |
| **intset** | Integer-only sets | ~4-8 bytes per element vs 64+ byte dictEntry |
| **Quicklist with compression** | Lists | LZF compression on middle nodes |
| **Object sharing** | Small integers (0-10000) | Reuse pre-allocated string objects |
| **Pointer tagging** | Redis Objects | Encode type + encoding in low bits of pointer |

### When Optimization Matters Most

With millions of small keys, per-key overhead dominates:
- A `redisObject` header is 16 bytes (on 64-bit)
- A dictEntry is 24 bytes (key ptr + val ptr + next ptr)
- Total overhead per key: ~40 bytes minimum, regardless of value size
- **Solution**: Use hashes to group related fields: `HSET user:1 name Alice age 30` is cheaper than `SET user:1:name Alice` + `SET user:1:age 30`

## Interview Questions

**Q: Why does Redis use SDS instead of C strings?**
A: Three main reasons: (1) **O(1) length** — C strings require `strlen()` (O(N)), SDS stores `len` in the header. (2) **Binary safety** — C strings can't contain null bytes; SDS uses length-delimited data. (3) **Buffer overflow prevention** — SDS checks `free` space before writes and auto-extends. Additionally, SDS supports **amortized O(1) append** via pre-allocated `free` space.

**Q: Explain the quicklist data structure. Why not just use a linked list or ziplist?**
A: A plain linked list has high per-node `malloc` overhead (each node is a separate allocation) and poor cache locality. A single ziplist is compact but has O(N) insertions at arbitrary positions and a risk of cascade reallocation on large data. Quicklist splits into a doubly-linked list of ziplists: each ziplist is ~8KB (cache-friendly), push/pop on head/tail is O(1) (operates on the edge ziplist), and middle nodes can be LZF-compressed for additional memory savings.

**Q: How does progressive rehashing work in Redis?**
A: When the load factor exceeds 1 (or 5 for fork-saving mode), Redis allocates a new hash table (ht[1]) at 2x the size. Instead of rehashing everything at once, it sets `rehashidx` to 0 and rehashes one bucket per 1000 operations (or 100 during RDB save). During rehashing, both ht[0] and ht[1] are checked on lookups; new inserts go to ht[1] only. This spreads the O(N) rehash cost over many operations.

**Q: Why do sorted sets use both a skiplist and a hashtable?**
A: The skiplist provides O(log N) range queries (`ZRANGE`, `ZRANGEBYSCORE`) and O(log N) insert/delete by score. The hashtable provides O(1) lookup by member (`ZSCORE`). Without the hashtable, `ZSCORE` would be O(log N). Without the skiplist, range queries would be O(N) (scan the entire set).

**Q: What happens when a hash exceeds `hash-max-listpack-entries`?**
A: Redis converts the listpack to a full hashtable. This conversion is O(N) and happens inline during the command that triggers the threshold breach. After conversion, all operations switch to hashtable semantics (O(1) amortized for HSET/HGET, O(1) amortized for HDEL). The threshold is configurable — increasing it saves memory for small hashes at the cost of slower operations as the listpack grows.

**Q: A Redis instance has 10 million keys, each storing a small hash with 3 fields. How can you reduce memory?**
A: (1) Ensure the hashes stay below `hash-max-listpack-entries` (512) — at 3 fields, they will. (2) Each hash key has ~40 bytes of overhead (redisObject + dictEntry); if field names are long, shorten them. (3) Consider using a single large hash instead of many small ones: `HSET all_users 1:field1 val 1:field2 val ...` — one key overhead instead of 10M. (4) Enable `activedefrag yes` for Redis 4.0+ to reclaim fragmentation.

## References

- [Redis SDS source](https://github.com/redis/redis/blob/unstable/src/sds.h)
- [Redis QuickList source](https://github.com/redis/redis/blob/unstable/src/quicklist.h)
- [Redis Memory Optimization](https://redis.io/docs/management/optimization/memory-optimization/)
