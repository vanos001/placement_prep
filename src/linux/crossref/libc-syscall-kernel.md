# libc -> syscall -> kernel subsystem (XR-001..XR-014)

## Overview

This map answers one question per libc entry point: **what actually happens below
libc?** One libc call may issue zero syscalls (pure userspace work), one thin
wrapped syscall, or a version-dependent composite; and one syscall may serve
dozens of libc functions. The rows below are the 14 rows `XR-001..XR-014` of the
[coverage ledger](./ledger.md) (statuses there are authoritative: all 14
documented; XR-012/XR-013 upgraded in the 7-d pass). Each row's table cites every libc function by its `GLIBC-<name>`
row in the [glibc ledger](../libc/ledger-glibc.md), every syscall by its
`SC-<name>` row in the [syscall ledger](../syscalls/ledger.md), and names kernel
subsystem file paths only where the syscall chapters established them.

### Reading rules

- **Typed arrows.** `wraps` = thin libc wrapper over the syscall; `implements` =
  work done in userspace with no dedicated syscall; `consumes` = libc reads the
  results of an interface; `services` = the kernel side serving the call;
  `gated-by` = a config, capability, or version gate. See the
  [method page](../interface-encyclopedia.md) for the full vocabulary.
- **Non-1:1 is the point.** Stdio buffering (many `printf` calls, zero syscalls
  until flush), the `malloc` arena model over `brk`/`mmap`, `posix_spawn` as a
  `clone`+`execve` composite, NSS resolution that touches no dedicated syscall,
  and the vDSO serving time without entering the kernel are rows here, not
  footnotes.
- **musl note policy.** Where glibc and musl 1.2.5 differ, the row says which
  implementation a fact comes from (musl facts cite the [musl catalog](../libc/musl/overview.md)
  and its source paths); unverified deltas are marked, not asserted.
- **Wrapper convention.** Syscall wrappers translate the kernel's negative-errno
  return into `-1` plus `errno` per `intro(2)`, do not retry on `EINTR`, and pass
  short counts through (three recurring deltas, XR-002).
- **Citation discipline.** Numbers in parentheses are x86_64 numbers from the
  [syscall ledger](../syscalls/ledger.md); every `GLIBC-`/`SC-` id is a real
  ledger row. Cross-links go only to pages verified to exist in the current
  tree -- per-function syscall pages (`syscalls/<domain>/<call>.md`), per-class
  sysfs pages, and per-function glibc pages -- because the wave-2 per-domain
  chapters this map was first written against have since been split up.
- **Ledger resolution.** Row ids and Map text follow the ledger's libc section
  exactly (`printf family -> write/writev -> vfs_write` ... `dynamic loader ->
  mmap/open/read -> ld.so`); statuses are the ledger's (XR-012, XR-013
  upgraded to documented in the 7-d pass, the rest documented). Agent status
  reports proposed the statuses; the ledger merged them, and this page carries
  the same split.
- **Architecture honesty.** The tables quote x86_64 numbers as representative;
  the ledger carries the full x64 / i386 / g64 (asm-generic) / arm32 columns,
  and several rows below lean on the differences (no `fork`/`vfork`/`time`
  g64 slots, no `stat` g64 slot, `socketcall` i386-only). Nothing here claims
  universal-arch availability.

---

### XR-001 -- printf family -> write/writev -> vfs_write (stdio buffering path)

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-printf`, `GLIBC-fprintf`, `GLIBC-fwrite`, `GLIBC-fflush`, `GLIBC-fclose` (stdio.h) | `SC-write` (x64 1), `SC-writev` (x64 20), `SC-openat` (x64 257) on first use, `SC-close` (x64 3) | `fs/read_write.c` (`vfs_write`, vector path), `fs/open.c` (`do_sys_openat2`) | `GLIBC-printf` **implements** stdio buffering; at the flush point **wraps** `SC-write`/`SC-writev`; the write path is **serviced** by `vfs_write`; buffer sizing is **gated-by** `st_blksize` |

The glibc stdio chapter documents a **flush-point
`write(2)`**: `printf`-family calls only format into the `FILE` buffer, and the
syscall happens when the buffer fills, at explicit `fflush`, or at `fclose` --
many library calls, zero syscalls in between. The musl catalog documents its
`vfprintf` flush path as issuing `writev`, so the overview's "printf issues
writev" is exactly true of musl; both attributions stand. The buffer size is
sized from `st_blksize` observed on the target via `fstat`, and the underlying
`FILE` is opened with `openat` when a stream is first used. Buffering mode is a
property of the stream, not the call: full buffering for files, **line
buffering for terminals**, and stderr is not fully buffered -- selectable with
the `setvbuf` family. Streams are also flushed at exit via the implicit flush
list, and each stream carries a recursive per-FILE lock (`flockfile` family)
so buffered writes stay coherent across threads. Syscall-side detail:
[write](../syscalls/descriptors-io/write.md), [readv/writev](../syscalls/descriptors-io/readv.md);
libc side: [printf family](../libc/glibc/stdio/printf-printf-fprintf-dprintf-sprintf-snprintf-asprintf.md),
[fflush](../libc/glibc/stdio/fflush.md), [setvbuf](../libc/glibc/stdio/setvbuf-setbuf-setbuffer-setlinebuf.md),
[flockfile](../libc/glibc/stdio/flockfile-ftrylockfile-funlockfile.md).

### XR-002 -- fopen/fread family -> open/read -> VFS/page cache

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-fopen`, `GLIBC-fread`, `GLIBC-fwrite`, `GLIBC-fclose`, `GLIBC-lseek` (stdio bridge); `GLIBC-open`, `GLIBC-read`, `GLIBC-write` (low-level) | `SC-open` (x64 2), `SC-openat` (257), `SC-read` (0), `SC-write` (1), `SC-lseek` (8), `SC-close` (3), `SC-pread64` (17), `SC-pwrite64` (18), `SC-readv` (19), `SC-writev` (20) | `fs/open.c` (`do_sys_openat2`), `fs/read_write.c` (`vfs_read`/`vfs_write`, `ksys_pread64`, vector paths), `fs/file.c` (`close_fd`), the page cache | `GLIBC-fread` **wraps** `SC-read`; VFS **services** the call; data is **consumed** from the page cache; `pread64` positioning is **gated-by** no shared offset |

