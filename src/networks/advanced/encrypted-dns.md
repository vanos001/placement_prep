# Encrypted DNS: Do53, DoT, DoH, DoQ, and ODoH

Port 53 was designed for a 1983 internet where nobody imagined an on-path observer. Every stub resolver query your laptop sends still crosses the access network as cleartext UDP, which means every domain you are about to visit is legible to the ISP, the coffee-shop access point, and any middlebox in between - before a single TLS byte of the actual connection flows. Encrypted DNS closes that gap, but it does so with four competing protocols (DoT, DoH, DoQ, ODoH) that differ in transport, cacheability, deployment locus, and - the interesting part - in who gets to see your queries. This page treats encrypted DNS as a systems-deployment problem, not just a wire format. For the DoH wire format and self-hosting walk-through, see [DNS over HTTPS](../dns/doh.md); for DNSSEC (authentication, not encryption), see [DNSSEC](../dns/dnssec.md).

## What plaintext DNS actually costs you

Three distinct failure classes motivate every protocol below:

| Problem | Who can do it | Concrete harm |
|---------|---------------|---------------|
| Passive observation | Anyone on path (ISP, Wi-Fi AP, backbone tap) | Browsing history from the query stream alone; no TLS needed |
| Spoofed answers | On-path attacker or hijacked router | NXDOMAIN injection, ad-injection rewrites, phishing redirects |
| Middleware rewriting | "Helpful" middleboxes, captive portals, parental filters | ISP NXDOMAIN-to-ads pages; spurious DNSSEC validation failures |

The third row is underappreciated: long-running measurements (dating back to at least 2008) have found a consistent fraction of lookups tampered with by intermediaries that rewrite or redirect answers, and DNSSEC-validating clients fail loudly on those rewrites. Encryption removes all three classes in one move - but moves trust to the encrypted resolver you pick, which is where the deployment politics begin.

## Where the encryption sits: a worked resolution path

Encrypted DNS only changes the first hop - stub to recursive. Everything downstream (resolver to root/TLD/authoritative) is out of scope for DoT/DoH/DoQ:

```text
  browser/app        OS stub         recursive resolver          authoritative
     |                  |            (1.1.1.1, 8.8.8.8, ...)         dns
     |  1. app asks     |                  |                           |
     |----------------->|                  |                           |
     |                  | 2. THE HOP THAT ENCRYPTED DNS CHANGES        |
     |                  |    Do53: UDP/53 cleartext                    |
     |                  |    DoT : TLS on TCP/853  (RFC 7858)          |
     |                  |    DoH : HTTP/2 on TCP/443 (RFC 8484)        |
     |                  |    DoQ : QUIC on UDP/853 (RFC 9250)          |
     |                  |----------------->|  3. recursion unchanged,  |
     |                  |                  |      still cleartext UDP  |
     |                  |                  |-------------------------->|
     |                  |                  |<--------------------------|
     |                  |<-----------------|                           |
     |<-----------------|                  |                           |
```

Two consequences follow. First, an ISP that loses visibility of hop 2 still sees hop 3 leaving its recursive resolver - though with most queries answered from cache, the observable residue shrinks a lot. Second, the recursive resolver becomes a juicier trust anchor than ever: whoever runs it sees everything the on-path observer used to see. ODoH, below, is the protocol answer to that.

## The protocol ladder: DoT, then DoH, then DoQ

### DoT - DNS over TLS (RFC 7858, 2018)

DoT is the minimal-intervention design: the standard DNS wire message over a TLS session on dedicated TCP port 853. No HTTP anywhere; scope is stub-to-recursive. One TLS connection carries many pipelined queries, and nothing about DNS semantics changes on the wire. Because it owns port 853, DoT is trivially identifiable - a property enterprises like (they can firewall it) and censors like (they can block it). RFC 8310 later defined strict usage profiles: the client supplies an authentication domain name for the resolver and enforces certificate validation against it, which is exactly what Android's "strict" Private DNS mode implements. DoT remains the natural choice for OS-level and enterprise resolver transport precisely because it is visible, dedicated, and blockable by policy.

