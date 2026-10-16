# arc_gettls(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARC table only) |
| Since (kernel) | 3.9 (syscalls(2): "ARC only") |
| Man page | none (no man2/arc_gettls.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; pair with [arc_settls](arc_settls.md) |
| Ledger ID | SC-arc_gettls |

## Purpose

arc_gettls() reads the ARC thread-pointer register -- the value userspace TLS code uses as its thread pointer -- and returns it to the caller. ARC cores have no dedicated TLS hardware register visible to userspace, so the kernel stores the value in the task's thread info and the two private syscalls move it in and out (kernel arch/arc implementation of the TLS pointer, alongside the kuser-helper-style access). It exists so libc (uClibc/musl/glibc ARC ports) can implement pthread_self()-class primitives.

## Synopsis

```c
/* ARC private syscall */
long syscall(SYS_arc_gettls);   /* returns the thread pointer */
```

## Arguments and behavior

No arguments. The call returns the current thread's TLS pointer value (arch/arc kernel TLS support).

## Return value and errors

Returns the thread pointer on success; a negated error on the raw path for a non-ARC kernel (ENOSYS).

## Flags and constants

None.

## Security and notes

This page is source-limited: no man page exists and the entry states the contract from the ARC TLS implementation's role rather than a fetched source; syscalls(2) confirms the name and its 3.9 ARC-only status. In interviews it matters as an example of "architectures without TLS hardware grow private syscalls" -- the same shape as [set_tls](set_tls.md) on ARM. Cross-reference: [arc_settls](arc_settls.md), [set_tls](set_tls.md), [arch_prctl](../process/arch_prctl.md).

## References

- man-pages syscalls(2) (arc_gettls(2), 3.9, ARC only)
- Ledger row SC-arc_gettls (numbers column: not present in x86_64/i386/asm-generic/arm32)

