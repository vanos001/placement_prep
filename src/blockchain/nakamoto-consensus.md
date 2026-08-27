# Nakamoto Consensus

Classical consensus (Raft, PBFT) needs a known, bounded member list, because
one node equals one vote. An open cryptocurrency has no member list -- anyone
can run a node, an attacker can spin up a million. Nakamoto consensus breaks
this deadlock by making votes *unforgeably expensive*: the right to extend
the chain is earned by burning real-world resources (hash power), so
identities become meaningless and only accumulated work matters. This page
is the mechanics-and-math companion to the survey in [Consensus
Mechanisms](./consensus-mechanisms.md): chain selection, retargeting,
confirmation probabilities, selfish-mining thresholds, all checked against
simulation.

## Proof of Work as Sybil Resistance

The lineage runs from hashcash (Back, 1997), an anti-spam scheme that made
each email cost one verifiable hash computation, to the Bitcoin block: find
a nonce such that

```text
SHA256(SHA256(block_header)) < target
```

where the header commits to the previous block hash, the Merkle root of
transactions, the timestamp, and the target. Any node can verify a solution
with one hash, but finding one takes on average `2^256 / target` tries
network-wide. Two properties fall out:

1. **Sybil resistance.** A million virtual miners with 1% of the hash power
   win 1% of the blocks. Casting votes costs electricity and hardware, so
   one-entity-many-identities buys nothing.
2. **Objective history.** Given any block header, anyone can verify the
   whole chain of work back to genesis without trusting anyone. A new node
   joining the network picks the valid chain with the most embedded work --
   no membership protocol, no checkpoint server.

## Heaviest Chain, Not Longest

Chain selection is often stated as "longest chain wins." The precise rule in
Bitcoin is **greatest cumulative work**: sum over all blocks of
`2^256 / (target + 1)` (the expected number of hashes per block), compare
totals, and call the winner the active chain. The distinction matters after
a retarget: blocks found under *low* difficulty embed less work, so 105
easy blocks can lose to 100 harder ones. A full node tracks each tip's total
work (`nChainWork` in Bitcoin Core) and switches only on strictly greater
work, which is why the quantity of interest for an attacker is cumulative
difficulty, not block count.

```text
  fork point at block B
     |
     +-- [A1] -- [A2] -- [A3]          attacker tip: 3 blocks, total work 3.0
     |     1.0     1.0     1.0
     |
     +-- [H1] -- [H2] -- [H3]          honest tip:   3 blocks, total work 4.2
           1.0     1.6     1.6         (H2, H3 mined after a difficulty raise)
     |
  every miner extends H3: heavier total work (4.2) beats the attacker's
  branch even at equal length; A1..A3 become orphans. After any retarget,
  "longest" and "heaviest" are different claims -- compare nChainWork,
  never block counts.
```

Nodes continuously hear candidate tips, keep every valid branch in memory,
and mine on the heaviest one. When a heavier branch arrives late, the node
reorganizes (reorgs) onto it, re-validating and re-applying those blocks.
Confirmations are depth *on the heaviest chain*: a reorg that overtakes your
transaction undoes it, which is exactly the attack modeled below.

## Difficulty Retarget: The Math

Every 2016 blocks (two weeks at the 10-minute target), the network retargets.
Bitcoin Core's `pow.cpp` implements:

```text
actual_timespan = block(2016).time - block(0).time
actual_timespan clamped into [T/4, 4*T]      where T = 2016 * 600s = 1209600s
new_target   = old_target * actual_timespan / T
difficulty   = difficulty_1_target / target  (so difficulty scales inversely)
```

If the last epoch took 8 days instead of 14, targets shrink by the factor
`8/14`, raising difficulty by `14/8 = 1.75x`. The clamp bounds any single
retarget to a 4x step in either direction, capping how fast difficulty can
fall if hash power vanishes (the 2013 and 2024 hashrate shocks played out
over multiple epochs for this reason). Two economic consequences: the 10-
minute interval is a *policy*, enforced only through this feedback loop; and
miners chasing a retarget can manipulate timestamps within consensus limits,
which is why the clamps exist.

## Probabilistic Finality

A BFT commit is final when 2f+1 signatures land. Nakamoto consensus never
reaches certainty -- it makes reversal exponentially improbable. The model:
an attacker with hash fraction `q` mines privately while the honest network
(fraction `p = 1-q`) extends the public chain by `z` confirmation blocks.
Nakamoto's whitepaper (Section 11) approximates the attacker's private
progress at the `z`-confirmation checkpoint with a Poisson distribution
(`lambda = z*q/p`) and closes the race with the gambler's ruin: from a
deficit of `d` blocks, an attacker catches up with probability `(q/p)^d`.
His table quotes `P = 0.0009137` for `q = 0.1, z = 5`. The exact treatment
(the private-block count before the z-th honest block is negative-binomial,
NB(z, q), not Poisson) is what the simulation below actually reproduces.

