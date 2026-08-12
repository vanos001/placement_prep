# Chapter 134: Consistent Hashing

## Prerequisites
- Hashing basics, hash tables, modular arithmetic, binary search trees

## Interview Frequency: ★★★★

Consistent hashing is a fundamental technique in distributed systems for mapping keys to servers with minimal redistribution when servers are added or removed. It is tested at **Google**, **Amazon**, **Meta**, **Microsoft**, **Netflix**, and virtually every company with a distributed infrastructure. It powers CDN load balancing, distributed caches (Memcached, Redis Cluster), distributed databases (Cassandra, DynamoDB), and distributed storage systems.

---

## 134.1 Motivation

### The Problem

You have K keys and N servers. You need to distribute keys across servers. When a server is added or removed, you want to move as few keys as possible.

### Naive Approach: Modular Hashing

```
server = hash(key) % N
```

**Problem**: When N changes (server added/removed), `hash(key) % N` changes for almost every key. If N goes from 3 to 4, approximately (N-1)/N = 75% of keys are remapped. This causes:
- **Cache storms**: Massive cache misses
- **Database overload**: All data needs redistribution
- **Downtime**: Unacceptable for production systems

### What We Want

When a server is added, only ~K/N keys should move (the keys that now map to the new server). When a server is removed, only its ~K/N keys should move to other servers. Everything else stays put.

---

## 134.2 The Hash Ring

**Core idea**: Map both servers and keys to positions on a circular hash space (ring).

```
Hash space: 0 ──────────────────────── 2^32 - 1
            │                           │
            └───────────────────────────┘
                    (circular)

Server positions on ring:
  Server A → hash("ServerA") = 0x1000...
  Server B → hash("ServerB") = 0x5000...
  Server C → hash("ServerC") = 0x9000...

Key assignment: Walk clockwise from key's hash position
until you hit a server. That server owns the key.
```

### How It Works

1. Hash each server to a point on the ring.
2. Hash each key to a point on the ring.
3. To find which server owns a key: walk clockwise from the key's position until you hit a server.

### Why It's Efficient

When a server is added, only the keys between it and the previous server (clockwise) are affected. That's approximately K/N keys. All other keys stay on their original servers.

---

## 134.3 Virtual Nodes

**Problem with basic ring**: If servers are few or unevenly distributed, load balancing is poor. One server might get 50% of the keys.

**Solution**: Virtual nodes (vnodes). Each physical server gets multiple positions on the ring.

```
Physical Server A → vnode A:0, A:1, A:2, ..., A:149
Physical Server B → vnode B:0, B:1, B:2, ..., B:149
Physical Server C → vnode C:0, C:1, C:2, ..., C:149
```

With 150 vnodes per server, the load distribution is nearly uniform (within ~10% of ideal).

**Trade-off**: More vnodes → better balance, but more memory (O(N · vnodes) entries in the ring).

---

## 134.4 Step-by-Step Walkthrough

### Setup

Servers: A, B, C
Vnodes per server: 3 (simplified)

```
Ring positions (after hashing):
  A:0 → 10,  A:1 → 50,  A:2 → 90
  B:0 → 25,  B:1 → 65,  B:2 → 100
  C:0 → 40,  C:1 → 80,  C:2 → 5

Sorted ring: [5:C2, 10:A0, 25:B0, 40:C0, 50:A1, 65:B1, 80:C2, 90:A2, 100:B2]
```

### Key Assignment

Key "user:1001" → hash = 33

Walk clockwise from 33:
- 33 → next position is 40 (C:0)
- **Server C owns "user:1001"**

Key "user:2002" → hash = 72

Walk clockwise from 72:
- 72 → next position is 80 (C:1)
- **Server C owns "user:2002"**

Key "user:3003" → hash = 15

Walk clockwise from 15:
- 15 → next position is 25 (B:0)
- **Server B owns "user:3003"**

### Adding Server D

Add D with vnodes at positions 20, 55, 95.

Updated ring: [5:C2, 10:A0, 20:D0, 25:B0, 40:C0, 50:A1, 55:D1, 65:B1, 80:C2, 90:A2, 95:D2, 100:B2]

Key "user:3003" (hash=15): now walks to 20 (D:0) → **moved to Server D**
Key "user:1001" (hash=33): still walks to 40 (C:0) → **stays on Server C**

