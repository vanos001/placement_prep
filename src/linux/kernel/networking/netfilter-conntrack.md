# Netfilter connection tracking (conntrack)

## Why conntrack exists

A *stateless* packet filter sees one packet at a time and decides accept/drop on its headers alone. Real firewalls want *stateful* decisions: "is this TCP packet a reply to a connection that I allowed?" Answering that question requires remembering prior packets, which is what Netfilter's **connection tracking** subsystem (`nf_conntrack`) does.

conntrack is implemented in `net/netfilter/nf_conntrack_core.c` and the protocol-specific helpers in `net/netfilter/nf_conntrack_proto_*.c`. It is built as the `nf_conntrack` module and enabled by `CONFIG_NF_CONNTRACK`. It exposes a single hash table — `nf_conntrack_hash` — of `struct nf_conn` entries.

When a packet traverses a Netfilter hook, `nf_conntrack_in()` (the function registered at the `NF_INET_PRE_ROUTING` and `NF_INET_LOCAL_OUT` hooks) is called. It looks up or creates the connection entry, then stores a pointer to it on the packet's `skb` via `nf_ct_set()`. Later, the `state`/`ct` match in iptables/nftables reads `skb->_nfct` to query it. Without conntrack, every rule that uses `-m conntrack` / `ct state` would have nothing to consult.

## The connection table

The table is a chained hash:

```
        nf_conntrack_hash  (nf_conntrack_hash_t, 2^bits buckets)
        +----+----+----+----+----+----+
        | h0 | h1 | h2 | h3 | h4 | h5 | ...
        +----+----+----+----+----+----+
          |              |
          v              v
       [nf_conn]      [nf_conn]
       tuplehash[0]   tuplehash[0]
       tuplehash[1]   tuplehash[1]
       timeout=432000 status=SEEN_REPLY
       ...
          |
          v
       [nf_conn] (collision chain)
```

Each `struct nf_conn` is allocated from the `nf_conntrack_cachep` slab. The key data (defined in `include/net/netfilter/nf_conntrack.h`):

```c
struct nf_conn {
    struct nf_conntrack_tuple_hash tuplehash[IP_CT_DIR_MAX]; /* ORIGINAL + REPLY */
    unsigned long status;           /* IPS_* flags */
    u32 timeout;                   /* jiffies + timeout value */
    possible_net_t ct_net;
    struct hlist_node nat_bysource; /* for NAT source grouping */
    struct nf_conn *master;        /* parent conn for RELATED */
    union nf_conntrack_proto proto;
    struct nf_conntrack_ext *ext;   /* helpers, NAT, labels, … */
    struct rcu_head rcu;
};
```

The two `tuplehash` slots are crucial: a connection is tracked in *both directions* — original (initiator → responder) and reply (responder → initiator). Hash lookups by either direction yield the same `nf_conn` because both `tuplehash` entries are linked to the same struct.

The tuple itself (`include/uapi/linux/netfilter/nf_conntrack_tuple.h`):

```c
struct nf_conntrack_tuple {
    struct nf_conntrack_man src;     /* IP + port + l3/l4 protonum */
    struct {
        union nf_inet_addr u3;
        union {
            __be16 all;
            struct { __be16 port; } tcp;
            struct { __be16 port; } udp;
            struct { __be16 port; } sctp;
            struct { __be16 port; } dccp;
            struct { __be16 key; } gre;
            struct { __be16 id;   } icmp;
            struct { __be16 port; } sctp_v6;
        } u;
        u_int8_t protonum;
        u_int8_t dir;
    } dst;
};
```

The hash is computed by `nf_conntrack_hash()` combining L3+L4 fields of the tuple, so a lookup with either direction's tuple finds the entry.

## Connection states

conntrack publishes a small enum (`enum ip_conntrack_info`, `include/uapi/linux/netfilter/nf_conntrack.h`):

| `ip_conntrack_info` | Numeric | Meaning |
|---------------------|---------|---------|
| `IP_CT_ESTABLISHED` | 0 | Reply seen, established |
| `IP_CT_RELATED`     | 1 | New connection related to an existing one (e.g., FTP data, ICMP errors) |
| `IP_CT_NEW`         | 2 | First packet of a brand-new connection |
| `IP_CT_IS_REPLY`    | 0x80 | Flag — set on the reply direction |
| `IP_CT_NUMBER`      | 3 | State count |

