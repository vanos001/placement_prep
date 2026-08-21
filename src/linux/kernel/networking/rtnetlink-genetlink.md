# rtnetlink and genetlink

## What netlink is, and why it's not an ioctl

Netlink is the kernel–userspace message multiplexor for Linux networking. It is a `SOCK_RAW` socket family (`AF_NETLINK`, `PF_NETLINK`) implemented in `net/netlink/af_netlink.c` that uses **datagrams with structured TLV payloads** instead of the ad-hoc binary blobs ioctl passes. Two properties distinguish it from ioctl:

1. **Asynchronous, multicast-capable**: the kernel can send unsolicited notifications to any userspace listener — `RTM_NEWLINK` when a NIC appears, `RTM_NEWROUTE` when a route is added, `NLMSG_DONE` after a dump completes. ioctl is fundamentally request–reply.
2. **Multiple protocols over one socket type**: the `protocol` argument to `socket(AF_NETLINK, SOCK_RAW, protocol)` selects the sub-protocol. There are about 25 of these; `NETLINK_ROUTE` (rtnetlink) is the most heavily used, but there is also `NETLINK_AUDIT`, `NETLINK_NETFILTER`, `NETLINK_KOBJECT_UEVENT`, `NETLINK_SCSITRANSPORT`, and a generic extensible channel called `NETLINK_GENERIC` (genetlink).

The canonical reference for the wire format is RFC 3549 ("Linux Netlink as an IP Services Protocol"). The man pages `netlink(7)`, `rtnetlink(7)`, and `genetlink(7)` cover userspace details. The implementation lives in `net/socket.c` (system call entry) and `net/netlink/af_netlink.c` (socket semantics), plus per-protocol subdirectories.

## The netlink message format

Every message starts with a fixed 16-byte header (`struct nlmsghdr` in `include/uapi/linux/netlink.h`):

```c
struct nlmsghdr {
    __u32 nlmsg_len;     /* total length including header */
    __u16 nlmsg_type;    /* message type (RTM_NEWLINK, etc.) */
    __u16 nlmsg_flags;   /* NLM_F_REQUEST, NLM_F_MULTI, NLM_F_DUMP, ... */
    __u32 nlmsg_seq;     /* sequence number */
    __u32 nlmsg_pid;     /* sender port id (= pid historically) */
};
```

The payload follows as a sequence of attributes, each preceded by a 4-byte sub-header:

```c
struct nlattr {
    __u16 nla_len;   /* length including header */
    __u16 nla_type;  /* attribute type */
    /* payload of nla_len - NLA_HDRLEN bytes, NLA aligned to 4 */
};
```

Attributes nest: an attribute's value can itself be a list of `nlattr`s. This is how `RTM_NEWLINK` packs interface name, MAC, statistics, and per-AF address info into one message. The kernel provides helpers (`nla_put`, `nla_put_u32`, `nla_parse`, `nla_get_string`) in `include/net/netlink.h` and `lib/nlattr.c` that handle alignment and bounds checking.

A minimal recv loop on a NETLINK_ROUTE socket:

```c
int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
struct sockaddr_nl sa = { .nl_family = AF_NETLINK };
bind(fd, (struct sockaddr *)&sa, sizeof(sa));

char buf[8192];
ssize_t n = recv(fd, buf, sizeof(buf), 0);
for (struct nlmsghdr *h = (struct nlmsghdr *)buf;
     NLMSG_OK(h, n);
     h = NLMSG_NEXT(h, n)) {
    switch (h->nlmsg_type) {
    case RTM_NEWLINK: {
        struct ifinfomsg *ifi = NLMSG_DATA(h);
        struct rtattr *rta;
        int rlen = IFLA_PAYLOAD(h);
        char ifname[IFNAMSIZ] = "?";
        for (rta = IFLA_RTA(ifi); RTA_OK(rta, rlen); rta = RTA_NEXT(rta, rlen)) {
            if (rta->rta_type == IFLA_IFNAME)
                strncpy(ifname, RTA_DATA(rta), sizeof(ifname)-1);
        }
        printf("ifindex=%d name=%s\n", ifi->ifi_index, ifname);
        break;
    }
    case NLMSG_DONE:
        goto out;
    }
}
out:;
```