Only keys in the ranges now covered by D's vnodes moved. Approximately 3/12 = 25% of keys moved (which is N_vnodes_D / total_vnodes — proportional to D's share).

---

## 134.5 C++ Implementation

```cpp
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include <functional>
#include <iomanip>

class ConsistentHash {
    int numVnodes;
    std::map<size_t, std::string> ring;  // hash → server name
    std::hash<std::string> hasher;
    
public:
    ConsistentHash(int numVnodes = 150) : numVnodes(numVnodes) {}
    
    void addServer(const std::string& server) {
        for (int i = 0; i < numVnodes; i++) {
            size_t hash = hasher(server + "#vnode" + std::to_string(i));
            ring[hash] = server;
        }
        std::cout << "Added server: " << server 
                  << " (" << numVnodes << " vnodes)\n";
    }
    
    void removeServer(const std::string& server) {
        int removed = 0;
        for (int i = 0; i < numVnodes; i++) {
            size_t hash = hasher(server + "#vnode" + std::to_string(i));
            removed += ring.erase(hash);
        }
        std::cout << "Removed server: " << server 
                  << " (" << removed << " vnodes)\n";
    }
    
    std::string getServer(const std::string& key) const {
        if (ring.empty()) return "";
        size_t hash = hasher(key);
        auto it = ring.lower_bound(hash);
        if (it == ring.end()) it = ring.begin();
        return it->second;
    }
    
    // Get distribution statistics
    void printDistribution(int numKeys) const {
        std::map<std::string, int> counts;
        for (int i = 0; i < numKeys; i++) {
            std::string key = "key:" + std::to_string(i);
            counts[getServer(key)]++;
        }
        
        std::cout << "\nDistribution over " << numKeys << " keys:\n";
        for (auto& [server, count] : counts) {
            double pct = 100.0 * count / numKeys;
            std::cout << "  " << server << ": " << count 
                      << " (" << std::fixed << std::setprecision(1) << pct << "%)\n";
        }
    }
};

int main() {
    ConsistentHash ch(150);
    
    // Add 3 servers
    ch.addServer("ServerA");
    ch.addServer("ServerB");
    ch.addServer("ServerC");
    
    // Print distribution
    ch.printDistribution(10000);
    
    // Record key mappings before adding ServerD
    std::vector<std::string> testKeys = {
        "user:1001", "user:2002", "user:3003", "user:4004", "user:5005"
    };
    
    std::cout << "\nBefore adding ServerD:\n";
    std::map<std::string, std::string> before;
    for (auto& key : testKeys) {
        before[key] = ch.getServer(key);
        std::cout << "  " << key << " -> " << before[key] << "\n";
    }
    
    // Add ServerD
    ch.addServer("ServerD");
    ch.printDistribution(10000);
    
    // Check key stability
    std::cout << "\nAfter adding ServerD:\n";
    int moved = 0;
    for (auto& key : testKeys) {
        std::string after = ch.getServer(key);
        std::cout << "  " << key << " -> " << after;
        if (after != before[key]) {
            std::cout << " [MOVED from " << before[key] << "]";
            moved++;
        }
        std::cout << "\n";
    }
    std::cout << "Keys moved: " << moved << "/" << testKeys.size() << "\n";
    
    // Remove a server
    ch.removeServer("ServerB");
    ch.printDistribution(10000);
    
    return 0;
}
```

---

## 134.6 Python Implementation

