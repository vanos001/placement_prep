# Data Availability: Can Light Clients Trust What They Cannot Store?

A light client downloads block headers, checks signatures and state roots, and accepts the chain — without ever seeing the bodies of most blocks. This works only under a hidden assumption: that the data described by the header was actually *published to the network*. Nothing in header validation checks that. The **data availability (DA) problem** asks: *how can a light client, with bounded resources, verify that the data behind a header exists and was broadcast — not merely that the header itself looks well-formed?* Get the answer wrong and the failure is silent: fraud proofs have nothing to check, exits have nothing to exit with, and the light client's "trustless" security quietly degrades to trusting whoever produced the header.

## Availability Is Not Validity

Blockchains need two independent guarantees, and conflating them is the classic interview trap:

| Guarantee | Question answered | Enforced by |
|-----------|-------------------|-------------|
| Data validity | "Was this state transition computed correctly?" | re-execution, fraud proofs, validity proofs |
| Data availability | "Were the inputs of that transition published at all?" | erasure coding + sampling (this page) |

The dependency runs one way: **validity checks need data**. An optimistic rollup's fraud proof (see [Optimistic Rollups](./optimistic-rollups.md)) is a re-execution diff — a challenger can only build it if the sequencer's transaction data is retrievable. If a block producer posts a header committing to an invalid transition and withholds the data, no challenger can construct the proof, and after the challenge window the fraud *silently stands*. Availability is therefore the precondition for fraud-proof security; a validity-proof system shrinks the problem (the proof itself attests correctness) but still needs data availability for users to reconstruct state and withdraw — liveness, not just safety.

The attack to defend against is subtle: a producer can publish *most* of the data and withhold a sliver. Full nodes notice something is wrong (they cannot sync), but a light client downloading only the header sees nothing. Brute force — "download everything" — eliminates light clients by definition. The fix is to make withholding *detectable from a few random probes*, which requires changing how data is stored in the first place.

## Erasure Coding: Any Half Is Everything

Reed–Solomon codes (mechanics in [Erasure Coding](../storage/erasure-coding.md)) expand `k` chunks into `n` chunks such that *any* `k` of the `n` recover all. The DA twist is strategic: encode so that **any 50% of the expanded data reconstructs the original**. Then the statements "someone published half the extended data" and "the full data is recoverable" coincide, and detection becomes cheap — a light client never needs to find the *withheld* chunks, only to confirm that *enough* chunks were published.

