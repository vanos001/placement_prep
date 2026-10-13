# top — interactive process viewer and task manager

## Overview

`top` is the standard live view of what a Linux system is doing: a continuously refreshing summary of load, CPU, and memory on top, and a sortable, filterable, killable table of processes below. It ships in the `procps` package at `/usr/bin/top` and is the one monitoring tool guaranteed to exist on every distro, minimal container, and rescue environment — which is exactly why interviews keep coming back to it.

`top` is often confused with `ps` (a point-in-time snapshot that exits immediately) and with `htop`/`btop` (richer interactive front-ends that must be installed separately). Nearly every number it displays is a formatted read of `/proc`: `/proc/loadavg`, `/proc/stat`, `/proc/meminfo`, and the per-PID files under `/proc/<pid>/`. There is no daemon and no sampling infrastructure — `top` is just a terminal UI over `/proc`.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 4.x) |
| Man section | 1 |
| Path | /usr/bin/top |
| First appeared | BSD, 1984 (William LeFebvre); rewritten for Linux by procps/procps-ng |
| Standards | None (not POSIX; Linux/BSD lineage) |

## Synopsis

```
top [options]
```

Common one-line forms:

```
top                  # interactive, default 3.0 s refresh on Debian
top -bn1             # one batch snapshot — the scripting workhorse
top -b -d 60 -n 60   # 60 samples, one per minute: a poor-man's logger
top -p 1,842         # track specific PIDs
top -u www-data      # filter the task list to one user
```

## How It Works

### Screen layout

`top` renders two areas every refresh interval (3.0 s by default on Debian; `-d` or the `s`/`d` keys change it):

```
┌─ summary area ────────────────────────────────────────────────┐
│ top - 15:33:31 up  7:42,  0 users,  load average: 0.00, 0.05, │  uptime + load
│ Tasks:   9 total,   1 running,   8 sleeping,   0 stopped,     │  task states
│ %Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,│  CPU split
│ MiB Mem :   4159.6 total,   2497.8 free,    609.5 used,       │  RAM
│ MiB Swap:      0.0 total,      0.0 free,      0.0 used.       │  swap
├─ task area ───────────────────────────────────────────────────┤
│   PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM    │  header
│     1 root      20   0    2564   1032    944 S   0.0   0.0    │  rows,
│   925 root      20   0  198384 171224  31600 S   0.0   4.0    │  sorted by
└───────────────────────────────────────────────────────────────┘  the sort key
```

Each refresh walks `/proc`, recomputes deltas against the previous sample (that is why the first batch sample of `%CPU` looks flat — there is no prior delta), and repaints. Nothing is averaged over minutes except the load numbers, which come straight from the kernel's own counters (see [uptime](./uptime.md)).

### /proc behind the screen

Every displayed number has a file behind it — a mapping worth internalizing because it turns `top` into a gateway for raw `/proc` debugging:

| Display element | Source |
| --- | --- |
| load average + uptime line | `/proc/loadavg` (and `/proc/uptime` for the clock) |
| `Tasks:` state counts | `/proc/<pid>/stat` state character, aggregated |
| `%Cpu(s)` split | `/proc/stat` `cpu` line, delta between samples |
| `MiB Mem` line | `/proc/meminfo` |
| `MiB Swap` line | `/proc/meminfo` (`SwapTotal`, `SwapFree`) |
| per-task `VIRT`/`RES`/`SHR` | `/proc/<pid>/statm` (page counts, scaled by page size) |
| per-task `%CPU` | delta of `utime + stime` in `/proc/<pid>/stat` |
| per-task `S` state, `NI`, `PR` | `/proc/<pid>/stat` |
| full `COMMAND` line | `/proc/<pid>/cmdline`; program name from `/proc/<pid>/comm` |

Two consequences: a container sees the host's `/proc` for most of these files, so `top` inside an unnamespaced container reports host-wide numbers; and any tool that can `cat /proc/stat` can reproduce `top`'s math.

