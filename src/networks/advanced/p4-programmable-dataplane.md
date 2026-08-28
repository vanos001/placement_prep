# P4 and the Programmable Data Plane

**P4** (Programming Protocol-independent Packet Processors) is a domain-specific
language for describing how a network device parses, matches, and forwards
packets. Unlike OpenFlow, which programs *entries* into a fixed pipeline, P4
programs the *pipeline itself* — which headers exist, what tables match on,
what actions do. The interview-critical model is the **Protocol Independent
Switch Architecture (PISA)** of the 2013 RMT paper
([Bosshart et al., SIGCOMM 2013](https://doi.org/10.1145/2486001.2486011)):
a fixed sequence of cheap programmable stages (parser, match-action units,
deparser) that compiled P4 *configures*, so new protocols no longer wait 2–4
years for the next ASIC. The survey
[Programmable Networks](./programmable-networks.md) places P4 beside
DPDK/XDP/eBPF; this page goes deep on the language, hardware model, toolchain,
and what happened to Intel Tofino.

## The match-action abstraction: parser -> MAU -> deparser

PISA hardware is a pipeline of Match-Action Units (MAUs) between a
reconfigurable parser and deparser. Each MAU holds several tables, a bank of
very-long-instruction-word ALUs, registers, and hash units; a packet makes one
pass, and within a stage everything happens in parallel:

```text
            +-----------------  one pass, ~1 us at line rate  ----------------+
            |                                                                 |
 ingress -->+-> parser (state machine) -> MAU 1 -> MAU 2 -> ... -> MAU N --+  |
            |    extracts header fields      tables + ALUs + registers     |  |
            |    into the PHV                                              v  |
            |                                            traffic manager (queueing)
            |                                                             |  |
 egress  <--+<- deparser (emit fields) <- MAU M <- ... <- MAU 1 <---------+  |
            |    writes chosen headers back to bytes                          |
            +-----------------------------------------------------------------+

 PHV = Packet Header Vector: wide registers holding the parsed fields; the
 only view of the packet the MAUs ever get.
```

Three consequences interviewers probe: **no loops, no recursion** (control
flow is straight-line with a bounded number of stage crossings — route
recursion and reassembly recirculate or go to the control plane); **state is
explicit** (stateful memory must be declared externs — `Register`, `Counter`,
`Meter` — with declared widths; there is no heap); and **byte order is your
problem** (the parser sees a byte stream, the deparser rebuilds it; checksums
are explicit externs, not implicit).

## P4-16: what the language gives you

P4-16 (the 2016 redesign of the 2014 language) is strongly typed and
architecture-parametrized. A program declares **header types** (typed field
bundles plus metadata headers that never hit the wire), **parsers** (state
machines: `extract()` pulls bits, `select()` transitions on values), **tables
+ actions**, **controls** sequencing table applications, **externs**, and an
**architecture package** binding it to a target (`V1Switch(...)` for v1model,
`Main` for PNA, `TofinoSwitch` for TNA).

The core table declaration is `table ipv4_lpm { key = { hdr.ipv4.dst_addr :
lpm; } actions = { forward; drop; } size = 65536; default_action = drop(); }`
in a `control` block. Details that matter at depth: **`lpm` is syntactic
sugar** for ternary with auto-generated masks (`mask = ~((1 << prefix_len) -
1)`); **`isValid()`** reads the per-header valid bit set by the parser — the
only "existence" notion MAUs have; **`const entries`** pin configuration at
compile time; every value is width-explicit (`bit<32>`) so operations pack
into fixed-width stage ALUs. The current language revision is P4-16 v1.2.5
([spec](https://p4.org/wp-content/uploads/sites/53/2024/10/P4-16-spec-v1.2.5.html)).

## Table types and their hardware cost

| Match kind | Lookup semantics | Hardware structure | Relative cost / limit |
|------------|------------------|--------------------|-----------------------|
| `exact`    | full key equality | hash + SRAM banks | cheap; ~100k+ entries/stage |
| `lpm`      | longest prefix match | TCAM or algorithmic (SRAM) | medium; ALPM trades SRAM+stages |
| `ternary`  | `(key AND mask) == (val AND mask)`, priority-ordered | TCAM + priority encoder | expensive; ~k entries, high power |

The first three are the staples (`range` and `optional` are target-dependent
extras). **Exact-match scales, ternary doesn't**:
production designs push everything possible into exact tables and reserve TCAM
for the few thousand rules that truly need wildcards. And **LPM is a
negotiation**: a pipeline cannot walk a multibit trie across stages in one
pass, so targets implement *algorithmic LPM* (ALPM) — hash prefixes into SRAM,
keep a small TCAM for exceptions, spend extra stages on the lookup.

## Stateful objects: registers, counters, meters

| Object | Semantics | Typical use |
|--------|-----------|-------------|
| `Register` | indexed read/write array of `bit<W>` | flow state, EWMA of queue length, ECN marking |
| `Counter` | indexed packets/bytes, increment-only | drop reasons, per-prefix stats |
| `Meter` | token-bucket color (green/yellow/red) | rate policing (two-rate three-color, RFC 2698-style) |
| `Digest` / `Hash` | notify control plane; CRC16/32/56 | learning handoff; ECMP/LAG member choice |

Two subtleties: registers are **read-modify-write within one MAU stage** — you
see stage N-1's value when reading in stage N, so cross-packet feedback is one
packet of latency; and meters **color, they don't drop** — dropping is your
action on red.

## Architectures: v1model, PSA, PNA, TNA

| Architecture | Target class | Pipeline shape | Notes |
|--------------|--------------|----------------|-------|
| **v1model** | BMv2, teaching | parser -> verify -> ingress -> egress -> checksum -> deparser | de-facto teaching model; `V1Switch` |
| **PSA** | switch ASICs, eBPF | parser -> ingress -> traffic manager -> egress -> deparser | standardizes TM, multicast, clones |
| **PNA** | SmartNICs / DPUs | pre-entry/entry/post-entry, host + pre/post directions | two traffic directions; no TM; [PNA spec](https://p4.org/wp-content/uploads/sites/53/p4-spec/docs/pna-working-draft-html-version.html) |
| **TNA** | Intel Tofino 1/2 | parser -> MAU stages -> deparser, ingress + egress | vendor externs (mirror, recirculate); open-sourced 2025 |

PSA and PNA moved checksums to externs, and PNA drops the Traffic Manager
entirely — a NIC's "egress" is the host or the wire, not a fabric. Porting
between architectures is real work, which is exactly why PSA/PNA exist:
portable P4 the way POSIX made C portable.

## Toolchain: p4c, BMv2, P4Runtime

```text
 my.p4 (P4-16)
    |
    v
 +----------------+        front-end: parse, type-check
 |      p4c       |  -->   mid-end: IR passes (const fold, DCE, width infer)
 +----------------+        back-ends (one per target):
    |     |                  bmv2 JSON -> behavioral-model (simple_switch)
    |     +--> eBPF C ------> kernel/XDP      +--> p4tc -> Linux TC pipeline
    +----------> DPDK SWX -> p4c-dpdk (Intel E810 DDP profiles)
    +----------> (Tofino: open-p4studio compiler, open-sourced Jan 2025)

 control plane:  p4c --p4runtime-files -> P4Info protobuf
                 P4Runtime (gRPC) Write/Read/TableEntry  <->  device
```

- **p4c** ([github.com/p4lang/p4c](https://github.com/p4lang/p4c)) — reference
  compiler: shared front/mid-end plus seven sample back-ends. The two
  invocations everyone types: `p4c --target bmv2 --arch v1model` and
  `--p4runtime-files`.
- **BMv2** ([behavioral-model](https://github.com/p4lang/behavioral-model)) —
  software reference target: `simple_switch` (v1model), `simple_switch_grpc`
  (adds P4Runtime). Correct but ~1 Mpps slow — the unit-test bed.
- **P4Runtime** ([spec v1.5.1](https://p4lang.github.io/p4runtime/spec/main/P4Runtime-Spec.html))
  — the gRPC control-plane standard: P4Info describes the compiled pipeline
  and controllers manipulate `TableEntry` objects. OpenFlow for the P4 world,
  but the *schema* is program-defined.

## Tofino: rise, discontinuation, open-sourcing

Tofino was the proof that PISA + P4 could be merchant silicon. The timeline
explains today's landscape:

| Date | Event |
|------|-------|
| 2013 | RMT paper; Barefoot Networks founded (P4 co-authors) |
| 2016–19 | Tofino 1 shipping (PISA, ~6.5 Tbps class); Intel acquires Barefoot |
| Jan 2023 | Intel confirms it stops further Tofino switch-ASIC development; Tofino 1/2 sales/support continue for deployed customers ([p4.org forum](https://forum.p4.org/t/suggestion-for-p4-programmable-switches-other-than-intel-tofino/692)) |
| Jan 2025 | Intel open-sources the Tofino software: compiler/tooling in [p4lang/open-p4studio](https://github.com/p4lang/open-p4studio), architecture definitions in [Open-Tofino](https://github.com/barefootnetworks/open-tofino), [p4.org announcement](https://p4.org/intels-tofino-p4-software-is-now-open-source) |
| 2026 | No Tofino 3; Intel pages still document Tofino IFPs for existing deployments; the language and tooling live on elsewhere |

## The NIC pivot: where P4 lives now

- **NVIDIA BlueField-3/4**: DOCA's Data Path Language accepts P4 programs for
  the embedded pipeline ([DOCA P4 support](https://networking-docs.nvidia.com/doca/archive/3-4-0/p4-language-support-in-dpl));
  BlueField-4 (announced Oct 2025, 800 Gb/s, shipping with Vera Rubin
  platforms) continues the line.
- **AMD Pensando DPUs**: pitched around a P4-programmable data plane plus Arm
  cores ([amd.com Pensando](https://www.amd.com/en/products/data-processing-units/pensando.html)).
- **Intel**: p4c-dpdk compiles P4 into E810 Dynamic Device Personalization
  profiles (programmable parser/classify on a fixed-function NIC); Mount Evans
  (co-designed with Google) proved P4 host NICs at scale; successors continue
  the pitch ([Intel IPU](https://www.intel.com/content/www/us/en/products/network-io/ipu.html)).

Honest summary: switch-ASIC P4 traded on full pipeline reprogrammability at
terabits; the surviving answers trade pipeline depth for volume (every server
gets one).

## Executed demo: a mini match-action pipeline

The simulator models the three table kinds, a register, and a token-bucket
meter, then walks six packets through one pass; real RMT hardware does this in
nanoseconds, but the *semantics* (priority vs longest prefix, meter colors,
read-modify-write registers) are the same.

```python
# Mini RMT-style match-action pipeline (one pass of an L3 switch):
# parser -> [l2_fib: exact] -> [ipv4_lpm: LPM] -> [acl: ternary]
#          -> meter (token bucket) -> registers -> deparser
L2_FIB = {bytes.fromhex(m): p for m, p in     # exact -> SRAM hash
          [('020000aaaa02', 12), ('020000bbbb03', 24)]}
IPV4_LPM = {(0x0A011000, 24): (24, '02:00:00:bb:bb:03'),   # 10.1.16/24
            (0x0A010000, 16): (12, '02:00:00:aa:aa:02')}   # 10.1/16  -> SRAM/ALPM
ACL = [(0x0A011005, 0xFFFFFFFF, 'drop'),      # ternary, priority order -> TCAM
       (0x0A011000, 0xFFFFFF00, 'permit')]    # deny host 10.1.16.5, allow /24

def lpm(ip):                       # longest prefix wins
    best = None
    for (net, plen), res in IPV4_LPM.items():
        if ip >> (32 - plen) == net >> (32 - plen) and (best is None or plen > best[0]):
            best = (plen, res)
    return best[1] if best else None

def ternary(ip):                   # first entry whose mask matches
    for val, mask, act in ACL:
        if (ip & mask) == (val & mask):
            return act
    return 'permit(default)'

port_bytes = {12: 0, 24: 0}        # register: per-egress byte counters
tokens, rate, burst = 0, 800, 1600 # meter: 800 B/tick refill, 1600 B burst
pkts = [('02:00:00:aa:aa:02', '10.1.16.5', 800),   # bridged, ACL host-deny
        ('02:00:00:aa:aa:02', '10.1.20.7', 800),   # bridged, permitted
        ('02:00:00:cc:cc:04', '10.1.16.9', 800),   # L2 miss -> routed /24
        ('02:00:00:cc:cc:04', '10.2.0.1', 800),    # L2 miss, no route
        ('02:00:00:aa:aa:02', '10.1.16.9', 800),   # bridged, permitted
        ('02:00:00:bb:bb:03', '10.1.16.9', 1400)]  # meter drained -> DROP
print(f"{'#':>2}  {'l2_fib(exact)':<14} {'ipv4_lpm(LPM)':<26} "
      f"{'acl(ternary)':<15} {'meter':<5} verdict        egress")
for i, (dmac, dip, plen) in enumerate(pkts, 1):
    r1 = L2_FIB.get(bytes.fromhex(dmac.replace(':', '')))
    r2 = lpm(int.from_bytes(bytes(int(x) for x in dip.split('.')), 'big')) if not r1 else None
    aclres = ternary(int.from_bytes(bytes(int(x) for x in dip.split('.')), 'big'))
    tokens = min(burst, tokens + rate)          # one packet per tick
    if tokens >= plen: tokens -= plen; meter = 'pass'
    else: meter = 'DROP'
    if r1: stage2, egress = 'bridge', r1
    elif r2: stage2, egress = 'route ' + r2[1], r2[0]
    else: stage2, egress = 'MISS', 0
    if not r1 and not r2: verdict, port = 'drop(no-route)', '-'
    elif aclres == 'drop': verdict, port = 'drop(acl)', '-'
    elif meter == 'DROP':  verdict, port = 'drop(meter)', '-'
    else:
        verdict, port = 'forward', egress
        port_bytes[egress] += 14 + 20 + plen    # eth + IPv4 + payload
    print(f"{i:>2}  {('hit' if r1 else 'miss'):<14} {stage2:<26} "
          f"{aclres:<15} {meter:<5} {verdict:<14} {port}")
print("\nregister port_bytes (egress -> bytes):", dict(sorted(port_bytes.items())))
print("meter tokens left:", tokens, "of burst", burst)
```

Output (verbatim from a run):

```text
 #  l2_fib(exact)  ipv4_lpm(LPM)              acl(ternary)    meter verdict        egress
 1  hit            bridge                     drop            pass  drop(acl)      -
 2  hit            bridge                     permit(default) pass  forward        12
 3  miss           route 02:00:00:bb:bb:03    permit          pass  forward        24
 4  miss           MISS                       permit(default) pass  drop(no-route) -
 5  hit            bridge                     permit          pass  forward        12
 6  hit            bridge                     permit          DROP  drop(meter)    -

register port_bytes (egress -> bytes): {12: 1668, 24: 834}
meter tokens left: 800 of burst 1600
```

Trace reading: #1 is bridged but the ternary ACL's host-deny entry (highest
priority) wins -> drop; #3 misses L2 and takes the /24 route (longest prefix
beats /16); #6 passes every table but the meter is drained -> drop(meter).

## Interview angles

- **"Why is P4 not just a config language?"** The parser and PHV layout are
  programmable: new protocols need zero ASIC changes. OpenFlow configures
  entries; P4 configures the schema of what entries can mean.
- **"Exact vs ternary — where and why?"** Exact on SRAM hash (cheap,
  scalable); ternary on TCAM only where wildcards are essential (area- and
  power-bound). Bonus trap: reading a register twice in one stage is a
  read-after-write hazard — the compiler schedules it to the next stage,
  subtly changing semantics.
- **"Is P4 dead now that Tofino is?"** No — the language moved into
  DPUs/NICs (BlueField DPL, Pensando, E810 DDP) and the Tofino toolchain is
  open source. What died is the merchant *switch-ASIC* SKU.

## Related pages and references

- [SRv6](./srv6.md) — SID behaviors (End, End.X) are exactly the per-packet instructions a P4 program implements.
- [Data-Center TCP](./datacenter-tcp.md) — HPCC's congestion signal is in-network telemetry; see [In-Band Telemetry](./in-band-telemetry.md).
- [DPU & SmartNIC Offload](../../arch/advanced/dpu-smartnic-offload.md) — the hardware P4 targets today (survey page: [Programmable Networks](./programmable-networks.md)).

1. P4.org, *P4-16 Language Specification*, v1.2.5 — <https://p4.org/wp-content/uploads/sites/53/2024/10/P4-16-spec-v1.2.5.html>
2. P. Bosshart et al., "Forwarding Metamorphosis," ACM SIGCOMM 2013 — <https://doi.org/10.1145/2486001.2486011>
3. P. Bosshart et al., "P4: Programming Protocol-Independent Packet Processors," ACM CCR 45(3), 2014 — <https://doi.org/10.1145/2656877.2656890>
4. P4.org API WG, *P4Runtime Specification*, v1.5.1 — <https://p4lang.github.io/p4runtime/spec/main/P4Runtime-Spec.html>
5. P4.org, "Intel's Tofino P4 Software Is Now Open Source" (Jan 2025) — <https://p4.org/intels-tofino-p4-software-is-now-open-source>
6. p4lang, *open-p4studio* — open-source Tofino compiler and toolchain — <https://github.com/p4lang/open-p4studio>