The original construction ([Al-Bassam, Sonnino, Buterin — "Fraud and Data Availability Proofs"](https://arxiv.org/abs/1809.09044)) uses a **2D matrix**, because a 1D code has a hole: a producer could publish enough chunks to pass sampling yet encode *incorrectly*, making reconstruction impossible. In 2D, rows and columns are each extended and cross-committed, so any invalid extension is itself detectable and provable via a small **fraud proof of wrong encoding**:

```text
k x k data matrix (k = 4 shown), extended to 2k x 2k with Reed-Solomon:

            +----+----+----+----+----+----+----+----+
    row 0   | D  | D  | D  | D  | P  | P  | P  | P | <- each row RS-extended
    row 1   | D  | D  | D  | D  | P  | P  | P  | P |
    row 2   | D  | D  | D  | D  | P  | P  | P  | P |
    row 3   | D  | D  | D  | D  | P  | P  | P  | P |
            +----+----+----+----+----+----+----+----+
    row 4   | P  | P  | P  | P  | P  | P  | P  | P | <- each column RS-extended
      :     | P  | P  | P  | P  | P  | P  | P  | P |    (rows 4..7 are column
    row 7   | P  | P  | P  | P  | P  | P  | P  | P |     parity over columns)
            +----+----+----+----+----+----+----+----+

    light client picks random cells:   . . X . . . X .
    each cell verifies against its row AND column commitment
    if < 1/2 of the matrix was published, any single cell has
    p >= 1/2 of landing in withheld territory
```

Every row and column carries a short commitment (a Merkle root, or a KZG commitment in Ethereum's design). A sampled cell arrives with proofs against *both* its row and its column, so a lying chunk is caught immediately, and a consistent half-matrix mathematically determines the whole.

## The Sampling Math

Model: the adversary published a fraction `1 - u` of the `2k x 2k` extended matrix (withheld fraction `u`). A light client draws `k` cell positions independently at random and requests each. Each sample lands in withheld territory with probability `u`, so:

```text
P(light client fooled: all k samples hit published data) = (1 - u)^k
```

The security claim in the DA-proofs paper is about the 50% threshold: **if fewer than half the chunks are available, then each independent sample fails with probability > 1/2**, hence `P(fooled) < (1/2)^k`. This is the *doubling argument* — every additional sample halves the probability of silent failure, so confidence grows exponentially in a *linear* number of downloads:

- If all `k` samples succeed, then with probability at least `1 - (1/2)^k` at least half the extended data is available — and by Reed–Solomon, that means *all* of it is reconstructible.
- `k = 30` samples give `2^-30 ≈ 9.3 x 10^-10`: roughly a one-in-a-billion chance of accepting unavailable data.
- Symmetric view: the expected number of samples until the *first* withheld cell is `1/u` — just 2 samples on average when half is missing.

Two honest caveats. Sampling *without* replacement is strictly stronger: `P(fooled) = C(published, k)/C(total, k) <= (1-u)^k`, so the with-replacement formula is a conservative bound. And sampling says nothing about validity — it certifies that data *exists*, never that it was correct; the two guarantees from the table above compose.

## Running the Numbers

```python
# Data-availability sampling: probability a light client is fooled when an
# adversary withholds a fraction u of the erasure-coded data. Each of k samples
# is an independent random read: accept prob = (1-u)^k.
# Guarantee: if ALL k samples succeed, then with prob >= 1 - (1/2)^k at least
# half of the extended matrix is retrievable (Reed-Solomon recovers the rest).
# Every extra sample halves the silent-failure odds -> "doubling argument".
import math, random

K_SAMPLES = [5, 10, 15, 20, 30, 40, 60, 80]
FRACTIONS = [0.50, 0.30, 0.10, 0.01]

hdr = " k |" + "|".join(f"  u={u:.2f}  " for u in FRACTIONS)
print("P(light client fooled) = (1-u)^k")
print(hdr)
print("-" * len(hdr))
for k in K_SAMPLES:
    row = f"{k:>2} |"
    for u in FRACTIONS:
        row += f" {(1-u)**k:.2e}"
    print(row)

print()
k_star = math.ceil(math.log(1e-9) / math.log(0.5))
print(f"samples for silent-failure odds <= 1e-9 under the 50% rule: k = {k_star}"
      f"  (2^-30 = {0.5**30:.2e})")
print(f"expected samples until first withheld chunk at u=0.50: {1/0.50:.0f}")

print()
# Monte Carlo check of the 50% rule: 4096-cell extended matrix, half withheld,
# k=10 samples drawn with replacement.
rng = random.Random(42)
TOTAL, WITHHELD, K, TRIALS = 4096, 2048, 10, 1_000_000
accepted = 0
for _ in range(TRIALS):
    ok = True
    for _ in range(K):
        if rng.randrange(TOTAL) < WITHHELD:
            ok = False
            break
    accepted += ok
mc = accepted / TRIALS
print(f"monte carlo: {TRIALS:,} trials, 50% withheld, k={K} (with replacement)")
print(f"  measured accept rate {mc:.3e}   theory 2^-{K} = {0.5**K:.3e}")
```

Real output:

```text
P(light client fooled) = (1-u)^k
 k |  u=0.50  |  u=0.30  |  u=0.10  |  u=0.01  
-----------------------------------------------
 5 | 3.12e-02 1.68e-01 5.90e-01 9.51e-01
10 | 9.77e-04 2.82e-02 3.49e-01 9.04e-01
15 | 3.05e-05 4.75e-03 2.06e-01 8.60e-01
20 | 9.54e-07 7.98e-04 1.22e-01 8.18e-01
30 | 9.31e-10 2.25e-05 4.24e-02 7.40e-01
40 | 9.09e-13 6.37e-07 1.48e-02 6.69e-01
60 | 8.67e-19 5.08e-10 1.80e-03 5.47e-01
80 | 8.27e-25 4.05e-13 2.18e-04 4.48e-01

samples for silent-failure odds <= 1e-9 under the 50% rule: k = 30  (2^-30 = 9.31e-10)
expected samples until first withheld chunk at u=0.50: 2

monte carlo: 1,000,000 trials, 50% withheld, k=10 (with replacement)
  measured accept rate 9.680e-04   theory 2^-10 = 9.766e-04
```

Read the columns, not just the rows: sampling gives ironclad protection only against *gross* withholding. At `u = 0.50` (the regime the 50% rule covers), 30 samples are overkill and 10 nearly suffice. But if the adversary published 90% of the data (`u = 0.10`), even 80 samples accept 22% of the time. That residual risk is real yet survivable: with 90% published, the data *is* reconstructible in the RS sense, so "fooling" the sampler there is not an attack — the column-to-zero slope at the right is why the guarantee is phrased around the 50% threshold rather than absolute certainty.

## Celestia: Data Availability as a Minimal Layer

[Celestia](https://docs.celestia.org/) productizes the paper: a minimal blockchain whose only jobs are ordering transactions and guaranteeing their data is available — execution lives entirely in rollups above it. The pipeline follows the 2D design: transactions are erasure-coded into the row/column matrix, rows and columns are committed with **Namespaced Merkle Trees** (so a rollup can efficiently query the shares belonging to its own namespace), and light clients continuously sample random shares, sounding the alarm via wrong-encoding fraud proofs if anything fails verification. Because sampling demand *is* the security budget, the architecture makes light-client participation a consensus resource rather than a convenience — the "modular" thesis in one sentence: separate consensus-and-DA from execution, and scale each independently.

## Ethereum's Path: 4844, PeerDAS, Danksharding

Ethereum adopted the same primitives incrementally, reusing KZG commitments at every step:

- **EIP-4844 "proto-danksharding"** shipped with the Dencun hard fork (March 13, 2024): a new blob-carrying transaction type. Each blob carries 4096 field elements of 32 bytes (131,072 bytes, ~128 KiB) and is committed in the header by a single 48-byte KZG commitment; blobs live in their own fee market (separate base fee, minimum 1 wei) and are pruned after ~18 days. Initial throughput was a target of 3 blobs (max 6) per block — deliberately conservative.
- **EIP-7691** (activated with Pectra, May 2025) doubled throughput to a target of 6 blobs (max 9), with further raises designed to come from *blob-parameter-only* (BPO) forks that adjust the two numbers without a full hard fork. At 4844 scale each validator already downloads full blobs; sampling is not yet needed.
- **PeerDAS ([EIP-7594](https://eips.ethereum.org/EIPS/eip-7594), Final status)** is the first true deployment of sampling: each blob's extended data is split into columns and each validator stores and samples only a subset, with the gossip network aggregating coverage so the block as a whole is verified by the collective. It is the headline protocol change of the Fusaka upgrade — check the [Ethereum roadmap](https://ethereum.org/en/roadmap/danksharding/) for its activation status as you read this.
- **Full danksharding** (target ~16-32 MB blobs) generalizes sampling to *all* light clients over the 2D matrix, with KZG multiproofs letting any sampled cell be verified against the header commitments. The same point-evaluation precompile introduced with 4844 (address `0x0a`) is what lets L2s prove "this blob commitment opens to this chunk" on-chain — see [EVM Internals](./evm-internals.md) and the KZG section of [Ethereum Internals](./ethereum-internals.md).

The structural point for interviews: danksharding does not shard *execution* (the abandoned 64-shard plan); it shards *data custody*. Execution scaling is delegated to rollups, which is why the DA layer, not the EVM, is Ethereum's scaling bottleneck post-4844.

## Off-Chain DA: Plasma, Validium, and the Exit Game

Not every system wants to pay L1 for data. The alternatives move custody off-chain and inherit a different failure mode:

| Design | Where data lives | Retrieval guarantee | Failure mode |
|--------|------------------|---------------------|--------------|
| Rollup (on-chain DA) | calldata / blobs on L1 | L1 consensus | none beyond L1 failure |
| Validium | off-chain + DA committee signatures | committee honesty | committee withholds -> funds frozen |
| Plasma | operator-only, fraud proofs + exits | exit game | operator withholds -> mass exit to L1 |
| External DA (Celestia-style) | dedicated DA chain | its own sampler fleet | DA chain's security assumptions |

Validiums and Plasma get validity-or-fraud guarantees for *cheap*, but the fine print is availability: when the operator or committee withholds data, users cannot prove their balances anywhere — the exit game only functions if exit *proofs* are constructible, which again needs published data. This is the DA/validity separation from the top of the page, resurfacing as a business trade-off; see [ZK Rollups](./zk-rollups.md) for where validity proofs soften but do not remove it.

## Gotchas

- **"Light clients verify headers, so they're safe, right?"** Header verification checks commitments, not presence. Without DA sampling, a light client accepts headers whose data was never broadcast.
- **"Why 2D erasure coding instead of one long codeword?"** 1D sampling can be satisfied by a producer who encodes invalidly — enough correct chunks pass sampling but reconstruction still fails. Row/column cross-commitments make wrong encodings themselves provable.
- **"Does sampling prove the block is valid?"** No — only that data was published. Validity needs re-execution, fraud proofs, or validity proofs. The guarantees compose; neither substitutes for the other.
- **"Why prune blobs after 18 days without losing security?"** Because availability is needed for the challenge/reconstruction window, not forever: state commitments and validity proofs persist in headers, and archival DA can live with third parties. History (EIP-4444) and state commitments are separable concerns.
- **"What does the KZG trusted setup buy attackers here?"** A broken ceremony would allow *forged commitments* (fake data verification), not just forged witnesses — which is why the 4844 ceremony's 1-of-N honesty guarantee matters as much on this page as on the verkle one.

## Cross-References

- [Ethereum Internals](./ethereum-internals.md) — sharding roadmap table, KZG commitments summary
- [Verkle Trees](./verkle-trees.md) — the same KZG primitive applied to state witnesses
- [Optimistic Rollups](./optimistic-rollups.md) — the fraud-proof systems that depend on DA
- [ZK Rollups](./zk-rollups.md) — validity proofs vs fraud proofs; validium trade-offs
- [Erasure Coding](../storage/erasure-coding.md) — Reed–Solomon mechanics in storage systems

## References

- [Al-Bassam, Sonnino, Buterin — Fraud and Data Availability Proofs (arXiv:1809.09044)](https://arxiv.org/abs/1809.09044) — the 2D Reed–Solomon + sampling construction
- [EIP-4844: Shard Blob Transactions](https://eips.ethereum.org/EIPS/eip-4844) — proto-danksharding spec (live since Dencun, March 2024)
- [EIP-7594: PeerDAS — Peer Data Availability Sampling](https://eips.ethereum.org/EIPS/eip-7594) — validator-subset sampling for Fusaka
- [Celestia Documentation](https://docs.celestia.org/) — modular DA layer: namespaced Merkle trees, light-client sampling
- [Ethereum Roadmap: Danksharding](https://ethereum.org/en/roadmap/danksharding/) — current status of the blob-throughput roadmap
