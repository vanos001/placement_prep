# move_pages(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 279 / 317 / 239 / 344 (hub) |
| Since (kernel) | 2.6.18 (hub; move_pages.2 VERSIONS: "first appeared on Linux in version 2.6.18") |
| Man page | man2/move_pages.2 (cached, dated 2021-03-22) |
| glibc wrapper | none ("Glibc does not provide a wrapper"; libnuma supplies one, link with -lnuma; <numaif.h> from libnuma-devel) |
| Aliases covered | none |
| Ledger ID | SC-move_pages |

## Purpose

move_pages() moves individual pages of process `pid` to chosen NUMA
nodes, or (when `nodes` is NULL) just reports where each page currently
resides. Unlike migrate_pages(2) ([migrate_pages](migrate_pages.md)),
which moves all pages between node sets, this call operates on an
explicit list of page addresses and can interleave moves with status
queries (move_pages.2).

## Synopsis

```c
#include <numaif.h>
long move_pages(int pid, unsigned long count, void **pages,
                const int *nodes, int *status, int flags);
```

## Arguments and behavior

`pid` 0 means the calling process. `count` sizes three parallel arrays:
`pages` (page-aligned addresses as seen by the target process), `nodes`
(desired node per page; NULL turns the call into a pure status query),
and `status` (per-page result). `flags` may combine MPOL_MF_MOVE (move
only pages exclusively used by the process) and MPOL_MF_MOVE_ALL (also
shared pages; needs CAP_SYS_NICE). Per-page status values (move_pages.2):
a node number 0..MAX_NUMNODES, or a negated errno: -EACCES (shared page,
needs MPOL_MF_MOVE_ALL), -EBUSY (page under I/O or otherwise busy),
-EFAULT (zero page or unmapped), -EIO (dirty page cannot be written
back), -EINVAL (dirty page, no migration function), -ENOENT (page not
present), -ENOMEM (no memory on target node).

## Return value and errors

0 on success; -1 with `errno` on failure; and, since 4.17, a positive
return is possible: the number of nonmigrated pages for nonfatal
reasons. `errno` values: `E2BIG` (too many pages; kernel stopped
generating it in 2.6.29), `EACCES` (target node not allowed by cpuset),
`EFAULT` (parameter arrays unreadable), `EINVAL` (flags other than
MPOL_MF_MOVE/MPOL_MF_MOVE_ALL; migrating a kernel thread), `ENODEV`
(target node offline), `EPERM` (MPOL_MF_MOVE_ALL or cross-user move
without CAP_SYS_NICE), `ESRCH` (no such process).

## Flags and constants

MPOL_MF_MOVE (1 << 1) and MPOL_MF_MOVE_ALL (1 << 2) as in the
[mbind](mbind.md) table.

## Security and notes

- Permission to move another process's pages changed in 4.13: from then
  on a ptrace access mode PTRACE_MODE_READ_REALCREDS check governs it
  (before that: CAP_SYS_NICE or matching real/effective UID vs real or
  saved-set UID of the target) -- the change was an ASLR-protection fix
  (move_pages.2).
- Memory policy does not constrain the destination nodes: the move may
  leave pages violating mbind/set_mempolicy policy (move_pages.2 NOTES).

## References

- Cached man page: source-cache/man-pages-sparse/man2/move_pages.2.
- Numbers/Since: hub [overview](overview.md); ledger SC-move_pages.
