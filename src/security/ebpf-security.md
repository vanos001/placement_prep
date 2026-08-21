# eBPF for Security

eBPF (extended Berkeley Packet Filter) has become a cornerstone of modern Linux security tooling. By allowing kernel-attached programs to observe and enforce policy on system calls, network packets, and kernel state, eBPF enables security tools that are non-invasive (no kernel patches), low-overhead (in-kernel execution), and flexible (program updates without restarts). This page covers the eBPF security use cases (syscall filtering, LSM hooking, network observability), the production tools (Falco, Tetragon, Tracee), and the operational considerations.

## The Three Layers of eBPF Security

```text
┌─────────────────────────────────────────────────────────────────┐
│  Network layer (XDP, TC, cgroup/skb)                            │
│  - DDoS mitigation                                              │
│  - L7 firewall                                                  │
│  - Service mesh security (Cilium, Istio Ambient)                │
└─────────────────────────────────────────────────────────────────┘
        │
┌─────────────────────────────────────────────────────────────────┐
│  Syscall layer (tracepoints, kprobes)                           │
│  - Syscall auditing                                              │
│  - Process lineage tracking                                     │
│  - Container escape detection                                   │
└─────────────────────────────────────────────────────────────────┘
        │
┌─────────────────────────────────────────────────────────────────┐
│  LSM layer (BPF-LSM)                                            │
│  - File access policy enforcement                              │
│  - Process capability control                                   │
│  - Kernel function access control                              │
└─────────────────────────────────────────────────────────────────┘
```

## Network Layer Security

### XDP for DDoS Mitigation

XDP (eXpress Data Path) programs run at the NIC driver level, before packets enter the kernel's network stack. They can drop packets before they allocate any kernel memory:

```c
SEC("xdp")
int drop_ddos(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_DROP;
    
    if (eth->h_proto == bpf_htons(ETH_P_IP)) {
        struct iphdr *ip = (void *)(eth + 1);
        if ((void *)(ip + 1) > data_end) return XDP_DROP;
        
        // Drop packets from known-bad IPs
        __u32 src = ip->saddr;
        if (is_blacklisted(src)) {
            return XDP_DROP;
        }
    }
    return XDP_PASS;
}
```

