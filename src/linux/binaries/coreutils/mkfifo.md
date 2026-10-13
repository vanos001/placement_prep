# mkfifo — create named pipes (FIFOs)

## Overview

`mkfifo` creates a named pipe: a special file of type FIFO (`p` in `ls -l`, "fifo" in `stat`) that gives unrelated processes a rendezvous point for unidirectional byte-stream I/O. Unlike the anonymous pipes the shell creates with `|`, a FIFO lives in the filesystem namespace under a name you choose, so two processes that know only the path — started at different times, from different shells, with no common ancestor — can connect. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/mkfifo` and is POSIX-standardized.

`mkfifo` is often confused with `mknod NAME p` (which creates the identical object), with `|` (anonymous, lifetime bound to the two processes), and with a regular file (a FIFO stores nothing on disk — data lives in a kernel buffer and vanishes after being read).

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mkfifo |
| First appeared | Named pipes in AT&T System III (early 1980s); `mkfifo` utility standardized in POSIX.2 |
| Standards | POSIX.1-2018 (`mkfifo`) |

## Synopsis

```
mkfifo [OPTION]... NAME...
```

Common one-line forms:

```
mkfifo /tmp/pipe            # default mode a=rw minus umask (0644 with umask 022)
mkfifo -m 600 /tmp/secret   # explicit mode, like chmod
mknod /tmp/pipe p           # the same object via mknod
```

## How It Works

### What a FIFO is

A FIFO is a filesystem entry whose inode is marked `S_IFIFO`. It carries no data on disk: writers append to a kernel ring buffer (64 KiB by default on Linux, tunable per-pipe via `fcntl(F_SETPIPE_SZ)`), and readers drain it in FIFO order. When all writers close, readers see EOF; when a writer has no reader left, it gets `SIGPIPE` (shell children die) or `EPIPE`. Verified type and default mode on this system:

```bash
$ mkfifo pipe1
$ stat -c '%F mode=%a name=%n' pipe1
fifo mode=664 name=pipe1
$ ls -l pipe1
prw-rw-r-- 1 z z 0 Oct  9 10:06 pipe1
```

The default mode is `a=rw` masked by the umask — `0666 & ~022` here. Size is always 0; the kernel buffer is invisible to `ls`.

### The open() rendezvous

The behavior people find surprising happens at `open()`, before any I/O. The kernel blocks opens until both sides are present:

```
open(O_RDONLY)  blocks until some process opens the FIFO for writing
open(O_WRONLY)  blocks until some process opens the FIFO for reading
open(O_RDWR)    never blocks (GNU/Linux extension; avoids the rendezvous)
```

Verified by bounding both sides (the outer `timeout` must wrap the process that *does the open* — see the gotcha below):

```bash
$ mkfifo pipe1
$ timeout 3 bash -c 'printf "hello-from-writer\n" > /tmp/gnd/pipe1' &
$ sleep 0.3
$ timeout 3 bash -c 'exec cat < /tmp/gnd/pipe1'
hello-from-writer
$ echo $?
0
```

A reader with no writer ever arriving stays parked in `open()`:

```bash
$ timeout 2 bash -c 'exec cat < /tmp/gnd/pipe1'; echo "exit=$?"
exit=124          # killed by timeout while blocked in open()
```

A writer with no reader blocks the same way — `open(O_WRONLY)` waits; the `SIGPIPE` story only begins *after* a successful open whose readers then all close.

### FIFO vs the alternatives

| | Anonymous pipe `\|` | Named pipe (FIFO) | UNIX socket |
| --- | --- | --- | --- |
| Namespace | none (kernel object) | filesystem path | filesystem path |
| Direction | one-way | one-way | two-way |
| Participants | parent/child or same pipeline | any process that opens the path | any process (plus credentials) |
| Lifetime | dies with the processes | persists until unlinked | persists until unlinked |
| Datagrams/records | byte stream | byte stream (atomic ≤ PIPE_BUF) | stream or datagram |
| Created by | shell, `pipe(2)` | `mkfifo` / `mknod p` | `socket(2)`-based tools |

The FIFO's niche is the first two rows: a persistent, shareable, one-way byte stream with a name.

### Data flow and multi-writer behavior

```
   producer(s)                      kernel buffer            consumer
 ┌───────────────┐  write()  ┌──────────────────────┐  read()  ┌────────┐
 │ tar | gzip    │ ────────▶ │ 64 KiB ring buffer    │ ───────▶ │ ssh,   │
 │ log tailer    │           │ drains in FIFO order  │          │ cat,   │
 └───────────────┘           └──────────────────────┘          │ archiver│
      each open() waits for its counterpart; writers whose    └────────┘
      records are ≤ PIPE_BUF (4096 bytes on Linux) do not
      interleave mid-record
