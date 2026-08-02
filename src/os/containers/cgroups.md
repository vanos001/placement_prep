# Cgroups (Control Groups)

## Overview

**Cgroups (Control Groups)** is a Linux kernel feature that organizes processes into hierarchical groups and applies resource limits, accounting, and control to those groups. Cgroups are one of the two foundational technologies behind containers (the other being namespaces).

## Motivation

Without cgroups, a single process can consume all CPU, memory, disk I/O, and network bandwidth, starving other processes. Cgroups provide:

1. **Resource limiting**: Cap CPU, memory, I/O for a group of processes
2. **Accounting**: Track resource usage per group
3. **Prioritization**: Allocate more resources to critical workloads
4. **Control**: Freeze/throttle/kill groups of processes

```
Without cgroups:
  Process A: uses 100% CPU → Process B gets 0%
  Process C: leaks memory → OOM killer kills random process

With cgroups:
  Group 1 (A): CPU limit 50%, memory limit 1GB
  Group 2 (B): CPU limit 50%, memory limit 1GB
  → A can't starve B, C can't consume all memory
```

## Cgroup Versions

### Cgroups v1

```
┌──────────────────────────────────────────────────────────────┐
│  Cgroups v1 Architecture                                     │
│                                                              │
│  Each resource controller has its own hierarchy:             │
│                                                              │
│  /sys/fs/cgroup/cpu/         (CPU controller)                │
│  ├── group_a/                cpu.shares = 512                │
│  └── group_b/                cpu.shares = 512                │
│                                                              │
│  /sys/fs/cgroup/memory/      (Memory controller)             │
│  ├── group_a/                memory.limit_in_bytes = 1G     │
│  └── group_b/                memory.limit_in_bytes = 2G     │
│                                                              │
│  ⚠ Problem: Hierarchies are independent!                     │
│  group_a in CPU hierarchy ≠ group_a in memory hierarchy      │
│  Process can be in different positions in different trees     │
└──────────────────────────────────────────────────────────────┘
```

### Cgroups v2 (Unified Hierarchy)

```
┌──────────────────────────────────────────────────────────────┐
│  Cgroups v2 Architecture                                     │
│                                                              │
│  Single unified hierarchy for ALL controllers:               │
│                                                              │
│  /sys/fs/cgroup/                                             │
│  ├── cgroup.controllers  (cpu memory io pids)                │
│  ├── cgroup.subtree_control                                │
│  ├── workload_a/                                             │
│  │   ├── cpu.max        = "50000 100000"   (50% CPU)        │
│  │   ├── memory.max     = 1073741824       (1GB)            │
│  │   ├── io.max         = "8:0 rbps=104857600"              │
│  │   ├── pids.max       = 100                               │
│  │   └── cgroup.procs   (list of PIDs)                      │
│  └── workload_b/                                             │
│      ├── cpu.max        = "50000 100000"                    │
│      ├── memory.max     = 2147483648                        │
│      └── cgroup.procs                                       │
│                                                              │
│  ✓ Single hierarchy — process position is consistent         │
│  ✓ Better delegation model                                   │
│  ✓ Pressure Stall Information (PSI)                         │
└──────────────────────────────────────────────────────────────┘
```

## Resource Controllers

### CPU Controller

```bash
# Cgroups v2

# Create a cgroup
sudo mkdir /sys/fs/cgroup/mygroup

# Set CPU limit (50% of one CPU, period = 100ms)
echo "50000 100000" | sudo tee /sys/fs/cgroup/mygroup/cpu.max

# Add process to cgroup
echo $PID | sudo tee /sys/fs/cgroup/mygroup/cgroup.procs

# CPU weight (relative priority, default 100)
echo 200 | sudo tee /sys/fs/cgroup/mygroup/cpu.weight

# CPU affinity (which cores)
echo "0-3" | sudo tee /sys/fs/cgroup/mygroup/cpuset.cpus
```

```
cpu.max format: $MAX $PERIOD
  $MAX: microseconds of CPU time per period
  $PERIOD: period length in microseconds (default 100000 = 100ms)

  "50000 100000" = 50% of one CPU core
  "100000 100000" = 100% of one CPU core
  "200000 100000" = 200% = two full CPU cores
  "max 100000" = unlimited
```

