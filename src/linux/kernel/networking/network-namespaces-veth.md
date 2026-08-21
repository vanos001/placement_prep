# Network namespaces and veth pairs

## The kernel's isolation primitive for networking

A **network namespace** (`struct net`, `include/net/net_namespace.h`) is the Linux kernel's mechanism for giving a process (or set of processes) a private view of the networking stack. Inside a netns, the system sees its own set of network interfaces, its own routing table, its own `iptables`/`nftables` rules, its own ARP/ND table, its own `/proc/net` and `/sys/class/net`, its own neighbour cache, its own conntrack table view, its own unix-domain-socket namespace, its own port number space, and its own loopback device.

This is the foundation on which container networking rests: every Docker container, every Kubernetes pod, every systemd-nspawn machine gets its own netns by default. Without netns, you'd have to invent a userspace TCP/IP stack or rely on VLANs (which only isolate L2).

The first netns is the *init* namespace — what we normally call "the host's network". When you create a new netns, the kernel allocates a fresh `struct net` (about 4 KB on 64-bit), initializes a new loopback (`lo`), an empty routing table, an empty `dev` list, and registers the new netns with `net_alloc()` and `setup_net()`.

## Creating and entering a netns

There are two ways to create a netns:

**1. With `unshare(1)` or `clone(2)` with `CLONE_NEWNET`.** This creates the netns as part of a new process. `ip netns` wraps it:

```
ip netns add blue
ip netns exec blue -- ip link set lo up
ip netns exec blue -- ip addr add 10.0.0.1/24 dev lo
```

`ip netns add` does the `unshare(CLONE_NEWNET)` itself, holds the netns open by bind-mounting `/proc/self/ns/net` onto `/var/run/netns/blue` (the default location for `ip netns`). This means the namespace survives the `ip` process — it stays alive until the bind mount is removed by `ip netns del blue`.

**2. Directly via `clone(2)` in code:**

```c
#define _GNU_SOURCE
#include <sched.h>
#include <unistd.h>
#include <sys/wait.h>
#include <stdio.h>

int main(void) {
    pid_t pid = clone(child_main, stack_top,
                      CLONE_NEWNET | SIGCHLD, NULL);
    if (pid < 0) { perror("clone"); return 1; }
    waitpid(pid, NULL, 0);
    return 0;
}
```

`setns(2)` lets an existing process move into a different netns by file descriptor — the same `/proc/PID/ns/net` symlink used by bind mounts. This is what `ip netns exec` does:

```
$ ls -l /proc/$$/ns/net
lrwxrwxrwx. 1 user user 0 /proc/1718/ns/net -> 4026531992
$ stat -c %i /proc/self/ns/net   # inode number — your netns ID
```

## What lives inside a netns

```
   +------------------------------------------+
   | struct net (the netns)                   |
   |                                          |
   |   lo (loopback)                          |
   |   eth0, eth1, ...                        |
   |   routing table (fib)                    |
   |   neighbour cache (arp/ndisc)            |
   |   iptables/nftables ruleset              |
   |   conntrack view                         |
   |   unix-domain sockets namespace          |
   |   /proc/net, /sys/class/net view         |
   |   ipv4.dev_conf (per-net sysctls)        |
   |                                          |
   +------------------------------------------+
```

The full list is in `net_assign_generic()` and `setup_net()` in `net/core/net_namespace.c`. Notable per-netns members:

- `loopback_net` — a per-netns `lo` device, link type 772, MTU 65536, created in `net_ns_init()`.
- `ipv4`/`ipv6` — per-netns routing tables, FIBs, and the `devconf` sysctls (`/proc/sys/net/ipv4/conf/all/*`).
- `netfilter` — per-netns ruleset and per-netns conntrack view (the global hash is shared but entries are tagged with `ct_net`).
- `xfrm` — per-netns IPsec state.

The actual netns "operations vector" is `pernet_operations` — registered subsystems add a `setup` and `exit` callback. The full list lives in `net/core/net_namespace.c`'s `init_net_ns` and is iterated on every netns creation and deletion.

## Veth pairs: the wire between namespaces

A netns is useless without connectivity. The simplest way to give a netns access to the wider network is a **veth pair** — a pair of virtual interfaces linked at L2, where a packet sent in one end pops out the other (and vice versa).

Conceptually:

```
       +--------------+               +--------------+
       |   veth-a     | <==virtual==> |   veth-b     |
       | (in netns A) |               | (in netns B) |
       +--------------+               +--------------+
              |                              |
           (its own                          (its own
            MAC, IP,                         MAC, IP,
            rx/tx stats)                     rx/tx stats)
```

A veth pair is created as a single device pair:

```
ip link add veth-a type veth peer name veth-b
```

By default both ends live in the *current* netns. To move one end, use `ip link set netns`:

```
ip link set veth-b netns blue
```

After moving:

```
ip -n blue link show     # list interfaces in netns blue
ip -n blue addr add 10.0.0.2/24 dev veth-b
ip -n blue link set veth-b up
ip -n blue link set lo up
ip -n blue route add default via 10.0.0.1
```

