# TCP Fast Open

TCP Fast Open (TFO, RFC 7413) is a TCP extension that allows data to be exchanged during the initial handshake, eliminating one RTT of latency for the first request to a server. Combined with TLS 1.3's 1-RTT handshake (or 0-RTT with PSK), TFO enables sub-10 ms initial connections to previously-contacted servers. This page covers the protocol, the cookie mechanism, the privacy and security considerations, and the production deployment patterns.

## The Problem TFO Solves

A standard TCP connection to a server takes:

```text
Time:    0 ──────── 10 ms ──────── 20 ms ──────── 30 ms ──────── 40 ms
                SYN  →
                       ← SYN-ACK
                ACK   →
                              [TCP connection established]
                              HTTP GET →
                                              ← HTTP response
[~30 ms for first response byte on a 10 ms RTT link]
```

Three RTTs for the first response: TCP handshake (1 RTT) + TLS handshake (1 RTT) + HTTP request/response (1 RTT). For a 10 ms RTT link, that's 30 ms — most of it spent on handshake overhead rather than useful work.

TFO removes the first RTT by allowing the client to send data in the SYN packet itself. The server processes the request immediately and starts responding with the SYN-ACK.

## The Protocol

TFO uses a **cookie** mechanism to authenticate the client's SYN+data:

### First connection (no cookie yet)