### DoH - DNS over HTTPS (RFC 8484, 2018)

DoH puts the same wire-format message in an HTTP request: `GET /dns-query?dns=<base64url>` or `POST` with `content-type: application/dns-message`. Implementations must support HTTP/2; HTTP/3 works too. Two consequences matter more than the encoding:

1. **Indistinguishability.** DoH rides port 443 and looks like ordinary HTTPS. Blocking it means blocking web traffic, which is why browsers chose it and why some networks resent it.
2. **It inherits HTTP caching semantics.** A DoH response carries `Cache-Control: max-age=N` derived from the minimum DNS TTL in the answer; RFC 8484 forbids a cache serving a freshness lifetime longer than the TTL, caps negative responses by the SOA MINIMUM field, and requires clients to subtract the HTTP `Age` header from the DNS TTL they honor.

The caching rule creates a subtle interplay with browser connection management. Browsers keep long-lived HTTP/2 connections to the DoH resolver with many streams multiplexed, so queries pipeline without a per-query TCP/TLS handshake - once the connection is warm, DoH latency is dominated by resolver think time, not handshakes. But if an intermediary HTTP cache sits between browser and resolver, two users sharing that cache can hit each other's entries: a performance win and a privacy correlation vector at the same time. RFC 8484 lets servers defeat sharing with `max-age=0` or `Vary`-based secondary cache keys, and permits `stale-while-revalidate` for serving slightly stale answers under load. Firefox keeps its DoH connection to the trusted resolver separate from site connections, so page-load connection pools never stall waiting behind a DNS answer stream.

### DoQ - DNS over QUIC (RFC 9250, 2022)

DoQ maps each query/response pair onto its own client-initiated bidirectional QUIC stream over one long-lived connection to the resolver; server-initiated bidirectional streams are reserved for server push. The payoff versus DoT is QUIC's transport behavior: no TCP head-of-line blocking across concurrent queries, better loss recovery, and connection migration - a phone moving from Wi-Fi to cellular can keep its resolution session alive.

The caveat is early data. RFC 9250 section 4.5 is explicit:

> The 0-RTT mechanism MUST NOT be used to send DNS requests that are not "replayable" transactions. In this specification, only transactions that have an OPCODE of QUERY or NOTIFY are considered replayable.

Anything else (UPDATE, zone transfer opcodes) must wait for the handshake. Because 0-RTT data is replayable by a network observer, the RFC gives servers three lawful reactions to non-replayable opcodes arriving in 0-RTT: queue them until the handshake completes, answer REFUSED with Extended DNS Error "Too Early", or close the connection with `DOQ_PROTOCOL_ERROR`. Sections 7.1-7.4 add the privacy ledger: resumption tokens and address-validation tokens can link a roaming client across addresses, and very long-lived sessions concentrate linkability - so privacy-focused clients deliberately skip 0-RTT and sometimes pin shorter sessions even where the server offers more.

## ODoH - splitting "who is asking" from "what is asked"

DoT/DoH/DoQ all share one gap: your encrypted resolver still sees your source IP alongside every query. ODoH (RFC 9230) fixes this by splitting the path into two untrusted halves - a relay that sees the client but only ciphertext, and a resolver that sees the query but only the relay's address:

```text
         ODoH (RFC 9230): proxy splits client identity from query content

   Client                    Relay                     Resolver
     |                         |                          |
     | 1. DNS query, HPKE-     |                          |
     |    encrypted with the   |                          |
     |    resolver's public    |                          |
     |    key (config fetched  |                          |
     |    beforehand)          |                          |
     |------------------------>|  2. opaque ciphertext    |
     |    (sees client IP,     |     forwarded over HTTPS |  3. decrypt, resolve
     |     cannot read query)  |------------------------->|     (sees relay IP,
     |                         |                          |      not client IP)
     |                         |  4. encrypted response   |
     |  5. decrypt locally     |<-------------------------|
     |<------------------------|                          |
     |                         |                          |

   Invariant: no single party holds both (client identity, query content).
   The relay cannot decrypt; the resolver never learns the source address.
```

