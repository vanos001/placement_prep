# WireGuard VPN

WireGuard is a layer-3 VPN that runs over UDP, uses the Noise Protocol Framework to negotiate symmetric keys via X25519, and encrypts every datagram with ChaCha20-Poly1305. Unlike IPSec or OpenVPN, the protocol is stateless from the kernel's perspective: there is no "connection" object on the wire — every encrypted datagram is processed independently, looked up via a 4-byte receiver index in a per-peer table that maps public keys to allowed IP ranges (the "cryptokey routing table"). This page covers the handshake, the cryptographic primitives, the stateless design, the roaming model, multi-peer configuration, and the tradeoffs versus IPSec and OpenVPN.

## Why WireGuard Exists

The WireGuard whitepaper opens with a critique of the existing VPN stack:

- **IPSec** spans thousands of pages of specification (RFC 4301-4355 plus dozens of extensions), multiple key-exchange protocols (IKEv1/IKEv2), two IP modes (transport and tunnel), and an authentication payload format that the paper calls "an inch deep and a mile wide." An implementation bug anywhere in this surface is a security bug.
- **OpenVPN** is effectively a distribution of OpenSSL: it inherits every CVE that ships in OpenSSL, plus the runtime cost of TLS in the data path.

WireGuard's design goal is "code small enough to audit in an afternoon." The in-tree Linux implementation is ~4,000 lines of C; the userspace `wireguard-go` is ~5,000 lines of Go. For comparison, strongSwan is ~600k lines and OpenVPN is ~100k.

## The Crypto Primitives

WireGuard uses exactly four primitives, all reviewed and standardized:

| Purpose | Primitive | Spec |
|---|---|---|
| Key agreement | X25519 (ECDH over Curve25519) | RFC 7748 |
| AEAD | ChaCha20-Poly1305 | RFC 8439 |
| Hash | BLAKE2s-256 | RFC 7693 |
| KDF | HKDF over BLAKE2s (chained) | RFC 5869 |

Total cryptographic surface: 4 primitives. If any one falls (e.g., ECDH on Curve25519 is broken), WireGuard breaks — but so does TLS 1.3 with X25519. There is no agility: WireGuard does not negotiate ciphers.

### Why no cipher negotiation?

Cipher negotiation is what made SSL/TLS vulnerable to downgrade attacks (POODLE, FREAK, Logjam). WireGuard refuses to negotiate — every peer must use the same 4 primitives. A protocol that never negotiates cannot be downgraded.

## The Noise Handshake

WireGuard uses the Noise pattern **Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s**. The Noise grammar decomposes the name as:

- `IK` — the initiator's static key is sent in message 1, and the responder already knows it (out-of-band distribution).
- `psk2` — a pre-shared symmetric key is mixed into the keys derived after message 2.
- `25519_ChaChaPoly_BLAKE2s` — the DH group, AEAD, and hash function.

The handshake is two UDP datagrams (one round trip). After both sides have these two messages, they share a transport key and can exchange user data bidirectionally:

```text
Initiator                                Responder
   |                                        |
   |  (1) handshake msg 1:                  |
   |      ephemeral E_i (plaintext) +       |
   |      AEAD-encrypted static_i, timestamp|
   |--------------------------------------->|
   |                                        |
   |  (2) handshake msg 2:                  |
   |      ephemeral E_r (plaintext) +       |
   |      empty payload + MAC over transcript
   |<---------------------------------------|
   |                                        |
   |  Both sides derive transport keys via  |
   |  HKDF over (ECDH(E_i,E_r),             |
   |             ECDH(E_i, static_r),       |
   |             ECDH(static_i, E_r), PSK)  |
   |                                        |
   |<====== transport data, both ways =====>|
   |       ChaCha20-Poly1305 per message    |
```

The initiator's static key is **encrypted** in message 1 using a key derived from `ECDH(e_i, static_r)` — only the responder (who has `static_r`'s private key) can decrypt it. This gives initiator identity protection against passive observers. The PSK is mixed in at message 2: even if X25519 is broken (e.g., by a future quantum adversary), the PSK still keys the AEAD, so traffic remains confidential unless the attacker also brute-forces the 256-bit PSK.

### Handshake state machine (per peer)

```text
                +-------------+
                |    IDLE     |
                +-------------+
                      |
                      | outbound packet, no transport key
                      v
                +-------------+
                |  HANDSHAKE |   rekey after 120s (REKEY_AFTER_TIME)
                | INITIATION |   give up after 180s (REJECT_AFTER_TIME)
                +-------------+
                      |
                      | recv message 2 (handshake response)
                      v
                +-------------+
                | ESTABLISHED |
                +-------------+
                      |
                      | no traffic + keepalive misses
                      v
                +-------------+
                |    IDLE     |
                +-------------+
```

Rekey happens after 2 minutes (`REKEY_AFTER_TIME`) when traffic is flowing, or after 2^60 transport messages (~7.6 EB at maximum payload size). The state is small: per-peer, the kernel stores the peer's static public key, the current transport key, the 8-byte send/receive counters, and the last-known endpoint.

