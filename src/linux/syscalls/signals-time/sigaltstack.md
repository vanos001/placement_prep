# sigaltstack(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 131 / 186 / 132 / 186 (ledger SC-sigaltstack; verified syscall_64.tbl line 143, syscall_32.tbl line 201, syscall_generic.tbl line 168, syscall_arm.tbl line 203) |
| Since (kernel) | 2.2 (ledger SC-sigaltstack); SS_AUTODISARM since Linux 4.7 (sigaltstack.2) |
| Man page | man2/sigaltstack.2 (cached) |
| glibc wrapper | sigaltstack(3) is the direct wrapper; since glibc 2.34 the SIGSTKSZ and MINSIGSTKSZ constants became run-time values (SIGSTKSZ = sysconf(_SC_SIGSTKSZ), MINSIGSTKSZ = SIGSTKSZ; glibc NEWS quoted in worklog 1-e; installed bits/sigstksz.h carries the sysconf form) |
| Aliases covered | none |
| Ledger ID | SC-sigaltstack |

## Purpose

sigaltstack() lets a thread define a new alternate signal stack and/or retrieve the state of an existing one. A handler established with the SA_ONSTACK flag then runs on that stack instead of the normal one - the standard defense when the normal stack may itself be exhausted (SIGSEGV from stack overflow), and the base for stack switching inside handlers (sigaltstack.2).

## Synopsis

```c
#include <signal.h>
int sigaltstack(const stack_t *ss, stack_t *old_ss);
typedef struct {
    void  *ss_sp;     /* base address of stack */
    int    ss_flags;  /* flags */
    size_t ss_size;   /* number of bytes in stack */
} stack_t;
```

## Arguments and behavior

ss installs a new stack: ss_sp/ss_size describe the memory, ss.ss_flags is either 0 or SS_AUTODISARM. old_ss (or ss = NULL) retrieves the current setting; the returned ss_flags reads SS_ONSTACK while the thread executes on the alternate stack (changing it then fails with EPERM), or SS_DISABLE when none is set. The usual sequence is: allocate an area, register it here, establish handlers with SA_ONSTACK (sigaltstack.2).

## Return value and errors

0 on success, -1 with errno on failure (sigaltstack.2). Errors: EFAULT (ss or old_ss invalid); EINVAL (invalid flag in ss_flags, or SS_AUTODISARM on a kernel without support); ENOMEM (ss_size below MINSIGSTKSZ); EPERM (attempt to change the stack while it is active).

## Flags and constants

| Flag | Value | Source | Since |
|---|---|---|---|
| SS_ONSTACK | 1 | glibc bits/ss_flags.h enum; /usr/include/linux/signal.h | 1.0 |
| SS_DISABLE | 2 | same headers | 1.0 |
| SS_AUTODISARM | 1U << 31 | /usr/include/linux/signal.h ("disable sas during sighandling") | 4.7 (sigaltstack.2) |

SS_AUTODISARM clears the alternate-stack setting on handler entry and restores it on return, making swapcontext(3) away from a handler safe; without it a later signal corrupts the switched-away state (sigaltstack.2).

## Security and notes

MINSIGSTKSZ is the minimum stack able to run a handler; SIGSTKSZ the recommended size (sigaltstack.2). Because these constants became run-time values in glibc 2.34, code must call sysconf(_SC_SIGSTKSZ) instead of using the macro in static initializers (worklog 1-e, sourced from glibc NEWS; sigaltstack.2 documents the MINSIGSTKSZ floor for ENOMEM).

## References

- https://man7.org/linux/man-pages/man2/sigaltstack.2.html
- /usr/include/linux/signal.h, /usr/include/x86_64-linux-gnu/bits/ss_flags.h, bits/sigstksz.h
- worklog Task 1-e (glibc 2.34 MINSIGSTKSZ/SIGSTKSZ sysconf dynamics)
- [rt_sigaction](rt_sigaction.md) (SA_ONSTACK), [sigreturn](sigreturn.md), [overview](overview.md)
