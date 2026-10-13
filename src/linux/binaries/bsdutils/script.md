# script — record a terminal session to a typescript (with timing)

## Overview

`script` records everything that appears on a terminal session into a file — the *typescript* — and optionally a companion timing file that lets `scriptreplay(1)` replay the session with its original rhythm. It ships in the `bsdutils` package at `/usr/bin/script` (upstream util-linux; 3.0BSD ancestry). Under the hood it allocates a pseudoterminal, runs your shell (or `-c command`) inside it, and tees the raw byte stream to disk — which is also why it changes program behavior: any tool that checks `isatty(3)` now sees a terminal.

Three uses dominate: session audit trails (root shells, incident response), capturing output of commands that behave differently without a tty (colored `ls`, fancy progress bars, prompts), and producing replayable demos paired with `scriptreplay`/`scriptlive`. It is often confused with shell history (`history` misses output), with `tee` (captures piped streams, not a terminal, and changes the pipe semantics), and with terminal multiplexers like tmux (which can log panes but owns the session — `script` is a one-shot wrapper).

| Field | Value |
| --- | --- |
| Package | bsdutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/script |
| First appeared | 3.0BSD |
| Standards | — (BSD heritage; not in POSIX) |

## Synopsis

```
script [options] [file]
```

Common one-line forms:

```
script                         # record into ./typescript until you exit the shell
script -a session.log          # append to an existing log
script -c 'make test' out.log  # record one command instead of a shell
script -T time.tm -O out.log   # record with timing for scriptreplay
script --log-in in.log -T t.tm # also record what was typed (scriptlive material)
```

## How It Works

### The pseudoterminal loop

`script` allocates a pty, forks a child whose stdin/stdout/stderr are the pty slave, and executes `$SHELL` (or the `-c` command) there. Everything the child writes to the pty is read by the parent from the master side, written both to your real terminal and to the log file; everything you type flows in the opposite direction and can be logged with `--log-in`:

```
your terminal ◄──────► script (pty master)
                          │  tee the raw byte stream
                          ▼
                 typescript / log files
                          ▲
                          │ fork + exec, stdin/stdout = pty slave
                    $SHELL or -c command
```

Because the child genuinely runs on a tty, `isatty()` is true inside it — the classic trick `script -qec 'some-cli' /dev/null` exists to coax color output or interactive prompts out of programs that disable them when stdout is a pipe.

The family ecosystem, all fed by one recording session:

```
                        ┌────────────────────────────────────────────┐
                        │  script -T t.tm -O out.log --log-in in.log │
                        └───────────────┬────────────────────────────┘
                                        │ writes
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
         out.log                    t.tm                     in.log
      (content stream)        (classic/advanced             (typed bytes)
               │                timing entries)                  │
               │                      │                         │
               ▼                      ▼                         ▼
        cat/grep/col -b        scriptreplay              scriptlive
        (post-process)         (redisplay at pace)       (re-execute input)
```

### What lands in the typescript

The log is the *raw* pty output: header line, everything the session printed (including `\r\n` line endings, backspaces, escape sequences, colors), and a footer. Observed with `-c` and no tty attached:

```
Script started on 2026-10-09 16:38:31+00:00 [COMMAND="bash demo.sh" <not executed on terminal>]
step-one
step-two

Script done on 2026-10-09 16:38:31+00:00 [COMMAND_EXIT_CODE="0"]
```

The child's exit code is stored in the `COMMAND_EXIT_CODE` footer field regardless of options. `-q`/`--quiet` suppresses the start/done messages on the *terminal* (`Script started, output log file is 'x.log'` …), not the header/footer written into the file. The default file name is `typescript`; `--force` is required to write through a hard or symbolic link with that name (a symlink-attack guard).

File plumbing summary: the positional `file` argument and `-O/--log-out` are two spellings of the same destination (passing both is redundant); `-a/--append` applies to the output log; the input log has no default — `--log-in` without a value is not a thing, you must name the file. When only `--log-in` is given, output logging is disabled — `-I` alone records typed bytes, not the session display.

### Timing files: classic and advanced