The *user-facing* states (visible to `iptables -m conntrack --ctstate` / `nft ct state`) are a higher-level projection:

- `NEW` — first packet, no reply yet
- `ESTABLISHED` — bidirectional traffic seen
- `RELATED` — entry whose `master` is an existing connection
- `INVALID` — packet that doesn't fit any tracked connection (bad checksums, mismatched sequence numbers, unknown protocol)
- `UNTRACKED` — packet explicitly exempted via `raw` table NOTRACK or nftables `notrack` statement
- `SNAT`/`DNAT` — pseudo-states reporting whether the connection was translated

## TCP state machine

TCP gets a per-connection state machine beyond the generic NEW/ESTABLISHED. The states are `enum tcp_conntrack` (`include/uapi/linux/netfilter/nf_conntrack_tcp.h`):

```
        SYN
  CLOSED ---> SYN_SENT
                  |  SYN+ACK
                  v
              SYN_RECV
                  |  ACK
                  v
              ESTABLISHED
                  |  FIN
                  v
              FIN_WAIT
                  |  FIN
                  v
              CLOSE_WAIT  ----> LAST_ACK  (ACK)
                                  |
                                  v
                              CLOSE
```

Each transition consumes one TCP flag combination. The actual transitions are table `tcp_conntracks[6][TCP_FLAG_MAX]` indexed by `[current_state][flags]` returning the next state and the action (e.g., `sNO`, `sIV` = invalid, `sIG` = ignore). Transitions can be tuned by module parameters `nf_conntrack_tcp_loose`, `nf_conntrack_tcp_be_liberal`, `nf_conntrack_tcp_max_retrans`, `nf_conntrack_tcp_timeout_close`, ….

## UDP, ICMP, and "generic" tracking

UDP is connectionless, so conntrack uses timeouts: an entry stays `NEW` until a reply is seen, then becomes `ESTABLISHED` with a longer timeout. Defaults (in `nf_conntrack_proto_udp.c`):

- `nf_conntrack_udp_timeout` = 30 s — for unidirectional stream
- `nf_conntrack_udp_timeout_stream` = 180 s — for bidirectional

ICMP is tracked by mapping echo request ↔ echo reply (and similar for other types), keyed by ICMP `id`. An ICMP *error* (e.g., "destination unreachable") is treated specially: it's parsed to find the inner packet that triggered it, then matched against an existing tracked connection — that's how an ICMP unreachable in reply to a TCP SYN becomes `RELATED` to the TCP connection.

For other protocols conntrack falls back to the generic tracker, which just keys on the L4 tuple and uses `nf_conntrack_generic_timeout` (default 600 s).

## NAT

Network Address Translation is layered on top of conntrack. A NAT rule manipulates a single `struct nf_nat_range2` applied to the `nf_conn`'s tuple. Because the tuple is shared between the two directions, rewriting the *original* tuple in PRE_ROUTING (DNAT) automatically rewrites what the reply must look like — conntrack will translate the reply in the reverse direction.

The three flavors:

| Target | Hook | What it does |
|--------|------|--------------|
| `DNAT` | PREROUTING, OUTPUT | Rewrite destination address/port (range, `--to-destination`) |
| `SNAT` | POSTROUTING, INPUT (since 4.18) | Rewrite source address/port (`--to-source`) |
| `MASQUERADE` | POSTROUTING | Like SNAT but picks source from the egress interface (so it survives DHCP address changes) |
| `REDIRECT` | PREROUTING, OUTPUT | DNAT to localhost (transparent proxy) |

A single `struct nf_conn` carries a `struct nf_conn_nat` extension. NAT for IPv4 lives in `net/netfilter/nf_nat_core.c`; the manipulation function is `nf_nat_packet()`:

```c
unsigned int nf_nat_packet(struct nf_conn *ct, enum ip_conntrack_info ctinfo,
                           unsigned int hooknum, struct sk_buff *skb)
{
    enum ip_conntrack_dir dir = CTINFO2DIR(ctinfo);
    unsigned int verdict = NF_ACCEPT;
    struct nf_nat_range2 range;

    if (nf_nat_initialized(ct, hooknum))   /* Only NAT once per hook */
        return NF_ACCEPT;

    range.flags       = NF_NAT_RANGE_MAP_IPS;
    range.min_addr = range.max_addr
                   = ct->tuplehash[!dir].tuple.src.u3;

    if (!nf_nat_setup_info(ct, &range, HOOK2MANIP(hooknum)))
        return NF_ACCEPT;

    /* manipulate the packet itself — IP, ports, checksums */
    if (ct->tuplehash[dir].tuple.dst.protonum == IPPROTO_TCP)
        verdict = nf_nat_manip_pkt(skb, ct, dir, &range, hooknum,
                                   nf_nat_manip_pkt_tcp);
    /* ... udp, icmp, etc. */

    return verdict;
}
```

## Helpers: application-layer gateways

Some protocols embed connection information in their payload (FTP active mode tells the server which port to connect to; SIP advertises RTP ports; H.323 carries call signaling). conntrack *helpers* inspect application-layer traffic, anticipate the secondary connection, and mark it `RELATED` to the primary so the firewall can accept it without a separate rule.

Helpers are kernel modules. They register a `struct nf_conntrack_helper` with `nf_conntrack_helper_register()`. The classic example, FTP, lives in `net/netfilter/nf_conntrack_ftp.c` and operates on the command channel parsing `PORT` and `PASV` commands. Helpers must be explicitly attached per-connection:

```
iptables -A PREROUTING -t raw -p tcp --dport 21 -j CT --helper ftp
# or nftables:
nft add rule inet filter input tcp dport 21 ct helper set "ftp"
```

The `nf_conntrack_helper` autoloading of helpers was disabled by default in kernel 3.5 (commit `4d6013172e`, "netfilter: nf_conntrack: change conntrack helper<br>disable default on"). To opt in for a connection, set the `CT` target's `--helper` option, or in nftables the `ct helper set` expression.

## The conntrack table in /proc

The system exposes conntrack state in `/proc/net/nf_conntrack` (readable, one line per connection) and `/proc/sys/net/netfilter/nf_conntrack_*`. Examples:

```
ipv4     2 tcp      6 86399 ESTABLISHED src=10.0.0.5 dst=93.184.216.34 \
  sport=43210 dport=80 src=93.184.216.34 dst=10.0.0.5 sport=80 dport=43210 \
  [ASSURED] mark=0 use=2
```

Key sysctls (see `Documentation/networking/nf_conntrack-sysctl.rst`):

| Sysctl | Default | Purpose |
|--------|---------|---------|
| `nf_conntrack_max` | 16384 (or memory-based) | Max entries in the table; bump for high traffic |
| `nf_conntrack_buckets` | same as `nf_conntrack_max/4` (rounded) | Hash bucket count; can only be set at module load |
| `nf_conntrack_checksum` | 1 | Validate packet checksums |
| `nf_conntrack_tcp_timeout_established` | 432000 s (5 days) | Time to keep an idle TCP conn |
| `nf_conntrack_tcp_timeout_time_wait` | 120 | 2MSL after close |
| `nf_conntrack_udp_timeout` | 30 | UDP stream idle |
| `nf_conntrack_udp_timeout_stream` | 180 | UDP "established" idle |
| `nf_conntrack_icmp_timeout` | 30 | ICMP echo idle |
| `nf_conntrack_generic_timeout` | 600 | Other protocols |
| `nf_conntrack_icmpv6_timeout` | 30 | |
| `nf_conntrack_log_invalid` | 0 | Log invalid packets per protocol |
| `nf_conntrack_acct` | 0 | Enable per-flow byte/packet counters (since 3.7 default off; back as `CONFIG_NF_CONNTRACK_PROC_COMPAT`) |

## Sizing and tuning

The table's hash size is set at module load time by `nf_conntrack_hash_init()`:

```c
void nf_conntrack_init_net(struct net *net)
{
    /* Hash size scales with nf_conntrack_max / 4, with 1024..2^20 bounds */
    if (!nf_conntrack_hash_sz)
        nf_conntrack_hash_sz = 1 << (ilog2(nf_conntrack_max / 4));
    nf_conntrack_hash = nf_ct_alloc_hashtable(&nf_conntrack_hash_sz, 0);
}
```