These are the honest thin wrappers: 1:1 mapping with the three wrapper deltas
only -- negative errno becomes `-1`/`errno` (per `intro(2)`), `EINTR` is **not**
retried (the glibc manual's Interrupted Primitives section documents that glibc
primitives fail on `EINTR` rather than looping), and short counts are passed
through, so `fread` can return fewer items and requires `feof`/`ferror` to
distinguish EOF from error. The VFS/page-cache side of `read`/`write` is
documented in the kernel's page-cache page; underneath the fd sits the
fd-table -> open-file-description -> inode layering that the descriptors
chapter's overview diagrams, and the descriptor lifecycle is where the
`O_CLOEXEC` discipline (set at creation, not patched in later) pays off for
the stdio bridges (`fdopen`, `popen`). Per-call pages:
[open](../syscalls/descriptors-io/open.md), [read](../syscalls/descriptors-io/read.md),
[pread64](../syscalls/descriptors-io/pread.md), [dup](../syscalls/descriptors-io/dup.md);
libc-side: [open-close](../libc/glibc/stdio/open-close.md),
[read-write](../libc/glibc/stdio/read-write.md),
[lseek](../libc/glibc/stdio/lseek.md),
[readv/pread family](../libc/glibc/stdio/readv-writev-pread-pwrite.md),
[fopen group](../libc/glibc/stdio/fopen-fdopen-freopen-fclose.md).

### XR-003 -- malloc -> brk/mmap -> mm allocator path (arena model, non-1:1)

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-malloc`, `GLIBC-calloc`, `GLIBC-realloc`, `GLIBC-free` | `SC-brk` (x64 12), `SC-mmap` (9), `SC-munmap` (11), `SC-mprotect` (10), `SC-madvise` (28) | `mm/mmap.c` (mmap/munmap), `mm/mprotect.c`, `mm/madvise.c` | allocator **implements** arena logic in userspace; arena growth/trim **wraps** `SC-brk`/`SC-mmap`/`SC-munmap`; the VM subsystem **services** the calls; musl hardening is **gated-by** `mprotect` |

Non-1:1 exemplar: one `malloc` call usually issues **zero** syscalls because the
request is served from arena free lists. The glibc `ptmalloc` split: the main
arena grows via `brk`, additional arenas and large blocks come from `mmap`,
`munmap` returns large blocks directly, and trimming shrinks the heap. musl
1.2.5 `mallocng` instead: `mmap` slots for allocations, `brk` for metadata
areas, `mprotect`-based hardening, and `MADV_FREE` dropped in musl 1.2.4. Two wrapper-level details from the memory chapter: the raw `SC-brk`
returns the new break on success while the glibc `brk` wrapper normalizes to
0/-1, and `sbrk` is libc-only -- no syscall carries that name. Non-1:1 cuts
both ways here: many allocations, zero syscalls; one `munmap`, potentially
thousands of freed allocations. The memory chapter names XR-003 for this
split; per-call pages:
[brk](../syscalls/memory/brk.md), [mmap](../syscalls/memory/mmap.md),
[munmap](../syscalls/memory/munmap.md), [madvise](../syscalls/memory/madvise.md),
[mprotect](../syscalls/memory/mprotect.md);
libc-side: [malloc group](../libc/glibc/strings/malloc-calloc-realloc-free.md),
[aligned allocation](../libc/glibc/strings/aligned_alloc-posix_memalign-memalign-valloc.md).

### XR-004 -- posix_spawn -> clone+execve composite (action list, non-1:1)

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-posix_spawn`, `GLIBC-posix_spawnp`, `GLIBC-fork`, `GLIBC-vfork`, `GLIBC-system`, exec family (`GLIBC-execv`, `GLIBC-execl`, `GLIBC-execvp`) | `SC-clone` (x64 56), `SC-execve` (59), `SC-execveat` (322), `SC-wait4` (61), `SC-waitid` (247), `SC-exit_group` (231), `SC-fork` (57; no g64 slot), `SC-vfork` (58; no g64 slot) | `kernel/fork.c` (creation), `fs/exec.c` (image swap), `kernel/exit.c` (reaping) | `GLIBC-posix_spawn` **wraps** the `clone`+`execve` composite; file_actions **implement** child-side housekeeping; `fork` **wraps** `SC-clone(SIGCHLD)`; parent notify is **gated-by** the exit status |

