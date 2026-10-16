# old_getrlimit(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (per-arch compat tables) |
| Since (kernel) | 2.4 (syscalls(2): "Old variant of getrlimit(2)") |
| Man page | none (no man2/old_getrlimit.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction; the base call is documented on [getrlimit](../process/getrlimit.md) and man2/getrlimit.2 |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; base call [getrlimit](../process/getrlimit.md) |
| Ledger ID | SC-old_getrlimit |

## Purpose

old_getrlimit() is the pre-2.6-structure variant of getrlimit(2): it fills the older `struct rlimit` whose rlim_cur/rlim_max were unsigned long members rather than the modern rlim_t, and which could not represent RLIM_INFINITY's full 64-bit range on 32-bit platforms. The name survives in per-arch compat tables (syscalls(2) dates the rename-era entry at 2.4); the modern call lives on [getrlimit](../process/getrlimit.md).

## Synopsis

```c
/* compat variant */
long syscall(SYS_old_getrlimit, int resource, struct old_rlimit *rlim);
```

## Arguments and behavior

`resource` selects the limit (RLIMIT_NOFILE and friends); `rlim` receives the old-layout values (kernel compat rlimit machinery).

## Return value and errors

0 on success; -1 with the getrlimit(2) error set (EINVAL for a bad resource, EFAULT for a bad pointer) -- see man2/getrlimit.2 for the base contract.

## Flags and constants

RLIMIT_* constants (shared with the base call); the old rlimit struct layout is the variant's defining trait.

## Security and notes

Source-limited: no man page exists for the variant; the entry names the gap and describes the layout-change reason. Interview angle: old_getrlimit is the same struct-widening story as oldstat/olduname (see [stat](stat.md), [uname](uname.md)) -- layout growth forces new numbers while old slots freeze. Cross-reference: [getrlimit](../process/getrlimit.md), [old_adjtimex](old_adjtimex.md).

## References

- man-pages syscalls(2) (old_getrlimit(2), 2.4, "Old variant of getrlimit(2)")
- Ledger row SC-old_getrlimit

