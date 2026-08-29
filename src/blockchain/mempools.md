# Mempools: The Public Waiting Room Before Consensus

There is no "the mempool": every full node keeps its own set of signed-but-unconfirmed
transactions, and no two nodes must agree. A mempool is a per-node, admission-controlled
cache of *candidate* state transitions -- valid today, reorderable tomorrow, all leaving
at once when a block confirms. The interesting parts are the admission policy (what a
node will spend memory and bandwidth on) and what it leaks to observers. Block cadence
lives in [Nakamoto Consensus](nakamoto-consensus.md), the market on ordering in
[MEV and PBS](mev-pbs.md); this page is the waiting room: gates, gossip, replacement,
eviction, private entrances.

## N caches, not one queue

```text
  wallet --sign--> edge node --policy gates (fee floor, dust, size, standardness)
    |                | fail -> SILENT drop, no feedback message
    v                v (admit)
  local txpool [ pending | queued ]  <-- per-node, never global
    | announce hashes to peers
    v
  gossip mesh: every hop re-runs the same admission checks
    v
  block template (miners / builders, see mev-pbs.md) -> block -> confirm
```

Divergence is normal: an offline node misses announcements, a higher-fee-floor node
refuses traffic its neighbors hold, a replacement wipes the original from some pools.
Fee estimates differ per node, "my tx vanished" usually means local eviction or expiry,
and a valid transaction can vanish everywhere -- hence scheduled wallet rebroadcasting.

## Bitcoin: admission is a stack of gates

A transaction clears, in order: consensus validity, standardness (script types, weight,
datacarrier), the relay fee floor, dust rules, mempool limits, conflict handling.
Defaults verified against Bitcoin Core `master` (August 2026):