The client sends a regular SYN with the TFO option but no data. The server responds with a SYN-ACK that includes a TFO cookie (typically 16-32 bytes derived from the server's secret + client IP). The client caches this cookie.

### Subsequent connections (with cookie)

The client sends a SYN with the TFO option, the cached cookie, and any data (e.g., an HTTP GET request). The server validates the cookie and processes the data immediately. If the cookie is valid, the server can respond with data in the SYN-ACK.

```text
Time:    0 ──── 10 ms ──── 20 ms ──── 30 ms
              SYN+cookie+GET →
                              ← SYN-ACK+response (data in response)
              ACK →
[~10 ms for first response byte — same as a single RTT]
```

## The Cookie Mechanism

The cookie is a MAC (Message Authentication Code) computed by the server:

```c
// Pseudocode for the cookie
cookie = AES_encrypt(server_secret, client_IP || timestamp);
```

The server keeps a secret (rotated periodically, e.g., every 5 minutes). The cookie includes a timestamp to allow expiry. The server can validate the cookie without storing per-client state — the cookie is self-authenticating given the server's secret.

Validation on subsequent SYNs:

```c
// Server-side validation
expected_cookie = AES_encrypt(server_secret, client_IP || extract_timestamp(received_cookie));
if (expected_cookie == received_cookie) {
    accept_data_in_syn();
} else {
    // Cookie invalid (stale, malicious, or server rotated secret)
    // Fall back to regular TCP handshake
    send_syn_ack_without_data();
    wait_for_third_handshake();
}
```

The fallback ensures TFO doesn't break compatibility — a client with a stale cookie just gets a regular handshake.

## Security and Privacy Considerations

TFO introduces two new attack surfaces:

1. **SYN flood amplification**: an attacker could spoof client IPs and send SYNs with data, causing servers to do work (e.g., HTTP parsing) without verifying the source. TFO mitigates this by requiring a valid cookie before processing data; a SYN without a cookie is treated as a regular TCP handshake.

2. **Replay attacks**: an attacker who captures a SYN+cookie+data can replay it. The cookie is bound to the client's IP, so a different-IP replay fails. Same-IP replay (e.g., behind a NAT) is a real risk; TFO mitigates by having the server-side include a per-server nonce in the cookie that changes on rotation.

3. **Privacy**: a server-side attacker can identify a client across IP changes if the client uses the same TFO cookie. To mitigate, cookies should be IP-bound (the default).

## Production Deployment

TFO is enabled by default on Linux kernel 3.13+ (2014). The sysctls:

```bash
# View current setting (1 = client TFO, 2 = server TFO, 3 = both)
cat /proc/sys/net/ipv4/tcp_fastopen

# Enable both client and server TFO
echo 3 > /proc/sys/net/ipv4/tcp_fastopen
```

Application support:

- **Linux**: `setsockopt(fd, IPPROTO_TCP, TCP_FASTOPEN_CONNECT, &on, sizeof(on))` on client; `TCP_FASTOPEN` on the listening socket.
- **FreeBSD**: similar, plus `setsockopt` with `TCP_FASTOPEN` on both ends.
- **macOS**: enabled since 10.11 (El Capitan) but opt-in per socket.

Production caveats:

1. **Middleboxes may strip TFO.** Some firewalls and load balancers (especially older Cisco/Juniper gear) strip unknown TCP options, breaking TFO silently. The fallback (regular handshake) means connectivity survives, but the latency win is lost.

2. **TFO + TLS 1.3 = 0-RTT data.** Combined with TLS 1.3's 0-RTT mode, the client can send encrypted HTTP request data in the very first packet. The trade-off is 0-RTT is replayable (an attacker who captures the packet can replay it later). For idempotent requests (GET), this is fine; for non-idempotent (POST), use TLS 1.3's regular 1-RTT mode.

3. **Cookie rotation matters.** A server that never rotates its TFO secret is vulnerable to cookie theft. A server that rotates too often forces clients to re-do the regular handshake frequently. Linux rotates every 5 minutes by default.

## When TFO Doesn't Help

- **First connection to a server**: no cached cookie, so the first SYN must be a regular handshake.
- **Mobile networks with carrier-grade NAT**: TFO cookies are IP-bound, and CGNAT rotates IPs frequently, breaking cookie caching.
- **Servers behind TCP-terminating load balancers**: the LB terminates TCP, so client cookies don't reach the backend. The LB itself must support TFO to pass it through.
- **HTTP/2 multiplexing**: HTTP/2 already amortizes the handshake cost across many requests on a single TCP connection, so TFO's first-request win is less impactful. HTTP/3 (QUIC) eliminates the TCP handshake entirely.

## Comparison to QUIC

QUIC (the transport protocol behind HTTP/3) provides similar first-packet-data semantics but eliminates the TCP handshake entirely. QUIC's advantages over TFO:

- Built-in TLS (no separate handshake).
- Connection migration across IP changes (mobile client moving from Wi-Fi to cellular).
- Per-stream flow control (no head-of-line blocking).

QUIC's disadvantages:

- Mostly user-space (kernel modules are rare).
- Higher CPU cost (no hardware offload).
- Less mature on middleboxes.

For greenfield deployments, QUIC is the better choice. For retrofitting TCP-based services, TFO is the lowest-cost optimization.

## Common Pitfalls

1. **Enabling TFO without verifying middlebox compatibility.** Some networks strip TFO options, and the server's behavior with stripped cookies can be subtle (treat as regular SYN). Test in production with a small percentage of clients first.

2. **Forgetting to make 0-RTT requests idempotent.** TLS 1.3 + TFO 0-RTT lets an attacker replay a captured request. If the request transfers $100, replay attacks cost $100 each. Only use 0-RTT for idempotent operations.

3. **Cookie expiration mismatch.** A client that connects to a server every 6 hours may have a stale cookie (servers often expire cookies after ~1 hour). The fallback is graceful (regular handshake) but defeats the TFO benefit.

4. **Trusting cookies for authentication.** TFO cookies are for SYN authenticity only — they prevent spoofed-source-IP SYN floods. They do NOT authenticate the user; HTTPS or other auth is still required.

5. **Mixing TFO and non-TFO sockets on the same port.** The server's `TCP_FASTOPEN` socket option applies to all connections. A non-TFO client connecting to a TFO-enabled server gets a regular handshake. A TFO client with a bad cookie also gets a regular handshake. There's no way to "disable TFO for this specific connection".

## References

- [RFC 7413: TCP Fast Open](https://datatracker.ietf.org/doc/html/rfc7413) (2014)
- Radhakrishnan et al., "[TCP Fast Open](https://research.google/pubs/pub36646/)" (ACM CoNEXT 2011) — the original paper
- [Linux TCP Fast Open documentation](https://www.kernel.org/doc/Documentation/networking/tcp_fastopen.txt)
- [TCP Fast Open in nginx](https://nginx.org/en/docs/http/ngx_http_v2_module.html) (since 1.11)
- [TFO deployment at Google](https://research.google/pubs/pub36640/) (Google paper)
- [LWN: TCP Fast Open overview (2014)](https://lwn.net/Articles/508818/)
- [Cloudflare: TFO at Cloudflare scale](https://blog.cloudflare.com/tcp-fast-open/)