`posix_spawn` is a composite, not a wrapper: since glibc 2.24 the child is
created with `clone(CLONE_VM|CLONE_VFORK)` (no page-table copy, parent suspended
until exec, no `pthread_atfork` handlers), then `execve`/`execveat` swaps the
image; if any housekeeping step or the exec fails in the child, the child exits
with status **127**, which the caller only discovers through
`waitpid`/`WEXITSTATUS`. `fork` has been a `clone(SIGCHLD)` wrapper since glibc
2.3.3; `vfork` maps to the flag triple; and `system` wraps child creation in
the documented signal dance -- SIGINT/SIGQUIT ignored and SIGCHLD blocked
while the child runs, dispositions restored afterwards -- so an interactive
child shell cannot kill the program that invoked it. On arm64 there are no `fork`/`vfork` numbers at all (asm-generic
table) -- only `clone`. Symbol-version notes from the process chapter: glibc
2.34 merged libpthread, so `posix_spawn`-family symbols carry `GLIBC_2.15`
(default) with `GLIBC_2.2.5` compat aliases, `execvpe` is 2.11, and `_Fork`
(2.34) is the fork variant that deliberately skips atfork handlers. musl
delta: musl implements `vfork` in C as fork/clone (its source notes a raw
vfork syscall cannot be made from C code), and musl's `fork` locks every
internal lock across the child while `_Fork` does not. Pages:
[posix_spawn](../libc/glibc/process/posix-spawn-and-posix-spawnp.md),
[fork](../libc/glibc/process/fork.md), [vfork](../libc/glibc/process/vfork.md),
[system](../libc/glibc/process/system.md),
[wait family](../libc/glibc/process/wait-and-waitpid.md); syscall side:
[clone](../syscalls/process/clone.md), [execve](../syscalls/process/execve.md),
[execveat](../syscalls/process/execveat.md), [wait4](../syscalls/process/wait4.md),
[_exit](../syscalls/process/_exit.md).

### XR-005 -- pthread_create -> clone(CLONE_VM|CLONE_THREAD) -> scheduler

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-pthread_create` | `SC-clone` (56), `SC-set_tid_address` (218), `SC-set_robust_list` (273), `SC-rseq` (334; ledger row source-limited), `SC-gettid` (186) | `kernel/fork.c` (thread creation), `kernel/rseq.c`; the new task then belongs to the scheduler | `GLIBC-pthread_create` **wraps** `SC-clone` with the thread flag set; stack + TLS setup is **implemented** in userspace; join wake **consumes** the child `tid` address registration; rseq registration is **gated-by** glibc 2.35 |

Thread creation goes through the same `clone` entry as processes, differing
only in the shared-context flag set (`CLONE_VM|CLONE_THREAD|CLONE_SIGHAND` and
friends); the musl catalog documents musl's exact flag set from
`src/thread/pthread_create.c` verbatim. The new thread registers its child
`tid` address (`set_tid_address`) so join can wake the waiter, registers the
robust-futex list (`set_robust_list`) for crash handover, and -- since glibc
2.35 -- the loader auto-registers rseq (`SC-rseq`; that ledger row itself is
source-limited because no rseq man page exists in any consulted source).
Flag-level detail from the thread chapters: the shared-context bits are plain
flag values on the same syscall (`CLONE_VM` = 0x00000100,
`CLONE_VFORK` = 0x00004000), and on x86-64 the new thread's TLS is pointed at
its block via `arch_prctl(ARCH_SET_FS)` (musl does this in
`__set_thread_area`); `SC-gettid` is how the runtime learns the TID it just
became. Pages:
[pthread_create](../libc/glibc/process/pthread-create.md),
[clone](../syscalls/process/clone.md), [set_tid_address](../syscalls/process/set_tid_address.md),
[set_robust_list](../syscalls/process/get_robust_list.md),
[getpid/gettid](../syscalls/process/getpid.md).

### XR-006 -- pthread_mutex_lock -> futex -> futex wait queue

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-pthread_mutex_lock` (mutex family row) | `SC-futex` (x64 202) | `kernel/futex/*` (wait queues) | uncontended path **implements** the acquire with a userspace atomic; `SC-futex` is **wrapped** only under contention; the kernel futex code **services** blocking/waking; robust and PI variants are **gated-by** mutex attributes |

