# lscpu — display CPU architecture information

## Overview

`lscpu` reports the CPU topology and capabilities of the machine: architecture, core/thread/socket/NUMA layout, cache hierarchy, frequencies, virtualization, and the CPU feature flags. It assembles its answer from sysfs (`/sys/devices/system/cpu/`), `/proc/cpuinfo`, and `cpuid`-derived data, presenting it in a human summary plus machine-oriented extended/JSON formats. Ships in the `util-linux` package (Debian bookworm) at `/usr/bin/lscpu`.

Reach for it whenever "how many cores", "is this NUMA", "does the CPU support AVX", or "which CPUs are offline" needs answering — capacity planning, container sizing, performance tuning, and hardware inventories all start here. It is often confused with `nproc` (respects the *caller's* CPU affinity mask; lscpu shows the whole machine regardless of affinity), with `/proc/cpuinfo` (raw per-logical-CPU lines without topology interpretation), and with `chcpu`/`taskset` (the tools that *change* what lscpu merely reports).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/lscpu |
| First appeared | util-linux addition (2000s), inspired by AIX `lscpu` |
| Standards | None (Linux sysfs/cpuid; no command standard) |

## Synopsis

```
lscpu [options]
```

Common one-line forms:

```
lscpu                    # full human summary
lscpu -e                 # extended per-CPU table
lscpu -p=CPU,CORE,SOCKET # parsable, selected columns
lscpu -J                 # JSON
```

## How It Works

### The summary, block by block

```bash
$ lscpu | head -16
Architecture:                       x86_64
CPU op-mode(s):                     32-bit, 64-bit
Address sizes:                      52 bits physical, 57 bits virtual
Byte Order:                         Little Endian
CPU(s):                             2
On-line CPU(s) list:                0,1
Vendor ID:                          GenuineIntel
Model name:                         Intel(R) Xeon(R) Processor
CPU family:                         6
Model:                              173
Thread(s) per core:                 1
Core(s) per socket:                 2
Socket(s):                          1
BogoMIPS:                           6400.00
Flags:                              fpu vme de pse tsc ...
```

- **CPU(s)** — logical CPUs (hardware threads), *not* cores. Physical cores = `Core(s) per socket` × `Socket(s)` (× `Books`/`Drawers` on s390).
- **On-line CPU(s) list** — currently usable CPUs; hot-unplugged ones appear only with `-a`/`-e`.
- **Flags** — cpuid feature bits (`lm` = 64-bit, `vmx`/`svm` = hardware virtualization, `avx2`, `aes`, `hypervisor` = running under one).
- Later blocks: per-NUMA-node CPU lists, `Caches (sum of all)`, `Vulnerability …` rows (Meltdown/Spectre-class mitigations), `Hypervisor vendor` / `Virtualization` when guest.

### Topology from the kernel, not the CPU

`lscpu` does not interrogate raw cpuid for the summary; it reads the kernel's exported topology (`/sys/devices/system/cpu/cpuN/topology/{core_id,core_cpus_list}`, `node_cpus_list`, cache indices) and interprets it per architecture (x86, s390 `book`/`drawer`, ARM clusters). This is why it is trustworthy inside VMs where raw cpuid lies, and why `--sysroot <dir>` can analyze another root's view (a chroot or a mounted image) instead of the live system.

### Machine-readable views

```bash
$ lscpu -e
CPU NODE SOCKET CORE L1d:L1i:L2:L3 ONLINE
  0    0      0    0 0:0:0:0          yes
  1    0      0    1 0:0:0:0          yes

$ lscpu -p=CPU,CORE,SOCKET
# CPU,Core,Socket
0,0,0
1,1,0
```

`-e, --extended[=<list>]` is the per-logical-CPU table (default columns `CPU,NODE,SOCKET,CORE,L1d:L1i:L2:L3,ONLINE`); `-p, --parse[=<list>]` emits comment-prefixed, comma-separated rows designed for `awk`/`cut` consumption; `-J` wraps the summary in JSON; `-r` raw mode strips formatting from the table forms. Column names (`CPU, CORE, SOCKET, NODE, CLUSTER, CACHE, ONLINE, MHZ, MAXMHZ, MODELNAME`) are selectable for both.

### Counting things correctly

The recurring interview trap: "CPU(s): 96" is *logical* CPUs (threads). Distinct physical cores need deduplication over topology ids:

```bash
lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l    # physical cores
```

or just multiply the summary's `Core(s) per socket` × `Socket(s)`.

### Where each field comes from

Every summary row maps to a specific kernel export: online state from `/sys/devices/system/cpu/online`; core/socket/thread ids from `cpuN/topology/{core_id,core_cpus_list,package_cpus_list}`; NUMA nodes from `nodeN/cpulist` plus the distance matrix in `nodeN/distance`; cache shapes from `cpuN/cache/index*/{level,type,size,shared_cpu_list}`; feature flags from `/proc/cpuinfo` (which the kernel filled from cpuid); vulnerability rows from `/sys/devices/system/cpu/vulnerabilities/`. Nothing requires root — it is all world-readable sysfs/procfs, which is also why lscpu works identically in containers and why `--sysroot` can substitute a mounted image's tree.

### Cache sharing — the answer most people miss

`-C` and the `L1d:L1i:L2:L3` column in `-e` report which logical CPUs *share* which cache instance — the ground truth for pinning latency-sensitive work. Co-locate busy threads on CPUs sharing L1/L2 for cheap communication; keep noisy neighbors on separate L3 domains:

```bash
$ cat /sys/devices/system/cpu/cpu0/cache/index3/shared_cpu_list
0-1
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-e, --extended[=<list>]` | Per-CPU table (select columns with `=<list>`) |
| `-p, --parse[=<list>]` | Parsable comma format with `#` header comments |
| `-C, --caches[=<list>]` | Cache inventory (one row per cache, sharing shown) |
| `-J, --json` | JSON output of the summary |
| `-r, --raw` | Raw (unformatted) output for table modes |
| `-a/-b/-c` | All / online-only / offline-only CPUs (for `-e`, `-p`, `-C`) |
| `-x, --hex` | CPU lists as hexadecimal masks (taskset-compatible) |
| `-y, --physical` | Show physical (core) ids instead of logical CPU numbers |
| `-s, --sysroot <dir>` | Read topology from `<dir>` (analyzing a mounted image/chroot) |
| `--output-all` | All columns for `-e`/`-p`/`-C` |

## Usage Patterns

```bash
# Hardware overview of any machine, human summary
lscpu

# How many logical CPUs and physical cores?
nproc                          # respects affinity mask!
lscpu -p=CPU,CORE,SOCKET | grep -vc '^#'   # logical count
lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l   # physical cores

# Is hyperthreading on? (Thread(s) per core > 1)
lscpu | grep -E 'Thread|Core|Socket'

# Which CPUs are offline (hot-unplugged)?
lscpu -e=CPU,ONLINE | grep no

# NUMA layout for memory binding decisions
lscpu -e=CPU,NODE
lscpu | grep -A4 'NUMA'

# Does the CPU support a feature before deploying tuned binaries?
lscpu | grep -o avx2        # or grep the Flags line
lscpu | grep -o 'svm\|vmx'  # AMD / Intel hardware virtualization

# CPU mask compatible with taskset affinity syntax
lscpu -x | grep -i 'On-line CPU(s) mask'

# Cache inventory: how is L3 shared?
lscpu -C

# Analyze a disk image's view of the CPU (forensics, container roots)
sudo lscpu -s /mnt/rootfs

# JSON for inventory systems
lscpu -J | jq -r '.lscpu[] | select(.field=="Model name:") | .data'

# Vulnerability/mitigation rows (security audits)
lscpu | grep -i vulnerability

# Pin a latency-sensitive service to one L3 domain (cache-aware affinity)
L3CPUS=$(cat /sys/devices/system/cpu/cpu0/cache/index3/shared_cpu_list)
taskset -c "$L3CPUS" ./lowlatency_server

# Before/after a CPU hotplug change (or another operator's surprise)
lscpu -e=CPU,ONLINE
echo 0 > /sys/devices/system/cpu/cpu1/online   # root; kernel may refuse in VMs
lscpu -e=CPU,ONLINE

# Full inventory export for asset tracking systems
lscpu -J --output-all > "$(hostname)-cpu.json"

# What the container sees vs the machine (affinity vs whole-host topology)
lscpu | grep -E '^CPU\(s\)|On-line'
nproc

# CPUs per NUMA node, for topology-aware worker pools
lscpu -p=CPU,NODE | grep -v '^#' | awk -F, '{c[$2]++} END {for (n in c) print n, c[n]}'
```

## Nuances and Gotchas

- **Affinity is ignored.** In a container pinned by `taskset`/cpuset, `lscpu` still reports *all* host CPUs; `nproc` (or `grep -c Cpus_allowed_list /proc/self/status`) reports what *this process* may use. Sizing a worker pool from lscpu inside a cgroup-limited container is a classic mistake.
- **Logical ≠ physical.** `CPU(s): 96` on a 2-socket, 24-core, SMT-2 box means 96 threads / 48 cores. Licensing and performance math both need the core count — derive it, do not read `CPU(s)`.
- **Flags are the *CPU's* capabilities**, filtered through the kernel; some bits (e.g. `hypervisor`) describe the environment, and microcode-dependent mitigations appear as separate Vulnerability rows rather than flag removals.
- **BogoMIPS is decorative.** It measures delay-loop calibration, not performance; never quote it as speed.
- **Frequency lines** (`CPU max/min MHz`, per-CPU `MHZ` in `-e`) are instantaneous or nominal values; actual cores boost dynamically (`turbostat` for measurement).
- **s390/ARM topology terms** differ (`BOOK`, `DRAWER`, `CLUSTER` columns); scripts hardcoding `Socket(s)` break across architectures — use `-p` column selection instead.
- **`-e`/`-p` default visibility differs:** `-e` shows online and offline by default (`-a` implied), `-p` shows online only (`-b` implied) — the asymmetry surprises anyone parsing both.
- **`--sysroot` reads files, not the machine** — it re-derives the view from another root's sysfs/proc snapshots; numbers can be stale or inconsistent with the running host.
- **`-x` masks are for affinity APIs** (taskset, sched_setaffinity) — `0x0000000000000003` = CPUs 0-1. Mixing list format (`0-1`) and mask format in scripts trips simple parsers.
- **Cache columns show sharing sets, not sizes.** Two CPUs with the same `L3` index share that cache instance; the index number itself is not an id you can quote in a ticket. Use `-C` for per-cache rows with level, type, size, and shared-CPU lists.
- **`MHZ` in `-e` is a sample, not a spec.** The per-CPU value is read from sysfs at invocation and shifts constantly with boost governors; `MAXMHZ`/`MINMHZ` (cpufreq policy bounds) are the stable numbers for capacity math.
- **`-y/--physical` is about ID *kind*, not physicalness.** It swaps logical CPU numbers for the kernel's core ids in table output — a confusing name; for core counts prefer the (Core,Socket) dedup.
- **Virtual guests report virtual topology.** A 4-vCPU VM shows 4 CPUs and possibly fabricated sockets/cores; use the `Hypervisor vendor` row to interpret, and never license "per core" off a guest's topology without the host view.

## Exit Status

- `0` — information gathered and displayed.
- `1` — error: invalid options/columns, or unreadable sysfs/procfs (unusual outside broken containers).

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`chcpu`](./chcpu.md) — the config-side sibling: enable/disable CPUs, set dispatching mode.
- [`chmem`](./chmem.md) — memory-side equivalent for hotplug/online operations.
- [`chrt`](./chrt.md) — scheduling policy/priority; what the CPUs *run* once enumerated.
- [`taskset`/`nproc`](../../admin/process-management.md) — affinity-aware CPU counting vs lscpu's whole-machine view.
- [`internals`](../../internals.md) — sysfs CPU topology export and cpuid feature bits.

