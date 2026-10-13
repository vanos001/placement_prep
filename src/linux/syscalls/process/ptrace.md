# ptrace(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 101 / 26 / 117 / 26 |
| Since (kernel) | 1.0 (hub); newer requests per ptrace.2: SEIZE/INTERRUPT/LISTEN 3.4, PTRACE_O_EXITKILL 3.8, PTRACE_GET_SYSCALL_INFO 5.3 |
| Man page | man2/ptrace.2 (cached roff, dated 2021-03-22); no aliases |
| glibc wrapper | ptrace(3), symbol version GLIBC_2.2.5 (nm -D on glibc 2.41); glibc declares it variadic with only request fixed (ptrace.2, NOTES) |
| Aliases covered | none |
| Ledger ID | SC-ptrace |

## Purpose

ptrace() lets one process (the tracer) observe and control another (the tracee): single-stepping, breakpoints, register and memory inspection, and syscall tracing. It is the mechanism behind gdb, strace, and tracers generally. Attachment and commands are per thread; "tracee" always means one thread (ptrace.2, DESCRIPTION).

## Synopsis

```c
#include <sys/ptrace.h>
long ptrace(enum __ptrace_request request, pid_t pid, void *addr, void *data);
```

## Arguments and behavior

request selects the action; pid is the tracee thread ID; addr/data are request-specific. Request groups (values from /usr/include/x86_64-linux-gnu/sys/ptrace.h; semantics from ptrace.2):

| Group | Requests (value) | Notes |
|---|---|---|
| Self | PTRACE_TRACEME (0) | tracee volunteer; only used by the tracee |
| Peek/poke | PTRACE_PEEKTEXT (1), PEEKDATA (2), PEEKUSER (3), POKETEXT (4), POKEDATA (5), POKEUSER (6) | word-granular memory/USER-area access; TEXT and DATA equivalent on Linux |
| Run control | PTRACE_CONT (7), PTRACE_KILL (8), PTRACE_SINGLESTEP (9), PTRACE_SYSCALL (24), PTRACE_SYSEMU (31), PTRACE_SYSEMU_SINGLESTEP (32) | restart requests; require a stopped tracee |
| Registers | PTRACE_GETREGS (12), SETREGS (13), GETFPREGS (14), SETFPREGS (15), GETFPXREGS (18), SETFPXREGS (19), GETREGSET (0x4204), SETREGSET (0x4205), GET_THREAD_AREA (25), SET_THREAD_AREA (26) | REGSET is the NT_* uio-based portable form |
| Attach | PTRACE_ATTACH (16), PTRACE_DETACH (17), PTRACE_SEIZE (0x4206), PTRACE_INTERRUPT (0x4207), PTRACE_LISTEN (0x4208) | SEIZE is the modern attach without the SIGSTOP side effect |
| Info | PTRACE_GETEVENTMSG (0x4201), GETSIGINFO (0x4202), SETSIGINFO (0x4203), PEEKSIGINFO (0x4209), GETSIGMASK (0x420a), SETSIGMASK (0x420b), GET_SYSCALL_INFO (0x420e), SECCOMP_GET_FILTER (0x420c), SECCOMP_GET_METADATA (0x420d) | GETEVENTMSG returns event-specific data |
| Options | PTRACE_SETOPTIONS (0x4200) | sets PTRACE_O_* flags below |

Tracees stop on signal delivery, on syscall entry/exit (PTRACE_SYSCALL), and at PTRACE_EVENT_* points selected by options: PTRACE_O_TRACESYSGOOD (1), TRACEFORK (1<<1), TRACEVFORK (1<<2), TRACECLONE (1<<3), TRACEEXEC (1<<4), TRACEVFORKDONE (1<<5), TRACEEXIT (1<<6), TRACESECCOMP (1<<7), EXITKILL (1<<20), SUSPEND_SECCOMP (1<<21) (/usr/include/linux/ptrace.h); events PTRACE_EVENT_FORK 1, VFORK 2, CLONE 3, EXEC 4, VFORK_DONE 5, EXIT 6, SECCOMP 7, STOP 128 (same header).

## Return value and errors

PTRACE_PEEK* requests return the requested word (which may legitimately be -1, so clear errno first and check it afterwards); PTRACE_SECCOMP_GET_FILTER returns the BPF instruction count; PTRACE_GET_SYSCALL_INFO returns the number of bytes the kernel could write; all other requests return 0. On error, -1 with errno (ptrace.2, RETURN VALUE):

| Error | Meaning |
|---|---|
| EPERM | Tracee cannot be traced: insufficient privilege (needs CAP_SYS_PTRACE for unrelated processes), suid/setgid targets, already traced |
| ESRCH | Process does not exist, is not traced by the caller, or is not stopped when required |
| EIO | Invalid request, invalid memory area, word-alignment violation, or invalid injected signal |
| EFAULT | Bad tracer/tracee memory area (Linux returns EIO or EFAULT somewhat arbitrarily here) |
| EINVAL | Invalid option bits |
| EBUSY | i386 only: debug-register allocation failure |

## Flags and constants

See tables above (values verified in sys/ptrace.h and linux/ptrace.h). Access-mode constants are kernel-internal: PTRACE_MODE_READ vs PTRACE_MODE_ATTACH (distinction since 2.6.27) crossed with PTRACE_MODE_FSCREDS vs PTRACE_MODE_REALCREDS (since 4.5); PTRACE_MODE_ATTACH_REALCREDS gates pidfd_getfd(2) (ptrace.2, Ptrace access mode checking).

## Security and notes

Access is governed by ptrace access-mode checks: same-UID requirement or CAP_SYS_PTRACE, dumpable target, LSM decisions (SELinux, Yama, Smack, commoncap). Yama restricts attach to descendants unless PR_SET_PTRACER is used (ptrace.2, /proc/sys/kernel/yama/ptrace_scope). Set-user-ID processes cannot be ptraced, and a successful execve sends SIGTRAP to the tracee unless PTRACE_O_TRACEEXEC is set (execve.2). PTRACE_O_SUSPEND_SECCOMP requires CAP_SYS_ADMIN. Cross-reference: [prctl](prctl.md), [pidfd_getfd](pidfd_getfd.md), [execve](execve.md), [clone](clone.md).

## References

- https://man7.org/linux/man-pages/man2/ptrace.2.html
- kernel/ptrace.c (source named in the syscall tables work; worklog 1-a documented ptrace facts from ptrace.2)
- /usr/include/x86_64-linux-gnu/sys/ptrace.h, /usr/include/linux/ptrace.h
