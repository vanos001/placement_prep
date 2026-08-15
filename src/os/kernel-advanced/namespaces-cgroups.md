# Namespaces & cgroups — Internals and systemd Integration

## Overview

Namespaces and cgroups are the two kernel primitives that enable **containers**. This chapter covers their kernel-internal data structures, the cgroup v2 unified hierarchy, systemd's dependency graph, journald, udev, the kernel device model, and the virtual filesystems (sysfs, procfs, debugfs).

## Namespace Internals

### struct nsproxy

Each process has a pointer to `struct nsproxy` (`include/linux/nsproxy.h`) which groups its namespace references:

```c
struct nsproxy {
    atomic_t count;
    struct uts_namespace *uts_ns;      // CLONE_NEWUTS: hostname, NIS domain
    struct ipc_namespace *ipc_ns;      // CLONE_NEWIPC: System V IPC, POSIX msg queues
    struct mnt_namespace *mnt_ns;      // CLONE_NEWNS: mount points
    struct pid_namespace *pid_ns_for_children; // CLONE_NEWPID: process IDs
    struct net_namespace *net_ns;      // CLONE_NEWNET: network stack
    struct cgroup_namespace *cgroup_ns; // CLONE_NEWCGROUP: cgroup view
    struct user_namespace *user_ns;    // CLONE_NEWUSER: UIDs/GIDs
};
```

When `clone(CLONE_NEWPID | CLONE_NEWNET)` is called, the kernel:
1. Allocates a new `struct pid_namespace` (`kernel/pid_namespace.c`).
2. The new namespace's `child_reaper` is set to the calling process (it becomes PID 1 in the new namespace).
3. The new `struct net_namespace` is allocated (`net/core/net_namespace.c`), with independent routing tables, iptables rules, network devices (except loopback, which is always created).

### Namespace Lifetime

Namespaces are reference-counted. A namespace is destroyed when the **last process** inside it exits AND the last **reference** from outside (e.g., a bind-mount or open fd on `/proc/<pid>/ns/<type>`) is closed.

```bash
# See namespaces of a process:
ls -la /proc/$$/ns/
# lrwxrwxrwx 1 root root 0 ... cgroup -> 'cgroup:[4026531835]'
# lrwxrwxrwx 1 root root 0 ... net -> 'net:[4026531993]'

# Hold a namespace alive (even after all processes exit):
touch /tmp/ns_hold
mount --bind /proc/$$/ns/net /tmp/ns_hold
# Now the network namespace won't be freed until unmount
```

### User Namespaces and UID Mapping

User namespaces allow **unprivileged users** to create namespaces with their own UID/GID mappings:

```c
// kernel/user_namespace.c
// Each user namespace has a uid/gid mapping table
struct user_namespace {
    struct uid_gid_map uid_map;   // maps child UIDs → parent UIDs
    struct uid_gid_map gid_map;
    struct user_namespace *parent; // hierarchy
    kuid_t owner;                 // the creator's UID in parent ns
    // ... capabilities, proc limits ...
};

// Newuidmap/newgidmap (userspace) writes to /proc/<pid>/uid_map / gid_map
// Format: <start_in_ns> <start_in_parent> <count>
// Example: 0 1000 1  →  map UID 0 (root in container) to UID 1000 (host)
```

> **Interview Angle**: "How does root in a container not have root on the host?" The container's root (UID 0) is mapped to an unprivileged UID (e.g., 1000) on the host via the user namespace's `uid_map`. When a syscall checks capabilities, the kernel translates the UID through the namespace hierarchy. A `CAP_SYS_ADMIN` in the container only grants it within that user namespace's scope.

## cgroup v2 — Unified Hierarchy

### Architecture

```text
/sys/fs/cgroup/ (cgroup v2 mount point)
├── cgroup.controllers     # available controllers: memory cpu io pids
├── cgroup.subtree_control # enabled controllers at this level
├── cgroup.max.depth        # nesting limit
├── cgroup.procs            # processes in this cgroup
├── memory.max              # memory limit (e.g., "512M")
├── memory.current          # current usage
├── memory.events           # oom_kill, low, high events
├── memory.swap.max         # swap limit
├── cpu.max                 # CPU bandwidth: "100000 1000000" (10%)
├── io.max                  # block I/O bandwidth per device
├── pids.max                # max processes
├── my-container/
│   ├── cgroup.procs
│   ├── memory.max = "256M"
│   └── ...
```

