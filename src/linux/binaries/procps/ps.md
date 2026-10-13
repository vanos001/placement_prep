# ps — snapshot of running processes

## Overview

`ps` reports a point-in-time snapshot of processes: who they belong to, what state the kernel has them in, how much memory and CPU they consume, and what command line they were started with. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/ps`, and reads everything straight from `/proc` — there is no daemon and no persistent state.

The single most important thing to understand about `ps` is that it carries **two option syntaxes side by side**: the POSIX style with a leading dash (`ps -ef`) and the BSD style without one (`ps aux`). The same letter means different things depending on whether a dash precedes it (`ps u` is a format, `ps -u root` is a filter), which is why `ps` help output groups flags into "Basic", "Selection", "Output formats" families. Interviewers test this constantly.

`ps` is often confused with `top` (continuous refresh, interactive) and `htop` (interactive tree view); `ps` is the scripting tool — one shot, stable columns, pipeable. It is also confused with `/proc` itself: `ps` is just a formatter over `/proc/<pid>/stat`, `/proc/<pid>/status`, and `/proc/<pid>/cmdline`.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/ps |
| First appeared | AT&T UNIX Version 4 (1973); BSD flags via BSD lineage |
| Standards | POSIX.1-2018 (`ps`); procps-ng adds BSD and GNU extensions |

## Synopsis

```
ps [options]
```

Common one-line forms:

```
ps -ef                 # POSIX: every process, full format
ps aux                 # BSD: every process, user-oriented format
ps -eo pid,%cpu,cmd    # custom columns for all processes
ps -u alice -f         # all processes owned by alice, full format
ps -p 1234 -o pid,stat,vsz,rss,cmd
ps -e --forest         # ASCII process tree
```

## How It Works

### One binary, two personalities

`ps` decides how to interpret its arguments by looking at the first character. Options with a leading dash are parsed with UNIX98/POSIX semantics; options without a dash get BSD semantics. GNU long options (`--forest`, `--sort`) are a third, always-dashed family. The trap is that letter meanings shift between personalities:

```
ps u         # 'u' = user-oriented OUTPUT FORMAT (USER %CPU %MEM VSZ RSS ...)
ps -u root   # '-u' = SELECT processes by effective user
ps p 1,2     # bare 'p' = select by PID list
ps -p 1,2    # same selection, dash form
```

Because the two parsers are independent, mixing is legal and common:

```
ps ax        # BSD 'a' + 'x': all processes, with and without a tty
ps axu       # same selection, user-oriented format
ps -ef       # POSIX: everything, full format
ps -eF       # POSIX: everything, extra-full format
```

A rule of thumb worth memorizing: `ps aux` for interactive exploration, `ps -ef` when POSIX portability matters (AIX, Solaris, minimal busybox), `ps -eo ...` when you want exact columns for scripts.

### What is shown by default

Bare `ps` shows only *your* processes attached to *your* terminal — historically the shell's process group. This surprises people who expect `ps` alone to be a system-wide view:

```
$ ps
    PID TTY          TIME CMD
   8333 pts/0    00:00:00 bash
   8400 pts/0    00:00:00 ps
```

`-e` (or `-A`, or BSD `ax`) lifts both limits and shows every process on the system that your user is allowed to see.

### Selection: choosing which processes

Selection options combine with AND; arguments within one option are comma- or blank-separated lists that act as OR:

```
ps -p 4711,4712        # specific PIDs
ps -u root,nobody      # effective user is root OR nobody
ps -U root             # REAL user id (matters after setuid/sudo)
ps --ppid 909          # children of PID 909
ps -t pts/2            # processes on that terminal
ps -C nginx            # by command name
ps -e --deselect -u root   # everything except root's processes
```

`-u` selects by **effective** UID, `-U` by **real** UID. After `sudo cmd`, the shell has real=effective=you, while the sudoed process has real=you, effective=root — so `ps -u root` shows it, `ps -U root` does not. `--ppid` is the cheapest way to walk a parent/child relationship in scripts.

Negation is `--deselect` (or `-N`): it inverts the whole selection.

### Output control: `-o` and specifiers

`-o` (POSIX form) takes a comma-separated list of format specifiers; each becomes a column in the order given:

```
$ ps -o pid,ppid,user,%cpu,%mem,stat,vsz,rss,etime,cmd -p 2
  PID  PPID USER     %CPU %MEM STAT    VSZ   RSS     ELAPSED CMD
    2     1 root     0.0  1.1 Sl+  1267756 48980 07:43:58 caddy run ...
