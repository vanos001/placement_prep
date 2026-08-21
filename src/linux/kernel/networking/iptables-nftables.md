# iptables and nftables

## What these tools actually are

Linux packet filtering is implemented by the **Netfilter** framework, a set of hooks inside the kernel's network stack (`net/netfilter/`). `iptables` (legacy) and `nft` (nftables) are two different *front-ends* to that framework. They differ in how rules are represented in the kernel, not in *where* the rules run — both ultimately execute inside the five Netfilter hooks that span the receive and transmit paths.

The five hooks are registered by `nf_register_net_hook()` (or `nf_register_net_hooks()` for batches) and form the canonical packet traversal:

```
           NIC RX
             |
             v
     +---------------+
     | PREROUTING    |  nf_hook_entry, prio -200 (raw), -100 (mangle), -10 (conntrack-in)
     +---------------+
             |
   +---------+---------+
   |                   |
   v                   v
+----------+     +-----------+
| INPUT    |     | FORWARD   |
+----------+     +-----------+
   |                   |
   v                   v
   local            +-----------+
   socket           | POSTROUTING |
                    +-----------+
                        |
                        v
                     NIC TX

                       +-----------+
                       | OUTPUT    |   (locally generated packets)
                       +-----------+
                       |
                       v
                   POSTROUTING
```

The hooks are defined in `enum nf_inet_hooks` in `include/uapi/linux/netfilter.h`:

```c
enum nf_inet_hooks {
    NF_INET_PRE_ROUTING,   /* 0 — all incoming packets, before routing */
    NF_INET_LOCAL_IN,      /* 1 — packets destined for this host */
    NF_INET_FORWARD,      /* 2 — packets being routed through */
    NF_INET_LOCAL_OUT,    /* 3 — packets generated locally */
    NF_INET_POST_ROUTING, /* 4 — all outgoing packets, after routing */
    NF_INET_NUMHOOKS
};
```

Each hook is a sorted list of `struct nf_hook_ops`, ordered by priority (signed int). Lower priority runs first. `INT_MIN` is reserved.

## iptables: tables, chains, rules

iptables organizes rules into **tables** (which select a class of operations) and **chains** (which map to the hooks). The four standard tables:

| Table | Purpose | Default chains |
|-------|---------|----------------|
| `raw`  | Mark packets *before* conntrack, set NOTRACK | PREROUTING, OUTPUT |
| `mangle` | Modify packet headers (TOS, TTL, MPLS) | all five |
| `nat`  | Connection-address translation (SNAT/DNAT/MASQUERADE) | PREROUTING, OUTPUT, POSTROUTING, INPUT |
| `filter` | Accept/drop decisions | INPUT, FORWARD, OUTPUT |

The `security` table exists when SELinux is compiled in, for MAC labeling.

Each rule has the structure: **match → target**. Matches are kernel modules registered with `xt_register_match()`; targets with `xt_register_target()`. Both are looked up via `struct xt_match` / `struct xt_target` in `net/netfilter/x_tables.c`. The dispatch table `xt[t][NPROTO]` is indexed by table and protocol family.

A typical rule:

```
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -j ACCEPT
```

This appends (`-A`) to the INPUT chain a rule matching TCP destination port 22 with conntrack state NEW, target ACCEPT. Internally, `iptables-restore` translates the textual rules into `struct ipt_replace` payloads and issues `setsockopt(SO_SET_REPLACE, …)` on a raw `SOCK_RAW` socket of protocol `IPPROTO_RAW`. The kernel then walks the chains and converts every match into a sequence of `xt_match` invocations.

The x_tables evaluation loop, simplified from `ipt_do_table()` in `net/ipv4/netfilter/ip_tables.c`:

```c
unsigned int
ipt_do_table(struct sk_buff *skb, const struct nf_hook_state *state, struct xt_table *table)
{
    const struct iphdr *ip = ip_hdr(skb);
    const struct xt_table_info *private = READ_ONCE(table->private);
    const struct ipt_entry *e;
    struct xt_action_jump *jumpstack[XT_JUMP_STACK_SIZE];
    unsigned int verdict = NF_ACCEPT;
    int stackptr = 0;

    e = (const struct ipt_entry *)private->entries;
    ip_arg_iph = *ip;

    xt_info_rdlock();
    do {
        const struct xt_entry_target *t;
        const struct xt_match *m;
        struct xt_mtchk_param match_param = { .skb = skb };

        /* Iterate all matches in this rule. */
        if (!ip_packet_match(ip, &e->ip, state->in, state->out,
                             e->comefrom & (1 << NF_INET_PRE_ROUTING)) ||
            IPT_MATCH_ITERATE(e, do_match, skb, &state, &m, &match_param) != 0) {
            no_match:
            e = ipt_next_entry(e);
            continue;
        }
        t = ipt_get_target_c(e);
        verdict = t->u.kernel.target->target(skb, &state, e, t->data);
        if (verdict == XT_CONTINUE)
            e = ipt_next_entry(e);
        else if (verdict == XT_JUMP) {
            jumpstack[stackptr++] = e;
            e = (struct ipt_entry *)t->data; /* jump target */
        } else if (verdict == XT_RETURN) {
            e = jumpstack[--stackptr];
        } else {
            /* NF_ACCEPT, NF_DROP, … */
            break;
        }
    } while (!ipt_is_last_entry(e, private));
    xt_info_rdunlock();
    return verdict;
}
```

The `jumpstack` here is the per-CPU array that handles `-j` jumps to user-defined chains. The depth is capped by `XT_JUMP_STACK_SIZE` (16 on most kernels).

## Match and target semantics

Matches extend what a rule can look at. Examples shipped with the kernel:

- `tcp`/`udp` — L4 ports, flags
- `conntrack` — `--ctstate`, `--ctorigip`, `--ctreplsrc`, `--ctdir`
- `state` — legacy alias of conntrack, states NEW/ESTABLISHED/RELATED/INVALID
- `multiport`, `iprange`, `hashlimit`, `recent`, `string`, `bpf` (added in 4.18)
- `connlimit` — limit number of connections per source IP

Targets decide the fate of the packet:

- `ACCEPT`, `DROP`, `RETURN`, `QUEUE` (NFQUEUE), `LOG`, `ULOG`
- `SNAT`, `DNAT`, `MASQUERADE`, `REDIRECT` (in the `nat` table only)
- `TOS`, `DSCP`, `TTL`, `MARK`, `CONNMARK` (in `mangle` mostly)
- `TPROXY`, `TEE`, `IDLETIMER`, `NFLOG`

Targets are either **terminating** (ACCEPT/DROP) or **non-terminating** (LOG, MARK, CONNMARK save). The `XT_CONTINUE` return tells the engine to keep walking.

## nftables: the redesign

nftables (merged in 3.13, 2014) replaces the four protocol-specific engines (iptables/ip6tables/ebtables/arptables) with a single bytecode VM. The kernel now exposes a generic Netlink protocol family `NFNL_SUBSYS_NFTABLES`, and the userspace `nft` tool compiles rules into `nft_expr` byte sequences.

A rule in nftables looks like:

```
nft add rule ip filter input tcp dport 22 ct state new accept
```

The rule itself is a chain of *expressions* (`struct nft_expr`), each consuming a few bytes of bytecode. The evaluation engine `nft_do_chain()` in `net/netfilter/nf_tables_core.c` walks the blob:

```c
unsigned int nft_do_chain(struct nft_pktinfo *pkt, void *priv)
{
    const struct nft_chain *chain = priv, *inner_chain;
    const struct nft_rule_dp *rule, *last_rule;
    const struct nft_expr *expr, *last;
    const struct nft_rule_blob *blob;
    struct nft_regs regs;
    unsigned int verdict;

do_chain:
    blob = READ_ONCE(chain->blob_gen_0);
    rule = (struct nft_rule_dp *)blob->data;
    last_rule = (const struct nft_rule_dp *)blob->data + blob->size;

next_rule:
    if (rule == last_rule)
        return regs.verdict.code;

    nft_rule_for_each_expr(expr, last, rule) {
        if (expr->ops == &nft_cmp_fast_ops)
            nft_cmp_fast_eval(expr, &regs);
        else if (expr->ops == &nft_bitwise_fast_ops)
            nft_bitwise_fast_eval(expr, &regs);
        else if (expr->ops != &nft_payload_fast_ops ||
                 !nft_payload_fast_eval(expr, &regs, pkt))
            expr_call_ops_eval(expr, &regs, pkt);

        if (regs.verdict.code != NFT_CONTINUE)
            break;
    }

    switch (regs.verdict.code) {
    case NFT_BREAK:
        regs.verdict.code = NFT_CONTINUE;
        rule = nft_rule_next(rule);
        goto next_rule;
    case NFT_JUMP:
        inner_chain = regs.verdict.chain;
        if (WARN_ON_ONCE(inner_chain == chain))
            return NFT_BREAK;
        chain = inner_chain;
        goto do_chain;
    case NFT_GOTO:
        /* similar, but RETURN unwinds to caller */
    case NFT_RETURN:
        return regs.verdict.code;
    default: /* ACCEPT, DROP, … */
        return regs.verdict.code;
    }
}
```