The textbook non-1:1: an uncontended `pthread_mutex_lock` never enters the
kernel -- the acquire is an atomic instruction on a userspace word. Only when a
thread actually blocks does the library call `SC-futex` (`FUTEX_WAIT`) and park
on the kernel's futex wait queue; unlock issues `FUTEX_WAKE` for a waiter. The
robust-mutex story hands the lock state over via the `set_robust_list` list
(from XR-005) with `FUTEX_OWNER_DIED` (0x40000000) marking dead-owner locks so
the next locker can clean up. Priority-inheriting mutexes route through the
same syscall with PI operations, serviced by the kernel's PI-futex machinery --
the split between wait-queue mechanics and PI plumbing has its own kernel-side
page. musl delta worth knowing: musl returns `ENOTSUP` for
`PTHREAD_PRIO_PROTECT` mutexattr attempts (catalog-verified), so
PI-dependent code is a glibc-only assumption at the mutex layer. Pages:
[pthread_mutex family](../libc/glibc/process/pthread-mutex-init-lock-unlock-trylock-timedlock-destroy-mutexattr.md),
[futex](../syscalls/process/futex.md), kernel side: [futex](../kernel/sync/futex.md).

### XR-007 -- readdir(3) -> getdents64 -> fs/readdir.c

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-readdir`, `GLIBC-opendir` | `SC-getdents64` (x64 217), `SC-getdents` (78; legacy, no g64 slot), `SC-openat` (dirfd), `SC-close` | `fs/readdir.c` | `GLIBC-readdir` **implements** dirent buffering over `SC-getdents64`; the directory fd **wraps** `SC-openat`; `fs/readdir.c` **services** the enumeration |

There was **no public wrapper** for `getdents64` until glibc 2.30 (the symbol is
now exported, `getdents64@@GLIBC_2.30` on the checked glibc), and none **ever**
for legacy `getdents`. `readdir(3)` therefore implements its own buffered loop:
one `getdents64` fetches a block of dirents that several `readdir` calls consume,
and the record shape is length-driven -- each `linux_dirent64` carries
`d_reclen`, so the buffer walk never assumes fixed-size entries. musl
delta: since musl 1.2.4 `getdents64` is a macro delta in the header layer
(catalog-verified). The arm64/asm-generic story pairs with `SC-newfstatat` (g64
79) as the carrier for stat-style lookups, since plain `stat` has no g64 slot.
This row is the encyclopedia's canonical "libc implements, kernel services"
case: the syscall is documented, the wrapper arrived late, and the POSIX API
was never a wrapper at all. Pages:
[getdents64](../syscalls/descriptors-io/getdents64.md),
[readdir context](../syscalls/descriptors-io/readdir.md).

### XR-008 -- exec family -> execve/execveat -> fs/exec.c (binfmt)

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-execve`, `GLIBC-execv`, `GLIBC-execl`, `GLIBC-execvp` (grouped rows) | `SC-execve` (x64 59), `SC-execveat` (322) | `fs/exec.c` (binfmt dispatch) | `execl`/`execv` **implement** argv-array construction over `SC-execve`; `execvp` **implements** PATH search; `fexecve` **wraps** `SC-execveat`; binfmt handlers **service** the image load |

`execve` replaces the process image in place -- same PID, same fds (modulo
`FD_CLOEXEC`), new program -- and the `execl`/`execv`/`execvp` family is libc
convenience over it (array building, `PATH` search), while `fexecve` goes
through `execveat`. Version-honest flags: `execveat` takes `AT_EMPTY_PATH` and
`AT_SYMLINK_NOFOLLOW` only -- `AT_SYMLINK_FOLLOW` does not exist (correction
recorded in the process chapter). `execveat` gained its glibc wrapper at 2.34
(`execveat@@GLIBC_2.34` on the checked glibc). The kernel side is `fs/exec.c`,
which dispatches to the binfmt handlers that decide whether the file is an
elf image, a script, or something else, and the exec leg of XR-004's
`posix_spawn` composite lands here too. The whole exec family returns only on
failure; a successful exec ends in the new program's `main` with the exit leg
(`SC-exit_group`) covered by XR-004's reaping chain. Pages:
[exec family](../libc/glibc/process/exec-family-execl-execlp-execle-execv-execvp-execvpe-execve-fexecve.md),
[execve](../syscalls/process/execve.md), [execveat](../syscalls/process/execveat.md).

