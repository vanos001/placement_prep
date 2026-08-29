# Modular Blockchains: Splitting Execution, Settlement, Consensus, and Data Availability

Every blockchain does four jobs: it **orders** transactions (consensus), **publishes** their bytes so anyone can reconstruct state (data availability), **executes** the state transition, and **settles** disputes and cross-domain transfers. A monolithic chain runs all four in one node under one validator set. The modular thesis says the couplings between those jobs - not the jobs themselves - are the scaling bottleneck: cut them selectively and each piece can scale on its own economics. This page is the architecture-level view: what each split buys, what it breaks, and who has to verify what. The mechanics live elsewhere - [Data Availability](./data-availability.md) owns sampling and erasure-coding math, and [ZK Rollups](./zk-rollups.md) / [Optimistic Rollups](./optimistic-rollups.md) own proof systems.

## Four Jobs, One Meter: What Monolithic Chains Couple

In a monolithic design the four functions share three resources, and each shared resource is a scaling ceiling:

- **One gas meter.** Compute and data are priced in the same unit (the EVM charges 16 gas per nonzero calldata byte out of the same block gas cap), so a chain cannot make data cheap without also making computation cheap, and vice versa. [EVM Internals](./evm-internals.md) shows how deep this meter runs.
- **One re-execution model.** Every full node re-executes every transaction to check validity, so throughput is capped by the *slowest honest node*, not by aggregate hardware.
- **One validator set.** Consensus security, data custody, and execution integrity all ride on the same stakers/miners with the same hardware profile.

| Function | Scarce resource it consumes | Constraint if scaled alone |
|---|---|---|
| Consensus | signatures to verify per block | protocol/slot time limits |
| Data availability | bytes each node must receive | bandwidth of light clients |
| Execution | compute per node | single-core-ish EVM semantics |
| Settlement | state growth from disputes/bridges | state size on every node |

## The Two Stacks

```text
          MONOLITHIC: one node, one meter
+------------------------------------------------------+
|  users                                               |
|    |                                                 |
|    v                                                 |
|  [ execution ]   state transition; one gas meter     |
|    |             prices BOTH compute and bytes       |
|    v                                                 |
|  [ settlement ]  disputes + bridges (usually fused   |
|    |             with execution above)               |
|    v                                                 |
|  [ consensus ]   one validator set orders blocks     |
|    |                                                 |
|    v                                                 |
|  [ data avail. ] every full node stores every byte   |
+------------------------------------------------------+

          MODULAR: functions distributed by contract
+---------------------+        +---------------------------+
| execution layer     |        | consensus + DA layer      |
| (rollup: own VM,    |  roots | (Ethereum blobs, Celestia)|
|  own fee market)    |=======>| orders txs; guarantees    |
|                     |        | bytes are retrievable     |
+---------------------+        +---------------------------+
          |       settlement: where disputes resolve   ^
          +------- and cross-rollup transfers anchor---+
```

The settlement box is the contested one. On Ethereum it stays on the L1 (rollups post state roots there); Celestia's "sovereign rollup" pushes settlement into the rollup itself, using the DA layer purely for ordering and bytes; shared-sequencing designs add a middleman that orders for many rollups at once. Each placement changes the trust model, which is why "modular" is a family of architectures, not one design.

## The Splits, and What Each Buys

| Split | Name | What it buys | What it costs |
|---|---|---|---|
| Execution out of settlement+consensus+DA | rollup | own VM, own fee market, throughput uncoupled from L1 node specs | sequencer liveness, bridge/proof machinery (see rollup pages) |
| Data out of execution+consensus | blob DA / danksharding | header stays small while bytes scale; consensus verifies commitments, not payloads | retrievability must be re-established by sampling ([Data Availability](./data-availability.md)) |
| Settlement relocated | sovereign rollup / shared settlement | native interoperability between rollups, no L1 bridge queues | least mature option; finality now depends on rollup governance |
| Sequencing decoupled | shared sequencer | atomic cross-rollup composability | new MEV and censorship trust party |

## Who Verifies What

