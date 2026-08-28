# sk_buff Anatomy: The Envelope the Linux Network Stack Lives In

Every packet that moves through the Linux kernel travels inside a `struct sk_buff`
("skb"). The struct itself carries no packet data — it is a bag of pointers, lengths,
flags, and reference counts that describes where the packet lives in memory. Once you
can read the four central pointers and the `skb_shared_info` block that trails every
buffer, driver code, protocol code, and offload code all become predictable. This page
is a layout-and-lifetime deep dive; for a survey-level tour of the whole stack see
[the kernel networking overview](./overview.md) and the
[OS-level network stack chapter](../../../os/kernel-advanced/network-stack.md).

## One envelope, four pointers

A skb is a *double-ended queue over a linear memory region*: headers get prepended on
transmit, headers get consumed on receive, and the same buffer must support both
directions without ever copying payload. Four pointers make that possible:

| Pointer | Points at | Invariant |
|---|---|---|
| `head` | First byte of the allocated data area | Fixed for the life of the data area |
| `data` | First byte of the current protocol header | Moves down on receive (`skb_pull`), up on transmit (`skb_push`) |
| `tail` | One past the last byte of packet content | Moves up with `skb_put`, down with `skb_trim` |
| `end` | First byte of `skb_shared_info` | Fixed for the life of the data area |

The `sk_buff` struct is pure metadata — roughly 200–250 bytes of bookkeeping on 64-bit
builds — allocated from its own slab cache (`skbuff_head_cache`) so that an skb header
is hot, compact, and independent of the data area it describes. That separation is what
makes `skb_clone()` (below) cheap.

## Physical layout: what alloc_skb actually allocates

`alloc_skb(size)` does not hand you `size` bytes. It asks the page allocator for
`SKB_DATA_ALIGN(size) + sizeof(struct skb_shared_info)` bytes, and the shared-info
block — fragment descriptors, GSO metadata, the dataref — lives *after* `end`, which is
why the tailroom of a fresh skb is already smaller than you asked for. On x86_64 with
4 KiB pages, `MAX_SKB_FRAGS` is 17 and `sizeof(skb_shared_info)` is about 320 bytes.

```text
kmalloc'ed data area (one allocation):
+----------------------+------------------------------+--------------------+
|       headroom       |         packet data          |      tailroom      |
+----------------------+------------------------------+--------------------+
^                      ^                              ^                    ^
head                  data                           tail                 end
|                                                                          |
+-----------------------+----------------------------------------+---------+
|                       |                                        |         |
v                       v                                        v         v
+----------------------+----------------------------------------+---------+
| headroom for header  |        linear data (data .. tail)      | skb_shared_info
| pushes (tx / encap)  |        <- skb->len (linear part) ->    | frags[17], frag_list,
+----------------------+----------------------------------------+ gso_size, gso_segs,
                                                                dataref, destructor
```

Driver receive paths fill this template the same way every time: allocate, `skb_reserve()`
enough headroom for the longest header chain the device may see (`dev->needed_headroom`),
`skb_put()` the frame length, DMA into the data region.

## The pointer walk: reserve, put, push, pull

The four mutators are the entire grammar of the data path:

- `skb_reserve(n)` — advance `data` and `tail` together, carving empty headroom before
  any data exists.
- `skb_put(n)` — claim `n` bytes of tailroom as data (used by the producer: driver RX,
  TCP copy into a send buffer skb).
- `skb_push(n)` — move `data` back by `n` bytes and return the new `data` (used to
  prepend a header: TCP header, IP header, Ethernet header, tunnel headers).
- `skb_pull(n)` — move `data` forward by `n` bytes (used to consume a header:
  `eth_type_trans()` pulls `ETH_HLEN`, `ip_rcv()` pulls the IP header,
  `tcp_v4_rcv()` pulls the TCP header including options).

Receive is therefore a walk of `data` downhill and transmit the same walk uphill. The
headroom a driver reserved is consumed layer by layer on the way in; nothing is copied.
The worked simulation at the end of this page prints the full RX and TX walk with
headroom/tailroom accounting at every stage.

## Headroom economics

Headroom is the scarcest region of the buffer because every encapsulation pushes into
it and `skb_push()` cannot fail gracefully — in the kernel it `BUG`s (via
`skb_under_panic`) if the reservation was wrong. Sizing comes from the device:

- `dev->needed_headroom` — what the driver says it needs (e.g. 32 bytes for a typical
  Ethernet driver: `LL_RESERVED_SPACE` covers link header plus alignment).
- Per-layer growth: VLAN tag (+4), GRE/VXLAN outer headers (+38/+50), IPsec, bonding
  headers. Stacked devices (bond over VLAN over VXLAN) push cumulative reserves down
  into the members via `netdev_update_needed_headroom`-style propagation.
- When headroom really runs out, `pskb_expand_head()` reallocates the data area and
  copies the linear data — a real copy in the fast path, which is exactly why
  under-reserving a driver's headroom shows up as silent throughput loss rather than
  an error.

TCP's transmit reserve is the mirror image: the stack reserves
`ETH_HLEN + IP header + TCP header (+ options)` up front so that `tcp_write_xmit()` can
push each header without expanding.

## The non-linear tail: skb_shared_info, nr_frags, frag_list

Everything past `end` belongs to `skb_shared_info`, and two fields there change what
"the packet" even is:

- `len` is the total packet length; `data_len` is how much of it lives *outside* the
  linear region. A skb is "non-linear" when `data_len > 0`.
- `frags[MAX_SKB_FRAGS]` — up to 17 paged fragment descriptors (each 16 bytes:
  page pointer, offset, size). Jumbo receive and GRO-built skbs and
  [zero-copy sends](./zero-copy-data-paths.md) all live here instead of one linear blob.
- `frag_list` — a chain of *whole other skbs* whose bytes count as this packet's tail.
  GRO uses `frag_list` to stitch original segments together, preserving them intact.

This split has a practical consequence: code that wants to parse payload (IDS, deep
inspection, some NIC formats) must call `skb_linearize()`, which copies every fragment
into the linear region. Anything that only reads headers can proceed — headers are
guaranteed linear.

## clone, copy, and the dataref discipline

`skb_clone()` duplicates the `sk_buff` struct but *shares* the data area and the
`skb_shared_info` block: `shinfo->dataref` goes to 2, both skbs' `head/data/tail/end`
point into the same bytes. It costs one slab allocation and a refcount bump. The rule
that follows: **a clone must not be written.** Pushing a header on a clone moves its
own pointer into bytes the other holder also owns; before any header edit the clone
must call `pskb_expand_head()`, which allocates a fresh data area, copies, and drops
dataref back to 1.

`skb_copy()` is the full duplicate: new struct *and* new data. Use the right one:

| Operation | What is copied | Cost | Typical user |
|---|---|---|---|
| `skb_clone()` | Metadata struct only, data shared | One slab alloc + refcount | Packet taps, GRO bookkeeping, netfilter queueing |
| `pskb_expand_head()` | New data area, linear data re-copied | One alloc + memcpy | Writing headers on a clone, growing headroom |
| `skb_copy()` | Struct + entire linear data | Alloc + full memcpy | When both holders must diverge |
| `skb_linearize()` | Fragments into linear area | Full payload memcpy | Payload inspection, some checksum paths |

The dataref word itself is split into halves for the "headerless clone" trick (clones
whose metadata lies in the *cloned data area* rather than the slab), which is how the
stack can have more holders than slab objects — details live in the long comment above
`skb_shared_info` in `include/linux/skbuff.h`.

## The checksum fields

`skb->ip_summed` is the stack's summary of *who has verified or must produce* the
checksum; the full TX/RX contract — including `csum_start`, `csum_offset`, and
`CHECKSUM_PARTIAL` offload — is the subject of the
[offloads page](./rx-offloads-gro-gso-tso.md). The skb-level summary:

| `ip_summed` | Meaning on receive | Meaning on transmit |
|---|---|---|
| `CHECKSUM_NONE` | Nobody verified; stack must check | Stack computes and fills checksum |
| `CHECKSUM_UNNECESSARY` | Driver verified L4 checksum in hardware | (not used on TX) |
| `CHECKSUM_COMPLETE` | `skb->csum` holds the verified complete sum | (not used on TX) |
| `CHECKSUM_PARTIAL` | Set by GRO or local-origin packets | NIC must complete; stack did everything but the final field |

## Timestamps and tstamp_type

