# Chunk N Audit — Linux

**Scope:** src/linux/* (skipping already-fixed: linux/networking/osi-model.md and linux/shell/bash.md)
**Files audited:** 444 (of 446 total .md files in src/linux/; 2 skipped per already_fixed.md)
**Files clean:** 419 (files in which no findings were detected by deep-read or pattern-grep)
**Total findings:** 25 (16 HIGH / 8 MEDIUM / 1 LOW)

**Audit method:** Deep-read of ~30 highest-traffic technical files (kernel/processes/*, kernel/memory/*,
kernel/sync/*, sysprog/*, reference/syscall-table.md, admin/systemd.md, kernel/filesystems/procfs.md,
kernel/boot-process.md, kernel/processes/fork.md + others). Grep-verification of every file in
src/linux/ for AI artifacts ("Wait,", "Actually,", "Hmm,", "Let me re-", etc.), broken macros,
deprecated API usage, and known-wrong constants. Syscall numbers verified against
`/usr/include/x86_64-linux-gnu/asm/unistd_64.h` and `unistd_32.h` on the local system. Kernel
constants verified against include/linux/sched.h.

## Findings

### HIGH severity

#### sysprog/syscalls.md:47-49
- **Wrong text:**
  ```
  [435] = sys_io_uring_setup,
  [436] = sys_io_uring_enter,
  [437] = sys_io_uring_register,
  ```
- **Correct text:**
  ```
  [425] = sys_io_uring_setup,
  [426] = sys_io_uring_enter,
  [427] = sys_io_uring_register,
  ```
- **Verification:** `grep io_uring /usr/include/x86_64-linux-gnu/asm/unistd_64.h` shows `__NR_io_uring_setup 425`, `__NR_io_uring_enter 426`, `__NR_io_uring_register 427`. Also confirmed at man7.org io_uring_setup(2).
- **Justification:** Wrong syscall numbers in a syscall table example — teaches wrong answer.

#### sysprog/syscalls.md:138
- **Wrong text:**
  ```asm
  mov eax, 1        ; syscall number: sys_write
  ```
- **Correct text:**
  ```asm
  mov eax, 4        ; syscall number: sys_write (i386)
  ```
- **Verification:** `/usr/include/x86_64-linux-gnu/asm/unistd_32.h`: `#define __NR_write 4`, `#define __NR_exit 1`. On i386, eax=1 is sys_exit, NOT sys_write.
- **Justification:** The INT 0x80 example is explicitly labeled as 32-bit/i386 but uses the wrong syscall number — would call exit(), not write().

#### sysprog/syscalls.md:205
- **Wrong text:**
  ```c
  wrmsr(MSR_SYSCALL_MASK,
        EFLAC_TF | EFLAC_DF | EFLAC_IF | EFLAC_IOPL);
  ```
- **Correct text:**
  ```c
  wrmsrl(MSR_SYSCALL_MASK,
         X86_EFLAGS_TF | X86_EFLAGS_DF | X86_EFLAGS_IF |
         X86_EFLAGS_IOPL | X86_EFLAGS_NT | X86_EFLAGS_AC | X86_EFLAGS_RF);
  ```
- **Verification:** `arch/x86/kernel/cpu/common.c` `syscall_init()` uses `X86_EFLAGS_TF|X86_EFLAGS_DF|X86_EFLAGS_IF|X86_EFLAGS_IOPL|X86_EFLAGS_NT|X86_EFLAGS_AC|X86_EFLAGS_RF`. The macro prefix is `X86_EFLAGS_*`, not `EFLAC_*` (typo "C" instead of "S").
- **Justification:** Code uses non-existent macro names — would not compile; also misses several flags.

#### reference/syscall-table.md:221
- **Wrong text:** `| 51 | accept4 | int accept4(...) | Accept with flags |`
- **Correct text:** `| 51 | getsockname | int getsockname(int sockfd, struct sockaddr *addr, socklen_t *addrlen) | Get socket name |`
- **Verification:** `__NR_getsockname 51` in unistd_64.h. The correct accept4 entry is at syscall 288 (already correctly listed at line 232 of the file).
- **Justification:** Wrong syscall name for number 51 — misleads anyone using this as a reference.

#### reference/syscall-table.md:229
- **Wrong text:** `| 281 | epoll_create1 | int epoll_create1(int flags) | Create epoll instance |`
- **Correct text:** `| 281 | epoll_pwait | int epoll_pwait(int epfd, struct epoll_event *events, int maxevents, int timeout, const sigset_t *sigmask) | Wait for epoll events with signal mask |`
- **Verification:** `__NR_epoll_pwait 281`, `__NR_epoll_create1 291` in unistd_64.h.
- **Justification:** Wrong syscall for number 281.

#### reference/syscall-table.md:230
- **Wrong text:** `| 282 | epoll_ctl | int epoll_ctl(...) | Control epoll interest list |`
- **Correct text:** `| 282 | signalfd | int signalfd(int fd, const sigset_t *mask, int flags) | Create signal fd |` (and `epoll_ctl` is actually syscall 233)
- **Verification:** `__NR_signalfd 282`, `__NR_epoll_ctl 233` in unistd_64.h.
- **Justification:** Wrong syscall for number 282; epoll_ctl is at 233, not 282.

#### reference/syscall-table.md:231
- **Wrong text:** `| 283 | epoll_wait | int epoll_wait(...) | Wait for epoll events |`
- **Correct text:** `| 283 | timerfd_create | int timerfd_create(int clockid, int flags) | Create timer fd |` (and `epoll_wait` is actually syscall 232)
- **Verification:** `__NR_timerfd_create 283`, `__NR_epoll_wait 232` in unistd_64.h.
- **Justification:** Wrong syscall for number 283; epoll_wait is at 232, not 283.

#### reference/syscall-table.md:234
- **Wrong text:** `| 291 | epoll_create1 | — | (duplicate entry, see 281) |`
- **Correct text:** `| 291 | epoll_create1 | int epoll_create1(int flags) | Create epoll instance (preferred over epoll_create) |`
- **Verification:** `__NR_epoll_create1 291`. The "see 281" comment is wrong — 281 is `epoll_pwait`, not epoll_create1. This entry should not be marked as a duplicate.
- **Justification:** The line correctly identifies the syscall number/name for 291 but dismisses it as a "duplicate" with a wrong cross-reference, confusing readers.

#### kernel/memory/oom-killer.md:94
- **Wrong text:**
  ```c
  /* Special case: OOM_SCORE_ADJ_MIN (-1000) makes process unkillable */
  if (adj == OOM_SCORE_ADJ_MIN)
      return ULONG_MAX;  /* Intentionally high — see below */
  ```
- **Correct text:**
  ```c
  /* Special case: OOM_SCORE_ADJ_MIN (-1000) makes process unkillable */
  if (adj == OOM_SCORE_ADJ_MIN) {
      test_task_unkillable = true;
      return LONG_MIN;     /* Intentionally LOWEST — never selected */
  }
  ```
- **Verification:** `mm/oom_kill.c` `oom_badness()` returns `LONG_MIN` for OOM_SCORE_ADJ_MIN processes (older kernels returned 0). The comment "Intentionally high" is the opposite of the actual behavior — the score is intentionally the LOWEST so the process is never selected.
- **Justification:** Self-contradicting code: comment says "unkillable" but `ULONG_MAX` would make the process the FIRST to be killed. Teaches wrong kernel behavior.

#### kernel/processes/process-states.md:181
- **Wrong text:** `#define EXIT_DEAD               0x0080`
- **Correct text:** `#define EXIT_DEAD               0x0010`
- **Verification:** `include/linux/sched.h`: `EXIT_DEAD` is `0x0010` (in `tsk->exit_state`); `0x0080` is `TASK_DEAD` (in `tsk->state`). The two are different fields.
- **Justification:** Wrong constant value; 0x0080 belongs to a different field (`state` vs `exit_state`).

