# shmget(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | shmget 29 / 395 / 194 / 307; shmat 30 / 397 / 196 / 305; shmctl 31 / 396 / 195 / 308; shmdt 67 / 398 / 197 / 306 (hub) |
| Since (kernel) | 2.0 (hub; SysV shared memory syscalls since 1.0-era on the multiplexed ABIs, named slots since 2.0) |
| Man page | man2/shmget.2 (cached); shmat/shmdt: shmop.2 (shmat.2 and shmdt.2 are .so aliases, verified); shmctl.2 is a real page |
| glibc wrapper | yes for all four, in libc (header <sys/shm.h>); shmget/shmat POSIX.1-2001/2008 (shmat marked legacy in POSIX.1-2008) |
| Aliases covered | shmat, shmdt, shmctl (SC-shmat, SC-shmdt, SC-shmctl, grouped per ledger) |
| Ledger ID | SC-shmget (+ SC-shmat, SC-shmdt, SC-shmctl) |

## Purpose

System V shared memory segments. shmget() returns the identifier of the
segment for `key`, creating one of `size` bytes (rounded up to page
size, contents zeroed) when key is IPC_PRIVATE or none exists and
IPC_CREAT is given; shmat() attaches the segment into the caller's
address space; shmdt() detaches; shmctl() performs control operations
(IPC_STAT, IPC_SET, IPC_RMID, IPC_INFO, SHM_INFO, SHM_STAT,
SHM_STAT_ANY, SHM_LOCK, SHM_UNLOCK) (shmget.2, shmop.2, shmctl.2;
overview in svipc.7).

## Synopsis

```c
#include <sys/shm.h>
int shmget(key_t key, size_t size, int shmflg);
void *shmat(int shmid, const void *shmaddr, int shmflg);
int shmdt(const void *shmaddr);
int shmctl(int shmid, int cmd, struct shmid_ds *buf);
```

## Arguments and behavior

shmget flags: IPC_CREAT, IPC_EXCL (EEXIST on collision), low 9 bits
permissions, plus SHM_HUGETLB (2.6; huge pages, needs CAP_IPC_LOCK or
membership of /proc/sys/vm/sysctl_hugetlb_shm_group), SHM_HUGE_2MB /
SHM_HUGE_1GB (3.8; encode log2 size in SHM_HUGE_SHIFT bits),
SHM_NORESERVE (2.6.15; no swap reservation, may SIGSEGV under
pressure). shmat: NULL shmaddr picks an address; SHM_RND rounds a
non-NULL shmaddr down to SHMLBA; otherwise shmaddr must be page
aligned; SHM_RDONLY attaches read-only; SHM_REMAP replaces existing
mappings in the range; SHM_EXEC (2.6.9) allows execution. Attach with
SHM_RDONLY does not update shm_atime/dtime the usual way (shmop.2).

## Return value and errors

Identifier / attached address (shmat returns (void *) -1 on error) / 0
on success; -1 with `errno`: `EACCES` (CAP_IPC_OWNER check),
`EEXIST`, `EINVAL`, `ENOMEM`, `ENOSPC` (SHMMNI or SHMALL), `ENOENT`,
`ENFILE`, `EPERM` (SHM_HUGETLB privilege; IPC_SET/IPC_RMID), `EIDRM`
(segment removed), `EIDRM`/`EINVAL` on attach of a marked segment.

## Flags and constants

IPC_* from <sys/ipc.h>; SHM_HUGETLB, SHM_NORESERVE, SHM_RND,
SHM_RDONLY, SHM_REMAP, SHM_EXEC, SHMLBA, SHMMIN/SHMMAX/SHMALL/SHMMNI
from <sys/shm.h> / <linux/shm.h>. Limits via /proc/sys/kernel/shmall,
shmmax, shmmni; SHMMAX default since 3.16 is ULONG_MAX - 2^24
(shmget.2).

## Security and notes

- Attach/detach counts (shm_nattch) and IPC_RMID semantics: the segment
  vanishes once the last detach happens after RMID (shmop.2/shmctl.2).
- shmat on i386 goes through the [ipc](ipc.md) multiplexer (SHMAT 21,
  result passed back via ptr) -- x64 has direct slots 30/31/67.

## References

- Cached man pages: man2/shmget.2, man2/shmop.2 (via shmat.2/shmdt.2
  .so), man2/shmctl.2; fetched svipc.7
  (source-cache/fetched/svipc.7.txt).
- Numbers: hub [overview](overview.md); ledger shm* rows.