## Interview Questions

### Q: Why do `nproc` and `lscpu` disagree inside a container, and which do you trust for worker sizing?

`lscpu` reports the machine's full topology from sysfs regardless of the caller; `nproc` applies the current process's affinity mask (cpuset-cgroup-limited containers show fewer). For "how many workers may this container run", `nproc` (or the cpuset itself) is authoritative; `lscpu` describes the host. Trusting lscpu over-provisions and thrashes the cgroup CPU quota.

### Q: How do you compute the physical core count from lscpu output, and why is it not just `CPU(s)`?

Physical cores = deduplicated (core, socket) pairs: `lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l`, or `Core(s) per socket` × `Socket(s)`. `CPU(s)` counts logical CPUs — with SMT each core contributes two, so licensing per-core and performance-per-core analyses both understate or overstate by the SMT factor if you read `CPU(s)` naively.

### Q: What data sources does lscpu combine, and why is that better than parsing /proc/cpuinfo?

sysfs topology (`/sys/devices/system/cpu/*`: online state, core/socket/NUMA ids, cache sharing), `/proc/cpuinfo`, and architecture knowledge (s390 books, ARM clusters). `/proc/cpuinfo` is per-CPU, format varies by architecture, and contains no cache-sharing or online/offline interpretation; lscpu collapses it into a topology model and stable column/JSON interfaces — and `-s sysroot` can even do it for another root filesystem.