The `-n` flag is shorthand for `ip netns exec NAME --`.

From the kernel side, veth is implemented in `drivers/net/veth.c`. The pair is two `struct net_device`s, each carrying `struct veth_priv *` pointing to the peer:

```c
struct veth_priv {
    struct net_device __rcu *peer;     /* the other end */
    atomic64_t dropped;
    struct bpf_prog __rcu *_xdp_prog;
    struct veth_rq *rq;                /* per-CPU NAPI context */
    unsigned int requested_headroom;
    int xdp_queue_index;
};
```

`veth_xmit()` is the transmit function. When the kernel hands a packet to `dev_queue_xmit(skb)` on one end, the driver calls `veth_xmit`, which in turn calls `netif_receive_skb()` on the peer's `net_device` (after some queue management for NAPI). The packet never touches a wire — it's a `sk_buff` pointer hop. Cost: a clone of the metadata, one skb clone or pointer swap depending on the XDP path, and a softirq to deliver on the peer's CPU.

Important nuance: veth is **per-CPU**. The peer's RX is scheduled on the peer CPU via an IPI. With XDP, veth can be used as a fast in-kernel packet transfer path for XDP program testing — `xdpgeneric`/`xdpdrv`/`xdpoffload` modes are honored.

## Bridging namespaces

Two veth ends can be plugged into a Linux bridge (`brctl`/`ip link add name br0 type bridge`) — that's how Docker's default `docker0` works:

```
         +----------------------+
         |  docker0 (bridge)    |
         |  MAC 02:42:..:..:..  |
         +----------------------+
            |       |       |
        veth0   veth1   veth2      (host side)
            |       |       |
        [container1]  [container2]  [container3]
        eth0     eth0     eth0     (container side, in respective netns)
```

```
ip link add br0 type bridge
ip link set br0 up
ip addr add 172.17.0.1/16 dev br0

for c in 1 2 3; do
    ip netns add c$c
    ip link add veth$c type veth peer name eth0 netns c$c
    ip link set veth$c master br0
    ip link set veth$c up
    ip -n c$c link set lo up
    ip -n c$c link set eth0 up
    ip -n c$c addr add 172.17.0.$((c+1))/16 dev eth0
done
```

Now containers `c1`, `c2`, `c3` can talk to each other and to the host at `172.17.0.1`. To give them external connectivity, add masquerade (SNAT):

```
iptables -t nat -A POSTROUTING -s 172.17.0.0/16 -o eth0 -j MASQUERADE
# plus
iptables -A FORWARD -i br0 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o br0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
echo 1 > /proc/sys/net/ipv4/ip_forward
```

This is, in essence, what Docker does.

## Routing between namespaces (no bridge)

A netns is also a router. To make two netns talk without a bridge, build a triangle:

```
      +-------------+              +-------------+
      |   netns r1  |              |   netns r2  |
      |             |              |             |
      |  veth-r1    | <===pair===> |   veth-r2   |
      | 10.0.1.1/24 |              | 10.0.1.2/24 |
      |             |              |             |
      | (route to   |              | (route to   |
      |  10.0.2.0/24|              |  10.0.1.0/24|
      |  via r2)    |              |  via r1)    |
      +-------------+              +-------------+
```

Commands:

```
ip netns add r1
ip netns add r2
ip link add veth-r1 type veth peer name veth-r2
ip link set veth-r1 netns r1
ip link set veth-r2 netns r2
ip -n r1 link set lo up
ip -n r2 link set lo up
ip -n r1 link set veth-r1 up
ip -n r2 link set veth-r2 up
ip -n r1 addr add 10.0.1.1/24 dev veth-r1
ip -n r2 addr add 10.0.1.2/24 dev veth-r2
```

Confirm:

```
ip -n r1 route
ip netns exec r1 ping 10.0.1.2
```

To reach *another* subnet via this router you'd add a default route, e.g. `ip -n r1 route add default via 10.0.1.2`. This is the building block of network simulators like `mininet` and complex pod networks.

## MACVLAN and IPVLAN

For containers that share a single parent interface but want distinct L2 (or L3) identities, **MACVLAN** and **IPVLAN** provide lighter alternatives to bridge+veth.

**MACVLAN**: Each child device gets its own MAC address on the parent's wire. The switch learns each child as a separate host. Modes:

- `private` — children cannot communicate with each other (no hairpin)
- `vepa` (Virtual Ethernet Port Aggregator) — all traffic to the parent must come back to the parent (requires a hairpin-aware switch, used with VEPA switches)
- `bridge` — children can talk to each other directly (the most common mode)
- `passthru` — single child takes over the parent

```
ip link add link eth0 name mac0 type macvlan mode bridge
```

**IPVLAN**: Children share the parent's MAC. Distinguishing between them happens at L3 — the kernel demuxes based on destination IP. Modes `L2` (L2-like, ARP is proxied by parent) and `L3`/`L3S` (the parent acts as a router, requires a route in each child). L3S is what allows containers to be addressable from outside without L2 broadcast — used in Calico's eBPF mode.

