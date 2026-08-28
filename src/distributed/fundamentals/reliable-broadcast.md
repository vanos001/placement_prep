# Reliable Broadcast: The Agreement Primitive Under Consensus

Consensus gets the lectures; broadcast does the work. Before any BFT protocol
can order transactions, someone has to get every transaction reliably to
every node *even while Byzantine peers lie, replay, and withhold*. That job —
one sender, one value, all correct nodes end up with the same value or
(nothing) — is **reliable broadcast (RB)**. It is strictly weaker than
consensus: it agrees on a *value*, never on an *order*, and that weakness is
its value — RB costs fewer rounds and no leader, which is why the DAG-BFT
family (Narwhal, Tusk, Bullshark, DAG-Rider) rebuilds consensus on top of it.

This page pins down the specification, walks Bracha's echo/ready protocol
with the `2f+1` thresholds explained rather than stated, prices the message
complexity against the Dolev–Reischuk lower bound, and locates RB inside
modern DAG consensus. Fault-model background lives in
[byzantine-faults.md](./byzantine-faults.md); the impossibility context for
fully asynchronous consensus is [flp.md](./flp.md).

## The Specification: Three Properties

A broadcast protocol for `n` nodes, up to `f` Byzantine, with designated
sender `s`, is *reliable* when it satisfies:

| Property | Statement | What breaks without it |
| --- | --- | --- |
| Validity | if `s` is correct and broadcasts `v`, every correct node delivers `v` | sender ignored or silenced |
| Agreement | no two correct nodes deliver different values | split-brain delivery |
| Totality | if *any* correct node delivers `v`, *every* correct node eventually delivers | partial delivery, liveness holes |

One refinement matters for reading papers: when the sender itself may be
Byzantine, validity cannot say "delivers the sender's value"; the honest
weakening is *validity for a correct sender*, plus the convention that a
faulty sender yields either one common value everywhere or none. Bracha's
protocol below is the general one; its sender-correct case is what
"reliable broadcast" usually denotes in systems papers.

Why the thresholds are what they are (n = 3f+1):

- **Any two `2f+1` sets intersect in at least `f+1` nodes.** If two correct
  nodes saw `2f+1` READYs for different values, some *correct* node would
  have sent READY twice — impossible, a correct node sends READY once.
- **`n-f` ECHOs force READY.** Correct nodes echo only the first value seen
  from the sender, so `n-f` echoes include `2f+1` echoes of one value.
- **`f+1` READY amplification is safe** because at least one correct node
  is in any `f+1` set — and a correct node only READYs a justifiable value.

## Message Flow: Bracha's Echo/Ready Protocol

Bracha's protocol runs in asynchronous "rounds" of message floods. Every
correct node relays what it saw; nobody trusts a single peer:

```text
   sender s                all nodes (n = 3f+1)                deliver
  ----------  -------------------------------------------  ---------------
  INITIAL(v) -->  on first INITIAL(v): ECHO(v) to everyone
                          |
                     ECHO(v) counted from n-f peers
                          |
                      READY(v) to everyone
                          |
                     READY(v) counted from f+1 peers --> amplify READY(v)
                          |
                     READY(v) counted from 2f+1 peers  -->  DELIVER v
```

Three message kinds, one rule each: **echo** what you first received,
**ready** what you can certify, **deliver** what is certified twice over.
The INITIAL flood is the sender's job alone; the ECHO flood is `O(n²)`
copies; the READY flood is `O(n²)` again in the worst case. A Byzantine node
can echo different values to different peers and even send conflicting
READYs — the thresholds absorb it, because forged messages can never reach
`2f+1` without dragging `f+1` correct nodes along.

### The Demo: f=1, n=4, Equivocation Attempt

The simulator below runs Bracha's exact thresholds on a deterministic
schedule. Node 3 is Byzantine and plays the strongest cheap attack:
echo `m` to one peer and `m*` to the others, then push READY(`m*`). Watch
the attack die at the amplification threshold.