The interview-grade question about modular stacks is not "how do they scale" but "who has to do what work to be convinced" - and where each split moves that burden:

| Participant | Re-executes? | Checks data presence? | Residual trust |
|---|---|---|---|
| Monolithic full node | yes, everything | yes (has all bytes) | none beyond consensus |
| Monolithic light client | no | headers only - *not* presence | committee/validator honesty |
| DA-layer sampling light client | no | samples random shares | withholding succeeds only with negligible odds ([Data Availability](./data-availability.md)) |
| Rollup node | rollup txs, locally | yes, reads DA layer | DA layer + sequencer liveness |
| Rollup light client, validity proof | no | verifies proof vs posted state | proof system soundness |
| Rollup light client, fraud proof | only disputed transitions | needs DA during challenge window | at least one honest watcher + data published in time |

Two structural readings of that table. First, modularization *redistributes* verification but never deletes it: execution moves off the consensus path, yet someone (disputer, prover, sampler) still performs each original check. Second, the fraud-proof row is the load-bearing one: an optimistic system is only as trustless as its ability to fetch challenge data, which is why data availability is the first dependency auditors check (see [Optimistic Rollups](./optimistic-rollups.md) for the 7-day window this feeds).

## Security Inheritance: What a Rollup Actually Inherits

A rollup inherits from its settlement+consensus+DA base exactly three things: resistance to reordering (consensus finality), a place where disputes resolve (settlement), and a guarantee that posted data can be retrieved (DA). Everything else is the rollup's own problem, and each departure from the base stack replaces an inherited guarantee with a newer, weaker one:

- **DA moved off the base chain** (validiums, external DA committees): retrieval now rests on the committee/quorum rather than base-layer consensus. EigenDA, for example, disperses erasure-coded data to EigenLayer-restaked operators who sign attestations backed by slashing - the security unit is restaked stake, not base-layer validators.
- **Sequencing centralized without an escape hatch**: a rollup with centralized sequencing but no forced-inclusion path inherits a censorship risk that no proof system can paper over; with a good escape hatch, censorship is temporary by construction.
- **Proof system choice**: validity proofs inherit state correctness immediately but depend on soundness and liveness of provers; fraud proofs inherit correctness probabilistically, after a challenge window, and only if watchers exist (rows above).

The economic corollary: a modular stack has *two* security budgets instead of one - the base layer's staking budget and the DA market's fee budget - and rollup assurance is the composition. L2Beat's risk/stage framework exists precisely because the composition varies per rollup; it tracked 70+ rollups carrying tens of billions of dollars in value secured during 2026 (figures as reported by L2Beat; they move daily), and the spread of risk labels across that population is the empirical evidence that "modular" is not automatically "inherits everything".

## Block-Space Economics: A Two-Meter Model

The splits ultimately show up as a change in *what you bill for*. The runnable model below contrasts a monolithic chain (one gas meter, one cap) with a modular stack (separate exec and DA meters). It is a **model, not a measurement** - flat fee markets, no MEV, no proof amortization; prices are stated assumptions, in the neighborhood of post-4844 Ethereum (6-blob target set by Pectra, ~128 KiB blobs; blob-parameter-only forks adjust these over time).