`-T/--log-timing FILE` records a timeline alongside the content. Two formats exist (force with `-m classic|advanced`):

```
# classic: "<elapsed seconds> <byte count>" per output burst   (verified)
0.010113 10        # "step-one\r\n" reached the log 10 ms in
0.391612 10        # next burst 0.39 s later
0.302062 4         # final "\r\n" burst
```

```
# advanced (multi-stream): one letter per entry type, plus metadata headers
H 0.000000 START_TIME 2026-10-09 16:40:39+00:00
H 0.000000 SHELL /bin/bash
H 0.000000 COMMAND printf "abc\n"; sleep 0.2; printf "def\n"
O 0.010117 5
O 0.191611 5
H 0.000000 DURATION 0.212092
H 0.000000 EXIT_CODE 0
```

Classic is used when only one stream (usually output) is logged; advanced kicks in automatically when input and output are logged together (`-B`, or `-I` plus `-O`) and adds entry types `I` (input), `O` (output), `H` (header metadata), `S` (signal). The advanced format is what `scriptreplay --summary` reads. The deprecated `-t[FILE]` alias writes timing to stderr or a file; prefer `-T`.

### Input logging and the security cliff

`-I/--log-in FILE` records what was typed; `-B/--log-io` merges both streams into one file. The man page's warning deserves quoting in spirit: input is logged **independently of the terminal echo flag** — passwords typed at a non-echoing prompt land in the log in plaintext. Never point `-I`/`-B` at world-readable paths, and treat input logs as credentials when you audit them.

### Echo control

`-E auto|always|never` controls the ECHO flag on the pty slave. `auto` (default) disables echo on the pty when your real stdin is a terminal (you see your typing once, from your terminal), and enables it when stdin is a pipe so piped input becomes visible and loggable. `never` changes the log content itself: typed input is not repeated into the output stream.

### Flushing, limits, and exit codes

`-f/--flush` flushes the log after each write — the documented telecooperation trick is `mkfifo foo; script -f foo` while a colleague watches with `cat foo`. Flushing costs performance; `SIGUSR1` flushes on demand instead. `-o/--output-limit SIZE` (KiB/MiB/… suffixes) stops the child when the logs exceed the limit — note `-o` is a *size*, not a file name, a recurring flag-confusion trap. `-e/--return` makes `script` exit with the child's status (including the `128+N` signal convention); without `-e`, `script` exits 0 even when the child failed (verified: child `exit 3` → 0 without `-e`, 3 with `-e`).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a, --append` | append to the log instead of truncating |
| `-c, --command CMD` | run CMD instead of an interactive shell |
| `-e, --return` | propagate the child's exit code as script's own |
| `-f, --flush` | flush logs after each write (or send SIGUSR1) |
| `-q, --quiet` | no start/done messages on the terminal |
| `-I, --log-in FILE` | log input (⚠ includes non-echoed secrets) |
| `-O, --log-out FILE` | log output; default file is `typescript` |
| `-B, --log-io FILE` | log input+output interleaved (needs timing to split) |
| `-T, --log-timing FILE` | timing log for scriptreplay/scriptlive |
| `-m, --logging-format FMT` | force `classic` or `advanced` timing format |
| `-E, --echo WHEN` | pty echo: auto / always / never |
| `-o, --output-limit SIZE` | stop child when logs exceed SIZE (suffixes KiB…YiB) |
| `--force` | allow the default `typescript` file to be a (sym)link |
| `-t[FILE], --timing[=FILE]` | deprecated alias of `-T` (file optional, defaults to stderr) |

## Usage Patterns

```bash
# Audit trail for a root maintenance session
sudo script -a -T /var/log/admin-sessions/$(date +%F).time /var/log/admin-sessions/$(date +%F).log
```

```bash
# Record a session with timing for later replay
script -T timing.tm -O demo.log
# ... work ... exit
scriptreplay -t timing.tm -O demo.log
```

```bash
# Coax tty-only behavior out of a program (colors, prompts, progress bars)
script -qec 'ls --color=always /etc' /dev/null | less -R
```

