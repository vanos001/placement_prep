# IPFS and Filecoin

## Overview

HTTP addresses data by **location** — "get the file at `https://cdn.example.com/foo.png`". The URL changes if the file moves to another host, even if the content is unchanged. IPFS addresses data by **content** — "get the file whose SHA-256 hash is `bafy...`". The address is intrinsic to the bytes, so any peer holding a copy can serve it.

This shift — from location-addressing to content-addressing — has three structural consequences: deduplication becomes free (two copies of the same file produce the same CID), integrity becomes intrinsic (any mutation changes the CID), and the network can route requests without a directory service. IPFS provides the addressing and retrieval layer; Filecoin provides the persistence layer, paying storage providers to keep CIDs alive over time.

This page covers CIDs, the DAG-PB block format, the bitswap message protocol, the Kademlia DHT, Filecoin's proof-of-replication and proof-of-spacetime, the storage market, and a comparison with traditional S3/CDN.

## Content Identifiers (CIDs)

A CID is a self-describing handle. It is composed of three parts:

```
CIDv1 = multibase_prefix + multicodec + multihash

  multibase_prefix: 1 byte  (e.g., 0x12 = base32 with no padding, 'b' ASCII)
  multicodec:       varint  (e.g., 0x70 = dag-pb; 0x55 = raw)
  multihash:        varint + varint + bytes
                    (hash_code, length, digest)
```

A CIDv0 is base58-encoded, starts with `Qm`, and is always SHA-256 over a DAG-PB node (a legacy format from early IPFS). CIDv1 is the modern form: `bafy...` for dag-pb with SHA-256, `bafk...` for raw with SHA-256, `bafyb...` with a multihash listing multiple hash functions for migration.

Example decoding:

```
CIDv1:  bafybeig6gk7bpa2bxgin23shab3a4gca4nqfqphsn5kj5ej5t2fevdpome

base32 decode  -> 0120 + (32 bytes of SHA-256 digest)
                   ^^  ^^^
                   |   multihash body (digest)
                   |
                   multihash tag 0x12 = SHA-256, length 0x20 = 32 bytes

preceded by multicodec 0x70 (dag-pb) and multibase prefix 0x62 ('b')
```

A multihash lets you migrate hash functions without breaking CIDs: a future IPFS node can support both SHA-256 and BLAKE3, and clients reading a CID can identify which to use. This is why CIDs survive cryptographic-deprecation events — they self-describe.

## DAG-PB: The Block Format

IPFS stores data as a Merkle DAG (Directed Acyclic Graph where each node can have multiple parents). The serialization format for nodes is **DAG-PB** (formerly "unixfs-encoded dag-pb"). DAG-PB is a Protocol Buffers-encoded structure:

```protobuf
message PBNode {
    repeated PBLink Links = 1;   // references to child nodes by CID
    optional bytes Data = 2;     // the raw bytes (only if leaf, no Links)
}

message PBLink {
    optional bytes Hash = 1;     // child CID (raw bytes of the multihash)
    optional string Name = 2;    // optional human-readable name
    optional uint64 Tsize = 3;   // total encoded size of the child subtree
}
```

A file larger than ~256 KB is chunked (default splitter: rabin fingerprinting for variable-size content-defined chunks, or fixed-size for predictable hashing). The leaf chunks are each wrapped as DAG-PB nodes (with `Data = chunk_bytes, Links = []`). A "linker" process assembles an intermediate parent node that lists all leaves as `Links`; if there are more leaves than fit in a single node (~174 links at 256 KB chunks ≈ 44 MB), the linker builds a tree.

```
                root node (CID: bafy...root)
              /       |         \
         leaf 0    leaf 1     leaf 2
        (256 KB)  (256 KB)   (256 KB)
```

The root CID uniquely addresses the entire file: any modification to any chunk changes its CID, which changes every parent node's `Links` hash, which changes the root. The same file on any machine produces the same root CID — enabling cross-peer deduplication.

UnixFS is a thin layer on top of DAG-PB that adds metadata (file mode, mtime, size, type). A directory is just a DAG-PB node whose `Data` is empty and whose `Links` are `(name -> child CID)` pairs. This is essentially Git's tree-blob model with multi-parent links (deduplication across directories).

## Bitswap: The Block Exchange Protocol

Bitswap is the data-exchange protocol between two IPFS peers. Conceptually, each peer maintains a `wantlist` (CIDs it would like) and a `havelist` (CIDs it can serve). The protocol has gone through three revisions; the current (Bitswap 1.2.0+) uses **GraphSync** for large sub-DAG requests.

The message structure is:

```
Message {
  repeated Message_Wantlist wantlist = 1;
  repeated Block blocks = 3;
  repeated bytes pendingBytes = 4;
  repeated Cid blockPresence = 5;
}

Message_Wantlist {
  repeated Message_Wantlist_Entry entries = 1;
  optional bytes fullMessage = 2;  // sync only on a join (warm start)
}

Block {
  bytes prefix = 1;   // multicodec + multihash code + length
  bytes data  = 2;
}
```

A typical session:

```
1. Peer A opens Bitswap session with peer B (over libp2p stream).
2. A sends Wantlist: [bafy...foo, bafy...bar]
3. B responds with blockPresence: ["HAVE bafy...foo", "DONT_HAVE bafy...bar"]
4. A sends "block request" for bafy...foo.
5. B sends Block message with the bytes.
6. A verifies: multihash(bytes) == embedded hash in CID. Reject on mismatch.
```

The critical optimization is the **block-presence** gossip. Before sending a multi-MB block, peers exchange HAVE/DONT_HAVE. Bitswap also supports a "session" mode in which multiple peers collaborate: A may announce its wantlist to B, C, D; whoever has the block sends it; whoever doesn't tracks the want so they can later serve it. This minimizes redundant traffic.

The economics of bitswap is asymmetric altruism: peers are not directly paid. Without a budget, free-riders (leechers) can drain the network. The production implementation includes a **Bitswap credit system**: each peer tracks per-peer `debt_ratio = sent / (sent + received)`. If a remote peer's debt ratio exceeds a threshold (typically 5x), requests from it are throttled. This is the de facto tit-for-tat of IPFS, weaker than BitTorrent's tit-for-tat but simpler.

## Kademlia DHT

IPFS uses a Distributed Hash Table for content discovery: "which peer holds CID X?". The DHT is Kademlia, as implemented by libp2p's `KadDHT`. Each node has a 256-bit `NodeID` (the SHA-256 of its public key). Each key (a CID's multihash) is also a 256-bit value. Distance is XOR:

```
distance(a, b) = a XOR b
```

XOR has the metric properties (identity, symmetry, triangle inequality) — it induces a metric space on `2^256` keys. Each node maintains `256` "k-buckets": bucket `i` holds up to `k=20` peers whose XOR-distance falls in `[2^i, 2^(i+1))`.

```
       node ID        bucket index     distance range
 0xff00...00           0                [2^0, 2^1)       — nearest peers
 0x80000...            1                [2^1, 2^2)
 ...
 0x01000...            254              [2^254, 2^255)
 0x00000...            255              [2^255, 2^256)   — furthest peers
```

The lookup algorithm:

```
FIND_NODE(target):
  candidates = closest k peers from local routing table to target
  while improvement > threshold:
    query each candidate concurrently for peers closer to target
    add returned peers to candidate set
    keep only closest k candidates
  return candidates
```

Each query's complexity is `O(log n)` messages; with `alpha=3` parallel queries, the wall-clock lookup time is `O(log² n)` round-trips. For an IPFS network of ~30,000 public DHT nodes, that's ~15 hops per lookup in the worst case.

IPFS distinguishes two DHT modes:

- **Client mode**: peer maintains routing table but does not serve `PUT`/`GET` requests to others. Used for clients behind NAT or short-lived sessions.
- **Server mode**: peer is a full DHT member, responding to `FIND_NODE`, `PUT_PROVIDER`, and `GET_PROVIDER`. Requires port reachability (`AutoNAT` verifies this).

`PUT_PROVIDER(CID, peerID)` records "I hold CID X" in the K closest DHT nodes to `H(CID)`. `GET_PROVIDER(CID)` queries those K nodes for the list of providers. The result is a small set of candidate peers that the client then contacts via Bitswap.

## Filecoin: Persistence Layer

IPFS's problem: a CID is only retrievable while at least one peer is actively pinning it. If everyone who has a copy goes offline, the CID is gone. Filecoin adds a market where clients pay storage providers (SPs) to hold their CIDs for a contracted duration.

### Proof of Replication (PoRep)

The naive "I'm storing the data" claim is trivially forgeable: an SP can keep a single copy of the data and claim to have N copies. PoRep's job is to prove the SP has performed a unique encoding step — a **slow, sequential seal** — that produces a *physically distinct* copy from any other encoding.

The seal:

```
seal(sector_id, data):
  replica = data
  for layers in 1..N:  // typically 11 layers
    replica = layer_hash(layer_id, sector_id, replica, ...)
  // The result: a unique 32 GiB sector encoded specifically for this
  // (miner_id, sector_id). Any tampering changes the final hash.
  return hash(replica)
```

The key trick is that seal is **sequentially bound**: each layer depends on the previous one, so it cannot be parallelized below a wall-clock minimum. This forces the SP to spend real time producing the replica; "decoding-on-demand" attacks (storing only the original and re-sealing when challenged) would not complete within the proving window.

A PoRep proof is a SNARK proving that the SP knows a `replica` whose hash matches the registered commitment and which was produced by applying the seal function to a publicly announced `data_commitment`. SNARK size: ~192 bytes; verification: ~100 ms.

### Proof of Spacetime (PoSt)

PoRep proves the SP sealed the data *once*. The protocol still needs a continuous proof that the data is *still* stored at every challenge. PoSt is the proof of ongoing storage.

Window PoSt runs on a daily cadence. Each sector is challenged at a random time within its assigned window (the sector space is partitioned into 30-min windows of the day). At challenge, the SP must:

```
1. Receive a random challenge seed (from the Filecoin chain).
2. For each challenged sector, derive a random leaf.
3. Open that leaf in the sealed replica (decode-on-demand not possible in 30 min).
4. Submit a SNARK proving: "I know a leaf at position X in sealed sector S
   whose hash matches the publicly committed root."
```

If the SP fails to produce a PoSt in the window, the network slashes the sector's collateral. Missing ~4 hours of PoSts consecutively terminates the sector. Winning PoSt is a parallel function used during block production — the block producer proves it still holds the sectors it has won the right to seal.

### Storage Market and Deal Pipeline

A client/SP deal is negotiated off-chain via the **Storage Market**: client posts a `ClientDealProposal` (CID, duration, price, SP address). The SP accepts by countersigning. The deal then runs through a multi-step on-chain pipeline:

```
1. ClientTransfer (off-chain):  client sends bytes to SP via GraphSync.
2. DealPublished:  deal published on-chain; client funds locked.
3. SectorSealing:  SP adds the deal to a new sector and PoReps it.
4. DealActive:  deal considered proven; SP starts earning per-epoch FIL.
5. DealSlashing:  if a PoSt fails during the deal window, the SP is slashed.
6. DealCompletion:  client can request early termination; SP pays a penalty.
```

The collateral model: SPs must put up `precommit_collateral` (per-sector) before sealing, plus `deal_collateral` per accepted deal, plus `initial_pledge` per sector proven active. Total pledged collateral for a 32 GiB sector on mainnet is on the order of `0.2 FIL` (varies with network power and circulating supply). These collaterals are slashed on PoSt failure, providing economic teeth to the "I'm storing your data" promise.

### Retrieval Market

Retrieval is *not* covered by on-chain PoSts — it's a separate, payment-channel-based market. Clients open a payment channel with an SP, fund it, then pay per byte received. The SP sends bytes via GraphSync, with each chunk paid via incremental micropayments on the channel. The retrieval market is the harder problem because the latency budget is small (seconds) and most state is off-chain.

## Comparison to Traditional CDN/S3

| Dimension | AWS S3 / CloudFront | IPFS pinning | Filecoin |
|-----------|--------------------|--------------|----------|
| **Addressing** | URL by location (bucket + key) | CID by content hash | CID by content hash |
| **Persistence SLA** | AWS contract; 99.999999999% durability | No SLA — depends on pinning peer | On-chain proof with collateral |
| **Retrieval latency** | ~30 ms (edge), ~100 ms (origin) | Variable, often seconds for cold CIDs | Seconds-minutes (retrieval market) |
| **Throughput** | Provisioned, multi-Tbps edge | Depends on peer bandwidth | Aggregated across SPs |
| **Pricing** | $0.023/GB-month storage; $0.085/GB egress | Variable (Pinata, Infura plans) | Auction-priced per deal, ~$0.0001/GB-month |
| **Immutability** | Versioning + object-lock (opt-in) | Intrinsic (CID changes on mutation) | Intrinsic (sealed replica) |
| **Verification** | Trust AWS | Trust the pinning service | Verify PoSt proofs on-chain |
| **Censorship resistance** | AWS can deplatform | Multiple pinners raise the cost | Distributed SPs; collusion-resistance |
| **Failure mode** | Single-region outage (e.g., us-east-1 2017) | Peer churn (single pinner disappears) | SP PoSt failure → slash + sector termination |
| **Cold storage** | S3 Glacier, hours to retrieve | Same as hot (same CID) | Same CID; retrieval market adds latency |

The structural difference: S3 durability is guaranteed by *contractual replication inside AWS's infrastructure*, opaque to the user. Filecoin durability is guaranteed by *public, verifiable proofs of storage on a decentralized set of SPs*, each economically staked. S3 egress pricing makes large-scale reads expensive ($90/TB egress); Filecoin retrieval is auction-priced and often orders of magnitude cheaper, but the latency and reliability floor is much higher.

The typical real-world hybrid: enterprise workloads use S3 for hot data, IPFS + pinning service for content-addressable sharing (NFT metadata, dApp frontends), and Filecoin for cheap cold backup of large datasets (genomics, video archives, model checkpoints) where retrieval latency is acceptable.

## References

- IPFS documentation — https://docs.ipfs.tech/
- CID specification (multiformats) — https://github.com/multiformats/cid
- DAG-PB specification — https://github.com/ipld/specs/blob/master/block-layer/codecs/dag-pb.md
- Bitswap specification — https://github.com/ipfs/specs/blob/main/BITSWAP.md
- Kademlia DHT in libp2p — https://github.com/libp2p/specs/blob/master/kad-dht/README.md
- Filecoin documentation — https://docs.filecoin.io/
- Filecoin Proof-of-Replication paper — https://filecoin.io/papers/storage-f2/
- Filecoin Proof of Spacetime (Window PoSt) — https://spec.filecoin.io/algorithms/pos/post/
- Storage Market actor specification — https://spec.filecoin.io/systems/filecoin_markets/storage_market/
- GraphSync protocol spec — https://github.com/ipld/specs/blob/master/graph-sync/graph-sync.md