```python
# Block-space economics: monolithic gas cap vs modular exec + DA split.
# MODEL, not measurement. Stated assumptions:
#   * Monolithic: ONE gas meter prices compute and data together
#     (EVM-style: 16 gas per nonzero calldata byte), block cap G.
#   * Modular: execution meters ops only at its own (cheaper) gas
#     price; data is billed by the DA layer per byte, blob-priced.
#   * Flat fee markets; no MEV, no proof amortization, no fixed costs.
#   * DA budget = 6 blobs/block x 128 KiB (post-Pectra blob target).

G1   = 30_000_000          # monolithic block gas cap (gas)
P1   = 20e-6               # monolithic price, $ per gas
P2   = 0.05e-6             # modular exec price, $ per L2 gas
BLOB = 131_072             # bytes per blob (4096 x 32-byte elements)
C_BLOB = 8.00              # assumed DA price, $ per blob
D    = C_BLOB / BLOB       # modular DA price, $ per byte
DA_BUDGET = 6 * BLOB       # modular per-block byte budget

#             name                exec gas   bytes
WORKLOADS = [("AMM swap",          120_000,    180),
             ("batched game tick",  25_000,  4_096)]

print(f"prices: L1 ${P1*1e6:.2f}/Mgas | L2 ${P2*1e6:.3f}/Mgas | "
      f"DA ${D*1024:.3f}/KiB (${C_BLOB:.2f}/blob)")
print("byte/compute break-even (bytes per exec-gas where data cost = compute cost):")
print(f"  monolithic  16 gas/byte  -> {1/16:.4f} B/gas")
print(f"  modular     P2/D         -> {P2/D:.6f} B/gas")
print()
for name, g, b in WORKLOADS:
    mono = (g + 16 * b) * P1
    mod  = g * P2 + b * D
    d_star = ((g + 16 * b) * P1 - g * P2) / b * BLOB
    print(f"{name}: {g:,} gas, {b:,} bytes")
    print(f"  monolithic ${mono:.4f}/tx (data = {16*b*P1/mono:5.1%})"
          f"   modular ${mod:.4f}/tx (data = {b*D/mod:5.1%})")
    print(f"  modular stays cheaper iff blob price < ${d_star:,.2f}/blob")
print()
print("per-block capacity at a 9:1 swap-to-tick mix:")
gas_c, gas_d = 120_000 + 16 * 180, 25_000 + 16 * 4_096
k = G1 // (9 * gas_c + gas_d)
m = DA_BUDGET // (9 * 180 + 4_096)
print(f"  monolithic {k*9:4d} swaps + {k:3d} ticks = {k*10} txs (gas-capped at {G1:,})")
print(f"  modular    {m*9:4d} swaps + {m:3d} ticks = {m*10} txs (DA-capped at {DA_BUDGET:,} B)")
```

Real output from the script above:

```text
prices: L1 $20.00/Mgas | L2 $0.050/Mgas | DA $0.062/KiB ($8.00/blob)
byte/compute break-even (bytes per exec-gas where data cost = compute cost):
  monolithic  16 gas/byte  -> 0.0625 B/gas
  modular     P2/D         -> 0.000819 B/gas

AMM swap: 120,000 gas, 180 bytes
  monolithic $2.4576/tx (data =  2.3%)   modular $0.0170/tx (data = 64.7%)
  modular stays cheaper iff blob price < $1,785.20/blob
batched game tick: 25,000 gas, 4,096 bytes
  monolithic $1.8107/tx (data = 72.4%)   modular $0.2512/tx (data = 99.5%)
  modular stays cheaper iff blob price < $57.90/blob

per-block capacity at a 9:1 swap-to-tick mix:
  monolithic  225 swaps +  25 ticks = 250 txs (gas-capped at 30,000,000)
  modular    1233 swaps + 137 ticks = 1370 txs (DA-capped at 786,432 B)
```

Reading the numbers as an architect:

- **Execution got cheap, data did not.** In the model exec is 400x cheaper per unit on the modular stack (`P1/P2`) while bytes are only ~5.2x cheaper (`16*P1/D`). The byte/compute break-even therefore collapses from 0.0625 to 0.000819 B/gas: on a rollup, almost any transaction is *data-dominated*, which is exactly why blob throughput (not EVM speed) is the binding constraint of post-4844 Ethereum.
- **The break-even blob prices are the honest version of "rollups are always cheaper"**: they hold only below $1,785/blob for the compute-heavy swap and below $57.90/blob for the data-heavy tick. Blob fees have transiently spiked into the tens of dollars during demand bursts, so the data-heavy gap can briefly close - the architecture does not repeal supply and demand, it just re-prices the scarce resource separately.
- **Capacity is decoupled from price.** The monolithic chain moves 250 mixed txs/block no matter how much users pay; the modular stack moves 1,370 at the mix, and its two dials (blob count, exec throughput) can now be turned independently.

