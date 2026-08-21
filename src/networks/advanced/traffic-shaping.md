# Traffic Shaping and Policing

Two classical mechanisms enforce a traffic contract between a customer and a network: **shaping** delays excess traffic so that the departure rate stays within bounds, while **policing** drops (or re-marks) excess traffic the instant it exceeds the contract. Both are built around the **token bucket** and the closely related **leaky bucket** algorithms. This chapter derives the formulas, walks through the standard three-colour markers (RFC 2697 and RFC 2698), and shows how they are configured in Linux `tc` (TBF, HTB, and the qdisc layer) and Cisco IOS.

## Why Two Mechanisms?

Imagine a customer paying for a 10 Mb/s CIR (Committed Information Rate) on a 100 Mb/s access link.

- **Shaping**: if the customer sends a 20 Mb/s burst, the shaper buffers the excess and paces it out at 10 Mb/s. The downstream network always sees ≤10 Mb/s. The cost is **latency** for the queued packets; the benefit is **no loss**.
- **Policing**: if the customer sends a 20 Mb/s burst, the policer drops (or marks down) the excess immediately. The downstream network still sees the burst, but anything above 10 Mb/s is shed. The cost is **packet loss**; the benefit is **no added latency and no buffering**.

Shaping is appropriate when the contract is about the *rate the network commits to carry* and the application tolerates delay (e.g., a VPN interconnect). Policing is appropriate when the contract is about *what traffic the network will accept at all* and the application cannot afford additional latency (e.g., real-time voice, where added buffering would be worse than loss).

The two are often combined: an edge node **shapes** downstream traffic to a policer's contract rate, eliminating drops entirely.

## The Token Bucket

A token bucket is defined by two parameters:

- **Rate R** (bytes/sec): the rate at which tokens are added to the bucket.
- **Bucket capacity / burst size B** (bytes): the maximum number of tokens that can be stored.

A packet of size s bytes can be transmitted if and only if the bucket holds ≥ s tokens; otherwise it is queued (shaper) or dropped (policer). When transmitted, s tokens are removed. Tokens are added at rate R but capped at B (so a long idle period does not accumulate unbounded credit).

### Steady-state behaviour

Let a(t) be the cumulative arrival (in bytes) at the shaper/policer up to time t, and d(t) the cumulative departure. The token bucket enforces the constraint, for any interval [t_1, t_2]:

```
d(t_2) - d(t_1) ≤ R (t_2 - t_1) + B
```

That is, over any time window of length Δt, no more than `R·Δt + B` bytes can depart. The "+B" is the **burst allowance**: a single burst of up to B bytes can be sent instantly (provided the bucket was full), but the *long-term rate* cannot exceed R.

### Worked example

A shaper is configured with R = 10 Mb/s and B = 1 Mb (125,000 bytes = 1,000,000 bits). If the bucket starts full:

- **Sustained rate**: any flow sending ≤10 Mb/s passes with no delay.
- **Instantaneous burst**: a flow can send a full 1 Mb burst at the line rate (100 Mb/s, taking 10 ms) — the bucket had 1 Mb of tokens, so this is allowed.
- **Recovery**: after the burst, the bucket is empty. The next packet can leave only after 1/R = 1 µs of token accumulation per byte. To send another 1 Mb burst immediately, the shaper would have to wait B/R = 1,000,000 / 10,000,000 = 0.1 s = 100 ms (the "burst-recovery time").

### Numerical sanity check

A flow that arrives at the shaper as a constant 15 Mb/s for 1 s:

- The shaper can drain at 10 Mb/s + initial burst of 1 Mb = 11 Mb in the first second.
- The remaining 4 Mb is delayed into the next interval; departure stretches over 1.4 s instead of 1 s, adding 0.4 s of latency to those final packets.
- The shaper's queue grows during the burst: peak queue depth = 4 Mb / 100 Mb/s ≈ 40 ms of buffering (in terms of line-rate time).

## The Leaky Bucket

A leaky bucket is a different but related abstraction. Imagine a bucket with a small hole: water (packets) drips out at constant rate R regardless of how it arrived. If water arrives faster than R can drain, the bucket fills up; once full, additional arrivals are dropped (or rejected).

