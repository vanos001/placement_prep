# HashiCorp Consul

Consul is a service mesh and service discovery tool, originally developed by HashiCorp in 2014. It provides service discovery (via a DNS or HTTP API), health checking, key-value storage, and multi-datacenter support. Consul is widely used as a Service Mesh alternative to Istio/Linkerd, especially in non-Kubernetes environments. This page covers the architecture, the gossip protocol, the service discovery model, and the comparison to etcd and ZooKeeper.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Consul Cluster (per datacenter)                            │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐         │
│  │  Server 1 (leader)  │  │  Server 2 (follower)  │         │
│  │  - Raft consensus    │  │  - Raft consensus     │         │
│  │  - KV store          │  │  - KV store           │         │
│  └─────────────────────┘  └─────────────────────┘         │
│  ┌─────────────────────┐                                   │
│  │  Server 3 (follower)  │                                   │
│  └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
        ▲                                ▲
        │ gossip (LAN)                   │ gossip (WAN)
        │                                │
┌──────────────────────┐    ┌──────────────────────┐
│  Client agent (Node A) │    │  Client agent (Node B) │
│  - Gossips with servers│    │  - Gossips with servers│
│  - Health checks         │    │  - Health checks         │
│  - Proxies to services   │    │  - Proxies to services   │
└──────────────────────┘    └──────────────────────┘
```

Consul has two planes:
- **Control plane**: servers (3-5 per datacenter, Raft-replicated).
- **Data plane**: client agents on each node, plus Envoy sidecars (or built-in proxies).

## The Gossip Protocol

Consul uses the SWIM (Scalable Weakly-consistent Infection-style Process Group Membership) gossip protocol for failure detection:

```text
Each node (server or client) gossips every 1 second:
  - Picks a random peer, sends its known state.
  - Receives the peer's state, updates its own.

Failure detection:
  - A node that doesn't respond to direct probes is "suspected".
  - Suspected nodes are gossiped; consensus forms.
  - After a configurable timeout, the node is declared dead.
```

The gossip protocol provides:
- **Fast failure detection**: ~3 seconds to detect a failed node.
- **Decentralized**: no central failure detector; each node tracks all peers.
- **Scalable**: gossip is O(1) per node per second, regardless of cluster size.

Consul uses HashiCorp's memberlist library for the gossip layer.

## Service Discovery

Services register with the local Consul agent:

```json
{
  "service": {
    "name": "my-web",
    "id": "my-web-1",
    "address": "10.0.0.1",
    "port": 8080,
    "check": {
      "http": "http://10.0.0.1:8080/health",
      "interval": "10s"
    }
  }
}
```

The agent:
1. Registers the service with the local state.
2. Runs the health check periodically.
3. Gossips the service state to the servers.
4. The servers propagate to all agents.

Clients discover via:
- **DNS**: `my-web.service.consul` resolves to healthy instances' IPs.
- **HTTP API**: `GET /v1/health/service/my-web?passing=true`.

```bash
# DNS lookup
dig my-web.service.consul

# HTTP API
curl http://localhost:8500/v1/health/service/my-web?passing=true
```

The DNS interface makes Consul a drop-in for existing applications that use DNS for service discovery.

## Health Checking

Consul supports multiple check types:
- **HTTP**: GET a URL; pass if 2xx.
- **TCP**: open a TCP connection; pass if successful.
- **Script**: run a script; pass if exit 0.
- **TTL**: the service must "heartbeat" within a TTL window.
- **Docker**: check a Docker container's health.
- **gRPC**: gRPC health checking protocol.

```json
{
  "check": {
    "id": "web-health",
    "name": "Web HTTP check",
    "http": "http://localhost:8080/health",
    "interval": "10s",
    "timeout": "2s"
  }
}
```

Failed checks mark the service as "critical"; the DNS interface won't return that instance's IP.

## Key-Value Store

Consul has a hierarchical KV store, like etcd:

```bash
# Put a value
consul kv put config/myapp/log_level debug

# Get a value
consul kv get config/myapp/log_level

# Watch for changes
consul watch -type=kv -key=config/myapp/log_level handler.sh
```

The KV store uses Raft for strong consistency. It's not as feature-rich as etcd (no leases), but covers most config-management use cases.

## Multi-Datacenter Support

Consul's design supports multi-datacenter out of the box:

```text
DC1 (US-East):
  - 3 servers, gossip LAN
  - Many client agents

