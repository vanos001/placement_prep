# futex(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | futex: 202 / 240 / 98 / 240; futex_time64: - / 422 / - / 422; futex_waitv: 449 / 449 / 449 / 449; futex_wake: 454 (all four columns); futex_wait: 455 (all); futex_requeue: 456 (all) |
| Since (kernel) | futex 2.6 (hub; futex.2 VERSIONS: stable with 2.6.0, merged 2.5.7, 6-arg form by 2.6.7); futex_waitv 5.16 (worklog 1-a table bisection; ledger Since "-"); futex_wait/futex_wake/futex_requeue ledger Since 6.14, but worklog 1-a found numbers 454-456 first present in v6.7 kernel tables; futex_time64 Since not recorded (ledger "-"), unverified |
| Man page | man2/futex.2 (cached, dated 2021-08-27); futex_waitv.2 fetched from man7.org (man-pages 6.19); no man pages exist for futex_wait/futex_wake/futex_requeue (status/1-a.status: source-limited, kernel source only) |
| glibc wrapper | none: glibc provides no wrapper for futex() (futex.2 note); no futex symbol exported by installed glibc 2.41 (nm -D); futex.2 NOTES lists the pthreads/semaphore abstractions built on futexes |
| Aliases covered | futex_time64, futex_waitv, futex_wait, futex_wake, futex_requeue (documented inline per the alias map) |
| Ledger ID | SC-futex, SC-futex_time64, SC-futex_waitv, SC-futex_wait, SC-futex_wake, SC-futex_requeue |

## Purpose

futex() provides wait/wake primitives over a 32-bit "futex word" in shared memory: user space performs the fast-path synchronization atomically and only invokes the kernel when blocking (FUTEX_WAIT) or waking (FUTEX_WAKE) is likely needed. POSIX mutexes, condvars, rwlocks, and semaphores are built on it (futex.2). The 6.7 "futex2" calls futex_wait/futex_wake/futex_requeue and 5.16 futex_waitv expose the same engine through non-multiplexed, variable-sized entry points.

## Synopsis

```c
#include <linux/futex.h>
long syscall(SYS_futex, uint32_t *uaddr, int futex_op, uint32_t val,
             const struct timespec *timeout /* or uint32_t val2 */,
             uint32_t *uaddr2, uint32_t val3);

long syscall(SYS_futex_waitv, struct futex_waitv *waiters,
             unsigned int n, unsigned int flags,
             const struct timespec *timeout, clockid_t clockid);
```

futex2 signatures (kernel/futex/syscalls.c, fetched from torvalds master): `futex_wake(uaddr, mask, nr, flags)`; `futex_wait(uaddr, val, mask, flags, timeout, clockid)` (timeout absolute); `futex_requeue(struct futex_waitv *waiters, flags /* must be 0 */, nr_wake, nr_requeue)`.

## Arguments and behavior

uaddr points to the 4-byte-aligned futex word; futex_op is a command ORed with option bits FUTEX_PRIVATE_FLAG (128, since 2.6.22, process-private fast path) and FUTEX_CLOCK_REALTIME (256, since 2.6.28, valid with FUTEX_WAIT_BITSET, FUTEX_WAIT_REQUEUE_PI, FUTEX_WAIT (4.5+), FUTEX_LOCK_PI2 (5.14+)); timeout measures CLOCK_MONOTONIC by default. For requeue/wake_op operations the timeout slot is reinterpreted as the integer val2. Blocking ops compare the word against the expected value atomically and fail with EAGAIN on mismatch (lost-wakeup protection).