### XR-009 -- signal functions -> rt_sig* family -> kernel/signal.c

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-sigaction`, `GLIBC-kill`, `GLIBC-raise` | `SC-rt_sigaction` (x64 13), `SC-rt_sigprocmask` (14), `SC-rt_sigreturn` (15), `SC-kill` (62), `SC-tgkill` (234), `SC-pause` (34), `SC-sigaltstack` (131), `SC-rt_sigtimedwait` (128) | `kernel/signal.c` (queueing and delivery) | libc wrappers **wrap** the `rt_sig*` calls; `raise` **wraps** `kill -> tgkill` (glibc 2.3.3); `sigwait` **implements** over `SC-rt_sigtimedwait`; `SC-rt_sigreturn` never returns |

The POSIX signal API maps onto the `rt_sig*` family; the restorer trampoline is
internal (the `SA_RESTORER` flag is kernel-internal and not exposed in the
installed headers), and glibc installs it for you. `raise()` has gone through
`tgkill` (target a specific thread) since glibc 2.3.3. `sigwait` is implemented
over `SC-rt_sigtimedwait` (the wait-for-accept-and-clear pattern), and the
`sigwait` trio plus the psignal/strsignal utilities share the same delivery
machinery. A returning handler ends in the vDSO-provided trampoline whose
`rt_sigreturn` syscall never returns to the trampoline -- control resumes at
the interrupted site. Note the layering: dispositions and masks are
per-process state served by `kernel/signal.c`; every wrapper here is thin,
with none of the buffering or compositing seen in the stdio rows. The
delivery pipeline is documented per call:
[rt_sigaction](../syscalls/signals-time/rt_sigaction.md),
[rt_sigprocmask](../syscalls/signals-time/rt_sigprocmask.md),
[kill](../syscalls/signals-time/kill.md), [tgkill](../syscalls/signals-time/tgkill.md),
[rt_sigreturn](../syscalls/signals-time/sigreturn.md), and
[sigaltstack](../syscalls/signals-time/sigaltstack.md); libc-side entry points
are grouped under `GLIBC-kill`, `GLIBC-raise`, `GLIBC-sigaction` in the
[glibc ledger](../libc/ledger-glibc.md).

### XR-010 -- clock_gettime/gettimeofday -> vDSO/clock_gettime64 -> timekeeping

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-clock_gettime`, `GLIBC-gettimeofday`, `GLIBC-nanosleep` | `SC-clock_gettime` (x64 228), `SC-gettimeofday` (96), `SC-clock_nanosleep` (230), `SC-nanosleep` (35), `SC-timer_create` (222), `SC-time` (201; no g64 slot) | `kernel/time/` + `posix-timers.c` (timekeeping) | the vDSO path **implements** time reads with no syscall; the syscall is the **wrapped** fallback; timekeeping **services** both; seccomp policies are **gated-by** vDSO invisibility |

Time is the other flagship non-1:1: `clock_gettime`/`gettimeofday` normally
execute in the vDSO (the vvar page mapped read-only into every process) and
**never enter the kernel**, which also makes them invisible to seccomp filters;
the syscall is the fallback when the vDSO cannot serve a clock. The libc
`time_t` story splits by architecture: `SC-time` has no asm-generic slot at all,
the 32-bit arches gained the `_time64` twins in kernel 5.1 (XR-205), and the
timer family (`timer_create` and friends) stays syscall-wrapped. The
clockid space (`CLOCK_REALTIME`, `CLOCK_MONOTONIC`, and the rest) is tabled on
the clock_getres page, and the interval-timer cousins (`setitimer`/`getitimer`)
ride the same timekeeping layer. Pages:
[clock_gettime/clock_getres](../syscalls/signals-time/clock_getres.md),
[gettimeofday](../syscalls/signals-time/gettimeofday.md),
[clock_nanosleep](../syscalls/signals-time/clock_nanosleep.md),
[timer_create](../syscalls/signals-time/timer_create.md),
[setitimer](../syscalls/signals-time/setitimer.md); kernel side:
[vDSO and vsyscall](../kernel/core/vdso-vsyscall.md).

