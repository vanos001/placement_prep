# vmstat — virtual memory and system activity reporter

## Overview

`vmstat` is the classic flat time series of kernel activity: one line of fixed-width columns per sample, covering runnable and blocked processes, memory and swap movement, block I/O, interrupts, context switches, and the CPU split. It ships in the `procps` package at `/usr/bin/vmstat` (man section 8, because reporting on the system rather than manipulating it) and reads the same `/proc` sources as `top` — `/proc/stat`, `/proc/meminfo`, `/proc/vmstat` — but as terse columns instead of a screen.

It is often confused with `iostat` (sysstat package; per-device detail), `free` (memory only, point-in-time), and `top` (per-process view). The niche `vmstat` owns: *one command, whole-system, over time* — the first tool you run when a box is "slow" and you need to know whether the bottleneck is CPU, memory, swap, or disk. Its `r`/`b` columns and `si`/`so` swap columns are canonical interview vocabulary.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 4.x) |
| Man section | 8 |
| Path | /usr/bin/vmstat |
| First appeared | BSD (early 1980s); rewritten for Linux in procps/procps-ng |
| Standards | None (column meanings are Linux-specific) |

## Synopsis

```
vmstat [options] [delay [count]]
```

Common one-line forms:

```
vmstat 2            # sample every 2 s, forever
vmstat 1 5          # five one-second samples
vmstat -s           # since-boot counter summary
vmstat -d           # per-disk statistics
vmstat -p vda1      # one partition
vmstat -a 2         # add active/inactive memory columns
```

## How It Works

### Modes

`vmstat` has one default mode and several one-shot report modes:

| Invocation | Output |
| --- | --- |
| `vmstat [delay [count]]` | VM mode: the column table below, one line per sample |
| `vmstat -s` | Event counters since boot (memory, swap, CPU ticks, faults, forks) |
| `vmstat -d` | Per-disk read/write counters since boot |
| `vmstat -D` | Same, summarized into one line per disk-adjacent total |
| `vmstat -p DEV` | Statistics for one partition |
| `vmstat -m` | Slab allocator usage (from `/proc/slabinfo`) |
| `vmstat -f` | Just the fork count since boot |

The `delay`/`count` positionals belong to VM mode: `vmstat 2` samples every 2 seconds forever; `vmstat 1 5` takes five one-second samples and exits.

### The default columns, every one of them

Grounded output on this bookworm-era procps:

```
procs -----------memory---------- ---swap-- -----io---- -system-- -------cpu-------
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st gu
 0  0      0 2557312 187344 1091152    0    0     0     0  359  695  0  0 100  0  0  0
```

| Column | Meaning |
| --- | --- |
| `r` | Runnable processes: running on a CPU or waiting for run time — the instantaneous run-queue length |
| `b` | Processes blocked waiting for I/O to complete (kernel `D` state) |
| `swpd` | Swap memory currently used |
| `free` | Idle memory |
| `buff` | Memory used as buffers (block-device metadata) |
| `cache` | Memory used as page cache (includes tmpfs contents) |
| `si` | Memory swapped in **from disk per second** |
| `so` | Memory swapped out **to disk per second** |
| `bi` | Kibibytes received from block devices per second |
| `bo` | Kibibytes sent to block devices per second |
| `in` | Interrupts per second, including the clock |
| `cs` | Context switches per second |
| `us` | User time, non-kernel code (includes nice time) |
| `sy` | Kernel (system) time |
| `id` | Idle time |
| `wa` | Time waiting for I/O — CPU idle with I/O pending |
| `st` | Time stolen from a virtual machine by the hypervisor |
| `gu` | KVM guest time (shown by recent procps on kernels that report it) |

`vmstat -a` swaps `buff`/`cache` for `inact`/`active` (the LRU split from `/proc/meminfo`), which is more informative when judging whether cache is hot or stale. `-w` widens the columns so numbers never overlap; `-S k|K|m|M` changes display units (see Gotchas); `-t` prefixes each line with a timestamp — worth it for any log you plan to read later.

