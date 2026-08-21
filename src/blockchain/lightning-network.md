# Lightning Network

## Overview

The Lightning Network is a Layer 2 for Bitcoin that uses bidirectional payment channels to enable near-instant, low-fee Bitcoin transfers without committing every transaction to the base chain. It is not a rollup: there is no shared state root, no sequencer, no global consensus on L2. Instead, Lightning is a *network of pairwise payment channels* — a graph in which the vertices are Lightning nodes and the edges are on-chain Bitcoin UTXOs locked in 2-of-2 multisig.

The protocol was specified by Joseph Poon and Thaddeus Dryja in their January 2016 paper, "The Bitcoin Lightning Network: Scalable Off-Chain Instant Payments." The first production implementation (lnd from Lightning Labs) shipped mainnet in March 2018; today there are three interoperable implementations (lnd, Core Lightning from Blockstream, and Eclair from ACINQ) coordinated by the **BOLT** (Basis of Lightning Technology) specification.

This page covers the building blocks: payment channels, the commitment transaction and its in-channel penalty model, HTLCs as the routing primitive, the multi-hop atomic relay that makes Lightning a *network* rather than a single channel, the role of the Bitcoin base layer as the trust anchor, and the trade-offs versus other L2 designs.

## Payment Channels

A payment channel is, in its simplest form, two Bitcoin UTXOs (one from each participant) that have been combined into a single 2-of-2 multisig output on-chain. Neither party can move the funds alone. Off-chain, the two parties maintain a sequence of *commitment transactions* that re-allocate the multisig UTXO between them. The on-chain footprint is one open transaction and one close transaction, regardless of how many payments the channel carries.

```
                Single-payment-channel lifecycle

   Alice                       Bitcoin L1                    Bob
   -----                       ----------                    ---
   fund 1 BTC -----(P2MSH 2-of-2 UTXO)------ fund 1 BTC

       open transaction broadcast
       channel capacity = 2 BTC

       channel state #1 (off-chain, signed by both):
            Alice 1.0  |  Bob 1.0

   <- Alice pays 0.3 to Bob ->

       channel state #2 (off-chain, signed by both):
            Alice 0.7  |  Bob 1.3

   <- Bob pays 0.1 to Alice ->

       channel state #3 (off-chain, signed by both):
            Alice 0.8  |  Bob 1.2

       cooperative close: both sign a single
       on-chain tx paying 0.8 to Alice, 1.2 to Bob
```