The leaky bucket **strictly polices the instantaneous rate**: it never emits faster than R. There is no burst allowance at the output — output is shaped into a constant bit-rate stream. (In practice, a leaky bucket is implemented by a small per-packet queue with a constant-rate server, i.e., a strict packet shaper.)

### Token bucket vs. leaky bucket

| Property | Token Bucket | Leaky Bucket |
|----------|--------------|--------------|
| Burst allowance | Yes (up to B) | No |
| Output rate when full | Can exceed R briefly | Exactly R |
| Use case | Allow bursts, cap average rate | Enforce strict CBR |
| Policing-friendly? | Yes — flexible contracts | Less so — too strict for bursty apps |

In modern IP QoS, **token bucket** is overwhelmingly the more common choice; the leaky bucket lives on in ATM and in some cellular-rubber-stamp schedulers.

## CIR, EIR, and Three-Colour Marking

A traffic contract typically has two rates:

- **CIR** (Committed Information Rate): the rate the network guarantees to deliver (subject to a small loss bound). Above CIR, traffic is best-effort.
- **EIR** (Excess Information Rate): the rate above CIR that the network will *try* to deliver, with no loss guarantee; beyond CIR + EIR, packets are dropped at the ingress.

These are formalised by the three-colour markers RFC 2697 (single-rate) and RFC 2698 (two-rate):

- **Green**: in-profile (≤ CIR). Should be delivered with high probability.
- **Yellow**: excess, but within EIR (≤ CIR + EIR). May be delivered if there is capacity.
- **Red**: above CIR + EIR. Should be dropped at the ingress.

The three colours map directly onto the Assured Forwarding drop-precedence levels (green = AFx1, yellow = AFx2, red = AFx3), so a downstream AF queue will degrade yellow before green and red before yellow under congestion.

### Single-Rate Three-Colour Marker (srTCM, RFC 2697)

srTCM is configured with CIR, plus two burst sizes:

- **CBS** (Committed Burst Size): the green bucket.
- **EBS** (Excess Burst Size): the yellow bucket.

Algorithm (per packet of size s):

1. Tokens are added to both buckets at rate CIR; the buckets are capped at CBS and EBS respectively.
2. If T_c ≥ s, the packet is **green**; decrement T_c by s.
3. Else if T_e ≥ s, the packet is **yellow**; decrement T_e by s.
4. Else, the packet is **red**.

This produces the behaviour: bursts up to CBS are green, bursts beyond CBS up to CBS+EBS are yellow, anything more is red. The two buckets share the same token-generation rate; only the second bucket catches the overflow when the first is full.

### Two-Rate Three-Colour Marker (trTCM, RFC 2698)

trTCM decouples the green and yellow rates:

- **CIR** (green rate) with **CBS** burst.
- **PIR** (Peak Information Rate, where PIR = CIR + EIR) with **PBS** burst.

Algorithm (per packet of size s):

1. T_p is the PIR bucket, T_c is the CIR bucket. Both fill at their respective rates.
2. If T_p < s, the packet is **red** (above peak).
3. Else if T_c < s, the packet is **yellow**; decrement T_p by s.
4. Else, the packet is **green**; decrement both T_p and T_c by s.

This produces a strict peak cap (yellow traffic cannot exceed PIR), plus an independent green-rate cap. trTCM is preferred when the network needs a hard rate ceiling.

### Worked example (trTCM)

Configure trTCM with CIR = 10 Mb/s, CBS = 100 KB, PIR = 20 Mb/s, PBS = 200 KB. Suppose buckets start full and a 1 MB file is sent at line rate (100 Mb/s = 12.5 MB/s):

```
Packet arrives at t=0, s = 1500 bytes:
- T_c = 100,000 ≥ 1500 → green; T_c -= 1500 → 98,500
- T_p = 200,000 ≥ 1500 → green; T_p -= 1500 → 198,500

After 67 packets (= 100 KB ≈ T_c):
- T_c = 0; first 67 packets all green
- 68th packet: T_c < 1500 → yellow; T_p -= 1500

After 133 packets (= 200 KB ≈ T_p):
- T_p = 0; everything yellow up to here
- 134th packet: T_p < 1500 → red, dropped
- Time elapsed at 100 Mb/s for 200 KB = 200 KB / 12.5 MB/s = 16 ms
- During these 16 ms, T_c has gained 16 ms × 10 Mb/s = 20 KB → green occasionally for ~13 packets of 1500 B, rest yellow
```