### Summary area, line by line

```
top - 15:33:31 up  7:42,  0 users,  load average: 0.00, 0.05, 0.01
Tasks:   9 total,   1 running,   8 sleeping,   0 stopped,   0 zombie
```

- **Line 1** is the [uptime](./uptime.md) output verbatim: clock, uptime, session count, and the 1/5/15-minute load averages.
- **Line 2** classifies every task the kernel tracks: `running` (on a CPU), `sleeping` (waiting on an event), `stopped` (SIGSTOP/ptrace), `zombie` (exited, unwaited). Note what is *missing* as a category: `D`-state (uninterruptible) tasks are folded into "sleeping" here even though they are the interesting ones during I/O storms — `vmstat`'s `b` column is where they surface.
- **The `MiB Mem` line** shows `total, free, used, buff/cache` — the same four numbers as [free](./free.md), where "used" excludes the page cache and `buff/cache` is reclaimable. A high `used` with high `buff/cache` is healthy caching, not memory pressure.
- **The `MiB Swap` line** adds `avail Mem`, the kernel's estimate of how much can be handed out before swapping — usually much more than `free` alone, because cache can be reclaimed.

The `t`, `m`, and `l` keys collapse or re-style each of these groups, and procps 4.x offers an abbreviated graph mode (`%Cpu(s): 75.0/25.0 100[...]`) where the pair is user-vs-system and the bar is a visual total.

### Global commands

Single-key commands, pressed while `top` is in the foreground. The set interviews actually probe:

| Key | Effect |
| --- | --- |
| `h` | Help screen (then `1`/`2`/`3`... for more help levels in procps 4.x) |
| `q` | Quit |
| `Space` / `Enter` | Force an immediate refresh |
| `k` | Kill: prompts for PID, then signal number (default 15, SIGTERM) |
| `r` | Renice: prompts for PID, then nice value (default 0) |
| `z` | Toggle color display |
| `b` | Toggle bold/reverse-video highlighting (pairs with `z`) |
| `W` | Write current settings to `~/.toprc` (capital W — this is persistence) |
| `1` | Toggle per-core CPU lines instead of the aggregate `%Cpu(s)` line |
| `t` | Cycle the task/CPU summary display (4-way toggle) |
| `m` | Cycle the memory summary display |
| `l` | Toggle the load-average/uptime line |
| `c` | Toggle full command line vs program name |
| `H` | Show individual threads instead of processes |
| `i` | Toggle display of idle/zombie tasks |
| `u` / `U` | Filter by user name (prompted) |
| `f` | Field manager: add/remove/reorder columns, pick the sort field |
| `o` | Add an ad-hoc filter (`o` then e.g. `COMMAND=nginx`) |
| `s` / `d` | Change the refresh delay |
| `<` / `>` | Move the sort column left/right |

`k` and `r` are `top`'s claim to being a management tool, not just a viewer: they wrap `kill(2)` and `setpriority(2)` under your own privileges — you cannot use them to signal processes you do not own, and root's grace is what makes them useful. `k` defaults to signal 15 (SIGTERM), not SIGKILL — a polite default that still requires the target to cooperate, and typing an invalid PID or `<Esc>` at the prompt aborts. In secure mode (`-s`) both are disabled.

### The %Cpu(s) line, decoded

This is the interview centerpiece. A busy example:

```
%Cpu(s): 38.9 us,  4.6 sy,  0.0 ni, 54.0 id,  1.7 wa,  0.0 hi,  0.5 si,  0.3 st
```