The capacity of the channel (the total UTXO value) is fixed at channel open — Lightning does not allow a channel to be "topped up" without an on-chain transaction. (Splicing, ratified in BOLTs 782 and 862, lets you replace the channel's UTXO with a larger one atomically, but the on-chain footprint is still one transaction per splice.)

The non-trivial problem is **how to revoke a previous state**. If Alice and Bob have signed state #3 but Alice tries to broadcast the older state #2 (in which she held 0.7 instead of 0.8), she can profit by reverting the last payment. The penalty-transaction construction is what makes Lightning *trustless*.

## The Commitment Transaction

A Lightning commitment transaction is *not* a symmetric "both parties sign the same transaction" construction. It is **asymmetric**: each party holds a different commitment transaction for the same logical state. Each transaction pays the *other* party immediately and conditions payment to *oneself* on a time lock. This is the so-called **Decker-Wattenhofer** construction, refined in the Poon-Dryja paper.

For state *n*, Alice's commitment transaction (call it `C_A^N`) has this structure:

```
   C_A^n (signed by Bob, kept by Alice):

   input:  spends the 2-of-2 multisig funding UTXO
   output 1:  to Bob's_pubkey            [immediately spendable]
   output 2:  to Alice's_pubkey,
              CSV-delayed by `to_self_delay` blocks   [to_local]
   output 3..k:  HTLC outputs (one per in-flight payment)
```

Bob's commitment transaction for the same state *n* (`C_B^n`) is the mirror image:

```
   C_B^n (signed by Alice, kept by Bob):

   input:  spends the 2-of-2 multisig funding UTXO
   output 1:  to Alice's_pubkey            [immediately spendable]
   output 2:  to Bob's_pubkey,
              CSV-delayed by `to_self_delay` blocks   [to_local]
   output 3..k:  HTLC outputs (one per in-flight payment)
```

The asymmetry is the security-critical part: **if Alice broadcasts an old commitment `C_A^{n-1}` to the chain, Bob can spend Alice's delayed output 2 immediately, before Alice's time lock expires** — provided Bob holds the revocation secret that proves the old state was already revoked.

## The Penalty Transaction (Revoked States)

Each commitment has a *revocation key* `R^n` derived from two halves: a public half `R_pub^n` (known to both parties) and a private half `R_priv^n` (initially held only by the commitment owner). When the parties move from state *n* to state *n+1*, they exchange revocation secrets — Alice reveals her `R_priv^n` to Bob and vice versa. After this exchange, neither party can safely broadcast state *n* anymore, because the other party now holds the corresponding revocation secret and can steal all the funds.

The penalty transaction uses the revocation secret as follows:

```
   Alice broadcasts stale C_A^{n-1} on-chain.

   The transaction contains, in output 2, a script that allows spending:
     EITHER  (Alice's signature + wait to_self_delay blocks)  [normal]
     OR      (Bob's signature + R_priv^{n-1})                 [penalty]

   Bob watches the mempool. He sees C_A^{n-1} broadcast.
   He has R_priv^{n-1} (because Alice revoked this state when they
   moved to state n).

   Bob immediately broadcasts the penalty transaction:
     input:  C_A^{n-1}'s output 2 (the to_local, delayed output)
     output: to Bob's wallet key

   This sweep happens before Alice's CSV delay expires.
   Alice loses ALL her funds in the channel, not just the difference.
```

The economic design is severe on purpose: a cheating party loses the entire channel balance, not just the disputed amount. This makes the *attempted* fraud economically irrational even when the fraudulent amount is small.

The revocation model imposes a hard requirement on every Lightning node: it must **watch the chain continuously** for stale commitment transactions. Three patterns exist:

1. **Always-on watchtowers**: the node itself runs and watches the chain.
2. **Outsourced watchtowers**: a third party (the "watchtower" service) monitors on your behalf. The watchtower needs only a hash of each revoked commitment, so it cannot steal funds; it can only act on your behalf.
3. **Channel watchtower protocols**: BOLTs 651 (`watchtower`), 822 (`rendezvous`), and the Eltoo/Guide To Taproot Channels proposal simplify this for newer Lightning-Vault designs.

## HTLCs (Hashed Timelock Contracts)

A Hashed Timelock Contract is the atomic primitive that lets a payment *route* through multiple channels without trusting any intermediate node. An HTLC is an output (or off-chain conditional payment) of the form:

```
   HTLC(recipient, hash_preimage R, value v, timeout T):

   spendable IF
     recipient's signature AND preimage P such that SHA256(P) == R
   ELSE IF (timeout T has elapsed)
     sender's signature
```

The hash preimage `R` is the cryptographic "claim token": whoever knows `P` (the preimage) can claim the HTLC's funds. The timeout `T` lets the sender recover the funds if no one ever reveals `P`.

A Lightning payment is built on a chain of HTLCs across multiple channels. Consider a route `Alice -> Bob -> Carol -> Dave`, where Alice wants to pay Dave 1 BTC, but has no direct channel with Dave:

```
                       HTLC chain (simplified, no fees)

   1. Dave generates random preimage P, hashes it: R = SHA256(P).
      Dave sends R to Alice out-of-band (via the Lightning
      invoice/BOLT 11 format).

   2. Alice adds an HTLC to her channel with Bob:
        "Bob, I'll pay you 1.001 BTC if you reveal P such that
         SHA256(P) == R, within 40 blocks."
        (Alice -> Bob:  1.001 BTC, T = N+40 blocks)

   3. Bob adds an HTLC to his channel with Carol:
        "Carol, I'll pay you 1.0005 BTC if you reveal P such that
         SHA256(P) == R, within 30 blocks."
        (Bob -> Carol:  1.0005 BTC, T = N+30 blocks)

   4. Carol adds an HTLC to her channel with Dave:
        "Dave, I'll pay you 1 BTC if you reveal P such that
         SHA256(P) == R, within 20 blocks."
        (Carol -> Dave: 1 BTC, T = N+20 blocks)

   5. Dave knows P (he generated it). He reveals P to Carol,
      claiming the 1 BTC HTLC.

   6. Carol now knows P. She reveals P to Bob, claiming the
      1.0005 BTC HTLC.

   7. Bob now knows P. He reveals P to Alice, claiming the
      1.001 BTC HTLC.

   Net: Alice paid 1.001, Dave received 1.000, Bob netted +0.0005,
        Carol netted +0.0005 (skipping a hop for clarity).
```

The decrementing timeouts are critical: each upstream hop must have a *longer* timeout than the downstream hop. If Dave fails to reveal, Carol needs time to claw back her HTLC with Bob before Bob's HTLC with Alice times out. The standard "cltv_expiry_delta" (BOLT 7 parameter `cltv_expiry_delta`) is typically 6–144 blocks.

## Multi-Hop Routing

Routing is the hard problem of finding a path of channels with sufficient *directed capacity* from payer to payee. Unlike a packet-switched network where capacity is fungible, Lightning's capacity is *per-channel and directional*: a channel with 1 BTC on Alice's side and 0 on Bob's side can route Alice → Bob but not Bob → Alice.

The network uses source routing (the payer computes the full path), not hop-by-hop forwarding. The standard algorithm is **gossip-based pathfinding**: nodes broadcast their channel announcements (BOLT 7), and every node maintains a full network graph. The payer runs a constrained shortest-path search on the local graph.

```
   Lightning routing (BOLT 7 gossip + BOLT 4 onion packets)

   Payer                             Network                Payee
   -----                             -------                -----
   (1) Build local graph from
       gossip messages
       (channel_announcement,
        channel_update, node_announcement)
   (2) Run pathfinding:
        - filter channels by
          sufficient capacity and
          direction
        - apply fees
        - apply cltv_expiry_delta
        - apply min_htlc, max_htlc
        - prefer known-good routes
   (3) Construct an onion packet
       (Sphinx, BOLT 4): each hop
       sees only next hop + payload
       for that hop
   (4) Send update_add_htlc to
       first hop with the onion
                                                    (5) Forwarder
                                                        peels one
                                                        layer of the
                                                        onion, sees
                                                        next hop and
                                                        their HTLC
                                                        parameters
                                                    (6) Each
                                                        intermediate
                                                        forwards
                                                        update_add_htlc
                                                    (7) Final hop =
                                                        payee; reveals
                                                        preimage ->
                                                        update_fulfill_htlc
                                                        backwards
   (8) Payer receives
       update_fulfill_htlc
       -> payment settled
```

The Sphinx packet format (BOLT 4) is the cryptographic guarantee that intermediate nodes cannot learn their position in the path or the ultimate destination — each hop sees only the next hop, encrypted under its own key, with decoy "filler" bytes to keep the packet size constant.

The hard routing problems in 2024:

- **Pathfinding under uncertainty.** Channel balances are not public — a node knows only its own side's balance. A path may have the right *directed capacity* on paper but no actual available liquidity. Solutions: probing (sending small test payments to learn balances), Just-In-Time liquidity (JIT-Channel), and trampoline routing (BOLT 738), which moves pathfinding to trampoline nodes so the payer does not need a full graph.
- **Channel jamming attacks.** An attacker can lock up channel liquidity by sending many HTLCs that never resolve. The two variants — *liquidity* jamming (locks channel capacity) and * HTLC jamming (locks the limited slot count, default 483 per node) — are documented in the "Channel Jamming Mitigation" research from 2023.

## The Base Layer (Bitcoin)

Lightning's security model depends entirely on the Bitcoin L1. The L1 provides:

1. **Channel funding**: the multisig UTXO that anchors all off-chain state.
2. **Penalty enforcement**: the chain validates the revocation scripts that let a cheated party claw back funds.
3. **HTLC enforcement**: the chain enforces the time-locks and preimage conditions if a channel must unilaterally close mid-payment.
4. **Block timestamping**: provides the trusted clock for `cltv_expiry` (absolute time-locks) and `to_self_delay` (relative time-locks via `OP_CSV`).

Two L1 features that Lightning critically depends on:

- **CHECKSEQUENCEVERIFY (CSV, BIP 112)**: enables the `to_self_delay` relative time-lock in the commitment transaction's `to_local` output. Without CSV, you cannot make Alice's refund wait *N blocks after the commitment is broadcast*.
- **Segregated Witness (SegWit, BIP 141)**: solves transaction malleability, which is required because the commitment transaction's txid must be computable before it is broadcast (otherwise the funding UTXO cannot be referenced). Pre-SegWit, a third party could malleate the witness data and change the txid, breaking the off-chain construction.

Without these L1 upgrades (SegWit activated August 2017, CSV November 2016), Lightning cannot exist on Bitcoin. This is why the deployment of Lightning lagged the Poon-Dryja paper by two years — the L1 first needed to ship the prerequisites.

## Taproot Channels and Future L1 Improvements

The November 2021 Taproot upgrade (BIPs 340/341/342) opened the door to **Taproot Channels** (sometimes called Lightning-Taproot, or the Eltoo-style construction):

- **PTLCs (Point Time Lock Contracts)**: replace HTLCs with elliptic curve points instead of hashes. The advantage is size — a 32-byte point vs a 32-byte hash, but with no on-chain footprint when used with adaptor signatures. The practical benefit is that PTLCs do not have the quadratic on-chain cost growth that multi-hop HTLCs have when many channels must unilaterally close at once.
- **MuSig2 channels**: the funding UTXO is a key-spending path under a single BIP-340 key, indistinguishable on-chain from any other Taproot spend. This improves Lightning's privacy (channel opens and closes look like normal transactions) and reduces chain analysis leakage.
- **Eltoo (BOLTs 1191 / Guide-to-Taproot-Channels)**: a layer-2 protocol that removes the asymmetric penalty model entirely. State updates are signed by both parties with relative time-locks; only the latest state can be confirmed because earlier states have a longer time-lock. This eliminates the watchtower requirement, since old states are simply invalid on-chain, not penalised.

Eltoo is the long-term direction but requires a new opcode (`OP_TLV` or `OP_CHECKSIGFROMSTACK` family) that is not yet in Bitcoin's consensus rules. The Lightning community is discussing these via the "Guide to Taproot Channels" BOLT draft.

## Comparison to Other L2 Solutions

```
                              Lightning             Ethereum rollups
                              ---------             -----------------
  Topology                    P2P graph of          single global state
                              bilateral channels    with shared root
  L1 data model               UTXO lock +           state root + calldata/
                              spend                 blob commitment
  On-chain footprint          2 txs per channel     1 batch per L2 block
                              lifetime              (~1 per minute)
  Throughput per node         ~1K payments/sec      ~10K tx/sec across
                                                     all users
  Finality                    1 block (post-         minutes (ZK) /
                              confirmation),         7 days (optimistic)
                              on L2
  Privacy                     better than L1          weaker than L1 (all
                              (no per-transaction     txs in calldata/blobs
                              on-chain record)        are public)
  Failures                    per-channel:            global: sequencer
                              unilateral close       failure stalls all
  Trustless auditability       must run a node       anyone can verify
                              + watchtower           by reading L1
```

Lightning's design point is fundamentally different from rollups: it optimises for *small, frequent, peer-to-peer payments* with millisecond-level finality. Rollups optimise for *smart-contract execution* with global composability. Lightning cannot run a DEX; rollups cannot match Lightning's per-payment latency or fee (a Lightning payment settles in <1 second for ~1 satoshi of fee).

Other L2s that sit in between:

- **Bitcoin's Ark / Fedimint**: a custodial/semi-custodial L2 where a server holds coins and uses ecash-style Chaumian blind signatures for off-chain transfers. Cheaper than Lightning per transaction, but with weaker trust model.
- **State channels (Ethereum)**: the generalisation of Lightning to EVM. Used by L2s like Connext (now closed) and the Cards Network; niche compared to rollups because of state-size problems for general contracts.
- **Validium (zk rollup + off-chain data)**: similar to Lightning in that data availability is moved off-chain; different in that the proving system still ensures state correctness.

> **Interview Angle**: "Why doesn't Bitcoin just do rollups like Ethereum?" Two reasons. First, Bitcoin's scripting language is deliberately not Turing-complete — you cannot express an interactive fraud-proof game or a SNARK verifier in Bitcoin Script (the cost of a verifier is also higher because Bitcoin does not have a generic pairing precompile). Second, Bitcoin's culture and consensus rules are extremely conservative — activating SegWit and Taproot each took years of debate; a soft fork to enable ZK-friendly opcodes would take a decade. Lightning's design is exactly what you build when the L1 cannot change to support rollups.

## Interview Questions

### Q1: What happens if a Lightning node goes offline for a week?

It depends on whether the channel partner broadcasts a stale commitment in the meantime. If the offline node has a watchtower monitoring on its behalf, the watchtower can broadcast the penalty transaction if needed. If there is no watchtower, and the partner broadcasts a stale commitment, the offline node has only `to_self_delay` blocks (typically 144 = 24 hours) to come back online and broadcast the penalty. After that window, the partner's funds in the `to_local` output become spendable, and the cheater wins.

### Q2: Why does Lightning use source routing instead of hop-by-hop forwarding?

Two reasons. (1) **Privacy**: with hop-by-hop forwarding, every intermediate node learns the destination; source routing with onion packets (Sphinx) ensures each hop sees only the next hop. (2) **Atomicity**: the HTLC chain works only if the entire path commits simultaneously; with source routing, the payer constructs the entire path before sending, ensuring the timeouts decrement correctly along the route.

### Q3: How does the penalty mechanism scale to channels with thousands of state updates?

Each state update (a payment) requires exchanging a new commitment transaction and a revocation secret for the previous one. The revocation secrets are tiny (~32 bytes each); a node with 1000 open channels and 1000 payments per day per channel accumulates ~30 MB/month of revocation data. The bottleneck is not storage but the **computation and signature verification** for each update — every Lightning implementation uses batched signature verification and incremental state machine updates to sustain hundreds of payments per second per channel.

## References

- Joseph Poon, Thaddeus Dryja, "The Bitcoin Lightning Network: Scalable Off-Chain Instant Payments" (2016): https://lightning.network/lightning-network-paper.pdf
- BOLT Specifications (Basis of Lightning Technology): https://github.com/lightning/bolts
- BOLT 4 — Onion Routing: https://github.com/lightning/bolts/blob/master/04-onion-routing.md
- BOLT 7 — P2P Gossip: https://github.com/lightning/bolts/blob/master/07-routing-gossip.md
- Lightning Labs Developer Docs: https://docs.lightning.engineering/
- BIP 112 — CHECKSEQUENCEVERIFY: https://github.com/bitcoin/bips/blob/master/bip-0112.mediawiki
- BIP 141 — Segregated Witness: https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki
- Mastering the Lightning Network (Antonopoulos, Osuntokun, Pickhardt): https://github.com/lightningnetwork/lightning-rfc/blob/master/00-introduction.md

## Related Topics

- [Ethereum Internals](./ethereum-internals.md) — rollup alternative to payment channels
- [Optimistic Rollups](./optimistic-rollups.md) — fraud proofs vs Lightning's penalty model
- [Bridge Protocols](./bridge-protocols.md) — cross-chain HTLCs and atomic swaps
- [Consensus Mechanisms](./consensus-mechanisms.md) — Bitcoin's L1 consensus that Lightning depends on
