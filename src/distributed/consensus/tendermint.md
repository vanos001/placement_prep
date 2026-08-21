# Tendermint

Tendermint is a Byzantine fault-tolerant (BFT) consensus algorithm developed by Jae Kwon in 2014, refined by Buchman et al. for the Cosmos network, and described formally in "The Latest Gossip on BFT Consensus" (2020). It is the consensus layer of the Cosmos Hub and ~50 application-specific blockchains ("zones" in Cosmos terminology). This page covers the three-stage voting protocol, the lock mechanism that prevents equivocation attacks, and the synchronization model that lets Tendermint process blocks deterministically without synchronization assumptions on the network round-trip time.

## The Model

Tendermint runs in an N = 3f + 1 replica system, tolerating f Byzantine (actively malicious) replicas. The protocol assumes **weak synchrony**: there exists a known upper bound Δ on network delay, but only after an unknown Global Stabilization Time (GST). Before GST, the network can be arbitrarily slow.

The protocol advances through **rounds**, each with a proposed block and a three-stage voting phase. If a round fails (the proposer is Byzantine, or the network is too slow), the round is abandoned and the next round begins.

## The Three Stages

A round consists of:

1. **Propose**: The round's proposer broadcasts a candidate block.
2. **Prevote**: Each replica broadcasts a prevote (signed message) either for the proposed block, `nil`, or for a previously-locked block.
3. **Precommit**: After collecting 2f+1 prevotes for the same block, replicas broadcast precommits. After collecting 2f+1 precommits, the block is committed.

```text
Propose ──── Prevote ──── Precommit
   │            │             │
   │            │             │
   ▼            ▼             ▼
   block       2f+1 prevotes 2f+1 precommits → COMMIT
   broadcast  → agree on     → block finalized
   by leader   block         in this round
```

If 2f+1 prevotes for the same block are not collected within `timeoutPropose` or `timeoutPrevote`, replicas broadcast `nil` and the round moves on without committing.

## The Lock Mechanism

Tendermint's key safety mechanism is **PoLC (Proof of Lock Change)**: once a replica has prevoted for a block in round R, it "locks" on that block. In subsequent rounds, the replica can only prevote for the locked block, *unless* it sees a "PoLC for a higher round" (i.e., 2f+1 prevotes for a different block in a higher round).

This prevents a Byzantine proposer from trying to commit two different blocks across two rounds: as soon as a quorum locks on a value, the only way to unlock is to prove that a *higher* quorum agreed on a *different* value, which is impossible without f+1 honest replicas lying.

```text
Round R1:
  Proposer P1 (Byzantine) proposes block B1.
  2f+1 honest replicas prevote for B1.
  Replicas lock on B1. Precommit fails (P1 didn't send precommit).
  Round R1 times out.

Round R2:
  Proposer P2 proposes block B2 (different from B1).
  Honest replicas are locked on B1.
  They prevote for B1, not B2 — they cannot unlock without
  seeing a PoLC for a higher round.
  Round R2 also fails to commit B2.

Round R3:
  Proposer P3 proposes block B1 (back to B1).
  Honest replicas see their own locks agree, prevote for B1.
  Round R3 commits B1.
```

## Validator Set and Proposer Selection

Each round's proposer is determined by a deterministic algorithm on the validator set:

```go
func (vals *ValidatorSet) GetProposer(round int32) *Validator {
    // (height + round) % total_voting_power
    // ... selected via deterministic weighted round-robin
    // Each validator's weight is proportional to its stake.
    return vals[valIdx]
}
```

The selection is deterministic given `(height, round)`, so every honest replica computes the same proposer. A Byzantine proposer can withhold or equivocate, but cannot move the chain to a different value because of the lock mechanism.

## Synchronization Model

Tendermint uses a gossip protocol (`pp` or "peer-to-peer") to disseminate proposals, prevotes, and precommits. Every replica gossips every signed message it sees to all peers. With N replicas, the gossip cost per message is O(N), but each replica receives ~3 copies of every message — a redundancy that compensates for unresponsive peers.

The protocol distinguishes **synchronous decisions** (committed when 2f+1 precommits are collected) from **asynchronous propagation** (the full block content takes longer than a vote to propagate). A block can be committed in a round even if some honest replicas haven't fully received the block data; they will catch up via state sync.

## Block Production and Finality