### XR-011 -- socket/connect/send -> socket family -> net/socket.c

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-socket`, `GLIBC-connect`, `GLIBC-getaddrinfo` | `SC-socket` (x64 41), `SC-connect` (42), `SC-sendto` (44), `SC-sendmsg` (46), `SC-recvfrom` (45), `SC-recvmsg` (47), `SC-socketcall` (i386 102 only), `SC-gethostname` (no numbers on any tabulated arch) | `net/socket.c` | socket functions **wrap** their calls 1:1; `getaddrinfo` **implements** resolution in userspace (NSS chain, DNS over `SC-socket`/`SC-sendto`/`SC-recvfrom`); `SC-socketcall` is a **gated-by**-i386 multiplexer |

The socket family is the clean 1:1 case -- except for the two deliberate
non-1:1 rows inside it. `getaddrinfo` has **no syscall of its own**: it is a
userspace resolver (NSS chain in glibc: `files`, `dns`, ...; musl has a built-in
resolver with no nsswitch) whose DNS traffic rides ordinary
`socket`/`sendto`/`recvfrom` calls. And on i386 the whole family historically
multiplexed through `socketcall` (`SYS_*` 1..20). Ancillary detail sourced in
the net-ipc chapter: control messages (`SCM_RIGHTS` = 0x01,
`SCM_CREDENTIALS` = 0x02) ride the same `sendmsg`/`recvmsg` pair, and
`accept4`/`SOCK_CLOEXEC` exist so the create-and-accept path can be
race-free without a post-`accept` `fcntl` (musl even retries `socket` with
`SOCK_CLOEXEC` when the type bits are rejected). Precision note carried from
the syscall chapter: `gethostname(2)` states glibc never employs a
`gethostname` syscall -- it is a library function over `uname(2)` -- and the
*syscall* exists only on Alpha and SPARC/SPARC64 per `syscalls(2)`. Pages:
[socket](../syscalls/net-ipc/socket.md), [connect](../syscalls/net-ipc/connect.md),
[sendto](../syscalls/net-ipc/sendto.md), [sendmsg](../syscalls/net-ipc/sendmsg.md),
[socketcall](../syscalls/net-ipc/socketcall.md), [gethostname](../syscalls/net-ipc/gethostname.md);
libc side: [socket family](../libc/glibc/net/socket-connect-bind-listen-accept.md),
[getaddrinfo](../libc/glibc/net/getaddrinfo-getnameinfo.md).

### XR-012 -- getpwnam/NSS -> no direct syscall -> /etc/passwd + NSS modules (musl: built-in)

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-getpwnam`, `GLIBC-getpwuid` | no dedicated syscall; generic `SC-openat` (257), `SC-read` (0), `SC-socket` (41), `SC-connect` (42) under the hood | none directly -- the kernel only serves generic file and socket work | `GLIBC-getpwnam` **implements** the whole lookup in userspace; file parsing **consumes** `SC-openat`+`SC-read`; nscd transport **consumes** `SC-socket`+`SC-connect`; module loading is **gated-by** `/etc/nsswitch.conf` |

The glibc side is fully sourced by the NSS manual nodes (manual `nss.texi`):
`getpwnam` dispatch reads `/etc/nsswitch.conf`, one database per line, where a
line lists services with optional action expressions `[(!?status=action)+]`
(`status` in `success|notfound|unavail|tryagain`, `action` in
`return|continue|merge`; defaults: `success` -> `return`, the rest ->
`continue`). Each service name names a module `libnss_<service>.so.2` whose
functions are found by symbol name -- `_nss_<service>_<function>`, e.g.
`_nss_files_gethostbyname_r` -- with no jump table (the manual is explicit
that the functions are identified by their names); modules only carry the
reentrant variants, a missing function is treated as `unavail`, and the
module functions return `enum nss_status` (`SUCCESS` = 1, `NOTFOUND` = 0,
`UNAVAIL` = -1, `TRYAGAIN` = -2, plus the internal `NSS_STATUS_RETURN`) with
`*errnop` carrying `EAGAIN`/`ERANGE`. The `files` module parses
`/etc/passwd` with ordinary file reads, later modules are `dlopen`ed shared
objects, and the nscd path speaks a socket protocol to the daemon -- so the
kernel sees only XR-002's file path and XR-011's socket path, with no
user-database syscall anywhere.

Host reality on the reference glibc 2.41 backs the split:
`/etc/nsswitch.conf` reads `passwd: files`, `group: files`, `shadow: files`,
`hosts: files dns` and friends (the `db files` style for protocols/services,
`netgroup: nis`), and the files service has been compiled into libc itself:
`libc.so.6` exports `_nss_files_getpwnam_r`, `_nss_files_getpwuid_r` and
`_nss_files_getpwent_r` as `GLIBC_PRIVATE` symbols, while the on-disk
`libnss_files.so.2` (14,336 bytes) is a stub with only five dynamic symbols.
The `libnss_<service>.so.2` loading mechanism remains the extension path for
third-party modules.

The musl column is now sourced from the musl tree itself: `getpwnam` routes
to `__getpw_a` in `src/passwd/getpw_a.c`, which opens `/etc/passwd`
(`fopen("/etc/passwd", "rbe")`) and scans it with `__getpwent_a` comparing
`pw_name`/`pw_uid`; on a miss it queries a running nscd via `__nscd_query`
(`src/passwd/nscd_query.c`, requests `GETPWBYNAME`/`GETPWBYUID`). There is
no nsswitch file, no action expressions, and no `dlopen`ed modules anywhere
in the tree (grep: zero hits; `src/network/` carries the same philosophy as
a hardcoded backend order -- `lookup_name.c` tries `name_from_null` ->
`name_from_numeric` -> `name_from_hosts` -> `name_from_dns_search`, i.e.
`/etc/hosts` first, then DNS). The consequence is practical: a musl-built
program and a glibc-built one resolve the same name through different
userspace machinery, and both sides are now cited. Page:
[getpwnam family](../libc/glibc/net/getpwnam-getpwuid-family.md).