## Reference Architectures Compared

| Stack | Consensus + DA home | Execution home | Settlement | Inheritance model |
|---|---|---|---|---|
| Ethereum (rollup-centric roadmap) | L1 + blob market | rollups (zk + optimistic) | L1 contracts | consensus, DA, settlement all inherited |
| Celestia | dedicated DA chain | sovereign rollups | inside each rollup | ordering + DA inherited; execution/settlement self-owned |
| Avail | dedicated DA chain, KZG commitments | rollups/validiums above it | rollup-dependent | DA inherited with validity-proof light clients |
| EigenDA | restaked committee (not a chain) | rollups/validiums above it | usually Ethereum | DA from slashed stake, not consensus; validium-style trust |
| Solana | one integrated chain | same layer, parallel exec | fused | the monolithic counter-thesis: one fee market, no bridges |

## Design Questions

- **Which single coupling, if removed, most increases throughput - and why is it DA, not execution?** Execution re-execution is checkable by few (proofs), but every consumer needs the bytes; making bytes retrievable without every node storing them is the only split that relaxes the slowest-node ceiling.
- **A rollup moves DA to EigenDA. What three inherited properties change?** Retrieval guarantee (restaked quorum instead of base consensus), fee market (separate DA pricing), and challenge safety (fraud proofs now need the committee to actually hand over data).
- **Why do sovereign rollups make bridging easier but auditing harder?** Settlement inside the rollup removes the L1 bridge queue, but there is no external contract whose guarantees you can read; you audit the rollup's own fork-choice rules.
- **At what blob price does the modular stack lose its cost advantage for data-heavy apps?** Roughly the break-even in the model above (tens of dollars per blob at these assumptions) - compute-heavy apps keep the advantage across any plausible DA price.

## Cross-References

- [Data Availability](./data-availability.md) - sampling math, erasure coding, Celestia/EIP-4844 pipeline details
- [ZK Rollups](./zk-rollups.md) - validity-proof execution layer; where settlement anchors on L1
- [Optimistic Rollups](./optimistic-rollups.md) - fraud-proof model and the challenge window this page's DA rows feed
- [EVM Internals](./evm-internals.md) - the monolithic gas meter the model's L1 side abstracts

## References

- [Celestia Documentation - How Celestia Works: the Data Availability Layer](https://docs.celestia.org/learn/how-celestia-works/data-availability-layer) - DA-as-a-minimal-chain design and sovereign-rollup framing (docs.celestia.org, probed 200)
- [Ethereum.org - Roadmap: Scaling](https://ethereum.org/en/roadmap/scaling/) - the rollup-centric scaling roadmap as maintained by the foundation (probed 200)
- [Vitalik Buterin - A Rollup-Centric Ethereum Roadmap (EthMagicians, Oct 2020)](https://ethereum-magicians.org/t/a-rollup-centric-ethereum-roadmap/4698) - the post that named the strategy (probed 200)
- [Al-Bassam, Sonnino, Buterin, Khoffi - Fraud and Data Availability Proofs](https://arxiv.org/abs/1809.09044) - foundational paper; published in Financial Cryptography 2021 workshops, Springer LNCS 12675; arXiv version probed 200
- [EigenDA Documentation - Overview](https://docs.eigencloud.xyz/eigenda/core-concepts/overview) - restaked DA with KZG commitments and disperser attestations; note: site returns 403 to curl, existence verified via search indexing (EigenDA docs moved from docs.eigenlayer.xyz to docs.eigencloud.xyz)
- [Avail Documentation](https://docs.availproject.org/) - DA layer with KZG commitments and light-client network (probed 200)
- [L2Beat - Layer 2 Summary](https://l2beat.com/layer2s/summary) - rollup population, risk/stage ratings, and TVS figures quoted above as reported (probed 200)
- [Vitalik Buterin - An Incomplete Guide to Rollups](https://vitalik.eth.limo/general/2021/01/05/rollup.html) - the execution/settlement/DA decomposition this page builds on (probed 200)
