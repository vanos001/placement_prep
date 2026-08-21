# ZK Rollups

## Overview

ZK rollups replace the optimistic "publish-and-challenge" model with a *validity-proof* model: every batch of L2 transactions is posted alongside a succinct cryptographic proof that the state transition was computed correctly. The L1 verifier contract checks the proof in constant time, regardless of how many transactions the batch contains. There is no challenge window, no honest-watcher assumption, and no 7-day withdrawal delay (the bottleneck becomes proof generation and L1 inclusion, not a security timer).

This page covers the validity-proof model, the L2 state commitment and its verification, the prover/verifier split, and the four production systems that define the current ZK-EVM landscape: **zkSync Era**, **StarkNet**, **Polygon zkEVM**, and **Scroll**. We end with a head-to-head against optimistic rollups — not to declare a winner, but to make the trade-offs explicit so you can pick the right tool for a given workload.

## The Validity-Proof Model

A ZK rollup is, formally, a *computational integrity* scheme. The prover (an off-chain cluster) computes the new state root `S'` from the old state root `S`, a batch of transactions `txs`, and a list of pre/post state diffs. It produces a proof `π` such that:

```
    π  attests to:   ∃ valid execution E with
                     E.initial_state = S
                     E.txs           = txs
                     E.final_state   = S'
                     E.gas_used      ≤ block_gas_limit
                     (every opcode charged per EVM rules)
```

The proof `π` is **non-interactive** (no back-and-forth between prover and verifier) and **succinct** (the proof is hundreds of bytes to a few hundred KB regardless of how long `txs` is). The verifier contract on L1 takes `(S, S', txs_commitment, π)` and outputs accept/reject.

The crucial property is **soundness**: assuming the underlying proof system's cryptographic assumptions hold, a malicious prover cannot construct a `π` that convinces the verifier of a false statement. There is no "honest majority" assumption on the prover, no slashing required for safety, and no time window.

```
                       ZK rollup per-batch flow

  Sequencer          Prover cluster          L1 verifier contract
  ---------          --------------          --------------------
       |                       |                       |
       |  order txs             |                       |
       |  execute off-chain     |                       |
       |  produce:              |                       |
       |   - txs (compressed)  |                       |
       |   - pre/post roots     |                       |
       |   - trace witness      |                       |
       |----------------------->|                       |
       |                        |  witness -> AIR      |
       |                        |  AIR -> prover        |
       |                        |  prover -> π          |
       |                        |  (Π over batch)       |
       |                        |---------------------->|
       |                        |                       |
       |                        |                       |  verify π against
       |                        |                       |  (S, S', txs_commit)
       |                        |                       |  cost: O(log |txs|)
       |                        |                       |  -> accept
       |                        |                       |  S_final = S'
```

The prover's job is dominated by one operation: turning the EVM (or the rollup's VM) execution trace into a system of polynomial constraints — an **AIR** (Algebraic Intermediate Representation) for STARKs or a **circuit** for SNARKs — and then running the SNARK/STARK prover on that system. The work is parallelizable but extremely memory-intensive.

## The L2 State Commitment

Each ZK rollup maintains a state commitment — typically a Merkle root of the L2 state tree, in the same tradition as Ethereum's MPT but with a different choice of commitment primitive.

| System | State commitment | Hash function | Tree structure |
|---------|------------------|----------------|----------------|
| **zkSync Era** | Account + storage Merkle roots | Boojum (Poseidon-based SNARK) | Binary storage tree, key derived from `keccak(slot)` |
| **StarkNet** | Contract storage + nonce + balance commitments | Pedersen (legacy) / Poseidon (v0.11+) | Binary Patricia |
| **Polygon zkEVM** | Merkle root compatible with Ethereum MPT | Poseidon (Pil Stark24) | Reuses MPT structure for EVM equivalence |
| **Scroll** | Ethereum-compatible state root | Poseidon (Goldfeder-style) | Ethereum MPT, type-1 equivalence |

For type-1 zkEVMs (Polygon, Scroll, and the in-progress Taiko), the state root is byte-for-byte identical to what `eth_getProof` would return on an L1 node. This is the deepest form of EVM equivalence — every JSON-RPC method, every storage layout, every gas cost matches L1. The cost is proof complexity: the entire EVM including the MPT hashing must be expressible as constraints.

For zkSync Era and StarkNet, the state root is *not* Ethereum-compatible. Both maintain their own account model. zkSync's account abstraction (native account contracts for every address) means there is no EOA/contract distinction; StarkNet goes further by using the Cairo VM in lieu of the EVM entirely.

