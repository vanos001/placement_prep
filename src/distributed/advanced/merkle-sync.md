# Merkle Tree Synchronization

A Merkle tree is a hash tree where each non-leaf node is the hash of its children. In distributed systems, Merkle trees are the standard data structure for detecting divergence between two replicas with O(log N) communication cost (where N is the number of keys). This page covers the tree construction, the sync protocol, and the production use cases (Cassandra repair, Bitcoin light clients, Git blob trees).

## The Structure

A Merkle tree over a set of (key, value) pairs:

```text
                              Root hash = H(H_L || H_R)
                              /                          \
                  H_L = H(H_LL || H_LR)        H_R = H(H_RL || H_RR)
                  /              \              /              \
        H_LL = H(L1||L2)    H_LR = H(L3||L4)  H_RL = H(L5||L6)  H_RR = H(L7||L8)
        /        \         /        \         /        \         /        \
      L1         L2       L3         L4       L5         L6      L7         L8
   (k1,v1)    (k2,v2)  (k3,v3)    (k4,v4)  (k5,v5)    (k6,v6)  (k7,v7)    (k8,v8)
```

Each `Li` is a hash of `(key_i, value_i)`. Each non-leaf `Hi` is `H(child1 || child2)`, where `H` is a cryptographic hash function (typically SHA-256).

A leaf change (e.g., `(k3, v3)` → `(k3, v3')`) propagates up: `H_LR` changes, then `Root` changes. Two replicas with the same root have identical data; two replicas with different roots have diverged somewhere, and the tree's structure lets them identify exactly which leaves differ in O(log N) rounds.

## The Sync Protocol

To sync replicas A and B that each have a Merkle tree over the same key range:

```text
Round 1: A sends RootA. B compares with RootB.
  If equal: A and B agree on all keys in this range. Done.
  If different: descend.

Round 2: A sends H_L (left subtree root). B compares with its H_L.
  If equal: divergence is in the right subtree. Skip left.
  If different: divergence is in the left subtree. Recurse left.

Round 3: A sends H_R (right subtree root). B compares with its H_R.
  If different: recurse right.

... continue until reaching leaves.

Final: A sends the differing (key, value) pairs to B. B applies them.
```

The communication cost is O(log N) for the comparison (sending root, then 2 child roots, then 4 grandchild roots, etc.) plus O(diff) for the actual data transfer (only the differing leaves).

## Hash Functions

The hash function determines the Merkle tree's security properties:

- **SHA-256**: standard choice for tamper-resistant trees (Bitcoin, Git). 32 bytes per node.
- **xxHash, CityHash, FarmHash**: fast non-cryptographic hashes for performance-sensitive sync (Cassandra, Riak). 8 bytes per node, but vulnerable to malicious collisions.
- **MurmurHash3**: similar to xxHash. 16 bytes per node.

