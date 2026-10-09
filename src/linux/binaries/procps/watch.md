# watch — run a command repeatedly, full-screen, with change highlighting

## Overview

`watch` wraps any command in a refresh loop: it re-runs the command every N seconds (2 by default), clears the screen, and displays the output with a header showing the interval, the command, the hostname, and the timestamp. It ships in the `procps` package at `/usr/bin/watch` and is the terminal-native answer to "keep an eye on this" — no cron job, no monitoring stack, no `while true; do clear; cmd; sleep 1; done` scaffolding.

It is often confused with `top` (fixed process view, not arbitrary commands), with shell loops (which you must assemble yourself but which can log), and with event-driven tools like `inotifywait` (which react to filesystem events instead of polling). What `watch` uniquely owns is *interactive polling with change detection*: highlight what changed between runs, beep or exit when a condition appears.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 4.x) |
| Man section | 1 |
| Path | /usr/bin/watch |
| First appeared | procps, 1990s (Linux rewrite of a BSD idea) |
| Standards | None |

## Synopsis

```
watch [options] command
```

Common one-line forms:

```
watch df -h                          # default: every 2 s, sh -c, screen view
watch -n5 'kubectl get pods'         # every 5 s
watch -d 'ls -l /var/tmp'            # highlight what changed
watch -g 'test -f /tmp/ready'        # exit when output first changes
watch -n1 -x tail -n5 /log/app.log   # exec mode: no shell in the middle
```

## How It Works

### Execution model

`watch` does not re-exec itself in a loop — every iteration it spawns a shell to run your string:

```
watch 'df -h | tail -1'
        │
        ▼
 fork + execl("/bin/sh", "-c", "df -h | tail -1")      ← each iteration
        │
        ▼
 capture first screenful of stdout+stderr
        │
        ▼
 compare with previous output  ── highlight diffs (-d)
                               ── exit on change     (-g)
                               ── beep/exit on error (-b / -e)
        │
        ▼
 sleep remaining interval → repaint header + output
```

Consequences that follow directly from the `sh -c` model:

- **Pipes, globs, redirections, and subshells all work** — *if quoted into the command string*. `watch df -h | tail -1` instead pipes `watch`'s screen output into `tail` and leaves you staring at one frozen line.
- **Each run is a fresh shell**: no aliases, no functions, no state between iterations; the working directory and environment are `watch`'s own.
- The header confirms what is being run and when — grounded output:

```
Every 1.0s: date +%s  myhost: Fri Oct  9 15:38:59 2026
```

### The header line, decoded

```
Every 1.0s: date +%s  myhost: Fri Oct  9 15:38:59 2026
└────┬────┘ └───┬───┘ └─┬─┘ └──────────┬─────────────┘
   interval  command  hostname     timestamp of the LAST run
```

Two details worth noticing: the timestamp is when the displayed output was *produced* (during `-p` precise runs it stays close to the interval grid), and the command is echoed exactly as passed — a quick way to spot quoting mistakes, since what you see in the header is what `sh -c` received. The header spans two rendered lines including a blank separator; `-t` removes it when the command's output is exactly one terminal tall.

### Quoting rules, worked

One level of shell quoting wraps the whole command; inner quotes must nest:

```bash
# inner double quotes are fine inside single quotes:
watch -n5 'ps -o pid,pcpu,comm -p "$(pgrep -n java)"'

# command substitution with pipes inside:
watch -n10 'tail -n2 $(ls -t /var/log/app/*.log | head -1)'

# awk needs its own quotes — switch the outer quoting style:
watch -n1 "vmstat 1 2 | awk 'NR==4 {print \$13, \$14}'"

# exec mode: no quoting at all, argv passes through literally:
watch -n1 -x ip -brief addr show eth0
```

The awk line shows the real trap: once the outer string is double-quoted, the shell expands `$13` *before* `watch` ever runs — hence the escaped `\$13`. When a one-liner needs three levels of quoting, stop and write a small script; `watch -n1 /usr/local/bin/probe.sh` is the maintainable form.

### Change detection: -d, -g, -q

