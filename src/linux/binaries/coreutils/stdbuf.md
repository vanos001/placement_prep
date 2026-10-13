# stdbuf — run a command with adjusted stdio buffering

## Overview

`stdbuf` launches a command with the buffering of its standard C library
streams (`stdin`, `stdout`, `stderr`) preset to a mode you choose. Its main
job is fixing the classic pipeline stall: a long-running program whose output
sits in a fully buffered `stdout` for minutes because `stdout` is a pipe
instead of a terminal. Prefixing the program with `stdbuf -oL` makes every
newline reach the pipe immediately, so downstream `grep`, `awk`, or log
collectors see output in real time.

It ships in the Debian `coreutils` package and lives at `/usr/bin/stdbuf`
(on merged-`/usr` systems `/bin/stdbuf` resolves to the same file). Unlike
most of coreutils it is a pure GNU addition — there is no POSIX `stdbuf`, no
BSD equivalent, and nothing comparable in the traditional Unix toolbox. The
nearest external analogues are `unbuffer` (from expect) and `script -qec`,
both of which fake a terminal instead of adjusting buffers.

People usually meet `stdbuf` in two places: tailing a chatty log through a
pipeline, and interview questions about why `prog 2>&1 | grep` prints nothing
until the program exits. It is often confused with `tee`, which sets its own
buffering and thereby overrides `stdbuf` — a documented exception, not a bug.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/stdbuf` |
| First appeared / lineage | GNU coreutils 8.x era (circa 2010); no older Unix heritage |
| Standards | none — GNU extension, not in POSIX |

## Synopsis

```text
stdbuf OPTION... COMMAND [ARG]...
```

```bash
stdbuf -oL COMMAND       # stdout: line buffered
stdbuf -o0 COMMAND       # stdout: unbuffered
stdbuf -e0 -oL COMMAND   # stderr unbuffered, stdout line buffered
stdbuf -o1M COMMAND      # stdout fully buffered, 1 MiB buffer
```

## How It Works

C stdio offers three buffering modes:

```text
┌──────────────────┬──────────────────────────────────────────────────┐
│ Mode             │ Behaviour                                        │
├──────────────────┼──────────────────────────────────────────────────┤
│ unbuffered (0)   │ every character is written immediately           │
│ line buffered L  │ the buffer flushes on every '\n'                 │
│ fully buffered   │ flushes only when the buffer fills (or at exit)  │
└──────────────────┴──────────────────────────────────────────────────┘
```

The default mode is not one value but a rule: streams
connected to a terminal are line buffered, streams connected to a pipe or
file are fully buffered, and `stderr` is unbuffered by default. That rule is
why a program looks interactive when run directly but "hangs" mid-pipeline.

The size of the fully buffered default is an implementation constant —
`BUFSIZ` from `<stdio.h>`, typically 8 KiB on glibc — chosen at libc build
time, not by the kernel. Nothing about the pipe itself demands 8 KiB
batches; it is purely a userspace decision made inside the writing process.
That is also why the fix must happen inside the process, and why no amount
of kernel or reader-side tuning (bigger pipe buffers, `grep --line-buffered`
alone) can force a block-buffered writer to flush sooner.

Two standard-library details complete the picture. First, a program can
flush manually — `fflush(stdout)` — and many do before reading input, which
is why *some* pipelines appear to work until an unusual code path skips the
flush. Second, the C standard only guarantees the terminal/pipe distinction
for "input/output streams" and "error streams"; real implementations agree,
but the precise default sizes vary between libc builds, so never hard-code
an observed chunk size into a parser.

`stdbuf` works by preload injection. It execs the command with `LD_PRELOAD`
pointing at a helper library — on Debian this is
`/usr/libexec/coreutils/libstdbuf.so` — whose ELF constructor calls
`setvbuf(3)` on each standard stream *before* the program's `main()` runs.
The program then inherits whatever mode you asked for:

```text
┌─────────┐  LD_PRELOAD=libstdbuf.so  ┌──────────────┐   pipe    ┌──────┐
│ stdbuf  │ ────────────────────────▶ │ COMMAND main │ ────────▶ │ grep │
│ wrapper │  constructor: setvbuf()   │ (C stdio)    │  \n flux  └──────┘
└─────────┘                           └──────────────┘
```

Because the adjustment happens in-process, it applies to every `printf`,
`puts`, and `fwrite` the program makes — but only to C stdio streams. Raw
`write(2)` syscalls, and C++ `iostreams`, never touch stdio buffers and are
unaffected.

```bash
$ echo hi | stdbuf -oL cat
hi
# exit status of COMMAND propagates:
$ stdbuf -o0 /nonexistent; echo $?
stdbuf: failed to run command '/nonexistent': No such file or directory
127
```

## Options That Matter

| Option | Effect |
|---|---|
| `-i MODE` | Set buffering of standard input (`L` is invalid here — stdin cannot be line buffered) |
| `-o MODE` | Set buffering of standard output |
| `-e MODE` | Set buffering of standard error |
| `MODE = 0` | Unbuffered: flush on every character |
| `MODE = L` | Line buffered: flush on every newline (stdout/stderr only) |
| `MODE = SIZE` | Fully buffered with an explicit buffer size |
| `SIZE` suffixes | `K` 1024, `KB` 1000, `M`/`MB`, `G`, `T`, ... (binary and decimal both accepted) |

MODE applies to exactly one stream, so realistic invocations are usually of
the form `stdbuf -oL -eL cmd` — line-buffer both output streams.

## Usage Patterns

```bash
# The flagship idiom: watch a log through grep without the 4 KiB stall
stdbuf -oL tail -f /var/log/nginx/access.log | grep --line-buffered 500
```

```bash
# Merge stderr into the pipe and still see matches as they happen
stdbuf -oL -eL ./batchjob 2>&1 | grep ERROR
```

```bash
# Unbuffered stdout for a program you drive byte-by-byte over a pipe
stdbuf -o0 ./expect-style-server | socat - TCP:localhost:9000
```

```bash
# Give a huge buffer to a program that writes many small records
stdbuf -o4M ./export --stream | gzip > export.gz
```

```bash
# Line-buffer a build so make's output interleaves correctly with warnings
stdbuf -oL make -j8 2>&1 | tee build.log
```

```bash
# Both streams through awk in real time during a deployment
ssh host "stdbuf -oL systemctl status nginx" | awk '/Active:/'
```

```bash
# Compare buffering behaviour: one flushes live, the other in chunks
stdbuf -oL ping -c 5 example.org | grep -c ttl
ping -c 5 example.org | grep -c ttl
```

```bash
# Keep stdin unbuffered when a program asks for input through a pipe
printf 'yes\n' | stdbuf -i0 ./quiz
```

## Nuances and Gotchas

- **Programs that set their own buffering win.** `tee` explicitly adjusts its
  own streams, so `stdbuf -o0 tee` silently does nothing — the man page
  documents this. Any program calling `setvbuf`/`setbuf` after startup
  overrides the preload.
- **Non-stdio I/O is invisible to stdbuf.** `dd`, `cat` (for large blocks),
  and anything using raw `read(2)`/`write(2)` are unaffected. C++ programs
  using `iostream` are also unaffected — `stdbuf` only touches C stdio.
- **Statically linked binaries ignore it.** `LD_PRELOAD` works by dynamic
  linking; a static binary has no `libc` symbols to interpose. Go and Rust
  programs (which bypass stdio anyway) are doubly out of reach.
- **Setuid/setcap programs drop the preload.** Secure-execution mode ignores
  `LD_PRELOAD`, so `sudo stdbuf -oL cmd` adjusts nothing on `cmd`.
- **`-iL` is rejected**: stdio line-buffering is meaningless for input
  streams, and coreutils refuses the combination rather than guessing.
- **`2>&1 | grep` hides the real problem.** The stall comes from the
  *producer's* block-buffered stdout, not from `grep` (whose own output you
  may also need `grep --line-buffered` to unblock downstream).
- **It only handles the first three streams.** Files the program opens itself
  keep their default buffering; there is no way to target fd 4.

## Exit Status

| Status | Meaning |
|---|---|
| that of COMMAND | `stdbuf` transparently propagates the child's exit status |
| 126 | COMMAND was found but could not be executed |
| 127 | COMMAND could not be found |

There is no special "buffering failed" status — if the preload cannot help
(static binary, secure-execution mode), the command simply runs unmodified.

## Related Commands

- [`timeout`](./timeout.md) — put a deadline on the same pipelines stdbuf fixes.
- [`yes`](./yes.md) — the canonical fast pipe writer; buffering explains its throughput folklore.
- [`stty`](./stty.md) — terminal-level line discipline, a different layer of the same I/O stack.
- [bash](../../shell/bash.md) — pipeline semantics, `2>&1`, and where buffering problems appear.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: Why does `./app | grep ERROR` hang until the app exits, and how do you fix it?

When stdout is a pipe, C stdio switches from line buffered (the terminal
default) to fully buffered, typically 4-8 KiB. Output accumulates until the
buffer fills or the process exits. `stdbuf -oL ./app | grep ERROR` calls
`setvbuf` on stdout before `main()` runs, restoring line-flushed behaviour.
If the app adjusts its own buffering (like `tee`) or is statically linked,
`stdbuf` cannot help and you need `unbuffer` or a code change.

### Q: What mechanism does stdbuf use, and what are its hard limits?

It sets `LD_PRELOAD` to a small coreutils library whose ELF constructor runs
`setvbuf(3)` on `stdin`, `stdout`, and `stderr` before `main()`. Limits follow
from the mechanism: only dynamically linked C stdio I/O is affected, secure
executables ignore `LD_PRELOAD`, programs that call `setvbuf` themselves
override it, and raw syscall I/O (`dd`, C++ streams) is untouched.

### Q: Why is there no `stdbuf -iL`?

stdio line buffering is an output concept: it means "flush the output buffer
when a newline is written". It has no sensible meaning for an input stream,
so coreutils rejects the combination instead of accepting it silently. Input
can only be unbuffered (`-i0`) or fully buffered with an explicit size.

### Q: A colleague says "stdbuf doesn't work on our Go service". Explain.

Two independent reasons. First, Go's runtime performs its own I/O syscalls
and does not use C stdio, so there is no stdio buffer to adjust. Second, even
a C program compiled statically would ignore `LD_PRELOAD` because there are
no dynamic symbols to interpose. The fix belongs in the application (flush
explicitly) or a terminal-faking wrapper like `unbuffer`.

### Q: Which buffer sizes does `stdbuf -o10M` actually mean, and why do suffixes matter?

`M` means 1024*1024 bytes (binary), while `MB` means 1000*1000 (decimal) —
the same convention as coreutils size options like `dd` and `head -c`. The
distinction only matters for large buffers or storage capacity math, but
interviewers use it to check you read the man page rather than guessing.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/stdbuf.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