```
ip link add link eth0 name ipvl0 type ipvlan mode l3
```

Both MACVLAN and IPVLAN live in `drivers/net/macvlan.c` and `drivers/net/ipvlan/ipvlan_core.c` respectively.

## Comparison: VLAN, MACVLAN, IPVLAN, veth+bridge

| Feature | VLAN (802.1Q) | MACVLAN | IPVLAN | veth + bridge |
|---------|---------------|---------|--------|----------------|
| Layers | L2 (tag) | L2 (MAC) | L3 (IP) | L2 (MAC) |
| Per-child MAC | No (parent's) | Yes | No (parent's) | Yes |
| Hardware switch required | Yes (tag) | Optional | No | No |
| External L2 connectivity | Yes | Yes | No (L3 only) | Yes (via bridge) |
| BPF/XDP friendly | Yes | Yes | Partially | Yes |
| Packet path cost | Tag add/remove | demux | demux + route | softirq hop |
| Where used | data center VLANs | VMs/containers in same L2 | cloud pod networks | typical container bridge |

VLAN is L2 broadcast-domain separation enforced by an 802.1Q tag. The kernel uses `vlan_dev` (`net/8021q/vlan_core.c`), reuses the parent's MAC, and is transparent above L2. For container isolation, MACVLAN/IPVLAN are usually more flexible than 802.1Q because a single parent can host thousands of distinct MACs/IPs without VLAN ID exhaustion (only 4096 VLANs).

## Worked example: a three-netns topology

Goal: namespaces `a`, `b`, `c` plugged into a central bridge `br0`, with `c` able to reach the host's network via NAT.

```
#!/bin/bash
set -e
# Bridge
ip link add br0 type bridge
ip link set br0 up
ip addr add 10.10.0.1/24 dev br0

# Namespaces
for ns in a b c; do
    ip netns add $ns
    ip -n $ns link set lo up
    ip link add v-$ns type veth peer name eth0 netns $ns
    ip link set v-$ns master br0
    ip link set v-$ns up
    ip -n $ns link set eth0 up
done

# Addresses
ip -n a addr add 10.10.0.2/24 dev eth0
ip -n b addr add 10.10.0.3/24 dev eth0
ip -n c addr add 10.10.0.4/24 dev eth0
for ns in a b c; do
    ip -n $ns route add default via 10.10.0.1
done

# Host NAT for outbound
iptables -t nat -A POSTROUTING -s 10.10.0.0/24 -o eth0 -j MASQUERADE
iptables -A FORWARD -i br0 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o br0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sysctl -w net.ipv4.ip_forward=1

# Sanity checks
ip netns exec a ping -c1 10.10.0.3
ip netns exec c ping -c1 8.8.8.8
```

Run it as root. After teardown, `ip netns del a b c` and `ip link del br0` will clean up (deleting the bridge also deletes the host-end veths; deleting the netns removes the in-netns eth0).

## Things to know for production

- **Resource limits**: every netns has its own netstack data structures but they share host RAM. Use `ip netns add` moderately; 10 000 netns is fine, 1 M is not. The `nf_conntrack` hash is shared across all netns, so a misbehaving pod can fill the host table.
- **Per-netns sysctls**: `ip netns exec ns sysctl -w net.ipv4.ip_forward=0` toggles forwarding only inside `ns`. The host setting does not change.
- **Cleanup**: deleting a netns via `ip netns del` requires all references gone. `unshare -n` processes hold their netns; `setns`d processes hold it; bind mounts hold it. To find leaks, `lsns -t net` lists all live netns and their holder PIDs.
- **Container runtimes**: runc/containerd create netns per-container and use CNI plugins to plug in the veth pair. CNI itself is essentially `ip link add … type veth` followed by `ip link set netns`.
- **eBPF and netns**: many BPF program types are netns-scoped (`BPF_PROG_TYPE_CGROUP_SKB`, `cgroup_sock_addr`). TC/XDP programs attach to a *device*, not a netns, so a container's eth0 veth can have a custom XDP program — used by Cilium for kube-proxy replacement.

## References

- `man 8 ip-netns` — ip netns subcommand: https://man7.org/linux/man-pages/man8/ip-netns.8.html
- `man 4 veth` — veth device: https://man7.org/linux/man-pages/man4/veth.4.html
- `man 2 unshare`, `man 2 clone`, `man 2 setns`: https://man7.org/linux/man-pages/man2/unshare.2.html
- Kernel source `net/core/net_namespace.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/core/net_namespace.c
- Kernel source `drivers/net/veth.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/veth.c
- Kernel source `drivers/net/macvlan.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/macvlan.c
- LWN: "Network namespaces", J. Corbet (2013): https://lwn.net/Articles/580893/
- LWN: "Namespaces in operation, part 3: Network namespaces", M. Kerrisk (2013): https://lwn.net/Articles/546921/
- CNI specification (container network interface): https://github.com/containernetworking/cni/blob/main/SPEC.md
- Linux kernel docs `Documentation/networking/veth.rst` and `Documentation/networking/macvlan.rst`: https://www.kernel.org/doc/html/latest/networking/veth.html