This is what `ip link show` is doing behind the scenes. The dump ends with an `NLMSG_DONE` sentinel because `NLM_F_DUMP` requests are streamed.

## rtnetlink: the ROUTE protocol family

`NETLINK_ROUTE` (protocol number 0, defined as `NETLINK_ROUTE` in `include/uapi/linux/netlink.h`) is what `iproute2` speaks. Its messages cover:

| Message type | What it does |
|--------------|--------------|
| `RTM_NEWLINK`, `RTM_DELLINK`, `RTM_GETLINK`, `RTM_SETLINK` | Add/delete/query/modify network interfaces (`struct ifinfomsg`) |
| `RTM_NEWADDR`, `RTM_DELADDR`, `RTM_GETADDR` | Add/delete/query L3 addresses (`struct ifaddrmsg`) |
| `RTM_NEWROUTE`, `RTM_DELROUTE`, `RTM_GETROUTE` | Add/delete/query routes (`struct rtmsg`) |
| `RTM_NEWNEIGH`, `RTM_DELNEIGH`, `RTM_GETNEIGH` | Add/delete/query neighbour (ARP/ND) entries |
| `RTM_NEWRULE`, `RTM_DELRULE`, `RTM_GETRULE` | Routing policy database (RPDB) rules |
| `RTM_NEWQDISC`, `RTM_DELQDISC`, … | Traffic control qdiscs |
| `RTM_NEWTFILTER`, … | Traffic control filters |
| `RTM_NEWNSID`, `RTM_GETNSID` | Network namespace IDs |
| `RTM_NEWCACHEREPORT` | IPv4 route cache notifications |

The kernel-side dispatch is in `net/netlink/rtnetlink.c`. The function `rtnetlink_rcv_msg()` parses the top-level message, looks up a `struct rtnetlink_link` keyed by `[protocol][message_type]`, and calls the registered `doit` (for single operations) or `dumpit` (for dumps) callback. The classic registration call:

```c
rtnl_register(PF_UNSPEC, RTM_GETLINK, rtnl_getlink, rtnl_dump_ifinfo, 0);
rtnl_register(PF_INET,   RTM_NEWROUTE, inet_rtm_newroute, NULL, 0);
rtnl_register(PF_INET6,  RTM_NEWADDR,   inet6_rtm_newaddr, NULL, 0);
```

rtnetlink is **transactional** under a global `rtnl` mutex (`rtnl_lock()` / `rtnl_unlock()`). Most link operations require the lock; this is why `ip link set eth0 up` can stall when another process holds `rtnl` — the kernel's `RTNL` contention is a known throughput problem on hosts that reconfigure networking frequently. There has been ongoing work to make more operations lockless (e.g., `RCU`-protected device lookup), but the big lock remains.

A few important rtnetlink attributes:

- `IFLA_IFNAME` (3) — interface name
- `IFLA_MTU` (4) — MTU
- `IFLA_LINK` (5) — parent ifindex
- `IFLA_QDISC` (6) — qdisc name
- `IFLA_STATS` (7) — `struct rtnl_link_stats`
- `IFLA_ADDRESS` (1), `IFLA_BROADCAST` (2) — MAC addresses
- `IFLA_LINKINFO` (18) — nested; contains `IFLA_INFO_KIND` ("veth", "vlan", "macvlan"…) and `IFLA_INFO_DATA` with kind-specific attributes (e.g., `VETH_INFO_PEER` for the veth peer)
- `IFLA_XDP` (43) — XDP program attachment (prog id, attached mode)

This nesting is why "ip link add veth-a type veth peer name veth-b" is a single message: the outer `RTM_NEWLINK` carries the veth kind and a nested `IFLA_LINKINFO` blob with the peer name.

## Worked example: adding an address without `ip`

You can replace `ip addr add 10.0.0.1/24 dev eth0` with raw netlink:

```c
int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
struct sockaddr_nl sa = { .nl_family = AF_NETLINK };
bind(fd, (struct sockaddr *)&sa, sizeof(sa));

char buf[256];
struct nlmsghdr *h = (struct nlmsghdr *)buf;
struct ifaddrmsg *ifa = (struct ifaddrmsg *)NLMSG_DATA(h);

memset(buf, 0, sizeof(buf));
h->nlmsg_len   = NLMSG_LENGTH(sizeof(*ifa));
h->nlmsg_type  = RTM_NEWADDR;
h->nlmsg_flags = NLM_F_REQUEST | NLM_F_CREATE | NLM_F_EXCL | NLM_F_ACK;
h->nlmsg_seq   = 1;

ifa->ifa_family    = AF_INET;
ifa->ifa_prefixlen = 24;
ifa->ifa_flags     = 0;
ifa->ifa_scope     = RT_SCOPE_UNIVERSE;
ifa->ifa_index     = 2;                /* eth0 — get with RTM_GETLINK */

struct in_addr ip = { .s_addr = htonl(0x0A000001) };  /* 10.0.0.1 */
struct in_addr br = { .s_addr = htonl(0x0A00FFFF) };  /* 10.0.255.255 */

addattr_l(h, sizeof(buf), IFA_LOCAL,   &ip, sizeof(ip));
addattr_l(h, sizeof(buf), IFA_ADDRESS, &ip, sizeof(ip));
addattr_l(h, sizeof(buf), IFA_BROADCAST, &br, sizeof(br));

send(fd, h, h->nlmsg_len, 0);

/* read NLM_F_ACK */
char rbuf[4096];
recv(fd, rbuf, sizeof(rbuf), 0);
/* parse for NLMSG_ERROR with err=0 → success */
```

The `addattr_l` helper is from `iproute2`'s `libnetlink`. libnl (see below) provides the higher-level `rtnl_link_add`/`rtnl_addr_add` APIs.

## genetlink: a kernel API for new protocols

When a kernel subsystem wants to add its own netlink protocol (think taskstats, wireguard, drop_monitor, acpi_event, tcp diagnostics, etc.), the historical approach was to allocate a new protocol number. There are only ~25 slots, and adding one requires editing `include/uapi/linux/netlink.h`. **genetlink** (`NETLINK_GENERIC`, protocol number 16) is the alternative: an indirection layer where new "families" register at runtime and receive a dynamic ID.

The flow:

1. Kernel calls `genl_register_family(&my_family)` with a static `struct genl_family` listing supported operations and multicast groups.
2. Userspace issues `CTRL_CMD_GETFAMILY` on a `NETLINK_GENERIC` socket with the family name as an attribute. The kernel replies with the dynamic family ID, the multicast group IDs, and the operation table.
3. Userspace sends real messages with `nlmsg_type = <dynamic family id>`, plus a nested `nlattr` of type 1 carrying the command number (`genlmsghdr.cmd`).

The genetlink header (`struct genlmsghdr`) is 4 bytes:

```c
struct genlmsghdr {
    __u8 cmd;        /* command within the family */
    __u8 version;    /* family-specific version */
    __u16 reserved;  /* must be 0 */
};
```

Kernel registration example (from `net/wireless/nl80211.c`, simplified):

```c
static const struct genl_ops nl80211_ops[] = {
    { .cmd = NL80211_CMD_GET_WIPHY,
      .doit = nl80211_get_wiphy,
      .dumpit = nl80211_dump_wiphy,
      .policy = nl80211_policy,
      /* can be NL80211_CMD_*; or generic cmd flags */ },
    /* … */
};

static struct genl_family nl80211_family = {
    .name     = NL80211_GENL_NAME,        /* "nl80211" */
    .version  = 1,
    .maxattr  = NL80211_ATTR_MAX,
    .ops      = nl80211_ops,
    .n_ops    = ARRAY_SIZE(nl80211_ops),
    .mcgrps   = nl80211_mcgrps,
    .n_mcgrps = ARRAY_SIZE(nl80211_mcgrps),
};

genl_register_family(&nl80211_family);
```

