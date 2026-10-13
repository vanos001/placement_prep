# free — report system memory usage

## Overview

`free` prints the system's memory and swap totals in a single, instantly recognizable table: how much RAM exists, how much is used, how much is truly unused, how much is cache, and — the column everyone should read — how much is *available* for new work. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/free`, and its entire input is one parse of `/proc/meminfo`.

`free` is the tool behind the most common Linux memory question: "why is all my memory used?" The answer is in the distinction between the `free` and `available` columns, and between memory that is *used* and memory that is *merely occupied by cache*. `free` is often confused with `top` (per-process view), `vmstat` (trend view with si/so swap traffic), and `df` (disk space — the "-h" habit makes people mix them up under pressure).

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/free |
| First appeared | early 1990s with Linux procps (Linux-specific) |
| Standards | none; Linux-only, column layout is a de-facto convention |

## Synopsis

```
free [options]
```

Common one-line forms:

```
free -h           # human-readable, the interactive habit
free -m           # mebibytes, the scripting habit
free -h -s 5      # refresh every 5 seconds
free -h -w        # wide: split buff/cache into buffers + cache
free -t -m        # append a RAM+swap total row
```

## How It Works

### The anatomy of the output

```
$ free -h
               total        used        free      shared  buff/cache   available
Mem:           4.1Gi       610Mi       2.4Gi        52Ki       1.2Gi       3.5Gi
Swap:             0B          0B          0B
```

One `Mem:` row for physical RAM, one `Swap:` row for swap space. With `-t`, a `Total:` row sums both. Each number is a policy decision, not a raw kernel counter — the mapping from `/proc/meminfo` is documented below.

### The mapping to /proc/meminfo

`free` does no kernel magic; it reads `/proc/meminfo` once per refresh. The columns are derived fields:

| Column | Source in /proc/meminfo |
| --- | --- |
| `total` | `MemTotal` (or `SwapTotal` for the swap row) |
| `used` | calculated as `total - available` in modern procps |
| `free` | `MemFree` (or `SwapFree`) |
| `shared` | `Shmem` — mostly tmpfs/POSIX shared memory |
| `buffers` | `Buffers` — kernel block-device buffers, mostly metadata |
| `cache` | `Cached + SReclaimable` — page cache plus reclaimable slab |
| `buff/cache` | sum of the two above |
| `available` | `MemAvailable` (kernel 3.14+; emulated on 2.6.27+, else equals `free`) |

Two consequences worth internalizing:

- **`used = total - available`, not `total - free - cache`.** Recent procps versions redefined `used` this way, so `used` now includes unreclaimable slab and other kernel memory that older formulas lumped into cache. Old scripts that compute `total - free - buff/cache` will disagree with the `used` column — and the `free` column is the one that is "wrong" for capacity planning, not `used`.
- **`free` is almost never the interesting number.** Unused RAM is wasted RAM; the kernel fills it with page cache. The kernel reclaims that cache instantly on demand, which is exactly what `available` estimates.

### available vs free — the interview question

`MemFree` counts pages that are *nobody's*: truly untouched memory. `MemAvailable` is the kernel's estimate of how much memory it could hand to a new userspace process **without swapping**, counting:

- all of `MemFree`, plus
- active/inactive *file* pages (page cache) it can drop or write back, plus
- `SReclaimable` slab it can shrink,

minus reserves it must keep for root and kernel operation (watermarks, lowmem reserves).

```
MemFree:         2556124 kB     <- truly unused
MemAvailable:    3634104 kB     <- what apps can realistically get
```

The gap here — roughly 1 GiB of cache the kernel would release under pressure — is why a machine showing `free: 200 MiB, available: 20 GiB` is perfectly healthy. On kernels older than 3.14 `MemAvailable` did not exist; userspace emulated it (procps computes an approximation for 2.6.27+), and on anything older `available` simply equals `free`.

### The raw input, annotated

`free` is a thin formatter; learning to read `/proc/meminfo` directly pays off whenever a dashboard and `free` disagree:

```
MemTotal:        4259396 kB     # total usable RAM (minus reserved/kernel binary)
MemFree:         2556124 kB     # truly unused
MemAvailable:    3634104 kB     # the allocatable estimate free(1) reports
Buffers:          187344 kB     # block-device metadata buffers
Cached:           601168 kB     # page cache
SwapCached:            0 kB     # swapped-out pages also cached in RAM
Active:           584400 kB     # recently used; not first-choice evictions
Inactive:         563884 kB     # eviction candidates
Active(anon):   Anonymous memory (heap, stacks) recently used
Inactive(anon): Anonymous memory candidates — swap-out fodder
Active(file):   Page cache recently used
Inactive(file): Page cache eviction candidates
Dirty:                 0 kB     # modified cache awaiting writeback
Writeback:             0 kB     # currently being written back
AnonPages:        340912 kB     # anonymous pages mapped into processes
Mapped:            86980 kB     # file-backed mappings (libs, mmap'd files)
Shmem:                52 kB     # tmpfs/shmem -> free(1)'s 'shared'
Slab:             533364 kB     # kernel object caches, total
SReclaimable:     489972 kB     # slab portion that can be shrunk
SUnreclaim:        43392 kB     # slab that never shrinks
```

`Active`/`Inactive` splits (anon vs file) are how the kernel answers "what do I evict first?": file pages can simply be dropped or written back, anonymous pages must go to swap. `MemAvailable` is computed from exactly these buckets — which is why it is an estimate with real semantics, not a marketing number.

### Reading trends, not snapshots

A single `free` line answers "am I OK *right now*". The interesting operational questions are trends: is `available` monotonically declining (leak), is `Dirty` spiking (write burst), is `SwapCached` growing while swap-used shrinks (pages coming home)? For rate-based answers pair `free -s` with `vmstat` — `free` shows levels, `vmstat` shows flows (`si`/`so` swap-in/out per second, `bi`/`bo` block IO).

### buff/cache: what is actually in there

The combined `buff/cache` column (modern procps merged `buffers` and `cache` into one column; `-w` splits them again) contains:

- **Page cache** — file contents the kernel keeps in RAM for read/write speedup. Reclaimable at any time (dirty pages must be written back first, which is what `Dirty`/`Writeback` in meminfo track).
- **Buffers** — block-device-level buffers, historically metadata-heavy.
- **SReclaimable** — the portion of kernel slab (dentry/inode caches and friends) that can be shrunk.

None of it is "used" in the sense of being lost: on memory pressure the kernel evicts clean cache immediately. This is why `used` going up and `buff/cache` staying large is normal, and why alerting on `free` memory is an anti-pattern — alert on `available`.

### Swap rows and swap accounting

The `Swap:` row reads `SwapTotal`/`SwapFree`. Swap used (`total - free` on the swap row) is not automatically bad: long-idle anonymous pages migrated to swap cost nothing while they stay untouched. What hurts is *active* swap traffic — watch `vmstat`'s `si`/`so` columns, not `free`'s static swap figure. `SwapCached` counts swapped-out pages still cached in RAM (a good thing: re-swapping is free).

The swap row follows the same column discipline as `Mem:` — `total`, `used`, `free` — but `shared`, `buff/cache`, and `available` are meaningless there and print zero. With `-t`, the added `Total:` row sums RAM and swap, which is mostly useful for spotting the pathological case where `total` RAM is nearly exhausted and swap is carrying a real share of anonymous memory.

### Units: kibi, mebi, and the --kilo trap

| Option | Base | Effect |
| --- | --- | --- |
| `-b` | bytes | exact bytes |
| `-k` (default) | 1024 | kibibytes |
| `-m` | 1024 | mebibytes |
| `-g` | 1024 | gibibytes |
| `--kilo`, `--mega`, `--giga`, `--tera`, `--peta` | **1000** | decimal SI units |
| `--si` | 1000 | human-readable with SI powers |
| `-h` | 1024 | human-readable (Ki/Mi/Gi suffixes) |

`--kilo` means "print in kilobytes with 1000-base division", *not* "the same as `-k`". Comparing `free --mega` output against `free -m` output will differ by ~2.4% — a subtle trap when correlating with monitoring systems that use one or the other.

### Refreshing, totalling, wide, committed

