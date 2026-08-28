# Overlay Mesh VPNs: Coordination Planes, DERP Relays, and Certificate Meshes

Classic remote-access VPNs move packets through a chokepoint: one hub concentrator
every client dials into. Overlay mesh VPNs invert that: every node gets a stable
virtual identity (an IP inside a tailnet or Nebula network), traffic flows
peer-to-peer over whatever underlay exists, and encryption lives at the edge.
This page is the machinery that makes meshing tractable: coordination servers,
certificate hierarchies, relays for unpunchable paths, and path-selection economics.
The raw WireGuard handshake lives in
[WireGuard Protocol](../../cryptography/wireguard-protocol.md); the ops survey is
[VPN Technologies](../../linux/networking/vpn.md); STUN/TURN/ICE mechanics are in
[STUN and TURN](./stun-turn.md).

## Why Mesh: the O(n^2) Configuration Wall

Raw WireGuard is site-to-site: one config entry per peer, per interface -- Tailscale
states the wall directly:

> If you wanted to fully connect 10 nodes, then that would be 9 peer nodes that
> each node has to know about, or 90 separate tunnel endpoints.

Every addition or key rotation touches every config, and devices without static
addresses must be updated on every move. The classic answers were a hub-and-spoke
IPsec concentrator (all traffic hairpins through one box to size, scale, and
defend) or manual full meshing (small nets only). Overlay meshes keep the flat
any-to-any model but replace per-peer config with a control plane handing each
node its identity plus a filtered view of who it may reach. A hub is the only
fixed address, so it survives roaming, but every byte crosses it; a mesh needs a
different fixed point -- not a data path, a *coordination* path.

## Two Planes: Identity Distribution vs Packet Movement

Each node registers by leaving "its public key and a note about where that node
can currently be found, and what domain it's in" at the coordination server. The
server compiles the ACL policy and pushes each node a *signed network map*: which
peers exist, their current endpoints, their public keys. ACL enforcement happens
here, by omission -- a node never learns the endpoint and key of a peer it is not
allowed to contact; unauthorized destinations are simply unreachable. IPsec
instead inspects packets in the data path:

| Item | Coordination server | Notes |
| ---- | ------------------- | ----- |
| Node public keys | yes | signs/verifies map updates, scopes ACLs |
| Endpoint IPs/ports, STUN reflexive addresses | yes | hole-punch hints for peers |
| Private keys, application traffic | never | "private keys never leave the node where they were generated"; payload is end-to-end WireGuard |
| Who talks to whom | partially | map requests reveal allowed intent, not flows |

The coordination plane is a metadata authority, not a key escrow: it can partition
you (stop handing out maps) but cannot read or forge data-plane traffic; the
handshake mechanics both planes rely on are in [WireGuard Protocol](../../cryptography/wireguard-protocol.md).

## DERP: Encrypted Relays for the Unpunchable Path

Some pairs cannot establish a direct UDP path at all: symmetric NATs (the port
mapping depends on the remote endpoint, so a STUN-learned reflexive address is
useless), carrier-grade NAT, and networks that "block UDP entirely, or are
otherwise so strict that they simply cannot be traversed using STUN and ICE".
The fallback must be reachable from anywhere, hence TCP 443: DERP (Designated
Encrypted Relay for Packets) servers are "encrypted TCP relays" that "fill the
same role as TURN servers in the ICE standard, except they use HTTPS streams and
WireGuard keys instead of the obsolete TURN recommendations". Frames cross the
relay over TLS, but the payload stays WireGuard-encrypted between peers:

1. **The relay cannot decrypt.** DERP frames carry WireGuard-encrypted payloads;
   "there is never a way for a DERP server to decrypt your traffic" because
   private keys stay on nodes. The relay is untrusted infrastructure.
2. **It is the bootstrap path, not just a failure path.** Early packets flow
   over DERP while hole punching proceeds in the background, so connections
   feel instant even when the direct path wins 200 ms later.
