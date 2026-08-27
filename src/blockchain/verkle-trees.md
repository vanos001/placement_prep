# Verkle Trees: Killing the Witness-Size Tax

Every Ethereum block header commits to the entire world state through one 32-byte root. Full nodes verify that root because they store the whole trie; everyone else must take it on faith. The stateless-client vision inverts this: the block itself carries a **witness** — the proof material needed to check every state item the block touches — so a validator needs zero stored state and a phone-class device can verify the chain. Witnesses only work if they are small. In Ethereum's current Merkle Patricia trie they are not, and the replacement designed to fix them is the **verkle tree** (a Merkle tree whose links are *vector commitments* instead of hashes), specified in [EIP-6800](https://eips.ethereum.org/EIPS/eip-6800). This page expands the summary treatment in [Ethereum Internals](./ethereum-internals.md); the hash-tree mechanics it builds on are covered separately in [Merkle Tree Synchronization](../distributed/advanced/merkle-sync.md).

## Why Merkle Witnesses Blow Up

A Merkle proof answers "what is the value under key k, and is it committed by the root?" by walking from the leaf to the root and publishing, at each level, **every sibling hash needed to recompute the parent**. In a binary tree that is one 32-byte hash per level, so a proof costs `32 x log2(n)` bytes — tolerable. Ethereum's trie is 16-ary (one tree level per key *nibble*, 4 bits), and the cost model is much worse:

- A branch node carries up to 16 child hashes. The parent hash covers *all* of them, so a proof must transmit the entire branch node at every level — roughly `16 x 32 = 512` bytes per level, not 32.
- Keys are 32-byte hashes, so the nominal path is up to 64 nibble levels deep. Path compression shortens this for dense subtrees, but with ~10^8 accounts the average proof still walks a handful of branch nodes *per access*, each several hundred bytes after RLP encoding.
- A block touches thousands of keys. Summing independent per-key paths gives megabytes of witness per block; even after deduplicating shared internal nodes (a multiproof), the per-access cost stays proportional to trie depth.

The disease is structural: **hash links force you to publish the whole node** to prove membership, and node size scales with fanout. A wider tree (fewer levels) makes each level bigger — the product stays large. Escaping the trade-off requires a link primitive that can prove "child i of this node is C" *without* showing the other children. That primitive is a vector commitment.

```text
Proving one key, 16-ary Merkle Patricia trie (d = depth in branch levels):

  root [branch: h0 h1 ... h15]   <- transmit ALL 16 child hashes (~512 B)
        |
     [branch: h0 h1 ... h15]     <- another ~512 B
        |                         (repeat for every level)
      leaf value (32 B)

  witness(k keys)  ~  k x (512 B x d)      cost scales with depth AND fanout

Same key in a verkle trie (256-way, KZG commitments):

  root  C0 = commit([C1_0 .. C1_255])
        |   one opening: "child #i of C0 is C1"   (single group element)
     stem node  C1 = commit([v0 .. v255])
        |   one opening: "value at suffix #s is v"
     value v

  witness(k keys)  ~  k x (opening) + (unique stems) x (small constant)
```

## Vector Commitments: Open One Element, Pay a Constant

A **vector commitment** lets a committer publish a short value `C` for a vector `v` and later prove, for any index `i`, that `v[i] = x` with a proof whose size is (ideally) independent of the vector length. Merkle trees are the transparent vector commitment — but with logarithmic, fanout-amplified openings. The scheme Ethereum adopted is **KZG** (Kate–Zaverucha–Goldberg, ASIACRYPT 2010):

- Encode the vector as the evaluations of a polynomial `f` (element `i` is `f(i)`). Commit by publishing `C = [f(tau)]_1` — the polynomial evaluated at a secret point `tau`, hidden inside an elliptic-curve group element (48 bytes compressed on BLS12-381). Nobody knows `tau`; it exists only as powers-of-tau group elements produced by a **trusted setup ceremony**.
- To open at point `z`, the prover divides: `q(X) = (f(X) - f(z)) / (X - z)` and publishes the proof `W = [q(tau)]_1` plus the claimed value `f(z)`.
- The verifier checks one **pairing equation**: `e(C - f(z)*G1, G2_gen) = e(W, [tau]_2 - z*G2)`. Pairings are bilinear maps `G1 x G2 -> GT`, which effectively lets the verifier "multiply through" the hidden `tau` and confirm both sides encode the same polynomial identity — without ever learning `tau` or any other value of `f`. Verification is a constant number of pairing checks regardless of degree.

