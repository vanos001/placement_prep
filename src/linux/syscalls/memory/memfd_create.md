# memfd_create(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 319 / 356 / 279 / 385 |
| Since (kernel) | 3.17 |
| Man page | man2/memfd_create.2 (cached, dated 2021-03-22; predates MFD_NOEXEC_SEAL/MFD_EXEC, which are header-sourced below) |
| glibc wrapper | yes, since glibc 2.27; _GNU_SOURCE |
| Aliases covered | none |
| Ledger ID | SC-memfd_create |

## Purpose

`memfd_create()` creates an anonymous file and returns a file descriptor
for it. The file behaves like a regular file -- modifiable, truncatable,
sealable, memory-mappable -- but lives in RAM with volatile backing storage
and is released once all references are dropped. Its primary purpose is to
carry the file-sealing API (`fcntl(2)` `F_ADD_SEALS`/`F_GET_SEALS`), letting
mutually distrusting processes share memory without TOCTOU races or SIGBUS
surprises. It is also a cleaner alternative to manually mounting tmpfs or
`open(2)` `O_TMPFILE` when the file should never be linked into a
filesystem. See [memfd_secret](memfd_secret.md) for the hardened variant.

## Synopsis

```c
#define _GNU_SOURCE
#include <sys/mman.h>
int memfd_create(const char *name, unsigned int flags);
```

## Arguments and behavior

`name` is display-only: it appears as `memfd:<name>` in `/proc/self/fd/`
symlink targets, is limited to 249 bytes excluding the terminator (EINVAL
otherwise), and duplicates are harmless. The file starts at size 0; size it
with `ftruncate(2)` or populate it with `write(2)`. The returned descriptor
is `O_RDWR` with `O_LARGEFILE`. `fork(2)` shares the same file;
`execve(2)` keeps the descriptor unless `MFD_CLOEXEC` was set. Sealing
starts empty with `MFD_ALLOW_SEALING`, or locked to `F_SEAL_SEAL` (nothing
can ever be sealed) without it.

## Return value and errors

New file descriptor on success; -1 with `errno` on failure. Documented
errors: `EFAULT` (bad `name` pointer), `EINVAL` (unknown flag bits; name
too long; MFD_HUGETLB with MFD_ALLOW_SEALING before 4.16), `EMFILE` /
`ENFILE` (fd limits), `ENOMEM`, `EPERM` (MFD_HUGETLB without `CAP_IPC_LOCK`
and not in `sysctl_hugetlb_shm_group`).

## Flags and constants

Values verified in the installed kernel UAPI header
`/usr/include/linux/memfd.h` and glibc `bits/mman-shared.h`
(`#ifdef __USE_GNU`):

| Flag | Value | Since | Note |
|---|---|---|---|
| MFD_CLOEXEC | 0x0001U | 3.17 | set FD_CLOEXEC on the descriptor |
| MFD_ALLOW_SEALING | 0x0002U | 3.17 | enable F_ADD_SEALS; otherwise seals stay F_SEAL_SEAL-locked |
| MFD_HUGETLB | 0x0004U | 4.14 | file lives in hugetlbfs |
| MFD_NOEXEC_SEAL | 0x0008U | 6.3 era | not executable; sealed against becoming executable (header comment); absent from the cached 2021 man page |
| MFD_EXEC | 0x0010U | 6.3 era | executable (header comment); absent from the cached 2021 man page |
| MFD_HUGE_* / MFD_HUGE_SHIFT | encoded in high bits | 4.14 era | huge-page size selection; encoding mirrors MAP_HUGE_* |

MFD_HUGETLB + MFD_ALLOW_SEALING together are supported since 4.16 (man).
Unused flag bits must be zero.

## Security and notes

- Sealing threat model: seals are enforced by the kernel against *all*
  holders of the file, which is what makes them stronger than
  cooperation-based protocols; a peer holding the descriptor via
  SCM_RIGHTS, fork, or `/proc/<pid>/fd/<n>` cannot shrink or rewrite a
  sealed region (man "File sealing" walkthrough).
- MFD_NOEXEC_SEAL / MFD_EXEC respond to the noexec-mapping hardening push;
  coverage here is header-sourced because the cached man page (2021-03-22)
  predates them -- kernel version stated as the 6.3 era, not tag-probed
  this session (unverified exact since).
- Hugetlb flavor needs `CAP_IPC_LOCK` or membership in
  `sysctl_hugetlb_shm_group` (EPERM otherwise).
- Linux-specific; no POSIX analog. Pair with [mmap](mmap.md) for the
  mapping side and [userfaultfd](userfaultfd.md) for fault-driven
  population.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/memfd_create.2`.
- Headers: `/usr/include/linux/memfd.h` (all MFD_* values incl.
  MFD_NOEXEC_SEAL/MFD_EXEC with comments),
  `/usr/include/x86_64-linux-gnu/bits/mman-shared.h` (glibc-side copies).
- Numbers: hub [overview](overview.md); cached kernel syscall tables.