Tendermint produces blocks at a configurable interval (typically 1-5 seconds on Cosmos zones). Finality is **instant** — once a block is committed, it cannot be reverted (no forks). This contrasts with probabilistic finality in PoW chains (Bitcoin) or PoS chains without BFT consensus (early Ethereum).

Instant finality is a strong property: applications built on Tendermint chains can assume that once a transaction is in a committed block, it is forever. No reorgs, no "probabilistic depth" requirements.

## ABCI: Application-Blockchain Interface

Tendermint separates the consensus engine from the application via the ABCI (Application Blockchain Interface):

```text
┌─────────────────┐     ABCI        ┌──────────────────┐
│ Tendermint Core │ ←──────────────→│  Application     │
│  - Networking   │   (Unix socket) │  - State machine │
│  - Consensus   │                 │  - Transaction   │
│  - Block store  │                 │    validation    │
└─────────────────┘                  └──────────────────┘
```

The application implements three ABCI calls:

- `DeliverTx(tx)`: Apply a committed transaction to the application state.
- `Commit()`: Return the new state hash (Merkle root) to be included in the next block.
- `Query(path, data)`: Read-only queries against the latest committed state.

Tendermint validates the state hash on each block: if a proposed block's transactions would produce a state hash that doesn't match the application's reported state hash, the block is rejected.

## Light Client Verification

Tendermint's light client is unusually simple because of BFT finality: to verify that a block at height H is committed, the light client asks a trusted full node for the validator set at height H and the signatures for that block. It verifies:

1. The validator set hash matches the chain's `chain_id` (which is fixed at genesis).
2. ≥ 2/3 of the validators' signatures are valid for that block.

Once verified, the block is final. No need to download the entire chain or wait for confirmations. This is the basis of Cosmos's IBC (Inter-Blockchain Communication): a light client of chain A is embedded in chain B's smart contract, allowing trustless cross-chain messages.

## Comparison to Other BFT Protocols

| Protocol | Finality | Communication | Phases | Leader rotation |
|----------|----------|---------------|--------|-----------------|
| PBFT (1999) | Instant | O(n²) | 3 + view-change | Implicit |
| Tendermint | Instant | O(n) gossip | 3 + lock | Deterministic per round |
| HotStuff (2019) | Instant | O(n) | 3 pipelined | Rotating |
| DiemBFT (2020) | Instant | O(n) + gossip | 3 pipelined | VRF-based |

The distinguishing feature of Tendermint is the **lock mechanism**: it prevents equivocation across rounds but adds latency in failure cases. HotStuff achieves the same safety via its 3-chain commit, without explicit locks. Tendermint is simpler to implement from scratch; HotStuff is theoretically cleaner.

## Common Pitfalls

1. **Validator set changes between blocks must be carefully sequenced.** If validators V1 and V2 have different sets at heights H and H+1, a light client verifying H must use the H validator set, not the H+1 set. Cosmos's `ValidatorSetChange` ABCI call handles this; applications must implement it correctly.
2. **The proposer-selection algorithm must be deterministic and bit-identical across replicas.** Any drift in the algorithm (e.g., integer overflow on voting power) causes replicas to disagree on the proposer, halting the chain. Cosmos uses a fixed-point arithmetic library for this.
3. **Timeouts must be configurable per-chain.** A 1-second timeout is too short for a globally distributed chain; a 10-second timeout is wasteful for a private testnet. Cosmos chains expose `timeout_propose`, `timeout_prevote`, `timeout_precommit` as consensus parameters.
4. **ABCI applications must be deterministic.** Any non-determinism (random number, local clock, iteration over a map with nondeterministic order) causes replicas to diverge and halt. Tendermint provides a deterministic merkle tree library for ABCI apps.
5. **Replay attacks across chains.** A transaction signed for chain `cosmoshub-4` must not be valid on chain `cosmoshub-5`. The `chain_id` is part of the signed message and is enforced by Tendermint Core.

## References

- Jae Kwon, "[Tendermint: Consensus without Mining](https://tendermint.com/static/docs/tendermint.pdf)" (2014)
- Buchman, Kwon, Milosevic, "[The Latest Gossip on BFT Consensus](https://arxiv.org/abs/1807.04906)" (2018, arXiv)
- [Tendermint Core documentation](https://docs.tendermint.com/)
- [Cosmos SDK application development guide](https://tutorials.cosmos.network/)
- [IBC protocol specification](https://github.com/cosmos/ibc)
- Ethan Buchman, "[The Cosmos white paper](https://cosmos.network/cosmos-white-paper.pdf)" (2016)
