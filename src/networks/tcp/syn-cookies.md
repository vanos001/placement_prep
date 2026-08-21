# SYN Cookies

SYN cookies are a TCP server-side defense against SYN flood attacks. When a server's SYN backlog is full (a sign of a SYN flood), it stops tracking half-open connections and instead encodes the connection's state in the SYN-ACK's initial sequence number (ISN). The client's ACK then validates the cookie and reconstructs the connection state. This page covers the SYN flood attack, the cookie encoding, the limitations of cookies, and the production tuning of `tcp_syncookies`.

## The SYN Flood Attack

A SYN flood is a denial-of-service attack where the attacker sends many SYN packets with spoofed source IPs:

```text
Attacker ── SYN (spoofed IP 10.0.0.5) ──→ Server
Attacker ── SYN (spoofed IP 10.0.0.6) ──→ Server
Attacker ── SYN (spoofed IP 10.0.0.7) ──→ Server
...
Server: SYN backlog fills with half-open connections.
       Each waiting for an ACK that never comes (spoofed IPs don't reply).
       No more SYNs can be accepted — server is unreachable.
```

The server allocates ~300 bytes per half-open connection (PCB + sk_buff). With a 1 Mpps SYN flood and a 60-second timeout, the server accumulates 60 million half-opens × 300 bytes = 18 GB of memory — saturating RAM.

Without SYN cookies, the only defense is to expand the SYN backlog (`net.ipv4.tcp_max_syn_backlog`) and shorten the SYN-ACK retry interval. These buy time but don't solve the fundamental problem of state-per-SYN.

## The SYN Cookie Mechanism

With SYN cookies enabled, the server doesn't allocate per-connection state on receiving a SYN. Instead, it computes a cookie that encodes the connection's state and embeds it in the SYN-ACK's ISN:

```c
// Simplified cookie computation
cookie = (t mod 32) << 24       // 5 bits: time (wraps every 64 sec)
       | (mss_index) << 16       // 3 bits: MSS encoded as index
       | (hash(client_ip, server_ip, ports, t) & 0xFFFF);  // 16 bits: MAC
```

The client sends its ACK with `ack_seq = server_isn + 1`. The server extracts the cookie from the ACK's `ack_seq - 1`, recomputes the hash, and verifies it matches. If it does, the server reconstructs the connection state (MSS from the index, etc.) and the connection is established — without ever having allocated a half-open entry.

```text
Client → SYN            → Server (cookie enabled)
Client ← SYN-ACK(ISN=C) ← Server (computed cookie C, no per-conn state allocated)
Client → ACK(ISN=C+1)   → Server

Server receives ACK, extracts cookie C from C+1-1, recomputes hash,
if match: connection established (allocate state now, when we know it's real).
if no match: drop the packet (cookie was invalid or spoofed).
```

The cookie's MAC prevents an attacker from forging valid cookies — they'd need the server's secret. The time field allows cookies to expire (default 64 seconds) so a captured cookie can't be replayed indefinitely.

## Cookie Encoding Details

The cookie is packed into 32 bits of the ISN:

| Bits | Field | Notes |
|------|-------|-------|
| 0-4 (5 bits) | Time counter (t mod 32) | Wraps every ~64 seconds |
| 5-7 (3 bits) | MSS index | Encodes one of 8 common MSS values (e.g., 1460, 1300, 1440) |
| 8-23 (16 bits) | MAC of (client IP, server IP, ports, t) | Computed via SHA-1 truncated to 16 bits |

The hash uses a server-side secret that is randomly initialized at boot. The 16-bit MAC means an attacker forging a cookie has a 1 in 65536 chance of success per attempt — a 1000-attempt flood succeeds 1.5% of the time.

## Linux Implementation

Linux's SYN cookie code (`net/ipv4/syncookies.c`) is ~600 lines. Key functions:

- `cookie_v4_init_sequence()` — computes the cookie for an incoming SYN.
- `cookie_v4_check()` — validates the cookie on the ACK.
- `cookie_tcp_reqsk_alloc()` — allocates the connection state if the cookie is valid.

Sysctls:

```bash
# 0: never use cookies (always track in backlog)
# 1: use cookies when the SYN backlog is full (default on most distros)
# 2: always use cookies (no SYN backlog at all)
sysctl net.ipv4.tcp_syncookies
# default: 1

# SYN backlog size (half-open connections tracked)
sysctl net.ipv4.tcp_max_syn_backlog
# default: 2048 (varies by distro)

# SYN-ACK retries before giving up
sysctl net.ipv4.tcp_synack_retries
# default: 5 (6 retries total = ~63 sec)
```

