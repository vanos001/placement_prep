# Differentiated Services (DiffServ) QoS

Differentiated Services (**DiffServ**) is the architecture that dominates modern IP QoS. Instead of negotiating per-flow reservations across the network — the way its predecessor, IntServ/RSVP, did — DiffServ pushes **complexity to the edge** and keeps the **core simple**. Edge routers classify, mark, and shape traffic; interior routers look at a 6-bit field in each packet header and apply one of a small number of per-hop behaviours. The result is a system that scales to the entire Internet: there is no per-flow state in the core, and the only thing a transit router needs to do is read six bits and pick a queue.

This chapter covers the architecture, the code points, the per-hop behaviours (EF, AF, BE), the traffic-conditioning block, and the comparison with IntServ.

## The DSCP Field

DiffServ redefines the IPv4 **Type of Service** (ToS) octet (and the IPv6 **Traffic Class** octet) as follows:

```
Bit:    7 6 5 4 3 2 | 1 0
       ┌──────────┬──┐
       │   DSCP   │CU│
       └──────────┴──┘
        6 bits   2 bits
```

- **DSCP** (Differentiated Services Code Point): bits 0–5, six bits → **64 possible code points**.
- **CU** (Currently Unused): bits 6–7, historically the ECN (Explicit Congestion Notification) bits, now standardised in RFC 3168 for end-to-end congestion signalling.

The 6-bit DSCP field is **not backward-compatible** with the original IPv4 ToS precedence bits, but the upper three bits of the DSCP do correspond to a 3-bit precedence field, allowing a degree of interoperability.

### Class Selector (CS) Code Points

The eight code points of the form `xxx000` are the **Class Selector (CS)** code points, semi-compatible with the old IPv4 precedence. They are named `CS0` through `CS7`:

| DSCP name | Binary | Decimal | Old precedence |
|-----------|--------|---------|----------------|
| CS0 (default) | 000000 | 0 | Routine |
| CS1 | 001000 | 8 | Priority |
| CS2 | 010000 | 16 | Immediate |
| CS3 | 011000 | 24 | Flash |
| CS4 | 100000 | 32 | Flash Override |
| CS5 | 101000 | 40 | Critical / Internetwork Control |
| CS6 | 110000 | 48 | Internetwork Control (routing protocols) |
| CS7 | 111000 | 56 | Network Control (link-local) |

The Class Selector PHB provides at least the relative priority ordering inherited from old IP precedence.

## Per-Hop Behaviour (PHB) — the Core Abstraction

A **PHB** is a description of the *observable forwarding behaviour* a router applies to a class of packets at a single hop. The PHB abstraction is what makes DiffServ scale: routers in different administrative domains can implement the same PHB using entirely different schedulers (priority queue, WFQ, DWRR, …) as long as the externally observable treatment matches.

RFC 2474 defines the abstract requirements of a PHB; the concrete PHBs used in practice are:

| PHB | RFC | DSCP value | Purpose |
|-----|-----|-----------|---------|
| **Default (BE)** | 2474 | 000000 (CS0) | Best-effort forwarding, no QoS |
| **Class Selector (CSn)** | 2474 | xxx000 (n = 0..7) | Backward-compatible priority |
| **Expedited Forwarding (EF)** | 3246 | 101110 (46) | Low-loss, low-latency, low-jitter (PQ) |
| **Assured Forwarding (AF)** | 2597 | xxbaar0 (12 values) | Reliable delivery under congestion |

## Expedited Forwarding (EF) — RFC 3246

The EF PHB provides a "virtual leased line" service: packets marked EF experience **low loss, low latency, low jitter, and assured bandwidth** across a DiffServ domain. Conceptually, EF traffic should appear as if it traverses a dedicated link of capacity R bits/sec.

### Mechanism

The router must guarantee that the EF aggregate is served at a rate ≥ R (the configured EF rate) at every hop, *regardless of other traffic*. Implementation choices:

1. **Strict Priority Queue**: EF packets go to the head of the queue, served whenever the link is free.
2. **Weighted Fair Queueing with high weight**: EF gets a guaranteed share R; excess EF traffic is dropped (it must not starve best-effort traffic).
3. **Deficit Round Robin (DRR)** with a high quantum for the EF class.

### DSCP Value

The recommended DSCP for EF is `101110` (decimal **46**). RFC 3246 mandates that this code point maps to a queue receiving priority treatment, but allows networks to use other code points for EF as a matter of local policy.

### Misbehavior and Mitigation

The single biggest risk with EF is that a single non-conformant flow (e.g., a torrent of EF-marked packets from a misbehaving edge) can starve all other classes. RFC 3246 imposes strict policing:

- An edge policer must cap the EF rate to a configured PIR (Peak Information Rate) and a burst size B.
- Packets exceeding PIR or B are **dropped** (not demoted) at the edge.
- A "per-domain behaviour" (PDB) is used so that interior routers never see EF traffic above the reserved rate.

### Math of EF at the Edge

Suppose a node reserves R = 10 Mb/s for EF on a 100 Mb/s link, with a maximum burst B = 50,000 bytes. The token bucket for the EF policer has:

```
tokens added at rate R = 10 Mb/s, bucket capacity = B
```

For a flow to pass, its arrival times t_i must satisfy:

```
Σ_{j=1}^i s_j ≤ R (t_i - t_1) + B
```

where s_j is the size in bits of packet j. Packets beyond this bound are dropped. The result is that the EF aggregate entering the core is deterministically bounded; an interior PQ scheduler then sees only well-behaved EF traffic, so latency is bounded by:

```
D_max ≈ B / R + serialization_delay_per_hop
```

For B = 50,000 bytes = 400,000 bits, R = 10 Mb/s, the burst waiting time at a hop is at most 40 ms.

## Assured Forwarding (AF) — RFC 2597

The Assured Forwarding PHB group defines **four independent classes** (AF1 through AF4), each with **three drop-precedence levels** (low, medium, high). This gives 12 code points:

```
        Drop precedence
Class    Low (1)  Medium (2)  High (3)
─────────────────────────────────────────
AF1      AF11     AF12         AF13
AF2      AF21     AF22         AF23
AF3      AF31     AF32         AF33
AF4      AF41     AF42         AF43
```

The binary DSCP structure is `xxbbb0`, where `bb` is the class (1–4) and `aaa` is the drop precedence (1–3). For example, AF31 = `011010` (decimal 26).

### Forwarding Behaviour

- Each class gets a **separate queue** with a guaranteed bandwidth share.
- Within a class, packets are marked with drop precedence 1, 2, or 3 indicating relative importance.
- During congestion, the router preferentially drops precedence-3 packets, then precedence-2, then precedence-1, using **Weighted Random Early Detection (WRED)**.

### WRED example (AF class)

A router configures three WRED thresholds for AF class 1 on a 1 Gb/s link with queue depth limit 1000 packets:

| Drop precedence | Min threshold | Max threshold | Drop prob at max |
|-----------------|---------------|---------------|------------------|
| AF11 (low) | 700 | 1000 | 0.10 |
| AF12 (med) | 400 | 900 | 0.20 |
| AF13 (high) | 200 | 600 | 0.50 |

When the queue depth is, say, 450 packets: AF13 has been dropping for 250 packets already (avg drop prob ~25%), AF12 just started dropping (avg drop prob ~3%), and AF11 has not started dropping yet. This is the **graceful degradation** characteristic of AF — under mild congestion, only the lowest-precedence packets are shed; only under severe congestion does AF11 (the protected core of the class) start seeing drops.

### The Olympic Model

RFC 2597 recommends an "Olympic" interpretation: AF1 = Bronze, AF2 = Silver, AF3 = Gold, AF4 = Platinum, with decreasing probability of drop. (This is the historical source of cloud-provider tier names.)

## Best Effort (BE) — Default PHB

The default PHB (`DSCP = 000000`) gives standard best-effort forwarding. No guarantees on latency, jitter, loss, or throughput. RFC 2474 mandates that this code point be available and that all routers must support it without configuration.

## The Traffic Conditioning Block (TCB)

DiffServ defines a canonical set of elements at the network edge that condition inbound traffic before it enters the DiffServ domain. RFC 2475 names these as the canonical TCB:

```
                       DiffServ edge node

   Ingress ┌─────┐  ┌────────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────┐  Egress
   ───────▶│     │─▶│        │─▶│        │─▶│         │─▶│         │─▶│      │──────▶
           │ Cls │  │ Meter  │  │ Marker │  │ Dropper │  │ Shaper  │  │ Out  │
           │ ifr │  │        │  │        │  │         │  │         │  │ Q    │
           └─────┘  └────────┘  └────────┘  └─────────┘  └─────────┘  └──────┘

   1. Classifier   – matches on 5-tuple, DSCP, MAC, VLAN, etc.
   2. Meter        – measures rate vs. configured profile (token bucket).
   3. Marker       – sets the DSCP based on meter result (green/yellow/red).
   4. Dropper      – drops out-of-profile packets (or remarks to a lower class).
   5. Shaper       – buffers excess to smooth into the configured rate.
```

### Classifier

Matches packets by any combination of fields: 5-tuple (src/dst IP, src/dst port, proto), MAC, VLAN tag, ingress interface, or existing DSCP. The output is a **microflow** identifier feeding the meter.

### Meter

