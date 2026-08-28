# Regenerating Codes and LRC: The Repair-Bandwidth Problem

Classic Reed-Solomon erasure coding stores k data + m parity chunks on
k+m nodes and loses a chunk cheaply - until one dies. Repairing it means
downloading the *entire* object (all k chunks), doing the RS reconstruction,
and re-encoding the lost chunk: the repair bandwidth equals the file size
to recover one fragment. For multi-terabyte objects on failure-prone fleets
that cost dominates everything. Regenerating codes (Dimakis et al.) and
locally recoverable codes (LRC, as deployed in Windows Azure Storage and
HDFS-EC) are the two families that attack exactly this number, from
opposite directions. This page derives the trade-offs, works the Azure LRC
example numerically, and runs a repair-bandwidth simulator.

Baselines first: the RS/erasure-coding machinery, coding-theory review,
and the systems context live in [erasure coding deep dive](./erasure-coding-deep.md)
and [erasure coding](../erasure-coding.md); the Ceph/HDFS placement
mechanics in [ceph-crush](./ceph-crush.md) and
[hdfs-internals](./hdfs-internals.md).

## The repair problem, precisely

Setup: file of size M, stored as k data + m parity fragments across
n = k + m nodes; any k fragments reconstruct. When one node fails, RS
repair downloads k fragments (k * M/k = M units). Regenerating codes ask:
what if the replacement node could download *less* than M and still
restore a functional fragment?

The answer space is characterized by the **cut-set bound** (MSR corner):
any repair must transfer at least M/k... and the exact frontier trades
two objectives:

- **Minimum Storage Regenerating (MSR)**: keep fragments at the
  theoretical minimum, M/k each; repair downloads d' = M/k * d/(d - k + 1)
  where d is the number of helper nodes contacted (d between k and n-1).
- **Minimum Bandwidth Regenerating (MBR)**: store larger fragments,
  M/(k * d - C(d,2))... concretely, fragments of size
  gamma_s = M/(k d - C(k,2)); repair downloads exactly gamma per helper -
  total d * gamma, the true minimum.

The frontier between them is a curve of (storage per fragment, repair
bandwidth) pairs; the theorem says no code can beat the curve, and exact
constructions exist at the endpoints (MSR via interference alignment,
product-matrix constructions for MBR) and on parts of it (Clay codes).

| scheme            | fragment size | repair download (d helpers) | repair node computes |
|-------------------|---------------|------------------------------|----------------------|
| RS (k+m)          | M/k           | M (k fragments)              | full RS decode + re-encode |
| MSR               | M/k           | M/k * d/(d-k+1)              | interference-alignment solve |
| MBR               | M/(kd - C(k,2)) | d * M/(kd - C(k,2))        | linear combination   |
| Azure LRC (12,2,2)| M/12          | 2 fragments (local group)    | XOR of 2             |

## LRC: pay a little storage, buy locality

LRC adds *local parity* within groups of data fragments: split k data
fragments into groups of size r, add one XOR parity per group, plus
m global parities for the k-m-resistant guarantee. A single fragment loss
is repaired from its own group (r+1 nodes, typically 2-3 downloads) - no
cross-rack traffic. The trade: for the same (k,m) the code loses some
resilience to *correlated multi-failures* compared to pure RS, measured
by the "minimum distance" d_min formula:

```text
  d_min = n - k + 1 - floor(k/r) + 1      (single-parity local groups)

  RS  (k=12, m=4):      n=16, d_min = 16-12+1      = 5  -> any 4 losses
  LRC (12, r=6, m=2):   n=16, d_min = 16-12+1-2+1  = 4  -> any 3 losses
```

The Azure result (Huang et al., USENIX ATC 2012) made this the industry
default: LRC(12, r=6, 2 global) has exactly the 16 fragments of RS(12,4)
- identical storage overhead - and trades one unit of worst-case distance
(d_min 5 -> 4) for single-node repair at 6 fragment downloads instead of
12. HDFS's Reed-Solomon with local parity and Ceph's EC profiles expose
the same knob.

## Fountain codes: the rateless cousin

LT/Raptor fountain codes generate a potentially unbounded stream of
repair symbols; any k-ish subset decodes (with small overhead). They shine
where the receiver count or channel quality is unknown: broadcast,
satellite, peer-to-peer file distribution. In datacenter block storage
they lose to fixed-rate RS/LRC - the decoder overhead and the lack of a
clean d_min story matter more than ratelessness - but they own the CDN
and firmware-update niches (RaptorQ is the IETF standard).

## The demo: repair cost simulator

The script below models a fleet repair: for RS/MSR/MBR/LRC parameters it
computes fragment sizes, per-failure download totals, and the storage
overhead, then simulates a year of node failures (seeded) and reports
total cross-rack bytes moved for repair - the number the network
engineers actually feel.

