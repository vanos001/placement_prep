# WireGuard Protocol Deep-Dive: Noise IK, Timers, and DoS Defense

WireGuard is a layer-3 VPN designed by Jason A. Donenfeld (first release 2015, merged
into the Linux kernel in 5.6, March 2020). Its defining property is a *fixed* crypto
suite — no cipher negotiation, no certificates, no options — and one 1-RTT handshake in
about 4,000 lines of kernel code. This page dissects the protocol itself: the Noise
IKpsk2 handshake, exact message formats, the key-rotation timer state machine, the
cookie-based DoS defense, and roaming. For day-to-day Linux operations (`wg-quick`,
AllowedIPs, interface setup) see the ops-level
[WireGuard VPN Deep Dive](../linux/networking/wireguard.md).

## 1. The Fixed Cryptographic Suite

Every WireGuard packet is built from exactly five primitives, with no negotiation — a
deliberate security decision: no downgrade path, and an auditable implementation.
Primitive deep dives: [ChaCha20/symmetric encryption](./symmetric-encryption.md),
[BLAKE2/hashing](./hashing.md), [Curve25519/Ed25519](./ed25519.md).

| Primitive      | Algorithm          | Specified in            | Role in WireGuard                          |
| -------------- | ------------------ | ----------------------- | ------------------------------------------ |
| AEAD           | ChaCha20-Poly1305  | RFC 8439                | Encrypts handshakes and all transport data |
| ECDH           | X25519             | RFC 7748                | Static/ephemeral key agreement             |
| Hash / KDF     | BLAKE2s            | RFC 7693                | Chaining key, HKDF, MACs (mac1/mac2)       |
| DoS cookie     | XChaCha20-Poly1305 | draft-irtf-cfrg-xchacha | Encrypts cookie replies (24-byte nonce)    |

The registered Noise name `Noise_IKpsk2_X25519_CHACHA20POLY1305_BLAKE2s` encodes the
whole suite; SipHash-2-4 serves hashtable keys and RFC 5869 HKDF (keyed BLAKE2s)
serves derivation.

## 2. The Noise Framework and the IK Pattern

WireGuard is built on the Noise Protocol Framework, a family of handshakes composed
from a small token grammar: `s` is a static DH key, `e` an ephemeral one, and a token
like `es` means "compute DH(ephemeral, static), mix into chaining key".

```text
IKpsk2:
    <- s              responder's static key is pre-known (not transmitted)
    ...
    -> e, es, s, ss   initiator: ephemeral; DH(e_i, s_r);
    |                 encrypted static s_i; DH(s_i, s_r)
    <- e, ee, se, psk responder: ephemeral; DH(e_i, e_r);
                      DH(e_r, s_i); mix pre-shared key
```

Pattern semantics worth internalizing:

- **"IK" means "initiator static is Known"** — the responder's public static key is an
  input, not a message: peers hold each other's Curve25519 public keys, and `AllowedIPs`
  (cryptokey routing) maps destination prefixes to peers. No certificates needed.
- **Initiator identity hiding.** The initiator's static key goes on the wire only
  *encrypted* (keys from `es`, `ss`); the responder's identity is implicit — the price
  of a single round trip.
- **`psk2` adds a 32-byte (256-bit) pre-shared key** at the end of message 2. Even if a
  future break of X25519 reveals static keys, an attacker *without the PSK* still
  cannot decrypt recorded sessions — the hedge against "harvest now, decrypt later".

Each DH step advances a BLAKE2s chaining key `ch` via HKDF, producing `(ch_next, key)`
pairs; the final chaining key yields the two 32-byte transport keys `k_i2r, k_r2i` plus
32-bit receiver indexes (session identifiers). Ephemeral keypairs are erased
immediately — forward secrecy on a ~2-minute cadence, not a session-lifetime one.

## 3. Message Anatomy (Exact Bytes)