### Where the numbers come from

```
/proc/stat      → r (procs_running), b (procs_blocked),
                  us sy id wa st gu (cpu ticks), in (intr), cs (ctxt)
/proc/meminfo   → swpd free buff cache (or inact active with -a)
/proc/vmstat    → si/so (pswpin/pswpout), bi/bo (pgpgin/pgpgout, ×page→KiB)
```

This explains a subtle but interview-worthy distinction: `bi`/`bo` measure *page-cache* I/O (pgpgin/pgpgout), not per-device traffic — `vmstat -d` is where per-disk detail lives. It also explains the container caveat below: none of these files are namespaced, so `vmstat` inside a container reports the host.

### r and b vs load average

The single most testable distinction on this page:

```
load average (1/5/15 min)  =  exponentially damped average of
                              runnable (R)  +  uninterruptible (D) tasks
vmstat r                   =  instantaneous count of runnable (R) tasks
vmstat b                   =  instantaneous count of uninterruptible (D) tasks
```

Load average folds both populations into one smoothed number (Linux-specific — see [uptime](./uptime.md)); `vmstat` shows them separately and unsmeared. That split is diagnostic: `r` high with `id` low is a CPU shortage; `b` high with `wa` high and `r` low is a storage problem that would show up as an unfairly high load average. Run `vmstat 1` and `uptime` side by side and you can watch the difference.

### The first line is not a sample

```
$ vmstat 1 3
procs -----------memory---------- ---swap-- -----io---- -system-- -------cpu-------
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st gu
 1  0      0 2556668 187344 1090756    0    0     2   131  428    4  1  0 99  0  0  0
 0  0      0 2556452 187344 1090824    0    0     0    64  454  856  0  0 100  0  0  0
 0  0      0 2556496 187344 1090824    0    0     0     0  421  702  0  0 100  0  0  0
```

Line 1 of data is the *average since boot*, not the current state. On a long-uptime server those since-boot averages are mush that hides everything interesting. Always read from line 2 onward, or suppress the first report entirely with `-y` on recent procps. This misread is the number-one `vmstat` bug in scripts and blog posts.

### swpd nonzero vs si/so nonzero

Two different alarms that look similar:

- `swpd` = how many pages are *parked* in swap right now. Nonzero is normal on a system that ever came under memory pressure; those pages can sit there for weeks with zero cost.
- `si`/`so` = pages *moving* right now. Nonzero, sustained, means swapping is happening — memory was needed and the kernel chose (or was forced) to reclaim anonymous pages via disk.

The alert is `si + so > 0` persistently while `free` is low, not `swpd > 0`. A brief `so` burst during a large file copy can be reclaim behavior, not catastrophe.

### The one-shot report modes

`vmstat -s` prints the kernel's cumulative counters — the same numbers VM mode divides by time:

```
$ vmstat -s
      4259396 K total memory
       626032 K used memory
       584252 K active memory
      2555700 K free memory
       187344 K buffer memory
      1090824 K swap cache
            0 K total swap
        36706 non-nice user cpu ticks
        23008 system cpu ticks
      5479943 idle cpu ticks
          210 IO-wait cpu ticks
```

`vmstat -d` gives per-disk counters since boot (reads: total/merged/sectors/ms, writes likewise, then I/O time):

```
$ vmstat -d | head -4
disk- ------------reads------------ ------------writes----------- -----IO------
       total merged sectors      ms  total merged sectors      ms    cur    sec
vda     4644      2  115762    1054  64458 737420 7305344  163875      0      9
```

Both are snapshots at invocation time — diff two invocations to get rates, or just run VM mode and let it do the arithmetic.

### Reading the shapes

Four load signatures recur so often they are worth memorizing as column shapes:

```
CPU-bound        r high | us high, id low          → find the culprit in top
I/O-bound        b high | wa high, bi/bo high      → storage, NFS, fsync storms
memory-thrashing si/so high, free low, swpd rising → add RAM or cap the workload
interrupt-heavy  in/cs high | si high, us modest   → network RX, timers, IRQ balance
```

