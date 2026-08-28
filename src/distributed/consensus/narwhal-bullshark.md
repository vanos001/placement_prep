# Narwhal and Bullshark: DAG Mempools and Order-Free BFT

Classical BFT consensus interleaves two jobs: *disseminating* client
transactions (gossip, batching, availability) and *ordering* them (voting,
quorum certificates, committing). HotStuff-style protocols fuse the jobs
under a per-view leader: if the leader is slow or Byzantine, both jobs stall.
Narwhal and Bullshark split them cleanly - Narwhal is a DAG-shaped mempool
that disseminates and certifies batches no matter who is faulty, and
Bullshark is an *ordering rule* read off that DAG with zero extra message
rounds. The result is the modern DAG-BFT family that Aptos and Sui shipped
production.

Companion reading: [HotStuff](./hotstuff.md) for the leader-driven protocol
being displaced, [Tendermint](./tendermint.md) for the per-height voting
alternative, [PBFT](./pbft.md) for the ancestor with the same quorum
arithmetic, and [Byzantine quorum systems](../advanced/byzantine-quorum-systems.md)
for why `3b+1` servers with `2b+1`-certificates is the floor.

## Why a DAG mempool

In a leader-based protocol the leader aggregates client transactions and
proposes them; availability of the payload is established by a quorum voting
for the proposal. Two costs follow. First, the leader's uplink is a
bottleneck (everyone else idles while it disseminates). Second, and worse,
view changes are expensive: on a leader timeout the system must prove to the
next leader *what it missed* (timely certificates, PACEMAKER/timeout
certificates) - the notorious "blame shifting" machinery.

Narwhal removes the leader from the data path:

1. Each validator continuously gossips its own **batches** of transactions
   (through dedicated **workers**, scaling dissemination horizontally).
2. A batch is **certified** when a quorum of `2b+1` workers/primaries ack it
   - the batch certificate (BC) is a dissemination quorum proof that the
   payload is available *everywhere that matters*.
3. Each round, a validator's **primary** proposes a vertex containing: its
   own new batch references plus references to *all* vertices it saw last
   round. Since vertices must reference a quorum (`2b+1`) of previous-round
   vertices, the structure knits itself into a DAG with provable
   connectivity.

After `n - f` primaries have proposed round r, every future vertex can see
round r's history: dissemination is complete without any leader. The mempool
never stalls on a Byzantine or slow leader; at worst its payloads wait for
someone else's anchor.

```text
round r-2      round r-1           round r (leader round, even)
  A1 ----------> [a1 a2 a3] ---------> A2 (anchor candidate)
   \              \    \                 \
    \ refs 2b+1 of prev round each; leader = deterministic function of round
     \             \    \_________________\
      v             v
  every vertex references >= 2b+1 of the previous round -> DAG connectivity
```

## Bullshark: ordering with zero extra messages

Bullshark reads a commit decision out of the existing DAG. The
partially-synchronous variant (CCS 2022) works in *waves* of two rounds:

- **Even rounds are leader rounds.** The leader of round r is a deterministic
  function of r (round-robin over primaries).
- **Odd rounds vote.** A vertex in odd round r+1 *votes* for the anchor
  (leader vertex) of round r iff there is an edge to it - and every vertex
  has edges to at least `n - f` vertices of the previous round, so a
  well-connected leader collects votes from almost everyone who is honest
  and live.
- **Commit rule: an anchor with at least `f + 1` votes is committed** (f =
  number of Byzantine faults, n = 3f+1). Why f+1 suffices: any two vote
  sets of size f+1 can differ in at most ... more precisely, an honest
  voter only votes when it sees the anchor with a quorum of references
  behind it, and the DAG's connectivity (`n - f` edges per vertex) forces
  every later committed anchor to have a causal path to that vote.
- **Ordering the payload.** Once anchors are committed, order their causal
  histories by a deterministic traversal: walk recursively from each
  committed anchor Ai to its predecessor anchor (commit-order = path
  order); anchors with no path from a later committed anchor are *skipped*
  (their payloads ride along with the next anchor that does causally
  include them).

The total-order decision therefore costs **no extra message rounds**: votes
are ordinary DAG references that would have been exchanged anyway, and
commitment is a local computation over received vertices. That is the
"order-free" in the title: ordering consumes dissemination, it does not
follow it.

### Asynchronous and post-Bullshark variants

