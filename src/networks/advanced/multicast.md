# IP Multicast

IP multicast is a network communication pattern where a single sender sends packets to multiple receivers efficiently. The sender sends one copy; the network duplicates the packet at branch points, delivering to all subscribed receivers. Standardized in RFC 1112 (1989), multicast is widely used for streaming media (IPTV, video conferencing), financial market data, and software updates. This page covers the addressing model, the protocols (IGMP, PIM), the tree-building algorithms, and the production deployment state.

## The Addressing Model

Multicast uses the IPv4 address range `224.0.0.0/4` (224.0.0.0 to 239.255.255.255) or IPv6 `ff00::/8`. Each multicast address represents a "group" that receivers join.

```text
224.0.0.0/4 (IPv4):
  224.0.0.0/24: link-local (not forwarded by routers)
  224.0.1.0/24 - 224.0.0.255: well-known
  224.0.1.0 - 238.255.255.255: globally scoped
  239.0.0.0/8: administratively scoped (private use, like RFC 1918)

ff00::/8 (IPv6):
  ff02::1: link-local all nodes
  ff05::1: site-local all nodes
  ff0e::1: global scope
```

For example, `239.0.0.1` could be the "video stream" group; receivers subscribe to this address to receive the stream.

## IGMP (IPv4) and MLD (IPv6)

For a receiver to join a multicast group, it uses IGMP (Internet Group Management Protocol, IPv4) or MLD (Multicast Listener Discovery, IPv6):

```text
Receiver (10.0.0.5) wants to join group 239.0.0.1:
  → Sends IGMP Membership Report to 224.0.0.22 (the "all-IGMP-routers" group).
  → Local router (the "Designated Router") records: 10.0.0.5 joined 239.0.0.1.

Receiver wants to leave:
  → Sends IGMP Leave to 224.0.0.22.
  → Or, after a timeout (default 260 seconds), the router assumes the receiver left.
```

The router uses this info to decide whether to forward multicast traffic for a group out a particular interface. If no receivers are joined on an interface, the router doesn't forward.

## PIM (Protocol Independent Multicast)

PIM is the routing protocol for multicast — it builds the multicast tree from sender to receivers. "Protocol independent" means PIM uses any underlying unicast routing protocol (OSPF, BGP, etc.) for path selection.

### PIM-SM (Sparse Mode)

For most deployments (sparse — receivers are scattered):

```text
Sender → first hop router → RP (Rendezvous Point) → receiver's router → receiver
```

1. The sender's first hop router registers the stream with the RP.
2. The RP is the "meeting point" for senders and receivers.
3. Receiver's router joins the tree toward the RP.
4. Once data flows, the receiver's router can switch to the shortest path tree (SPT) toward the sender (bypassing the RP).

PIM-SM scales well but requires an RP.

### PIM-DM (Dense Mode)

For densely-populated receivers (e.g., a data center):

```text
Sender's router floods the multicast packet to all neighbors.
Routers that have no receivers send "Prune" messages upstream.
The tree is built by "flood and prune".
```

PIM-DM is simpler but floods the network initially. Used in LANs.

### Bidirectional PIM (BIDIR-PIM)

For many-to-many communication (e.g., financial trading where any participant can send):

```text
Sender → first hop router → RP → receiver's router
                ↑                                  ↑
                (bidirectional: traffic flows both ways through the RP)
```

BIDIR-PIM scales to many senders; standard PIM-SM doesn't.

## The Multicast Tree

PIM builds a "tree" from the sender to all receivers:

```text
                    Sender
                       |
                   Router A
                  /         \
              Router B    Router C
                |            |
            Receiver 1   Receiver 2
```

Router A duplicates packets; B and C each get a copy. This is "shared tree" (with RP) or "source tree" (without RP).

## Reverse Path Forwarding (RPF)

The key forwarding rule for multicast: a router forwards a multicast packet only if it arrived on the interface that the router would use to reach the source (RPF check).

```text
Router R has:
  Interface 1: shortest path to Sender S.
  Interface 2: not on the path to S.

R receives a multicast packet from S on Interface 1 → RPF check passes → forward.
R receives a multicast packet from S on Interface 2 → RPF check fails → drop.
```

RPF prevents loops and ensures the tree is consistent.

## Production Use Cases

### IPTV

