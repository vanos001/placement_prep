# swapon(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | swapon 167 / 87 / 224 / 87; swapoff 168 / 115 / 225 / 115 (hub) |
| Since (kernel) | 1.0 (hub; syscalls(2) row 1.0; second swapflags argument since 1.3.2, swapon.2 CONFORMING TO) |
| Man page | man2/swapon.2 (cached, dated 2021-03-22; canonical page covering swapoff) |
| glibc wrapper | yes for both, in libc (header <sys/swap.h>) |
| Aliases covered | swapoff (SC-swapoff, grouped per ledger) |
| Ledger ID | SC-swapon (ledger status: researched brief; SC-swapoff also brief) |

## Purpose

swapon() makes the file or block device at `path` a swap area;
swapoff() stops swapping to it. Both need CAP_SYS_ADMIN, and the path
must be prepared with mkswap(8) (swapon.2). Explicit priorities are
"high": exhausted before lower areas; equal top priorities run
round-robin.

## Synopsis

```c
#include <sys/swap.h>
int swapon(const char *path, int swapflags);
int swapoff(const char *path);
```

## Arguments and behavior

`swapflags` may set SWAP_FLAG_PREFER (priority encoded as
`(prio << SWAP_FLAG_PRIO_SHIFT) & SWAP_FLAG_PRIO_MASK`) and
SWAP_FLAG_DISCARD (discard freed swap pages before reuse when the
device supports it; invalid flags give EINVAL since 3.4).

## Return value and errors

0 on success; -1 with `errno`: `EBUSY`, `EINVAL` (bad path/type/signature;
tmpfs; not a swap area for swapoff), `ENFILE`, `ENOENT`, `ENOMEM`,
`EPERM` (no CAP_SYS_ADMIN; MAX_SWAPFILES exhausted).

## Flags and constants

SWAP_FLAG_PREFER, SWAP_FLAG_PRIO_SHIFT/MASK, SWAP_FLAG_DISCARD from
<sys/swap.h>; discard conditional on the flag since 2.6.36.

## Security and notes

- MAX_SWAPFILES: 32 since 2.4.10, minus 2 with CONFIG_MIGRATION
  (page-migration machinery of [mbind](mbind.md)/[migrate_pages](migrate_pages.md)),
  minus 1 more with CONFIG_MEMORY_FAILURE (swapon.2 NOTES).
- Brief page per worklog 1-b split; both ledger IDs `researched`.

## References

- Cached man page: source-cache/man-pages-sparse/man2/swapon.2.
- Numbers/Since: hub [overview](overview.md); ledger SC-swapon,
  SC-swapoff.
