# AF_XDP

`AF_XDP` (Address Family - eXpress Data Path) is the Linux socket family that gives user-space programs near-line-rate packet processing by mapping the kernel's RX ring buffer directly into user-space memory, bypassing the sk_buff allocator, the protocol stack, and the queue-discipline layer. It was merged in kernel 4.18 (2018) and substantially extended by the 5.x series with zero-copy modes, multi-buffer support, and metadata passing.

## Where AF_XDP Sits

The Linux network receive path has many layers:

```text
 NIC hardware RX queue
        │
        ▼
 NAPI poll (softirq)              ← driver pulls frames from RX ring
        │
        ▼
netif_receive_skb()               ← allocates sk_buff, queues for stack
        │
        ▼
 __netif_receive_skb_core()       ← delivers to taps, protocol handlers
        │
        ▼
ip_rcv() / arp_rcv() / ...        ← protocol stack
        │
        ▼
udp_queue_rcv_skb() / tcp_v4_rcv() ← transport layer
        │
        ▼
socket receive queue               ← user-space recv() reads here
```

AF_XDP bypasses all of this. The driver's NAPI poll pushes the frame directly into a UMEM area shared with user-space, and user-space polls an RX ring to learn which offsets in the UMEM contain packets.

## The UMEM and the Rings

An AF_XDP socket has four rings in shared memory:

| Ring | Direction | Contents |
|------|-----------|----------|
| `FILL` | user → kernel | Pointers to free UMEM chunks the kernel can use to receive into |
| `RX`   | kernel → user | Pointers to chunks that contain received packets |
| `TX`   | user → kernel | Pointers to chunks the kernel should transmit |
| `COMPLETION` | kernel → user | Pointers to chunks the kernel has transmitted and that the user can reuse |

The UMEM is a contiguous region of memory registered with the kernel via `setsockopt(SOL_XDP, XDP_UMEM_REG, ...)`. Each packet fits in one chunk (default 4 KB); large packets span multiple chunks when `XDP_USE_NEED_WAKEUP` and `XDP_UMEM_UNALIGNED_CHUNK_FLAG` are configured.

```c
struct xdp_umem_reg {
    __u64 addr;          /* pointer to UMEM memory */
    __u64 chunk_size;    /* bytes per chunk, e.g., 4096 */
    __u64 headroom;      /* reserved headroom for metadata, e.g., 256 */
    __u32 flags;         /* XDP_UMEM_UNALIGNED_CHUNK_FLAG, XDP_UMEM_USE_4K_PAGES */
};

/* The four rings are mmap'd from the socket fd */
xsctx->fill = mmap(NULL, fill_size, PROT_READ|PROT_WRITE,
                   MAP_SHARED|MAP_POPULATE, fd, XDP_PGOFF_FILL_RING);
xsctx->rx   = mmap(NULL, rx_size,   PROT_READ|PROT_WRITE,
                   MAP_SHARED|MAP_POPULATE, fd, XDP_PGOFF_RX_RING);
/* etc. */
```

The fill ring is the contract: user-space pre-stocks it with empty chunk descriptors. The kernel pulls one descriptor per packet received, fills that chunk, and pushes the descriptor onto the RX ring. User-space pulls from the RX ring, processes the packet, and pushes the descriptor back onto the fill ring.

## Modes: Copy, Zero-Copy, Native

AF_XDP has three execution modes:

1. **Copy mode** (`XDP_COPY`): the driver allocates an sk_buff for the received frame (normal path), then copies it into the UMEM chunk pointed to by the fill ring. Works on any NIC. Throughput is bounded by the copy and the sk_buff allocator — typically 5–10 Mpps on a modern CPU core.

2. **Zero-copy mode** (`XDP_ZEROCOPY`): the NIC DMA writes packets directly into UMEM chunks. Requires driver and hardware support for `AF_XDP`-aware rings (Intel ice/i40e, Mellanox mlx5, Broadcom bnxt, Netronome nfp). Throughput limited only by PCIe and NAPI cycle budget — commonly 20+ Mpps per queue on 100 GbE.

3. **Native mode**: zero-copy is on AND the driver is on the XDP fast path (BPF program returns `XDP_REDIRECT` to the socket). No sk_buff allocation, no protocol stack traversal. The fastest path.

Driver support is the gating factor. As of kernel 6.x, `mlx5`, `ice`, `i40e`, `igc`, `bnxt`, `veth`, `tun`, and `virtio_net` support native AF_XDP. `ixgbe` is partial. `e1000e` is copy-only.

## Use Case: User-Space TCP Stack at Line Rate

A common AF_XDP application is a user-space TCP stack for high-performance networking:

```text
┌────────────────────────────────────┐
│  Application: HTTP server, 100 GbE │
│      │                             │
│      ▼                             │
│  User-space TCP/IP stack (F-Stack, │
│    mTCP, Seastar)                 │
│      │                             │
│      ▼                             │
│  AF_XDP socket → UMEM → driver    │ ← zero-copy DMA
│      │                             │
│      ▼                             │
│  NIC RX/TX rings                   │
└────────────────────────────────────┘
```

