# migrate_pages(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 256 / 294 / 238 / 400 (hub) |
| Since (kernel) | 2.6.16 (hub; migrate_pages.2 VERSIONS: "first appeared on Linux in version 2.6.16") |
| Man page | man2/migrate_pages.2 (cached, dated 2021-03-22) |
| glibc wrapper | none ("Glibc does not provide a wrapper"; libnuma supplies one; <numaif.h> from libnuma-devel) |
| Aliases covered | none |
| Ledger ID | SC-migrate_pages |

## Purpose

migrate_pages() attempts to move all pages of process `pid` that live on
nodes in `old_nodes` to nodes in `new_nodes`; pages outside old_nodes
are untouched. The kernel tries to preserve the relative topology
relationship among old_nodes in the migration to new_nodes. Unlike
move_pages(2) ([move_pages](move_pages.md)) it takes no page list: the
whole-process node-remap use case (for example cpuset/numactl
migratepages(8)) is the target (migrate_pages.2).

## Synopsis

```c
#include <numaif.h>
long migrate_pages(int pid, unsigned long maxnode,
                   const unsigned long *old_nodes,
                   const unsigned long *new_nodes);
```

## Arguments and behavior

`old_nodes` and `new_nodes` are bit masks of node numbers with up to
`maxnode` bits each (maxnode = highest node number plus one, same
convention as mbind(2) [mbind](mbind.md), unlike select(2)); bits beyond
maxnode in the final unsigned long are ignored. `pid` 0 targets the
calling process. Pages shared with another process are moved only if
the caller holds CAP_SYS_NICE. Masks that name no online, cpuset-allowed
node with memory fail with EINVAL.

## Return value and errors

Success returns the number of pages that could not be moved (0 = all
moved). On error -1 with `errno`: `EFAULT` (old/new_nodes unreadable),
`EINVAL` (maxnode over the kernel limit; node IDs above the supported
maximum; no on-line allowed node with memory in new_nodes), `EPERM`
(insufficient privilege for the target process or for the target
nodes), `ESRCH` (no process with that pid). The man page FIXME notes
further undocumented errors exist.

## Flags and constants

No flags argument. Related capability: CAP_SYS_NICE for cross-process
and shared-page moves.

## Security and notes

- Moving pages of another process requires CAP_SYS_NICE or matching
  user IDs (real or effective caller ID vs real or saved-set target ID)
  (migrate_pages.2).
- Like move_pages(2), the result may violate existing memory policies
  (policy does not constrain destinations, migrate_pages.2 NOTES).
- CONFIG_MIGRATION reserves two swap slots (MAX_SWAPFILES count drops to
  30 when built in) -- noted on [swapon](swapon.md); the same kernel
  page-migration machinery backs this call (migrate_pages.2 SEE ALSO
  Documentation/vm/page_migration.rst).

## References

- Cached man page: source-cache/man-pages-sparse/man2/migrate_pages.2.
- Numbers/Since: hub [overview](overview.md); ledger SC-migrate_pages.
