# socketcall(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 - / i386 102 / g64 - / arm - (hub; arm OABI table has slot 102 sys_oabi_socketcall) |
| Since (kernel) | 1.0 (hub) |
| Man page | man2/socketcall.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | none: "glibc provides no wrapper for socketcall(), necessitating the use of syscall(2)" (socketcall.2) |
| Aliases covered | none |
| Ledger ID | SC-socketcall |

## Purpose

socketcall() is the common kernel entry point for the socket system
calls on architectures that multiplex them. `call` selects one of the
functions documented in this directory ([socket](socket.md),
[bind](bind.md), [listen](listen.md), [accept](accept.md),
[connect](connect.md), [sendto](sendto.md), ...) and `args` points to
a block of unsigned long holding that function's arguments, passed
through to it. User programs should call socket functions by their
usual names; only libc implementors and kernel hackers need
socketcall() (socketcall.2).

## Synopsis

```c
#include <linux/net.h>
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_socketcall, int call, unsigned long *args);
```

## Arguments and behavior

`call` values, verified against /usr/include/linux/net.h (SYS_* 1-20):

| call | Constant | Target |
|---|---|---|
| 1 | SYS_SOCKET | socket(2) |
| 2 | SYS_BIND | bind(2) |
| 3 | SYS_CONNECT | connect(2) |
| 4 | SYS_LISTEN | listen(2) |
| 5 | SYS_ACCEPT | accept(2) |
| 6 | SYS_GETSOCKNAME | getsockname(2) |
| 7 | SYS_GETPEERNAME | getpeername(2) |
| 8 | SYS_SOCKETPAIR | socketpair(2) |
| 9 | SYS_SEND | send(2) |
| 10 | SYS_RECV | recv(2) |
| 11 | SYS_SENDTO | sendto(2) |
| 12 | SYS_RECVFROM | recvfrom(2) |
| 13 | SYS_SHUTDOWN | shutdown(2) |
| 14 | SYS_SETSOCKOPT | setsockopt(2) |
| 15 | SYS_GETSOCKOPT | getsockopt(2) |
| 16 | SYS_SENDMSG | sendmsg(2) |
| 17 | SYS_RECVMSG | recvmsg(2) |
| 18 | SYS_ACCEPT4 | accept4(2) |
| 19 | SYS_RECVMMSG | recvmmsg(2) |
| 20 | SYS_SENDMMSG | sendmmsg(2) |

Range check: kernel net/socket.c validates `call` against
[1, SYS_SENDMMSG] and returns EINVAL outside it (worklog 1-g kernel
read).

## Return value and errors

Whatever the selected socket call returns, or -1/EINVAL for an
out-of-range `call` (net/socket.c via worklog 1-g).

## Flags and constants

None beyond the SYS_* table above (linux/net.h).

## Security and notes

x86-64, arm64/generic and arm32-EABI have no socketcall: socket(2),
accept(2), bind(2) and so on are real separate syscalls there
(socketcall.2 NOTES; the cached arm table lists 102 only under `oabi`).
On x86-32 socketcall was historically the only sockets entry point;
starting with Linux 4.3 (commit 9dea5dc921b5) direct i386 socket
syscalls exist (359-373 in the cached syscall_32.tbl), mainly to make
seccomp(2) filters practical for sockets and for a small performance
gain. New 32-bit binaries should prefer the direct calls; old ones
still route through 102.

## References

- Cached man page: source-cache/man-pages-sparse/man2/socketcall.2.
- SYS_* values: /usr/include/linux/net.h (worklog 1-g verification).
- net/socket.c call range: worklog Task 1-g.
- Numbers: hub overview.md; source-cache/kernel/syscall_32.tbl.
