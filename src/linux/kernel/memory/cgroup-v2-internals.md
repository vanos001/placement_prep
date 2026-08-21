# cgroup v2

`cgroup v2` is the unified control group hierarchy introduced in kernel 4.5.0 (2016) and declared the default in kernel 5.10 (2020). It replaces the multiple parallel hierarchies of v1 with a single tree, adds explicit support for `systemd`-managed units, and standardizes the controller set under a uniform `control_type.events` interface. This page covers the v2 model, the controllers, the file protocol, and the v1-to-v2 migration that production services must handle.

## Why v2: The Problems of v1

cgroup v1 (Linux 2.6.24, 2008) allowed each controller (`memory`, `cpu`, `blkio`, `net_cls`, `devices`, ...) to be mounted on its own hierarchy. The result was:

- A process could be in `/cgroup/cpu/group_a` and `/cgroup/memory/group_b` simultaneously, making it impossible to reason about resource ownership.
- `systemd` had to coordinate multiple mounts and could not reliably assign a unit's tasks to a consistent group across controllers.
- Tasks had to be moved via per-thread `tasks` files, with no atomic move across controllers.
- Controllers had inconsistent APIs: `memory.usage_in_bytes` vs `cpu.stat` vs `blkio.throttle.io_serviced`.

v2 makes the hierarchy the single source of truth. A process is in exactly one cgroup at each level of the tree. Controllers are enabled per-cgroup with `cgroup.subtree_control` and apply uniformly to all descendants.

## The Single Hierarchy

```text
                              cgroup v2 root
                                  │
        ┌─────────────────────────┼───────────────────────────┐
        │                         │                           │
    user.slice              system.slice                machine.slice
    (user sessions)         (systemd units)             (VMs, containers)
        │                         │                           │
   user-1000.slice         nginx.service           machine-libvirt.scope
        │                         │                           │
   user@1000.service       /worker-{1,2,3}.service     qemu-vm-1
```

Each cgroup has the same set of files. Controllers are enabled selectively at each level via:

```bash
# Enable memory and cpu for all descendants of /system.slice
echo +memory +cpu > /sys/fs/cgroup/system.slice/cgroup.subtree_control
```

The set of controllers enabled at a level determines which files exist in the cgroup's children. A cgroup with no controllers enabled is a "leaf" that holds processes only.

## Controllers

The v2 controllers are a curated subset of v1's controllers, with new additions and some renames:

| Controller | v1 name | v2 status | Purpose |
|-----------|----------|-----------|---------|
| `cpu`     | `cpu`   | Stable | CPU time distribution via CFS bandwidth |
| `cpuacct` | `cpuacct` | Merged into `cpu` | CPU accounting (no separate controller) |
| `cpuset`  | `cpuset` | Stable | NUMA/HT pinning |
| `memory`  | `memory` | Stable, extended | Memory limits, accounting, OOM control |
| `io`      | `blkio` | Stable, simplified | I/O throttling (read/write bytes per device) |
| `pids`    | — (new)| Stable | Process count limit |
| `rdma`    | — (new)| Stable | RDMA resource limits |
| `hugetlb` | `hugetlb` | Stable | Hugepage accounting |
| `devices` | `devices` | **Removed**, replaced by eBPF LSM | Device access control is now via BPF |
| `net_cls` | `net_cls` | **Removed** | Use `iptables`/`nftables` `cgroup` match |
| `net_prio`| `net_prio` | **Removed** | Use `tc` per-cgroup |

The removals reflect real-world patterns: BPF-LSM handles device access more flexibly than the v1 controller, and network shaping is more naturally done at the `tc` or `nftables` layer than in cgroups.

## Files at Each Level

Every cgroup exposes:

| File | Meaning |
|------|---------|
| `cgroup.controllers` | Read-only list of available controllers at this level |
| `cgroup.subtree_control` | Read/write set of enabled controllers for children |
| `cgroup.threads` | PID list (in threaded mode) |
| `cgroup.procs` | Process leader PID list |
| `cgroup.events` | Notifications: `populated`, `frozen`, `kill` |
| `cgroup.stat` | Aggregate stats: `nr_descendants`, `nr_dying_descendants` |
| `cgroup.type` | `domain`, `threaded`, or `domain invalid` |

When the `memory` controller is enabled at the parent:

| File | Meaning |
|------|---------|
| `memory.current` | Current memory usage (bytes, accurate) |
| `memory.peak`    | Maximum memory usage since reset |
| `memory.min`     | Hard floor — never reclaim below |
| `memory.low`     | Soft floor — reclaim only when pressure |
| `memory.high`    | Throttle allocation above this |
| `memory.max`     | Hard limit — OOM above |
| `memory.swap.max`| Swap usage hard limit |
| `memory.swap.current` | Current swap usage |
| `memory.zswap.max` | zswap writeback limit |
| `memory.oom.group` | If 1, OOM kills all processes in the cgroup, not just one |
| `memory.events` | Counters: `oom`, `oom_kill`, `low`, `high`, `max`, `swap_max`, `reclaim` |
| `memory.events.local` | Per-cgroup (not aggregated to root) events |
| `memory.stat` | Per-cgroup page counters by type (anon, file, slab, etc.) |

The `memory.events` file is the heart of the v2 model. systemd's `MemoryHigh` maps to `memory.high`, `MemoryMax` to `memory.max`, and `MemoryLow` to `memory.low`. The kernel bumps the `high` event counter whenever the cgroup exceeds `memory.high`, and `oom_kill` whenever the OOM killer fires.

## Memory Reclaim in v2

