# getresgid(2) / getresgid32

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 211 / -- / -- |
| Since (kernel) | 2.4 (32-bit twin; base getresgid is 2.2, man-pages 6.19 HISTORY) |
| Man page | man2/getresgid.2 is a one-line .so alias to getresuid.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | getresgid(3) @@GLIBC_2.2.5 (nm -D, glibc 2.41); the wrapper selects the right kernel entry transparently (getresuid.2, HISTORY) |
| Aliases covered | getresgid32 (this page, SC-getresgid32); family entry on [getresuid](getresuid.md) |
| Ledger ID | SC-getresgid32 |

## Purpose

getresgid32 is the 32-bit group-ID twin of the original 16-bit i386 getresgid() entry (syscall 171). Linux 2.4 added getresgid32() (i386 211) -- alongside getresuid32() (i386 209) -- so that 32-bit user and group IDs could be returned on architectures whose historical entry carried 16-bit IDs (getresuid.2, HISTORY). The family semantics -- reading the real, effective, and saved set-group-IDs in one call -- are documented on [getresuid](getresuid.md), which also covers the base getresgid() row (SC-getresgid).

## Synopsis

```c
/* no glibc-visible distinct prototype: the wrapper hides the twin */
#include <unistd.h>
int getresgid(gid_t *rgid, gid_t *egid, gid_t *sgid);
```

Invoked directly (if ever needed) as `syscall(211, rgid, egid, sgid)` on i386.

## Arguments and behavior

Identical to the base getresgid() call: three out-parameters receiving the real, effective, and saved set-group-IDs (getresuid.2, DESCRIPTION). On asm-generic architectures (arm64, riscv, loongarch) the base entry was 32-bit from the start (g64 150 for getresgid), so no twin exists -- the ledger columns show `--` for x64 and g64, which is meaningful rather than an omission (ledger overview, scope caveats).

## Return value and errors

Same contract as the family page: 0 on success; -1 with EFAULT if an argument points outside the address space (getresuid.2, ERRORS).

## Flags and constants

None.

## Security and notes

Userspace never calls the twin by number: glibc's getresgid(3) wrapper picks the appropriate kernel entry per kernel version (getresuid.2, HISTORY). The 16/32-bit split is the same compatibility pattern as [setgid](setgid.md)/setgid32 and [getuid](getuid.md)/getuid32; interviews occasionally probe why the *32 names exist at all -- the answer is the 2.4-era 16-bit-to-32-bit credential widening. Cross-reference: [getresuid](getresuid.md), [setgid](setgid.md), [setresuid](setresuid.md).

## References

- https://man7.org/linux/man-pages/man2/getresuid.2.html (getresgid.2 .so alias target)
- man-pages syscalls(2) version table (2.4 additions)
- worklog: wrapper symbol getresgid @@GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