Compares the packet stream against a configured traffic contract. The standard meters are defined in RFC 2697 (**srTCM**, single-rate three-colour marker) and RFC 2698 (**trTCM**, two-rate three-colour marker). The meter produces a colour for each packet — green (in-profile), yellow (out-of-profile), red (severely out-of-profile).

### Marker

Sets the DSCP based on the colour. A typical AF mapping is:

| Colour | AF1 DSCP |
|--------|----------|
| Green  | AF11 (low drop precedence) |
| Yellow | AF12 (medium) |
| Red    | AF13 (high) |

The marker may also **re-mark** down on congestion, demoting high-priority traffic rather than dropping it. This is "color-aware" metering: a downstream meter trusts the colour already present in the packet and may only demote, never promote.

### Dropper

Packets coloured red (or yellow, under severe congestion) are dropped. Two common dropper modes:

- **Tail drop** per colour: when the per-colour queue limit is hit.
- **RED/WRED**: probabilistic drop based on queue depth, scaled per colour.

### Shaper

Buffers packets that arrive above the configured rate so that the departure rate is capped. Unlike the dropper, the shaper does not discard — it delays. Internally a token bucket: a packet can leave only when a token is available. Implemented in Linux as the **TBF (Token Bucket Filter)** qdisc and in Cisco IOS as `shape` policy-map commands.

## Per-Domain Behaviour (PDB)

A **PDB** (RFC 3086) describes the end-to-end service a customer sees crossing an entire DiffServ domain, not just one hop. A PDB is realised by composing edge conditioning + a PHB at each interior hop + consistent configuration. Two classic PDBs:

- **EF PDB**: low-latency, low-loss, low-jitter service. Composed of: edge policing to a contracted rate + strict-PQ EF PHB inside.
- **Assured-rate PDB**: rate-guaranteed but latency-variable service. Composed of: edge shaping + AF PHB inside.

## DiffServ vs. IntServ/RSVP

| Aspect | IntServ + RSVP | DiffServ |
|--------|----------------|----------|
| **Reservation unit** | Per flow (RSVP PATH/RESV signalling) | Per aggregate (DiffServ code point) |
| **State in core** | Per-flow soft state | None |
| **Signalling** | End-to-end (RSVP) | None; configured statically |
| **Scalability** | Limited (every router per-flow) | Internet-scale (per-hop lookups) |
| **Admission control** | Yes — per-flow at every hop | Yes — at the edge only |
| **Granularity** | Fine | Coarse (per-class) |
| **Best for** | Real-time per-flow (e.g., IPTV studio feeds, RSVP-controlled MPLS-TE) | Bulk Internet QoS, VPNs, ISP peering |

IntServ was the original IETF design (RFC 1633) — a host uses RSVP to install a per-flow reservation along the path, and each router must maintain soft state and run a per-flow scheduler. This simply does not scale: a backbone router carrying 1M concurrent flows would need 1M queue slots and 1M signalling refreshes. RFC 2475 (DiffServ) acknowledged this and pushed the complexity out.

**Hybrid**: MPLS Traffic Engineering (MPLS-TE) and RSVP-TE combine DiffServ with signalling for per-LSP bandwidth reservations. RFC 5460 ("Diffserv-aware traffic engineering" or DS-TE) provides pre-standard mechanisms; the modern form is RFC 8656, "Explicit Resource Allocation for MPLS Traffic Engineering".

## A Concrete End-to-End Example

Consider an enterprise with three traffic classes between two sites over a 100 Mb/s WAN link:

| Class | DSCP | Traffic | Rate cap |
|-------|------|---------|----------|
| EF (voice) | 46 | VoIP RTP | 8 Mb/s |
| AF31 (call signaling) | 26 | SIP/SDP | 2 Mb/s |
| AF11 (business-critical) | 10 | ERP/DB | 30 Mb/s |
| BE | 0 | everything else | 60 Mb/s |

Edge marking (at the LAN-WAN router):

```
1. Classify by 5-tuple: src/dst IP+port, proto=UDP, dst port 10000-20000 → EF
2. Meter EF at 8 Mb/s, burst 64 KB; in-profile → mark DSCP 46; out-of-profile → drop (NEVER demote EF).
3. Classify SIP/SDP → AF31; meter at 2 Mb/s, burst 32 KB; out-of-profile → remark AF33 (high drop precedence).
4. Classify ERP/DB server subnets → AF11; meter at 30 Mb/s, burst 256 KB; out-of-profile → remark AF13.
5. All else → DSCP 0 (BE), no metering.
```

Interior routers run a 4-class scheduler (priority queue + 3 DRR classes):