### Memory Controller

```bash
# Set memory limit (1GB)
echo 1073741824 | sudo tee /sys/fs/cgroup/mygroup/memory.max

# Set soft limit (memory.high — triggers reclaim, not OOM)
echo 858993459 | sudo tee /sys/fs/cgroup/mygroup/memory.high

# Set swap limit
echo 2147483648 | sudo tee /sys/fs/cgroup/mygroup/memory.swap.max

# View memory usage
cat /sys/fs/cgroup/mygroup/memory.current
cat /sys/fs/cgroup/mygroup/memory.stat

# OOM group kill (kill whole cgroup, not individual process)
echo 1 | sudo tee /sys/fs/cgroup/mygroup/memory.oom.group
```

```
Memory limits behavior:
  memory.low:  "protected" memory — kernel tries not to reclaim below this
  memory.high: Throttle limit — processes slowed down (reclaim pressure)
  memory.max:  Hard limit — OOM killer activates if exceeded
  memory.swap.max: Swap usage limit

  memory.low < memory.high < memory.max

  Process behavior at limits:
  < memory.low:   Normal operation
  > memory.high:  Processes throttled (slowed down)
  > memory.max:   OOM killer invoked
```

### I/O Controller

```bash
# Set I/O limits (bytes per second)
# Format: major:minor rbps= wbps= riops= wiops=
echo "8:0 rbps=104857600 wbps=52428800" | \
    sudo tee /sys/fs/cgroup/mygroup/io.max

# I/O weight (relative priority, default 100)
echo 200 | sudo tee /sys/fs/cgroup/mygroup/io.weight

# View I/O usage
cat /sys/fs/cgroup/mygroup/io.stat
# 8:0 rbytes=1234567 wbytes=7654321
```

### PID Controller

```bash
# Limit number of processes (prevent fork bombs)
echo 100 | sudo tee /sys/fs/cgroup/mygroup/pids.max

# View current PID count
cat /sys/fs/cgroup/mygroup/pids.current
```

## Real-World Examples

### systemd and Cgroups

```bash
# systemd uses cgroups to manage services
# Each service gets its own cgroup

# View service cgroup
systemctl status nginx
# CGroup: /system.slice/nginx.service
#         └─1234 nginx: master process

# Set resource limits for a service
sudo systemctl set-property nginx.service CPUQuota=50%
sudo systemctl set-property nginx.service MemoryMax=1G

# Or in the unit file:
# [Service]
# CPUQuota=50%
# MemoryMax=1G
# IOWeight=200
# TasksMax=100

# View all cgroup hierarchies
systemd-cgls
systemd-cgtop
```

### Docker and Cgroups

```bash
# Docker creates cgroups for each container

# Limit CPU
docker run --cpus="1.5" myimage          # Max 1.5 CPU cores
docker run --cpu-shares=512 myimage      # Relative weight

# Limit memory
docker run --memory=1g myimage           # Hard limit
docker run --memory=1g --memory-swap=2g myimage  # With swap

# Limit I/O
docker run --device-read-bps /dev/sda:10mb myimage
docker run --blkio-weight=200 myimage

# View container cgroup
docker inspect --format '{{.State.Pid}}' mycontainer
cat /sys/fs/cgroup/docker/<container-id>/memory.max
```

### Kubernetes Resource Management

```yaml
# Pod resource specification
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: myapp
    image: myimage
    resources:
      requests:        # Guaranteed resources (memory.low, cpu shares)
        cpu: "500m"    # 0.5 CPU core
        memory: "256Mi"
      limits:          # Maximum resources (memory.max, cpu.max)
        cpu: "1"       # 1 CPU core
        memory: "512Mi"
```

```
Kubernetes → Cgroup mapping:

requests.cpu → cpu.weight (relative shares)
limits.cpu → cpu.max (hard limit)
requests.memory → memory.low (soft protection)
limits.memory → memory.max (hard limit)

QoS Classes:
  Guaranteed: requests == limits for all resources
  Burstable:  requests < limits
  BestEffort: no requests or limits

OOM Priority:
  BestEffort killed first → Burstable → Guaranteed killed last
```

## Cgroup Namespace

