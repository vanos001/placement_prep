# Stateless Clients: Verkle Witnesses and the End of State Bloat

Ethereum's execution layer has a structural coupling: to validate a block honestly, you need the entire world state on disk, because a single transaction can read or write any account, any storage slot, any byte of contract code. State only grows, so the hardware floor for full validation rises every year -- the quiet centralization engine of an otherwise permissionless system. The stateless-client proposal breaks the coupling by moving state data *into the block*: every block ships with a **witness**, the minimal proof material a validator needs to re-execute the block against zero stored state. The companion page [Verkle Trees](./verkle-trees.md) covers the tree math that makes witnesses small enough to ship (vector commitments, KZG, stems and chunks); this page covers the architecture around it: why full nodes hold state in the first place, what a witness contains, the verification flow, weak versus strong statelessness, the state-expiry pairing, the gas-model restructuring that pays for witness bandwidth, and what it all means for light clients.

## Why Every Validator Carries the Whole State

The root cause is the account model. A Bitcoin transaction *names its inputs* -- the UTXOs it spends -- so validation is a lookup of a few dozen explicitly referenced items. An Ethereum transaction names nothing: `SLOAD` can hit any slot of any contract, `CALL` can reach any account, and code executes dynamically. Two consequences follow:

- **Execution is random access over the whole state.** The EVM is defined against the world state trie; without it you cannot even compute a transaction receipt, let alone verify the post-state root in the block header.
- **Every full node must therefore be a stateful node.** There is no purely computational validation path, only computational-plus-storage. [Ethereum Internals](./ethereum-internals.md) sketches the resulting scale problem; the numbers on ethereum.org's roadmap page are blunt: a fast 2TB SSD is recommended for a full node, unpruned nodes grow at roughly 14 GB/week, and archive nodes storing everything since genesis were already approaching 12 TB by early 2023 -- and the state itself (the part you cannot prune and still validate) grows monotonically.

State size is not just a disk bill. It drives initial-sync time (snap sync must download and verify trie chunks), it makes state access a denial-of-service surface (the repricing lineage EIP-150 -> EIP-1884 -> EIP-2929, documented in [EVM Internals](./evm-internals.md), exists because underpriced trie access nearly froze mainnet in 2016), and it prices out home stakers. The pre-history of statelessness is a series of attempts to *declare* access patterns instead of hiding them: EIP-2930 transaction access lists, EIP-2929 warm/cold accounting. Stateless clients finish the job by making the declaration complete and provable.

## The Witness Contract

A **witness** is the per-block bundle of proof material that lets a validator check every state transition the block performs without holding any state. For each state item the block touches, the witness carries the item plus its proof of membership (or non-membership) under the block's pre-state root:

- account **basic data** (nonce, balance, code hash) and its proof;
- the specific **storage leaves** (slots) read or written, with proofs;
- the **code chunks** executed -- under the post-verkle key layout, code is stored as 32-byte chunks of the account's stem vector, so running a contract means proving the chunks you jump through;
- **non-inclusion proofs** for accounts/slots the block creates or that must be shown empty (creation rules such as EIP-684's collision checks depend on absence).

The verification flow inverts today's roles:

```text
  today (stateful validation)                 stateless validation
  ---------------------------                 --------------------------------
  builder: holds state, makes block           builder: holds state, makes block
                                              + derives WITNESS for all touches
  validator: holds state, executes            validator: holds NOTHING,
  against local DB, compares                     re-executes using witness items,
  header state root                              recomputes post-state root,
                                                 compares header state root

  validation cost  ~  f(state size, block)    validation cost  ~  f(witness size, block)
  hardware floor grows with chain age         hardware floor: a laptop, or a phone
```

Two properties of this contract are easy to miss. First, it is a *trust shift*, not a trust elimination: execution verification becomes stateless, but witness *availability* becomes a liveness dependency -- a block without a complete witness is unverifiable, so whoever assembles blocks (in practice, builders under proposer-builder separation) gains a new gatekeeping role. Second, the witness is ephemeral: it validates one block and is discarded, so witness traffic is pure recurring bandwidth. Both points shape the rest of the design.

## Weak vs Strong Statelessness

| Property | Weak statelessness | Strong statelessness |
|----------|--------------------|----------------------|
| Who holds full state | block builders/proposers only | nobody; even builders rebuild from witnesses |
| Who generates witnesses | specialized stateful builders | transaction senders, via relays/providers |
| Transaction format | unchanged | must attach per-tx witness fragments |
| Mempool impact | none | stale-witness invalidation on state churn |
| UX burden | none | wallets need state-provider infrastructure |
| Prerequisite | verkle/binary tree + PBS | weak statelessness first |
| Ethereum roadmap status | the targeted milestone (per ethereum.org roadmap) | research direction |

Ethereum targets the weak variant. ethereum.org's statelessness roadmap page (updated June 2026) defines it directly: statelessness "puts the responsibility for state storage onto block proposers, while all other nodes on the network verify blocks without storing the full state data," noting that proposing requires full state while verifying requires none, and that proposer-builder separation lets builders be the specialized, stateful machines. The infrastructure pieces for this are moving: EIP-7732 (enshrined PBS) and EIP-7928 (Block-Level Access Lists) both sit in the scheduled-for-inclusion list of the Glamsterdam meta-EIP (EIP-7773, Review). BALs deserve emphasis for systems engineers: the block itself declares every state location it accesses plus post-transaction state diffs, which turns witness checking into a declarative comparison, unlocks parallel execution, and removes the last implicit access information from execution. Strong statelessness -- where even block production needs no stored state -- remains a research direction; its hard problems are economic and infrastructural (who serves users' witnesses, at what price, with what censorship properties), not cryptographic.

## State Expiry: The Other Half of the Deal

Witnesses shrink *proofs*, not *state* -- a stateless network still replicates the full state on every builder, and dormant accounts from 2016 still live in every stateful copy. Capping state growth requires expiry: state untouched for a lease period drops out of the active tree and moves to a cheaper "residual" tier, and is resurrected later by re-inserting it together with a witness proving it was not tampered with in the meantime. Because resurrection relies on witness-verified re-insertion, expiry and statelessness are a package: neither is fully useful alone. Concretely, EIP-7736 (leaf-level state expiry in verkle trees, *Stagnant*) expires per-stem extension trees that have not been touched within the window, and the binary-tree replacement EIP-7864 lists state-expiry among its design goals.

The second half of the pairing is pricing. If creating permanent state costs almost nothing, users will keep doing it, and expiry windows become griefing surfaces (reactivation spam). That is the motivation for the new generation of state-growth pricing: EIP-8037 (*Review*) re-meters state creation in its own dimension, targeting an average state growth of 120 GiB/year at a 150M gas limit, with a cost-per-state-byte (CPSB) parameter of 1530 gas and 120 state bytes charged per new account. Do not confuse any of this with *history* expiry: EIP-4444 (*Draft*) bounds old blocks and receipts, which are needed for data retrieval but not for validation -- state is the resource that blocks validation itself.

## Pricing the State: Gas Model Restructuring

Today's gas schedule prices the *latency* of state access (cold vs warm, EIP-2929) but badly underprices *permanence*: `SSTORE` from zero to nonzero costs 20,000 gas for ~32+ bytes of state kept alive by every future stateful node, and a fresh account under `CREATE` adds 25,000 gas -- around 1,000 gas per permanent byte is far cheaper than the calldata a user would pay to merely *mention* those bytes (16 gas/nonzero-byte). Under statelessness this mismatch becomes acute, because every byte of created state also becomes witness bytes in every subsequent block that touches it. The gas model must therefore bill for proof material directly. The drafted design is EIP-4762 ("changes the gas schedule to reflect the costs of creating a witness"), whose accounting replaces per-storage-op cold/warm costs with **witness-chunk accounting**:

| EIP-4762 constant (Draft) | Value | What it bills |
|---------------------------|-------|---------------|
| `WITNESS_BRANCH_COST` | 1900 | first access into a new witness branch/subtree |
| `WITNESS_CHUNK_COST` | 200 | each 32-byte chunk accessed (replaces cold/warm split) |
| `SUBTREE_EDIT_COST` | 3000 | first edit within a new subtree |
| `CHUNK_EDIT_COST` | 500 | writing to a new chunk |
| `CHUNK_FILL_COST` | 6200 | filling an empty chunk (state creation path) |

Note what this does to incentives: `SLOAD` and `SSTORE` stop having privileged cold/warm tiers of their own and instead pay for the proof chunks they force the builder to include; contract deploys pay per code chunk emitted; and the draft collapses `CREATE`/`CREATE2` to 1,000 gas because state creation is billed through the chunk/edit costs instead. EIP-8037 goes further with multidimensional metering -- a separate "state gas" dimension so that a block cannot fill itself with cheap computation and expensive state at the same average price -- plus per-byte pricing calibrated to the 120 GiB/year growth target. The economics read: state goes from a nearly free annuity to a metered, front-loaded rental.

## Light Clients and the SNARK Endgame

Today's "light clients" (sync-committee designs like Helios) verify *consensus* -- they check validator signatures cheaply -- but still trust a remote RPC for *execution*: they cannot check that a balance or token supply is real. Witness verification changes the calculus completely: a device with zero stored state re-executes the block from witnesses and independently checks the state root, so a phone-class wallet reaches full execution verification for the cost of downloading roughly a hundred-ish KiB per block (model below). The open infrastructure question shifts from storage to distribution: who gossips witnesses to every phone? Portal-network-style distributed state providers are the proposed answer, and the reliability of witness delivery becomes a liveness property of the whole system.

The endgame is to stop shipping per-access proofs at all. The drafted binary-tree design EIP-7864 is explicitly motivated by "SNARK friendliness and Post-Quantum security": hash-based arity-2 trees are cheap inside a STARK, so the witness collapses into one per-block proof of the entire state transition (order of a hundred KiB, regardless of transaction count), and the pairing-based trusted-setup assumption disappears from the state layer. This connects directly to [Data Availability](./data-availability.md) (the other KZG consumer) and to [ZK Rollups](./zk-rollups.md) (the same proof-of-state-transition pattern, generalized to native rollups). The research bet: prove the state transition, ship one proof, keep every validator stateless and post-quantum.

## Roadmap Status (August 2026)

Hedged, interview-safe facts -- timelines beyond 2026 are speculative:

- **Verkle state is not live.** EIP-6800 (unified verkle tree) is *Stagnant*; EIP-4762 (witness gas) is *Draft*; EIP-7736 (leaf-level expiry) is *Stagnant*.
- **The center of gravity moved to binary tries.** EIP-7864 (*Draft*) proposes replacing the hexary Patricia state with a unified binary tree; benchmarking published in March 2026 reports the binary trie at roughly 1.7x slower reads and 2.5x slower writes than production MPT per storage operation -- a real but bounded gap, shrinking under active optimization.
- **State-growth pricing is in active review.** EIP-8037 (state creation cost increase) and EIP-7928 (BALs) are both *Review*; BALs and enshrined PBS (EIP-7732) are listed as scheduled for Glamsterdam per EIP-7773 (*Review*) -- schedules can and do slip.
- **Fusaka shipped December 3, 2025** (EIP-7607, *Final*; PeerDAS via EIP-7594), which scaled blob data availability but did not touch the state tree.
- **History expiry remains separate and open** (EIP-4444, *Draft*); ethereum.org's roadmap page (updated June 2026) still narrates verkle-based weak statelessness as the destination, while the research conversation has shifted toward binary trees plus SNARK aggregation as the likely route.

## A Witness-Budget Model

The model below sizes the bill a 150-transaction block imposes on every validator, for three witness regimes, under three transaction mixes. Per-tx state footprints (accounts, storage slots, code chunks) come from the class table; account reuse is modeled by drawing from a 60,000-address active pool. Constants are the ones justified in [Verkle Trees](./verkle-trees.md) (~3.5 KiB per MPT access at mainnet scale; ~96 B per verkle stem, ~48 B per opening), with binary-trie access modeled as sibling hashes along the path. This is a *model* for order-of-magnitude reasoning, not a measurement.

