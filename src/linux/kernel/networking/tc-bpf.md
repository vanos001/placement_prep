# tc-BPF

`tc-BPF` is the use of BPF programs in the Linux traffic control (`tc`) layer to make per-packet scheduling, classification, and rewriting decisions. Unlike XDP (which runs at the driver RX path before sk_buff allocation), `tc` runs after the packet is in the kernel and can modify, drop, or redirect packets on both ingress and egress paths. The combination of `tc` and BPF is the foundation of Cilium's data path, Calico's policy enforcement, and most modern load balancers that need per-connection state.

## Where tc Sits

The Linux packet path has multiple hook points. From the NIC RX queue to a user-space socket:

```text
        NIC RX
          │
          ▼
   driver NAPI poll
          │
          ▼
   XDP hook (BPF)            ← driver RX, can redirect/drop/rewrite
          │
          ▼
   skb alloc, netif_receive_skb
          │
          ▼
   tc ingress hook (BPF)     ← can drop, mark, redirect, recirculate
          │
          ▼
   iptables/nftables PREROUTING
          │
          ▼
   routing decision
          │
          ▼
   ip_local_deliver / ip_forward
          │
          ▼
   Netfilter FORWARD / INPUT
          │
          ▼
   socket receive queue
```

The egress path is the reverse, with a `tc egress` hook between routing and the driver. `tc` runs in softirq context for ingress and either softirq (kernel-generated packets) or process context (forwarded packets) for egress. Programs are limited to ~3.5 µs per packet to avoid starving the softirq budget.

## The tc-BPF Program Model

A `tc` BPF program receives a `__sk_buff` pointer with metadata fields the kernel populates:

```c
struct __sk_buff {
    __u32 len;            /* packet length, can be modified */
    __u32 pkt_type;      /* PACKET_* */
    __u32 mark;           /* skb->mark, persistent across netfilter */
    __u32 queue_mapping;  /* RSS queue override */
    __u32 protocol;       /* ethernet protocol, set to 0 to re-parse */
    __u32 vlan_present;   /* vlan_tci != 0 */
    __u32 vlan_tci;       /* 802.1Q tag */
    __u32 vlan_proto;     /* 802.1Q proto */
    __u32 priority;       /* skb->priority, affects sch_prio */
    __u32 ingress_ifindex;
    __u32 ifindex;         /* output device */
    __u32 tc_index;        /* skb->tc_index */
    __u32 cb[5];           /* control block: 5 u32s shared with iptables */
    __u32 hash;            /* skb->hash, populated by hardware RSS */
    __u32 tc_classid;      /* classifier verdict: TC_H_*, use bpf_set_tc_class() */
    __u32 data;            /* start of L2 header */
    __u32 data_end;        /* end of L2 header */
    /* more fields in BPF_PROG_TYPE_SCHED_ACT vs CLS */
};
```

The program returns one of the verdicts:

| Verdict | Numeric | Effect |
|---------|--------:|--------|
| `TC_ACT_OK`     | 0  | Continue processing; use `skb->tc_classid` to pick the queue |
| `TC_ACT_RECLASSIFY` | 1 | Re-run the classifier chain |
| `TC_ACT_SHOT`   | 2  | Drop the packet; charge the dropping qdisc |
| `TC_ACT_STOLEN` | 3  | The packet was redirected; do not free it from this path |
| `TC_ACT_QUEUED` | 4  | The packet was queued for later processing |
| `TC_ACT_REPEAT` | 5  | Restart from the top of the current classifier |

For `SCHED_ACT` programs, additional helpers are available: `bpf_skb_load_bytes`, `bpf_skb_store_bytes`, `bpf_skb_vlan_push`, `bpf_skb_vlan_pop`, `bpf_skb_adjust_room`, `bpf_csum_diff`, `bpf_l3_csum_replace`, `bpf_l4_csum_replace`, `bpf_skb_redirect`, `bpf_skb_change_head`, `bpf_skb_change_proto`, `bpf_clone_redirect`, and many more.

## Loading a tc-BPF Program

```bash
# Compile the program
clang -O2 -g -target bpf -c my_classifier.c -o my_classifier.o

# Load as a classifier on ingress of eth0
tc qdisc add dev eth0 ingress
tc filter add dev eth0 ingress bpf da obj my_classifier.o sec classifier flowid 1:1

# Or load as an action (post-classification)
tc filter add dev eth0 ingress pref 1 bpf da obj my_classifier.o sec classifier action mpls
```

`da` ("direct-action") tells tc to use the BPF program's verdict directly, without involving a separate qdisc. This is the modern idiom — `da` removes a layer of indirection and is the only mode that lets the program return `TC_ACT_SHOT`.

For egress, replace `ingress` with `clsact`-style:

```bash
tc qdisc add dev eth0 clsact   # creates both ingress and egress
tc filter add dev eth0 egress bpf da obj my_classifier.o sec egress_cls
```

`clsact` is the modern qdisc that exists only to host ingress/egress BPF programs. It adds no queuing and is required if you want BPF on egress.

## A Concrete Classifier

A common pattern is DSCP marking: parse the IP header, look up the flow's class in a BPF map, set the DSCP field, recompute the IP checksum incrementally.

