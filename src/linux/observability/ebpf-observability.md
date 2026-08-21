# eBPF for Observability

eBPF (extended Berkeley Packet Filter) has become the foundation of modern Linux observability tooling. By attaching programs to kernel hook points (syscalls, tracepoints, kprobes, network events), eBPF enables zero-instrumentation observability of any application — without code changes, recompilation, or restarts. This page covers the observability use cases (CPU profiling, syscall tracing, network analysis, file access), the production tools (bcc, bpftrace, Pixie, Parca), and the comparison to traditional profilers.

## The Three Layers of eBPF Observability

```text
┌─────────────────────────────────────────────────────────────┐
│  Profiling layer (CPU samples, off-CPU, lock contention)    │
│  - Profile: where is CPU time spent?                          │
│  - Off-CPU: where is wait time spent?                        │
│  - Lock: which locks cause contention?                       │
└─────────────────────────────────────────────────────────────┘
        │
┌─────────────────────────────────────────────────────────────┐
│  Syscall layer (what is the application doing?)              │
│  - File access: which files are read/written?                │
│  - Network: which sockets are opened/closed?                  │
│  - Process: which processes are spawned?                      │
└─────────────────────────────────────────────────────────────┘
        │
┌─────────────────────────────────────────────────────────────┐
│  Network layer (packet-level analysis)                       │
│  - TCP retransmits: which connections are unreliable?        │
│  - Latency: per-connection RTT                              │
│  - Throughput: per-flow byte counts                          │
└─────────────────────────────────────────────────────────────┘
```

## CPU Profiling with eBPF

```bash
# Profile at 999 Hz, capture user+kernel stacks
bpftrace -e 'profile:hz:999 { @[ustack, kstack] = count(); }' -p <pid> | flamegraph.pl > cpu.svg

# Or with perf (which uses eBPF on modern kernels)
perf record -F 999 -p <pid> -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu.svg
```

eBPF's advantage over traditional profilers (gprof, oprofile): it can sample both user and kernel stacks simultaneously, with low overhead (~1% CPU).

## Off-CPU Profiling with eBPF

Off-CPU profiling captures time the process spent blocked (waiting for I/O, locks, sleep):

```bash
# Trace sched_switch (when the task goes off-CPU)
bpftrace -e '
tracepoint:sched:sched_switch {
  if (args->prev_pid == <pid>) {
    @[ustack] = count();
  }
}
' -p <pid> | flamegraph.pl > off-cpu.svg
```

For I/O-bound workloads, off-CPU profiling reveals the actual bottleneck (database wait, file I/O, network round-trip) — the on-CPU time is just noise.

## Syscall Tracing

```bash
# Count syscalls per process
bpftrace -e 'tracepoint:syscalls:sys_enter_* { @[probe, comm] = count(); }' -p <pid>

# Trace file opens
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s opens %s\n", comm, str(args->filename)); }'

# Trace TCP connections
bpftrace -e 'tracepoint:syscalls:sys_enter_connect { @[comm] = count(); }'
```

The output is immediately actionable — you can see exactly which files the application opens, which connections it makes, and which syscalls dominate.

## Network Analysis

```bash
# Trace TCP retransmits per connection
bpftrace -e 'tracepoint:tcp:tcp_retransmit_skb { @[skaddr->inet_saddr, skaddr->inet_daddr] = count(); }'

# Trace per-connection RTT
bpftrace -e 'tracepoint:tcp:tcp_probe { @[skaddr->inet_saddr, skaddr->inet_daddr] = avg(args->srtt); }'

# Trace HTTP requests (via socket-level inspection)
bcc$ share/bcc/tools/http_trace.py
```

Network observability via eBPF reveals issues that traditional monitoring (Prometheus, dashboards) can't see — per-connection RTT, retransmit causes, application-layer latency.

## Continuous Profiling Tools

### Pixie

Pixie (developed by New Relic, open-sourced 2020) is a continuous profiling tool for Kubernetes:

```text
Pixie agent on each node:
  - Uses eBPF to profile all pods on the node.
  - Captures HTTP requests, CPU profiles, network stats.
  - Streams data to Pixie Cloud (or self-hosted backend).

No code changes needed; the agent sees all traffic automatically.
```

Pixie's HTTP tracing reveals per-endpoint latency for all services on a node — useful for finding slow dependencies.

### Parca

Parca (open-sourced 2022) is a continuous profiling agent:

```text
Parca agent on each node:
  - Uses eBPF to sample all processes.
  - Stores profiles in Parca server (S3-backed).
  - Visualizes as flame graphs over time.

Supports multiple languages (C, C++, Go, Rust, Java, Python).
```

Parca focuses on CPU and off-CPU profiles; it doesn't do HTTP tracing like Pixie.

### Pyroscope

Pyroscope (acquired by Grafana 2022) is another continuous profiler:

```text
Pyroscope agent:
  - Integrates with Go, Java, Python, Ruby, .NET, Rust.
  - Some languages use eBPF (Go, Rust); others use language-specific SDKs (Java, Python).
  - Stores profiles in Pyroscope server.
```