> **Interview Angle**: "What does 'EVM equivalence' actually mean for a ZK rollup?" There is a five-level taxonomy due to Vitalik (type 1 = fully equivalent, type 2 = equivalent except gas costs, type 2.5 = equivalent with worst-case gas increases for some opcodes, type 3 = almost-equivalent with some opcodes unprovable, type 4 = source-equivalent only). Polygon zkEVM is type 2, Scroll is type 1 (state root identical to L1), zkSync Era is type 4 (Solidity compiles to a custom VM, not EVM bytecode), StarkNet is "no EVM at all."

## The Prover/Verifier Split

This is the defining design tension of any ZK rollup. The asymmetry is enormous:

```
                       Cost asymmetry (per batch of 10K simple transfers)

  Metric                 Prover              Verifier (L1 contract)
  -----------------      --------            ---------------------
  Wall-clock time        30–600 s            200–800 ms (in block gas)
  Compute                100s of CPU cores    single EVM call
                         + GPU (optional)
  Memory                 50–500 GB            ~constant
  Energy / batch         ~0.5–2 kWh           negligible
  Result                 π (proof, 200B–200KB) accept/reject bit
```

Because verification is constant-time and constant-cost, the L1 contract's gas cost per batch is dominated by a fixed call (verifier precompile or a pairing check) plus the cost of *posting the data* (which dominates on EIP-4844 chains). Per-transaction L1 cost amortises to roughly `gas_per_batch / txs_per_batch`, which is why all ZK rollups push to increase batch size — more transactions per proof amortises the constant verification cost.

The prover cluster is the operational cost centre. zkSync's prover cluster ("Boojum", launched 2023, replaced the original "Plonk/Sync" stack) uses a SNARK over a PLONK-style arithmetisation, with Poseidon hashes and elliptic curve operations on the Babyjon curve — chosen because it has efficient modular arithmetic. StarkNet's "Sharp" prover uses STARKs over the small Mersenne prime field `2^61 - 1`, with proofs then wrapped in a SNARK for L1 cost reduction (STARK proofs are 50–200 KB; a SNARK wrapper compresses them to ~100 KB).

### SNARK vs STARK

| Property | SNARK (Groth16, PLONK, Halo2) | STARK |
|----------|-------------------------------|-------|
| **Trusted setup** | Groth16 needs per-circuit setup; PLONK universal; Halo2 none | None (transparent) |
| **Proof size** | ~200 bytes | ~50–200 KB |
| **Verification gas** | ~250K (Groth16 pairing) | ~5M (STARK FRI verification) — typically wrapped in SNARK |
| **Prover time** | Slower (FFT-heavy) | Faster on parallel hardware (hash-based, GPU-friendly) |
| **Post-quantum** | No (pairings broken by Shor) | Yes (hashes safe) |
| **Used by** | zkSync Era (Boojum/PLONK), Polygon zkEVM (Plonk + GulnoxBob), Scroll (Halo2 on BN254) | StarkNet (Booting STARK + SNARK wrapper) |

