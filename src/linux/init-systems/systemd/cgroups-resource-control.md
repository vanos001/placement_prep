# cgroups and Resource Control (slices, scopes, systemd.resource-control)

## Overview

Control groups are the foundation systemd is built on. The founding design
insight — stated in the original systemd announcement and repeated in every
architecture discussion since — is that PID 1 should manage a *cgroup per
service*: every process a service spawns, however many times it forks or
however it dissociates from its session, remains a member of the service's
cgroup, so attribution, cleanup, and killing become kernel-guaranteed
operations instead of pidfile guesswork. Everything else on this page —
slices, scopes, resource limits, oomd — is elaboration on that one idea:
cgroups give the manager a kernel-visible handle on "all processes of unit
X".

Resource control is the user-facing payoff. Each unit that owns a cgroup
can be given CPU weights and quotas, memory protections and hard limits, IO
weights and bandwidth caps, and PID counts — configured with
`systemd.resource-control(5)` directives that systemd translates into
cgroup v2 controller files (`cpu.max`, `memory.max`, `io.max`, `pids.max`).
Because the settings live on the cgroup, they apply to the whole process
tree including future children, and because systemd owns the hierarchy, the
same directives work identically for services, scopes, and slices.

This page covers the hierarchy modes, the slice/scope/service unit model,
each controller's directives and kernel mapping, delegation, the tools for
applying and verifying limits, and the interview-grade "why" questions.
Kernel mechanics of cgroup v2 itself are covered in
[cgroups.md](../../../os/containers/cgroups.md) and
[namespaces-cgroups.md](../../../os/kernel-advanced/namespaces-cgroups.md);
this page focuses on systemd's layer above them.

## Hierarchy Modes and the Default Tree

Modern systemd (v243 and later on kernels with cgroup v2 support) defaults
to the **unified** hierarchy: a single cgroup v2 tree mounted at
`/sys/fs/cgroup`. Older modes still exist for compatibility: **legacy**
(v1, one hierarchy per controller, `systemd.legacy_systemd_cgroup_controller=`
plus `cgroup_no_v1=all` style setups) and **hybrid** (v2 for systemd's own
bookkeeping plus v1 controllers for legacy software). All three change
which controllers are available where; virtually everything below assumes
unified v2, where each cgroup has one directory with all controller files.

The systemd-created top-level structure:

```text
/sys/fs/cgroup/                      ← -.slice (root slice)
├── init.scope                       ← PID 1 and its children
├── system.slice/                    ← all system services
│   ├── nginx.service/               ←   each service = one cgroup
│   │   ├── cpu.max  memory.max ...  ←   the controller files
│   │   └── 1234 1235 ...            ←   member PIDs
│   ├── ssh.service/
│   └── backup.service/
├── user.slice/                      ← user sessions
│   └── user-1000.slice/
│       ├── user@1000.service/       ← the user's own manager (delegated)
│       ├── session-3.scope/         ← one login session
│       └── app.slice/ ...
└── machine.slice/                   ← containers/VMs registered with machined
```

Every unit with a cgroup lives somewhere in this tree: services under
`system.slice` (or a custom slice), each login session as a `session-N.
scope` under `user.slice`, the per-user service manager as
`user@UID.service`, and containers under `machine.slice`. The naming maps
directly to escaped unit paths — `/sys/fs/cgroup/system.slice/nginx.
service` is `nginx.service` — which is why `systemd-cgls` output and
`systemctl` output line up one-to-one.

## Slice, Scope, and Service Units

Three unit types own cgroups, and their division of labor is the model to
internalize:

- **`.service` units** are cgroups systemd *manages*: the manager forks the
  processes, tracks them, and applies kill policies. Covered in
  [service-units](./service-units.md).
- **`.scope` units** are cgroups for *foreign* processes — processes
  systemd did not fork but is asked to contain: login sessions (created by
  logind), `systemd-run --scope` invocations, container runtimes that opt
  in. A scope is created transiently (`systemd-run --scope`, logind's
  PAM hooks); there are no scope files on disk. Unlike services, scopes
  have no lifecycle management: the manager watches membership but does
  not supervise the processes.
- **`.slice` units** build the *hierarchy*: a slice is a purely
  organizational cgroup under which services/scopes/other slices are
  arranged, and it carries default resource settings inherited by
  everything beneath it. Slice units are real unit files (`-.slice`,
  `system.slice`, `user.slice` ship in `/usr/lib/systemd/system`).