| Field | Meaning | The story you should tell |
| --- | --- | --- |
| `us` | time running un-niced user processes | Application code in userland. High `us` = the work is CPU-bound in your own program. |
| `sy` | time running kernel code | Syscalls, page faults, network stack. High `sy` with low `us` suggests syscall- or lock-heavy workloads. Also absorbs guest CPU time. |
| `ni` | time running niced user processes | Userland time spent on processes with a modified nice value. |
| `id` | time spent in the kernel idle handler | True spare capacity. |
| `wa` | time waiting for I/O completion | The CPU *was idle* but had at least one task blocked on disk I/O. It is not consumed CPU — sustained high `wa` is a storage/NFS symptom, not a CPU shortage. |
| `hi` | time servicing hardware interrupts | Driver IRQ handling. |
| `si` | time servicing software interrupts | Deferred work: network RX softirq, timers. High `si` on a router/broker box is normal. |
| `st` | time stolen from this VM by the hypervisor | Only meaningful inside a virtual machine: the host scheduled another guest instead of yours. Persistent `st` = overcommitted host / noisy neighbor. |
| `gu` | guest time running KVM guest code | Shown by recent procps on kernels that report it; conceptually nested inside what older `sy` handling absorbed. |

Two corollaries worth memorizing: pressing `1` expands this into one line per core (per-core skew is invisible in the aggregate line), and `wa` counts as *idle-ish* time — a machine showing 90 `id` and 10 `wa` has CPU to spare but an I/O layer that cannot keep up.

### Task-area columns

```
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
  925 root      20   0  198384 171224  31600 S   0.0   4.0   1:39.23 python
```

| Column | Meaning |
| --- | --- |
| `VIRT` | Total virtual address space: code, data, mmap'd files, glibc arenas, reserved-but-untouched regions. Large `VIRT` is normal for JVMs and malloc-heavy programs and is not, by itself, a leak signal. |
| `RES` | Resident set: physical pages actually touched. This is the number to watch, and it is the numerator of `%MEM`. |
| `SHR` | The share of `RES` that is shared (shared libraries, shared memory segments). Two 500 MB services linking the same libs do not really own 1 GB. |
| `%CPU` | CPU share normalized per core: `200.0` = two full cores. Toggle the basis with the `I` key (Irix vs Solaris modes). |
| `%MEM` | `RES` / physical RAM. |
| `TIME+` | Cumulative CPU time with hundredths of a second. |
| `S` | State: `R` running, `S` sleeping, `D` uninterruptible sleep (almost always I/O), `T` stopped/traced, `Z` zombie. The `+` suffix means the task is in the *foreground* process group of its terminal. |

The `D` state matters beyond trivia: a `D` process ignores SIGKILL, so `k` appears to do nothing against it, and `D` tasks are counted into load average (see [uptime](./uptime.md)) even though they burn zero CPU.

### Sorting

The sort key defaults to `%CPU`. The three keys everyone must know — uppercase, case-sensitively:

```
Shift+P   sort by %CPU      (the default; P = Processor? no — P = percent CPU)
Shift+M   sort by %MEM      (M = memory)
Shift+T   sort by TIME+     (T = time)
```

`<` and `>` shift the sort column through the visible fields, `f` opens the field manager where the sort field can be chosen permanently, and the same choice is available non-interactively with `-o`:

```
top -bn1 -o %MEM | head -15     # batch snapshot sorted by memory
```

### Batch mode: -b -n -d

`-b` switches `top` from screen-painting to plain text, which is what makes it scriptable:

```
$ top -bn1 | head -12            # one snapshot, first screen
top - 15:33:31 up  7:42,  0 users,  load average: 0.00, 0.05, 0.01
Tasks:   9 total,   1 running,   8 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   4159.6 total,   2497.8 free,    609.5 used,   1248.1 buff/cache
MiB Swap:      0.0 total,      0.0 free,      0.0 used.   3550.1 avail Mem
```

`-n` caps iterations and `-d` sets the interval, so `top -b -d 60 -n 60 >> top.log` is a one-hour logger needing no cron job. One trap: batch output is capped at 512 columns unless `-w N` (or a terminal width) widens it — without that, the `COMMAND` column is truncated in logs.

A compact decision view:

```
need a live, killable view?            → top            (interactive)
need a snapshot in a script/report?    → top -bn1       (batch, 1 iteration)
need a time series to diff later?      → top -b -d S -n N  (batch, N samples)
need per-thread detail?                → top -H -p PID
need plain text columns for awk?       → ps            (top's columns move width-wise)
```

### Filtering

```
top -p 842            # one PID
top -p 1,842,925      # comma list (repeatable -p also works)
top -u www-data       # effective-UID match by name or number
top -U root           # any-UID match: real, effective, saved, fs
```

Inside a live session, `u` prompts for the same user filter and `o` applies free-form `FIELD=value` filters. Combining `pgrep` with `-p` is the standard "watch everything named X" idiom:

```
top -p $(pgrep -d, nginx)        # all nginx PIDs as one comma list
```

The sort field chosen interactively applies immediately; to make it permanent without pressing `W`, remember that `-o` accepts the column's exact name as displayed in the header (`%MEM`, `TIME+`, `COMMAND`), and `-o` can appear once with one field — for multi-level ordering there is the `f` field manager, not repeated `-o`.

### Windows: one top, four views

`procps` `top` maintains four independent task windows (field groups). `A` toggles between the normal full-screen view and the four-window split, `a`/`w` cycle which window is active, and each window carries its own sort key, columns, filters, and delay. This is what a persisted `~/.toprc` actually encodes — which is why restoring a colleague's `.toprc` can land you in a four-paned screen wondering where your process table went: press `A` to leave split mode.

### Configuration persistence: W and ~/.toprc

Pressing `W` writes the current layout — sort field, columns, delay, colors, per-window settings — to `~/.toprc`, and every future `top` starts that way. `procps` 4.x stores per-window settings (the four field groups behind `A`), so a saved `.toprc` can carry several different views. The failure mode is real: an `.toprc` written by a different procps generation can wedge `top` at startup, and the fix is simply deleting the file.

### top vs htop

| Aspect | top | htop |
| --- | --- | --- |
| Availability | Every distro and container (procps is a base package) | Usually needs installing |
| Batch mode | `-b -n -d`: scriptable, loggable | None — interactive only |
| Sorting/filter/kill | All present, keyboard-driven | Same, plus mouse |
| Tree view, search, per-core bars | Partial (`H`, `V`, `1`) | Richer defaults |
| Verdict | The universal baseline; the only option in minimal/rescue contexts | The comfort choice on machines you administer |

The interview framing: know `top` because it is always there and because its fields (`us/sy/id/wa/st`, `VIRT/RES/SHR`) are the shared vocabulary of every other monitor.

## Options That Matter

### Batch and sampling

| Option | Effect |
| --- | --- |
| `-b` | Batch mode: plain-text output, no screen control |
| `-n N` | Exit after N iterations (with `-b`, the log-length control) |
| `-d N[.m]` | Delay between refreshes (fractional seconds allowed) |
| `-w [N]` | Batch output width; default 512 columns in `-b` mode |

### Selection

| Option | Effect |
| --- | --- |
| `-p PIDS` | Monitor only these PIDs (comma list, repeatable) |
| `-u USER` | Match by effective UID (name or number) |
| `-U USER` | Match any UID variant: real, effective, saved, filesystem |
| `-H` | Threads mode: one row per kernel task |
| `-i` | Start with idle/zombie tasks hidden |

### Display

| Option | Effect |
| --- | --- |
| `-o FIELD` | Set the sort field (e.g. `-o %MEM`) |
| `-c` | Start showing full command lines |
| `-1` | Start with per-core CPU lines |
| `-E k|m|g|t|p` | Scale summary-area memory units |
| `-e k|m|g|t|p` | Scale task-area memory units |
| `-s` | Secure mode: disable `k`, `r`, and similar destructive keys |
| `-z` | Start with color enabled |

## Usage Patterns

