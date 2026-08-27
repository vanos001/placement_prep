# MEV and Proposer-Builder Separation

Block producers decide which transactions a block contains and in what order. When that
ordering power can be sold for money, an invisible market forms on top of the chain:
searchers bid for block positions, specialized builders assemble the most profitable
blocks, and validators sell their slot to the highest bidder. That market -- Maximal
Extractable Value (MEV) and its industrialization via Proposer-Builder Separation (PBS) --
is now the main supply chain of every full Ethereum block. Block production and consensus
basics live in [Ethereum Internals](ethereum-internals.md) and
[Consensus Mechanisms](consensus-mechanisms.md); this page assumes them.

## A taxonomy with money attached

| Type | Mechanism | Typical extractor | User impact |
|---|---|---|---|
| DEX arbitrage (atomic) | price diff between AMM pools closed in one bundle | searchers | ~none (rebalancing is socialized in LP fees) |
| CEX-DEX arbitrage | hedge on-chain fill against off-chain price move | pro shops | drives most builder competition |
| Liquidation | trigger undercollateralized loan, take penalty | liquidation bots | intended; fights over *who* gets it |
| Sandwich | front-run a swap, back-run it, profit from the victim's slippage | bots | direct loss: slippage + extra gas |
| Generalized backrunning | react to any state-changing tx (oracle updates, mints) | everyone | gas inflation |

The sandwich is the one users feel directly. A victim buys 100 ETH of a token against a
pool holding 1,000,000 ETH and 1,000,000 tokens; in a constant-product pool the price
impact of a trade is roughly twice the trade's fraction of pool reserves -- about 0.02%
here -- and the sandwicher clips most of that move by buying first and selling last,
paying the victim's gas-price-plus-one to get adjacent placement.

## Flash Boys 2.0 and the priority gas auction era

