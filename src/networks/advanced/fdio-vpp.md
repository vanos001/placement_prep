# FD.io VPP: Vector Packet Processing in User Space

## Introduction

FD.io (Fast Data Project, hosted by the Linux Foundation since 2016) is built
around VPP, the Vector Packet Processor: a user-space stack whose one idea is
to pay per-*vector*, not per-packet, fixed costs. Descended from a Cisco
data-plane project in development since 2002, it runs as an ordinary process
on x86, ARM, and Power, fed by DPDK drivers, AF_PACKET, vhost/virtio, AF_XDP,
or memif. Instead of pushing packet 1 through the stack, then packet 2, VPP
pulls a *vector* of up to 256 packets off the RX ring and runs each stage
across the entire vector.

## Why vectorize a packet loop?

A scalar stack processes one packet at a time: `fooA(p1) -> fooB(p1) ->
fooC(p1)`, then the same for p2, p3, ... If the code path exceeds the I-cache,
every packet re-fills the same instruction working set -- the per-packet
miss cost is constant however fast packets arrive -- and the deep call stack
evicts stack locals from L1 data cache. The VPP docs name exactly these two
inefficiencies and show the fix:

```text
scalar:  [A p1][B p1][C p1][A p2][B p2][C p2][A p3][B p3][C p3]
          ^cold   ^cold   ^cold     (I-cache refilled per packet)
vector:  [A p1..p256][B p1..p256][C p1..p256]
          ^cold once, then warm for the other 255 packets
```

The first packet warms the stage's instruction cache; the rest run mostly
from cache: the fixed cost is *amortized* over the vector instead of paid 256
times. The FD.io technology page adds that the system self-tunes -- falling
behind means the next vector holds more packets, per-packet cost drops, and
VPP catches up -- and that pipelining plus prefetch of table data come free
with the same structure.

## The packet processing graph

VPP decomposes forwarding into a directed graph of *nodes*; each node's
dispatch function receives a vector of buffer indices, arcs are possible
next-node transitions, and the scheduler invokes one node at a time -- stack
depth stays a few frames regardless of feature count. Node names below are
registered in the FDio/vpp source tree (paths checked Aug 2026):

| Node               | Role in an IPv4 pass                        | Defined in (FDio/vpp)            |
|--------------------|---------------------------------------------|----------------------------------|
| `dpdk-input`       | RX: dequeue a vector from DPDK PMD RX rings | `src/plugins/dpdk/device/node.c` |
| `ethernet-input`   | L2 parse, classify into L3/L2 subgraphs     | `src/vnet/ethernet/node.c`       |
| `ip4-lookup`       | FIB lookup, pick the load-balance path      | `src/vnet/ip/ip4_forward.c`      |
| `interface-output` | TX enqueue toward the device node           | `src/vnet/interface_output.c`    |
| `memif-input`      | RX from a memif shared-memory interface     | `src/plugins/memif/node.c`       |

```text
  RX ring --> [dpdk-input] --handoff--> other worker
                  |
             [ethernet-input]
                  |             |
             [ip4-lookup]   [error-drop]
                  |
             [ip4-rewrite] --> [interface-output] --> [device TX]
```

The scheduler works on `(vector, node)` pairs -- workers process different
vectors of different nodes concurrently, and a `handoff` node moves packets
between threads when a flow changes CPU. Per-node counters and dispatch
traces make debugging graph-shaped, not stack-trace-shaped.

## DPDK as the wire side

VPP does not own most NIC drivers; it consumes DPDK. The `dpdk` plugin
configures poll-mode drivers, hugepages, and RX/TX rings; `dpdk-input`
dequeues vectors into the graph:

| Concern             | Owner          | Notes                                         |
|---------------------|----------------|-----------------------------------------------|
| NIC register access | DPDK PMDs      | polled RX/TX loops, no interrupts             |
| Buffers             | both           | DPDK mempools back VPP `vlib_buffer_t` frames |
| Lockless queues     | rte_ring style | SPSC rings, barrier-published tails           |
| Packet processing   | VPP graph      | DPDK stops at "a vector of packets in memory" |

That third row is an interview answer: DPDK's `rte_ring` and io_uring's
submission/completion rings are the same SPSC, cache-line-padded,
barrier-published queue design -- see
[io_uring internals](../../os/kernel/io-uring.md) for the kernel-side version.
The VPP config reference keeps a dedicated DPDK section (uio/vfio, hugepages,
device whitelist); see [SR-IOV networking](./sr-iov-networking.md) for how
VFIO passthrough hands the NIC to a user-space process. VPP also ships
first-party input nodes for non-DPDK IO (`af_packet`, `af_xdp`, `avf`,
virtio/vhost, `memif-input`) -- the graph is indifferent to the source.

