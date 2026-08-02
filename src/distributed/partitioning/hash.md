# Hash Partitioning

## Overview

Hash partitioning distributes data across partitions by computing a **hash of the partition key** and mapping it to a partition. This provides uniform distribution of data regardless of the key's natural distribution, making it the most common partitioning strategy for key-value stores and distributed databases.

## How It Works

```mermaid
graph LR
    K[Key] --> H[Hash Function]
    H --> V[Hash Value]
    V --> M["Mod N (num partitions)"]
    M --> P[Partition Number]
```

### Formula

```
partition = hash(key) % num_partitions
```

### Example

```mermaid
graph TD
    subgraph "Hash Partitioning (N=4)"
        K1["key='user:123'"] --> H1["hash = 7"]
        H1 --> P1["7 % 4 = 3 → Partition 3"]
        
        K2["key='user:456'"] --> H2["hash = 2"]
        H2 --> P2["2 % 4 = 2 → Partition 2"]
        
        K3["key='user:789'"] --> H3["hash = 5"]
        H3 --> P3["5 % 4 = 1 → Partition 1"]
        
        K4["key='user:101'"] --> H4["hash = 8"]
        H4 --> P4["8 % 4 = 0 → Partition 0"]
    end
```

## Uniform Distribution

Hash functions distribute data uniformly regardless of key patterns:

```mermaid
graph TD
    subgraph "Natural Distribution (Skewed)"
        S1["user:1 → P1"] 
        S2["user:2 → P1"]
        S3["user:3 → P1"]
        S4["user:1000 → P2"]
    end
    
    subgraph "Hash Distribution (Uniform)"
        H1["user:1 → hash → P3"]
        H2["user:2 → hash → P1"]
        H3["user:3 → hash → P4"]
        H4["user:1000 → hash → P2"]
    end
```

## Choosing a Hash Function

| Hash Function | Properties | Use Case |
|--------------|-----------|----------|
| **MurmurHash** | Fast, good distribution | Cassandra, Redis |
| **xxHash** | Very fast, good distribution | General purpose |
| **SHA-256** | Cryptographic, slow | Security-sensitive |
| **MD5** | Fast, good distribution | Legacy systems |

## Partitioning with Hash Tables

```mermaid
graph TD
    subgraph "Hash Ring (Simplified)"
        H0["Hash 0-25"] --> P0["Partition 0"]
        H1["Hash 26-50"] --> P1["Partition 1"]
        H2["Hash 51-75"] --> P2["Partition 2"]
        H3["Hash 76-100"] --> P3["Partition 3"]
    end
```

## Composite Keys

For complex data models, use composite partition keys:

```python
# Simple key
partition = hash(user_id) % N

# Composite key (for multi-tenant systems)
partition = hash(tenant_id + user_id) % N

# Compound key (for time-series)
partition = hash(sensor_id) % N  # Distribute sensors
# Within partition: sort by timestamp
```

## Advantages

1. **Uniform distribution**: Hash functions spread data evenly
2. **No hotspots**: Random distribution prevents concentration
3. **Simple implementation**: Just hash and mod
4. **O(1) lookup**: Direct calculation of partition

## Disadvantages

1. **No range queries**: Can't efficiently query ranges (keys are scattered)
2. **Repartitioning is expensive**: Changing N requires redistributing all data
3. **No ordering**: Data is not sorted within or across partitions
4. **Loss of locality**: Related data may end up on different partitions

## The Repartitioning Problem

When adding a new partition, most keys need to move:

```mermaid
graph TD
    subgraph "Before (N=3)"
        B0["hash%3=0 → P0"]
        B1["hash%3=1 → P1"]
        B2["hash%3=2 → P2"]
    end
    
    subgraph "After (N=4)"
        A0["hash%4=0 → P0"]
        A1["hash%4=1 → P1"]
        A2["hash%4=2 → P2"]
        A3["hash%4=3 → P3"]
    end
    
    B0 -.->|"~75% keys move"| A0
```

With N=3 changing to N=4, approximately 75% of keys must be redistributed. This is why **consistent hashing** is preferred for dynamic clusters.

## Hash Partitioning in Practice

### Cassandra

```sql
-- Partition key determines which node stores the data
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    name TEXT,
    email TEXT
);
-- partition = hash(user_id) % num_tokens
```

### MongoDB

```javascript
// Shard key determines partition
db.users.createIndex({ user_id: "hashed" })
sh.shardCollection("mydb.users", { user_id: "hashed" })
```

### Redis Cluster

```python
# Hash slot = CRC16(key) % 16384
# Each node owns a range of slots
slot = crc16(key) % 16384
```

## Hash Partitioning vs. Range Partitioning

| Aspect | Hash Partitioning | Range Partitioning |
|--------|------------------|-------------------|
| **Distribution** | Uniform | Can be skewed |
| **Range queries** | Not supported | Efficient |
| **Hotspots** | Rare | Common |
| **Repartitioning** | Expensive | Minimal |
| **Use case** | Key-value lookups | Time-series, alphabetical |

## Interview Questions

1. **How does hash partitioning work?**
   - Compute hash(key) % N to determine the partition. This distributes data uniformly regardless of key distribution.

2. **What are the disadvantages of hash partitioning?**
   - No range queries (keys are scattered), expensive repartitioning (changing N redistributes most data), no ordering.

3. **Why is repartitioning expensive with hash partitioning?**
   - Changing N from 3 to 4 means hash%3 ≠ hash%4 for most keys. Approximately (N-1)/N of all keys must move.

4. **When would you choose hash over range partitioning?**
   - Hash: when you need uniform distribution and only do point lookups (key-value stores). Range: when you need range queries or ordered data.

5. **How do databases like Cassandra use hash partitioning?**
   - Cassandra uses MurmurHash to compute a token for each partition key. Each node owns a range of tokens. The partition key determines which node stores the data.

## Common Mistakes

- Using a **poor hash function** — leads to uneven distribution
- Not considering **repartitioning costs** — use consistent hashing for dynamic clusters
- Choosing hash partitioning when **range queries are needed**
- Forgetting about **composite keys** for multi-tenant or hierarchical data
- Not accounting for **data skew** even with hashing (some keys may be much hotter)

## Summary

Hash partitioning provides uniform data distribution by computing hash(key) % N. It's simple, efficient for point lookups, and prevents hotspots. However, it doesn't support range queries and repartitioning is expensive. For dynamic clusters, consistent hashing is preferred. For ordered data, range partitioning is better.

## Cross-References

- [Partitioning Overview](README.md) — Partitioning strategies comparison
- [Range Partitioning](range.md) — Ordered alternative
- [Consistent Hashing](consistent-hashing.md) — Dynamic repartitioning
- [Kafka](../messaging/kafka.md) — Uses hash partitioning for messages
- [Cassandra](../replication/quorum.md) — Uses hash partitioning with quorum replication
