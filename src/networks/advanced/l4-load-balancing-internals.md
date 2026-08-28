# L4 Load-Balancing Internals: Data Paths, Maglev Hashing, and Replica State

An L7 proxy decides *where to route a request*. An L4 balancer answers a harder
question: *given one packet, which backend machine gets it, and who remembers
that decision for the next ten thousand packets of the flow?* Every design here
-- NAT vs DSR data paths, Maglev's lookup table, Ananta's two-level split,
Katran's XDP fast path -- is a different answer to one tension: **state is
expensive to share, but the flow decision must be stable**. The survey-level
picture (round robin vs least-conn, L4 vs L7) lives in
[LB algorithms](../load-balancing/algorithms.md),
[L4 vs L7](../load-balancing/l4-vs-l7.md), and
[Consistent Hashing](../../distributed/partitioning/consistent-hashing.md)
(ring/vnode mechanics, not re-derived here). This page stays at the packet path.

## Three data paths: what the balancer must remember

Every L4 balancer is one of three designs, distinguished by where the return
traffic goes and what state that implies:

| Property | NAT / DNAT | DSR | Full proxy |
|---|---|---|---|
| Forward path | LB rewrites dst IP/port | LB rewrites MAC or tunnels | LB terminates TCP, re-originates |
| Return path | back through the LB | direct backend -> client | back through the LB |
| LB per-flow state | required (conntrack) | none on fast path | required (2 sockets/flow) |
| Backend sees client IP? | no (unless preserved) | yes | no |
| LB bandwidth cost | 2x flow traffic | 1x (ingress only) | 2x + termination CPU |
| Passive health checking | possible | impossible | possible |

```text
     NAT / DNAT (symmetric)                 DSR (asymmetric return)
  client                                      client
     |  dst=VIP:443                             ^  src=VIP:443
     v                                          |  (never touches the LB)
  +--------+  DNAT: VIP:443 -> 10.0.0.7:443  +--------------------+
  | L4 LB  | -------------------------------> | backend 10.0.0.7   |
  | ct:    |                                 | VIP on lo (ARP off)|
  | flow->be <------------------------------- +--------------------+
  +--------+  SNAT: 10.0.0.7 -> VIP            v  raw L3 route to client
  (LB sees 100% of NAT packets, 0% of DSR return packets)
```

NAT is the default because it is symmetric: the LB counts bytes, sniffs RSTs,
and health-checks passively. DSR exists because that symmetry doubles the LB's
bandwidth bill -- Maglev and Katran both chose DSR so commodity boxes forward
only ingress traffic. But DSR is not just "don't NAT"; four traps:

1. **ARP suppression.** The VIP lives on a loopback/dummy interface and the
   backend must not answer ARP for it, or clients arp the backend's MAC
   directly and bypass the LB (the LVS "hidden interface" problem; Linux:
   `arp_ignore=1` / `arp_announce=2`; classic write-up:
   [LVS direct routing](http://www.linuxvirtualserver.org/VS-DRouting.html)).
2. **Tunnel overhead.** IP-in-IP (+20 B) or GUE turns a 1500 B client packet
   into a 1520 B inner frame: PMTUD must work, or the LB must clamp MSS on the
   SYN -- the one DSR packet that allows it.
3. **Asymmetric routing vs stateful middleboxes.** The return path carries TCP
   packets with no LB on the route; a stateful firewall that never saw the SYN
   drops them as unsolicited. DSR needs an unconstrained return path -- why it
   is a data-center/edge technique, not retrofittable behind corporate gear.
4. **Hairpin.** A backend calling a sibling *via the VIP* targets an IP its
   own kernel considers local (the VIP is on `lo`), so the connection
   short-circuits to itself. NAT balancers hairpin both rewrites; DSR fleets
   route backend-to-backend traffic over DIPs or an internal VIP.

## Stage one: routers, ECMP, and hash stability

Before any single balancer sees a packet, routers split VIP traffic across the
balancer fleet. Equal-cost multi-path (ECMP) does this with a hash over the
flow key -- stateless, but not *stable*: RFC 2992 shows a naive mod-N rehash
redistributes nearly every flow when a next-hop joins or leaves, while
highest-random-weight (HRW) keeps most flows pinned. The same math reappears
inside Maglev: a router rehashing breaks flows *to balancers*, a balancer
rehashing breaks flows *to backends* -- both layers need disruption-aware
hashing. The hash key is a policy choice:

| Hash key | Behavior | Failure mode |
|---|---|---|
| 2-tuple (src IP only) | all flows of one client pinned together | hot spots behind large NATs |
| 5-tuple (src, sport, dst, dport, proto) | per-flow spread, good balance | non-first IP fragments lack L4 headers; ICMP errors must be matched back |
| IPv6 flow label | sender-stamped stable L3 hash input | only if senders set it per RFC 6437 |

VIPs are also commonly **anycast**: the same VIP announced via BGP from every
PoP, clients landing on the nearest site, a site withdrawing its announcement
on failure. Anycast gives site-level balancing for free and pushes the
flow-stickiness problem down to the per-site balancer fleet.

## Maglev: a fixed lookup table plus per-replica connection tracking

Maglev (Google, NSDI'16) is the canonical design: commodity Linux servers sit
behind router ECMP, identically configured, each computing the same decision
from packet headers alone. Two data structures cooperate.

**The lookup table.** Fixed size M, prime (65521 in Google's production), built
once per backend-pool generation. For backend `b_i`, two hashes give
`offset_i = h1(b_i) mod M` and `skip_i = h2(b_i) mod (M-1) + 1`; because M is
prime and `skip_i != 0`, the sequence `offset_i + j*skip_i` (mod M) visits
*every* slot. Backends claim slots round-robin, each walking its own
permutation to the next unclaimed slot; a cap of `floor(M/n)` entries per
backend keeps the fill balanced (the two-population rule): in Population 1 a
backend claims only while it owns fewer than `floor(M/n)` entries; once all
reach the cap, Population 2 fills the remainder. The demo below runs this.

**Looking a packet up.** Hash the 5-tuple with *two* independent hash functions
to get two candidate entries; if they agree, done, otherwise take the backend
with greater weight. The dual probe smooths collisions -- and the *loser*
becomes the flow's **backup** backend.

**The connection tracking table.** Each Maglev keeps a per-replica flow table;
at flow setup it records primary and backup backend, and later packets of an
established flow hit this table first, bypassing the lookup. When a backend
dies the lookup table is rebuilt, but established flows keep their entry (or
fall to the backup) without the balancer ever having replicated state anywhere.
Maglev runs in two layers -- **Maglev Cluster** between routers and rack
balancers, **Maglev Host** for the last hop to destination hosts.

### What actually happens when a backend dies

The rebuild is the part people get wrong: the fill is sequential, so removing
one backend changes the claim order for *all* backends and reshuffles far more
than 1/n of the table. The demo builds a Maglev-style table, removes a backend,
rebuilds, and measures table churn and flow impact against mod-N hashing:

```python
# Maglev-style lookup table: build it, then measure disruption when a backend dies.
import hashlib

def H(seed, data): return int.from_bytes(hashlib.md5(f"{seed}:{data}".encode()).digest()[:8], "big")

def build_maglev_table(backends, M):
    """offset/skip permutations + two-population fill (see text above)."""
    n = len(backends)
    assert M > 1 and all(M % p for p in range(2, int(M ** 0.5) + 1)), "M must be prime"
    offset = [H(1, b) % M for b in backends]
    skip = [H(2, b) % (M - 1) + 1 for b in backends]
    table, nxt, owned = [-1] * M, [0] * n, [0] * n
    cap, filled = M // n, 0
    while filled < M:
        for i in range(n):
            if owned[i] >= cap or filled == M:
                continue
            while table[(offset[i] + nxt[i] * skip[i]) % M] != -1:
                nxt[i] += 1               # walk own permutation to next free slot
            table[(offset[i] + nxt[i] * skip[i]) % M] = i
            nxt[i] += 1
            owned[i] += 1
            filled += 1
        if all(x >= cap for x in owned):  # every backend hit the cap
            cap = M
    return table, owned

backends = [f"10.0.0.{i}" for i in range(1, 9)]   # n = 8
M = 1013                                          # prime, ~127x n
tbl, owned = build_maglev_table(backends, M)
print(f"table M={M}, n={len(backends)}; entries/backend min={min(owned)} max={max(owned)} "
      f"(ideal {M // len(backends)}); spread={100 * (max(owned) - min(owned)) / M:.2f}% of M")
alive = [b for b in backends if b != "10.0.0.4"]  # backend 10.0.0.4 dies
tbl2, _ = build_maglev_table(alive, M)
flows = [H(9, k) for k in range(100_000)]
stats = [
    ("lookup-table churn after backend death", 100 * sum(a != b for a, b in zip(tbl, tbl2)) / M),
    ("flows hashed to the dead backend", 100 * sum(tbl[f % M] == backends.index("10.0.0.4") for f in flows) / len(flows)),
    ("flows whose table entry changed", 100 * sum(tbl[f % M] != tbl2[f % M] for f in flows) / len(flows)),
    ("flows remapped by plain mod-N hashing", 100 * sum(backends[f % 8] != alive[f % 7] for f in flows) / len(flows)),
]
for label, pct in stats:
    print(f"{label}: {pct:.2f}%")
```

Output (real run):

```text
table M=1013, n=8; entries/backend min=126 max=127 (ideal 126); spread=0.10% of M
lookup-table churn after backend death: 61.70%
flows hashed to the dead backend: 12.65%
flows whose table entry changed: 61.47%
flows remapped by plain mod-N hashing: 87.57%
```

Read that carefully: the table churns 61.70% of entries on a single failure --
the sequential fill is far more fragile than a ring -- yet only the 12.65% of
flows pinned to the dead backend *must* move (conntrack redirects them to the
backup entry). Established flows survive because of the connection tracking
table, not the hashing; consistent hashing only minimizes disruption for *new*
connections and lets every replica reach the same answer without communicating.
Plain mod-N hashing (87.57%) offers neither property.

## Ananta: two-level balancing with indirect DSR

Ananta (Microsoft Research + Azure, SIGCOMM'13) attacks the same state problem
from the host side. Two levels: a layer of **MUXes** (software LBs) and a
**host agent** on every machine. Inbound, a MUX picks the destination host and
encapsulates; the agent delivers to the VM. The trick is **indirect DSR**: the
agent remembers which MUX it chose per flow and tunnels *response* packets back
through that same MUX, which just decapsulates and forwards -- so the MUX keeps
no per-flow state on its fast path, and ECMP can reshuffle inbound traffic
across MUXes without breaking a connection. Outbound, host agents perform SNAT
themselves, and a replicated table (the "Churn" database) at the MUX layer maps
SNAT'd flows back to the right agent. Where Maglev pushes state into
per-replica tables, Ananta pushes it all the way to the hosts.

## Katran: Maglev hashing in XDP

[Katran](https://github.com/facebookincubator/katran) (Meta) is the
open-source modernization of this lineage: a C++ library plus an eBPF program
running at XDP in NIC driver mode -- before `sk_buff` even exists (hook
taxonomy in [eBPF networking](../../networks/ebpf-networking.md), packet-path
position in [networking-advanced](../networking-advanced.md)). Its README is
unusually direct about the design: DSR-only forwarding, IP-in-IP encapsulation
with a *varying* outer source IP so the L7 tier behind it still gets NIC RSS
spread, a fixed-size per-CPU LRU connection tracking table (lockless, per RX
queue), and "modified Maglev hashing" for backend selection. Replicas share no
state; one instance can restart or drain without touching existing flows. The
cost is the DSR tax from above: no return-path visibility, hence built-in
active health checking.

## Replica state: synchronize it or design it away

| Approach | State location | Flow survival on replica loss | Cost |
|---|---|---|---|
| Stateful NAT + `conntrackd` sync | replicated conntrack tables | flows survive replica crash | sync bandwidth, replication lag, failover machinery |
| Stateless DSR + deterministic hashing | nowhere shared | flows keep working if another replica picks them up | none, but DSR constraints (return path, hairpin) |
| Stateless DSR + per-replica conntrack cache | per-replica LRU (Katran) / flow table (Maglev) | only flows on the dead backend break, until the backup entry takes over | table memory; hashing must be identical fleet-wide |

Rule of thumb: **NAT is a stateful protocol, so stateful NAT balancers must
replicate state; DSR makes balancer state optional, so they scale by
replicating *configuration* instead of *state*.** That is why every
planet-scale L4 balancer you can read about -- Maglev, Ananta, Katran -- is
DSR-shaped, and why a small-office IPVS NAT setup and a global anycast fleet
are structurally different animals, not just sizes.

## Health checking and the client IP problem

- **Active probes** (Maglev, Katran) hit each backend directly and remove
  failures from the next table generation. Mandatory under DSR: the LB never
  sees RSTs or retransmits, so it is otherwise blind.
- **Passive detection** (NAT/full-proxy) notices retransmission storms and
  RSTs in-band -- faster for gray failures, impossible under DSR.
- **Vantage matters.** A backend can answer probes from the LB yet fail from
  client paths (MTU, ACLs); weighted tables and slow-start keep a re-added
  backend from being crushed by a continent's anycast traffic. The LB only
  *stops sending* to a dead backend; draining is the backend's job.
- **Client IP.** DSR hands backends the true client IP for free; NAT and
  full-proxy do not. Escapes: **PROXY protocol** (the LB prepends a v1 text /
  v2 binary header with the original 4-tuple,
  [spec](https://www.haproxy.org/download/2.6/doc/proxy-protocol.txt)) or
  **TOA** (client IP in a TCP option + backend kernel module so
  `getpeername()` reports it -- common in LVS-derived cloud LBs).

## Failure modes worth memorizing

- Treating a NAT balancer as stateless: conntrack exhaustion silently
  blackholes new flows while established ones sail through.
- Enabling DSR without ARP suppression: backends answer ARP for the VIP and
  traffic intermittently bypasses the LB -- the worst kind of flaky.
- Hashing fragments inconsistently: 5-tuple on the head, IP-only on non-first
  fragments (they lack L4 headers) sends one flow to two backends.
- Forgetting that ECMP rehash *upstream* of the balancer also breaks flows:
  the RFC 2992 mod-N analysis applies at both layers. IPIP DSR without MSS
  handling: 1500 B + 20 B tunnel = silent blackholes for max-MTU senders.
- Assuming consistent hashing saves established flows: it does not -- conntrack
  (or indirect DSR) does. The 61.70% churn in the demo is the proof.

## Cross-references

- [Data-Center TCP: Incast Collapse](datacenter-tcp.md) -- what backend TCP
  stacks experience under L4-balanced fan-out.
- [Networking Advanced](../networking-advanced.md) -- packet hooks (XDP/TC/
  netfilter) these fast paths exploit; also a survey-level LB mention.
- [LB Algorithms](../load-balancing/algorithms.md),
  [L4 vs L7](../load-balancing/l4-vs-l7.md), and
  [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) --
  selection algorithms, the layer split, and ring/vnode/HRW mechanics.

## References

- [Maglev: A Fast and Reliable Software Network Load Balancer, Eisenbud et al., USENIX NSDI 2016](https://www.usenix.org/conference/nsdi16/technical-sessions/presentation/eisenbud)
- [Ananta: Cloud Scale Load Balancing, Patel et al., ACM SIGCOMM 2013](https://doi.org/10.1145/2486001.2486026)
- [Katran: a high-performance L4 load balancing forwarding plane (Meta open source)](https://github.com/facebookincubator/katran)
- [RFC 2992: Analysis of an Equal-Cost Multi-Path Algorithm](https://www.rfc-editor.org/rfc/rfc2992.html)