### Controllers

| Controller | Files | What It Controls | Kernel Source |
|------------|-------|-----------------|---------------|
| `memory` | `memory.max`, `memory.current`, `memory.oom_group`, `memory.swap.max` | Physical memory + swap, OOM handling | `mm/memcontrol.c` |
| `cpu` | `cpu.max`, `cpu.stat`, `cpu.weight` | CFS bandwidth throttling (period/quota) | `kernel/sched/core.c` |
| `io` | `io.max`, `io.stat`, `io.weight` | Block I/O bandwidth (per-device) | `block/blk-cgroup.c` |
| `pids` | `pids.max`, `pids.current` | Max forkable processes | `kernel/pid_controller.c` |
| `rdma` | `rdma.max` | RDMA resource limits | `drivers/infiniband/core/cgroup.c` |
| `hugetlb` | `hugetlb.*.max`, `hugetlb.*.current` | Huge page allocation limits | `mm/hugetlb_cgroup.c` |
| `perf_event` | `perf_event.max` | Perf event allocation limit | `kernel/events/core.c` |
| `misc` | `misc.capacity` | Resource controllers not yet in core | `kernel/cgroup/misc.c` |

### cgroup v2 vs v1

| Aspect | cgroup v1 | cgroup v2 |
|--------|----------|----------|
| Hierarchy | Multiple (memory, cpu, blkio as separate mounts) | Single unified tree |
| Delegation | Complicated, thread-mode needed | Clean delegation model |
| No-internal-process rule | Not enforced | A cgroup can't have both processes and child controllers |
| PSI | Optional | Built-in (memory/io/cpu pressure) |
| Default in | RHEL 7, older distros | RHEL 9, Ubuntu 22.04+, all modern distros |

### PSI — Pressure Stall Information

PSI (`kernel/sched/psi.c`) tracks the fraction of time that tasks are stalled waiting for CPU, memory, or I/O:

```bash
cat /sys/fs/cgroup/memory.pressure
# some avg10=0.00 avg60=0.00 avg300=0.00 total=0
# full avg10=0.00 avg60=0.00 avg300=0.00 total=0

# "some": at least one task stalled
# "full": all non-idle tasks stalled (system is unresponsive)
# Kubernetes uses PSI for OOM killing (kubelet eviction)
```

PSI is implemented via **state change aggregation** in the scheduler: when a task blocks on memory reclaim or I/O, the PSI state machine transitions; when it wakes, it transitions back. The cumulative stall time is tracked per-cgroup using per-CPU counters (to avoid atomic contention).

## systemd Internals

### Dependency Graph

systemd represents the boot as a **directed acyclic graph (DAG)** of units (.service, .target, .socket, .mount, etc.). Each unit has:

```
[Unit]
Description=My Service
After=network.target       # start after this
Wants=network-online.target # soft dependency
Requires=dbus.service      # hard dependency (restart if failed)
Before=multi-user.target   # I must start before this
Conflicts=shutdown.target  # mutually exclusive
```

systemd-resolved dependency ordering and runs units in parallel where possible (two services with no dependency on each other run concurrently).

```text
# Boot transaction (simplified):
basic.target
  ├─ sysinit.target
  │   ├─ systemd-tmpfiles-setup.service
  │   ├─ systemd-udev-trigger.service
  │   └─ cryptsetup.target (if LUKS)
  ├─ network.target
  │   └─ systemd-networkd.service
  ├─ sshd.service
  └─ multi-user.target
      └─ docker.service
```

### cgroup Delegation

systemd creates a cgroup tree that mirrors the unit hierarchy:

```text
/sys/fs/cgroup/
├── user.slice/
│   └── user-1000.slice/
│       └── session-1.scope/
│           └── app.service/
├── system.slice/
│   ├── sshd.service/
│   ├── docker.service/
│   └── systemd-journald.service/
└── machine.slice/             # systemd-nspawn / systemd-machined
```