| Operation (futex_op, /usr/include/linux/futex.h) | Value | Effect (futex.2) | Since |
|---|---|---|---|
| FUTEX_WAIT | 0 | sleep if *uaddr == val; relative timeout | 2.6.0 |
| FUTEX_WAKE | 1 | wake up to val waiters | 2.6.0 |
| FUTEX_FD | 2 | pollable fd; inherently racy, removed in 2.6.26 | 2.6.0-2.6.25 |
| FUTEX_REQUEUE | 3 | wake val, requeue up to val2 to uaddr2 (no value check) | 2.6.0 |
| FUTEX_CMP_REQUEUE | 4 | as above but only if *uaddr == val3 | 2.6.7 |
| FUTEX_WAKE_OP | 5 | atomic read-modify-write on uaddr2, then wakes; op/cmp encoded in val3 (FUTEX_OP macro) | 2.6.14 |
| FUTEX_LOCK_PI | 6 | priority-inheritance lock | 2.6.18 |
| FUTEX_UNLOCK_PI | 7 | PI unlock | 2.6.18 |
| FUTEX_TRYLOCK_PI | 8 | nonblocking PI lock | 2.6.18 |
| FUTEX_WAIT_BITSET | 9 | wait with absolute timeout and 32-bit wake mask in val3 | 2.6.25 |
| FUTEX_WAKE_BITSET | 10 | wake waiters whose mask ANDs val3 | 2.6.25 |
| FUTEX_WAIT_REQUEUE_PI | 11 | PI wait then requeue to uaddr2 | 2.6.31 |
| FUTEX_CMP_REQUEUE_PI | 12 | PI-aware requeue with val3 check | 2.6.31 |
| FUTEX_LOCK_PI2 | 13 | PI lock with CLOCK_REALTIME-capable timeout | 5.14 |

futex_waitv (man-pages 6.19 futex_waitv.2; kernel 5.16) atomically waits on up to FUTEX_WAITV_MAX (128) futex words described by struct futex_waitv { u64 val; u64 uaddr; u32 flags; u32 __reserved; }; each waiter's flags must contain exactly one size flag: FUTEX2_SIZE_U8 0x00, FUTEX2_SIZE_U16 0x01, FUTEX2_SIZE_U32 0x02, FUTEX2_SIZE_U64 0x03 (only U32 supported; others EINVAL), optionally FUTEX2_NUMA (0x04) and FUTEX2_PRIVATE (= FUTEX_PRIVATE_FLAG, 128). It returns the index of a woken waiter. The futex2 trio mirrors FUTEX_WAKE_BITSET / FUTEX_WAIT_BITSET / FUTEX_CMP_REQUEUE with FUTEX2_* flags instead of the multiplexed op byte (kernel source comments).

## Return value and errors

Error: -1 with errno. Success is per operation (futex.2): WAIT/WAIT_BITSET/WAIT_REQUEUE_PI/LOCK_PI/UNLOCK_PI/TRYLOCK_PI return 0 (treat 0 as a possible spurious wakeup and recheck the word); WAKE/WAKE_BITSET/REQUEUE/CMP_REQUEUE(/_PI) return the number woken or woken+requeued; WAKE_OP returns the total woken on both words; futex_waitv returns the index of a woken waiter. Main errors: EAGAIN (value mismatch; also ETIMEDOUT on expiry), EACCES (no read access to the word), EFAULT, EINVAL (bad op/flags/alignment), EINTR, EDEADLK (PI re-lock), EPERM/ESRCH (PI owner checks), EMFILE/ENFILE (removed FUTEX_FD). futex_waitv adds EINVAL for n outside [1, FUTEX_WAITV_MAX], unknown/unsupported flags, nonzero __reserved, or misaligned uaddr (futex_waitv.2).

## Flags and constants

See the operation table (values verified in /usr/include/linux/futex.h). FUTEX_BITSET_MATCH_ANY = 0xffffffff; FUTEX_WAITV_MAX = 128; robust-futex bits FUTEX_WAITERS 0x80000000, FUTEX_OWNER_DIED 0x40000000, FUTEX_TID_MASK 0x3fffffff (same header). FUTEX2_SIZE_MASK = 0x03.

## Security and notes

The six numbers share one page per the domain alias map: the ledger marks futex_wait/futex_wake/futex_requeue source-limited (no man page reachable; documented from kernel/futex/syscalls.c) and futex_time64 lacks a recorded Since - treat its introduction version as unverified. set_tid_address(2) wires the CLONE_CHILD_CLEARTID exit wake, which threads libraries implement as futex(FUTEX_WAKE, 1) on the clear_child_tid address (set_tid_address.2). Cross-reference: [clone](clone.md), [set_tid_address](set_tid_address.md).

## References

- https://man7.org/linux/man-pages/man2/futex.2.html
- https://man7.org/linux/man-pages/man2/futex_waitv.2.html (fetched; man-pages 6.19)
- kernel/futex/syscalls.c, Documentation/userspace-api/futex2.rst (torvalds master; named in worklog 1-a)
- /usr/include/linux/futex.h (op and FUTEX2_* values)
