# mlock(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | mlock 149 / 150 / 228 / 150; mlock2 325 / 376 / 284 / 390; mlockall 151 / 152 / 230 / 152; munlock 150 / 151 / 229 / 151; munlockall 152 / 153 / 231 / 153 |
| Since (kernel) | mlock/mlockall/munlock/munlockall 2.0 (hub); mlock2 4.4 (hub + man VERSIONS) |
| Man page | man2/mlock.2 (cached, dated 2021-03-22) is the family page; man2/mlock2.2, man2/mlockall.2, man2/munlock.2, man2/munlockall.2 are `.so` aliases of it (all cached) |
| glibc wrapper | yes for all five; mlock2 since glibc 2.27 |
| Aliases covered | mlock2, mlockall, munlock, munlockall (SC-mlock2, SC-mlockall, SC-munlock, SC-munlockall) |
| Ledger ID | SC-mlock |

## Purpose

The mlock family locks part or all of the calling process's virtual address
space into RAM so the kernel never pages it to swap. Man-page motivations:
deterministic latency for real-time code (paging is a major jitter source)
and keeping secrets (passwords, keys) off persistent swap, where they would
outlive the process's erasure of RAM. `munlock()`/`munlockall()` are the
converses.

## Synopsis

```c
#include <sys/mman.h>
int mlock(const void *addr, size_t len);
int mlock2(const void *addr, size_t len, unsigned int flags);
int munlock(const void *addr, size_t len);
int mlockall(int flags);
int munlockall(void);
```

## Arguments and behavior

`mlock()`/`mlock2()`/`munlock()` operate on `[addr, addr+len)` in whole-page
units; Linux rounds `addr` down (POSIX may require alignment, so portable
code should align). `mlock()` guarantees every page containing part of the
range is resident on return and stays so until unlocked. `mlock2(flags == 0)`
equals `mlock()`; `MLOCK_ONFAULT` locks current pages and marks the range so
later faulted-in pages lock automatically. `mlockall()` locks all mapped
pages (code, data, stack, shared libraries, shared memory, mapped files);
`munlockall()` unlocks everything. With `MCL_FUTURE`, later calls exceeding
the locked limit fail -- and stack growth is denied with `SIGSEGV`.

## Return value and errors

0 on success; -1 with `errno`, and no locks change on failure. `EAGAIN`
(range could not be locked), `EINVAL` (addr+len overflow; unknown
mlock2/mlockall flags; MCL_ONFAULT without MCL_CURRENT or MCL_FUTURE),
`ENOMEM` (range not fully mapped; split would exceed the maximum number of
distinct-attribute mappings; since 2.6.9 locking past a nonzero
`RLIMIT_MEMLOCK` soft limit), `EPERM` (unprivileged caller needing
`CAP_IPC_LOCK`).

## Flags and constants

Values verified in glibc headers (`bits/mman-linux.h` MCL_*;
`bits/mman-shared.h` MLOCK_ONFAULT under `#ifdef __USE_GNU`):

| Constant | Value | Since | Applies to |
|---|---|---|---|
| MLOCK_ONFAULT | 1U | 4.4 | mlock2 only |
| MCL_CURRENT | 1 | 2.0 | mlockall |
| MCL_FUTURE | 2 | 2.0 | mlockall |
| MCL_ONFAULT | 4 | 4.4 | mlockall; must combine with MCL_CURRENT and/or MCL_FUTURE |

## Security and notes

- Capability gate: locking beyond `RLIMIT_MEMLOCK` requires `CAP_IPC_LOCK`;
  unprivileged callers are bounded by the rlimit (visible as `VmLck` in
  `/proc/[pid]/status`).
- Locks are not inherited across `fork(2)`, dropped on `execve(2)` and at
  exit; `MCL_FUTURE` (with or without MCL_ONFAULT) is likewise not
  inherited. Locks do not stack; one `munlock()` releases them; unmapping
  removes them.
- Swap caveat from the man page: suspend-to-disk writes RAM to disk
  regardless of memory locks.
- Real-time guidance: prefault a large stack array before the critical
  section; avoid `fork(2)` after mlockall (COW faults).
- `MLOCK_ONFAULT` / `MCL_ONFAULT` suit large sparse mappings where locking
  everything up front is too expensive.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mlock.2` (family
  page); alias files verified: `mlock2.2`, `mlockall.2`, `munlock.2`,
  `munlockall.2` (`.so man2/mlock.2`).
- Constants: `/usr/include/x86_64-linux-gnu/bits/mman-linux.h` (MCL_*),
  `bits/mman-shared.h` (MLOCK_ONFAULT).
- Numbers: hub [overview](overview.md); cached kernel syscall tables
  (generic 228/229/230/231/284; arm 150/151/152/153/390).