Cable companies use multicast to deliver TV channels:
- Each channel has a multicast group (e.g., `239.0.0.10` for CNN, `239.0.0.11` for Fox).
- Set-top boxes join the group when the user tunes to the channel.
- The provider's backbone sends one copy per channel, duplicated at branch points.

This is far more efficient than unicast (one stream per viewer).

### Financial Market Data

Stock exchanges use multicast to distribute market data:
- Each symbol (e.g., AAPL) has a multicast group.
- Trading firms subscribe to receive ticks.
- The exchange sends one copy; the network delivers to all subscribers.

This is latency-critical; the network must be designed for low-latency multicast.

### Video Conferencing (1-to-many)

For one-to-many webcasts (e.g., a CEO's all-hands meeting):
- The presenter's stream is multicast to all viewers.
- Saves bandwidth at the presenter's site.

But most modern video conferencing uses SFUs (Selective Forwarding Units) over HTTP/WebRTC, not IP multicast, because IP multicast doesn't traverse the public internet.

### Software Updates

For distributing OS updates to many machines on a LAN:
- The update server multicasts the update image.
- All clients receive the same stream.

This is efficient for large deployments (e.g., a corporate LAN with 1000 machines).

## Production Deployment State

IP multicast is widely used within enterprise and service provider networks, but **not deployed on the public internet**. Reasons:
- Multicast requires all routers on the path to support it.
- The business model for internet multicast (who pays for the extra state?) is unclear.
- Security concerns (DDoS amplification via multicast).

For internet-scale one-to-many, applications use:
- **CDN-based multicast emulation**: the sender sends to many CDN edge servers; each viewer connects to one edge.
- **Application-layer multicast (ALM)**: peer-to-peer networks (e.g., BitTorrent) build their own overlay.

## Common Pitfalls

1. **Forgetting that multicast requires router support.** Most home routers don't support multicast; home networks can't use IP multicast natively.

2. **Forgetting that multicast can be a DDoS amplification vector.** An attacker sending to a multicast group can amplify (one packet, many receivers). This is why the public internet doesn't run multicast.

3. **Forgetting that PIM-SM requires an RP.** Without an RP, the protocol doesn't bootstrap. Use Auto-RP or BSR (Bootstrap Router) for automatic RP election.

4. **Forgetting that IGMP snooping is needed on switches.** Layer-2 switches forward multicast as broadcast, wasting bandwidth. Enable IGMP snooping to forward only to ports with receivers.

5. **Forgetting that multicast over VPNs requires special configuration.** Most VPNs (IPSec, WireGuard) don't support multicast natively. Use GRE-over-IPSec or a multicast-aware VPN.

6. **Forgetting that multicast latency isn't necessarily lower than unicast.** For one-to-one communication, unicast is faster (no tree-building overhead). Multicast's benefit is bandwidth, not latency.

## Comparison to Other Distribution Models

| Model | Sender bandwidth | Receiver count | Use case |
|-------|------------------|-----------------|----------|
| Unicast | N× (one stream per receiver) | Limited by sender | Point-to-point |
| Broadcast | 1× (one stream to all) | All nodes on LAN | LAN-only |
| Multicast | 1× (one stream, duplicated at branches) | Limited by network design | One-to-many |
| Anycast | 1× per query | One receiver per query | Service discovery |
| CDN (unicast + caching) | Sender sends to N CDN edges | CDN edges scale | Internet-scale one-to-many |

For internet-scale one-to-many, CDN beats IP multicast (which doesn't traverse the internet).

## References

- [RFC 1112: Host Extensions for IP Multicasting](https://datatracker.ietf.org/doc/html/rfc1112)
- [RFC 4601: PIM-SM](https://datatracker.ietf.org/doc/html/rfc4601)
- [RFC 3376: IGMP v3](https://datatracker.ietf.org/doc/html/rfc3376)
- [RFC 3810: MLD v2 (IPv6)](https://datatracker.ietf.org/doc/html/rfc3810)
- [Cisco: IP Multicast Technology Overview](https://www.cisco.com/c/en/us/tech/ip/ip-multicast/index.html)
- [Juniper: Multicast Protocols](https://www.juniper.net/documentation/topics/topic-map/multicast-overview.html)
- [LWN: IP Multicast overview (2020)](https://lwn.net/Articles/820133/)