```python
# Witness-budget model (a model with stated assumptions, NOT a measurement).
# Question: what does carrying the state inside the block cost, per block and
# per year, for different witness regimes -- vs storing the state on disk?
#
# Model constants (see blockchain/verkle-trees.md for the tree-math derivation):
#   MPT_ACCESS   3584 B per independent trie access (3.5 KiB/access,
#                mainnet-scale MPT extrapolation; multiproof sharing can lower it)
#   VERKLE_STEM    96 B per unique account stem touched (commitment material)
#   VERKLE_OPEN    48 B per touched chunk (compressed BLS12-381 opening)
#   BIN_ACC_PATH  768 B per unique account (24 shared levels x 32 B sibling hash,
#                EIP-7864-style binary trie, hash-based, no aggregation)
#   BIN_SUB_PATH  256 B per extra slot/code chunk (8 suffix levels x 32 B)
#   SNARK_BLOCK  120 KiB fixed per block (order-of-magnitude aggregated proof)
#
# Tx-class state footprint: (accounts, storage slots, code chunks, new accounts).
# Slot/chunk counts are drawn from ranges to model per-tx variance.
import random

SLOTS_PER_YEAR = 365 * 24 * 300            # 12 s slots -> 1 witness/slot
MPT_ACCESS, V_STEM, V_OPEN = 3584, 96, 48
BIN_ACC, BIN_SUB, SNARK_BLOCK = 768, 256, 120 * 1024

CLASSES = {
    # class: (accounts touched, slot range, chunk range, new accounts)
    "transfer": (2, (0, 0), (0, 0), 0),
    "erc20":    (3, (1, 4), (1, 3), 0),
    "swap":     (5, (4, 13), (15, 44), 0),
    "deploy":   (1, (1, 2), (20, 32), 1),
}
MIXES = {
    "transfers-heavy": {"transfer": 85, "erc20": 10, "swap": 5, "deploy": 0},
    "mainnet-2026":    {"transfer": 55, "erc20": 28, "swap": 15, "deploy": 2},
    "defi-heavy":      {"transfer": 35, "erc20": 40, "swap": 22, "deploy": 3},
}

def block_footprint(mix, n_tx=150, seed=51):
    rng = random.Random(seed)
    names = sorted(mix)
    weights = [mix[n] for n in names]
    accounts, slots, chunks, new = set(), 0, 0, 0
    for _ in range(n_tx):
        cls = rng.choices(names, weights)[0]
        acc, (s0, s1), (c0, c1), na = CLASSES[cls]
        accounts.update(rng.randrange(60_000) for _ in range(acc))  # pool reuse
        slots += rng.randint(s0, s1)
        chunks += rng.randint(c0, c1)
        new += na
    return len(accounts), slots, chunks, new

def witness_bytes(accounts, slots, chunks):
    mpt = (accounts + slots + chunks) * MPT_ACCESS
    verkle = accounts * V_STEM + (slots + chunks) * V_OPEN
    binary = accounts * BIN_ACC + (slots + chunks) * BIN_SUB
    return mpt, verkle, binary

print(f"model: 150-tx blocks, {SLOTS_PER_YEAR:,} slots/yr, 60k-address active pool")
hdr = (f"{'mix':>15} | {'acc':>4} {'slot':>5} {'chunk':>5} |"
       f" {'MPT MB':>7} {'verkle KB':>9} {'bintrie KB':>10} {'+STARK KB':>9}")
print(hdr)
print("-" * len(hdr))
per_year = {}
for mix in MIXES:
    acc, slots, chunks, new = block_footprint(MIXES[mix])
    mpt, verkle, binary = witness_bytes(acc, slots, chunks)
    per_year[mix] = (verkle, binary, mpt)
    print(f"{mix:>15} | {acc:>4} {slots:>5} {chunks:>5} |"
          f" {mpt/1e6:>7.2f} {verkle/1024:>9.1f} {binary/1024:>10.1f}"
          f" {SNARK_BLOCK/1024:>9.0f}")

print()
print("bandwidth/yr if every slot ships a witness (GiB/yr):")
print(f"{'mix':>15} | {'MPT TiB':>8} | {'verkle GiB':>10} | {'bintrie GiB':>11} |"
      f" {'STARK GiB':>9} | {'state growth':>20}")
print("-" * 96)
STATE_GROWTH = "120 GiB/yr (EIP-8037 ref)"
for mix, (verkle, binary, mpt) in sorted(per_year.items()):
    v_y = verkle * SLOTS_PER_YEAR
    b_y = binary * SLOTS_PER_YEAR
    m_y = mpt * SLOTS_PER_YEAR
    s_y = SNARK_BLOCK * SLOTS_PER_YEAR
    print(f"{mix:>15} | {m_y/2**40:>8.1f} | {v_y/2**30:>10.1f} | {b_y/2**30:>11.1f} |"
          f" {s_y/2**30:>9.1f} | {STATE_GROWTH:>20}")
print()
print("reading: stateless verification trades a disk problem (state growth, GiB/yr)")
print("for a bandwidth problem (witness bytes/slot); naive MPT witnesses are not")
print("shippable, unaggregated binary-trie witnesses are marginal at high gas, and")
print("per-block aggregation (STARK) or KZG-sized verkle witnesses are what fit.")
```