XDP achieves ~24 million packet drops per second on a single CPU core (Cloudflare's published numbers). Compare with iptables (which runs after skb allocation): ~500K drops/sec.

### tc-BPF for L7 Firewall

`tc-BPF` runs in the kernel's traffic control layer (after skb allocation but before protocol stack). It can examine the full L3-L7 packet and enforce policy:

```c
SEC("classifier")
int http_filter(struct __sk_buff *skb) {
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    
    // Parse to HTTP layer
    struct ethhdr *eth = data;
    // ... parse IP, TCP, HTTP ...
    
    // Drop requests to /admin from non-internal IPs
    if (is_admin_path(http_path) && !is_internal_ip(src_ip)) {
        return TC_ACT_SHOT;  // drop
    }
    return TC_ACT_OK;  // allow
}
```

This is the foundation of Cilium's L7 network policy and Envoy's "ambient mesh" mode.

## Syscall Layer Security

### Syscall Auditing (Falco)

Falco (CNCF graduated project) uses eBPF to observe syscalls and alert on suspicious patterns:

```text
Suspicious: a shell spawned by a web server process.
  → Falco rule: "Shell spawned by HTTP server"
  
  Condition: proc.name in (shell_binaries) and 
             proc.pname in (apache, nginx, httpd)

Suspicious: a write to /etc/passwd.
  → Falco rule: "Write to /etc/passwd"

Suspicious: a network connection to a known-bad IP.
  → Falco rule: "Outbound connection to blacklist IP"
```

Falco's rules engine uses eBPF to capture every syscall, then evaluates against a YAML rule file. The rules engine is in user space; the syscall capture is in kernel.

The throughput: ~500K syscalls/sec observed on a busy server, ~10 ms added latency per syscall.

### Process Lineage (Tetragon)

Tetragon (Isovalent, 2022) tracks process ancestry: every process's parent, its parent, etc. This is critical for forensics:

```text
Process tree:
  systemd → kubelet → containerd-shim → runc → nginx
                                                    ↓
                                                  shell (compromised!)

Tetragon alert: shell process has ancestor nginx (not allowed).
```

Tetragon's eBPF program records every `execve` (process spawn) in a kernel ring buffer; the user-space agent reads the buffer and applies policy.

## LSM Layer Security

### BPF-LSM

Linux 5.7 (2020) added BPF-LSM: eBPF programs that attach to Linux Security Module hooks. These hooks fire on security-sensitive operations:

```c
SEC("lsm/bprm_check_security")
int enforce_binary_policy(struct linux_binprm *bprm) {
    // Check if the binary is in the allowlist
    if (!is_allowlisted(bprm->filename)) {
        return -EPERM;  // block execution
    }
    return 0;
}
```

The BPF-LSM hooks include:
- `bprm_check_security`: before a binary is executed.
- `file_open_security`: before a file is opened.
- `socket_create_security`: before a socket is created.
- `task_setuid`: before a process changes UID.

These hooks were previously only accessible to AppArmor, SELinux, or custom LSM modules. With BPF-LSM, custom policies can be loaded at runtime.

## Production Tools

### Falco

Falco is the most widely deployed eBPF security tool. It ships with ~150 default rules covering common attacks:
- Shell spawned by web servers.
- Writes to system binaries.
- Reverse shells.
- Privilege escalations.
- Container escapes.

Falco runs as a daemonset in Kubernetes; alerts are sent to Prometheus, Slack, or a SIEM.

### Tetragon

Tetragon (Isovalent) is more focused than Falco: it enforces policy in-kernel (not just observes). A Tetragon policy can block an operation in real-time:

```yaml
apiVersion: cilium.io/v1
kind: TracingPolicy
metadata:
  name: block-shell-from-nginx
spec:
  kprobes:
  - call: "sys_execve"
      syscall: true
      args:
      - index: 0
        type: "string"
  matchActions:
  - action: Sigkill
    # If nginx tries to exec a shell, kill the process
```

Tetragon is the basis of Cilium's runtime security feature.

### Tracee

Tracee (Aqua Security) is similar to Falco but focuses on raw event capture for forensics. It's used for IR (incident response) — capturing every syscall during an attack.

### Pixie

Pixie (New Relic) uses eBPF for application observability — not strictly security, but related. It traces HTTP requests in microservices without code changes.

## Operational Considerations

1. **CPU overhead**: eBPF programs run on every event they observe. A syscall observer adds ~100 ns per syscall. On a busy server doing 100K syscalls/sec, that's 10 ms/sec of CPU (1%).

2. **Memory overhead**: eBPF maps (the data structures programs read/write) take kernel memory. A large rule set in Falco can use 100+ MB.

3. **Kernel version compatibility**: eBPF features are added with each kernel release. BPF-LSM requires 5.7+; CO-RE requires 5.4+; XDP requires 4.8+. Match the kernel version to the feature requirements.

4. **Privilege**: eBPF programs require `CAP_BPF` or `CAP_SYS_ADMIN`. In containerized environments, this means the security tool runs as a privileged pod.

5. **Program stability**: an eBPF program that loops or crashes can hang the kernel. The verifier prevents most issues, but production programs must be tested carefully.

## Common Pitfalls

1. **Trusting the eBPF verifier.** The verifier catches most bugs but not all. A program that loops on a specific input can hang the kernel. Test on staging.

2. **Forgetting that BPF-LSM is opt-in.** The kernel config must have `CONFIG_BPF_LSM=y` and the kernel command line must have `lsm=...,bpf`. Without this, BPF-LSM programs don't attach.

3. **Forgetting that eBPF programs are kernel-version-dependent.** A program written for kernel 5.15 may not run on 5.10. Use CO-RE (Compile Once, Run Everywhere) or target a specific kernel version.

4. **Forgetting that Falco's rules can have false positives.** A rule like "shell spawned by web server" can fire on legitimate dev tools. Tune rules before deploying to production.

5. **Forgetting that BPF programs can be unloaded.** An attacker who compromises root can unload eBPF security programs. Monitor for BPF program loads/unloads.

6. **Forgetting that eBPF doesn't see into other containers' view of the network.** A program in the host network namespace sees all traffic; in a pod's namespace, only that pod's traffic. Use `cgroup/skb` for per-container visibility.

## References

- [BPF Compiler Collection (BCC)](https://github.com/iovisor/bcc)
- [Falco documentation](https://falco.org/docs/)
- [Tetragon documentation](https://tetragon.io/docs/)
- [Tracee documentation](https://aquasecurity.github.io/tracee/latest/)
- [Cilium: eBPF-based security](https://docs.cilium.io/en/stable/security/)
- [BPF-LSM documentation](https://docs.kernel.org/bpf/bpf_lsm.html)
- Daniel Borkmann, "[BPF: The future of Linux networking](https://netdevconf.info/0x15/session.html?borkmann-bpf)" (Netdev 0x15)
- [LWN: eBPF for security (2021)](https://lwn.net/Articles/850489/)
