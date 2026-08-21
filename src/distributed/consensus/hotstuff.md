# HotStuff

HotStuff is a Byzantine fault-tolerant (BFT) consensus protocol introduced by Yin, Malkhi, Reiter, Gueta, and Abraham at ACM CCS 2019. Its distinguishing feature is a clean separation between a linear view-change protocol and a pipelined three-chain commit, allowing it to achieve O(n) message complexity per consensus decision under partial synchrony — compared with PBFT's O(n²) — while preserving linear communication and a responsiveness property under happy-path conditions. HotStuff is the consensus core of Facebook's Libra/Novi/Diem blockchain, of Aptos, and of several academic BFT frameworks.

## Why HotStuff Exists

PBFT (Castro-Liskov, 1999) was the first practical BFT protocol and is widely studied, but it has three scaling problems:

1. **MAC is O(n²)**: PBFT's pre-prepare phase requires the primary to send a different pre-prepare message to every replica. With 100 replicas, that's 10,000 messages per decision.
2. **Three-phase commit**: PBFT uses pre-prepare, prepare, and commit. The first phase is essentially primary-to-replica dispatch; the next two are all-to-all broadcasts. The cost per decision is 3 × O(n²) messages.
3. **View change is expensive**: When the primary is suspected faulty, a new primary must collect `n − f − 1` view-change messages, then broadcast a "new-view" message that piggybacks every in-flight consensus instance's state. In the worst case, this is O(n³).

HotStuff refactors these phases into a unified three-stage pipeline where each stage is a single round of communication through a rotating leader. The leader uses threshold signatures (or signature aggregation) so that any "vote" message is exactly 1 signature, not n. View change becomes essentially free because the pipeline naturally advances: a new leader takes over at the next view boundary, with the previous view's highest-QC as the starting point.

## The Model

- **n = 3f + 1** replicas, **f** of which may be Byzantine.
- **Synchrony**: The protocol assumes partial synchrony (DLS 1988) — there is a known bound Δ on message delay, but the bound is only known to be in effect after some unknown Global Stabilization Time (GST).
- **Quorum**: A quorum is any 2f + 1 replicas.
- **Cryptographic** primitives: Each replica signs votes with its private key; the leader aggregates them into an 80-byte threshold signature (BLS) or a compact multi-sig (Schnorr). Byzantine replicas cannot forge the aggregate.

## The Three-Chained Commit

A HotStuff decision is a chain of three QCs (Quorum Certificates) — essentially three rounds of voting, each producing an 80-byte aggregate signature. The chain is the key:

```text
View n:     QC₁ ── prepare
View n+1:        ── pre-commit  (QC₁ included in the proposal)
View n+2:             ── commit  (QC₂ included in the proposal)
View n+3:                  ── decide  (QC₃ included in the proposal)
```

A `QC` is a `(view, block_hash, signature)` triple — the aggregate of 2f+1 votes for that block in that view. The "blockchain" terminology is apt: HotStuff organizes proposals into a tree of blocks, and a block is committed when its QC chain has depth 3.

Why three? Two chains give you safety if all replicas are honest; three chains give you safety even with f Byzantine replicas because any two valid commit-certificates must overlap by f+1 honest replicas, which would have signed conflicting commits — a contradiction.

## Linear View Change

The pipelined design is what makes view change linear:

1. When a replica suspects the primary is faulty (timeout), it sends a `timeout` message containing the highest QC it has seen.
2. The next-view primary collects `n − f` timeouts (i.e., 2f+1 timeouts including f+1 honest).
3. The new primary's proposal includes the highest QC it received. This is the only state carried across the view change — no full inventory of in-flight instances.

Because the protocol is a chain of QCs, the new leader's job is just to "extend the chain" — propose a new block whose parent is the highest QC. The chain's safety is preserved regardless of how many views in a row failed.

## The Basic HotStuff Algorithm (simplified pseudocode)

```text
Replica state:
  • b_lock  = highest known committed-3-chain block (or genesis)
  • b_exec  = last executed block
  • v       = current view number
  • high_qc = highest QC this replica has voted on

Upon proposal P (block with parent QC) in view v:
  if P.parent_qc.view >= high_qc.view and P is valid:
    # Vote
    send ⟨VOTE, v, hash(P), σ_i⟩ to leader(v)
    high_qc = P.parent_qc
  else:
    send ⟨TIMEOUT, v, high_qc, σ_i⟩ to all

Leader of view v:
  On collecting 2f+1 VOTEs for P:
    qc = aggregate(2f+1 votes)
    new_block = Block(parent=P, qc)
    broadcast ⟨PROPOSE, v+1, new_block⟩
  On collecting 2f+1 TIMEOUTs for view v:
    high_qc' = max(timeout.qc for timeout in timeouts)
    new_block = Block(parent=high_qc'.block, qc=high_qc')
    broadcast ⟨PROPOSE, v+1, new_block⟩

On receiving PROPOSE in view v+1:
  verify signature on QC
  if parent is descendant of b_lock:
    # Continue voting
  else:
    # Reject and timeout
```

The `b_lock` invariant: a replica only votes for a block whose parent is at the head of the highest known 3-chain. This prevents forks.

## Chained HotStuff (Pipelined)