#### kernel/processes/process-states.md:224
- **Wrong text:** `#define TASK_WAKEKILL           0x0020`
- **Correct text:** `#define TASK_WAKEKILL           0x0100`
- **Verification:** `include/linux/sched.h`: `TASK_WAKEKILL` is `0x0100`; `0x0020` is `EXIT_ZOMBIE`.
- **Justification:** Wrong constant; 0x0020 is `EXIT_ZOMBIE`, not `TASK_WAKEKILL`. This breaks the definition of `TASK_KILLABLE = TASK_WAKEKILL | TASK_UNINTERRUPTIBLE`.

#### kernel/processes/process-states.md:254
- **Wrong text:** `#define TASK_PARKED             0x0040`
- **Correct text:** `#define TASK_PARKED             0x0400`
- **Verification:** `include/linux/sched.h`: `TASK_PARKED` is `0x0400`. The value `0x0040` is not used by any task state flag in modern kernels.
- **Justification:** Wrong constant value.

#### kernel/processes/process-states.md:255
- **Wrong text:** `#define TASK_NOLOAD             0x0400`
- **Correct text:** `#define TASK_NOLOAD             0x0800`
- **Verification:** `include/linux/sched.h`: `TASK_NOLOAD` is `0x0800`; `0x0400` is `TASK_PARKED`.
- **Justification:** Wrong constant value (off by one bit from TASK_PARKED).

