# Rendezvous Hashing (HRW)

Rendezvous Hashing, also called Highest Random Weight (HRW), is a distributed hashing algorithm that maps a key to one of N servers, with the property that adding or removing a server only reassigns O(K/N) keys (where K is the total key count). It was introduced by Thaler and Ravishankar in 1996 (Topology Dissemination in FIS) as an alternative to consistent hashing. This page covers the algorithm, the comparison to consistent hashing, and the production use cases (Google's pub/sub, Apache Ignite, Cloudflare's load balancing).

## The Algorithm

For each key K and server S, compute a hash `H(K, S)`. Pick the server with the highest hash value. The server selection is deterministic given K and the server set.

```python
def hrw(key, servers):
    weights = [(hash(key, server), server) for server in servers]
    return max(weights)[1]
```

The `hash` function must be:
- **Pseudorandom**: same input → same output, but different inputs → uncorrelated outputs.
- **Fast**: called O(N) times per lookup, where N is the server count.
- **Cryptographically non-reversible**: an attacker shouldn't be able to craft a key that maps to a specific server (avoiding load-balancing attacks).

A typical hash function is a keyed hash like HMAC-SHA1 with a per-deployment secret key:

```python
import hashlib, hmac

def server_hash(key, server):
    h = hmac.new(b"my_secret_key", (key + "|" + server).encode(), hashlib.sha1)
    return int.from_bytes(h.digest()[:8], "big")
```

## Why O(1) Reassignment on Server Changes

When a server S is added to the set:
- For each key K, the hash H(K, S) might be higher than the previous max.
- If yes, the key moves to S; otherwise, it stays with the previous server.
- Expected number of keys that move: K × (1 / (N+1)) = K / (N+1).

When a server S is removed:
- For each key K that was assigned to S, find the next-highest hash.
- The key moves to the server with the next-highest hash.
- Expected: K × (1/N) keys move.

This is O(K/N) reassignment — optimal. Compare with naive modulo hashing (`server = hash(K) % N`), which reassigns ~K keys on any server change (almost all keys move).

## Comparison to Consistent Hashing

| Aspect | Rendezvous (HRW) | Consistent Hashing |
|--------|------------------|---------------------|
| Lookup time | O(N) (hash with each server) | O(log N) (binary search in ring) |
| Memory | O(N) (server set) | O(N) (ring of virtual nodes) |
| Reassignment on add/remove | K/(N+1) or K/N keys move | K/V keys move (V = virtual nodes per server) |
| Implementation complexity | Simple (hash + max) | Moderate (ring + virtual nodes) |
| Hotspot mitigation | None (uniform by hash) | Virtual nodes (mitigates) |
| Production users | Google Pub/Sub, Ignite | Cassandra, Memcached, Dynamo |

Consistent hashing's advantage: O(log N) lookup vs. HRW's O(N). For very large N (>1000), HRW's per-lookup cost becomes significant.

HRW's advantage: simpler implementation, no virtual nodes (which can be tricky to tune for hotspot mitigation), and slightly better distribution for small N (<100).

## Weighted HRW

HRW can be extended to weighted servers (e.g., a server with 2× the capacity gets 2× the keys):

```python
def weighted_hrw(key, servers):
    weights = []
    for server in servers:
        w = server.capacity  # weight 1.0 for normal, 2.0 for double-capacity
        h = hash(key, server)
        # Adjust the hash by the weight (using the "weighted rendezvous hashing" formula)
        weights.append((w_adjusted = -w / math.log(h / MAX_HASH), server))
    return max(weights)[1]
```

This is the algorithm by OJ et al. (Weighted Rendezvous Hashing, 2008). The mathematical property: a server with weight 2.0 receives 2× the keys of a server with weight 1.0.

## Production Use Cases

### Google Cloud Pub/Sub

Pub/Sub uses HRW for topic-to-server assignment. Each topic is hashed against the cluster's server set; the server with the highest hash hosts the topic's metadata.