A fifth shape — `r` low, `b` moderate, load average huge — is the stuck-`D`-state signature described in the `r`/`b` section above. None of these shapes tell you *which process*; `vmstat` tells you what kind of problem exists, and [top](./top.md) or `ps` names the offender.

## Options That Matter

| Option | Effect |
| --- | --- |
| `delay [count]` | Seconds between samples; with count, stop after that many samples |
| `-a` | Show `inact`/`active` memory instead of `buff`/`cache` |
| `-S k|K|m|M` | Scale memory columns: lowercase = 1000-based, uppercase = 1024-based |
| `-w` | Wide output — no column truncation/overlap on wide values |
| `-t` | Timestamp each sample line |
| `-y` | Skip the first (since-boot) report (recent procps) |
| `-s` | Since-boot summary: counters, CPU ticks, paging events, forks |
| `-d` / `-D` | Per-disk statistics / summarized disk totals |
| `-p DEV` | Partition-level statistics |
| `-m` | Slab info — kernel object caches (dentry, inode, buffers) |
| `-f` | Fork count since boot |
| `-n` | Print the header only once in continuous mode |

## Usage Patterns

```bash
# Steady-state watch: read from the SECOND data line
vmstat 2

# Exactly five samples, then exit — for a ticket attachment
vmstat 1 5

# Is the box swapping right now? (data lines start at line 4)
vmstat 1 5 | awk 'NR>3 && ($7+$8)>0 {print $NF}'

# Memory pressure triage: swpd climbing, si/so active, free shrinking
vmstat -w -t 5

# Since-boot counters in one screenful
vmstat -s

# Which disk is busy — per-device counters
vmstat -d

# One partition only
vmstat -p vda1

# Kernel slab blowup check (dentry/inode caches after file churn)
vmstat -m | head -15

# Hot vs cold cache, with the LRU split
vmstat -a 2

# Human units, wide, timestamped — the loggable form
vmstat -w -S m -t 2 60 >> /var/tmp/vmstat-night.log

# Fork-rate over 10 s — delta of the -f counter
prev=$(vmstat -f | awk '{print $1}'); sleep 10
awk -v p="$prev" -v n="$(vmstat -f | awk '{print $1}')" 'BEGIN {print (n-p)/10 " forks/sec"}'
```

## Nuances and Gotchas

- **The first data line is since-boot averages.** Filter it (`NR>3` in awk) or use `-y`. Every misdiagnosis of "we have 99% idle since boot" traces back here.
- **`k` vs `K` in `-S` are different bases** — `k` = 1000 bytes, `K` = 1024. Picking `-S k` and comparing against `free`'s KiB numbers quietly skews everything by 2.4%.
- **`wa` is not CPU consumption.** It is idle time that coincided with pending I/O. High `wa` says "storage slow", never "CPU busy" — and it does not appear in `us`+`sy`.
- **`r` is instantaneous, not smoothed.** A 1-second sample can miss a 200 ms burst entirely; conversely a single busy web worker makes `r=1` look like "queue empty" when latency is terrible. Watch several samples, or several sources.
- **`b` counts `D`-state tasks**, which ignore SIGKILL. High `b` with stuck processes points at NFS, FUSE, or failing storage — not at killable workloads.
- **`bi`/`bo` are cache I/O, not device I/O.** For per-device attribution use `vmstat -d` or `iostat -x`; `bo` also counts page cache writeback, which may not be a bottleneck at all.
- **`st` only means something in a VM.** On bare metal it is always 0; in a guest, persistent `st` = hypervisor overcommit, and no amount of guest tuning gets those cycles back.
- **Containers see the host.** `/proc/stat` and `/proc/meminfo` are not namespaced by default, so `vmstat` in a container measures the host — useless for per-container analysis.
- **Column meanings are Linux-specific.** AIX/Solaris `vmstat` have `pi`/`po` (paging) and different `sr` semantics; online advice for those Unices does not transfer.
- **`vmstat -d`/`-s`/`-m` are cumulative since boot** — they are for diffing or one-shot triage, not rates.

