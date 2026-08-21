# DNS over HTTPS (DoH)

DNS over HTTPS (DoH, RFC 8484, 2018) is a protocol for performing DNS resolution via the HTTPS protocol, providing confidentiality (encryption) and integrity for DNS queries. Unlike traditional DNS (port 53, plaintext), DoH encrypts the queries, preventing eavesdropping and tampering by intermediaries. This page covers the protocol, the wire format, the deployment state, and the comparison to DoT (DNS over TLS).

## The Problem

Traditional DNS queries are plaintext on port 53:

```text
User's machine → DNS resolver (e.g., 8.8.8.8) over UDP/53
  Query: example.com A
  Response: 1.2.3.4
```

Anyone on the network path (ISP, hotel Wi-Fi, employer) can:
- See what websites the user is querying (privacy issue).
- Inject forged responses (security issue, even with DNSSEC if DNSSEC isn't deployed).
- Block queries (censorship).

DoH encrypts the DNS query in HTTPS, preventing these attacks.

## The Protocol

DoH wraps DNS messages in HTTP/2 (or HTTP/3) requests:

```http
POST /dns-query HTTP/2
Host: dns.google
Content-Type: application/dns-message
Content-Length: 33

<binary DNS query message>
```

Response:

```http
HTTP/2 200 OK
Content-Type: application/dns-message
Cache-Control: max-age=128
Content-Length: 64

<binary DNS response message>
```

The DNS message is the standard wire format (RFC 1035); DoH just wraps it in HTTP.

GET is also supported:

```http
GET /dns-query?dns=AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB HTTP/2
Accept: application/dns-message
```

The `dns` parameter is the base64url-encoded DNS query.

## The Wire Format

The DNS message format is unchanged from RFC 1035:

```text
DNS Message (33 bytes for example.com A query):
  Header (12 bytes): ID, flags, QDCOUNT=1, ANCOUNT=0, NSCOUNT=0, ARCOUNT=0
  Question: QNAME="example.com", QTYPE=A (1), QCLASS=IN (1)
```

DoH doesn't change the wire format; it just adds the HTTP/2 framing and TLS encryption.

## HTTP Caching

DoH responses can be cached by HTTP intermediaries (proxies, CDNs) using standard HTTP caching:

```http
HTTP/2 200 OK
Content-Type: application/dns-message
Cache-Control: max-age=128, public
Age: 30
```

The `max-age` is derived from the DNS response's TTL. A CDN like Cloudflare can cache DoH responses at edge locations, reducing load on the DoH server.

## Production Deployment

### Browser Configuration

Most modern browsers support DoH:
- **Firefox**: enabled by default for some regions; configurable in `about:preferences`.
- **Chrome**: enabled by default in some regions; configurable in Settings.
- **Edge, Safari, Brave**: supported.

Browsers typically use a "Trusted Recursive Resolver" (TRR) list — DoH servers that meet certain privacy and security standards.

### DoH Servers

Public DoH servers:
- Google: `https://dns.google/dns-query`
- Cloudflare: `https://cloudflare-dns.com/dns-query` (1.1.1.1)
- Quad9: `https://dns.quad9.net/dns-query`
- AdGuard: `https://dns.adguard-dns.com/dns-query`

These are free; most have privacy policies that limit logging.

### Self-Hosting DoH

For enterprises that want to control DNS resolution:

```bash
# Using dnscrypt-proxy
dnscrypt-proxy --resolver-name my-doh-server --listen 127.0.0.1:53

# Or using a custom DoH server (e.g., dnsdist, CoreDNS with DoH plugin)
```

Self-hosted DoH lets you:
- Apply internal filtering (block malware, etc.).
- Log queries (with privacy controls).
- Avoid trusting public DoH providers.

## Comparison to DoT (DNS over TLS)

| Aspect | DoH (HTTPS) | DoT (TLS) |
|--------|-------------|------------|
| Port | 443 (HTTPS) | 853 (dedicated) |
| Transport | HTTP/2 or HTTP/3 | TLS |
| Caching | HTTP cache possible | No caching |
| Browser support | First-class | Limited (Firefox, some Android) |
| Firewall traversal | Works (port 443 looks like normal HTTPS) | Often blocked (port 853) |
| Standard | RFC 8484 | RFC 7858 |

DoH and DoT provide the same security (encryption + integrity); the difference is the transport. DoH's advantage is that it uses port 443 (indistinguishable from normal HTTPS, harder to block); DoT's advantage is dedicated infrastructure (port 853, easier to filter for enterprises).

## Production Use Cases

### Privacy from ISP

For users whose ISPs track DNS queries for advertising or other purposes, DoH encrypts the queries — the ISP can't see what sites the user is visiting (unless they connect to the site directly).

### Bypassing DNS-Level Censorship

Some countries block websites at the DNS level (the resolver returns NXDOMAIN for censored domains). DoH with an offshore resolver bypasses this.

### Enterprise DNS Security

For enterprises that want encrypted DNS without losing visibility:
- Self-host a DoH server.
- Configure browsers to use it via Group Policy or MDM.
- Log queries (for security audits).

## Common Pitfalls

1. **Forgetting that DoH only encrypts DNS, not the actual HTTPS traffic.** The user's HTTPS traffic to websites is separately encrypted (TLS); DoH protects the DNS layer.

2. **Forgetting that the DoH server still sees queries.** A public DoH server (Google, Cloudflare) sees your queries. Their privacy policies promise not to log, but you're trusting them.

3. **Forgetting that DoH can bypass enterprise DNS filtering.** If an enterprise uses DNS-level filtering (e.g., blocking malware sites), DoH to an external server bypasses the filter. Use enterprise DoH or block DoH at the firewall.

4. **Forgetting that DoH can be slow.** Each DoH query is an HTTPS round-trip; for many queries (a typical page load has 50+ DNS queries), this can add latency. Use a DoH client with caching.

5. **Forgetting that some DoH clients bypass system DNS settings.** Firefox and Chrome may use their own DoH server, ignoring the system's configured resolver. This can cause split-brain DNS issues in enterprises.

6. **Forgetting that DoH doesn't protect against on-path attackers with TLS interception.** An enterprise with TLS interception (SSL bridging) can see DoH queries in plaintext. For full privacy, the DoH server's TLS cert must be trusted by the interception box.

## Comparison to Other DNS Privacy Solutions

| Solution | Encryption | Authentication | Caching |
|----------|-----------|-----------------|---------|
| DNSSEC | No (plaintext) | Yes (signatures) | Yes |
| DoH | Yes (HTTPS) | Yes (TLS) | Yes (HTTP cache) |
| DoT | Yes (TLS) | Yes (TLS) | No (per-query) |
| DoQ (DNS over QUIC) | Yes (QUIC) | Yes (QUIC) | No |

DoH and DoT are the dominant solutions; DoQ is newer (RFC 9250, 2022) and gaining adoption. All three provide encryption; DoH adds HTTP caching.

## References

- [RFC 8484: DNS over HTTPS](https://datatracker.ietf.org/doc/html/rfc8484)
- [RFC 7858: DNS over TLS](https://datatracker.ietf.org/doc/html/rfc7858)
- [RFC 9250: DNS over QUIC](https://datatracker.ietf.org/doc/html/rfc9250)
- [Mozilla: Trusted Recursive Resolver policy](https://wiki.mozilla.org/Security/DNS-over-HTTPS)
- [Cloudflare DNS over HTTPS](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/)
- [Google Public DNS over HTTPS](https://developers.google.com/speed/public-dns/docs/doh)
- [dnscrypt-proxy: DoH client](https://github.com/DNSCrypt/dnscrypt-proxy)
- [LWN: DNS over HTTPS (2021)](https://lwn.net/Articles/820133/)