| Gate | Default | Purpose |
|---|---|---|
| `-minrelaytxfee` | 0.1 sat/vB (v30.0, PR #33106; was 1 sat/vB) | marginal-cost pricing for relay |
| `-incrementalrelayfee` | 0.1 sat/vB | minimum added fee a replacement must bring |
| `-maxmempool` | 300 MB | hard memory ceiling |
| `-mempoolexpiry` | 336 h (14 days) | drop unconfirmed entries after 2 weeks |
| `-limitancestorcount` / `-limitdescendantcount` | 25 each | bound work and eviction cost per chain |
| cluster limits (v31.0+) | 64 txs, 101 kvB per cluster | keep linearization tractable |
| `-dustrelayfee` | 3 sat/vB | outputs too small to be spendable are rejected |

The chain limits are the anti-DoS core: a child's fee makes its unconfirmed parent
profitable to mine (CPFP), but without limits an attacker could append thousands of
children and make every node track the family. Since v31.0 the pool is fee-sorted
**clusters**, linearized into decreasing-feerate chunks -- block building picks chunks
from the front, eviction trims from the back (`doc/policy/mempool-design.md`). The
floor is dynamic: trimming at some feerate ratchets the node's `mempoolminfee` up, so
under pressure the *effective* admission floor sits far above 0.1 sat/vB.

## RBF: paying to edit your place in line

A conflicting transaction (same input) may replace one already in the pool. BIP 125
formalized opt-in signaling; Bitcoin Core made full-RBF available in v24.0 (PR #25353)
and the **default** in v28.0 (PR #30493), so signaling no longer matters. The
replacement must:

1. pay an absolute fee >= the sum paid by everything it evicts (originals plus their
   in-mempool descendants);
2. pay for its own extra bandwidth at >= `-incrementalrelayfee` -- the docs' example:
   0.1 sat/vB on a 500 vB replacement means +50 satoshis minimum;
3. evict no more than 100 distinct clusters;
4. strictly improve the mempool's feerate diagram (v31.0 rule).

The sum rule exists because a feerate-only rule lets attackers cycle ever-smaller
replacements paying one extra satoshi each, burning relay bandwidth for pennies.
Package relay arrived in v28.0: one-parent-one-child acceptance via `submitpackage`
lets a high-fee child drag in a below-floor parent; packages are capped at
`MAX_PACKAGE_COUNT=25` and `MAX_PACKAGE_WEIGHT=404000` weight units.

## Ethereum: three queues and a nonce

Geth's txpool splits by nonce readiness: **pending** (executable -- the account's next
nonce, fee >= pool price limit), **queued** (future nonces or nonce gaps), and, since
EIP-4844, a separate blobpool. There is no Bitcoin-style network fee floor: the default
`PriceLimit` is 1 wei (operators raise it) because spam defense is gas metering per
operation, not per-relay pricing. Defaults from `core/txpool/legacypool/legacypool.go`:

| Parameter | Default | Meaning |
|---|---|---|
| `AccountSlots` | 16 | guaranteed executable slots per account |
| `GlobalSlots` | 4096 + 1024 | pending capacity (urgent + floating, 4:1) |
| `GlobalQueue` | 1024 | non-executable (gapped) capacity |
| `PriceBump` | 10% | minimum fee bump to replace a same-nonce tx |
| blobpool `PriceBump` | 100% | "either have patience or be aggressive" |
| `Lifetime` | 3 h | queued entries expire far faster than Bitcoin's 14 d |

Replacement is by **nonce**, not conflict set: resubmit the same nonce with >= 10%
higher price and it overwrites. A transaction arriving with a nonce gap (e.g., #5
before #4) waits in **queued**; if #4 is never admitted, #5 and its successors are
stuck until #4 arrives or expires. A full pending pool drops the cheapest entries; a
base-fee spike above a transaction's fee cap makes it a prime eviction candidate.

## Gossip: announce first, fetch on demand

Both chains separate advertising a transaction from transferring it. Bitcoin peers
send `INV` messages carrying 32-byte hashes; interested peers pull full bodies with
`GETDATA`. Ethereum's eth/68 is the same shape: "Initially, both ends should send
`NewPooledTransactionHashes` messages", and clients fetch unknown bodies via
`GetPooledTransactions` (`devp2p/caps/eth.md`). Announce-then-fetch turns a 400-byte
tx to 8 peers per hop into 32-byte hashes to all and bodies only to peers that ask.
The shifted cost lands on admission: every hop re-runs full policy, so a rejected
transaction is rejected N times, once per node -- with zero feedback. Neither protocol
sends rejection reasons (Bitcoin retired transaction `REJECT` messages; Ethereum never
had them): silence prevents amplification but leaves wallets guessing.

## Private order flow: the VIP entrance

The public mempool is an intelligence leak: anyone can simulate your transaction
before it is mined. Flash Boys 2.0 documented bots racing pending transactions in
priority gas auctions; the modern response is to not broadcast publicly at all.
A Protect-style RPC (Flashbots Protect, MEV-Share) forwards the signed transaction
directly to chosen builders; searchers see nothing in gossip, or only *hints*
("a swap of token X", not the amount) with refunds for revealed data. The builder
auction and why exclusivity pays is [MEV and PBS](mev-pbs.md)'s subject; the mempool
consequence is that Ethereum's *effective* mempool for sophisticated order flow is a
set of private builder pools, and public gossip carries retail leftovers. Bitcoin runs
on the public mesh -- miners read gossip directly -- so its policy fights (RBF,
pinning, package relay) happen in relay rules rather than auction markets.

| Route | Who sees the tx | User gets | Cost |
|---|---|---|---|
| public gossip | every node + searcher | global redundancy, no trust | full MEV exposure |
| direct-to-builder RPC | selected builders only | privacy, hints, refunds | trust in endpoint; no relay redundancy |
| rollup sequencer | one operator | instant soft confirmation | fully private, fully trusted |

Rollups collapse the question: the sequencer *is* the mempool -- a private queue with
no gossip, ordering decided by one operator. See [ZK Rollups](zk-rollups.md) for how
validity proofs discipline sequencer inclusion, and [EVM Internals](evm-internals.md)
for the gas metering behind per-operation spam pricing.

## Eviction under pressure

Admission gates decide who gets in; pressure decides who gets thrown out. The
simulator below (pure stdlib, seeded) runs a fixed 100,000 vB pool fed by a lognormal
fee-rate distribution, evicts lowest-fee-rate-first, tracks the ratcheted admission
floor, then walks two chained-unconfirmed scenarios against the ancestor limits.

```python
"""Mempool admission + eviction sim, Bitcoin-style. Pure stdlib, seeded."""
import math
import random

def part1():
    CAP, FLOOR, ROUNDS, PER = 100_000, 0.1, 12, 40   # vbytes; sat/vB
    edges = [0, 1, 2, 5, 10, 20, 50, 100, math.inf]
    rng, pool, used = random.Random(50), [], 0       # entries: [rate, vb]
    seen = adm = rej = ev = 0
    floor = FLOOR
    print(f"PART 1: capacity={CAP} vB, min relay {FLOOR} sat/vB, {ROUNDS}x{PER} txs")
    for rnd in range(1, ROUNDS + 1):
        r_ev = 0
        for _ in range(PER):
            seen += 1
            vb = rng.randint(150, 900)
            rate = round(math.exp(rng.gauss(1.8, 1.5)), 2)  # median ~6 sat/vB
            if rate < FLOOR:
                rej += 1; continue
            pool.append([rate, vb]); used += vb; adm += 1
            while used > CAP:                 # evict lowest fee-rate first
                v = min(pool); pool.remove(v); used -= v[1]; ev += 1; r_ev += 1
        floor = max(floor, min(t[0] for t in pool))   # admission-floor ratchet
        if rnd % 3 == 0:
            print(f"  round {rnd:2d}: txs={len(pool):3d} used={used:6d} vB  "
                  f"evicted_now={r_ev:2d}  floor={floor:5.2f} sat/vB")
    hist = [0] * 8
    for rate, _vb in pool:
        hist[next(i for i in range(8) if edges[i] <= rate < edges[i + 1])] += 1
    peak = max(hist)
    print(f"  totals: seen={seen} admitted={adm} rejected<floor={rej} "
          f"evicted={ev} final_floor={floor:.2f}")
    print("  final fee-rate histogram (sat/vB):")
    for lo, n in zip(edges[:-1], hist):
        print(f"    {lo:5.1f}+ | {'#' * round(40 * n / peak):<40} {n:3d}")

def part2(limit=25, size=101_000):
    print(f"PART 2: ancestor limits ({limit} txs, {size} vB)")
    for vb, label in ((400, "light chain"), (4200, "heavy chain")):
        anc = avb = 0
        for i in range(1, 31):
            if anc >= limit:
                print(f"  {label}: tx#{i} REJECT too-long-mempool-chain "
                      f"(in-mempool ancestors={anc})"); break
            if avb + vb > size:
                print(f"  {label}: tx#{i} REJECT too-long-mempool-chain-size "
                      f"(ancestors={anc}, ancestor_vbytes={avb})"); break
            anc += 1; avb += vb

part1()
part2()
```

Output (verbatim):

```text
PART 1: capacity=100000 vB, min relay 0.1 sat/vB, 12x40 txs
  round  3: txs=119 used= 61681 vB  evicted_now= 0  floor= 0.12 sat/vB
  round  6: txs=189 used= 99747 vB  evicted_now=39  floor= 1.82 sat/vB
  round  9: txs=187 used= 99488 vB  evicted_now=40  floor= 6.06 sat/vB
  round 12: txs=179 used= 99920 vB  evicted_now=45  floor= 9.02 sat/vB
  totals: seen=480 admitted=479 rejected<floor=1 evicted=300 final_floor=9.02
  final fee-rate histogram (sat/vB):
      0.0+ |                                            0
      1.0+ |                                            0
      2.0+ |                                            0
      5.0+ | ###########                               21
     10.0+ | ########################################  75
     20.0+ | ##############################            56
     50.0+ | #######                                   13
    100.0+ | #######                                   14
PART 2: ancestor limits (25 txs, 101000 vB)
  light chain: tx#26 REJECT too-long-mempool-chain (in-mempool ancestors=25)
  heavy chain: tx#25 REJECT too-long-mempool-chain-size (ancestors=24, ancestor_vbytes=100800)
```

Part 1 is the ratchet in action: the pool saturates near round 5, every round then
admits ~40 and evicts ~40, and the effective admission floor climbs 0.12 -> 9.02
sat/vB -- ninety times the static relay fee -- with nothing below 5 sat/vB surviving.
"But the minimum relay fee is 0.1 sat/vB" is the wrong mental model on a busy chain:
the floor is whatever the last trim evicted. Part 2 shows the two distinct ancestor
failures -- a light chain dies at link 26 on the **count** limit, a heavy one at
link 25 on the **size** limit -- and nothing will admit a child of a rejected parent,
so the chain head waits for a confirmation or a package submission. Real eviction is
cluster-aware (lowest-feerate *chunk* first, so a well-paying parent is not dropped
for a bad child) and the real `mempoolminfee` ratchets exactly as the sim's floor does.

## Spam and dust policy

Relay pricing is marginal-cost accounting. Bitcoin's dust is an output whose spend
costs more than it carries: at the 3 sat/vB dust rate a spendable P2PKH output must be
>= 546 sat (182 vB to spend x 3) and P2WPKH >= 294 sat (98 vB x 3) -- derived in
`policy.cpp`. Ethereum's equivalent is coarser: gas prices every operation, so a "dust
transaction" is one whose tip does not cover the marginal cost of holding and relaying
it -- hence operator-tuned price limits instead of a protocol floor. Both gate *form*
too: Bitcoin's standardness rules (nonstandard scripts rejected at the edge despite
being consensus-valid), datacarrier and weight caps; Ethereum's slot limits and the
blob/execution fee split that keeps blob demand from pricing out ordinary txs.

## When the waiting room lies

- **Divergent mempools skew fee estimation**: your node's floor is not the network's;
  estimators overpay right after pressure spikes, and "evicted" is not "invalid" --
  scheduled wallet rebroadcasting exists for exactly this.
- **Stranded chains** (both chains): one low-fee Ethereum tx at nonce N leaves every
  later transaction from that account stuck in `queued` for up to 3 hours; one
  below-floor Bitcoin parent blocks its children until you RBF it up or 1P1C-package
  them in.
- **Pinning**: attacker-owned low-fee relatives abuse the limits meant to bound
  eviction, making it expensive to RBF your own transaction -- why the rules now
  compare feerate diagrams, not raw feerates.
- **Memory is the attack surface**: every limit above (300 MB, 25/101 kvB, 16-slot
  accounts, 3 h lifetimes) maps one-to-one to a way someone once tried to fill the
  waiting room for free.

Worth being able to answer: why does the replacement rule demand the fee *sum*, not
just a higher feerate? why no rejection feedback in either protocol? what can a
builder offer a user that a gossip-reading miner cannot?

## References

1. Bitcoin Core mempool policy docs (replacements, cluster design/linearization,
   package acceptance): <https://github.com/bitcoin/bitcoin/blob/master/doc/policy/mempool-replacements.md>,
   <https://github.com/bitcoin/bitcoin/blob/master/doc/policy/mempool-design.md>,
   <https://github.com/bitcoin/bitcoin/blob/master/doc/policy/packages.md>
2. Bitcoin Core `policy.h` (default constants):
   <https://github.com/bitcoin/bitcoin/blob/master/src/policy/policy.h>
3. v30.0 release notes (0.1 sat/vB defaults, PR #33106): <https://bitcoincore.org/en/releases/30.0/>
4. v28.0 release notes (full-RBF default, 1P1C package relay, TRUC): <https://bitcoincore.org/en/releases/28.0/>
5. BIP 125: <https://github.com/bitcoin/bips/blob/master/bip-0125.mediawiki>;
   Bitcoin Optech topics (RBF, cluster mempool): <https://bitcoinops.org/en/topics/replace-by-fee/>,
   <https://bitcoinops.org/en/topics/cluster-mempool/>
6. go-ethereum `legacypool` source (verified defaults):
   <https://github.com/ethereum/go-ethereum/blob/master/core/txpool/legacypool/legacypool.go>
7. devp2p eth spec: <https://github.com/ethereum/devp2p/blob/master/caps/eth.md>;
   Geth `txpool` RPC docs: <https://geth.ethereum.org/docs/interacting-with-geth/rpc/ns-txpool>
8. Flashbots Protect RPC: <https://docs.flashbots.net/flashbots-protect/overview>
9. Daian et al., "Flash Boys 2.0" (arXiv 1904.05234): <https://arxiv.org/abs/1904.05234>
10. mempool.space (live aggregated Bitcoin mempool): <https://mempool.space/docs/faq>