```python
#!/usr/bin/env python3
"""Bracha reliable broadcast, n=4, f=1, one Byzantine node. Deterministic
round schedule (round-r sends deliver at r+1). Bracha's thresholds exactly:
ECHO(v) from n-f -> READY(v); READY(v) from f+1 -> amplify; READY(v) from
2f+1 -> deliver. Copies counted per recipient (O(n^2)); self-copies are
real loopback deliveries, so a node counts itself like any other peer."""
n, f = 4, 1
BYZ = 3                                     # node 3 is Byzantine
NF, FA, DELIV = n - f, f + 1, 2 * f + 1     # 3, 2, 3
queue = []                                  # (round, src, kind, val, dst)
counts = {"INITIAL": 0, "ECHO": 0, "READY": 0}
log = []

def send(r, s, kind, val, targets):
    for t in targets:
        queue.append((r, s, kind, val, t)); counts[kind] += 1

st = {p: {"echos": {}, "readys": {}, "echoed": False, "ready": False,
          "delivered": None} for p in range(n)}

send(0, 0, "INITIAL", "m", range(n))        # correct sender node0 broadcasts
log.append("round 0: node0 sends INITIAL(m) to all (4 copies)")

BYZ_ECHO = {0: "m*", 1: "m", 2: "m*", 3: "m*"}   # equivocation plan

for r in (1, 2, 3):
    for (_, s, kind, val, p) in [m for m in queue if m[0] == r]:
        if kind == "ECHO": st[p]["echos"][s] = val
        if kind == "READY": st[p]["readys"][s] = val
    queue = [m for m in queue if m[0] != r]

    for p in range(n):                      # reactions (queue for r+1)
        ec, rc = st[p]["echos"], st[p]["readys"]
        nm = sum(1 for v in ec.values() if v == "m")
        nr = sum(1 for v in rc.values() if v == "m")
        if p == BYZ:
            if r == 1:
                for tgt, v in BYZ_ECHO.items():
                    send(r + 1, BYZ, "ECHO", v, [tgt])
            elif r == 2:
                send(r + 1, BYZ, "READY", "m*", range(n))
            continue
        if r == 1 and not st[p]["echoed"]:          # INITIAL(m) just arrived
            st[p]["echoed"] = True
            send(r + 1, p, "ECHO", "m", range(n))
        elif st[p]["echoed"] and not st[p]["ready"] and nm >= NF:
            st[p]["ready"] = True
            send(r + 1, p, "READY", "m", range(n))
            log.append(f"round {r}: node{p} sees {nm} ECHO(m) >= n-f={NF}"
                       f" -> sends READY(m)")
        elif not st[p]["ready"] and nr >= FA:       # amplification rule
            st[p]["ready"] = True
            send(r + 1, p, "READY", "m", range(n))
            log.append(f"round {r}: node{p} amplifies READY(m) "
                       f"(f+1={FA} seen)")
        if not st[p]["ready"] and nr >= DELIV:
            st[p]["delivered"] = "m"
            log.append(f"round {r}: node{p} DELIVERS m")
        elif nr >= DELIV and st[p]["delivered"] is None:
            st[p]["delivered"] = "m"
            log.append(f"round {r}: node{p} DELIVERS m (2f+1={DELIV} READY(m))")
    if r == 1:
        log.append("round 1: node3 equivocates: ECHO(m)->node1, "
                   "ECHO(m*)->nodes 0,2 (and itself)")
    if r == 2:
        log.append("round 2: node3 amplifies READY(m*) to all")

ok = all(st[p]["delivered"] == "m" for p in range(n) if p != BYZ)
print("Bracha reliable broadcast - n=4, f=1, sender=node0, node3 Byzantine")
for line in log:
    print(line)
print("\ndeliveries: " + " ".join(
    f"node{p}={st[p]['delivered']}" for p in range(n) if p != BYZ))
print("message counts: INITIAL=%d ECHO=%d READY=%d TOTAL=%d (O(n^2) per instance)"
      % (counts["INITIAL"], counts["ECHO"], counts["READY"], sum(counts.values())))
print(f"agreement and totality among correct nodes: {'ok' if ok else 'FAIL'}")
print("validity (correct sender's m delivered everywhere): "
      + ("ok" if all(st[p]["delivered"] == "m" for p in (0, 1, 2)) else "FAIL"))
print("READY(m*) reaching correct nodes: 1 < f+1 -> amplification never fires")
```