The trusted setup is the tax for this magic. The secret `tau` (the "toxic waste") must be destroyed; anyone holding it can forge any opening. The [Powers of Tau](https://dankradfeist.de/ethereum/2020/06/16/kate-polynomial-commitments.html) ceremony mitigates this with a multi-party computation: participants take turns adding randomness, and as long as *one* contributor deleted their share, the joint secret is unrecoverable. Ethereum's EIP-4844 ceremony collected contributions from over 140,000 participants. The same KZG machinery powers SNARK provers — see [ZK Proofs](../cryptography/zk-proofs.md) for that side of the family.

## The Verkle Trie Layout (EIP-6800)

The draft Ethereum design ([EIP-6800](https://eips.ethereum.org/EIPS/eip-6800), "Ethereum state using a unified verkle tree") reshapes the state around stems:

- A key is split into a **31-byte stem** and a **1-byte suffix**. Internal nodes are 256-way; the path from the root is indexed by the *bytes* of the stem.
- A path terminates in a **stem node**: a single vector commitment holding 256 slots — all state cells (balance, nonce, code chunks, storage slots) of one account share the stem, and the suffix byte addresses the slot.
- The stem design descends from the 2021 "extension and suffix tree" proposal: it exists so that *all* accesses to one account amortize a single stem proof. A block touching 1,000 storage slots of one contract pays the stem constant once, plus one small opening per slot.
- A naive path proof needs one opening per tree level (~31 per stem). Production proof systems **aggregate**: multi-opening schemes batch every opening in a block into a compact transcript, so the operational model is a per-element opening plus a per-stem constant rather than a per-level cost. (Group elements on BLS12-381 are 48 bytes compressed; papers often quote ~96–128 bytes per stem and ~32–48 bytes per opening after aggregation.)

| Property | Merkle Patricia Trie | Verkle Trie |
|----------|----------------------|-------------|
| Node fanout | 16 (nibble-indexed) | 256 (byte-indexed) |
| Link primitive | SHA-256 hash of child | KZG commitment to child vector |
| Proof per accessed element | whole branch node per level (~512 B x depth) | one aggregated opening (~32-48 B) |
| Witness scaling in state size n | O(fanout x log n) bytes | O(1) per element + O(1) per stem |
| Proof of non-inclusion | native (empty branch slot) | opening showing an empty slot |
| Trusted setup | none | required (Powers of Tau ceremony) |
| Post-quantum | yes (hash-based) | no (pairing-based) |
| Mainnet status (Aug 2026) | live | not activated (see below) |

## Measuring the Gap

The simulation below builds a 16-ary SHA-256 universe tree over 10,000 keys (the model: transmitting any branch node means transmitting all 16 child hashes) and compares naive per-access proofs, deduplicated multiproofs, and a verkle model of 32 bytes per element opening plus 96 bytes per unique stem:

```python
# Witness-size model: 16-ary SHA-256 Merkle tree vs verkle (vector-commitment) tree.
# Model (EIP-6800-style design):
#   Merkle: every branch node on a key's path must be transmitted in full
#           (parent hash covers all 16 children) -> 16 x 32 = 512 B per level;
#           leaf value = 32 B.
#   Verkle: per touched element one vector-commitment opening = 32 B;
#           per unique stem: 3 group elements (stem commitment + parent
#           commitment + proof) = 96 B.
import hashlib, math, random

H = 32
NODE = 16 * H          # bytes per 16-ary branch node
STEM_COST = 3 * H      # verkle material per unique stem
OPENING = H            # verkle opening per touched element

def universe_tree(n_keys):
    depth = max(1, math.ceil(math.log(n_keys, 16)))
    slots = 16 ** depth
    pos_by_key, keys = {}, []
    i = 0
    while len(keys) < n_keys:
        key = hashlib.sha256(b"key-%d" % i).digest()
        i += 1
        pos = int.from_bytes(key[:4], "big") % slots
        while pos in pos_by_key:            # collision -> linear probe
            pos = (pos + 1) % slots
        pos_by_key[len(keys)] = pos
        keys.append(key)
    return keys, pos_by_key, depth, slots

keys, pos_of, depth, slots = universe_tree(10_000)
rng = random.Random(7)

print(f"dataset: {len(keys):,} keys -> 16-ary depth {depth} ({slots:,} leaf slots)")
print(f"per-access naive: merkle {depth}x{NODE}+{H} = {depth*NODE+H} B"
      f" | verkle {STEM_COST}+{OPENING} = {STEM_COST+OPENING} B")
print()
print(f"{'batch':>7} | {'merkle naive':>12} {'verkle':>10} {'ratio':>7} |"
      f" {'merkle dedup':>12} {'verkle':>10} {'ratio':>7}")
print("-" * 82)
for T in (1, 10, 100, 1000, 10000):
    batch = rng.sample(range(len(keys)), T)
    naive_m = len(batch) * (depth * NODE + H)
    stems = {keys[k][:31] for k in batch}
    naive_v = len(batch) * OPENING + len(stems) * STEM_COST
    branches = set()
    for k in batch:
        p = pos_of[k]
        branches.update(p // 16 ** j for j in range(1, depth + 1))
    dedup_m = len(branches) * NODE + len(set(batch)) * H
    dedup_v = naive_v
    print(f"{T:>7} | {naive_m:>12,} {naive_v:>10,} {naive_m/naive_v:>6.1f}x |"
          f" {dedup_m:>12,} {dedup_v:>10,} {dedup_m/dedup_v:>6.1f}x")
print()
print("depth sweep (100 random reads):")
print(f"{'keys':>9} | {'depth':>5} | {'merkle/access':>13} | {'verkle/access':>13} | {'ratio':>6}")
for n in (1_000, 10_000, 100_000, 1_000_000):
    d = max(1, math.ceil(math.log(n, 16)))
    m = d * NODE + H
    v = STEM_COST + OPENING
    print(f"{n:>9,} | {d:>5} | {m:>13,} | {v:>13,} | {m/v:>5.1f}x")
print()
d = max(1, math.ceil(math.log(180_000_000, 16)))
print(f"mainnet-scale extrapolation: ~180M accounts -> depth ~{d} levels ->"
      f" merkle ~{d*NODE/1024:.1f} KiB/access vs verkle {STEM_COST+OPENING} B"
      f" (~{(d*NODE+H)/(STEM_COST+OPENING):.0f}x)")
```

Real output:

```text
dataset: 10,000 keys -> 16-ary depth 4 (65,536 leaf slots)
per-access naive: merkle 4x512+32 = 2080 B | verkle 96+32 = 128 B

  batch | merkle naive     verkle   ratio | merkle dedup     verkle   ratio
----------------------------------------------------------------------------------
      1 |        2,080        128   16.2x |        2,080        128   16.2x
     10 |       20,800      1,280   16.2x |       14,656      1,280   11.4x
    100 |      208,000     12,800   16.2x |      104,576     12,800    8.2x
   1000 |    2,080,000    128,000   16.2x |      601,856    128,000    4.7x
  10000 |   20,800,000  1,280,000   16.2x |    2,265,088  1,280,000    1.8x

depth sweep (100 random reads):
     keys | depth | merkle/access | verkle/access |  ratio
    1,000 |     3 |         1,568 |           128 |  12.2x
   10,000 |     4 |         2,080 |           128 |  16.2x
  100,000 |     5 |         2,592 |           128 |  20.2x
1,000,000 |     5 |         2,592 |           128 |  20.2x

mainnet-scale extrapolation: ~180M accounts -> depth ~7 levels -> merkle ~3.5 KiB/access vs verkle 128 B (~28x)
```

Three readings worth taking away. First, the naive-vs-verkle ratio is flat in batch size (16.2x) because both scale linearly in accesses — the win is the *constant*, not asymptotics. Second, deduplication (multiproofs) helps Merkle substantially on batches that share trie prefixes, but never below the per-node constant; at mainnet scale the extrapolated ~3.5 KiB per access matches the "kilobytes per account" figures quoted for real MPT witnesses, while the verkle model stays at 128 bytes. Third, the simulation is a *floor* for Merkle costs: real tries hash full 32-byte keys (deeper effective paths) and carry RLP overhead, while real verkle openings are 48-byte BLS12-381 points — so both sides of the model shift, which is why the design target is phrased as an order-of-magnitude witness reduction rather than the naive 30x+.

## Stateless Clients and State Expiry

Witnesses are the enabling primitive for two roadmap items beyond lightweight validation:

- **Stateless validators**: consensus participants verify blocks from witnesses alone, decoupling validation cost from state size. The gas model must change accordingly — [EIP-4762](https://eips.ethereum.org/EIPS/eip-4762) ("statelessness gas cost changes") re-prices operations by *witness chunks accessed* instead of storage-touched, charging for proof material the block must now carry.
- **State expiry**: if every access carries its proof, the network no longer needs every node to hold dormant accounts. Lease-based proposals periodically expire untouched state (recoverable by re-inserting a witness), capping state growth. Related housekeeping already landed separately: [EIP-4444](https://eips.ethereum.org/EIPS/eip-4444) bounds *history* (old blocks/receipts), which is distinct from *state* expiry.
- Transition care: semantics that relied on trie deletion had to change before witnesses could assume tree invariants. The Cancun-era restriction of `SELFDESTRUCT` (EIP-6780: self-destruct only takes effect in the same transaction that created the contract) is exactly this kind of pre-implementation cleanup; see [EVM Internals](./evm-internals.md).

## Implementation Status (August 2026)

Be precise in interviews: **verkle trees are not live on mainnet**. In the official EIP repository, EIP-6800 sits in *Stagnant* status and EIP-4762 remains *Draft*; no hard fork has activated verkle state. The research conversation has also moved: proposals for IPA (inner-product-argument)-based commitments over interleaved codes, and post-quantum hash-based state designs, are actively debated on ethresear.ch — the KZG-based stem design is the *drafted* baseline, not a fixed endpoint. What *is* production-tested from the same toolbox: KZG commitments have been live on mainnet since EIP-4844 (Dencun, March 2024) for blob data availability — see [Data Availability](./data-availability.md). The pairing machinery works; the state migration (migrating ~10^8 accounts into a new tree, re-pricing gas, coordinating every client) is the part still pending.

## Gotchas

- **"Why not just widen the Merkle tree to 256-ary?"** Fanout growth makes each level *bigger* (255 sibling hashes instead of 15); with hash links the total witness gets worse, not better. Only a vector commitment makes wide fanouts cheap.
- **"KZG openings are constant-size — is verification constant too?"** Yes: one pairing check per opening (or a small batched check). This is why KZG, not IPA/FRI, was drafted for state — on-chain and in-client verification budgets are tight.
- **"What does the trusted setup actually risk?"** If the ceremony's toxic waste were reconstructed, an attacker could forge witness proofs — inventing balances. The 1-of-N honesty assumption over 140k+ contributors is the mitigation; post-quantum hash-based designs would remove the assumption entirely.
- **"Do verkle trees shrink the state?"** No. They shrink *proofs*. State expiry shrinks the stored state; witnesses are what make expiry survivable for old accounts.

## Cross-References

- [Ethereum Internals](./ethereum-internals.md) — where verkle trees sit in the roadmap; stateless clients summary
- [Merkle Tree Synchronization](../distributed/advanced/merkle-sync.md) — hash-tree proof mechanics without vector commitments
- [ZK Proofs](../cryptography/zk-proofs.md) — KZG inside SNARKs; trusted setup taxonomy
- [Data Availability](./data-availability.md) — the other KZG consumer: blob sampling
- [EVM Internals](./evm-internals.md) — opcode/precompile surface, SELFDESTRUCT transition rules

## References

- [EIP-6800: Ethereum state using a unified verkle tree](https://eips.ethereum.org/EIPS/eip-6800) — the drafted stem/suffix layout and proof model
- [EIP-4762: Statelessness gas cost changes](https://eips.ethereum.org/EIPS/eip-4762) — witness-chunk gas accounting draft
- [Kate, Zaverucha, Goldberg — Constant-Size Commitments to Polynomials and Their Applications (ASIACRYPT 2010)](https://iacr.org/archive/asiacrypt2010/6477178/6477178.pdf) — the KZG paper (DOI: [10.1007/978-3-642-17373-8_11](https://doi.org/10.1007/978-3-642-17373-8_11))
- [Dankrad Feist — KZG polynomial commitments](https://dankradfeist.de/ethereum/2020/06/16/kate-polynomial-commitments.html) — the standard intuition-first explainer, including Powers of Tau
- [EIP-4444: Bound Historical Data in Execution Clients](https://eips.ethereum.org/EIPS/eip-4444) — history pruning, the state-expiry sibling