Four message types are multiplexed over one UDP port (default 51820), each starting
with a 4-byte header: 1 byte of type, 3 reserved zero bytes.

| Type | Name                 | Size    | Fields after header (sizes in bytes)                          |
| ---- | -------------------- | ------- | ------------------------------------------------------------- |
| 1    | Handshake Initiation | 148     | sender idx 4, ephemeral 32, enc. static 48, enc. timestamp 28, mac1+mac2 32 |
| 2    | Handshake Response   | 92      | sender idx 4, receiver idx 4, ephemeral 32, enc. empty 16, mac1+mac2 32 |
| 3    | Cookie Reply         | 64      | receiver idx 4, nonce 24, enc. cookie 32                      |
| 4    | Transport Data       | 16 + n  | receiver idx 4, counter 8, encrypted data n (incl. 16-byte tag) |

Sums you can verify: initiation = 4+4+32+48+28+32 = 148; response = 4+8+32+16+32 = 92;
cookie = 4+4+24+32 = 64 — matching the whitepaper and the kernel's
`drivers/net/wireguard/messages.h`. Two fields deserve comment:

- **Timestamp (12 bytes)** in the initiation is TAI64N (8 bytes of TAI seconds, 4 of
  nanoseconds) — not clock synchronization but a *monotone replay marker*: an initiation
  is accepted only if strictly greater than the last one seen for that peer.
- **Counter (8 bytes)** on data packets is the per-direction packet number; with the
  receiver index it forms the 96-bit ChaCha20 nonce. Anti-replay uses an 8192-bit
  sliding-window bitmap (8128 usable bits).

## 4. Key-Rotation Timers: The Exact Constants

WireGuard replaces connection state with timers: a peer is a set of keys plus counters,
and these constants (whitepaper §6.2) decide when keys rotate, retransmit, and die.

| Constant                | Value        | Meaning                                        |
| ----------------------- | ------------ | ---------------------------------------------- |
| `REKEY_AFTER_MESSAGES`  | 2^60         | Rekey after this many sends under one key      |
| `REJECT_AFTER_MESSAGES` | 2^64-2^13-1  | Counter limit; beyond it, packets are rejected |
| `REKEY_AFTER_TIME`      | 120 s        | Initiator rekeys sessions older than this      |
| `REJECT_AFTER_TIME`     | 180 s        | Session unusable after this age without rekey  |
| `REKEY_TIMEOUT`         | 5 s + 0-333 ms jitter | Handshake retransmission interval     |
| `REKEY_ATTEMPT_TIME`    | 90 s         | Give up a handshake attempt series after this  |
| `KEEPALIVE_TIMEOUT`     | 10 s         | Send empty packet if nothing sent this long    |
| Rate limit per IP       | 90 hs / 60 s | Beyond it, the cookie mechanism kicks in       |

The subtle rule is the *safe rekey margin*: `REKEY_AFTER_TIME - KEEPALIVE_TIMEOUT -
REKEY_TIMEOUT = 105 s`. The initiator starts a new handshake at 105 s so that even with
one lost initiation it gets fresh keys before 120 s, ahead of the 180 s deadline. The
responder deliberately does *not* rekey at `REKEY_AFTER_TIME` — only when it has
traffic to send — so both sides never stampede a live peer.

### Executed Demo: The Rotation State Machine

The simulation walks one peer through sessions under a lossy network (the first
initiation of each rekey is lost); constants and rules are the whitepaper's:

```python
"""WireGuard key-rotation state machine (whitepaper s6.2 constants)."""
import random

REKEY_AFTER_TIME, REJECT_AFTER_TIME, REKEY_TIMEOUT = 120, 180, 5   # seconds
KEEPALIVE_TIMEOUT = 10
REJECT_AFTER_MSGS, REKEY_AFTER_MSGS = 2**64 - 2**13 - 1, 2**60
MARGIN = REKEY_AFTER_TIME - KEEPALIVE_TIMEOUT - REKEY_TIMEOUT      # 105 s

random.seed(42)
t, log, sessions, active = 0.0, [], [], {"est": 0.0, "n": 1}  # we initiate; traffic flows
attempt, next_rekey, response_at = None, None, None
log.append((0.0, "session 1 established (we initiated); data flows"))

while t <= 240:
    t = round(t + 0.2, 2)
    age = t - active["est"]
    if next_rekey is None and age >= MARGIN:             # time-based rekey
        log.append((t, f"session {active['n']} age {age:.0f}s >= {MARGIN}s -> rekey"))
        log.append((t, "handshake initiation sent (attempt 1)"))
        attempt = {"sent": t, "tries": 1}
        next_rekey = t + REKEY_TIMEOUT + random.uniform(0, 1 / 3)
    elif attempt and response_at is None and t >= next_rekey:
        if attempt["tries"] == 2:
            response_at = t + 0.2                        # peer answers 2nd attempt
        else:
            attempt["tries"] += 1
            log.append((t, "no response in 5s + jitter -> retransmit"))
            next_rekey = t + REKEY_TIMEOUT + random.uniform(0, 1 / 3)
    elif attempt and response_at is not None and t >= response_at:
        log.append((t, f"response received -> session {active['n'] + 1} established"))
        sessions.append(dict(active))
        active = {"est": t, "n": active["n"] + 1}
        attempt, next_rekey, response_at = None, None, None
    for s in sessions:                                   # old sessions age out
        if t - s["est"] >= REJECT_AFTER_TIME and not s.get("rej"):
            s["rej"] = True
            log.append((t, f"session {s['n']} age {t - s['est']:.0f}s = REJECT_AFTER_TIME -> keys dropped"))

yrs = REJECT_AFTER_MSGS * 1416 / (125e9 * 3600 * 24 * 365.25)
print(f"REKEY_AFTER_MESSAGES = {REKEY_AFTER_MSGS:,}; REJECT_AFTER_MESSAGES = {REJECT_AFTER_MSGS:,}")
print(f"counter path at 1 Gbit/s, 1416-byte packets: {yrs:.0f} years -> time-based rules govern")
print()
for when, what in log:
    print(f"t={when:6.1f}s  {what}")

```

Real output of the run above:

```text
REKEY_AFTER_MESSAGES = 1,152,921,504,606,846,976; REJECT_AFTER_MESSAGES = 18,446,744,073,709,543,423
counter path at 1 Gbit/s, 1416-byte packets: 6622 years -> time-based rules govern

t=   0.0s  session 1 established (we initiated); data flows
t= 105.0s  session 1 age 105s >= 105s -> rekey
t= 105.0s  handshake initiation sent (attempt 1)
t= 110.4s  no response in 5s + jitter -> retransmit
t= 115.8s  response received -> session 2 established
t= 180.0s  session 1 age 180s = REJECT_AFTER_TIME -> keys dropped
t= 220.8s  session 2 age 105s >= 105s -> rekey
t= 220.8s  handshake initiation sent (attempt 1)
t= 226.0s  no response in 5s + jitter -> retransmit
t= 231.4s  response received -> session 3 established
```

Note the overlap: after session 2 is established, session 1 keeps working until its own
180 s deadline — both directions briefly hold two keysets, which makes rekeying lossless
for in-flight packets. Dead-session keys are zeroed at `3 x REJECT_AFTER_TIME = 540 s`.


## 5. The Cookie Mechanism: DoS Defense

A 1-RTT handshake means an initiator can force the responder to do two Curve25519
operations plus hashing for free — a CPU-exhaustion and amplification vector. WireGuard
therefore authenticates cheaply *before* any cryptography happens:

```text
mac1 = BLAKE2s-128(HASH("mac1----" || responder_static_pub), packet_up_to_mac1)
mac2 = BLAKE2s-128(current_cookie,                           packet_up_to_mac2)

"under load" = > 90 handshakes / 60 s from one IP, or handshake queue full
     |
     v  responder still answers, but with a 64-byte Cookie Reply (type 3)
cookie = BLAKE2s-128(cookie_secret, initiator_ephemeral_pub)  secret rotates ~2 min
reply  = XChaCha20-Poly1305(HASH("cookie--" || responder_static_pub),
                            nonce = 24 random bytes, pt = cookie, ad = e_pub)
     |
     v  initiator retries handshake with mac2 filled in; responder checks mac2 FIRST
```

1. **mac1 authenticates cheaply and statelessly.** Any legitimate peer (holding the
   responder's public key) can compute it; the responder verifies it before spending a
   single X25519. Spoofed garbage dies at MAC-check cost.
2. **The cookie binds to the real sender.** It is a MAC of the initiator's *ephemeral*
   public key under a rotating secret. An attacker sending from a spoofed source never
   receives the cookie reply, so it cannot complete the retry — spoofing floods are
   filtered with zero per-attacker state.
3. **The cookie reply is anonymous.** Encrypted under a key derived from the responder's
   static public key, it reveals nothing; the 24-byte nonce is why it uses XChaCha20-
   Poly1305 rather than 12-byte-nonce ChaCha20-Poly1305.

Because mac1 covers the source IP, a packet that validates also proves it was not
address-spoofed — exactly the property roaming leans on.

## 6. Roaming

WireGuard decouples *session* from *endpoint*: a peer's identity is its Curve25519
static key, and the UDP 5-tuple is just the last-seen location. When an authenticated
packet (mac1 valid, timestamp/counter fresh) arrives from a new IP:port, the responder
atomically updates that peer's endpoint and starts using it — no rehandshake, no state
migration, both paths live during transition. A phone moving Wi-Fi to LTE keeps its VPN
session transparently; handshakes follow time, not connectivity. Both peers behind NATs
re-establish reachability themselves: the side receiving an initiation learns where to
reply, and `PersistentKeepalive` (the `KEEPALIVE_TIMEOUT` rule at a fixed interval,
e.g. 25 s) keeps the NAT binding warm. Hijacking an endpoint requires forging mac1 —
the same material needed for everything else.

## 7. Implementations: Kernel vs. wireguard-go

The handshake is identical everywhere; the differences are operational.

| Aspect          | Linux kernel (5.6+)              | wireguard-go / WireGuardKit     | boringtun (Rust)             |
| --------------- | -------------------------------- | ------------------------------- | ---------------------------- |
| Crypto location | In-kernel (Zinc, now lib/crypto) | Userspace, TUN device           | Userspace, TUN device        |
| Per-packet cost | No syscall/context switch        | 2 context switches + copy       | Same shape as wireguard-go   |
| Platform        | Linux only                       | Windows, macOS, FreeBSD, mobile | Cloudflare WARP, library use |
| Throughput      | Line-rate on commodity CPUs      | Lower; ample for client links   | Similar to wireguard-go      |

The kernel implementation (`drivers/net/wireguard/`) keeps per-peer queues, rotates
keyslots, and uses RCU so the data path is essentially lock-free. Userspace builds move
packets through a TUN device: every packet costs a syscall pair and a copy, which is
why multi-gigabit gateways run the kernel module. In exchange, userspace code is
portable and sandboxable — the Windows client is wireguard-go, the official iOS/macOS
apps are built on WireGuardKit (a wireguard-go derivative), and Cloudflare's WARP
client is boringtun. All three exist because the fixed suite makes reimplementation
feasible: there is no option matrix to match.

## 8. Formal Analysis and Known Limitations

WireGuard is among the most formally scrutinized protocols in production; the project
collects the results on its formal-verification page. **Symbolic**: Tamarin and
ProVerif model the IKpsk2 flow against a Dolev-Yao attacker, checking authentication
and secrecy. **Computational**: Dowling and Paterson (ESORICS 2018; eprint 2018/080)
prove key secrecy, mutual authentication, forward secrecy, and resistance to
key-compromise impersonation and reflection in eCK-style and ACCE models.

Honest limitations, none accidental: the responder's identity is not hidden (inherent
to IK's 1-RTT goal); there are no signatures, so sessions are *deniable* — a third
party cannot attribute a transcript to a peer, useful for privacy and useless when
auditability is required; there is no multicast or QoS/DSCP handling; traffic analysis
from sizes and timing remains possible. If a static key leaks, past sessions stay safe
(PFS) but future ones are exposed until rekeying — the optional PSK is the hedge.

## 9. WireGuard vs. IPsec vs. OpenVPN

| Dimension         | WireGuard                      | IPsec (IKEv2)                  | OpenVPN                  |
| ----------------- | ------------------------------ | ------------------------------ | ------------------------ |
| Crypto suite      | Fixed, no negotiation          | Negotiated, agile              | Negotiated via TLS       |
| Handshake         | 1-RTT, ~148 + 92 bytes         | IKE_SA_INIT + IKE_AUTH (2 RTT) | Full TLS handshake       |
| Roaming/reconnect | Instant, timer-driven          | MOBIKE (optional, complex)     | TLS session re-estab.    |
| Key material      | Static pubkeys (+optional PSK) | PSK or X.509 PKI               | X.509 PKI                |
| NAT traversal     | Built into protocol + timers   | NAT-T negotiation              | TCP fallback works       |
| Deniability       | Yes (no signatures)            | No (certificates)              | No (certificates)        |
| FIPS compliance   | Not certifiable (fixed suite)  | Yes, with approved suites      | Yes, with TLS suites     |
| Best fit          | Site-to-site, mobile clients   | Enterprises needing PKI/agility| Legacy remote access     |

The trade WireGuard makes is agility. IPsec can swap algorithms and live in FIPS
environments; WireGuard answers that an algorithm swap is a protocol version bump (v1
is literally in the handshake identifier) and that the small attack surface is the real
defense. For IPsec's packet formats, see [IPsec](../networks/security/ipsec.md).

## 10. Failure Modes to Remember

- **Timestamp regression**: restoring an old VM snapshot or clock makes the responder
  reject all initiations — the classic "VPN died after rollback" incident.
- **Nonce reuse** under a key is catastrophic; a broken RNG is the realistic path,
  which is why ephemeral keys are erased immediately after the handshake.
- **AllowedIPs mistakes** silently route to the wrong peer; the trie is a routing
  table, not a firewall. **MTU**: 60/80 bytes of outer overhead (IPv4/IPv6) means the
  inner interface is usually 1420 — misconfigurations cause "pings work, bulk stalls".

## References

1. J. A. Donenfeld, *WireGuard: Next Generation Kernel Network Tunnel*, whitepaper —
   <https://www.wireguard.com/papers/wireguard.pdf> (timers, message formats, cookies)
2. WireGuard project, *Protocol & Cryptography* — <https://www.wireguard.com/protocol/>
3. Y. Nir, A. Langley, *ChaCha20 and Poly1305 for IETF Protocols*, RFC 8439 —
   <https://www.rfc-editor.org/rfc/rfc8439.html>
4. Noise Protocol Framework (IK pattern semantics) — <https://noiseprotocol.org/noise.html>
5. B. Dowling, K. G. Paterson, *A Cryptographic Analysis of the WireGuard Protocol*,
   ESORICS 2018; eprint 2018/080 — <https://eprint.iacr.org/2018/080>
6. wireguard-linux kernel sources, `drivers/net/wireguard/messages.h` (constants,
   message structs) — <https://git.zx2c4.com/wireguard-linux/plain/drivers/net/wireguard/messages.h>