The "chained" form is what production systems implement. Instead of explicit three-stage rounds, each view's PROPOSE message *is* one stage of the pipeline for an earlier proposal:

```text
View v:   propose block B
View v+1: propose block B' = (parent B, QC of B)       ← B is at "prepare" stage
View v+2: propose block B'' = (parent B', QC of B')    ← B is at "pre-commit"
View v+3: propose block B''' = (parent B'', QC of B'') ← B is at "commit"
View v+4: ...                                           ← B is at "decide"
```

Every view advances every in-flight block by one stage. There is no separate "view change" message: a new leader's first proposal naturally continues the chain. If the leader is Byzantine and refuses to propose, the timeout mechanism kicks in, but no consensus state is lost.

## Linear Communication and Threshold Signatures

HotStuff's O(n) message complexity relies on a star topology: every replica sends to the leader only, and the leader broadcasts to all. The leader's broadcast is O(n) and each replica's vote is O(1). Without threshold signatures, the leader's broadcast would still be O(n) but the *verification* by each replica would require O(n) signature checks (verifying 2f+1 individual signatures).

The threshold signature (BLS or Schnorr multi-sig) reduces this to a single signature check per replica, so the per-decision crypto cost is:

- Replicas: 1 signature per round (signing own vote) + 1 verification (checking leader's aggregate).
- Leader: 2f+1 signature aggregations + 1 broadcast.

Total: O(n) cryptographic operations across the network.

## Responsiveness (the Linear-Liveness Property)

HotStuff's other key property is "responsiveness": under synchrony (after GST), the protocol makes progress in time proportional to the actual network delay, not the worst-case bound Δ. The leader waits for 2f+1 votes — which arrive after one network round-trip — and proposes the next block. There is no built-in delay.

This is critical for production: a protocol that is "live" but takes Δ time per decision (like Tendermint's original spec) wastes 200 ms per consensus decision even when the actual network is 5 ms.

## LibraBFT / DiemBFT: The Production Variant

The Diem project (formerly Libra) implemented HotStuff as `LibraBFT` with several practical modifications:

1. **Pacemaker**: explicit timeout-based view advancement, with exponential backoff.
2. **Validator-signed votes** (not threshold signatures): each vote is individually signed; the leader aggregates them into a multi-signature. Simpler to reason about, slightly higher message size.
3. **State sync**: new validators can join mid-chain by downloading the committed prefix from peers and verifying against the QC chain.
4. **Execution-on-commit**: transactions in a committed block are executed by every replica's VM, producing deterministic state transitions.

Aptos and Sui (post-Diem forks) use essentially the same algorithm with minor changes.

## HotStuff vs. Other BFT Protocols

| Protocol | Year | Message complexity | Phases | Liveness | Notes |
|----------|------|-------------------|--------|----------|-------|
| PBFT     | 1999 | O(n²)             | 3 + view-change | Synchronous | The classic |
| Tendermint| 2018 | O(n²) (gossip)    | 2 + lock | Synchronous after GST | Blockchains: Cosmos |
| HotStuff | 2019 | O(n) (leader)     | 3 pipelined | Responsive | Diem, Aptos |
| DiemBFT  | 2020 | O(n) + gossip     | 3 pipelined | Responsive | Production HotStuff |
| Narwhal/Bullshark | 2022 | O(n²) gossip | 2 | Synchronous | Sui |

HotStuff's responsiveness advantage over Tendermint (which advances views in lockstep with `Δ`-bound timers) is the principal production difference. The communication complexity advantage matters less in practice because all real-world BFT networks use ~100-300 validators, not 10,000.

## Pitfalls

1. **Leader rotation must be unpredictable** to prevent Byzantine leaders from strategically timing their failures. HotStuff uses a verifiable random function (VRF) or a hash-chain leader schedule.
2. **Threshold signature setup is expensive.** Generating the BLS public key requires a distributed key generation (DKG) ceremony; rotating the validator set requires re-running DKG. Production systems like Diem have multi-day ceremonies.
3. **Timeout-based pacemakers can stall if too many replicas are offline.** HotStuff cannot make progress with < 2f+1 live replicas, regardless of synchrony.
4. **The 3-chain commit is 3 network round-trips per decision in the worst case.** Chained HotStuff amortizes this to ~1 RTT per decision under steady state, but the *first* decision after a leader change still takes 3 RTTs.
5. **Aggregated signatures are not zero-knowledge.** Each vote reveals which replica signed it. For privacy-sensitive applications, ring signatures or zk-proofs are needed, which break the linear-complexity guarantee.

## References

- Yin, Malkhi, Reiter, Gueta, Abraham, "HotStuff: BFT Consensus with Hot Signal" ([CCS 2019 paper](https://arxiv.org/abs/1803.05069))
- [DiemBFT: The Diem consensus specification](https://developers.diem.com/docs/technical-papers/diem-consensus-paper/)
- [AptosBFT v2 spec](https://aptos.dev/guides/best-practices-glossary)
- [A Survey of BFT consensus protocols (2023)](https://arxiv.org/abs/2302.10849)
- [Cosmos SDK — Tendermint consensus](https://docs.tendermint.com/v0.34/introduction/what-is-tendermint.html)
- [Libra white paper (2019)](https://libra.org/white-paper/) — original HotStuff production reference
