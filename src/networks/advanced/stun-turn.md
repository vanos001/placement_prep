# STUN and TURN

STUN (Session Traversal Utilities for NAT) and TURN (Traversal Using Relays around NAT) are protocols that enable WebRTC and other real-time communication protocols to traverse Network Address Translation (NAT) and firewalls. STUN discovers the public IP/port of a peer; TURN provides a relay server for cases where direct connection fails. This page covers the protocols, the NAT traversal problem, and the production deployment patterns.

## The NAT Problem

Most home networks use NAT: the internal IPs (192.168.1.x) are translated to one public IP by the router. When a peer outside tries to connect to a peer inside the NAT, the connection fails because the NAT doesn't know how to route the inbound packet.

```text
Peer A (10.0.0.5) → NAT-A (1.2.3.4) → Internet
                                          ↓
                                          Peer B (5.6.7.8)
```

Peer B can't send packets to 10.0.0.5 (a private IP); the router at 1.2.3.4 doesn't know how to forward them.

## STUN

STUN (RFC 5389) is a protocol that lets a peer discover its public IP/port:

```text
Peer A (10.0.0.5) sends STUN request to STUN server (stun.example.com):
  - Source: 10.0.0.5:12345 (internal IP/port)
  - Destination: stun.example.com:3478

STUN server sees the request from the public side:
  - Source: 1.2.3.4:54321 (NAT-A's public IP/port)
  - Response: "Your public IP is 1.2.3.4, port 54321"

Peer A learns its public IP/port and shares it with Peer B.
Peer B can now send UDP packets to 1.2.3.4:54321; the NAT routes them to 10.0.0.5:12345.
```

This works for many NAT types (full-cone NAT, restricted-cone NAT) but not for symmetric NAT (where the NAT assigns a different public port per destination).

## TURN

TURN (RFC 5766) is a protocol for relaying traffic through a server. Used when direct peer-to-peer connection fails (e.g., symmetric NAT, restrictive firewall):

```text
Peer A ←→ TURN server ←→ Peer B
       (relay)
```

TURN is expensive: every byte goes through the TURN server, which costs bandwidth and adds latency. It's used as a fallback when STUN fails.

## The ICE Protocol

ICE (Interactive Connectivity Establishment, RFC 8445) is the protocol that orchestrates STUN and TURN:

```text
1. Both peers gather "candidates":
   - Host candidates: the local IPs (10.0.0.5).
   - Server-reflexive candidates: from STUN (1.2.3.4:54321).
   - Relay candidates: from TURN (turn.example.com:3478, port 9999).

2. Peers exchange candidates (via signaling — typically WebSocket or HTTP).

3. Each peer tries to connect to the other peer's candidates:
   a. Try host → host (local IPs; usually fails across the internet).
   b. Try server-reflexive → server-reflexive (direct P2P; works for most NATs).
   c. Try relay → relay (TURN; always works but is slow).

4. The first working connection is used.
```

## WebRTC ICE Configuration

```js
const peerConnection = new RTCPeerConnection({
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },  // public STUN server
    {
      urls: 'turn:turn.example.com:3478',
      username: 'user',
      credential: 'pass',
    },
    {
      urls: 'turns:turn.example.com:5349',  // TURN over TLS
      username: 'user',
      credential: 'pass',
    },
  ],
});

// Listen for ICE candidates
peerConnection.addEventListener('icecandidate', (event) => {
  if (event.candidate) {
    // Send the candidate to the other peer via signaling
    signalingChannel.send({ type: 'ice-candidate', candidate: event.candidate });
  }
});

// Receive ICE candidates from the other peer
signalingChannel.onMessage((message) => {
  if (message.type === 'ice-candidate') {
    peerConnection.addIceCandidate(message.candidate);
  }
});
```

## The TURN Allocation Protocol

TURN allocation:
1. Client sends TURN Allocate request to the TURN server.
2. Server allocates a "relay transport address" (an IP/port on the TURN server).
3. Server returns the address to the client.
4. Client shares the address with peers.
5. Peers send packets to the TURN address.
6. TURN server forwards to the client's allocation.

TURN has a permission model: the client must "create permission" for a peer's IP before TURN forwards traffic from that peer. This prevents abuse.

The allocation has a lifetime (default 10 minutes); the client must send refresh requests to keep it alive.

## Production Use Cases

