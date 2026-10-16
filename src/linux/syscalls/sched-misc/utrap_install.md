# utrap_install(2) (SPARC)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (SPARC table only) |
| Since (kernel) | 2.2 (syscalls(2) SPARC family; ledger since 2.2) |
| Man page | none (no man2/utrap_install.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-utrap_install |

## Purpose

utrap_install() installs userspace handlers for SPARC precision traps: instead of the kernel delivering a SIGFPE/SIGSEGV-shaped signal, the registered handler receives the trap with the processor state -- the OSF/1-derived mechanism SPARC Solaris used for things like visible-FPU emulation. The verified implementation is `SYSCALL_DEFINE5(utrap_install, utrap_entry_t, type, utrap_handler_t, new_p, utrap_handler_t, new_d, utrap_handler_t __user *, old_p, utrap_handler_t __user *, old_d)` (arch/sparc/kernel/sys_sparc_64.c:625, fetched 2026-10-17), with UTH_NOCHANGE semantics for handlers passed as the special value (verified in the fetched body).

## Synopsis

```c
/* SPARC syscall */
long syscall(SYS_utrap_install, utrap_entry_t type,
             utrap_handler_t new_p, utrap_handler_t new_d,
             utrap_handler_t *old_p, utrap_handler_t *old_d);
```

## Arguments and behavior

`type` selects the trap entry (UTH_* constants from <asm/utrap.h>); `new_p`/`new_d` install the handler and its data, with UTH_NOCHANGE preserving the current values; `old_p`/`old_d` receive the previous ones (verified source body).

## Return value and errors

0 on success; a negated error on the raw path for invalid types (the fetched body also handles the no-utraps-yet allocation path).

## Flags and constants

UTH_NOCHANGE and the UTH_* trap-type constants (<asm/utrap.h>; the source includes <asm/utrap.h>).

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. Interview angle: userspace trap handlers with processor state are a different philosophy from POSIX signals -- Solaris used them for x86-emulation layers; Linux kept them only on SPARC. Cross-reference: [rt_sigaction](../signals-time/rt_sigaction.md), [memory_ordering](memory_ordering.md), [kern_features](kern_features.md).

## References

- Kernel source: arch/sparc/kernel/sys_sparc_64.c (SYSCALL_DEFINE5(utrap_install)), torvalds/linux master, fetched 2026-10-17
- Ledger row SC-utrap_install