### XR-013 -- ioctl -> fs/ioctl dispatch -> driver unlocked_ioctl (tty: tty_ioctl chain)

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-ioctl`, `GLIBC-tcgetattr`, `GLIBC-tcsetattr` | `SC-ioctl` (x64 16) -- e.g. `TCGETS`/`TCSETS` for the terminal pair | `fs/ioctl.c`: `SYSCALL_DEFINE3` -> `security_file_ioctl` -> `do_vfs_ioctl` generic switch -> on `-ENOIOCTLCMD` -> `vfs_ioctl` -> `filp->f_op->unlocked_ioctl`; tty case: `drivers/tty/tty_io.c` registers `.unlocked_ioctl = tty_ioctl` (`tty_fops`/`console_fops`; hung-up: `hung_up_tty_ioctl`) and `tty_ioctl` falls through `tty_jobctrl_ioctl` -> `tty->ops->ioctl` -> `ld->ops->ioctl`, `-ENOIOCTLCMD` -> `-ENOTTY` | `GLIBC-tcgetattr`/`tcsetattr` **wrap** `SC-ioctl(TCGETS/TCSETS)`; the generic switch **services** file-generic commands; driver `.unlocked_ioctl` **services** the rest |

`ioctl` is one syscall serving thousands of commands; the syscall chapter
documents the dispatch chain above and the generic commands handled centrally
(`FIOCLEX`, `FIONCLEX`, `FIONBIO`, `FIOASYNC`, `FIOQSIZE`, `FIFREEZE`, `FITHAW`,
`FIONREAD`, `FS_IOC_GETFLAGS`/`SETFLAGS`, `FS_IOC_FSGETXATTR`/`SETXATTR`,
`FICLONE(RANGE)`, `FIDEDUPERANGE`, `FIGETBSZ`, `FS_IOC_FIEMAP`). Everything
driver-specific exits that switch with `-ENOIOCTLCMD` and lands in the
`f_op->unlocked_ioctl` of the file's driver -- which is why one libc function
can touch a tty, a sound device, an NVMe controller, or a loop device through
the same `SC-ioctl` slot while the kernel-side code paths diverge completely.
The terminal half is now sourced end to end at the cached sources'
granularity: `ioctl_tty.2` (cached man-pages tree) documents the terminal
request contract -- `TCGETS`/`TCSETS` taking `struct termios *`, the
`termios2`/`TCGETS2` variants, and the wider `TIO*` set -- and the fetched
`drivers/tty/tty_io.c` names the file path: the tty `file_operations`
register `.unlocked_ioctl = tty_ioctl` (`tty_fops`, and `console_fops`;
`hung_up_tty_fops` gets `hung_up_tty_ioctl`), and `tty_ioctl` handles its
explicit cases (`TIOCGWINSZ`, `TIOCMGET`, `TCFLSH`, `TIOCGSERIAL`, ...) then
delegates what remains: `tty_jobctrl_ioctl` first, then the driver's
`tty->ops->ioctl`, then the line discipline's `ld->ops->ioctl`, mapping a
final `-ENOIOCTLCMD` to `-ENOTTY`. Flagged sub-claim: the exact site that
copies the termios struct (the tty_ioctl.c/`n_tty` layer below `tty_ioctl`)
is not itself in the fetched sources -- the dispatch chain and the request
contract are, so the row is documented with that boundary named. Page:
[ioctl](../syscalls/descriptors-io/ioctl.md);
the sysfs side of the same tty devices is XR-103 in the
[sibling map](./sysfs-driver-tools.md).

### XR-014 -- dynamic loader -> mmap/open/read -> ld.so program loading

| libc functions | syscalls | kernel subsystem | typed arrows |
|---|---|---|---|
| `GLIBC-dlopen`, `GLIBC-dlsym` | `SC-openat` (257), `SC-read` (0), `SC-mmap` (9), `SC-munmap` (11), `SC-mprotect` (10), `SC-close` (3) | `fs/open.c` (`do_sys_openat2`), `mm/mmap.c`, `mm/mprotect.c` | `GLIBC-dlopen` **implements** relocation and symbol resolution entirely in userspace; object mapping **wraps** the `openat`+`mmap` machinery; the VM layer **services** the mappings; symbol versioning is **gated-by** glibc (musl ignores it) |

There is **no dedicated syscall** for dynamic linking: `dlopen` is pure `ld.so`
work -- `openat` the object, `read` headers, `mmap` segments, `mprotect`
relocate-and-flag pages -- and `dlsym` is lookup bookkeeping. musl delta: the
loader is part of libc itself, dynamic lookup ignores symbol versions (flat
ABI; no `dlvsym`), and a statically linked musl program gets only a dlopen
stub rather than a loader. The GLIBC- rows for `dlopen`/`dlsym` live in the
ledger's exported-symbols section, which is also where the symbol-version
machinery (`GLIBC_2.2.5` and friends) that the loader itself consumes is
tracked. The loader's own view of the process image is covered in the
dynamic-linking page. Pages: [mmap](../syscalls/memory/mmap.md),
[mprotect](../syscalls/memory/mprotect.md); kernel side:
[mmap internals](../kernel/memory/mmap.md); userspace machinery:
[dynamic linking](../sysprog/dynamic-linking.md).

---

## Three exemplar paths

One read-side path, one contention path, one no-syscall path -- the three
shapes a "libc call" can take below libc:

```text
Exemplar 1 -- stdio write path (XR-001)

  GLIBC-printf  GLIBC-printf  GLIBC-printf     (format into FILE buffer;
        |             |             |           zero syscalls so far)
        +------+------+------+
                     |
              flush point (buffer full / fflush / fclose)
                     |
              SC-write or SC-writev   --->wraps--->  vfs_write()
                                                    [fs/read_write.c]
                                                           |
                                                           v
                                                    page cache, then driver queue