- `-s N` reprints every N seconds; `-c N` stops after N prints (`-s 2 -c 5` = five samples two seconds apart). Without `-s`, `-c` alone still refreshes once per second.
- `-t` appends a `Total:` row of RAM + swap.
- `-w` switches to wide mode, splitting `buff/cache` into separate `buffers` and `cache` columns.
- `-v` prints committed memory: `Committed_AS` vs `CommitLimit` — the overcommit pressure gauge.
- `-L` prints a single machine-friendly line; `-l` (legacy) shows low/high memory statistics relevant only on ancient split-memory kernels.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-h, --human` | human-readable with binary suffixes (Ki, Mi, Gi) |
| `-b / -k / -m / -g` | bytes / kibi / mebi / gibibytes (1024 base) |
| `--kilo / --mega / --giga / --tera / --peta` | fixed unit with **1000** base |
| `--si` | human-readable with 1000 base (kB, MB, GB) |
| `-w, --wide` | split buff/cache into buffers + cache columns |
| `-s, --seconds N` | repeat print every N seconds |
| `-c, --count N` | print N times, then exit (pairs with `-s`) |
| `-t, --total` | append RAM+swap total row |
| `-v, --committed` | show committed memory vs commit limit |
| `-L, --line` | single-line output |
| `-l, --lohi` | legacy low/high memory detail |

## Usage Patterns

```bash
# The habitual check: is this machine healthy right now?
free -h

# The scripting check: stable integer mebibytes, compare against thresholds
free -m | awk '/^Mem:/ {print $7}'

# Print only the available value in MiB (what alerting should use)
free -m | awk '/^Mem:/ {print "available MiB:", $7}'

# Sample memory every 2 seconds, five times, while running a load test
free -m -s 2 -c 5

# See buffers and cache separately
free -h -w

# Include swap in a grand total
free -h -t

# Check overcommit pressure (Committed_AS vs CommitLimit)
free -v

# Compare decimal (SI) output against a monitoring dashboard that uses MB
free --si

# One-line output for logging pipelines
free -L -m

# Watch available memory collapse during an OOM experiment
watch -n 1 free -m

# Extract raw MemAvailable the way free computes it
grep MemAvailable /proc/meminfo

# Health-check snippet for CI: fail if available drops under 256 MiB
[ "$(free -m | awk '/^Mem:/ {print $7}')" -gt 256 ] || exit 1

# Compare two samples around a workload to measure its cache footprint
free -m -s 1 -c 2 | grep Mem:

# Decide whether a box can take another JVM of size X
free -m | awk -v need=4096 '/^Mem:/ {exit !($7 > need)}'

# How much swap is actually consumed, in MiB
free -m | awk '/^Swap:/ {print $3}'

# Log a memory sample every 10 seconds to a file during an incident
free -m -s 10 >> /tmp/memlog.txt