## Cryptokey Routing

WireGuard does not route by IP alone. The peer table contains, per peer:

- `public_key` — X25519 public key
- `endpoint` — last known UDP address (host:port), updated on every receive
- `allowed_ips` — set of CIDR ranges
- `preshared_key` — optional 256-bit symmetric key for post-quantum resistance
- `persistent_keepalive_interval` — interval in seconds

The routing logic, on every outbound packet:

```text
on packet to send:
  for each peer P:
    if dst_ip ∈ P.allowed_ips (longest-prefix match):
      encrypt with P's current transport key
      send to P.endpoint
      return
  drop packet  # no peer owns this dst
```

On every inbound packet:

```text
on packet received:
  use the 4-byte receiver_index to find the peer P
  verify the Poly1305 tag with P's transport key (constant-time)
  if tag fails: drop
  if src_ip ∉ P.allowed_ips: drop  # source-spoofed
  deliver the inner IP packet to the tun interface
```

This is what "cryptokey routing" means: the routing decision is keyed on the public key of the peer, not on the destination IP alone. Multiple peers can have overlapping `allowed_ips` — the longest-prefix match decides. A peer with `allowed_ips = 0.0.0.0/0` is a "default-route" peer (a.k.a. full-tunnel VPN).

### Multi-peer hub-and-spoke example

```ini
# /etc/wireguard/wg0.conf on hub
[Interface]
PrivateKey = <hub-private-key>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
# spoke A
PublicKey = <spokeA-public-key>
PresharedKey = <shared-a-hub-psk>
AllowedIPs = 10.0.0.2/32, 192.168.1.0/24

[Peer]
# spoke B
PublicKey = <spokeB-public-key>
PresharedKey = <shared-b-hub-psk>
AllowedIPs = 10.0.0.3/32, 192.168.2.0/24

[Peer]
# spoke C (roaming laptop)
PublicKey = <spokeC-public-key>
AllowedIPs = 10.0.0.4/32
```

Spoke A's config:

```ini
[Interface]
PrivateKey = <spokeA-private-key>
Address = 10.0.0.2/24

[Peer]
PublicKey = <hub-public-key>
Endpoint = hub.example.com:51820
AllowedIPs = 10.0.0.0/24, 192.168.0.0/16
PersistentKeepalive = 25
```

`PersistentKeepalive = 25` keeps spoke A's NAT pinhole alive — critical for a spoke behind NAT to remain reachable for incoming handshakes. Without it, the hub loses spoke A's endpoint after ~30 seconds of silence and cannot send packets until spoke A initiates again.

## Stateless Design

The most surprising property of WireGuard is that the implementation is **stateless from the kernel's perspective**: there is no connection object indexed by the 5-tuple. Every encrypted datagram carries, in its 16-byte header, a 4-byte `receiver_index` that the receiver uses to find the right peer and transport key:

```text
Transport message format (16-byte header):

  +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  |type|  reserved   | receiver_idx | counter (8 bytes)             |
  +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  | 1 | 3           | 4            | 8                             |  <-- 16 bytes
  +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  |  encrypted inner IP packet (variable length)                  |
  +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
  |  Poly1305 tag (16 bytes)                                        |
  +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+

  Per-packet WG overhead: 32 bytes (16 header + 16 tag).
  Per-packet total overhead (IPv4): 60 bytes (32 WG + 8 UDP + 20 IP).
```

The receiver uses the 4-byte `receiver_index` to find the peer. There is no session ID that depends on the 5-tuple — the source IP/port are not part of the lookup. This is what enables roaming.

### Comparison: how IPSec/OpenVPN handle roaming

IPSec (IKEv2 + MOBIKE, RFC 4555) supports roaming but requires both peers to maintain IKE SA state, and the responder must explicitly support MOBIKE. A change in source IP triggers IKEv2 INFORMATIONAL exchanges that update the SA's traffic selectors.

OpenVPN does not natively support roaming at all: the TCP/UDP session is bound to a 5-tuple. To "roam," OpenVPN must reconnect.

WireGuard simply works — the source IP is part of the wire format's context only for the `endpoint` field; the receiver updates it on each inbound packet and replies to the new address.

## Roaming in Practice

```text
Time 0: client connects via WiFi 192.168.1.10
        client sends encrypted packet from 192.168.1.10:54321 -> hub:51820

Time 5: client roams to LTE 100.64.5.6
        client sends encrypted packet from 100.64.5.6:43210 -> hub:51820
        (same receiver_idx in header → hub updates endpoint = 100.64.5.6:43210)
        hub replies to 100.64.5.6:43210
```

There is no handshake on roam — the `receiver_index` is sufficient. The client's transport key is unchanged because it was derived from the X25519 ECDH, not from the source IP. A packet sent immediately after a roam arrives with the right key, and the reply is sent to the new endpoint.

## Performance