## Exit Status

| Code | When |
| --- | --- |
| 0 | Samples collected and printed successfully |
| 1 | Bad arguments, unparseable delay/count, or failure opening a `/proc` source |

`vmstat(8)` does not formally document exit codes; treat nonzero as "nothing useful was printed".

## Related Commands

- [`top`](./top.md) — per-process view of the same CPU split; `vmstat` for the system, `top` for the culprit.
- [`free`](./free.md) — the memory columns (`swpd free buff cache`) in a friendlier layout.
- [`uptime`](./uptime.md) — the smoothed average of roughly `r + b`, over 1/5/15 minutes.
- [`pidof`](./pidof.md) — attach names to the PIDs behind the `r` queue.
- [`ps`](./ps.md) — find *which* processes are in `R` or `D` state (`ps -eo stat,comm | grep '^D'`).
- [Process management](../../admin/process-management.md) — task states behind the `r` and `b` columns.
- [procps overview](./overview.md) — the rest of the collection.

## Interview Questions

### Q: Load average is 20 but vmstat shows r=1, b=19, id=90. What is happening?

Nineteen tasks are in uninterruptible sleep (`b=19`), almost certainly blocked on storage or NFS, while CPUs are nearly idle (`id=90`). Linux's load average counts `D`-state tasks, so the load number looks catastrophic while the CPU story is fine. The fix is storage-side: check `wa`, `bi`/`bo`, device utilization, and what `ps -eo stat,pid,comm | grep '^D'` is stuck on. This scenario is also why Linux load averages cannot be compared naively with other Unixes, which count only runnable tasks.

### Q: swpd is 2 GB but si/so are 0. Is the system swapping?

No — swapping *happened* at some point and 2 GB of pages remain parked in swap, costing nothing until they are touched. The live alarm is `si`/`so` activity: sustained nonzero values mean pages are moving between RAM and disk right now, i.e. the working set exceeds what memory can hold. Judgment about memory sizing should follow `si`/`so` plus `free`/`avail`, never `swpd` alone.

### Q: What does the first line of `vmstat 1 10` mean, and why does it matter?

It is the average since boot, not a current sample — `vmstat` has no prior data point to diff against, so it reports cumulative averages. On a server up for months, that line smooths every spike into oblivion and routinely hides the exact problem you are investigating. Scripts must skip it (or use `-y` on recent procps), and humans should read from the second data line onward.

### Q: Explain the difference between r high and b high.

`r` counts runnable tasks — things that want CPU and will get it as soon as a core frees up; high `r` against core count means CPU contention, and the remedy is faster code, more cores, or a concurrency limit. `b` counts uninterruptible `D`-state tasks — processes frozen mid-syscall, typically disk or NFS I/O; high `b` with high `wa` means the CPUs are starving for data, and more CPU power changes nothing. Same "slow system", opposite bottleneck, opposite remediation.

### Q: What is the st column and where does it come from?

`st` is steal time: the fraction of CPU time the hypervisor gave to another guest instead of this virtual machine. The kernel learns it from the hypervisor (via paravirt clock sources) and reports it in `/proc/stat`; prior to Linux 2.6.11 it did not exist, and the field may be absent on some kernels. Persistent `st` means host overcommit — the guest-side remedy is resizing or migrating, not tuning, because those cycles never existed for you.

### Q: Where does vmstat get its numbers, and what limitation follows from that?

From `/proc/stat` (runnable/blocked counts, CPU ticks, interrupt and context-switch counters), `/proc/meminfo` (memory columns), and `/proc/vmstat` (swap-in/out and page-in/out rates). Because none of those files are namespaced for containers, `vmstat` running inside a container reports host-wide figures — a per-container memory or CPU story requires cgroup files (`/sys/fs/cgroup/...`) or namespaced tooling instead.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/vmstat.8.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
