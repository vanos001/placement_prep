# sys_debug_setcontext(2) (PowerPC)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC table only) |
| Since (kernel) | 2.6.11 (syscalls(2): "PowerPC only") |
| Man page | none (no man2/sys_debug_setcontext.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [swapcontext](swapcontext.md) |
| Ledger ID | SC-sys_debug_setcontext |

## Purpose

sys_debug_setcontext() is the debugger-facing variant of PowerPC's setcontext: it restores a saved signal context with the additional checks and bookkeeping debuggers need when they force a tracee into a restored state -- the dispatcher's fault handler even names it explicitly ("signal_fault(current, regs, "sys_debug_setcontext", ctx)" appears in the verified source, arch/powerpc/kernel/signal_32.c:1270, fetched 2026-10-17). gdb uses it to resume tracees from a captured context.

## Synopsis

```c
/* PowerPC syscall */
long syscall(SYS_sys_debug_setcontext, struct ucontext *ctx,
             int size, ...);
```

## Arguments and behavior

`ctx`/`size` carry the context to restore, mirroring swapcontext/setcontext conventions (the extra variant exists for the debug path's stricter validation).

## Return value and errors

0 on success; negated errors for invalid contexts; the kernel raises signal_fault diagnostics when the restored frame is malformed (verified source line).

## Flags and constants

None.

## Security and notes

Source-limited: the fault-path reference was verified in the fetched source; no man page exists. Interview angle: "why would setcontext need a debug twin?" -- because a debugger restoring a context must not run the normal sigreturn-side effects; a dedicated syscall keeps the debug semantics out of the production path. Cross-reference: [swapcontext](swapcontext.md), [ptrace](../process/ptrace.md), [sigreturn](../signals-time/sigreturn.md).

## References

- Kernel source: arch/powerpc/kernel/signal_32.c (sys_debug_setcontext fault path), torvalds/linux master, fetched 2026-10-17
- man-pages syscalls(2) (sys_debug_setcontext(2), 2.6.11, PowerPC only)