Each peer on the hub has its own handshake timer and its own transport key. The kernel maintains a per-peer 2^64 message counter; ChaCha20-Poly1305's nonce is the 8-byte counter from the header, so messages can never repeat (the counter is non-repeating, and the AEAD tag prevents forgery).

Throughput on a 2023-era x86_64 box with AVX2 ChaCha20: ~3-4 Gbps per tunnel, limited by userspace→kernel copies and CPU. IPSec with AES-NI in tunnel mode achieves 5-6 Gbps on the same hardware (AES-NI is faster than AVX2 ChaCha20 here). For mobile devices, ChaCha20-Poly1305 wins because many ARM cores lack AES acceleration.

## Comparison

| Aspect | WireGuard | IPSec (IKEv2) | OpenVPN |
|---|---|---|---|
| Transport | UDP | UDP / ESP | UDP or TCP |
| Key exchange | X25519 (Noise IK) | DH/ECDH (RFC 7296) | TLS 1.3 (since 2.5) |
| Cipher | ChaCha20-Poly1305 | AES-GCM, AES-CCM, ChaCha20 | AES-GCM, ChaCha20 |
| Code size | ~4k LoC kernel | ~600k LoC (strongSwan) | ~100k LoC |
| Roaming | Native, no extra messages | MOBIKE (RFC 4555) | No (must reconnect) |
| Negotiation | None (no downgrade) | Cipher negotiation (downgrade-prone) | TLS negotiation |
| Handshake | 2 msgs (1 RTT) | 2-3 round trips IKEv2 | TLS handshake + data |
| Re-key | 2 min OR 2^60 msgs | IKEv2 rekey every 8h typical | TLS session resumption |
| Auditability | Days | Months | Weeks |

## Operational Notes

1. **Each peer needs the other peer's static public key out-of-band.** Most commonly via configuration management (Ansible, Nix). There is no certificate authority — trust is configured directly.

2. **The PSK is optional but recommended.** Mixing a 256-bit PSK into the handshake via HKDF means an attacker who breaks X25519 still cannot decrypt traffic without the PSK. Per-pair PSKs increase blast-radius isolation.

3. **Handshake initiation is rate-limited.** A peer that has not received a reply to its initiation message will back off. MAC validation of handshake messages happens before any work, so spoofed-source floods are cheap to reject.

4. **WireGuard silently drops unauthorized packets.** If a peer sends a packet whose `receiver_index` doesn't match any peer's session, the packet is dropped without any response — the protocol is invisible to port scanners. This is a deliberate choice: stealth over diagnostics.

5. **There is no protocol-level MTU negotiation.** The interface MTU defaults to 1420 to leave headroom for the outer IP/UDP/WG headers (60 bytes for IPv4; 80 for IPv6). For jumbo-frame backbones, set MTU = 8920 to use 9000-byte frames.

## Common Pitfalls

1. **Using the same private key across multiple peers.** WireGuard's Noise handshake assumes unique static keys per peer. Duplicate keys cause message 1 to authenticate two peers — the receiver randomly picks one and the other becomes a black hole.

2. **Forgetting PersistentKeepalive on NAT'd spokes.** Without keepalives, the spoke's NAT pinhole times out and the hub cannot reach the spoke. Set `PersistentKeepalive = 25`.

3. **Allowing 0.0.0.0/0 on the hub.** A spoke with `AllowedIPs = 0.0.0.0/0` on the hub config becomes the default route on the hub, intercepting hub traffic. Use the most specific CIDR that contains only the spoke's own subnet.

4. **Confusing AllowedIPs with "the remote subnet."** `AllowedIPs` is both an ACL (inbound: src_ip must match) and a longest-prefix-match table (outbound: dst_ip picks the peer). Many operators expect it to be only the remote subnet and are surprised that 0.0.0.0/0 also routes ALL hub outbound traffic to that peer.

5. **Rotating keys without coordination.** When you change a peer's PrivateKey on spoke A, you must update the corresponding PublicKey on the hub. There is no certificate rotation; the operator must do it manually.

## References

- [WireGuard whitepaper (Donenfeld, 2020)](https://www.wireguard.com/papers/wireguard.pdf)
- [Noise Protocol Framework](https://noiseprotocol.org/noise.html)
- [RFC 7748: Elliptic Curves for Security (X25519)](https://datatracker.ietf.org/doc/html/rfc7748)
- [RFC 8439: ChaCha20-Poly1305 AEAD](https://datatracker.ietf.org/doc/html/rfc8439)
- [RFC 7693: BLAKE2](https://datatracker.ietf.org/doc/html/rfc7693)
- [RFC 5869: HKDF](https://datatracker.ietf.org/doc/html/rfc5869)
- [WireGuard manual: wg(8) and wg-quick(8)](https://manpages.debian.org/unstable/wireguard-tools/wg.8.en.html)
- [RFC 7296: IKEv2 (IPSec comparison)](https://datatracker.ietf.org/doc/html/rfc7296)
- [RFC 4555: IKEv2 Mobility and Multihoming (MOBIKE)](https://datatracker.ietf.org/doc/html/rfc4555)