Three flags read the *visible* output and act on it:

| Flag | Behavior |
| --- | --- |
| `-d` | Highlight characters that changed since the previous update (reverse video) |
| `-d=permanent` | Highlight everything that changed since the *first* sample — accumulates |
| `-g` | Exit when the visible output changes — the poll-until-condition primitive |
| `-q CYCLES` | Exit after CYCLES consecutive *unchanged* outputs — the wait-until-stable primitive |

`-g` deserves a caveat from the man page: only *on-screen* output counts. If the change you wait for scrolls past line 24, `watch` never sees it — keep the compared output short, or filter it down (`| tail -1`, `| wc -l`) so the signal fits the screen.

### Error handling: -e, -b

```
$ watch -n1 -e ./check.sh
# ... on failure watch stops refreshing and prints:
command exit with a non-zero status, press a key to exit
```

`-e` (errexit) freezes updates on the first non-zero exit and exits after a keypress — deliberate for humans, hostile to automation, because a script calling `watch -e` will hang waiting for keyboard input. `-b` (beep) keeps running but rings the terminal bell on each failed run. Neither flag stops you from combining them: `watch -b -g 'tail -1 job.log'` beeps when the job errors and exits when its status line changes.

### -x: exec mode

`-x` replaces the `sh -c` hop with a direct `execvp`: arguments go to the program untouched, no quoting rules apply twice, and the shell-parsing traps disappear:

```
watch -n1 'tail -n5 /var/log/app.log'    # shell mode: string parsed by sh
watch -n1 -x tail -n5 /var/log/app.log   # exec mode: argv passed literally
```

Use `-x` when the command is a fixed program with fixed arguments; use shell mode when you need pipes, substitution, or globs. Note that with `-x` you *cannot* write `watch -x 'df -h | tail -1'` — there is no shell to interpret the pipe.

### Precision and interval control

- Default interval is 2 s; `-n` takes fractional values down to 0.1 s (`.` and `,` both work regardless of locale).
- `-p` (precise) compensates for the command's own runtime so iterations land on exact boundaries — the difference between "every ~2.3 s because the probe takes 0.3 s" and "every 2.0 s".
- The `WATCH_INTERVAL` environment variable persists a non-default interval across invocations.
- `-t` drops the two-line header; `-w` disables line wrapping (long lines truncate instead); `-c` interprets ANSI colors so colorized commands stay colored; `-C` (the default) strips them.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n SECS`, `--interval` | Seconds between runs; default 2, minimum 0.1, fractions allowed |
| `-d[=permanent]`, `--differences` | Highlight changes since last update (or since first) |
| `-g`, `--chgexit` | Exit when the visible output changes |
| `-q CYCLES`, `--equexit` | Exit after CYCLES identical outputs |
| `-e`, `--errexit` | Freeze and exit (after keypress) when the command fails |
| `-b`, `--beep` | Beep on non-zero exit |
| `-x`, `--exec` | Run via `execvp`, not `sh -c` — arguments literal, no shell |
| `-c` / `-C` | Interpret / strip ANSI color sequences |
| `-p`, `--precise` | Compensate runtime to keep intervals exact |
| `-t`, `--no-title` | Remove the header |
| `-w`, `--no-wrap` | Truncate instead of wrapping long lines |
| `-r`, `--no-rerun` | Do not re-run the command on window resize |

## Usage Patterns

```bash
# The reflex: watch disk space fill up during a large copy
watch -n5 df -h

# Highlight exactly what changed between samples
watch -d ls -l /var/tmp/incoming

# Accumulate all changes since you started watching (leak tracing)
watch -d=permanent free -m

# Block until a file appears, then return (poll-for-condition)
watch -n1 -g 'test -f /tmp/ready && echo GO'

# Wait for a flaky service to come back
watch -n2 -g 'curl -fsS -o /dev/null http://localhost:8080/health && echo UP'

# Exit once the counter stops moving (deploy settled)
watch -q5 -n10 'kubectl get pods -n ci | grep -c Running'

