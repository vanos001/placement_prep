# msgget(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | msgget 68 / 399 / 186 / 303; msgsnd 69 / 400 / 189 / 301; msgrcv 70 / 401 / 188 / 302; msgctl 71 / 402 / 187 / 304 (hub) |
| Since (kernel) | 2.0 (hub; SysV message queue syscalls since 1.0-era on the multiplexed ABIs, named slots since 2.0) |
| Man page | man2/msgget.2 (cached); msgsnd/msgrcv: msgop.2 (msgsnd.2 and msgrcv.2 are .so aliases, verified in the cache); msgctl.2 is a real page |
| glibc wrapper | yes for all four, in libc (header <sys/msg.h>); POSIX.1-2001/2008 for msgget/msgsnd/msgrcv/msgctl |
| Aliases covered | msgsnd, msgrcv, msgctl (SC-msgsnd, SC-msgrcv, SC-msgctl, grouped per ledger) |
| Ledger ID | SC-msgget (+ SC-msgsnd, SC-msgrcv, SC-msgctl) |

## Purpose

System V message queue family. msgget() returns the identifier for
`key`, creating a queue when key is IPC_PRIVATE or no queue exists and
IPC_CREAT is given; msgsnd() appends a message (struct msgbuf: long
mtype > 0, then msgsz bytes of mtext); msgrcv() removes a message,
selecting by `msgtyp` (0 = FIFO, > 0 = first of that type, < 0 = lowest
type <= |msgtyp|); msgctl() performs control operations (IPC_STAT,
IPC_SET, IPC_RMID, IPC_INFO, MSG_INFO, MSG_STAT, MSG_STAT_ANY)
(msgget.2, msgop.2, msgctl.2; overview in svipc.7).

## Synopsis

```c
#include <sys/msg.h>
int msgget(key_t key, int msgflg);
int msgsnd(int msqid, const void *msgp, size_t msgsz, int msgflg);
ssize_t msgrcv(int msqid, void *msgp, size_t msgsz, long msgtyp,
               int msgflg);
int msgctl(int msqid, int cmd, struct msqid_ds *buf);
```

## Arguments and behavior

`msgflg` low 9 bits are the queue permissions (open(2) style; execute
unused). MSG_NOERROR (msgrcv) silently truncates oversize messages;
IPC_NOWAIT makes a full queue (msgsnd) or empty queue (msgrcv) fail
with EAGAIN instead of blocking; msgsnd blocks while the byte total
would exceed msg_qbytes (initially MSGMNB, tunable via msgctl IPC_SET;
raising it needs CAP_SYS_RESOURCE). msgrcv MSG_EXCEPT (Linux-specific)
inverts msgtyp > 0 selection. Creation initializes msqid_ds: uid/gid
from the caller, mode from msgflg, msg_qbytes = MSGMNB, msg_ctime =
now (msgget.2).

## Return value and errors

Identifiers and byte counts on success (msgrcv returns msgsz received);
-1 with `errno`: `EACCES` (permission, CAP_IPC_OWNER check),
`EAGAIN` (IPC_NOWAIT), `EIDRM` (queue removed), `EINTR`,
`EINVAL`, `ENOMEM` (msgsnd undo structures / creation), `ENOSPC`
(MSGMNI limit at creation; default 32,000 since 3.19 via
/proc/sys/kernel/msgmni), `ENOMSG` (msgrcv, MSG_NOERROR-less no match
with IPC_NOWAIT), `E2BIG` (msgsz over msgmax / msg_qbytes), `EFAULT`,
`EPERM` (msgctl IPC_SET raising limits).

## Flags and constants

IPC_CREAT 00001000, IPC_EXCL 00002000, IPC_NOWAIT 00004000,
IPC_PRIVATE (key 0) from <linux/ipc.h> / <sys/ipc.h>; MSG_NOERROR,
MSG_EXCEPT, MSG_COPY (4.20-era, with IPC_NOWAIT) from <sys/msg.h>.

## Security and notes

- EACCES is decided with CAP_IPC_OWNER in the governing user namespace
  (msgget.2/msgop.2); IPC namespace scoping in ipc_namespaces(7)
  (svipc.7 SEE ALSO).
- Until Linux 2.3.20 msgget returned EIDRM for a queue scheduled for
  deletion (msgget.2 Linux notes).

## References

- Cached man pages: man2/msgget.2, man2/msgop.2 (via msgsnd.2/msgrcv.2
  .so), man2/msgctl.2; fetched svipc.7
  (source-cache/fetched/svipc.7.txt).
- Numbers: hub [overview](overview.md); ledger msg* rows.