The "always use cookies" mode (value 2) is sometimes recommended for high-load servers, but it disables the SYN backlog, which means the server cannot detect SYNs that arrive between the SYN-ACK and the client's ACK (because there's no per-conn state to wait). Production deployments typically keep the default `1`.

## Limitations of SYN Cookies

1. **Loss of TCP options.** The cookie encodes only MSS, so any TCP options the client sent in the SYN (Window Scale, Timestamps, SACK, TCP-AO) are lost. The connection operates in the most basic TCP mode.

2. **Lower throughput for legitimate clients under attack.** Without SACK, fast-recovery from packet loss is impossible. Without Window Scale, the receive window is limited to 64 KB. A 1 Gbps connection with 100 ms RTT needs an 8 MB window; without Window Scale, throughput is capped at 5 Mbps.

3. **Cookie validation CPU cost.** Each ACK requires a SHA-1 hash. At 1 Mpps SYN flood, the server does 1M SHA-1 ops/sec — ~5% of one CPU core.

4. **Cookies don't protect against direct attacks on the bandwidth.** A 10 Gbps SYN flood saturates the inbound link regardless of cookie state.

5. **Cookies don't help if the attacker can complete the handshake.** If the attacker uses real source IPs and completes the ACK, the server allocates the connection. SYN cookies only help against spoofed-source SYN floods.

## SYN Cookies vs SYN Proxy vs TCP Reset

SYN flood mitigation has multiple layers:

- **SYN cookies** (server-side): protects the server's memory; lost TCP options.
- **SYN proxy** (intermediate device): the firewall/LB completes the TCP handshake with the SYN-flooder and only forwards established connections to the backend. Used by Cloudflare, AWS Shield, and other DDoS services.
- **TCP Reset attack** (intermediate device): the firewall sends RSTs for SYNs that look like floods, forcing attackers to use real IPs (which can then be blocklisted).

A multi-layer defense combines SYN cookies (for the server) with SYN proxy (at the edge) and traffic scrubbing (upstream).

## Modern Alternatives

1. **XDP-based SYN filtering**: an XDP BPF program at the NIC can drop SYN floods before they reach the kernel, at 100+ Mpps rates. This is how modern DDoS services (Cloudflare, AWS Shield Advanced) handle terabit-scale SYN floods.

2. **TCP-AO (RFC 5925)**: replaces the older TCP MD5 signature. Authenticates every TCP segment, eliminating spoofed-source attacks entirely. Requires pre-shared keys; not commonly deployed outside of BGP sessions.

3. **DPDK-based SYN flood handling**: similar to XDP but in user space, used by custom DDoS appliances.

These are not replacements for SYN cookies but additions — the kernel's SYN cookie mechanism remains the last line of defense if the upstream filtering is insufficient.

## Common Pitfalls

1. **Disabling SYN cookies "for performance".** A common misconfiguration is `sysctl -w net.ipv4.tcp_syncookies=0` on the theory that cookies slow down the kernel. The reality is that cookies are only used when the SYN backlog is full — they don't affect normal-traffic performance.

2. **Setting `tcp_max_syn_backlog` too low.** The default 2048 is too low for a server receiving more than 1000 new connections/sec. For a busy web server, 8192-32768 is more appropriate.

3. **Forgetting the SYN-ACK retry interval.** With `tcp_synack_retries=5`, a spoofed SYN's half-open entry stays for ~63 seconds. Reducing to 2 retries gives ~7 seconds, freeing the backlog faster.

4. **Relying on cookies alone.** Cookies protect the kernel's memory, not the inbound link. A 100 Gbps SYN flood saturates the link before cookies help. Combine with upstream DDoS scrubbing.

5. **Testing cookies by simulating floods.** Real floods have very different characteristics than simulated ones (variable source IPs, varied MSS, varying SYN options). Test in a controlled production environment.

## References

- [TCP SYN Cookies (D. Bernstein's original description)](https://cr.yp.to/syncookies.html) (1996)
- [RFC 4987: TCP SYN Flooding Attacks and Common Mitigations](https://datatracker.ietf.org/doc/html/rfc4987)
- [Linux SYN cookies source code](https://github.com/torvalds/linux/blob/master/net/ipv4/syncookies.c)
- [LWN: SYN cookies and TCP performance (2001)](https://lwn.net/2001/0607-a.html)
- [Cloudflare: How we use SYN cookies](https://blog.cloudflare.com/syn-cookie/)
- [AWS Shield: SYN flood mitigation](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/operational-adaptations-tcp-syn-flood.html)
