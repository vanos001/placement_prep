# set_mempolicy_home_node(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 450 / 450 / 450 / 450 (hub) |
| Since (kernel) | 5.17 (hub; worklog 1-b tag-probed absent 5.16 / present 5.17; sourced from mm/mempolicy.c -- no man page, marked as such) |
| Man page | none (no man2/set_mempolicy_home_node.2 in man-pages 6.19 or the sparse cache; documented from kernel source mm/mempolicy.c, SYSCALL_DEFINE4(set_mempolicy_home_node)) |
| glibc wrapper | none (no glibc wrapper; libnuma integration not verified -- gap) |
| Aliases covered | none |
| Ledger ID | SC-set_mempolicy_home_node |

## Purpose

set_mempolicy_home_node() sets the "home node" (the preferred NUMA node
for the demotion/promotion balance path) on a VMA range whose policy is
MPOL_BIND or MPOL_PREFERRED_MANY: for each VMA in [start, start + len)
that already carries one of those two modes, the call duplicates the
policy, assigns `home_node`, and rebinds the range (mm/mempolicy.c:
mpol_dup + mbind_range). The home node acts as the target node when the
kernel balances memory across the bound nodes (kernel commit history
describes it as the node toward which hot pages are promoted).

## Synopsis

```c
/* kernel 5.17+, from mm/mempolicy.c (no man page, no glibc header) */
long set_mempolicy_home_node(unsigned long start, unsigned long len,
                             unsigned long home_node, unsigned long flags);
```

## Arguments and behavior

`start` must be page-aligned (after untagged_addr) and `len` is page
aligned by the kernel; a zero effective length returns 0 immediately
(mm/mempolicy.c: `if (end == start) return 0;`). `flags` must be 0
(`EINVAL` otherwise). `home_node` must be below MAX_NUMNODES and online
(`!node_online(home_node)` gives `EINVAL`). VMAs in the range without a
policy are skipped; if any VMA in the range has a policy other than
MPOL_BIND or MPOL_PREFERRED_MANY the call fails with `EOPNOTSUPP` and
does not reset the home node for VMAs already updated (mm/mempolicy.c
comment: "We don't reset the home node for vmas we already updated
before").

## Return value and errors

0 on success. Negated errors from the raw call: `EINVAL` (unaligned
start, nonzero flags, offline or out-of-range home_node, overflow),
`ENOENT` (no VMA in the range had a policy: err is initialized to
-ENOENT), `EOPNOTSUPP` (a VMA in the range has a policy other than
MPOL_BIND / MPOL_PREFERRED_MANY). The syscall takes mmap_write_lock for
the operation.

## Flags and constants

None: `flags` must be 0. Related constants MPOL_BIND (2) and
MPOL_PREFERRED_MANY (5) live in the [mbind](mbind.md) table.

## Security and notes

- No man page exists (man-pages 6.19); this page is a kernel-source
  entry, per the method's source-limited convention -- prose beyond the
  SYSCALL_DEFINE4 body (promotion/demotion interaction) is from
  mm/mempolicy.c context comments and is marked as such.
- i386, arm64-generic and arm32 share number 450 with x64 (hub).
- Worklog 1-b verified Since 5.17 by tag probing.

## References

- Kernel source: source-cache/fetched/master-mm-mempolicy.c
  (SYSCALL_DEFINE4(set_mempolicy_home_node), lines ~1763-1830).
- Numbers/Since: hub [overview](overview.md); worklog Task 1-b.