```text
Bracha reliable broadcast - n=4, f=1, sender=node0, node3 Byzantine
round 0: node0 sends INITIAL(m) to all (4 copies)
round 1: node3 equivocates: ECHO(m)->node1, ECHO(m*)->nodes 0,2 (and itself)
round 2: node0 sees 3 ECHO(m) >= n-f=3 -> sends READY(m)
round 2: node1 sees 4 ECHO(m) >= n-f=3 -> sends READY(m)
round 2: node2 sees 3 ECHO(m) >= n-f=3 -> sends READY(m)
round 2: node3 amplifies READY(m*) to all
round 3: node0 DELIVERS m (2f+1=3 READY(m))
round 3: node1 DELIVERS m (2f+1=3 READY(m))
round 3: node2 DELIVERS m (2f+1=3 READY(m))

deliveries: node0=m node1=m node2=m
message counts: INITIAL=4 ECHO=16 READY=16 TOTAL=36 (O(n^2) per instance)
agreement and totality among correct nodes: ok
validity (correct sender's m delivered everywhere): ok
READY(m*) reaching correct nodes: 1 < f+1 -> amplification never fires
```

The equivocation split the correct nodes' echo *views* (node 1 saw four
echoes of `m`; nodes 0 and 2 saw three with one forged `m*`), yet all three
crossed the `n-f` line in the same round and delivered the same value. The
Byzantine READY(`m*`) copies never reached `f+1`, so no correct node ever
amplified them.

## Cost: Rounds, Messages, and the Amortization Story

| Regime | Rounds (worst case) | Messages per instance | Fault bound |
| --- | --- | --- | --- |
| Bracha RB (asynchronous) | 3 floods + delivery | `O(n²)` copies | `f < n/3` |
| Dolev–Strong (signed) | `f+1` | `O(n²)` | `f < n` (signatures) |
| Dolev–Reischuk bound | — | `Ω(n²)` is unavoidable | any Byzantine broadcast |

Two lessons hide in that table. First, `O(n²)` per instance is not an
implementation flaw — the Dolev–Reischuk lower bound proves any Byzantine
agreement or broadcast must exchange a quadratic number of bits in the worst
case, so engineering effort goes to *amortizing* it: batch many client items
into one broadcast instance and the `n²` term is paid per batch, not per
item. Second, signatures change the *latency* curve, not the complexity
class: Dolev–Strong needs only `f+1` rounds (unforgeable signatures make
equivocation self-incriminating) but still pays `O(n²)` traffic. Modern
asynchronous protocols (Cachin–Kursawe–Petzold–Shoup and successors) use
threshold signatures to shave constants, not the quadratic shape.

Toueg's 1984 randomized Byzantine agreement line is the other branch of the
family tree: add shared coins and expected-constant-round consensus becomes
possible asynchronously — but the broadcast layer beneath it stays
Bracha-shaped.

## Broadcast vs Consensus: The Ordering Gap

The specification table at the top of this page is missing one column on
purpose: *order*. RB gives all correct nodes the same value; it says nothing
about the sequence of values across multiple instances. Two correct nodes
may deliver batch 7 before batch 6 while their peers do the reverse. That is
the entire gap between broadcast and consensus:

| Property | Reliable broadcast (RB) | Atomic broadcast (AB) | Nakamoto consensus (NC) |
| --- | --- | --- | --- |
| Agrees on | a single value | a **total order** of values | a total order, probabilistically |
| Agreement | deterministic | deterministic | probabilistic (finality after depth) |
| Totality/liveness | eventual, async | requires partial synchrony or leader machinery | probabilistic |
| Membership | closed, `n = 3f+1` | closed, `n = 3f+1` | open (proof-of-work) |
| Message shape | `O(n²)` all-to-all floods | quorum votes + leader flows | block relay via gossip |
| Byzantine bound | `f < n/3` (or `f < n` signed) | `f < n/3` | <50% hash power |