```c
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <linux/ip.h>
#include <bpf/bpf_helpers.h>

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __type(key, __u32);   /* source IPv4 */
    __type(value, __u8);  /* DSCP value */
    __uint(max_entries, 65536);
} dscp_map SEC(".maps");

SEC("classifier")
int mark_dscp(struct __sk_buff *skb) {
    void *data = (void *)(unsigned long)skb->data;
    void *data_end = (void *)(unsigned long)skb->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return TC_ACT_OK;

    if (eth->h_proto != __builtin_bswap16(ETH_P_IP))
        return TC_ACT_OK;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return TC_ACT_OK;

    __u32 src = ip->saddr;
    __u8 *dscp = bpf_map_lookup_elem(&dscp_map, &src);
    if (!dscp)
        return TC_ACT_OK;

    __u8 new_tos = (*dscp << 2) | (ip->tos & 0x03);
    /* Incremental checksum update: see bpf_l3_csum_replace */
    __u32 csum_diff = bpf_csum_diff((__u32 *)&ip->tos, 4,
                                    (__u32 *)&new_tos, 4, 0);
    bpf_l3_csum_replace(skb, offsetof(struct iphdr, check) +
                       offsetof(struct iphdr, tos) - offsetof(struct iphdr, check),
                       ip->tos, new_tos, 2);
    /* Actually rewrite the field */
    if (bpf_skb_store_bytes(skb, sizeof(*eth) +
                            offsetof(struct iphdr, tos),
                            &new_tos, sizeof(new_tos), 0))
        return TC_ACT_SHOT;
    return TC_ACT_OK;
}

char _license[] SEC("license") = "GPL";
```

The program is 80 lines of code and runs in ~50 ns per packet on a modern CPU. A `skbedit` program of this complexity sustained at 100 Gbps on a single CPU core is the design point for Cilium and Calico's data planes.

## Comparison to Alternatives

| Mechanism | When it runs | Use case |
|-----------|-------------|----------|
| `iptables`/`nftables` | After tc (in `PRE_ROUTING`/`INPUT`/`FORWARD`/`OUTPUT`/`POST_ROUTING`) | Stateful filtering, NAT |
| `tc` (`sch_*` qdiscs) | Softirq, before Netfilter | Shaping, scheduling |
| `tc cls/act` (BPF) | Softirq, in `tc` | Per-flow logic, custom rewriting |
| `XDP` (BPF) | Driver RX, before skb alloc | Custom high-rate forwarding, before kernel stack |
| `cgroup/skb` (BPF) | Socket bind and recv | Per-socket filtering |
| `sk_skb` (BPF) | Socket recv/send | Per-socket processing (strparser) |

`tc-BPF` vs `XDP`: XDP is faster (no sk_buff allocation, no kernel stack), but cannot see packets that the kernel generated (TCP retransmissions, ICMP errors) or that loopback. `tc` sees all of these. The two are complementary: XDP for the high-rate hot path, tc for the full-featured path.

## Production Tooling: Cilium

Cilium compiles a single BPF program per interface that handles:

- Network policy enforcement (drop packets that don't match any allow rule)
- Service load balancing (DNAT to a backend endpoint selected from a BPF map)
- DSR (Direct Server Return) for bypassing the LB on egress
- Source-based routing (overlay encapsulation)

```bash
# See the BPF programs Cilium has loaded
tc filter show dev eth0 ingress
tc filter show dev eth0 egress

# See the Cilium-internal maps
bpftool map list | grep cilium
```

A single Cilium-managed interface on a busy node typically has 6–10 BPF programs: `from-netdev`, `from-container`, `to-netdev`, `to-container`, `to-overlay`, `from-overlay`, `egress-gw`, and a few more. Each is ~5–20 KB of bytecode.

## Pitfalls

1. **`bpf_skb_store_bytes` invalidates the cached `data`/`data_end` pointers.** After any rewrite, you must re-fetch `data` and `data_end`. The verifier catches pointer-staleness by tag tracking — if you skip the re-fetch, the load is rejected.
2. **`tc ingress` does not see packets from the loopback device.** Loopback traffic has no `tc` ingress hook. Use `tc egress` on `lo` or use `bpf_prog_test_run` in tests.
3. **State (`bpf_map_update_elem`) is shared across all cores.** Lock contention on BPF maps can be a bottleneck at high PPS. Use `BPF_MAP_TYPE_LRU_HASH` for per-flow state — each core has its own LRU cache.
4. **`tc` programs can be loaded multiple times for different `pref` values.** They run in `pref` order until one returns a non-OK verdict. This can lead to surprising "drop" verdicts when a low-priority program shoots a packet a high-priority program was supposed to forward.
5. **Loading a `da` program is not the same as loading a `cls/act` pair.** `da` (direct action) lets the program's verdict directly affect the packet; non-`da` programs only set `skb->tc_classid` and let the qdisc decide.

## References

- [kernel.org: tc-BPF documentation](https://docs.kernel.org/networking/tc_clsact.html)
- [Cilium documentation: BPF datapath](https://docs.cilium.io/en/latest/bpf/)
- Daniel Borkmann, "[tc BPF — A practical look](https://qmonnet.github.io/whirl-offload/2019/04/18/tc-bpf-egress/)"
- Daniel Borkmann, "[BPF: The next generation packet filter](https://www.netdevconf.org/2.1/session.html?borkmann-bpf)" (netdevconf 2.1, 2017)
- [`tc-bpf(8)` manpage](https://man7.org/linux/man-pages/man8/tc-bpf.8.html)
- [LWN: "SCH_BPF: Traffic control with BPF" (2016)](https://lwn.net/Articles/680875/)