To find the family ID without hardcoding, userspace sends a generic netlink "control" message:

```
socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC);
struct {
    struct nlmsghdr   h;
    struct genlmsghdr g;
    struct nlattr     a;
    char              name[GENL_NAMSIZ];
} msg = {};
msg.h.nlmsg_len   = sizeof(msg);
msg.h.nlmsg_type  = GENL_ID_CTRL;     /* 0x10 */
msg.h.nlmsg_flags = NLM_F_REQUEST;
msg.g.cmd         = CTRL_CMD_GETFAMILY;
msg.g.version     = 1;
msg.a.nla_len     = sizeof(msg.a) + sizeof(msg.name);
msg.a.nla_type    = CTRL_ATTR_FAMILY_NAME;
strcpy(msg.name, "nl80211");
send(fd, &msg, sizeof(msg), 0);
```

The reply carries `CTRL_ATTR_FAMILY_ID` (the dynamic 16-bit ID), `CTRL_ATTR_MCAST_GROUPS`, etc. WireGuard does exactly this dance in its userspace tooling. iproute2's `devlink`, `ss -m`, and `tmon` all use genetlink. Newer kernels (5.x) let families register small ops tables via `genl_small_ops` to save memory, and there is work-in-progress on the "global genl" family to remove the per-family `genl_family` static allocation.

## libnl