The crypto is HPKE with the resolver's public key distributed out-of-band, so the relay is genuinely dumb transport. Cloudflare operates production ODoH relays and resolvers, and Apple's iCloud Private Relay routes DNS through this two-hop oblivious design. The cost is one extra network hop and a harder operational story, which is why ODoH stayed an opt-in technology rather than a browser default.

## Deployment reality: who turned it on, and how

**Browsers.** Firefox shipped DoH-by-default in the US in 2019 through its Trusted Recursive Resolver program, then extended the rollout regionally; users control it via `network.trr.mode` (the Mozilla wiki documents the mode matrix). The move drew institutional blowback - the UK ISPA named Mozilla its 2019 "Internet Villain" over DoH-by-default, arguing it would bypass content filters and parental controls. Chrome took the opposite path: **auto-upgrade**. Chrome never sends your traffic to a third-party resolver; it upgrades to DoH only when the DNS server the OS already points at appears in Chrome's list of DoH-capable providers, falling back to plaintext otherwise. Firefox optimizes user privacy; Chrome optimizes non-disruption - a textbook values trade-off encoded in rollout strategy.

**Operating systems.** Android 9+ exposes Private DNS: "opportunistic" mode (try TLS, fall back silently) or "strict" mode with a hostname, authenticated per RFC 8310. iOS 14 and macOS Big Sur brought system-wide encrypted DNS (DoH and DoT) through app APIs and configuration profiles, so VPN-less fleets can pin a resolver fleet-wide. The OS path matters more than the browser path for enterprises because it composes with MDM and applies to every app, not just one browser.

**Routers and networks.** The weakest link by default: home routers and DHCP still advertise plaintext resolvers, so an encrypted-capable device only gets protected if it carries its own resolver list. The IETF's designated-resolver discovery work (DDR) aims to let a local network advertise "here is my encrypted resolver" instead of clients resorting to hardcoded lists; the operational questions around it are still argued in operator circles, and APNIC's measurement team published a dedicated write-up on it as recently as 2025.

| Locus | Who controls it | Typical failure mode when it breaks |
|-------|-----------------|-------------------------------------|
| Browser DoH | End user / browser policy | Split-brain: internal names fail in-browser only |
| OS (Android/iOS) | User or MDM | Opportunistic mode silently falls back to plaintext |
| Router | Whoever owns the box | Stale firmware advertises dead resolvers; no encryption at all |
| Enterprise firewall | Network team | Blanket DoH blocks break browser DNS; allow-listing is a chase |

## The centralization debate and enterprise pain