```bash
# Cgroup namespace hides the real cgroup path from processes
# Container sees / as the root of its cgroup tree

# Without cgroup namespace:
cat /proc/self/cgroup
# 0::/system.slice/docker-abc123.scope

# With cgroup namespace:
cat /proc/self/cgroup
# 0::/
# (container thinks it's at the root)

# Linux 4.6+ supports cgroup namespaces
unshare --cgroup bash
```

## Interview Questions

### Beginner

**Q: What are cgroups and why are they important?**
A: Cgroups (Control Groups) is a Linux kernel feature that groups processes and applies resource limits — CPU, memory, I/O, and process count. They're important because they prevent any single process or group from consuming all system resources, enabling fair resource sharing and isolation between workloads. They're a foundational technology for containers.

**Q: What is the difference between cgroups v1 and v2?**
A: Cgroups v1 has separate hierarchies for each resource controller, which is complex and inconsistent. Cgroups v2 uses a single unified hierarchy where all controllers are managed together. V2 also adds features like Pressure Stall Information (PSI), better delegation, and a cleaner interface. Most modern distributions use v2 by default.

### Intermediate

**Q: Explain the difference between `cpu.max` and `cpu.weight` in cgroups v2.**
A:
- **cpu.max**: A hard CPU limit. `"50000 100000"` means the cgroup gets at most 50ms of CPU time per 100ms period (50% of one core). Exceeding this causes throttling.
- **cpu.weight**: A relative priority. Default is 100. If two cgroups have weights 200 and 100, the first gets 2/3 of CPU when there's contention, and the second gets 1/3. No hard limit — a cgroup can use more CPU if it's available.

Use `cpu.max` for strict isolation; use `cpu.weight` for fair sharing with burst capability.

**Q: How does the OOM killer interact with cgroups?**
A: When a cgroup exceeds its `memory.max` limit, the kernel invokes the OOM killer to kill processes within that cgroup. With `memory.oom.group = 1`, all processes in the cgroup are killed (container-style behavior). The OOM killer selects the process with the highest `oom_score` (usually the one using the most memory). Kubernetes sets `oom_score_adj` based on QoS class to control kill priority.

### FAANG-Level

**Q: Design a resource isolation strategy for a multi-tenant Kubernetes cluster where tenants have different QoS requirements (production, staging, batch jobs).**

A:

```
Design: Hierarchical Cgroup Structure with QoS Tiers

/sys/fs/cgroup/kubepods/
├── production/                    # Guaranteed QoS
│   ├── pod-frontend/
│   │   └── container-nginx/
│   │       ├── cpu.max: "200000 100000"  (2 cores guaranteed)
│   │       ├── cpu.weight: 200           (high priority)
│   │       ├── memory.max: 2G
│   │       ├── memory.low: 1.5G          (protected)
│   │       └── io.weight: 200            (high I/O priority)
│   └── pod-database/
│       ├── cpu.max: "400000 100000"      (4 cores)
│       ├── memory.max: 8G
│       └── memory.low: 6G
│
├── staging/                       # Burstable QoS
│   ├── pod-test-app/
│   │   ├── cpu.max: "100000 100000"      (1 core max)
│   │   ├── cpu.weight: 100               (normal priority)
│   │   ├── memory.max: 1G
│   │   └── memory.low: 256M              (minimal protection)
│   └── ...
│
└── batch/                         # BestEffort QoS
    ├── pod-training-job/
    │   ├── cpu.max: "max 100000"         (unlimited when available)
    │   ├── cpu.weight: 50                (low priority)
    │   ├── memory.max: 16G
    │   └── memory.low: 0                 (no protection)
    └── ...

Resource Allocation Strategy:
1. CPU: production gets 70% guaranteed, staging 20%, batch 10%
   - Use cpu.weight for relative sharing
   - Use cpu.max for hard limits
   - Batch jobs use "max" — can burst when production is idle

2. Memory:
   - Production: memory.low = 80% of limit (protected)
   - Staging: memory.low = 25% of limit (some protection)
   - Batch: memory.low = 0 (can be reclaimed)
   
   When memory pressure occurs:
   → Batch processes throttled/reclaimed first
   → Staging processes throttled next
   → Production processes protected until their memory.low

3. I/O:
   - Production: io.weight = 200 (high priority)
   - Staging: io.weight = 100 (normal)
   - Batch: io.weight = 50 (low priority)

4. Eviction priority:
   - OOM score: batch > staging > production
   - Kubernetes preemption: batch pods preempted first
   - Node pressure: batch pods evicted first

5. Monitoring:
   - PSI (Pressure Stall Information) for each cgroup
   - Alert when production cgroups show memory pressure
   - Track CPU throttling percentage

Implementation:
- Kubernetes LimitRange for defaults
- ResourceQuota per namespace
- PriorityClass for preemption
- PodDisruptionBudget for availability
```