```
Queue 0 (EF, PQ):    strict priority, configured cap = 8 Mb/s
Queue 1 (AF3x, DRR): quantum = 5% of remaining BW, WRED thresholds for AF31/32/33
Queue 2 (AF1x, DRR): quantum = 45% of remaining BW, WRED thresholds for AF11/12/13
Queue 3 (BE,   DRR): quantum = 50% of remaining BW, tail drop at 1000 pkts
```

Net effect on the wire: VoIP traffic gets strict priority and bounded jitter; ERP traffic competes within its class but never falls behind best-effort; best-effort gets the leftovers.

## References

1. Nichols, K., Blake, S., Baker, F., Black, D. *Definition of the Differentiated Services Field (DS Field) in the IPv4 and IPv6 Headers*. RFC 2474, December 1998. — [https://www.rfc-editor.org/rfc/rfc2474](https://www.rfc-editor.org/rfc/rfc2474)
2. Blake, S., Black, D., Carlson, M., Davies, E., Wang, Z., Weiss, W. *An Architecture for Differentiated Services*. RFC 2475, December 1998. — [https://www.rfc-editor.org/rfc/rfc2475](https://www.rfc-editor.org/rfc/rfc2475)
3. Heinanen, J., Baker, F., Weiss, W., Wroclawski, J. *Assured Forwarding PHB Group*. RFC 2597, June 1999. — [https://www.rfc-editor.org/rfc/rfc2597](https://www.rfc-editor.org/rfc/rfc2597)
4. Davie, B., Charny, A., Bennet, J.C.R., Benson, K., Le Boudec, J.Y., Courtney, W., Davari, S., Firoiu, V., Stiliadis, D. *An Expedited Forwarding PHB (Per-Hop Behavior)*. RFC 3246, March 2002. — [https://www.rfc-editor.org/rfc/rfc3246](https://www.rfc-editor.org/rfc/rfc3246)
5. Grossman, D., Heinanen, J., McCloghrie, K., Perkins, C., Polk, T., Ramachandran, J., de Smet, P. *Differentiated Services Reauthentication and the effect of RFC 2597 precursors*. RFC 3260 (also clarifications to Diffserv). — [https://www.rfc-editor.org/rfc/rfc3260](https://www.rfc-editor.org/rfc/rfc3260)
6. Heinanen, J., Guérin, R. *A Single Rate Three Color Marker*. RFC 2697, September 1999. — [https://www.rfc-editor.org/rfc/rfc2697](https://www.rfc-editor.org/rfc/rfc2697)
7. Heinanen, J., Guérin, R. *A Two Rate Three Color Marker*. RFC 2698, September 1999. — [https://www.rfc-editor.org/rfc/rfc2698](https://www.rfc-editor.org/rfc/rfc2698)
8. Nichols, K., Carpenter, B. *Definition of Differentiated Services Per Domain Behaviors and Rules for their Specification*. RFC 3086, April 2001. — [https://www.rfc-editor.org/rfc/rfc3086](https://www.rfc-editor.org/rfc/rfc3086)
9. Braden, R., Clark, D., Shenker, S. *Integrated Services in the Internet Architecture: an Overview*. RFC 1633, June 1994. — [https://www.rfc-editor.org/rfc/rfc1633](https://www.rfc-editor.org/rfc/rfc1633)
10. Cisco. *QoS Architecture and Configuration Guide*. — [https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/qos/configuration/15-mt/qos-15-mt-book.html](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/qos/configuration/15-mt/qos-15-mt-book.html)
11. Linux Foundation. *Linux Advanced Routing & Traffic Control Howto: tc, HTB, and DSCP marking*. — [https://tldp.org/HOWTO/Adv-Routing-HOWTO/](https://tldp.org/HOWTO/Adv-Routing-HOWTO/)
12. Wikipedia: [Differentiated services](https://en.wikipedia.org/wiki/Differentiated_services).

## Interview Questions

1. Why does DiffServ push complexity to the network edge? What is the specific complexity it pushes, and what does the core see?
2. What is the DSCP field? How many code points are there, and why is the old IPv4 ToS precedence field only partially compatible?
3. Explain the difference between EF and AF. Why does RFC 3246 require EF traffic to be strictly poled at the edge?
4. List the four AF classes and the three drop-precedence levels. What is the "Olympic model" mapping?
5. Walk through the five elements of a Traffic Conditioning Block (classifier, meter, marker, dropper, shaper). What does each one do, and where is each located in the network?
6. Compare DiffServ and IntServ/RSVP along the dimensions of scalability, state, signalling, and admission control. Why did IntServ fail to scale to the Internet?
7. Given a DiffServ domain using EF on a 1 Gb/s link, configured rate 50 Mb/s and burst 100 KB, what is the upper bound on delay at a strict-PQ interior hop? What assumption must you make?
8. How does WRED combine with the AF PHB to provide graceful degradation under increasing congestion? Sketch the drop-probability curves.