```bash
# Wrap a CI step, keep its exit code for the pipeline gate
script -qec 'make test' build.log; status=$?
```

```bash
# Append today's runs to one rolling log without clobbering
script -a -c 'df -h' daily.log
```

```bash
# Record input too — the material scriptlive needs
script -T t.tm --log-in typed.log --log-out shown.log
```

```bash
# Telecooperation: let someone watch your session live
mkfifo /tmp/watch && script -f /tmp/watch
# colleague runs:  cat /tmp/watch
```

```bash
# Bounded recording for unattended captures
script -q -o 10MiB -T t.tm -O out.log -c 'stress-ng --cpu 1 -t 60s'
```

```bash
# Guard against nested script loops from shell init files (man NOTES pattern)
if [ -z "$SCRIPT_RUNNING" ]; then
    SCRIPT_RUNNING=1 script
fi
```

```bash
# Clean the CRs when post-processing a typescript
sed 's/\r$//' typescript | grep -i error
```

```bash
# The classic cleanup: col -b eats backspaces and underscores-overprint junk
col -bp < typescript > clean.txt   # col ships in util-linux; see its page
```

```bash
# Per-run file names so parallel sessions never clobber each other
script -a -T /tmp/audits/$(date +%F-%H%M%S).time /tmp/audits/$(date +%F-%H%M%S).log
```

```bash
# Flush on demand mid-session: SIGUSR1 works even without -f
script -O /tmp/long-run.log -c 'some-long-job' &
kill -USR1 %1                        # script flushes its logs on demand
```

```bash
# Check what was recorded without the noise: just the child's exit code
tail -1 out.log | grep COMMAND_EXIT_CODE
```

## Nuances and Gotchas

- **The log is raw, not pretty.** `\r\n` endings, backspaces (your "deleted" typos are all in there), and ANSI escapes are preserved. Naive greps match garbage; strip with `sed 's/\r$//'` or `col -b` first. Screen-manipulating programs (`vi`, `htop`) leave full-screen garbage — `script` is a hardcopy terminal emulator, not a video recorder.
- **`-o` is a size limit, not an output file.** `script -o out.log` fails with `failed to parse output limit size: 'out.log'` (verified). Output goes to `--log-out`/positional `file`; the limit flag is `-o/--output-limit`.
- **Input logs contain passwords.** `-I`/`-B` capture keystrokes regardless of terminal echo — sudo prompts, `read -s`, database passwords. Log them only deliberately, protect the file, and rotate/delete like credentials.
- **Exit code without `-e` is always script's own.** Pipelines and CI that assume the child's status propagate will silently pass on failures (verified: child exits 3, `script` exits 0). Add `-e`.
- **Non-interactive stdin can hang.** `echo foo | script` can wedge because the inner interactive shell never sees EOF (man BUGS). For scripted capture use `-c`.
- **Nesting is a footgun.** `script` inside `script` inside a shell that starts `script` in its profile = infinite loop; guard with an env var or restrict auto-start to login shells (`test -t 0` in `.profile`).
- **Pipes read more than you expect.** `script` in a pipeline can consume input meant for the child (man NOTES). Keep it out of pipelines.
- **Default file is `typescript`, truncated, not appended.** Two `script` invocations in a directory overwrite each other; use `-a`, or name files per run. `--force` exists because `typescript` being a symlink was an attack vector.
- **`$SHELL` decides the inner shell.** If `SHELL` is unset or set oddly in a cron/systemd context, the recorded session runs the Bourne shell assumption — test what `-c` actually executes.
- **Timing formats are not interchangeable.** `scriptreplay --summary` requires the advanced format; `--stream in` selection only means something with multi-stream logs. Record with explicit `-T`/`-I`/`-O` when the downstream tool is known.
- **The deprecated `-t` defaults to stderr.** `script -t` with no file argument streams timing data into stderr, where it interleaves with anything else on that channel — an ancient and confusing default; always give the file explicitly with `-T`.
- **Logs grow unboundedly.** A long session with a chatty program (tail -f, big builds) writes every repaint to disk; use `-o` for unattended runs, and remember append mode (`-a`) keeps growing yesterday's file rather than starting fresh.
- **No timestamps in the body.** Only the header/footer carry times; for time-correlated forensics pair the timing file (elapsed offsets) with the header START_TIME of the advanced format.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Recording finished (child status ignored unless `-e`) |
| child's status | With `-e`: the child's exit code, `128+N` if it died from signal N |
| >0 | `script`'s own errors (bad options, unwritable log, size limit hit) |