Each `.service` gets its own cgroup with `memory.max`, `cpu.max` configured via the unit file's `[Slice]` or `[Service]` directives. systemd uses **cgroup v2's delegation** feature to allow non-root services to manage their own sub-cgroups.

## journald

`systemd-journald` is the central logging daemon:

- **Source**: reads log data from multiple sources:
  - `/dev/kmsg` — kernel log messages
  - `/run/systemd/journal/` — stdout/stderr of services (via socket activation, `sd_journal_stream_fd()`)
  - `AF_UNIX` sockets at `/run/systemd/journal/socket`, `/run/log/journal`
  - `auditd` netlink socket
- **Storage**: writes to `/var/log/journal/<machine-id>/` in a binary format (forward-compatible, seekable, compressed with LZ4/XZ)
- **Structure**: each log entry is a set of key-value fields (`MESSAGE=...`, `_PID=1234`, `_COMM=sshd`, `_UID=0`, `SYSLOG_IDENTIFIER=...`)
- **Retention**: vacuuming based on size (`SystemMaxUse=`), time (`MaxRetentionSec=`), or disk free space (`SystemKeepFree=`)

## udev — Device Manager

`systemd-udevd` is the userspace device manager that receives **uevents** from the kernel:

```text
Kernel (device driver)
  → kobject_uevent() (lib/kobject_uevent.c)
    → sends uevent via netlink socket (NETLINK_KOBJECT_UEVENT)
      → udevd receives uevent
        → matches against rules in /usr/lib/udev/rules.d/
          → applies: symlink, permissions, runs external program
            → e.g., creates /dev/sda1, /dev/disk/by-id/..., runs systemd-automount
```

The kernel's **kobject model** (`lib/kobject.c`) is the foundation. Every device, driver, and bus is represented as a `struct kobject` in a hierarchical tree. `kobject_uevent()` serializes attributes (DEVPATH, SUBSYSTEM, ACTION) and broadcasts them via netlink.

## Kernel Device Model

### kobject/kset/ktype

```c
// include/linux/kobject.h
struct kobject {
    const char *name;          // name in sysfs
    struct list_head entry;    // sibling list
    struct kobject *parent;    // parent kobject
    struct kset *kset;         // the kset this belongs to
    struct kobj_type *ktype;   // type: release, sysfs_ops, default_attrs
    struct kernfs_node *sd;    // sysfs directory entry
    struct kref kref;          // reference count
    // ... state flags ...
};
```

- **kobject**: a single object with a sysfs directory.
- **kset**: a collection of related kobjects (e.g., all PCI devices belong to `devices/pci` kset). The kset provides the uevent operations.
- **ktype**: defines the release function and sysfs attribute operations for a kobject type.

### struct device

```c
// include/linux/device.h
struct device {
    struct kobject kobj;           // embedded — has a sysfs directory
    struct device_parent *parent;  // parent device in tree
    struct bus_type *bus;          // bus this device is on
    struct device_driver *driver;  // bound driver
    void *platform_data;           // platform-specific data
    struct device_node *of_node;   // device tree (ARM)
    // ... DMA, power management, NUMA node ...
};
```

## Virtual Filesystems

### sysfs (`/sys`)

sysfs is a **ramfs-based** filesystem that exports the kobject hierarchy:

```text
/sys/
├── devices/           # device tree (kobjects)
│   ├── pci0000:00/
│   │   └── 0000:00:1f.0/
│   │       ├── vendor    # sysfs attribute file
│   │       ├── device    # symlink to driver
│   │       └── net/
│   │           └── eth0/
├── bus/
│   ├── pci/
│   │   ├── drivers/     # symlinks to bound drivers
│   │   └── devices/     # symlinks to devices on bus
├── class/
│   ├── net/             # all network devices
│   └── block/           # all block devices
├── kernel/
│   └── notes            # kernel .notes section
├── module/
│   └── ext4/            # module parameters
├── firmware/            # firmware loading interface
└── fs/                 # filesystem registrations
```

### procfs (`/proc`)

procfs is the **process-centric** virtual filesystem. Each process gets a directory (`/proc/<pid>/`), and there are kernel-wide files:

| File | Content | Source |
|------|---------|--------|
| `/proc/meminfo` | Memory statistics | `fs/proc/meminfo.c` — reads from `si_meminfo()` and `vm_node_stat()` |
| `/proc/cpuinfo` | CPU topology, features, caches | `fs/proc/cpuinfo.c` — reads CPUID, per-CPU data |
| `/proc/<pid>/status` | Process state, VmRSS, Threads, Capabilities | `fs/proc/array.c` — reads `task_struct` |
| `/proc/<pid>/maps` | Virtual memory areas | `fs/proc/task_mmu.c` — walks `mm->mmap` under `mmap_lock` |
| `/proc/<pid>/fd/` | File descriptor symlinks | `fs/proc/fd.c` — reads `files_struct` under `files_lock` |
| `/proc/sys/` | Sysctl tunables | `fs/proc/proc_sysctl.c` — writes to kernel variables |
| `/proc/<pid>/ns/` | Namespace symlinks | `proc_pid_ns_link()` — reads `nsproxy` |

### debugfs (`/sys/kernel/debug`)

debugfs is for **debugging only** — it should never appear in production. Kernel subsystems create files dynamically:

```c
// Creating a debugfs file:
struct dentry *d = debugfs_create_file("my_debug", 0444, NULL, data, &my_fops);

// Or a simple u32 value:
debugfs_create_u32("my_counter", 0644, dir, &counter);
// Reading/writing /sys/kernel/debug/.../my_counter directly reads/writes &counter
```

## Interview Questions

### Q: What's the difference between PID namespaces and user namespaces?

PID namespaces isolate process ID numbers — PID 1 in the container is a different process on the host (with a different PID). User namespaces isolate UIDs/GIDs — root (UID 0) in the container maps to an unprivileged UID on the host. You can have a PID namespace without a user namespace (still root on host), but user namespaces are what enable **rootless containers**.

### Q: How does systemd manage cgroups?

systemd is the cgroup manager on modern Linux (via `systemd-run`, `systemctl set-property`). It creates a cgroup for every unit and moves all processes of that unit into the cgroup. This enables resource control (memory/CPU limits), process tracking (all PIDs of a service), and clean teardown (freezing + SIGKILL the entire cgroup on `systemctl stop`).

### Q: Why is cgroup v2's no-internal-process rule important?

In v1, you could have processes in a cgroup and also enable controllers on it (mixing leaf and internal nodes). This created ambiguity about which processes the controller applied to. In v2, a cgroup is either a **leaf** (has processes, no sub-cgroups with controllers) or an **internal node** (has sub-cgroups with controllers, no processes). This ensures unambiguous resource accounting.

### Q: How does udev create /dev nodes?

udevd receives kernel uevents (via netlink), matches rules, and creates device nodes using `mknod()` with the major/minor numbers from the uevent. For block devices, it also handles partition scanning and creates symlinks (`/dev/disk/by-id/`, `/dev/disk/by-uuid/`). Modern systems use `systemd-tmpfiles` and devtmpfs for the initial device node creation; udev handles permissions and symlinks.

## References

- `kernel/nsproxy.c`, `kernel/pid_namespace.c` — namespace implementation
- `kernel/cgroup/` — cgroup v2 implementation
- `kernel/sched/psi.c` — PSI pressure tracking
- `lib/kobject.c`, `include/linux/kobject.h` — kobject/device model
- `fs/proc/`, `fs/sysfs/`, `debugfs/` — virtual filesystem implementations
- `Documentation/admin-guide/cgroup-v2.rst` — cgroup v2 specification
- `Documentation/driver-api/driver-model/` — kernel device model
- [freedesktop.org/systemd](https://www.freedesktop.org/wiki/Software/systemd/) — systemd documentation

## Related Topics

- [Boot Process](./boot-process.md) — initramfs, PID 1 startup
- [VFS Internals](./vfs-internals.md) — how procfs/sysfs/debugfs implement filesystem ops
- [eBPF Deep Dive](./ebpf-deep.md) — cgroup BPF, LSM BPF
- [Containers](../containers/README.md) — higher-level container concepts
