# sigreturn(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | rt_sigreturn: 15 / 173 / 139 / 173 (ledger SC-rt_sigreturn; verified syscall_64.tbl line 27, syscall_32.tbl line 188, syscall_generic.tbl line 176, syscall_arm.tbl line 190); legacy sigreturn: - / 119 / - / 119 (ledger SC-sigreturn; verified syscall_32.tbl line 134) |
| Since (kernel) | rt_sigreturn 2.2 (ledger, same rt_* split as the other rt_ signal calls); legacy sigreturn 1.0 (ledger SC-sigreturn) |
| Man page | man2/sigreturn.2 (cached); rt_sigreturn.2 is an .so alias ("\.so man2/sigreturn.2") |
| glibc wrapper | none: a glibc sigreturn() stub simply returns -1 with errno ENOSYS (sigreturn.2 NOTES); applications never call it directly |
| Aliases covered | rt_sigreturn (kernel name, the rt ABI), legacy sigreturn (i386/arm32 slot 119, old frame layout) |
| Ledger ID | SC-rt_sigreturn, SC-sigreturn |

## Purpose

sigreturn() is the second half of every handled signal: it undoes what the kernel did to deliver a signal, restoring the interrupted context (signal mask, alternate signal stack, registers including stack pointer and instruction pointer) so execution resumes where the signal interrupted it (sigreturn.2). The kernel never calls it on your behalf in a way you arrange; it is wired into the signal trampoline.

## Synopsis

```c
/* no glibc wrapper; architecture-specific */
int syscall(SYS_rt_sigreturn);
```

## Arguments and behavior

Flow (sigreturn.2): when an unblocked signal becomes deliverable, the kernel saves the process context (processor status word, registers, signal mask, signal stack settings) in a frame it builds on the user-space stack, arranges a transition to the handler, and on handler return passes control to the signal trampoline; the trampoline calls sigreturn(), which rebuilds the state from that frame. On x86-64 the syscall takes no arguments - everything it needs sits in the stack frame (sigreturn.2 NOTES). The frame is visible to SA_SIGINFO handlers as the third argument, a ucontext_t (sigreturn.2; <sys/ucontext.h>).

## Return value and errors

sigreturn() never returns (sigreturn.2 RETURN VALUE). It has no error convention: there is no errno contract, and the glibc stub returns -1 with ENOSYS only because the stub itself is meaningless (sigreturn.2).

## Flags and constants

SA_RESTORER (sigaction.2, "not intended for application use"): when the signal trampoline lives in the C library, the sigaction wrapper places its address in sa_restorer and sets SA_RESTORER so the kernel knows where to return (sigaction.2 C library/kernel differences; sigreturn.2). Historical detail: trampoline code once sat on the user stack; user stacks are now non-executable, so on contemporary systems the trampoline lives in the vDSO or in the C library, depending on architecture (sigreturn.2).

## Security and notes

Never call sigreturn() yourself: without the kernel-built frame the restored context is garbage and the call is a jump to an attacker-influenced register state. The frame layout is architecture-specific; the legacy i386 sigreturn (slot 119) and the rt_sigreturn frames differ (ledger; sigreturn.2).

## References

- https://man7.org/linux/man-pages/man2/sigreturn.2.html
- [rt_sigaction](rt_sigaction.md) (SA_RESTORER field), [sigaltstack](sigaltstack.md), [overview](overview.md)
