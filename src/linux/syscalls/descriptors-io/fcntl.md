# fcntl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | fcntl 72 / 55 / 25 / 55; fcntl64 - / 221 / - / 221 (per-call table below) |
| Since (kernel) | fcntl 1.0; fcntl64 2.4 (32-bit large-file lock variant) |
| Man page | man2/fcntl.2 (fcntl64.2 is an .so alias of it) |
| glibc wrapper | fcntl() declared in <fcntl.h>, variadic third argument; host glibc 2.41 exports fcntl64@@GLIBC_2.28 (nm -D) -- on 64-bit off_t architectures fcntl64 is exported as an alias so old binaries bind; F_* command constants in bits/fcntl-linux.h |
| Aliases covered | fcntl64 |
| Ledger ID | SC-fcntl, SC-fcntl64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| fcntl | 72 | 55 | 25 | 55 | 1.0 |
| fcntl64 | - | 221 | - | 221 | 2.4 |

fcntl64 is the i386/arm32 variant of the locking commands with 64-bit lock-offset fields (struct flock64); the kernel maps the F_GETLK/F_SETLK/F_SETLKW group onto the *64 forms when the caller is a 32-bit process with large-file support (man2/fcntl.2; ledger SC-fcntl64).

## Purpose

fcntl() is the multiplexer for descriptor-level operations: cmd selects one of several unrelated groups. The duplication group makes descriptors (F_DUPFD picks a number >= arg, unlike dup2's exact target; F_DUPFD_CLOEXEC adds close-on-exec atomically). The descriptor-flags group reads and writes FD_CLOEXEC (F_GETFD/F_SETFD) -- per-descriptor state, unlike the file status flags of F_GETFL/F_SETFL, which live on the shared open file description and can only partly be changed after open. The locking group places advisory byte-range locks: traditional process-associated locks (F_SETLK/F_SETLKW/F_GETLK with struct flock) and the Linux-only open file description locks (F_OFD_SETLK/F_OFD_SETLKW/F_OFD_GETLK, 3.15), whose association with the open file description fixes the process-associated model's close-releases-everything and threads-share-locks hazards. Remaining groups manage signal-driven I/O ownership, leases, dnotify, pipe capacity, memfd seals, and write-lifetime hints. Probe support for a new command at runtime by calling it and checking for EINVAL (man2/fcntl.2).

## Synopsis

```c
#include <fcntl.h>
int fcntl(int fd, int cmd, ... /* arg */);
```

## Arguments and behavior

cmd groups (values from /usr/include/x86_64-linux-gnu/bits/fcntl-linux.h, glibc 2.41; "since" from man2/fcntl.2):

| Command | Value | Since | arg and behavior |
|---|---|---|---|
| F_DUPFD | 0 | 1.0 | int: lowest free descriptor >= arg; EMFILE at the limit; EINVAL for arg < 0 or above the maximum |
| F_GETFD | 1 | 1.0 | void: return descriptor flags (arg ignored) |
| F_SETFD | 2 | 1.0 | int: set descriptor flags; only defined bit is FD_CLOEXEC |
| F_GETFL | 3 | 1.0 | void: return access mode + file status flags |
| F_SETFL | 4 | 1.0 | int: set status flags; on Linux only O_APPEND, O_ASYNC, O_DIRECT, O_NOATIME, O_NONBLOCK can change; access mode and O_CREAT/O_EXCL/O_NOCTTY/O_TRUNC ignored; O_DSYNC/O_SYNC immutable after open |
| F_GETLK | 5 | 1.0 | struct flock *: test; fills l_type F_UNLCK if free, else one conflicting lock (l_pid -1 for an OFD conflict) |
| F_SETLK | 6 | 1.0 | struct flock *: acquire (F_RDLCK/F_WRLCK) or release (F_UNLCK); conflict fails EACCES or EAGAIN |
| F_SETLKW | 7 | 1.0 | struct flock *: as F_SETLK but block; kernel detects deadlocks and fails one waiter EDEADLK; interrupted waiting gives EINTR |
| F_SETOWN | 8 | 1.0 | int: process (positive) or process group (negative) to get SIGIO/SIGURG; needs O_ASYNC via F_SETFL; permission check uses the caller's saved credentials |
| F_GETOWN | 9 | 1.0 | void: return the SIGIO/SIGURG owner |
| F_SETSIG | 10 | 1.0 | int: signal to deliver instead of SIGIO; 0 restores SIGIO; nonzero with SA_SIGINFO delivers si_fd |
| F_GETSIG | 11 | 1.0 | void: return the configured signal (0 means SIGIO) |
| F_GETLK64 / F_SETLK64 / F_SETLKW64 | 12 / 13 / 14 | 2.4 | 64-bit lock-offset forms used on 32-bit ABIs |
| F_SETOWN_EX / F_GETOWN_EX | 15 / 16 | 2.6.32 | struct f_owner_ex *: target a thread, process, or process group (F_OWNER_TID/PID/PGRP) |
| F_OFD_GETLK / F_OFD_SETLK / F_OFD_SETLKW | 36 / 37 / 38 | 3.15 | struct flock *: open file description locks; l_pid must be 0 on input; no deadlock detection in the current implementation |
| F_SETLEASE | 1024 | 2.4 | int F_RDLCK/F_WRLCK/F_UNLCK: take or drop a read/write lease; unprivileged callers need matching file UID, otherwise CAP_LEASE |
| F_GETLEASE | 1025 | 2.4 | void: current lease type |
| F_NOTIFY | 1026 | 2.4 | int: DN_* directory-change notification, one-shot unless DN_MULTISHOT; superseded by inotify (2.6.13) |
| F_DUPFD_QUERY | 1027 | (header, newer than cached man page) | int: test whether two descriptors refer to the same open file description |
| F_DUPFD_CLOEXEC | 1030 | 2.6.24 | int: as F_DUPFD with close-on-exec set |
| F_SETPIPE_SZ / F_GETPIPE_SZ | 1031 / 1032 | 2.6.35 | int / void: pipe capacity in bytes; unprivileged range [page size, /proc/sys/fs/pipe-max-size], CAP_SYS_RESOURCE may exceed; EBUSY if shrinking below used space; kernel may round up to a power-of-two page multiple and returns the actual size |
| F_ADD_SEALS | 1033 | 3.17 | int: add seals (F_SEAL_* below) to the inode; fd must be writable; EPERM if F_SEAL_SEAL already set; EBUSY for F_SEAL_WRITE with a writable shared mapping |
| F_GET_SEALS | 1034 | 3.17 | void: current seal mask, 0 if none; EINVAL if the filesystem does not support sealing |
| F_GET_RW_HINT / F_SET_RW_HINT | 1035 / 1036 | 4.13 | uint64_t *: read/write lifetime hint on the inode (RWH_WRITE_LIFE_* values) |
| F_GET_FILE_RW_HINT / F_SET_FILE_RW_HINT | 1037 / 1038 | 4.13 | uint64_t *: same hint on the open file description |

F_DUPFD_QUERY and F_SEAL_EXEC (0x0020) are present in the installed glibc 2.41 headers but not described in the cached 2021 man2/fcntl.2; they are header-sourced here and their kernel since-versions are unverified in this session.

Seal values (bits/fcntl-linux.h, __USE_GNU): F_SEAL_SEAL 0x0001 (no further seals), F_SEAL_SHRINK 0x0002 (no truncate/shrink), F_SEAL_GROW 0x0004 (no growth), F_SEAL_WRITE 0x0008 (no content modification), F_SEAL_FUTURE_WRITE 0x0010 (5.1: no new writable mappings or writes, existing mappings keep write access). Seals exist only on memfd_create() files (MFD_ALLOW_SEALING); they are inode properties shared by all descriptors and can never be removed, only added.

## Return value and errors

Success value depends on cmd: a new descriptor (F_DUPFD*), the flags/owner/signal/lease/seal mask/pipe capacity for the F_GET* forms, and 0 for the rest. On error, -1 and errno: EACCES or EAGAIN (lock conflict), EAGAIN (mandatory lock with O_NONBLOCK, or file mapped by another process), EBADF (fd not open; F_SETLK/F_SETLKW with a lock type the open mode does not permit), EBUSY (F_SETPIPE_SZ below used space; F_ADD_SEALS with writable shared mapping), EDEADLK (F_SETLKW deadlock detected), EFAULT (lock outside address space), EINTR (F_SETLKW/F_OFD_SETLKW waiting; F_GETLK/F_SETLK/F_OFD_GETLK/F_OFD_SETLKW interrupted before completing, mostly on NFS), EINVAL (unknown cmd; unrecognized seal bit; sealing unsupported; F_DUPFD arg out of range; F_SETSIG invalid signal; F_OFD_* with nonzero l_pid), EMFILE (F_DUPFD limit), ENOLCK (lock table full or remote protocol failure), ENOTDIR (F_NOTIFY on a non-directory), EPERM (clearing O_APPEND on an append-only file; F_SETPIPE_SZ pipe-limit cases; F_ADD_SEALS on a read-only fd or with F_SEAL_SEAL set).

## Flags and constants

- FD_CLOEXEC is the only defined descriptor flag (F_GETFD/F_SETFD).
- F_SETFL's changeable set is fixed at O_APPEND, O_ASYNC, O_DIRECT, O_NOATIME, O_NONBLOCK (man2/fcntl.2); everything else needs open()/fcntl F_DUPFD dance or a new descriptor.
- struct flock: l_type (F_RDLCK 1 / F_WRLCK 2 / F_UNLCK 3), l_whence (SEEK_* of lseek.md), l_start, l_len (0 means to end of file, growing with it; negative l_len supported since 2.4.21/2.5.49), l_pid (result field for F_GETLK/F_OFD_GETLK).
- Locks and reads/writes: read locks need a read-open fd, write locks a write-open fd; locks are advisory by default; mandatory locking requires fs "mand" mount option plus set-GID-no-exec permission bits, is unreliable (man page warning), and was optional via CONFIG_MANDATORY_FILE_LOCKING since 4.5: the option is still present in fs/Kconfig at kernel tag v5.14 and absent at v5.15 and in master (tag-probed this session), so recent kernels dropped the feature.
- Lost locks: NFS lock loss makes later read()/write() fail EIO until the lock is removed or the fd closed (since 3.12 at least for NFSv4); Linux has no SIGLOST.

## Security and notes

- F_SETFD race: setting FD_CLOEXEC with F_SETFD while another thread runs fork()+execve() can leak the descriptor; use O_CLOEXEC at open()/dup3()/F_DUPFD_CLOEXEC time (man2/fcntl.2; open.md, dup.md).
- Process-associated lock hazards: closing any fd for a file drops all of that process's locks on it (a library function that opens and closes a file can silently drop your locks), and threads share the locks; F_OFD_* fixes both, and OFD locks conflict with traditional locks even within one process. Locks are not inherited across fork but survive execve; OFD locks are inherited across fork and released on the last close of the description. stdio buffering makes record locking over stdio(3) unreliable.
- F_SETOWN permission model: signal delivery is checked like kill(2) using credentials saved at F_SETOWN time; failure silently discards the signal. POSIX specifies F_GETOWN/F_SETOWN only for SIGURG on sockets; SIGIO is not POSIX-specified.
- Leases: a conflicting open()/truncate() blocks and signals the lease holder (SIGIO by default, F_SETSIG to change); after /proc/sys/fs/lease-break-time seconds the kernel breaks the lease forcibly.

## References

- man2/fcntl.2 in the cached man-pages tree (dated 2021-03-22); .so alias fcntl64.2.
- Constants: /usr/include/x86_64-linux-gnu/bits/fcntl-linux.h (commands, seals, hints); /usr/include/asm-generic/fcntl.h (lock types).
- [Syscalls ledger](../ledger.md) rows SC-fcntl, SC-fcntl64; siblings [dup](dup.md), [open](open.md), [readv](readv.md); [domain hub](overview.md).