The "SNARK wrapper" pattern (StarkNet, Polygon's "FRI-then-SNARK") is increasingly common: generate the big STARK efficiently, then compress it with a SNARK whose verifier is small enough to fit cheaply in an L1 transaction.

## zkSync Era

zkSync Era is Matter Labs' flagship L2, in production since March 2023. Three things distinguish it from the others:

1. **Native account abstraction.** Every address is a smart contract; there is no EOA/contract split. This means signature schemes are user-chosen (not just secp256k1), sessions and meta-transactions are native, and nonce handling is per-account. The trade-off is that L1 → L2 transactions must be processed by the Bridge's "base token" logic, since you cannot "transfer ETH to an EOA" in the L1 sense.
2. **The Boojum proof system** (PLONK-style, Poseidon hashes, Babyjon curve, with a recursive wrapper). Boojum replaced the earlier "Sync" stack and reduced prover memory from ~100 GB to ~32 GB per batch — meaningfully better unit economics.
3. **LLVM-based compiler.** Solidity, Vyper, and (via the LLVM pipeline) Rust, C++, and Move all compile to the same VM, which is *not* the EVM. This is type-4 in the equivalence taxonomy.

```
                  zkSync Era request path

   Wallet (EIP-1193)
        |
        |  eth_sendTransaction
        v
   zkSync JSON-RPC node
        |
        |  validate (account abstraction:
        |            signature, nonce, gas)
        v
   Mempool
        |
        |  sequencer selects
        v
   Block executor (zkEVM, type-4)
        |  produces state diff + witness
        v
   Prover cluster (Boojum, recursive)
        |  π (final SNARK)
        v
   L1: zkSync Bridge contract
        |  verifyAndExecute
        v
   L2 state root finalised on L1
```

zkSync Era also pioneered the "validium → rollup" continuum: a separate mode, **zkSync Portillium**, allows data availability to be moved to a committee, lowering per-tx cost but introducing a trust assumption.

## StarkNet

StarkNet (StarkWare) is the only major ZK rollup that does *not* target EVM compatibility at all. Its VM is Cairo — a Turing-complete, register-based VM designed from the ground up for provability. Cairo programs are essentially lists of algebraic assertions over a finite field; the prover turns execution into an AIR and a STARK.

Cairo 1.0 (released 2023) replaced the original Cairo (which was essentially a hand-written AIR assembly) with a Rust-like syntax that compiles to Sierra (a safe intermediate representation), which then compiles to Cairo assembly. The Sierra layer guarantees that no runtime fault can occur — every program is total — which simplifies the prover (no error branches in the AIR).

```
              StarkNet compilation + proof pipeline

   Cairo 1.0 source
        |
        |  compile
        v
   Sierra (safe IR, all panics compiled to explicit branches)
        |
        |  compile
        v
   Cairo (assembly-like, register VM bytecode)
        |
        |  execute
        v
   Execution trace (Cairo VM steps)
        |
        |  AIR constraints applied
        v
   STARK proof (FRI over Mersenne 2^61-1)
        |
        |  SNARK wrapper (Plonk/Babyjon)
        v
   π (compact, ~100 KB) -> L1 verifier
```

StarkNet also introduced **Pil Stark24** (a constraint language) and **Stone** (the production prover). The verifier contract on L1 is ~5M gas for raw STARK; the SNARK wrapper brings this to ~300K. The trade-off for StarkNet's design is ecosystem: most existing Solidity tooling does not work natively, requiring a transpiler (Warp, deprecated) or native Cairo rewrites.

## Polygon zkEVM

Polygon zkEVM (type 2 equivalent) targets full EVM bytecode equivalence with one deliberate deviation: the **state root hash function** is Poseidon rather than Keccak. This means an L1 node would compute a *different* state root from a Polygon zkEVM node for the same state — type 2, not type 1.

The proof pipeline uses three chained SNARKs:

1. **zREDS** — a zkEVM execution circuit (in-house, Plonkish arithmetisation).
2. **fRI** — a STARK-like intermediate proof that aggregates many zREDS proofs.
3. **Groth16** — a final SNARK that compresses the fRI output for cheap L1 verification.

The chain of transformations is:

```
   EVM trace
        |
        |  zREDS circuit (~10M constraints/batch)
        v
   zREDS proof
        |  aggregated by FRI (sumcheck-style)
        v
   Aggregated STARK (~500 KB)
        |  wrapped by Groth16 over the aggregated STARK verifier
        v
   Final proof (~200 bytes)
        |  verified on L1 in ~250K gas
        v
   state root committed
```

The end-to-end prover time on commodity hardware (no specialised ASICs) is on the order of minutes for a batch of ~500 transactions. Polygon has invested heavily in proving ASICs (the "Polygon Miden" project, though that is a separate STARK-based VM, not the EVM).

## Scroll

Scroll is the closest production system to a type-1 zkEVM: it produces state roots byte-for-byte compatible with Ethereum's MPT. The trade-off is throughput and prover cost — type-1 equivalence means the *entire MPT hashing* must be expressed as a circuit, including the keccak256 hash function, which is the most expensive primitive to express arithmetically (keccak has ~30K bit-constraints per absorbed block).

Scroll uses **Halo2** (the Zcash-derived proof system) over the BN254 curve. Halo2's distinctive feature is **no trusted setup** — proofs are recursive and use a cycle of curves (BN254 + Pasta, eventually EVM-friendly cycles). The prover is open-source and runs on a distributed cluster.

Scroll's architecture is intentionally modular: the sequencer is a separate role, the prover is a separate role, and the L1 contracts (the bridge and the verifier) are designed to be swappable. This reflects the project's research orientation — they have published detailed accounts of how each EVM opcode is mapped to the AIR.

## Comparison to Optimistic Rollups

The honest, detailed comparison:

```
                              Optimistic           ZK
                              ---------            --------
  L1 verification cost         O(1) typical,       O(1) always
                              O(batch) on fraud
  Finality delay               7 days               minutes (proof time
                                                   + L1 inclusion)
  Capital efficiency           low (funds locked     high (instant
                              for 7d during wd)      finality)
  Prover hardware              none required         required (expensive)
  Sequencer failures           censorship only,      censorship + proving
                              funds safe via         failures (liveness
                              forced inclusions      hit if prover stalls)
  Worst-case L1 load           bursty (only on fraud)  steady (always
                                                   verifying)
  EVM equivalence              full today            type 1-4, with
                                                   trade-offs per type
  Cross-L2 composability       requires 7-day delay   near-instant
                              (or 3rd-party LP)
  Audited, in production       2+ years              1+ year (zkSync),
                                                   StarkNet; 6-12 months
                                                   others
```

The market is bifurcating: optimistic rollups dominate *user-facing* L2 traffic today (Base, Arbitrum, OP mainnet) because EVM equivalence is bulletproof and the 7-day window is hidden behind third-party liquidity providers. ZK rollups dominate *application-specific* L2s where the 7-day window matters (perpetual DEXes that need fast settlement, gaming chains where assets move often, and cross-L2 bridges where the L2 → L1 path is on the critical path).

> **Interview Angle**: "Why isn't everyone on ZK yet if it's strictly stronger?" Because the safety advantage is real but the *liveness* and *cost* trade-offs are also real: ZK provers are expensive (Polygon's prover cluster runs to seven figures annually per chain), the type-1 zkEVMs have the worst prover economics because they must express the full MPT, and EVM tooling (foundry, hardhat, viem) requires small but real adjustments for type-4 systems like zkSync. The gap is narrowing — Scroll and Polygon type-2 have made enormous progress in 2024 — but the optimistic ecosystem still has a 2-year head start in operational maturity.

## Interview Questions

### Q1: What's the worst-case failure mode of a ZK rollup?

Censorship or proving failure. The sequencer can refuse to include transactions (mitigated by L1 forced-inclusion transactions, same as optimistic rollups). The prover cluster can refuse or fail to generate proofs, halting finality. Funds are never at risk of being stolen (cryptographic soundness), but they may be temporarily inaccessible. The mitigation is permissionless proving — anyone can submit a valid proof to the L1 contract — but in practice, the prover cluster is operated by the rollup vendor for cost reasons.

### Q2: How does EIP-4844 affect ZK rollups differently from optimistic rollups?

For both, blobs reduce the L1 data-posting cost by ~10–100x. For ZK rollups, the savings are *larger* because ZK batches typically post more data per batch (compressed transaction data plus the proof). zkSync Era moved almost entirely to blob-based data posting within weeks of the Dencun upgrade (March 2024). The blob fee market (separate from the EVM calldata market) is now the dominant variable cost component for all rollups.

### Q3: Why does StarkNet wrap its STARK in a SNARK?

STARK proofs are 50–200 KB and verification costs ~5M gas on L1. A SNARK wrapping a STARK reduces the L1 verification to a single pairing check (~250K gas) at the cost of an additional prover step (the SNARK prover over the STARK verifier circuit). The trade-off is favourable because L1 gas is expensive (~$50 for 5M gas at 30 gwei) while the additional prover work is amortised over many batches in the same final SNARK.

## References

- zkSync Era Docs — "Prover system (Boojum)": https://docs.zksync.io/zk-stack/concepts/prover
- StarkNet Docs — "Architecture overview": https://docs.starknet.io/architecture/
- Polygon zkEVM Docs — "Proof generation": https://docs.polygon.technology/zkEVM/technology/proof-generation/
- Vitalik Buterin, "Different types of ZK-EVMs" (2022): https://vitalik.ca/general/2022/08/04/zkevm.html
- Vitalik Buterin, "An Incomplete Guide to Rollups" (2021): https://vitalik.ca/general/2021/01/05/rollup.html
- Scroll Docs — "Architecture": https://docs.scroll.io/technology/overview
- EIP-4844: Shard Blob Transactions: https://eips.ethereum.org/EIPS/eip-4844

## Related Topics

- [Ethereum Internals](./ethereum-internals.md) — state trie, EIP-4844, rollups overview
- [Optimistic Rollups](./optimistic-rollups.md) — the fraud-proof alternative
- [Consensus Mechanisms](./consensus-mechanisms.md) — L1 finality that rollups inherit
- [Blockchain Security](./blockchain-security.md) — prover/sequencer attack vectors