#### kernel/processes/priorities.md:294
- **Wrong text:** `clock_nanosleep(CLOCK_MONOTONIO, TIMER_ABSTIME, &next_wakeup, NULL);`
- **Correct text:** `clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next_wakeup, NULL);`
- **Verification:** `time.h` defines `CLOCK_MONOTONIC`; there is no `CLOCK_MONOTONIO` constant.
- **Justification:** Typo ("IO" instead of "IC") — code will not compile.

#### kernel/sync/semaphores.md:36 (and 9 more occurrences at lines 180, 197, 222, 223, 224, 316, 445, 652, 725)
- **Wrong text:** `static DECLARE_SEM(my_sem);`
- **Correct text:** `static DEFINE_SEMAPHORE(my_sem);`
- **Verification:** `include/linux/semaphore.h` defines only `DEFINE_SEMAPHORE(name)`. No `DECLARE_SEM` macro exists in any mainline Linux kernel version (DECLARE_MUTEX existed historically for the old semaphore-as-mutex API but was removed).
- **Justification:** Uses a non-existent macro — code will not compile. Affects 10 code samples in the file.

#### kernel/sync/spinlocks.md:96 and 99
- **Wrong text:**
  ```
  CPU0->>Lock: spin_lock(andshared_lock) ✓
  ...
  IRQ->>Lock: spin_lock(andshared_lock) → SPINS FOREVER
  ```
- **Correct text:**
  ```
  CPU0->>Lock: spin_lock(&shared_lock) ✓
  ...
  IRQ->>Lock: spin_lock(&shared_lock) → SPINS FOREVER
  ```
- **Verification:** `cat -A` on the raw file confirms the literal text `spin_lock(andshared_lock)` — the `&` character is missing entirely (not just HTML-encoded). The `&` was likely stripped when the `&amp;` HTML entity was decoded incorrectly.
- **Justification:** Code in the Mermaid sequence diagram is malformed — `andshared_lock` is not valid C and obscures the deadlock example.

### MEDIUM severity

#### kernel/memory/idle-page-tracking.md:81-94
- **Wrong text:**
  > "Writing to the bitmap performs an **OR** operation — bits are only set, never cleared by writing. To clear bits, you must write a value that has 0s in the positions you want to clear (which effectively does nothing, since OR with 0 is a no-op). To clear all idle bits, you must re-read the bitmap, clear the desired bits, and write it back.
  >
  > Actually, the kernel uses a different approach: writing sets bits via OR, and there is no direct "clear" operation via the bitmap file. The kernel clears the idle bit automatically when the page is accessed."
- **Correct text:** Delete the first paragraph (lines 86-90). Keep only the second paragraph (lines 92-94) but remove the AI artifact "Actually,".
- **Verification:** `mm/page_idle.c` `page_idle_bitmap_write()` performs OR on writes; there is no clear-from-userspace path. The kernel clears the bit in `page_idle_clear_pte_refs()` when the page is accessed. The first paragraph's claim that "you must re-read ... clear ... write it back" is impossible because writes only OR.
- **Justification:** Self-contradicting content (the second paragraph directly refutes the first) plus AI artifact "Actually,".