Exemplar 2 -- mutex under contention (XR-006)

  GLIBC-pthread_mutex_lock
        |
        +-- uncontended: atomic op on a userspace word (no syscall)
        |
        +-- contended:  SC-futex (FUTEX_WAIT) ----wraps----> futex wait queue
                        ... later SC-futex (FUTEX_WAKE)      [kernel/futex/*]

Exemplar 3 -- user lookup with no dedicated syscall (XR-012)

  GLIBC-getpwnam
        |
        +-- NSS dispatch per /etc/nsswitch.conf
        |     [files] -> parse /etc/passwd       (SC-openat + SC-read)
        |     [nscd]  -> nscd socket protocol    (SC-socket + SC-connect)
        |     other modules -> dlopen, then sockets as above
        |
        v
  the kernel never sees a "user lookup": only generic file and socket work
```

Reading the diagram: the connector lines are the **typed arrows** in action --
a `wraps` step is a thin libc-to-syscall translation, an `implements`
annotation means the work happened without any syscall, and the bracketed
paths are the kernel subsystems that service the call. The three exemplars
were chosen because they are the three interview-shaped answers to "what does
libc do below the API": batch it (XR-001), defer it until contention
(XR-006), or do it all in userspace (XR-012). Every other row in this map is
a variation on one of those three shapes.

## Status summary

| Rows | Status | Note |
|---|---|---|
| XR-001 .. XR-014 | documented (14) | sourced from the syscall/libc/kernel chapters listed per row; XR-012/XR-013 upgraded in the 7-d pass (XR-013 keeps its termios-answer-site boundary flagged in place) |

## Key Takeaways

- Three shapes below libc: thin wrappers (XR-002, XR-009, XR-011),
  userspace-implemented behavior with syscall support (XR-001, XR-003, XR-005,
  XR-006, XR-007, XR-012, XR-014), and composites that sequence several
  syscalls (XR-004, XR-008).
- The recurring libc-side deltas are small but constant: errno translation,
  no `EINTR` retry, short counts -- plus version-dependent wrapper arrivals
  (`getdents64` 2.30, `execveat` 2.34) that the ledgers pin.
- Every row of this map is now documented; the formerly limited rows were
  held back on named missing sources -- XR-012's musl passwd-lookup
  implementation (now cited from the musl tree) and XR-013's terminal-ioctl
  file path (now cited from fetched `tty_io.c` + cached `ioctl_tty.2`) --
  and upgraded only once those sources existed.

## Interview Questions

1. **How many syscalls does `printf("hi\n")` issue on a fresh program?**
   Usually zero at call time -- the text goes into the `FILE` buffer; the
   syscall (`SC-write`/`SC-writev`) happens at the flush point (XR-001).
2. **When does `pthread_mutex_lock` enter the kernel?** Only under contention:
   the uncontended acquire is a userspace atomic; blocking calls
   `SC-futex(FUTEX_WAIT)` and parks on a kernel futex queue (XR-006).
3. **Which syscall serves `getpwnam`?** None directly -- it is userspace NSS
   work over generic file/socket syscalls, which is why the row is a map row
   and not a wrapper row (XR-012).

## Cross-References

- [Method and coverage](../interface-encyclopedia.md) -- status vocabulary and citation rules.
- [Cross-layer maps overview](./overview.md) and [coverage ledger](./ledger.md) -- the 38 XR rows.
- [Syscall ledger](../syscalls/ledger.md) and [glibc ledger](../libc/ledger-glibc.md) -- `SC-`/`GLIBC-` IDs used above.
- [sysfs class -> driver model -> tools](./sysfs-driver-tools.md) and [feature matrix](./feature-matrix.md) -- the sibling maps.
- [futex](../kernel/sync/futex.md), [page cache](../kernel/memory/page-cache.md), [vDSO](../kernel/core/vdso-vsyscall.md) -- kernel-side companions for XR-006, XR-002, XR-010.