The original Bullshark (arXiv:2201.05677, CCS 2022) is *asynchronous*: no
partial-synchrony assumption, and its anchor selection is probability-based
(random leader per round) with a similar f+1 style commit argument; the
separate partially-synchronous manuscript (arXiv:2209.05633) is the cleaner
two-round-wave exposition summarized above. Successors sharpen the constant
factors: **Mysticeti** (arXiv:2310.14821) drops the per-batch certificates
("uncertified DAGs") to cut end-to-end latency to a few hundred
milliseconds in production deployments, and 2026's **Lemonshark** pushes
early finality on the asynchronous line. The design axis all of them ride:
how much certification overhead can be dropped while keeping the DAG's
safety argument intact.

## How the latency really behaves

The honest comparison with HotStuff is not a single number; it is latency
*as a function of leader luck*:

- **Chained HotStuff** commits block b when block b+2 is committed. Under a
  healthy stable leader each block takes one round; commit latency ~ 2
  rounds. A failed view (Byzantine/slow leader) costs a timeout plus a
  view change before progress resumes, and the payload ordering pauses.
- **Bullshark** has an anchor every two rounds. A failed leader anchor is
  simply not committed - the *DAG keeps growing*, and the failed anchor's
  payloads become part of the causal history of the next committed anchor.
  No timeout machinery, no view-change certificates.

The demo below models exactly that: 200 rounds of fixed duration, each
round's designated leader fails with probability p, and transactions carry a
round timestamp. For HotStuff, failed proposals waste 2 rounds (timeout +
recovery) and their transactions wait; for Bullshark, failed anchors just
delay their payload until the next successful anchor commits. The output is
mean transaction latency versus leader-failure rate - the structural reason
DAG-BFT systems survive adversarial or flaky leaders with a gentler latency
curve.

```python
#!/usr/bin/env python3
"""Commit-latency model: Chained HotStuff (2-chain) vs Bullshark waves
under random leader failures. Pure stdlib, deterministic (seeded).

Model
-----
N_ROUNDS rounds of fixed duration R. Each round has a designated leader
(deterministic round-robin) that fails with probability P_FAIL
(Byzantine/crashed/offline); a failed HotStuff proposal costs a timeout +
view change = 2 lost rounds before the next leader proposes; a failed
Bullshark anchor simply is not committed -- the DAG keeps growing and its
payload rides with the next committed anchor.

Commit rules:
  HotStuff 2-chain: block of round r commits when rounds r and r+1 both
                    produced successful blocks (pipelined), i.e. 2 rounds
                    after proposal if no leader failure in between.
  Bullshark: anchor of even round r (leader round) commits in round r+1
             (votes) if the leader succeeded; payload of failed anchors is
             ordered with the next committed anchor's causal history.

Transactions: each round injects T txs; a tx commits with its payload.
Mean latency reported in round-units and ms (R = 250 ms)."""
import random

N_ROUNDS = 200
R_MS = 250.0
T = 100          # txs injected per round
SEED = 7


def simulate(p_fail, proto):
    rng = random.Random(SEED)
    ok = [False] * (N_ROUNDS + 4)        # round -> proposal succeeded
    total_lat, txs = 0.0, 0
    r = 0
    while r < N_ROUNDS:
        ok[r] = rng.random() >= p_fail
        r += 1
    for r in range(N_ROUNDS):
        if proto == "hotstuff":
            # block r commits when r and r+1 both succeeded; if r+1 failed
            # the commit waits until two consecutive successes occur
            c = r + 1
            while c < N_ROUNDS + 2 and not (ok[c - 1] and ok[c]):
                c += 1
            lat_rounds = (c - r)
        else:  # bullshark: anchors on even rounds, commit 1 round later
            if r % 2 == 1:
                anchor = r - 1
            else:
                anchor = r
            if not ok[anchor]:
                # failed anchor: payload ordered with next committed anchor
                c = anchor + 2
                while c < N_ROUNDS + 2 and not ok[c]:
                    c += 2
            else:
                c = anchor + 1
            lat_rounds = (c - r)
        lat_rounds = max(1, lat_rounds)
        total_lat += T * lat_rounds
        txs += T
    return total_lat / txs


print(f"model: {N_ROUNDS} rounds, R={R_MS:.0f} ms, {T} txs/round, seed={SEED}")
print(f"{'p_fail':>7} | {'HotStuff 2-chain':>17} | {'Bullshark':>10} | ratio")
print("-" * 52)
for p in (0.0, 0.1, 0.2, 0.3, 0.5):
    hs = simulate(p, "hotstuff")
    bs = simulate(p, "bullshark")
    print(f"{p:>7.1f} | {hs:>9.1f} rounds | {bs:>6.1f} rounds | {hs/bs:5.2f}x")

hs = simulate(0.2, "hotstuff") * R_MS
bs = simulate(0.2, "bullshark") * R_MS
print()
print(f"at p_fail=0.2: HotStuff ~{hs:.0f} ms vs Bullshark ~{bs:.0f} ms mean tx latency")
print("structure: HotStuff pays timeout+viewchange (2 rounds) per failed leader;")
print("Bullshark only waits for the next successful anchor (2-round cadence),")
print("and dissemination never pauses -- the mempool is leaderless by design.")
```