HRW was chosen over consistent hashing because:
- Simpler implementation.
- Better distribution for the typical topic count (~10K topics, ~50 servers).
- Easy to add weighted servers (e.g., a new server with 2× capacity gets 2× topics).

### Apache Ignite

Apache Ignite (an in-memory data grid) uses HRW for affinity-based key routing. Each key is hashed against the cluster's node set; the node with the highest hash owns the key's primary copy.

Ignite's documentation emphasizes the simplicity of HRW vs. consistent hashing with virtual nodes.

### Cloudflare's Load Balancer

Cloudflare's load balancer uses HRW to assign client IPs to backend pools. Adding a backend pool doesn't invalidate existing assignments; only the new clients (or those whose hash favors the new pool) move.

### Discord's Erlang Chat Servers

Discord uses HRW for routing messages between chat servers. Adding a new server doesn't disrupt existing channels; only channels that hash-favor the new server move.

## Variants

### Skeptical Rendezvous

For very large N, computing N hashes per lookup is expensive. Skeptical rendezvous (also called "skeleton-based") precomputes a sorted list of (hash, server) pairs per key, and the lookup is a binary search.

Trade-off: more memory (store the sorted list), but O(log N) lookup. Used in some implementations where N is large.

### Bounded Load HRW

A modification that limits the load on any single server. If a key's HRW-selected server is over-loaded, the next-highest-hash server is chosen instead. Used in load-balancing applications where fairness matters.

## When to Use Rendezvous vs Consistent Hashing

Use **rendezvous** when:
- N is small (< 1000).
- Simplicity matters more than peak performance.
- Weighted servers are needed.

Use **consistent hashing** when:
- N is large (> 1000).
- Lookup latency is critical.
- The hotspot mitigation via virtual nodes is well-tuned.

## Common Pitfalls

1. **Using a poor hash function.** A weak hash (e.g., CRC32) can have collisions on similar keys, leading to load imbalance. Use a cryptographic hash (SHA-1, BLAKE2).

2. **Forgetting that HRW is O(N) per lookup.** For N=10,000, the per-lookup cost is ~10,000 hash operations = ~1 ms. Use consistent hashing for large N.

3. **Forgetting to handle the empty server set.** If all servers are removed (a rare failure mode), `max()` returns nothing. Always have a fallback.

4. **Trusting that HRW distributes uniformly.** For small N (<10), the variance per server is high (~30% deviation from mean). For uniform distribution, use weighted HRW or consistent hashing with many virtual nodes.

5. **Forgetting that HRW is not stateless.** Each lookup recomputes the hash for each server. The "state" is the server set, which all clients must know.

6. **Forgetting that HRW's reassignment on add/remove is probabilistic.** Real-world reassignment can be slightly more than K/N due to variance. The expected value is K/N; the actual can deviate by ±O(sqrt(K/N)).

## References

- Thaler & Ravishankar, "[A Comparison of Rendezvous and Consistent Hashing](https://www.eecs.umich.edu/~rvs/pubs/HRW.pdf)" (1996)
- OJ et al., "[Weighted Rendezvous Hashing](https://arxiv.org/abs/0809.4451)" (2008)
- [Rendezvous Hashing at Google (Cloud Pub/Sub)](https://cloud.google.com/pubsub/architecture)
- [Apache Ignite: Affinity-based key routing](https://ignite.apache.org/docs/latest/key-value-store/collocated-affinity)
- [Cloudflare Load Balancing with HRW](https://blog.cloudflare.com/common-hash-conflcit-and-solutions/)
- [HRW implementation in Rust (rendezvous_hash crate)](https://github.com/sile/rendezvous_hash)
- [Comparison: HRW vs Consistent Hashing](https://www.eecs.umich.edu/~rvs/pubs/HRW.pdf)
- [LWN: Rendezvous hashing (2014)](https://lwn.net/Articles/609615/)
