# old_adjtimex(2) (Alpha)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Alpha table only) |
| Since (kernel) | 2.0 (syscalls(2): "Alpha only; see NOTES") |
| Man page | none (no man2/old_adjtimex.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction; the base call is documented at [adjtimex](../signals-time/clock_adjtime.md) and man2/adjtimex.2 |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; base call [adjtimex/clock_adjtime](../signals-time/clock_adjtime.md) |
| Ledger ID | SC-old_adjtimex |

## Purpose

old_adjtimex() is Alpha's 32-bit-struct variant of adjtimex(2): the verified signature is `SYSCALL_DEFINE1(old_adjtimex, struct timex32 __user *, txc_p)` (arch/alpha/kernel/osf_sys.c:1175, fetched 2026-10-17) -- identical semantics to adjtimex but converting between the kernel's 64-bit `struct timex` and OSF/1's 32-bit timex32 layout for pre-existing binaries.

## Synopsis

```c
/* Alpha syscall */
long syscall(SYS_old_adjtimex, struct timex32 *buf);
```

## Arguments and behavior

One argument: a pointer to the 32-bit timex32 structure; fields behave as the base adjtimex(2) contract (modes selector, offset/freq/status), with the kernel translating layouts (verified source signature).

## Return value and errors

Returns the clock state (TIME_OK, TIME_INS, ... -- the adjtimex(2) contract) on success; -1 with the adjtimex error set otherwise.

## Flags and constants

The ADJ_* mode selectors and STA_* status bits, in their 32-bit layout (base call: man2/adjtimex.2).

## Security and notes

Source-limited: the signature was verified in the fetched source; no man page exists for the variant. Interview angle: old_adjtimex is the 32/64-struct-conversion pattern (like the *time64 twins) applied to OSF/1 heritage rather than y2038. Cross-reference: [adjtimex/clock_adjtime](../signals-time/clock_adjtime.md), [old_getrlimit](old_getrlimit.md).

## References

- Kernel source: arch/alpha/kernel/osf_sys.c (SYSCALL_DEFINE1(old_adjtimex), torvalds/linux master, fetched 2026-10-17)
- man-pages syscalls(2) (old_adjtimex(2), 2.0, Alpha only)

