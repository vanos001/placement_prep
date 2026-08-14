# Kubernetes Networking Deep Dive

## CNI Plugins

The Container Network Interface (CNI) is the plugin interface Kubernetes uses for pod networking. The CNI is responsible for assigning IPs to pods and enabling cross-node communication.

| CNI | Data Plane | Network Policy | Performance | Best For |
|-----|-----------|----------------|-------------|----------|
| **Flannel** | VXLAN, host-gw, WireGuard | No (requires Calico overlay) | Good (VXLAN ~10% overhead) | Simple clusters, getting started |
| **Calico** | VXLAN, IPIP, BGP, WireGuard | Yes (rich policy) | Excellent (BGP mode, no encap) | Production, network policy required |
| **Cilium** | eBPF, VXLAN, Native Routing | Yes (L3-L7, DNS-aware) | Excellent (bypasses iptables) | Modern clusters, observability needs |

### Flannel
- Simplest CNI: assigns /24 per node from a /16 cluster CIDR
- Default backend: VXLAN overlay (encapsulates in UDP port 8472)
- `host-gw` backend: no encapsulation, but requires L2 connectivity (single subnet)
- No native NetworkPolicy support

### Calico
- Uses BGP for routing (can integrate with physical network BGP)
- Supports both overlay (IPIP/VXLAN) and non-overlay (BGP/native routing)
- Rich NetworkPolicy with labels, namespaces, and service account selectors
- `calicoctl` CLI for debugging: `calicoctl get workloadendpoints`, `calicoctl ipam show`

### Cilium
- Uses eBPF in the kernel for data plane—bypasses iptables entirely for pod-to-pod traffic
- Provides L3-L7 network policies (can filter on HTTP methods, headers, DNS names)
- Hubble: built-in observability for network flows, metrics, and tracing
- Transparent encryption with WireGuard or IPsec
- Bandwidth management and CIDR-aware policy
- Requires Linux kernel ≥ 5.10 for full feature set

## Service Networking

### Service Types

| Type | Scope | Access | Use Case |
|------|-------|--------|----------|
| **ClusterIP** | Cluster-internal | `service-name.ns.svc.cluster.local` | Internal microservices |
| **NodePort** | Node-level | `NodeIP:30000-32767` | Dev/testing, bare metal | 
| **LoadBalancer** | External | Cloud provider LB → NodePort | Public-facing services on cloud |
| **Headless** | DNS only | Returns pod IPs directly (no VIP) | StatefulSets, custom load balancing |

Headless services (ClusterIP: None) are critical for StatefulSets—the DNS returns individual pod A records (`pod-0.service.ns.svc.cluster.local`), enabling stable network identities.

### kube-proxy Modes

kube-proxy programs the node's network rules so that Service VIPs resolve to actual pod IPs.

| Mode | Implementation | Performance | Scaling |
|------|---------------|-------------|---------|
| **iptables** (default) | iptables rules + random pod selection | Good for <5000 services | O(n) rule match, slows at scale |
| **IPVS** | Linux IPVS virtual server in kernel | Excellent | O(1) lookup, handles 50K+ services |
| **nftables** | nftables (K8s 1.29+, experimental) | Good | Better than iptables at scale |
| **userspace** | Proxy in userspace (deprecated) | Poor | Not recommended |

IPVS load balancing algorithms:
- `rr` (round-robin), `lc` (least connections), `wrr` (weighted round-robin), `sh` (source hashing for session affinity)

Enable IPVS:
```yaml
# kube-proxy configmap
mode: ipvs
ipvs:
  scheduler: least-connections
```

### Why is kube-proxy NOT a real proxy?

Despite the name, kube-proxy does not proxy packets. It programs kernel-level rules (iptables/IPVS) that perform DNAT (destination NAT) on packets destined for a Service ClusterIP. The packet is directly forwarded to a pod IP—no userspace proxy is involved in the data path.

## Ingress Controllers

Ingress operates at L7 (HTTP/HTTPS) and routes external traffic to Services based on host/path rules.

| Controller | Features | Best For |
|-----------|----------|----------|
| **NGINX Ingress** | Mature, annotation-based config, Lua scripting | General purpose |
| **Traefik** | Auto-discovery, dashboard, Let's Encrypt | Dynamic environments, dev |
| **Istio Gateway** | mTLS, traffic management, observability | Service mesh deployments |
| **Kong** | API gateway, plugins, rate limiting | API management |
| **AWS ALB Ingress** | Native ALB integration | AWS-only clusters |
| **HAProxy** | Advanced L4/L7, TCP routing | High-performance TCP + HTTP |

