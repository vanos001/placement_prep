# Memcached Internals

Memcached is an in-memory key-value cache, originally developed by Brad Fitzpatrick for LiveJournal in 2003 and now used by Wikipedia, Twitter, YouTube, Reddit, and most large web properties. It is the canonical example of a "sharded, stateless, in-memory cache" and the basis of many subsequent systems (Twemproxy, Nutcracker, Mcrouter). This page covers the architecture, the slab allocator, the LRU per slab class, and the operational patterns that have made Memcached the default cache for two decades.

## The Architecture

A Memcached deployment is a set of N independent Memcached server processes, each on its own machine (or container). There is no cluster membership, no replication, no failover. Clients shard keys across servers via consistent hashing or similar; each server caches only its assigned keys.

```text
Client (web app)
   │
   │ 1. Compute server for key K: server = consistent_hash(K)
   │ 2. Send `GET K` to that server
   │
   ▼
Memcached server (the cache for that key's range)
   - Holds keys assigned to it by the client's hash function
   - State: in-memory only, no persistence
   - Failure: cache miss for the keys it held (clients recompute from DB)
```

The architecture is "shared-nothing": each server is independent. This is intentional — the cache is a performance optimization, not a durability layer. Data loss on a cache server is recoverable from the database.

## The Slab Allocator

Memcached's memory model is the **slab allocator**: memory is divided into "slabs", each slab is a fixed size, and keys of similar size are stored in the same slab.

```text
Slab class 1: chunk size 80 bytes
  [chunk_1][chunk_2][chunk_3]...

Slab class 2: chunk size 104 bytes  (each slab is ~1.25× the previous)
  [chunk_1][chunk_2][chunk_3]...

Slab class 3: chunk size 136 bytes
  ...

Slab class 42: chunk size 1 MB (max)
```

When a key is inserted, Memcached finds the smallest slab class that fits the key + value + metadata, and allocates a chunk from that slab.

The slab allocator avoids memory fragmentation: instead of `malloc`-ing arbitrary sizes (which fragments the heap), Memcached allocates from pre-divided chunks. The chunk sizes grow by ~1.25× per class (the default), giving ~42 classes for sizes 80B to 1MB.

## Per-Slab-Class LRU

Each slab class has its own LRU (Least Recently Used) list. When the slab is full and a new item is inserted, the LRU tail is evicted:

```text
Slab class 2 (104 bytes):
  Head → [item_A][item_B][item_C][...] → Tail
                                          ↑
                                    (evicted first when full)
```

The LRU is per-slab-class, not global. This means a slab class with high churn (lots of inserts) can evict its own items, while a slab class with low churn sits mostly empty. The result: one slab class can be evicting aggressively while another has free memory — Memcached cannot rebalance across slab classes (the "slab automove" feature tries, but slowly).

## The "Slab Automove" Problem

If your workload has more keys of a particular size than the slab class for that size can hold, Memcached will evict frequently for that class while other classes are empty. The `automove` feature periodically moves memory from underused slabs to overused ones, but it's slow (every ~10 minutes) and not always effective.

The common workaround: profile the workload's key size distribution and tune the slab class sizes via the `-f` (slab growth factor) and `-n` (minimum chunk size) flags:

```bash
memcached -m 4096 -f 1.10 -n 64
# 4 GB memory, 1.10× growth factor, 64-byte minimum chunk
```

For a workload with many 1KB-2KB keys, `-f 1.10 -n 64` gives ~50 slab classes from 64B to 1MB, with finer granularity in the 1-2KB range.

## Eviction Policies

Memcached supports several eviction policies (since 1.4):

- **LRU** (default): evict the least recently used item from the same slab class.
- **LRU + (LRU with TTL)**: items with TTL (expiration time) are evicted before items without TTL.
- **FIFO** (`memcached -M`): evict the oldest item, regardless of access time.
- **LFU** (`-o lru_queue=maintail`): not fully implemented in OSS Memcached; available in some forks.

The `-M` flag disables eviction entirely: if the cache is full, new inserts fail with `OUT OF MEMORY`. Useful for caches that must not silently lose data (e.g., a rate-limit counter cache).

## The Binary Protocol

Memcached has two protocols:

- **ASCII protocol** (the original): human-readable text. `get mykey\r\n`, `set mykey 0 3600 5\r\nvalue\r\n`. Easy to test with `nc` or `telnet`.
- **Binary protocol** (since 1.4): binary framing, faster to parse, supports more features (CAS, binary keys).

```text
Binary protocol packet:
  Magic (1 byte): 0x80 (request) or 0x81 (response)
  Opcode (1 byte): 0x00 (get), 0x01 (set), etc.
  Key length (2 bytes)
  Extras length (1 byte)
  Data type (1 byte)
  Reserved (2 bytes)
  Total body length (4 bytes)
  Opaque (4 bytes)
  CAS (8 bytes)
  Extras (variable)
  Key (variable)
  Value (variable)
```