Writing netlink code by hand is painful (TLV encoding, alignment, ack parsing, dump iteration, retry on `ENOBUFS`). **libnl** (https://github.com/thom311/libnl) is the C library used by NetworkManager, iproute2's advanced paths, and many vendor daemons. It provides:

- `nl_socket_alloc()`, `nl_connect()` — socket lifecycle
- `nl_recvmsgs_default()` — driven receive loop with callbacks
- `nl_cache` — kernel state caches (e.g., link cache, route cache) that auto-refresh on notification
- Per-subsystem libraries: `libnl-route`, `libnl-genl`, `libnl-nf`, `libnl-idiag`

A typical route-add via libnl-route:

```c
struct nl_sock *sk = nl_socket_alloc();
nl_connect(sk, NETLINK_ROUTE);
struct rtnl_route *r = rtnl_route_alloc();
rtnl_route_set_dst(r, nla_build_ipv4("192.168.2.0/24"));
rtnl_route_set_gateway(r, nla_build_ipv4("10.0.0.1"));
rtnl_route_set_iif(r, 2);
int err = rtnl_route_add(sk, r, NLM_F_CREATE | NLM_F_EXCL);
if (err < 0) fprintf(stderr, "%s\n", nl_geterror(err));
rtnl_route_put(r);
nl_socket_free(sk);
```

libnl handles ACKs, sequence numbers, dump iteration, and retry on `-ENOBUFS` automatically. The Python equivalent is `pyroute2` (userspace) and `libnl-python`.

## Comparison to ioctl

| Aspect | ioctl | netlink |
|--------|-------|---------|
| Channel | fd on device/`/dev/` | socket |
| Direction | request/reply only | request/reply + unsolicited notifications |
| Payload | flat struct, one per ioctl | TLV; arbitrary nesting |
| Addressing | inode-specific | protocol family + message type |
| Concurrency | BKL for some paths; per-driver for others | rtnetlink global mutex; per-protocol otherwise |
| Userspace tooling | `ioctl(2)` syscall | libnl, libmnl, pyroute2 |
| Discovery | none | dump operations |
| Typical API | `SIOCSIFADDR` (set interface IP) | `RTM_NEWADDR` |

A subtle but important reason for netlink's ascendance: ioctl requires a `/dev/` node or socket fd to operate on. Netlink is just a socket — it works across namespaces (you can `setns` then `socket(AF_NETLINK)`) and from unprivileged users with the right `CAP_NET_ADMIN` capability.

## Observability via netlink

Because rtnetlink is **multicast-capable**, the kernel broadcasts state changes to listeners — and these notifications are what monitoring tools consume:

- `RTM_NEWLINK`/`RTM_DELLINK` (with `NLM_F_CREATE`/`NLM_F_DELETE` flags) — a NIC was added/removed (driver probe, USB device, container namespace change). Consumed by `udev` (sets the device name) and `systemd-udevd`'s `net_setup_link`.
- `RTM_NEWNEIGH`/`RTM_DELNEIGH` — ARP/ND entries come and go. Consumed by ARP-monitoring tools and host networking daemons.
- `RTM_NEWROUTE`/`RTM_NEWADDR` — config changes. Consumed by NetworkManager.
- `NLMSG_DONE` after a `RTM_GETLINK | NLM_F_DUMP` — closes the streamed dump.

The simplest listener is `ip monitor`:

```
# ip monitor link     # streams RTM_NEWLINK/RTM_DELLINK as they happen
# ip monitor route    # routes
# ip monitor neigh    # ARP/ND entries
# ip monitor all      # all of the above
```

The implementation lives in `ipmonitor.c` in `iproute2`; it just opens a `NETLINK_ROUTE` socket, joins the right multicast group (`RTMGRP_LINK`, `RTMGRP_IPV4_ROUTE`, etc.) with `setsockopt(SOL_NETLINK, NETLINK_ADD_MEMBERSHIP, &group, sizeof(group))`, and reads.

Multicast groups for rtnetlink are bitmask-encoded in `nl_groups` of `sockaddr_nl`: `RTMGRP_LINK = 1`, `RTMGRP_NOTIFY = 2`, `RTMGRP_NEIGH = 4`, `RTMGRP_IPV4_IFADDR = 0x10`, etc. Modern kernels use a 32-bit `NETLINK_ADD_MEMBERSHIP` group number rather than the legacy bitmask; both are accepted on rtnetlink for compatibility.

A more sophisticated example is `drop_monitor`: a genetlink family that lets the kernel stream dropped packet events to userspace. `ss`, `devlink`, `tcpdiag` all ride netlink.

## iproute2 internals

`iproute2` (https://github.com/shemminger/iproute2) is the canonical userspace suite built on raw rtnetlink and libmnl. The relevant entry points:

- `ip/ip.c` — `main()` dispatches to `ip link`, `ip addr`, `ip route`, etc.
- `ip/ipaddress.c` — implements `ip addr` by issuing `RTM_GETADDR` dumps
- `ip/iplink.c` — implements `ip link`, including `ip link add … type veth` via nested `IFLA_LINKINFO`
- `ip/iproute.c` — `RTM_GETROUTE` / `RTM_NEWROUTE` / `RTM_DELROUTE`
- `lib/netlink.c` — the low-level netlink helpers (`addattr_l`, `rtnl_talk`, `rtnl_dump_filter`) used throughout iproute2

Note that iproute2 deliberately avoids libnl — instead, it uses libmnl (minimal) plus its own `libnetlink.c`. This keeps the suite self-contained and is the reason `ip`'s `--json` output and `--brief` form were easy to add (just a different filter on the same dumped messages).

## References

- RFC 3549 — "Linux Netlink as an IP Services Protocol": https://www.rfc-editor.org/rfc/rfc3549
- `man 7 netlink` and `man 7 rtnetlink` and `man 3 genl`: https://man7.org/linux/man-pages/man7/netlink.7.html
- `man 7 genetlink` (Linux-specific): https://man7.org/linux/man-pages/man7/genetlink.7.html
- Kernel source `net/netlink/af_netlink.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/netlink/af_netlink.c
- Kernel source `net/netlink/genetlink.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/netlink/genetlink.c
- Kernel source `net/core/rtnetlink.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/core/rtnetlink.c
- libnl documentation: https://www.infradead.org/~tgr/libnl/
- iproute2 source: https://github.com/shemminger/iproute2
- LWN: "An updated look at netlink", J. Corbet (2007): https://lwn.net/Articles/247019/
- kernel.org documentation `Documentation/networking/netlink_spec/` (YAML-generated netlink protocol descriptions): https://www.kernel.org/doc/html/latest/networking/netlink_spec/index.html
- M. Kerrisk, "Linux Netlink", LinuxConfEU 2017 talk and slides: https://man7.org/conf/
