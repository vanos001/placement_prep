# XDP and AF_XDP

> XDP (eXpress Data Path) runs an eBPF program at the earliest point a
> packet exists in Linux: inside the driver's RX path, before skbs are
> allocated. From `XDP_DROP` DDoS filters to `AF_XDP` sockets that hand
> raw frames to userspace with zero copies, XDP turned Linux from a
> host that *receives* packets into one that can *dispose* of them at
> line rate. This page covers the execution points, the actions, the
> memory model behind zero-copy, and where XDP beats — and loses to —
> DPDK.

## Where XDP Runs

A NIC delivers frames into an RX ring of descriptors pointing at packet
buffers. XDP hooks exactly there:

```text
        NIC hardware
             │ DMA
             ▼
   RX ring descriptors ── packet buffers (per-queue, per-RSS-CPU)
             │
             ▼
   xdp_buff {data, data_end, data_meta}   <- NO skb allocated yet
             │
             ▼
   XDP program (eBPF) returns one action:
     XDP_PASS      -> build skb, continue up the normal stack
     XDP_DROP      -> recycle buffer; packet gone (fast path: ~10-20ns)
     XDP_TX        -> transmit back out the SAME NIC queue
     XDP_REDIRECT  -> another queue/NIC (XDP_TX-like) or an AF_XDP socket
     XDP_ABORTED   -> drop + tracepoint (program bug signal)

   generic XDP:   hook after skb allocation in receive path (any NIC,
                  slower — exists for testing only)
   native XDP:    driver implements the hook before skb alloc
   zero-copy:     driver donates the DMA buffer pool to an AF_XDP
                  socket; frames are never copied at all
```

The per-queue, per-CPU placement matters: with RSS steering flows to
queues, each XDP program instance runs lock-free on its own CPU, and
`XDP_TX` loops a packet back without ever touching the stack — the
basis of in-NIC load balancers (Katran-style) and firewalls.

## The Actions and Their Costs

| Action | What happens | Typical use |
|---|---|---|
| `XDP_DROP` | Buffer returned to driver ring | DDoS scrubbing: 10-25M pps/core |
| `XDP_TX` | Rewrite header, retransmit same queue | SYN cookies, LB backends |
| `XDP_REDIRECT` | To another NIC/queue (nd_xdp_xmit) or AF_XDP | L2 LB, packet capture |
| `XDP_PASS` | Build skb, enter normal stack | selective inspection |

`XDP_PASS` is the only action that allocates an skb — the whole design
goal is to make everything else skb-free. Note the asymmetry with
tc/eBPF: tc programs run *after* skb allocation, so they cannot match
XDP's per-packet cost floor no matter how good their bytecode is.

## AF_XDP: Zero-Copy to Userspace

`AF_XDP` is a socket address family whose receive path is an XDP
`XDP_REDIRECT` into a userspace-visible ring. The memory model:

```text
  UMEM: a registered region of (usually huge) pages, carved into
        4096B frames, addressed by 15-bit frame indexes

  FILL ring:  app -> kernel   "here are empty frames, use them for RX"
  RX ring:    kernel -> app   "these frames now hold packets"
  TX ring:    app -> kernel   "these frames hold packets to send"
  COMP ring:  kernel -> app   "these TX frames are done, recycle"

  XDP_REDIRECT with mode XDP_ZEROCOPY: the driver's DMA writes into
  UMEM frames directly; userspace reads the same bytes the NIC wrote.
  No skb, no copy, no syscall (rings are mapped via mmap).
```

Copy-mode (`XDP_COPY`) exists as the fallback: the driver copies into
UMEM frames, which works on any NIC but loses the zero-copy property.
The socket API (`xdp_socket(7)` docs) exposes `XDP_UMEM_REG`,
`XDP_UMEM_FILL_RING`, `XDP_UMEM_COMPLETION_RING` via socket options and
`XDP_SHARED_UMEM` for sharing one UMEM among sockets/queues.

## XDP vs DPDK

| Dimension | XDP | DPDK |
|---|---|---|
| Driver model | in-kernel drivers, hooks in RX path | userspace PMDs own the NIC (kernel driver unbound) |
| Programmability | eBPF, verifier-checked, hot-swappable | C code in your app |
| Syscalls per packet | none (rings) | none (PMD loops) |
| Ecosystem with Linux stack | native: PASS into stack per-packet | none: kernel networking bypassed |
| Interop with existing daemons | yes (XDP_PASS) | no (separate dataplane) |
| Peak pps/core | slightly below DPDK | ceiling |
| Safety | verifier: no crashes, no loops | your responsibility |

The decision rule used in practice: if packets must *sometimes* reach
the Linux stack (or you need to patch data-plane logic at runtime),
XDP; if you are building a dedicated appliance that will never call
`send()`, DPDK's ceiling can win. AF_XDP narrows the gap: benchmarks
with the xdp-project's `xdpsock` sample show AF_XDP zero-copy within
striking distance of DPDK raw-ring throughput for simple loops, while
keeping the kernel driver (and thus `ethtool`, counters, XDP_PASS
fallback).