## memif: shared memory as a NIC

memif (Memory Interface) turns shared memory into a point-to-point virtual
cable between two packet processors -- VPP to container, VM, or another VPP.
One endpoint creates the socket as *server*; the *client* connects and
negotiates memory regions and rings with `add region` / `add ring` messages;
the producer writes packets into the shared ring, the consumer drains them,
zero copies cross the boundary. DPDK implements memif as a poll-mode driver
and FD.io ships `libmemif` -- the seam to container CNIs, VMs, and tests.

## Binary API and the plugin ecosystem

Control processes (or `vppctl`) talk over the *binary API*: versioned,
machine-generated messages with multi-language bindings (C, Python, Java, Go
via GoVPP); the lock-free stat segment lets collectors read counters without
touching the data path. Plugins are shared libraries loaded at runtime, and a
plugin is an equal citizen: new graph nodes, rewired arcs, new API messages
and CLI commands, buildable out of tree against installed headers. Shipped
examples:

| Plugin   | What it contributes to the graph                   |
|----------|----------------------------------------------------|
| `dpdk`   | PMD device nodes, crypto device offload hooks      |
| `acl`    | ACL classifier nodes (5-tuple and MACIP match)     |
| `memif`  | memif input/output nodes and the control protocol  |
| `af_xdp` | kernel-bypass rings backed by AF_XDP sockets       |
| `avf`    | native Intel Adaptive Virtual Function driver      |

The ACL plugin is the canonical "add a feature without forking" example: the
graph stays intact; ACL inserts classifier nodes on selected interface arcs.

## Vector size: the cache-vs-latency dial

Vector length is a trade-off, not a free win. Bigger vectors amortize warm-up
better, but each packet waits for the batch to form and for the stage to sweep
the whole vector: buffer footprint and head-of-line delay grow. Model the
per-packet cost of one graph pass as `T(n) = A + B/n + E*n` -- warm work `A`,
amortized fixed cost `B/n`, growing penalty `E*n` -- whose optimum
`n* = sqrt(B/E)` lands almost exactly on the 256-packet vector VPP ships:

```python
#!/usr/bin/env python3
"""Scalar vs vector cost model for one VPP graph pass.

T(n) = A + B/n + E*n: A warm work; B fixed dispatch + I-cache warm-up,
amortized over the vector; E per-packet growing cost. Optimum n* = sqrt(B/E).
"""

A, B, E = 90.0, 160.0, 0.0025

def cost(n):
    return A + B / n + E * n

def drain(scalar_mode, arrivals, budget):
    backlog, rows, drained_at = 0, [], None
    for r, arr in enumerate(arrivals, 1):
        backlog += arr
        n = 1 if scalar_mode else min(backlog, 256)
        served = min(backlog, int(budget / cost(n)))
        backlog -= served
        if backlog == 0 and drained_at is None:
            drained_at = r
        rows.append((r, n, cost(n), backlog))
    return rows, drained_at

print("Per-packet cost vs vector length (A=90 B=160 E=0.0025 ns)")
print("%6s | %12s | %9s" % ("n", "T(n) ns/pkt", "speedup"))
print("-" * 34)
for n in (1, 16, 64, 256, 1024):
    print("%6d | %12.2f | %8.2fx" % (n, cost(n), cost(1) / cost(n)))
print("optimum n* = sqrt(B/E) = %.1f, grid search = %d" %
      ((B / E) ** 0.5, min(range(1, 4097), key=cost)))
print("T(n*) = %.2f ns/packet vs scalar %.2f ns/packet" %
      (cost(int(round((B / E) ** 0.5))), cost(1)))

arrivals = [6000, 6000, 6000, 100, 100, 100, 100]  # burst, then light load
vrows, vdr = drain(False, arrivals, 250000.0)
srows, _ = drain(True, arrivals, 250000.0)
print()
print("Burst-drain race (CPU budget 0.25 ms/round, same arrivals)")
print("%4s | %6s %9s %9s | %6s %9s %9s" %
      ("rnd", "V:vec", "V:ns/pkt", "V:backlog", "S:vec", "S:ns/pkt", "S:backlog"))
print("-" * 60)
for (rv, nv, cv, bv), (rs, ns_, cs, bs) in zip(vrows, srows):
    print("%4d | %6d %9.2f %9d | %6d %9.2f %9d" % (rv, nv, cv, bv, ns_, cs, bs))
print("vector drained the burst in round %d; scalar still holds %d"
      % (vdr, srows[-1][3]))
```

Real output:

```text
Per-packet cost vs vector length (A=90 B=160 E=0.0025 ns)
     n |  T(n) ns/pkt |   speedup
----------------------------------
     1 |       250.00 |     1.00x
    16 |       100.04 |     2.50x
    64 |        92.66 |     2.70x
   256 |        91.27 |     2.74x
  1024 |        92.72 |     2.70x
optimum n* = sqrt(B/E) = 253.0, grid search = 253
T(n*) = 91.26 ns/packet vs scalar 250.00 ns/packet

Burst-drain race (CPU budget 0.25 ms/round, same arrivals)
 rnd |  V:vec  V:ns/pkt V:backlog |  S:vec  S:ns/pkt S:backlog
------------------------------------------------------------
   1 |    256     91.27      3261 |      1    250.00      5001
   2 |    256     91.27      6522 |      1    250.00     10002
   3 |    256     91.27      9783 |      1    250.00     15003
   4 |    256     91.27      7144 |      1    250.00     14104
   5 |    256     91.27      4505 |      1    250.00     13205
   6 |    256     91.27      1866 |      1    250.00     12306
   7 |    256     91.27         0 |      1    250.00     11407
vector drained the burst in round 7; scalar still holds 11407
```

The first table shows diminishing returns: most amortization is banked by
n=64, and by n=1024 the `E*n` penalty overtakes the shrinking `B/n`, so the
curve has a real minimum (n* = 253 here), not "bigger is always better." The
race table shows catch-up: under the same burst, vector mode runs 2.74x
cheaper per packet precisely while backlog exists (vectors fill to 256) and
drains in round 7; scalar mode serves only ~1000 packets per round and still
owes 11407. The cost is latency inside forming vectors -- why latency-critical
deployments tune vector size down and throughput deployments keep 256.

## VPP vs XDP vs eBPF programmability

The natural comparison is Linux XDP (see
[XDP](../../linux/kernel/networking/xdp.md) and
[advanced XDP programming](../../linux/kernel/networking/xdp-advanced.md)):
also "restricted programs at the earliest point," but in-kernel and per-packet.
The CoNEXT 2018 XDP paper (DOI 10.1145/3281411.3281443) evaluates XDP against
DPDK-class bypass: in-kernel trades a few hundred ns of stack overhead for
staying inside the kernel ecosystem.

| Dimension           | VPP (user space + DPDK)         | XDP (in-kernel eBPF)              |
|---------------------|---------------------------------|-----------------------------------|
| Execution model     | vector of 256 per node dispatch | scalar: one packet per program run|
| Programming model   | C graph nodes / plugins         | eBPF bytecode, verifier-sandboxed |
| I-cache amortization| yes, by construction            | no (per-packet JIT'd run)         |
| Packet dropped at   | NIC -> user-space RX ring       | driver, before `sk_buff` alloc    |
| Unsafe pointer math | yes (ordinary C)                | no (verifier rejects)             |
| Ecosystem           | FIB, host stack, binary API     | maps, tracing, `iproute2`, CO-RE  |
| Sweet spot          | forwarding boxes, vRouters, NFV | DDoS scrubbing, LB, host net      |

Two honest nuances. First, "VPP is faster than XDP" is not a law: XDP avoids
the user-space crossing and wins the first-packet race, VPP's amortization
wins steady-state cache economics, and head-to-head numbers depend on workload
and NIC. Second, VPP's programmability is *not* eBPF: extensibility loads C
shared objects with full machine access -- faster and more expressive, but no
verifier, the sandbox trade eBPF made in reverse. AF_XDP (see
[AF_XDP internals](../../linux/kernel/networking/af-xdp-internals.md)) is the
middle path: kernel rings, eBPF steering, user-space consumer.

## Where CSIT fits

FD.io's CSIT project runs the per-release performance and functional
campaigns over VPP -- the VPP docs credit "out of the box production
quality" to it -- publishing reproducible throughput/latency baselines.

## References

1. FD.io project home + technology overview -- https://fd.io/technology/
2. FD.io VPP docs, "Scalar vs Vector packet processing" -- https://s3-docs.fd.io/vpp/25.10/aboutvpp/scalar-vs-vector-packet-processing.html
3. FD.io VPP docs, "The Packet Processing Graph" (256-packet vectors, plugins) -- https://s3-docs.fd.io/vpp/25.10/aboutvpp/extensible.html
4. FD.io VPP plugin development guide -- https://s3-docs.fd.io/vpp/25.10/developer/plugindoc/index.html
5. DPDK docs, memif poll mode driver (server/client shared-memory roles) -- https://doc.dpdk.org/guides/nics/memif.html
6. FDio/vpp source tree (node registrations cited above) -- https://github.com/FDio/vpp
7. "The eXpress Data Path: Fast Programmable Packet Processing in the Operating System Kernel," CoNEXT 2018 (ACM), DOI 10.1145/3281411.3281443 -- XDP-vs-DPDK-class bypass evaluation; resolver https://doi.org/10.1145/3281411.3281443
