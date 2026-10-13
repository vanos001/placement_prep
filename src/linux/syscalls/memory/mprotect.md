# mprotect(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 10 / 125 / 226 / 125 |
| Since (kernel) | 1.0 |
| Man page | man2/mprotect.2 (cached, dated 2021-03-22); man2/pkey_mprotect.2 and man2/pkey_alloc.2 also cached |
| glibc wrapper | mprotect: libc; pkey_mprotect / pkey_alloc / pkey_free: _GNU_SOURCE, glibc 2.27 |
| Aliases covered | pkey_mprotect (SC-pkey_mprotect); pkey_alloc / pkey_free summarized below (SC-pkey_alloc, SC-pkey_free) |
| Ledger ID | SC-mprotect |

## Purpose

`mprotect()` changes the access protections of the pages covering
`[addr, addr+len-1]`; violating the protection raises `SIGSEGV`. It
underpins guard pages, W^X toggling for JITs, and -- via the protection-key
sibling `pkey_mprotect()` -- hardware-isolated memory compartments
(`pkeys(7)`).

## Synopsis

```c
#include <sys/mman.h>
int mprotect(void *addr, size_t len, int prot);
int pkey_mprotect(void *addr, size_t len, int prot, int pkey); /* _GNU_SOURCE */
```

## Arguments and behavior

`addr` must be page-aligned. `prot` is `PROT_NONE` or a bitwise OR of the
flags below. POSIX leaves behavior unspecified for memory not obtained via
`mmap(2)`, but on Linux the call is valid on any address in the process's
address space (except the kernel vsyscall area), including making code
mappings writable. `PROT_GROWSDOWN`/`PROT_GROWSUP` extend the change to
the start/end of a stack-like or upward-growing mapping. `pkey_mprotect()`
additionally assigns a pkey from `pkey_alloc(2)`; on hardware without pkeys
it may be called with `pkey == -1`, behaving exactly like `mprotect()`.
On x86, `mprotect()` with `PROT_EXEC` may implicitly set a pkey, but only
when the pkey was 0 before (man NOTES).

## Return value and errors

0 on success; -1 with `errno` on failure. Errors: `EACCES` (requested
access impossible, e.g. PROT_WRITE on a read-only file mapping), `EINVAL`
(addr unaligned; pkey not allocated; both PROT_GROWSUP and PROT_GROWSDOWN;
invalid prot bits; PowerPC PROT_SAO without SAO hardware), `ENOMEM`
(unmapped pages in range -- before 2.4.19 EFAULT was wrongly returned;
split would exceed the maximum number of distinct-attribute mappings).
Access violations deliver `SIGSEGV`.

## Flags and constants

| Constant | Meaning | Since / note |
|---|---|---|
| PROT_NONE | no access at all | POSIX |
| PROT_READ | readable | POSIX |
| PROT_WRITE | writable | POSIX; implies PROT_READ on some archs (e.g. i386) |
| PROT_EXEC | executable | POSIX; may equal PROT_READ (READ_IMPLIES_EXEC personality) |
| PROT_SEM | atomic operations allowed | 2.5.7; futex-era, unused on any architecture |
| PROT_SAO | strong access ordering | 2.6.26; PowerPC only |
| PROT_GROWSDOWN / PROT_GROWSUP | extend to growing end of mapping | since Linux 2.6.0 (man) |

### pkey_alloc(2) / pkey_free(2) (brief)

`pkey_alloc(flags, access_rights)` returns a positive pkey; `flags` must
be 0 today; `access_rights` may contain `PKEY_DISABLE_ACCESS` (0x1) and
`PKEY_DISABLE_WRITE` (0x2) (glibc `bits/mman-shared.h`). `ENOSPC` means no
keys remain (15 on x86) or no hardware/kernel support -- the call doubles
as a support probe. `pkey_free(pkey)` returns the key for reuse; freeing a
key still assigned to live memory is undefined. Man VERSIONS: kernel 4.9,
glibc 2.27; hub and syscall tables say 4.8 (conflict kept visible, per
worklog 1-b). Full treatment belongs on the hub's separate `pkey_alloc.md`
page when written. Numbers: x64 330/331, i386 381/382, g64 289/290,
arm 395/396 (hub).

## Security and notes

- pkey_mprotect numbers: x64 329, i386 380, g64 288, arm 394 (hub,
  cross-checked in the cached tables); hub Since 4.8 vs man VERSIONS 4.9.
- `PROT_EXEC` on a no-exec mount fails with `EPERM` at mmap time;
  `READ_IMPLIES_EXEC` personality silently widens `PROT_READ` to exec.
- Protection keys are a second enforcement layer: even with
  `PROT_READ|PROT_WRITE`, a disabled pkey (PKRU on x86) makes access fault.
  No mprotect-specific capability is required.

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/mprotect.2`
  (DESCRIPTION, ERRORS, VERSIONS, NOTES), `man2/pkey_mprotect.2` (`.so`
  alias), `man2/pkey_alloc.2`.
- Constants: `/usr/include/x86_64-linux-gnu/bits/mman-shared.h` (PKEY_*).
- Numbers/Since: hub [overview](overview.md); cached kernel syscall tables.
