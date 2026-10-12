# clone(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | clone: 56 / 120 / 220 / 120; clone3: 435 / 435 / 435 / 435 |
| Since (kernel) | clone 1.0; clone3 5.3 (clone.2 VERSIONS); set_tid/set_tid_size 5.5; cgroup field 5.7 |
| Man page | man2/clone.2 (cached, dated 2021-03-22); clone3.2 is a .so alias of clone.2 (verified in cache); clone2/__clone2 documented inside clone.2 |
| glibc wrapper | clone(3) wrapper with (fn, stack, flags, arg, ...) signature; no wrapper for clone3 (clone.2 note; no clone3 symbol exported by installed glibc 2.41, checked with nm -D) |
| Aliases covered | clone2 / __clone2 (ia64), clone3 |
| Ledger ID | SC-clone, SC-clone2, SC-clone3 |

## Purpose

clone() creates a new ("child") process with fine-grained control over what execution context is shared with the caller: virtual address space, file-descriptor table, signal-handler table, filesystem info, I/O context, and namespaces. It is the kernel primitive behind fork(2), vfork(2), and pthread_create(3). clone3() (since 5.3) is a struct-based superset with room for more flag bits and an explicit stack size.

## Synopsis

```c
#define _GNU_SOURCE
#include <sched.h>
int clone(int (*fn)(void *), void *stack, int flags, void *arg,
          ... /* pid_t *parent_tid, void *tls, pid_t *child_tid */ );

#include <linux/sched.h>   /* struct clone_args */
long syscall(SYS_clone3, struct clone_args *cl_args, size_t size);
```

Raw system call on x86-64: `long clone(unsigned long flags, void *stack, int *parent_tid, int *child_tid, unsigned long tls);` on x86-32 and ARM the last two arguments are swapped: `(... int *parent_tid, unsigned long tls, int *child_tid)` (clone.2, C library/kernel differences). On ia64 the entry point is `__clone2(fn, stack_base, stack_size, ...)` - raw clone2 takes (flags, stack_base, stack_size, ...) like microblaze (clone.2).

## Arguments and behavior

With the glibc wrapper the child starts executing at fn(arg) and terminates when fn returns; the wrapper rejects fn == NULL or stack == NULL with EINVAL. The raw syscall behaves like fork(): execution continues from the call site in the child, and stack may be NULL (copy-on-write copy of the parent stack; then CLONE_VM must not be set). stack points to the topmost byte of the child stack area on downward-growing architectures; no stack size is conveyed by the old interface, while clone3 passes stack (lowest byte) and stack_size explicitly (clone.2).

clone_args fields (all u64, linux/sched.h; struct version sizes CLONE_ARGS_SIZE_VER0/VER1/VER2 = 64/80/88):

| Field | Meaning | Since |
|---|---|---|
| flags | flag bit mask (table below) | 5.3 |
| pidfd | int * where the child pidfd is stored (CLONE_PIDFD) | 5.3 |
| child_tid | pid_t * in child memory (CLONE_CHILD_SETTID/CLEARTID) | 5.3 |
| parent_tid | pid_t * in parent memory (CLONE_PARENT_SETTID) or pidfd target | 5.3 |
| exit_signal | termination signal to parent (low byte of flags in old clone) | 5.3 |
| stack / stack_size | child stack location and size | 5.3 |
| tls | new TLS (arch-specific; fs base on x86-64) | 5.3 |
| set_tid / set_tid_size | select PIDs per nested PID namespace | 5.5 |
| cgroup | fd of a version 2 cgroup (CLONE_INTO_CGROUP) | 5.7 |

size semantics (clone.2 plus kernel/fork.c copy_clone_args_from_user): size < 64 -> EINVAL; size > PAGE_SIZE -> E2BIG; the kernel copies its known 88 bytes and requires any user-supplied trailing bytes to be zero (copy_struct_from_user convention).

## Return value and errors

Success: the old clone returns the child's TID in the caller; clone3 returns 0 in the child and the child's PID in the parent. Main errors (clone.2):

| Error | Meaning |
|---|---|
| EAGAIN | Too many processes (see fork.2 limits) |
| EINVAL | Illegal flag combinations (SIGHAND without VM since 2.6.0; THREAD without SIGHAND since 2.5.35; FS with NEWNS or NEWUSER; NEWIPC with SYSVSEM; NEWPID/NEWUSER with THREAD/PARENT; CLEAR_SIGHAND with SIGHAND; PIDFD with DETACHED/PARENT_SETTID/THREAD; clone3 DETACHED; stack alignment, e.g. 16 on aarch64; glibc wrapper NULL fn/stack) |
| EPERM | NEWCGROUP/NEWIPC/NEWNET/NEWNS/NEWPID/NEWUTS without CAP_SYS_ADMIN; NEWUSER with unmapped euid/egid or in a chroot (3.9+); set_tid without CAP_SYS_ADMIN or, since 5.9, CAP_CHECKPOINT_RESTORE |
| ENOMEM | Task-structure or context allocation failed |
| ENOSPC | PID-namespace nesting (3.7+), user-namespace nesting or /proc/sys/user limits (4.9+, EUSERS 3.11-4.8) |
| EEXIST | clone3 only: a PID in set_tid already exists |
| EBUSY / EOPNOTSUPP | clone3 only: CLONE_INTO_CGROUP fd is a v2 cgroup with a domain controller enabled / in domain-invalid state |
| ERESTARTNOINTR | Since 2.6.17, visible only during a trace |