```python
"""Double-spend race: attacker hash fraction q vs honest network (p = 1-q).
Block arrivals are exponential (Poisson); by memorylessness the next block
belongs to the attacker with probability q. Phase 1: attacker mines
privately until the public chain has z confirmations -- ahead at the
checkpoint means publish and win. Phase 2: biased random walk on the
deficit d = honest - private; d == 0 wins, d >= GIVEUP abandons."""
import math
import random

TRIALS = 400_000
SEED = 20260827

def nakamoto_p(q, z):                        # whitepaper Section 11, Poisson
    p = 1.0 - q
    lam = z * q / p
    return 1.0 - sum(math.exp(-lam) * lam ** k / math.factorial(k)
                     * (1.0 - (q / p) ** (z - k)) for k in range(z + 1))

def exact_p(q, z):                           # NB(z,q) + gambler's ruin
    p = 1.0 - q
    nb = lambda k: math.comb(z + k - 1, k) * p ** z * q ** k
    return (sum(nb(k) * (q / p) ** (z - k) for k in range(z))
            + 1.0 - sum(nb(k) for k in range(z)))

def race(q, z, giveup, rng):
    p = 1.0 - q
    honest = private = 0
    while honest < z:                        # phase 1: z confirmations accrue
        if rng.random() < q:
            private += 1
        else:
            honest += 1
    deficit = honest - private
    if deficit <= 0:
        return True
    while deficit < giveup:                  # phase 2: catch-up walk
        deficit += -1 if rng.random() < q else 1
        if deficit <= 0:
            return True
    return False

rng = random.Random(SEED)
print(f"Monte Carlo double-spend race: {TRIALS:,} trials per row, seed {SEED}")
print(f"{'q':>5} {'z':>3} | {'measured':>10} {'+-95%':>8} | {'NB-exact':>9} {'Nakamoto':>9}")
for q, z in [(0.1, 1), (0.1, 5), (0.2, 5), (0.3, 5), (0.3, 20), (0.45, 5)]:
    wins = sum(race(q, z, 200 if z <= 5 else 500, rng) for _ in range(TRIALS))
    phat = wins / TRIALS
    err = 1.96 * math.sqrt(phat * (1.0 - phat) / TRIALS)
    print(f"{q:>5.2f} {z:>3} | {phat:>10.6f} {err:>8.6f} | "
          f"{exact_p(q, z):>9.6f} {nakamoto_p(q, z):>9.6f}")
print("Nakamoto 2008 quotes P(q=0.1, z=5) = 0.0009137 in its table;")
print(f"his Poisson formula evaluated here: {nakamoto_p(0.1, 5):.7f} "
      f"(exact NB race: {exact_p(0.1, 5):.7f})")
```

Output (the simulation tracks the exact negative-binomial race to 4-5
digits; note the Poisson approximation is *not* uniformly conservative -- it
understates the attacker at q <= 0.3 and overstates at q = 0.45):

```text
Monte Carlo double-spend race: 400,000 trials per row, seed 20260827
    q   z |   measured    +-95% |  NB-exact  Nakamoto
 0.10   1 |   0.200068 0.001240 |  0.200000  0.204587
 0.10   5 |   0.001730 0.000129 |  0.001782  0.000914
 0.20   5 |   0.039535 0.000604 |  0.039163  0.027416
 0.30   5 |   0.197063 0.001233 |  0.197617  0.177352
 0.30  20 |   0.008740 0.000288 |  0.008674  0.002480
 0.45   5 |   0.757642 0.001328 |  0.757158  0.789786
Nakamoto 2008 quotes P(q=0.1, z=5) = 0.0009137 in its table;
his Poisson formula evaluated here: 0.0009137 (exact NB race: 0.0017818)
```

Read this as a merchant would: 6 confirmations against a 10%-hashrate
attacker leaves roughly a 2-in-10,000 reversal chance; the same attacker at
1 confirmation reverses 20% of the time. "51% attack" is the wrong headline
-- at q = 0.45 with 5 confirmations the attacker already wins three times
out of four, and security degrades smoothly below 51%.

## Selfish Mining: Below 51% Is Still an Attack

Eyal and Sirer ("Majority is not Enough", Financial Cryptography 2014;
arXiv 1311.0243) showed a revenue attack that needs no double-spend: a pool
withholds a found block and keeps mining privately. If the honest network
finds a competing block, the pool races; with `gamma` = the fraction of
honest hash power that mines on the pool's block when the race starts:

| Scenario | Threshold pool size for excess revenue |
|---|---|
| gamma = 1 (pool's blocks always win races) | effectively 0 (any size profits) |
| gamma = 0 (honest tie-break on first-seen) | 1/3 |
| gamma = 0.5 (their proposed countermeasure) | 1/4 |

Below the threshold, selfish mining loses money; above it, revenue is
superlinear, rational miners join the pool, and the paper shows the pool
grows toward majority. The countermeasure (always mine on the first block
you see, never re-relay to favor the attacker) pushes the threshold down to
1/4 -- defense here means changing the payoff matrix, not detecting anyone.
Later work (Carlsten et al., ACM CCS 2016) showed that once the block
subsidy shrinks and volatile transaction fees dominate rewards, the
incentive to deviate sharpens and selfish-mining thresholds fall further.

## Centralization and Energy

Proof of work concentrates through economies of scale: ASICs, cheap power,
and pool variance-smoothing mean a handful of pools coordinate large
fractions of total hash power. Pools do not equal hash power (members can
leave), but they are a censorship and protocol-negotiation chokepoint --
the live measurements in [MEV and PBS](./mev-pbs.md) show the same
concentration pattern on Ethereum's builder market. Energy use is not
incidental: the security budget *is* the energy spend, and Cambridge's
Bitcoin Electricity Consumption Index (CBECI) tracks an estimate on the
order of tens of TWh per year -- comparable to a mid-sized nation. The
design question is never "waste vs no waste" but whether the security
bought justifies the burn -- the core PoW/PoS debate in [Consensus
Mechanisms](./consensus-mechanisms.md).

## Nakamoto vs BFT Finality

| Property | Nakamoto PoW | BFT (PBFT / HotStuff) |
|---|---|---|
| Membership | Permissionless, pseudonymous | Known validator set |
| Sybil resistance | Extrinsic (hash cost) | Intrinsic (identity + stake/permission) |
| Finality | Probabilistic, grows with depth | Deterministic after commit round |
| Fault tolerance | Below 50% hash power | f < n/3 validators |
| Message complexity per block | O(1) (gossip) | O(n^2) PBFT, O(n) HotStuff |
| Under partition | Both sides keep building; heavier wins | Loses liveness (no quorum), keeps safety |
| Reversal mechanism | Reorg with more cumulative work | No mechanism (safety proof) |

The root difference: BFT protocols *decide*, Nakamoto consensus *weighs*.
That costs finality and buys open membership, objective reorganization-free
sync for new nodes, and graceful healing after partitions -- a BFT chain
halts under partition until operators intervene, while a PoW chain merges
both sides' work at the partition seam by total-work comparison. Hybrid
systems acknowledge both halves: Bitcoin exchanges treat deep confirmations
as settlement, and Tendermint-style chains ([Tendermint](../distributed/consensus/tendermint.md))
graft BFT commit onto proof-of-stake membership.

## Failure Modes and Common Misconfusions

1. **"Longest chain" as a rule.** After a retarget, length and work diverge;
   always reason in cumulative difficulty.
2. **Confirmations as guarantees.** They price an attack, they don't forbid
   it; the price collapses as q approaches 0.5 or z shrinks.
3. **Retarget as attacker tool.** A cabal of miners can suppress timestamps
   within bounds to lower difficulty, but the 4x clamp and honest-majority
   timestamps keep the window narrow; historical exploits (2017's BCH
   emergency-difficulty saga) exploited *retarget algorithm changes*, not
   the Bitcoin rule itself.
4. **Assuming honest tie-breaking.** Relay infrastructure that lets an
   attacker's blocks win races lowers the selfish-mining threshold toward
   the 1/4 floor without any majority hash power.
5. **Finality equivalence.** Exchanges treating 1-2 confirmations as
   "settled" for high-value transfers are renting probabilistic security at
   its weakest depth.

## References

- [S. Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System" (2008) -- Section 11: probability model](https://bitcoin.org/bitcoin.pdf)
- [I. Eyal, E. G. Sirer, "Majority is not Enough: Bitcoin Mining is Vulnerable" (FC 2014; arXiv)](https://arxiv.org/abs/1311.0243)
- [Bitcoin Wiki: Difficulty (2016-block retarget, target encoding)](https://en.bitcoin.it/wiki/Difficulty)
- [Cambridge Centre for Alternative Finance: Bitcoin Electricity Consumption Index](https://ccaf.io/cbnsi/cbeci)
- [M. Carlsten et al., "On the Instability of Bitcoin Without the Block Reward" (ACM CCS 2016)](https://doi.org/10.1145/2976749.2978408)
