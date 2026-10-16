# swapcontext(2) (PowerPC)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC table only) |
| Since (kernel) | 2.6.3 (syscalls(2): "PowerPC/PowerPC64 only") |
| Man page | none (no man2/swapcontext.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-swapcontext |

## Purpose

swapcontext() atomically saves the calling thread's signal context into old_ctx and loads new_ctx -- getcontext(3)+setcontext(3) fused into one kernel operation for PowerPC, added so userspace thread packages could context-switch without the race window between saving and restoring. The implementation is verified: `SYSCALL_DEFINE3(swapcontext, struct ucontext __user *, old_ctx, struct ucontext __user *, new_ctx, int, size)` in arch/powerpc/kernel/signal_32.c:993 (fetched 2026-10-17), with a COMPAT twin for 32-bit contexts on ppc64.

## Synopsis

```c
/* PowerPC syscall */
long syscall(SYS_swapcontext, struct ucontext *old_ctx,
             struct ucontext *new_ctx, int size);
```

## Arguments and behavior

`old_ctx` receives the current context (mcontext + signal mask); `new_ctx` is restored; `size` guards the structure version (verified source signature). The kernel performs the save-then-restore atomically with respect to signal delivery -- the property the separate POSIX calls cannot give.

## Return value and errors

0 on success; -1-class negated errors on the raw path for bad pointers (EFAULT) or size mismatch (EINVAL-class).

## Flags and constants

None.

## Security and notes

Source-limited: signature verified in the fetched source; no man page exists. Interview angle: the race that swapcontext closes (a signal arriving between getcontext and setcontext can clobber the just-saved state) is a favorite systems-design question; POSIX's answer is sigprocmask games, PPC's was a syscall. Cross-reference: [rt_sigprocmask](../signals-time/rt_sigprocmask.md), [rt_sigreturn](../signals-time/sigreturn.md), [sys_debug_setcontext](sys_debug_setcontext.md).

## References

- Kernel source: arch/powerpc/kernel/signal_32.c (SYSCALL_DEFINE3(swapcontext)), torvalds/linux master, fetched 2026-10-17
- man-pages syscalls(2) (swapcontext(2), 2.6.3, PowerPC only)