### Q: A security audit asks for the Spectre/Meltdown posture of the machine. Where does lscpu fit?

The `Vulnerability <name>: <status/mitigation>` rows summarize the kernel's per-issue assessment (e.g. "Mitigation: …; IBPB; STIBP"), complemented by flags like `ibrs`/`ssbd` showing microcode support. It is a quick first pass; the authoritative state remains in `/sys/devices/system/cpu/vulnerabilities/*` — same data lscpu renders, and what you cite when the rows are ambiguous.

### Q: How would you script "is AVX-512 available" for a deployment gate?

`lscpu | grep -q avx512f` — exit status as the gate (checking the Flags line), or parse `-J`/`-p` for inventory systems. Caveats: flags describe the *host* CPU under a VM (nested hypervisors can mask features), and kernel/hypervisor pinning can hide features from guests — so gate on the target environment's lscpu, not the build machine's.

### Q: What does `-x, --hex` change and when is a hex mask preferable to a CPU list?

`-x` renders CPU sets as hexadecimal bitmask strings (e.g. `0x000000000000000f`) instead of range lists (`0-3`). `taskset` consumes masks in its default mode (`taskset 0xf cmd`; `-c` switches it to lists), and affinity syscalls are mask-native. Prefer lists for humans and configs, masks for bit-logic (union = OR of masks) and API interop.