Verified locally: child `exit 3` → 0 without `-e`; → 3 with `-e`.

## Related Commands

- [`./scriptreplay.md`](./scriptreplay.md) — plays the typescript back with the timing file; display-only.
- [`./scriptlive.md`](./scriptlive.md) — re-*executes* the recorded input in a fresh shell; needs `--log-in`.
- [`./logger.md`](./logger.md) — line-level event logging into syslog, the complement to full-session recording.
- [`../util-linux/col.md`](../util-linux/col.md) — the traditional post-processor: `col -b` strips the backspace/CR noise from typescripts.
- [`./overview.md`](./overview.md) — the bsdutils collection hub. Upstream, the whole script family is util-linux — see [`../util-linux/overview.md`](../util-linux/overview.md) for that collection's scope.
- [`../../admin/systemd.md`](../../admin/systemd.md) — where scripted sessions meet `systemd-run`/`script`-style service capture.

## Interview Questions

### Q: What exactly is inside a `script` typescript, and why does it look "dirty"?

The raw byte stream of the pty: a `Script started on …` header, all output including `\r\n` pairs, backspaces from typos, ANSI color/escape sequences, and a `Script done … [COMMAND_EXIT_CODE=…]` footer. It emulates a hardcopy terminal, so anything the screen showed — including screen-manipulation garbage from `vi` — is in the file. Cleaning means stripping CRs and escape sequences; the dirtiness is the feature, since it makes replay faithful.

### Q: Why does `script -qec 'some-command' /dev/null` change a program's behavior?

Because the command now runs on a real pseudoterminal, so `isatty(stdout)` is true. Programs gate colors, progress bars, and interactive prompts on that check and otherwise degrade their output for pipes. The `/dev/null` positional just discards the log; `-e` would propagate the exit code; `-q` drops the start/done chatter.

### Q: Compare the classic and advanced timing file formats.

Classic is two whitespace-separated fields per line: elapsed seconds since the previous burst and the number of bytes output — sufficient for output-only replay. Advanced (multi-stream) prefixes each entry with a type letter (`H` header metadata, `I` input, `O` output, `S` signal) and records session metadata like START_TIME, COMMAND, DURATION and EXIT_CODE; it is produced automatically when input and output are logged together, and it is the only format `scriptreplay --summary` understands.

### Q: What is the security problem with `script --log-in`?

The input log captures every byte typed into the session *even when the terminal echo flag is off* — so passwords and tokens typed at hidden prompts are stored in plaintext. Input logs must be treated as credential stores: restrictive file modes, protected directories, deliberate retention, and never in world-readable CI artifacts. If you only need the output record, log with `-O` and skip `-I`/`-B`.

### Q: Your CI step `script -c 'make test' build.log` always passes, even when tests fail. Why, and what's the fix?

Without `-e/--return`, `script` exits with its own status (0) after the recording finishes, discarding the child's exit code — the footer in the log still shows `COMMAND_EXIT_CODE` but the process status doesn't. The fix is `script -e -c 'make test' build.log`, which returns the child's status, including the 128+N convention for signal deaths.

### Q: How do the three members of the script family divide the work?

`script` records: content to the typescript, timeline to the timing file, optionally input via `--log-in`. `scriptreplay` re-*displays* the output stream paced by the timing file — nothing is executed, so it is safe. `scriptlive` re-*executes* the recorded input stream in a fresh pty and shell — nothing is displayed from the old session, and everything the log contains runs again. The pairing rule: scriptlive requires the timing file plus an input log (`--log-in`/`--log-io`), and you should inspect the input first with `scriptreplay --stream in` because you are about to run it.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/script.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