```text
model: 200 rounds, R=250 ms, 100 txs/round, seed=7
 p_fail |  HotStuff 2-chain |  Bullshark | ratio
----------------------------------------------------
    0.0 |       1.0 rounds |    1.0 rounds |  1.01x
    0.1 |       1.5 rounds |    1.1 rounds |  1.29x
    0.2 |       2.4 rounds |    1.4 rounds |  1.67x
    0.3 |       3.0 rounds |    1.6 rounds |  1.88x
    0.5 |       5.3 rounds |    2.9 rounds |  1.82x

at p_fail=0.2: HotStuff ~591 ms vs Bullshark ~354 ms mean tx latency
structure: HotStuff pays timeout+viewchange (2 rounds) per failed leader;
Bullshark only waits for the next successful anchor (2-round cadence),
and dissemination never pauses -- the mempool is leaderless by design.
```

(At zero failures the curves touch - both protocols commit in about one
pipelined round - the entire win is in the failure tail, which is where
production latency distributions actually live.)

## What this buys, and what it costs

| dimension            | HotStuff / Tendermint            | Narwhal + Bullshark              |
|----------------------|----------------------------------|----------------------------------|
| leader on data path  | yes (proposes payload)           | no (leader only orders)          |
| view-change cost     | timeout certificates, blame      | none (skip the anchor)           |
| votes on payload     | quorum per block                 | none (DAG references are votes)  |
| messages per payload | O(n) per block + view changes    | O(n) per round, amortized over all payloads |
| liveness model       | partial synchrony (GST)          | async (original) / partial-sync (waves variant) |
| storage overhead     | one block per view               | full DAG until GC - every validator stores everyone's batches |
| fairness             | leader picks payload order       | causal-history traversal (deterministic, more fair in practice) |

The cost column is the honest counterweight: DAG protocols trade message
rounds for *storage and bandwidth* - every vertex carries references and
batches that all validators replicate, and garbage collection (pruning the
DAG behind the committed frontier) is a real engineering subsystem. This is
why Mysticeti's "uncertified" variant matters operationally: certification
is the expensive line item, and the research frontier is how little of it
survives while the f+1-style safety argument stays provable.

## Interview probes

- Why does an anchor need only `f + 1` votes when the quorum everywhere
  else is `2b + 1`? (Answer in terms of what an honest voter checks before
  voting, and the `n - f` edge-connectivity of the DAG.)
- Where exactly does Bullshark's ordering rule use determinism, and why
  must every validator derive the *same* skip decision for an uncommitted
  anchor?
- HotStuff also reaches 3-message-commit in the common case: name the two
  sources of its tail latency that the DAG design eliminates.
- Given `n = 3b + 1`, derive how many workers' certificates a Narwhal batch
  needs, and connect that number to the dissemination-quorum condition in
  [Byzantine quorum systems](../advanced/byzantine-quorum-systems.md).

## References

1. [Narwhal and Tusk: a DAG-based mempool and efficient BFT consensus](
   https://arxiv.org/abs/2105.11827) (Spiegelman, Giridharan, Sonnino,
   Kokoris-Kogias; AFT 2021) - the DAG mempool architecture and the first
   DAG-ordering protocol.
2. [Bullshark: DAG BFT protocols made practical](
   https://arxiv.org/abs/2201.05677) (CCS 2022) - the asynchronous protocol.
3. [Bullshark: the partially synchronous version](
   https://arxiv.org/abs/2209.05633) (Spiegelman et al., 2022) - the
   two-round-wave exposition this page's commit rule follows; commit rule
   and anchor-ordering mechanics quoted from its figures 2-5.
4. [Mysticeti: reaching the limits of latency with uncertified DAGs](
   https://arxiv.org/abs/2310.14821) (2023) - the uncertified-DAG successor
   and its production latency results.
5. [Lemonshark: asynchronous DAG-BFT with early finality](
   https://arxiv.org/html/2604.03974v1) (2026) - the current state of the
   asynchronous line; cited as a 2026-era pointer, not load-bearing for
   the mechanics above.