```bash
# One-shot snapshot for a bug report or ticket
top -bn1 | head -20

# Top consumers by memory, batch mode
top -bn1 -o %MEM | head -15

# Follow one service's processes live
top -p $(pgrep -d, nginx)

# Isolate a misbehaving user's tasks
top -u deploy

# Log CPU hogs once a minute for an hour
top -b -d 60 -n 60 -o %CPU > /var/tmp/top-hour.log

# Per-thread view of one process (find the hot thread)
top -H -p 925

# Widen batch output so COMMAND is not truncated at 512 columns
top -bn1 -w 200 | cat

# Summary area in mebibytes instead of the default scaling
top -bn1 -E m | head -8

# Five two-second samples — second+ samples have real deltas
top -b -d 2 -n 5

# Safe inspection on a production box: no accidental kills
top -s

# Per-core balance check: is one core pegged while others idle?
#   start interactive, press 1 — or read the per-core lines in batch:
top -bn1 | sed -n '/^%Cpu[0-9]/p'

# Follow the memory pressure of one process family over time
top -b -d 10 -n 30 -p $(pgrep -d, python) >> python-mem.log

# Persist your layout once, interactively:
#   arrange columns, set sort key, delay, then press W  →  ~/.toprc
```

## Nuances and Gotchas

- **First-batch `%CPU` is unreliable.** In `-b` mode the first sample's per-task `%CPU` is computed without a prior delta; for meaningful numbers take two samples (`top -b -d 1 -n 2`) and read the second.
- **`%CPU` exceeds 100 by design** — it is per-core-normalized. A process at 250% is using 2.5 cores. The `I` toggle (Irix/Solaris modes) changes the scaling basis; expect confusion if screenshots disagree.
- **`wa` is not consumed CPU.** It is idle time that coincided with pending I/O. Troubleshoot it with storage tools ([vmstat](./vmstat.md) `b`/`wa`/`bi`/`bo`), not with CPU tools.
- **`st` only exists in VMs.** On bare metal it is 0 forever; in a guest, persistent `st` means the hypervisor is overcommitted. If you quote a `st` story on a bare-metal box, you have already lost the point.
- **`VIRT` is not a leak indicator.** Address-space reservations are cheap; watch `RES` and `%MEM`.
- **`D`-state tasks ignore SIGKILL.** `k` against them silently does nothing. They vanish only when the I/O they are blocked in completes (or the system is rebooted).
- **Sort keys are case-sensitive and collide with display toggles.** `Shift+M/P/T` sort; lowercase `t`/`m`/`l` toggle summary lines. Muscle-memory misses here scramble the screen instead of sorting it.
- **Batch width truncation.** `top -b` emits at most 512 columns unless `-w` widens it — long command lines silently lose their tails in logs.
- **`-u` vs `-U`.** `-u` matches effective UID only; a process running setuid will appear under the other user. Use `-U` for the full picture.
- **A stale `~/.toprc` from a different procps version can break startup.** Delete it rather than debug it.
- **Load average is not CPU%.** It counts runnable *and* uninterruptible tasks (Linux-specific) — see [uptime](./uptime.md) before equating `1.0` with "one core busy".
- **`top` inside a container reports the host.** `/proc/loadavg`, `/proc/stat`, and `/proc/meminfo` are not namespaced by default, so a container's `top` shows host-wide CPU and load; only the task list (via PID namespace) is container-local.
- **Interactive output cannot be redirected.** `top > file` (without `-b`) produces terminal control sequences and a mess. Batch mode exists precisely for this.
- **`k`/`r` prompts eat the next keypress.** After a kill or renice prompt, what you type next is input to `top`, not to your shell — reflexively typing a shell command at the PID prompt sends it nowhere or aborts the prompt.
- **`top` has no version flag.** Unlike its siblings (`watch -v`, `vmstat -V`, `free -V`), `top` rejects `-v` outright; `top -h` prints the usage text. Probe the procps-ng version with the package manager (`dpkg -l procps`) or another procps binary.