Seastar (ScyllaDB's engine) uses AF_XDP to bypass the kernel entirely for its RPC and storage protocols. Reported throughput on a single core: 100 GbE line rate for 64-byte UDP packets (~148 Mpps) with zero-copy.

## Use Case: Network Function (Firewall, Load Balancer)

A user-space firewall reads packets from AF_XDP, makes forwarding decisions, and writes them back via the TX ring. The kernel never sees the packet. This is the basis of Cilium's `cilium-agent` data path and Cloudflare's DDoS mitigation pipeline.

## The XDP Program: Where AF_XDP Connects

AF_XDP is paired with an XDP BPF program in the NIC driver's receive path. The BPF program inspects each packet and decides where to send it:

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

struct bpf_map_def SEC("maps/xsks_map") = {
    .type = BPF_MAP_TYPE_XSKMAP,
    .key_size = sizeof(int),    /* RX queue index */
    .value_size = sizeof(int),  /* socket fd */
    .max_entries = 64,
};

SEC("xdp")
int xdp_redirect(struct xdp_md *ctx) {
    int queue = ctx->rx_queue_index;
    /* Look up the socket bound to this queue */
    int *sock_fd = bpf_map_lookup_elem(&xsks_map, &queue);
    if (sock_fd)
        return bpf_redirect_map(&xsks_map, queue, XDP_PASS);
    return XDP_PASS;   /* fall through to stack */
}
```

`bpf_redirect_map` to an `XSKMAP` is the BPF primitive that steers a packet into an AF_XDP socket. Without the XDP program, AF_XDP sockets only receive packets if no in-kernel listener claimed them first.

## BPF Metadata and Multi-Buffer

Kernel 5.x added two capabilities critical for production:

1. **`XDP_UMEM_UNALIGNED_CHUNK_FLAG`** + `XDP_USE_NEED_WAKEUP` — chunks can be placed anywhere in UMEM (not just on chunk-size boundaries), and the kernel only triggers a wake-up when necessary, reducing syscall overhead.

2. **Metadata** — BPF programs can write a small metadata block at the start of the UMEM chunk (in the headroom), which the user-space application reads alongside the packet. This is how timestamps, RX hash, and queue IDs are passed from NIC → BPF → user space without crossing the kernel boundary again.

```c
struct xdp_md_ctx {
    __u64 rx_time;     /* set by BPF using bpf_ktime_get_ns */
    __u32 rx_hash;     /* from ctx->rx_hash */
    __u32 rx_queue;    /* from ctx->rx_queue_index */
} __attribute__((aligned(8)));

/* BPF side */
SEC("xdp")
int xdp_meta(struct xdp_md *ctx) {
    /* Write metadata at the start of the packet's headroom */
    struct xdp_md_ctx *meta = (void *)(unsigned long)ctx->data_meta;
    if ((void *)(meta + 1) > (void *)(unsigned long)ctx->data)
        return XDP_PASS;
    meta->rx_time = bpf_ktime_get_ns();
    meta->rx_hash = ctx->rx_hash;
    meta->rx_queue = ctx->rx_queue_index;
    return bpf_redirect_map(&xsks_map, ctx->rx_queue_index, XDP_PASS);
}

/* User side */
struct xdp_md_ctx *meta = (void *)(pkt - sizeof(*meta));
```

## Pitfalls

1. **`XDP_USE_NEED_WAKEUP` is critical for performance.** Without it, the kernel calls `recvmsg` semantics on every fill-ring push, causing spurious wake-ups. With it, the user polls the ring and only calls `recvmsg` when the ring's flag indicates a wake-up is needed.

2. **Driver support is fragile.** A NIC that works in copy mode may silently fall back in zero-copy mode if the firmware is too old. Verify with `ethtool -i eth0` (driver name and firmware version) before assuming zero-copy is on.

3. **NIC RSS and AF_XDP queues must match.** AF_XDP sockets are bound to a specific RX queue. RSS must direct the right flows to the right queue, or you'll see packets on the kernel stack instead of your socket. Use `ethtool -N eth0 rx-flow-hash ...` to tune RSS.

4. **UMEM memory is `HUGEPAGES`-friendly.** 4 KB pages require 1 GB of UMEM to be backed by 262,144 page-table entries. Use 2 MB hugepages (`MAP_HUGETLB`) — same memory, ~128 entries, far fewer TLB misses.

5. **AF_XDP requires root or `CAP_NET_RAW`.** Without one, `socket(AF_XDP, ...)` fails with `EPERM`. In container environments, this requires running privileged or granting the capability.

6. **AF_XDP is not a replacement for iptables.** It is a high-throughput data path, not a packet-filtering framework. Filtering decisions still need a control-plane tool.

## References

- [kernel.org: XDP documentation](https://docs.kernel.org/networking/af_xdp.html)
- Björn Töpel, Magnus Karlsson, "[AF_XDP: A Linux socket for high-performance networking](https://www.kernel.org/doc/html/latest/networking/af_xdp.html)"
- Magnus Karlsson et al., "[The eXpress Data Path: Fast Programmable Packet Processing in the Operating System Kernel](https://dl.acm.org/doi/10.1145/3281411.3281447)" (ACM CoNEXT 2018)
- [LWN: "AF_XDP: Future of high-performance networking" (2018)](https://lwn.net/Articles/750855/)
- [`libxdp` and `libbpf` XDP tutorials](https://github.com/xdp-project/xdp-tutorial)
- [Intel ice driver AF_XDP documentation](https://www.intel.com/content/www/us/en/docs/networking/ice-user-guide.html)
