# Failure Detectors

A failure detector is not a daemon that pings machines. Formally, it is an
**oracle**: an object that answers one question per process — *suspected of
crashing, or not?* — with no guarantee of being right right now. The
abstraction exists because of an impossibility: in a purely asynchronous
system, consensus cannot guarantee termination with even one crash fault
([flp.md](./flp.md)). Every protocol that actually terminates — Raft's
election timeout, Paxos's leader failure detection, a lease manager's
expiry decision — smuggles in exactly this oracle under a different name.
This page builds the formal machinery, then makes it quantitative the way
production systems do.

## The formal object: two axes, eight classes

Chandra and Toueg (JACM 1996) define detectors by two independent
properties, each in a now-or-eventually flavor:

- **Completeness** — crashed processes *do* get suspected.
  *Strong*: every crashed process is eventually suspected by **every**
  correct process. *Weak*: eventually suspected by **some** correct process.
- **Accuracy** — correct processes *don't* get suspected.
  *Strong*: no correct process is ever suspected. *Weak*: **some** correct
  process is never suspected. The eventual variants relax these to hold
  only after some (unknown) time — the honest assumption once the network
  stabilizes.

Crossing the two axes gives the canonical classes (all eight appear in the
paper; the four below are the ones that matter in practice):

| Class | Completeness | Accuracy | Practical reading |
|-------|--------------|----------|-------------------|
| P (perfect) | strong | strong | Ideal and unrealizable: timeouts can't provide it in asynchrony |
| ◇P (eventually perfect) | strong | eventual strong | The right model for a stable LAN: wrong suspicions only during instability |
| S (strong) | strong | weak | Every crash suspected everywhere; one process never suspected |
| ◇S (eventually strong) | strong | eventual weak | Suffices for consensus; what timeout-based leaders converge to |

Two results organize this zoo. First, **reducibility**: detector D₁
reduces to D₂ if an algorithm can transform D₂'s output into D₁'s
properties — so strengths are comparable, and the hierarchy collapses into
equivalence classes. Second, the **weakest** result: ◇P is the weakest
failure detector that solves consensus (Chandra, Hadzilacos & Toueg, JACM
1996) — weaken ◇P by any epsilon and consensus becomes impossible again.
For more on the impossibility side and the class hierarchy in context, see
[impossibility-models.md](../advanced/impossibility-models.md).

## Why no real detector is "perfect": the partial-synchrony bridge

Completeness is cheap — stop receiving and eventually suspect. The hard
property is accuracy, and its impossibility in asynchrony is just FLP
restated: a slow process is indistinguishable from a crashed one, so any
detector that suspects the slow process violates strong accuracy, and one
that doesn't violates completeness. Dwork, Lynch and Stockmeyer (JACM
1988) supply the escape hatch: assume **partial synchrony** — message
latency and clock drift are bounded, but the bounds hold only *eventually*
or are only *eventually known*. Under partial synchrony, a timeout-based
detector implements ◇P: once the system becomes stable (bounds hold), its
suspicions are correct. This is the precise sense in which "Raft uses a
failure detector": the election timeout is a ◇P-approximating oracle whose
accuracy holds *after* the network stops misbehaving, never before.

## Making suspicion quantitative: the φ accrual detector

A binary detector throws away the most useful signal available: *how*
strange is this silence? The φ accrual detector (Hayashibara et al., SRDS
2004) replaces suspect/not with a continuous **suspicion level** φ computed
from the observed heartbeat inter-arrival distribution:

```text
 1. monitor records each inter-arrival time in a sliding window W
 2. estimate the distribution X ~ (mu, sigma) of inter-arrivals
 3. for elapsed silence t since the last heartbeat:
        P_late(t) = P(X > t)                    tail probability
        phi(t)    = -log10( P_late(t) )         suspicion level
 4. declare failure when phi(t) >= Phi_threshold
```

The log scale gives φ a direct probabilistic reading: **φ = n means "a
live process would produce silence this long with probability about
10^-n"**. φ = 1 → one in ten; φ = 8 → one in a hundred million. The
operator picks the false-alarm risk they tolerate, and the *same* number
adapts across networks because the distribution does the scaling:

| φ threshold | False-alarm odds per silence check | Typical use |
|-------------|-----------------------------------|-------------|
| 1 | 1 in 10 | Aggressive gossip cleanup, huge clusters |
| 6 | 1 in 1,000,000 | LAN services, fast failover wanted |
| 12 | 1 in 10^12 | Conservative core metadata (e.g. Akka defaults near here) |

Practical parameters matter more than the bare formula:

- **Window size W** — how many inter-arrivals the estimate uses; too small
  and one hiccup poisons μ, σ; too large and the detector lags a genuine
  network change.
- **σ floor (min std)** — the raw σ of a clean LAN can be ~10 ms, which
  makes φ explode past any threshold the first time a scheduler hiccups
  300 ms. Implementations floor σ (Akka's default minimum is 100 ms) so
  φ grows at a sane rate against long silences.
- **Threshold** — decouples policy (risk tolerance) from mechanism
  (distribution). Raising it never changes the detector's view of the
  network, only the verdict.

## Sizing heartbeat timeouts under jitter

The fixed-timeout alternative has to answer: what P(inter-arrival > T) is
acceptable? With inter-arrivals ~ N(μ, σ) and jitter, the answer is a tail
integral — and the tail is exactly where GC pauses, page-cache stalls, and
virtualization noise live. Sizing T for the observed jitter (μ + 3σ) hands
the system to the first 5-second GC pause; sizing it for the pause makes
every real crash look slow. The demo below quantifies both horns on one
deterministic trace: a 1400 ms fixed timeout false-suspects during a single
GC pause; a 2000 ms timeout that survives the pause on the LAN still
false-suspects when the same traffic moves to a WAN; the accrual detector
with the same threshold survives both, paying 10-30% longer time-to-detection
as the price of zero false suspicions.

Two practical refinements complete the picture: **suspicion vs
confirmation** (SWIM's suspicion subprotocol delays "dead" verdicts while
the suspect refutes with an incremented incarnation number — see
[swim-membership.md](./swim-membership.md)), and **hysteresis** (require
the condition to persist, or confirm via an indirect probe, before acting —
a φ threshold is itself a hysteresis over raw latency).

## Where detectors plug in

- **Leader election.** Raft's election timeout is a fixed-T detector per
  follower; a candidate whose quorum answer arrives treats stale leaders'
  heartbeats as False suspicions. The classical election algorithms this
  replaces are in [bully.md](./bully.md).
- **Lease expiry.** A lease holder keeps a lock only until expiry; the
  grantor re-grants only when its detector says the holder is dead or the
  lease lapsed. Detector accuracy limits become lease-safety limits — the
  interplay is worked out in [leases.md](../advanced/leases.md).
- **Membership.** SWIM makes detection a distributed protocol: every member
  probes k others directly, then indirectly through random delegates before
  suspecting; suspicions disseminate by gossip with incarnation numbers for
  refutation. φ accrual and SWIM compose naturally — accrual as the local
  signal, infection-style dissemination as the transport
  ([gossip.md](./gossip.md) covers the transport side).
- **Framework lineage.** Akka Cluster ships φ accrual with explicit
  `min-std-deviation` and threshold settings; Cassandra ran accrual
  detection inside its gossip for years and added SWIM-style direct and
  indirect probing in its 4.0 failure-detection rework — the industry
  trajectory runs from local statistics toward probing protocols, not the
  reverse.

## Runnable check: φ over a synthetic trace

```python
"""Phi-accrual failure detection over a deterministic heartbeat trace.

Trace: a monitor receives heartbeats every 500 ms nominal (LAN) or 800 ms
(WAN). Jitter comes from a fixed LCG (uniform +/-20 ms). Mid-trace the
sender suffers one GC pause (~1460 ms extra gap); after the last beat it
dies for good. We compare detection policies on the identical trace:
  - fixed timeout 1400 ms (aggressive)
  - fixed timeout 2000 ms (sized to survive the pause)
  - phi accrual (Hayashibara et al. 2004), normal-distribution model:
      P_late(t) = P(inter-arrival > t) = 1 - Phi((t - mean) / sigma)
      phi(t)    = -log10(P_late(t))
    window W=50, sigma floored at min_std=250 ms, suspicion at phi >= 12.
False suspicions count silence episodes where the sender was still alive.
Detection delay = time from the last heartbeat to first suspicion.
"""
import math

_seed = [7]
def lcg_jitter(n):
    """Deterministic LCG: n jitter terms, uniform ints in [-20, 20]."""
    out = []
    for _ in range(n):
        _seed[0] = (1103515245 * _seed[0] + 12345) % 2**31
        out.append(_seed[0] % 41 - 20)
    return out

def build_trace(base_ms, pause_at=30, total=60):
    jit = lcg_jitter(total)
    t, arr = 0.0, []
    for i in range(total):
        gap = base_ms + jit[i]
        if i == pause_at:
            gap += 1460                   # the GC pause
        t += gap
        arr.append(t)
    return arr                            # after last beat the sender is dead

class PhiFD:
    def __init__(self, base, window=50, min_std=250.0, thr=12.0):
        self.win, self.min_std, self.thr = [base] * 2, min_std, thr
        self.W, self.last = window, 0.0

    def beat(self, t):
        if self.last:                     # skip t=0 sentinel
            self.win.append(t - self.last)
            if len(self.win) > self.W: self.win.pop(0)
        self.last = t

    def phi(self, now):
        mu = sum(self.win) / len(self.win)
        var = sum((x - mu) ** 2 for x in self.win) / len(self.win)
        sd = max(math.sqrt(var), self.min_std)
        # P_late(t) = P(inter-arrival > t), X ~ N(mu, sd)  (Hayashibara 3.1)
        z = (now - self.last - mu) / sd
        p_late = 0.5 * math.erfc(z / math.sqrt(2.0))
        return -math.log10(max(p_late, 1e-300))

def monitor(trace, fixed_ms=None, fd=None):
    """Tick the monitor every 50 ms; returns (false episodes, death delay)."""
    beats, bi, last_beat = sorted(trace), 0, 0.0
    episodes, suspected, death_delay = 0, False, None
    t = 0.0
    while t <= beats[-1] + 6000:
        while bi < len(beats) and beats[bi] <= t:     # heartbeats reset suspicion
            last_beat, suspected = beats[bi], False
            if fd is not None: fd.beat(beats[bi])
            bi += 1
        gone = t - last_beat
        dead = bi >= len(beats)
        bad = (gone >= fixed_ms) if fixed_ms is not None else (fd.phi(t) >= fd.thr)
        if bad:
            if dead:
                if death_delay is None: death_delay = gone
            elif not suspected:
                episodes += 1; suspected = True
        t += 50.0
    return episodes, death_delay

print("phi vs elapsed silence (window fitted on first 20 LAN beats):")
fd = PhiFD(500)
tr = build_trace(500)
for b in tr[:20]: fd.beat(b)
mu = sum(fd.win) / len(fd.win)
var = sum((x - mu) ** 2 for x in fd.win) / len(fd.win)
sd = max(math.sqrt(var), fd.min_std)
print("  mean=%.0f ms  raw sigma=%.0f ms  sd used=%.0f ms  threshold phi=12" %
      (mu, math.sqrt(var), sd))
for gone in (500, 1000, 1500, 2000, 2500):
    print("  silence %4d ms -> phi = %5.2f" % (gone, fd.phi(fd.last + gone)))
print("  phi=12 crossing: %.0f ms of silence (mean + 6.71 * sd)" % (mu + 6.708 * sd))

for name, base in [("LAN, nominal 500 ms", 500), ("WAN, nominal 800 ms", 800)]:
    print("trace: %s, one GC pause (~+1460 ms), then death" % name)
    tr = build_trace(base)
    for label, kw in [("fixed timeout 1400 ms", dict(fixed_ms=1400)),
                      ("fixed timeout 2000 ms", dict(fixed_ms=2000)),
                      ("phi accrual thr=12   ", dict(fd=PhiFD(base)))]:
        ep, delay = monitor(tr, **kw)
        print("  %-22s false suspicions: %d   death detected after: %s ms" %
              (label, ep, ("%d" % delay) if delay else "n/a"))
```

```text
phi vs elapsed silence (window fitted on first 20 LAN beats):
  mean=503 ms  raw sigma=12 ms  sd used=250 ms  threshold phi=12
  silence  500 ms -> phi =  0.30
  silence 1000 ms -> phi =  1.63
  silence 1500 ms -> phi =  4.47
  silence 2000 ms -> phi =  8.97
  silence 2500 ms -> phi = 15.16
  phi=12 crossing: 2180 ms of silence (mean + 6.71 * sd)
trace: LAN, nominal 500 ms, one GC pause (~+1460 ms), then death
  fixed timeout 1400 ms  false suspicions: 1   death detected after: 1445 ms
  fixed timeout 2000 ms  false suspicions: 0   death detected after: 2045 ms
  phi accrual thr=12     false suspicions: 0   death detected after: 2295 ms
trace: WAN, nominal 800 ms, one GC pause (~+1460 ms), then death
  fixed timeout 1400 ms  false suspicions: 1   death detected after: 1433 ms
  fixed timeout 2000 ms  false suspicions: 1   death detected after: 2033 ms
  phi accrual thr=12     false suspicions: 0   death detected after: 2633 ms
```

Read the two trace blocks together: the 2000 ms fixed timeout is the
operator's LAN-tuned compromise — zero false alarms at home — but the
moment the same sender crosses a WAN, the pause exceeds it. The accrual
detector keeps false suspicions at zero in *both* environments with one
unchanged threshold, because its effective timeout (μ + 6.71σ) scales with
the observed μ. That adaptivity, not raw speed, is the sales pitch of φ.

## Interview drills

1. *State the completeness and accuracy of ◇S, and explain why ◇S suffices
   for consensus while S is unimplementable.*
2. *Your φ threshold is 12 and inter-arrivals are N(500 ms, 250 ms). A
   heartbeat is 1900 ms late. Suspect or not? What if σ were 100 ms?*
3. *Why does a lease built on an eventually-accurate detector still need a
   fencing token? (Hint: eventual is not never-wrong.)*
4. *Cassandra moved from accrual-only to SWIM-style probing. What does an
   indirect probe buy that a local φ computation cannot?*
5. *Design a detector for 50k cellular IoT gateways: which of the above
   knobs do you widen first, and why?*

## References

- Chandra & Toueg, "Unreliable Failure Detectors for Reliable Distributed
  Systems", JACM 43(2), 1996. DOI: 10.1145/226643.226647
- Chandra, Hadzilacos & Toueg, "The Weakest Failure Detector for Solving
  Consensus", JACM 43(4), 1996. DOI: 10.1145/234533.234549
- Hayashibara, Defago, Yared & Katayama, "The φ Accrual Failure Detector",
  SRDS 2004. DOI: 10.1109/RELDIS.2004.1353004
- Das, Gupta & Motivala, "SWIM: Scalable Weakly-consistent Infection-style
  Process Group Membership Protocol", DSN 2002. DOI: 10.1109/DSN.2002.1028914
- Dwork, Lynch & Stockmeyer, "Consensus in the Presence of Partial
  Synchrony", JACM 35(2), 1988. DOI: 10.1145/42282.42283
- Akka documentation, "Failure Detector" (φ implementation and defaults):
  <https://doc.akka.io/libraries/akka-core/current/typed/failure-detector.html>
2. Chandra & Toueg, "Unreliable failure detectors for reliable
   distributed systems", JACM 43(2), 1996,
   [doi:10.1145/226643.226647](https://doi.org/10.1145/226643.226647) -
   the completeness/accuracy classes this page's table summarizes.
3. Hayashibara, Defago, Yared, Katayama, "The phi accrual failure
   detector", SRDS 2004,
   [the paper](http://paperhub.s3.amazonaws.com/f516fdfa940caa08c679d3946b273128.pdf)
   - the phi definition and its parameterization.
4. [Raft scope paper page](https://raft.github.io/) - the canonical
   Raft references, including the failure-detector assumptions section
   of the extended paper.