The chain length is bounded by `nf_conntrack_max / nf_conntrack_buckets`, ideally ≤ 8 entries per chain. The classic "conntrack table full, dropping packet" log fires in `__nf_conntrack_confirm()` when the count exceeds `nf_conntrack_max`; the oldest entry (lowest timeout) is evicted to make room. If you see this, bump:

```
echo 524288 > /proc/sys/net/netfilter/nf_conntrack_max
echo 131072 > /proc/sys/net/netfilter/nf_conntrack_buckets  # at module load only
```

For 1 Mpps firewalls, set `nf_conntrack_max` to ≥ concurrent connections × safety factor (typically 2×). Calculate concurrent connections from peak pps × timeout.

The `nf_conntrack` slab grows; check `cat /proc/slabinfo | head -2; grep nf_conn` (root). Each entry costs roughly 200–300 bytes plus extensions; 1 M entries ≈ 250 MB.

## conntrack and performance

conntrack is one of the most expensive steps in the receive path on a busy router. Each packet pays:

1. Hash computation on the tuple (one jhash).
2. Lockless lookup under `nf_conntrack_lock` (RCU read side).
3. For new connections: a `kmem_cache_alloc` of `struct nf_conn` and insertion under the spinlock.
4. For confirmed connections: a timeout bump (writes the `timeout` field; on overflow the entry is re-inserted into the timer wheel).
5. NAT manipulation if any rule applies.

To shave microseconds, the kernel can bypass conntrack entirely for traffic that doesn't need it:

```
iptables -t raw -A PREROUTING -p tcp --dport 80 -j NOTRACK
nft add rule inet filter prerouting tcp dport 80 notrack
```

`NOTRACK`/`notrack` sets `IPS_UNTRACKED` so `skb->_nfct` stays NULL; subsequent rules see `ct state untracked`. This is correct only for traffic that doesn't require NAT or state.

Per-CPU stats are available at `/proc/net/stat/nf_conntrack`:

```
entries  searched found new invalid ignore delete delete_list \
insert insert_failed drop early_drop error expect_new expect_create \
expect_delete search_restart
```

High `insert_failed` indicates hash collisions or duplicate connections; high `early_drop` means the table is full and entries are being evicted; high `search_restart` means the lock was contended and the lookup was restarted.

The conntrack table is also the foundation for `CTINFO` mode (DSCP marking via `dscp`), `CONNMATCH` against labels (`xt_connmark`/`ct mark set`), and `cgroup`-aware classification (`ct zone` for network namespaces isolation, see `struct nf_ct_zone`).

## conntrack and namespaces

`struct nf_conn` carries a `possible_net_t ct_net`, so each *network namespace* has its own logical table view (one per netns). The hash table itself is global, but entries are filtered by netns during lookup. This means a container's conntrack entries don't leak across netns but DO compete for the same global capacity — the host's `nf_conntrack_max` is shared. On Kubernetes nodes this has been a real production issue (one pod exhausting the host's conntrack). Workaround: tune host's `nf_conntrack_max` and apply per-pod quotas via the CNI or `connlimit` match.

## References

- Netfilter connection tracking documentation: https://www.netfilter.org/documentation/HOWTO/netfilter-extensions-HOWTO.html
- Kernel source `net/netfilter/nf_conntrack_core.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/netfilter/nf_conntrack_core.c
- Kernel source `net/netfilter/nf_nat_core.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/netfilter/nf_nat_core.c
- Kernel docs `Documentation/networking/nf_conntrack-sysctl.rst`: https://www.kernel.org/doc/html/latest/networking/nf_conntrack-sysctl.html
- LWN: "Network address translation and connection tracking", J. Corbet (2004): https://lwn.net/Articles/83110/
- LWN: "Connection tracking and NAT in the kernel" series: https://lwn.net/Articles/813793/
- Conntrack-tools user manual (`conntrack(8)`): https://man7.org/linux/man-pages/man8/conntrack.8.html
- RFC 3022 — Traditional IP Network Address Translator (Traditional NAT): https://www.rfc-editor.org/rfc/rfc3022
- Rusty Russell, "Linux 2.4 Packet Filtering HOWTO" (the original netfilter/iptables documentation): https://www.netfilter.org/documentation/HOWTO/packet-filtering-HOWTO.html
- Pablo Neira Ayuso, "Netfilter's connection tracking system", Netdev 0x1: https://netdevconf.info/0x1/