```

Frequently used specifiers: `pid`, `ppid`, `user` (effective name), `group`, `stat`, `%cpu`, `%mem`, `vsz`, `rss`, `etime` (elapsed since start, `[[dd-]hh:]mm:ss`), `etimes` (elapsed seconds — better for arithmetic), `lstart` (absolute start timestamp), `cmd` (full command line), `comm` (executable name only), `nlwp` (thread count), `lwp`/`spid` (thread id in thread mode), `pgid`, `sid`, `tty`, `wchan`.

Append `=` to rename or suppress a header, which makes output stable for parsing:

```
$ ps -o pid=,cmd= -p 1
1 /usr/bin/tini -- /start.sh
```

`-O` prepends specifiers to the default column set; `-f`/`-F`/`-l`/`-j`/`u`/`v` are predefined bundles (full, extra-full, long, jobs, user, virtual-memory).

### Sorting

`--sort` (GNU) takes `[+|-]key[,key...]`:

```
$ ps -eo pid,%mem,comm --sort=-%mem,pid | head -4
  PID %MEM COMMAND
  925 17.5 python
  909  0.8 uv
    2  1.1 caddy
```

The BSD spelling is `k`: `ps ax k -%mem`. Default order is undefined — never rely on it; always sort explicitly when scripting.

### The STAT field, decoded

The `stat` specifier shows the kernel task state plus BSD modifier letters. First character — the fundamental state:

| Letter | Meaning |
| --- | --- |
| `R` | running or runnable (on the run queue) |
| `S` | interruptible sleep, waiting for an event; signals wake it |
| `D` | uninterruptible sleep (usually IO); signals — even SIGKILL — do NOT wake it |
| `Z` | zombie: terminated, not yet reaped by its parent |
| `T` | stopped by job-control signal (SIGTSTP/SIGSTOP) |
| `t` | stopped by the debugger during tracing (ptrace) |
| `I` | idle kernel thread |
| `X` | dead (should never be seen) |

Additional characters (BSD formats and `stat` only):

| Letter | Meaning |
| --- | --- |
| `<` | high priority (not nice to other users) |
| `N` | low priority (nice) |
| `L` | has pages locked in memory |
| `s` | session leader |
| `l` | multi-threaded (CLONE_THREAD, i.e. pthreads) |
| `+` | in the foreground process group of its tty |

So `Ssl+` = sleeping, session leader, multi-threaded, foreground — exactly what you see for a terminal-launched multithreaded shell pipeline. The one-character-only variant is the `s`/`state` specifier (header `S`).

### The state machine in one picture

```
              fork()/exec()
                   │
                   ▼
                ┌─────┐   scheduler    ┌────────────────────┐
                │  R  │◄─────────────► │ run queue (on CPU) │
                └──┬──┘                └────────────────────┘
     waits for an  │
     event, signal │ page IO / driver call that
     will wake it  │ cannot be interrupted
                   ▼
                ┌─────┐
                │  S  │  interruptible sleep
                └──┬──┘
                   ▼
                ┌─────┐
                │  D  │  uninterruptible sleep
                └─────┘  not even SIGKILL applies

   terminated, parent has not reaped it:      [ Z ]  zombie
   SIGTSTP / SIGSTOP (job control):  [ T ] ──SIGCONT──► [ R ]
   ptrace stop by debugger:                   [ t ]
```

### D state deserves emphasis

A process in `D` is blocked inside a syscall the kernel refuses to interrupt — typically NVMe/FCP IO, NFS with a dead server, FUSE, or a buggy driver. Consequences that show up in interviews and war rooms alike:

- `kill -9` does nothing. There is no way to kill a D-state process from user space; the task leaves D only when the IO completes or the driver gives up. The "fix" is resolving the storage path (recover NFS, unbind the device, reboot).
- D-state tasks **count toward load average** (load includes running *and* uninterruptible tasks). A load of 40 with 2% CPU is the classic signature of mass D state, not CPU saturation.
- Diagnostic one-liner: `ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'` — `wchan` shows which kernel function it is parked in.

### Zombies