A service is placed under a non-default slice with `Slice=`:

```ini
# /etc/systemd/system/heavy-worker.slice
[Slice]
CPUWeight=400
MemoryHigh=6G

[Install]
WantedBy=machine.slice     # unusual but legal; more often no [Install]
```

```ini
# /etc/systemd/system/heavy-worker.service
[Service]
Slice=heavy-worker.slice
ExecStart=/usr/local/bin/worker
```

The cgroup path becomes `/sys/fs/cgroup/heavy-worker.slice/heavy-worker.
service`, the service inherits the slice's CPU weight and memory throttle
as its own defaults, and both levels remain independently tunable. Slices
can nest (a slice's `Slice=` names its parent), giving arbitrarily deep
resource hierarchies — with the cgroup v2 caveat that controllers must be
enabled top-down and delegation boundaries are where nesting stops being
systemd-managed.

## CPU Control

| Directive | Kernel file (v2) | Semantics |
|---|---|---|
| `CPUAccounting=` | (implicit on v2) | Enable accounting; effectively always on under unified |
| `CPUWeight=` | `cpu.weight` | Relative share, 1–10000, default 100 — only matters under contention |
| `StartupCPUWeight=` | `cpu.weight` | Weight while the unit is starting (faster boot for latency-sensitive units) |
| `CPUQuota=` | `cpu.max` | Hard throughput cap as a percentage of one CPU (e.g. `50%`) |
| `CPUQuotaPeriodSec=` | `cpu.max` period | CFS period; default 100ms |
| `AllowedCPUs=` / `AllowedMemoryNodes=` | `cpuset.cpus` / `cpuset.mems` | Pin to CPUs / NUMA nodes (also startup variants) |

The weight/quota distinction is the interview core. `CPUWeight=200` means
"twice the share of a default-100 sibling *when they compete*"; an idle
machine gives the unit everything anyway. `CPUQuota=50%` means "never more
than half a CPU even if the machine is idle", implemented as `cpu.max =
50000 100000` (50ms of runtime per 100ms period — check it directly:

```bash
cat /sys/fs/cgroup/system.slice/nginx.service/cpu.max
# 50000 100000      ← quota_us period_us : CPUQuota=50% at default period
systemctl show nginx.service -p CPUQuotaPerSecUSec
# CPUQuotaPerSecUSec=500ms
```

Weights map to `cpu.weight` (v2 rescales the 1–10000 range into the
kernel's 1–10000 weight directly), quotas to `cpu.max` via CFS bandwidth
control. Slices carry weights naturally (a busy `workload.slice` with
`CPUWeight=800` competes with `system.slice` at its own weight), while
quotas are typically per-service. Legacy `CPUShares=` (v1
`cpu.shares`) still parses but is a compatibility alias — new units should
use `CPUWeight=`.

## Memory Control

| Directive | Kernel file (v2) | Semantics |
|---|---|---|
| `MemoryAccounting=` | implicit | Charge pages to the cgroup |
| `MemoryMin=` | `memory.min` | Hard protection: reclaim from *siblings* first; cannot be breached without OOM |
| `MemoryLow=` | `memory.low` | Soft protection: best-effort reclaim shield |
| `MemoryHigh=` | `memory.high` | Throttle point: above it the kernel forces reclaim and stalls allocation — a slowdown, not a kill |
| `MemoryMax=` | `memory.max` | Hard limit: allocation above it triggers OOM kill within the cgroup |
| `MemorySwapMax=` | `memory.swap.max` | Cap swap usage of the cgroup |

The semantics ladder is: `Min` (absolute, charge-ancestors protection) >
`Low` (best-effort protection) > unlimited-with-throttle `High` >
hard-kill `Max`. `MemoryHigh=` is the underrated one: it converts
"runaway service" into "runaway service that got slow", which is often the
operationally correct failure mode for caches and batch jobs. `MemoryMax=`
is the replacement for v1's `MemoryLimit=` and produces — via the kernel —
an OOM kill *within the cgroup*, visible in the journal as
`oom-kill:constraint=CONSTRAINT_MEMCG` on the memcg OOM path, plus
systemd's own `A cgroup memory.max was hit` style records.

```ini
[Service]
MemoryAccounting=yes
MemoryLow=2G          # protect the cache under pressure
MemoryHigh=4G         # start throttling here
MemoryMax=6G          # OOM here
MemorySwapMax=1G
```

Unit-level OOM policy (`OOMPolicy=` in `systemd.service(5)`/
`systemd.scope(5)`; values `continue`, `stop`, `kill`) decides what the
*unit* does when the kernel kills one of its members — `kill` (the whole
cgroup gets killed too) is the container-like behavior, `continue` the
default. The userspace preemptive killer is separate: **systemd-oomd**
monitors PSI pressure and swap state at configured *monitor points*
(`ManagedOOMMemoryPressure=` / `ManagedOOMSwap=` on slices and scopes,
typically `user@.service` and `system.slice` in distro defaults) and kills
the highest-pressure cgroup *before* the kernel would — trading a
policy-chosen victim for avertable system-wide stall. Ubuntu enables oomd
by default on desktops; its kills log as `systemd-oomd killed ... due to
memory pressure` and are the first thing to check when a desktop app
"disappeared".

## IO and PIDs

### IO control

`IOAccounting=`, `IOWeight=` (1–10000, default 100) and the
`io.max`-backed caps `IOReadBandwidthMax=`, `IOWriteBandwidthMax=`,
`IOReadIOPSMax=`, `IOWriteIOPSMax=` — each taking `device bytes/s` pairs
or `max`:

```ini
[Service]
IOAccounting=yes
IOWeight=50
IOReadBandwidthMax=/dev/nvme0n1 100M
IOWriteIOPSMax=/dev/nvme0n1 1000
```

The `IO*` directives map to cgroup v2's `io.weight`/`io.max` and require
the backing device to use the `bfq` or `blk-cgroup`-capable scheduler for
weights; bandwidth caps work through `io.max` regardless. Do not confuse
them with `IOSchedulingClass=`/`IOSchedulingLevel=` from
`systemd.exec(5)`: those set the *per-process* `ionice`-style scheduling
class of the unit's processes (a property of the task, not the cgroup) and
compose with, but do not replace, cgroup IO control. `Nice=` and
`CPUWeight=` have the same relationship.

### PIDs control

`TasksAccounting=` and `TasksMax=` cap the number of tasks (threads +
processes) in the cgroup — `pids.max`, the only controller designed
exactly for fork-bomb containment:

```ini
[Service]
TasksMax=64            # absolute count

[Slice]
TasksMax=10%           # fraction of the system-wide PIDs ceiling
```

The manager default comes from `DefaultTasksMax=` in
`systemd-system.conf(5)`: **15% of the minimum of `kernel.pid_max`,
`kernel.threads-max`, and the root cgroup's `pids.max`** — thousands of
tasks on a normal server, but a real ceiling, which is why "my service
can't fork anymore" on systemd systems is often a `TasksMax=` hit (check
`systemctl show foo -p TasksMax`, or `pids.max`/`pids.current` in the
cgroup directory) and not a ulimit. Slices can tighten it further for
blast-radius control; containers get their own via delegation.

## Device Access and Delegation

### Device policy (eBPF device controller)

Cgroup v2 has no `devices` controller; systemd implements device access
control with a BPF program per cgroup, configured with the same
directives the v1 era used:

```ini
[Service]
DevicePolicy=closed                # auto | closed | strict
DeviceAllow=/dev/null rw
DeviceAllow=char-rtc r
```

`DeviceAllow=` takes a device node path or a `char-*`/`block-*` special
name followed by an `rwm` combination. The three policies: `auto` (the
default) permits all device access except where `DeviceAllow=` restricts
it; `closed` denies everything except the standard pseudo devices
(`/dev/null`, `/dev/zero`, `/dev/random`, and friends) plus whatever
`DeviceAllow=` grants; `strict` allows *only* what `DeviceAllow=` grants.
The practical use is sandboxing: combined with `PrivateDevices=` from
`systemd.exec(5)` most services need only `/dev/null`, `/dev/urandom`,
and nothing else.

### Delegation

`Delegate=` turns the unit's cgroup subtree over to processes inside it:
the manager stops managing controllers below that point (enables a
controller set — by default the ones the unit uses plus the delegation
safe-list — and marks the boundary), and the payload decides the rest.
Three consumers matter: **user managers** (`user@.service` runs delegated
so `systemctl --user` can nest its own slices/scopes/services), **
containers** (runc/systemd-nspawn children manage their own internal
hierarchy — this is how "docker under systemd" coexists with the host
manager: the container lives in a scope under `machine.slice` or the
runtime's slice and delegates inward), and **batch systems** that build
their own trees. Delegation comes with rules: the delegating manager
should not touch controllers above the boundary, and processes inside may
not enable controllers their ancestors left disabled — the cgroup v2
"no-internal-process" and top-down enablement constraints, explained in
[cgroups.md](../../../os/containers/cgroups.md).

## Applying and Verifying Controls

Settings can live in unit files, drop-ins (`systemctl edit nginx.service`
→ `/etc/systemd/system/nginx.service.d/override.conf`), slice files, or
be set at runtime:

```bash
# transient scope with a CPU cap — the systemd-run one-liner
systemd-run --scope -p CPUQuota=20% -p MemoryMax=1G ./analytics-job

# persistent property change on a slice (runtime only, lost on reboot)
systemctl set-property --runtime workload.slice CPUWeight=200

# persistent property change (writes a drop-in)
systemctl set-property workload.slice CPUWeight=200 MemoryHigh=4G
```

`set-property` works on services, scopes, and slices and is the
recommended way to experiment before baking values into drop-ins. For
[systemctl-cli](./systemctl-cli.md) day-to-day workflows, the trio
`systemctl show -p <prop>`, `systemctl edit`, and `set-property` covers
the read-modify-write cycle.

Verification tools:

```bash
systemd-cgls                       # cgroup tree, annotated with unit names
systemd-cgtop                      # live CPU/MEM/IO per cgroup, like top
cat /sys/fs/cgroup/system.slice/foo.service/cpu.max
cat /sys/fs/cgroup/system.slice/foo.service/memory.current
systemctl show foo.service -p CPUQuotaPerSecUSec -p TasksMax -p MemoryMax
journalctl -k | grep -i oom        # kernel OOM records
journalctl -u systemd-oomd         # oomd kill decisions
```

`systemd-cgtop` reads accounting data from the cgroup filesystem (so it
needs accounting enabled, which under unified v2 is effectively free) and
is the fastest way to answer "which unit is eating the machine" with
unit-level attribution instead of process-level — the answer `top`
cannot give because it aggregates per-PID.

## Why cgroups and not pidfiles: the interview core

- **Attribution under fork storms.** A pidfile records one PID. A daemon
  that forks workers, re-executes, or is double-forked by a wrapper leaves
  a process tree no pidfile can describe. The cgroup membership is
  maintained by the kernel at fork time — every descendant, including
  ones that called `setsid(2)` or daemonized, is accounted. This is why
  `systemctl status` shows accurate main/child process lists and why
  per-service CPU/memory numbers are trustworthy.
- **Cleanup without leaks.** `KillMode=control-group` (the default) sends
  the kill signal to *all remaining processes of the cgroup* — including
  grandchildren that escaped their parent's process group. SysVinit
  stop scripts and runit-style supervisors must walk process trees
  themselves and miss escaped processes; systemd cannot, because the
  kernel does the bookkeeping. (Compare
  [runit stages-services](../runit/stages-services.md) and
  [sysvinit init-scripts](../sysvinit/init-scripts.md) where stop logic is
  hand-written.)
- **Resource control needs a container anyway.** Quotas and protections
  are cgroup concepts; once the per-service cgroup exists for lifecycle
  reasons, `CPUQuota=`/`MemoryMax=` are just files to write.
- **Containers are the degenerate case.** A container is a delegated
  subtree plus namespaces; "docker under systemd" works because the
  runtime gets a scope under `machine.slice`/`system.slice` and delegates
  inward — see [daemons](../../../os/processes/daemons.md) for the
  process-model background.

The cost side is worth one sentence in interviews too: per-service
cgroups make `ps` output hierarchical (use `systemd-cgls` or `ps xawf -eo
pid,cgroup,args` to see membership) and add a nesting boundary
(`Delegate=`) that ad-hoc scripts must respect.

## Interview Questions

### Q: Why does systemd create one cgroup per service instead of tracking PIDs?

Because PID tracking fails exactly when it matters: double-forking
daemons, workers, and re-executing parents produce trees no pidfile
captures, and a stop script that misses an escaped PID leaks processes.
Cgroup membership is assigned by the kernel at fork and cannot be escaped
by `setsid()` or daemonization, so the manager always knows the complete
member set — enabling accurate status, complete `KillMode=control-group`
cleanup, and per-service accounting. The resource-control directives are
then a natural consequence: the kernel already maintains the container.

### Q: What is the difference between CPUWeight and CPUQuota, and when does each apply?

`CPUWeight=` (1–10000, default 100) is a *relative* share that matters
only under contention: a weight-200 unit gets twice a default sibling's
CPU when both are busy, and everything when idle. `CPUQuota=` is an
*absolute* cap as a percentage of one CPU, enforced via CFS bandwidth
(`cpu.max`, e.g. `50000 100000` for 50% at the default 100ms period) and
applies even on an idle machine. Shares for fair division among known
workloads; quotas for hard protection against any one unit monopolizing
the box.

### Q: Explain the memory protection ladder MemoryMin/Low/High/Max.

`MemoryMin=` is hard protection — the kernel reclaims from siblings
before touching these pages, breaching it only via OOM. `MemoryLow=` is
best-effort protection with the same spirit. `MemoryHigh=` is a throttle:
above it the cgroup's allocations stall under forced reclaim, turning a
runaway service slow instead of dead. `MemoryMax=` is the hard limit whose
exhaustion OOM-kills within the cgroup. Operationally: Min/Low protect
important working sets, High is the polite container of last resort, Max
is for strict isolation — and `MemorySwapMax=` bounds the swap side
independently.

### Q: What are slice and scope units, and how do they differ from services?

Services are cgroups whose processes systemd forks and supervises.
Slices are hierarchy-building cgroups that group units and carry default
resource settings (`Slice=` places a service under a custom slice).
Scopes are cgroups for *foreign* processes systemd didn't fork — login
sessions from logind, `systemd-run --scope` jobs, opting-in container
runtimes — created transiently, watched but not supervised. The triple
maps the whole system: `-.slice` → `system.slice`/`user.slice`/
`machine.slice` → services and scopes as leaves.

### Q: What is the default TasksMax and why does it exist?

`DefaultTasksMax=` in `systemd-system.conf(5)` defaults to 15% of the
minimum of `kernel.pid_max`, `kernel.threads-max`, and the root cgroup's
`pids.max` — a few thousand tasks on typical servers, enforced per-cgroup
via `pids.max`. It exists because a runaway service forking without
bound (a fork bomb) must be contained at the cgroup level, not at the
machine level (`kernel.threads-max` exhaustion takes down everything).
When a service fails spawning threads, check `TasksMax=`/`pids.current`
before blaming ulimits — `TasksMax=` is per-unit overridable.

### Q: How does systemd-oomd differ from the kernel OOM killer, and what do ManagedOOM* settings do?

The kernel OOM killer acts after memory is exhausted, picking a victim by
badness score. systemd-oomd acts *before*: it watches PSI memory pressure
and swap exhaustion at configured monitor points and kills the
highest-pressure cgroup early. `ManagedOOMSwap=`/`ManagedOOMMemoryPressure=`
(on slices/scopes) opt a subtree into monitoring, and
`ManagedOOMMemoryPressureLimit=` tunes the threshold; kills are logged by
`systemd-oomd`. The design goal is avoiding system-wide stalls by
sacrificing a chosen victim early — which is why desktop distros enable
it and why "app vanished" on those systems starts with
`journalctl -u systemd-oomd`.

## References

- https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.slice.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.scope.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- https://manpages.debian.org/bookworm/systemd/systemd.resource-control.5.en.html
- https://manpages.debian.org/bookworm/systemd/systemd.slice.5.en.html
- https://manpages.debian.org/bookworm/systemd/systemd.scope.5.en.html
- https://docs.kernel.org/admin-guide/cgroup-v2.html
- https://man7.org/linux/man-pages/man7/cgroups.7.html

## Cross-References

- [unit-types.md](./unit-types.md) — slice/scope among the systemd unit types.
- [service-units.md](./service-units.md) — `KillMode=` and the per-service cgroup lifecycle.
- [systemctl-cli.md](./systemctl-cli.md) — `set-property`, `show`, `edit` for applying controls.
- [os/containers/cgroups.md](../../../os/containers/cgroups.md) — kernel cgroup v2 mechanics in depth.
- [os/kernel-advanced/namespaces-cgroups.md](../../../os/kernel-advanced/namespaces-cgroups.md) — namespaces plus cgroups as the container foundation.
- [comparison.md](../comparison.md) — how non-systemd inits handle process containment.
