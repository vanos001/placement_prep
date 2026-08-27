# Cilium: eBPF as the Kubernetes Datapath

Every pod-to-pod packet in a Kubernetes cluster crosses policy and load-balancing
checkpoints. kube-proxy implements those checkpoints with iptables rules; Cilium replaces
them with eBPF programs attached at the same hooks, compiled from pod labels and Service
state. This page covers that datapath: why the thing it replaces scales badly, where the
programs attach, how a packet carries an identity instead of just an IP, and what Hubble
can observe. Raw XDP/TC/AF_XDP mechanics: [eBPF Networking](../ebpf-networking.md);
overlay encapsulation: [Geneve Overlay Network](geneve.md).

## Why kube-proxy's iptables mode hits a wall

A Service in iptables mode is a set of rules, not a table. For every Service port,
kube-proxy appends a rule to the KUBE-SERVICES chain that matches the cluster IP and
jumps to a per-Service chain, which contains one rule per backend plus statistic-module
probability rules for load distribution. Consequences, all mechanical:

- Every first packet on the node walks the KUBE-SERVICES chain rule by rule until it
  matches. Cost per packet grows linearly with the number of Services and backends
  installed on the node; the kube-proxy documentation describes iptables mode as
  "linearly" scaling and recommends IPVS for large clusters
  ([virtual IPs reference](https://kubernetes.io/docs/reference/networking/virtual-ips/)).
- Rule *updates* replay the whole table: iptables cannot replace one rule atomically
  cheaply, so kube-proxy serializes diffs through iptables-restore. At thousands of
  Services, a single endpoint change costs a large ruleset rewrite per node.
- Everything rides on conntrack (the NAT is conntrack state), so the conntrack table is
  on the critical path of both the data path and the CRR (connect-request-response)
  workload, which is the worst case for iptables: in Cilium's 2021 bare-metal benchmark
  on 100 Gbit/s NICs, bypassing iptables conntrack with NOTRACK rules lifted the baseline
  to about 200K new connections/s, and the best datapaths pushed single-TCP-stream
  throughput to just over 40 Gbit/s
  ([CNI benchmark](https://cilium.io/blog/2021/05/11/cni-benchmark/)).

Isovalent's "why replace iptables" write-up states the structural reason plainly: iptables
matches rules sequentially, so per-packet cost scales linearly with rule count
([Isovalent blog](https://isovalent.com/blog/post/why-replace-iptables-with-ebpf/)).
IPVS mode fixes the lookup with hash tables (O(1)) but keeps the conntrack dependency and
a userspace sync loop, and has its own traps: stale conntrack entries after backend
removal keep landing traffic on a dead pod until they time out.

A small scaling model makes the shape concrete (a model, not a measurement -- the
per-rule constant is illustrative; the linear-vs-constant asymptotics are the point).

```python
"""First-packet service lookup cost: iptables chain walk vs single hash lookup.
Model constants are illustrative; only the asymptotic shape is the claim."""
RULE_NS = 90        # ~per-rule match cost (match + jump accounting)
SERVICES_PER_NODE = [40, 1_000, 5_000, 20_000]
RULES_PER_SVC = 5   # KUBE-SERVICES entry, jump, per-port mark/EXT rules, backend rules

def iptables_walk(services):
    rules = services * RULES_PER_SVC
    hits_at = rules // 2          # average match position, no early exit
    return hits_at * RULE_NS

def ebpf_lookup(_services):
    return 120                    # one hash map lookup + NAT decision, ~flat

print(f"{'services':>9} | {'iptables walk (us)':>19} | {'eBPF hash (us)':>14}")
for s in SERVICES_PER_NODE:
    print(f"{s:>9} | {iptables_walk(s)/1000.0:>19.1f} | {ebpf_lookup(s)/1000.0:>14.2f}")
```

Real output (Python 3.12):

```text
 services |  iptables walk (us) | eBPF hash (us)
       40 |                 9.0 |           0.12
     1000 |               225.0 |           0.12
     5000 |              1125.0 |           0.12
    20000 |              4500.0 |           0.12
```

Four and a half milliseconds of pure rule-walk per first packet at 20K Services: the
qualitative claim above, made concrete. The eBPF path stays flat because its Service
table is a hash map keyed by (VIP, port, protocol), not a chain.

## The datapath: which program runs where

Cilium compiles its state (Services, endpoints, identities, policy) into BPF maps and a
set of per-hook programs. The names below are the actual source files in the Cilium tree
(bpf_host.c, bpf_lxc.c, bpf_overlay.c, bpf_xdp.c), and they attach like this:

| Program | Attach point | Job |
|---|---|---|
| bpf_xdp | native NIC, XDP driver/generic mode | earliest drop/forward, NodePort XDP acceleration |
| bpf_host | TC on native device + cilium_host/cilium_net | from/to-host, NodePort on host, host policy |
| bpf_overlay | TC on cilium_vxlan / cilium_geneve | decap, identity lookup, tail into bpf_lxc |
| bpf_lxc | TC on each pod veth (host side) | policy, L4/L7 redirect, service DNAT, encap |
| sock-lb progs | cgroup/connect4, connect6, sendmsg | service translation at connect() time |

The connect()-time socket-LB programs are the quiet win: east-west Service access gets
DNAT'ed inside connect(), so the packet leaves the socket already addressed to a backend
and never touches the Service path at all.

Maps carry the state: a services map (VIP -> backend slot), a global backends map,
reverse-NAT entries, global conntrack maps (CT4/CT6), the ipcache (IP -> security
identity), endpoint maps, and per-endpoint tail-call maps (cilium_calls_lxc_<id>) that
stitch policy fragments onto bpf_lxc. Tail calls exist
because a single program cannot hold the whole pipeline: the kernel caps a tail-call
chain at 32 hops, BPF stack at 512 bytes, and program complexity at 1M instructions
(since kernel 5.2). Cilium's policy engine is literally structured around that budget.

Illustrative excerpt in Cilium BPF style (trimmed; chained via the per-endpoint
`cilium_calls` tail-call map):

```c
/* service decision inside bpf_lxc: hash-map lookup, O(1) */
static __always_inline int lb4_local(struct ip4 *ip4, __u16 dport)
{
    struct lb4_service *svc = lb4_lookup_service(ip4, dport);
    if (!svc)
        return CTX_ACT_OK;                      /* not a Service: pass on */
    if (!lb4_local_get_backend(ip4, svc))       /* pick backend slot */
        return DROP_NO_BACKEND;
    return __lb4_revnat_update(ip4, svc);       /* DNAT + reverse-NAT entry */
}
```

## Packet path, pod to pod across nodes

```text
  node A                                                      node B
  ------                                                      ------
  pod A eth0                                                  pod B eth0
     | veth                                                      ^ veth
     | (TC)                                                      | (TC)
     v                                                          bpf_lxc:
   bpf_lxc:           underlay routing                bpf_overlay:  policy,
     policy           10.0.0.0/16   +------------+    decap VNI/   conntrack
     svc DNAT   ===================> |  fabric    | =>  option,     reply NAT
     encap VXLAN/      (ECMP by     +------------+    identity      tail calls
     Geneve, mark=id   outer flow)        |            from
     |                                    |            overlay
     v (TC, native dev)                   v            |
   bpf_host: forward -> eth0 (uplink)  underlay     bpf_host: receive on uplink
```

First packet from pod A: bpf_lxc runs ingress policy, consults the service map if the
destination is a VIP, DNATs, records conntrack, stamps the mark with the source identity,
and hands the packet to the overlay device, where bpf_overlay encapsulates with the
identity in the option space. Node B runs the mirror image: decap, identity re-derivation
from the ipcache, policy check against the destination's policy map, delivery. Subsequent
packets take the conntrack fast path and skip most decisions.

## Identities, not IPs

Cilium's security model is label-based: the agent hashes a pod's namespace and label
selector set into a numeric security identity; policy rules ("allow from app=frontend to
app=backend:8080") compile into per-endpoint BPF policy maps keyed by that identity, not
by CIDR. Three propagation facts matter:

1. On the node, the source identity rides in the skb mark across the veth hop so the
   second-stage program does not recompute it.
2. Across the overlay, the identity is encoded in the encapsulation metadata: the VXLAN
   reserved field (GBP-style marking) or a Geneve TLV option -- see
   [Geneve Overlay Network](geneve.md) for the option format.
3. For traffic that arrives from outside (host, world, remote pods in native-routing
   mode), bpf programs consult the ipcache map, which the agent keeps in sync: IP prefix
   -> identity. This map is the identity cache in the datapath; the reverse lookup is
   what makes "allow from the production namespace" enforceable against changing pod IPs.

When a pod dies its identity is released; on reuse, stale ipcache entries are the classic
short-window source of surprising allow/deny behavior during rolling deploys.

Policy is L3/L4 in the fast path; L7 (HTTP paths, Kafka topics) is enforced after the
packet is redirected to a node-local Envoy via socket redirection, with the datapath
marking the flow so return traffic bypasses the proxy in the right direction.

```yaml
# CiliumNetworkPolicy: identity-based, L7 aware
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-ingress
  namespace: prod
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
            io.kubernetes.pod.namespace: prod
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          rules:
            http:
              - method: "GET"
                path: "/api/v[0-9]+/items.*"
```

## Hubble: visibility from the datapath

Hubble is a consumer layer on top of events the datapath already produces. Every policy
verdict, drop, and service translation emits a trace/drop notification (with a numeric
drop reason) over a perf/ring buffer to the agent; Hubble renders these as flows (tuple,
verdict, identity pair, optional L7 labels) and Hubble Relay aggregates per-node
observers into one API/UI ([Hubble docs](https://docs.cilium.io/en/stable/observability/hubble/)).
Versus sidecar logging: you see every pod's flows, including traffic dropped *before* it
reached the pod, and the same events export as Prometheus metrics. Cost caveat: flow
records share a ring buffer; under pressure events drop -- the datapath never blocks on
observability.

## Tunnel or native routing

| Mode | Overhead | Identity transport | Notes |
|---|---|---|---|
| VXLAN (UDP 8472) | +50 bytes | reserved-field marking | default; works over any L3 fabric |
| Geneve (UDP 6081) | +~50-70 bytes | TLV option | more option headroom; see geneve.md |
| Native routing | none | mark + ipcache only | requires CNI-consistent node CIDR routing (BGP/cloud routes); identity re-derived from ipcache on the receiver |

MTU is the common deployment bug: pod MTU must leave room for the overlay header
(underlay minus 50 bytes for VXLAN) or you get PMTU blackholes that look like random
timeouts on large packets only.

## Comparisons that come up in interviews

| Axis | kube-proxy iptables | kube-proxy IPVS | Cilium eBPF |
|---|---|---|---|
| Lookup structure | linear chain walk | hash tables | hash maps + tail calls |
| Per-first-packet cost vs Service count | linear | ~flat (lookup) + conntrack | ~flat |
| Ruleset update cost | full table replay per node | incremental but sync loop | map update, per key |
| Conntrack dependency | yes (NAT lives there) | yes | own BPF conntrack maps |
| NetworkPolicy | via another CNI plugin | via another CNI plugin | identity-based, in datapath |
| Observability | counters only | counters only | per-flow (Hubble) |

Against service meshes: classic Istio and Linkerd inject a sidecar proxy per pod -- an
extra hop, an extra process, a per-workload resource tax. Cilium's sidecar-less model
keeps a node-local proxy (Envoy embedded in or beside the agent) and eBPF-redirects L7
traffic through it, with L4 done entirely in the kernel. Istio's ambient mode (GA in
1.24, late 2024) converges on the same shape from the mesh side: a per-node L4 proxy
(ztunnel) plus optional waypoint proxies for L7. What remains is operational (proxy
lifecycle ownership, mTLS story, protocol breadth), not architectural.

## Failure modes

- Conntrack maps sized for yesterday's traffic: a full BPF conntrack map forces
  create-drops (lookup falls off the fast path); watch cilium's map pressure metrics.
- Tail-call/complexity budget regressions: some kernel versions silently cap differently;
  a feature (fragments, L7) that pushes bpf_lxc over budget fails to load on upgrade.
- MTU mismatch after enabling WireGuard on top of VXLAN -- large-packet-only symptoms.
- Fragmented packets need explicit handling (fragment tracking is a datapath feature, not
  free); NodePort on fragments historically misroutes when it is off.
- Identity churn: mass pod churn can exhaust the identity allocator or leave stale
  ipcache prefixes; rolling-deploy policy denies are usually this, not the rules.
- kube-proxy replacement migration: leftover kube-proxy rules double-NAT traffic; the
  documented cutover requires removing kube-proxy first
  ([kubeproxy-free guide](https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/)).

## References

- [Cilium docs: Kubernetes without kube-proxy](https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/)
- [Isovalent: What is kube-proxy and why move from iptables to eBPF?](https://isovalent.com/blog/post/why-replace-iptables-with-ebpf/)
- [Cilium 2021 CNI benchmark (bare metal, 100 Gbit/s)](https://cilium.io/blog/2021/05/11/cni-benchmark/)
- [Cilium docs: Hubble observability](https://docs.cilium.io/en/stable/observability/hubble/)
- [eBPF.io: introduction to eBPF](https://ebpf.io/)