## Exit Status

| Code | When |
| --- | --- |
| 0 | Normal termination: `q`, or `-n` iterations completed in batch mode |
| 1 | Startup failure: bad option, invalid `-p` list, inability to open `/proc` or initialize the terminal |

Batch mode adds one practical rule: an interrupted `top -b` (SIGPIPE from `| head`, for instance) exits immediately without flushing a final summary — safe to truncate, but do not expect a closing line.

`top(1)` documents exit codes sparsely; scripts should parse batch output rather than trusting richer status semantics.

## Related Commands

- [`ps`](./ps.md) — point-in-time process table; `ps` for filtering, `top` for deltas over time.
- [`free`](./free.md) — memory breakdown behind the summary area's `MiB Mem` line.
- [`vmstat`](./vmstat.md) — the same CPU split (`us/sy/id/wa/st`) as a flat time series.
- [`pgrep`](./pgrep.md) / [`pkill`](./pkill.md) — build `top -p` lists and do the killing `k` does, by name.
- [`pidof`](./pidof.md) — map a program name to the PIDs you would otherwise hunt for in the task area.
- [Process management](../../admin/process-management.md) — signals, states, and priority where these keys come from.
- [procps overview](./overview.md) — the rest of the collection.

## Interview Questions

### Q: The %Cpu(s) line shows 40 wa. What do you do next?

`wa` means CPUs sat idle while at least one task had disk I/O pending — the CPU is not the bottleneck, storage is. Corroborate with `vmstat` (`b` column and `bi`/`bo` rates) or `iostat -x` for device utilization, check for fsync-heavy workloads or an NFS mount gone slow, and remember a single stuck `D`-state process can produce sustained `wa` while `id` remains high on the other cores.

### Q: A process shows VIRT 100G but RES 2G. Is it leaking?

No — at least not demonstrably. `VIRT` is the reserved address space: mmaps, glibc arenas, JVM heaps, thread stacks, much of it never touched. `RES` (2G) is physical memory actually resident and is what `%MEM` and the OOM killer care about. Growth of `RES` alongside stable `VIRT` is the pattern that indicates a real leak; `VIRT` alone can grow from a single large `mmap` with no memory cost.

### Q: Why can %CPU exceed 100, and what changes with the I toggle?

`%CPU` is normalized per core: 100% equals one full core, so a multithreaded process can show 800% on eight cores. Irix mode (default) uses that per-core scale; Solaris mode divides by the core count so the maximum is 100%. The underlying data never changes — only the presentation — which is why the same process can read 400% in one screenshot and 50% in another.

### Q: top shows one %CPU for a process, ps shows another. Why?

They measure different windows. `top` computes `%CPU` as a delta over its refresh interval (typically seconds), so it reflects *current* behavior — the number to watch live. `ps` computes `pcpu` as lifetime CPU time divided by elapsed wall-clock time since process start, so a process that did heavy work at startup shows a high `ps` value forever after, even while sleeping. Interviewers use this to test whether you know sampling windows matter.

### Q: You spot a st value of 8% in a VM. Interpret it.

`st` is steal time: CPU cycles the hypervisor assigned to another guest instead of yours. 8% means roughly one hour of every twelve is lost to host contention; everything else you measure (latency percentiles, throughput) inherits that noise. First move is confirming it is not your own saturation, then resizing the instance, migrating to a less-contended host, or escalating to the provider — application tuning cannot reclaim stolen time.

### Q: What does the W key do, and when does it bite?

`W` writes the current configuration — sort key, visible columns, delay, colors, per-window settings — to `~/.toprc`, making them permanent for that user. It bites when a config written by a different procps generation (or an experimental field layout) makes `top` misbehave or refuse to start; deleting `~/.toprc` resets to defaults. It also bites in shared accounts, where one person's saved sort field surprises everyone else.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/top.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