An Ingress controller is NOT a built-in Kubernetes component—you must deploy one. The Ingress resource is just a configuration object; the controller implements the actual routing.

## CoreDNS

CoreDNS is the cluster DNS server, replacing the older kube-dns. It resolves:

- `pod-ip-10-0-1-5.ns.pod.cluster.local` → Pod IP (disabled by default)
- `service-name.ns.svc.cluster.local` → ClusterIP
- `headless-pod-0.service.ns.svc.cluster.local` → Pod IP
- External names via ExternalName services
- Custom DNS entries via ConfigMap plugins

```yaml
# CoreDNS ConfigMap (kube-system/coredns)
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

Common DNS issues:
- **NDots (default 5)**: If a query has fewer than 5 dots, it's tried with the cluster domain suffixes first, then the absolute name. This causes 2-3 DNS lookups per external request. For external services, use fully qualified names (trailing dot) or reduce `ndots`.
- **DNS resolution delay**: `dnsPolicy: Default` uses the node's resolv.conf (skips CoreDNS), useful for pods that make many external calls.

## Network Policy Examples

### Default deny all ingress:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # Selects all pods
  policyTypes:
    - Ingress
  ingress: []  # Empty = deny all
```

### Allow cross-namespace traffic via label:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              team: monitoring
        - podSelector:
            matchLabels:
              app: prometheus
      ports:
        - port: 9090
```

## References

- [CNI Spec](https://github.com/containernetworking/cni)
- [Cilium Documentation](https://docs.cilium.io/)
- [kube-proxy IPVS](https://kubernetes.io/docs/concepts/services-networking/service/#proxy-mode-ipvs)
- [CoreDNS Plugins](https://coredns.io/plugins/)

## Interview Questions

### Q1: How do pods communicate across nodes in Kubernetes?
**Answer**: Each CNI handles this differently. **Flannel** uses VXLAN encapsulation (wraps pod packets in a UDP overlay) or host-gw (direct routing if L2 connected). **Calico** can use BGP to advertise pod CIDRs to the network, allowing direct routing without overlay, or IPIP/VXLAN for overlay. **Cilium** uses eBPF programs that perform smart routing decisions in the kernel, avoiding iptables overhead. All CNIs assign each pod a unique IP from a cluster-wide CIDR and ensure the routing table on each node knows how to reach other nodes' pod subnets.

### Q2: What is the difference between a Service and an Ingress?
**Answer**: A Service operates at L4 (TCP/UDP) and provides stable networking for a set of pods. Ingress operates at L7 (HTTP/HTTPS) and routes external traffic to Services based on host and path rules. A Service of type LoadBalancer exposes one Service per cloud load balancer (expensive). Ingress allows a single load balancer to route to many Services based on HTTP headers, paths, and hosts. Services are for internal cluster communication; Ingress is for external HTTP access.

### Q3: Why would you choose IPVS over iptables for kube-proxy?
**Answer**: iptables uses sequential rule matching (O(n)), which degrades as the number of services grows—typically noticeable above 5,000 services with increased latency. IPVS uses a hash table for O(1) lookup and runs in kernel space, supporting multiple load balancing algorithms (least connections, weighted round-robin, source hashing). IPVS handles tens of thousands of services with minimal overhead. The tradeoff is that IPVS requires the `ip_vs` kernel module and is slightly more complex to debug.

### Q4: What is a headless Service and when would you use one?
**Answer:** A headless Service has `clusterIP: None`. It does NOT allocate a virtual IP or do load balancing. Instead, CoreDNS returns the individual Pod IPs as A records. Use cases: (1) **StatefulSets** where each pod needs a stable DNS identity (pod-0.service.ns.svc.cluster.local), (2) Custom load balancing where the client selects pods itself, (3) Direct pod addressing for debugging. For StatefulSets like Kafka or Cassandra, headless services are required for stable network identities.

### Q5: How does DNS work in Kubernetes and what is the ndots problem?
**Answer**: CoreDNS resolves all in-cluster DNS queries. By default, `ndots: 5` means that if a hostname has fewer than 5 dots, Kubernetes tries appending cluster suffixes first (`svc.cluster.local`, `cluster.local`) before resolving the absolute name. For external domains like `api.github.com` (2 dots), this causes 2-3 DNS round trips before resolving. Solutions: (1) Use fully qualified names with a trailing dot (`api.github.com.`), (2) Set `dnsPolicy: Default` for pods making many external calls, (3) Reduce ndots in the pod's DNS config. In latency-sensitive applications, this can add 10-50ms per DNS lookup.