DC2 (EU-West):
  - 3 servers, gossip LAN
  - Many client agents

WAN gossip connects the DCs:
  - Each DC's servers gossip with each other DC's servers.
  - Cross-DC service discovery works via DNS (with a `@dc1` suffix).
```

This is a major advantage over etcd (which is single-datacenter by design).

```bash
# Discover service in another DC
dig my-web.service.consul.@dc1
# Returns the IPs of my-web in dc1.
```

## Consul Service Mesh (Connect)

Consul Connect (since 1.2, 2018) adds service mesh features:
- Sidecar proxies (Envoy) for mTLS between services.
- Intentions (L7 policy): "service A can call service B on /admin/*".
- Built-in CA for cert management.

```hcl
# Intentions: deny frontend → database on /admin/*
resource "consul_intention" "deny-admin" {
  source_name = "frontend"
  destination_name = "database"
  action = "deny"
  description = "Frontend can't access /admin/* on database"
}
```

Consul Connect integrates with Envoy as the data plane (similar to Istio), but can also use a built-in proxy for simpler setups.

## Production Use Cases

### Service Discovery in Non-K8s

For VMs, bare metal, or mixed infra:
- Each VM runs a Consul agent.
- Services register with the agent.
- Discovery via DNS: `my-web.service.consul`.

### Multi-DC Service Mesh

For applications spanning multiple datacenters:
- Each DC has its own Consul cluster.
- WAN gossip connects them.
- Services can discover each other across DCs.

### Configuration Management

For distributed config (alternative to etcd):
```bash
consul kv put config/myapp/feature_flags '{ "new_ui": true }'
```

Services watch the config key and apply changes dynamically.

## Production Performance

Consul's performance on a 5-server cluster:
- Service registration: ~1000 services/sec.
- DNS lookup: <1 ms (cached).
- HTTP API: ~5 ms.
- Health check interval: 10 sec (default).
- Failure detection: ~3 sec.

Consul's bottleneck is the Raft consensus on writes; reads can be served by any server (eventually consistent) or by the leader (linearizable).

## Common Pitfalls

1. **Forgetting that Consul needs at least 3 servers for HA.** A 2-server cluster can't survive a failure; use 3 or 5.

2. **Forgetting that the client agent is required.** Without the agent on each node, the node's services can't register or be discovered.

3. **Forgetting that gossip doesn't tolerate network partitions gracefully.** A partitioned node may gossip "I'm healthy" to itself; the servers may declare it dead. Use multiple gossip probes for reliability.

4. **Forgetting that Consul's KV store is Raft-based.** A failed write means the leader lost quorum; the cluster is briefly unavailable. Don't use Consul's KV for high-throughput writes.

5. **Forgetting that health checks should be lightweight.** A 5-second HTTP check that takes 4 seconds to return delays the next check. Keep checks <1 second.

6. **Forgetting that Consul Connect's sidecars need Envoy.** The built-in proxy is for dev only; production needs Envoy. Plan Envoy deployment.

## Comparison to etcd and ZooKeeper

| Aspect | Consul | etcd | ZooKeeper |
|--------|--------|------|-----------|
| Origin | HashiCorp 2014 | CoreOS 2013 | Yahoo 2008 |
| Consensus | Raft | Raft | ZAB |
| Service discovery | First-class | Via watch | Via watch |
| Health checking | Built-in | External | External |
| Multi-DC | First-class | Manual | Manual |
| Service mesh | Connect | None | None |
| Best for | Service discovery + mesh | KV store | Hadoop/Kafka coordination |

Consul's strength is the integrated service discovery + health checking + mesh. etcd is simpler for KV. ZooKeeper is older and still widely used in the Hadoop/Kafka ecosystem.

## References

- [Consul documentation](https://developer.hashicorp.com/consul/docs)
- Das et al., "[SWIM: Scalable Weakly-consistent Infection-style Process Group Membership](https://www.cs.cornell.edu/~asdas/research/swim.pdf)" (1999)
- [Consul Architecture](https://developer.hashicorp.com/consul/docs/architecture)
- [Consul Connect (service mesh)](https://developer.hashicorp.com/consul/docs/connect)
- [HashiCorp memberlist library](https://github.com/hashicorp/memberlist)
- [Consul vs etcd vs ZooKeeper comparison](https://www.consul.io/docs/intro/zk-etcd-consul-cmp.html)
- [LWN: Consul overview (2019)](https://lwn.net/Articles/796030/)