```

Multiple writers may share one FIFO; reads interleave at record granularity for writes up to `PIPE_BUF`. When the last writer closes, the reader's next `read()` returns 0 — EOF — which is what lets a consumer terminate cleanly.

### Classic producer–consumer, end to end

```bash
# Feed a slow consumer from a fast producer through a named pipe
mkfifo /tmp/feed
timeout 3 bash -c 'printf "AAA\n" > /tmp/feed' &
timeout 3 bash -c 'printf "BBB\n" > /tmp/feed' &
sleep 0.3
timeout 3 bash -c 'exec cat < /tmp/feed'
AAA
BBB
rm -f /tmp/feed
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m`, `--mode=MODE` | Set permission bits as in `chmod` (exact mode, not umask-masked) instead of the default `a=rw` minus umask |
| `-Z` | Set the SELinux security context to the default type |
| `--context[=CTX]` | Like `-Z`, or set an explicit SELinux/SMACK context |

That is the entire option list — `mkfifo` is a two-trick tool: the name operand and the mode.

## Usage Patterns

```bash
# Simple relay: producer and consumer in separate terminals
mkfifo /tmp/pipe
grep ERROR /var/log/syslog > /tmp/pipe     # terminal 1: blocks until reader
less /tmp/pipe                             # terminal 2: drains the stream
```

```bash
# Insert a processing stage into an existing pipeline without rewriting it
mkfifo /tmp/stage
zcat access.log.gz > /tmp/stage &          # producer keeps its own process
awk '$9==500' < /tmp/stage | wc -l         # consumer filters 500s
rm -f /tmp/stage
```

```bash
# Stream an archive to a remote host: tar writes the FIFO, ssh drains it
mkfifo /tmp/xfer
tar -czf /tmp/xfer bigdir &                # waits until ssh opens the pipe
ssh remote 'tar -xzf -' < /tmp/xfer
rm -f /tmp/xfer
```

```bash
# Private FIFO for sensitive traffic: exact mode at creation
mkfifo -m 600 /run/user/1000/myapp-ctl
```

```bash
# Bound a possibly-hanging reader: timeout must wrap the opener
timeout 5 bash -c 'exec consumer < /tmp/pipe'
```

```bash
# Find the FIFOs already on a system
find /run /tmp -type p 2>/dev/null
```

```bash
# Clean up — a FIFO is just an inode; unlink it like a file
rm /tmp/pipe
```

```bash
# Test FIFO-ness in shell
[ -p /tmp/pipe ] && echo "named pipe present"
```

```bash
# Two-way conversation: one FIFO per direction (a socket would be simpler).
# stdbuf -oL matters: tr's stdout is a FIFO, so stdio buffers fully by default.
mkfifo /tmp/req /tmp/resp
stdbuf -oL tr a-z A-Z < /tmp/req > /tmp/resp &   # "server": uppercases requests
bash -c 'exec 3>/tmp/req; exec 4</tmp/resp; echo ping >&3; head -1 <&4'
PING
rm -f /tmp/req /tmp/resp
```

```bash
# Throttle a flood into a slow consumer: the 64 KiB buffer is the queue
mkfifo /tmp/slowlog
journalctl -f > /tmp/slowlog &
python3 -u /opt/parse.py < /tmp/slowlog
```

## Nuances and Gotchas

- **Scripts hang at open(), not at read().** The classic failure: `cat < /tmp/pipe` with no writer parks the *shell* in the open() syscall forever. Interviewers love this one; the fix is ensuring a writer exists, or opening `O_RDWR` in a helper, or bounding the process that opens.
- **`timeout` cannot rescue a shell redirection.** `timeout 5 cat < /tmp/pipe` does *not* time out: the invoking shell performs `< /tmp/pipe` before `timeout` even starts, and the timer never begins. Verified during this write-up — the bounded form is `timeout 5 bash -c 'exec cat < /tmp/pipe'`, where the open happens inside the timeout'd process. This is the deepest gotcha in the whole FIFO story.
- **SIGPIPE kills producers silently.** If your consumer exits early, the producer's next write raises `SIGPIPE`; in scripts that often looks like "the job just vanished". Set `trap '' PIPE` (and handle `EPIPE`) when the producer must survive.
- **The FIFO outlives the conversation.** Nothing removes it automatically — every example above ends with `rm`. Leftover FIFOs in `/tmp` are a hygiene and (on multi-user systems) a squatting hazard; use `-m 600` or a private `$XDG_RUNTIME_DIR`.
- **Atomicity is bounded.** Writes up to `PIPE_BUF` (4096 bytes on Linux) are atomic; larger streams from multiple writers may interleave arbitrarily. Design record boundaries accordingly.
- **stdio buffering bites FIFO peers.** A filter writing to a FIFO (not a tty) gets stdio's full buffering, so short replies may sit in userspace indefinitely while the peer blocks in read(). Verified while writing this page: plain `tr a-z A-Z < req > resp` never delivered a 5-byte answer; `stdbuf -oL tr ...` (see [stdbuf](./stdbuf.md)) delivers it instantly. The other cure is closing your write end (`exec 3>&-`) so the peer sees EOF and flushes on exit.
- **Not seekable, one direction.** `lseek` fails; each byte is delivered once. Two-way conversations need two FIFOs (or a socket).
- **Portability.** `mkfifo` and its `-m` are POSIX and available everywhere, including BusyBox. `-Z` is GNU/SELinux. Some filesystems (classic FAT) cannot host FIFOs — `mkfifo` fails there regardless of permissions.
- **`mkfifo` vs `mknod p`.** Identical resulting inode; `mkfifo` is the friendlier, more portable spelling of the same syscall with `S_IFIFO`.
- **No verbose flag exists.** Unlike `mkdir -v`, `mkfifo` has nothing to say on success — silence is success; check with `stat -c %F` when in doubt.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All FIFOs created |
| 1 | Any failure: name exists, unwritable parent, unsupported filesystem, invalid mode |

## Related Commands

- [`mknod`](./mknod.md) — the general special-file creator; `mknod NAME p` builds the same FIFO.
- [`cat`](./cat.md) — the standard test reader/writer for FIFO experiments.
- [`timeout`](./timeout.md) — bounds blocked processes — provided the open happens inside it.
- [`stdbuf`](./stdbuf.md) — fixes the stdio buffering that delays FIFO-to-FIFO filters.
- [`test`](./test.md) — `-p` checks for the existence of a FIFO.
- [`rm`](./rm.md) — unlinks the FIFO when the conversation is over.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [bash](../../shell/bash.md) — process substitution and job control, the anonymous-pipe counterpart.
- [find](../../shell/find.md) — `-type p` locates FIFOs across a tree.

## Interview Questions

### Q: What exactly blocks when you use a FIFO, and when?

The `open()` calls. A reader's `open(O_RDONLY)` blocks until a writer opens the path, and a writer's `open(O_WRONLY)` blocks until a reader opens it — the kernel rendezvous. After that, `write()` blocks only while the 64 KiB kernel buffer is full, and `read()` blocks while the buffer is empty (returning EOF once every writer has closed). Writing after all readers closed raises `SIGPIPE`/`EPIPE`. With `O_NONBLOCK`, the asymmetry matters: `O_RDONLY` succeeds immediately even with no writer, while `O_WRONLY` fails with `ENXIO`.

### Q: Why does `timeout 5 cat < fifo` not time out, and how do you bound it correctly?

Because the redirection is performed by the invoking shell *before* `timeout` execs: the shell blocks in `open()` on the FIFO, and `timeout`'s five-second timer never starts. To bound it, make the blocked process the one timeout controls — `timeout 5 bash -c 'exec cat < fifo'` — or have the shell open the FIFO against a guaranteed writer. This is a recurring production incident shape: a "timeboxed" backup reader that hangs forever.

### Q: What's the difference between `prog1 | prog2` and routing both through a named pipe?

`|` creates an anonymous pipe owned by the shell: both programs must be started together, and the pipe dies with them. A FIFO decouples them in time and process tree: producer and consumer only share a path name, can be started independently (or by different users, subject to permissions), and the connection endpoint persists between conversations. Cost: you manage creation, permissions, cleanup, and the open-blocking semantics yourself.

### Q: Design a shell-level producer/consumer with three parallel producers and one consumer. What do you watch out for?

Create the FIFO with a restrictive mode (`mkfifo -m 600`), start each producer writing to it, then start the consumer — or start the consumer first; order doesn't matter as long as every open eventually finds its counterpart. Writes of ≤ `PIPE_BUF` (4096 bytes on Linux) won't interleave mid-record, so keep records under that size or funnel producers through a lock. The consumer must read until EOF, and cleanup (`rm`) is manual; a producer dying early changes when EOF arrives, which the consumer logic must tolerate.

### Q: Why would a backup script prefer a FIFO over a temp file when moving data to ssh?

A FIFO never materializes the data on local disk: no temp space consumed, no sensitive copy left behind to shred, and the transfer is naturally streaming (memory and disk pressure stay flat). The trade-offs are exactly the FIFO semantics: the `tar` writer blocks until the reader opens the FIFO, `SIGPIPE` propagates if the network dies, and the node must be cleaned up. Temp files fail differently — they fill disk — but are seekable and survive reader crashes.

### Q: A script left a FIFO at /tmp/feed and now `ls` shows it but every reader hangs. Diagnose.

`ls -l` shows `p` and size 0 — it's a FIFO with no writer, so every `open(O_RDONLY)` parks. Confirm with `stat -c %F` or `find -type p`. Fixes: start the expected producer, or `timeout N bash -c 'exec consumer < /tmp/feed'` for a bounded read, or simply `rm /tmp/feed` if the producer is gone. Prevention: private runtime directories, explicit modes, and a cleanup `trap` in the creating script.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/mkfifo.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — mkfifo](https://pubs.opengroup.org/onlinepubs/9699919799/)