`skb->tstamp` holds a packet timestamp used by three consumers: network
[egress/ingress timestamping](./timestamping.md), TCP's rate pacing (earliest-departure
times ride in `tstamp`), and traffic control ( fq's earliest-departure scheduling).
Kernels of the 6.x series replaced the old mono/realtime flag bit with an explicit
`tstamp_type` selector, so the same field carries wall-clock stamps for `SO_TIMESTAMP`
and CLOCK_TAI stamps for `SO_TIMESTAMPING` without ambiguity. The hardware-stamp story
(PDO, SCM timestamping schemas) lives in the timestamping page; here it matters that a
timestamp is skb metadata, not data, so it survives clones but is zeroed on fresh
allocation.

## Lifetime: who owns an skb and who may free it

An skb's refcount (`skb->users`) governs lifetime; freeing is a *semantic* choice,
reflected in the API you pick:

| Function | Semantics | Use when |
|---|---|---|
| `kfree_skb(skb)` | Drop: records an `SKB_DROP_REASON_*`, fires the `kfree_skb` tracepoint | Any error/drop path |
| `kfree_skb_reason(skb, reason)` | Same, with explicit reason | New code; `kfree_skb` passes `NOT_SPECIFIED` |
| `consume_skb(skb)` | Normal release of a successfully processed packet | Packet was consumed, not dropped |
| `dev_kfree_skb(a)` | Alias for `consume_skb(a)` | Driver code in process context |
| `dev_kfree_skb_irq(skb)` | Deferred free usable from hardirq (completes via softirq) | Driver completing TX from IRQ |
| `dev_kfree_skb_any(skb)` | Picks irq-safe or normal variant by context | Drivers that free from mixed contexts |

The distinction is not cosmetic: `dropwatch`, `perf trace`, and every BPF program
attached to the `kfree_skb` tracepoint rely on `kfree_skb` being called exactly on the
drop path, with the reason encoded, to build "why are we losing packets" tooling.
`consume_skb` events are the denominator that makes drop-rate graphs meaningful.

## Ownership on the transmit path

`dev_queue_xmit()` is a *handoff with no way back*: the moment the skb is enqueued on a
qdisc, the caller must treat it as freed memory. The qdisc may queue it, drop it, or
hand it to another CPU (`XPS`), and the driver frees it after DMA completion. The
`ndo_start_xmit()` callback returns `netdev_tx_t`:

- `NETDEV_TX_OK` — driver took the packet (it will free it later; not necessarily sent).
- `NETDEV_TX_BUSY` — no descriptor space right now; the qdisc requeues and retries.

Anything else is a bug. Holding a pointer after `dev_queue_xmit()` returns is the
classic use-after-free interview answer — the correct pattern is to read what you need
(`skb->len`, timestamps, clone for a tap) *before* the call. Queuing discipline
internals themselves are covered in [the tc page](./tc.md).

## Worked model: pointer accounting in Python

The simulator below models the linear buffer, the shared-info reservation, the RX and
TX pointer walks, and clone/expand semantics. Every assertion encodes a kernel
invariant (for instance, `skb_push` past the headroom would corrupt foreign memory).

```python
#!/usr/bin/env python3
"""skb pointer-accounting simulator.

Models the four-pointer layout (head/data/tail/end) of a linear sk_buff,
the skb_shared_info reservation at the end of the data area, the RX/TX
pointer walk, and skb_clone()/pskb_expand_head() semantics.
Numbers mirror x86_64: SKB_DATA_ALIGN rounds to SMP_CACHE_BYTES = 64;
sizeof(skb_shared_info) ~ 320 B (MAX_SKB_FRAGS = 17 x 16 B descriptors).
"""

SMP_CACHE_BYTES = 64
SHINFO_SIZE = 320          # sizeof(skb_shared_info) on x86_64 (approx.)
ETH_HLEN = 14
IPV4_HLEN = 20
TCP_HLEN_NOOPT = 20
LL_RESERVED = 32           # typical dev->needed_headroom for an ethernet driver


def skb_data_align(size: int) -> int:
    """alloc_skb rounds the user size; the allocator is given
    SKB_DATA_ALIGN(size) + sizeof(skb_shared_info) bytes."""
    return (size + SMP_CACHE_BYTES - 1) & ~(SMP_CACHE_BYTES - 1)


class SimSkb:
    def __init__(self, size: int, tag: str = "skb"):
        self.alloc = skb_data_align(size) + SHINFO_SIZE   # allocator request
        self.head = 0
        self.end = self.alloc - SHINFO_SIZE               # shinfo begins at end
        self.data = self.head
        self.tail = self.head
        self.tag = tag
        self.dataref = 1                                  # shinfo->dataref

    @property
    def headroom(self):
        return self.data - self.head

    @property
    def tailroom(self):
        return self.end - self.tail

    def skb_reserve(self, n: int):
        assert n <= self.tailroom, "skb_reserve: tailroom exhausted"
        self.data += n
        self.tail += n

    def skb_put(self, n: int):
        assert n <= self.tailroom, "skb_put: tailroom exhausted"
        self.tail += n

    def skb_push(self, n: int):
        assert n <= self.headroom, "skb_push: headroom exhausted (would corrupt)"
        self.data -= n

    def skb_pull(self, n: int):
        assert self.tail - self.data >= n, "skb_pull: past end of data"
        self.data += n

    def clone(self):
        """skb_clone(): shares the data area and skb_shared_info."""
        c = SimSkb.__new__(SimSkb)
        c.head, c.data, c.tail, c.end = self.head, self.data, self.tail, self.end
        c.alloc = self.alloc
        c.dataref = 2
        c.tag = self.tag + "-clone"
        self.dataref = 2
        return c


def row(stage: str, skb: SimSkb) -> str:
    return (f"{stage:<30} {skb.headroom:>7} {skb.tailroom:>7} "
            f"{skb.data:>5} {skb.tail:>5} {skb.dataref:>5}")


print("=== A. alloc_skb(2048) raw layout (x86_64, SMP_CACHE_BYTES=64) ===")
skb = SimSkb(2048)
print(f"allocator data area = SKB_DATA_ALIGN(2048) + 320 = {skb.alloc} B")
print(f"{'stage':<30} {'headroom':>7} {'tailroom':>7} {'data':>5} {'tail':>5} {'dref':>5}")
print(row("alloc_skb(2048)", skb))

print()
print("=== B. driver fill: skb_reserve(LL_RESERVED) then skb_put(frame) ===")
frame = 1500
skb.skb_reserve(LL_RESERVED)
print(row(f"skb_reserve({LL_RESERVED})", skb))
skb.skb_put(frame)
print(row(f"skb_put({frame})", skb))

print()
print("=== C. RX pull-through (each layer strips its header) ===")
skb.skb_pull(ETH_HLEN)
print(row("eth_type_trans: pull 14", skb))
skb.skb_pull(IPV4_HLEN)
print(row("ip_rcv: pull 20", skb))
tcp_h = TCP_HLEN_NOOPT + 12
skb.skb_pull(tcp_h)
print(row(f"tcp_v4_rcv: pull {tcp_h}", skb))

print()
print("=== D. TX build-up (reverse walk: push headers before send) ===")
tx = SimSkb(2048, tag="tx-skb")
tx.skb_reserve(ETH_HLEN + IPV4_HLEN + tcp_h)   # typical TCP xmit reserve
tx.skb_put(1460)
print(row("reserve(66) + put(1460)", tx))
tx.skb_push(tcp_h)
print(row(f"tcp_write_xmit: push {tcp_h}", tx))
tx.skb_push(IPV4_HLEN)
print(row("ip_send_skb: push 20", tx))
tx.skb_push(ETH_HLEN)
print(row("dev_hard_header: push 14", tx))

print()
print("=== E. skb_clone(): shared data area, pskb_expand_head() to write ===")
orig = SimSkb(2048, tag="orig")
orig.skb_reserve(LL_RESERVED)
orig.skb_put(frame)
cl = orig.clone()
print(f"after clone: dataref={orig.dataref}, both share the buffer "
      f"(orig.data={orig.data}, clone.data={cl.data})")
print("kernel rule: a clone may not write; header edits need pskb_expand_head()")
exp = SimSkb(2048, tag="expanded")          # expand_head: fresh data area
exp.skb_reserve(LL_RESERVED + 4)            # room for a VLAN tag, e.g.
exp.skb_put(frame)
print(f"pskb_expand_head(clone): new data area, clone.dataref={exp.dataref} "
      f"(orig untouched: {orig.dataref})")
print(f"clone can now skb_push(4): headroom {exp.headroom} -> {exp.headroom - 4}")
```

Output (verified byte-for-byte against a run of this exact script):

```text
=== A. alloc_skb(2048) raw layout (x86_64, SMP_CACHE_BYTES=64) ===
allocator data area = SKB_DATA_ALIGN(2048) + 320 = 2368 B
stage                          headroom tailroom  data  tail  dref
alloc_skb(2048)                      0    2048     0     0     1

=== B. driver fill: skb_reserve(LL_RESERVED) then skb_put(frame) ===
skb_reserve(32)                     32    2016    32    32     1
skb_put(1500)                       32     516    32  1532     1

=== C. RX pull-through (each layer strips its header) ===
eth_type_trans: pull 14             46     516    46  1532     1
ip_rcv: pull 20                     66     516    66  1532     1
tcp_v4_rcv: pull 32                 98     516    98  1532     1

=== D. TX build-up (reverse walk: push headers before send) ===
reserve(66) + put(1460)             66     522    66  1526     1
tcp_write_xmit: push 32             34     522    34  1526     1
ip_send_skb: push 20                14     522    14  1526     1
dev_hard_header: push 14             0     522     0  1526     1

=== E. skb_clone(): shared data area, pskb_expand_head() to write ===
after clone: dataref=2, both share the buffer (orig.data=32, clone.data=32)
kernel rule: a clone may not write; header edits need pskb_expand_head()
pskb_expand_head(clone): new data area, clone.dataref=1 (orig untouched: 2)
clone can now skb_push(4): headroom 36 -> 32
```

Three readings worth taking away: the TX walk ends with *zero* headroom left (that is
what a correctly-sized reserve looks like); the RX walk leaves headroom behind because
`skb_pull` only advances `data`; and section E shows why writing on a clone is a
memory-corruption class of bug rather than a logic bug.

## Questions that reveal you have read the struct

- Why does `skb_shared_info` live after `end` instead of in the struct? Because the
  data area is shared by clones but the *metadata struct* is not: per-clone fields
  must stay out of the shared region, and per-data fields (fragments, dataref) must
  stay out of the per-packet slab.
- What breaks if a driver under-reserves headroom? Not an error — a
  `pskb_expand_head()` copy per packet (or worse, a `skb_under_panic` if a layer pushes
  without checking), visible as throughput loss under encapsulation-heavy traffic.
- Where does a 40 KiB GRO aggregate live if the ring buffer slot was 2 KiB? Nowhere in
  the linear area: the original segments hang off `frag_list`, `len` reports the sum,
  `data_len` reports how much is non-linear.
- `kfree_skb` vs `consume_skb`: which one did your driver use on the TX-complete path,
  and what did it do to the drop-monitor graphs? (TX-complete frees are `consume_skb`;
  a stray `kfree_skb` makes every transmitted packet look like a drop.)
- Who may free an skb after `dev_queue_xmit()`? Not you — ownership transferred; the
  qdisc or driver frees it, possibly on another CPU.

## Reading list

- [struct sk_buff — kernel documentation](https://docs.kernel.org/networking/skbuff.html)
  — the kernel's own annotated skb documentation.
- [include/linux/skbuff.h in the source tree](https://github.com/torvalds/linux/blob/master/include/linux/skbuff.h)
  — struct definition, the `ip_summed` contract comment, and the dataref/headerless-clone
  discussion. (The canonical `git.kernel.org` copy of these paths exists but blocks
  scripted clients with HTTP 403; the GitHub mirror is the same tree.)
- [net/core/skbuff.c](https://github.com/torvalds/linux/blob/master/net/core/skbuff.c)
  — `__alloc_skb`, `skb_clone`, `pskb_expand_head`, `kfree_skb_reason`.
- [packet mmap](https://docs.kernel.org/networking/packet_mmap.html) — how AF_PACKET
  rings expose skb data without copies, the reason clone semantics matter to capture
  tools; see also [the AF_PACKET page](./af-packet.md).
- [zero-copy data paths](./zero-copy-data-paths.md) — page-fragment skbs and
  `MSG_ZEROCOPY` on the same `skb_shared_info` machinery.
