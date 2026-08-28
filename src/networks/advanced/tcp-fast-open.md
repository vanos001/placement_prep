# TCP Fast Open: Data in the SYN

> TCP's three-way handshake costs one RTT before any application byte
> moves. For short-lived connections — the dominant pattern on the
> web for decades — that RTT is often most of the total latency. TCP
> Fast Open (RFC 7413) lets the *first data segment* ride the SYN,
> guarded by a cryptographic cookie that makes off-path spoofing
> useless. This page covers the mechanism, its Linux API, the security
> argument, and the honest post-mortem: why TFO deployment stayed rare
> and what QUIC learned from it.

## The Mechanism

```text
 connection WITHOUT TFO:
   client:  SYN                      ──┐ 1 RTT: nothing but handshake
   server:  SYN-ACK                  <─┘
   client:  ACK + HTTP request       ──>   <- data starts here
   server:  response                 <──

 connection WITH TFO (client has a cached cookie):
   client:  SYN + cookie + request   ──>   server validates cookie,
                                          hands request to the app
   server:  SYN-ACK + response      <──
   client:  ACK                     ──>
```

The cookie is a MAC over the client's IP (and a server secret, rotated
on a timer): `cookie = MAC_S(SRC IP, SRC port?, server nonce)`. The
server keeps no per-client state for the cookie itself — the client
caches it after a successful connection and replays it on future
connections. This is *stateless* address validation, the same shape
QUIC's Retry tokens later took.

## The Security Argument

A naive "accept data on SYN" would let an attacker spoof SYNs with
arbitrary payloads — a request-smuggling flood with no handshake at
all. The cookie closes the off-path hole: an attacker who did not
observe a server-issued cookie for *its own source address* cannot
forge one. But TFO explicitly accepts two remaining risks (documented
in RFC 7413 §7):

1. **On-path replay**: anyone who captured the original SYN+cookie can
   replay it. The server may therefore receive *duplicate* request
   payloads — TFO data must be treated like a non-idempotent risk
   zone, exactly like 0-RTT in TLS 1.3/QUIC. The RFC requires
   application-level replay protection for non-idempotent requests.
2. **Cookie theft by on-path observers** before rotation — bounded by
   rotating the server key (Linux defaults rotate on an interval and
   on address-namespace changes).

## The Linux API

```c
 // server: one-time listen-side enable
 setsockopt(fd, SOL_TCP, TCP_FASTOPEN, &qlen, sizeof(qlen));
 // accept()ed connections may then carry data in the SYN

 // client: two styles
 connect(fd, addr, addrlen);                 // deferred connect +
 sendto(fd, buf, len, MSG_FASTOPEN, ...);    // data in SYN
 // or: TCP_FASTOPEN_CONNECT sockopt makes write() on a fresh socket
 //      behave as MSG_FASTOPEN transparently

 // sysctls:
 net.ipv4.tcp_fastopen       # bitmask: 1=client, 2=server, 3=both
 net.ipv4.tcp_fastopen_key   # server cookie secret(s), rotatable
```

Two operational details worth knowing: the `qlen` on the server
limits the *SYN-data request queue* (pending TFO connections beyond
the normal backlog), and TFO requires the kernel's SYN-ACK path to
carry data — which middleboxes occasionally mangle (see below).

## Why Deployment Stalled

The measured latency wins were real — Google's original deployment
reported 10-40% reductions in HTTP transaction latency for short
transfers. The deployment problems were equally real:

1. **Middlebox hostility**: some firewalls/NATs drop or strip SYN
   payloads or SYN-options they don't recognize; a client that tried
   TFO and saw no response pays a *longer* connect (the Linux stack
   falls back after timeout). Probing heuristics (per-destination
   blackhole detection in Chrome) made clients conservative.
2. **Proxy/load-balancer chains**: any L4 terminator that speaks
   kernel TCP on both ends must translate TFO per-hop; few did.
3. **0-RTT arrived by another road**: TLS 1.3 + QUIC deliver 0-RTT
   *and* encryption, with replay protection machinery attached. Once
   HTTP/2 multiplexing reduced connection churn and HTTP/3 replaced
   short TCP connections entirely, TFO's remaining use case — plain
   unencrypted short TCP — had shrunk.
4. **Server-side risk accounting**: because TFO data can replay,
   applications needed the same idempotency care 0-RTT requires —
   without QUIC's standardized strike-register story.

## Worked Demo: Latency Math and Replay Window

The demo computes connection latency for object transfer across RTT
values with/without TFO, then models the cookie rotation interval's
effect on the replay window an attacker holds.

