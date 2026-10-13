# get_mempolicy(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 239 / 275 / 236 / 320 (hub) |
| Since (kernel) | 2.6.6 (hub/ledger, syscalls(2) row); get_mempolicy.2 VERSIONS says 2.6.7 -- discrepancy recorded (worklog 1-b) |
| Man page | man2/get_mempolicy.2 (cached, dated 2021-03-22) |
| glibc wrapper | none ("Glibc does not provide a wrapper for this system call"; libnuma supplies one, link with -lnuma) |
| Aliases covered | none |
| Ledger ID | SC-get_mempolicy |

## Purpose

get_mempolicy() retrieves the NUMA memory policy of the calling thread,
or of a memory address, depending on `flags`. With flags 0 it returns
the thread default policy set by set_mempolicy(2)
([set_mempolicy](set_mempolicy.md)) in `mode` and `nodemask` -- values
usable to restore that policy later. With MPOL_F_ADDR it returns the
policy governing `addr` (which may be a range policy from mbind(2)
[mbind](mbind.md)). With MPOL_F_MEMS_ALLOWED (2.6.24) `mode` is ignored
and `nodemask` receives the nodes the thread may specify in subsequent
mbind/set_mempolicy calls (get_mempolicy.2).

## Synopsis

```c
#include <numaif.h>
long get_mempolicy(int *mode, unsigned long *nodemask,
                   unsigned long maxnode, void *addr,
                   unsigned long flags);
```

## Arguments and behavior

`mode` (if not NULL) receives the policy mode plus any optional mode
flags; `nodemask` (if not NULL) receives the node bitmask, holding up to
`maxnode` bits (always rounded up to a multiple of sizeof(unsigned
long) * 8). Flag combinations (get_mempolicy.2):

| Flag | Value | Behavior |
|---|---|---|
| (none) | 0 | thread default policy; addr must be NULL |
| MPOL_F_NODE (1 << 0) + MPOL_F_ADDR (1 << 1) | -- | return in *mode the node ID where addr is allocated; if no page exists yet one is allocated as if the thread had read it |
| MPOL_F_NODE without MPOL_F_ADDR | -- | thread policy must be MPOL_INTERLEAVE; *mode receives the next node to be used for interleaving of kernel-internal allocations |
| MPOL_F_MEMS_ALLOWED (1 << 2), 2.6.24 | -- | *nodemask = nodes allowed in future mbind/set_mempolicy; mode ignored; may not combine with MPOL_F_ADDR or MPOL_F_NODE |

Other flag values are reserved.

## Return value and errors

0 on success; -1 with `errno`: `EFAULT` (nodemask/maxnode range
unreadable), `EINVAL` (maxnode below system node count; reserved flags;
MPOL_F_ADDR with NULL addr or missing with non-NULL addr; MPOL_F_NODE
without MPOL_F_ADDR when the policy is not MPOL_INTERLEAVE;
MPOL_F_MEMS_ALLOWED combined with MPOL_F_ADDR/MPOL_F_NODE; "other
EINVAL cases" per the man page).

## Flags and constants

MPOL_F_NODE (1 << 0), MPOL_F_ADDR (1 << 1), MPOL_F_MEMS_ALLOWED
(1 << 2) -- values verified in installed /usr/include/linux/mempolicy.h.
The returned mode constant values are the MPOL_* table on
[mbind](mbind.md).

## Security and notes

- The MPOL_F_NODE + MPOL_F_ADDR combination allocates a page for the
  address if none exists, which is a side effect to remember when
  probing addresses.
- Worklog 1-b NUMA-group note: policies apply per thread, and cpuset
  changes can invalidate the allowed node set at any time.

## References

- Cached man page: source-cache/man-pages-sparse/man2/get_mempolicy.2.
- Flag values: /usr/include/linux/mempolicy.h (installed).
- Numbers/Since: hub [overview](overview.md); ledger SC-get_mempolicy.