For sync between trusted replicas (same cluster), a fast non-cryptographic hash is appropriate. For sync between untrusted nodes (e.g., a client verifying a server's data), a cryptographic hash is required to prevent a malicious server from hiding divergence.

## Tree Construction Patterns

### Range-Based (Dynamo, Cassandra)

Keys are partitioned into ranges (e.g., a hash range from `0x0000` to `0xFFFF`), and each range has its own Merkle tree. The tree's leaves are sorted by key, so two replicas with the same keys produce the same tree.

A Cassandra vnode (virtual node) has one Merkle tree covering its range. The tree is rebuilt on demand during repair (not maintained continuously).

### Key-Hash-Based (Git, Bitcoin)

The tree's leaves are the hash of the key (not the key itself). This allows unsorted insertion: leaves are sorted by their hash, which is uniformly distributed. Git's tree objects work this way; Bitcoin's transaction Merkle tree uses transaction hashes as leaves.

### BLOB-Based (Git packfiles)

For storage systems where the "value" is a large blob, the tree's leaves are hashes of blob chunks. The blob is split into 4 KB chunks; each chunk is hashed; the tree of hashes is the "manifest". Two replicas with the same root have the same blob without exchanging it.

This is the basis of Git's packfile format and IPFS's content-addressable storage.

## Production Use Cases

### Cassandra's Anti-Entropy Repair

`nodetool repair` runs a Merkle tree sync per vnode. For each vnode pair:

1. Each replica computes a Merkle tree over its vnode's keys.
2. The trees are exchanged and compared.
3. Diverging leaves trigger row-level repair.

The tree computation is expensive (O(N) hash operations for N keys). Cassandra 4.x added "incremental repair" that only hashes keys modified since the last repair, reducing the per-repair cost.

### Git's Blob Tree

Each Git tree object is a Merkle tree over the blobs and subtrees in a directory. The commit's hash is the hash of the tree's root, which transitively covers every blob in the repository.

A `git fetch` between two repos compares commit hashes; if they differ, the trees are compared recursively to identify which blobs differ, and only those are transferred. This makes `git fetch` extremely efficient — most repos share most of their history, and only the new commits' blobs need to be transferred.

### Bitcoin SPV (Simplified Payment Verification)

A Bitcoin block contains a Merkle tree over its transactions. A "light" client that doesn't download the full block can verify a transaction is included by:

1. Asking a full node for the transaction's path in the Merkle tree (log N hashes).
2. Recomputing the root from the path.
3. Comparing with the block's published root hash.

This is how SPV wallets work without downloading the full blockchain.

### IPFS Content Addressing

IPFS stores each file as a Merkle tree over its chunks. The file's IPFS "CID" is the root hash. Two IPFS nodes with the same CID can confirm they have the same file with no further communication; if their CIDs differ, they compare trees to identify the differing chunks.

## Implementation Patterns

### Incremental Tree Maintenance

Recomputing the entire Merkle tree on each write is O(N). The standard optimization is to maintain the tree incrementally: on each write, update only the path from the modified leaf to the root (O(log N)).

```python
def update_key(tree, key, value):
    leaf_hash = hash(key, value)
    tree.leaf[key] = leaf_hash
    # Walk up the tree, updating each ancestor's hash
    node = leaf.parent
    while node:
        node.hash = hash(node.left.hash + node.right.hash)
        node = node.parent
```

This is what Riak's AAE does: the tree is maintained continuously, and comparison is cheap (just compare the root).

### Lazy Tree Construction

For very large key sets (e.g., 100M keys), the tree's memory cost is ~100M × 32 bytes = 3 GB per replica, which is too much for small nodes. The solution is to construct the tree lazily — only when sync is requested, and discard it after.

Cassandra takes this approach: `nodetool repair` builds the tree, syncs, and discards. The cost is high (full tree build) but the steady-state memory is zero.

### Hash Tree Skips

For very large trees, an alternative is a "skip list" structure: instead of a binary tree, use a multi-level list where higher levels have fewer entries. The trade-off: comparison is O(log N) but the hash computation is O(N / level).

## Common Pitfalls

1. **Using a non-uniform hash for leaf ordering.** If keys are not evenly distributed across the hash space, the tree becomes unbalanced, with some leaves holding many more keys than others. This makes the sync protocol slower on the heavy ranges.

2. **Forgetting to update the tree on writes.** A tree that's stale (e.g., not updated after a write) gives false "in sync" results. Always update the tree in the same transaction as the data write, or use lazy reconstruction on repair.

3. **Assuming hashes are collision-free.** SHA-256 has 2^256 possible outputs; xxHash has 2^64. For 1 billion keys, the probability of a hash collision in xxHash is ~3 × 10^-11 — small but not zero. For collision-free sync, use SHA-256 or larger.

4. **Tree depth mismatches between replicas.** If A's tree has depth 20 (for ~1M keys) and B's has depth 21 (for ~2M keys), the sync protocol must handle different depths. Always include the depth in each node's serialized form.

5. **Sending the full tree on every sync.** A naive sync sends the whole tree; a good sync sends only the differing subtrees. The recursive descend protocol above handles this, but a careless implementation sends everything.

## References

- Ralph Merkle, "[A Certified Digital Signature](https://www.merkle.com/papers/Certified1979.pdf)" (CRYPTO 1979) — the original
- [Cassandra Merkle Tree source code](https://github.com/apache/cassandra/blob/trunk/src/java/org/apache/cassandra/utils/MerkleTree.java)
- [Git internals: tree objects and Merkle trees](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [Bitcoin SPV documentation](https://developer.bitcoin.org/devguide/operating_modes.html#simplified-payment-verification-spv)
- [IPFS Merkle DAG](https://docs.ipfs.tech/concepts/merkle-dag/)
- DeCandia et al., "[Dynamo](https://www.cs.ucsb.edu/~suri/psdir/SOSP07-Dynamo.pdf)" (SOSP 2007) — production Merkle tree sync
- [Merkle tree sync in Apache Cassandra (Cassandra Summit 2015)](https://www.youtube.com/watch?v=MerkleTreeSync)