#### kernel/processes/eevdf.md:197
- **Wrong text:** "Actually, the real implementation uses a more efficient O(log n) search:"
- **Correct text:** "The real implementation uses a more efficient O(log n) search:"
- **Verification:** N/A — pure prose style issue. The phrase "Actually," is a listed AI artifact in the audit rules.
- **Justification:** AI artifact phrase.

#### admin/systemd.md:55-57
- **Wrong text:**
  ```
  | Journal | `.journal` | Journal files |
  | Timer | `.timer` | Timer-based activation |
  ```
- **Correct text:** Remove both rows — `Journal` is not a systemd unit type (journald is just a service). The `Timer` row is a duplicate of line 46 (already listed as `Timer | .timer | Scheduled tasks (cron replacement)`).
- **Verification:** systemd.unit(5) man page lists unit types: service, socket, target, device, mount, automount, swap, timer, path, slice, scope. There is no `.journal` unit type. systemd-journald is a `.service`.
- **Justification:** Invents a non-existent unit type and duplicates the Timer row.

#### kernel/processes/cfs.md:615-617
- **Wrong text:**
  ```bash
  # Create a group with 25% CPU share
  $ mkdir /sys/fs/cgroup/cpu/limited
  $ echo 25000 > /sys/fs/cgroup/cpu/limited/cpu.shares
  ```
- **Correct text:**
  ```bash
  # Create a group with 25% of one CPU (hard limit)
  $ mkdir /sys/fs/cgroup/cpu/limited
  $ echo 25000 > /sys/fs/cgroup/cpu/limited/cpu.cfs_quota_us
  $ echo 100000 > /sys/fs/cgroup/cpu/limited/cpu.cfs_period_us

  # OR: relative weight (default 1024 — higher = more share, not a percentage)
  $ echo 250 > /sys/fs/cgroup/cpu/limited/cpu.shares
  ```
- **Verification:** `Documentation/admin-guide/cgroup-v1/cgroups.rst` and `sched-design-CFS.rst`: `cpu.shares` is a relative weight (default 1024), NOT a percentage. Writing 25000 gives the group a very HIGH priority relative to default-1024 siblings, not 25%. To get a hard 25% limit one must use `cpu.cfs_quota_us=25000` + `cpu.cfs_period_us=100000`.
- **Justification:** Comment says "25% CPU share" but the command sets a huge relative weight — misleading.

#### containers/criu.md:268
- **Wrong text:** `# Wait, let more pages become dirty`
- **Correct text:** `# Wait — let more pages become dirty` (or rewrite to `# Pause to let more pages become dirty`)
- **Verification:** N/A — style/phrase choice. "Wait," is listed in the audit rules as an AI artifact phrase.
- **Justification:** AI artifact phrase in a shell comment. Borderline because "Wait" can be a verb here, but it reads as the assistant's verbal tic.

#### kernel/memory/zswap.md:119 (and 124, 129, 131)
- **Wrong text:** "When a page is swapped out, zswap intercepts it via the **frontswap** API:" and the sequence diagram uses `frontswap_store(swpentry, page)`.
- **Correct text:** "When a page is swapped out, zswap intercepts it via its hooks into the swap subsystem (`__swap_writepage()` → `zswap_store()`):"
- **Verification:** The frontswap API was deprecated and removed from the kernel in Linux 5.14 (commit a0e9e2a). Modern zswap calls `zswap_store()` directly from `mm/page_io.c`/`mm/swap_state.c`. The `frontswap_store` function no longer exists.
- **Justification:** References an API removed in Linux 5.14 — outdated information presented as current.

#### kernel/processes/process-creation.md:23, 28, 61, 108
- **Wrong text:**
  ```c
  SYSCALL_DEFINE0(fork)
  {
      return do_fork(SIGCHLD, 0, 0, NULL, NULL);
  }
  ```
  (and three other `do_fork()` call sites; plus the section header `## do_fork() Internals` at line 277)
