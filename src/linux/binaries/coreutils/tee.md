# tee — copy stdin to stdout and one or more files

## Overview

`tee` is the plumbing T-junction of the shell: it reads standard input, writes one copy to standard output, and writes identical copies to every file named as an argument. That single behavior solves a whole family of problems — log a build while watching it live, capture an intermediate pipeline stage without breaking the flow, write to a privileged file from an unprivileged pipeline, or fan one stream out to many sinks at once.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/tee`, from upstream GNU coreutils. The command is ancient — present in early AT&T UNIX — and is POSIX.1-2018-standardized with `-a` (append) and `-i` (ignore interrupts). GNU adds `-p` and `--output-error` for finer control over write errors, which is where the interesting engineering of this page lives.

`tee` is often confused with plain redirection (`>`), which replaces stdout instead of *adding* a file alongside it, and with the `sudo` redirection trap — `sudo cmd > /root/file` fails because *your* shell opens the file; `sudo tee` fixes it. The name is literal: it is the letter T drawn in pipes.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/tee` |
| First appeared / lineage | Early AT&T UNIX (1970s); every Unix and Unix-like since |
| Standards | POSIX.1-2018 (`tee`: `-a`, `-i`); GNU adds `-p`, `--output-error` |

## Synopsis

```
tee [OPTION]... [FILE]...
```

Input flows to stdout and to each FILE simultaneously. Main forms:

```
cmd | tee log.txt              # watch stdout, keep a copy
cmd | tee -a log.txt           # append instead of truncate
cmd | tee a.txt b.txt c.txt    # fan out to many files + stdout
cmd | sudo tee /etc/conf       # privileged write from unprivileged pipe
cmd | tee >(gzip > old.gz)     # tee into a process substitution
cmd | tee -p log | head        # tolerate a closed downstream reader
```

With no FILE, `tee` is a pure pass-through. A FILE operand of `-` means stdout (so `tee - -` duplicates).

## How It Works

### The copy loop

`tee` opens all FILE operands up front (truncating, unless `-a`), then loops: read a chunk from stdin, write it to every open descriptor plus stdout. There is no buffering policy of its own beyond the standard I/O it inherits — it copies chunks as they arrive, so its position inside a pipeline does not change upstream buffering:

```
                    ┌────────── tee ───────────┐
                    │                          │
   upstream ──────► │ chunk ──► stdout         │ ──────► downstream
   pipeline         │   ├──► FILE1             │
                    │   ├──► FILE2             │
                    │   └──► ...               │
                    └──────────────────────────┘
        open all files first (O_TRUNC, or O_APPEND with -a)
        read → write N+1 copies → repeat → close all
```

```
$ echo build started | tee build.log
build started
$ cat build.log
build started
```

### Write-error policy — the part interviews probe

What happens when one of those writes fails? A broken downstream pipe (`head` exited), a full disk, an unwritable path — each is a decision point, and `tee`'s defaults are deliberate:

- **Error writing to a pipe** (stdout, typically because the reader left): exit immediately, quietly — this is the classic SIGPIPE death, visible as status 141.
- **Error writing to a file operand** (full disk, bad path): diagnose on stderr, *keep going* with the remaining outputs, and exit nonzero at the end.

```
$ echo hi | tee /nope/f >/dev/null; echo $?
tee: /nope/f: No such file or directory
1
$ echo hi | tee /nope/f
hi                        # stdout still got the data
tee: /nope/f: No such file or directory
$ echo $?
1
```

`--output-error=MODE` overrides the defaults: `warn` (diagnose everything, continue), `warn-nopipe` (diagnose non-pipe errors, silently ignore EPIPE), `exit` (stop at the first error of any kind), `exit-nopipe` (stop on non-pipe errors, ignore EPIPE). `-p` is shorthand for `--output-error=warn-nopipe` — the "behave nicely in pipelines" mode.

### SIGPIPE, `head`, and pipefail

When a downstream reader exits early, the kernel raises SIGPIPE on tee's next write, and the default disposition kills the process — the shell reports 128+13 = 141:

```
$ seq 1 1000000 | tee /dev/null | head -n1
1
$ echo "${PIPESTATUS[@]}"        # without pipefail
141 141 0                        # seq and tee both died of SIGPIPE
$ set -o pipefail
$ seq 1 1000000 | tee /dev/null | head -n1 >/dev/null; echo $?
141                              # pipefail surfaces tee's death
$ seq 1 1000000 | tee -p /dev/null | head -n1 >/dev/null; echo $?
0                                # -p treats EPIPE as normal pipeline life
```

This is the canonical debugging scenario: a "failed" long pipeline that actually worked, failing only because `head`/`grep -m1` closed the pipe — and `set -o pipefail` turning an everyday Unix idiom into a nonzero status. `tee -p` (or `--output-error=warn-nopipe`) is the designed fix on the tee side.

### Signals

