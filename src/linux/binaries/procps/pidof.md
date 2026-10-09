# pidof — find PIDs of a running program by exact name

## Overview

`pidof` does one thing: it prints the PIDs of running programs whose name matches the argument, space-separated on a single line. No regex, no attribute filters beyond a few, no columns — `pidof nginx` and you have your answer. It ships in the `sysvinit-utils` package (Debian bookworm) at `/usr/bin/pidof`, **not** in procps: it is part of the sysvinit source tree, historically the same binary as `killall5(8)`, dispatched by the name it is invoked under.

`pidof` is the tool of System V rc scripts and of shell one-liners shaped like `kill $(pidof foo)`. It is often confused with `pgrep -x` (similar job, richer filters, regex residue, one-PID-per-line output) and with `killall` (psmisc, signals by name instead of listing). On systems where init scripts cannot assume procps, `pidof` is the lowest-common-denominator lookup.

Its value proposition is narrowness: a literal name in, PIDs out, exit code that works in an `if`. Everything pgrep does beyond that — regex, attribute filters, namespaces, cgroups — is exactly the surface pidof deliberately leaves out, which is why decades-old init scripts still run unmodified.

| Field | Value |
| --- | --- |
| Package | sysvinit-utils (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/pidof |
| First appeared | 1998, Miquel van Smoorenburg (sysvinit); same program as killall5(8) |
| Standards | none; System V rc-script tradition (used by LSB-style init scripts) |

## Synopsis

```
pidof [-s] [-c] [-n] [-x] [-z] [-o omitpid[,omitpid...]] [-d sep] program [program...]
```

Common one-line forms:

```
pidof nginx            # all PIDs of programs named nginx
pidof -s nginx         # just one PID
pidof -x backup.sh     # PIDs of shells running that script
pidof -o %PPID bash    # exclude the calling shell itself
kill -TERM $(pidof -s app)   # the classic scripting pattern
```

## How It Works

### Name lookup, the literal way

`pidof` walks `/proc`, compares each process's name against the argument(s), and prints every match on one line. The comparison is **literal and exact** — no regex engine is involved, so names with dots, dashes, or regex metacharacters behave the way a shell scripter expects:

```
$ pidof -s caddy
2
$ pidof nginx caddy
2
```

Multiple program arguments are allowed and all matches are merged into the output. This is the whole contract; everything else is an edge-case flag. The simplicity is the selling point: there is no pattern that can over-match, no 15-character regex subtleties beyond the same `comm` truncation every /proc-scanning tool shares, and no quoting hazards.

### How matching actually resolves

Two layers of resolution matter in practice:

1. The process name compared is the kernel-visible `comm` (field 2 of `/proc/<pid>/stat`, at most 15 characters) — the same string `ps -o comm` shows.
2. `pidof` additionally `stat(2)`s the on-disk binaries of candidates; processes whose binary lives on a network filesystem make that stat slow or hanging, which is what `-n` (and the `PIDOF_NETFS` variable) opt out of.

The `-x` flag extends matching to a case comm cannot cover: **shell scripts**. A script `backup.sh` runs as a `bash` process whose comm is `bash`; `-x` makes pidof look at the script name in the invocation and report those shells:

```
$ ./backup.sh &
$ pidof -x backup.sh
12412
$ pidof backup.sh          # without -x: nothing (comm is "bash")
```

### Output shape: one line, space-separated

Unlike pgrep's one-PID-per-line, pidof prints a single line with spaces — ergonomic for `$(...)` substitution and for `kill`, awkward for line-oriented tools:

```
$ pidof -d , -x sleep
4711,4712          # -d chooses the separator
```

`-s` truncates the result to a single PID (the first found — historically "the most likely" one for init scripts that just want *the* daemon PID). `-o omitpid` removes specific PIDs from the result, most idiomatically with the magic value `%PPID`, which names the caller — used by init scripts to exclude themselves when the script's own name matches the daemon's. `-q` suppresses output entirely (exit code only).

### Edge-case flags for sysvinit contexts

| Flag | Purpose |
| --- | --- |
| `-c` | only PIDs with the same root directory (chroot-aware; root-only) |
| `-n` | skip `stat(2)` on binaries on network filesystems (NFS hangs) |
| `-z` | also list zombie and IO-waiting processes — documented as possibly hanging |
| `-q` | no output, exit code only |
| `-d sep` | custom output separator (default space) |

`-c` exists for init scripts running inside a chroot: without it, pidof would happily report daemons from *outside* the chroot root. `-z` matters because the default skip of zombies and D-state tasks is usually right — those processes are on their way out and their PIDs are worthless to signal.

### The lookup flow, end to end

```
pidof [flags] name [name...]
        │
        ▼
walk /proc/[0-9]*
        │
        ├─ comm == name ?          (literal compare, 15-char cap)
        │
        ├─ -x: script name match   (interpreter shells running <name>)
        │
        ├─ -o omitpid?             (drop %PPID caller, listed PIDs)
        │
        ├─ -c: same chroot root?   (root only)
        │
        └─ zombie / D-state?       (skipped unless -z)
                │
                ▼
      print PIDs, space-separated on one line
      exit 0 if any matched, else 1
```

### pidof in the init-script ecosystem

`pidof` exists because System V rc scripts (`/etc/rc?.d/`, `/etc/init.d/`) needed a dependency-free way to answer "is the daemon already up?" and "which PID do I signal?". Its man page points out the modern answer when available: if the system has `start-stop-daemon(8)`, that should be used instead — it verifies identity through pidfiles, executable paths, and user checks rather than name alone. Under systemd, the question itself dissolves: `systemctl is-active unit` and `systemctl status` consult cgroup membership, which neither pidof nor pgrep can see into.

That heritage explains the design: no output decoration (rc scripts parse it), space-separated single line (`kill $(pidof foo)`), `-s` for singleton daemons, `-c` for chrooted services, and exit codes that slot directly into `if` statements. LSB-style init scripts frequently wrap it in a `pidofproc` helper; the raw binary remains the floor of the abstraction.

### Verifying what you found

Because matching is name-only, the returned PIDs deserve a second look when the stakes are real:

```
$ ps -o pid,ppid,user,etime,args -p "$(pidof -s nginx)"
```

That one line confirms ownership, uptime, and the actual command line before anything is signalled — the manual equivalent of the checks `start-stop-daemon` automates.

### Containers and PID namespaces

Like every /proc walker, pidof sees only the PID namespace it runs in. Inside a container, `pidof app` finds container processes and knows nothing of the host; from the host, it finds host processes and does not descend into container namespaces — use `nsenter`-style tooling or `pgrep --ns` for that. One practical consequence: container healthchecks built on `pidof` validate only what the container's own namespace exposes, which is exactly what a healthcheck wants.

### The killall5 twin

The man page notes `pidof` "is actually the same program as `killall5(8)`; the program behaves according to the name under which it is called". `killall5` is the sysvinit mass-signaller used by shutdown scripts to signal every process except those in its own session. One binary, two personalities — a miniature of the procps pgrep/pkill/pidwait family design, years earlier.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-s` | return only a single PID |
| `-c` | only processes with the same root directory (ignored for non-root) |
| `-n` | avoid `stat(2)` on binaries on network filesystems |
| `-x` | match shells running scripts with the given name |
| `-z` | include zombie and IO-waiting processes (may hang) |
| `-o omitpid` | omit PIDs from the result; `%PPID` = the calling process |
| `-q` | quiet: no output, exit status only |
| `-d sep` | use `sep` between PIDs (default: space) |

## Usage Patterns

```bash
# The init-script classic: signal the daemon by name
kill -TERM $(pidof -s nginx)

# Restart guard: is it already running?
[ -n "$(pidof -s myapp)" ] && { echo "already running"; exit 1; }

# All instances, one per argument-safe token
for pid in $(pidof worker); do kill -TERM "$pid"; done

# Find shells running a particular script
pidof -x backup.sh

# Exclude the calling shell when the script name collides
pidof -o %PPID -x myscript.sh

# Count running instances in a monitoring probe
pidof -q -x somejob && echo up || echo down

# Comma-separated for a log line
echo "pids=$(pidof -d , caddy)"

# Chroot-safe lookup from inside a service chroot (root)
pidof -c nginx

# Verify before acting: full identity of the PID you are about to signal
ps -o pid,ppid,user,etime,args -p "$(pidof -s nginx)"

# Wait-free existence check inside a container healthcheck
pidof -q app >/dev/null || exit 1

# Distinguish interpreter shells from the binary itself
pidof -x deploy.sh; pgrep -x deploy.sh   # only the first finds anything
```

## Nuances and Gotchas

- **`pidof` is not a procps binary.** On Debian it comes from `sysvinit-utils`; minimal procps-only images and some containers may lack it entirely. Scripts that must run anywhere should fall back to `pgrep -x` or check both.
- **Exact name means exactly the comm.** `/usr/sbin/nginx` is found by `pidof nginx`, but a systemd-spawned process whose comm is truncated to 15 characters only matches its truncated name. The 15-character kernel cap applies as everywhere.
- **`-x` is for scripts, not renamed processes.** A program that rewrites its own comm (`prctl(PR_SET_NAME)`) matches its new name, not its executable path; `pidof` has no full-cmdline mode like `pgrep -f`.
- **Exit code is the boolean.** 0 = at least one program found, 1 = none. `pidof -q` exists precisely for `[ ]`-style probes with no output noise.
- **`-s` returns an arbitrary pick** when several instances run — fine for singleton daemons, wrong for multi-instance services where you want the whole list.
- **The NFS stat can hang.** Candidate binaries on dead NFS mounts stall the stat; `-n` (or exporting `PIDOF_NETFS`) skips it. `-z` is documented as possibly hanging too — it reaches into zombie/IO-wait states that are not cheap to enumerate.
- **Output is one line with spaces, not one PID per line.** Piping it into `xargs` works; piping into `while read pid` does not. This is the most common pgrep-habit porting error.
- **No attribute filters.** No user, parent, terminal, or runstate selection — anything finer belongs to `pgrep`. If a one-liner grows a second condition, switch tools instead of filtering pidof's output with ps.
- **Under systemd, cgroups answer the question better.** A service can be active while its binary is momentarily absent, or multiple units can run the same binary name; `systemctl is-active` and `systemctl status` read cgroup membership that name-scanning tools cannot see. `pidof` answers "processes named X", not "unit running".
- **busybox ships a pidof too.** The busybox applet covers `-s -x -o -q` but not `-c -n -z`; init scripts meant for rescue environments should stick to the intersection.
- **`-o` accepts a list, not just `%PPID`.** `pidof -o 4711,4712 -x script` excludes several known PIDs — the sysvinit way to skip the supervisor and the caller at once. The separator is a comma and the option may repeat.

## Exit Status

| Code | Meaning |
| --- | --- |
| `0` | at least one program was found with the requested name |
| `1` | no program was found with the requested name |

## Related Commands

- [`pgrep`](./pgrep.md) — regex plus attribute filters; the modern superset of the lookup.
- [`pkill`](./pkill.md) — signal by pattern when a two-step `pidof` + `kill` is not needed.
- [`ps`](./ps.md) — the full snapshot view behind every PID lookup.
- [`overview`](./overview.md) — procps collection hub (pidof itself lives in sysvinit-utils).
- [Process management](../../admin/process-management.md) — init scripts, sessions, and signaling context.

## Interview Questions

### Q: When is `pidof` preferable to `pgrep -x`, and vice versa?

`pidof` for the shell-scripting shape: literal name matching with zero regex surprises, space-separated single-line output ideal for `kill $(pidof foo)`, and `-x` for finding shells running a script — something pgrep cannot do. `pgrep -x` when the query has structure: attribute filters (`-u`, `-P`, `-t`, `-r`), counting, one-PID-per-line for pipelines, and exit-code semantics identical to grep. Also note pidof is not procps — availability differs by image.

### Q: What is the `%PPID` idiom in `pidof -o %PPID` for?

Init and wrapper scripts often share a name with the daemon or job they manage, and the script process itself would otherwise appear in the result — leading to the script signalling or counting itself. `-o %PPID` omits the parent of the pidof invocation, i.e. the calling shell, from the match set. It is pidof's built-in answer to the ancestor-exclusion problem that pgrep solves with `--ignore-ancestors`.

### Q: Why does `pidof -x backup.sh` work while `pidof backup.sh` finds nothing?

A shell script has no process of its own; the interpreter (`bash`, `sh`) runs it, and the kernel-visible comm of that process is `bash`, not `backup.sh`. Plain pidof therefore matches nothing. `-x` makes pidof inspect the script name from the invocation and report the shells running it. The same confusion explains why `pgrep -x backup.sh` also fails: comm is capped and rewritten to the interpreter's name.

### Q: A legacy rc script uses `kill $(pidof -s app)`. Name two failure modes and modern alternatives.

First, `-s` picks one arbitrary PID of possibly many instances, so multi-instance services get partially signalled — the init-script assumption of singletons does not survive containers. Second, the PID can be recycled between lookup and signal, or the process may be a zombie that ignores the signal entirely. Modern practice: `pkill -x app` fuses selection and delivery with proper exit codes, or systemd unit management (`systemctl restart app`) removes PID bookkeeping from the shell entirely.

### Q: What does "pidof is the same program as killall5" mean, and what does it teach about tool design?

The sysvinit source ships one binary that dispatches on argv[0]: invoked as `pidof` it lists PIDs, invoked as `killall5(8)` it signals every process outside its own session — the shutdown-time mass-killer. One codebase, two contracts, chosen by name rather than flags. It prefigures the procps pgrep/pkill/pidwait family, where the shared selection engine serves three verbs; the lesson is that lookup, signal, and wait are three faces of one query, and mature tooling unifies them rather than duplicating parsers.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/sysvinit-utils/pidof.8.en.html)
- [Source — Debian sources](https://sources.debian.org/src/sysvinit/)