Real output:

```text
model: 150-tx blocks, 2,628,000 slots/yr, 60k-address active pool
            mix |  acc  slot chunk |  MPT MB verkle KB bintrie KB +STARK KB
---------------------------------------------------------------------------
transfers-heavy |  336   102   198 |    2.28      45.6      327.0       120
   mainnet-2026 |  423   360  1016 |    6.45     104.2      661.2       120
     defi-heavy |  446   451  1311 |    7.91     124.4      775.0       120

bandwidth/yr if every slot ships a witness (GiB/yr):
            mix |  MPT TiB | verkle GiB | bintrie GiB | STARK GiB |         state growth
------------------------------------------------------------------------------------------------
     defi-heavy |     18.9 |      311.8 |      1942.3 |     300.8 | 120 GiB/yr (EIP-8037 ref)
   mainnet-2026 |     15.4 |      261.0 |      1657.3 |     300.8 | 120 GiB/yr (EIP-8037 ref)
transfers-heavy |      5.4 |      114.2 |       819.5 |     300.8 | 120 GiB/yr (EIP-8037 ref)

reading: stateless verification trades a disk problem (state growth, GiB/yr)
for a bandwidth problem (witness bytes/slot); naive MPT witnesses are not
shippable, unaggregated binary-trie witnesses are marginal at high gas, and
per-block aggregation (STARK) or KZG-sized verkle witnesses are what fit.
```

Three readings worth carrying into an interview. First, the stateless transition converts a *storage* problem (state grows ~120 GiB/year under the EIP-8037 reference scenario, replicated on every stateful node) into a *bandwidth* problem (witness bytes per slot, replicated on every validator): the per-block verkle witness of ~50-125 KiB is comfortably shippable, while naive MPT witnesses measured in whole megabytes per block never were. Second, the unaggregated binary-trie column is the honest cost of the post-quantum-friendly path -- ~0.8-2 TiB/year of witness traffic in this model -- which is precisely why EIP-7864 pairs the hash-based tree with SNARK aggregation rather than shipping raw sibling-hash proofs. Third, the fixed STARK column shows the endgame's shape: witness cost becomes independent of transaction count, which means gas pricing (who pays for the per-block proof?) decouples from witness size (how big is it?) -- a fee-market redesign hiding inside a data-structure change. All numbers are model outputs under stated assumptions; multiproof sharing, witness compression, and realistic block access reuse can move the binary-trie and verkle columns substantially.

## Gotchas