```python
import hashlib
from bisect import bisect_right
from collections import defaultdict
from typing import Dict, List, Optional


class ConsistentHash:
    """
    Consistent hashing with virtual nodes.
    
    Maps keys to servers using a hash ring. When servers are
    added or removed, only ~1/N of keys are remapped.
    """
    
    def __init__(self, num_vnodes: int = 150):
        self.num_vnodes = num_vnodes
        self.ring: Dict[int, str] = {}  # hash → server
        self.sorted_keys: List[int] = []  # sorted hash positions
        self.servers: set = set()
    
    def _hash(self, key: str) -> int:
        """Hash a string to a 32-bit integer."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)
    
    def add_server(self, server: str) -> None:
        """Add a server with virtual nodes to the ring."""
        if server in self.servers:
            return
        self.servers.add(server)
        for i in range(self.num_vnodes):
            vnode_key = f"{server}#vnode{i}"
            h = self._hash(vnode_key)
            self.ring[h] = server
            self.sorted_keys.append(h)
        self.sorted_keys.sort()
        print(f"Added {server} ({self.num_vnodes} vnodes)")
    
    def remove_server(self, server: str) -> None:
        """Remove a server and its virtual nodes from the ring."""
        if server not in self.servers:
            return
        self.servers.discard(server)
        new_keys = []
        for h in self.sorted_keys:
            if self.ring[h] == server:
                del self.ring[h]
            else:
                new_keys.append(h)
        self.sorted_keys = new_keys
        print(f"Removed {server}")
    
    def get_server(self, key: str) -> Optional[str]:
        """Find the server responsible for the given key."""
        if not self.ring:
            return None
        h = self._hash(key)
        idx = bisect_right(self.sorted_keys, h)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]
    
    def get_distribution(self, num_keys: int = 10000) -> Dict[str, float]:
        """Get the percentage of keys mapped to each server."""
        counts = defaultdict(int)
        for i in range(num_keys):
            server = self.get_server(f"key:{i}")
            counts[server] += 1
        return {s: c / num_keys * 100 for s, c in counts.items()}
    
    def print_distribution(self, num_keys: int = 10000) -> None:
        """Print key distribution across servers."""
        dist = self.get_distribution(num_keys)
        print(f"\nDistribution over {num_keys} keys:")
        for server, pct in sorted(dist.items()):
            bar = "█" * int(pct / 2)
            print(f"  {server}: {pct:.1f}% {bar}")


def demo():
    ch = ConsistentHash(150)
    
    # Add servers
    ch.add_server("ServerA")
    ch.add_server("ServerB")
    ch.add_server("ServerC")
    
    ch.print_distribution()
    
    # Record before state
    test_keys = [f"user:{i}" for i in range(1000)]
    before = {k: ch.get_server(k) for k in test_keys}
    
    # Add ServerD
    ch.add_server("ServerD")
    ch.print_distribution()
    
    # Check how many keys moved
    after = {k: ch.get_server(k) for k in test_keys}
    moved = sum(1 for k in test_keys if before[k] != after[k])
    print(f"\nKeys moved after adding ServerD: {moved}/{len(test_keys)} ({moved/len(test_keys)*100:.1f}%)")
    print(f"Expected: ~{100/4:.1f}% (1/N servers)")
    
    # Remove a server
    ch.remove_server("ServerB")
    ch.print_distribution()
    
    after2 = {k: ch.get_server(k) for k in test_keys}
    moved2 = sum(1 for k in test_keys if after[k] != after2[k])
    print(f"\nKeys moved after removing ServerB: {moved2}/{len(test_keys)} ({moved2/len(test_keys)*100:.1f}%)")


demo()
```

---

## 134.7 Java Implementation

```java
import java.util.*;

public class ConsistentHash {
    private final int numVnodes;
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final Set<String> servers = new HashSet<>();
    
    public ConsistentHash(int numVnodes) {
        this.numVnodes = numVnodes;
    }
    
    private long hash(String key) {
        // FNV-1a hash
        long h = 0xcbf29ce484222325L;
        for (char c : key.toCharArray()) {
            h ^= c;
            h *= 0x100000001b3L;
        }
        return h;
    }
    
    public void addServer(String server) {
        if (servers.contains(server)) return;
        servers.add(server);
        for (int i = 0; i < numVnodes; i++) {
            long h = hash(server + "#vnode" + i);
            ring.put(h, server);
        }
        System.out.println("Added " + server + " (" + numVnodes + " vnodes)");
    }
    
    public void removeServer(String server) {
        if (!servers.remove(server)) return;
        for (int i = 0; i < numVnodes; i++) {
            long h = hash(server + "#vnode" + i);
            ring.remove(h);
        }
        System.out.println("Removed " + server);
    }
    
    public String getServer(String key) {
        if (ring.isEmpty()) return null;
        long h = hash(key);
        Map.Entry<Long, String> entry = ring.ceilingEntry(h);
        if (entry == null) entry = ring.firstEntry();
        return entry.getValue();
    }
    
    public void printDistribution(int numKeys) {
        Map<String, Integer> counts = new TreeMap<>();
        for (int i = 0; i < numKeys; i++) {
            String server = getServer("key:" + i);
            counts.merge(server, 1, Integer::sum);
        }
        System.out.println("\nDistribution over " + numKeys + " keys:");
        for (var entry : counts.entrySet()) {
            double pct = 100.0 * entry.getValue() / numKeys;
            System.out.printf("  %s: %d (%.1f%%)%n", 
                entry.getKey(), entry.getValue(), pct);
        }
    }
    
    public static void main(String[] args) {
        ConsistentHash ch = new ConsistentHash(150);
        
        ch.addServer("ServerA");
        ch.addServer("ServerB");
        ch.addServer("ServerC");
        ch.printDistribution(10000);
        
        // Record before
        Map<String, String> before = new HashMap<>();
        for (int i = 0; i < 1000; i++) {
            String key = "user:" + i;
            before.put(key, ch.getServer(key));
        }
        
        ch.addServer("ServerD");
        ch.printDistribution(10000);
        
        int moved = 0;
        for (int i = 0; i < 1000; i++) {
            String key = "user:" + i;
            if (!before.get(key).equals(ch.getServer(key))) moved++;
        }
        System.out.println("\nKeys moved: " + moved + "/1000 (" 
            + String.format("%.1f", moved / 10.0) + "%)");
        
        ch.removeServer("ServerB");
        ch.printDistribution(10000);
    }
}
```