A `Z` process is already dead; only its exit status remains, held until the parent calls `wait()`. You cannot kill it — it has no code left to signal. Remedies: make the parent reap it (it may be stuck), or kill the parent so init/systemd adopts and reaps the orphan. `ps -eo pid,ppid,stat,comm | awk '$3 ~ /Z/'` lists them with their parents.

### VSZ vs RSS

- `vsz` — virtual memory in KiB, i.e. the whole address space: mapped files, shared libraries, anonymous mappings, and large `malloc` reservations the process never touched. Kernel counterpart: `VmSize` in `/proc/<pid>/status`.
- `rss` — resident set in KiB: pages actually in RAM right now. Counterpart: `VmRSS`. It includes pages *shared* with other processes (libc, common libs), so summing RSS across processes overestimates real usage.

```
$ ps -o pid,vsz,rss,comm -p 2
  PID    VSZ   RSS COMMAND
    2 1267756 48980 caddy
```

A Go/Rust/Java server can legitimately report VSZ of gigabytes with RSS of tens of megabytes: the virtual space is reserved, not used. Alarming VSZ on Linux is normal; watch RSS, and for shared-aware totals use pmap or smem-style accounting.

### Threads

`ps` shows processes by default. Three BSD-family switches change that:

```
-L    # one line per thread, adds LWP (thread id) and NLWP (thread count)
-T    # one line per thread, adds SPID column
H     # bare letter: show threads as if they were separate processes
```

```
$ ps -L -p 2 -o pid,lwp,nlwp,stat,comm
  PID   LWP NLWP STAT COMMAND
    2     2    8 Sl+  caddy
    2   947    8 Sl+  caddy
    ...
```

All threads of a process share the PID (TGID) but have distinct LWPs; `nlwp` is the fastest "how many threads" answer. `/proc/<pid>/status` `Threads:` shows the same number.

### Forest and hierarchy

`--forest` indents children under parents with `\_` connectors; `-H` shows hierarchy via indentation without the art. Both need a selection that includes the ancestors (`-ef`, `ax`) or the tree is truncated:

```
$ ps --forest -ef
UID   PID  PPID  C STIME TTY      TIME CMD
root    1     0  0 07:51 pts/0  00:00:00 /usr/bin/tini -- /start.sh
root    2     1  0 07:51 pts/0  00:00:06 caddy run --config ...
root  909     2  0 07:51 pts/0  00:00:00  \_ uv run main.py
root  925   909  0 07:51 pts/0  00:01:40      \_ /app/.venv/bin/python main.py
```

### Snapshot semantics, cost, and `ps` vs `top`

`ps` is a single pass over `/proc`: cheap, consistent-ish (not an atomic snapshot — processes appear and vanish between entries), and safe to run in tight loops. `top`/`htop` re-read continuously and compute deltas; use them for interactive monitoring, `ps` for scripts, postmortems, and exact columns. In containers `ps` sees only the container's PID namespace unless `/proc` is mounted with host visibility.

## Options That Matter

### Selection

| Option | Effect |
| --- | --- |
| `-e`, `-A` | every process on the system |
| `-a` | all with a tty, except session leaders |
| `-d` | all except session leaders |
| `-p, --pid LIST` | by PID list (comma or blank separated) |
| `--ppid LIST` | by parent PID list |
| `-u, --user LIST` | by effective user (name or UID) |
| `-U, --User LIST` | by real user (name or UID) |
| `-g, --group LIST` | by session id or effective group name |
| `-G, --Group LIST` | by real group |
| `-t, --tty LIST` | by controlling terminal |
| `-C cmdlist` | by command name (no path, no args) |
| `-s, --sid LIST` | by session id |
| `-N, --deselect` | invert the selection |
| `-q, --quick-pid` | like `-p` but skips some lookups (fast one-PID probe) |
| `-r` | only running processes (BSD letter) |
| `T` | only processes on this terminal (BSD letter) |

### Output