# Beep when a long job finishes or fails, watching its last line
watch -b -g 'tail -1 /var/tmp/job.status'

# Follow the newest log in a rotating directory (globs + substitution)
watch -n2 'tail -n3 $(ls -t /var/log/app/*.log | head -1)'

# Exec mode: literal argv, zero shell involvement
watch -n1 -x tail -n5 /var/log/syslog

# Keep colors from colorized commands (ip, ls --color=always)
watch -c 'ip -c addr show eth0'

# Fast polling of a counter file
watch -n0.2 'cat /sys/class/net/eth0/statistics/rx_packets'

# Header-free output for piping a single update to a file
watch -t -n3600 date +%s

# Watch a build directory for compile output appearing
watch -d -n1 'ls -lt src/*.o | head -5'

# Poll a queue depth with units
watch -n1 'redis-cli llen job-queue'

# Precise 1-second grid despite the probe taking ~200 ms
watch -p -n1 'curl -o /dev/null -s -w "%{time_total}\n" http://localhost:8080/health'

# Terminal-clock variant of the classic uptime glance, header included
watch -n30 uptime
```

### watch vs the alternatives

| Need | Reach for |
| --- | --- |
| Re-run an arbitrary command on screen | `watch` |
| Watch system/process state with real batch output | [`top -b`](./top.md), [`vmstat`](./vmstat.md) |
| React to filesystem *events* (not polls) | `inotifywait` (out of scope here) |
| Run on a schedule, unattended | cron / systemd timers |
| Log a command's output over time | `while` loop with `>>`, not `watch` |

The division: `watch` is for a human looking at a screen right now; everything that must survive into a file or a pager belongs to the batch-mode tools or a loop.

## Nuances and Gotchas

- **The quoting trap is the #1 failure.** `watch df -h | tail -1` pipes *watch's screen* into `tail`; the pipeline must be inside the quoted string: `watch 'df -h | tail -1'`. Same for redirections and command substitution — one level of shell-quoted string, and any inner quotes must nest (`'... "$(date +%s)"'`).
- **`-e` waits for a keypress.** In a script, `watch -e` that hits an error will sit there forever waiting for keyboard input. If automation needs exit-on-error semantics, run the command in a loop or guard it — `watch -e` is an interactive tool.
- **`-g` only sees the visible screen.** A change that lands below the first screenful never triggers the exit. Filter the command down until the compared output is a line or two.
- **Fresh shell every iteration.** No aliases or shell functions; `cd` does not persist between runs; environment changes made by the command evaporate. `PATH` differences between your interactive shell and `sh` can even change *which binary* runs.
- **Colors need two stars.** `-c` makes watch interpret ANSI codes, but many tools auto-disable color when not on a tty — force it (`ls --color=always`, `grep --color=always`).
- **Watch cannot be logged.** Its output is screen-replacement control sequences; redirecting or running it without a tty is meaningless. For a text record of the same loop: `while true; do date; cmd; sleep N; done >> log`, or `top -b` / `vmstat -t` which have real batch modes.
- **Interval floor is 0.1 s**, and each run waits for the command to *finish* before sleeping — an expensive probe at `-n0.1` becomes a self-inflicted load generator unless `-p` is understood.
- **BusyBox has no watch; macOS has none by default.** In minimal containers and on Macs the while-loop idiom or a brew/coreutils install is the fallback — and BusyBox's limited applets behave differently where they do exist.
- **The header eats two lines.** Inside small panes the effective viewport shrinks; `-t` reclaims them when the command prints exactly one screen.
- **`WATCH_INTERVAL` is a persistent default.** Exported in a shell profile, it silently re-intervals every `watch` invoked without `-n` — an env var is not a per-invocation setting, and profiles set years ago are why "watch runs every 10s here but 2s there".
- **No scrollback, no history.** Every repaint destroys the previous output; if you need to compare against a past state, that is what `-d=permanent` (accumulate highlights) and `-q CYCLES` (exit when stable) are for — or stop watching and log.

## Exit Status

| Code | When |
| --- | --- |
| 0 | Normal end: interrupted by the user, or `-g`/`-q` condition satisfied |
| 1 | Watch's own errors: bad options, command could not be run, terminal problems |

With `-e`, the process exits after the keypress following a failed command; do not build scripts on the exact propagated status — behavior there is implementation detail across procps versions. Interruption by `Ctrl-C` is the normal way to leave an unbounded watch and is not an error condition.

## Related Commands

- [`top`](./top.md) — batch mode (`top -b`) is the loggable way to watch system state over time.
- [`vmstat`](./vmstat.md) — already a repeating reporter; `watch vmstat 1` is redundant, `vmstat 5` is not.
- [`uptime`](./uptime.md) / [`free`](./free.md) — the classic one-liners people wrap in `watch`.
- [`ps`](./ps.md) — underlies most ad-hoc `watch 'ps ...'` pipelines.
- [`pgrep`](./pgrep.md) — the PID supplier inside `watch 'ps -p "$(pgrep -n java)"'` style probes.
- [Process management](../../admin/process-management.md) — signals and job control for the processes these loops watch.
- [procps overview](./overview.md) — the rest of the collection.

## Interview Questions

### Q: How exactly does watch execute its argument, and what follows from that?

As a full string to `sh -c`, once per interval (or via `execvp` with `-x`). Everything shell-flavored — pipes, globs, redirection, substitution — is interpreted *inside* that string, so the whole pipeline must be quoted as one argument; conversely each iteration gets a fresh shell with no aliases, no functions, and no state carried over. The exec-mode corollary: with `-x` there is no shell, so a pipeline string becomes a literal (and doomed) argv, while program arguments survive quoting intact.

### Q: What is wrong with `watch df -h | tail -1`?

The pipe binds to `watch`, not to `df`: watch runs `df -h`, paints the screen, and *its* screen output is piped into `tail -1` — you see one static line and the screen stops updating. The fix is quoting the pipeline into the command string, `watch 'df -h | tail -1'`, or exec mode for a plain command. Interviewers use this to test whether you understand that `watch`'s argument is a shell string, not a command prefix.

### Q: Design a shell one-liner that blocks until a service is healthy.

`watch -n2 -g 'curl -fsS -o /dev/null http://localhost:8080/health && echo UP'` — output is empty while curl fails and becomes `UP` on first success, and `-g` exits exactly when the visible output changes. It is polling, not event-driven, so add `-p` if interval precision matters, and remember the caveat that only on-screen output counts — keep the compared output to one line. The while-loop equivalent (`until curl ...; do sleep 2; done`) is equally valid but lacks the live display of *why* the service is still failing, which is watch's quiet advantage.

### Q: What does -d=permanent show that plain -d does not?

Plain `-d` highlights only what changed since the *previous* update — transient values flash and revert. `-d=permanent` accumulates: every value that has ever changed since the first sample stays highlighted, which turns watch into a cheap drift detector — run it against `free -m` or an `ls -l` listing and every field that ever moved remains lit, making slow leaks and periodic writers visible at a glance.

### Q: Why can't you log watch's output, and what do you use instead?

Watch writes screen-control sequences: it clears, repositions, and repaints, so its output stream only makes sense on a terminal and a capture is an unusable mess of escapes. The replacements have real plain-text modes: `top -b -d N -n M` for system snapshots, `vmstat -t` for columnar time series, or a hand-rolled `while true; do date; cmd; sleep N; done >> file` loop. The skill being tested is knowing which tools are *viewers* (screen-oriented) and which are *reporters* (stream-oriented).

### Q: When do you choose -x over the default shell mode, and what breaks if you switch?

Choose `-x` when the command is a fixed program with fixed arguments: arguments pass through as literal argv, so none of the double-quoting or expansion traps apply, and you save a shell startup per interval. Switching a shell-mode invocation to `-x` breaks anything shell-flavored — pipes, globs, substitution, and redirection silently stop working because there is no interpreter to run them; `watch -x 'df -h | tail -1'` would exec a binary literally named `df -h | tail -1` and fail. The rule of thumb: `-x` for static argv, shell mode the moment you need composition.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/watch.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
