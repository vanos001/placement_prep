# Optimistic Rollups

## Overview

Optimistic rollups inherit the security of their L1 by posting compressed L2 transaction data on-chain and *assuming* that state transitions are correct unless proven otherwise. They sit at the centre of Ethereum's rollup-centric roadmap for one practical reason: they are fully EVM-equivalent today, they are cheap to operate because they do not generate cryptographic proofs for every batch, and they reuse the L1 as the court of last resort via a *fraud-proof* protocol.

This page covers the fraud-proof model end-to-end: the 7-day challenge window, the L2 → L1 withdrawal flow, the OP Stack architecture (Optimism, Base, opBNB), the Arbitrum Nitro design with its interactive bisection game, and a side-by-side comparison against ZK rollups. The intent is to be concrete enough that you could reason about an incident postmortem on any of these chains without re-reading the docs.

## The Fraud-Proof Model

The core wager of an optimistic rollup is this: every batch posted to L1 is treated as *presumptively valid*, but anyone can challenge it during a fixed window. If a challenger wins, the batch is re-executed on L1 (or the dispute is resolved through an interactive game) and the sequencer's bond is slashed. If no one challenges within the window, the batch is considered final.

The trade-off is asymmetric and important to internalise:

- **L1 verification cost is O(1)** for batches that are *not* challenged (which is the overwhelmingly common case).
- **L1 verification cost is O(batch size)** only when a fraud proof is actually triggered, and only the disputed portion is re-executed.

This is why optimistic rollups can sustain much higher throughput than the L1 — the L1 only ever pays for the *rare* dishonest batch, not for every honest one.

```
                    Optimistic Rollup Lifecycle (per batch)

  Sequencer                L1 (rollup contract)            Challengers
  ---------                --------------------            -----------
       |                            |                           |
       |  order L2 txs              |                           |
       |----------------------------+                           |
       |  execute off-chain         |                           |
       |  compute new state root S' |                           |
       |----------------------------+                           |
       |  post: (compressed data,   |                           |
       |         S_old,  S_new)     |                           |
       |--------------------------->|  emit BatchPosted event  |
       |                            |-------------------------->|
       |                            |   start challenge timer   |
       |                            |   T = 7 days              |
       |                            |                           |
       |                            |<-------------------------|
       |                            |  if S' wrong: submit     |
       |                            |  fraud proof             |
       |                            |                           |
       |                            |  verify proof on-chain   |
       |                            |  slash sequencer bond    |
       |                            |  revert to S_old         |
       |                            |                           |
       |                            |  (else) after T elapses  |
       |                            |  S_new is FINAL          |
```

The "optimism" is therefore in the verification *policy*, not in the cryptography. The protocol does not cryptographically guarantee correctness; it makes it economically irrational to publish a wrong state root, because doing so invites a slashable fraud-proof response.

## The 7-Day Challenge Period

The challenge window is set to **one week (604,800 seconds, or 5040 Ethereum epochs)** on both Optimism and Arbitrum. The choice of seven days is not arbitrary — it is the result of three constraints:

1. **L1 congestion tolerance.** A challenger may need to land an L1 transaction to initiate or progress a dispute. If L1 gas prices spike to thousands of gwei for several days, the window must be long enough that a challenger can afford to wait out the spike.
2. **Sequencer downtime tolerance.** If a sequencer posts a batch and then goes offline, the system must give time for fallback sequencers or social recovery to kick in.
3. **Prover time for fraud-proof generation.** Especially on Arbitrum, where the dispute is a multi-round bisection, each round requires re-execution of a slice of L2 history on L1, which itself costs gas and wall-clock time.

The window is *not* a "withdrawal delay" per se — withdrawals are only one consumer of finality. Any L1 contract that reads the rollup's state root (bridges, oracles, governance) must respect the same window.

> **Interview Angle**: "Why exactly 7 days?" The honest answer is that it is a conservative choice. The lower bound is "long enough that the L1 cannot be censored or congested into blocking a challenger." Seven days covers historical worst-case L1 gas spikes (e.g., the May 2022 de-peg episode where base fee exceeded 800 gwei for ~24 hours) with several multiples of safety margin. Reducing it to, say, 24 hours would lower user-friction but raise the risk that an attacker combined a network congestion attack with a fraudulent batch.

## L2-to-L1 Withdrawal Flow

A withdrawal from L2 to L1 is the canonical "test" of a rollup's security model, because the L1 bridge contract must decide whether to release funds based solely on the L2 state root. The full flow on OP Stack chains is:

```
  L2 user                        L2 sequencer              L1 bridge                L1 user
  -------                        ------------              ---------                -------
     |                                  |                       |                      |
     |  withdraw ETH:                   |                       |                      |
     |  burnOnL2(amount)                |                       |                      |
     |--------------------------------->|                       |                      |
     |                                  |                       |                      |
     |                                  |  include in batch,    |                      |
     |                                  |  post data to L1      |                      |
     |                                  |---------------------->|                      |
     |                                  |                       |                      |
     |                                  |   wait 7-day window   |                      |
     |                                  |   (challenge period)  |                      |
     |                                  |                       |                      |
     |  proveWithdrawal:               |                       |                      |
     |  submit Merkle proof of         |                       |                      |
     |  the burn tx against the         |                       |                      |
     |  finalized L2 state root        |                       |                      |
     |------------------------------------------------------->|                      |
     |                                  |                       |                      |
     |                                  |                       |  verify storage      |
     |                                  |                       |  proof against       |
     |                                  |                       |  finalized root      |
     |                                  |                       |  start 2nd timer     |
     |                                  |                       |  (claim window)      |
     |  claimWithdrawal:               |                       |                      |
     |  after claim window elapses     |                       |                      |
     |------------------------------------------------------->|                      |
     |                                  |                       |  release ETH         |
     |                                  |                       |--------------------->|
```

There are effectively *two* delays stacked:

1. **Challenge window** — the time between the batch containing the burn transaction being posted and the L2 state root being considered final on L1 (~7 days).
2. **Prove + claim window** — once the state root is final, the user posts a Merkle proof that their withdrawal was included, then waits a secondary "claim" window (typically a few hours on OP Stack, configurable per withdrawal) before anyone can sweep. The secondary window exists to allow a *fast* challenger to invalidate a withdrawal that depended on a non-final root in a reorg scenario.

In practice, third-party *liquidity providers* (e.g., Across, Hop, Bungee) front users the L1 funds and absorb the 7-day delay themselves, charging a fee. This means users rarely wait the full 7 days, but the security model still depends on it.

## OP Stack (Optimism)

The OP Stack is the modular, open-source software stack originally built for Optimism's mainnet and now used by **Base** (Coinbase), **opBNB** (BNB Chain), **Zora**, **Mode**, and many others. It is best understood as a *specification* plus a *reference implementation* — the spec is what matters because it lets anyone run a federated rollup with the same invariants.

### Architecture

```
                  OP Stack (per chain)
   ---------------------------------------------------------
   | L1 (Ethereum or other L1)                            |
   |     - L1CrossDomainMessenger                         |
   |     - L1StandardBridge (canonical ETH/ERC20 bridge)  |
   |     - OptimismPortal (deposits, withdrawals, proofs) |
   |     - SystemConfig (chain params: gasPayer, scalar)  |
   ---------------------------------------------------------
                          ^
                          | (deposits, withdrawals, batch posting)
                          v
   ---------------------------------------------------------
   | L2 (rollup)                                          |
   |     - op-node  : rollup consensus driver             |
   |     - op-geth  : Geth fork (execution, EVM-equivalent)|
   |     - op-batcher : posts sequenced L2 txs to L1      |
   |     - op-proposer : posts L2 output roots to L1      |
   |     - op-challenger: monitors for invalid outputs    |
   |     - op-conductor: multi-sequencer coordination     |
   ---------------------------------------------------------
```

A few details interviewers love to probe:

- **op-geth** is a fork of go-ethereum with minimal diffs: it adds a deposit transaction type (L1-to-L2 messages minted from L1), it changes the fee formula to `base_fee * (1 + dynamic_overhead)` (EIP-1559 still applies on L2), and it adds a `l1Cost` field to receipts so users can see how much L1 data they paid for.
- **op-batcher** posts transactions in *frames* — each frame is ≤ 120 KB to fit in a single L1 blob. Multiple frames per blob are concatenated; a single batch can span many blobs.
- **op-proposer** is intentionally lightweight: it only posts the L2 state root every few minutes (the L1 contract reads the latest root, doesn't need every block). The challenger daemon continuously compares the proposer's roots to its own locally-computed roots; if they diverge, it initiates a dispute.

### Fault Proofs (Cannon)

Optimism's original fraud-proof system was *not* fully operational for the first two years of mainnet — the chain relied on a "security council" multi-sig for emergency intervention. The **Cannon** fault-proof system, live since June 2023 on OP mainnet, replaced this with a real on-chain proof.

Cannon is built on the **MIPS** architecture: op-geth is compiled to MIPS bytecode, and a MIPS interpreter written in Solidity (yes, an EVM-implemented MIPS CPU) re-executes disputed L2 blocks step-by-step. The dispute is reduced to a bisection over the execution trace — challenger and proposer alternate narrowing down to a single MIPS instruction they disagree on, then the L1 contract executes that one instruction and decides.

```
       Cannon bisection game (single dispute)

  Step  Proposer claims         Challenger claims        Action
  ----  ----------------        -----------------        ------
   0    root at instr 0..N      disagree at instr N/2   split into halves
   1    root at instr 0..N/2    root at instr 0..N/2    agree on left, dispute right
   2    root at instr N/2..N     root at instr N/2..N    dispute continues
  ...   ...                     ...                     ...
   k    root at instr i..i+1     root at instr i..i+1    single-step
        (claim S_i correct)      (claim S_i wrong)       on-chain MIPS step
                                                        => verdict
```

The depth is bounded by `log2(N)` where N is the trace length — practical disputes complete in tens of rounds, not millions.

## Arbitrum Nitro

Arbitrum Nitro (One, Nova) takes a similar philosophical stance but a very different technical one. Where OP Stack uses MIPS-as-EVM-target, Nitro uses **WASM**.

### Architecture

```
                  Arbitrum Nitro
   ----------------------------------------------------------------
   | L1 (Ethereum)                                                 |
   |     - Bridge contract (escrow)                                |
   |     - Inbox contracts (delayed, sequencer, L1-to-L2)          |
   |     - Rollup contract (validators, stakes)                    |
   |     - Outbox contract (L2-to-L1 withdrawals, Merkle proofs)   |
   ----------------------------------------------------------------
                              ^
                              | (batches, stakes, challenges)
                              v
   ----------------------------------------------------------------
   | L2 (rollup)                                                   |
   |     - Nitro node (Geth-derived, with ArbOS precompiles)       |
   |     - Sequencer (feed + tx ordering)                          |
   |     - Feed server (real-time L2 data, pre-confirmation)       |
   |     - Validator (computes state roots, posts commitments)    |
   |     - Prover (WASM-based, generates execution proofs)        |
   ----------------------------------------------------------------
```

The trick: Nitro takes go-ethereum, compiles it to **WASM** using a custom Go-to-WASM compiler, and the WASM is then compiled to a custom ISA ("WAVM") for the on-chain interpreter. The dispute bisection operates over the WAVM execution trace.

### Nitro vs Cannon

| Dimension | OP Stack + Cannon | Arbitrum Nitro |
|-----------|--------------------|----------------|
| **Target ISA** | MIPS | WAVM (derived from WASM) |
| **Source** | op-geth compiled to MIPS | go-ethereum compiled to WASM, then to WAVM |
| **Dispute resolution** | Single-step on MIPS | Single-step on WAVM |
| **Challenge window** | 7 days | 7 days |
| **Sequencer** | Single (with failover) | Single ("anytrust" fallback on Nova) |
| **Permissionless validators** | Yes (since fault-proof launch) | Yes (since Nitro, 2022) |
| **Withdrawal time** | 7 days + claim window | 7 days + claim window |

The two designs are conceptually isomorphic: both compile the L2 client to a small ISA, run an EVM-implemented interpreter of that ISA on L1, and use bisection to localise disputes. The choice of ISA is an engineering decision (MIPS is simpler to implement in Solidity; WAVM is closer to a compiler-native target so the build pipeline is cleaner).

### AnyTrust and Data Availability

Arbitrum Nova uses a variant called **AnyTrust**, which trades the rollup's "data on L1" guarantee for a Data Availability Committee (DAC) of trusted committee members. The committee posts a signed commitment to the data; if any member refuses to release data, the system falls back to posting it to L1. This is a hybrid rollup/validium model.

## Comparison to ZK Rollups

The honest comparison hinges on three axes: **finality latency**, **proving cost**, and **EVM equivalence**.

```
                       Optimistic                ZK
                       ---------------           ---------------
  Per-batch L1 cost     ~ data cost only         ~ data + proof verification
  L1 verification       re-execute on dispute    verify a succinct proof
                       (O(batch) only on fraud) (O(1) always)
  Finality latency      7 days                   minutes (proof time + L1
                                                  inclusion)
  Trust assumption      >=1 honest watcher       none (cryptographic)
                       within 7 days
  EVM equivalence       full (today)             partial (zkEVM type 1-3,
                                                  trade-offs)
  Sequencer failure     censor only; funds safe   censor only; funds safe
                       via L1 forced txs         via L1 forced txs
  Worst-case recovery   challenger re-executes    prover re-submits proof
                       on L1                     (but must have data)
```

The "1 honest watcher" assumption is weaker than it sounds: anyone can be the watcher, including the user themselves. The risk is not "no honest watcher exists" but "the honest watcher cannot get an L1 transaction in" — i.e., L1 censorship. The 7-day window exists precisely to make this attack uneconomic.

ZK rollups have a different failure mode: they require the *prover* to be honest, not a watcher. A malicious prover cannot forge a proof (cryptographic impossibility, assuming soundness), but a prover can refuse to generate proofs, halting finality. This is mitigated by permissioned proving committees and, increasingly, proof-marketplace designs.

> **Interview Angle**: "If ZK is cryptographically stronger, why has the market stayed on optimistic rollups?" Three reasons: (1) **EVM equivalence is harder for ZK** — the EVM has 140+ opcodes, many of which (CALL, SELFDESTRUCT pre-Shanghai, dynamic jumps) are awkward to express as arithmetic circuits; type-1 zkEVMs (Taiko, Scroll, Polygon zkEVM type 2) exist but proof times are still 5–30 minutes per batch. (2) **Operational cost** — running a prover cluster is an order of magnitude more expensive than running op-batcher. (3) **Maturity** — the OP Stack and Arbitrum stack have multi-year track records, multiple audits, and hundreds of millions of TVL battle-tested through real incidents (Coinbase USDC depeg in March 2023, FTX collapse in November 2022). The cost-of-mistake for moving billions in stablecoin liquidity to a younger ZK stack is non-trivial.

## Real-World Incident: The November 2023 OP Sequencer Stall

On June 6, 2023, an OP Stack chain's sequencer stalled for ~3 hours because of a state inconsistency between op-node and op-geth after the Bedrock upgrade. The social recovery path worked — the chain resumed with a manual sequencer handover — but no funds were at risk because (a) withdrawals require the 7-day window and (b) the L1 contract never accepted a wrong state root. This is a textbook case of the optimistic model's safety holding even when its liveness fails.

## Interview Questions

### Q1: Why not shorten the 7-day window to 1 day?

The window length is set by the cost of L1 censorship, not by computation. If an attacker controls enough L1 validator stake or gas to censor a challenger's dispute transaction for 24 hours, a 1-day window would let a fraudulent batch finalise. Seven days makes a sustained L1 censorship attack economically infeasible at the scale required (you'd need to control majority of validator stake *and* sustain gas-price denial for the entire window).