- **"Stateless clients eliminate trust in block builders, right?"** No -- they eliminate *state storage* for validators, but witness completeness becomes a new liveness dependency on builders. This is exactly why enshrined PBS (EIP-7732) and BALs (EIP-7928) travel in the same fork package.
- **"Does statelessness shrink the state?"** Nothing here shrinks stored state; verkle witnesses shrink proofs, expiry shrinks state, and pricing (EIP-8037) slows growth. Keep the three levers separate.
- **"Why not just keep Merkle Patricia tries and eat big witnesses?"** Because witnesses recur every slot: multiply per-access proof cost by ~2.6M slots/year and the bandwidth bill dwarfs the disk bill it replaced -- see the model's MPT column.
- **"Are light clients today stateless?"** Sync-committee light clients (Helios-style) verify consensus and trust execution RPCs; witness verification is what adds full *execution* verification, and SNARKified transitions are what remove the remaining per-access proof traffic.

## Cross-References

- [Verkle Trees](./verkle-trees.md) -- the tree math behind witness sizes: vector commitments, KZG, stems, aggregation (not re-derived here)
- [EVM Internals](./evm-internals.md) -- current gas schedule, cold/warm accounting, `SELFDESTRUCT` transition rules that precede witness-based state
- [Ethereum Internals](./ethereum-internals.md) -- survey-level stateless-client summary and the state-size problem in context
- [Data Availability](./data-availability.md) -- the sibling KZG consumer: blobs, PeerDAS, sampling
- [ZK Rollups](./zk-rollups.md) -- proof-of-state-transition patterns that the stateless endgame adopts
- [Merkle Tree Synchronization](../distributed/advanced/merkle-sync.md) -- hash-tree proof mechanics without vector commitments

## References

- [ethereum.org -- Statelessness, state expiry and history expiry (roadmap)](https://ethereum.org/en/roadmap/statelessness/) -- official weak-statelessness definition; page last updated June 30, 2026
- [EIP-4762: Statelessness gas cost changes](https://eips.ethereum.org/EIPS/eip-4762) -- witness-branch/chunk gas accounting (Draft; constants quoted above)
- [EIP-8037: State Creation Gas Cost Increase](https://eips.ethereum.org/EIPS/eip-8037) -- CPSB, per-account state bytes, 120 GiB/year target (Review)
- [EIP-7864: Ethereum state using a unified binary tree](https://eips.ethereum.org/EIPS/eip-7864) -- the post-verkle binary-tree draft, with SNARK/post-quantum rationale (Draft)
- [EIP-7928: Block-Level Access Lists](https://eips.ethereum.org/EIPS/eip-7928) -- enforced block-level access declarations and post-tx diffs (Review)
- [EIP-7736: Leaf-level state expiry in verkle trees](https://eips.ethereum.org/EIPS/eip-7736) -- lease-based per-stem expiry design (Stagnant)
- [EIP-7773: Hardfork Meta - Glamsterdam](https://eips.ethereum.org/EIPS/eip-7773) -- scheduled EIPs incl. EIP-7732 (enshrined PBS) and EIP-7928 (Review)
- [EIP-7607: Hardfork Meta - Fusaka](https://eips.ethereum.org/EIPS/eip-7607) -- Fusaka inclusion list and December 3, 2025 mainnet activation (Final)
- [EIP-4444: Bound Historical Data in Execution Clients](https://eips.ethereum.org/EIPS/eip-4444) -- history expiry, distinct from state expiry (Draft)
- [Julian -- A Protocol Design View on Statelessness (ethresear.ch, April 2025)](https://ethresear.ch/t/a-protocol-design-view-on-statelessness/22060) -- design-space framing for stateless verification
- [CPerezz -- The Path Towards Binary Tries 2: MPT vs. BTree (ethresear.ch, March 2026)](https://ethresear.ch/t/the-path-towards-binary-tries-2-how-fast-is-the-binary-trie-today-mpt-vs-btree/24564) -- binary-trie performance benchmarks quoted above
- [Helios (a16z) -- Ethereum light client](https://github.com/a16z/helios) -- sync-committee-based client that trusts execution RPCs
- [go-verkle -- Ethereum's verkle tree implementation](https://github.com/ethereum/go-verkle) -- the implementation home of the drafted state tree
