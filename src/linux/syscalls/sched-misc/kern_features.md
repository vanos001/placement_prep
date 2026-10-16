# kern_features(2) (SPARC64)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (SPARC64 table only) |
| Since (kernel) | 3.7 (syscalls(2) lists kern_features as SPARC64; ledger since 3.7) |
| Man page | none (no man2/kern_features.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [memory_ordering](memory_ordering.md) |
| Ledger ID | SC-kern_features |

## Purpose

kern_features() reports which optional kernel behaviors the running SPARC64 kernel supports, so userspace can adapt without probing through failure: the verified implementation returns a fixed feature bitmask -- `return KERN_FEATURE_MIXED_MODE_STACK;` (arch/sparc/kernel/sys_sparc_64.c:720, torvalds/linux master fetched 2026-10-17). KERN_FEATURE_MIXED_MODE_STACK advertises support for 32-bit and 64-bit stack frames coexisting in one process (the sparc64 compat-signal-frame capability).

## Synopsis

```c
/* SPARC64 syscall */
long syscall(SYS_kern_features);   /* returns a KERN_FEATURE_* bitmask */
```

## Arguments and behavior

No arguments.

## Return value and errors

Returns the feature bitmask; on the current master tree the only advertised bit is KERN_FEATURE_MIXED_MODE_STACK (verified source).

## Flags and constants

KERN_FEATURE_MIXED_MODE_STACK (arch/sparc kernel headers).

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. Interview angle: kern_features is the syscall-shaped capability bitmap -- the same design idea as getauxval(AT_HWCAP*) and ELF auxv feature flags, but kernel-private to SPARC64's compat needs. Cross-reference: [memory_ordering](memory_ordering.md), [getcpu](getcpu.md), [uname](uname.md).

## References

- Kernel source: arch/sparc/kernel/sys_sparc_64.c (SYSCALL_DEFINE0(kern_features)), torvalds/linux master, fetched 2026-10-17
- man-pages syscalls(2) (kern_features(2), 3.7, SPARC64 only)