### Q: What exactly does lscpu read, and what does that imply inside containers?

Only kernel-exported files: sysfs CPU topology, online state, caches, and NUMA data, `/proc/cpuinfo`, and the vulnerabilities directory — no privileged calls, no direct hardware probing. Implication one: it reports *host* topology even when the container is cpuset-limited, so size workers with `nproc`/affinity instead. Implication two: `--sysroot` works — any directory tree with a plausible sysfs/proc layout can be analyzed, which is how you inspect a mounted disk image.

### Q: How would you find which CPUs share an L3 cache, and why does it matter for performance?

`lscpu -C` lists each cache instance with its shared-CPU list; equivalently, `cat /sys/devices/system/cpu/cpuN/cache/index*/shared_cpu_list`. It matters because it is the real partitioning the scheduler only partially respects: co-scheduled threads fighting over one L3 lose more than they gain from sharing cores, and cache-aware pinning (taskset/cgroups built from these lists) is the standard fix for noisy-neighbor latency.

### Q: A benchmark on a 2-socket box scales worse than expected. Which lscpu facts do you check first?

NUMA layout first: `-e=CPU,NODE` and the `NUMA nodeN CPU(s)` pairings — cross-node memory access explains most scaling surprises. Then `Thread(s) per core` (SMT contention means 2× CPUs is not 2× throughput), then L3 sharing via `-C` for cache thrash between workers. The output turns "it scales badly" into "workers 0-47 share L3 with the writer process" — an actionable statement.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lscpu.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