The "blob_gen_0 / blob_gen_1" trick is nftables' **generation** mechanism: rule updates are committed atomically by swapping two generation blobs. This lets a million-rule ruleset be replaced without locking the data path — readers use `READ_ONCE(blob_gen_N)`, writers build the new blob off-path, then publish it by bumping the generation counter (`nft_net->generation`).

## Table / chain / rule / set in nftables

A nftables configuration is hierarchical:

```
table ip filter {
    set blackhole { type ipv4_addr; flags interval; }
    chain input {
        type filter hook input priority 0; policy drop;
        ip saddr @blackhole drop
        ct state established,related accept
        tcp dport { 22, 80, 443 } accept
    }
}
```

- **Table**: namespace container; carries a `family` (ip, ip6, inet, arp, bridge, netdev).
- **Chain**: a `base` chain carries `type` + `hook` + `priority` + `policy`; a regular chain is just a jump target.
- **Rule**: ordered list of expressions ending in a verdict (`accept`, `drop`, `jump`, `goto`, `return`, `queue`).
- **Set/Map**: first-class objects. `set` holds scalars; `map` keys → values. Both support `interval`, `timeout`, `counter`, `comment`, `mark`. Internally stored in pipapo, rbtrees, or hashes (`net/netfilter/nft_set_pipapo.c`, `nft_set_rbtree.c`, `nft_set_hash.c`).

The `inet` family is notable: a single chain evaluates both IPv4 and IPv6 packets, removing the iptables tradition of writing parallel ip/ip6 rulesets.

## Verdicts and priorities

Verdicts in nftables are encoded in `enum nft_verdicts` (`include/uapi/linux/netfilter/nf_tables.h`):

```c
enum nft_verdicts {
    NFT_CONTINUE = -1,
    NFT_BREAK    = -2,
    NFT_JUMP     = -3,
    NFT_GOTO     = -4,
    NFT_RETURN   = -5,
};
/* NF_ACCEPT = 1, NF_DROP = 0 from netfilter.h */
```

Chain priorities are signed 32-bit integers. The convention, set by `NF_IP_PRI_*` in `include/uapi/linux/netfilter_ipv4.h`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `NF_IP_PRI_RAW`       | -300  | raw table, before conntrack |
| `NF_IP_PRI_SELINUX_FIRST` | -225 | |
| `NF_IP_PRI_CONNTRACK` | -200  | conntrack (defragmentation + tracking) |
| `NF_IP_PRI_MANGLE`    | -150  | mangle before NAT |
| `NF_IP_PRI_NAT_DST`   | -100  | DNAT |
| `NF_IP_PRI_FILTER`    | 0     | filter table |
| `NF_IP_PRI_SECURITY`  | 50    | |
| `NF_IP_PRI_NAT_SRC`   | 100   | SNAT |
| `NF_IP_PRI_SELINUX_LAST` | 225 | |
| `NF_IP_PRI_CONNTRACK_CONFIRM` | INT_MAX | commit conntrack entry |

So a base chain `priority -300` runs before conntrack even sees the packet — useful for `notrack` / `ct state untracked`.

## iptables vs nftables, concretely

The same firewall as iptables and nftables:

iptables:
```
iptables -P INPUT DROP
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp -m multiport --dports 22,80,443 -j ACCEPT
iptables -A INPUT -s 10.0.0.0/8 -j LOG --log-prefix "BAD "
iptables -A INPUT -j DROP
```

nftables:
```
nft add rule inet filter input \
  ct state established,related accept
nft add rule inet filter input \
  tcp dport { 22, 80, 443 } accept
nft add rule inet filter input \
  ip saddr 10.0.0.0/8 log prefix '"BAD "' drop
```

Differences:

| Aspect | iptables | nftables |
|--------|----------|----------|
| Engine | Per-family x_tables | Single bytecode VM |
| Rule format | C structs in `ipt_replace` | nft_expr blob in `nft_rule_blob` |
| Atomic update | `iptables-restore` flush+replace | Generation swap (no flush) |
| Sets | No first-class sets (ipset is separate) | First-class sets & maps |
| IPv4+IPv6 | Two rulesets | `inet` family |
| Counters | Always on (per-rule `xt_counter`) | Opt-in (nft `counter` expr) |
| Maps / lookups | Not supported | Native |
| Performance (rule walk) | O(n) per chain, per-CPU seqlock | O(n) per chain; set lookups O(1)/O(log n) |
| Userspace | `iptables(8)` + per-family binaries | Single `nft(8)` |

For new deployments use nftables. The `iptables` binary on modern distros is the **iptables-nft** variant — a translation layer that compiles iptables syntax to nftables bytecode. So `iptables -A INPUT ...` on Fedora/Debian actually loads an nft rule. Check with `update-alternatives --display iptables` or `iptables --version` (`nf_tables` in the output means iptables-nft).

## A worked example: stateful home router with NAT

Goal: eth0 (WAN, DHCP), eth1 (LAN 192.168.1.0/24). Forward LAN traffic, NAT it, drop unsolicited inbound.

```
# nftables.conf
flush ruleset

table ip nat {
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        oifname "eth0" masquerade
    }
}

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif "lo" accept
        ct state established,related accept
        iifname "eth1" ip saddr 192.168.1.0/24 tcp dport 22 accept
        icmpv6 type { nd-neighbor-solicit, nd-router-advert, nd-neighbor-advert } accept
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
        iifname "eth1" oifname "eth0" ip saddr 192.168.1.0/24 accept
        iifname "eth0" oifname "eth1" ct state new drop
    }
}
```

Apply with `nft -f nftables.conf`. Inspect: `nft list ruleset` and `conntrack -L` (from conntrack-tools) to see the live entries NAT created.

## Operational details worth knowing

- **Rule counters**: iptables maintains counters per rule (`xt_matchinfo.counters`, padded to 64 bytes for cache lines). nftables stores them in `NFT_MSG_NEWOBJ` counters that the user attaches as `counter` expressions; they live in a side-table keyed by rule pointer.
- **Replace without dropping packets**: `iptables-restore` uses `SO_SET_REPLACE` with `IPT_REPLACE` carrying the full table snapshot. For long rulesets this briefly stops forwarding because the swap is not generation-based. nftables' `nft -f` issues a sequence of NEW/DEL messages bounded by `NFT_MSG_NEWGEN` and is non-disruptive.
- **Logs**: `LOG` target in iptables writes to `/var/log/kern.log` via `printk`. `NFLOG` uses `nfnetlink_log` (the `ulogd` daemon). nftables has `log` and `log group N queue-num M` that go through `nfnetlink_log` too.
- **Audit**: Netfilter audit events appear as `type=AUDIT_NETFILTER_*` from `audit_log_nf_info()`.

## References

- Netfilter project documentation, *iptables* and *nftables* wikis: https://wiki.nftables.org/ and https://ipset.netfilter.org/
- `man 8 iptables` and `man 8 iptables-extensions`: https://man7.org/linux/man-pages/man8/iptables.8.html
- `man 8 nft`: https://man7.org/linux/man-pages/man8/nft.8.html
- Kernel source `net/netfilter/nf_tables_api.c` and `net/netfilter/nf_tables_core.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/netfilter/nf_tables_api.c
- Kernel source `net/ipv4/netfilter/ip_tables.c`: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/ipv4/netfilter/ip_tables.c
- Netfilter hooks API documentation: https://www.netfilter.org/documentation/HOWTO/netfilter-hOWTO-3.html
- LWN: "nftables: a new firewall and packet filtering subsystem", J. Corbet (2014): https://lwn.net/Articles/564151/
- LWN: "nftables: a packet filter for the future" (2013): https://lwn.net/Articles/348245/
- Linux kernel nftables docs (`Documentation/networking/nf_conntrack.rst`): https://www.kernel.org/doc/html/latest/networking/nf_conntrack.html
- Florian Westphal, "nftables: An overview", netfilter workshop: https://netfilter.org/projects/nftables/
- Eric Leblond & Pierre Chifflier, "nftables: the Linux firewall subsystem", Netdev 0x14 (2020): https://netdevconf.info/
