# mbind(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 237 / 274 / 235 / 319 (hub) |
| Since (kernel) | 2.6.6 (hub/ledger, syscalls(2) row); mbind.2 VERSIONS says 2.6.7 -- discrepancy recorded (worklog 1-b) |
| Man page | man2/mbind.2 (cached, dated 2021-03-22) |
| glibc wrapper | none ("Glibc does not provide a wrapper for this system call"; libnuma supplies one, link with -lnuma, header <numaif.h> not in glibc) |
| Aliases covered | none |
| Ledger ID | SC-mbind |

## Purpose

mbind() sets the NUMA memory policy (mode plus optional node set) for
the address range [addr, addr + len). It governs where new pages for
that range are allocated: anonymous memory and MAP_PRIVATE file maps
allocate per policy on first write/touch; MAP_SHARED file maps ignore
the range policy (the faulting thread's policy wins); SysV shared
memory attached with shmat(2) honors it (SHM_HUGETLB only for the
calling process's allocations) (mbind.2). By default only future
allocations are affected; MPOL_MF_MOVE/MPOL_MF_MOVE_ALL move existing
pages.

## Synopsis

```c
#include <numaif.h>
long mbind(void *addr, unsigned long len, int mode,
           const unsigned long *nodemask, unsigned long maxnode,
           unsigned int flags);
```

## Arguments and behavior

`addr` must be page-aligned. `mode` is one MPOL_* value, optionally ORed
with a mode flag; modes are shared with set_mempolicy(2)
([set_mempolicy](set_mempolicy.md)): MPOL_DEFAULT (use the thread
policy), MPOL_BIND (restrict to the mask; since 2.6.26 the nearest node
with free memory wins), MPOL_INTERLEAVE (round-robin across the mask),
MPOL_PREFERRED (first mask node preferred, empty mask = local),
MPOL_LOCAL (3.8: local allocation, empty mask required). `nodemask` is a
bitmask of up to `maxnode` bits (rounded to unsigned long; NULL/0 =
empty set); a required mask must name an online, cpuset-allowed node
with memory. Values verified in installed /usr/include/linux/mempolicy.h:

| Constant | Value |
|---|---|
| MPOL_DEFAULT | 0 |
| MPOL_PREFERRED | 1 |
| MPOL_BIND | 2 |
| MPOL_INTERLEAVE | 3 |
| MPOL_LOCAL | 4 |
| MPOL_PREFERRED_MANY | 5 |
| MPOL_WEIGHTED_INTERLEAVE | 6 |

## Return value and errors

0 on success; -1 with `errno`: `EFAULT` (nodemask unreadable; unmapped
hole in the range), `EINVAL` (bad mode/flags; addr unaligned; addr+len
overflow; wrong mask for the mode; both MPOL_F_STATIC_NODES and
MPOL_F_RELATIVE_NODES), `EIO` (MPOL_MF_STRICT and pages off policy, or
pages that MPOL_MF_MOVE could not move), `ENOMEM` (kernel memory),
`EPERM` (MPOL_MF_MOVE_ALL without CAP_SYS_NICE).

## Flags and constants

| Flag | Value | Since / note |
|---|---|---|
| MPOL_MF_STRICT | 1 << 0 | fail with EIO on nonconforming pages |
| MPOL_MF_MOVE | 1 << 1 | 2.6.16; move this process's pages only |
| MPOL_MF_MOVE_ALL | 1 << 2 | 2.6.16; move shared pages too; needs CAP_SYS_NICE |
| MPOL_MF_LAZY | 1 << 3 | unsupported flag per uapi header ("UNSUPPORTED FLAG: Lazy migrate on fault") |
| MPOL_F_STATIC_NODES | 1 << 15 | 2.6.26; mask is physical node IDs |
| MPOL_F_RELATIVE_NODES | 1 << 14 | 2.6.26; mask relative to cpuset |

## Security and notes

- MPOL_MF_STRICT was ignored on huge page mappings before 5.7 (mbind.2).
- Setting home node for MPOL_BIND/PREFERRED_MANY ranges is done by
  set_mempolicy_home_node (5.17) ([set_mempolicy_home_node](set_mempolicy_home_node.md)).
- Worklog 1-b groups SC-mbind as "grouped" with the NUMA family pages.

## References

- Cached man page: source-cache/man-pages-sparse/man2/mbind.2.
- Constants: /usr/include/linux/mempolicy.h; kernel uapi copy
  source-cache/fetched/master-include-uapi-linux-mempolicy.h.
- Numbers/Since: hub [overview](overview.md); ledger SC-mbind.