**Q: A container is experiencing memory pressure but its memory usage is well below the limit. What cgroup knobs would you investigate?**

A:

```
Possible causes and cgroup diagnostics:

1. memory.high (soft limit):
   - If memory.high is set, the kernel throttles processes approaching it
   - Even below memory.max, being above memory.high causes reclaim pressure
   - Fix: raise memory.high or remove it

2. Kernel memory (memory.current includes kernel):
   - memory.current = user memory + kernel memory (slab, page tables, etc.)
   - A container with many files open may use lots of kernel memory
   - Check: memory.stat → "slab" "sock" "file" entries
   - Fix: limit file descriptors, reduce mmap usage

3. Cgroup-wide vs per-process pressure:
   - memory.pressure shows PSI metrics
   - High "some" percentage = some processes stalled
   - High "full" percentage = ALL processes stalled
   - Investigate which process is the memory hog

4. Swap usage:
   - memory.swap.current — if swap is active, performance degrades
   - memory.swap.max = 0 to disable swap entirely
   - Swapping causes "memory pressure" even below limits

5. Memory.low too low:
   - If memory.low is very low, kernel may reclaim container's memory
   - Under global memory pressure, kernel reclaims unprotected memory first
   - Fix: set memory.low to a reasonable protection level

6. Parent cgroup limits:
   - Check if parent cgroup has limits that are more restrictive
   - Container's effective limit = min(self, parent)

Diagnostic commands:
  cat /sys/fs/cgroup/<container>/memory.current
  cat /sys/fs/cgroup/<container>/memory.high
  cat /sys/fs/cgroup/<container>/memory.max
  cat /sys/fs/cgroup/<container>/memory.stat
  cat /sys/fs/cgroup/<container>/memory.pressure
  cat /sys/fs/cgroup/<container>/memory.swap.current
```

## Common Mistakes

1. **Confusing v1 and v2 paths**: `/sys/fs/cgroup/cpu/` is v1; `/sys/fs/cgroup/<group>/cpu.max` is v2. Check which version your system uses.
2. **Not setting memory.low**: Without a soft limit, the kernel may reclaim container memory under global pressure, even if the container has plenty.
3. **Using cpu.shares (v1) with cpu.weight (v2)**: These are different mechanisms. Don't mix v1 and v2.
4. **Forgetting about kernel memory**: `memory.current` includes kernel memory (slab, page tables). A container may hit its limit due to kernel memory, not user memory.
5. **Not accounting for child cgroups**: Parent cgroup limits apply to the sum of all children. If parent has 4GB and 5 children each request 2GB, they can't all get their limit.

## Summary

| Controller | Resource | Key File | Description |
|-----------|----------|----------|-------------|
| cpu | CPU time | cpu.max, cpu.weight | Limit/prioritize CPU |
| memory | RAM + swap | memory.max, memory.low | Limit memory |
| io | Disk I/O | io.max, io.weight | Limit disk bandwidth |
| pids | Process count | pids.max | Prevent fork bombs |
| cpuset | CPU/memory nodes | cpuset.cpus, cpuset.mems | NUMA pinning |
| hugetlb | Huge pages | hugetlb.max | Limit huge page usage |

## Cross-References

- [Namespaces](namespaces.md) — Isolation (complementary to cgroups)
- [Docker](docker.md) — Docker's use of cgroups
- [Kubernetes](kubernetes.md) — Kubernetes resource management
- [Security: Access Control](../security/access-control.md) — Resource access control


## Cross References

- [Namespaces](namespaces.md)
- [Docker](docker.md)
- [Scheduling](../scheduling/README.md)
- [Resource Management](../memory/numa.md)