The v2 reclaim model is generation-based: each cgroup has a generation counter, and the global reclaim walks cgroups oldest-generation-first. The effective protection is `max(memory.min, memory.low)` minus what's already used by ancestors:

```text
For cgroup A with memory.low=200MB and child B with memory.low=100MB:
  - Effective protection of A: min(usage of A, 200MB)
  - Effective protection of B: min(usage of B, 100MB) — but only if A is below 200MB

If A's usage exceeds 200MB, B's protection is 0 — the kernel reclaims from B before A's
unprotected pages, but only because A has overflowed its own protection.
```

The `memory.oom.group` flag is critical for container runtimes: a `podman` container wants OOM to kill the whole container, not just the unlucky worker inside. Set to 1, the OOM walker kills every process in the cgroup when it triggers.

## The `pids` Controller

The `pids` controller is the most underappreciated tool for hardening services. Without it, a single `fork()`-loop bug in a service can OOM the machine by exhausting the PID space (default 4 million on x86_64 with `pid_max`):

```bash
# /etc/systemd/system/api-worker.service
[Service]
ExecStart=/usr/bin/api-worker
PidsLimit=200      # max 200 processes in this unit
TasksMax=200       # alias for PidsLimit on systemd 239+
MemoryMax=2G       # max 2 GB RAM
```

`pids.current` reports the count; `pids.events` reports `max` when the limit is hit. A worker attempting `fork()` while at the limit sees `EAGAIN`.

## The `io` Controller

The v2 `io` controller replaces v1's `blkio` with a per-device, per-direction byte/IO budget:

```bash
# /sys/fs/cgroup/system.slice/api-worker.service/io.max
8:16 rbps=10485760 wbps=10485760 riops=1000 wiops=1000
```

Where `8:16` is `major:minor` of the block device (find with `lsblk -o MAJ:MIN`). The limits are enforced in the block layer via `ioc_cost_qos` (kernel 5.x+). For NVMe with multiple hardware queues, each queue gets its own `blkg` (block-layer cgroup) reference; the limit is applied across all of them.

## Threaded Mode

A v2 cgroup is by default a "domain" cgroup: it manages processes. To manage individual threads within a process, the cgroup can be set to `threaded`:

```bash
mkdir /sys/fs/cgroup/system.slice/api-worker/threads
echo threaded > /sys/fs/cgroup/system.slice/api-worker/threads/cgroup.type
# Now threads (TIDs, not PIDs) can be written to threads/cgroup.threads
```

Threaded mode is required for `cpu`-pinning of specific threads (e.g., a database's writer thread vs. its WAL flush thread). It cannot host `memory` (memory is per-process, not per-thread).

## systemd Integration

systemd maps unit files to cgroups automatically. The `systemd-cgls` and `systemd-cgtop` tools visualize the tree; `systemctl set-property` updates limits live:

```bash
systemctl set-property nginx.service MemoryMax=2G CPUQuota=200%
```

The unit file equivalent:

```ini
# /etc/systemd/system/nginx.service
[Service]
ExecStart=/usr/sbin/nginx -g 'daemon off;'
MemoryMax=2G
MemoryHigh=1500M
CPUQuota=200%
CPUWeight=500
IOWeight=200
TasksMax=512
```

## Migration from v1

The migration pain is concentrated in:

1. **Network shaping** — `tc`/`nftables` configuration must be redone. The `cgroup` match in `nftables` matches v2 paths: `nft add rule netdev filter cgroup-path "system.slice/nginx.service"`.
2. **Device whitelisting** — `devices.allow`/`devices.deny` is gone; use `bpftrace` or BPF-LSM with `BPF_PROG_TYPE_CGROUP_DEVICE`.
3. **Memory accounting** — `memory.usage_in_bytes` (v1) included slab, `memory.current` (v2) does not include shared slab unless `memory_slab` is configured separately.
4. **Docker** — `--memory` and `--cpus` map cleanly to v2; `--device-read-bps` works with `io.max`; `--blkio-weight` becomes `--io-weight`.

Modern Docker (≥20.10) and containerd (≥1.4) default to v2 when the host mounts `/sys/fs/cgroup` as a v2 unified hierarchy.

## Common Pitfalls

1. **Forgetting that `cgroup.subtree_control` only affects children.** Writing `+memory` to `/sys/fs/cgroup/system.slice/cgroup.subtree_control` does not enable memory accounting for `system.slice` itself — only for `system.slice/*` cgroups.
2. **Setting `memory.high` ≥ `memory.max`.** This silently disables `memory.high` throttling. `memory.high` must be strictly less than `memory.max` to take effect.
3. **Confusing `cpu.weight` and `cpu.max`.** `cpu.weight` is a relative share (default 100, range 1–10000); `cpu.max` is a quota (`"50000 100000"` = 50% of one CPU). They are independent.
4. **Not enabling `pids` globally.** Without `pids`, a buggy service can crash the host. Always `+pids` at the root and set per-unit limits.
5. **Reading `memory.current` as the actual footprint.** It includes page cache that may be shared with other cgroups; `memory.stat` field `file` is the unshared file-backed portion.

## References

- [kernel.org: cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- Tejun Heo, "The cgroup v2 interface" (LPC 2015, [slides](https://lpc.events/event/2/contributions/75/))
- [LWN: "Control group v2" (2014)](https://lwn.net/Articles/601826/) and [follow-up](https://lwn.net/Articles/611727/)
- [systemd.resource-control(5)](https://www.freedesktop.org/software/systemd/man/systemd.resource-control.html)
- [cgroup v2 best practices — Kubernetes](https://kubernetes.io/docs/concepts/architecture/cgroups/)
- Roman Gushchin, "cgroup v2 memory controller: implementation notes" (LPC 2019)