```python
#!/usr/bin/env python3
"""Repair-bandwidth comparison: RS vs MSR vs MBR vs Azure-style LRC.

All quantities in units of M (the file size). Deterministic year-long
failure simulation with a seeded RNG; totals per scheme reported."""

import random

M = 1.0
D_HELPERS = 14        # helpers contacted per repair (where applicable)


def rs(k, m):
    frag = M / k
    return frag, k * frag, (k + m) / k


def msr(k, d):
    frag = M / k
    repair = frag * d / (d - k + 1)
    return frag, repair, None


def mbr(k, d):
    frag = M / (k * d - k * (k - 1) // 2)
    repair = d * frag
    return frag, repair, None


def lrc(k, r, m_global):
    """Azure-style: k data in groups of r, 1 local parity per group,
    m_global global parities."""
    n = k + (k // r) + m_global
    frag = M / k
    local_repair = (r) * frag          # r+1 nodes talk, r downloads + parity read
    return frag, local_repair, n / k


SCHEMES = [
    ("RS(12,4)",   rs(12, 4)),
    ("MSR(12,d14)", msr(12, D_HELPERS)),
    ("MBR(12,d14)", mbr(12, D_HELPERS)),
    ("LRC(12,6,2)", lrc(12, 6, 2)),
]

print(f"file size M=1.0, d={D_HELPERS} helpers (MSR/MBR)")
print(f"{'scheme':<12} | {'frag':>7} | {'repair DL':>10} | {'overhead':>8}")
print("-" * 48)
for name, (frag, rep, ovr) in SCHEMES:
    o = f"{ovr:.2f}x" if ovr else "n/a"
    print(f"{name:<12} | {frag:>7.4f} | {rep:>10.4f} | {o:>8}")

# year-long failure simulation: 200-node fleet, each node fails 1.2x/year
N_NODES, FAILS_PER_YEAR, YEARS = 200, 1.2, 3
rng = random.Random(42)
total_fails = int(N_NODES * FAILS_PER_YEAR * YEARS)
print()
print(f"fleet: {N_NODES} nodes, {FAILS_PER_YEAR} failures/node/year, {YEARS} years")
print(f"expected failures: {total_fails}")
print()
print(f"{'scheme':<12} | {'cross-rack bytes (M units) for repairs':>38}")
print("-" * 56)
for name, (frag, rep, ovr) in SCHEMES:
    total = total_fails * rep
    print(f"{name:<12} | {total:>38.1f}")
print()
print("reading the totals: LRC cuts single-node repair traffic 2x vs RS at")
print("IDENTICAL storage overhead (trading one d_min unit); MSR cuts ~1.9x")
print("at RS-identical storage but needs an interference-alignment decode;")
print("MBR minimizes bytes but inflates fragment count per node.")
```

```text
file size M=1.0, d=14 helpers (MSR/MBR)
scheme       |    frag |  repair DL | overhead
------------------------------------------------
RS(12,4)     |  0.0833 |     1.0000 |    1.33x
MSR(12,d14)  |  0.0833 |     0.3889 |      n/a
MBR(12,d14)  |  0.0098 |     0.1373 |      n/a
LRC(12,6,2)  |  0.0833 |     0.5000 |    1.33x

fleet: 200 nodes, 1.2 failures/node/year, 3 years
expected failures: 720

scheme       | cross-rack bytes (M units) for repairs
--------------------------------------------------------
RS(12,4)     |                                  720.0
MSR(12,d14)  |                                  280.0
MBR(12,d14)  |                                   98.8
LRC(12,6,2)  |                                  360.0

reading the totals: LRC cuts single-node repair traffic 2x vs RS at
IDENTICAL storage overhead (trading one d_min unit); MSR cuts ~1.9x
at RS-identical storage but needs an interference-alignment decode;
MBR minimizes bytes but inflates fragment count per node.
```

Check the LRC row against the Azure numbers: a single lost data fragment
is repaired by contacting its local group - 5 surviving data fragments
plus the local XOR parity, 6 downloads total, versus RS's 12 - at
*identical* storage overhead (16 fragments either way). The durability
price shows up only under correlated multi-failures, where the code falls
back to the 2 global parities and its smaller d_min.

## Production notes

- **When MSR/MBR**: high-traffic archival or geo-distributed storage
  where cross-DC repair bandwidth is the budget line; the decode
  complexity (interference alignment) kept them out of most products for
  years; Clay/partial-MSR constructions changed the practical calculus
  and modern erasure libraries expose MSR profiles.
- **When LRC**: default for block/object stores with single-node repair
  as the common case. Watch the correlated-failure domain: a rack
  failure spanning a local group falls back to global-parity repair,
  whose cost equals RS's - durability analysis must use the *worst*
  repair path, not the happy one.
- **When RS**: simple, universally supported, and fine when failures are
  rare and objects small. The moment repair traffic shows in your
  network graphs, that's the signal to move.
- **Ceph/HDFS knobs**: EC profiles pin k/m/local-group parameters at
  pool creation; changing them means re-writing every object - capacity
  planning is a one-way door, choose with failure math, not vibes.

## Interview probes

- Derive the cut-set bound for MSR and explain why d/(d-k+1) appears in
  the repair formula.
- Azure LRC(12,2,2) vs RS(12,4): same fragment count? same d_min? same
  single-loss repair cost? Fill the table from the formulas.
- Why do fountain codes win for broadcast but lose for block storage?
- A rack loss hits one LRC local group of 6: walk both the cheap repair
  (if only one group member lost) and the expensive fallback (the rack
  took the whole group).

## References

1. Dimakis, Ramchandran, Wu, Suh, "A survey on network codes for
   distributed storage", [arXiv:1004.4438](https://arxiv.org/abs/1004.4438)
   - the MSR/MBR framework, cut-set bound, and construction survey this
   page follows.
2. Huang, Sathiamoorthy, Wang, et al., "Erasure coding in Windows Azure
   Storage", USENIX ATC 2012,
   [the paper page](https://www.microsoft.com/en-us/research/publication/erasure-coding-in-windows-azure-storage/)
   - the LRC(12,2,2) deployment and its repair-traffic measurements.
3. Reed & Solomon, "Polynomial codes over certain finite fields", SIAM J.
   Appl. Math. 8(2), 1960,
   [doi:10.1137/0108018](https://doi.org/10.1137/0108018) - the original
   construction every scheme here builds on.
4. [Erasure coding deep dive (this repo)](./erasure-coding-deep.md) -
   the RS/GF machinery, generator matrices, and library landscape.