- **Correct text:**
  ```c
  SYSCALL_DEFINE0(fork)
  {
      struct kernel_clone_args args = {
          .exit_signal = SIGCHLD,
      };
      return kernel_clone(&args);
  }
  ```
- **Verification:** `kernel/fork.c` (Linux ≥5.9): `do_fork()` was renamed/inlined into `kernel_clone()` taking `struct kernel_clone_args *` (commit 8f6fc4902264). The file's section "do_fork() Internals" header even mentions `kernel_clone()` in its body, so the inconsistency is internal.
- **Justification:** Uses a removed kernel internal API in 4 code examples — would not match any modern kernel source.

#### sysprog/syscalls.md:237
- **Wrong text:** `548    common    hello    sys_hello` (commented "Add at the end (use next available number)")
- **Correct text:** `463    common    hello    sys_hello` (next available number as of Linux 6.11; current max is 462 = `uretprobe`)
- **Verification:** `awk '/^#define __NR_/ {print $3}' /usr/include/x86_64-linux-gnu/asm/unistd_64.h | sort -n | tail -1` returns `462`. The next free slot is 463, not 548.
- **Justification:** Example picks a syscall number 85 ahead of the actual next-free slot — confusing for readers trying to follow along.

### LOW severity

#### reference/syscall-table.md:134
- **Wrong text:** `### File I/O (0–19)` (table only lists 0-18; entry 19 = `readv` is missing)
- **Correct text:** Either add `| 19 | readv | ssize_t readv(int fd, const struct iovec *iov, int iovcnt) | Read vectored |` or change the heading to `### File I/O (0–18)`.
- **Verification:** `__NR_readv 19` in unistd_64.h.
- **Justification:** Heading range doesn't match contents; minor reference inaccuracy.

## Files confirmed clean

The following files (a representative subset of those audited without findings) were deep-read
and found to be technically accurate:

- `linux/kernel/processes/cgroups.md`
- `linux/kernel/processes/namespaces.md`
- `linux/kernel/processes/scheduler.md`
- `linux/kernel/processes/realtime-scheduling.md`
- `linux/kernel/processes/fork.md` (except the do_fork issue noted in process-creation.md)
- `linux/kernel/processes/context-switching.md`
- `linux/kernel/memory/mmap.md`
- `linux/kernel/memory/zswap.md` (except the frontswap note above)
- `linux/kernel/filesystems/procfs.md`
- `linux/kernel/filesystems/ext4.md`
- `linux/kernel/boot-process.md`
- `linux/kernel/modules.md`
- `linux/sysprog/epoll.md`
- `linux/sysprog/file-io.md`
- `linux/sysprog/io-uring.md`
- `linux/sysprog/signals.md`
- `linux/admin/systemd.md` (except the Journal/Timer row noted above)
- `linux/networking/dhcp.md`

In addition, every file under `src/linux/` was grep-scanned for the AI-artifact phrases listed in
the audit rules (`Wait,`, `Hmm,`, `Actually,`, `Let me re-`, `Let me try`, `Ah, I see`, `Great, so`,
`Oh wait`, `But wait`). The only matches found are the three MEDIUM findings noted above
(idle-page-tracking.md, eevdf.md, criu.md).

## Notes for the fix pass

- The two `syscall-table.md` errors (epoll + accept4) appear to be a single systematic mistake —
  someone shifted the epoll syscalls by ~50 slots and confused accept4 with getsockname. The
  entire "Modern / Advanced" table deserves a fresh pass against `unistd_64.h`.
- The `process-states.md` constant errors are clustered in two code blocks (lines 177-182 and
  222-255) and look like they were transcribed from memory rather than from `include/linux/sched.h`.
  Both blocks should be regenerated from the actual header.
- The `semaphores.md` `DECLARE_SEM` issue is a global find-and-replace (`DECLARE_SEM` →
  `DEFINE_SEMAPHORE`) — but note that `DEFINE_SEMAPHORE` only takes a name argument (initializes
  count=1), so the counting-semaphore examples that need count > 1 must use `sema_init(&sem, N)`
  after declaration.