## Flags and constants

Values from /usr/include/linux/sched.h; "Since" from clone.2 unless noted:

| Flag | Value | Effect | Since |
|---|---|---|---|
| CLONE_NEWTIME | 0x00000080 | new time namespace (in UAPI header; not in the clone.2 flag list) | header only |
| CLONE_VM | 0x00000100 | share address space | 2.0 |
| CLONE_FS | 0x00000200 | share fs info (root, cwd, umask) | 2.0 |
| CLONE_FILES | 0x00000400 | share fd table (unshared by execve) | 2.0 |
| CLONE_SIGHAND | 0x00000800 | share handler table (requires CLONE_VM) | 2.0 |
| CLONE_PIDFD | 0x00001000 | allocate child pidfd (parent_tid for clone; cl_args.pidfd for clone3) | 5.2 |
| CLONE_PTRACE | 0x00002000 | trace child if caller traced | 2.2 |
| CLONE_VFORK | 0x00004000 | suspend caller until child execve/_exit | 2.2 |
| CLONE_PARENT | 0x00008000 | child's parent is the caller's parent | 2.3.12 |
| CLONE_THREAD | 0x00010000 | same thread group (requires CLONE_SIGHAND) | 2.4.0 |
| CLONE_NEWNS | 0x00020000 | new mount namespace | 2.4.19 |
| CLONE_SYSVSEM | 0x00040000 | share System V semadj list | 2.5.10 |
| CLONE_SETTLS | 0x00080000 | set child TLS (arch-specific) | 2.5.32 |
| CLONE_PARENT_SETTID | 0x00100000 | store child TID in parent memory | 2.5.49 |
| CLONE_CHILD_CLEARTID | 0x00200000 | zero child_tid and futex-wake on child exit | 2.5.49 |
| CLONE_DETACHED | 0x00400000 | historical; no effect since 2.6.0, error with PIDFD (clone) and in clone3 | 2.5.32 era |
| CLONE_UNTRACED | 0x00800000 | tracer cannot force CLONE_PTRACE | 2.5.46 |
| CLONE_CHILD_SETTID | 0x01000000 | store child TID in child memory | 2.5.49 |
| CLONE_NEWCGROUP | 0x02000000 | new cgroup namespace | 4.6 |
| CLONE_NEWUTS | 0x04000000 | new UTS namespace | 2.6.19 |
| CLONE_NEWIPC | 0x08000000 | new IPC namespace | 2.6.19 |
| CLONE_NEWUSER | 0x10000000 | new user namespace | 2.6.23 (current semantics 3.5) |
| CLONE_NEWPID | 0x20000000 | new PID namespace | 2.6.24 |
| CLONE_NEWNET | 0x40000000 | new network namespace | 2.6.24 |
| CLONE_IO | 0x80000000 | share I/O context (no-op without CONFIG_BLOCK) | 2.6.25 |
| CLONE_CLEAR_SIGHAND | 0x100000000ULL | reset handled signals to SIG_DFL in child | 5.5 |
| CLONE_INTO_CGROUP | 0x200000000ULL | spawn child into a cgroup v2 (cl_args.cgroup fd) | 5.7 |

The low byte of clone's flags is the child termination signal (fork = SIGCHLD only); clone3 moves it to exit_signal, and kernel/fork.c (clone3_args_valid) rejects exit_signal values with bits outside 0xff and rejects the CLONE_DETACHED and legacy low-byte patterns.

## Security and notes

All CLONE_NEW* namespace flags except CLONE_NEWUSER need CAP_SYS_ADMIN; CLONE_NEWUSER has needed no privileges since 3.8 but cannot combine with CLONE_FS, CLONE_THREAD, or CLONE_PARENT. CLONE_PIDFD cannot combine with CLONE_THREAD, so a pidfd always names a thread-group leader. pthread_atfork(3) handlers do not run across clone calls. The glibc wrapper writes into the child stack buffer before the syscall, so do not pass the parent's own stack buffer (clone.2, NOTES). Thread libraries pass (CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND | CLONE_THREAD | CLONE_SYSVSEM | CLONE_SETTLS | CLONE_PARENT_SETTID | CLONE_CHILD_CLEARTID) plus SIGCHLD-free exit signal 0; see worklog 1-a (musl pthread_create.c) for the exact thread flag set. Cross-reference: [fork](fork.md), [pidfd_open](pidfd_open.md), [set_tid_address](set_tid_address.md), [wait4](wait4.md).

## References

- https://man7.org/linux/man-pages/man2/clone.2.html (clone3.2 is its .so alias)
- kernel/fork.c (clone3, copy_clone_args_from_user, clone3_args_valid; fetched from torvalds master; source file named in worklog 1-a)
- /usr/include/linux/sched.h (CLONE_* values, clone_args sizes)