---

## 134.8 Bounded-Load Consistent Hashing

Standard consistent hashing can have imbalance. **Bounded-load** (Mirrokni et al., 2018) adds a capacity constraint: each server can handle at most `⌈average_load × (1 + ε)⌉` keys. If a server is full, the key goes to the next server on the ring.

```python
class BoundedLoadConsistentHash(ConsistentHash):
    """Consistent hashing with a load bound."""
    
    def __init__(self, num_vnodes: int = 150, epsilon: float = 0.25):
        super().__init__(num_vnodes)
        self.epsilon = epsilon
        self.load: Dict[str, int] = defaultdict(int)
        self.total_keys = 0
    
    def get_server_bounded(self, key: str) -> Optional[str]:
        """Get server with bounded-load constraint."""
        if not self.ring:
            return None
        
        num_servers = len(self.servers)
        if num_servers == 0:
            return None
        
        avg_load = self.total_keys / num_servers
        max_load = int(avg_load * (1 + self.epsilon)) + 1
        
        h = self._hash(key)
        idx = bisect_right(self.sorted_keys, h)
        
        # Walk clockwise, skip overloaded servers
        for _ in range(len(self.sorted_keys)):
            if idx >= len(self.sorted_keys):
                idx = 0
            server = self.ring[self.sorted_keys[idx]]
            if self.load[server] < max_load:
                self.load[server] += 1
                self.total_keys += 1
                return server
            idx += 1
        
        # All servers at capacity (shouldn't happen with reasonable ε)
        return None
```

---

## 134.9 Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| Add server | O(V · log(N·V)) | O(N·V) |
| Remove server | O(V · log(N·V)) | O(N·V) |
| Lookup key | O(log(N·V)) | O(1) |
| Rebalance on add/remove | ~K/N keys moved | — |

Where N = number of servers, V = vnodes per server, K = total keys.

**Practical values**: V = 150-200 gives good balance. N·V for 100 servers = 15,000 entries — trivial memory.

---

## 134.10 Comparison of Approaches

| Approach | Redistribution on Server Change | Lookup Time | Balance |
|---|---|---|---|
| hash % N | ~K · (N-1)/N keys | O(1) | Perfect |
| Basic consistent hash (1 vnode) | ~K/N keys | O(log N) | Poor |
| Consistent hash + vnodes | ~K/N keys | O(log(N·V)) | Good |
| Bounded-load | ≤ ⌈K/N · (1+ε)⌉ per server | O(log(N·V)) | Excellent |
| Jump hash (Google) | ~K/N keys | O(log N) | Perfect for ordered servers |

---

## 134.11 Jump Consistent Hash (Google)

A simpler alternative by Google (Lamping & Veach, 2014) that achieves perfect balance with O(log N) time and O(1) space. Works only when servers are numbered 0 to N-1.