The phenomenon was named and measured in "Flash Boys 2.0" (Daian et al., 2019): the
authors documented arbitrage bots paying escalating fees for priority ordering on
decentralized exchanges and formalized priority gas auctions (PGAs) as a
continuous-time, partial-information game. Their central warnings: fee wars burn value
(winner's payment approaches the whole opportunity while losing bids still pay gas), and
high fees for ordering priority are a systemic risk to consensus, because the expected
value of rewriting history is bounded by extractable value -- hence "miner extractable
value", later renamed *maximal* extractable value after the Merge moved block production
to proposers ([arXiv 1904.05234](https://arxiv.org/abs/1904.05234)).

PGAs are open, ascending-bid escalations in the public mempool. The economics: if an
opportunity is worth V, and n bots can react within the same block, bids ratchet up by
the minimum increment until all but one are priced out -- and the winner's payment
approaches V minus a fraction of one increment. The loser of the whole auction is the
chain: gas prices spike for everyone, and the wasted bids of the losers still hit the
mempool. The simulation below makes the ratchet concrete:

```python
"""Priority gas auction ratchet: bots take turns outbidding the current best by
one increment until no profitable raise is left. Winner's payment approaches
the full opportunity value; every other bid is burned gas."""

def pga(mev_wei, n_bots, increment_wei, floor_wei):
    bids = [floor_wei] * n_bots          # everyone's floor = running gas cost
    turn, rounds = 0, 0
    while True:
        nxt = max(bids) + increment_wei  # next bot must beat the current best
        if nxt > mev_wei:                # raising would wipe out the profit
            break
        bids[turn % n_bots] = nxt
        turn += 1
        rounds += 1
    return rounds, max(bids), mev_wei - max(bids)

print(f"{'MEV (ETH)':>9} | {'bots':>4} | {'rounds':>7} | {'winner pays (ETH)':>17} | {'margin (gwei)':>13}")
for mev_eth in (0.1, 1.0, 10.0):
    mev = int(mev_eth * 10**18)
    rounds, pays, margin = pga(mev, n_bots=8, increment_wei=7 * 10**12, floor_wei=10**15)
    print(f"{mev_eth:>9.1f} | {8:>4} | {rounds:>7} | {pays/10**18:>17.6f} | {margin/10**9:>13.1f}")
```

Real output (Python 3.12):

```text
MEV (ETH) | bots |  rounds | winner pays (ETH) | margin (gwei)
      0.1 |    8 |   14142 |          0.099994 |        6000.0
      1.0 |    8 |  142714 |          0.999998 |        2000.0
     10.0 |    8 | 1428428 |          9.999996 |        4000.0
```

Tens of thousands to over a million bidding rounds for one slot, every round a
broadcast and a fee override: this is what the public mempool looked like at the top of
a liquidation cascade in 2020. The margin column is the point -- 2,000 to 6,000 gwei of
leftover profit on opportunities worth 0.1 to 10 ETH. Competition pushes essentially all
extractable value to the block producer, minus a fraction of one increment.

## The modern supply chain: searcher -> builder -> relay -> proposer

Flashbots' MEV-Geth (2021) moved the auction off-chain: searchers submit *bundles*
(atomically ordered transaction lists with revert protection) directly to miners, sealed
bid. Post-Merge, that pipeline generalized into MEV-Boost, an open sidecar any validator
can run, specified in builder-specs ([Flashbots docs](https://docs.flashbots.net/flashbots-auction/overview)):

```text
 searcher(s)                builder(s)                 relay(s)                  proposer (validator)
     |  bundle: txs +           |  full block body          |  header + bid only      |  sees bid (value)
     |  bid + revert rules      |  (ordered, MEV-packed)    |  (payload hash,         |  signs blinded header
     +------------------------> +-------------------------> +  payment target)       +---------------------->
                                |                           |                          |  getPayload -> full block
                                |  verifies validity,       |  acts as escrow:        |  publishes on p2p network
                                |  holds body, escrow       |  body released only     |
                                |                           |  after proposer signs   |
                                |                           +<------------------------+
```

- **Searchers**: arbitrage/liquidation bots (and normal users via private RPCs) submit
  bundles with discrete bids to many builders.
- **Builders**: assemble a full execution block from thousands of bundles plus
  public/private order flow, compute the proposer payment, and submit (header, value,
  payment commitment) to relays.
- **Relays**: data intermediaries. They validate the builder's block, hold the body in
  escrow, and forward only the signed-header bid to proposers. Open source, no consensus
  role, economically unbilled.
- **Proposer**: runs MEV-Boost instead of building locally; compares bids (including
  "build locally" at 0 MEV), signs the header with the highest value, requests the body,
  and publishes. The signature commits to the header hash (a Merkle root over the payload
  header), so payment terms cannot be altered afterward.

Adoption is the headline number: MEV-Boost went from zero at the Merge (Sept 2022) to
the dominant block production path; over the last few years roughly nine in ten blocks
have been built externally (live figures: [mevboost.pics](https://mevboost.pics/),
[relayscan.io](https://www.relayscan.io/); both showed high-80s percentages through
2025-2026). Concentration is the second headline: a handful of builders produce most
MEV-Boost blocks and builder market share rotates but stays oligopolistic; a dozen or so
relays have carried essentially all traffic since the Merge.

## Trust model: who can steal what

- **Builder steals by withholding.** The relay verifies the full body and holds it in
  escrow before any bid is shown, so a proposer never signs a header for a block that
  does not exist; a builder that fails to deliver gets cut off. Withholding is only
  rational for a builder that no longer wants bids -- which is why relay reputation and
  allowlists matter.
- **Builder steals by reordering?** Impossible after submission: the bid is bound to a
  specific payload header, and the relay validates the body against it.
- **Relay can steal.** A malicious relay can leak a valuable block body to a competing
  builder, or swap in its own higher-paying-but-different header to induce a signature
  on a block it controls (the 2023-2024 era of "malicious relay" incidents). Mitigations
  are social (allowlists) plus protocol-level: multiple relays per validator, and
  ultimately enshrining the escrow in consensus (ePBS below).
- **Proposer can cheat (a little).** After signing a header, a proposer could equivocate
  and propose a competing self-built block; it keeps nothing from the builder's payment
  (which is in the builder's block) but risks attestor penalties. Honest-but-greedy
  behavior is mainly: running multiple relays, or withholding until the slot's last
  moment.
- **Proposer commitments** (inclusion lists, preconfirmations) exist to claw back
  guarantees: the proposer commits in advance to including a list of transactions,
  limiting what builders can censor or delay.

## Censorship

After the Aug 2022 Tornado Cash sanctions, OFAC filtering by relays became the era's
defining debate: relays that excluded OFAC-sanctioned addresses from their blocks
carried, at the 2022-2023 peak, close to four-fifths of MEV-Boost blocks, meaning most
slots would temporarily refuse to include a sanctioned transaction
([mevboost.pics](https://mevboost.pics/) tracks the numbers). The share then collapsed
as several major relays dropped full-block filtering (2024-2025); censoring-relay share
has since sat in the low tens of percent (live: mevwatch.info). The structural lesson is
qualitative and durable: an unbilled middleman (the relay) became the effective
censorship enforcement point, which is the argument for removing relays from the
critical path.

## ePBS and beyond

Enshrined PBS moves the escrow into the protocol. EIP-7732 (2024) splits the beacon
block into a consensus part (header commitments, bids) and an execution part delivered
by the builder, with the protocol enforcing payment and slashing equivocation -- no
trusted relay. As of mid-2026 it is the headline candidate for the Glamsterdam fork
(targeted for the second half of 2026, alongside block-level access lists); scope can
still shift, so check the current roadmap
([ethereum.org roadmap: PBS](https://ethereum.org/en/roadmap/pbs/),
[EIP-7732](https://eips.ethereum.org/EIPS/eip-7732)). Flashbots' SUAVE pursued the same
decentralization goal from the application side (a shared, cross-domain auction network
with builders as first-class participants; development stayed at testnet scale), and the
preconfirmation ecosystem (proposer-signed promises of future inclusion/execution for
L2 sequencing and fast UX) grew around proposer commitments rather than waiting for
protocol enshrinement.

## Failure modes and open risks

- Builder outage: top-two builders going down simultaneously leaves proposers with
  low-value local blocks -- slot revenue, not safety, is at risk.
- Relay single point of liveness: a proposer pointing at one dead relay skips its slot;
  most operator guides configure two or three for this reason.
- Order-flow deals: exclusive arrangements between wallets and builders push toward
  builder centralization; BuilderNet (2025) is the notable attempt at a federated,
  auditable builder cooperative.
- Timing games: proposers delaying their slot to catch late, higher bids (dedicated
  "timing games" tooling exists) stretches effective slot times; watch attester
  inclusion-delay statistics rather than assuming every slot is 12 seconds of block
  time.
- Latency arms race between searchers and builders re-creates the colocation economics
  of Flash Boys -- inside one block now, not one exchange.

## References

- [Flash Boys 2.0: Frontrunning, Transaction Reordering, and Consensus Instability in Ethereum, Daian et al., 2019](https://arxiv.org/abs/1904.05234)
- [Flashbots docs: the Flashbots auction (searchers, builders, relays)](https://docs.flashbots.net/flashbots-auction/overview)
- [mevboost.pics: MEV-Boost dashboards (adoption, payments, relay share)](https://mevboost.pics/)
- [EIP-7732: Enshrined Proposer-Builder Separation](https://eips.ethereum.org/EIPS/eip-7732)
- [ethereum.org roadmap: Proposer-Builder Separation](https://ethereum.org/en/roadmap/pbs/)