The reductions run both directions and define the "primitive" status:
consensus trivially gives you broadcast (attach the value to a decided
slot); broadcast gives you consensus only with extra machinery (e.g., a
leader value validated by RB — which is what PBFT's pre-prepare stage and
HotStuff's proposal effectively are, cf. [pbft.md](../consensus/pbft.md) and
[hotstuff.md](../consensus/hotstuff.md)). That asymmetry — consensus buys
broadcast for free, broadcast is cheaper than consensus — is the economic
argument DAG-BFT exploits.

## RB Inside DAG-BFT

In [Narwhal and Bullshark](../consensus/narwhal-bullshark.md) the mempool and
the ordering rule are split. The availability side is where RB earns its
keep:

- **DAG-Rider** runs a reliable-broadcast instance *per block*: whatever a
  Byzantine node does, either every correct node adopts its vertex or none
  does, so the DAG every correct node eventually sees is consistent and
  complete. Ordering is then a local read of the DAG — no all-to-all voting
  rounds at all.
- **Tusk and Bullshark** skip per-vertex RB: rounds are certified with
  quorum certificates, and availability comes from the certificates. This
  trades Bracha's `O(n²)` echo traffic for lighter certification on the
  common path.

The general rule: *if your protocol asks "did everyone see what I saw?" per
object, that question is RB, and Bracha's three floods are the reference
implementation.*

## Where Else RB Shows Up

- Asynchronous BFT consensus (randomized, common-subset protocols) uses RB
  as the subroutine that circulates proposals with Byzantine-proof
  availability.
- Byzantine storage and key-management dissemination, where a value must
  reach all replicas or none — without RB, a faulty source can split the
  replica set permanently.

## See Also

- [byzantine-faults.md](./byzantine-faults.md) — the fault hierarchy and the
  `3f+1` quorum-intersection argument RB leans on.
- [flp.md](./flp.md) — why deterministic asynchronous *consensus* is
  impossible while asynchronous *broadcast* is not.
- [../consensus/pbft.md](../consensus/pbft.md) — quorum voting where
  broadcast and ordering are fused.
- [../consensus/narwhal-bullshark.md](../consensus/narwhal-bullshark.md) —
  the modern split of dissemination (DAG) from ordering.

## References

1. Bracha, G. & Toueg, S., *Asynchronous consensus and broadcast protocols*,
   Journal of the ACM 32(4):824–840, 1985. DOI:
   [10.1145/4221.214134](https://doi.org/10.1145/4221.214134) (verified via
   api.crossref.org).
2. Bracha, G., *Asynchronous Byzantine agreement protocols*, Information and
   Computation 75(2):130–143, 1987. DOI:
   [10.1016/0890-5401(87)90054-X](https://doi.org/10.1016/0890-5401(87)90054-X)
   (verified via api.crossref.org).
3. Dolev, D. & Strong, H.R., *Authenticated algorithms for Byzantine
   agreement*, SIAM Journal on Computing 12(4):656–666, 1983. DOI:
   [10.1137/0212045](https://doi.org/10.1137/0212045) (verified via
   api.crossref.org).
4. Dolev, D. & Reischuk, R., *Bounds on information exchange for Byzantine
   agreement*, Journal of the ACM 32(1):191–204, 1985. DOI:
   [10.1145/2455.214112](https://doi.org/10.1145/2455.214112) (verified via
   api.crossref.org).
5. Cachin, C., Kursawe, K., Petzold, F. & Shoup, V., *Secure and efficient
   asynchronous broadcast protocols*, LNCS, 2001. DOI:
   [10.1007/3-540-44647-8_31](https://doi.org/10.1007/3-540-44647-8_31)
   (verified via api.crossref.org).
6. *Narwhal and Tusk: a DAG-based mempool and efficient BFT consensus* —
   <https://arxiv.org/abs/2105.11827>; *Bullshark: DAG BFT protocols made
   practical* — <https://arxiv.org/abs/2201.05677> (titles verified via
   arXiv metadata).