3. **It is regional.** DERP clusters sit in many POPs; relaying via the nearest
   one is what keeps relayed RTT tolerable (quantified below). The relay is
   open source ([tailscale/tailscale/derp](https://github.com/tailscale/tailscale/tree/main/derp)).

## Magicsock: Keeping the Direct Path Warm

The Tailscale client multiplexes everything over one wildcard UDP socket
(internally, the "magicsock"): one socket talks to DERP regions, sends STUN
requests, and fires WireGuard packets. Two jobs:

- **Re-STUN on a timer.** NAT bindings expire (STUN mappings live for minutes,
  not hours; RFC 8489 describes the mechanism). The socket re-derives the node's
  current external endpoint and reports it to the coordination plane so peers
  always hold fresh punch targets; the toolkit is standard STUN/TURN/ICE
  ([STUN and TURN](./stun-turn.md)).
- **Roaming.** Switch Wi-Fi to LTE and the node updates its endpoint note; peers
  learn the new address on their next map update, because identity is the key
  pair, not the address. Upgrade is lazy: packets start on DERP, background
  probes find a direct path, and the path swaps once proven.

## Headscale: Self-Hosting the Coordination Plane

The control plane is the one trust root you cannot avoid, so it is the piece
people want to own. [Headscale](https://github.com/juanfont/headscale) is "an
open source, self-hosted implementation of the Tailscale control server": stock
clients register against your instance, keeping keys, endpoint notes, and ACL
policy in your infrastructure; DERP regions also become yours to run.

Self-hosting the control plane does not move the data plane: peer traffic still
flows directly, and each DERP region you skip weakens the fallback in that area.

## Nebula: Certificate Chains Instead of Coordination Logins

Nebula (Slack-originated, now Defined Networking) reaches the same mesh goals
with a different trust structure: a PKI instead of login-based coordination.
From the README, Nebula is "a mutually authenticated peer-to-peer software-defined
network based on the Noise Protocol Framework" and "uses certificates to assert a
node's IP address, name, and membership within user-defined groups".

```text
      Nebula PKI                        Tailscale-style trust
 root CA cert (kept offline)      coordination server (online,
 |   signs host certs             signs maps from login identity)
 +-- host cert: node A            +-- node A pubkey + endpoint note
 +-- host cert: node B            +-- node B pubkey + endpoint note
 +-- host cert: lighthouse        +-- ACL policy held centrally
 (overlay IP, name, groups        (identity = login account;
  are IN the cert itself)          ACLs evaluated by coordinator)
```

- **Identity is offline-verifiable.** A host cert carries the node's overlay IP
  and groups; any peer verifies handshakes against the CA cert it already holds,
  no coordination server in the loop, using Noise-based mutual auth.
- **Lighthouses do discovery, not policy.** "Discovery nodes (aka lighthouses)
  allow individual peers to find each other and optionally use UDP hole
  punching" -- rendezvous for endpoint discovery, while firewalling stays local,
  expressed against cert groups (cloud-security-group style filtering).
- **Conservative MTU.** Docs set `tun.mtu` noting the "safe setting is (and the
  default) 1300 for internet routed packets".
- **Boring, but not bug-free.** The 2025-10-07 advisory (source IP spoofing,
  v1.9.4-1.9.6, mishandled packets when a sender's cert configured
  `unsafe_routes`) shows cert-driven authorization has edge cases too.

The trade: no external availability dependency and no third-party metadata, paid
for in PKI lifecycle work and heavier revocation tooling.

## MTU and Fragmentation Realities

Overlays add headers to every packet, and mis-sized MTUs show up as silent
black-holing of bulk transfers (small pings pass, large copies stall):

| Layer | MTU / overhead | Source of the number |
| ----- | -------------- | -------------------- |
| Tailscale TUN (tailscale0) | 1420 | source: with an underlay "MTU of 1500 bytes, the maximum size of a packet entering the tailscale TUN is 1420 bytes" |
| WireGuard data-plane overhead | 60 B (IPv4) / 80 B (IPv6) | IP+UDP (28/48) + 32-byte transport header incl. 16-byte Poly1305 tag |
| Nebula tun.mtu default | 1300 | docs: "safe setting is (and the default) 1300" |
| DERP-relayed packets | extra HTTPS/TCP framing | TLS record + stream framing on top |

Two rules follow. Composing overlays means each layer subtracts, so path MTU
discovery fails softly into fragmentation or stalls -- probe with `ping -M do -s`
sized packets rather than trusting interface values. A deliberately low MTU is
insurance against unknown underlays (GRE, PPPoE, mobile) with bad fragmentation.

## Path Economics: Direct vs Relayed

Relaying costs a detour: A -> DERP -> B is roughly RTT(A,region) + RTT(B,region)
plus userspace forwarding, versus the direct geodesic. Punching is probabilistic
and depends on both ends' NAT types; the model below compares a blocking
probe-then-fallback policy against starting on DERP, then computes relay load.

```python
#!/usr/bin/env python3
# Direct path vs DERP relay cost model; params are model assumptions.
NAT_PUNCH = {        # single-sided probability the NAT permits hole punching
    "eim":   0.95,   # endpoint-independent mapping (home / cone NAT)
    "cgnat": 0.40,   # carrier-grade NAT, double NAT
    "sym":   0.05,   # symmetric NAT: mapping varies per remote endpoint
    "block": 0.00,   # UDP egress blocked outright
}
PROBE_MS = 250       # one blocking hole-punch attempt budget
DERP_FIXED_MS = 8    # userspace relay enqueue/forward overhead

def relay_rtt(ad, bd):
    return ad + DERP_FIXED_MS + bd

def expected(ab, ad, bd, a, b):
    p = NAT_PUNCH[a] * NAT_PUNCH[b]
    r = relay_rtt(ad, bd)
    probe = PROBE_MS + p * ab + (1 - p) * r   # blocking probe-then-fallback
    return p, r, probe

scenarios = [  # name, direct RTT, A->DERP, B->DERP, NAT A, NAT B
    ("home laptop -> home NAS",  30, 12, 14, "eim",   "eim"),
    ("laptop -> office printer", 40, 10, 22, "eim",   "sym"),
    ("phone  -> phone (CGNAT)",  55, 18, 20, "cgnat", "cgnat"),
    ("two symmetric-NAT hosts",  45, 15, 16, "sym",   "sym"),
    ("corporate UDP lockdown",   35,  9, 15, "block", "eim"),
]
print("PANEL A: expected latency-to-first-packet (ms)")
print("%-26s %7s %8s %8s %8s" % ("scenario", "p_dir", "relay", "probe", "policy"))
for name, ab, ad, bd, na, nb in scenarios:
    p, r, probe = expected(ab, ad, bd, na, nb)
    print("%-26s %7.2f %8.1f %8.1f %8s" % (name, p, r, probe,
          "direct" if probe < r else "relay"))
print()
print("PANEL B: break-even punch probability, fleet relay load")
for name, ab, ad, bd, na, nb in scenarios:
    p, r, _ = expected(ab, ad, bd, na, nb)
    be = PROBE_MS / (r - ab) if r > ab else float("inf")
    print("%-26s break-even %5.2f  p_dir %.2f  relayed %5.1f%% = %6.0f/100k"
          % (name, be, p, (1 - p) * 100, 100000 * (1 - p)))
print()
print("PANEL C: DERP region placement (same 30 ms pair, p_dir = 0)")
for label, ad, bd in [("nearest region", 12, 14), ("wrong-coast region", 60, 55)]:
    r = relay_rtt(ad, bd)
    print("%-20s %4.0f ms  %4.1fx direct" % (label, r, r / 30))
```

Output (real run, byte-stable across two executions):

```text
PANEL A: expected latency-to-first-packet (ms)
scenario                     p_dir    relay    probe   policy
home laptop -> home NAS       0.90     34.0    280.4    relay
laptop -> office printer      0.05     40.0    290.0    relay
phone  -> phone (CGNAT)       0.16     46.0    297.4    relay
two symmetric-NAT hosts       0.00     39.0    289.0    relay
corporate UDP lockdown        0.00     32.0    282.0    relay

PANEL B: break-even punch probability, fleet relay load
home laptop -> home NAS    break-even 62.50  p_dir 0.90  relayed   9.8% =   9750/100k
laptop -> office printer   break-even   inf  p_dir 0.05  relayed  95.2% =  95250/100k
phone  -> phone (CGNAT)    break-even   inf  p_dir 0.16  relayed  84.0% =  84000/100k
two symmetric-NAT hosts    break-even   inf  p_dir 0.00  relayed  99.8% =  99750/100k
corporate UDP lockdown     break-even   inf  p_dir 0.00  relayed 100.0% = 100000/100k

PANEL C: DERP region placement (same 30 ms pair, p_dir = 0)
nearest region         34 ms   1.1x direct
wrong-coast region    123 ms   4.1x direct
```

- **Panel A**: blocking-probe loses everywhere: the 250 ms probe budget dominates
  while the relay penalty is only 4-14 ms above direct. Break-even is
  `p_dir > PROBE / (relay - direct)`; no realistic punch probability clears it.
- **Panel B**: steady-state relay load, not first-packet latency, is the real
  cost: the healthy eim/eim pair fails to punch 9.8% of the time (1 - 0.95^2),
  and symmetric-NAT or UDP-blocked pairs relay essentially all traffic.
- **Panel C**: relay quality is placement: the same unpunchable pair is 1.1x
  direct RTT via a nearby region but 4.1x via a far one.

## Interview Angles

- "Where do ACLs get enforced in Tailscale?" -- in map distribution, not the
  data path; stronger than packet filtering (unreachable equals unconfigured),
  but the coordinator sees allowed intent.
- "Why TCP 443 for DERP?" -- UDP-hostile networks leave one near-universal
  channel; HTTPS on 443 provides it, and WireGuard-in-DERP keeps the relay
  untrusted without TURN-style credential machinery.
- "Tailscale vs Nebula trust roots?" -- online coordination with login-derived
  identity vs offline CA-signed certs embedding IP and groups; argue revocation,
  availability, and audit differences.

## References

1. Tailscale, "How Tailscale Works" -- coordination server, DERP, node-key model: <https://tailscale.com/blog/how-tailscale-works>
2. Tailscale DERP relay implementation (open source): <https://github.com/tailscale/tailscale/tree/main/derp>
3. Tailscale `net/tstun` MTU sizing (TUN MTU 1420 on a 1500 underlay): <https://github.com/tailscale/tailscale/blob/main/net/tstun/mtu.go>
4. Headscale -- self-hosted Tailscale control server: <https://github.com/juanfont/headscale>
5. Nebula README (Noise, certs, lighthouses) and config docs (tun.mtu): <https://github.com/slackhq/nebula> and <https://nebula.defined.net/docs/>

Inline standards: RFC 8489 (STUN) and RFC 8445 (ICE) specify the traversal primitives the magicsock and its peers reuse.
