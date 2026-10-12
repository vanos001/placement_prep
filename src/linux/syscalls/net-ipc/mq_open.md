# mq_open(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | mq_open 240 / 277 / 180 / 274; mq_unlink 241 / 278 / 181 / 275; mq_timedsend 242 / 279 / 182 / 276; mq_timedreceive 243 / 280 / 183 / 277; mq_notify 244 / 281 / 184 / 278; mq_getsetattr 245 / 282 / 185 / 279; time64 twins: mq_timedsend_time64 - / 418 / - / 418; mq_timedreceive_time64 - / 419 / - / 419 (hub) |
| Since (kernel) | 2.6.6 (hub; all six base numbers share the row; time64 twins are 5.1-era, 5.1 time64 migration per worklog 1-g) |
| Man page | the mq_*.2 files in man-pages are .so aliases of the man3 pages (mq_open.2 -> man3/mq_open.3, mq_unlink.2 -> man3/mq_unlink.3, mq_notify.2 -> man3/mq_notify.3, mq_timedsend.2/mq_timedreceive.2 -> man3/mq_timedsend.3/mq_timedreceive.3; verified in the cached tree); mq_getsetattr.2 is a real page ("Do not use this system call"); overview: man7 mq_overview.7 fetched to source-cache/fetched/mq_overview.7.txt |
| glibc wrapper | yes, in librt (link with -lrt); POSIX.1-2001/2008 API mq_open(3) etc. layered on these syscalls |
| Aliases covered | mq_unlink, mq_timedsend, mq_timedreceive, mq_notify, mq_getsetattr, mq_timedsend_time64, mq_timedreceive_time64 (ledger grouping) |
| Ledger ID | SC-mq_open (+ SC-mq_unlink, SC-mq_timedsend, SC-mq_timedreceive, SC-mq_notify, SC-mq_getsetattr, SC-mq_timedsend_time64, SC-mq_timedreceive_time64) |

## Purpose

The POSIX message queue syscall family: mq_open() opens/creates a queue
named `name` (leading slash, no other slashes; glibc enforces and then
strips it, man3 "C library/kernel differences") and returns an mqd_t;
mq_unlink() removes the name; mq_send/mq_timedsend and
mq_receive/mq_timedreceive move messages; mq_notify() registers for an
empty-queue notification; mq_getsetattr() is the raw entry behind
mq_getattr(3)/mq_setattr(3) ("Do not use this system call",
mq_getsetattr.2).

## Synopsis

```c
#include <fcntl.h>
#include <sys/stat.h>
#include <mqueue.h>
mqd_t mq_open(const char *name, int oflag);
mqd_t mq_open(const char *name, int oflag, mode_t mode,
              struct mq_attr *attr);
```

(struct mq_attr carries mq_flags, mq_maxmsg, mq_msgsize, mq_curmsgs;
only mq_maxmsg and mq_msgsize are used by mq_open.)

## Arguments and behavior

`oflag` needs exactly one of O_RDONLY/O_WRONLY/O_RDWR, optionally
O_CLOEXEC (2.6.26), O_CREAT, O_EXCL, O_NONBLOCK. With O_CREAT, `mode`
is masked against the umask (not applied before 2.6.14) and attr
specifies mq_maxmsg/mq_msgsize; unprivileged callers are capped by
/proc/sys/fs/mqueue/msg_max and msgsize_max (HARD_MAX still applies);
defaults come from msg_default/msgsize_default since 3.5 (mq_open.3,
mq_overview.7). Queues live in the mqueue virtual filesystem
(mount -t mqueue). Receiving blocks when empty and sending blocks when
full unless O_NONBLOCK (then EAGAIN); timed variants add an absolute
timeout (time64 twins use 64-bit timespec on 32-bit ABIs, i386 418/419).

## Return value and errors

mqd_t on success; (mqd_t) -1 with `errno`: `EACCES`, `EEXIST`
(O_CREAT|O_EXCL), `EINVAL` (bad name; bad attr values), `EMFILE`,
`ENAMETOOLONG`, `ENFILE`, `ENOENT`, `ENOMEM`, `ENOSPC` (queues_max);
mq_unlink: `EACCES`, `ENAMETOOLONG`, `ENOENT`.

## Flags and constants

O_RDONLY/O_WRONLY/O_RDWR, O_CLOEXEC, O_CREAT, O_EXCL, O_NONBLOCK
(fcntl.h); notification with SIGEV_NONE/SIGEV_SIGNAL/SIGEV_THREAD and
the O_NONBLOCK toggle via mq_setattr are covered by mq_notify.3 /
mq_overview.7.

## Security and notes

- mq_getsetattr exists so libc can implement getattr/setattr; it is not
  a documented user interface (mq_getsetattr.2 NOTES: "Never call it
  unless you are writing a C library!").
- Since conflict note: worklog 1-g flagged that the mq Since row
  (2.6.6) matches syscalls(2); individual man3 pages have no kernel
  version lines, so the hub value is the only source.

## References

- Cached man pages: man3/mq_open.3 (via mq_open.2 .so),
  man2/mq_getsetattr.2; fetched mq_overview.7
  (source-cache/fetched/mq_overview.7.txt).
- Numbers/Since: hub [overview](overview.md); ledger mq_* rows
  (lines 558-565).