| Option | Effect |
| --- | --- |
| `-f` | full format: UID PID PPID C STIME TTY TIME CMD |
| `-F` | extra full: adds SZ, RSS, PSR, NI, flags |
| `-l` | long format (POSIX layout) |
| `u` | user-oriented format (BSD): USER %CPU %MEM VSZ RSS STAT ... |
| `-j`, `j` | jobs format: PGID SID |
| `-o, --format LIST` | user-defined columns |
| `-O LIST` | user columns prepended to defaults |
| `-y` | with `-l`: drop flags, show RSS instead of ADDR |
| `--forest` | ASCII tree under parents |
| `-H` | hierarchy by indentation |
| `--no-headers` | drop the header line (scripting) |
| `--cols N` / `-w` | width control; `-ww` disables truncation of CMD |
| `e` | append environment after the command (BSD letter) |

### Threads, sorting, misc

| Option | Effect |
| --- | --- |
| `-L` | threads with LWP/NLWP columns |
| `-T` | threads with SPID column |
| `H` | threads as processes |
| `-m`, `m` | threads listed after/before their process |
| `--sort=SPEC` | sort by `[+|-]key` list |
| `k SPEC` | BSD spelling of `--sort` |
| `S, --cumulative` | include dead-child CPU/time in parents |
| `L` | list all format specifiers and aliases |
| `n` | numeric UID and wchan |
| `c` | true command name (no args) |
| `-V` | version |

## Usage Patterns

```bash
# Full system view, POSIX style
ps -ef

# Interactive exploration with the classic BSD layout
ps aux

# Top memory consumers (sort descending, take 5)
ps -eo pid,user,%mem,rss,comm --sort=-%mem | head -6

# Top CPU consumers right now
ps -eo pid,user,%cpu,stat,comm --sort=-%cpu | head -6

# Everything about one process, exactly the columns you need
ps -o pid,ppid,user,stat,vsz,rss,etime,cmd -p "$(pgrep -x caddy)"

# Find processes leaking into D state (storage trouble)
ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'

# List zombies and the parent that must reap them
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/'

# Count threads per process, heaviest first
ps -eo nlwp,pid,comm --sort=-nlwp | head -5

# Process tree of one service subtree
ps --forest -o pid,ppid,stat,cmd --ppid "$(pgrep -x uv)"

# Processes started after boot time window, absolute timestamps
ps -eo pid,lstart,cmd -u root | grep nginx

# Script-friendly: no headers, stable width, machine-readable
ps -eo pid=,rss=,comm= --sort=-rss | head -10

# Watch one user's processes continuously (poor man's monitor)
watch -n 2 "ps -u deploy -o pid,%cpu,%mem,stat,etime,cmd --sort=-%cpu"
```

## Nuances and Gotchas

- **Dash or no dash changes meaning.** `ps u` (format) vs `ps -u root` (filter); `ps p 1` (select) vs `ps -p 1` (same, POSIX). A script that "works" with one spelling can silently do something else with the other. Pick one style per script.
- **`ps aux` truncates `CMD` to terminal width.** Piped output is not truncated, but on a narrow terminal you lose args — use `ps auxww` (`-ww`) for unlimited width.
- **VSZ is not memory usage.** Reserved-but-untouched mappings inflate VSZ; comparing VSZ against physical RAM is meaningless. Use RSS, and remember RSS double-counts shared pages.
- **D state is unkillable.** `kill -9` on a D-state process does nothing and returns success. Only IO completion or a reboot clears it.
- **Zombies cannot be killed.** The parent must `wait()`; kill the parent if it is stuck. Killing a zombie's "children" makes no sense — it has none.
- **`%CPU` in `ps` is lifetime average, not current.** `ps -o %cpu` divides total CPU time by elapsed time since process start; a process that finished a burst shows a decaying number. `top` shows the recent window.
- **Load average includes D state.** High load + idle CPU means uninterruptible IO wait, not missing CPU — check `ps -eo stat | grep -c D`.
- **Default `ps` is filtered.** Without `-e`/`ax` you only see your own tty's processes; piping `ps` into grep and wondering why the daemon is missing is a classic mistake.
- **PID reuse and races.** Between `ps` printing a PID and you acting on it, the process can exit and the PID can be reused — for anything automatic, prefer matching by attributes with pgrep/pkill in one step.
- **Portability.** `aux`, `-ef`, and `-o` exist nearly everywhere (POSIX guarantees `-o`), but specifier spellings and STAT letters differ on BSD/macOS, and the GNU conveniences (`--sort`, `--forest`, `--no-headers`) do not exist there. Busybox `ps` accepts `aux` but little else; treat `-eo` as the most portable core.
- **`ps` output is locale-affected** for user names and widths; scripts that parse columns should use `-o pid=,comm=` style headers and fixed specifiers rather than slicing the default layout.