# Wide output to see whether growth is in buffers or in cache
free -h -w | head -2
```

## Nuances and Gotchas

- **Never alert on the `free` column.** Low `free` with high `available` is the normal, healthy state of a Linux system; the kernel is using spare RAM as cache. Capacity alarms belong on `available`.
- **`used = total - available` in modern procps.** Anyone reconciling `used` against `total - free - buff/cache` will see a mismatch — the definition changed, not the kernel. Document the formula in runbooks.
- **`--kilo`/`--mega` are 1000-based, `-k`/`-m` are 1024-based.** Mixing them produces numbers that are close enough to pass a glance and wrong enough to break comparisons.
- **`available` can be zero or equal to `free` on old kernels.** `MemAvailable` needs kernel 3.14+; procps emulates it on 2.6.27+ but genuinely ancient kernels just report `free`.
- **`shared` is tmpfs, not "shared libraries".** It counts `Shmem` (tmpfs files, POSIX shm). Shared library pages show up in each process's RSS, not here.
- **Cache is not instantly all-reclaimable.** Dirty pages must be written back, locked pages (`mlock`) cannot move, and some slab (`SUnreclaim`) never shrinks — which is precisely why `available` is an *estimate* and not a sum you can reproduce by adding two meminfo lines.
- **`-s` without `-c` runs forever.** In scripts and CI, always pair it (`-s 2 -c 1` for a delayed single sample) or you hang the pipeline.
- **Container caveat.** Inside a container, `/proc/meminfo` typically shows the *host's* memory, not the cgroup limit — `free` in Docker/Kubernetes reports host numbers. Use cgroup files (`/sys/fs/cgroup/memory.current` or the v1 `memory.usage_in_bytes`) for container-scoped truth.
- **The numbers are a snapshot of a moving target.** Two consecutive `free` runs rarely agree; when comparing before/after a change, sample several times (`-s 1 -c 5`) and compare medians.
- **`Dirty`/`Writeback` are the missing context behind cache spikes.** A huge `buff/cache` right after `cp bigfile /mnt/nfs` is dirty pages awaiting writeback; the memory is only reclaimable once IO drains. If `Dirty` stays high on a slow device, cache pressure becomes real pressure.
- **`available` estimates have variance under fragmentation.** On long-running boxes with fragmented memory, `MemAvailable` can overstate what a huge-order allocation will actually get; low-order allocations are fine, but allocating a 1 GiB hugepage can still fail while `available` shows room.
- **`free -h` column widths shift with magnitude.** `awk` field positions on human output break when a value crosses into the next unit; machine parsing belongs on `-m`/`-b`, not `-h`.
- **A swap row of zeros does not prove swap is disabled.** With no swap configured, `SwapTotal` is 0 and the row prints zeros — but a swap *file* added without `swapon` also leaves the row flat. Confirm actual swap devices with `swapon --show` or `/proc/swaps` before believing "no swap in use" means "no swap exists".
- **`-v` is a procps 4.x-era addition.** Older releases lack `--committed`; scripts using it fail on the LTS-era 3.3.x still common on older distros. Feature-test with `free --help | grep -q committed` if the script must be portable.

## Exit Status

- `0` — success, including when swap is entirely absent (the swap row prints zeros).
- Non-zero — only on genuine failures such as an invalid option or being unable to read `/proc/meminfo`; the man page documents no finer breakdown.

## Related Commands

- [`ps`](./ps.md) — per-process RSS/VSZ; free is the system-wide rollup of the same memory.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — where memory pressure, the OOM killer, and cgroups fit into process administration.

## Interview Questions

### Q: What is the difference between the `free` and `available` columns, and which should you monitor?

`free` (`MemFree`) counts pages nobody is using at all; `available` (`MemAvailable`) estimates how much memory the kernel could grant to new processes without swapping — free pages plus reclaimable page cache and reclaimable slab, minus kernel reserves. Since Linux aggressively uses spare RAM for cache, `free` is normally small on a healthy system and is meaningless for capacity. `available` is the monitorable number: low `available` means real pressure, high `free` just means an idle cache.

### Q: A manager says the server is out of memory because `used` is 95%. How do you respond?

Show the full `free -h`: if `buff/cache` is large and `available` is healthy, the memory is mostly page cache the kernel will evict on demand, and `used` being `total - available` includes exactly that reclamation headroom. The system is doing what Linux is designed to do — cache everything it can. Real trouble looks like low `available`, growing swap `si`/`so` traffic in `vmstat`, and OOM killer events in `dmesg`.

### Q: Why is swap in use while `free` shows gigabytes of free memory?

Swap residency and memory pressure are different axes. The kernel proactively swapped out long-idle anonymous pages days ago; they cost nothing while untouched, and their RAM was freed for cache. This is normal paging policy, not thrashing. Pathology is *active* swap traffic — `vmstat` showing sustained non-zero `si`/`so` — not a static swap-used figure in `free`.

### Q: What does the `buff/cache` column actually contain, and is it safe to reclaim?

Page cache (file contents), `Buffers` (block-device metadata buffers), and `SReclaimable` (shrinkable kernel slab like dentry/inode caches). Clean entries are dropped instantly on demand; dirty pages must be written back first; locked pages and unreclaimable slab stay. That is why the kernel reports `available` as an estimate instead of letting you sum the column — reclamation is conditional, and `free`'s author does not pretend otherwise.

### Q: Why would `free` inside a Docker container report the host's memory, and what should you use instead?

`/proc/meminfo` is a virtual file the kernel populates system-wide; containers do not get a per-cgroup rendering of it (without lxcfs-style tricks), so `free` shows host totals regardless of cgroup limits. For container truth, read cgroup accounting: `/sys/fs/cgroup/memory.current` (v2) or `memory.usage_in_bytes` (v1), plus the limit in `memory.max`. This is a common Kubernetes on-call confusion: the pod "runs out" while `free` claims gigabytes remain.

### Q: What changed in how procps computes the `used` column, and why does it matter for dashboards?

Older procps computed `used` as `total - free - buff/cache - shared`; modern versions compute `used = total - available`, which pushes unreclaimable kernel memory (like `SUnreclaim` slab) into `used` instead of hiding it in cache. Dashboards upgraded in place therefore show a step-change in `used` that is a definitional change, not a memory leak. When reconciling graph against graph across hosts, confirm both sides use the same formula — or plot `available` instead, which is the number with stable semantics.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/free.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