Pyroscope is more language-aware than Parca but less eBPF-universal.

### Vector and BCC

For low-level observability:

```bash
# Vector (Rust-based agent) with eBPF integration
vector --config vector.toml
# Can capture system metrics, network stats, file events

# BCC (BPF Compiler Collection) tools
bcc$ ls /usr/share/bcc/tools
bashreadline    biolatency    btrfsdist    ... 100+ tools
```

BCC provides 100+ pre-built tools for specific observability tasks (per-process I/O, per-socket retransmits, syscall latency).

## Production Deployment

### Kubernetes DaemonSet Pattern

For eBPF observability in a K8s cluster:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: parca-agent
spec:
  template:
    spec:
      hostPID: true  # required to see all processes on the host
      hostNetwork: true  # required for network observability
      containers:
        - name: parca-agent
          image: ghcr.io/parca-dev/parca-agent:latest
          securityContext:
            privileged: true  # or specific capabilities
          args:
            - --node=$(NODE_NAME)
            - --remote-store-address=parca-server:7070
```

The agent runs on every node, observes all pods, and sends profiles to a central server.

### Required Capabilities

For eBPF observability, the agent needs:
- `CAP_BPF` (load BPF programs)
- `CAP_PERFMON` (read perf events)
- `CAP_SYS_PTRACE` (read /proc/<pid>/ for stack walking)
- Host PID and host network namespaces

For security-conscious deployments, use a `securityContext` with specific capabilities instead of `privileged: true`.

## Production Use Cases

### Performance Regression Detection

Continuous profiling lets you compare profiles before and after a deployment:

```bash
# Query Parca for profiles from before and after the deploy
parca-cli query --label deployment=v1 --from 1h | flamegraph.pl > before.svg
parca-cli query --label deployment=v2 --from 1h | flamegraph.pl > after.svg
```

The diff shows which functions got slower.

### Hot Path Identification at Scale

For a microservices deployment with 100 services, eBPF profiles all of them simultaneously:

```text
Pixie dashboard shows:
  - Top 10 services by CPU usage.
  - Top 10 endpoints by latency.
  - Top 10 HTTP errors by count.
```

Without eBPF, you'd need to add a profiler to each service (with language-specific instrumentation).

### Network Bottleneck Detection

For a slow service:
- Check the off-CPU profile: is the bottleneck in the application or in network I/O?
- Check the per-connection RTT: is one remote service slow?
- Check the retransmit count: is the network reliable?

## Comparison to Traditional Profilers

| Aspect | eBPF | gprof (C) | JFR (Java) | Py-spy (Python) |
|--------|------|-----------|-------------|-----------------|
| Instrumentation | Zero (kernel attaches) | Compile-time | JVM hook | Sampling via ptrace |
| Languages | All (stack walks) | C/C++ only | Java only | Python only |
| Kernel + user | Both | User only | User only | User only |
| Overhead | <1% | 5-10% | <1% | 1-5% |
| Production | Yes | No (compile-time) | Yes | Yes |

eBPF's advantage: language-agnostic, kernel-aware, low overhead. The disadvantage: requires Linux and specific capabilities.

## Common Pitfalls

1. **Forgetting that eBPF needs CAP_BPF or root.** Without these, programs can't load. Use a securityContext with the capabilities, or `--privileged` (less secure).

2. **Forgetting that some kernels don't have BPF features.** BPF-LSM requires 5.7+; BTF (for CO-RE) requires 5.4+. Match the agent version to the kernel.

3. **Forgetting that frame pointers are needed for stack walking.** Many distributions compile without frame pointers; eBPF stack walking is unreliable. Either compile with `-fno-omit-frame-pointer` or use DWARF-based unwinding (slower).

4. **Forgetting that continuous profiling can generate huge data.** A 1000-pod cluster with 999 Hz sampling generates GBs of profiles per day. Use sampling (10 Hz) for storage efficiency.

5. **Forgetting that eBPF programs are kernel-version-dependent.** A program written for 5.15 may not run on 5.10. Use CO-RE (Compile Once, Run Everywhere) for portability.

6. **Forgetting that continuous profiling tools have their own overhead.** Parca and Pixie each add ~1-5% CPU. Don't run multiple profilers on the same node.

## References

- Brendan Gregg, "[BPF Performance Tools](http://www.brendangregg.com/bpf-performance-tools-book.html)" (Addison-Wesley 2019)
- [BCC (BPF Compiler Collection)](https://github.com/iovisor/bcc)
- [bpftrace documentation](https://github.com/iovisor/bpftrace)
- [Pixie: continuous profiling](https://github.com/pixie-io/pixie)
- [Parca: continuous profiling](https://github.com/parca-dev/parca)
- [Pyroscope: continuous profiling](https://github.com/grafana/pyroscope)
- [eBPF observability tutorials](https://github.com/iovisor/bpftrace/tree/master/tools)
- [LWN: eBPF for observability (2021)](https://lwn.net/Articles/853299/)