`-i`/`--ignore-interrupts` makes `tee` ignore SIGINT. Use case: `Ctrl-C` in a foreground pipeline kills the *producer*; with `-i`, tee survives long enough to flush what it already read to the log — useful for keeping the tail of interrupted captures. Note the limits: it covers SIGINT only, not SIGHUP/SIGTERM, and it is equally POSIX and GNU.

### Duplicate operands and append semantics

Files are opened separately and written independently, so listing the same file twice doubles the content, and each write position advances independently:

```
$ printf 'x\n' | tee f f >/dev/null && cat f
x
x
```

`-a` switches open mode from truncate to append, preserving prior content — the flag for log rotation by hand (`tee -a` into yesterday's log) and for accumulating output across multiple invocations.

## Options That Matter

| Option | Effect |
|---|---|
| `-a, --append` | Append to FILEs instead of truncating; prior content kept |
| `-i, --ignore-interrupts` | Ignore SIGINT, so Ctrl-C on the pipeline doesn't kill the tee itself |
| `-p` | Pipe-friendly mode: default `--output-error=warn-nopipe`; don't die on broken pipes |
| `--output-error=MODE` | `warn` / `warn-nopipe` / `exit` / `exit-nopipe` — explicit write-error policy |
| `--help`, `--version` | usage / version |

POSIX guarantees only `-a` and `-i`. `-p` and `--output-error` are GNU; scripts for busybox or BSD boxes must not rely on them.

## Usage Patterns

```bash
# Watch a build live and keep the full log
make 2>&1 | tee build.log
```

```bash
# Append to a persistent log across runs
./probe.sh | tee -a /var/log/probe.log
```

```bash
# The sudo-redirect idiom: unprivileged producer, privileged file
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-vm.conf
```

```bash
# Same idiom with heredocs for multi-line config
sudo tee /etc/motd >/dev/null <<'EOF'
Authorized access only.
EOF
```

```bash
# Silence the stdout copy when only the file matters
dmesg | sudo tee /var/log/dmesg.today >/dev/null
```

```bash
# Fan out to several consumers at once
curl -s "$URL" | tee raw.json >(jq . > pretty.json) >/dev/null
```

```bash
# Capture an intermediate stage without breaking the pipeline
ps aux | tee ps.snapshot | grep -c nginx
```

```bash
# Tee into a compressor (process substitution)
gzip -c big.csv > big.csv.gz &
cat big.csv | tee >(gzip -c > big.csv.gz) | head -c 1000
```

```bash
# Pipeline with early exit: don't fail the whole chain when head leaves
long_job | tee -p audit.log | head -n 20
```

```bash
# Keep logging despite Ctrl-C on the producer
tcpdump -i eth0 -w - 2>/dev/null | tee -i capture.bin >/dev/null
```

```bash
# Mirror one download to disk and a checksum simultaneously
curl -sLo - "$URL" | tee image.iso | sha256sum
```

```bash
# Structured debug tap on any pipeline stage
ps aux | tee /dev/stderr | awk 'NR==1 || /chrome/' | wc -l
```

## Nuances and Gotchas

- **`sudo cmd > file` is not `cmd | sudo tee file`.** The `>` redirect is performed by *your* (unprivileged) shell before sudo even runs, so it fails with "Permission denied" on root-owned paths. `sudo tee` puts the privileged process on the write side. The same logic applies to `>>` → `sudo tee -a`. Alternative: `sudo sh -c 'cmd > file'` — heavier and shell-quoting-sensitive.
- **SIGPIPE under `set -o pipefail` is the #1 tee surprise.** `producer | tee log | head` exits 141 because tee was killed when head left — even though the log is fine and nothing really failed. Either accept 141, add `|| true`, or use `tee -p`. Conversely, remember that *without* pipefail, a tee that genuinely failed (disk full) can hide inside an otherwise-successful `$?`.
- **`-i` ignores only SIGINT.** A pipeline killed via SIGTERM or a closed terminal (SIGHUP) still takes tee down; for robust capture use `nohup`, `setsid`, or `timeout`-style supervision rather than `-i`.
- **Same file listed twice writes everything twice** (`tee f f`), because each operand is an independent descriptor. Alias or variable expansion can silently duplicate a path — dedupe arguments if it matters.
- **File creation follows normal open rules:** new files get `0666 & ~umask`, existing files keep their permissions, and `-a` never extends a file you lack write access to — tee running as you cannot append to root's file; only `sudo tee` can.
- **Partial writes on ENOSPC:** when the disk fills, tee diagnoses and continues to stdout; the file gets a truncated copy with no marker inside the file itself. Check tee's exit status (nonzero) rather than trusting the log's completeness.
- **tee does not fix buffering.** A producer whose libc block-buffers stdout when piped still dribbles late; if you need line-fresh logging, wrap the producer: `stdbuf -oL producer | tee log`. (See `stdbuf`.)
- **Portability:** `-a` and `-i` are universal (POSIX). `-p` and `--output-error` are GNU-only; BusyBox tee supports `-a`/`-i`; BSD/macOS tee likewise lacks `-p`. A `-p`-dependent script breaks quietly on macOS.
- **Process-substitution order:** `tee >(cmd)` starts the consumer concurrently; tee does not wait for it, so its exit status and output interleaving are unsynchronized — for strict ordering, use a named pipe (FIFO) or restructure.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All chunks written to every output; also with `-p`/`warn-nopipe` when only EPIPE occurred |
| 1 | Any diagnosed write error (bad path, full disk) reached the end-of-run check, or `--output-error=exit` hit an error |
| 141 | Killed by SIGPIPE (default mode, downstream reader gone) — 128+13 |

## Related Commands

- [`overview`](./overview.md) — GNU Coreutils collection hub.
- [`stdbuf`](./stdbuf.md) — controls the buffering that tee inherits; pair for live logs.
- [`cat`](./cat.md) — the pure concatenation counterpart (files → stdout; tee is stdin → files+stdout).
- [`nohup`](./nohup.md) — survives hangups; the robust alternative to `-i`.
- [`head`](./head.md) — the early-exiting downstream reader that triggers SIGPIPE.
- [`mkfifo`](./mkfifo.md) — named pipes for the ordering guarantees process substitution lacks.
- [`timeout`](./timeout.md) — bounds a tee'd capture run.
- [Process management](../../admin/process-management.md) — signals, SIGPIPE, and exit-status arithmetic behind 141.

## Interview Questions

### Q: Why does `echo x | sudo tee /etc/sysctl.conf` work when `sudo echo x > /etc/sysctl.conf` fails?

Redirection is performed by the calling shell before the command runs, and the calling shell is unprivileged — so `>` on a root-owned file fails with EACCES regardless of sudo on the left side. `sudo tee` places the privileged process at the receiving end of the pipe: the shell only builds a pipe (always permitted), and root's tee opens the target. This is also why the idiom usually ends with `>/dev/null` — to discard tee's echo of the data on stdout. Mention `sudo sh -c '...'` as the quoting-hazardous alternative.

### Q: A nightly script runs `produce | tee log | head -c 1M` and pipefail reports 141. Nothing looks wrong in the log. Explain and give two resolutions.

When `head` has consumed its quota it exits, the pipe closes, and tee's next write raises SIGPIPE, killing it (128+13=141); with `pipefail` that status becomes the pipeline's. The log is complete up to the cut — the "failure" is the designed early-exit idiom. Resolution 1: `tee -p` (or `--output-error=warn-nopipe`) makes tee treat EPIPE as normal, exiting 0. Resolution 2: restructure so no early exit exists (`head` → full consumer), or tolerate the status (`... || [ $? -eq 141 ]`). Knowing the 141 = 128+SIGPIPE(13) arithmetic is the expected detail.

### Q: What does `tee` do when one of its output files becomes unwritable mid-stream — say the disk fills?

Default mode: writes to pipes and stdout are fatal (exit immediately on pipe errors), but errors on file operands are diagnosed on stderr and tee *continues* serving its remaining outputs, exiting nonzero at the end. So `tee full_disk.log` keeps streaming to stdout while the log silently stops growing — the shell sees an error only via `$?`. With `--output-error=exit` tee aborts at the first error instead, and with `warn` even pipe errors become non-fatal diagnostics. The design goal: never let one bad sink destroy data meant for the others.

### Q: Explain the difference between `cmd > f`, `cmd | tee f`, and `cmd | tee -a f`, including what happens to stdout.

`cmd > f` redirects stdout into f — stdout sees nothing, and f is truncated. `cmd | tee f` sends stdout through the pipe to the terminal (or next stage) *and* writes a truncated copy to f — the stream is duplicated, not diverted. `cmd | tee -a f` is the same but appends, preserving f's previous content. The trap to mention: with `>`, exit status and any "tee died" concerns vanish (there is no tee), while with `tee` you gain a second consumer whose write errors surface in `$?` and whose presence in the pipeline affects SIGPIPE dynamics.

### Q: Why might `producer | tee log | consumer` appear to buffer output, and how do you get live logs?

The buffering is upstream, not in tee: when a producer's stdout is a pipe rather than a TTY, libc switches from line-buffered to block-buffered, so data arrives at tee in 4-8 KB clumps. tee copies chunks faithfully and cannot flush what it hasn't received. The fix targets the producer: `stdbuf -oL producer | tee log` forces line buffering via LD_PRELOAD, or the producer offers its own flush/`--line-buffered` flag (grep does). Interview point: naming *which* process's buffer it is distinguishes people who've debugged this from people who've read about it.

### Q: Is `tee` POSIX, and which of its flags would you avoid in a portable script?

Yes — POSIX.1-2018 specifies `tee [-ai] [file...]`, covering append and interrupt-ignore, both of which behave identically on GNU, BusyBox, BSD, and macOS. `-p` and `--output-error` (the write-error policy modes) are GNU coreutils extensions; a script relying on them degrades on macOS/BSD and busybox-initramfs environments, where a broken pipe kills tee with 141 again. Portable scripts either accept the default error semantics or explicitly handle the 141 status, and they treat tee's nonzero exit as "a sink failed" — a diagnostic, not necessarily a pipeline failure.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/tee.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