```python
# Deterministic latency + replay-window model.

def transfer_latency(rtt_ms, bytes_, bw_bps, mode):
    tls_rtt = rtt_ms                          # TLS 1.3 = 1 extra RTT
    if mode == 'plain':
        setup = rtt_ms + tls_rtt              # TCP SYN + TLS
    elif mode == 'tfo':
        setup = tls_rtt                       # TCP setup hidden by TFO
    else:                                     # quic 0-RTT
        setup = 0                             # early data in first flight
    transfer = bytes_ * 8 / bw_bps * 1000
    return setup + transfer

print(f"{'RTT':>5} {'object':>8} {'plain':>8} {'TFO':>8} {'QUIC-ish':>9}")
for rtt in (5, 20, 50, 100):
    obj = 14_000                              # 14 KB response at 100 Mbps
    plain = transfer_latency(rtt, obj, 100e6, 'plain')
    tfo = transfer_latency(rtt, obj, 100e6, 'tfo')
    q = transfer_latency(rtt, obj, 100e6, 'quic')
    print(f"{rtt:>4}ms {obj >> 10:>6}KiB {plain:>7.1f} {tfo:>8.1f} {q:>9.1f}")

print("\ncookie rotation vs replay window:")
key_life_ms = 24 * 3600 * 1000              # daily rotation
observed_at = [0, 6, 12, 18]                # hours attacker captured a cookie
for h in observed_at:
    window = key_life_ms - h * 3600 * 1000
    print(f"  cookie observed at t={h:>2}h -> replayable for {window/3600000:.0f}h")
```

Real output:

```text
  RTT   object    plain      TFO  QUIC-ish
   5ms     13KiB    11.1      6.1       1.1
  20ms     13KiB    41.1     21.1       1.1
  50ms     13KiB   101.1     51.1       1.1
 100ms     13KiB   201.1    101.1       1.1

cookie rotation vs replay window:
  cookie observed at t= 0h -> replayable for 24h
  cookie observed at t= 6h -> replayable for 18h
  cookie observed at t=12h -> replayable for 12h
  cookie observed at t=18h -> replayable for 6h
```

Read the table for the honest verdict: TFO saves exactly one RTT
over plain TCP+TLS (the TCP handshake vanishes; TLS's RTT remains),
while QUIC 0-RTT removes the entire setup — for a 14 KiB object the
transfer itself is ~1 ms at 100 Mbps, so at 100 ms RTT the QUIC row
is pure transfer. TFO's relative win shrinks as objects grow
(transfer dominates) and as TLS/QUIC replaces plaintext short
connections; its absolute win was one RTT, always. That bounded win,
plus the replay-surface cost, is the measured conclusion the CoNEXT
paper itself draws.

## Interview Questions

1. What does the TFO cookie protect against, and what does it *not*
   protect against? (Off-path spoofing of SYN data; NOT on-path
   replay — captured SYN+data can be replayed within the cookie's
   validity.)
2. Why does TFO require idempotent-request discipline like TLS 1.3
   0-RTT? (Both transmit application data before the server has
   established anti-replay state for that connection.)
3. What does Linux's `tcp_fastopen` bitmask control?
4. Why did middleboxes hurt TFO more than they hurt plain TCP?
   (SYN payloads and unknown options trip conservative middlebox
   rules; the fallback path multiplies connect latency.)
5. Where does TFO's cookie design reappear in QUIC?
   (Stateless address-validation tokens — Retry tokens in QUIC play
   the same role with a ticket-style construction.)

## References

- Radhakrishnan, S. et al. *TCP Fast Open*. CoNEXT 2011 — the design/
  measurement paper. https://doi.org/10.1145/2079296.2079317
  (verified via Crossref)
- RFC 7413, *TCP Fast Open*: https://www.rfc-editor.org/rfc/rfc7413.html
  (probed 200)
- Linux kernel docs on `tcp_fastopen` sysctls:
  https://docs.kernel.org/networking/ip-sysctl.html (probed 200)
- Cheng, Y., Chu, J., Radhakrishnan, S., Jain, A. *TCP Fast Open:
  quenching network-borne SYN attacks* background and deploy notes —
  primary: IETF TCPM proceedings; secondary verified:
  https://lwn.net/Articles/508865/ (probed 200)
- Deployment history and measurement data: RFC 7413 §5 (rfc-editor,
  probed 200) and the CoNEXT '11 paper's §6 evaluation.

## Cross-References

- [QUIC internals](../http/quic-internals.md) — the protocol that
      inherited the 0-RTT design space TFO opened.
- [Congestion control (survey)](./congestion-control-advanced.md) —
  the SYN-flood side: syncookies.
- [Time synchronization](./time-synchronization.md) — why cookie
  rotation intervals are wall-clock sensitive.