The binary protocol is faster (~20% throughput improvement on small keys) and supports binary keys (the ASCII protocol requires keys to be printable).

## Connection Handling

Memcached uses libevent (or libusockets in newer versions) for I/O multiplexing. A single Memcached process can handle 100,000+ concurrent connections via epoll.

The default `c` (max connections) is 1024; production deployments raise it to 100,000+:

```bash
memcached -c 100000
```

Each connection consumes ~10 KB of memory for its read/write buffers; 100,000 connections = 1 GB. Plan memory accordingly.

## Replication: Twemproxy, Mcrouter, Mason

Memcached itself has no replication. Production deployments add a proxy layer:

- **Twemproxy** (Twitter, 2012): a proxy that shards keys across multiple Memcached servers, with consistent hashing. The proxy is single-threaded, fast (1M ops/sec).
- **Mcrouter** (Facebook, 2014): a more sophisticated proxy with regional pools, async replication, and warm/cold tiering.
- **Mason** (Pinterest): a regional-aware proxy.

The proxy pattern is essential for stateless clients that can't track Memcached server membership directly.

## Common Operational Patterns

### Pattern 1: Read-Through Cache

```python
def get_user(user_id):
    cache_key = f"user:{user_id}"
    user = memcached.get(cache_key)
    if user is None:  # cache miss
        user = db.query("SELECT * FROM users WHERE id = ?", user_id)
        memcached.set(cache_key, user, ttl=3600)
    return user
```

The application reads from the cache first, falls back to the DB on miss, and populates the cache. Standard Memcached usage.

### Pattern 2: Write-Through Cache

```python
def update_user(user_id, data):
    db.update("users", user_id, data)
    memcached.set(f"user:{user_id}", data, ttl=3600)
```

The application writes to the DB then to the cache. The cache is always up-to-date; on cache miss, the next read fetches from DB.

### Pattern 3: Cache Aside (Lazy Update)

```python
def update_user(user_id, data):
    db.update("users", user_id, data)
    memcached.delete(f"user:{user_id}")  # invalidate cache
```

The application writes to the DB and invalidates the cache entry. The next read repopulates the cache. This is more correct than write-through (no race between cache update and DB update) but adds latency on the next read.

### Pattern 4: Memcached as a Session Store

```python
# Store user session in Memcached (TTL = 30 minutes)
session_id = generate_session_id()
memcached.set(f"session:{session_id}", user_data, ttl=1800)
# Read session
session = memcached.get(f"session:{session_id}")
```

Memcached's in-memory nature makes it ideal for session storage: low latency, automatic expiration, and easy horizontal scaling. The risk: a Memcached server failure logs out the users whose sessions were on that server.

## Common Pitfalls

1. **Trusting Memcached with important data.** Memcached is volatile; data is lost on restart. Use it only for cacheable data (data recoverable from a DB).

2. **Forgetting to set TTLs.** Without a TTL, keys stay in the cache forever (or until evicted). Stale data can persist for days.

3. **Using key sizes that don't fit a slab class.** Keys slightly larger than a slab class's chunk size waste memory (the key uses the next larger class, with significant overhead).

4. **Forgetting that Memcached is single-threaded by default.** A single Memcached process uses one CPU core. For high-throughput, run multiple processes per machine.

5. **Trusting "get" for atomic operations.** `get` is atomic, but `get + set` is not. For atomic operations (e.g., incrementing a counter), use `incr` / `decr` which are atomic.

6. **Forgetting about UDP.** Memcached supports UDP for `get` requests (lower latency than TCP for one-shot reads). Enable with `-U 11211`.

7. **Not handling cache stampedes.** If many requests hit the same key on a cache miss, they all query the DB simultaneously (the thundering herd). Solutions: probabilistic early expiration (request the cached value early with some probability), or a lock around the DB query.

## References

- Fitzpatrick, "[Distributed Caching with Memcached](https://web.archive.org/web/20080724000505/http://www.linuxjournal.com/article/7412)" (Linux Journal 2004)
- [Memcached source code](https://github.com/memcached/memcached)
- [Memcached documentation](https://github.com/memcached/memcached/wiki)
- [Twemproxy: Twitter's memcached proxy](https://github.com/twitter/twemproxy)
- [Mcrouter: Facebook's memcached proxy](https://github.com/facebook/mcrouter)
- [Memcached Binary Protocol](https://github.com/memcached/memcached/wiki/BinaryProtocol)
- [Slab Allocator documentation](https://github.com/memcached/memcached/wiki/Performance)
- [LWN: Memcached internals (2014)](https://lwn.net/Articles/593420/)