```python
def jump_hash(key: int, num_buckets: int) -> int:
    """
    Google's Jump Consistent Hash.
    Maps key to one of num_buckets buckets (0-indexed).
    Only works when buckets are numbered 0..N-1.
    """
    b, j = -1, 0
    while j < num_buckets:
        b = j
        key = ((key * 2862933555777941757) + 1) & 0xFFFFFFFFFFFFFFFF
        j = int((b + 1) * (1 << 31) / ((key >> 33) + 1))
    return b
```

**Limitation**: Doesn't support arbitrary server names or weighted servers. Used in Google's production systems for sharding.

---

## 134.12 Real-World Applications

1. **Amazon DynamoDB**: Uses consistent hashing for partition assignment. Each partition is a vnode on the ring.
2. **Apache Cassandra**: Uses consistent hashing with vnodes (configurable, default 256). Each node owns multiple ranges.
3. **Memcached**: Clients use consistent hashing to determine which server caches a key.
4. **CDNs (Akamai, Cloudflare)**: Route requests to the nearest edge server using consistent hashing.
5. **Load balancers**: Distribute connections across backend servers.
6. **Distributed file systems**: Map file chunks to storage nodes.

---

## 134.13 Exercises

1. **Easy**: Implement consistent hashing with 1 vnode per server. Measure the load imbalance for 5 servers and 10,000 keys.

2. **Medium**: Implement bounded-load consistent hashing. Compare its balance with standard consistent hashing for 10 servers and 100,000 keys.

3. **Medium**: Implement jump consistent hash. Verify that adding a bucket only moves ~1/N of the keys.

4. **Hard**: Design a consistent hashing scheme that supports weighted servers (server A gets 2x the load of server B).

5. **Hard**: Implement consistent hashing that supports replication — each key is stored on the next k distinct physical servers on the ring.

---

## 134.14 Interview Questions

1. **Q**: What problem does consistent hashing solve?
   **A**: It minimizes key redistribution when servers are added or removed. With hash % N, changing N remaps almost all keys. With consistent hashing, only ~K/N keys move, where K is the total number of keys and N is the number of servers.

2. **Q**: What are virtual nodes and why are they needed?
   **A**: Virtual nodes give each physical server multiple positions on the hash ring. Without them, if servers are few or unlucky, one server might get a disproportionate share of keys. With 100-200 vnodes per server, the load distribution is nearly uniform.

3. **Q**: How would you implement consistent hashing in production?
   **A**: Use a balanced BST (TreeMap in Java, sortedcontainers in Python) to store the ring. Hash server names with a good hash function (SHA-256 or MurmurHash). Use 150-200 vnodes per server. For bounded load, track per-server key counts and skip overloaded servers during lookup.

4. **Q**: What is the time complexity of consistent hashing operations?
   **A**: Lookup: O(log(N·V)) using binary search on the sorted ring. Add/remove server: O(V · log(N·V)) to insert/remove V entries. Space: O(N·V) for the ring.

5. **Q**: How does consistent hashing differ from rendezvous hashing?
   **A**: Rendezvous hashing (HRW) assigns each key to the server with the highest hash(key, server). It achieves the same minimal redistribution property but has O(N) lookup time. Consistent hashing with a BST achieves O(log N) lookup. Rendezvous is simpler and supports weighted servers more naturally.

6. **Q**: A server in your consistent hash ring crashes. What happens to its keys?
   **A**: The keys that were mapped to the crashed server now map to the next server clockwise on the ring. If replication is enabled (k replicas), each key is stored on the next k distinct physical servers, so a single crash doesn't lose data.

---

## 134.15 Cross-References

- **Chapter 43 (Hash Tables)**: Hashing fundamentals
- **Chapter 44 (Hash Functions)**: Choosing hash functions
- **Chapter 156 (Dynamic Graph Algorithms)**: Dynamic data structures
- **Chapter 135 (Distributed Systems)**: Broader distributed systems context
- **Chapter 97 (Pattern Recognition)**: When to use hashing-based approaches

---

## Summary

| Approach | Redistribution | Lookup | Balance | Use Case |
|---|---|---|---|---|
| hash % N | Most keys | O(1) | Perfect | Static systems |
| Consistent hash | ~K/N keys | O(log N) | Good | General purpose |
| + Virtual nodes | ~K/N keys | O(log NV) | Excellent | Production |
| Bounded-load | ≤ K/N·(1+ε) | O(log NV) | Perfect | Strict SLA |
| Jump hash | ~K/N keys | O(log N) | Perfect | Numbered buckets |
