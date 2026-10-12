# set_mempolicy(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 238 / 276 / 237 / 321 (hub) |
| Since (kernel) | 2.6.6 (hub/ledger, syscalls(2) row); set_mempolicy.2 VERSIONS says 2.6.7 -- discrepancy recorded (worklog 1-b) |
| Man page | man2/set_mempolicy.2 (cached, dated 2021-06-20) |
| glibc wrapper | none in glibc (libnuma supplies one; link with -lnuma; <numaif.h> comes from the numactl/libnuma-devel package) |
| Aliases covered | none |
| Ledger ID | SC-set_mempolicy |

## Purpose

set_mempolicy() sets the calling thread's default NUMA memory policy
(mode plus node set). The thread policy governs page allocation outside
ranges controlled by mbind(2) ([mbind](mbind.md)), including MAP_PRIVATE
file pages on read and all MAP_SHARED file allocations; it applies only
when a new page is allocated (first touch of anonymous memory). The
policy survives execve(2) and is inherited through fork(2)/clone(2)
(set_mempolicy.2).

## Synopsis

```c
#include <numaif.h>
long set_mempolicy(int mode, const unsigned long *nodemask,
                   unsigned long maxnode);
```

## Arguments and behavior

`mode` is one of the MPOL_* values of the [mbind](mbind.md) table
(verified in installed /usr/include/linux/mempolicy.h): MPOL_DEFAULT
(reset; nodemask must be empty, falls back to system default local
allocation), MPOL_BIND (strict node set; lowest-ID-first order in the
man page description), MPOL_INTERLEAVE (numeric-ID round-robin),
MPOL_PREFERRED (first mask node preferred; empty mask = local), MPOL_LOCAL
(3.8: local allocation; empty mask required). A required `nodemask`
(up to `maxnode` bits, NULL/0 = empty) must name an online,
cpuset-allowed node with memory; with MPOL_F_STATIC_NODES a required
mask naming no allowed nodes reverts the policy to local allocation
until the cpuset includes a named node. Optional mode flags:

| Flag | Value | Since / note |
|---|---|---|
| MPOL_F_NUMA_BALANCING | 1 << 13 | 5.12; with MPOL_BIND enables kernel NUMA balancing; unsupported or wrong mode gives EINVAL |
| MPOL_F_STATIC_NODES | 1 << 15 | 2.6.26; physical node IDs, never remapped |
| MPOL_F_RELATIVE_NODES | 1 << 14 | 2.6.26; IDs relative to the cpuset |

## Return value and errors

0 on success; -1 with `errno`: `EFAULT` (nodemask unreadable), `EINVAL`
(invalid mode; empty/nonempty mask mismatches the mode; maxnode over a
page worth of bits; node IDs above the maximum; no allowed node with
memory; both STATIC and RELATIVE set; MPOL_F_NUMA_BALANCING misuse),
`ENOMEM` (kernel memory).

## Flags and constants

Mode and flag values are in the table above and the [mbind](mbind.md)
table; MPOL_MAX (7) bounds the enum in the uapi header.

## Security and notes

- Memory policy is not remembered across swap-out: pages paged back in
  use the policy in effect at that time (set_mempolicy.2 NOTES).
- Worklog 1-b sourced the 5.17 home-node extension separately:
  [set_mempolicy_home_node](set_mempolicy_home_node.md).

## References

- Cached man page: source-cache/man-pages-sparse/man2/set_mempolicy.2.
- Constants: /usr/include/linux/mempolicy.h; kernel kernel_set_mempolicy
  path in source-cache/fetched/master-mm-mempolicy.c.
- Numbers/Since: hub [overview](overview.md); ledger SC-set_mempolicy.