APNIC's measurement program (Geoff Huston's long-running analysis, plus the continuous APNIC Labs dashboards) documented the uncomfortable consequence of encrypted DNS: queries concentrated on a very small set of public resolvers. When a browser can pick any resolver on earth and the OS default is often "whatever the router says" (i.e., the ISP's, now bypassed), the beneficiaries are the operators with brand recognition and anycast scale - Cloudflare and Google chief among them. Huston's writing frames the trade plainly: DoH shifts surveillance from thousands of local ISPs to a handful of hyperscale resolver operators, trading distributed local observation for centralized global observation with a privacy policy attached. The counterweight is programmatic: browser TRR policies and OS profiles impose data-handling requirements on resolvers, which is governance by client rather than governance by market share.

Enterprise operators face the mirror-image problem - **split-horizon pain**:

- Internal names (`jenkins.corp.local`) leak to a public resolver that cannot answer them, or worse, get queried from off-premise.
- DoH from employee browsers tunnels past the corporate resolver entirely, so malware-domain filtering, logging, and DNS-based parental controls silently stop working - the "middleware breakage" argument in its strongest form.
- The standard responses, in increasing desperation: run an internal DoH server and advertise it (works for OS paths, ignored by browser defaults), block known DoH endpoints at the firewall (whack-a-mole against provider lists), or accept the loss and monitor at egress.

There is no protocol fix - any technology that lets the endpoint bypass the local resolver also lets it bypass every policy that rides on the local resolver. It is a governance question about who the resolver's trust anchor serves, and it is why enterprise DNS vendors now ship DoH servers instead of only blocking them.

## ECH: closing the other leak

Encrypting DNS while sending TLS ClientHellos in cleartext still leaks intent: the SNI field names the host you are connecting to. Encrypted Client Hello (RFC 9849, published March 2026 on the standards track) encrypts the sensitive ClientHello (the inner one) under the server's public key and sends a cover plaintext ClientHello (the outer one) carrying only a public name. The HTTPS/SVCB DNS record is the delivery vehicle for the ECH configuration - which is why ECH is the natural complement to encrypted DNS: the resolver that already returns your IP addresses hands you the key material too. Deployment has been stop-and-go: broad CDN enablement in 2023 was temporarily rolled back within weeks under censorship-avoidance criticism and later re-enabled, which tells you the fight is political, not cryptographic. With DNS and SNI both encrypted, the remaining on-path signal is the destination IP itself - which is why encrypted DNS plus ECH gets you most of the way to VPN-grade metadata privacy without VPN-grade throughput costs.

## Comparison

| Protocol | Port | Transport | On-path observer sees | Hides client IP from resolver | Middlebox interference |
|----------|------|-----------|-----------------------|-------------------------------|------------------------|
| Do53 | 53 | UDP/TCP cleartext | Every query and answer | No (sees you) | Rewrites, redirects, blocks freely |
| DoT | 853 | TCP + TLS | Opaque content, but DoT-identifiable | No | Trivially blocked by port |
| DoH | 443 | HTTP/2 or HTTP/3 over TLS | Indistinguishable from HTTPS | No | Hard to block without collateral |
| DoQ | 853 | QUIC (ALPN "doq") | Opaque, QUIC-identifiable | No | Blockable; migration survives roams |
| ODoH | 443 | HTTPS via relay (ciphertext) | Relay connection only | Yes | Blockable at relay; breaks if relay filtered |

## Failure modes and interview angles

- "Why four protocols?" - DoT: simplest, enterprise-friendly; DoH: censorship- and NAT-proof, HTTP-cache-aware; DoQ: transport-modern; ODoH: metadata privacy. Overlapping but non-identical threat models.
- DoH hides DNS from the path, not from the resolver. For that you need ODoH; for the SNI leak you need ECH; IP addresses remain visible regardless.
- A shared HTTP cache in front of a DoH server can serve another user's answers - legal per RFC 8484 only within TTL, and it correlates users; careful deployments disable sharing (`max-age=0`).
- 0-RTT in DoQ is replayable: only QUERY/NOTIFY opcodes belong in early data, and privacy-conscious clients skip resumption to avoid token linkability.
- Debugging "DNS is broken": check whether the endpoint resolves via a browser DoH path that bypasses the resolver you are debugging (classic split-brain symptom), then check whether opportunistic modes degraded to plaintext.
- Security review takeaway: DNSSEC authenticates records, encrypted DNS protects the query path, ECH protects the connection handshake - each closes a different leak, and none substitutes for another.

## References

1. [RFC 7858: Specification for DNS over Transport Layer Security (TLS)](https://www.rfc-editor.org/rfc/rfc7858.html)
2. [RFC 8484: DNS Queries over HTTPS (DoH)](https://www.rfc-editor.org/rfc/rfc8484.html)
3. [RFC 9250: DNS over Dedicated QUIC Connections](https://www.rfc-editor.org/rfc/rfc9250.html)
4. [RFC 9230: Oblivious DNS over HTTPS](https://www.rfc-editor.org/rfc/rfc9230.html)
5. [Cloudflare 1.1.1.1 docs: DNS over HTTPS endpoint, wire format, and policies](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/)