## Constraints Worth Knowing

- **Verifier limits**: XDP programs are bounded (instructions, no
  unbounded loops), so "just parse deeper" costs program complexity —
  protocol headers via bounded loops only.
- **Driver maturity varies**: native mode requires driver support;
  zero-copy fewer still. `xdp-device` tooling (`xdp-loader`, bpftool)
  reports per-NIC capability.
- **Frame size**: UMEM frames are fixed (4 KiB default); jumbos need
  XDP programs that handle multi-buffer (`XDP_PKT_MM`-style multi-buff
  support landed per-driver).
- **Checksums**: XDP_TX/REDIRECT retransmit frames without the stack's
  checksum path — programs that rewrite L4 must fix checksums
  themselves (or use driver offload hints).

## Worked Demo: An XDP Action Table

The demo implements a deterministic mini-XDP: a packet trace flows
through a program with a blocklist and a mirror rule, and reports the
per-action tallies plus the effective "ppps" (packets per second the
stack never sees). It models exactly the counters an operator would
read from `bpftool prog show` stats.

```python
# Deterministic XDP action dispatch over a synthetic packet trace.
# Packets: (src_ip_last_octet, port, syn_flag). Program policy:
#   - src in BLOCKLIST                 -> XDP_DROP
#   - TCP SYN to port 443              -> XDP_TX (SYN-cookie style reply)
#   - otherwise                        -> XDP_PASS
# Counters mirror what bpftool would report per action.

BLOCKLIST = {23}
TRACE = [
    (10, 443, True), (23, 80, False), (23, 443, True),
    (11, 443, True), (12, 80, False), (23, 8080, False),
    (13, 443, False), (23, 443, True), (14, 22, False),
]

counts = {"XDP_DROP": 0, "XDP_TX": 0, "XDP_PASS": 0}

def xdp_program(pkt):
    src, port, syn = pkt
    if src in BLOCKLIST:
        return "XDP_DROP"
    if port == 443 and syn:
        return "XDP_TX"
    return "XDP_PASS"

for pkt in TRACE:
    counts[xdp_program(pkt)] += 1

total = len(TRACE)
reached_stack = counts["XDP_PASS"]
print(f"packets: {total}")
for a in ("XDP_DROP", "XDP_TX", "XDP_PASS"):
    print(f"  {a}: {counts[a]}")
print(f"stack load avoided: {total - reached_stack}/{total} "
      f"({100 * (total - reached_stack) / total:.0f}%)")
```

Real output:

```text
packets: 9
  XDP_DROP: 4
  XDP_TX: 2
  XDP_PASS: 3
stack load avoided: 6/9 (67%)
```

Under DDoS conditions the real numbers invert dramatically: an attack
trace where 95% of packets hit the blocklist leaves the kernel stack
handling 1 in 20 packets — the difference between a saturated host and
an idle one.

## Interview Questions

1. Why can an XDP program be faster than an identical tc/eBPF program?
   (No skb allocation or metadata initialization on the XDP path; tc
   starts after the stack has already built an skb.)
2. What does zero-copy AF_XDP actually share, and what are the four
   rings? (UMEM frames via DMA; FILL/RX for receive, TX/COMP for
   transmit.)
3. When would you pick XDP_TX over XDP_REDIRECT?
   (Reply from the same queue/NIC — no cross-NIC DMA; REDIRECT is for
   shipping to a different NIC or socket.)
4. How does RSS interact with XDP's scaling?
   (Per-queue programs run per-CPU lock-free; RSS spreads flows, so
   hash-based LB logic works without any locking.)
5. Your DDoS filter in XDP still passes too much traffic — what are the
   first two things to check? (Action counters via bpftool: is the
   program actually attached in native mode? Is the blocklist matching
   the field the attack varies — port vs IP vs payload hash?)

## References

- Kernel docs: *AF_XDP* — https://docs.kernel.org/networking/af_xdp.html
  (probed 200); *XDP RX metadata* —
  https://docs.kernel.org/networking/xdp-rx-metadata.html (probed 200)
- iovisor XDP overview: https://www.iovisor.org/technology/xdp
  (probed 200)
- xdp-project tutorial (driver capability tables, setup):
  https://github.com/xdp-project/xdp-tutorial (probed 200)
- LWN: Corbet, J. *Accelerating networking with AF_XDP*.
  https://lwn.net/Articles/750845/ (probed 200) and
  *AF_XDP: introducing zero-copy support*.
  https://lwn.net/Articles/756549/ (probed 200)
- Linux source: `net/xdp/xsk.c`, `include/net/xdp.h` —
  https://github.com/torvalds/linux/blob/master/net/xdp/xsk.c (probed 200)

## Cross-References

- [io_uring internals](../../../os/advanced/fast-io.md) — the completion-
  based sibling for storage; XDP rings follow the same zero-copy
  philosophy for packets.
- [eBPF verifier](../bpf-verifier.md) — why XDP
  programs cannot crash the kernel.
- [DPDK](../../../os/advanced/dpdk.md) — the bypass alternative and when
  each wins.
