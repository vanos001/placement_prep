# sendmmsg(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sendmmsg 307 / 345 / 269 / 374; recvmmsg 299(64) / 337(time32) / 243 / 365(time32); recvmmsg_time64 417 (i386 + arm32) (hub + cached tables) |
| Since (kernel) | sendmmsg 3.0 (sendmmsg.2 VERSIONS); recvmmsg 2.6.33 (recvmmsg.2 VERSIONS); recvmmsg_time64 5.1 (worklog 1-e/1-g tag probe v5.0 vs v5.1) |
| Man page | man2/sendmmsg.2 (2020-06-09), man2/recvmmsg.2 (2020-11-01) -- cached roff, real pages |
| glibc wrapper | sendmmsg glibc 2.14; recvmmsg glibc 2.12 (VERSIONS; nm: sendmmsg@@GLIBC_2.14, recvmmsg@@GLIBC_2.12) |
| Aliases covered | recvmmsg (SC-recvmmsg) + recvmmsg_time64 twin (SC-recvmmsg_time64) |
| Ledger ID | SC-sendmmsg |

## Purpose

sendmmsg() extends [sendmsg](sendmsg.md): it transmits up to `vlen`
messages from an array of `mmsghdr` in one syscall (batching win for
UDP-like workloads). recvmmsg() is the receive twin and adds a
`timeout`. Both are Linux-specific.

## Synopsis

```c
#define _GNU_SOURCE
#include <sys/socket.h>
int sendmmsg(int sockfd, struct mmsghdr *msgvec, unsigned int vlen,
             int flags);
int recvmmsg(int sockfd, struct mmsghdr *msgvec, unsigned int vlen,
             int flags, struct timespec *timeout);
```

## Arguments and behavior

`struct mmsghdr { struct msghdr msg_hdr; unsigned int msg_len; }`:
msg_hdr is a normal msghdr (see [sendmsg](sendmsg.md)); msg_len
receives the byte count for that entry -- the value a single
sendmsg/recvmsg would have returned. flags are the sendmsg/recvmsg
flags. A blocking sendmmsg blocks until vlen messages are sent; a
nonblocking one sends as many as possible. recvmmsg blocks until
vlen messages arrive or `timeout` (timespec) expires; NULL means
block indefinitely; the interval is rounded up to clock granularity.
recvmmsg adds one flag: MSG_WAITFORONE (2.6.34) turns on
MSG_DONTWAIT after the first message is received.

## Return value and errors

Number of messages sent/received (elements of msgvec updated); -1 with
errno only if no datagram could be sent -- errors are otherwise as for
sendmsg/recvmsg, plus EINVAL for an invalid recvmmsg timeout (BUGS:
after the first message the error code can be lost or overwritten).
Retry at the first failed element, as for short read/write.

## Flags and constants

MSG_WAITFORONE (2.6.34) as above; all other MSG_* flags per
[sendto](sendto.md) / [sendmsg](sendmsg.md). vlen is capped to
UIO_MAXIOV (1024) silently (sendmmsg.2 NOTES, commit 98382f419f32).

## Security and notes

recvmmsg timeout BUGS (recvmmsg.2): the timeout is checked only after
each datagram, so if vlen-1 datagrams arrive and then traffic stops,
the call blocks forever -- it is not a wall-clock bound.
recvmmsg_time64 twin: added in Linux 5.1 on 32-bit arches
(i386/arm 417; worklog 1-e tag-probed syscall_32.tbl v5.0 had 0
time64 rows, v5.1 had them), taking a struct __kernel_timespec so
tv_sec is 64-bit even on 32-bit. The hub row carries the base
time32 numbers 337/365; this page records both.

## References

- Cached man pages: source-cache/man-pages-sparse/man2/sendmmsg.2, recvmmsg.2.
- Numbers: hub overview.md, ledger.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Time64 date: worklog Task 1-g (v5.0 vs v5.1 tag probe).
- glibc symbols: nm -D libc.so.6 (glibc 2.41, worklog 3-f).
