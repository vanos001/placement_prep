# arc_settls(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARC table only) |
| Since (kernel) | 3.9 (syscalls(2): "ARC only") |
| Man page | none (no man2/arc_settls.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; pair with [arc_gettls](arc_gettls.md) |
| Ledger ID | SC-arc_settls |

## Purpose

arc_settls() sets the ARC thread-pointer register for the calling thread to the given value, completing the TLS-pointer pair with [arc_gettls](arc_gettls.md). libc's thread-creation path calls it after clone so each thread's TLS area is addressable through the platform's thread-pointer convention.

## Synopsis

```c
/* ARC private syscall */
long syscall(SYS_arc_settls, void *tls_ptr);
```

## Arguments and behavior

One argument: the new thread-pointer value (arch/arc kernel TLS support).

## Return value and errors

0 on success; a negated error on the raw path (ENOSYS on non-ARC kernels).

## Flags and constants

None.

## Security and notes

Source-limited: no man page exists; the entry names that gap and rests on the syscall's role in the ARC TLS design plus the syscalls(2) listing. Cross-reference: [arc_gettls](arc_gettls.md), [set_tls](set_tls.md), [clone](../process/clone.md) (CLONE_SETTLS is the generic mechanism).

## References

- man-pages syscalls(2) (arc_settls(2), 3.9, ARC only)
- Ledger row SC-arc_settls

