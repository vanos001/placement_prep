# pipe(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | pipe 22 / 42 / - / 42; pipe2 293 / 331 / 59 / 359 (hub + cached tables) |
| Since (kernel) | pipe 1.0 (hub); pipe2 2.6.27 (pipe.2 VERSIONS) |
| Man page | man2/pipe.2 (cached roff, dated 2021-03-22; pipe2.2 is a .so alias) |
| glibc wrapper | yes for both; pipe2 in glibc since 2.9 (pipe.2 VERSIONS) |
| Aliases covered | pipe2 (SC-pipe2, grouped per ledger) |
| Ledger ID | SC-pipe |

## Purpose

pipe() creates a pipe: a unidirectional data channel for
interprocess communication. It returns two fds in `pipefd`:
pipefd[0] the read end, pipefd[1] the write end. Data written to the
write end is buffered by the kernel until read from the read end
(pipe.2, details in pipe(7)). On arm64-generic there is no `pipe`
slot (hub shows "-"): the modern ABI starts at pipe2.

## Synopsis

```c
#include <unistd.h>
int pipe(int pipefd[2]);
#define _GNU_SOURCE
#include <fcntl.h>
#include <unistd.h>
int pipe2(int pipefd[2], int flags);
```

## Arguments and behavior

pipe2() equals pipe() when flags is 0. flags (pipe.2):

| Flag | Since | Effect |
|---|---|---|
| O_CLOEXEC | - | FD_CLOEXEC on both new fds |
| O_NONBLOCK | - | O_NONBLOCK on both open file descriptions atomically |
| O_DIRECT | 3.4 | packet mode: each write is a packet; short reads discard the rest; zero-length packets unsupported; EINVAL on older kernels; toggleable via fcntl since 4.5 |

Writes of more than PIPE_BUF bytes are split into packets in
O_DIRECT mode; a buffer of PIPE_BUF suffices for the largest packet
(pipe.2, PIPE_BUF from <limits.h>). After fork(2) the child inherits
both ends; the usual pattern closes the unused end per process and
the reader sees EOF when the writer closes.

## Return value and errors

Zero on success; -1 with errno, `pipefd` unchanged on failure (both
pipe() and pipe2(); POSIX.1-2008 TC2 standardized this): EFAULT,
EINVAL (pipe2 bad flags), EMFILE (per-process fd limit), ENFILE
(system-wide; also the user pipe-memory hard limit when unprivileged,
pipe.2).

## Flags and constants

O_CLOEXEC, O_NONBLOCK, O_DIRECT as above (fcntl.h values; O_DIRECT
here is pipe-specific packet mode, unrelated to file O_DIRECT
semantics).

## Security and notes

Architecture note (pipe.2 NOTES): Alpha, IA-64, MIPS, SuperH and
SPARC/SPARC64 return both fds as a struct fd_pair return value
because their ABIs allow multi-register returns; the glibc wrapper
hides this. Wrapper fallback (worklog 1-g, musl 1.2.5
src/unistd/pipe.c): musl calls SYS_pipe when defined, else falls back
to SYS_pipe2(fd, 0) -- which is what arm64/generic need since they
have no pipe slot. eventfd(2) is the lower-overhead single-fd
alternative for pure event signaling (eventfd.2 NOTES; see
[eventfd](eventfd.md)).

## References

- Cached man page: source-cache/man-pages-sparse/man2/pipe.2 (pipe2.2 .so).
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- musl fallback: source-cache/musl-clone/musl/src/unistd/pipe.c (worklog 1-g).