## Exit Status

The man page documents no formal table; observed behavior (procps-ng 4.x):

- `0` — output produced successfully.
- `1` — usage or runtime error (unknown option, bad specifier, invalid list) **or an empty selection**: `ps -p 999` exits 1 when no process matches.

The empty-selection exit code is exactly why `ps` is a poor existence check compared to pgrep: it double-codes "nothing matched" with "you made a mistake", and historic procps releases did not return 1 on empty output — scripts that branch on ps's exit status are testing an undocumented, version-dependent behavior.

## Related Commands

- [`pgrep`](./pgrep.md) — find PIDs by name/attributes; safer than `ps | grep`.
- [`pkill`](./pkill.md) — signal processes by the same criteria.
- [`pidwait`](./pidwait.md) — wait for processes matching criteria to exit.
- [`pidof`](./pidof.md) — exact-name PID lookup, sysvinit tradition.
- [`free`](./free.md) — system memory totals; the system-wide counterpart of `rss`.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — signals, job control, and cgroups context around `ps`.

## Interview Questions

### Q: What is the difference between `ps aux` and `ps -ef`, and why does the dash matter?

Both list every process, but they invoke different option parsers. `aux` is BSD syntax — `a` (all with tty), `x` (also without tty), `u` (user-oriented format with %CPU/%MEM/VSZ/RSS/STAT) — while `-ef` is POSIX syntax — `-e` (everything) plus `-f` (full format with UID/PPID/STIME/C column). The dash switches parser personalities, so the same letter selects different behavior (`u` vs `-u`). In practice `ps aux` is the interactive habit, `ps -ef` the portable POSIX habit, and `ps -eo ...` the scripting choice.

### Q: A server shows load average 60 but CPU is 98% idle. What do you check?

Whether the load is made of D-state tasks. Linux load average counts running *and* uninterruptible tasks, so blocked IO inflates it without any CPU use. Run `ps -eo pid,stat,wchan,cmd | awk '$2 ~ /^D/'`; a pile of D processes parked in NFS, FUSE, or a device driver means storage trouble — and `kill -9` will not clear them, because an uninterruptible syscall only returns when the kernel's IO path does.

### Q: What is the difference between VSZ and RSS, and why can VSZ exceed physical RAM?

VSZ is the size of the virtual address space — every mapping, including shared libraries, file mappings, and `malloc` reservations never touched. RSS is the subset of pages physically resident, and it includes pages shared with other processes. Virtual memory makes VSZ arbitrarily large (overcommit, reservations, mapped files), so VSZ beyond RAM is normal; RSS is the meaningful per-process figure, and even summing RSS overestimates because shared pages are counted once per process.

### Q: How do you find and clean up zombie processes?

`ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/'` lists them with their parents. A zombie is already dead — only its exit status awaits `wait()` from the parent — so signals are useless. Options: get the parent to reap (it may be event-loop-stuck; fix it), send the parent SIGCHLD if it handles it, or kill the parent so the zombie is reparented to PID 1/systemd, which reaps promptly. If the zombie's parent is PID 1 and it still persists, something is wrong in that container's init.

### Q: How do you see the threads of a process, and how do threads appear in `ps`?

`ps -L -p PID` prints one line per thread with `LWP` (kernel thread id) and `NLWP` (count); `-T` uses an `SPID` column, and bare `H` shows threads as if they were processes. All threads share the process PID; they differ in LWP. `/proc/PID/status` shows the same count as `Threads:`. A high NLWP with flat CPU can point at thread-pool misconfiguration or leak.

### Q: Why do experienced users prefer `pgrep`/`pkill` over `ps aux | grep ... | awk '{print $2}'`?

The pipeline has three failure modes: the `grep` process itself matches the pattern and appears in its own output; the 15-character command-name truncation in `ps aux` (and `ps`'s default width) mangles matches; and column slicing breaks when CMD contains spaces or the width changes. `pgrep` excludes itself, matches kernel-visible names or with `-f` the full command line, and composes with `pkill`/`pidwait` in one step — no quoting, slicing, or self-match pitfalls. The `ps aux | grep [n]ginx` bracket trick survives only as an interview antique.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/ps.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
