# snice — change process priority using skill-style selection

## Overview

`snice` changes the scheduling priority (nice value) of processes selected with `skill`-style expressions — by terminal, user, PID, or command name — instead of the `renice` flag syntax. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) and is not a separate program: `/usr/bin/snice` is a **symlink to `/usr/bin/skill`**, a multi-call binary whose behavior comes from `argv[0]` (`skill` sends signals, `snice` renices).

The man page is unusually blunt: *skill and snice are "obsolete and unportable. The command syntax is poorly defined. Consider using the killall, pkill, and pgrep commands instead."* That warning is itself the interview answer: snice survives because it predates `pkill`/`renice` conveniences, still script-runs fine, and supports one thing `renice` lacks — namespace-aware selection via `--ns`. New code should reach for `renice -n <value> -p <pid>` or `pkill`/`pgrep` first.

Its priority model differs from `renice` in a way interviewers love: snice sets an **absolute** nice value as the first positional argument (`snice +7 -c compilejob`), while `renice -n 7` is an **increment**. And because the syntax is "poorly defined", several traps (unsigned priorities, silent permission failures) live below.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 (same page as skill) |
| Path | /usr/bin/snice → symlink to /usr/bin/skill |
| First appeared | 1999, Albert Cahalan, as a free replacement for a non-free skill/snice pair |
| Standards | No standards apply |

## Synopsis

```
snice [new priority] [options] <expression>
```

Common one-line forms:

```
snice +10 -c backup     # slow every 'backup' command down
snice -u alice +15      # be nice to everything alice runs
snice +4 -p 1234        # reset one PID to the default +4
snice -n +5 -u root     # dry run: print PIDs that would change
snice --ns 4321 +10     # renice processes in PID 4321's namespace
```

## How It Works

### One binary, two behaviors

```
                 argv[0]
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
    /usr/bin/skill          /usr/bin/snice (symlink)
    send signals            change priority
    default: SIGTERM        default: +4
```

The dispatcher compares the invoked name; everything else (selection, `-l`/`-L` signal listing, `-i`, `-n`) is shared. That is why `snice -l` prints signal names, and why fixes to skill's parser historically changed snice's behavior too.

Priority application is a `setpriority(PRIO_PROCESS, pid, value)` per matched process, with the kernel's rules: an unprivileged user may only *increase* the nice value (make the process lower priority) for processes they own; lowering it (values below current, i.e. faster) requires root or `CAP_SYS_NICE`. The valid range is +20 (lowest priority) to −20 (highest). Verified end-to-end:

```bash
$ ps -o ni= -p $$
0
$ snice +3 -p $$
$ ps -o ni= -p $$
3
$ snice +8 -p $$
$ ps -o ni= -p $$
8
```

The value is absolute: `+3` moved nice from 0 to 3 (not to 3 *more* than before). `renice -n 3` would have moved it to 3 as well only because the base was 0 — the difference shows on a second call (`renice -n 3` again → 6; `snice +3` again → 3).

### Selection expressions

Selection criteria can be a terminal, user, PID, or command name; the disambiguation flags force an interpretation when a name could be either (a user named `sync`, a command named `pts/1`):

```bash
$ snice -n +1 -u root          # dry run lists what would change
1
2
909
925
```