So a 1 MB burst at 100 Mb/s produces roughly the first 67 packets (100 KB) green, the next 67 packets (100 KB) yellow, the rest red — exactly the contract: 10 Mb/s green sustained, plus a 10 Mb/s yellow cushion up to a 200 KB peak.

## Color-Aware vs. Color-Blind Operation

A meter can operate in two modes:

- **Color-blind**: the meter ignores any pre-existing colour; it colours the packet solely from its own token buckets. A flow that arrives already pre-coloured by a downstream meter is re-evaluated as if fresh.
- **Color-aware**: the meter assumes the arriving packet is already coloured (e.g., by the customer's own edge). It **never promotes** a packet (yellow stays yellow, red stays red), but it can **demote** an over-rate flow's green packets to yellow if the meter sees that the CIR is being exceeded.

Color-aware mode is used in **cascaded metering** scenarios — when a service provider resells capacity to a downstream ISP and wants to honor the downstream's marking under the contracted rate but cap bursts above it.

## Linux Traffic Control (`tc`) Implementation

Linux exposes DiffServ-style shaping and policing through the **`tc`** command and the **qdisc** (queueing discipline) layer. The relevant components:

```
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ Classify │───▶│  qdisc   │───▶│  NIC TX  │
   │ (filter) │    │ (shape/  │    │ (driver) │
   │          │    │  police) │    │          │
   └──────────┘    └──────────┘    └──────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  child class │   (HTB/CBS)
                  │  with rate/   │
                  │  ceil         │
                  └──────────────┘
```

### TBF (Token Bucket Filter)

The simplest shaper. Configures a classic token bucket on the interface's egress:

```
tc qdisc add dev eth0 root tbf \
    rate 10mbit \
    burst 32kb \
    latency 50ms \
    peakrate 12mbit \
    minburst 1520
```

- `rate 10mbit`: token-generation rate R.
- `burst 32kb`: bucket capacity B (must be ≥ MTU).
- `latency 50ms`: maximum queueing delay; packets that would exceed this are dropped.
- `peakrate 12mbit`: optional second bucket limiting peak output rate (so the shaper is not just averaging 10 Mb/s but never exceeds 12 Mb/s).
- `minburst 1520`: a small "mini-burst" bucket for packet-atomicity reasons (a single packet must always pass even if slightly over the rate).

Internally, TBF is a strict token bucket plus a single FIFO queue. It is cheap and adequate for single-class shaping but cannot prioritise.

### HTB (Hierarchy Token Bucket)

HTB (Linux's most-used shaping qdisc) **extends token bucket with class hierarchy**. Each HTB class has two rates:

- `rate`: the guaranteed rate (CIR).
- `ceil`: the maximum rate the class can borrow to, above its `rate`.

```
                root HTB qdisc
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   class 1:1     class 1:2     class 1:3
   rate=8mbit    rate=4mbit    rate=2mbit
   ceil=10mbit   ceil=10mbit   ceil=10mbit
       │            │             │
       ▼            ▼             ▼
   leaf qdisc   leaf qdisc    leaf qdisc
   (pfifo)     (pfifo)       (pfifo)
```

**Borrowing**: if class 1:2 has packets queued but its `rate` (4 Mb/s) is exhausted, it can **borrow** from unused parent bandwidth up to its `ceil` (10 Mb/s). Borrowed tokens come from the parent's bucket. If the parent is also rate-capped, borrowing cascades up; if there is no excess, the class is throttled to `rate`.

This is the **classful token bucket** — a hybrid of shaping (per-class rate limiting) and hierarchical scheduling (parent aggregate cap).

Example configuration:

```
tc qdisc add dev eth0 root handle 1: htb default 99

tc class add dev eth0 parent 1: classid 1:1 htb rate 10mbit ceil 10mbit

tc class add dev eth0 parent 1:1 classid 1:10 htb \
    rate 8mbit ceil 10mbit prio 1         # EF: priority 1
tc class add dev eth0 parent 1:1 classid 1:20 htb \
    rate 1mbit  ceil 5mbit  prio 2         # AF31
tc class add dev eth0 parent 1:1 classid 1:30 htb \
    rate 1mbit  ceil 5mbit  prio 3         # AF11
tc class add dev eth0 parent 1:1 classid 1:99 htb \
    rate 100kbit ceil 10mbit prio 7       # BE default

# Filters to assign packets to classes by DSCP
tc filter add dev eth0 parent 1: protocol ip prio 1 \
    u32 match ip tos 0xb8 0xfc flowid 1:10   # DSCP 46 (EF) → class 1:10
tc filter add dev eth0 parent 1: protocol ip prio 2 \
    u32 match ip tos 0x68 0xfc flowid 1:20   # DSCP 26 (AF31) → class 1:20
tc filter add dev eth0 parent 1: protocol ip prio 3 \
    u32 match ip tos 0x28 0xfc flowid 1:30   # DSCP 10 (AF11) → class 1:30
```

(The `u32 match ip tos` matches the DS field; the mask `0xfc` selects the 6 DSCP bits and excludes the 2 ECN bits.)

The result is: 10 Mb/s capped link, 8 Mb/s guaranteed to EF, 1 Mb/s each guaranteed to AF31/AF11, best-effort gets 100 Kb/s minimum but can borrow to 10 Mb/s. Under congestion, EF priority queue dominates; AF and BE borrow proportionally.

### Policing with `tc` (ingress)

Shaping is egress-only. For ingress, the only operation is **policing** (you cannot delay a packet you have not received yet). The `tc filter ... police` command attaches a token-bucket policer:

```
tc qdisc add dev eth0 ingress

tc filter add dev eth0 parent ffff: protocol ip prio 1 u32 \
    match ip dport 80 0xffff \
    police rate 10mbit burst 100kb \
           mtu 66000 drop \
           flowid :1
```

This drops HTTP traffic exceeding 10 Mb/s after a 100 KB burst. Other available actions include `reclassify` (move to a different class), `pass` (let through), and `ok` (continue classifying).

### Other qdiscs

- **CBQ** (Class-Based Queueing): older, more academic, mostly replaced by HTB.
- **PRIO**: strict priority queue, child classes with strictly ordered priorities. Used as a leaf under HTB for EF/AF/BE separation.
- **FQ_Codel**: modern AQM with sub-flow fairness and Codel active-queue management. Recommended default for general-purpose links.
- **HFSC** (Hierarchical Fair Service Curve): supports latency-bounded classes via service-curve scheduling; used for VoIP-carrying networks.

## Comparison with Cisco IOS

The same algorithms appear in Cisco IOS, with different names:

| Linux | Cisco IOS |
|-------|-----------|
| TBF qdisc | `shape average` (default GTS) |
| HTB | `policy-map ... class ... priority` + `bandwidth` |
| `tc filter police` | `police` (CAR: Committed Access Rate) |
| FQ_Codel | (no equivalent; Cisco has WRED + DRR) |
| HTB leaf with `ceil` | `priority percent` (LLQ) with `police` |

Cisco configuration of a single-rate three-colour marker:

```
policy-map AF31-MARKER
  class AF31
    police cir 10000000 bc 100000 pir 20000000 be 100000
      conform-action transmit
      exceed-action set-dscp-transmit af32
      violate-action set-dscp-transmit af33
```

This is exactly trTCM: 10 Mb/s CIR with 100 KB CBS, 20 Mb/s PIR with 100 KB EBS. Conform → green (transmit unchanged); exceed → yellow (re-mark AF32); violate → red (re-mark AF33, may be dropped downstream by WRED).

## Common Pitfalls

1. **Bucket size too small**: if B < MTU, no packet can ever pass. Rule of thumb: B ≥ MTU × 2.
2. **Burst size too large**: lets a customer blow out the bucket at the line rate for an extended period, causing downstream queueing. Most access networks cap B at 1× to 4× the rate's seconds of traffic.
3. **`burst` and `latency` inconsistent in TBF**: `burst / rate` is the steady-state recovery time; `latency` is the queue depth (in seconds). If `latency < burst / rate`, the bucket can never empty through the queue, and you get drops at low rate.
4. **Policing on egress**: technically possible but useless; the packet was already queued and forwarded. Always use shaping on egress and policing on ingress.
5. **Mark-then-shape vs. shape-then-mark**: marking must happen *before* shaping so the marker sees the customer's actual contract, not the post-shape rate.
6. **Color-awareness breakage**: cascaded meters must agree on whose colour wins. The convention is "the upstream meter's colour is authoritative for in-profile packets; downstream only demotes."

## References

1. Heinanen, J., Guérin, R. *A Single Rate Three Color Marker*. RFC 2697, September 1999. — [https://www.rfc-editor.org/rfc/rfc2697](https://www.rfc-editor.org/rfc/rfc2697)
2. Heinanen, J., Guérin, R. *A Two Rate Three Color Marker*. RFC 2698, September 1999. — [https://www.rfc-editor.org/rfc/rfc2698](https://www.rfc-editor.org/rfc/rfc2698)
3. Blake, S., et al. *An Architecture for Differentiated Services*. RFC 2475, December 1998. — [https://www.rfc-editor.org/rfc/rfc2475](https://www.rfc-editor.org/rfc/rfc2475)
4. Cisco. *Cisco IOS Quality of Service Solutions Configuration Guide, Release 12.4*. — "Configuring Traffic Shaping" and "Configuring Traffic Policing" chapters. [https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/qos/configuration/15-mt/qos-15-mt-book.html](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/qos/configuration/15-mt/qos-15-mt-book.html)
5. Linux Foundation. *Linux Advanced Routing & Traffic Control HOWTO*. — Chapter 9: "Token bucket filter (TBF)", Chapter 15: "HTB — Hierarchical Token Bucket". [https://tldp.org/HOWTO/Adv-Routing-HOWTO/](https://tldp.org/HOWTO/Adv-Routing-HOWTO/)
6. Linux man-pages. *tc(8), tc-tbf(8), tc-htb(8), tc-cbq(8), tc-police(8), tc-filter(8)*. — [https://man7.org/linux/man-pages/man8/tc.8.html](https://man7.org/linux/man-pages/man8/tc.8.html)
7. Devera, M. (Martin Devera, "iker"). *HTB Home Page*. — The original HTB author's documentation. [http://luxik.cdi.cz/~devik/qos/htb/](http://luxik.cdi.cz/~devik/qos/htb/)
8. Nichols, K., Jacobson, V. *Controlling High Bandwidth Aggregates in the Network*. ACM CCR, 1998 (cited for RED/WRED background, the policer companion). — [http://www.icir.org/floyd/papers/early.pdf](http://www.icir.org/floyd/papers/early.pdf)
9. IEEE 802.1Qaz. *Congestion Management*. (For DCBX/PFC, the data-centre complement to DiffServ shaping.) — [https://1.ieee802.org/802/802.1/802.1az/](https://1.ieee802.org/802/802.1/802.1az/)
10. Wikipedia: [Token bucket](https://en.wikipedia.org/wiki/Token_bucket), [Leaky bucket](https://en.wikipedia.org/wiki/Leaky_bucket), [Committed information rate](https://en.wikipedia.org/wiki/Committed_information_rate).

## Interview Questions

1. Why is shaping done on egress and policing on ingress? What goes wrong if you try to shape ingress?
2. Explain the token bucket parameters R and B. Over a window of length Δt, what is the maximum number of bytes that can depart?
3. A shaper has R = 100 Mb/s and B = 1 MB. A flow sends 2 MB at line rate (1 Gb/s). How long does the transmission take? What is the peak queue depth in the shaper?
4. Distinguish CIR, CBS, PIR, PBS. Which RFC defines each combination of three-colour marker?
5. Walk through the difference between srTCM and trTCM. Under what traffic pattern do they produce different colourings for the same packets?
6. Explain color-aware vs. color-blind metering. When would you configure color-aware, and what guarantee does it require of the upstream meter?
7. In Linux `tc`, what is the difference between TBF and HTB? When would you choose HTB, and what extra capability does it give you?
8. Given an HTB class with `rate 4mbit ceil 10mbit`, what happens when the parent has 6 Mb/s of unused bandwidth available? What if the parent is itself saturated?
9. The HTB `ceil` parameter is sometimes called "burst borrowing". Explain the metaphor — what is being borrowed, from whom, and what happens when it cannot be repaid?
