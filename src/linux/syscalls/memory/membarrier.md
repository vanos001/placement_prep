# membarrier(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 324 / 375 / 283 / 389 (hub) |
| Since (kernel) | 3.17 (hub; syscalls(2) row "3.17"; membarrier.2 VERSIONS instead says "added in Linux 4.3" -- the command API including QUERY landed 4.3; both recorded, see notes) |
| Man page | man2/membarrier.2 (cached, dated 2021-08-27) |
| glibc wrapper | none ("glibc provides no wrapper for membarrier(), necessitating the use of syscall(2)", man page) |
| Aliases covered | none |
| Ledger ID | SC-membarrier |

## Purpose

membarrier() executes memory barriers across a set of threads so that
fast paths in synchronization algorithms can use plain compiler barriers
(`asm volatile("" : : : "memory")`) while the matching slow-side barrier
becomes a membarrier() call. After the call returns, targeted running
threads are guaranteed to have passed through a state where all
user-space memory accesses match program order between entry and return
(man DESCRIPTION; designed for RCU libraries and garbage collectors).

## Synopsis

```c
#include <linux/membarrier.h>
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_membarrier, int cmd, unsigned int flags, int cpu_id);
```

Before 5.10 the prototype was `int membarrier(int cmd, int flags)`; the
cpu_id argument was added with the rseq command (man VERSIONS).

## Arguments and behavior

`cmd` selects the operation (values verified in installed
/usr/include/linux/membarrier.h):

| Command | Value | Since | Effect |
|---|---|---|---|
| MEMBARRIER_CMD_QUERY | 0 | 4.3 | return bitmask of supported commands (QUERY itself not included) |
| MEMBARRIER_CMD_GLOBAL (=MEMBARRIER_CMD_SHARED) | 1 << 0 | 4.16 (alias 4.3) | barrier on all running threads of all processes |
| MEMBARRIER_CMD_GLOBAL_EXPEDITED | 1 << 1 | 4.16 | barrier on registered processes' running threads |
| MEMBARRIER_CMD_REGISTER_GLOBAL_EXPEDITED | 1 << 2 | 4.16 | register intent for GLOBAL_EXPEDITED |
| MEMBARRIER_CMD_PRIVATE_EXPEDITED | 1 << 3 | 4.14 | barrier on running threads of the calling process |
| MEMBARRIER_CMD_REGISTER_PRIVATE_EXPEDITED | 1 << 4 | 4.14 | register intent for PRIVATE_EXPEDITED |
| MEMBARRIER_CMD_PRIVATE_EXPEDITED_SYNC_CORE | 1 << 5 | 4.16 | additionally core-serializing instruction on siblings |
| MEMBARRIER_CMD_REGISTER_PRIVATE_EXPEDITED_SYNC_CORE | 1 << 6 | 4.16 | register intent for SYNC_CORE |
| MEMBARRIER_CMD_PRIVATE_EXPEDITED_RSEQ | 1 << 7 | 5.10 | restart running rseq critical sections; flags may select one CPU |
| MEMBARRIER_CMD_REGISTER_PRIVATE_EXPEDITED_RSEQ | 1 << 8 | 5.10 | register intent for RSEQ |
| MEMBARRIER_CMD_GET_REGISTRATIONS | 1 << 9 | header | bitmask of prior registration commands |

`flags` must be 0 except with the RSEQ command, where
MEMBARRIER_CMD_FLAG_CPU (1 << 0) makes `cpu_id` select the target CPU.
With flags 0 the call is deterministic per command: same result until
reboot, so error handling is needed only on the first call (man).

## Return value and errors

QUERY returns the bitmask; other commands return 0. On failure -1 with
`errno`: `EINVAL` (invalid cmd, nonzero flags, GLOBAL disabled under
nohz_full, SYNC_CORE unimplemented on the architecture), `ENOSYS`
(syscall absent), `EPERM` (private expedited used without registration).

## Flags and constants

MEMBARRIER_CMD_FLAG_CPU (1 << 0) is the only flag (linux/membarrier.h).

## Security and notes

- Since conflict: ledger/hub record 3.17 (syscalls(2) row), while the
  individual man page VERSIONS says "added in Linux 4.3"; the man page
  also stamps each command with 4.3/4.14/4.16/5.10. Both cited here;
  worklog 1-b flags such table-vs-page discrepancies.
- Expedited commands never block but impose overhead on the target
  threads (man).

## References

- Cached man page: source-cache/man-pages-sparse/man2/membarrier.2.
- Command values: /usr/include/linux/membarrier.h (installed); kernel
  uapi copy source-cache/fetched/master-include-uapi-linux-membarrier.h.
- Numbers/Since: hub [overview](overview.md); ledger SC-membarrier.