### Q2: How does Cannon's MIPS interpreter fit in the EVM gas budget?

Each MIPS step in the on-chain interpreter costs roughly 100K–300K gas (a few EVM calls plus storage reads). The bisection algorithm localises to a single MIPS instruction before triggering on-chain re-execution, so only *one* MIPS step is actually run on L1. The cost of the dispute is dominated by the bisection itself (one L1 transaction per round, ~50K gas each), with depths bounded by `log2(trace_length)` — typically 20–30 rounds.

### Q3: Can a sequencer steal user funds?

No. The sequencer can censor or reorder transactions (an MEV vector, mitigated by forced-inclusion transactions that bypass the sequencer after a delay), but it cannot forge a state transition. Any withdrawal requires a Merkle proof against a finalised L2 state root, which the L1 contract verifies independently. A sequencer that published a wrong state root would be slashed during the challenge window.

## References

- Optimism Docs — "Protocol / Rollup Protocol": https://docs.optimism.com/stack/protocol/rollup
- OP Stack Specs — "Fault Proofs": https://specs.optimism.io/fault-proof/index.html
- Arbitrum Nitro Docs — "How Nitro Works": https://docs.arbitrum.io/how-arbitrum-works/nitro-overview
- Vitalik Buterin, "An Incomplete Guide to Rollups" (2021): https://vitalik.ca/general/2021/01/05/rollup.html
- EIP-4844: Shard Blob Transactions: https://eips.ethereum.org/EIPS/eip-4844
- Optimism Docs — "Withdrawal flow on OP Stack": https://docs.optimism.com/builders/app-developers/bridging
- Arbitrum Docs — "Challenge protocol": https://docs.arbitrum.io/how-arbitrum-works/challenge-protocol

## Related Topics

- [Ethereum Internals](./ethereum-internals.md) — EIP-4844 blobs, state trie, the L1 that rollups inherit from
- [ZK Rollups](./zk-rollups.md) — the validity-proof alternative
- [Consensus Mechanisms](./consensus-mechanisms.md) — L1 finality that rollups depend on
- [Blockchain Security](./blockchain-security.md) — sequencer attacks, bridge exploits, MEV