`--ns <pid>` matches processes in the same namespace(s) as the given PID, and `--nslist ipc,mnt,net,pid,user,uts` narrows which namespaces count — renice has no equivalent, which is snice's one modern raison d'être (e.g. renice a whole container's process tree from outside).

### The nice value, precisely

snice writes a single integer into the process's static scheduling priority via `setpriority()`. The rules the kernel enforces:

| Who | May set |
| --- | --- |
| Unprivileged user, own process | Any value ≥ current nice (only demote) |
| Root / `CAP_SYS_NICE` | Any value, +20 to −20, any process |

(The RLIMIT_NICE resource limit can grant a user process a bounded promotion window, but no distribution sets it by default — in practice, unprivileged means demote-only.)

Nice values are inherited across `fork()`, survive `execve()`, and only matter for SCHED_OTHER tasks competing for CPU: an IO-bound process at nice +19 loses nothing because it never competes for a run queue slot. The classic operational move is snice +19 on a batch job — it still finishes, it just yields instantly whenever anything interactive needs a core.

### The silent failure gotcha

snice does not report setpriority failures, and exits 0 regardless:

```bash
$ ps -o ni= -p $$          # nice 8
8
$ snice +2 -p $$           # decreasing nice needs root → EPERM
$ echo $?
0
$ ps -o ni= -p $$          # unchanged, no message
8
$ snice +4 -p 999999       # nonexistent PID: also silent, also 0
$ echo $?
0
```

Always verify with `ps -o ni= -p PID` (or `pgrep` + a loop) rather than trusting the exit status. `-v` does at least explain successful actions.

## Options That Matter

| Option | Effect |
| --- | --- |
| *[new priority]* | First positional argument, signed (`+4`, `-10`); default +4 if omitted |
| `-n`, `--no-action` | Dry run: print what would happen, change nothing |
| `-i`, `--interactive` | Ask before each action |
| `-v`, `--verbose` | Explain what is being done |
| `-c, --command <name>` | Expression is a command name |
| `-u, --user <user>` | Expression is a username |
| `-p, --pid <pid>` | Expression is a PID |
| `-t, --tty <tty>` | Expression is a terminal (tty or pty) |
| `--ns <pid>` | Match processes sharing namespaces with `<pid>` |
| `--nslist <ns,...>` | Which namespaces `--ns` considers: ipc, mnt, net, pid, user, uts |
| `-l` / `-L` | List signal names (skill heritage; works in snice too) |
| `-f`, `-w` | "Fast mode" / "warnings" — documented as not implemented |

## Usage Patterns

```bash
# Slow down a CPU-hungry build so it stops starving your session
snice +15 -c make

# Be nice to everything a user runs (login, current and future PIDs alike)
snice +10 -u alice

# Reset a runaway renice experiment to the default
snice +0 -p 1234

# Dry run first — see exactly which PIDs match before committing
snice -n +5 -c java

# Same command name in different namespaces (two containers on one host)
snice --ns 4321 +10 -c worker

# Terminal-wide: everything on a stuck SSH session
snice +10 -t pts/3

# Multiple criteria in one call
snice +7 -c seti -c crack

# Interactive: approve each change (useful with broad selections)
snice -i +9 -u guest

# Verify instead of trusting exit status
snice +5 -p "$(pgrep -x worker | head -1)" && ps -o ni=,cmd -C worker

# Demote a whole cgroup-free pile of cron leftovers
snice +19 -u backup

# Bring yesterday's nice experiment back to neutral (root for promotions)
sudo snice +0 -c stress-ng

# Confirm matching before acting on a broad pattern
snice -n +10 -c python3 ; snice +10 -c python3
```

## Nuances and Gotchas

- **Priorities need an explicit sign.** A bare number is not recognized as a priority: observed behavior of `snice 5 -p $$` on a nice-0 shell was to *fall back to the default +4* (the `5` is consumed as an expression), while `snice +5` set 5. This is the "poorly defined syntax" the man page warns about, in its purest form.
- **Omitted priority means +4, silently.** `snice -c foo` does not fail for lack of a value; it renices foo to +4. Combined with the unsigned-number trap, a mistyped command can quietly demote processes you meant to leave alone.
- **Failures are silent and exit 0.** `setpriority()` EPERM (lowering nice unprivileged) and nonexistent PIDs both produce no output, no error, exit 0. Scripts must verify with `ps -o ni=`.
- **Absolute, not relative.** `snice +2` does not add 2; it *targets* 2 (and fails for unprivileged users if the target is below current nice). Use `renice -n 2` for increments.
- **Negative values are root-only.** Anything faster than the current nice (and in particular any negative value) requires root or CAP_SYS_NICE; an unprivileged `snice -2 -p PID` silently does nothing (verified). Prefer the `+N` spelling universally — leading-dash numbers collide with the option parser's territory.
- **Selection matches at a point in time.** New processes started after snice runs are untouched; for ongoing demotion use a `nice`d launcher, a systemd `Nice=` property, or cgroup `cpu.weight`.
- **The man page tells you not to use it.** "Obsolete and unportable" — BSDs and busybox do not ship snice; any cross-platform script should use renice/pkill-style tools.
- **`-l`/`-L` list signals, not priorities.** Leftover from the skill half of the binary; confusing when you grep the help looking for nice-related options.

## Exit Status

No exit-status table is documented. Observed procps-ng 4.x behavior:

- `0` — returned on success, on a dry run, *and* when the selection matched nothing or every `setpriority()` failed with EPERM. snice's exit status carries essentially no information; verify results in `/proc`.

## Related Commands

- [`pgrep`](./pgrep.md) — the recommended modern selector; pair with renice-style tools.
- [`pkill`](./pkill.md) — the signaling half of pgrep's machinery (what skill should be today).
- [`ps`](./ps.md) — `ps -o ni=,pid,cmd` to verify snice actually changed anything.
- [`top`](./top.md) — NI column live view; press `r` to renice interactively.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — nice values, scheduling classes, and cgroup alternatives in context.

## Interview Questions

### Q: What is the difference between snice +5 and renice -n 5?

snice sets an absolute nice value of 5; `renice -n 5` adds 5 to the current value (it is an increment). On a nice-0 process both land at 5, which is exactly why the difference goes unnoticed until the second invocation: renice again → 10, snice again → still 5. Scripts that intend "set to N" are safer with snice's model but must survive its silent failures; scripts that intend "make it N worse" want renice.

### Q: You ran `snice +2 -p $PID` as a normal user and the nice value did not change — and snice printed nothing and exited 0. What happened?

`setpriority()` refused the change because decreasing a process's niceness (increasing its scheduling priority) is reserved for root/`CAP_SYS_NICE`; unprivileged users may only increase nice values. snice neither reports the error nor changes its exit status, so the tool *looks* successful. The fix is running as root (or `sudo snice -2 ...`), and the general lesson is: verify priority changes with `ps -o ni=`, never with snice's exit code.

### Q: Why is snice a symlink to skill, and what does that imply?

They are one multi-call binary dispatching on `argv[0]`: skill sends signals, snice changes priority; selection logic, `-l`/`-L`, `-i`, and `-n` are shared. Implications: every skill parser quirk (unimplemented `-f`/`-w`, signal names listed by snice's help) exists in snice too, and the two man pages are one page. The multi-call pattern is also worth naming in interviews — busybox is built on the same idea.

### Q: The man page calls skill/snice "obsolete and unportable" — why, and what replaces them?

The expression grammar is positional and ambiguous (a bare number can be a priority, a PID, or a command depending on parsing order), failures are silent, and the selection flags predate pgrep's. Modern equivalents: `pkill`/`pgrep -f` for selection, `renice` for priority changes (incremental, well-defined exit codes), and for "renice a container's processes", snice's `--ns` is the one feature without a direct renice equivalent — otherwise cgroup `cpu.weight` or systemd's `Nice=`/`CPUWeight=` properties are the durable answer.

### Q: What does nice +20 vs −20 actually mean to the scheduler?

Nice maps onto the CFS weight of the task: +20 is the least CPU-favored, −20 the most, with roughly a 1.4× weight ratio per step at the extremes compounding (a −20 task can receive orders of magnitude more CPU than a +19 one competing for the same core). Nice only matters under CPU contention — an IO-bound process at +20 loses nothing — and only affects normal SCHED_OTHER tasks, not realtime classes. snice touches exactly this one knob via `setpriority()`.

### Q: How would you renice every process in another container's PID namespace?

From the host, `snice --ns <container-pid> --nslist pid +10` matches processes sharing that PID namespace — functionality renice lacks. Alternatively list the namespace's PIDs via `/proc/<pid>/ns/pid`-aware tools or nsenter and pipe them to `renice -n 10 -p`. Inside the container, plain `renice` works on its own PIDs subject to the same privilege rules (root inside the userns can demote, not promote).

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/snice.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