### Video Conferencing

The canonical use: WebRTC video chat. For two peers behind NATs:
1. Both get STUN candidates.
2. Try direct P2P.
3. If fails (e.g., both behind symmetric NAT), fall back to TURN.

For larger calls (3+ participants), use SFU (Selective Forwarding Unit) instead of P2P mesh.

### Multiplayer Games

For low-latency real-time multiplayer (e.g., fighting games), TURN provides a fallback when P2P fails.

### IoT Device Communication

For IoT devices behind carrier-grade NAT (which often blocks inbound traffic), TURN is the only way to reach them.

## Production Performance

STUN/TURN performance characteristics:
- STUN latency: ~50-200 ms per request (depends on STUN server location).
- TURN throughput: limited by TURN server's bandwidth; typically 10-100 Mbps per allocation.
- TURN latency: adds ~20-50 ms per direction (vs. direct P2P).
- TURN cost: egress bandwidth is the dominant cost.

For 1-hour video calls at 2.5 Mbps (HD video), 3 GB of TURN bandwidth per call. At $0.05/GB, that's $0.15 per call.

## Public STUN Servers

Many public STUN servers are available:
- `stun:stun.l.google.com:19302` (Google).
- `stun:stun1.l.google.com:19302`.
- `stun:stun2.l.google.com:19302`.
- `stun:stun.cloudflare.com:3478` (Cloudflare).

For production deployments, run your own STUN server (e.g., coturn). Public servers may rate-limit or be unreliable.

## Self-Hosting coturn

coturn is the standard open-source STUN/TURN server:

```conf
# /etc/turnserver.conf
listening-port=3478
tls-listening-port=5349
listening-ip=0.0.0.0
external-ip=1.2.3.4  # your public IP

# Authentication (use long-term credentials for production)
lt-cred-mech
user=user:pass

# Realm (for credentials)
realm=example.com

# Bandwidth limits per session
max-bps=5000000  # 5 Mbps

# Logging
log-file=/var/log/turnserver.log
simple-log
```

```bash
# Start coturn
turnserver -c /etc/turnserver.conf
```

For HA, run multiple coturn instances behind a load balancer; clients will pick whichever the load balancer routes to.

## Common Pitfalls

1. **Forgetting that STUN doesn't work for symmetric NAT.** Symmetric NAT assigns a different public port per destination; the STUN server's response is useless for peer-to-peer connections.

2. **Forgetting that TURN is expensive.** TURN bandwidth is the dominant cost in WebRTC deployments. Monitor and budget carefully.

3. **Forgetting to refresh TURN allocations.** TURN allocations expire (default 10 minutes); the client must send refresh requests. Most WebRTC libraries handle this automatically.

4. **Forgetting that TURN permissions are per-peer.** TURN won't forward traffic from a peer without permission. WebRTC libraries create permissions automatically when adding ICE candidates.

5. **Forgetting that the TURN server must be reachable from both peers.** A TURN server behind a corporate firewall doesn't help if the peers are outside.

6. **Forgetting that STUN over TCP is rare.** STUN is typically UDP; for TCP fallback (when UDP is blocked), use TURN over TCP (`turn:turn.example.com:3478?transport=tcp`).

## Comparison to Other NAT Traversal Approaches

| Approach | Use case | Performance |
|----------|----------|-------------|
| STUN | Discover public IP/port | Fast (one round-trip) |
| TURN | Relay traffic | Slow (always through server) |
| UPnP-IGD | Auto-port-forward on home routers | Only works with UPnP-enabled routers |
| Manual port forwarding | Reliable when allowed | Requires user config |
| VPN | Tunnel all traffic | Heavier; encrypts everything |

For WebRTC and real-time communication, STUN + TURN (with ICE) is the standard.

## References

- [RFC 5389: STUN](https://datatracker.ietf.org/doc/html/rfc5389)
- [RFC 5766: TURN](https://datatracker.ietf.org/doc/html/rfc5766)
- [RFC 8445: ICE](https://datatracker.ietf.org/doc/html/rfc8445)
- [WebRTC: STUN and TURN](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols)
- [coturn: Open-source TURN server](https://github.com/coturn/coturn)
- [Public STUN server list](https://gist.github.com/mondain/b2619a01463ce0ec2234)
- [LWN: STUN/TURN overview (2020)](https://lwn.net/Articles/815575/)
