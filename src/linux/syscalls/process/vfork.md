# vfork(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 58 / 190 / - / 190 |
| Since (kernel) | 2.2 |
| Man page | man2/vfork.2 (cached roff, dated 2021-03-22); History section: equivalent to fork(2) until about 2.2.0-pre6, independent system call since 2.2.0-pre9 (i386; later elsewhere) |
| glibc wrapper | vfork(3) @@GLIBC_2.2.5 (nm -D, glibc 2.41); support added in glibc 2.0.112 (vfork.2, History); declaration gated by (_XOPEN_SOURCE >= 500) && !(_POSIX_C_SOURCE >= 200809L), or _DEFAULT_SOURCE/_BSD_SOURCE (vfork.2, SYNOPSIS) |
| Aliases covered | none; arm64-generic has no vfork number (hub g64 column "-"), consistent with worklog 1-a: arm64 has no fork/vfork syscalls |
| Ledger ID | SC-vfork |

## Purpose

vfork() creates a child that shares the parent's address space -- including the stack -- while the calling thread is suspended until the child terminates or calls execve(2): fork()+exec(3) without copying page tables.

## Synopsis

```c
#include <unistd.h>
pid_t vfork(void);
```

## Arguments and behavior

vfork() is a special case of clone(2): equivalent to clone(2) with flags CLONE_VM | CLONE_VFORK | SIGCHLD (vfork.2, Linux notes). Until the child terminates (via _exit(2) or a fatal signal) or successfully execve's, it shares all parent memory, including the stack; POSIX marks the behavior undefined if the child modifies any data other than a pid_t holding vfork()'s return, returns from the calling function, or calls any other function before _exit(2)/exec(3) (vfork.2, Standard description). The child must not call exit(3) -- that would run the parent's exit handlers and flush the parent's stdio buffers -- but may call _exit(2). Signals sent to the parent arrive only after the child releases the memory. Other fork(2) attributes (file descriptors, signal dispositions, working directory) are inherited; only address-space treatment differs. BSD introduced vfork when fork copied the whole data space (vfork.2, Historic description); Linux copy-on-write fork made the win small, yet the call survived.

## Return value and errors

Same as fork(2): 0 in the child, the child's PID in the parent, -1 with errno on failure (vfork.2, Linux description -- details deferred to fork.2).

## Flags and constants

CLONE_VM 0x00000100 and CLONE_VFORK 0x00004000 (/usr/include/linux/sched.h); SIGCHLD 17 (/usr/include/asm-generic/signal.h).

## Security and notes

Why it survived (vfork.2, NOTES): performance-critical applications still want the advantage; it works on MMU-less systems where fork(2) cannot exist (the posix_spawn(3) rationale); and on memory-constrained systems it avoids committing memory for a large parent running a small child, which strict-overcommit fork(2) would require. Caveats: the child's memory changes are seen by the parent, and signal handlers in the vfork child can corrupt parent state; in a multithreaded parent the other threads keep running while the child shares their address space, so a concurrent setuid(2) drop plus mmap(2) of code is a documented privilege-escalation scenario (vfork.2, Caveats). pthread_atfork(3) handlers are not run by the NPTL vfork path (vfork.2, Linux notes). Wrapper notes: glibc's vfork is a real syscall wrapper; musl 1.2.5 instead implements vfork() as fork()/clone() -- "vfork syscall cannot be made from C code" (source-cache/musl-clone/musl/src/process/vfork.c), so the parent is not suspended under musl. Cross-reference: [fork](fork.md), [clone](clone.md), [execve](execve.md), [_exit](_exit.md).

## References

- https://man7.org/linux/man-pages/man2/vfork.2.html
- /home/z/my-project/source-cache/musl-clone/musl/src/process/vfork.c (musl wrapper source)
- /usr/include/linux/sched.h (CLONE_VM 0x00000100, CLONE_VFORK 0x00004000)
- /usr/include/asm-generic/signal.h (SIGCHLD 17)
- worklog Task 1-a (CLONE_VFORK story, arm64 numbering)
